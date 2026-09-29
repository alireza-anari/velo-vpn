#!/usr/bin/env bash
set -euo pipefail
PUB=${1:?public key required}
wg set wg0 peer "$PUB" remove
