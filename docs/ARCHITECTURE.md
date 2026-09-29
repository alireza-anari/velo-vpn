# Velo architecture

## Android
`Compose UI -> ViewModel -> VeloRepository -> HTTPS API`

The VPN path is separate from ordinary API traffic:
`VeloViewModel -> WireGuardTunnelManager -> official WireGuard GoBackend -> wg0 server`

The Android client creates its WireGuard private key locally; only the public key is sent to Velo. Private keys are not generated or stored by the Velo backend.

Rewarded ads use the current Tapsell Mediation callback surface. The client first asks Velo for a one-use challenge. Only after Tapsell invokes `onRewarded` does the client redeem that challenge with the provider response/ad id. Reward seconds are decided by backend remote config, not hard-coded in the APK.

## Identity
- Guest: anonymous device token; sufficient for free ad/time/VPN use.
- Account: email OTP only; required for durable value such as Premium, hearts, support payments and referrals.
- A device can be linked to a user later without changing the guest-first UX.

## VPN policy
- Free: automatic server, backend-controlled time credit, backend-controlled speed shaping, no volume cap.
- Premium: full Velo speed, no time/volume cap for ordinary consumer use, server choice.
- One active Premium VPN session per account. Multiple installed/logged-in devices are allowed; takeover explicitly replaces the previous active session.

## Data minimization
Velo stores operational/account/reward/payment/session metadata needed to run the product. It does not intentionally store destination websites, DNS browsing history, URLs or packet contents.

## Server evolution
MVP: API + WireGuard on one VPS, PostgreSQL local/private.

Scale-out: central API/PostgreSQL + multiple independent VPN nodes. Node selection remains behind the same `/v1/vpn/connect` contract.

## Multi-node control plane (Milestone 5)
The central API is the source of truth for users, rewards, subscriptions and active VPN leases. A VPN server may either be local to the API or point to a remote `agent_url` with a per-node secret. For a remote node, peer provisioning, shaping cleanup and WireGuard transfer reads go through the Velo Node Agent. Mobile clients never receive agent credentials.

Server selection is capacity-aware: among eligible nodes, Velo chooses the lowest `active_sessions / max_sessions` ratio, using the default flag only as a tie-breaker. A manually selected Premium server is rejected if it has reached capacity.

The node-agent port is an infrastructure control-plane endpoint and must be reachable only from the central API (preferably on provider private networking). It is not a public mobile API.


## Resilience (Milestone 5)
Automatic connect requests are attempted across multiple eligible nodes when peer provisioning fails. Repeated health failures open a short circuit for a node so new sessions avoid it. Existing leases on an unhealthy node are marked for reconnect; Android learns this via heartbeat and requests a fresh automatic server configuration.

The reconciler compares WireGuard peer state with active DB leases. Managed orphan peers are removed, while missing expected peers mark their session for reconnect. This makes temporary node/API failures recover without leaving permanent shaping/peer state behind.

Android bearer tokens are stored with an AES-GCM key held by Android Keystore. The anonymous install identifier remains non-secret.


## Release-candidate operations (Milestone 6)
Schema changes are now tracked by Alembic; production startup applies migrations before Uvicorn while development can retain automatic schema creation. Request IDs are propagated through responses and logs. Prometheus exposes only aggregate operational metrics; public Nginx denies the metrics path and production requires a bearer token for direct/private scraping. Android records only a local crash fingerprint rather than automatically uploading stack traces.
