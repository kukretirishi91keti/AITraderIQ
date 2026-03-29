"""add_profile_and_trade_fields

Revision ID: b1c2d3e4f5a6
Revises: a278fd0a1186
Create Date: 2026-03-29 00:00:00.000000

Adds 4 extended profile columns to users table, creates paper_trades table,
and adds 2 stop-loss/take-profit columns to paper_trades table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a278fd0a1186'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table — extended profile fields
    op.add_column('users', sa.Column('investment_horizon', sa.String(20), nullable=True, server_default='medium'))
    op.add_column('users', sa.Column('experience_level', sa.String(20), nullable=True, server_default='intermediate'))
    op.add_column('users', sa.Column('capital_range', sa.String(20), nullable=True, server_default='medium'))
    op.add_column('users', sa.Column('goals', sa.Text(), nullable=True, server_default='[]'))

    # Create paper_trades table (was missing from initial migration)
    op.create_table(
        'paper_trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='open'),
        sa.Column('strategy', sa.String(50), nullable=True),
        sa.Column('market', sa.String(20), nullable=True, server_default='US'),
        sa.Column('currency', sa.String(10), nullable=True, server_default='$'),
        sa.Column('stop_loss_price', sa.Float(), nullable=True),
        sa.Column('take_profit_price', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_percent', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True, server_default=''),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_paper_trades_id'), 'paper_trades', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_paper_trades_id'), table_name='paper_trades')
    op.drop_table('paper_trades')
    op.drop_column('users', 'goals')
    op.drop_column('users', 'capital_range')
    op.drop_column('users', 'experience_level')
    op.drop_column('users', 'investment_horizon')
