from __future__ import annotations

import base64
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User, VpnServer, WebVpnAccess
from .settings_store import get_json
from .subscriptions import active_subscription
from .time_utils import as_utc, utcnow
from .wireguard import WireGuardError, add_peer, allocate_client_ip, choose_servers, remove_peer


class WebVpnBusinessError(RuntimeError):
    pass


def generate_keypair() -> tuple[str, str]:
    private = X25519PrivateKey.generate()
    private_raw = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(private_raw).decode("ascii"), base64.b64encode(public_raw).decode("ascii")


def _future(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    value = as_utc(value)
    return value if value > utcnow() else None


def effective_access_until(db: Session, access: WebVpnAccess) -> tuple[datetime | None, bool]:
    candidates: list[datetime] = []
    free_until = _future(access.free_until)
    if free_until:
        candidates.append(free_until)

    sub = active_subscription(db, access.user_id)
    premium_until = _future(sub.ends_at) if sub else None
    if premium_until:
        candidates.append(premium_until)

    return (max(candidates) if candidates else None, premium_until is not None)


def _welcome_minutes(db: Session) -> int:
    raw = get_json(db, "web_welcome_minutes", settings.web_welcome_minutes)
    try:
        return max(0, min(24 * 60, int(raw)))
    except (TypeError, ValueError):
        return max(0, int(settings.web_welcome_minutes))


def _free_speed(db: Session) -> int:
    raw = get_json(db, "free_speed_mbps", settings.free_speed_mbps)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return max(1, int(settings.free_speed_mbps))


def build_wireguard_config(private_key: str, access: WebVpnAccess, server: VpnServer) -> str:
    endpoint = f"{server.endpoint_host}:{server.endpoint_port}"
    return (
        "[Interface]\n"
        f"PrivateKey = {private_key}\n"
        f"Address = {access.client_ip}/32\n"
        f"DNS = {server.dns}\n\n"
        "[Peer]\n"
        f"PublicKey = {server.public_key}\n"
        f"Endpoint = {endpoint}\n"
        "AllowedIPs = 0.0.0.0/0\n"
        "PersistentKeepalive = 25\n"
    )


def _server_payload(server: VpnServer) -> dict:
    return {
        "id": server.id,
        "name": server.name,
        "country_code": server.country_code,
        "city": server.city,
    }


def access_status(db: Session, user: User) -> dict:
    access = db.scalar(select(WebVpnAccess).where(WebVpnAccess.user_id == user.id))
    if not access:
        return {
            "provisioned": False,
            "active": False,
            "peer_enabled": False,
            "access_until": None,
            "remaining_seconds": 0,
            "premium": bool(active_subscription(db, user.id)),
            "welcome_available": True,
            "welcome_minutes": _welcome_minutes(db),
            "config_version": None,
            "server": None,
        }

    until, premium = effective_access_until(db, access)
    remaining = max(0, int((until - utcnow()).total_seconds())) if until else 0
    server = db.get(VpnServer, access.server_id)
    return {
        "provisioned": True,
        "active": bool(access.peer_enabled and until),
        "peer_enabled": bool(access.peer_enabled),
        "access_until": until,
        "remaining_seconds": remaining,
        "premium": premium,
        "welcome_available": access.welcome_granted_at is None,
        "welcome_minutes": _welcome_minutes(db),
        "config_version": access.config_version,
        "server": _server_payload(server) if server else None,
    }


def _choose_server_for_user(db: Session, user: User) -> VpnServer:
    premium = bool(active_subscription(db, user.id))
    try:
        candidates = choose_servers(db, premium=premium)
    except WireGuardError as exc:
        raise WebVpnBusinessError(str(exc)) from exc
    if not candidates:
        raise WebVpnBusinessError("no_server_capacity")
    return candidates[0]


def issue_config(db: Session, user: User, replace: bool = False) -> tuple[dict, str]:
    access = db.scalar(select(WebVpnAccess).where(WebVpnAccess.user_id == user.id))
    if access and not replace:
        raise WebVpnBusinessError("configuration_already_issued")

    now = utcnow()
    is_new = access is None
    old_key: str | None = None
    old_enabled = False
    old_server: VpnServer | None = None
    old_ip: str | None = None
    private_key, public_key = generate_keypair()

    if is_new:
        server = _choose_server_for_user(db, user)
        client_ip = allocate_client_ip(db, server)
        access = WebVpnAccess(
            user_id=user.id,
            server_id=server.id,
            client_public_key=public_key,
            client_ip=client_ip,
            peer_enabled=False,
            config_version=1,
        )
        minutes = _welcome_minutes(db)
        access.welcome_granted_at = now
        access.free_until = now + timedelta(minutes=minutes) if minutes > 0 else now
        db.add(access)
        db.flush()
    else:
        assert access is not None
        server = db.get(VpnServer, access.server_id)
        if not server or not server.is_active:
            server = _choose_server_for_user(db, user)
            access.server_id = server.id
            access.client_ip = allocate_client_ip(db, server)
        old_key = access.client_public_key
        old_enabled = bool(access.peer_enabled)
        old_server = server
        old_ip = access.client_ip
        access.config_version = int(access.config_version or 0) + 1

    until, premium = effective_access_until(db, access)
    entitled = until is not None

    if old_key and old_enabled and old_server and old_ip:
        remove_peer(old_server, old_key, old_ip)

    try:
        if entitled:
            add_peer(server, public_key, access.client_ip, None if premium else _free_speed(db))
    except Exception:
        if old_key and old_enabled and old_server and old_ip:
            try:
                add_peer(old_server, old_key, old_ip, None if premium else _free_speed(db))
            except Exception:
                pass
        db.rollback()
        raise

    access.client_public_key = public_key
    access.peer_enabled = entitled
    access.last_error = None
    try:
        db.commit()
    except Exception:
        if entitled:
            remove_peer(server, public_key, access.client_ip)
        db.rollback()
        raise
    db.refresh(access)

    config = build_wireguard_config(private_key, access, server)
    return access_status(db, user), config


def sync_access(db: Session, access: WebVpnAccess) -> bool:
    server = db.get(VpnServer, access.server_id)
    if not server:
        access.peer_enabled = False
        access.last_error = "server_not_found"
        db.commit()
        return False

    until, premium = effective_access_until(db, access)
    should_enable = until is not None and server.is_active

    if should_enable and not access.peer_enabled:
        try:
            add_peer(server, access.client_public_key, access.client_ip, None if premium else _free_speed(db))
            access.peer_enabled = True
            access.last_error = None
        except WireGuardError as exc:
            access.last_error = str(exc)[:1000]
    elif not should_enable and access.peer_enabled:
        remove_peer(server, access.client_public_key, access.client_ip)
        access.peer_enabled = False
        access.last_error = None

    db.commit()
    return bool(access.peer_enabled)


def sync_all_accesses(db: Session) -> dict:
    rows = db.scalars(select(WebVpnAccess)).all()
    enabled = 0
    disabled = 0
    failures = 0
    for access in rows:
        try:
            if sync_access(db, access):
                enabled += 1
            else:
                disabled += 1
            if access.last_error:
                failures += 1
        except Exception:
            db.rollback()
            failures += 1
    return {"checked": len(rows), "enabled": enabled, "disabled": disabled, "failures": failures}


def config_filename(status: dict) -> str:
    server = status.get("server") or {}
    country = str(server.get("country_code") or "VPN").upper()
    version = int(status.get("config_version") or 1)
    return f"velo-{country.lower()}-v{version}.conf"
