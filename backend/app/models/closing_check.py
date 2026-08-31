from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


class ClosingCheck(SQLModel, table=True):
    """Gün sonu kapanış Excel'i ile yapılan sipariş kontrolü.

    Her yükleme bir kayıt: önce `analyzed` olarak yazılır (hiçbir şey
    değişmez), kullanıcı onaylarsa `applied` olur ve iptaller fişlere
    yansır. Denetim izi bu tabloda kalır.
    """
    __tablename__ = "closing_checks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cycle_id: UUID = Field(foreign_key="cycles.id", index=True)
    depot_id: UUID = Field(foreign_key="depots.id", index=True)
    filename: str
    file_size: int
    file_hash: str  # sha256
    status: str = Field(default="analyzed")  # analyzed, applied
    # Analiz raporu (A/B/C/D vakaları + doğrulama çıktısı). Uygulama
    # anında buradaki A listesi kullanılır — dosya tekrar istenmez.
    report_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    # Analiz anındaki en büyük import_batch. Uygulamaya kadar yeni Excel
    # yüklenirse rapor bayatlamıştır; apply bunu görüp reddeder.
    max_batch_at_analysis: int = Field(default=0)
    cancelled_count: int = Field(default=0)
    uploaded_at: datetime = Field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None
