#!/usr/bin/env bash
set -euo pipefail
# Usage: add_peer.sh <client_public_key> <client_ip_without_cidr>
PUB=${1:?public key required}
IP=${2:?client IP required}
wg set wg0 peer "$PUB" allowed-ips "$IP/32" persistent-keepalive 25
echo "peer added: $IP"
