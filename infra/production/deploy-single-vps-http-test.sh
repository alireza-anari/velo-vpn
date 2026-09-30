#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "run as root" >&2; exit 2; }

PUBLIC_IP="${PUBLIC_IP:-185.19.33.72}"
REPO_URL="${VELO_REPO_URL:-https://github.com/alireza-anari/velo-vpn.git}"
REPO_REF="${VELO_REPO_REF:-web-mvp-phase-2}"
SOURCE_DIR="/opt/velo/source"
BACKEND_DIR="/opt/velo/backend"
WEB_ROOT="/var/www/velo"
SSH_PORT="${VELO_SSH_PORT:-22}"

[[ "$PUBLIC_IP" =~ ^[0-9a-fA-F:.]+$ ]] || { echo "invalid PUBLIC_IP" >&2; exit 2; }
[[ "$SSH_PORT" =~ ^[0-9]+$ ]] && (( SSH_PORT >= 1 && SSH_PORT <= 65535 )) || {
  echo "invalid SSH port" >&2
  exit 2
}

if ! wg show wg0 >/dev/null 2>&1; then
  echo "wg0 is not active; provision the VPN node first" >&2
  exit 3
fi
[[ -s /etc/wireguard/wg0.pub ]] || { echo "missing /etc/wireguard/wg0.pub" >&2; exit 3; }

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y   git rsync nginx postgresql postgresql-client   python3-venv python3-pip nodejs npm   curl ca-certificates openssl sudo ufw

id velo >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin velo
install -d -m 755 /opt/velo "$SOURCE_DIR" "$BACKEND_DIR" "$WEB_ROOT"
install -d -m 700 /etc/velo
install -d -m 755 -o velo -g velo "$BACKEND_DIR/uploads"

# Fetch exactly the requested ref. This works with branches/tags and keeps deployment repeatable.
if [[ ! -d "$SOURCE_DIR/.git" ]]; then
  rm -rf "$SOURCE_DIR"
  git clone "$REPO_URL" "$SOURCE_DIR"
fi
git -C "$SOURCE_DIR" fetch --prune origin
git -C "$SOURCE_DIR" checkout --force "$REPO_REF" 2>/dev/null || {
  git -C "$SOURCE_DIR" fetch origin "$REPO_REF"
  git -C "$SOURCE_DIR" checkout --force FETCH_HEAD
}
git -C "$SOURCE_DIR" reset --hard "origin/$REPO_REF" 2>/dev/null || true

# Backend code is deployed separately so secrets/uploads/venv survive code refreshes.
rsync -a --delete   --exclude '.env'   --exclude '.venv'   --exclude 'uploads/'   "$SOURCE_DIR/backend/" "$BACKEND_DIR/"

python3 -m venv "$BACKEND_DIR/.venv"
"$BACKEND_DIR/.venv/bin/pip" install --upgrade pip
"$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

systemctl enable --now postgresql

ENV_FILE="$BACKEND_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  DB_PASSWORD="$(openssl rand -hex 32)"
  JWT_SECRET="$(openssl rand -hex 48)"
  METRICS_TOKEN="$(openssl rand -hex 32)"
  ADMIN_API_KEY="$(openssl rand -hex 32)"
  ADMIN_PANEL_PASSWORD="$(openssl rand -hex 24)"
  WG_PUBLIC_KEY="$(cat /etc/wireguard/wg0.pub)"

  if runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='velo'" | grep -q 1; then
    runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "ALTER ROLE velo WITH LOGIN PASSWORD '$DB_PASSWORD';"
  else
    runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE ROLE velo WITH LOGIN PASSWORD '$DB_PASSWORD';"
  fi

  if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='velo'" | grep -q 1; then
    runuser -u postgres -- createdb -O velo velo
  fi

  cat >"$ENV_FILE" <<EOF
DATABASE_URL=postgresql+psycopg://velo:$DB_PASSWORD@127.0.0.1:5432/velo
JWT_SECRET=$JWT_SECRET
ENVIRONMENT=development
PUBLIC_BASE_URL=http://$PUBLIC_IP
UPLOAD_DIR=$BACKEND_DIR/uploads
AUTO_SCHEMA_CREATE=false
LOG_LEVEL=INFO
LOG_JSON=true
METRICS_ENABLED=true
METRICS_BEARER_TOKEN=$METRICS_TOKEN
READINESS_REQUIRE_VPN_SERVER=true
ADMIN_API_KEY=$ADMIN_API_KEY
ADMIN_PANEL_PASSWORD=$ADMIN_PANEL_PASSWORD
ADMIN_SESSION_HOURS=12

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
ADMIN_NOTIFICATION_EMAIL=
LEGAL_CONTACT_EMAIL=support@example.com
LEGAL_EFFECTIVE_DATE=2026-09-29

MANUAL_CARD_NUMBER=CHANGE_ME
MANUAL_CARD_HOLDER=Velo

TIMEZONE_NAME=Asia/Tehran
FREE_SPEED_MBPS=2
AD_REWARD_MINUTES=20
MAX_HEART_DISCOUNT_PERCENT=30
WEB_WELCOME_MINUTES=15
WEB_ACCESS_SYNC_INTERVAL_SECONDS=15

WIREGUARD_MANAGE_LOCAL=true
WIREGUARD_USE_SUDO=true
WIREGUARD_INTERFACE=wg0
WIREGUARD_SCRIPT_DIR=/opt/velo/wireguard
WIREGUARD_DEFAULT_DNS=1.1.1.1
VPN_CONNECT_FAILOVER_ATTEMPTS=3
VPN_HEARTBEAT_TIMEOUT_SECONDS=180
VPN_PEER_ACTIVITY_GRACE_SECONDS=240
NODE_HEALTH_INTERVAL_SECONDS=30
NODE_HEALTH_FAILURE_THRESHOLD=2
NODE_CIRCUIT_BREAKER_SECONDS=90
PEER_RECONCILE_INTERVAL_SECONDS=120

BOOTSTRAP_SERVER_NAME=NL-01
BOOTSTRAP_SERVER_COUNTRY=NL
BOOTSTRAP_SERVER_CITY=Amsterdam
BOOTSTRAP_SERVER_ENDPOINT=$PUBLIC_IP:51820
BOOTSTRAP_SERVER_PUBLIC_KEY=$WG_PUBLIC_KEY
BOOTSTRAP_SERVER_CLIENT_CIDR=10.77.1.0/24
EOF
else
  echo "Existing backend .env preserved."
fi

chown -R velo:velo "$BACKEND_DIR"
chmod 600 "$ENV_FILE"
chmod 750 "$BACKEND_DIR"
chmod 755 "$BACKEND_DIR/uploads"

# Build the same-origin responsive web client.
cd "$SOURCE_DIR/web"
npm install --no-audit --no-fund
npm run build
rsync -a --delete "$SOURCE_DIR/web/dist/" "$WEB_ROOT/"
chown -R www-data:www-data "$WEB_ROOT"
find "$WEB_ROOT" -type d -exec chmod 755 {} +
find "$WEB_ROOT" -type f -exec chmod 644 {} +

# Backend may manage local wg0 through the narrowly scoped helper scripts.
install -m 440 "$SOURCE_DIR/infra/systemd/velo-sudoers" /etc/sudoers.d/velo
visudo -cf /etc/sudoers.d/velo
install -m 644 "$SOURCE_DIR/infra/systemd/velo-api.service" /etc/systemd/system/velo-api.service

# This VPS is both the control plane and VPN node. Keep node-agent off the public interface.
if systemctl cat velo-node-agent.service >/dev/null 2>&1; then
  install -d -m 755 /etc/systemd/system/velo-node-agent.service.d
  cat >/etc/systemd/system/velo-node-agent.service.d/local-only.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/opt/velo/node-agent/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8787
EOF
fi

install -m 644 "$SOURCE_DIR/infra/nginx/velo-rate-limits.conf" /etc/nginx/conf.d/velo-rate-limits.conf
install -m 644 "$SOURCE_DIR/infra/nginx/velo-http-test.conf" /etc/nginx/sites-available/velo
ln -sfn /etc/nginx/sites-available/velo /etc/nginx/sites-enabled/velo
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
if systemctl cat velo-node-agent.service >/dev/null 2>&1; then
  systemctl restart velo-node-agent
fi
systemctl enable --now velo-api
nginx -t
systemctl enable --now nginx
systemctl restart nginx

# Stage firewall rules but do not enable UFW remotely. Verify a second SSH login first.
ufw allow "$SSH_PORT/tcp" >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 51820/udp >/dev/null

sleep 2
curl -fsS http://127.0.0.1:8000/health/live >/dev/null
curl -fsS http://127.0.0.1/ >/dev/null

echo
echo "============================================================"
echo "Velo single-VPS HTTP test deployment is ready."
echo "Web:   http://$PUBLIC_IP/"
echo "Admin: http://$PUBLIC_IP/admin"
echo "API:   http://127.0.0.1:8000 (local only)"
echo "WG:    $PUBLIC_IP:51820/udp"
echo
echo "TEST MODE: ENVIRONMENT=development and HTTP are intentional."
echo "The OTP appears in the web UI for testing. Do not use this mode for public sales."
echo
echo "Admin password is stored only in: $ENV_FILE"
echo "To view it locally: grep '^ADMIN_PANEL_PASSWORD=' $ENV_FILE"
echo "Do not paste that password into chat or GitHub."
echo
echo "UFW remains inactive. After opening a second SSH session successfully,"
echo "enable it manually with: ufw --force enable"
echo "============================================================"
