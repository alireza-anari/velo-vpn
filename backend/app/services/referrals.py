from __future__ import annotations

import secrets
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Device, HeartLedger, Referral, ReferralDailyReward, User, VpnSession
from .settings_store import get_json
from .time_utils import local_date, local_now


def ensure_referral_code(db: Session, user: User) -> str:
    if user.referral_code:
        return user.referral_code
    for _ in range(8):
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()
        exists = db.scalar(select(User).where(User.referral_code == code))
        if not exists:
            user.referral_code = code
            db.commit()
            return code
    raise RuntimeError("could_not_allocate_referral_code")


def attach_referral_on_install(db: Session, device: Device, referral_code: str | None) -> Referral | None:
    if not referral_code:
        return None
    existing = db.scalar(select(Referral).where(Referral.invited_device_id == device.id))
    if existing:
        return existing
    inviter = db.scalar(select(User).where(User.referral_code == referral_code.strip().upper()))
    if not inviter:
        return None
    if device.user_id and device.user_id == inviter.id:
        return None
    hearts = int(get_json(db, "referral_install_hearts", 10))
    referral = Referral(inviter_user_id=inviter.id, invited_device_id=device.id, install_rewarded=True)
    db.add(referral)
    if hearts > 0:
        db.add(HeartLedger(user_id=inviter.id, amount=hearts, reason="referral_install", reference=f"device:{device.id}"))
    db.commit()
    db.refresh(referral)
    return referral


def link_invited_user(db: Session, device: Device, user: User) -> None:
    row = db.scalar(select(Referral).where(Referral.invited_device_id == device.id))
    if row and not row.invited_user_id and row.inviter_user_id != user.id:
        row.invited_user_id = user.id
        db.commit()


def record_referral_usage(db: Session, session: VpnSession) -> None:
    # A real usage day requires at least five minutes of VPN time.
    if session.consumed_seconds < 300:
        return
    referral = db.scalar(select(Referral).where(Referral.invited_device_id == session.device_id))
    if not referral:
        return
    # Only first 7 distinct usage days after installation are rewarded.
    if referral.rewarded_days >= 7:
        return
    today = local_date()
    existing = db.scalar(
        select(ReferralDailyReward).where(
            ReferralDailyReward.referral_id == referral.id,
            ReferralDailyReward.local_date == today,
        )
    )
    if existing:
        return
    hearts = int(get_json(db, "referral_daily_hearts", 5))
    reward = ReferralDailyReward(referral_id=referral.id, local_date=today, hearts=hearts)
    db.add(reward)
    if hearts > 0:
        db.add(HeartLedger(user_id=referral.inviter_user_id, amount=hearts, reason="referral_daily_use", reference=f"referral:{referral.id}:{today}"))
    referral.rewarded_days += 1
    # Optional completion bonus on the seventh rewarded day.
    if referral.rewarded_days == 7:
        bonus = int(get_json(db, "referral_day7_bonus_hearts", 5))
        if bonus > 0:
            db.add(HeartLedger(user_id=referral.inviter_user_id, amount=bonus, reason="referral_7day_bonus", reference=f"referral:{referral.id}"))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
