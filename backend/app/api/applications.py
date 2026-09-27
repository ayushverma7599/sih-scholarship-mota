"""Applicant portal: scheme discovery, applications, documents, deficiency inbox."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rbac import get_current_user, require_roles
from app.models import (
    AIFlag, AppStatus, Application, ApplicationDocument, Deficiency,
    ExtractedField, Roles, Scheme, StatusEvent, User,
)
from app.schemas import (
    ApplicationCreateIn, ApplicationUpdateIn, DeficiencyRespondIn,
)
from app.services import audit, classify, crossverify, risk, rule_engine
from app.services.extractor import get_extractor
from app.services.notifications import notify
from app.services.pipeline import run_auto_verification
from app.services.serialize import application_public
from app.services.storage import get_storage, sha256_bytes

router = APIRouter()


# --------------------------------------------------------------------------- #
# Scheme discovery with instant eligibility pre-check
# --------------------------------------------------------------------------- #
@router.get("/me/eligible-schemes")
def eligible_schemes(db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    out = []
    for scheme in db.query(Scheme).filter(Scheme.is_active == True).all():  # noqa: E712
        ctx = rule_engine.build_context(user.profile, {})
        result = rule_engine.evaluate(scheme.ruleset.rules if scheme.ruleset else None, ctx)
        out.append({
            "scheme_id": scheme.id, "code": scheme.code, "name": scheme.name,
            "description": scheme.description, "academic_year": scheme.academic_year,
            "slots": scheme.slots, "is_sample": scheme.is_sample,
            "eligible": result["eligible"], "summary": result["summary"],
            "reasons": result["results"],
        })
    # Likely-eligible first
    out.sort(key=lambda s: (not s["eligible"], s["code"]))
    return out


# --------------------------------------------------------------------------- #
# Application CRUD / draft / submit
# --------------------------------------------------------------------------- #
@router.get("/me/applications")
def my_applications(db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    apps = (db.query(Application).filter(Application.user_id == user.id)
            .order_by(Application.updated_at.desc()).all())
    return [application_public(a) for a in apps]


@router.post("/applications", status_code=201)
def create_application(payload: ApplicationCreateIn, db: Session = Depends(get_db),
                       user: User = Depends(require_roles(Roles.APPLICANT))):
    scheme = db.get(Scheme, payload.scheme_id)
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    existing = (db.query(Application)
                .filter(Application.user_id == user.id,
                        Application.scheme_id == scheme.id)
                .first())
    if existing:
        raise HTTPException(409, "You already have an application for this scheme.")
    app = Application(user_id=user.id, scheme_id=scheme.id,
                      status=AppStatus.DRAFT, form_data=payload.form_data, draft={})
    db.add(app)
    db.commit()
    db.refresh(app)
    return application_public(app, detail=True)


def _owned_app(db: Session, app_id: int, user: User) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.user_id != user.id and user.role.name not in (Roles.SCRUTINY, Roles.COMMITTEE, Roles.ADMIN):
        raise HTTPException(403, "Not your application")
    return app


@router.get("/applications/{app_id}")
def get_application(app_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    app = _owned_app(db, app_id, user)
    return application_public(app, detail=True)


@router.put("/applications/{app_id}")
def update_application(app_id: int, payload: ApplicationUpdateIn,
                       db: Session = Depends(get_db),
                       user: User = Depends(require_roles(Roles.APPLICANT))):
    app = _owned_app(db, app_id, user)
    if app.status not in (AppStatus.DRAFT, AppStatus.DEFICIENCY_RAISED):
        raise HTTPException(409, "Application can no longer be edited.")
    if payload.form_data is not None:
        app.form_data = payload.form_data
    if payload.draft is not None:
        app.draft = payload.draft
    db.commit()
    db.refresh(app)
    return application_public(app, detail=True)


@router.post("/applications/{app_id}/submit")
def submit_application(app_id: int, db: Session = Depends(get_db),
                       user: User = Depends(require_roles(Roles.APPLICANT))):
    app = _owned_app(db, app_id, user)
    if app.status not in (AppStatus.DRAFT, AppStatus.DEFICIENCY_RAISED, AppStatus.RESUBMITTED):
        raise HTTPException(409, f"Cannot submit from status {app.status}.")
    prev = app.status
    app.submitted_at = app.submitted_at or datetime.now(timezone.utc)
    db.add(StatusEvent(application_id=app.id, from_status=prev,
                       to_status=AppStatus.SUBMITTED, actor_id=user.id,
                       note="Application submitted."))
    app.status = AppStatus.SUBMITTED
    db.commit()
    result = run_auto_verification(db, app, actor=user)
    db.refresh(app)
    return {"application": application_public(app, detail=True), "auto_verification": result}


@router.post("/applications/{app_id}/resubmit")
def resubmit_application(app_id: int, db: Session = Depends(get_db),
                         user: User = Depends(require_roles(Roles.APPLICANT))):
    app = _owned_app(db, app_id, user)
    if app.status != AppStatus.DEFICIENCY_RAISED:
        raise HTTPException(409, "Only applications with raised deficiencies can be resubmitted.")
    db.add(StatusEvent(application_id=app.id, from_status=app.status,
                       to_status=AppStatus.RESUBMITTED, actor_id=user.id,
                       note="Applicant resubmitted after addressing deficiencies."))
    app.status = AppStatus.RESUBMITTED
    db.commit()
    result = run_auto_verification(db, app, actor=user)
    db.refresh(app)
    return {"application": application_public(app, detail=True), "auto_verification": result}


# --------------------------------------------------------------------------- #
# Document upload — instant feedback: classify + OCR + cross-verify inline
# --------------------------------------------------------------------------- #
def _process_document(db: Session, app: Application, adoc: ApplicationDocument,
                      scheme_doc, income_limit):
    extractor = get_extractor()
    fields = scheme_doc.extract_fields if scheme_doc else []

    # Classification
    cls = classify.classify(adoc.file_path, expected=adoc.doc_type)
    adoc.detected_type = cls["detected"]

    # OCR extraction
    extracted = extractor.extract(adoc.file_path, fields) if fields else {}
    confidences = [v.get("confidence", 0) for v in extracted.values()] or [cls["confidence"]]
    adoc.readability = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    for key, v in extracted.items():
        db.add(ExtractedField(app_document_id=adoc.id, key=key,
                              value=str(v.get("value", "")), confidence=v.get("confidence", 0)))

    # Per-document flags: wrong doc type
    if not cls["matches_expected"] and cls["detected"]:
        db.add(AIFlag(application_id=app.id, type="wrong_document", severity="high",
                      confidence=cls["confidence"],
                      reason=(f"Uploaded file for slot '{adoc.doc_type}' looks like a "
                              f"'{cls['detected']}'.")))

    # Cross-verification vs form data
    form_ctx = dict(app.form_data or {})
    form_ctx.setdefault("full_name", app.applicant.full_name)
    for flag in crossverify.cross_verify(extracted=extracted, form_data=form_ctx,
                                          income_limit=income_limit):
        db.add(AIFlag(application_id=app.id, **flag))

    db.flush()
    return {
        "detected_type": adoc.detected_type,
        "matches_expected": cls["matches_expected"],
        "readability": adoc.readability,
        "extracted": [{"key": k, **v} for k, v in extracted.items()],
    }


def _income_limit(scheme: Scheme) -> float | None:
    if not scheme.ruleset:
        return None
    for r in scheme.ruleset.rules.get("rules", []):
        if r.get("field") in ("family_income", "income") and r.get("op") in ("<=", "<"):
            try:
                return float(r.get("value"))
            except (TypeError, ValueError):
                return None
    return None


@router.post("/applications/{app_id}/documents")
def upload_document(
    app_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Roles.APPLICANT)),
):
    app = _owned_app(db, app_id, user)
    if file.content_type not in settings.allowed_upload_types:
        raise HTTPException(415, f"Unsupported file type '{file.content_type}'. "
                                 f"Allowed: {', '.join(settings.allowed_upload_types)}")
    data = file.file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_MB} MB limit.")

    storage = get_storage()
    path = storage.save(data, file.filename or "upload", subdir=f"app_{app.id}")
    digest = sha256_bytes(data)

    scheme_doc = next((sd for sd in app.scheme.documents if sd.doc_type == doc_type), None)

    # Replace an existing doc in the same slot (re-upload semantics).
    old = [d for d in app.documents if d.doc_type == doc_type]
    for d in old:
        db.delete(d)
    db.flush()

    adoc = ApplicationDocument(
        application_id=app.id, scheme_document_id=scheme_doc.id if scheme_doc else None,
        doc_type=doc_type, file_path=path, original_name=file.filename or "",
        content_type=file.content_type, sha256=digest,
    )
    db.add(adoc)
    db.flush()
    feedback = _process_document(db, app, adoc, scheme_doc, _income_limit(app.scheme))
    db.commit()
    return {"document_id": adoc.id, "doc_type": doc_type, **feedback}


@router.get("/documents/{doc_id}/file")
def get_document_file(doc_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    from fastapi.responses import FileResponse
    adoc = db.get(ApplicationDocument, doc_id)
    if not adoc:
        raise HTTPException(404, "Document not found")
    app = adoc.application
    if app.user_id != user.id and user.role.name not in (Roles.SCRUTINY, Roles.COMMITTEE, Roles.ADMIN):
        raise HTTPException(403, "Not authorized")
    return FileResponse(adoc.file_path, media_type=adoc.content_type or "application/octet-stream",
                        filename=adoc.original_name or f"document_{doc_id}")


# --------------------------------------------------------------------------- #
# Deficiency inbox
# --------------------------------------------------------------------------- #
@router.get("/applications/{app_id}/deficiencies")
def list_deficiencies(app_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    app = _owned_app(db, app_id, user)
    return [
        {"id": d.id, "doc_type": d.doc_type, "message": d.message,
         "status": d.status, "applicant_response": d.applicant_response}
        for d in app.deficiencies
    ]


@router.post("/deficiencies/{def_id}/respond")
def respond_deficiency(def_id: int, payload: DeficiencyRespondIn,
                       db: Session = Depends(get_db),
                       user: User = Depends(require_roles(Roles.APPLICANT))):
    d = db.get(Deficiency, def_id)
    if not d:
        raise HTTPException(404, "Deficiency not found")
    if d.application.user_id != user.id:
        raise HTTPException(403, "Not your application")
    d.applicant_response = payload.response
    db.commit()
    return {"id": d.id, "status": d.status, "applicant_response": d.applicant_response}
