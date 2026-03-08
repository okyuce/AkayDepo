"""
Depots API Router
Depo yönetimi endpoint'leri (SuperAdmin)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_session
from app.api.auth import require_superadmin
from app.models import Depot, Station, User

router = APIRouter()


class DepotCreate(BaseModel):
    code: str
    name: str
    city: str


class DepotUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_depots(
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_superadmin)
):
    """Tüm depoları listele (superadmin)"""
    depots = session.exec(select(Depot).order_by(Depot.name)).all()

    result = []
    for depot in depots:
        # Kullanıcı sayısı
        user_count = len(session.exec(
            select(User).where(User.depot_id == depot.id, User.is_active == True)
        ).all())

        # Tablet kullanıcı sayısı
        tablet_count = len(session.exec(
            select(User).where(User.depot_id == depot.id, User.role == "tablet", User.is_active == True)
        ).all())

        # İstasyon sayısı
        station_count = len(session.exec(
            select(Station).where(Station.depot_id == depot.id)
        ).all())

        result.append({
            "id": str(depot.id),
            "code": depot.code,
            "name": depot.name,
            "city": depot.city,
            "is_active": depot.is_active,
            "user_count": user_count,
            "tablet_count": tablet_count,
            "station_count": station_count,
        })

    return result


@router.post("/")
async def create_depot(
    data: DepotCreate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_superadmin)
):
    """Yeni depo oluştur (superadmin)"""
    # Code unique kontrolü
    existing = session.exec(select(Depot).where(Depot.code == data.code)).first()
    if existing:
        raise HTTPException(400, "Bu depo kodu zaten mevcut")

    depot = Depot(
        code=data.code.upper(),
        name=data.name,
        city=data.city,
    )
    session.add(depot)
    session.commit()
    session.refresh(depot)

    return {
        "id": str(depot.id),
        "code": depot.code,
        "name": depot.name,
        "city": depot.city,
        "is_active": depot.is_active,
    }


@router.put("/{depot_id}")
async def update_depot(
    depot_id: UUID,
    data: DepotUpdate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_superadmin)
):
    """Depo güncelle (superadmin)"""
    depot = session.get(Depot, depot_id)
    if not depot:
        raise HTTPException(404, "Depo bulunamadı")

    if data.name is not None:
        depot.name = data.name
    if data.city is not None:
        depot.city = data.city
    if data.is_active is not None:
        depot.is_active = data.is_active

    depot.updated_at = datetime.now()
    session.add(depot)
    session.commit()
    session.refresh(depot)

    return {
        "id": str(depot.id),
        "code": depot.code,
        "name": depot.name,
        "city": depot.city,
        "is_active": depot.is_active,
    }


