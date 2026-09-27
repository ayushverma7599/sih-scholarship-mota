"""Cross-verification: compare OCR-extracted values against the applicant's form.

Produces explainable flags (type, severity, reason, confidence). AI only assists —
these flags are surfaced to a human officer who can verify or override each one.
"""
from __future__ import annotations

import re
from datetime import date, datetime


def _norm_name(s: str) -> str:
    return re.sub(r"[^a-z ]", "", (s or "").lower()).strip()


def _name_similarity(a: str, b: str) -> float:
    """Token-overlap similarity (0..1) — order-independent, tolerant of initials."""
    ta, tb = set(_norm_name(a).split()), set(_norm_name(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _to_int(s) -> int | None:
    try:
        return int(re.sub(r"[^\d]", "", str(s)))
    except (TypeError, ValueError):
        return None


def _parse_date(s: str) -> date | None:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def cross_verify(
    *,
    extracted: dict[str, dict],
    form_data: dict,
    income_limit: float | None = None,
) -> list[dict]:
    """Return a list of flag dicts. Empty list == nothing to worry about.

    extracted: {field: {"value","confidence"}} from the extractor
    form_data: the applicant's typed values
    """
    flags: list[dict] = []

    def val(field):
        e = extracted.get(field) or {}
        return e.get("value", ""), e.get("confidence", 0.0)

    # --- Name mismatch (form vs document) ---
    doc_name, conf = val("name")
    form_name = form_data.get("full_name") or form_data.get("name") or ""
    if doc_name and form_name:
        sim = _name_similarity(doc_name, form_name)
        if sim < 0.5:
            flags.append({
                "type": "name_mismatch",
                "severity": "high",
                "confidence": round(1 - sim, 2),
                "reason": (
                    f"Name on document ('{doc_name}') does not match the name in the "
                    f"form ('{form_name}'). Overlap {int(sim*100)}%."
                ),
            })

    # --- Income above the configured limit ---
    doc_income, _ = val("income_amount")
    income = _to_int(doc_income) or _to_int(form_data.get("family_income"))
    if income is not None and income_limit is not None and income > income_limit:
        flags.append({
            "type": "income_exceeded",
            "severity": "high",
            "confidence": 0.9,
            "reason": (
                f"Detected annual family income ₹{income:,} exceeds the scheme limit "
                f"of ₹{int(income_limit):,}."
            ),
        })

    # --- Expired / invalid certificate ---
    valid_upto, _ = val("valid_upto")
    d = _parse_date(valid_upto)
    if d and d < date.today():
        flags.append({
            "type": "expired_certificate",
            "severity": "medium",
            "confidence": 0.85,
            "reason": f"Certificate validity expired on {d.isoformat()}.",
        })

    # --- Low-confidence extraction -> needs manual read ---
    weak = [f for f, e in extracted.items()
            if (e or {}).get("confidence", 0) < 0.4 and f != "aadhaar"]
    if weak:
        flags.append({
            "type": "low_readability",
            "severity": "low",
            "confidence": 0.6,
            "reason": (
                "Some fields could not be read automatically and need manual "
                f"verification: {', '.join(weak)}."
            ),
        })

    return flags
