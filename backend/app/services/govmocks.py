"""MOCK government verification APIs (DigiLocker / e-District / DBT-PFMS).

These are clearly-labelled stubs — no real network calls. Every response carries
`"mock": true` so the UI can show a "MOCK" badge and nobody mistakes it for a live
integration. Swap these for real adapters behind the same signatures later.
"""
from __future__ import annotations

import hashlib


def _deterministic_ok(seed: str, fail_ratio: float = 0.12) -> bool:
    """Stable pseudo-random pass/fail so demos are reproducible."""
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return (h % 100) >= int(fail_ratio * 100)


def verify_st_certificate(certificate_number: str, name: str) -> dict:
    ok = _deterministic_ok(f"st:{certificate_number}")
    return {
        "mock": True,
        "source": "DigiLocker (MOCK)",
        "verified": ok,
        "certificate_number": certificate_number,
        "holder_name": name,
        "message": (
            "Scheduled Tribe certificate verified against issuing authority records."
            if ok else
            "Certificate could not be verified — record not found at issuing authority."
        ),
    }


def verify_income_certificate(certificate_number: str, income: float) -> dict:
    ok = _deterministic_ok(f"income:{certificate_number}")
    return {
        "mock": True,
        "source": "e-District (MOCK)",
        "verified": ok,
        "certificate_number": certificate_number,
        "declared_income": income,
        "message": (
            "Income certificate verified with the state e-District portal."
            if ok else
            "Income certificate mismatch — please re-verify with the issuing office."
        ),
    }


def dbt_status(beneficiary_id: str) -> dict:
    """Mock DBT/PFMS disbursement status lookup."""
    return {
        "mock": True,
        "source": "DBT/PFMS (MOCK)",
        "beneficiary_id": beneficiary_id,
        "status": "READY_FOR_DISBURSEMENT",
        "message": "Beneficiary account validated (mock). No real payment is made.",
    }
