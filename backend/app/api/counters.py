"""
Load Counter API Router
Araç sayaç okuma endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_session
from app.core.websocket import manager
from app.api.auth import get_current_user
from app.models import LoadCounter, Cycle, Station

router = APIRouter()

class CounterReading(BaseModel):
    """Sayaç okuma request"""
    station_id: str
    counter_value: int


@router.post("/")
async def save_counter_reading(
    reading: CounterReading,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Sayaç okuma kaydet

    Args:
        reading: station_id ve counter_value
    """
    try:
        station_id = UUID(reading.station_id)

        # Aktif döngü bul
        depot_id = current_user.get("depot_id")
        stmt = select(Cycle).where(Cycle.status == "active")
        if depot_id:
            stmt = stmt.where(Cycle.depot_id == depot_id)
        stmt = stmt.order_by(Cycle.imported_at.desc())
        cycle = session.exec(stmt).first()
        
        if not cycle:
            raise HTTPException(404, "Aktif döngü bulunamadı")
        
        # Station var mı kontrol et
        station = session.get(Station, station_id)
        if not station:
            raise HTTPException(404, "İstasyon bulunamadı")
        
        # Yeni kayıt oluştur
        counter = LoadCounter(
            cycle_id=cycle.id,
            station_id=station_id,
            counter_value=reading.counter_value,
            recorded_at=datetime.now()
        )
        
        session.add(counter)
        session.commit()
        session.refresh(counter)
        
        # WebSocket bildirimi gönder
        await manager.notify_counter_reading(
            station_id=station_id,
            counter_value=reading.counter_value,
            depot_id=str(depot_id) if depot_id else "default"
        )
        
        return {
            "id": str(counter.id),
            "station_id": str(counter.station_id),
            "station_name": station.name,
            "counter_value": counter.counter_value,
            "recorded_at": counter.recorded_at.isoformat()
        }
        
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(400, "Geçersiz station_id formatı")
    except Exception as e:
        raise HTTPException(500, f"Sayaç kaydetme hatası: {str(e)}")


@router.get("/cycle/{cycle_id}")
async def get_cycle_counters(
    cycle_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Döngünün tüm sayaç okumalarını getir"""
    stmt = select(LoadCounter).where(LoadCounter.cycle_id == cycle_id).order_by(LoadCounter.recorded_at)
    counters = session.exec(stmt).all()
    
    result = []
    for counter in counters:
        station = session.get(Station, counter.station_id)
        result.append({
            "id": str(counter.id),
            "station_id": str(counter.station_id),
            "station_name": station.name if station else "",
            "counter_value": counter.counter_value,
            "recorded_at": counter.recorded_at.isoformat()
        })
    
    return result


@router.get("/station/{station_id}/latest")
async def get_latest_counter(
    station_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """İstasyonun son sayaç okumasını getir"""
    stmt = (
        select(LoadCounter)
        .where(LoadCounter.station_id == station_id)
        .order_by(LoadCounter.recorded_at.desc())
    )
    counter = session.exec(stmt).first()
    
    if not counter:
        return None
    
    station = session.get(Station, counter.station_id)
    
    return {
        "id": str(counter.id),
        "station_id": str(counter.station_id),
        "station_name": station.name if station else "",
        "counter_value": counter.counter_value,
        "recorded_at": counter.recorded_at.isoformat()
    }
