from sqlmodel import SQLModel, Field
from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4

class Cycle(SQLModel, table=True):
    """Döngü modeli - Her Excel yüklemesi bir döngü"""
    __tablename__ = "cycles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cycle_no: int = Field(index=True)  # 1, 2, 3
    run_time: str = Field(index=True)  # "14:00", "16:00", "17:00"
    plan_date: date = Field(index=True)
    imported_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(default="active")  # active, completed, archived
    completed_at: Optional[datetime] = None
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "cycle_no": 1,
                "run_time": "14:00",
                "plan_date": "2025-11-07",
                "status": "active"
            }
        }
