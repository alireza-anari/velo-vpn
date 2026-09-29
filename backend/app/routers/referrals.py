from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..db import get_db
from ..config import settings
from ..deps import current_user
from ..models import HeartLedger, Referral, ReferralDailyReward, User
from ..services.referrals import ensure_referral_code
from ..services.settings_store import get_json

router = APIRouter(prefix="/v1/referrals", tags=["referrals"])


@router.get("/me")
def my_referrals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    code = ensure_referral_code(db, user)
    rows = db.scalars(
        select(Referral).where(Referral.inviter_user_id == user.id).order_by(Referral.id.desc())
    ).all()
    items = []
    for idx, r in enumerate(rows, start=1):
        day_rewards = db.scalars(
            select(ReferralDailyReward)
            .where(ReferralDailyReward.referral_id == r.id)
            .order_by(ReferralDailyReward.local_date.asc())
        ).all()
        items.append(
            {
                "id": r.id,
                "label": f"دوست {len(rows) - idx + 1}",
                "installed": r.install_rewarded,
                "rewarded_days": r.rewarded_days,
                "days": [x.local_date.isoformat() for x in day_rewards],
                "complete": r.rewarded_days >= 7,
            }
        )
    return {
        "code": code,
        "share_url": f"{get_json(db, 'referral_base_url', settings.public_base_url.rstrip('/') + '/r')}/{code}",
        "install_reward_hearts": int(get_json(db, "referral_install_hearts", 10)),
        "daily_reward_hearts": int(get_json(db, "referral_daily_hearts", 5)),
        "items": items,
    }
