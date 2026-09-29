# Velo production operations — Milestone 6

## Node health and failover
The central API checks active VPN nodes periodically. Each server has a health state, failure counter and short circuit-breaker window. Automatic connections skip nodes whose circuit is open and may retry other eligible nodes. Manual Premium server selection remains exact: if that node is unhealthy, the request fails instead of silently moving the user somewhere else.

After repeated node-health failures, active sessions on that node are marked `reconnect_required`. Android heartbeats detect this flag, drop the stale local tunnel and request a new automatic server configuration. This is a reconnect, not seamless packet-level migration; an active flow can briefly interrupt.

Relevant environment values:
- `VPN_CONNECT_FAILOVER_ATTEMPTS=3`
- `NODE_HEALTH_INTERVAL_SECONDS=30`
- `NODE_HEALTH_FAILURE_THRESHOLD=2`
- `NODE_CIRCUIT_BREAKER_SECONDS=90`
- `PEER_RECONCILE_INTERVAL_SECONDS=120`

## Peer reconciliation
The node agent exposes the WireGuard peer list. Velo periodically compares it with active DB leases:
- a WireGuard peer inside the node's managed client CIDR with no active DB lease is removed as an orphan;
- an active DB lease whose managed peer disappeared is flagged for client reconnect;
- peers outside Velo's managed client CIDR are untouched.

Admins can also run reconciliation manually from the panel or `POST /v1/admin/servers/{id}/reconcile`.

## Admin security
Milestone 5 keeps `X-Admin-Key` for scripts, but the browser panel now uses a short-lived signed HttpOnly/SameSite=Strict cookie obtained from `/admin/login`. Set a distinct `ADMIN_PANEL_PASSWORD` in production. Production startup rejects placeholder/short core secrets, and OpenAPI/Swagger endpoints are disabled.

The example Nginx configuration adds basic security headers and separate request limits for admin and OTP endpoints. Install `infra/nginx/velo-rate-limits.conf` inside Nginx's `http {}` context before enabling `velo.conf`.

## Backup / restore
Files under `infra/backup/` back up both PostgreSQL and private receipt uploads.

1. Copy `backup.env.example` to `/etc/velo/backup.env`, owner-readable only by the `velo` service user.
2. Copy `backup.sh`/`restore.sh` to `/opt/velo/backup/`.
3. Create `/var/backups/velo`, owned by `velo`, mode `0700`.
4. Install `velo-backup.service` and `velo-backup.timer`.
5. Start the timer and run a manual backup once.

The backup directory contains `database.dump`, `uploads.tar.gz`, SHA-256 checksums and a manifest. These are private local staging backups, **not encryption by themselves**. Replicate them to encrypted off-site storage appropriate for your provider/jurisdiction.

A restore is intentionally gated:

```bash
sudo -u velo CONFIRM_RESTORE=YES /opt/velo/backup/restore.sh /var/backups/velo/20260929T031700Z
```

Do a restore drill before accepting paid users. During an actual restore, stop the API first so writes do not race `pg_restore`.

## First-node alert thresholds
For an MVP, alert or investigate when any of these occur:
- node health becomes `unhealthy`;
- active sessions exceed ~70% of a node's configured `max_sessions`;
- disk usage exceeds 75%;
- backup timer has no successful run in 36 hours;
- API 5xx rate or OTP failures spike;
- receipt storage grows unexpectedly;
- repeated reconnects happen for the same node.

## Logs and privacy
Operational logs should include request/error identifiers and node/session IDs where useful, but never destination websites, packet content, DNS browsing history, email OTP values, bearer tokens, WireGuard private keys or receipt image bodies.


## Schema migrations (Milestone 6)
Production uses Alembic. `AUTO_SCHEMA_CREATE=false` should be set in `.env`; systemd runs `alembic upgrade head` before the API process starts. For a database created by an earlier milestone, take a verified backup before the first Milestone 6 restart. The baseline is idempotent and the compatibility revision adds the resilience columns that older databases may lack.

To inspect migration state manually:

```bash
cd /opt/velo/backend
source .venv/bin/activate
alembic -c alembic.ini current
alembic -c alembic.ini history
```

## Metrics / logs
Set `LOG_JSON=true` in production. Every HTTP response carries `X-Request-ID`; unhandled server errors return the same identifier so logs can be correlated without logging user traffic. Prometheus metrics require `METRICS_BEARER_TOKEN` in production and the public Nginx example blocks `/metrics`. See `docs/MONITORING.md`.
