from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_admin
from ..models import AdminAuditLog, HeartLedger, ManualPayment, Subscription, User, VpnServer
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
    return [
        {
            "id": s.id,
            "name": s.name,
            "country_code": s.country_code,
            "city": s.city,
            "endpoint": f"{s.endpoint_host}:{s.endpoint_port}",
            "tier": s.tier,
            "active": s.is_active,
            "default": s.is_default,
            "max_sessions": s.max_sessions,
            "agent_configured": bool(s.agent_url),
            "health_state": s.health_state,
            "health_failures": s.health_failures,
            "last_health_at": s.last_health_at,
            "last_health_error": s.last_health_error,
            "unhealthy_until": s.unhealthy_until,
        }
        for s in rows
    ]


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
