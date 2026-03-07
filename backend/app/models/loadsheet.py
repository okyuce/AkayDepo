from sqlmodel import SQLModel, Field
from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4

class Station(SQLModel, table=True):
    """İstasyon modeli"""
    __tablename__ = "stations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str  # İstasyon-1, İstasyon-2, AnaStok
    active: bool = Field(default=True)
    worker_id: Optional[UUID] = None  # Depo görevlisi (opsiyonel)
    is_main_stock: bool = Field(default=False)  # AnaStok istasyonu mu?
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)

class StationAssignment(SQLModel, table=True):
    """İstasyon atama - territory'yi istasyona bağlar"""
    __tablename__ = "station_assignments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cycle_id: UUID = Field(foreign_key="cycles.id", index=True)
    plan_date: date
    station_id: UUID = Field(foreign_key="stations.id")
    territory_id: UUID = Field(foreign_key="territories.id")
    load_rank: int  # Sayım sırası (1..k)
    target_total_carton: int
    target_total_pack: int
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)

class Loadsheet(SQLModel, table=True):
    """Yükleme fişi"""
    __tablename__ = "loadsheets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cycle_id: UUID = Field(foreign_key="cycles.id", index=True)
    assignment_id: UUID = Field(foreign_key="station_assignments.id")
    dealer_id: UUID = Field(foreign_key="dealers.id")
    sheet_no: str
    package_number: str = Field(index=True)  # T07-B01, T07-B01-R
    batch_number: int = Field(default=1)  # 1, 2, 3... (hangi fiş seti)
    status: str = Field(default="pending")  # pending, loaded, cancelled, error
    loadsheet_type: str = Field(default="normal")  # normal, revision_increase, revision_decrease
    revision_diff: Optional[str] = None  # Revizyon farkı JSON (product diff listesi)
    is_revision: bool = Field(default=False)
    parent_loadsheet_id: Optional[UUID] = None  # Revizyon ise orjinal fişin ID'si
    printed_at: Optional[datetime] = None
    loaded_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None  # Tamamlandığı zaman
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)

class LoadsheetLine(SQLModel, table=True):
    """Fiş satırı - ürünler"""
    __tablename__ = "loadsheet_lines"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    loadsheet_id: UUID = Field(foreign_key="loadsheets.id")
    product_id: UUID = Field(foreign_key="products.id")
    qty_carton: int
    qty_pack: int

class LoadCounter(SQLModel, table=True):
    """Sayım döngüsü - C1, C2, C3..."""
    __tablename__ = "load_counters"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    assignment_id: UUID = Field(foreign_key="station_assignments.id")
    count_index: int  # C1..Ck
    remaining_carton: int
    remaining_pack: int
    note: Optional[str] = None
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)
