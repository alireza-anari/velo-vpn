from __future__ import annotations

from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Device, FreeUsageDay, VpnServer, VpnSession
from .subscriptions import active_subscription
from .store import free_speed_entitlement_mbps, has_server_access
from .time_utils import as_utc, local_date, next_local_midnight_utc, utcnow
from .settings_store import get_json
from .wireguard import (
    WireGuardError, add_peer, allocate_client_ip, choose_servers,
    mark_server_failure, mark_server_healthy, peer_latest_handshake_at, peer_transfer,
    remove_peer, validate_public_key,
)


class VpnBusinessError(RuntimeError):
    pass


def get_free_day(db: Session, device_id: int) -> FreeUsageDay:
    today = local_date()
    row = db.scalar(
        select(FreeUsageDay).where(
            FreeUsageDay.device_id == device_id,
            FreeUsageDay.local_date == today,
        )
    )
    if not row:
        row = FreeUsageDay(device_id=device_id, local_date=today)
        db.add(row)
        db.flush()
    return row


def remaining_free_seconds(db: Session, device_id: int) -> int:
    row = get_free_day(db, device_id)
    return max(0, int(row.earned_seconds - row.consumed_seconds))


def _elapsed_seconds(session: VpnSession, ended_at: datetime) -> int:
    started = session.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return max(0, int((ended_at - started).total_seconds()))


def close_session(db: Session, session: VpnSession, reason: str = "client_disconnect") -> VpnSession:
    if session.status != "active":
        return session
    ended = utcnow()
    elapsed = _elapsed_seconds(session, ended)
    server = db.get(VpnServer, session.server_id)
    rx, tx = peer_transfer(server, session.client_public_key) if server else (0, 0)
    if server:
        remove_peer(server, session.client_public_key, session.client_ip)

    session.status = "ended"
    session.ended_at = ended
    session.disconnect_reason = reason
    session.rx_bytes = max(session.rx_bytes or 0, rx)
    session.tx_bytes = max(session.tx_bytes or 0, tx)

    if not session.is_premium:
        free_day = get_free_day(db, session.device_id)
        remaining_before = max(0, free_day.earned_seconds - free_day.consumed_seconds)
        consumed = min(elapsed, remaining_before)
        free_day.consumed_seconds += consumed
        free_day.connection_seconds += consumed
        session.consumed_seconds = consumed
    else:
        session.consumed_seconds = elapsed
    db.commit()
    db.refresh(session)
    try:
        from .referrals import record_referral_usage
        record_referral_usage(db, session)
    except Exception:
        # Referral accounting must never block VPN cleanup.
        db.rollback()
    return session


def close_active_for_device(db: Session, device_id: int, reason: str) -> None:
    rows = db.scalars(
        select(VpnSession).where(
            VpnSession.device_id == device_id,
            VpnSession.status == "active",
        )
    ).all()
    for row in rows:
        close_session(db, row, reason)


def start_session(
    db: Session,
    device: Device,
    client_public_key: str,
    requested_server_id: int | None = None,
    force_takeover: bool = False,
) -> tuple[VpnSession, VpnServer, int | None]:
    client_public_key = validate_public_key(client_public_key)
    user_id = device.user_id
    sub = active_subscription(db, user_id) if user_id else None
    premium = sub is not None

    # A device gets only one live lease at a time. This also makes reconnect/failover idempotent.
    close_active_for_device(db, device.id, "replaced_on_same_device")

    if premium and user_id:
        other = db.scalar(
            select(VpnSession).where(
                VpnSession.user_id == user_id,
                VpnSession.status == "active",
                VpnSession.device_id != device.id,
            ).order_by(VpnSession.id.desc())
        )
        if other:
            if not force_takeover:
                raise VpnBusinessError("premium_active_on_other_device")
            close_session(db, other, "premium_takeover")

    if not premium:
        remaining = remaining_free_seconds(db, device.id)
        if remaining <= 0:
            raise VpnBusinessError("no_free_time")
    else:
        remaining = None

    now = utcnow()
    if premium:
        expires_at = as_utc(sub.ends_at) if sub else None
    else:
        # Free credit also expires at local midnight; an active session cannot carry it over.
        by_credit = now.timestamp() + int(remaining or 0)
        expires_at = min(
            datetime.fromtimestamp(by_credit, tz=timezone.utc),
            next_local_midnight_utc(),
        )

    free_speed = int(get_json(db, "free_speed_mbps", settings.free_speed_mbps))
    boosted = free_speed_entitlement_mbps(db, user_id) if not premium else None
    effective_free_speed = max(free_speed, int(boosted or 0))

    try:
        candidates = choose_servers(db, premium=premium, requested_id=requested_server_id)
    except WireGuardError as exc:
        raise VpnBusinessError(str(exc)) from exc
    if not candidates:
        raise VpnBusinessError("no_server_capacity")

    # Manual Premium server selection is exact. Automatic selection may fail over across nodes.
    max_attempts = 1 if requested_server_id is not None else max(1, int(settings.vpn_connect_failover_attempts))
    last_error: str | None = None
    attempted = 0

    for server in candidates:
        if attempted >= max_attempts:
            break
        if premium and server.tier == "vip" and user_id and not has_server_access(db, user_id, server.country_code):
            if requested_server_id is not None:
                raise VpnBusinessError("vip_entitlement_required")
            continue
        attempted += 1
        client_ip: str | None = None
        try:
            if not (server.endpoint_host or "").strip():
                raise WireGuardError("server_endpoint_invalid")
            client_ip = allocate_client_ip(db, server)
            add_peer(
                server,
                client_public_key,
                client_ip,
                None if premium else max(1, effective_free_speed),
            )
            # Successful provisioning closes the circuit immediately.
            mark_server_healthy(db, server)

            session = VpnSession(
                device_id=device.id,
                user_id=user_id,
                server_id=server.id,
                client_public_key=client_public_key,
                client_ip=client_ip,
                is_premium=premium,
                expires_at=expires_at,
                status="active",
                reconnect_required=False,
            )
            db.add(session)
            try:
                db.commit()
            except Exception:
                db.rollback()
                remove_peer(server, client_public_key, client_ip)
                raise
            db.refresh(session)
            return session, server, remaining
        except WireGuardError as exc:
            last_error = str(exc)
            # Address-pool exhaustion is a capacity/configuration condition, not a node-health failure.
            if last_error != "server_address_pool_exhausted":
                # A shape failure may happen after wg peer creation; best-effort cleanup is safe.
                try:
                    if client_ip:
                        remove_peer(server, client_public_key, client_ip)
                except Exception:
                    pass
                mark_server_failure(db, server, last_error, mark_sessions=True)
                db.commit()
            if requested_server_id is not None:
                raise VpnBusinessError(last_error) from exc
            continue

    if attempted == 0 and premium:
        raise VpnBusinessError("no_accessible_server")
    raise VpnBusinessError("all_servers_unavailable" if last_error else "no_server_capacity")


def expire_due_sessions(db: Session) -> int:
    now = utcnow()
    heartbeat_timeout = max(60, int(settings.vpn_heartbeat_timeout_seconds))
    peer_grace = max(heartbeat_timeout, int(settings.vpn_peer_activity_grace_seconds))
    rows = db.scalars(select(VpnSession).where(VpnSession.status == "active")).all()
    expired: list[tuple[VpnSession, str]] = []
    for row in rows:
        expires_at = as_utc(row.expires_at) if row.expires_at else None
        heartbeat = as_utc(row.last_heartbeat_at) if row.last_heartbeat_at else as_utc(row.started_at)
        if expires_at and expires_at <= now:
            expired.append((row, "expired"))
            continue
        if heartbeat > now - timedelta(seconds=heartbeat_timeout):
            continue

        # The app heartbeat can pause briefly during Android lifecycle/network changes.
        # Do not tear down a healthy tunnel if WireGuard itself has handshaken recently.
        server = db.get(VpnServer, row.server_id)
        latest_handshake = peer_latest_handshake_at(server, row.client_public_key) if server else None
        if latest_handshake and latest_handshake > now - timedelta(seconds=peer_grace):
            continue
        expired.append((row, "heartbeat_timeout"))

    for row, reason in expired:
        close_session(db, row, reason)
    return len(expired)


def _parse_bootstrap_endpoint(value: str) -> tuple[str, int]:
    host = value.strip()
    port = 51820
    if ":" in host:
        h, maybe_port = host.rsplit(":", 1)
        if maybe_port.isdigit():
            host, port = h.strip(), int(maybe_port)
    if not host:
        raise VpnBusinessError("bootstrap_server_endpoint_missing_host")
    return host, port


def bootstrap_server(db: Session) -> None:
    if not settings.bootstrap_server_endpoint or not settings.bootstrap_server_public_key:
        return

    host, port = _parse_bootstrap_endpoint(settings.bootstrap_server_endpoint)
    public_key = validate_public_key(settings.bootstrap_server_public_key)

    # Bootstrap is idempotent and may repair/update the original automatically-created node.
    # Prefer an exact name match, then the same public key. Never overwrite an unrelated
    # admin-created node merely because it happens to be first/default.
    existing = db.scalar(
        select(VpnServer).where(VpnServer.name == settings.bootstrap_server_name).order_by(VpnServer.id.asc())
    )
    if not existing:
        existing = db.scalar(
            select(VpnServer).where(VpnServer.public_key == public_key).order_by(VpnServer.id.asc())
        )

    if existing:
        existing.country_code = settings.bootstrap_server_country
        existing.city = settings.bootstrap_server_city
        existing.endpoint_host = host
        existing.endpoint_port = port
        existing.public_key = public_key
        existing.dns = settings.wireguard_default_dns
        existing.client_cidr = settings.bootstrap_server_client_cidr
        existing.tier = "free"
        existing.is_default = True
        existing.is_active = True
        db.commit()
        return

    any_server = db.scalar(select(VpnServer.id).limit(1))
    if any_server is not None:
        # Once operators have created nodes manually, bootstrap should not silently add another one.
        return

    row = VpnServer(
        name=settings.bootstrap_server_name,
        country_code=settings.bootstrap_server_country,
        city=settings.bootstrap_server_city,
        endpoint_host=host,
        endpoint_port=port,
        public_key=public_key,
        dns=settings.wireguard_default_dns,
        client_cidr=settings.bootstrap_server_client_cidr,
        tier="free",
        is_default=True,
        is_active=True,
    )
    db.add(row)
    db.commit()
