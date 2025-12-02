"""Update product display_order with SKU priority

Revision ID: 20251202_product_order
Revises: fix_revision_diff_type
Create Date: 2025-12-02 07:48:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251202_product_order'
down_revision = 'fix_revision_diff_type'
branch_labels = None
depends_on = None


# SKU sıralama mapping'i
SKU_ORDER = {
    'MLR100': 1,
    'MFTB': 2,
    'MLFTB': 3,
    'MLTBLUE': 4,
    'MLTGRAY': 5,
    'MLTONE': 6,
    'MLEDGE': 7,
    'MLEDBLUE': 8,
    'MLEDSLIMS': 9,
    'PL100': 10,
    'PLLONGRCB': 11,
    'PLRC': 12,
    'PLLRC': 13,
    'PLABS100': 14,
    'PLRSVRCB': 15,
    'PLMNRCB': 16,
    'LAB100RCB': 17,
    'LARKBRCB': 18,
    'CHNB100RCB': 19,
    'CHNAVYBRCB': 20,
    'CHMODENAVY': 21,
    'MUARCB': 22,
    'MUABLU': 23,
    'LM100RCB': 24,
    'LMRCB': 25,
    'MLROLL50': 26,
}


def upgrade() -> None:
    """Update display_order for products based on SKU priority"""
    conn = op.get_bind()
    
    # Her SKU için display_order güncelle
    for sku, order in SKU_ORDER.items():
        conn.execute(
            sa.text("UPDATE products SET display_order = :order WHERE code = :sku"),
            {"order": order, "sku": sku}
        )
    
    print(f"Updated display_order for {len(SKU_ORDER)} products")


def downgrade() -> None:
    """Reset display_order to default value (999)"""
    conn = op.get_bind()
    
    # Tüm ürünleri default değere döndür
    for sku in SKU_ORDER.keys():
        conn.execute(
            sa.text("UPDATE products SET display_order = 999 WHERE code = :sku"),
            {"sku": sku}
        )
    
    print(f"Reset display_order for {len(SKU_ORDER)} products to default (999)")
