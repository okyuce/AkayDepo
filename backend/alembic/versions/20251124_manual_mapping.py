"""
add manual mapping tables

Revision ID: 20251124_manual_mapping
Revises: c21b4f3e9d3e
Create Date: 2025-11-24 14:35:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = '20251124_manual_mapping'
down_revision: Union[str, None] = 'c21b4f3e9d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'planning_config',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), primary_key=True),
        sa.Column('auto_planning_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_table(
        'station_territory_map',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), primary_key=True),
        sa.Column('station_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('territory_code', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ondelete='CASCADE')
    )

def downgrade() -> None:
    op.drop_table('station_territory_map')
    op.drop_table('planning_config')