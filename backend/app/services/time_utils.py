from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from ..config import settings


def tz() -> ZoneInfo:
    return ZoneInfo(settings.timezone_name)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    return utcnow().astimezone(tz())


def local_date():
    return local_now().date()


def next_local_midnight_utc() -> datetime:
    now_local = local_now()
    tomorrow = now_local.date() + timedelta(days=1)
    next_midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tz())
    return next_midnight.astimezone(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
