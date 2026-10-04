"""Persist user-scoped mock calendar events.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "calendar_events" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calendar_events_user_id", "calendar_events", ["user_id"])
    op.create_index("ix_calendar_events_starts_at", "calendar_events", ["starts_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if "calendar_events" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_calendar_events_starts_at", table_name="calendar_events")
    op.drop_index("ix_calendar_events_user_id", table_name="calendar_events")
    op.drop_table("calendar_events")
