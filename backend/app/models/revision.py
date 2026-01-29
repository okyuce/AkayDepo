from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class RevisionDiff(SQLModel, table=True):
    """Revizyon farkları - Cycle-to-cycle değişiklik takibi"""
    __tablename__ = "revision_diffs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cycle_from_id: UUID = Field(foreign_key="cycles.id", index=True)  # Önceki döngü
    cycle_to_id: UUID = Field(foreign_key="cycles.id", index=True)  # Yeni döngü
    order_code: str  # SiparişKodu
    dealer_id: UUID = Field(foreign_key="dealers.id", index=True)
    product_id: UUID = Field(foreign_key="products.id")
    qty_old_carton: int  # Önceki miktar
    qty_new_carton: int  # Yeni miktar
    qty_change_carton: int  # new - old (pozitif=artış, negatif=azalış)
    change_type: str  # addition, reduction, new_product, removed_product
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_code": "D3J005897253121",
                "qty_old_carton": 2,
                "qty_new_carton": 5,
                "qty_change_carton": 3,
                "change_type": "addition"
            }
        }
