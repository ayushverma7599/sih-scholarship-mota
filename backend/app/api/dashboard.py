"""Ministry Admin dashboards & analytics: KPIs, charts, officer performance, export."""
from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from datetime import timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_roles
from app.models import (
    AppStatus, Application, AuditLog, Deficiency, Roles, Scheme, StatusEvent, User,
)

router = APIRouter()

_SELECTED = (AppStatus.SELECTED, AppStatus.FELLOWSHIP_ACTIVE)


@router.get("/kpis")
def kpis(db: Session = Depends(get_db),
         admin: User = Depends(require_roles(Roles.ADMIN, Roles.COMMITTEE))):
    apps = db.query(Application).filter(Application.status != AppStatus.DRAFT).all()
    total = len(apps)
    auto_verified = sum(1 for a in apps if a.status not in
                        (AppStatus.SUBMITTED,) and a.risk_score < 25)
    pending = sum(1 for a in apps if a.status in
                  (AppStatus.SUBMITTED, AppStatus.AUTO_VERIFIED,
                   AppStatus.UNDER_SCRUTINY, AppStatus.RESUBMITTED))
    with_def = sum(1 for a in apps if any(d.status == "OPEN" for d in a.deficiencies))
    selected = sum(1 for a in apps if a.status in _SELECTED)

    # Average processing time (submit -> screened/selected) in hours.
    durations = []
    for a in apps:
        ev = {e.to_status: e.at for e in a.events}
        start = ev.get(AppStatus.SUBMITTED) or a.submitted_at
        end = ev.get(AppStatus.SCREENED) or ev.get(AppStatus.SELECTED)
        if start and end:
            s = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
            e = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
            durations.append((e - s).total_seconds() / 3600)
    avg_proc = round(sum(durations) / len(durations), 1) if durations else 0.0

    funds = selected * 75000 * 4  # mock: 4 quarterly disbursements/selectee

    return {
        "total_applications": total,
        "auto_verified_pct": round(100 * auto_verified / total, 1) if total else 0,
        "pending_scrutiny": pending,
        "avg_processing_hours": avg_proc,
        "deficiency_rate_pct": round(100 * with_def / total, 1) if total else 0,
        "selected": selected,
        "funds_committed": funds,
    }


@router.get("/charts")
def charts(db: Session = Depends(get_db),
           admin: User = Depends(require_roles(Roles.ADMIN, Roles.COMMITTEE))):
    apps = db.query(Application).filter(Application.status != AppStatus.DRAFT).all()

    by_scheme = Counter()
    by_state = Counter()
    by_gender = Counter()
    by_tribe = Counter()
    by_course = Counter()
    for a in apps:
        p = a.applicant.profile or {}
        by_scheme[a.scheme.code] += 1
        by_state[p.get("state", "Unknown")] += 1
        by_gender[str(p.get("gender", "Unknown")).title()] += 1
        by_tribe[p.get("tribe", "Unknown")] += 1
        by_course[p.get("course_level", p.get("course", "Unknown"))] += 1

    # Funnel
    funnel = {
        "Applied": len(apps),
        "Auto-Verified": sum(1 for a in apps if a.status not in (AppStatus.SUBMITTED,)),
        "Screened": sum(1 for a in apps if a.status in
                        (AppStatus.SCREENED,) + _SELECTED),
        "Selected": sum(1 for a in apps if a.status in _SELECTED),
    }

    # Top deficiency reasons
    def_reasons = Counter()
    for d in db.query(Deficiency).all():
        key = (d.doc_type or "general").replace("_", " ").title()
        def_reasons[key] += 1

    def _fmt(counter):
        return [{"label": k, "value": v} for k, v in counter.most_common()]

    return {
        "by_scheme": _fmt(by_scheme),
        "by_state": _fmt(by_state),
        "by_gender": _fmt(by_gender),
        "by_tribe": _fmt(by_tribe),
        "by_course": _fmt(by_course),
        "funnel": [{"label": k, "value": v} for k, v in funnel.items()],
        "top_deficiencies": _fmt(def_reasons)[:8],
    }


@router.get("/officer-performance")
def officer_performance(db: Session = Depends(get_db),
                        admin: User = Depends(require_roles(Roles.ADMIN))):
    officers = db.query(User).join(User.role).filter(
        User.role.has(name=Roles.SCRUTINY)).all()
    perf = []
    for o in officers:
        actions = (db.query(StatusEvent)
                   .filter(StatusEvent.actor_id == o.id).count())
        verified = (db.query(StatusEvent)
                    .filter(StatusEvent.actor_id == o.id,
                            StatusEvent.to_status == AppStatus.SCREENED).count())
        perf.append({"officer": o.full_name or o.email, "actions": actions,
                     "verified": verified})
    perf.sort(key=lambda x: -x["verified"])
    # Backlog by scheme
    backlog = Counter()
    for a in db.query(Application).filter(Application.status.in_(
            [AppStatus.SUBMITTED, AppStatus.AUTO_VERIFIED,
             AppStatus.UNDER_SCRUTINY, AppStatus.RESUBMITTED])).all():
        backlog[a.scheme.code] += 1
    return {"officers": perf,
            "backlog": [{"label": k, "value": v} for k, v in backlog.items()]}


@router.get("/reports/export")
def export_report(format: str = "csv", db: Session = Depends(get_db),
                  admin: User = Depends(require_roles(Roles.ADMIN, Roles.COMMITTEE))):
    apps = db.query(Application).filter(Application.status != AppStatus.DRAFT).all()
    rows = [
        {
            "application_id": a.id, "applicant": a.applicant.full_name,
            "scheme": a.scheme.code, "state": (a.applicant.profile or {}).get("state", ""),
            "status": a.status, "risk_score": a.risk_score,
            "rank": a.merit.rank if a.merit else "",
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else "",
        }
        for a in apps
    ]

    if format == "pdf":
        from app.services import pdfgen  # reuse reportlab
        import io as _io
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        buf = _io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        c.setFont("Helvetica-Bold", 13)
        c.drawString(20 * mm, h - 20 * mm, "MoTA Scholarship — Applications Report")
        c.setFont("Helvetica", 8)
        y = h - 30 * mm
        c.drawString(20 * mm, y, "ID   Applicant                Scheme  Status            Risk  Rank")
        y -= 6 * mm
        for r in rows[:60]:
            c.drawString(20 * mm, y,
                         f"{r['application_id']:<4} {r['applicant'][:22]:<22} "
                         f"{r['scheme']:<6} {r['status'][:16]:<16} {r['risk_score']:<5} {r['rank']}")
            y -= 5 * mm
            if y < 20 * mm:
                c.showPage(); y = h - 20 * mm
        c.showPage(); c.save()
        return Response(content=buf.getvalue(), media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="report.pdf"'})

    # CSV default
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()) if rows else
                            ["application_id", "applicant", "scheme", "state", "status",
                             "risk_score", "rank", "submitted_at"])
    writer.writeheader()
    writer.writerows(rows)
    return Response(content=out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="report.csv"'})
