#!/usr/bin/env bash
set -euo pipefail
# Per-client Free-tier shaping.
# Usage: shape_peer.sh <client_ip> <mbit>
# Download is shaped on wg0 egress; upload is policed on wg0 ingress.

WG_INTERFACE="${WIREGUARD_INTERFACE:-wg0}"
IP=${1:?client ip required}
RATE=${2:?rate mbit required}

[[ "$IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || { echo "invalid client ip" >&2; exit 2; }
[[ "$RATE" =~ ^[0-9]+$ ]] || { echo "invalid rate" >&2; exit 2; }
(( RATE >= 1 && RATE <= 10000 )) || { echo "rate out of range" >&2; exit 2; }

ID=$(awk -F. '{print $4}' <<<"$IP")
(( ID >= 1 && ID <= 254 )) || { echo "unsupported client ip" >&2; exit 2; }
CLASS=$((100 + ID))
PREF=$((1000 + ID))

# Shared HTB root. Explicit quantum/burst avoids the large-quantum warning and
# gives low-rate classes enough burst for high-latency VPN paths.
if ! tc qdisc show dev "$WG_INTERFACE" | grep -q 'htb 1:'; then
  tc qdisc add dev "$WG_INTERFACE" root handle 1: htb default 999 r2q 10
fi

tc class replace dev "$WG_INTERFACE" parent 1: classid 1:999 \
  htb rate 1000mbit ceil 1000mbit burst 256k cburst 256k quantum 1514

tc class replace dev "$WG_INTERFACE" parent 1: classid "1:${CLASS}" \
  htb rate "${RATE}mbit" ceil "${RATE}mbit" burst 64k cburst 64k quantum 1514

# A small fq_codel queue keeps interactive traffic responsive while capped.
tc qdisc replace dev "$WG_INTERFACE" parent "1:${CLASS}" handle "${CLASS}:" fq_codel

# Download to peer: packets leave wg0 with the client VPN IP as destination.
tc filter replace dev "$WG_INTERFACE" protocol ip parent 1: prio "$PREF" \
  u32 match ip dst "$IP/32" flowid "1:${CLASS}"

# Upload from peer: police traffic as it enters wg0. This is intentionally a policer
# rather than a queue; a future IFB implementation can replace it if smoother upload
# shaping is required.
if ! tc qdisc show dev "$WG_INTERFACE" | grep -q 'ingress ffff:'; then
  tc qdisc add dev "$WG_INTERFACE" handle ffff: ingress
fi

tc filter replace dev "$WG_INTERFACE" parent ffff: protocol ip prio "$PREF" \
  u32 match ip src "$IP/32" \
  police rate "${RATE}mbit" burst 512k drop flowid :1

echo "shaped $IP to ${RATE}mbit"
