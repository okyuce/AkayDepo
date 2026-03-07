"""
Territory Info Model
Manuel territory yönetimi için master territory listesi
"""
from sqlmodel import SQLModel, Field, UniqueConstraint
from uuid import UUID, uuid4
from typing import Optional

class TerritoryInfo(SQLModel, table=True):
    """Territory master data"""
    __tablename__ = "territory_info"
    __table_args__ = (
        UniqueConstraint("code", "depot_id", name="uq_territory_info_code_depot"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(index=True)  # TERR030713-Büsan
    name: str  # Büsan
    display_number: str  # T13
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)
    is_active: bool = Field(default=True)  # Aktif/Pasif
    color: Optional[str] = Field(default=None)  # Hex color for UI (#FF5733)
    sort_order: int = Field(default=0)  # Manuel sıralama için
