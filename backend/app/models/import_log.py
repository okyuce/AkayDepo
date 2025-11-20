from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class CycleImport(SQLModel, table=True):
    """Excel import geçmişi (UI'da listelemek için)"""
    __tablename__ = "cycle_imports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cycle_id: UUID = Field(foreign_key="cycles.id", index=True)
    batch_number: int = Field(index=True)
    filename: str
    file_size: int
    file_hash: str  # sha256
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
