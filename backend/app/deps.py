from __future__ import annotations

import secrets

from fastapi import Cookie, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Device, User
from .security import decode_subject, verify_admin_session

bearer = HTTPBearer(auto_error=False)


def _subject(credentials: HTTPAuthorizationCredentials | None) -> tuple[str, int]:
    if not credentials:
        raise HTTPException(401, "missing_token")
    try:
        return decode_subject(credentials.credentials)
    except ValueError:
        raise HTTPException(401, "invalid_token")


def current_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Device:
    kind, ident = _subject(credentials)
    if kind == "device":
        device = db.get(Device, ident)
    else:
        user = db.get(User, ident)
        if not user:
            raise HTTPException(401, "invalid_user")
        raise HTTPException(400, "device_token_required")
    if not device or device.disabled:
        raise HTTPException(401, "invalid_device")
    return device


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    kind, ident = _subject(credentials)
    if kind != "user":
        raise HTTPException(401, "user_token_required")
    user = db.get(User, ident)
    if not user or not user.is_active:
        raise HTTPException(401, "invalid_user")
    return user


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        kind, ident = decode_subject(credentials.credentials)
    except ValueError:
        return None
    if kind != "user":
        return None
    user = db.get(User, ident)
    return user if user and user.is_active else None


def require_admin(
    x_admin_key: str | None = Header(None),
    velo_admin_session: str | None = Cookie(default=None),
) -> None:
    if velo_admin_session and verify_admin_session(velo_admin_session):
        return
    if x_admin_key and secrets.compare_digest(x_admin_key, settings.admin_api_key):
        return
    raise HTTPException(401, "invalid_admin_credentials")
