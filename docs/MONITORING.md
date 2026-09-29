# Velo monitoring — Milestone 6

Velo exposes privacy-safe Prometheus metrics at `GET /metrics`. Production requires `METRICS_BEARER_TOKEN`; the public Nginx vhost denies `/metrics`, so scrape it from localhost or a private monitoring network.

Useful metrics include:
- `velo_http_requests_total` and `velo_http_request_duration_seconds`
- `velo_background_errors_total`
- `velo_active_vpn_sessions`
- `velo_unhealthy_vpn_nodes`
- `velo_pending_manual_payments`
- `velo_reward_events_total_db`

Health probes:
- `/health/live`: process is alive; no database dependency.
- `/health/ready`: database is reachable and, when `READINESS_REQUIRE_VPN_SERVER=true`, at least one VPN node is active.

Recommended first-node alerts:
- readiness fails for 2 consecutive minutes;
- HTTP 5xx exceeds 2% for 5 minutes;
- p95 API latency exceeds 1.5s for 10 minutes;
- `velo_unhealthy_vpn_nodes > 0` for 2 minutes;
- active sessions exceed 70% of the aggregate configured node capacity;
- pending manual payments grow continuously for more than one business day;
- any background task error repeats more than 3 times in 10 minutes.

Do not add email addresses, tokens, client IPs, destination domains, WireGuard keys, receipt filenames or referral codes as Prometheus labels. They create both privacy risk and high-cardinality metrics.
