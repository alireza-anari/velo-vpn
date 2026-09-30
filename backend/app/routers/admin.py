from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_admin
from ..models import AdminAuditLog, Device, HeartLedger, ManualPayment, Subscription, User, VpnServer, VpnSession
from ..schemas import AdminPaymentReview, AdminServerIn
from ..services.settings_store import get_json, set_json
from ..services.emailer import send_email
from ..services.subscriptions import active_subscription
from ..services.time_utils import as_utc, utcnow
from ..services.wireguard import (
    WireGuardError, check_server_health as check_node_health, reconcile_server_peers, validate_public_key,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])

PLAN_DAYS = {"15d": 15, "1m": 30, "3m": 90, "6m": 180}
DEFAULT_SUPPORT_HEARTS = {50000: 40, 100000: 90, 250000: 250, 500000: 550}


def _audit(db: Session, action: str, target_type: str | None = None, target_id: str | int | None = None, detail: str | None = None):
    db.add(AdminAuditLog(action=action, target_type=target_type, target_id=str(target_id) if target_id is not None else None, detail=detail))


@router.get("/payments")
def payments(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(ManualPayment).order_by(ManualPayment.id.desc())
    if status:
        stmt = stmt.where(ManualPayment.status == status)
    rows = db.scalars(stmt).all()
    out = []
    for p in rows:
        user = db.get(User, p.user_id)
        out.append(
            {
                "id": p.id,
                "email": user.email if user else "",
                "kind": p.kind,
                "amount_toman": p.amount_toman,
                "plan_code": p.plan_code,
                "requested_hearts": p.requested_hearts,
                "status": p.status,
                "created_at": p.created_at,
                "reviewed_at": p.reviewed_at,
                "admin_note": p.admin_note,
            }
        )
    return out


@router.get("/payments/{payment_id}/receipt")
def receipt(payment_id: int, db: Session = Depends(get_db)):
    p = db.get(ManualPayment, payment_id)
    if not p:
        raise HTTPException(404, "payment_not_found")
    path = Path(p.receipt_path)
    if not path.exists():
        raise HTTPException(404, "receipt_not_found")
    return FileResponse(path)


@router.post("/payments/{payment_id}/review")
def review_payment(payment_id: int, payload: AdminPaymentReview, db: Session = Depends(get_db)):
    p = db.get(ManualPayment, payment_id)
    if not p:
        raise HTTPException(404, "payment_not_found")
    if p.status != "pending":
        raise HTTPException(409, "already_reviewed")

    p.status = payload.status
    p.admin_note = payload.admin_note
    p.reviewed_at = utcnow()

    if payload.status == "approved":
        if p.kind == "premium":
            days = PLAN_DAYS.get(p.plan_code or "")
            if not days:
                raise HTTPException(400, "invalid_plan_code")
            current = active_subscription(db, p.user_id)
            start = utcnow()
            current_end = as_utc(current.ends_at) if current else None
            base = current_end if current_end and current_end > start else start
            db.add(
                Subscription(
                    user_id=p.user_id,
                    starts_at=start,
                    ends_at=base + timedelta(days=days),
                    source=f"manual_payment:{p.id}",
                )
            )
        elif p.kind == "support":
            if payload.hearts_to_grant is not None:
                hearts = payload.hearts_to_grant
            else:
                tiers = get_json(db, "support_heart_tiers", DEFAULT_SUPPORT_HEARTS)
                # JSON object keys may be strings.
                normalized = {int(k): int(v) for k, v in tiers.items()}
                exact = normalized.get(int(p.amount_toman))
                if exact is not None:
                    hearts = exact
                else:
                    # Conservative custom-amount fallback; configurable by admin later.
                    hearts = max(0, int(p.amount_toman // 1500))
            if hearts > 0:
                db.add(
                    HeartLedger(
                        user_id=p.user_id,
                        amount=hearts,
                        reason="support_payment",
                        reference=f"payment:{p.id}",
                    )
                )
    elif payload.status == "rejected" and p.kind == "premium" and p.requested_hearts:
        db.add(
            HeartLedger(
                user_id=p.user_id,
                amount=p.requested_hearts,
                reason="premium_discount_refund",
                reference=f"payment:{p.id}",
            )
        )
    _audit(db, "payment_review", "payment", p.id, f"status={payload.status};note={payload.admin_note or ''}")
    db.commit()
    user = db.get(User, p.user_id)
    if user:
        status_fa = "تأیید شد" if payload.status == "approved" else "رد شد"
        send_email(
            user.email,
            f"Velo: وضعیت پرداخت #{p.id}",
            f"درخواست پرداخت شما {status_fa}.\nشناسه: {p.id}\nیادداشت: {payload.admin_note or '-'}",
        )
    return {"id": p.id, "status": p.status}


@router.get("/settings")
def settings_list(db: Session = Depends(get_db)):
    from ..models import AppSetting
    rows = db.scalars(select(AppSetting).order_by(AppSetting.key.asc())).all()
    return {row.key: get_json(db, row.key, None) for row in rows}


@router.put("/settings/{key}")
def settings_put(key: str, value=Body(...), db: Session = Depends(get_db)):
    if len(key) > 100:
        raise HTTPException(400, "invalid_key")
    set_json(db, key, value)
    _audit(db, "setting_update", "setting", key, repr(value)[:1000])
    db.commit()
    return {"key": key, "value": value}


@router.get("/servers")
def servers(db: Session = Depends(get_db)):
    rows = db.scalars(select(VpnServer).order_by(VpnServer.id.asc())).all()
    out = []
    for server in rows:
        active_sessions = int(db.scalar(
            select(func.count(VpnSession.id)).where(
                VpnSession.server_id == server.id,
                VpnSession.status == "active",
            )
        ) or 0)
        usage = db.execute(
            select(
                func.coalesce(func.sum(VpnSession.rx_bytes + VpnSession.tx_bytes), 0),
                func.coalesce(func.sum(VpnSession.consumed_seconds), 0),
            ).where(VpnSession.server_id == server.id)
        ).one()
        out.append({
            "id": server.id,
            "name": server.name,
            "country_code": server.country_code,
            "city": server.city,
            "endpoint": f"{server.endpoint_host}:{server.endpoint_port}",
            "client_cidr": server.client_cidr,
            "tier": server.tier,
            "active": server.is_active,
            "default": server.is_default,
            "max_sessions": server.max_sessions,
            "active_sessions": active_sessions,
            "utilization_percent": round((active_sessions / max(1, server.max_sessions)) * 100, 1),
            "usage_bytes": int(usage[0] or 0),
            "usage_seconds": int(usage[1] or 0),
            "agent_configured": bool(server.agent_url),
            "agent_url": server.agent_url,
            "health_state": server.health_state,
            "health_failures": server.health_failures,
            "last_health_at": server.last_health_at,
            "last_health_error": server.last_health_error,
            "unhealthy_until": server.unhealthy_until,
        })
    return out


@router.post("/servers")
def add_server(payload: AdminServerIn, db: Session = Depends(get_db)):
    if payload.tier not in {"free", "premium", "vip"}:
        raise HTTPException(400, "invalid_tier")
    try:
        validate_public_key(payload.public_key)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if payload.is_default:
        for s in db.scalars(select(VpnServer).where(VpnServer.is_default == True)).all():  # noqa: E712
            s.is_default = False
    row = VpnServer(**payload.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "server_add", "server", row.id, f"{row.name}:{row.country_code}:{row.tier}")
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@router.post("/servers/{server_id}/toggle")
def toggle_server(server_id: int, db: Session = Depends(get_db)):
    row = db.get(VpnServer, server_id)
    if not row:
        raise HTTPException(404, "server_not_found")
    row.is_active = not row.is_active
    _audit(db, "server_toggle", "server", row.id, f"active={row.is_active}")
    db.commit()
    return {"id": row.id, "active": row.is_active}


@router.post("/servers/{server_id}/health")
def check_server_health(server_id: int, db: Session = Depends(get_db)):
    row = db.get(VpnServer, server_id)
    if not row:
        raise HTTPException(404, "server_not_found")
    try:
        result = check_node_health(db, row)
    except WireGuardError as exc:
        raise HTTPException(502, str(exc))
    return {
        "id": row.id,
        "ok": True,
        "health": result,
        "health_state": row.health_state,
        "last_health_at": row.last_health_at,
    }


@router.post("/servers/{server_id}/reconcile")
def reconcile_server(server_id: int, db: Session = Depends(get_db)):
    row = db.get(VpnServer, server_id)
    if not row:
        raise HTTPException(404, "server_not_found")
    try:
        result = reconcile_server_peers(db, row)
    except WireGuardError as exc:
        raise HTTPException(502, str(exc))
    _audit(db, "server_reconcile", "server", row.id, repr(result)[:1000])
    db.commit()
    return result


@router.get("/audit")
def audit_log(limit: int = 100, db: Session = Depends(get_db)):
    limit = max(1, min(int(limit), 500))
    rows = db.scalars(select(AdminAuditLog).order_by(AdminAuditLog.id.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "detail": r.detail,
            "created_at": r.created_at,
        }
        for r in rows
    ]


class AdminSubscriptionGrantIn(BaseModel):
    email: EmailStr
    days: int = Field(ge=1, le=730)
    note: str | None = Field(default=None, max_length=500)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    now = utcnow()
    return {
        "users": int(db.scalar(select(func.count(User.id))) or 0),
        "active_subscriptions": int(db.scalar(select(func.count(Subscription.id)).where(Subscription.ends_at > now)) or 0),
        "active_sessions": int(db.scalar(select(func.count(VpnSession.id)).where(VpnSession.status == "active")) or 0),
        "pending_payments": int(db.scalar(select(func.count(ManualPayment.id)).where(ManualPayment.status == "pending")) or 0),
        "active_servers": int(db.scalar(select(func.count(VpnServer.id)).where(VpnServer.is_active == True)) or 0),  # noqa: E712
        "total_servers": int(db.scalar(select(func.count(VpnServer.id))) or 0),
    }


@router.get("/users")
def users(q: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    limit = max(1, min(int(limit), 300))
    stmt = select(User).order_by(User.id.desc()).limit(limit)
    if q:
        stmt = stmt.where(User.email.ilike("%" + q.strip() + "%"))
    rows = db.scalars(stmt).all()
    out = []
    now = utcnow()
    for user in rows:
        sub = active_subscription(db, user.id)
        device_count = int(db.scalar(select(func.count(Device.id)).where(Device.user_id == user.id)) or 0)
        active_sessions = int(db.scalar(select(func.count(VpnSession.id)).where(VpnSession.user_id == user.id, VpnSession.status == "active")) or 0)
        usage = db.execute(
            select(
                func.coalesce(func.sum(VpnSession.rx_bytes + VpnSession.tx_bytes), 0),
                func.coalesce(func.sum(VpnSession.consumed_seconds), 0),
            ).where(VpnSession.user_id == user.id)
        ).one()
        out.append({
            "id": user.id,
            "email": user.email,
            "active": user.is_active,
            "subscription_active": bool(sub and as_utc(sub.ends_at) > now),
            "subscription_ends_at": sub.ends_at if sub else None,
            "devices": device_count,
            "active_sessions": active_sessions,
            "usage_bytes": int(usage[0] or 0),
            "usage_seconds": int(usage[1] or 0),
            "created_at": user.created_at,
        })
    return out


@router.post("/subscriptions/grant")
def grant_subscription(payload: AdminSubscriptionGrantIn, db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email)
        db.add(user)
        db.flush()
    current = active_subscription(db, user.id)
    start = utcnow()
    current_end = as_utc(current.ends_at) if current else None
    base = current_end if current_end and current_end > start else start
    sub = Subscription(
        user_id=user.id,
        starts_at=start,
        ends_at=base + timedelta(days=payload.days),
        source="admin_manual",
    )
    db.add(sub)
    _audit(db, "subscription_grant", "user", user.id, f"email={email};days={payload.days};note={payload.note or ''}")
    db.commit()
    db.refresh(sub)
    send_email(email, "Velo: اشتراک شما فعال شد", f"اشتراک Velo شما برای {payload.days} روز فعال شد.\nاعتبار تا: {sub.ends_at}")
    return {"user_id": user.id, "email": email, "ends_at": sub.ends_at}


@router.post("/users/{user_id}/subscription/revoke")
def revoke_subscription(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "user_not_found")
    now = utcnow()
    rows = db.scalars(select(Subscription).where(Subscription.user_id == user_id, Subscription.ends_at > now)).all()
    for row in rows:
        row.ends_at = now
    sessions = db.scalars(select(VpnSession).where(VpnSession.user_id == user_id, VpnSession.status == "active")).all()
    from ..services.vpn import close_session
    for session in sessions:
        close_session(db, session, "subscription_revoked")
    _audit(db, "subscription_revoke", "user", user.id, user.email)
    db.commit()
    return {"user_id": user.id, "revoked": len(rows)}


@router.post("/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "user_not_found")
    user.is_active = not user.is_active
    if not user.is_active:
        from ..services.vpn import close_session
        sessions = db.scalars(select(VpnSession).where(VpnSession.user_id == user_id, VpnSession.status == "active")).all()
        for session in sessions:
            close_session(db, session, "user_disabled")
    _audit(db, "user_toggle", "user", user.id, f"active={user.is_active}")
    db.commit()
    return {"user_id": user.id, "active": user.is_active}


@router.get("/sessions")
def sessions(status: str = "active", limit: int = 200, db: Session = Depends(get_db)):
    limit = max(1, min(int(limit), 500))
    stmt = select(VpnSession).order_by(VpnSession.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(VpnSession.status == status)
    rows = db.scalars(stmt).all()
    out = []
    for row in rows:
        user = db.get(User, row.user_id) if row.user_id else None
        server = db.get(VpnServer, row.server_id)
        out.append({
            "id": row.id,
            "email": user.email if user else None,
            "server": server.name if server else str(row.server_id),
            "client_ip": row.client_ip,
            "premium": row.is_premium,
            "status": row.status,
            "started_at": row.started_at,
            "last_heartbeat_at": row.last_heartbeat_at,
            "rx_bytes": row.rx_bytes,
            "tx_bytes": row.tx_bytes,
        })
    return out
