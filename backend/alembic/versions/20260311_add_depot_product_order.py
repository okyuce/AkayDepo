"""Add depot_product_order table

Revision ID: 20260311_depot_product_order
Revises: 20260307_multi_depot
Create Date: 2026-03-11 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260311_depot_product_order'
down_revision: Union[str, None] = '20260307_multi_depot'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'depot_product_order',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('depot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='999'),
        sa.ForeignKeyConstraint(['depot_id'], ['depots.id'], name='fk_depot_product_order_depot_id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_depot_product_order_product_id'),
        sa.UniqueConstraint('depot_id', 'product_id', name='uq_depot_product_order'),
    )
    op.create_index('ix_depot_product_order_depot_id', 'depot_product_order', ['depot_id'])
    op.create_index('ix_depot_product_order_product_id', 'depot_product_order', ['product_id'])


def downgrade() -> None:
    op.drop_index('ix_depot_product_order_product_id', 'depot_product_order')
    op.drop_index('ix_depot_product_order_depot_id', 'depot_product_order')
    op.drop_table('depot_product_order')
