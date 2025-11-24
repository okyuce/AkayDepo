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
from app.models import (
    TerritoryInfo, Station, StationTerritoryMap, PlanningConfig
)

router = APIRouter()

@router.get("/config")
async def get_config(session: Session = Depends(get_session)):
    cfg = session.exec(select(PlanningConfig)).first()
    auto_planning = cfg.auto_planning_enabled if cfg else True

    stations = session.exec(select(Station)).all()
    assignments = session.exec(select(StationTerritoryMap)).all()
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
    session: Session = Depends(get_session),
):
    auto = bool(payload.get("auto_planning_enabled", True))
    items: List[Dict] = payload.get("assignments", [])

    # Upsert config (single row)
    cfg = session.exec(select(PlanningConfig)).first()
    if not cfg:
        cfg = PlanningConfig(auto_planning_enabled=auto)
    else:
        cfg.auto_planning_enabled = auto
    session.add(cfg)

    # Validate: only in manual mode (when auto=False)
    if not auto:
        active_territories = [t.code for t in session.exec(select(TerritoryInfo).where(TerritoryInfo.is_active == True)).all()]
        assigned_codes = [i.get("territory_code") for i in items]

        missing = sorted(set(active_territories) - set(assigned_codes))
        dup = sorted([c for c in set(assigned_codes) if assigned_codes.count(c) > 1])

        if missing:
            raise HTTPException(400, detail={"error": "unassigned_territories", "territories": missing})
        if dup:
            raise HTTPException(400, detail={"error": "duplicate_territories", "territories": dup})

    # Replace-all semantics
    for existing in session.exec(select(StationTerritoryMap)).all():
        session.delete(existing)
    session.flush()

    # Insert new
    for it in items:
        station_id = it.get("station_id")
        code = it.get("territory_code")
        if not station_id or not code:
            continue
        stm = StationTerritoryMap(station_id=UUID(station_id), territory_code=code)
        session.add(stm)

    session.commit()

    return {"success": True}

@router.post("/reset")
async def reset_mapping(session: Session = Depends(get_session)):
    # Delete all mappings, keep config as-is
    for existing in session.exec(select(StationTerritoryMap)).all():
        session.delete(existing)
    session.commit()
    return {"success": True}