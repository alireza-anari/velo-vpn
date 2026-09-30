"""Add persistent per-user web VPN access.

Revision ID: 0003_web_vpn_access
Revises: 0002_resilience_columns
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_web_vpn_access"
down_revision = "0002_resilience_columns"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    # 0001 imports current metadata, so a brand-new database may already contain
    # this table by the time it reaches 0003. Legacy databases need it created here.
    if "web_vpn_accesses" in _tables():
        return

    op.create_table(
        "web_vpn_accesses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("vpn_servers.id"), nullable=False),
        sa.Column("client_public_key", sa.String(length=80), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.Column("peer_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("free_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("welcome_granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_web_vpn_access_user"),
        sa.UniqueConstraint("client_public_key", name="uq_web_vpn_access_public_key"),
        sa.UniqueConstraint("server_id", "client_ip", name="uq_web_vpn_access_server_ip"),
    )
    op.create_index("ix_web_vpn_accesses_user_id", "web_vpn_accesses", ["user_id"], unique=True)
    op.create_index("ix_web_vpn_accesses_server_id", "web_vpn_accesses", ["server_id"])
    op.create_index("ix_web_vpn_accesses_client_public_key", "web_vpn_accesses", ["client_public_key"], unique=True)
    op.create_index("ix_web_vpn_accesses_client_ip", "web_vpn_accesses", ["client_ip"])
    op.create_index("ix_web_vpn_accesses_peer_enabled", "web_vpn_accesses", ["peer_enabled"])
    op.create_index("ix_web_vpn_accesses_free_until", "web_vpn_accesses", ["free_until"])


def downgrade() -> None:
    if "web_vpn_accesses" in _tables():
        op.drop_table("web_vpn_accesses")
