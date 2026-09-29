from __future__ import annotations

import base64
import ipaddress
import os
import re
import subprocess
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Velo Node Agent", docs_url=None, redoc_url=None)

AGENT_KEY = os.getenv("VELO_AGENT_KEY", "")
WG_INTERFACE = os.getenv("WIREGUARD_INTERFACE", "wg0")
SCRIPT_DIR = Path(os.getenv("WIREGUARD_SCRIPT_DIR", "/opt/velo/wireguard"))
USE_SUDO = os.getenv("WIREGUARD_USE_SUDO", "true").lower() in {"1", "true", "yes"}
CLIENT_CIDR = os.getenv("VELO_CLIENT_CIDR", "10.77.0.0/24")
KEY_RE = re.compile(r"^[A-Za-z0-9+/]{43}=$")


class PeerIn(BaseModel):
    public_key: str = Field(min_length=44, max_length=44)
    client_ip: str = Field(min_length=7, max_length=64)
    speed_mbps: int | None = Field(default=None, ge=1, le=10000)


class PeerRemove(BaseModel):
    public_key: str = Field(min_length=44, max_length=44)
    client_ip: str = Field(min_length=7, max_length=64)


class TransferIn(BaseModel):
    public_key: str = Field(min_length=44, max_length=44)


def auth(x_velo_agent_key: str | None):
    import secrets
    if not AGENT_KEY or not x_velo_agent_key or not secrets.compare_digest(x_velo_agent_key, AGENT_KEY):
        raise HTTPException(401, "invalid_agent_key")


def validate_key(value: str):
    if not KEY_RE.match(value):
        raise HTTPException(400, "invalid_wireguard_public_key")
    try:
        raw = base64.b64decode(value, validate=True)
    except Exception:
        raise HTTPException(400, "invalid_wireguard_public_key")
    if len(raw) != 32:
        raise HTTPException(400, "invalid_wireguard_public_key")


def validate_ip(value: str) -> str:
    try:
        ip = ipaddress.ip_address(value)
        network = ipaddress.ip_network(CLIENT_CIDR, strict=False)
    except ValueError:
        raise HTTPException(400, "invalid_client_ip")
    if ip.version != 4 or ip not in network or ip in {network.network_address, network.broadcast_address}:
        raise HTTPException(400, "client_ip_outside_managed_cidr")
    server_ip = next(network.hosts(), None)
    if server_ip is not None and ip == server_ip:
        raise HTTPException(400, "client_ip_reserved")
    return str(ip)


def run(args: list[str], check: bool = True):
    command = list(args)
    if USE_SUDO:
        command = ["sudo", "-n", *command]
    try:
        return subprocess.run(command, text=True, capture_output=True, check=check, timeout=12)
    except subprocess.CalledProcessError as exc:
        raise HTTPException(500, f"command_failed:{exc.stderr[-300:]}")
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(500, f"command_failed:{exc}")


def script(name: str) -> str:
    path = SCRIPT_DIR / name
    if not path.is_file():
        raise HTTPException(500, f"missing_helper:{name}")
    return str(path)


def _peer_rows() -> list[dict]:
    cp = run(["wg", "show", WG_INTERFACE, "allowed-ips"])
    rows: list[dict] = []
    for line in cp.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        allowed = [x.strip() for x in parts[1].split(",") if x.strip() and x.strip() != "(none)"]
        rows.append({"public_key": parts[0].strip(), "allowed_ips": allowed})
    return rows


@app.get("/health")
def health(x_velo_agent_key: str | None = Header(default=None)):
    auth(x_velo_agent_key)
    cp = run(["wg", "show", WG_INTERFACE], check=False)
    if cp.returncode != 0:
        return {"ok": False, "interface": WG_INTERFACE, "peer_count": 0}
    try:
        peer_count = len(_peer_rows())
    except HTTPException:
        peer_count = 0
    return {"ok": True, "interface": WG_INTERFACE, "peer_count": peer_count}


@app.get("/v1/peers")
def peers(x_velo_agent_key: str | None = Header(default=None)):
    auth(x_velo_agent_key)
    return {"peers": _peer_rows()}


@app.post("/v1/peers")
def add_peer(payload: PeerIn, x_velo_agent_key: str | None = Header(default=None)):
    auth(x_velo_agent_key)
    validate_key(payload.public_key)
    client_ip = validate_ip(payload.client_ip)
    run([script("add_peer.sh"), payload.public_key, client_ip])
    if payload.speed_mbps:
        run([script("shape_peer.sh"), client_ip, str(payload.speed_mbps)])
    return {"ok": True}


@app.post("/v1/peers/remove")
def remove_peer(payload: PeerRemove, x_velo_agent_key: str | None = Header(default=None)):
    auth(x_velo_agent_key)
    validate_key(payload.public_key)
    client_ip = validate_ip(payload.client_ip)
    run([script("unshape_peer.sh"), client_ip], check=False)
    run([script("remove_peer.sh"), payload.public_key], check=False)
    return {"ok": True}


@app.post("/v1/peers/transfer")
def transfer(payload: TransferIn, x_velo_agent_key: str | None = Header(default=None)):
    auth(x_velo_agent_key)
    validate_key(payload.public_key)

    rx_bytes = 0
    tx_bytes = 0
    cp = run(["wg", "show", WG_INTERFACE, "transfer"])
    for line in cp.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].strip() == payload.public_key:
            try:
                rx_bytes = int(parts[1])
                tx_bytes = int(parts[2])
            except ValueError:
                pass
            break

    latest_handshake_epoch = 0
    hs = run(["wg", "show", WG_INTERFACE, "latest-handshakes"])
    for line in hs.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].strip() == payload.public_key:
            try:
                latest_handshake_epoch = int(parts[1])
            except ValueError:
                pass
            break

    return {
        "rx_bytes": rx_bytes,
        "tx_bytes": tx_bytes,
        "latest_handshake_epoch": latest_handshake_epoch,
    }
