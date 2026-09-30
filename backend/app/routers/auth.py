from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Device, OtpCode, User
from ..schemas import GuestCreate, GuestOut, LinkDevice, OtpRequest, OtpVerify
from ..security import decode_subject, hash_value, token_for_device, token_for_user, verify_value
from ..services.emailer import send_email
from ..services.referrals import attach_referral_on_install, ensure_referral_code, link_invited_user
from ..services.time_utils import as_utc
from ..config import settings

router = APIRouter(prefix="/v1", tags=["auth"])


@router.post("/guest", response_model=GuestOut)
def create_guest(payload: GuestCreate, db: Session = Depends(get_db)):
    install_hash = sha256(payload.install_id.encode()).hexdigest()
    device = db.scalar(select(Device).where(Device.install_id_hash == install_hash))
    created = False
    if not device:
        device = Device(install_id_hash=install_hash)
        db.add(device)
        db.commit()
        db.refresh(device)
        created = True
    else:
        device.last_seen_at = datetime.now(timezone.utc)
        db.commit()
    if created and payload.referral_code:
        attach_referral_on_install(db, device, payload.referral_code)
    return GuestOut(device_id=device.id, device_token=token_for_device(device.id))


@router.post("/auth/request-otp")
def request_otp(payload: OtpRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    since = datetime.now(timezone.utc) - timedelta(minutes=10)
    recent = int(db.scalar(select(func.count(OtpCode.id)).where(OtpCode.email == email, OtpCode.created_at >= since)) or 0)
    if recent >= 4:
        raise HTTPException(429, "too_many_otp_requests")
    code = f"{secrets.randbelow(1_000_000):06d}"
    row = OtpCode(
        email=email,
        code_hash=hash_value(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(row)
    db.commit()
    sent = send_email(email, "کد ورود Velo", f"کد ورود شما به Velo: {code}\nاین کد ۱۰ دقیقه معتبر است.")
    if not sent and settings.environment != "development":
        raise HTTPException(503, "email_unavailable")
    out = {"sent": sent or settings.environment == "development"}
    if settings.environment == "development":
        out["dev_code"] = code
    return out


@router.post("/auth/verify-otp")
def verify_otp(payload: OtpVerify, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower()
    row = db.scalar(
        select(OtpCode)
        .where(OtpCode.email == email, OtpCode.used == False)  # noqa: E712
        .order_by(OtpCode.id.desc())
    )
    if not row or as_utc(row.expires_at) < datetime.now(timezone.utc) or not verify_value(payload.code, row.code_hash):
        raise HTTPException(400, "invalid_code")
    row.used = True
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email)
        db.add(user)
        db.flush()
    db.commit()
    ensure_referral_code(db, user)
    access_token = token_for_user(user.id)
    response.set_cookie(
        key="velo_web_session",
        value=access_token,
        max_age=30 * 86400,
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
        path="/",
    )
    return {
        "access_token": access_token,
        "user_id": user.id,
        "email": user.email,
        "referral_code": user.referral_code,
    }


@router.post("/auth/link-device")
def link_device(payload: LinkDevice, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        kind, device_id = decode_subject(payload.device_token)
    except ValueError:
        raise HTTPException(400, "invalid_device_token")
    if kind != "device":
        raise HTTPException(400, "invalid_device_token")
    device = db.get(Device, device_id)
    if not device or device.disabled:
        raise HTTPException(404, "device_not_found")
    device.user_id = user.id
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    link_invited_user(db, device, user)
    return {"linked": True, "device_id": device.id, "user_id": user.id}


@router.post("/auth/unlink-device")
def unlink_device(payload: LinkDevice, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        kind, device_id = decode_subject(payload.device_token)
    except ValueError:
        raise HTTPException(400, "invalid_device_token")
    if kind != "device":
        raise HTTPException(400, "invalid_device_token")
    device = db.get(Device, device_id)
    if not device or device.user_id != user.id:
        raise HTTPException(404, "device_not_linked")
    from ..services.vpn import close_active_for_device
    close_active_for_device(db, device.id, "account_logout")
    device.user_id = None
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return {"unlinked": True, "device_id": device.id}


@router.get("/auth/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_referral_code(db, user)
    return {"id": user.id, "email": user.email, "referral_code": user.referral_code}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key="velo_web_session",
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
        path="/",
    )
    return {"logged_out": True}
