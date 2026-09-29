# Velo build status — Milestone 7

## Implemented and exercised

### Android
- Kotlin + Jetpack Compose app using the approved Velo light/lilac minimalist design and approved logo assets.
- Guest-first flow; email account only when durable value/payment is needed; no phone number collection.
- WireGuard GoBackend, Android-generated client keypair, connect/disconnect, heartbeat, Free countdown and failover reconnect path.
- Debug Android config points to the current test VPS; when no rewarded zone is configured, debug builds can exercise the real reward wallet without live ad inventory. Release builds do not contain this reward bypass.
- Guest/device and user bearer tokens use Android Keystore-backed AES-GCM storage.
- Local privacy-preserving crash fingerprinting: Velo does not automatically upload stack traces; a short incident id can be included in support mail.
- HTTP client now has bounded connect/read/write/call timeouts, retry-on-connection-failure and normalized `network_unavailable` handling.
- Release Gradle guard refuses non-HTTPS API URLs or the placeholder Tapsell key.
- Settings link to the hosted Privacy/Terms pages and support email.
- Tapsell rewarded flow, Premium, payment receipt, reports, missions, referral, server selection, support and Heart Store flows remain wired to backend APIs.

### Backend
- FastAPI + SQLAlchemy/PostgreSQL model with guest/device tokens, email OTP, rewards, Premium, receipts, referrals, missions and entitlements.
- Alembic baseline and legacy-compatibility migration added; production can run with `AUTO_SCHEMA_CREATE=false`.
- Request IDs, structured JSON logging option and sanitized 500 responses with correlation IDs.
- Prometheus HTTP latency/request metrics plus privacy-safe VPN node/session/payment/reward gauges and background-task error counters.
- `/health/live` and `/health/ready`; optional readiness requirement for at least one active VPN server.
- Production metrics endpoint requires a bearer token and the public Nginx template denies `/metrics`.
- Public Persian `/legal/privacy` and `/legal/terms` pages built from the current Velo product behavior.
- Tehran-day Free wallet; Free time/speed controlled from backend; Premium has no Velo time/speed/volume cap for ordinary consumer use.
- One active Premium VPN session per account across unlimited signed-in devices.
- Server health/circuit breaker, automatic failover, reconnect signaling and peer reconciliation.
- Existing bootstrap nodes are repaired from current endpoint/public-key configuration rather than leaving stale endpoint data.
- Session reaping tolerates temporary API heartbeat loss when WireGuard reports a recent handshake.
- Browser admin panel uses signed HttpOnly/SameSite cookie; script `X-Admin-Key` remains available.
- Minimal operational data only; no intentional browsing/DNS destination/packet-content history.

### Infrastructure / operations
- Authenticated remote node agent for health, transfer counters and peer inventory.
- systemd API startup runs `alembic upgrade head` before serving traffic.
- Local/node-agent systemd hardening is compatible with the narrowly-scoped sudo required for WireGuard helper commands.
- Nginx TLS/rate-limit/security example plus public denial of metrics scraping.
- WireGuard `PostUp`/`PostDown` now restores forwarding and MASQUERADE after reboot; Free shaping has unique per-peer filters, tuned HTB classes and `fq_codel` download queues.
- PostgreSQL + private upload backup/restore assets and first-VPS hardening.
- Prometheus scrape example and monitoring/alert guidance.
- Draft Privacy, Terms, Data Safety worksheet and Google Play release checklist.

## Tests run in this environment
- Python compile pass for backend and node-agent.
- Bash syntax pass for backup, restore, bootstrap, database migration and WireGuard helper scripts.
- Alembic fresh-database smoke migration reaches `0002_resilience_columns (head)`.
- FastAPI integration suite with SQLite/dry WireGuard mode.
- **14 integration tests pass**, including prior reward/Premium/missions/store/referral/payment/failover/reconciliation tests plus Milestone 6 health/request-id/legal/metrics checks and Milestone 7 bootstrap-repair + handshake-aware reaper coverage.

## Important rewarded-ad limitation
The local Tapsell SDK callback is guarded with a short-lived single-use backend nonce and idempotency key, but a documented provider-side Tapsell server-to-server reward verification endpoint has not been identified. A heavily modified APK therefore cannot be made cryptographically trustworthy from the callback alone. Revisit this if Tapsell exposes SSV.

## Still required before public production release
- Real Tapsell app key/zone and actual eCPM/fill-rate measurement; then set Free minutes/speed from real economics.
- Real SMTP provider and sender domain.
- Production domain, final referral/store URL, support/legal contact and final card/account details.
- At least one real VPN host, provider compliance confirmation and end-to-end physical-device test.
- Real backup + restore drill and encrypted off-site replication.
- Remote node agents on private networking or TLS + strict firewall allowlisting.
- Static-IP provisioning before enabling that Store SKU.
- Private object storage before horizontally scaling receipt uploads/API instances.
- Legal review of the Privacy/Terms drafts and completion of current Play VpnService/Data Safety declarations from the final build.
- Android SDK/Gradle compile, lint, physical-device tests, signing keystore, release APK/AAB and Play pre-launch tests.

## Build-environment limitation
This chat runtime has no usable Android SDK/Gradle dependency cache and cannot fetch Android/Maven packages. Backend/node-agent code, Alembic and shell assets can be executed/tested here; Android sources cannot be honestly certified as compiled to an APK in this runtime. GitHub CI is configured to perform the Android debug compile and lint on an Android-capable runner.
