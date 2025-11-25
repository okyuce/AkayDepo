from sqlmodel import SQLModel, Field
from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4

class Dealer(SQLModel, table=True):
    """Bayi modeli"""
    __tablename__ = "dealers"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(unique=True, index=True)  # BayiKodu
    name: str  # BayiAdı
    position_code: str  # Pozisyon
    route_order: int  # BayiRutSırası
    territory_id: UUID = Field(foreign_key="territories.id")

class Product(SQLModel, table=True):
    """Ürün modeli"""
    __tablename__ = "products"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(unique=True, index=True)  # ÜrünKodu
    name: str  # ÜrünAdı
    pack_per_carton: int = Field(default=10)  # 1 karton = 10 paket
    display_order: int = Field(default=999)  # Excel'deki gösterim sırası

class Order(SQLModel, table=True):
    """Sipariş modeli"""
    __tablename__ = "orders"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cycle_id: UUID = Field(foreign_key="cycles.id", index=True)
    external_order_code: str = Field(index=True)  # SiparişKodu
    payment_type: str  # ÖdemeTipi
    order_date: datetime  # SiparişTarihi (tarih + saat)
    delivery_date: date  # TeslimatTarihi
    territory_id: UUID = Field(foreign_key="territories.id")
    dealer_id: UUID = Field(foreign_key="dealers.id")
    revision_group_id: UUID  # Aynı siparişin versiyonları
    revision_no: int  # 1, 2, 3
    source_sheet: str  # Recipe2 / Recip1
    import_batch: int = Field(default=1)  # 1, 2, 3... (hangi Excel import'u)
    is_revision: bool = Field(default=False)  # Bu sipariş revizyon mu?
    previous_order_id: Optional[UUID] = None  # Revizyon ise önceki sipariş
    imported_at: datetime = Field(default_factory=datetime.utcnow)

class OrderLine(SQLModel, table=True):
    """Sipariş satırı modeli"""
    __tablename__ = "order_lines"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="orders.id")
    product_id: UUID = Field(foreign_key="products.id")
    qty_carton: int  # Karton
    qty_pack: int  # Paket
