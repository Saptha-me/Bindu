"""Add webhook_configs table for long-running task notifications.

Revision ID: 20250614_0001
Revises: 20251207_0905_ef0d61440935
Create Date: 2025-06-14 10:00:00.000000

This migration adds the webhook_configs table to support persistent
webhook configurations for long-running tasks (Issue #69).

The table stores webhook configurations that need to survive server
restarts, enabling notifications for tasks that run longer than
typical request timeouts.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250614_0001"
down_revision: Union[str, None] = "20251207_0905_ef0d61440935"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add webhook_configs table for long-running task notifications."""
    # Create webhook_configs table
    op.create_table(
        "webhook_configs",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        comment="Webhook configurations for long-running task notifications",
    )

    # Create indexes for performance
    op.create_index(
        "idx_webhook_configs_created_at",
        "webhook_configs",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )

    # Create trigger for automatic updated_at updates
    op.execute("""
        CREATE TRIGGER update_webhook_configs_updated_at
        BEFORE UPDATE ON webhook_configs
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Remove webhook_configs table."""
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_webhook_configs_updated_at ON webhook_configs")

    # Drop index
    op.drop_index("idx_webhook_configs_created_at", table_name="webhook_configs")

    # Drop table
    op.drop_table("webhook_configs")
