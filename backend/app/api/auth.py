"""Authentication: register, mock OTP (printed to console), login, current user."""
from __future__ import annotations

import logging
import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Role, Roles, User
from app.schemas import (
    LoginIn, OTPRequestIn, OTPVerifyIn, ProfileUpdateIn, RegisterIn, TokenOut,
)
from app.services.serialize import user_public

router = APIRouter()
logger = logging.getLogger("auth")

# In-memory OTP store (mock). Console-printed; fine for a prototype.
_OTP_STORE: dict[str, str] = {}


def _get_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        role = Role(name=name)
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if payload.role not in Roles.ALL:
        raise HTTPException(400, f"Invalid role. One of {Roles.ALL}")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "Email already registered")

    role = _get_role(db, payload.role)
    user = User(
        email=payload.email,
        mobile=payload.mobile,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, role.name)
    return TokenOut(access_token=token, role=role.name, user_id=user.id,
                    full_name=user.full_name)


@router.post("/request-otp")
def request_otp(payload: OTPRequestIn):
    """Generate a mock OTP and print it to the server console."""
    otp = f"{random.randint(100000, 999999)}"
    _OTP_STORE[payload.identifier] = otp
    logger.warning("=== MOCK OTP for %s : %s ===", payload.identifier, otp)
    print(f"\n*** MOCK OTP for {payload.identifier}: {otp} ***\n")
    return {"sent": True, "channel": "console", "hint": "Check the backend console for the OTP."}


@router.post("/verify-otp")
def verify_otp(payload: OTPVerifyIn, db: Session = Depends(get_db)):
    expected = _OTP_STORE.get(payload.identifier)
    if not expected or expected != payload.otp:
        raise HTTPException(400, "Invalid or expired OTP")
    _OTP_STORE.pop(payload.identifier, None)
    user = (
        db.query(User)
        .filter((User.email == payload.identifier) | (User.mobile == payload.identifier))
        .first()
    )
    if not user:
        raise HTTPException(404, "No account for this identifier — please register first.")
    token = create_access_token(user.id, user.role.name)
    return TokenOut(access_token=token, role=user.role.name, user_id=user.id,
                    full_name=user.full_name)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account is inactive")
    token = create_access_token(user.id, user.role.name)
    return TokenOut(access_token=token, role=user.role.name, user_id=user.id,
                    full_name=user.full_name)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_public(user)


@router.put("/me")
def update_me(
    payload: ProfileUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.core.security import encrypt_pii, pii_fingerprint

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.mobile is not None:
        user.mobile = payload.mobile
    if payload.profile:
        profile = dict(user.profile or {})
        incoming = dict(payload.profile)
        # Encrypt sensitive fields at rest; keep a fingerprint for duplicate matching.
        if "aadhaar" in incoming:
            val = str(incoming.pop("aadhaar"))
            profile["aadhaar_enc"] = encrypt_pii(val)
            profile["aadhaar_fp"] = pii_fingerprint(val)
        if "bank_account" in incoming:
            val = str(incoming.pop("bank_account"))
            profile["bank_account_enc"] = encrypt_pii(val)
            profile["bank_account_fp"] = pii_fingerprint(val)
        profile.update(incoming)
        user.profile = profile
    db.commit()
    db.refresh(user)
    return user_public(user)
