from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy import func

from .config import settings
from .db import SessionLocal
from .models import ManualPayment, RewardEvent, VpnServer, VpnSession

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("velo_request_id", default="-")

HTTP_REQUESTS = Counter(
    "velo_http_requests_total",
    "HTTP requests handled by the Velo API",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "velo_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
BACKGROUND_ERRORS = Counter(
    "velo_background_errors_total",
    "Background task failures",
    ["task"],
)
ACTIVE_VPN = Gauge("velo_active_vpn_sessions", "Active VPN sessions")
UNHEALTHY_NODES = Gauge("velo_unhealthy_vpn_nodes", "Active VPN nodes currently unhealthy")
PENDING_PAYMENTS = Gauge("velo_pending_manual_payments", "Manual payments waiting for review")
REWARD_EVENTS = Gauge("velo_reward_events_total_db", "Reward events stored in the database")


class _RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    for handler in root.handlers:
        handler.addFilter(_RequestContextFilter())
        if settings.log_json:
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s")
            )


def background_error(task: str) -> None:
    BACKGROUND_ERRORS.labels(task=task).inc()


def _refresh_business_gauges() -> None:
    with SessionLocal() as db:
        ACTIVE_VPN.set(db.query(func.count(VpnSession.id)).filter(VpnSession.status == "active").scalar() or 0)
        UNHEALTHY_NODES.set(
            db.query(func.count(VpnServer.id))
            .filter(VpnServer.is_active.is_(True), VpnServer.health_state == "unhealthy")
            .scalar()
            or 0
        )
        PENDING_PAYMENTS.set(
            db.query(func.count(ManualPayment.id)).filter(ManualPayment.status == "pending").scalar() or 0
        )
        REWARD_EVENTS.set(db.query(func.count(RewardEvent.id)).scalar() or 0)


def install_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_and_metrics(request: Request, call_next):
        request_id = (request.headers.get("X-Request-ID") or "").strip()[:96] or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        response: Response | None = None
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - started
            route_obj = request.scope.get("route")
            route = getattr(route_obj, "path", None) or "unmatched"
            HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
            HTTP_LATENCY.labels(request.method, route).observe(elapsed)
            request_id_var.reset(token)

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception):
        request_id = request_id_var.get("-")
        logging.getLogger("velo.errors").exception(
            "unhandled request exception method=%s path=%s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "internal_server_error", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    @app.get("/metrics", include_in_schema=False)
    def metrics(request: Request):
        if not settings.metrics_enabled:
            return Response(status_code=404)
        expected = settings.metrics_bearer_token.strip()
        if expected:
            supplied = request.headers.get("Authorization", "")
            if supplied != f"Bearer {expected}":
                return Response(status_code=401)
        elif settings.environment.lower() == "production":
            # Never expose production metrics publicly by accident.
            return Response(status_code=404)
        try:
            _refresh_business_gauges()
        except Exception:
            logging.getLogger("velo.metrics").exception("business metric refresh failed")
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
