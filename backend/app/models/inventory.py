"""
Station Inventory Model
İstasyon bazlı ürün stoğu
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field

class StationInventory(SQLModel, table=True):
    __tablename__ = "station_inventory"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    station_id: UUID = Field(foreign_key="stations.id", nullable=False)
    product_id: UUID = Field(foreign_key="products.id", nullable=False)
    quantity_carton: int = Field(default=0)
    quantity_pack: int = Field(default=0)
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Unique constraint: Bir istasyonda bir ürün için tek kayıt
    class Config:
        indexes = [
            {"fields": ["station_id", "product_id"], "unique": True}
        ]


class StockMovement(SQLModel, table=True):
    """
    Stok Hareket Logu
    Tüm stok değişikliklerini izlemek için audit trail
    """
    __tablename__ = "stock_movements"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    station_id: UUID = Field(foreign_key="stations.id", nullable=False, index=True)
    product_id: UUID = Field(foreign_key="products.id", nullable=False, index=True)
    loadsheet_id: Optional[UUID] = Field(default=None, foreign_key="loadsheets.id", index=True)

    # Hareket tipi: deduction (düşüm), refund (iade), manual_add, manual_remove
    movement_type: str = Field(nullable=False)

    # Hareket miktarı (her zaman pozitif, yön movement_type'dan anlaşılır)
    quantity_carton: int = Field(default=0)
    quantity_pack: int = Field(default=0)

    # Hareket öncesi stok durumu
    before_carton: int = Field(default=0)
    before_pack: int = Field(default=0)

    # Hareket sonrası stok durumu
    after_carton: int = Field(default=0)
    after_pack: int = Field(default=0)

    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    note: Optional[str] = Field(default=None)
