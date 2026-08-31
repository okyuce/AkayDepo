"""add_closing_check

Revision ID: 20260831_closing_check
Revises: 20260419_is_park
Create Date: 2026-08-31

Gün sonu kapanış Excel kontrolü:
  - closing_checks tablosu (denetim izi)
  - loadsheets.cancelled_by_closing (iptalin nedenini ayırt etmek için)

Mevcut kayıtlara dokunulmaz: yeni kolon server_default='false' ile eklenir.

Idempotent: prod deploy'unda alembic otomatik çalışmadığı için tablo
`create_all` tarafından, kolon da `main.py` startup güvencesi tarafından
zaten oluşturulmuş olabilir. Bu migration ikisini de kontrol eder, böylece
sonradan `alembic upgrade head` çalıştırılsa da hata vermez.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


revision: str = '20260831_closing_check'
down_revision: Union[str, None] = '20260419_is_park'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    insp = _inspector()

    cols = {c['name'] for c in insp.get_columns('loadsheets')}
    if 'cancelled_by_closing' not in cols:
        op.add_column(
            'loadsheets',
            sa.Column('cancelled_by_closing', sa.Boolean(), nullable=False, server_default='false')
        )

    if 'closing_checks' not in insp.get_table_names():
        op.create_table(
            'closing_checks',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('cycle_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('depot_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('filename', sa.String(length=500), nullable=False),
            sa.Column('file_size', sa.Integer(), nullable=False),
            sa.Column('file_hash', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='analyzed'),
            sa.Column('report_json', sa.Text(), nullable=True),
            sa.Column('max_batch_at_analysis', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('cancelled_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('uploaded_at', sa.DateTime(), nullable=False),
            sa.Column('applied_at', sa.DateTime(), nullable=True),
            sa.Column('applied_by', sa.String(length=100), nullable=True),
            # create_all (SQLModel foreign_key=) ayni FK'lari kuruyor; iki yol
            # arasinda sema farki kalmasin diye burada da acikca tanimli.
            sa.ForeignKeyConstraint(['cycle_id'], ['cycles.id'],
                                    name='closing_checks_cycle_id_fkey'),
            sa.ForeignKeyConstraint(['depot_id'], ['depots.id'],
                                    name='closing_checks_depot_id_fkey'),
        )

    idx = {i['name'] for i in _inspector().get_indexes('closing_checks')}
    if 'ix_closing_checks_cycle_id' not in idx:
        op.create_index('ix_closing_checks_cycle_id', 'closing_checks', ['cycle_id'])
    if 'ix_closing_checks_depot_id' not in idx:
        op.create_index('ix_closing_checks_depot_id', 'closing_checks', ['depot_id'])


def downgrade() -> None:
    insp = _inspector()
    if 'closing_checks' in insp.get_table_names():
        op.drop_table('closing_checks')
    cols = {c['name'] for c in insp.get_columns('loadsheets')}
    if 'cancelled_by_closing' in cols:
        op.drop_column('loadsheets', 'cancelled_by_closing')
