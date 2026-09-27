"""Auto-verification pipeline run on submit / resubmit.

Orchestrates the AI-assist layer end-to-end but never makes a final human decision:
  1. duplicate detection across applications
  2. eligibility evaluation (configurable rules)
  3. deficiency detection (missing/wrong/unreadable docs + high-severity flags)
  4. explainable risk score
  5. status transition (AUTO_VERIFIED when clean, DEFICIENCY_RAISED otherwise)

Per-document OCR / classification / cross-verification flags are created at upload
time (see api/applications.upload_document); this pass adds cross-application checks
and rolls everything up.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AIFlag, AppStatus, Application, Deficiency, StatusEvent, User
from app.services import audit, deficiency as deficiency_svc, duplicate, risk, rule_engine
from app.services.notifications import notify


def _transition(db: Session, app: Application, to_status: str,
                actor: User | None, note: str = ""):
    prev = app.status
    if prev == to_status:
        return
    db.add(StatusEvent(application_id=app.id, from_status=prev,
                       to_status=to_status, actor_id=actor.id if actor else None,
                       note=note))
    app.status = to_status
    audit.record(db, actor=actor, entity="application", entity_id=app.id,
                 action="status_change", before={"status": prev},
                 after={"status": to_status, "note": note}, commit=False)


def run_auto_verification(db: Session, app: Application,
                          actor: User | None = None) -> dict:
    scheme = app.scheme

    # 1) Cross-application duplicate detection (fresh each run)
    for f in list(app.flags):
        if f.type in ("duplicate_aadhaar", "duplicate_document", "duplicate_bank_account"):
            db.delete(f)
    db.flush()
    for flag in duplicate.find_duplicates(db, app):
        db.add(AIFlag(application_id=app.id, **flag))
    db.flush()

    # 2) Eligibility (configurable rules) against profile + form data
    ctx = rule_engine.build_context(app.applicant.profile, app.form_data)
    elig = rule_engine.evaluate(scheme.ruleset.rules if scheme.ruleset else None, ctx)
    if not elig["eligible"]:
        for r in elig["results"]:
            if not r["pass"]:
                # record an eligibility flag (dedup by reason)
                exists = any(fl.type == "ineligible" and fl.reason == r["reason"]
                             for fl in app.flags)
                if not exists:
                    db.add(AIFlag(application_id=app.id, type="ineligible",
                                  severity="high", confidence=0.95, reason=r["reason"]))
    db.flush()

    # 3) Deficiency detection -> refresh OPEN deficiencies
    for d in list(app.deficiencies):
        if d.status == "OPEN":
            db.delete(d)
    db.flush()
    detected = deficiency_svc.detect_deficiencies(app, scheme)
    if not elig["eligible"]:
        for r in elig["results"]:
            if not r["pass"]:
                detected.append({"doc_type": None, "message": r["reason"]})
    for item in detected:
        db.add(Deficiency(application_id=app.id, doc_type=item.get("doc_type"),
                          message=item["message"], status="OPEN"))
    db.flush()

    # 4) Explainable risk score
    r = risk.compute_risk(app.flags)
    app.risk_score = r["score"]

    # 5) Status transition
    db.refresh(app)
    has_open_def = any(d.status == "OPEN" for d in app.deficiencies)
    if has_open_def:
        _transition(db, app, AppStatus.DEFICIENCY_RAISED, actor,
                    note="Auto-detected deficiencies — applicant action required.")
        notify(db, user_id=app.user_id,
               title="Action needed on your application",
               message=(f"{sum(1 for d in app.deficiencies if d.status=='OPEN')} "
                        "item(s) need your attention. Please check your deficiency inbox."),
               channels=("in_app", "email"), commit=False)
    else:
        _transition(db, app, AppStatus.AUTO_VERIFIED, actor,
                    note="Passed automated checks — queued for scrutiny.")
        notify(db, user_id=app.user_id,
               title="Application auto-verified",
               message="Your application passed automated checks and is now queued for scrutiny.",
               channels=("in_app",), commit=False)

    db.commit()
    db.refresh(app)
    return {
        "status": app.status,
        "eligible": elig["eligible"],
        "risk": r,
        "open_deficiencies": sum(1 for d in app.deficiencies if d.status == "OPEN"),
        "active_flags": sum(1 for f in app.flags if not f.overridden),
    }
