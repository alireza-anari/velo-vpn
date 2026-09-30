#!/usr/bin/env bash
set -euo pipefail

NAME=""
COUNTRY=""
CITY=""
PUBLIC_IP=""
CENTRAL_API_IP=""
CLIENT_CIDR=""
MAX_SESSIONS="200"
REPO_REF="${VELO_REPO_REF:-main}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --country) COUNTRY="$2"; shift 2 ;;
    --city) CITY="$2"; shift 2 ;;
    --public-ip) PUBLIC_IP="$2"; shift 2 ;;
    --central-api-ip) CENTRAL_API_IP="$2"; shift 2 ;;
    --cidr) CLIENT_CIDR="$2"; shift 2 ;;
    --max-sessions) MAX_SESSIONS="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ $EUID -eq 0 ]] || { echo "run with sudo/root" >&2; exit 2; }
for v in NAME COUNTRY CITY PUBLIC_IP CENTRAL_API_IP CLIENT_CIDR; do
  [[ -n "${!v}" ]] || { echo "missing --${v,,}" >&2; exit 2; }
done

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y wireguard iproute2 iptables python3-venv python3-pip ufw curl ca-certificates openssl

id velo-agent >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin velo-agent
install -d -m 755 /opt/velo/wireguard /opt/velo/node-agent
install -d -m 750 -o root -g velo-agent /etc/velo

RAW="https://raw.githubusercontent.com/alireza-anari/velo-vpn/${REPO_REF}"
curl -fsSL "$RAW/infra/wireguard/add_peer.sh" -o /opt/velo/wireguard/add_peer.sh
curl -fsSL "$RAW/infra/wireguard/remove_peer.sh" -o /opt/velo/wireguard/remove_peer.sh
curl -fsSL "$RAW/infra/wireguard/shape_peer.sh" -o /opt/velo/wireguard/shape_peer.sh
curl -fsSL "$RAW/infra/wireguard/unshape_peer.sh" -o /opt/velo/wireguard/unshape_peer.sh
curl -fsSL "$RAW/infra/wireguard/install.sh" -o /opt/velo/wireguard/install.sh
chmod 750 /opt/velo/wireguard/*.sh

curl -fsSL "$RAW/infra/node-agent/app.py" -o /opt/velo/node-agent/app.py
curl -fsSL "$RAW/infra/node-agent/requirements.txt" -o /opt/velo/node-agent/requirements.txt
curl -fsSL "$RAW/infra/node-agent/velo-node-agent.service" -o /etc/systemd/system/velo-node-agent.service
curl -fsSL "$RAW/infra/node-agent/velo-node-agent-sudoers" -o /etc/sudoers.d/velo-node-agent
chmod 440 /etc/sudoers.d/velo-node-agent
visudo -cf /etc/sudoers.d/velo-node-agent

python3 -m venv /opt/velo/node-agent/.venv
/opt/velo/node-agent/.venv/bin/pip install --upgrade pip
/opt/velo/node-agent/.venv/bin/pip install -r /opt/velo/node-agent/requirements.txt
chown -R velo-agent:velo-agent /opt/velo/node-agent

WG_ADDRESS="$(python3 - "$CLIENT_CIDR" <<'PY'
import ipaddress,sys
n=ipaddress.ip_network(sys.argv[1], strict=False)
print(str(next(n.hosts())) + "/" + str(n.prefixlen))
PY
)"

WG_ADDRESS="$WG_ADDRESS" WG_CLIENT_CIDR="$CLIENT_CIDR" WG_PORT=51820 /opt/velo/wireguard/install.sh

AGENT_TOKEN="$(openssl rand -hex 32)"
cat >/etc/velo/node-agent.env <<EOF
VELO_AGENT_KEY=$AGENT_TOKEN
WIREGUARD_INTERFACE=wg0
WIREGUARD_SCRIPT_DIR=/opt/velo/wireguard
WIREGUARD_USE_SUDO=true
VELO_CLIENT_CIDR=$CLIENT_CIDR
EOF
chown root:velo-agent /etc/velo/node-agent.env
chmod 640 /etc/velo/node-agent.env

ufw allow 51820/udp
ufw allow from "$CENTRAL_API_IP" to any port 8787 proto tcp
ufw --force enable

systemctl daemon-reload
systemctl enable --now wg-quick@wg0
systemctl enable --now velo-node-agent
sleep 2

curl -fsS -H "X-Velo-Agent-Key: $AGENT_TOKEN" http://127.0.0.1:8787/health >/dev/null

PUBKEY="$(cat /etc/wireguard/wg0.pub)"
echo
echo "============================================================"
echo "Velo node is ready. Copy these values into Velo Admin:"
echo "Name: $NAME"
echo "Country: $COUNTRY"
echo "City: $CITY"
echo "Endpoint Host: $PUBLIC_IP"
echo "Endpoint Port: 51820"
echo "Public Key: $PUBKEY"
echo "Client CIDR: $CLIENT_CIDR"
echo "Tier: premium"
echo "Max Sessions: $MAX_SESSIONS"
echo "Agent URL: http://$PUBLIC_IP:8787"
echo "Agent Token: $AGENT_TOKEN"
echo "============================================================"
echo
echo "Keep Agent Token private. It grants node-control access."
