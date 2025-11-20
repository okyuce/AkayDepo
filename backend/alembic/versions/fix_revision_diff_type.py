"""Change revision_diff from integer to text for JSON storage

Revision ID: fix_revision_diff_type
Revises: d65288a5dea9
Create Date: 2025-11-17 11:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fix_revision_diff_type'
down_revision: Union[str, None] = 'd65288a5dea9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change revision_diff column type from INTEGER to TEXT
    op.alter_column('loadsheets', 'revision_diff',
                    type_=sa.Text(),
                    existing_type=sa.Integer(),
                    existing_nullable=True)


def downgrade() -> None:
    # Revert revision_diff column type from TEXT to INTEGER
    op.alter_column('loadsheets', 'revision_diff',
                    type_=sa.Integer(),
                    existing_type=sa.Text(),
                    existing_nullable=True)
