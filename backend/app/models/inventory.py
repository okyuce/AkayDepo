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
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Unique constraint: Bir istasyonda bir ürün için tek kayıt
    class Config:
        indexes = [
            {"fields": ["station_id", "product_id"], "unique": True}
        ]
