from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..schemas import ConfigResponse
from ..services.settings_store import get_json

router = APIRouter(prefix="/v1/config", tags=["config"])


@router.get("/public", response_model=ConfigResponse)
def public_config(db: Session = Depends(get_db)):
    return ConfigResponse(
        free_speed_mbps=int(get_json(db, "free_speed_mbps", settings.free_speed_mbps)),
        ad_reward_minutes=int(get_json(db, "ad_reward_minutes", settings.ad_reward_minutes)),
        premium_prices=get_json(
            db,
            "premium_prices",
            {"15d": 189000, "1m": 349000, "3m": 949000, "6m": 1749000},
        ),
        max_heart_discount_percent=int(
            get_json(db, "max_heart_discount_percent", settings.max_heart_discount_percent)
        ),
        heart_discount_tiers={str(k): int(v) for k, v in get_json(
            db, "heart_discount_tiers", {100: 5, 250: 10, 450: 15, 700: 20, 1000: 25, 1400: 30}
        ).items()},
        support_heart_tiers={str(k): int(v) for k, v in get_json(
            db, "support_heart_tiers", {50000: 40, 100000: 90, 250000: 250, 500000: 550}
        ).items()},
        manual_card_number=str(get_json(db, "manual_card_number", settings.manual_card_number)),
        manual_card_holder=str(get_json(db, "manual_card_holder", settings.manual_card_holder)),
        tapsell_app_key=str(get_json(db, "tapsell_app_key", settings.tapsell_app_key)),
        tapsell_rewarded_zone_id=str(
            get_json(db, "tapsell_rewarded_zone_id", settings.tapsell_rewarded_zone_id)
        ),
        timezone_name=settings.timezone_name,
    )
