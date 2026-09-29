from __future__ import annotations

from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_device
from ..models import Device, FreeUsageDay, HeartLedger, MissionClaim, VpnSession
from ..services.settings_store import get_json
from ..services.time_utils import as_utc, local_date, utcnow

router = APIRouter(prefix="/v1/missions", tags=["missions"])

DEFAULT_DAILY = {
    "connect": {"title": "اولین اتصال امروز", "target": 1, "hearts": 1},
    "use_15m": {"title": "۱۵ دقیقه استفاده", "target": 900, "hearts": 2},
    "ad_1": {"title": "تماشای یک ویدیو", "target": 1, "hearts": 2},
    "ad_2": {"title": "تماشای دو ویدیو", "target": 2, "hearts": 4},
}
DEFAULT_DAILY_BONUS_HEARTS = 5


def _today_session_metrics(db: Session, device_id: int) -> tuple[int, int]:
    tz = ZoneInfo(settings.timezone_name)
    today = local_date()
    local_start = datetime.combine(today, time.min, tzinfo=tz).astimezone(timezone.utc)
    rows = db.scalars(
        select(VpnSession).where(
            VpnSession.device_id == device_id,
            VpnSession.started_at >= local_start,
        )
    ).all()
    total = 0
    for row in rows:
        start = as_utc(row.started_at)
        end = as_utc(row.ended_at) if row.ended_at else utcnow()
        total += max(0, int((end - start).total_seconds()))
    return len(rows), total


def _progress(db: Session, device: Device):
    today = local_date()
    usage = db.scalar(
        select(FreeUsageDay).where(
            FreeUsageDay.device_id == device.id,
            FreeUsageDay.local_date == today,
        )
    )
    ads = usage.completed_ads if usage else 0
    connections, seconds = _today_session_metrics(db, device.id)
    return {"connect": connections, "use_15m": seconds, "ad_1": ads, "ad_2": ads}


def _definitions(db: Session):
    raw = get_json(db, "daily_missions", DEFAULT_DAILY)
    out = {}
    for key, default in DEFAULT_DAILY.items():
        value = raw.get(key, default) if isinstance(raw, dict) else default
        out[key] = {
            "title": str(value.get("title", default["title"])),
            "target": max(1, int(value.get("target", default["target"]))),
            "hearts": max(0, int(value.get("hearts", default["hearts"]))),
        }
    return out


def _claimed_keys(db: Session, user_id: int, period: str) -> set[str]:
    return set(
        db.scalars(
            select(MissionClaim.mission_key).where(
                MissionClaim.user_id == user_id,
                MissionClaim.period_key == period,
            )
        ).all()
    )


@router.get("/today")
def today(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    defs = _definitions(db)
    progress = _progress(db, device)
    period = local_date().isoformat()
    claims = _claimed_keys(db, device.user_id, period) if device.user_id else set()
    missions = []
    all_complete = True
    for key, d in defs.items():
        current = min(progress[key], d["target"])
        complete = progress[key] >= d["target"]
        all_complete = all_complete and complete
        missions.append(
            {
                "key": key,
                "title": d["title"],
                "progress": current,
                "target": d["target"],
                "hearts": d["hearts"],
                "complete": complete,
                "claimed": key in claims,
            }
        )
    bonus_hearts = int(get_json(db, "daily_mission_bonus_hearts", DEFAULT_DAILY_BONUS_HEARTS))
    return {
        "date": period,
        "account_required_for_hearts": device.user_id is None,
        "missions": missions,
        "daily_complete": all_complete,
        "daily_bonus_hearts": bonus_hearts,
        "daily_bonus_claimed": "daily_bonus" in claims,
    }


@router.post("/claim/{mission_key}")
def claim(mission_key: str, device: Device = Depends(current_device), db: Session = Depends(get_db)):
    if not device.user_id:
        raise HTTPException(401, "account_required")
    defs = _definitions(db)
    progress = _progress(db, device)
    period = local_date().isoformat()

    if mission_key == "daily_bonus":
        if not all(progress[k] >= d["target"] for k, d in defs.items()):
            raise HTTPException(400, "mission_not_complete")
        hearts = int(get_json(db, "daily_mission_bonus_hearts", DEFAULT_DAILY_BONUS_HEARTS))
    else:
        d = defs.get(mission_key)
        if not d:
            raise HTTPException(404, "mission_not_found")
        if progress[mission_key] < d["target"]:
            raise HTTPException(400, "mission_not_complete")
        hearts = d["hearts"]

    row = MissionClaim(
        user_id=device.user_id,
        device_id=device.id,
        mission_key=mission_key,
        period_key=period,
        hearts=hearts,
    )
    db.add(row)
    if hearts:
        db.add(
            HeartLedger(
                user_id=device.user_id,
                amount=hearts,
                reason="mission",
                reference=f"{period}:{mission_key}",
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "already_claimed")
    return {"claimed": True, "mission_key": mission_key, "hearts": hearts}

DEFAULT_ONE_TIME = {
    "instagram_follow": {"title": "دنبال‌کردن اینستاگرام Velo", "url": "", "hearts": 10},
    "telegram_join": {"title": "عضویت در تلگرام Velo", "url": "", "hearts": 10},
}


def _one_time_defs(db: Session):
    raw = get_json(db, "one_time_missions", DEFAULT_ONE_TIME)
    out = {}
    for key, default in DEFAULT_ONE_TIME.items():
        value = raw.get(key, default) if isinstance(raw, dict) else default
        out[key] = {
            "title": str(value.get("title", default["title"])),
            "url": str(value.get("url", default["url"])),
            "hearts": max(0, int(value.get("hearts", default["hearts"]))),
        }
    return out


@router.get("/one-time")
def one_time(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    from ..models import MissionInteraction
    defs = _one_time_defs(db)
    claims = _claimed_keys(db, device.user_id, "once") if device.user_id else set()
    opened = set()
    if device.user_id:
        opened = set(db.scalars(select(MissionInteraction.mission_key).where(MissionInteraction.user_id == device.user_id)).all())
    return {
        "account_required_for_hearts": device.user_id is None,
        "missions": [
            {
                "key": key,
                "title": value["title"],
                "url": value["url"],
                "hearts": value["hearts"],
                "enabled": bool(value["url"]),
                "opened": key in opened,
                "claimed": key in claims,
            }
            for key, value in defs.items()
        ],
        "verification_note": "MVP social missions use a soft open-and-claim check; provider verification can replace it later.",
    }


@router.post("/open/{mission_key}")
def open_one_time(mission_key: str, device: Device = Depends(current_device), db: Session = Depends(get_db)):
    from ..models import MissionInteraction
    if not device.user_id:
        raise HTTPException(401, "account_required")
    defs = _one_time_defs(db)
    mission = defs.get(mission_key)
    if not mission or not mission["url"]:
        raise HTTPException(404, "mission_not_available")
    existing = db.scalar(
        select(MissionInteraction).where(
            MissionInteraction.user_id == device.user_id,
            MissionInteraction.mission_key == mission_key,
        )
    )
    if not existing:
        db.add(MissionInteraction(user_id=device.user_id, device_id=device.id, mission_key=mission_key))
        db.commit()
    return {"opened": True, "url": mission["url"]}


@router.post("/claim-once/{mission_key}")
def claim_one_time(mission_key: str, device: Device = Depends(current_device), db: Session = Depends(get_db)):
    from ..models import MissionInteraction
    from datetime import timedelta
    if not device.user_id:
        raise HTTPException(401, "account_required")
    defs = _one_time_defs(db)
    mission = defs.get(mission_key)
    if not mission or not mission["url"]:
        raise HTTPException(404, "mission_not_available")
    interaction = db.scalar(
        select(MissionInteraction).where(
            MissionInteraction.user_id == device.user_id,
            MissionInteraction.mission_key == mission_key,
        )
    )
    if not interaction:
        raise HTTPException(400, "mission_not_opened")
    if as_utc(interaction.opened_at) > utcnow() - timedelta(seconds=5):
        raise HTTPException(400, "wait_before_claim")

    hearts = mission["hearts"]
    db.add(MissionClaim(
        user_id=device.user_id,
        device_id=device.id,
        mission_key=mission_key,
        period_key="once",
        hearts=hearts,
    ))
    if hearts:
        db.add(HeartLedger(
            user_id=device.user_id,
            amount=hearts,
            reason="mission_once",
            reference=f"once:{mission_key}",
        ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "already_claimed")
    return {"claimed": True, "mission_key": mission_key, "hearts": hearts}

DEFAULT_WEEKLY = {
    "active_5_days": {"title": "۵ روز فعال در هفته", "target": 5, "hearts": 20},
    "ads_10": {"title": "تماشای ۱۰ ویدیوی جایزه‌ای", "target": 10, "hearts": 20},
    "use_120m": {"title": "۲ ساعت استفاده در هفته", "target": 7200, "hearts": 20},
}
DEFAULT_WEEKLY_BONUS_HEARTS = 15


def _week_bounds():
    tz = ZoneInfo(settings.timezone_name)
    now_local = datetime.now(tz)
    start_date = now_local.date() - timedelta(days=now_local.weekday())
    end_date = start_date + timedelta(days=7)
    start_utc = datetime.combine(start_date, time.min, tzinfo=tz).astimezone(timezone.utc)
    end_utc = datetime.combine(end_date, time.min, tzinfo=tz).astimezone(timezone.utc)
    iso = start_date.isocalendar()
    period = f"week:{iso.year}-W{iso.week:02d}"
    return start_date, end_date, start_utc, end_utc, period


def _weekly_defs(db: Session):
    raw = get_json(db, "weekly_missions", DEFAULT_WEEKLY)
    out = {}
    for key, default in DEFAULT_WEEKLY.items():
        value = raw.get(key, default) if isinstance(raw, dict) else default
        out[key] = {
            "title": str(value.get("title", default["title"])),
            "target": max(1, int(value.get("target", default["target"]))),
            "hearts": max(0, int(value.get("hearts", default["hearts"]))),
        }
    return out


def _weekly_progress(db: Session, device: Device):
    start_date, end_date, start_utc, end_utc, _ = _week_bounds()
    device_ids = [device.id]
    if device.user_id:
        from ..models import Device as DeviceModel
        device_ids = list(db.scalars(select(DeviceModel.id).where(DeviceModel.user_id == device.user_id)).all()) or [device.id]

    sessions = db.scalars(
        select(VpnSession).where(
            VpnSession.device_id.in_(device_ids),
            VpnSession.started_at >= start_utc,
            VpnSession.started_at < end_utc,
        )
    ).all()
    total_seconds = 0
    active_days = set()
    tz = ZoneInfo(settings.timezone_name)
    for row in sessions:
        start = as_utc(row.started_at)
        end = as_utc(row.ended_at) if row.ended_at else utcnow()
        secs = max(0, int((end - start).total_seconds()))
        total_seconds += secs
        if secs >= 300:
            active_days.add(start.astimezone(tz).date())

    usage_rows = db.scalars(
        select(FreeUsageDay).where(
            FreeUsageDay.device_id.in_(device_ids),
            FreeUsageDay.local_date >= start_date,
            FreeUsageDay.local_date < end_date,
        )
    ).all()
    ads = sum(int(row.completed_ads or 0) for row in usage_rows)
    return {"active_5_days": len(active_days), "ads_10": ads, "use_120m": total_seconds}


@router.get("/weekly")
def weekly(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    defs = _weekly_defs(db)
    progress = _weekly_progress(db, device)
    start_date, end_date, _, _, period = _week_bounds()
    claims = _claimed_keys(db, device.user_id, period) if device.user_id else set()
    missions = []
    all_complete = True
    for key, d in defs.items():
        current = min(progress[key], d["target"])
        complete = progress[key] >= d["target"]
        all_complete = all_complete and complete
        missions.append({
            "key": key,
            "title": d["title"],
            "progress": current,
            "target": d["target"],
            "hearts": d["hearts"],
            "complete": complete,
            "claimed": key in claims,
        })
    bonus = int(get_json(db, "weekly_mission_bonus_hearts", DEFAULT_WEEKLY_BONUS_HEARTS))
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "account_required_for_hearts": device.user_id is None,
        "missions": missions,
        "weekly_complete": all_complete,
        "weekly_bonus_hearts": bonus,
        "weekly_bonus_claimed": "weekly_bonus" in claims,
    }


@router.post("/claim-week/{mission_key}")
def claim_week(mission_key: str, device: Device = Depends(current_device), db: Session = Depends(get_db)):
    if not device.user_id:
        raise HTTPException(401, "account_required")
    defs = _weekly_defs(db)
    progress = _weekly_progress(db, device)
    _, _, _, _, period = _week_bounds()
    if mission_key == "weekly_bonus":
        if not all(progress[k] >= d["target"] for k, d in defs.items()):
            raise HTTPException(400, "mission_not_complete")
        hearts = int(get_json(db, "weekly_mission_bonus_hearts", DEFAULT_WEEKLY_BONUS_HEARTS))
    else:
        d = defs.get(mission_key)
        if not d:
            raise HTTPException(404, "mission_not_found")
        if progress[mission_key] < d["target"]:
            raise HTTPException(400, "mission_not_complete")
        hearts = d["hearts"]
    row = MissionClaim(
        user_id=device.user_id,
        device_id=device.id,
        mission_key=mission_key,
        period_key=period,
        hearts=hearts,
    )
    db.add(row)
    if hearts:
        db.add(HeartLedger(user_id=device.user_id, amount=hearts, reason="mission_weekly", reference=f"{period}:{mission_key}"))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "already_claimed")
    return {"claimed": True, "mission_key": mission_key, "hearts": hearts}
