# Milestone 6 — Release Candidate hardening

Milestone 6 focuses on operational visibility, repeatable schema changes, privacy/release documentation and safer mobile failures.

Implemented:
- Alembic baseline plus compatibility migration for pre-Alembic Velo databases;
- production `ExecStartPre` migration and `AUTO_SCHEMA_CREATE=false` mode;
- request IDs and privacy-safe structured JSON logs;
- Prometheus request, latency, VPN/node/payment/reward and background-task metrics;
- liveness/readiness endpoints and production metrics bearer token;
- public Persian Privacy/Terms endpoints plus release/Data Safety working documents;
- Android local crash fingerprinting (no automatic stack-trace upload);
- network timeout/retry and normalized offline error in the Android repository;
- settings links to privacy/terms/support and release configuration placeholders;
- Android/API version `0.6.0`.
