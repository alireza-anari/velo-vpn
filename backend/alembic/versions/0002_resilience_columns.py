"""Bring pre-Alembic Milestone databases to the current resilience schema.

Revision ID: 0002_resilience_columns
Revises: 0001_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_resilience_columns"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def _cols(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()
    if "manual_payments" in tables:
        cols = _cols("manual_payments")
        if "receipt_sha256" not in cols:
            op.add_column("manual_payments", sa.Column("receipt_sha256", sa.String(length=64), nullable=True))
        op.execute("CREATE INDEX IF NOT EXISTS ix_manual_payments_receipt_sha256 ON manual_payments (receipt_sha256)")

    if "vpn_servers" in tables:
        cols = _cols("vpn_servers")
        additions = [
            ("agent_url", sa.String(length=255)),
            ("agent_token", sa.String(length=255)),
            ("last_health_at", sa.DateTime(timezone=True)),
            ("health_state", sa.String(length=20), "unknown"),
            ("health_failures", sa.Integer(), 0),
            ("last_health_error", sa.Text()),
            ("unhealthy_until", sa.DateTime(timezone=True)),
        ]
        for item in additions:
            name, typ, *default = item
            if name not in cols:
                op.add_column(
                    "vpn_servers",
                    sa.Column(name, typ, nullable=True, server_default=str(default[0]) if default else None),
                )
        op.execute("CREATE INDEX IF NOT EXISTS ix_vpn_servers_last_health_at ON vpn_servers (last_health_at)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_vpn_servers_health_state ON vpn_servers (health_state)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_vpn_servers_unhealthy_until ON vpn_servers (unhealthy_until)")

    if "vpn_sessions" in tables:
        cols = _cols("vpn_sessions")
        if "reconnect_required" not in cols:
            op.add_column(
                "vpn_sessions",
                sa.Column("reconnect_required", sa.Boolean(), nullable=True, server_default=sa.false()),
            )
        op.execute("CREATE INDEX IF NOT EXISTS ix_vpn_sessions_reconnect_required ON vpn_sessions (reconnect_required)")


def downgrade() -> None:
    # Safe downgrade intentionally leaves legacy compatibility columns in place.
    # Removing them could destroy operational state on a production VPN node.
    pass
