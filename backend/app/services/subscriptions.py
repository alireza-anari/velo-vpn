from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Subscription
from .time_utils import as_utc


def active_subscription(db: Session, user_id: int) -> Subscription | None:
    now = datetime.now(timezone.utc)
    return db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.ends_at > now)
        .order_by(Subscription.ends_at.desc())
    )
