from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_device
from ..models import Device
from ..schemas import AdCompleteIn, FreeStatusOut
from ..services.rewards import RewardError, complete_rewarded_ad, create_ad_challenge
from ..services.time_utils import next_local_midnight_utc
from ..services.vpn import get_free_day

router = APIRouter(prefix="/v1/rewards", tags=["rewards"])


@router.get("/free-status", response_model=FreeStatusOut)
def free_status(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    day = get_free_day(db, device.id)
    db.commit()
    return FreeStatusOut(
        remaining_seconds=max(0, day.earned_seconds - day.consumed_seconds),
        earned_seconds=day.earned_seconds,
        consumed_seconds=day.consumed_seconds,
        completed_ads=day.completed_ads,
        reset_at=next_local_midnight_utc(),
    )


@router.post("/ad-challenge")
def ad_challenge(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    try:
        nonce = create_ad_challenge(db, device)
    except RewardError as exc:
        raise HTTPException(429, str(exc))
    return {"nonce": nonce, "expires_in_seconds": 600}


@router.post("/ad-complete")
def ad_complete(
    payload: AdCompleteIn,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
):
    try:
        granted, remaining, completed_ads = complete_rewarded_ad(
            db,
            device,
            payload.nonce,
            payload.client_event_id,
            payload.provider_response_id,
        )
    except RewardError as exc:
        raise HTTPException(400, str(exc))
    return {
        "granted_seconds": granted,
        "remaining_seconds": remaining,
        "completed_ads": completed_ads,
    }
