from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_device
from ..models import Device, FreeUsageDay, VpnServer, VpnSession
from ..services.time_utils import local_date, utcnow
from ..services.wireguard import peer_transfer

router = APIRouter(prefix="/v1/reports", tags=["reports"])


def _session_metrics(db: Session, s: VpnSession):
    now = utcnow()
    ended = s.ended_at or now
    started = s.started_at
    if started.tzinfo is None:
        from datetime import timezone
        started = started.replace(tzinfo=timezone.utc)
    if ended.tzinfo is None:
        from datetime import timezone
        ended = ended.replace(tzinfo=timezone.utc)
    seconds = max(0, int((ended - started).total_seconds()))
    rx, tx = s.rx_bytes or 0, s.tx_bytes or 0
    if s.status == "active":
        server = db.get(VpnServer, s.server_id)
        live_rx, live_tx = peer_transfer(server, s.client_public_key) if server else (0, 0)
        rx, tx = max(rx, live_rx), max(tx, live_tx)
    return seconds, rx, tx


@router.get("/summary")
def summary(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    tz = ZoneInfo(settings.timezone_name)
    today = local_date()
    month_start = today.replace(day=1)
    since = utcnow() - timedelta(days=40)
    sessions = db.scalars(
        select(VpnSession).where(
            VpnSession.device_id == device.id,
            VpnSession.started_at >= since,
        ).order_by(VpnSession.started_at.asc())
    ).all()

    by_day = defaultdict(lambda: {"seconds": 0, "bytes": 0, "connections": 0})
    for s in sessions:
        d = s.started_at.astimezone(tz).date() if s.started_at.tzinfo else s.started_at.replace(tzinfo=tz).date()
        sec, rx, tx = _session_metrics(db, s)
        by_day[d]["seconds"] += sec
        by_day[d]["bytes"] += rx + tx
        by_day[d]["connections"] += 1

    free_today = db.scalar(
        select(FreeUsageDay).where(
            FreeUsageDay.device_id == device.id,
            FreeUsageDay.local_date == today,
        )
    )
    today_data = by_day[today]
    month_days = [v for d, v in by_day.items() if d >= month_start]
    last7 = []
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        v = by_day[d]
        last7.append({"date": d.isoformat(), "seconds": v["seconds"], "bytes": v["bytes"]})

    return {
        "today_seconds": today_data["seconds"],
        "today_rx_bytes": 0,  # compact report UI uses total bytes; kept for API compatibility
        "today_tx_bytes": today_data["bytes"],
        "today_connections": today_data["connections"],
        "today_ads": free_today.completed_ads if free_today else 0,
        "month_seconds": sum(v["seconds"] for v in month_days),
        "month_bytes": sum(v["bytes"] for v in month_days),
        "last_7_days": last7,
    }
