"""Database migration for Hydra user ID mapping.

Revision ID: add_hydra_user_mapping
Revises: 
Create Date: 2025-12-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_hydra_user_mapping'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Hydra user ID mapping columns and migration tracking table."""
    
    # Add hydra_user_id column to existing user tables
    # Note: Adjust table names based on your actual schema
    
    # Example for a users table (if it exists)
    # op.add_column('users', sa.Column('hydra_user_id', sa.String(255), nullable=True))
    # op.create_index('ix_users_hydra_user_id', 'users', ['hydra_user_id'])
    
    # Create auth migration tracking table
    op.create_table(
        'auth_migration',
        sa.Column('auth0_user_id', sa.String(255), primary_key=True),
        sa.Column('hydra_user_id', sa.String(255), nullable=False),
        sa.Column('migrated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('migration_status', sa.String(50), default='completed'),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_auth_migration_hydra_user_id', 'auth_migration', ['hydra_user_id'])
    
    # Create OAuth connection tracking table (if using Kratos)
    op.create_table(
        'oauth_connections',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=True),
        sa.Column('connected_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
    )
    op.create_index('ix_oauth_connections_user_id', 'oauth_connections', ['user_id'])
    op.create_index('ix_oauth_connections_provider', 'oauth_connections', ['provider'])
    op.create_unique_constraint(
        'uq_oauth_connections_user_provider',
        'oauth_connections',
        ['user_id', 'provider']
    )


def downgrade() -> None:
    """Remove Hydra user ID mapping columns and tables."""
    
    # Drop tables
    op.drop_table('oauth_connections')
    op.drop_table('auth_migration')
    
    # Remove columns from user tables
    # op.drop_column('users', 'hydra_user_id')
