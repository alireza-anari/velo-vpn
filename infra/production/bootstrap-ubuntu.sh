#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "run as root" >&2; exit 2; }
SSH_PORT="${SSH_PORT:-22}"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y wireguard iproute2 iptables python3-venv nginx postgresql-client ufw curl ca-certificates

id velo >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin velo
mkdir -p /opt/velo/{backend,wireguard,backup} /var/backups/velo /etc/velo
chown -R velo:velo /opt/velo/backend /opt/velo/backup /var/backups/velo
chmod 700 /var/backups/velo /etc/velo

cat >/etc/sysctl.d/99-velo.conf <<SYSCTL
net.ipv4.ip_forward=1
net.ipv4.conf.all.src_valid_mark=1
SYSCTL
sysctl --system >/dev/null

ufw allow "${SSH_PORT}/tcp"
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 51820/udp
ufw --force enable

echo "Base host prepared. Copy Velo files, configure /opt/velo/backend/.env and WireGuard, then follow docs/DEPLOYMENT.md."
