"""
SuperAdmin API Router
Çoklu depo yönetimi - kullanıcı ve depo başlatma
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.database import get_session
from app.api.auth import require_superadmin
from app.models import User, Depot, Station

router = APIRouter()


class SuperAdminUserCreate(BaseModel):
    username: str
    password: str = Field(min_length=6)
    full_name: Optional[str] = None
    role: str  # admin, tablet, superadmin
    depot_id: Optional[str] = None  # UUID string
    station_id: Optional[str] = None  # UUID string


class SuperAdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    depot_id: Optional[str] = None
    station_id: Optional[str] = None
    is_active: Optional[bool] = None
    new_password: Optional[str] = None


class DepotInitRequest(BaseModel):
    worker_count: int = 1  # Depoculu sayısı (tablet kullanıcı + istasyon)


# --- Kullanıcı Yönetimi ---

@router.get("/users")
async def list_all_users(
    depot_id: Optional[UUID] = None,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_superadmin)
):
    """Tüm kullanıcıları listele (opsiyonel depo filtresi)"""
    stmt = select(User).order_by(User.created_at)
    if depot_id:
        stmt = stmt.where(User.depot_id == depot_id)

    users = session.exec(stmt).all()

    result = []
    for user in users:
        # Depo bilgisi
        depot = session.get(Depot, user.depot_id) if user.depot_id else None
        # İstasyon bilgisi
        station = session.get(Station, user.station_id) if user.station_id else None

        result.append({
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "depot_id": str(user.depot_id) if user.depot_id else None,
            "depot_code": depot.code if depot else None,
            "depot_name": depot.name if depot else None,
            "station_id": str(user.station_id) if user.station_id else None,
            "station_name": station.name if station else None,
            "created_at": user.created_at.isoformat(),
        })

    return result


@router.post("/users")
async def create_user(
    data: SuperAdminUserCreate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_superadmin)
):
    """Herhangi bir depoda kullanıcı oluştur"""
    # Username unique kontrolü
    existing = session.exec(select(User).where(User.username == data.username)).first()
    if existing:
        raise HTTPException(400, f"'{data.username}' kullanıcı adı zaten mevcut")

    # Role kontrolü
    if data.role not in ("admin", "tablet", "superadmin"):
        raise HTTPException(400, "Geçersiz rol. admin, tablet veya superadmin olmalı")

    # Depot kontrolü
    depot_id = None
    if data.depot_id:
        depot = session.get(Depot, UUID(data.depot_id))
        if not depot:
            raise HTTPException(404, "Depo bulunamadı")
        depot_id = depot.id

    # Station kontrolü
    station_id = None
    if data.station_id:
        station = session.get(Station, UUID(data.station_id))
        if not station:
            raise HTTPException(404, "İstasyon bulunamadı")
        station_id = station.id

    user = User(
        username=data.username,
        full_name=data.full_name,
        role=data.role,
        depot_id=depot_id,
        station_id=station_id,
        is_active=True,
    )
    user.set_password(data.password)
    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "id": str(user.id),
        "username": user.username,
        "role": user.role,
        "depot_id": str(user.depot_id) if user.depot_id else None,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    data: SuperAdminUserUpdate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_superadmin)
):
    """Kullanıcı güncelle (depo, rol, şifre dahil)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        if data.role not in ("admin", "tablet", "superadmin"):
            raise HTTPException(400, "Geçersiz rol")
        user.role = data.role
    if data.depot_id is not None:
        if data.depot_id == "":
            user.depot_id = None
        else:
            depot = session.get(Depot, UUID(data.depot_id))
            if not depot:
                raise HTTPException(404, "Depo bulunamadı")
            user.depot_id = depot.id
    if data.station_id is not None:
        if data.station_id == "":
            user.station_id = None
        else:
            station = session.get(Station, UUID(data.station_id))
            if not station:
                raise HTTPException(404, "İstasyon bulunamadı")
            user.station_id = station.id
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.new_password:
        user.set_password(data.new_password)

    user.updated_at = datetime.now()
    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "id": str(user.id),
        "username": user.username,
        "role": user.role,
        "depot_id": str(user.depot_id) if user.depot_id else None,
        "is_active": user.is_active,
    }


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_superadmin)
):
    """Kullanıcıyı pasifleştir"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı")

    if user.role == "superadmin":
        # Başka aktif superadmin var mı kontrol et
        other_superadmins = session.exec(
            select(User).where(
                User.role == "superadmin",
                User.is_active == True,
                User.id != user_id
            )
        ).all()
        if not other_superadmins:
            raise HTTPException(400, "Son superadmin pasifleştirilemez")

    user.is_active = False
    user.updated_at = datetime.now()
    session.add(user)
    session.commit()

    return {"success": True, "message": f"{user.username} pasifleştirildi"}


# --- Depo Başlatma ---

@router.post("/depots/{depot_id}/init")
async def init_depot(
    depot_id: UUID,
    data: DepotInitRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_superadmin)
):
    """
    Depo başlat - admin + tablet kullanıcıları + istasyonlar + AnaStok oluştur

    Args:
        depot_id: Depo UUID
        worker_count: Depoculu sayısı (1 veya 2)
    """
    depot = session.get(Depot, depot_id)
    if not depot:
        raise HTTPException(404, "Depo bulunamadı")

    # Mevcut kullanıcı ve istasyonları temizle (yeniden başlatma desteği)
    existing_users = session.exec(
        select(User).where(User.depot_id == depot.id)
    ).all()
    for u in existing_users:
        session.delete(u)

    existing_stations = session.exec(
        select(Station).where(Station.depot_id == depot.id)
    ).all()
    for s in existing_stations:
        session.delete(s)

    session.flush()

    created_items = {
        "admin_user": None,
        "tablet_users": [],
        "stations": [],
        "main_stock": None,
    }

    depot_code_lower = depot.code.lower()

    # 1. Admin kullanıcı oluştur
    admin_username = f"admin_{depot_code_lower}"
    admin_user = User(
        username=admin_username,
        full_name=f"{depot.name} Admin",
        role="admin",
        depot_id=depot.id,
        is_active=True,
    )
    admin_user.set_password("admin123")
    session.add(admin_user)
    created_items["admin_user"] = admin_username

    # 2. AnaStok istasyonu oluştur
    main_stock = Station(
        name="AnaStok",
        active=True,
        is_main_stock=True,
        depot_id=depot.id,
    )
    session.add(main_stock)
    session.flush()
    created_items["main_stock"] = "AnaStok"

    # 3. Tablet kullanıcıları ve istasyonlar oluştur
    for i in range(1, data.worker_count + 1):
        # İstasyon
        station = Station(
            name=f"İstasyon-{i}",
            active=True,
            depot_id=depot.id,
        )
        session.add(station)
        session.flush()

        # Tablet kullanıcısı
        tablet_username = f"tablet{i}_{depot_code_lower}"
        tablet_user = User(
            username=tablet_username,
            full_name=f"{depot.name} Tablet-{i}",
            role="tablet",
            depot_id=depot.id,
            station_id=station.id,
            is_active=True,
        )
        tablet_user.set_password("tablet123")
        session.add(tablet_user)

        created_items["tablet_users"].append(tablet_username)
        created_items["stations"].append(f"İstasyon-{i}")

    session.commit()

    return {
        "success": True,
        "depot": depot.name,
        "created": created_items,
    }
