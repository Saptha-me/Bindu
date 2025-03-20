"""Initial schema for cognitive agents

Revision ID: 001
Revises: 
Create Date: 2025-03-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create cognitive_states table
    op.create_table(
        'cognitive_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('state_data', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_cognitive_states'))
    )
    
    # Create indices
    op.create_index(op.f('ix_cognitive_states_agent_id'), 'cognitive_states', ['agent_id'], unique=False)
    op.create_index(op.f('ix_cognitive_states_session_id'), 'cognitive_states', ['session_id'], unique=False)
    op.create_index(op.f('ix_cognitive_states_agent_session'), 'cognitive_states', ['agent_id', 'session_id'], unique=False)
    
    # Create agent_interactions table
    op.create_table(
        'agent_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('operation', sa.String(50), nullable=False),
        sa.Column('request_content', sa.Text(), nullable=True),
        sa.Column('response_content', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('duration_ms', sa.String(50), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_interactions'))
    )
    
    # Create indices for agent_interactions
    op.create_index(op.f('ix_agent_interactions_agent_id'), 'agent_interactions', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_interactions_session_id'), 'agent_interactions', ['session_id'], unique=False)
    op.create_index(op.f('ix_agent_interactions_operation'), 'agent_interactions', ['operation'], unique=False)
    op.create_index(op.f('ix_agent_interactions_created_at'), 'agent_interactions', ['created_at'], unique=False)


def downgrade():
    # Drop agent_interactions table and indices
    op.drop_index(op.f('ix_agent_interactions_created_at'), table_name='agent_interactions')
    op.drop_index(op.f('ix_agent_interactions_operation'), table_name='agent_interactions')
    op.drop_index(op.f('ix_agent_interactions_session_id'), table_name='agent_interactions')
    op.drop_index(op.f('ix_agent_interactions_agent_id'), table_name='agent_interactions')
    op.drop_table('agent_interactions')
    
    # Drop cognitive_states table and indices
    op.drop_index(op.f('ix_cognitive_states_agent_session'), table_name='cognitive_states')
    op.drop_index(op.f('ix_cognitive_states_session_id'), table_name='cognitive_states')
    op.drop_index(op.f('ix_cognitive_states_agent_id'), table_name='cognitive_states')
    op.drop_table('cognitive_states')
