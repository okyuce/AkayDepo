"""
Seed script - Test verileri oluştur
e-sipariş.xlsx'ten alınan örnek veriler
"""
from datetime import date, datetime
from uuid import uuid4
from sqlmodel import Session, select
from app.core.database import engine
from app.models import Territory, Product, Station

def seed_territories():
    """Territory'leri oluştur"""
    territories_data = [
        {"code": "TERR030701-Bosna-Hersek", "name": "Bosna-Hersek", "display_number": "T01"},
        {"code": "TERR030702-Kadınlarpazarı", "name": "Kadınlarpazarı", "display_number": "T02"},
        {"code": "TERR030703-Sanayi", "name": "Sanayi", "display_number": "T03"},
        {"code": "TERR030704-Mevlana", "name": "Mevlana", "display_number": "T04"},
        {"code": "TERR030705-Meram", "name": "Meram", "display_number": "T05"},
        {"code": "TERR030707-Sille", "name": "Sille", "display_number": "T07"},
        {"code": "TERR030708-Form", "name": "Form", "display_number": "T08"},
        {"code": "TERR030709-Şeker-Tekke", "name": "Şeker-Tekke", "display_number": "T09"},
        {"code": "TERR030713-Büsan", "name": "Büsan", "display_number": "T13"},
        {"code": "TERR030714-Adliye", "name": "Adliye", "display_number": "T14"},
        {"code": "TERR030716-Lalebahçe", "name": "Lalebahçe", "display_number": "T16"},
        {"code": "TERR030723-Çevreyolu", "name": "Çevreyolu", "display_number": "T23"},
        {"code": "TERR030724-Yazır", "name": "Yazır", "display_number": "T24"},
        {"code": "TERR030727-Sancak", "name": "Sancak", "display_number": "T27"},
    ]
    
    with Session(engine) as session:
        for data in territories_data:
            # Check if exists
            stmt = select(Territory).where(Territory.code == data["code"])
            existing = session.exec(stmt).first()
            if not existing:
                territory = Territory(**data)
                session.add(territory)
        session.commit()
        print(f"✅ {len(territories_data)} territory oluşturuldu")

def seed_products():
    """Ürünleri oluştur"""
    products_data = [
        {"code": "PLMNRCB", "name": "PL Midnight Blue RCB", "pack_per_carton": 10},
        {"code": "MLFTB", "name": "MLR Touch KS Box", "pack_per_carton": 10},
        {"code": "MLEDGE", "name": "MLR Edge KS RCB", "pack_per_carton": 10},
        {"code": "MLTBLUE", "name": "MLR Touch Blue", "pack_per_carton": 10},
        {"code": "CHNB100RCB", "name": "CH NavyB 100 RCB", "pack_per_carton": 10},
        {"code": "MLRED", "name": "Marlboro Red", "pack_per_carton": 10},
        {"code": "PRBLUE", "name": "Parliament Blue", "pack_per_carton": 10},
        {"code": "CAMELBL", "name": "Camel Blue", "pack_per_carton": 10},
    ]
    
    with Session(engine) as session:
        for data in products_data:
            stmt = select(Product).where(Product.code == data["code"])
            existing = session.exec(stmt).first()
            if not existing:
                product = Product(**data)
                session.add(product)
        session.commit()
        print(f"✅ {len(products_data)} ürün oluşturuldu")

def seed_stations():
    """İstasyonları oluştur"""
    stations_data = [
        {"name": "İstasyon-1", "active": True},
        {"name": "İstasyon-2", "active": True},
        {"name": "İstasyon-3", "active": True},
        {"name": "İstasyon-4", "active": True},
        {"name": "İstasyon-5", "active": True},
    ]
    
    with Session(engine) as session:
        for data in stations_data:
            stmt = select(Station).where(Station.name == data["name"])
            existing = session.exec(stmt).first()
            if not existing:
                station = Station(**data)
                session.add(station)
        session.commit()
        print(f"✅ {len(stations_data)} istasyon oluşturuldu")

def main():
    print("🌱 Seed başlıyor...")
    print()
    
    seed_territories()
    seed_products()
    seed_stations()
    
    print()
    print("🎉 Seed tamamlandı!")
    print()
    print("Test verileri:")
    print("- 14 Territory")
    print("- 8 Ürün")
    print("- 5 İstasyon")
    print()
    print("Şimdi yapabilirsiniz:")
    print("1. Excel import (FAZ 2)")
    print("2. İstasyon planlama (FAZ 3)")
    print("3. Fiş üretimi")

if __name__ == "__main__":
    main()
