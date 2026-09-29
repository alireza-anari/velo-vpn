from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from .config import settings


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64d(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def hash_value(value: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, 120_000)
    return f"{_b64e(salt)}.{_b64e(digest)}"


def verify_value(value: str, encoded: str) -> bool:
    try:
        salt_text, digest_text = encoded.split(".", 1)
        salt = _b64d(salt_text)
        expected = _b64d(digest_text)
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, 120_000)
    return hmac.compare_digest(actual, expected)


def _token(subject: str, days: int) -> str:
    payload = {
        "sub": subject,
        "iat": int(time.time()),
        "exp": int(time.time()) + days * 86400,
    }
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


def token_for_user(user_id: int) -> str:
    return _token(f"user:{user_id}", 30)


def token_for_device(device_id: int) -> str:
    return _token(f"device:{device_id}", 180)


def decode_subject(token: str) -> tuple[str, int]:
    try:
        body, sig_text = token.split(".", 1)
        expected = hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest()
        supplied = _b64d(sig_text)
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("bad_signature")
        payload = json.loads(_b64d(body))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        subject = str(payload["sub"])
        kind, raw_id = subject.split(":", 1)
        if kind not in {"user", "device"}:
            raise ValueError("invalid subject kind")
        return kind, int(raw_id)
    except Exception as exc:
        raise ValueError("invalid_token") from exc


def admin_session_token(hours: int | None = None) -> str:
    """Create a short-lived signed browser session for the admin panel."""
    hours = int(hours or settings.admin_session_hours)
    payload = {
        "sub": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + max(1, hours) * 3600,
    }
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(settings.jwt_secret.encode(), ("admin." + body).encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


def verify_admin_session(token: str) -> bool:
    try:
        body, sig_text = token.split(".", 1)
        expected = hmac.new(settings.jwt_secret.encode(), ("admin." + body).encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig_text)):
            return False
        payload = json.loads(_b64d(body))
        return payload.get("sub") == "admin" and int(payload.get("exp", 0)) >= int(time.time())
    except Exception:
        return False
