from __future__ import annotations
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import AppSetting


def get_json(db: Session, key: str, default):
    row = db.get(AppSetting, key)
    if not row:
        return default
    try:
        return json.loads(row.value)
    except json.JSONDecodeError:
        return default


def set_json(db: Session, key: str, value) -> None:
    row = db.get(AppSetting, key)
    encoded = json.dumps(value, ensure_ascii=False)
    if row:
        row.value = encoded
    else:
        db.add(AppSetting(key=key, value=encoded))
    db.commit()
