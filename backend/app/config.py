from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://velo:velo@localhost:5432/velo"
    jwt_secret: str = "dev-secret-change-me"
    environment: str = "development"
    public_base_url: str = "http://localhost:8000"
    upload_dir: str = "uploads"
    auto_schema_create: bool = True

    # Observability
    log_level: str = "INFO"
    log_json: bool = False
    metrics_enabled: bool = True
    metrics_bearer_token: str = ""
    readiness_require_vpn_server: bool = False

    # Admin API. Replace in production and keep out of the mobile app.
    admin_api_key: str = "dev-admin-key-change-me"
    # Browser admin panel login. If empty, ADMIN_API_KEY is accepted as the panel password.
    admin_panel_password: str = ""
    admin_session_hours: int = 12

    # Email OTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    admin_notification_email: str = ""
    legal_contact_email: str = "support@example.com"
    legal_effective_date: str = "2026-09-29"

    # Manual payment fallback
    manual_card_number: str = "6037-XXXX-XXXX-1234"
    manual_card_holder: str = "Velo"

    # Product remote config defaults
    timezone_name: str = "Asia/Tehran"
    free_speed_mbps: int = 2
    ad_reward_minutes: int = 20
    max_heart_discount_percent: int = 30

    # Tapsell. The app key is build-time in Android Mediation; zone id is remote-configured.
    # tapsell_app_key remains for backward compatibility with early test builds.
    tapsell_app_key: str = ""
    tapsell_rewarded_zone_id: str = ""

    # WireGuard MVP: API and wg0 run on the same machine.
    wireguard_manage_local: bool = False
    wireguard_use_sudo: bool = True
    wireguard_interface: str = "wg0"
    wireguard_script_dir: str = "/opt/velo/wireguard"
    wireguard_default_dns: str = "1.1.1.1"

    # VPN node resilience. Automatic connections may fail over to another eligible node.
    vpn_connect_failover_attempts: int = 3
    # API heartbeat is intentionally more tolerant than the mobile 30s cadence.
    # A recent WireGuard handshake can also keep an otherwise stale API lease alive.
    vpn_heartbeat_timeout_seconds: int = 180
    vpn_peer_activity_grace_seconds: int = 240
    node_health_interval_seconds: int = 30
    node_health_failure_threshold: int = 2
    node_circuit_breaker_seconds: int = 90
    peer_reconcile_interval_seconds: int = 120

    # Optional first server bootstrap. The server public key is not secret.
    bootstrap_server_name: str = "Velo-1"
    bootstrap_server_country: str = "DE"
    bootstrap_server_city: str = "Frankfurt"
    bootstrap_server_endpoint: str = ""
    bootstrap_server_public_key: str = ""
    bootstrap_server_client_cidr: str = "10.77.0.0/24"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
