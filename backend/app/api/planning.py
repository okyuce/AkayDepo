"""
Planning API Router
İstasyon planlama endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.core.database import get_session
from app.api.auth import get_current_user, verify_depot_access
from app.services.station_planner import StationPlanner
from app.services.loadsheet_generator import LoadsheetGenerator

router = APIRouter()

class PlanRequest(BaseModel):
    worker_count: int
    force_station_count: Optional[int] = None
    method: str = "greedy"

@router.post("/{cycle_id}/plan")
async def create_plan(
    cycle_id: UUID,
    request: PlanRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    İstasyon planı oluştur
    
    Args:
        cycle_id: Döngü ID
        worker_count: Depocu sayısı
        force_station_count: Zorla istasyon sayısı (opsiyonel)
        method: "greedy" (varsayılan)
    """
    depot_id = current_user.get("depot_id")
    try:
        from app.models import Cycle
        cycle = session.get(Cycle, cycle_id)
        if not cycle:
            raise HTTPException(404, "Döngü bulunamadı")
        verify_depot_access(cycle, depot_id, "Döngü")

        planner = StationPlanner(session)
        plan = planner.create_plan(
            cycle_id=cycle_id,
            worker_count=request.worker_count,
            force_station_count=request.force_station_count,
            method=request.method,
            depot_id=depot_id
        )

        # Fişleri oluştur (yalnızca son batch)
        from app.models import Order
        from sqlmodel import select
        latest_batch = session.exec(select(Order.import_batch).where(Order.cycle_id==cycle_id).order_by(Order.import_batch.desc())).first()
        generator = LoadsheetGenerator(session)
        loadsheet_count = generator.generate_loadsheets_for_cycle(cycle_id, only_batch=latest_batch, depot_id=depot_id)
        
        plan["loadsheet_count"] = loadsheet_count
        
        return plan
        
    except Exception as e:
        raise HTTPException(500, f"Plan oluşturma hatası: {str(e)}")


@router.get("/{cycle_id}/plan")
async def get_plan(
    cycle_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Mevcut planı getir"""
    try:
        from app.models import StationAssignment, Territory, Cycle
        from sqlmodel import select

        depot_id = current_user.get("depot_id")
        cycle = session.get(Cycle, cycle_id)
        if not cycle:
            raise HTTPException(404, "Döngü bulunamadı")
        verify_depot_access(cycle, depot_id, "Döngü")

        # Assignments al
        stmt = select(StationAssignment).where(StationAssignment.cycle_id == cycle_id)
        assignments = session.exec(stmt).all()
        
        if not assignments:
            raise HTTPException(404, "Plan bulunamadı")
        
        # İstasyonlara göre grupla (station_id'ye göre)
        from app.models import Station
        
        stations_dict = {}
        for assignment in assignments:
            station_id = str(assignment.station_id)
            
            if station_id not in stations_dict:
                station = session.get(Station, assignment.station_id)
                station_name = station.name if station else f"İstasyon-{assignment.load_rank}"
                
                stations_dict[station_id] = {
                    "station_id": station_id,
                    "station_name": station_name,
                    "total_carton": 0,
                    "territories": []
                }
            
            # Territory bilgisi
            territory = session.get(Territory, assignment.territory_id)
            
            stations_dict[station_id]["total_carton"] += assignment.target_total_carton
            stations_dict[station_id]["territories"].append({
                "territory_code": territory.code if territory else "Unknown",
                "display_number": territory.display_number if territory else "T00",
                "carton": assignment.target_total_carton,
                "load_rank": assignment.load_rank
            })
        
        # İstasyonları station_name'e göre sırala
        stations_list = sorted(stations_dict.values(), key=lambda x: x["station_name"])
        
        return {
            "cycle_id": str(cycle_id),
            "stations": stations_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Plan getirme hatası: {str(e)}")
