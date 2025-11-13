"""initial schema

Revision ID: 001
Revises: 
Create Date: 2025-11-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cycles
    op.create_table('cycles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_no', sa.Integer(), nullable=False),
    sa.Column('run_time', sa.String(), nullable=False),
    sa.Column('plan_date', sa.Date(), nullable=False),
    sa.Column('imported_at', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cycles_cycle_no'), 'cycles', ['cycle_no'], unique=False)
    op.create_index(op.f('ix_cycles_run_time'), 'cycles', ['run_time'], unique=False)
    op.create_index(op.f('ix_cycles_plan_date'), 'cycles', ['plan_date'], unique=False)

    # Territories
    op.create_table('territories',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('display_number', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_territories_code'), 'territories', ['code'], unique=True)
    op.create_index(op.f('ix_territories_display_number'), 'territories', ['display_number'], unique=False)

    # Products
    op.create_table('products',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('pack_per_carton', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_code'), 'products', ['code'], unique=True)

    # Stations
    op.create_table('stations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('worker_id', sa.UUID(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # Dealers
    op.create_table('dealers',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('position_code', sa.String(), nullable=False),
    sa.Column('route_order', sa.Integer(), nullable=False),
    sa.Column('territory_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['territory_id'], ['territories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dealers_code'), 'dealers', ['code'], unique=True)

    # Orders
    op.create_table('orders',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('external_order_code', sa.String(), nullable=False),
    sa.Column('payment_type', sa.String(), nullable=False),
    sa.Column('order_date', sa.Date(), nullable=False),
    sa.Column('delivery_date', sa.Date(), nullable=False),
    sa.Column('territory_id', sa.UUID(), nullable=False),
    sa.Column('dealer_id', sa.UUID(), nullable=False),
    sa.Column('revision_group_id', sa.UUID(), nullable=False),
    sa.Column('revision_no', sa.Integer(), nullable=False),
    sa.Column('source_sheet', sa.String(), nullable=False),
    sa.Column('imported_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['cycle_id'], ['cycles.id'], ),
    sa.ForeignKeyConstraint(['territory_id'], ['territories.id'], ),
    sa.ForeignKeyConstraint(['dealer_id'], ['dealers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_cycle_id'), 'orders', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_orders_external_order_code'), 'orders', ['external_order_code'], unique=False)

    # Order Lines
    op.create_table('order_lines',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('qty_carton', sa.Integer(), nullable=False),
    sa.Column('qty_pack', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Station Assignments
    op.create_table('station_assignments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('plan_date', sa.Date(), nullable=False),
    sa.Column('station_id', sa.UUID(), nullable=False),
    sa.Column('territory_id', sa.UUID(), nullable=False),
    sa.Column('load_rank', sa.Integer(), nullable=False),
    sa.Column('target_total_carton', sa.Integer(), nullable=False),
    sa.Column('target_total_pack', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['cycle_id'], ['cycles.id'], ),
    sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ),
    sa.ForeignKeyConstraint(['territory_id'], ['territories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_station_assignments_cycle_id'), 'station_assignments', ['cycle_id'], unique=False)

    # Loadsheets
    op.create_table('loadsheets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('assignment_id', sa.UUID(), nullable=False),
    sa.Column('dealer_id', sa.UUID(), nullable=False),
    sa.Column('sheet_no', sa.String(), nullable=False),
    sa.Column('package_number', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('is_revision', sa.Boolean(), nullable=False),
    sa.Column('parent_loadsheet_id', sa.UUID(), nullable=True),
    sa.Column('printed_at', sa.DateTime(), nullable=True),
    sa.Column('loaded_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['cycles.id'], ),
    sa.ForeignKeyConstraint(['assignment_id'], ['station_assignments.id'], ),
    sa.ForeignKeyConstraint(['dealer_id'], ['dealers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loadsheets_cycle_id'), 'loadsheets', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_loadsheets_package_number'), 'loadsheets', ['package_number'], unique=False)

    # Loadsheet Lines
    op.create_table('loadsheet_lines',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('loadsheet_id', sa.UUID(), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('qty_carton', sa.Integer(), nullable=False),
    sa.Column('qty_pack', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['loadsheet_id'], ['loadsheets.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Load Counters
    op.create_table('load_counters',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('assignment_id', sa.UUID(), nullable=False),
    sa.Column('count_index', sa.Integer(), nullable=False),
    sa.Column('remaining_carton', sa.Integer(), nullable=False),
    sa.Column('remaining_pack', sa.Integer(), nullable=False),
    sa.Column('note', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['assignment_id'], ['station_assignments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Revision Diffs
    op.create_table('revision_diffs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_from_id', sa.UUID(), nullable=False),
    sa.Column('cycle_to_id', sa.UUID(), nullable=False),
    sa.Column('order_code', sa.String(), nullable=False),
    sa.Column('dealer_id', sa.UUID(), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('qty_old_carton', sa.Integer(), nullable=False),
    sa.Column('qty_new_carton', sa.Integer(), nullable=False),
    sa.Column('qty_change_carton', sa.Integer(), nullable=False),
    sa.Column('change_type', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['cycle_from_id'], ['cycles.id'], ),
    sa.ForeignKeyConstraint(['cycle_to_id'], ['cycles.id'], ),
    sa.ForeignKeyConstraint(['dealer_id'], ['dealers.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_revision_diffs_cycle_from_id'), 'revision_diffs', ['cycle_from_id'], unique=False)
    op.create_index(op.f('ix_revision_diffs_cycle_to_id'), 'revision_diffs', ['cycle_to_id'], unique=False)
    op.create_index(op.f('ix_revision_diffs_dealer_id'), 'revision_diffs', ['dealer_id'], unique=False)


def downgrade() -> None:
    op.drop_table('revision_diffs')
    op.drop_table('load_counters')
    op.drop_table('loadsheet_lines')
    op.drop_table('loadsheets')
    op.drop_table('station_assignments')
    op.drop_table('order_lines')
    op.drop_table('orders')
    op.drop_table('dealers')
    op.drop_table('stations')
    op.drop_table('products')
    op.drop_table('territories')
    op.drop_table('cycles')
