from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _columns(engine: Engine, table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def run_lightweight_migrations(engine: Engine) -> None:
    """Small pre-Alembic migrations for the private MVP.

    Velo has not reached public production yet, but this keeps a Milestone 3 database
    usable when upgrading to Milestone 4. Replace this with Alembic before a larger
    team starts creating concurrent schema changes.
    """
    tables = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        if "manual_payments" in tables:
            cols = _columns(engine, "manual_payments")
            if "receipt_sha256" not in cols:
                conn.execute(text("ALTER TABLE manual_payments ADD COLUMN receipt_sha256 VARCHAR(64)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_manual_payments_receipt_sha256 ON manual_payments (receipt_sha256)"))

        if "vpn_servers" in tables:
            cols = _columns(engine, "vpn_servers")
            if "agent_url" not in cols:
                conn.execute(text("ALTER TABLE vpn_servers ADD COLUMN agent_url VARCHAR(255)"))
            if "agent_token" not in cols:
                conn.execute(text("ALTER TABLE vpn_servers ADD COLUMN agent_token VARCHAR(255)"))
            if "last_health_at" not in cols:
                conn.execute(text("ALTER TABLE vpn_servers ADD COLUMN last_health_at TIMESTAMP"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vpn_servers_last_health_at ON vpn_servers (last_health_at)"))
        if "vpn_servers" in tables:
            cols = _columns(engine, "vpn_servers")
            if "health_state" not in cols:
                conn.execute(text("ALTER TABLE vpn_servers ADD COLUMN health_state VARCHAR(20) DEFAULT 'unknown'"))
            if "health_failures" not in cols:
                conn.execute(text("ALTER TABLE vpn_servers ADD COLUMN health_failures INTEGER DEFAULT 0"))
            if "last_health_error" not in cols:
                conn.execute(text("ALTER TABLE vpn_servers ADD COLUMN last_health_error TEXT"))
            if "unhealthy_until" not in cols:
                conn.execute(text("ALTER TABLE vpn_servers ADD COLUMN unhealthy_until TIMESTAMP"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vpn_servers_health_state ON vpn_servers (health_state)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vpn_servers_unhealthy_until ON vpn_servers (unhealthy_until)"))

        if "vpn_sessions" in tables:
            cols = _columns(engine, "vpn_sessions")
            if "reconnect_required" not in cols:
                conn.execute(text("ALTER TABLE vpn_sessions ADD COLUMN reconnect_required BOOLEAN DEFAULT 0"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vpn_sessions_reconnect_required ON vpn_sessions (reconnect_required)"))

