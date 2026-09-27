"""Duplicate detection across applications.

Flags the same Aadhaar, bank account, or identical document file (by SHA-256)
appearing on more than one application. Uses deterministic PII fingerprints
(no decryption) so it stays fast even over the whole applicant pool.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import mask_sensitive, pii_fingerprint
from app.models import Application, ApplicationDocument, User


def _fp(profile: dict, field: str) -> str | None:
    """Return the stored fingerprint for a PII field, computing it on the fly for
    legacy rows that only have the encrypted value + plaintext scratch."""
    fp = profile.get(f"{field}_fp")
    if fp:
        return fp
    from app.core.security import decrypt_pii
    enc = profile.get(f"{field}_enc")
    if enc:
        return pii_fingerprint(decrypt_pii(enc))
    return pii_fingerprint(profile.get(field))


def find_duplicates(db: Session, application: Application) -> list[dict]:
    flags: list[dict] = []
    profile = application.applicant.profile or {}

    my_aadhaar_fp = _fp(profile, "aadhaar")
    my_bank_fp = _fp(profile, "bank_account")

    if my_aadhaar_fp or my_bank_fp:
        # One lightweight query: (application_id, user_id, profile) — no ORM hydration.
        rows = (db.query(Application.id, User.profile)
                .join(User, Application.user_id == User.id)
                .filter(Application.id != application.id)
                .all())
        for other_id, other_profile in rows:
            other_profile = other_profile or {}
            if my_aadhaar_fp and _fp(other_profile, "aadhaar") == my_aadhaar_fp:
                flags.append({
                    "type": "duplicate_aadhaar", "severity": "high", "confidence": 0.98,
                    "reason": (f"Aadhaar {mask_sensitive(_plain(profile, 'aadhaar'))} is also "
                               f"used by application #{other_id}."),
                })
                break
        for other_id, other_profile in rows:
            other_profile = other_profile or {}
            if my_bank_fp and _fp(other_profile, "bank_account") == my_bank_fp:
                flags.append({
                    "type": "duplicate_bank_account", "severity": "medium", "confidence": 0.9,
                    "reason": (f"Bank account {mask_sensitive(_plain(profile, 'bank_account'))} "
                               f"is shared with application #{other_id}."),
                })
                break

    # Identical document file uploaded on another application (indexed SHA-256).
    my_hashes = {d.sha256 for d in application.documents if d.sha256}
    if my_hashes:
        dup = (db.query(ApplicationDocument)
               .filter(ApplicationDocument.sha256.in_(my_hashes),
                       ApplicationDocument.application_id != application.id)
               .first())
        if dup:
            flags.append({
                "type": "duplicate_document", "severity": "high", "confidence": 0.95,
                "reason": (f"An identical document file was already uploaded on "
                           f"application #{dup.application_id}."),
            })

    return flags


def _plain(profile: dict, field: str) -> str | None:
    """Best-effort plaintext for masking only (never returned raw)."""
    from app.core.security import decrypt_pii
    if profile.get(f"{field}_enc"):
        return decrypt_pii(profile[f"{field}_enc"])
    return profile.get(f"{field}_plain") or profile.get(field)
