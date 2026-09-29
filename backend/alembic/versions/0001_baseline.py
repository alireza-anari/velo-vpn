"""Velo baseline schema.

Revision ID: 0001_baseline
Revises:
"""
from alembic import op

from app.db import Base
import app.models  # noqa: F401

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The baseline deliberately uses the same SQLAlchemy metadata as the application.
    # create_all is idempotent, which lets a pre-Alembic Velo database pass through
    # this revision before 0002 adds any legacy-missing columns.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
