"""add_profile_and_trade_fields

Revision ID: b1c2d3e4f5a6
Revises: a278fd0a1186
Create Date: 2026-03-29 00:00:00.000000

Adds 4 extended profile columns to users table and 2 stop-loss/take-profit
columns to paper_trades table.
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

    # Paper trades table — stop-loss and take-profit levels
    op.add_column('paper_trades', sa.Column('stop_loss_price', sa.Float(), nullable=True))
    op.add_column('paper_trades', sa.Column('take_profit_price', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('paper_trades', 'take_profit_price')
    op.drop_column('paper_trades', 'stop_loss_price')
    op.drop_column('users', 'goals')
    op.drop_column('users', 'capital_range')
    op.drop_column('users', 'experience_level')
    op.drop_column('users', 'investment_horizon')
