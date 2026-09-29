#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "run as root" >&2; exit 1; fi

WG_INTERFACE="${WG_INTERFACE:-wg0}"
WG_ADDRESS="${WG_ADDRESS:-10.77.0.1/24}"
WG_CLIENT_CIDR="${WG_CLIENT_CIDR:-10.77.0.0/24}"
WG_PORT="${WG_PORT:-51820}"
WAN_INTERFACE="${WAN_INTERFACE:-$(ip -4 route show default | awk '/default/ {print $5; exit}')}"

[[ -n "$WAN_INTERFACE" ]] || { echo "could not detect WAN interface" >&2; exit 2; }

apt-get update
apt-get install -y wireguard iproute2 iptables
install -d -m 700 /etc/wireguard
KEY_FILE="/etc/wireguard/${WG_INTERFACE}.key"
PUB_FILE="/etc/wireguard/${WG_INTERFACE}.pub"
CONF_FILE="/etc/wireguard/${WG_INTERFACE}.conf"
if [[ ! -f "$KEY_FILE" ]]; then
  umask 077
  wg genkey | tee "$KEY_FILE" | wg pubkey > "$PUB_FILE"
fi
PRIV=$(cat "$KEY_FILE")
cat >"$CONF_FILE" <<CFG
[Interface]
Address = ${WG_ADDRESS}
ListenPort = ${WG_PORT}
PrivateKey = ${PRIV}
PostUp = sysctl -w net.ipv4.ip_forward=1; iptables -C FORWARD -i %i -o ${WAN_INTERFACE} -j ACCEPT 2>/dev/null || iptables -I FORWARD 1 -i %i -o ${WAN_INTERFACE} -j ACCEPT; iptables -C FORWARD -i ${WAN_INTERFACE} -o %i -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || iptables -I FORWARD 1 -i ${WAN_INTERFACE} -o %i -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT; iptables -t nat -C POSTROUTING -s ${WG_CLIENT_CIDR} -o ${WAN_INTERFACE} -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -s ${WG_CLIENT_CIDR} -o ${WAN_INTERFACE} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -o ${WAN_INTERFACE} -j ACCEPT 2>/dev/null || true; iptables -D FORWARD -i ${WAN_INTERFACE} -o %i -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true; iptables -t nat -D POSTROUTING -s ${WG_CLIENT_CIDR} -o ${WAN_INTERFACE} -j MASQUERADE 2>/dev/null || true
CFG
chmod 600 "$CONF_FILE" "$KEY_FILE"
systemctl enable --now "wg-quick@${WG_INTERFACE}"
echo "WireGuard interface: ${WG_INTERFACE}"
echo "WAN interface: ${WAN_INTERFACE}"
echo "Client CIDR: ${WG_CLIENT_CIDR}"
echo "Set VpnServer.client_cidr and the node agent VELO_CLIENT_CIDR to WG_CLIENT_CIDR."
echo "Server public key: $(cat "$PUB_FILE")"
