"""
Depot Model
Çoklu depo yönetimi
"""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class Depot(SQLModel, table=True):
    __tablename__ = "depots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(unique=True, index=True, nullable=False)  # VAN, KON, etc.
    name: str = Field(nullable=False)  # Van Deposu
    city: str = Field(nullable=False)  # Van
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
