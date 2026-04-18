"""add_is_park_to_stations

Revision ID: 20260419_is_park
Revises: 20260311_depot_product_order
Create Date: 2026-04-19

is_park flag'i ve her depoda Park istasyonu oluşturma.
Park'a atanan territory'ler hiçbir hesaba katılmaz (yükleme fişi,
stok dağılımı, istasyon dağılımı, planlama dahil).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260419_is_park'
down_revision: Union[str, None] = '20260311_depot_product_order'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # is_park kolonunu ekle (default False)
    op.add_column(
        'stations',
        sa.Column('is_park', sa.Boolean(), nullable=False, server_default='false')
    )

    # Her depo için Park istasyonu oluştur (yoksa)
    op.execute("""
        INSERT INTO stations (id, name, active, is_main_stock, is_park, depot_id)
        SELECT gen_random_uuid(), 'Park', true, false, true, d.id
        FROM depots d
        WHERE NOT EXISTS (
            SELECT 1 FROM stations s
            WHERE s.is_park = true AND s.depot_id = d.id
        )
    """)

    # Depot'suz (legacy) ortam için de bir Park oluştur (yoksa)
    op.execute("""
        INSERT INTO stations (id, name, active, is_main_stock, is_park, depot_id)
        SELECT gen_random_uuid(), 'Park', true, false, true, NULL
        WHERE NOT EXISTS (
            SELECT 1 FROM stations s WHERE s.is_park = true AND s.depot_id IS NULL
        )
        AND EXISTS (
            SELECT 1 FROM stations s WHERE s.depot_id IS NULL
        )
    """)


def downgrade() -> None:
    # Park istasyonlarını sil
    op.execute("DELETE FROM stations WHERE is_park = true")
    # Kolonu kaldır
    op.drop_column('stations', 'is_park')
