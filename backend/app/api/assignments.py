"""
Assignments API
- Get/save manual territory→station mapping
- Reset mapping
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict
from uuid import UUID

from app.core.database import get_session
from app.api.auth import get_current_user
from app.models import (
    TerritoryInfo, Station, StationTerritoryMap, PlanningConfig
)

router = APIRouter()

@router.get("/config")
async def get_config(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    depot_id = current_user.get("depot_id")

    cfg_stmt = select(PlanningConfig)
    if depot_id:
        cfg_stmt = cfg_stmt.where(PlanningConfig.depot_id == depot_id)
    cfg = session.exec(cfg_stmt).first()
    auto_planning = cfg.auto_planning_enabled if cfg else True

    station_stmt = select(Station)
    if depot_id:
        station_stmt = station_stmt.where(Station.depot_id == depot_id)
    stations = session.exec(station_stmt).all()

    assign_stmt = select(StationTerritoryMap)
    if depot_id:
        assign_stmt = assign_stmt.where(StationTerritoryMap.depot_id == depot_id)
    assignments = session.exec(assign_stmt).all()
    return {
        "auto_planning_enabled": auto_planning,
        "stations": [
            {"id": str(s.id), "name": s.name, "active": s.active}
            for s in stations
        ],
        "assignments": [
            {"station_id": str(a.station_id), "territory_code": a.territory_code}
            for a in assignments
        ],
    }

@router.post("/config")
async def save_config(
    payload: Dict,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    auto = bool(payload.get("auto_planning_enabled", True))
    items: List[Dict] = payload.get("assignments", [])
    depot_id = current_user.get("depot_id")

    # Upsert config (single row)
    cfg_stmt = select(PlanningConfig)
    if depot_id:
        cfg_stmt = cfg_stmt.where(PlanningConfig.depot_id == depot_id)
    cfg = session.exec(cfg_stmt).first()
    if not cfg:
        cfg = PlanningConfig(auto_planning_enabled=auto, depot_id=depot_id)
    else:
        cfg.auto_planning_enabled = auto
    session.add(cfg)

    # Validate: only in manual mode (when auto=False)
    if not auto:
        territory_stmt = select(TerritoryInfo).where(TerritoryInfo.is_active == True)
        if depot_id:
            territory_stmt = territory_stmt.where(TerritoryInfo.depot_id == depot_id)
        active_territories = [t.code for t in session.exec(territory_stmt).all()]
        assigned_codes = [i.get("territory_code") for i in items]

        missing = sorted(set(active_territories) - set(assigned_codes))
        dup = sorted([c for c in set(assigned_codes) if assigned_codes.count(c) > 1])

        if missing:
            raise HTTPException(400, detail={"error": "unassigned_territories", "territories": missing})
        if dup:
            raise HTTPException(400, detail={"error": "duplicate_territories", "territories": dup})

    # Manuel mappingleri GÜNCELLE (otomatik modda koruyoruz, sadece manuel modda güncelliyoruz)
    if not auto:
        # Replace-all semantics (sadece manuel modda)
        del_stmt = select(StationTerritoryMap)
        if depot_id:
            del_stmt = del_stmt.where(StationTerritoryMap.depot_id == depot_id)
        for existing in session.exec(del_stmt).all():
            session.delete(existing)
        session.flush()

        # Insert new
        for it in items:
            station_id = it.get("station_id")
            code = it.get("territory_code")
            if not station_id or not code:
                continue
            stm = StationTerritoryMap(station_id=UUID(station_id), territory_code=code, depot_id=depot_id)
            session.add(stm)

    session.commit()

    return {"success": True}

@router.post("/reset")
async def reset_mapping(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Delete all mappings, keep config as-is
    depot_id = current_user.get("depot_id")
    del_stmt = select(StationTerritoryMap)
    if depot_id:
        del_stmt = del_stmt.where(StationTerritoryMap.depot_id == depot_id)
    for existing in session.exec(del_stmt).all():
        session.delete(existing)
    session.commit()
    return {"success": True}