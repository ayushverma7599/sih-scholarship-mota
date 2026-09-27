"""Security primitives: password hashing, JWT, PII field encryption, masking."""
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import settings

# --- Password hashing (bcrypt directly to avoid passlib/bcrypt version drama) ---


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]  # bcrypt hard limit
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT ---


def create_access_token(subject: str, role: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


# --- PII encryption at rest (Fernet) ---

_fernet = Fernet(settings.FERNET_KEY.encode("utf-8"))


def encrypt_pii(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_pii(token: str | None) -> str | None:
    if token is None or token == "":
        return token
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def pii_fingerprint(value: str | None) -> str | None:
    """Deterministic, non-reversible fingerprint for equality matching (e.g. duplicate
    Aadhaar/bank detection) without decrypting stored ciphertext. Not for display."""
    if not value:
        return None
    import hashlib
    normalized = str(value).replace(" ", "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def mask_sensitive(value: str | None, visible: int = 4) -> str | None:
    """Mask all but the last `visible` characters (e.g. Aadhaar, bank a/c)."""
    if not value:
        return value
    digits = value.replace(" ", "")
    if len(digits) <= visible:
        return "X" * len(digits)
    return "X" * (len(digits) - visible) + digits[-visible:]
