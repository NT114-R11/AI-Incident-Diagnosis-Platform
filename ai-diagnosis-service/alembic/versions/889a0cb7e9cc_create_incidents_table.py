
"""create incidents table

Revision ID: 889a0cb7e9cc
Revises:
Create Date: 2026-11-08 08:37:14.908528
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "889a0cb7e9cc"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE SCHEMA IF NOT EXISTS incident_management"
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("alert_name", sa.String(255), nullable=False),
        sa.Column("namespace", sa.String(255), nullable=True),
        sa.Column("pod", sa.String(255), nullable=True),
        sa.Column("severity", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="incident_management",
    )

    op.create_index(
        "ix_incidents_fingerprint_status",
        "incidents",
        ["fingerprint", "status"],
        unique=False,
        schema="incident_management",
    )


def downgrade() -> None:
    op.drop_table(
        "incidents",
        schema="incident_management",
    )