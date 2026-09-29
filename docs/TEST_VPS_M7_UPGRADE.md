# Upgrade the current test VPS from Milestone 6.1 to Milestone 7

This procedure preserves PostgreSQL data, `/opt/velo/backend/.env`, WireGuard private keys and uploaded receipts. It is intended for the temporary no-domain test VPS.

1. Deactivate the Windows test tunnel, upload/extract Milestone 7 under the `ubuntu` home directory, then on the VPS:

```bash
sudo systemctl stop velo-api
sudo cp -a ~/velo-project/backend/. /opt/velo/backend/
sudo cp -a ~/velo-project/infra/wireguard/. /opt/velo/wireguard/
sudo chown -R root:root /opt/velo/wireguard
sudo chmod 750 /opt/velo/wireguard/*.sh
```

2. Refresh the narrow sudo policy and API service:

```bash
sudo cp ~/velo-project/infra/systemd/velo-sudoers /etc/sudoers.d/velo
sudo chmod 440 /etc/sudoers.d/velo
sudo visudo -cf /etc/sudoers.d/velo
sudo cp ~/velo-project/infra/systemd/velo-api.service /etc/systemd/system/velo-api.service
sudo mkdir -p /etc/systemd/system/velo-api.service.d
sudo cp ~/velo-project/infra/systemd/velo-api-test-override.conf /etc/systemd/system/velo-api.service.d/test-http.conf
```

3. Ensure the new lease settings exist without printing secrets:

```bash
grep -q '^VPN_HEARTBEAT_TIMEOUT_SECONDS=' /opt/velo/backend/.env || \
  echo 'VPN_HEARTBEAT_TIMEOUT_SECONDS=180' | sudo tee -a /opt/velo/backend/.env >/dev/null
grep -q '^VPN_PEER_ACTIVITY_GRACE_SECONDS=' /opt/velo/backend/.env || \
  echo 'VPN_PEER_ACTIVITY_GRACE_SECONDS=240' | sudo tee -a /opt/velo/backend/.env >/dev/null
```

Make sure `BOOTSTRAP_SERVER_ENDPOINT` contains the real public endpoint. Milestone 7 will repair the matching existing DB node from this value at startup.

4. Refresh the WireGuard configuration. `install.sh` preserves `/etc/wireguard/wg0.key` and writes persistent forwarding/NAT hooks:

```bash
sudo WG_ADDRESS=10.77.0.1/24 WG_CLIENT_CIDR=10.77.0.0/24 WG_PORT=51820 \
  /opt/velo/wireguard/install.sh
sudo systemctl restart wg-quick@wg0
```

5. Restart Velo and verify:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now velo-api
sleep 5
curl -sS http://127.0.0.1:8000/health/live
curl -sS http://127.0.0.1:8000/health/ready
sudo wg show wg0
```

For this test VPS only, keep TCP/8000 restricted to the tester's public IP. Production must remove the test systemd drop-in and use HTTPS/Nginx.
