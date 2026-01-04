"""add_is_main_stock_to_stations

Revision ID: daa42fabb8a9
Revises: 20251227_stock_movements
Create Date: 2026-01-04 03:06:47.589013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from uuid import uuid4


# revision identifiers, used by Alembic.
revision: str = 'daa42fabb8a9'
down_revision: Union[str, None] = '20251227_stock_movements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # is_main_stock kolonunu ekle (default False)
    op.add_column('stations', sa.Column('is_main_stock', sa.Boolean(), nullable=False, server_default='false'))

    # AnaStok istasyonunu oluştur (yoksa)
    op.execute("""
        INSERT INTO stations (id, name, active, is_main_stock)
        SELECT gen_random_uuid(), 'AnaStok', true, true
        WHERE NOT EXISTS (SELECT 1 FROM stations WHERE is_main_stock = true)
    """)


def downgrade() -> None:
    # AnaStok istasyonunu sil
    op.execute("DELETE FROM stations WHERE is_main_stock = true")
    # Kolonu kaldır
    op.drop_column('stations', 'is_main_stock')
