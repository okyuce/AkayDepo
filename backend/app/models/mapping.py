"""
Manual planning models: PlanningConfig and StationTerritoryMap
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field

class PlanningConfig(SQLModel, table=True):
    __tablename__ = "planning_config"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    auto_planning_enabled: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class StationTerritoryMap(SQLModel, table=True):
    __tablename__ = "station_territory_map"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    station_id: UUID = Field(foreign_key="stations.id")
    territory_code: str = Field(index=True, unique=True)  # From TerritoryInfo.code
    created_at: datetime = Field(default_factory=datetime.utcnow)