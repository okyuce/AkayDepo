from sqlmodel import SQLModel, Field, UniqueConstraint
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class Territory(SQLModel, table=True):
    """Territory modeli"""
    __tablename__ = "territories"
    __table_args__ = (
        UniqueConstraint("code", "depot_id", name="uq_territory_code_depot"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(index=True)  # TERR030707-Sille
    name: str  # Sille
    display_number: str = Field(index=True)  # T07 (paket numarası için)
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "TERR030707-Sille",
                "name": "Sille",
                "display_number": "T07"
            }
        }
