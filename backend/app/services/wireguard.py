from __future__ import annotations

import base64
import ipaddress
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import VpnServer, VpnSession
from .time_utils import as_utc, utcnow

_WG_KEY_RE = re.compile(r"^[A-Za-z0-9+/]{43}=$")


class WireGuardError(RuntimeError):
    pass


def validate_public_key(value: str) -> str:
    value = value.strip()
    if not _WG_KEY_RE.match(value):
        raise ValueError("invalid_wireguard_public_key")
    try:
        raw = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError("invalid_wireguard_public_key") from exc
    if len(raw) != 32:
        raise ValueError("invalid_wireguard_public_key")
    return value


def _script(name: str) -> str:
    path = Path(settings.wireguard_script_dir) / name
    return str(path)


def _run(args: list[str], check: bool = True, privileged: bool = False) -> subprocess.CompletedProcess[str]:
    command = list(args)
    if privileged and settings.wireguard_use_sudo:
        command = ["sudo", "-n", *command]
    return subprocess.run(command, text=True, capture_output=True, check=check, timeout=15)


def _agent_json(server: VpnServer, method: str, path: str, payload: dict | None = None) -> dict:
    if not server.agent_url:
        raise WireGuardError("node_agent_not_configured")
    url = f"{server.agent_url.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if server.agent_token:
        req.add_header("X-Velo-Agent-Key", server.agent_token)
    try:
        with urlopen(req, timeout=8) as resp:  # noqa: S310 - URL is admin-controlled infrastructure
            raw = resp.read(1024 * 1024)
            return json.loads(raw.decode("utf-8")) if raw else {}
    except HTTPError as exc:
        try:
            detail = exc.read(4096).decode("utf-8", "replace")
        except Exception:
            detail = ""
        raise WireGuardError(f"node_agent_http_{exc.code}:{detail[:200]}") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise WireGuardError(f"node_agent_unavailable:{exc}") from exc


def node_health(server: VpnServer) -> dict:
    if server.agent_url:
        return _agent_json(server, "GET", "/health")
    if not settings.wireguard_manage_local:
        return {"ok": True, "mode": "dry", "interface": settings.wireguard_interface}
    try:
        cp = _run(["wg", "show", settings.wireguard_interface], privileged=True)
        return {"ok": cp.returncode == 0, "mode": "local", "interface": settings.wireguard_interface}
    except (subprocess.SubprocessError, OSError) as exc:
        raise WireGuardError(f"local_node_unhealthy:{exc}") from exc


def mark_server_healthy(db: Session, server: VpnServer) -> None:
    server.last_health_at = utcnow()
    server.health_state = "healthy"
    server.health_failures = 0
    server.last_health_error = None
    server.unhealthy_until = None
    db.flush()


def mark_server_failure(db: Session, server: VpnServer, error: str, mark_sessions: bool = True) -> None:
    from datetime import timedelta

    server.last_health_at = utcnow()
    server.health_failures = int(server.health_failures or 0) + 1
    server.last_health_error = str(error)[:1000]
    threshold = max(1, int(settings.node_health_failure_threshold))
    if server.health_failures >= threshold:
        server.health_state = "unhealthy"
        server.unhealthy_until = utcnow() + timedelta(seconds=max(15, int(settings.node_circuit_breaker_seconds)))
        if mark_sessions:
            rows = db.scalars(
                select(VpnSession).where(
                    VpnSession.server_id == server.id,
                    VpnSession.status == "active",
                )
            ).all()
            for row in rows:
                row.reconnect_required = True
    else:
        server.health_state = "degraded"
    db.flush()


def check_server_health(db: Session, server: VpnServer) -> dict:
    try:
        result = node_health(server)
        if not bool(result.get("ok")):
            raise WireGuardError("node_health_reported_not_ok")
        mark_server_healthy(db, server)
        db.commit()
        return result
    except Exception as exc:
        mark_server_failure(db, server, str(exc), mark_sessions=True)
        db.commit()
        raise WireGuardError(str(exc)) from exc


def check_all_servers(db: Session) -> dict:
    rows = db.scalars(select(VpnServer).where(VpnServer.is_active == True)).all()  # noqa: E712
    healthy = 0
    failed = 0
    for server in rows:
        try:
            check_server_health(db, server)
            healthy += 1
        except WireGuardError:
            failed += 1
    return {"checked": len(rows), "healthy": healthy, "failed": failed}


def add_peer(server: VpnServer, public_key: str, client_ip: str, free_speed_mbps: int | None) -> None:
    if server.agent_url:
        _agent_json(
            server,
            "POST",
            "/v1/peers",
            {"public_key": public_key, "client_ip": client_ip, "speed_mbps": free_speed_mbps},
        )
        return
    if not settings.wireguard_manage_local:
        return
    try:
        _run([_script("add_peer.sh"), public_key, client_ip], privileged=True)
        if free_speed_mbps:
            _run([_script("shape_peer.sh"), client_ip, str(free_speed_mbps)], privileged=True)
    except (subprocess.SubprocessError, OSError) as exc:
        raise WireGuardError(f"peer_provision_failed:{exc}") from exc


def remove_peer(server: VpnServer, public_key: str, client_ip: str) -> None:
    if server.agent_url:
        try:
            _agent_json(
                server,
                "POST",
                "/v1/peers/remove",
                {"public_key": public_key, "client_ip": client_ip},
            )
        except WireGuardError:
            # Cleanup is best-effort so a temporarily unreachable node does not trap a DB session forever.
            pass
        return
    if not settings.wireguard_manage_local:
        return
    try:
        _run([_script("unshape_peer.sh"), client_ip], check=False, privileged=True)
        _run([_script("remove_peer.sh"), public_key], check=False, privileged=True)
    except (subprocess.SubprocessError, OSError):
        return


def peer_latest_handshake_at(server: VpnServer, public_key: str) -> datetime | None:
    """Return the most recent WireGuard handshake timestamp for one peer, if any."""
    if server.agent_url:
        try:
            body = _agent_json(server, "POST", "/v1/peers/transfer", {"public_key": public_key})
            epoch = int(body.get("latest_handshake_epoch", 0) or 0)
            return datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch > 0 else None
        except (WireGuardError, TypeError, ValueError, OSError):
            return None
    if not settings.wireguard_manage_local:
        return None
    try:
        cp = _run(["wg", "show", settings.wireguard_interface, "latest-handshakes"], privileged=True)
    except (subprocess.SubprocessError, OSError):
        return None
    for line in cp.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].strip() == public_key:
            try:
                epoch = int(parts[1])
            except ValueError:
                return None
            return datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch > 0 else None
    return None


def peer_transfer(server: VpnServer, public_key: str) -> tuple[int, int]:
    """Return (rx_bytes, tx_bytes) from the VPN node's point of view."""
    if server.agent_url:
        try:
            body = _agent_json(server, "POST", "/v1/peers/transfer", {"public_key": public_key})
            return int(body.get("rx_bytes", 0)), int(body.get("tx_bytes", 0))
        except (WireGuardError, TypeError, ValueError):
            return 0, 0
    if not settings.wireguard_manage_local:
        return 0, 0
    try:
        cp = _run(["wg", "show", settings.wireguard_interface, "transfer"], privileged=True)
    except (subprocess.SubprocessError, OSError):
        return 0, 0
    for line in cp.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].strip() == public_key:
            try:
                return int(parts[1]), int(parts[2])
            except ValueError:
                return 0, 0
    return 0, 0


def list_peers(server: VpnServer) -> list[dict]:
    """Return WireGuard peer keys and allowed IPs for reconciliation."""
    if server.agent_url:
        body = _agent_json(server, "GET", "/v1/peers")
        rows = body.get("peers", [])
        if not isinstance(rows, list):
            raise WireGuardError("invalid_node_peer_list")
        return [x for x in rows if isinstance(x, dict)]
    if not settings.wireguard_manage_local:
        return []
    try:
        cp = _run(["wg", "show", settings.wireguard_interface, "allowed-ips"], privileged=True)
    except (subprocess.SubprocessError, OSError) as exc:
        raise WireGuardError(f"peer_list_failed:{exc}") from exc
    rows: list[dict] = []
    for line in cp.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        allowed = [x.strip() for x in parts[1].split(",") if x.strip() and x.strip() != "(none)"]
        rows.append({"public_key": parts[0].strip(), "allowed_ips": allowed})
    return rows


def allocate_client_ip(db: Session, server: VpnServer) -> str:
    network = ipaddress.ip_network(server.client_cidr, strict=False)
    if network.version != 4:
        raise WireGuardError("only_ipv4_client_cidr_supported_in_mvp")

    active_ips = set(
        db.scalars(
            select(VpnSession.client_ip).where(
                VpnSession.server_id == server.id,
                VpnSession.status == "active",
            )
        ).all()
    )

    # First usable IP is reserved for wg0 server itself. Start from the second host.
    hosts = list(network.hosts())
    for addr in hosts[1:]:
        ip = str(addr)
        if ip not in active_ips:
            return ip
    raise WireGuardError("server_address_pool_exhausted")


def active_session_count(db: Session, server_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(VpnSession.id)).where(
                VpnSession.server_id == server_id,
                VpnSession.status == "active",
            )
        )
        or 0
    )


def _circuit_open(server: VpnServer) -> bool:
    if not server.unhealthy_until:
        return False
    try:
        return as_utc(server.unhealthy_until) > utcnow()
    except Exception:
        return False


def choose_servers(
    db: Session,
    premium: bool,
    requested_id: int | None = None,
    exclude_ids: set[int] | None = None,
) -> list[VpnServer]:
    exclude_ids = exclude_ids or set()
    if requested_id is not None:
        server = db.get(VpnServer, requested_id)
        if not server or not server.is_active or server.id in exclude_ids:
            raise WireGuardError("server_unavailable")
        if not premium and server.tier != "free":
            raise WireGuardError("premium_required")
        if _circuit_open(server):
            raise WireGuardError("server_temporarily_unhealthy")
        if active_session_count(db, server.id) >= server.max_sessions:
            raise WireGuardError("server_capacity_reached")
        return [server]

    rows = db.scalars(
        select(VpnServer)
        .where(VpnServer.is_active == True)  # noqa: E712
        .order_by(VpnServer.is_default.desc(), VpnServer.id.asc())
    ).all()
    eligible = [s for s in rows if (premium or s.tier == "free") and s.id not in exclude_ids and not _circuit_open(s)]

    # Least-loaded ratio wins. Healthy/unknown nodes are preferred to degraded nodes.
    candidates: list[tuple[int, float, int, int, VpnServer]] = []
    for server in eligible:
        count = active_session_count(db, server.id)
        if count < server.max_sessions:
            health_rank = 1 if server.health_state == "degraded" else 0
            ratio = count / max(1, server.max_sessions)
            candidates.append((health_rank, ratio, 0 if server.is_default else 1, server.id, server))
    candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return [x[4] for x in candidates]


def choose_server(db: Session, premium: bool, requested_id: int | None = None) -> VpnServer:
    rows = choose_servers(db, premium=premium, requested_id=requested_id)
    if rows:
        return rows[0]
    raise WireGuardError("no_server_capacity")


def _managed_ip_from_peer(server: VpnServer, peer: dict) -> str | None:
    try:
        network = ipaddress.ip_network(server.client_cidr, strict=False)
    except ValueError:
        return None
    for item in peer.get("allowed_ips", []) or []:
        try:
            iface = ipaddress.ip_interface(str(item))
        except ValueError:
            continue
        if iface.ip in network:
            return str(iface.ip)
    return None


def reconcile_server_peers(db: Session, server: VpnServer) -> dict:
    """Remove managed orphan peers and flag DB sessions whose peer disappeared.

    Only peers with an AllowedIP inside this server's client CIDR are considered Velo-managed,
    so manually configured infrastructure peers are left untouched.
    """
    if not server.agent_url and not settings.wireguard_manage_local:
        return {"server_id": server.id, "skipped": True, "removed_orphans": 0, "missing_sessions": 0}

    actual = list_peers(server)
    active = db.scalars(
        select(VpnSession).where(VpnSession.server_id == server.id, VpnSession.status == "active")
    ).all()
    expected = {row.client_public_key: row for row in active}
    actual_keys: set[str] = set()
    removed = 0

    for peer in actual:
        key = str(peer.get("public_key", "")).strip()
        if not key:
            continue
        managed_ip = _managed_ip_from_peer(server, peer)
        if managed_ip is None:
            continue
        actual_keys.add(key)
        if key not in expected:
            remove_peer(server, key, managed_ip)
            removed += 1

    missing = 0
    for key, session in expected.items():
        if key not in actual_keys:
            session.reconnect_required = True
            missing += 1
    if missing:
        db.commit()
    return {
        "server_id": server.id,
        "skipped": False,
        "removed_orphans": removed,
        "missing_sessions": missing,
        "actual_managed_peers": len(actual_keys),
        "expected_sessions": len(expected),
    }


def reconcile_all_servers(db: Session) -> dict:
    rows = db.scalars(select(VpnServer).where(VpnServer.is_active == True)).all()  # noqa: E712
    results = []
    failures = 0
    for server in rows:
        try:
            results.append(reconcile_server_peers(db, server))
        except WireGuardError as exc:
            failures += 1
            results.append({"server_id": server.id, "error": str(exc)})
    return {"servers": results, "failures": failures}
