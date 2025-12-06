"""Add users table with admin seed data

Revision ID: 20251206_add_users_table
Revises: fix_revision_diff_type
Create Date: 2025-12-06 08:14:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '20251206_add_users_table'
down_revision: Union[str, None] = '20251202_product_order'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('username', sa.String(length=50), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('station_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    
    # Create indexes
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_station_id', 'users', ['station_id'])
    
    # Add foreign key constraint to stations table
    op.create_foreign_key(
        'fk_users_station_id',
        'users', 'stations',
        ['station_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Seed admin user
    # Password: admin123 (bcrypt hash)
    op.execute("""
        INSERT INTO users (id, username, password_hash, full_name, role, station_id, is_active, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'admin',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxKHvKGHu',
            'System Administrator',
            'admin',
            NULL,
            true,
            NOW(),
            NOW()
        )
    """)


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_users_station_id', 'users', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_users_station_id', 'users')
    op.drop_index('ix_users_username', 'users')
    
    # Drop table
    op.drop_table('users')
