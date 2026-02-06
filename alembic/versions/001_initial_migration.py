"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create proxies table first (no dependencies)
    op.create_table(
        'proxies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('host', sa.String(), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('password', sa.String(), nullable=True),
        sa.Column('is_alive', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_tested', sa.DateTime(), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_proxies_id', 'proxies', ['id'], unique=False)
    
    # Create accounts table
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('encrypted_password', sa.LargeBinary(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'VALIDATING', 'VALID', 'INVALID', 'PROCESSING', 'COMPLETED', 'FAILED', 'ERROR', name='accountstatus'), nullable=False),
        sa.Column('proxy_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['proxy_id'], ['proxies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_accounts_email', 'accounts', ['email'], unique=False)
    op.create_index('ix_accounts_id', 'accounts', ['id'], unique=False)
    op.create_index('ix_accounts_status', 'accounts', ['status'], unique=False)
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('cookies', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('access_token', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sessions_id', 'sessions', ['id'], unique=False)
    
    # Create account_logs table
    op.create_table(
        'account_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_account_logs_account_id', 'account_logs', ['account_id'], unique=False)
    op.create_index('ix_account_logs_id', 'account_logs', ['id'], unique=False)
    op.create_index('ix_account_logs_timestamp', 'account_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_table('account_logs')
    op.drop_table('sessions')
    op.drop_table('accounts')
    op.drop_table('proxies')
