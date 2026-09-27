"""Screening & Selection: merit list generation, committee review, publish, letters."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_roles
from app.models import (
    AppStatus, Application, Fellowship, MeritScore, Roles, StatusEvent, User,
)
from app.schemas import MeritAdjustIn
from app.services import audit, merit as merit_svc, pdfgen, rule_engine
from app.services.notifications import notify

router = APIRouter()


def _values_for(app: Application) -> dict:
    """Pull raw criterion values from form data + profile for scoring."""
    ctx = rule_engine.build_context(app.applicant.profile, app.form_data)
    return {
        "marks": ctx.get("marks") or ctx.get("qualifying_marks") or ctx.get("marks_percentage"),
        "marks_percentage": ctx.get("marks_percentage") or ctx.get("marks"),
        "family_income": ctx.get("family_income") or ctx.get("income"),
        "income_bracket": ctx.get("family_income") or ctx.get("income"),
        "university_rank": ctx.get("university_rank") or ctx.get("qs_rank"),
        "qs_rank": ctx.get("qs_rank") or ctx.get("university_rank"),
        "research_proposal": ctx.get("research_proposal_score") or ctx.get("research_proposal"),
        "research_proposal_score": ctx.get("research_proposal_score") or ctx.get("research_proposal"),
        "interview": ctx.get("interview"),
    }


def _attributes_for(app: Application) -> dict:
    p = app.applicant.profile or {}
    gender = str(p.get("gender", "")).lower()
    return {
        "women": gender in ("female", "f", "woman", "women"),
        "pvtg": bool(p.get("pvtg")) or str(p.get("tribe_type", "")).lower() == "pvtg",
    }


@router.post("/schemes/{scheme_id}/generate-merit")
def generate_merit(scheme_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(Roles.COMMITTEE, Roles.ADMIN))):
    from app.models import Scheme
    scheme = db.get(Scheme, scheme_id)
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    weights = scheme.merit_criteria.weights if scheme.merit_criteria else {}
    criteria = {
        "tiebreak": scheme.merit_criteria.tiebreak if scheme.merit_criteria else [],
        "quotas": scheme.merit_criteria.quotas if scheme.merit_criteria else {},
    }

    # Only screened (scrutiny-cleared) applications are eligible for the merit list.
    apps = (db.query(Application)
            .filter(Application.scheme_id == scheme_id,
                    Application.status.in_([AppStatus.SCREENED, AppStatus.SELECTED]))
            .all())
    if not apps:
        raise HTTPException(400, "No screened applications available to rank.")

    scored = []
    for a in apps:
        values = _values_for(a)
        s = merit_svc.score(weights, values)
        scored.append({
            "application_id": a.id, "total": s["total"], "breakdown": s["breakdown"],
            "values": values, "attributes": _attributes_for(a), "app": a,
        })

    ranked = merit_svc.rank_applicants(scored, criteria, scheme.slots)

    for item in ranked:
        a = item["app"]
        ms = a.merit or MeritScore(application_id=a.id)
        ms.total = item["total"]
        ms.breakdown = item["breakdown"]
        ms.rank = item["rank"]
        ms.quota_tag = item.get("quota_tag")
        a.merit = ms
        db.add(ms)
    db.commit()

    audit.record(db, actor=user, entity="scheme", entity_id=scheme_id,
                 action="generate_merit", after={"ranked": len(ranked), "slots": scheme.slots})

    return {
        "scheme_id": scheme_id, "slots": scheme.slots, "ranked": len(ranked),
        "list": [
            {
                "application_id": it["app"].id,
                "applicant_name": it["app"].applicant.full_name,
                "total": it["total"], "rank": it["rank"],
                "selected": it["selected"], "quota_tag": it.get("quota_tag"),
                "breakdown": it["breakdown"],
            }
            for it in ranked
        ],
    }


@router.get("/schemes/{scheme_id}/merit-list")
def merit_list(scheme_id: int, db: Session = Depends(get_db),
               user: User = Depends(require_roles(Roles.COMMITTEE, Roles.ADMIN))):
    apps = (db.query(Application)
            .filter(Application.scheme_id == scheme_id)
            .join(Application.merit).all())
    apps = [a for a in apps if a.merit]
    apps.sort(key=lambda a: (a.merit.rank or 1e9))
    return [
        {
            "application_id": a.id, "applicant_name": a.applicant.full_name,
            "status": a.status, "total": a.merit.total, "rank": a.merit.rank,
            "quota_tag": a.merit.quota_tag, "adjusted": a.merit.adjusted,
            "breakdown": a.merit.breakdown,
        }
        for a in apps
    ]


@router.post("/merit/{app_id}/adjust")
def adjust_merit(app_id: int, payload: MeritAdjustIn, db: Session = Depends(get_db),
                 user: User = Depends(require_roles(Roles.COMMITTEE, Roles.ADMIN))):
    """Committee override of a merit entry — mandatory justification, always logged."""
    app = db.get(Application, app_id)
    if not app or not app.merit:
        raise HTTPException(404, "Merit entry not found")
    before = {"rank": app.merit.rank, "selected_status": app.status}
    if payload.rank is not None:
        app.merit.rank = payload.rank
    if payload.selected is not None:
        app.status = AppStatus.SELECTED if payload.selected else AppStatus.SCREENED
    app.merit.adjusted = True
    app.merit.adjustment_note = payload.justification
    audit.record(db, actor=user, entity="merit_score", entity_id=app.merit.id,
                 action="committee_adjust", before=before,
                 after={"rank": app.merit.rank, "status": app.status,
                        "justification": payload.justification}, commit=False)
    db.commit()
    return {"application_id": app.id, "rank": app.merit.rank, "status": app.status,
            "adjusted": True}


@router.post("/schemes/{scheme_id}/publish")
def publish_results(scheme_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_roles(Roles.COMMITTEE, Roles.ADMIN))):
    """Publish results: mark selected within slots, notify all, create fellowships."""
    from app.models import Scheme
    scheme = db.get(Scheme, scheme_id)
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    apps = (db.query(Application)
            .filter(Application.scheme_id == scheme_id)
            .join(Application.merit).all())
    apps = [a for a in apps if a.merit and a.merit.rank]
    apps.sort(key=lambda a: a.merit.rank)

    selected_count = 0
    for a in apps:
        within_slots = a.merit.rank <= scheme.slots if scheme.slots else True
        # Respect committee manual selections too.
        make_selected = within_slots or a.status == AppStatus.SELECTED
        new_status = AppStatus.SELECTED if make_selected else AppStatus.REJECTED
        if a.status != new_status:
            db.add(StatusEvent(application_id=a.id, from_status=a.status,
                               to_status=new_status, actor_id=user.id,
                               note="Result published."))
            a.status = new_status
        if make_selected:
            selected_count += 1
            if not a.fellowship:
                a.fellowship = Fellowship(application_id=a.id, stage="JRF",
                                          status="AWAITING_JOINING")
                db.add(a.fellowship)
        notify(db, user_id=a.user_id,
               title=("Congratulations — you are selected!" if make_selected
                      else "Selection result published"),
               message=("You have been selected. A provisional selection letter is "
                        "available in your portal." if make_selected else
                        "The selection list has been published. Unfortunately you were "
                        "not selected this cycle."),
               channels=("in_app", "email"), commit=False)
    audit.record(db, actor=user, entity="scheme", entity_id=scheme_id,
                 action="publish_results", after={"selected": selected_count}, commit=False)
    db.commit()
    return {"scheme_id": scheme_id, "selected": selected_count, "total_ranked": len(apps)}


@router.get("/selection/{app_id}/letter.pdf")
def selection_letter(app_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_roles(
                         Roles.APPLICANT, Roles.COMMITTEE, Roles.ADMIN))):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if user.role.name == Roles.APPLICANT and app.user_id != user.id:
        raise HTTPException(403, "Not your application")
    if app.status not in (AppStatus.SELECTED, AppStatus.FELLOWSHIP_ACTIVE):
        raise HTTPException(409, "Selection letter is available only for selected applicants.")
    pdf = pdfgen.selection_letter(
        applicant_name=app.applicant.full_name, scheme_name=app.scheme.name,
        scheme_code=app.scheme.code, academic_year=app.scheme.academic_year,
        rank=app.merit.rank if app.merit else None,
        reference_no=f"MoTA/{app.scheme.code}/{app.scheme.academic_year}/{app.id:05d}",
    )
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="selection_{app.id}.pdf"'})
