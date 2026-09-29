# Velo single-server MVP deployment

The first production-like Velo node can run **WireGuard + FastAPI on one VPS**, with PostgreSQL bound only to localhost. This keeps cost and operational complexity low while preserving a clean path to multiple VPN nodes later.

## 1. Host prerequisites
Use a provider whose terms allow the intended service and Iranian end users. On an Ubuntu/Debian VPS install:

```bash
sudo apt update
sudo apt install -y wireguard iproute2 iptables sudo python3-venv nginx docker.io docker-compose-plugin
```

Enable IPv4 forwarding and make sure UDP/51820 and TCP/80/443 are allowed by the host firewall/provider firewall.

## 2. Create the service account and deploy files

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin velo
sudo mkdir -p /opt/velo/backend /opt/velo/wireguard
sudo chown -R velo:velo /opt/velo/backend
sudo cp infra/wireguard/*.sh /opt/velo/wireguard/
sudo chmod 750 /opt/velo/wireguard/*.sh
```

Copy the backend application (including `alembic/` and `alembic.ini`) to `/opt/velo/backend`, create a virtualenv and install `backend/requirements.txt`.

## 3. WireGuard
Run the supplied installer once as root. Review interface/network values first:

```bash
sudo /opt/velo/wireguard/install.sh
```

The installer writes persistent forwarding/MASQUERADE rules into the WireGuard PostUp/PostDown hooks, so full-tunnel routing returns automatically after reboot. The API itself should **not** run as root. Install the narrow sudo policy:

```bash
sudo cp infra/systemd/velo-sudoers /etc/sudoers.d/velo
sudo chmod 440 /etc/sudoers.d/velo
sudo visudo -cf /etc/sudoers.d/velo
```

`WIREGUARD_USE_SUDO=true` makes the backend call only the whitelisted helper scripts and `wg show` through non-interactive sudo. The supplied systemd unit intentionally leaves `NoNewPrivileges=false` because setuid `sudo` cannot elevate under the no-new-privileges bit; privilege is constrained by the exact sudoers allowlist instead.

## 4. PostgreSQL
For the small MVP you can run only PostgreSQL in Docker:

```bash
cd infra
POSTGRES_PASSWORD='use-a-long-random-password' docker compose -f docker-compose.production-db.yml up -d
```

Put the same password in `/opt/velo/backend/.env`. The database port is bound to `127.0.0.1` only.

## 5. Backend environment
Copy `backend/.env.example` to `/opt/velo/backend/.env`, then change every secret/placeholder. Important values include:
- `JWT_SECRET`
- `ADMIN_API_KEY`
- `ADMIN_PANEL_PASSWORD`
- `METRICS_BEARER_TOKEN`
- `AUTO_SCHEMA_CREATE=false`
- SMTP credentials
- card holder/number
- `WIREGUARD_MANAGE_LOCAL=true`
- server endpoint/public key
- `TAPSELL_REWARDED_ZONE_ID`

Product values such as free speed, ad minutes and prices can later be changed via admin settings without releasing a new APK.

## 5.1 Database migration
Before the first API start, run the migration once manually and verify it succeeds:

```bash
cd /opt/velo/backend
source .venv/bin/activate
alembic -c alembic.ini upgrade head
alembic -c alembic.ini current
```

Take a backup first when upgrading an older Milestone database.

## 6. systemd

```bash
sudo cp infra/systemd/velo-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now velo-api
sudo systemctl status velo-api
```

The API listens only on `127.0.0.1:8000`.


### Direct HTTP test VPS only

For the temporary no-domain test VPS, keep the normal production unit and add the supplied drop-in:

```bash
sudo mkdir -p /etc/systemd/system/velo-api.service.d
sudo cp infra/systemd/velo-api-test-override.conf /etc/systemd/system/velo-api.service.d/test-http.conf
sudo systemctl daemon-reload
sudo systemctl restart velo-api
```

Allow TCP/8000 only from your current test IP at both the provider firewall and UFW. Remove this drop-in before production and return to HTTPS/Nginx on 443.

## 7. HTTPS reverse proxy
Copy `infra/nginx/velo.conf`, replace `api.example.com`, obtain a TLS certificate, then enable/reload Nginx. Production Android builds must use an `https://` API URL.

## 8. Android build values
Do not put secrets in source control. Supply Gradle properties at build time, for example:

```bash
./gradlew :app:assembleRelease \
  -PVELO_API_BASE_URL=https://api.example.com/ \
  -PVELO_TAPSELL_APP_KEY=YOUR_TAPSELL_MEDIATION_APP_KEY
```

The rewarded **zone id** comes from the backend remote config. The Tapsell Mediation **app key** is a manifest/build-time value as required by the current SDK sample.

## 9. First launch checklist
- Add/verify the first VPN server in `/v1/admin/servers`.
- Configure `ad_reward_minutes`, `free_speed_mbps`, plan prices and Tapsell zone id.
- Test a guest ad reward and confirm time is added.
- Test Free connection and verify shaping using a speed test.
- Test Premium payment approval and one-active-device takeover.
- Verify receipts are private and admin API key is never shipped in Android.
- Enable database and uploads backups.

## Scaling later
When the first node approaches capacity, separate the central API/database from VPN nodes and replace local helper execution with an authenticated node agent. The mobile API contract can remain the same.

## 10. Adding remote VPN nodes (Milestone 4)
Milestone 4 includes an authenticated **Velo Node Agent**, so the central API/database can stay on one machine while WireGuard traffic is spread across multiple VPN VPSes.

On each VPN node:

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin velo-agent
sudo mkdir -p /opt/velo/node-agent /opt/velo/wireguard /etc/velo
sudo cp infra/node-agent/app.py infra/node-agent/requirements.txt /opt/velo/node-agent/
sudo cp infra/wireguard/*.sh /opt/velo/wireguard/
sudo chmod 750 /opt/velo/wireguard/*.sh
sudo python3 -m venv /opt/velo/node-agent/.venv
sudo /opt/velo/node-agent/.venv/bin/pip install -r /opt/velo/node-agent/requirements.txt
sudo cp infra/node-agent/velo-node-agent-sudoers /etc/sudoers.d/velo-node-agent
sudo chmod 440 /etc/sudoers.d/velo-node-agent
sudo visudo -cf /etc/sudoers.d/velo-node-agent
sudo cp infra/node-agent/velo-node-agent.service /etc/systemd/system/
```

Create `/etc/velo/node-agent.env` from the example and use a long random `VELO_AGENT_KEY`. Start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now velo-node-agent
```

**Network rule:** TCP/8787 must never be open to the whole Internet. Prefer the provider's private network and permit port 8787 only from the central API server's private IP. If private networking is unavailable, put the agent behind TLS and an IP allowlist in addition to the shared agent key.

When adding the server through `/v1/admin/servers`, set:
- `agent_url`, e.g. `http://10.20.0.12:8787`
- `agent_token`, equal to that node's `VELO_AGENT_KEY`

The central API will then provision/remove peers and read WireGuard transfer counters through the node agent. Automatic server selection uses the lowest active-session/capacity ratio instead of filling one node first. The admin panel can run a health check for each node.

## Receipt hardening
Milestone 4 validates receipt content by file signature rather than trusting the filename, stores a SHA-256 fingerprint, and rejects reuse of a receipt that is already pending or approved. Receipt files remain private behind the admin API. For multi-API deployments, move these files to private object storage before scaling the API horizontally.

## 11. Production hardening and failover (Milestone 5)

### Admin panel
Set a distinct `ADMIN_PANEL_PASSWORD`; the browser panel exchanges it for an HttpOnly signed session cookie. Keep `ADMIN_API_KEY` separate for scripts/automation. Do not expose either secret in Android.

Install `infra/nginx/velo-rate-limits.conf` in Nginx's `http {}` scope before enabling `infra/nginx/velo.conf`. The example separates limits for OTP, admin and normal API traffic.

### Node health / failover
The API background monitor checks all active nodes. After repeated failures, a node enters a short circuit-breaker window and new automatic connections skip it. Existing sessions on that node receive `reconnect_required` through heartbeat, so the Android client can reconnect to another node.

Manual Premium server selection remains exact: if the selected server is unhealthy, Velo reports it unavailable instead of silently choosing another country.

### Peer reconciliation
Each node agent must include the Milestone 5 `/v1/peers` endpoint and the sudoers permission for `wg show wg0 allowed-ips`. Reconciliation removes only peers whose AllowedIP belongs to that node's configured Velo client CIDR.

### Backups
Copy `infra/backup/*` into `/opt/velo/backup` and `/etc/systemd/system`, create `/etc/velo/backup.env` and `/var/backups/velo`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now velo-backup.timer
sudo -u velo VELO_BACKUP_ENV=/etc/velo/backup.env /opt/velo/backup/backup.sh
sudo systemctl list-timers velo-backup.timer
```

Backups are local private staging files, not encryption by themselves. Replicate to encrypted off-site storage and perform a restore drill. See `docs/OPERATIONS.md`.


## Release-candidate documents
Before public distribution review `docs/PRIVACY_POLICY_DRAFT_FA.md`, `docs/TERMS_DRAFT_FA.md`, `docs/DATA_SAFETY_DRAFT.md` and `docs/PLAY_RELEASE_CHECKLIST.md`. The backend serves the current draft pages at `/legal/privacy` and `/legal/terms`; replace placeholder contact information before release.
