from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import HeartLedger, Subscription, User
from ..services.subscriptions import active_subscription
from ..services.time_utils import utcnow

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/me/hearts")
def hearts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    balance = db.scalar(select(func.coalesce(func.sum(HeartLedger.amount), 0)).where(HeartLedger.user_id == user.id))
    return {"balance": int(balance or 0)}


@router.get("/me/subscription")
def subscription(user: User = Depends(current_user), db: Session = Depends(get_db)):
    sub = active_subscription(db, user.id)
    return {
        "active": bool(sub),
        "ends_at": sub.ends_at if sub else None,
        "source": sub.source if sub else None,
    }
