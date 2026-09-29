from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
import secrets
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AdChallenge, Device, RewardEvent
from .time_utils import as_utc, utcnow
from .settings_store import get_json
from .vpn import get_free_day


class RewardError(RuntimeError):
    pass


def create_ad_challenge(db: Session, device: Device) -> str:
    # High ceiling only for automation/fraud protection; there is no normal product limit.
    since = utcnow() - timedelta(minutes=10)
    recent = int(
        db.scalar(
            select(func.count(AdChallenge.id)).where(
                AdChallenge.device_id == device.id,
                AdChallenge.created_at >= since,
            )
        )
        or 0
    )
    if recent >= 30:
        raise RewardError("too_many_ad_requests")

    nonce = secrets.token_urlsafe(32)
    row = AdChallenge(
        device_id=device.id,
        nonce_hash=sha256(nonce.encode()).hexdigest(),
        provider="tapsell",
        expires_at=utcnow() + timedelta(minutes=10),
    )
    db.add(row)
    db.commit()
    return nonce


def complete_rewarded_ad(
    db: Session,
    device: Device,
    nonce: str,
    client_event_id: str,
    provider_response_id: str | None,
) -> tuple[int, int, int]:
    nonce_hash = sha256(nonce.encode()).hexdigest()
    challenge = db.scalar(
        select(AdChallenge).where(
            AdChallenge.device_id == device.id,
            AdChallenge.nonce_hash == nonce_hash,
        )
    )
    if not challenge or challenge.consumed:
        raise RewardError("invalid_or_used_challenge")
    if as_utc(challenge.expires_at) < utcnow():
        raise RewardError("expired_challenge")

    existing = db.scalar(
        select(RewardEvent).where(
            RewardEvent.device_id == device.id,
            RewardEvent.client_event_id == client_event_id,
        )
    )
    if existing:
        day = get_free_day(db, device.id)
        return existing.reward_seconds, max(0, day.earned_seconds - day.consumed_seconds), day.completed_ads

    reward_minutes = int(get_json(db, "ad_reward_minutes", settings.ad_reward_minutes))
    reward_seconds = max(1, reward_minutes) * 60
    day = get_free_day(db, device.id)
    day.earned_seconds += reward_seconds
    day.completed_ads += 1
    challenge.consumed = True
    event = RewardEvent(
        device_id=device.id,
        user_id=device.user_id,
        provider="tapsell",
        client_event_id=client_event_id,
        provider_response_id=(provider_response_id or "")[:180] or None,
        reward_seconds=reward_seconds,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(RewardEvent).where(
                RewardEvent.device_id == device.id,
                RewardEvent.client_event_id == client_event_id,
            )
        )
        if not existing:
            raise
        day = get_free_day(db, device.id)
        return existing.reward_seconds, max(0, day.earned_seconds - day.consumed_seconds), day.completed_ads
    return reward_seconds, max(0, day.earned_seconds - day.consumed_seconds), day.completed_ads
