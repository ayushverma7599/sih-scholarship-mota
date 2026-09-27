"""Explainable risk / priority score to help officers triage.

Score is a transparent sum of active (non-overridden) flag weights, capped at 100.
The output always includes the WHY (contributing factors), never a black box.
"""
from __future__ import annotations

_SEVERITY_WEIGHT = {"high": 40, "medium": 20, "low": 8}
_TYPE_BONUS = {
    "duplicate_aadhaar": 15,
    "duplicate_document": 12,
    "income_exceeded": 10,
    "name_mismatch": 8,
    "wrong_document": 8,
    "expired_certificate": 5,
}


def compute_risk(flags: list) -> dict:
    """flags: iterable of objects/dicts with .type, .severity, .overridden.

    Returns {"score": 0..100, "level": str, "factors": [str, ...]}.
    """
    score = 0.0
    factors: list[str] = []
    for f in flags:
        ftype = _get(f, "type")
        severity = _get(f, "severity", "medium")
        overridden = _get(f, "overridden", False)
        if overridden:
            continue
        pts = _SEVERITY_WEIGHT.get(severity, 15) + _TYPE_BONUS.get(ftype, 0)
        score += pts
        factors.append(f"+{pts}: {ftype} ({severity})")

    score = min(100.0, round(score, 1))
    level = "high" if score >= 60 else "medium" if score >= 25 else "low"
    if not factors:
        factors = ["No active flags — clean application."]
    return {"score": score, "level": level, "factors": factors}


def _get(obj, attr, default=None):
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)
