from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_device
from ..models import Device, VpnServer, VpnSession
from ..schemas import ServerOut, VpnConnectIn, VpnConnectOut
from ..services.subscriptions import active_subscription
from ..services.settings_store import get_json
from ..config import settings
from ..services.store import free_speed_entitlement_mbps, has_server_access
from ..services.vpn import VpnBusinessError, close_session, remaining_free_seconds, start_session
from ..services.time_utils import as_utc, utcnow

router = APIRouter(prefix="/v1/vpn", tags=["vpn"])


@router.get("/servers", response_model=list[ServerOut])
def servers(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    premium = bool(device.user_id and active_subscription(db, device.user_id))
    rows = db.scalars(
        select(VpnServer).where(VpnServer.is_active == True).order_by(VpnServer.is_default.desc(), VpnServer.id.asc())  # noqa: E712
    ).all()
    if not premium:
        # The free UI intentionally exposes only the automatic choice.
        return []
    return [
        ServerOut(
            id=s.id,
            name=s.name,
            country_code=s.country_code,
            city=s.city,
            tier=s.tier,
            locked=(s.tier == "vip" and not has_server_access(db, device.user_id, s.country_code)),
            available=not (s.unhealthy_until and as_utc(s.unhealthy_until) > utcnow()),
        )
        for s in rows
    ]


@router.post("/connect", response_model=VpnConnectOut)
def connect(payload: VpnConnectIn, device: Device = Depends(current_device), db: Session = Depends(get_db)):
    premium = bool(device.user_id and active_subscription(db, device.user_id))
    requested_server = payload.server_id if premium else None
    try:
        session, server, remaining = start_session(
            db,
            device,
            payload.client_public_key,
            requested_server_id=requested_server,
            force_takeover=payload.force_takeover,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except VpnBusinessError as exc:
        code = str(exc)
        status = 409 if code == "premium_active_on_other_device" else 400
        raise HTTPException(status, code)
    return VpnConnectOut(
        session_id=session.id,
        premium=session.is_premium,
        client_address=f"{session.client_ip}/32",
        server_public_key=server.public_key,
        endpoint=f"{server.endpoint_host}:{server.endpoint_port}",
        dns=server.dns,
        allowed_ips=["0.0.0.0/0"],
        persistent_keepalive=25,
        expires_at=session.expires_at,
        free_remaining_seconds_before_start=remaining,
        server_id=server.id,
        server_name=server.name,
        country_code=server.country_code,
    )


@router.post("/disconnect/{session_id}")
def disconnect(session_id: int, device: Device = Depends(current_device), db: Session = Depends(get_db)):
    session = db.get(VpnSession, session_id)
    if not session or session.device_id != device.id:
        raise HTTPException(404, "session_not_found")
    close_session(db, session, "client_disconnect")
    return {"disconnected": True, "session_id": session.id}


@router.post("/heartbeat/{session_id}")
def heartbeat(session_id: int, device: Device = Depends(current_device), db: Session = Depends(get_db)):
    session = db.get(VpnSession, session_id)
    if not session or session.device_id != device.id or session.status != "active":
        raise HTTPException(404, "session_not_found")
    session.last_heartbeat_at = utcnow()
    db.commit()
    return {
        "ok": True,
        "expires_at": session.expires_at,
        "premium": session.is_premium,
        "free_remaining_seconds": None if session.is_premium else remaining_free_seconds(db, device.id),
        "reconnect_required": bool(session.reconnect_required),
        "server_id": session.server_id,
    }


@router.get("/status")
def status(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    session = db.scalar(
        select(VpnSession).where(
            VpnSession.device_id == device.id,
            VpnSession.status == "active",
        ).order_by(VpnSession.id.desc())
    )
    premium = bool(device.user_id and active_subscription(db, device.user_id))
    base_speed = int(get_json(db, "free_speed_mbps", settings.free_speed_mbps))
    boosted = free_speed_entitlement_mbps(db, device.user_id) if not premium else None
    effective_speed = None if premium else max(base_speed, int(boosted or 0))
    return {
        "connected": bool(session),
        "session_id": session.id if session else None,
        "premium": premium,
        "expires_at": session.expires_at if session else None,
        "free_remaining_seconds": None if premium else remaining_free_seconds(db, device.id),
        "effective_free_speed_mbps": effective_speed,
        "reconnect_required": bool(session.reconnect_required) if session else False,
    }
