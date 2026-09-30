from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import User
from ..services.web_vpn import WebVpnBusinessError, access_status, config_filename, issue_config

router = APIRouter(prefix="/v1/web-vpn", tags=["web-vpn"])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"


@router.get("/access")
def get_access(
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _no_store(response)
    return access_status(db, user)


def _issue(response: Response, user: User, db: Session, replace: bool) -> dict:
    _no_store(response)
    try:
        status, configuration = issue_config(db, user, replace=replace)
    except WebVpnBusinessError as exc:
        code = str(exc)
        status_code = 409 if code == "configuration_already_issued" else 400
        raise HTTPException(status_code, code) from exc
    return {
        "access": status,
        "configuration": configuration,
        "filename": config_filename(status),
    }


@router.post("/provision")
def provision(
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _issue(response, user, db, replace=False)


@router.post("/regenerate")
def regenerate(
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _issue(response, user, db, replace=True)
