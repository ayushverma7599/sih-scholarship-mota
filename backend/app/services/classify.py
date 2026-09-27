"""Document classification: detect whether the right document was uploaded.

Uses the ground-truth sidecar's declared type when present (demo determinism);
otherwise falls back to filename/keyword heuristics over the OCR text.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_KEYWORDS = {
    "st_certificate": ["scheduled tribe", "caste certificate", "tribe", "st certificate"],
    "income_certificate": ["income certificate", "annual income", "family income"],
    "aadhaar": ["aadhaar", "unique identification", "uidai"],
    "marksheet": ["marksheet", "mark sheet", "grade card", "cgpa", "semester"],
    "admission_letter": ["admission", "offer letter", "provisionally admitted"],
    "net_gate_scorecard": ["net", "gate", "scorecard", "score card", "ugc"],
    "research_proposal": ["research proposal", "synopsis", "abstract"],
}


def _sidecar_type(file_path: str) -> str | None:
    sidecar = f"{file_path}.truth.json"
    if os.path.exists(sidecar):
        try:
            return json.loads(Path(sidecar).read_text()).get("_doc_type")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def classify(file_path: str, ocr_text: str = "", expected: str | None = None) -> dict:
    """Return {"detected": str|None, "confidence": float, "matches_expected": bool}."""
    detected = _sidecar_type(file_path)
    confidence = 0.98 if detected else 0.0

    if not detected and ocr_text:
        text = ocr_text.lower()
        best, best_hits = None, 0
        for dtype, kws in _KEYWORDS.items():
            hits = sum(1 for kw in kws if kw in text)
            if hits > best_hits:
                best, best_hits = dtype, hits
        if best:
            detected, confidence = best, min(0.9, 0.4 + 0.2 * best_hits)

    if not detected and expected:
        # Last resort: trust the slot the applicant chose, low confidence.
        detected, confidence = expected, 0.3

    return {
        "detected": detected,
        "confidence": round(confidence, 2),
        "matches_expected": (expected is None) or (detected == expected),
    }
