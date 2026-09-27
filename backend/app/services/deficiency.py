"""Auto-detect incomplete / deficient applications and phrase deficiencies plainly.

Returns a list of {doc_type, message} the applicant can act on directly. Combines:
  - missing mandatory documents (from scheme config)
  - wrong document uploaded in a slot (classification mismatch)
  - unreadable / low-confidence documents
  - high-severity cross-verification flags (name/income/expiry)
"""
from __future__ import annotations

from app.models import Application, Scheme


def detect_deficiencies(application: Application, scheme: Scheme) -> list[dict]:
    deficiencies: list[dict] = []

    uploaded_by_type: dict[str, list] = {}
    for d in application.documents:
        uploaded_by_type.setdefault(d.doc_type, []).append(d)

    # 1) Missing mandatory documents
    for sd in scheme.documents:
        if sd.mandatory and sd.doc_type not in uploaded_by_type:
            deficiencies.append({
                "doc_type": sd.doc_type,
                "message": (
                    f"'{sd.label}' is mandatory for this scheme but has not been "
                    f"uploaded. Please upload a clear copy."
                ),
            })

    # 2) Wrong document in a slot / unreadable document
    for dtype, docs in uploaded_by_type.items():
        for d in docs:
            if d.detected_type and d.detected_type != dtype:
                deficiencies.append({
                    "doc_type": dtype,
                    "message": (
                        f"The file uploaded for '{_label(scheme, dtype)}' looks like a "
                        f"'{_pretty(d.detected_type)}'. Please upload the correct document."
                    ),
                })
            elif d.readability and d.readability < 0.4:
                deficiencies.append({
                    "doc_type": dtype,
                    "message": (
                        f"The '{_label(scheme, dtype)}' could not be read clearly. "
                        f"Please re-scan and upload a sharper copy."
                    ),
                })

    # 3) High-severity cross-verification flags become deficiencies
    for flag in application.flags:
        if flag.overridden:
            continue
        if flag.type in ("name_mismatch", "income_exceeded", "expired_certificate"):
            deficiencies.append({
                "doc_type": None,
                "message": flag.reason,
            })

    return deficiencies


def _label(scheme: Scheme, doc_type: str) -> str:
    for sd in scheme.documents:
        if sd.doc_type == doc_type:
            return sd.label
    return _pretty(doc_type)


def _pretty(doc_type: str) -> str:
    return (doc_type or "document").replace("_", " ").title()
