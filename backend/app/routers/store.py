from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import User
from ..services.store import active_entitlements, catalog, heart_balance, purchase

router = APIRouter(prefix="/v1/store", tags=["store"])


@router.get("/catalog")
def get_catalog(user: User = Depends(current_user), db: Session = Depends(get_db)):
    balance = heart_balance(db, user.id)
    owned = {e.sku for e in active_entitlements(db, user.id)}
    return {
        "heart_balance": balance,
        "items": [
            {
                **item,
                "owned": item["sku"] in owned,
                "affordable": balance >= item["hearts"],
            }
            for item in catalog(db)
        ],
    }


@router.get("/entitlements")
def entitlements(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [
        {
            "id": e.id,
            "sku": e.sku,
            "kind": e.kind,
            "target": e.target,
            "value": e.value,
            "starts_at": e.starts_at,
            "expires_at": e.expires_at,
        }
        for e in active_entitlements(db, user.id)
    ]


@router.post("/purchase/{sku}")
def buy(sku: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        ent = purchase(db, user.id, sku)
    except ValueError as exc:
        code = str(exc)
        status = 409 if code == "already_owned" else 400
        raise HTTPException(status, code)
    return {
        "purchased": True,
        "sku": ent.sku,
        "kind": ent.kind,
        "expires_at": ent.expires_at,
        "heart_balance": heart_balance(db, user.id),
    }
