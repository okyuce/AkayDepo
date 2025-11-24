"""
Territory Info Model
Manuel territory yönetimi için master territory listesi
"""
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from typing import Optional

class TerritoryInfo(SQLModel, table=True):
    """Territory master data"""
    __tablename__ = "territory_info"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(unique=True, index=True)  # TERR030713-Büsan
    name: str  # Büsan
    display_number: str  # T13
    is_active: bool = Field(default=True)  # Aktif/Pasif
    color: Optional[str] = Field(default=None)  # Hex color for UI (#FF5733)
    sort_order: int = Field(default=0)  # Manuel sıralama için
