from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine
from .migrations import run_lightweight_migrations
from .observability import background_error, configure_logging, install_observability
from .routers import admin, admin_web, auth, config, legal, marketing, missions, payments, referrals, reports, rewards, store, users, vpn
from .services.vpn import bootstrap_server, expire_due_sessions
from .services.wireguard import check_all_servers, reconcile_all_servers

configure_logging()
log = logging.getLogger("velo")


def _validate_production_secrets() -> None:
    if settings.environment.lower() != "production":
        return
    bad = []
    if settings.jwt_secret in {"", "dev-secret-change-me"} or len(settings.jwt_secret) < 32:
        bad.append("JWT_SECRET")
    if settings.admin_api_key in {"", "dev-admin-key-change-me"} or len(settings.admin_api_key) < 24:
        bad.append("ADMIN_API_KEY")
    admin_password = settings.admin_panel_password or settings.admin_api_key
    if len(admin_password) < 12:
        bad.append("ADMIN_PANEL_PASSWORD")
    if settings.metrics_enabled and not settings.metrics_bearer_token.strip():
        bad.append("METRICS_BEARER_TOKEN")
    if bad:
        raise RuntimeError("unsafe_production_secrets:" + ",".join(bad))


async def _session_reaper(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            with SessionLocal() as db:
                expire_due_sessions(db)
        except Exception:
            background_error("session_reaper")
            log.exception("session reaper failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass


async def _node_health_monitor(stop: asyncio.Event) -> None:
    delay = max(10, int(settings.node_health_interval_seconds))
    while not stop.is_set():
        try:
            with SessionLocal() as db:
                check_all_servers(db)
        except Exception:
            background_error("node_health_monitor")
            log.exception("node health monitor failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass


async def _peer_reconciler(stop: asyncio.Event) -> None:
    delay = max(30, int(settings.peer_reconcile_interval_seconds))
    # Do not race initial server bootstrap/health checks at process start.
    try:
        await asyncio.wait_for(stop.wait(), timeout=min(30, delay))
        return
    except asyncio.TimeoutError:
        pass
    while not stop.is_set():
        try:
            with SessionLocal() as db:
                reconcile_all_servers(db)
        except Exception:
            background_error("peer_reconciler")
            log.exception("peer reconciler failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_production_secrets()
    if settings.auto_schema_create:
        Base.metadata.create_all(engine)
        run_lightweight_migrations(engine)
    elif settings.environment.lower() == "production":
        log.info("automatic schema creation disabled; expecting Alembic migrations to be applied")
    with SessionLocal() as db:
        bootstrap_server(db)
    stop = asyncio.Event()
    tasks = [
        asyncio.create_task(_session_reaper(stop)),
        asyncio.create_task(_node_health_monitor(stop)),
        asyncio.create_task(_peer_reconciler(stop)),
    ]
    app.state.background_stop = stop
    try:
        yield
    finally:
        stop.set()
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass


_is_prod = settings.environment.lower() == "production"
app = FastAPI(
    title="Velo API",
    version="0.7.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

app.include_router(auth.router)
app.include_router(config.router)
app.include_router(legal.router)
app.include_router(marketing.router)
app.include_router(rewards.router)
app.include_router(store.router)
app.include_router(missions.router)
app.include_router(vpn.router)
app.include_router(users.router)
app.include_router(payments.router)
app.include_router(reports.router)
app.include_router(referrals.router)
app.include_router(admin.router)
app.include_router(admin_web.router)
install_observability(app)


@app.get("/health")
def health():
    return {"ok": True, "version": "0.7.0"}


@app.get("/health/live", include_in_schema=False)
def health_live():
    return {"ok": True, "service": "velo-api", "version": "0.7.0"}


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    checks = {"database": False, "vpn_server": None}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = True
        if settings.readiness_require_vpn_server:
            from .models import VpnServer
            with SessionLocal() as db:
                checks["vpn_server"] = db.query(VpnServer).filter(VpnServer.is_active.is_(True)).count() > 0
            if not checks["vpn_server"]:
                return JSONResponse(status_code=503, content={"ok": False, "checks": checks})
        return {"ok": True, "checks": checks}
    except Exception:
        log.exception("readiness check failed")
        return JSONResponse(status_code=503, content={"ok": False, "checks": checks})
