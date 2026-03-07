"""
Manual planning models: PlanningConfig and StationTerritoryMap
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, UniqueConstraint

class PlanningConfig(SQLModel, table=True):
    __tablename__ = "planning_config"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    auto_planning_enabled: bool = Field(default=True)
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)
    updated_at: datetime = Field(default_factory=datetime.now)

class StationTerritoryMap(SQLModel, table=True):
    __tablename__ = "station_territory_map"
    __table_args__ = (
        UniqueConstraint("territory_code", "depot_id", name="uq_station_territory_map_code_depot"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    station_id: UUID = Field(foreign_key="stations.id")
    territory_code: str = Field(index=True)  # From TerritoryInfo.code
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now)