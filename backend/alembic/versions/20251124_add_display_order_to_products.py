"""add display_order to products

Revision ID: add_display_order_to_products
Revises: a19f2d1c9b1c
Create Date: 2025-11-24 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b20a3e2d8c2d'
down_revision: Union[str, None] = 'a19f2d1c9b1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add display_order column to products table
    op.add_column('products', sa.Column('display_order', sa.Integer(), nullable=False, server_default='999'))


def downgrade() -> None:
    op.drop_column('products', 'display_order')
