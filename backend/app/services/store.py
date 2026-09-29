from __future__ import annotations

from datetime import timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import HeartLedger, StorePurchase, UserEntitlement
from .settings_store import get_json
from .time_utils import as_utc, utcnow


DEFAULT_STORE_CATALOG = [
    {
        "sku": "vip_us_30d",
        "title": "سرور VIP آمریکا",
        "description": "دسترسی ۳۰ روزه به سرورهای VIP آمریکا",
        "kind": "server_access",
        "target": "US",
        "hearts": 700,
        "duration_days": 30,
        "enabled": True,
        "badge": "VIP",
    },
    {
        "sku": "free_speed_4mbps_1d",
        "title": "افزایش سرعت رایگان",
        "description": "سرعت نسخه رایگان تا ۴ Mbps برای ۲۴ ساعت",
        "kind": "speed_boost",
        "target": "free",
        "value": 4,
        "hearts": 80,
        "duration_days": 1,
        "enabled": True,
        "badge": "24h",
    },
    {
        "sku": "theme_aurora",
        "title": "تم Aurora",
        "description": "یک ظاهر ویژه برای Velo",
        "kind": "cosmetic",
        "target": "aurora",
        "hearts": 250,
        "duration_days": 0,
        "enabled": True,
        "badge": "ظاهر",
    },
    {
        "sku": "static_ip_30d",
        "title": "IP ثابت",
        "description": "IP ثابت ۳۰ روزه؛ پس از فعال‌شدن زیرساخت قابل خرید خواهد بود",
        "kind": "static_ip",
        "target": "auto",
        "hearts": 3000,
        "duration_days": 30,
        "enabled": False,
        "badge": "به‌زودی",
    },
]


def heart_balance(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(HeartLedger.amount), 0)).where(HeartLedger.user_id == user_id)
        )
        or 0
    )


def catalog(db: Session) -> list[dict]:
    raw = get_json(db, "store_catalog", DEFAULT_STORE_CATALOG)
    if not isinstance(raw, list):
        raw = DEFAULT_STORE_CATALOG
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            sku = str(item["sku"]).strip()
            hearts = max(0, int(item.get("hearts", 0)))
            kind = str(item.get("kind", "cosmetic")).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if not sku or not kind:
            continue
        out.append(
            {
                "sku": sku,
                "title": str(item.get("title", sku)),
                "description": str(item.get("description", "")),
                "kind": kind,
                "target": str(item.get("target", "")) or None,
                "value": int(item["value"]) if item.get("value") is not None else None,
                "hearts": hearts,
                "duration_days": max(0, int(item.get("duration_days", 0))),
                "enabled": bool(item.get("enabled", True)),
                "badge": str(item.get("badge", "")),
            }
        )
    return out


def get_item(db: Session, sku: str) -> dict | None:
    return next((item for item in catalog(db) if item["sku"] == sku), None)


def active_entitlements(db: Session, user_id: int) -> list[UserEntitlement]:
    now = utcnow()
    rows = db.scalars(
        select(UserEntitlement)
        .where(UserEntitlement.user_id == user_id)
        .order_by(UserEntitlement.id.desc())
    ).all()
    return [row for row in rows if row.expires_at is None or as_utc(row.expires_at) > now]


def has_server_access(db: Session, user_id: int, country_code: str) -> bool:
    cc = country_code.upper()
    for ent in active_entitlements(db, user_id):
        if ent.kind == "server_access" and (ent.target or "").upper() in {cc, "*"}:
            return True
    return False


def free_speed_entitlement_mbps(db: Session, user_id: int | None) -> int | None:
    if not user_id:
        return None
    values = [
        ent.value
        for ent in active_entitlements(db, user_id)
        if ent.kind == "speed_boost" and ent.value and ent.value > 0
    ]
    return max(values) if values else None


def purchase(db: Session, user_id: int, sku: str) -> UserEntitlement:
    item = get_item(db, sku)
    if not item or not item["enabled"]:
        raise ValueError("store_item_unavailable")
    if item["kind"] == "static_ip":
        raise ValueError("store_item_not_ready")
    cost = int(item["hearts"])
    if heart_balance(db, user_id) < cost:
        raise ValueError("insufficient_hearts")

    # Permanent cosmetics should be idempotent instead of charging twice.
    if item["duration_days"] == 0:
        existing = db.scalar(
            select(UserEntitlement).where(
                UserEntitlement.user_id == user_id,
                UserEntitlement.sku == sku,
                UserEntitlement.expires_at.is_(None),
            )
        )
        if existing:
            raise ValueError("already_owned")

    now = utcnow()
    expires_at = now + timedelta(days=item["duration_days"]) if item["duration_days"] else None
    ent = UserEntitlement(
        user_id=user_id,
        sku=sku,
        kind=item["kind"],
        target=item.get("target"),
        value=item.get("value"),
        starts_at=now,
        expires_at=expires_at,
    )
    db.add(ent)
    db.flush()
    db.add(StorePurchase(user_id=user_id, sku=sku, hearts_spent=cost))
    if cost:
        db.add(
            HeartLedger(
                user_id=user_id,
                amount=-cost,
                reason="store_purchase",
                reference=f"entitlement:{ent.id}:{sku}",
            )
        )
    db.commit()
    db.refresh(ent)
    return ent
