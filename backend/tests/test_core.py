import base64
import os
from pathlib import Path

# Configure before importing Velo modules.
DB_PATH = Path('/tmp/velo_pytest.db')
if DB_PATH.exists():
    DB_PATH.unlink()
os.environ['DATABASE_URL'] = f'sqlite:///{DB_PATH}'
os.environ['ENVIRONMENT'] = 'development'
os.environ['JWT_SECRET'] = 'pytest-secret'
os.environ['ADMIN_API_KEY'] = 'pytest-admin'
os.environ['WIREGUARD_MANAGE_LOCAL'] = 'false'
os.environ['UPLOAD_DIR'] = '/tmp/velo_pytest_uploads'

from fastapi.testclient import TestClient
from app.main import app


def _key(byte: int) -> str:
    return base64.b64encode(bytes([byte]) * 32).decode()


def _auth(token: str):
    return {'Authorization': f'Bearer {token}'}


def _guest(client: TestClient, install='install-' + 'a' * 32):
    r = client.post('/v1/guest', json={'install_id': install})
    assert r.status_code == 200, r.text
    return r.json()['device_token']


def _login(client: TestClient, email='test@example.com'):
    r = client.post('/v1/auth/request-otp', json={'email': email})
    assert r.status_code == 200, r.text
    code = r.json()['dev_code']
    r = client.post('/v1/auth/verify-otp', json={'email': email, 'code': code})
    assert r.status_code == 200, r.text
    return r.json()['access_token']


def _add_server(client: TestClient):
    r = client.post(
        '/v1/admin/servers',
        headers={'X-Admin-Key': 'pytest-admin'},
        json={
            'name': 'Test-DE',
            'country_code': 'DE',
            'city': 'Frankfurt',
            'endpoint_host': '203.0.113.10',
            'endpoint_port': 51820,
            'public_key': _key(9),
            'dns': '1.1.1.1',
            'client_cidr': '10.77.0.0/24',
            'tier': 'free',
            'is_default': True,
            'max_sessions': 200,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()['id']


def test_guest_reward_remote_config_and_vpn_flow():
    with TestClient(app) as client:
        assert client.get('/health').json()['ok'] is True
        token = _guest(client)
        _add_server(client)

        r = client.put(
            '/v1/admin/settings/ad_reward_minutes',
            headers={'X-Admin-Key': 'pytest-admin'},
            json=17,
        )
        assert r.status_code == 200

        c = client.post('/v1/rewards/ad-challenge', headers=_auth(token)).json()
        r = client.post(
            '/v1/rewards/ad-complete',
            headers=_auth(token),
            json={
                'nonce': c['nonce'],
                'client_event_id': 'event-00000001',
                'provider_response_id': 'provider-test',
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()['granted_seconds'] == 17 * 60

        r = client.post(
            '/v1/vpn/connect',
            headers=_auth(token),
            json={'client_public_key': _key(1), 'force_takeover': False},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body['premium'] is False
        assert body['client_address'].startswith('10.77.0.')

        status = client.get('/v1/vpn/status', headers=_auth(token)).json()
        assert status['connected'] is True
        r = client.post(f"/v1/vpn/disconnect/{body['session_id']}", headers=_auth(token))
        assert r.status_code == 200


def test_email_link_manual_payment_and_single_premium_session():
    # Fresh DB within same app/test process retains first test data; unique identifiers are used.
    with TestClient(app) as client:
        # Ensure at least one server exists (idempotently tolerate duplicate from prior test).
        if not client.get('/v1/admin/servers', headers={'X-Admin-Key': 'pytest-admin'}).json():
            _add_server(client)

        user_token = _login(client, 'premium@example.com')
        d1 = _guest(client, 'install-' + 'b' * 32)
        d2 = _guest(client, 'install-' + 'c' * 32)
        for d in (d1, d2):
            r = client.post('/v1/auth/link-device', headers=_auth(user_token), json={'device_token': d})
            assert r.status_code == 200, r.text

        # Server validates the configured plan price; a tampered amount is rejected.
        files = {'receipt': ('receipt.png', b'\x89PNG\r\n\x1a\n' + b'0' * 32, 'image/png')}
        r = client.post(
            '/v1/payments/manual',
            headers=_auth(user_token),
            data={'kind': 'premium', 'amount_toman': '1', 'plan_code': '15d', 'requested_hearts': '0'},
            files=files,
        )
        assert r.status_code == 400
        assert r.json()['detail'] == 'premium_amount_mismatch'

        files = {'receipt': ('receipt.png', b'\x89PNG\r\n\x1a\n' + b'0' * 32, 'image/png')}
        r = client.post(
            '/v1/payments/manual',
            headers=_auth(user_token),
            data={'kind': 'premium', 'amount_toman': '189000', 'plan_code': '15d', 'requested_hearts': '0'},
            files=files,
        )
        assert r.status_code == 200, r.text
        payment_id = r.json()['id']

        r = client.post(
            f'/v1/admin/payments/{payment_id}/review',
            headers={'X-Admin-Key': 'pytest-admin'},
            json={'status': 'approved'},
        )
        assert r.status_code == 200, r.text
        sub = client.get('/v1/users/me/subscription', headers=_auth(user_token)).json()
        assert sub['active'] is True

        # First linked device connects as Premium.
        first = client.post(
            '/v1/vpn/connect',
            headers=_auth(d1),
            json={'client_public_key': _key(2), 'force_takeover': False},
        )
        assert first.status_code == 200, first.text
        assert first.json()['premium'] is True

        # A second device on same account is blocked until the user explicitly takes over.
        blocked = client.post(
            '/v1/vpn/connect',
            headers=_auth(d2),
            json={'client_public_key': _key(3), 'force_takeover': False},
        )
        assert blocked.status_code == 409, blocked.text
        assert blocked.json()['detail'] == 'premium_active_on_other_device'

        takeover = client.post(
            '/v1/vpn/connect',
            headers=_auth(d2),
            json={'client_public_key': _key(3), 'force_takeover': True},
        )
        assert takeover.status_code == 200, takeover.text
        assert takeover.json()['premium'] is True


def test_daily_mission_second_rewarded_video_claim():
    with TestClient(app) as client:
        user_token = _login(client, 'missions@example.com')
        device_token = _guest(client, 'install-' + 'd' * 32)
        assert client.post('/v1/auth/link-device', headers=_auth(user_token), json={'device_token': device_token}).status_code == 200

        # Two rewarded completions make the deliberate "extra video" mission claimable.
        for i in range(2):
            c = client.post('/v1/rewards/ad-challenge', headers=_auth(device_token)).json()
            r = client.post(
                '/v1/rewards/ad-complete',
                headers=_auth(device_token),
                json={
                    'nonce': c['nonce'],
                    'client_event_id': f'mission-ad-{i}-0000',
                    'provider_response_id': f'ad-{i}',
                },
            )
            assert r.status_code == 200, r.text

        today = client.get('/v1/missions/today', headers=_auth(device_token))
        assert today.status_code == 200, today.text
        ad2 = next(x for x in today.json()['missions'] if x['key'] == 'ad_2')
        assert ad2['complete'] is True
        assert ad2['claimed'] is False

        claim = client.post('/v1/missions/claim/ad_2', headers=_auth(device_token))
        assert claim.status_code == 200, claim.text
        assert claim.json()['hearts'] == 4
        hearts = client.get('/v1/users/me/hearts', headers=_auth(user_token)).json()['balance']
        assert hearts >= 4


def test_store_speed_boost_and_vip_entitlement():
    with TestClient(app) as client:
        user_token = _login(client, 'store@example.com')
        device_token = _guest(client, 'install-' + 'e' * 32)
        assert client.post('/v1/auth/link-device', headers=_auth(user_token), json={'device_token': device_token}).status_code == 200

        # Create a small support payment, then admin grants enough hearts for store tests.
        files = {'receipt': ('receipt.png', b'\x89PNG\r\n\x1a\n' + b'S' * 32, 'image/png')}
        r = client.post(
            '/v1/payments/manual',
            headers=_auth(user_token),
            data={'kind': 'support', 'amount_toman': '50000', 'requested_hearts': '0'},
            files=files,
        )
        assert r.status_code == 200, r.text
        payment_id = r.json()['id']
        r = client.post(
            f'/v1/admin/payments/{payment_id}/review',
            headers={'X-Admin-Key': 'pytest-admin'},
            json={'status': 'approved', 'hearts_to_grant': 1200},
        )
        assert r.status_code == 200, r.text

        catalog = client.get('/v1/store/catalog', headers=_auth(user_token))
        assert catalog.status_code == 200, catalog.text
        assert catalog.json()['heart_balance'] >= 1200

        speed = client.post('/v1/store/purchase/free_speed_4mbps_1d', headers=_auth(user_token))
        assert speed.status_code == 200, speed.text
        status = client.get('/v1/vpn/status', headers=_auth(device_token)).json()
        assert status['effective_free_speed_mbps'] == 4

        # Add a VIP US node and verify it unlocks only after its entitlement is purchased.
        vip = client.post(
            '/v1/admin/servers',
            headers={'X-Admin-Key': 'pytest-admin'},
            json={
                'name': 'Test-US-VIP',
                'country_code': 'US',
                'city': 'New York',
                'endpoint_host': '203.0.113.20',
                'endpoint_port': 51820,
                'public_key': _key(8),
                'dns': '1.1.1.1',
                'client_cidr': '10.88.0.0/24',
                'tier': 'vip',
                'is_default': False,
                'max_sessions': 100,
            },
        )
        assert vip.status_code == 200, vip.text

        # Premium is needed to display manual server selection in the current product model.
        files = {'receipt': ('receipt.png', b'\x89PNG\r\n\x1a\n' + b'P' * 32, 'image/png')}
        pay = client.post(
            '/v1/payments/manual',
            headers=_auth(user_token),
            data={'kind': 'premium', 'amount_toman': '189000', 'plan_code': '15d', 'requested_hearts': '0'},
            files=files,
        )
        assert pay.status_code == 200, pay.text
        assert client.post(
            f"/v1/admin/payments/{pay.json()['id']}/review",
            headers={'X-Admin-Key': 'pytest-admin'},
            json={'status': 'approved'},
        ).status_code == 200

        servers = client.get('/v1/vpn/servers', headers=_auth(device_token)).json()
        vip_row = next(x for x in servers if x['name'] == 'Test-US-VIP')
        assert vip_row['locked'] is True

        bought = client.post('/v1/store/purchase/vip_us_30d', headers=_auth(user_token))
        assert bought.status_code == 200, bought.text
        servers = client.get('/v1/vpn/servers', headers=_auth(device_token)).json()
        vip_row = next(x for x in servers if x['name'] == 'Test-US-VIP')
        assert vip_row['locked'] is False


def test_weekly_mission_can_be_claimed():
    with TestClient(app) as client:
        user_token = _login(client, 'weekly@example.com')
        device_token = _guest(client, 'install-' + 'f' * 32)
        assert client.post('/v1/auth/link-device', headers=_auth(user_token), json={'device_token': device_token}).status_code == 200

        # Make the weekly ad mission tiny for a deterministic integration test.
        weekly_defs = {
            'active_5_days': {'title': 'فعالیت', 'target': 1, 'hearts': 1},
            'ads_10': {'title': 'دو ویدیو', 'target': 2, 'hearts': 7},
            'use_120m': {'title': 'استفاده', 'target': 1, 'hearts': 1},
        }
        assert client.put(
            '/v1/admin/settings/weekly_missions',
            headers={'X-Admin-Key': 'pytest-admin'},
            json=weekly_defs,
        ).status_code == 200

        for i in range(2):
            challenge = client.post('/v1/rewards/ad-challenge', headers=_auth(device_token)).json()
            done = client.post(
                '/v1/rewards/ad-complete',
                headers=_auth(device_token),
                json={
                    'nonce': challenge['nonce'],
                    'client_event_id': f'weekly-ad-{i}-00000',
                    'provider_response_id': f'weekly-provider-{i}',
                },
            )
            assert done.status_code == 200, done.text

        week = client.get('/v1/missions/weekly', headers=_auth(device_token))
        assert week.status_code == 200, week.text
        ad = next(x for x in week.json()['missions'] if x['key'] == 'ads_10')
        assert ad['complete'] is True
        claimed = client.post('/v1/missions/claim-week/ads_10', headers=_auth(device_token))
        assert claimed.status_code == 200, claimed.text
        assert claimed.json()['hearts'] == 7


def test_admin_page_and_referral_landing_render():
    with TestClient(app) as client:
        assert client.get('/admin').status_code == 200
        assert 'Velo Admin' in client.get('/admin').text
        page = client.get('/r/ABC123')
        assert page.status_code == 200
        assert 'ABC123' in page.text


def test_receipt_validation_duplicate_and_admin_audit():
    with TestClient(app) as client:
        token = _login(client, 'receipts@example.com')
        valid_png = b'\x89PNG\r\n\x1a\n' + b'R' * 64
        files = {'receipt': ('receipt.png', valid_png, 'image/png')}
        first = client.post(
            '/v1/payments/manual',
            headers=_auth(token),
            data={'kind': 'support', 'amount_toman': '50000', 'requested_hearts': '0'},
            files=files,
        )
        assert first.status_code == 200, first.text

        files = {'receipt': ('receipt.png', valid_png, 'image/png')}
        dup = client.post(
            '/v1/payments/manual',
            headers=_auth(token),
            data={'kind': 'support', 'amount_toman': '50000', 'requested_hearts': '0'},
            files=files,
        )
        assert dup.status_code == 409, dup.text
        assert dup.json()['detail'] == 'duplicate_receipt'

        bad = client.post(
            '/v1/payments/manual',
            headers=_auth(token),
            data={'kind': 'support', 'amount_toman': '50000', 'requested_hearts': '0'},
            files={'receipt': ('receipt.png', b'not really an image', 'image/png')},
        )
        assert bad.status_code == 400, bad.text
        assert bad.json()['detail'] == 'invalid_receipt_content'

        review = client.post(
            f"/v1/admin/payments/{first.json()['id']}/review",
            headers={'X-Admin-Key': 'pytest-admin'},
            json={'status': 'approved'},
        )
        assert review.status_code == 200, review.text
        audit = client.get('/v1/admin/audit', headers={'X-Admin-Key': 'pytest-admin'})
        assert audit.status_code == 200, audit.text
        assert any(x['action'] == 'payment_review' for x in audit.json())


def test_least_loaded_server_selection():
    with TestClient(app) as client:
        # Add a second free node with much more capacity. Automatic selection should prefer lower load ratio.
        existing = client.get('/v1/admin/servers', headers={'X-Admin-Key': 'pytest-admin'}).json()
        if not existing:
            _add_server(client)
        second = client.post(
            '/v1/admin/servers',
            headers={'X-Admin-Key': 'pytest-admin'},
            json={
                'name': 'Load-DE-2',
                'country_code': 'DE',
                'city': 'Nuremberg',
                'endpoint_host': '203.0.113.30',
                'endpoint_port': 51820,
                'public_key': _key(7),
                'dns': '1.1.1.1',
                'client_cidr': '10.99.0.0/24',
                'tier': 'free',
                'is_default': False,
                'max_sessions': 1000,
            },
        )
        assert second.status_code == 200, second.text
        device = _guest(client, 'install-' + 'z' * 32)
        challenge = client.post('/v1/rewards/ad-challenge', headers=_auth(device)).json()
        assert client.post('/v1/rewards/ad-complete', headers=_auth(device), json={
            'nonce': challenge['nonce'], 'client_event_id': 'load-balance-0001', 'provider_response_id': 'load-provider'
        }).status_code == 200
        connected = client.post('/v1/vpn/connect', headers=_auth(device), json={'client_public_key': _key(6)})
        assert connected.status_code == 200, connected.text
        assert connected.json()['server_id'] == second.json()['id']


def test_admin_panel_session_cookie_login():
    with TestClient(app) as client:
        bad = client.post('/admin/login', json={'password': 'wrong-password'})
        assert bad.status_code == 401
        good = client.post('/admin/login', json={'password': 'pytest-admin'})
        assert good.status_code == 200, good.text
        assert client.get('/v1/admin/settings').status_code == 200
        assert client.post('/admin/logout').status_code == 200
        assert client.get('/v1/admin/settings').status_code == 401


def test_automatic_connect_fails_over_to_second_node(monkeypatch):
    from app.config import settings
    from app.db import SessionLocal
    from app.models import VpnServer
    from app.services.wireguard import WireGuardError
    import app.services.vpn as vpn_service

    with TestClient(app) as client:
        with SessionLocal() as db:
            previous = [(s.id, s.is_active, s.is_default) for s in db.query(VpnServer).all()]
            for s in db.query(VpnServer).all():
                s.is_active = False
                s.is_default = False
            db.commit()

        first = client.post('/v1/admin/servers', headers={'X-Admin-Key': 'pytest-admin'}, json={
            'name': 'Failover-DE-1', 'country_code': 'DE', 'city': 'Frankfurt',
            'endpoint_host': '203.0.113.41', 'endpoint_port': 51820, 'public_key': _key(21),
            'dns': '1.1.1.1', 'client_cidr': '10.141.0.0/24', 'tier': 'free',
            'is_default': True, 'max_sessions': 100,
        })
        assert first.status_code == 200, first.text
        second = client.post('/v1/admin/servers', headers={'X-Admin-Key': 'pytest-admin'}, json={
            'name': 'Failover-DE-2', 'country_code': 'DE', 'city': 'Nuremberg',
            'endpoint_host': '203.0.113.42', 'endpoint_port': 51820, 'public_key': _key(22),
            'dns': '1.1.1.1', 'client_cidr': '10.142.0.0/24', 'tier': 'free',
            'is_default': False, 'max_sessions': 100,
        })
        assert second.status_code == 200, second.text
        first_id, second_id = first.json()['id'], second.json()['id']

        old_threshold = settings.node_health_failure_threshold
        settings.node_health_failure_threshold = 1
        calls = []
        original_add_peer = vpn_service.add_peer
        def fake_add_peer(server, public_key, client_ip, speed):
            calls.append(server.id)
            if server.id == first_id:
                raise WireGuardError('simulated_node_down')
            return None
        monkeypatch.setattr(vpn_service, 'add_peer', fake_add_peer)
        monkeypatch.setattr(vpn_service, 'remove_peer', lambda *args, **kwargs: None)
        try:
            device = _guest(client, 'install-' + 'm' * 32)
            challenge = client.post('/v1/rewards/ad-challenge', headers=_auth(device)).json()
            reward = client.post('/v1/rewards/ad-complete', headers=_auth(device), json={
                'nonce': challenge['nonce'], 'client_event_id': 'm5-failover-event', 'provider_response_id': 'm5-provider'
            })
            assert reward.status_code == 200, reward.text
            connected = client.post('/v1/vpn/connect', headers=_auth(device), json={'client_public_key': _key(23)})
            assert connected.status_code == 200, connected.text
            assert connected.json()['server_id'] == second_id
            assert calls[:2] == [first_id, second_id]
            servers = client.get('/v1/admin/servers', headers={'X-Admin-Key': 'pytest-admin'}).json()
            first_row = next(x for x in servers if x['id'] == first_id)
            assert first_row['health_state'] == 'unhealthy'
            assert first_row['health_failures'] >= 1
        finally:
            settings.node_health_failure_threshold = old_threshold
            monkeypatch.setattr(vpn_service, 'add_peer', original_add_peer)
            with SessionLocal() as db:
                for ident, active, default in previous:
                    row = db.get(VpnServer, ident)
                    if row:
                        row.is_active = active
                        row.is_default = default
                for ident in (first_id, second_id):
                    row = db.get(VpnServer, ident)
                    if row:
                        row.is_active = False
                        row.is_default = False
                db.commit()


def test_peer_reconcile_removes_orphan_and_requests_reconnect(monkeypatch):
    from app.db import SessionLocal
    from app.models import VpnServer
    from app.security import decode_subject
    import app.services.wireguard as wg_service

    with TestClient(app) as client:
        with SessionLocal() as db:
            previous = [(s.id, s.is_active, s.is_default) for s in db.query(VpnServer).all()]
            for s in db.query(VpnServer).all():
                s.is_active = False
                s.is_default = False
            db.commit()

        created = client.post('/v1/admin/servers', headers={'X-Admin-Key': 'pytest-admin'}, json={
            'name': 'Reconcile-DE', 'country_code': 'DE', 'city': 'Berlin',
            'endpoint_host': '203.0.113.50', 'endpoint_port': 51820, 'public_key': _key(24),
            'dns': '1.1.1.1', 'client_cidr': '10.150.0.0/24', 'tier': 'free',
            'is_default': True, 'max_sessions': 100,
            'agent_url': 'http://10.0.0.50:8787', 'agent_token': 'test-agent-secret',
        })
        assert created.status_code == 200, created.text
        server_id = created.json()['id']

        # Provisioning itself is mocked; reconciliation then uses a controlled node snapshot.
        import app.services.vpn as vpn_service
        monkeypatch.setattr(vpn_service, 'add_peer', lambda *args, **kwargs: None)
        monkeypatch.setattr(vpn_service, 'remove_peer', lambda *args, **kwargs: None)
        device = _guest(client, 'install-' + 'n' * 32)
        challenge = client.post('/v1/rewards/ad-challenge', headers=_auth(device)).json()
        assert client.post('/v1/rewards/ad-complete', headers=_auth(device), json={
            'nonce': challenge['nonce'], 'client_event_id': 'm5-reconcile-event', 'provider_response_id': 'm5-rec-provider'
        }).status_code == 200
        key = _key(25)
        connected = client.post('/v1/vpn/connect', headers=_auth(device), json={'client_public_key': key})
        assert connected.status_code == 200, connected.text
        session_id = connected.json()['session_id']
        assigned_ip = connected.json()['client_address'].split('/')[0]

        orphan_key = _key(26)
        removed = []
        monkeypatch.setattr(wg_service, 'list_peers', lambda server: [
            {'public_key': key, 'allowed_ips': [assigned_ip + '/32']},
            {'public_key': orphan_key, 'allowed_ips': ['10.150.0.200/32']},
        ])
        monkeypatch.setattr(wg_service, 'remove_peer', lambda server, public_key, client_ip: removed.append((public_key, client_ip)))
        result = client.post(f'/v1/admin/servers/{server_id}/reconcile', headers={'X-Admin-Key': 'pytest-admin'})
        assert result.status_code == 200, result.text
        assert result.json()['removed_orphans'] == 1
        assert result.json()['missing_sessions'] == 0
        assert removed == [(orphan_key, '10.150.0.200')]

        # If the expected peer disappears from WireGuard, the mobile heartbeat is told to reconnect.
        monkeypatch.setattr(wg_service, 'list_peers', lambda server: [])
        result = client.post(f'/v1/admin/servers/{server_id}/reconcile', headers={'X-Admin-Key': 'pytest-admin'})
        assert result.status_code == 200, result.text
        assert result.json()['missing_sessions'] == 1
        heartbeat = client.post(f'/v1/vpn/heartbeat/{session_id}', headers=_auth(device))
        assert heartbeat.status_code == 200, heartbeat.text
        assert heartbeat.json()['reconnect_required'] is True

        with SessionLocal() as db:
            for ident, active, default in previous:
                row = db.get(VpnServer, ident)
                if row:
                    row.is_active = active
                    row.is_default = default
            row = db.get(VpnServer, server_id)
            if row:
                row.is_active = False
                row.is_default = False
            db.commit()


def test_milestone6_health_metrics_legal_and_request_id():
    with TestClient(app) as client:
        live = client.get('/health/live')
        assert live.status_code == 200
        assert live.json()['version'] == '0.7.0'

        ready = client.get('/health/ready')
        assert ready.status_code == 200, ready.text
        assert ready.json()['checks']['database'] is True

        legal = client.get('/legal/privacy')
        assert legal.status_code == 200
        assert 'حریم خصوصی Velo' in legal.text
        terms = client.get('/legal/terms')
        assert terms.status_code == 200
        assert 'شرایط استفاده از Velo' in terms.text

        rid = 'test-request-id-velo'
        response = client.get('/health', headers={'X-Request-ID': rid})
        assert response.headers['X-Request-ID'] == rid

        metrics = client.get('/metrics')
        assert metrics.status_code == 200, metrics.text
        assert 'velo_http_requests_total' in metrics.text
        assert 'velo_active_vpn_sessions' in metrics.text


def test_milestone7_bootstrap_repairs_existing_node_endpoint():
    from app.config import settings
    from app.db import SessionLocal
    from app.models import VpnServer
    from app.services.vpn import bootstrap_server

    name = 'Bootstrap-Repair-M7'
    key = _key(31)
    with SessionLocal() as db:
        row = db.query(VpnServer).filter(VpnServer.name == name).first()
        if not row:
            row = VpnServer(
                name=name,
                country_code='IR',
                city='Old',
                endpoint_host='',
                endpoint_port=51820,
                public_key=key,
                dns='9.9.9.9',
                client_cidr='10.177.0.0/24',
                tier='free',
                is_active=False,
                is_default=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        row_id = row.id

    old = (
        settings.bootstrap_server_name,
        settings.bootstrap_server_country,
        settings.bootstrap_server_city,
        settings.bootstrap_server_endpoint,
        settings.bootstrap_server_public_key,
        settings.bootstrap_server_client_cidr,
        settings.wireguard_default_dns,
    )
    try:
        settings.bootstrap_server_name = name
        settings.bootstrap_server_country = 'IR'
        settings.bootstrap_server_city = 'Test'
        settings.bootstrap_server_endpoint = '94.183.176.82:51820'
        settings.bootstrap_server_public_key = key
        settings.bootstrap_server_client_cidr = '10.177.0.0/24'
        settings.wireguard_default_dns = '1.1.1.1'
        with SessionLocal() as db:
            bootstrap_server(db)
            repaired = db.get(VpnServer, row_id)
            assert repaired.endpoint_host == '94.183.176.82'
            assert repaired.endpoint_port == 51820
            assert repaired.city == 'Test'
            assert repaired.dns == '1.1.1.1'
            assert repaired.is_active is True
    finally:
        (
            settings.bootstrap_server_name,
            settings.bootstrap_server_country,
            settings.bootstrap_server_city,
            settings.bootstrap_server_endpoint,
            settings.bootstrap_server_public_key,
            settings.bootstrap_server_client_cidr,
            settings.wireguard_default_dns,
        ) = old


def test_milestone7_recent_wireguard_handshake_prevents_early_reap(monkeypatch):
    from datetime import timedelta
    from app.config import settings
    from app.db import SessionLocal
    from app.models import VpnSession
    from app.services.time_utils import utcnow
    import app.services.vpn as vpn_service

    with TestClient(app) as client:
        if not client.get('/v1/admin/servers', headers={'X-Admin-Key': 'pytest-admin'}).json():
            _add_server(client)
        token = _guest(client, 'install-' + 'z' * 32)
        challenge = client.post('/v1/rewards/ad-challenge', headers=_auth(token)).json()
        reward = client.post('/v1/rewards/ad-complete', headers=_auth(token), json={
            'nonce': challenge['nonce'],
            'client_event_id': 'm7-heartbeat-reward',
            'provider_response_id': 'm7-provider',
        })
        assert reward.status_code == 200, reward.text
        connected = client.post('/v1/vpn/connect', headers=_auth(token), json={'client_public_key': _key(32)})
        assert connected.status_code == 200, connected.text
        session_id = connected.json()['session_id']

        old_timeout = settings.vpn_heartbeat_timeout_seconds
        old_grace = settings.vpn_peer_activity_grace_seconds
        settings.vpn_heartbeat_timeout_seconds = 60
        settings.vpn_peer_activity_grace_seconds = 240
        try:
            with SessionLocal() as db:
                row = db.get(VpnSession, session_id)
                row.last_heartbeat_at = utcnow() - timedelta(minutes=10)
                db.commit()

            monkeypatch.setattr(vpn_service, 'peer_latest_handshake_at', lambda server, key: utcnow())
            with SessionLocal() as db:
                assert vpn_service.expire_due_sessions(db) == 0
                assert db.get(VpnSession, session_id).status == 'active'

            monkeypatch.setattr(vpn_service, 'peer_latest_handshake_at', lambda server, key: None)
            with SessionLocal() as db:
                row = db.get(VpnSession, session_id)
                row.last_heartbeat_at = utcnow() - timedelta(minutes=10)
                db.commit()
                assert vpn_service.expire_due_sessions(db) == 1
                assert db.get(VpnSession, session_id).status == 'ended'
        finally:
            settings.vpn_heartbeat_timeout_seconds = old_timeout
            settings.vpn_peer_activity_grace_seconds = old_grace



def test_admin_can_grant_subscription_by_email_before_login():
    with TestClient(app) as client:
        email = 'admin-grant@example.com'
        grant = client.post(
            '/v1/admin/subscriptions/grant',
            headers={'X-Admin-Key': 'pytest-admin'},
            json={'email': email, 'days': 30, 'note': 'manual sale'},
        )
        assert grant.status_code == 200, grant.text
        assert grant.json()['email'] == email

        token = _login(client, email)
        sub = client.get('/v1/users/me/subscription', headers=_auth(token))
        assert sub.status_code == 200, sub.text
        assert sub.json()['active'] is True

        users = client.get('/v1/admin/users', headers={'X-Admin-Key': 'pytest-admin'}, params={'q': email})
        assert users.status_code == 200, users.text
        row = next(x for x in users.json() if x['email'] == email)
        assert row['subscription_active'] is True

        dashboard = client.get('/v1/admin/dashboard', headers={'X-Admin-Key': 'pytest-admin'})
        assert dashboard.status_code == 200, dashboard.text
        assert dashboard.json()['active_subscriptions'] >= 1

        revoke = client.post(
            f"/v1/admin/users/{row['id']}/subscription/revoke",
            headers={'X-Admin-Key': 'pytest-admin'},
        )
        assert revoke.status_code == 200, revoke.text
        sub = client.get('/v1/users/me/subscription', headers=_auth(token))
        assert sub.json()['active'] is False
