"""
Fix product display_order according to fixed sequence
"""
from sqlmodel import Session, select, create_engine
from app.models import Product
from app.core.config import settings

# Sabit sıralama tablosu
PRODUCT_ORDER = {
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

engine = create_engine(settings.DATABASE_URL)

with Session(engine) as session:
    products = session.exec(select(Product)).all()
    updated = 0
    
    for product in products:
        if product.code in PRODUCT_ORDER:
            new_order = PRODUCT_ORDER[product.code]
            if product.display_order != new_order:
                print(f"Updating {product.code}: {product.display_order} -> {new_order}")
                product.display_order = new_order
                session.add(product)
                updated += 1
    
    session.commit()
    print(f"\n✓ {updated} ürün güncellendi")
