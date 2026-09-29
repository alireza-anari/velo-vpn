from __future__ import annotations

from pathlib import Path
import hashlib
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import HeartLedger, ManualPayment, User
from ..services.emailer import send_email
from ..services.settings_store import get_json

router = APIRouter(prefix="/v1/payments", tags=["payments"])
UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
VALID_PLANS = {"15d", "1m", "3m", "6m"}
DEFAULT_PRICES = {"15d": 189000, "1m": 349000, "3m": 949000, "6m": 1749000}
DEFAULT_DISCOUNT_TIERS = {100: 5, 250: 10, 450: 15, 700: 20, 1000: 25, 1400: 30}


def _detect_receipt(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if data.startswith(b"%PDF-"):
        return ".pdf", "application/pdf"
    raise HTTPException(400, "invalid_receipt_content")


@router.post("/manual")
async def manual_payment(
    kind: str = Form(...),
    amount_toman: int = Form(...),
    plan_code: str | None = Form(None),
    requested_hearts: int = Form(0),
    receipt: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if kind not in {"premium", "support"}:
        raise HTTPException(400, "invalid_payment_kind")
    if kind == "premium" and plan_code not in VALID_PLANS:
        raise HTTPException(400, "invalid_plan_code")
    if amount_toman <= 0:
        raise HTTPException(400, "invalid_amount")
    if requested_hearts < 0:
        raise HTTPException(400, "invalid_requested_hearts")

    if kind == "premium":
        prices = get_json(db, "premium_prices", DEFAULT_PRICES)
        base_price = int(prices.get(plan_code or "", 0))
        if base_price <= 0:
            raise HTTPException(400, "invalid_plan_price")
        raw_tiers = get_json(db, "heart_discount_tiers", DEFAULT_DISCOUNT_TIERS)
        tiers = {int(k): int(v) for k, v in raw_tiers.items()}
        discount_percent = tiers.get(int(requested_hearts), 0) if requested_hearts else 0
        max_discount = int(get_json(db, "max_heart_discount_percent", settings.max_heart_discount_percent))
        if requested_hearts and discount_percent <= 0:
            raise HTTPException(400, "invalid_heart_discount_tier")
        if discount_percent > max_discount:
            raise HTTPException(400, "discount_above_cap")
        expected_amount = (base_price * (100 - discount_percent) + 99) // 100
        if int(amount_toman) != expected_amount:
            raise HTTPException(400, "premium_amount_mismatch")
        if requested_hearts:
            balance = int(db.scalar(select(func.coalesce(func.sum(HeartLedger.amount), 0)).where(HeartLedger.user_id == user.id)) or 0)
            if balance < requested_hearts:
                raise HTTPException(400, "insufficient_hearts")
    elif requested_hearts:
        raise HTTPException(400, "hearts_only_for_premium_discount")
    if receipt.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "invalid_receipt_type")

    data = await receipt.read()
    if not data:
        raise HTTPException(400, "empty_receipt")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "receipt_too_large")
    suffix, detected_type = _detect_receipt(data)
    if receipt.content_type != detected_type and not (receipt.content_type == "image/jpeg" and detected_type == "image/jpeg"):
        raise HTTPException(400, "receipt_type_mismatch")
    digest = hashlib.sha256(data).hexdigest()
    duplicate = db.scalar(
        select(ManualPayment).where(
            ManualPayment.receipt_sha256 == digest,
            ManualPayment.status.in_(["pending", "approved"]),
        )
    )
    if duplicate:
        raise HTTPException(409, "duplicate_receipt")
    name = f"{user.id}_{secrets.token_hex(16)}{suffix}"
    path = UPLOAD_DIR / name
    path.write_bytes(data)

    p = ManualPayment(
        user_id=user.id,
        kind=kind,
        amount_toman=amount_toman,
        plan_code=plan_code,
        requested_hearts=requested_hearts or None,
        receipt_path=str(path),
        receipt_sha256=digest,
        status="pending",
    )
    db.add(p)
    db.flush()
    if kind == "premium" and requested_hearts:
        db.add(
            HeartLedger(
                user_id=user.id,
                amount=-requested_hearts,
                reason="premium_discount_pending",
                reference=f"payment:{p.id}",
            )
        )
    db.commit()
    db.refresh(p)

    if settings.admin_notification_email:
        send_email(
            settings.admin_notification_email,
            f"Velo: درخواست پرداخت #{p.id}",
            f"کاربر: {user.email}\nنوع: {kind}\nمبلغ: {amount_toman:,} تومان\nشناسه: {p.id}",
        )
    return {"id": p.id, "status": p.status}


@router.get("/mine")
def mine(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ManualPayment)
        .where(ManualPayment.user_id == user.id)
        .order_by(ManualPayment.id.desc())
    ).all()
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "amount_toman": r.amount_toman,
            "plan_code": r.plan_code,
            "requested_hearts": r.requested_hearts,
            "status": r.status,
            "admin_note": r.admin_note,
            "created_at": r.created_at,
            "reviewed_at": r.reviewed_at,
        }
        for r in rows
    ]
