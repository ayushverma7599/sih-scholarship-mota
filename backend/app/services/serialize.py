"""Serialization helpers that enforce PII masking on the way out.

Aadhaar and bank account numbers are stored encrypted (…_enc) and are NEVER
returned in the clear — only masked for display.
"""
from __future__ import annotations

from app.core.security import decrypt_pii, mask_sensitive
from app.models import Application, Scheme, User, AppStatus


def public_profile(profile: dict | None) -> dict:
    """Return a copy of the profile with sensitive fields masked / stripped."""
    p = dict(profile or {})
    # Never expose seed-time plaintext scratch fields.
    p.pop("aadhaar_plain", None)
    # Aadhaar
    aadhaar = None
    if p.get("aadhaar_enc"):
        aadhaar = decrypt_pii(p.pop("aadhaar_enc"))
    elif p.get("aadhaar"):
        aadhaar = p.pop("aadhaar")
    if aadhaar:
        p["aadhaar_masked"] = mask_sensitive(aadhaar)
    # Bank account
    bank = None
    if p.get("bank_account_enc"):
        bank = decrypt_pii(p.pop("bank_account_enc"))
    elif p.get("bank_account"):
        bank = p.pop("bank_account")
    if bank:
        p["bank_account_masked"] = mask_sensitive(bank)
    return p


def user_public(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "mobile": user.mobile,
        "full_name": user.full_name,
        "role": user.role.name if user.role else None,
        "campus_verified": user.campus_verified,
        "profile": public_profile(user.profile),
    }


def scheme_public(scheme: Scheme) -> dict:
    return {
        "id": scheme.id,
        "code": scheme.code,
        "name": scheme.name,
        "description": scheme.description,
        "academic_year": scheme.academic_year,
        "slots": scheme.slots,
        "window_open": scheme.window_open.isoformat() if scheme.window_open else None,
        "window_close": scheme.window_close.isoformat() if scheme.window_close else None,
        "is_active": scheme.is_active,
        "is_sample": scheme.is_sample,
        "rules": scheme.ruleset.rules if scheme.ruleset else {},
        "documents": [
            {
                "id": d.id, "doc_type": d.doc_type, "label": d.label,
                "mandatory": d.mandatory, "extract_fields": d.extract_fields,
                "order": d.order,
            }
            for d in sorted(scheme.documents, key=lambda x: x.order)
        ],
        "merit_criteria": {
            "weights": scheme.merit_criteria.weights if scheme.merit_criteria else {},
            "tiebreak": scheme.merit_criteria.tiebreak if scheme.merit_criteria else [],
            "quotas": scheme.merit_criteria.quotas if scheme.merit_criteria else {},
        },
    }


def timeline(application: Application) -> list[dict]:
    """Build the visual timeline from status events + the canonical pipeline."""
    events = sorted(application.events, key=lambda e: e.at)
    reached = {e.to_status: e.at for e in events}
    steps = []
    for stage in AppStatus.PIPELINE:
        # SELECTED and REJECTED share a slot conceptually; show whichever happened.
        done = stage in reached
        steps.append({
            "stage": stage,
            "reached": done,
            "at": reached[stage].isoformat() if done else None,
            "current": application.status == stage,
        })
    if application.status == AppStatus.REJECTED:
        steps.append({
            "stage": "REJECTED", "reached": True,
            "at": reached.get("REJECTED").isoformat() if reached.get("REJECTED") else None,
            "current": True,
        })
    return steps


def application_public(application: Application, *, detail: bool = False) -> dict:
    scheme = application.scheme
    data = {
        "id": application.id,
        "scheme_id": application.scheme_id,
        "scheme_code": scheme.code if scheme else None,
        "scheme_name": scheme.name if scheme else None,
        "status": application.status,
        "risk_score": application.risk_score,
        "applicant_name": application.applicant.full_name if application.applicant else "",
        "applicant_state": (application.applicant.profile or {}).get("state") if application.applicant else None,
        "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
        "updated_at": application.updated_at.isoformat() if application.updated_at else None,
        "open_deficiencies": sum(1 for d in application.deficiencies if d.status == "OPEN"),
        "active_flags": sum(1 for f in application.flags if not f.overridden),
    }
    if detail:
        data.update({
            "form_data": application.form_data,
            "draft": application.draft,
            "timeline": timeline(application),
            "documents": [
                {
                    "id": d.id, "doc_type": d.doc_type, "detected_type": d.detected_type,
                    "original_name": d.original_name, "readability": d.readability,
                    "extracted": [
                        {"key": e.key, "value": e.value, "confidence": e.confidence}
                        for e in d.extracted
                    ],
                }
                for d in application.documents
            ],
            "flags": [
                {
                    "id": f.id, "type": f.type, "severity": f.severity,
                    "reason": f.reason, "confidence": f.confidence,
                    "overridden": f.overridden, "override_note": f.override_note,
                }
                for f in application.flags
            ],
            "deficiencies": [
                {
                    "id": d.id, "doc_type": d.doc_type, "message": d.message,
                    "status": d.status, "applicant_response": d.applicant_response,
                }
                for d in application.deficiencies
            ],
            "merit": (
                {
                    "total": application.merit.total,
                    "rank": application.merit.rank,
                    "breakdown": application.merit.breakdown,
                    "quota_tag": application.merit.quota_tag,
                }
                if application.merit else None
            ),
            "applicant_profile": public_profile(application.applicant.profile) if application.applicant else {},
        })
    return data
