# Velo Milestone 7 — real-VPS integration fixes

Milestone 7 folds the first real WireGuard VPS test findings back into the project.

## Verified manually on the test VPS

The test path reached a real WireGuard handshake and full tunnel, with DNS/NAT working and the public egress IP changing to the VPN node. Free-tier server-side shaping was also exercised against a file served over the tunnel.

## Fixes in this milestone

- Bootstrap server configuration is now idempotent: an existing auto-created node with the same name/public key is repaired/updated from environment values instead of being skipped forever. This fixes stale/empty endpoints after configuration changes.
- Session cleanup is more tolerant of temporary API-heartbeat gaps. A stale API heartbeat is not enough to remove a tunnel when WireGuard itself has a recent handshake.
- Local and remote node-agent paths can read `latest-handshakes`; sudoers/systemd assets were updated accordingly.
- Free shaping uses unique per-client filter priorities, explicit HTB burst/quantum, `fq_codel` on the download class, destination matching on `wg0` egress, and upload policing on `wg0` ingress.
- WireGuard installation now persists full-tunnel forwarding/NAT in `wg0.conf` PostUp/PostDown so a reboot does not require manual iptables commands.
- Debug Android builds point at the current test VPS and can grant a debug reward through the real backend wallet when no rewarded zone is configured. Release builds keep the HTTPS and real-Tapsell-key guards.
- Android/API version is `0.7.0`.

## Test-VPS notes

For direct HTTP debug testing, install `infra/systemd/velo-api-test-override.conf` as a systemd drop-in and restrict TCP/8000 at both provider firewall and UFW. Do not use this direct-HTTP mode for production.

The debug reward bypass is compiled only into `BuildConfig.DEBUG`; release builds never use it.
