# Milestone 5 changelog

- Added automatic VPN node failover for automatic server selection.
- Added per-node health state, failure counters and circuit-breaker windows.
- Added reconnect signaling for active sessions affected by a failed/missing node peer.
- Added periodic node health monitoring and managed-peer reconciliation.
- Added node-agent peer inventory endpoint and managed-CIDR validation.
- Added Android heartbeat-driven automatic reconnect to a healthy automatic node.
- Added Android Keystore-backed AES-GCM bearer-token storage with legacy migration.
- Added browser admin login using signed HttpOnly/SameSite cookie while keeping API-key automation support.
- Added production secret validation and disabled API docs in production.
- Added Nginx rate-limit/security-header examples.
- Added PostgreSQL + receipt-upload backup, checksum, retention, restore and systemd timer assets.
- Added first-VPS Ubuntu bootstrap/checklist and operations documentation.
- Added GitHub Actions backend tests + Android debug compile workflow.
- Backend integration test count: 11 passing in this environment.
