# Velo

Velo is an Android VPN product designed around a low-friction guest experience for Iranian users: watch an optional rewarded video, receive time-limited/speed-limited Free VPN access, or upgrade to Premium for full speed and no Velo time/volume limit.

This repository contains:
- `android/` — Kotlin/Jetpack Compose Velo application using the approved light/lilac minimalist brand.
- `backend/` — FastAPI API, PostgreSQL models, rewards, email OTP, payments, referrals, Heart Store and VPN orchestration.
- `infra/` — WireGuard, node-agent, Nginx, backup, monitoring and first-VPS deployment assets.
- `docs/` — frozen product decisions, architecture, release/legal drafts, deployment and milestone status.
- `design/` — approved brand board and core mockup references. Do not replace these with unrelated UI styles.

## Current milestone
**Milestone 7 / real-VPS integration hardening** preserves the live product paths:

`Guest -> Rewarded Ad -> Free Time -> WireGuard Connect -> server-side speed/time enforcement`

and:

`Email Account -> Manual Premium Payment -> Admin Approval -> Premium -> one active VPN session per account`

It folds the first real VPS/WireGuard integration findings back into the code: idempotent node endpoint repair, handshake-aware session cleanup, persistent full-tunnel NAT/forwarding, improved Free shaping, and a debug Android path wired to the current test VPS. Milestone 6 observability/migrations/legal-release work and Milestone 5 multi-node failover/reconciliation remain in place.

See `docs/BUILD_STATUS.md` for the exact tested state and remaining production work.

## Backend quick test

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q
```

## Database migrations

```bash
cd backend
alembic -c alembic.ini upgrade head
alembic -c alembic.ini current
```

Production should set `AUTO_SCHEMA_CREATE=false` and run Alembic before API startup. The supplied systemd unit does this automatically.

## Android
Debug builds are currently preconfigured for the test VPS. Production builds require Android SDK 35, Java 17, a real HTTPS `VELO_API_BASE_URL`, real `VELO_TAPSELL_APP_KEY` and your own signing key. See `docs/DEPLOYMENT.md` and `docs/PLAY_RELEASE_CHECKLIST.md`.

## CI build path
`.github/workflows/ci.yml` runs Alembic smoke migration, backend integration tests, Python/shell checks, Android debug compile and Android lint on GitHub-hosted runners. The uploaded CI APK is a debug artifact only; Production still needs your own signing keystore and real Velo/Tapsell configuration.
