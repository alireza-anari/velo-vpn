# First Velo VPS checklist

1. Verify the provider explicitly permits the intended VPN service and Iranian end users.
2. Use a fresh Ubuntu/Debian host; create SSH keys and disable password SSH after verifying key login.
3. Run `SSH_PORT=22 sudo infra/production/bootstrap-ubuntu.sh` (change the port if yours differs).
4. Generate WireGuard server keys on the VPS. Never commit the private key.
5. Configure `/opt/velo/backend/.env` with production secrets (`AUTO_SCHEMA_CREATE=false`, unique JWT/admin/metrics tokens) and `/etc/velo/backup.env` with the PostgreSQL backup URL.
6. Run `alembic -c alembic.ini upgrade head`, verify `alembic current`, then run `infra/wireguard/install.sh` and verify `wg show wg0` plus Internet forwarding.
7. Put FastAPI behind HTTPS Nginx; API must listen only on loopback.
8. If using a remote node agent, expose TCP/8787 only on a private network or IP allowlist to the central API host.
9. Run one manual backup and a restore drill before accepting paid subscriptions.
10. Verify `/health/ready`, a private authenticated `/metrics` scrape, Free speed shaping, reward expiry at Tehran midnight, Premium single-active-device takeover, and node failover.
