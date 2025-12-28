"""Add stock_movements table for audit trail

Revision ID: 20251227_stock_movements
Revises: 20251206_add_users_table
Create Date: 2025-12-27 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision: str = '20251227_stock_movements'
down_revision: Union[str, None] = '20251206_add_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create stock_movements table
    op.create_table(
        'stock_movements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('station_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('loadsheet_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('movement_type', sa.String(length=50), nullable=False),
        sa.Column('quantity_carton', sa.Integer(), nullable=False, default=0),
        sa.Column('quantity_pack', sa.Integer(), nullable=False, default=0),
        sa.Column('before_carton', sa.Integer(), nullable=False, default=0),
        sa.Column('before_pack', sa.Integer(), nullable=False, default=0),
        sa.Column('after_carton', sa.Integer(), nullable=False, default=0),
        sa.Column('after_pack', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('note', sa.String(length=500), nullable=True),
    )

    # Create indexes
    op.create_index('ix_stock_movements_station_id', 'stock_movements', ['station_id'])
    op.create_index('ix_stock_movements_product_id', 'stock_movements', ['product_id'])
    op.create_index('ix_stock_movements_loadsheet_id', 'stock_movements', ['loadsheet_id'])
    op.create_index('ix_stock_movements_created_at', 'stock_movements', ['created_at'])

    # Add foreign key constraints
    op.create_foreign_key(
        'fk_stock_movements_station_id',
        'stock_movements', 'stations',
        ['station_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_stock_movements_product_id',
        'stock_movements', 'products',
        ['product_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_stock_movements_loadsheet_id',
        'stock_movements', 'loadsheets',
        ['loadsheet_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key constraints
    op.drop_constraint('fk_stock_movements_loadsheet_id', 'stock_movements', type_='foreignkey')
    op.drop_constraint('fk_stock_movements_product_id', 'stock_movements', type_='foreignkey')
    op.drop_constraint('fk_stock_movements_station_id', 'stock_movements', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_stock_movements_created_at', 'stock_movements')
    op.drop_index('ix_stock_movements_loadsheet_id', 'stock_movements')
    op.drop_index('ix_stock_movements_product_id', 'stock_movements')
    op.drop_index('ix_stock_movements_station_id', 'stock_movements')

    # Drop table
    op.drop_table('stock_movements')
