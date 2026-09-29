#!/usr/bin/env bash
set -euo pipefail
WG_INTERFACE="${WIREGUARD_INTERFACE:-wg0}"
IP=${1:?client ip required}
ID=$(awk -F. '{print $4}' <<<"$IP")
CLASS=$((100 + ID))
PREF=$((1000 + ID))

tc filter del dev "$WG_INTERFACE" protocol ip parent 1: prio "$PREF" 2>/dev/null || true
tc qdisc del dev "$WG_INTERFACE" parent "1:${CLASS}" 2>/dev/null || true
tc class del dev "$WG_INTERFACE" parent 1: classid "1:${CLASS}" 2>/dev/null || true
tc filter del dev "$WG_INTERFACE" parent ffff: protocol ip prio "$PREF" 2>/dev/null || true
