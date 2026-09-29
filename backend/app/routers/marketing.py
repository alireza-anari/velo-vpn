from __future__ import annotations

from urllib.parse import quote, urlencode, urlparse, parse_qsl, urlunparse
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.settings_store import get_json

router = APIRouter(tags=["marketing"])


def _with_referrer(url: str, code: str) -> str:
    if not url:
        return ""
    parts = urlparse(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q["referrer"] = f"referral_code={code}"
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, urlencode(q), parts.fragment))


@router.get("/r/{code}", response_class=HTMLResponse)
def referral_landing(code: str, db: Session = Depends(get_db)):
    safe_code = "".join(ch for ch in code.upper() if ch.isalnum())[:20]
    store_url = str(get_json(db, "android_store_url", ""))
    target = _with_referrer(store_url, safe_code)
    button = (
        f'<a class="button" href="{target}">نصب Velo از Google Play</a>'
        if target else '<div class="soon">لینک انتشار Velo هنوز در پنل تنظیم نشده است.</div>'
    )
    return HTMLResponse(f'''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Velo</title><style>body{{margin:0;font-family:system-ui,Tahoma;background:#f8f6ff;color:#241d3d;display:grid;place-items:center;min-height:100vh}}.card{{width:min(92vw,430px);background:#fff;border-radius:30px;padding:34px;box-shadow:0 18px 60px #5f46a216;text-align:center}}.logo{{font-size:38px;font-weight:900;color:#7d4df5}}h1{{font-size:25px}}p{{color:#777086;line-height:1.9}}.button{{display:block;background:#8b5cf6;color:#fff;text-decoration:none;padding:15px;border-radius:18px;font-weight:800;margin-top:22px}}.code{{background:#f0ebff;padding:7px 11px;border-radius:12px;color:#6840c9;font-weight:700}}.soon{{background:#f4f1fb;padding:14px;border-radius:16px;color:#797286;margin-top:22px}}</style></head><body><div class="card"><div class="logo">♥ Velo</div><h1>دعوت شدی به Velo</h1><p>VPN ساده و دوستانه. با کد دعوت <span class="code">{safe_code}</span> وارد شو.</p>{button}</div></body></html>''')
