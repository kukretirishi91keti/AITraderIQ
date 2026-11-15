"""add_bot_tables

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-11-14 00:00:00.000000

Adds bot_configs and bot_decision_logs tables for Phase 1 auto-bot.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bot_configs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('enabled', sa.Boolean(), default=False, nullable=False, server_default='0'),
        sa.Column('strategy', sa.String(20), default='swing', nullable=False, server_default='swing'),
        sa.Column('symbols', sa.JSON(), nullable=True),
        sa.Column('max_position_usd', sa.Float(), default=1000.0, nullable=False, server_default='1000.0'),
        sa.Column('max_daily_trades', sa.Integer(), default=5, nullable=False, server_default='5'),
        sa.Column('max_daily_loss_pct', sa.Float(), default=2.0, nullable=False, server_default='2.0'),
        sa.Column('min_confidence', sa.Float(), default=70.0, nullable=False, server_default='70.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'bot_decision_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('action', sa.String(10), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('indicators', sa.JSON(), nullable=True),
        sa.Column('trade_id', sa.Integer(), sa.ForeignKey('paper_trades.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('bot_decision_logs')
    op.drop_table('bot_configs')
