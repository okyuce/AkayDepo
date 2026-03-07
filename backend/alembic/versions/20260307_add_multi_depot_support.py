"""Add multi-depot support

Revision ID: 20260307_multi_depot
Revises: daa42fabb8a9
Create Date: 2026-03-07 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260307_multi_depot'
down_revision: Union[str, None] = 'daa42fabb8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 13 depo tanımı
DEPOTS = [
    ("VAN", "Van Deposu", "Van"),
    ("HAK", "Hakkari Deposu", "Hakkari"),
    ("MUS", "Muş Deposu", "Muş"),
    ("BIT", "Bitlis Deposu", "Bitlis"),
    ("AGR", "Ağrı Deposu", "Ağrı"),
    ("DOG", "Doğubayazıt Deposu", "Doğubayazıt"),
    ("NIG", "Niğde Deposu", "Niğde"),
    ("AKS", "Akşehir Deposu", "Akşehir"),
    ("KAR", "Karaman Deposu", "Karaman"),
    ("ERE", "Ereğli Deposu", "Ereğli"),
    ("SEY", "Seydişehir Deposu", "Seydişehir"),
    ("CIH", "Cihanbeyli Deposu", "Cihanbeyli"),
    ("KON", "Konya Deposu", "Konya"),
]

# depot_id eklenecek tablolar
TABLES_WITH_DEPOT = [
    "users",
    "cycles",
    "territories",
    "territory_info",
    "dealers",
    "orders",
    "stations",
    "station_assignments",
    "loadsheets",
    "load_counters",
    "revision_diffs",
    "cycle_imports",
    "planning_config",
    "station_territory_map",
    "station_inventory",
    "stock_movements",
]

# Kaldırılacak eski unique index'ler
OLD_UNIQUE_INDEXES = [
    # (tablo, index_adı)
    ("territories", "ix_territories_code"),
    ("territory_info", "ix_territory_info_code"),
    ("dealers", "ix_dealers_code"),
    ("station_territory_map", "ix_station_territory_map_territory_code"),
]

NEW_COMPOUND_UNIQUE = [
    # (tablo, constraint_adı, kolonlar)
    ("territories", "uq_territory_code_depot", ["code", "depot_id"]),
    ("territory_info", "uq_territory_info_code_depot", ["code", "depot_id"]),
    ("dealers", "uq_dealer_code_depot", ["code", "depot_id"]),
    ("station_territory_map", "uq_station_territory_map_code_depot", ["territory_code", "depot_id"]),
]


def upgrade() -> None:
    # 1. depots tablosunu oluştur
    op.create_table(
        'depots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_depots_code', 'depots', ['code'], unique=True)

    # 2. 13 depo seed et
    for code, name, city in DEPOTS:
        op.execute(
            sa.text(
                "INSERT INTO depots (id, code, name, city) "
                "VALUES (gen_random_uuid(), :code, :name, :city)"
            ).bindparams(code=code, name=name, city=city)
        )

    # 3. Tüm tablolara depot_id kolonu ekle (nullable)
    for table in TABLES_WITH_DEPOT:
        op.add_column(table, sa.Column('depot_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_index(f'ix_{table}_depot_id', table, ['depot_id'])

    # 4. Mevcut tüm verileri KONYA deposuna ata
    for table in TABLES_WITH_DEPOT:
        op.execute(
            sa.text(
                f"UPDATE {table} SET depot_id = (SELECT id FROM depots WHERE code = 'KON') "
                f"WHERE depot_id IS NULL"
            )
        )

    # 5. Eski unique index'leri drop et
    for table, index_name in OLD_UNIQUE_INDEXES:
        op.drop_index(index_name, table)

    # 6. Yeni compound unique constraint'ler ekle
    for table, constraint_name, columns in NEW_COMPOUND_UNIQUE:
        op.create_unique_constraint(constraint_name, table, columns)

    # 7. Foreign key constraint'leri ekle
    for table in TABLES_WITH_DEPOT:
        op.create_foreign_key(
            f'fk_{table}_depot_id',
            table, 'depots',
            ['depot_id'], ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    # FK constraint'leri kaldır
    for table in TABLES_WITH_DEPOT:
        op.drop_constraint(f'fk_{table}_depot_id', table, type_='foreignkey')

    # Yeni compound unique constraint'leri kaldır
    for table, constraint_name, _ in NEW_COMPOUND_UNIQUE:
        op.drop_constraint(constraint_name, table, type_='unique')

    # Eski unique index'leri geri ekle
    for table, index_name in OLD_UNIQUE_INDEXES:
        column = index_name.replace(f'ix_{table}_', '')
        op.create_index(index_name, table, [column], unique=True)

    # depot_id kolonlarını ve index'lerini kaldır
    for table in TABLES_WITH_DEPOT:
        op.drop_index(f'ix_{table}_depot_id', table)
        op.drop_column(table, 'depot_id')

    # depots tablosunu sil
    op.drop_index('ix_depots_code', 'depots')
    op.drop_table('depots')
