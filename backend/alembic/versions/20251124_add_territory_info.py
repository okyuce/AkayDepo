"""add territory_info table

Revision ID: add_territory_info
Revises: b20a3e2d8c2d
Create Date: 2025-11-24 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'c21b4f3e9d3e'
down_revision: Union[str, None] = 'b20a3e2d8c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create territory_info table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'territory_info' not in inspector.get_table_names():
        op.create_table(
            'territory_info',
            sa.Column('id', sqlmodel.sql.sqltypes.GUID(), primary_key=True),
            sa.Column('code', sa.String(), nullable=False, index=True, unique=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('display_number', sa.String(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('color', sa.String(), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        )
        
        # Seed data from existing territories
        op.execute("""
            INSERT INTO territory_info (id, code, name, display_number, is_active, sort_order)
            VALUES
            (gen_random_uuid(), 'TERR030702-Kadınlarpazarı', 'Kadınlarpazarı', 'T02', true, 1),
            (gen_random_uuid(), 'TERR030703-Sanayi', 'Sanayi', 'T03', true, 2),
            (gen_random_uuid(), 'TERR030704-Mevlana', 'Mevlana', 'T04', true, 3),
            (gen_random_uuid(), 'TERR030705-Meram', 'Meram', 'T05', true, 4),
            (gen_random_uuid(), 'TERR030707-Sille', 'Sille', 'T07', true, 5),
            (gen_random_uuid(), 'TERR030708-Form', 'Form', 'T08', true, 6),
            (gen_random_uuid(), 'TERR030711-Çumra', 'Çumra', 'T11', true, 7),
            (gen_random_uuid(), 'TERR030713-Büsan', 'Büsan', 'T13', true, 8),
            (gen_random_uuid(), 'TERR030714-Adliye', 'Adliye', 'T14', true, 9),
            (gen_random_uuid(), 'TERR030715-Köyler', 'Köyler', 'T15', true, 10),
            (gen_random_uuid(), 'TERR030716-Lalebahçe', 'Lalebahçe', 'T16', true, 11),
            (gen_random_uuid(), 'TERR030723-Çevreyolu', 'Çevreyolu', 'T23', true, 12),
            (gen_random_uuid(), 'TERR030724-Yazır', 'Yazır', 'T24', true, 13),
            (gen_random_uuid(), 'TERR030727-Sancak', 'Sancak', 'T27', true, 14)
        """)


def downgrade() -> None:
    op.drop_table('territory_info')
