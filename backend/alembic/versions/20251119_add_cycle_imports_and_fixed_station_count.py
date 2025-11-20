"""add cycle_imports table and cycles.fixed_station_count

Revision ID: add_cycle_imports_and_fixed_station_count
Revises: fix_revision_diff_type
Create Date: 2025-11-19 19:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'a19f2d1c9b1c'
down_revision: Union[str, None] = 'fix_revision_diff_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cycles.fixed_station_count
    op.add_column('cycles', sa.Column('fixed_station_count', sa.Integer(), nullable=True))

    # cycle_imports
    op.create_table(
        'cycle_imports',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), primary_key=True),
        sa.Column('cycle_id', sqlmodel.sql.sqltypes.GUID(), sa.ForeignKey('cycles.id'), nullable=False, index=True),
        sa.Column('batch_number', sa.Integer(), nullable=False, index=True),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('cycle_imports')
    op.drop_column('cycles', 'fixed_station_count')
