"""Add new tables

Revision ID: 95d33eff1da1
Revises: 84c22eee2cb0
Create Date: 2025-12-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95d33eff1da1'
down_revision: Union[str, Sequence[str], None] = '84c22eee2cb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Создаем таблицу КРЕДИТОВ ---
    op.create_table('loans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('term_months', sa.Integer(), nullable=False),
        sa.Column('monthly_payment', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loans_id'), 'loans', ['id'], unique=False)

    # --- Создаем таблицу ГРАФИКА ПЛАТЕЖЕЙ ---
    op.create_table('loan_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('loan_id', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_paid', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loan_schedules_id'), 'loan_schedules', ['id'], unique=False)

    # --- Создаем таблицу ИЗБРАННОГО ---
    op.create_table('favorites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('color_start', sa.String(), nullable=True),
        sa.Column('color_end', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_favorites_id'), 'favorites', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_favorites_id'), table_name='favorites')
    op.drop_table('favorites')
    op.drop_index(op.f('ix_loan_schedules_id'), table_name='loan_schedules')
    op.drop_table('loan_schedules')
    op.drop_index(op.f('ix_loans_id'), table_name='loans')
    op.drop_table('loans')