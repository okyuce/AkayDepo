"""
Territory Info API Router
Territory tanımları yönetimi
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_session
from app.models import TerritoryInfo


class TerritoryCreate(BaseModel):
    code: str
    name: str
    display_number: str
    color: Optional[str] = None
    is_active: bool = True


class TerritoryUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    display_number: Optional[str] = None
    is_active: Optional[bool] = None
    color: Optional[str] = None

router = APIRouter()

@router.get("/")
async def list_territories(
    include_inactive: bool = False,
    session: Session = Depends(get_session)
):
    """Territory listesi"""
    stmt = select(TerritoryInfo)
    
    if not include_inactive:
        stmt = stmt.where(TerritoryInfo.is_active == True)
    
    stmt = stmt.order_by(TerritoryInfo.sort_order, TerritoryInfo.display_number)
    territories = session.exec(stmt).all()
    
    return [
        {
            "id": str(t.id),
            "code": t.code,
            "name": t.name,
            "display_number": t.display_number,
            "is_active": t.is_active,
            "color": t.color,
            "sort_order": t.sort_order
        }
        for t in territories
    ]


@router.get("/{territory_id}")
async def get_territory(
    territory_id: UUID,
    session: Session = Depends(get_session)
):
    """Territory detayı"""
    territory = session.get(TerritoryInfo, territory_id)
    if not territory:
        raise HTTPException(404, "Territory bulunamadı")
    
    return {
        "id": str(territory.id),
        "code": territory.code,
        "name": territory.name,
        "display_number": territory.display_number,
        "is_active": territory.is_active,
        "color": territory.color,
        "sort_order": territory.sort_order
    }


@router.post("/")
async def create_territory(
    data: TerritoryCreate,
    session: Session = Depends(get_session)
):
    """Yeni territory ekle"""
    # Code unique kontrolü
    stmt = select(TerritoryInfo).where(TerritoryInfo.code == data.code)
    existing = session.exec(stmt).first()
    if existing:
        raise HTTPException(400, "Bu territory kodu zaten mevcut")
    
    # Son sort_order'ı bul
    stmt = select(TerritoryInfo).order_by(TerritoryInfo.sort_order.desc())
    last = session.exec(stmt).first()
    next_sort_order = (last.sort_order + 1) if last else 1
    
    territory = TerritoryInfo(
        code=data.code,
        name=data.name,
        display_number=data.display_number,
        is_active=data.is_active,
        color=data.color,
        sort_order=next_sort_order
    )
    
    session.add(territory)
    session.commit()
    session.refresh(territory)
    
    return {
        "id": str(territory.id),
        "code": territory.code,
        "name": territory.name,
        "display_number": territory.display_number,
        "is_active": territory.is_active,
        "color": territory.color,
        "sort_order": territory.sort_order
    }


@router.put("/{territory_id}")
async def update_territory(
    territory_id: UUID,
    data: TerritoryUpdate,
    session: Session = Depends(get_session)
):
    """Territory güncelle"""
    territory = session.get(TerritoryInfo, territory_id)
    if not territory:
        raise HTTPException(404, "Territory bulunamadı")
    
    # Code unique kontrolü (eğer değiştirildiyse)
    if data.code is not None and data.code != territory.code:
        stmt = select(TerritoryInfo).where(TerritoryInfo.code == data.code)
        existing = session.exec(stmt).first()
        if existing:
            raise HTTPException(400, "Bu territory kodu zaten mevcut")
        territory.code = data.code
    
    if data.name is not None:
        territory.name = data.name
    if data.display_number is not None:
        territory.display_number = data.display_number
    if data.is_active is not None:
        territory.is_active = data.is_active
    if data.color is not None:
        territory.color = data.color
    
    session.add(territory)
    session.commit()
    session.refresh(territory)
    
    return {
        "id": str(territory.id),
        "code": territory.code,
        "name": territory.name,
        "display_number": territory.display_number,
        "is_active": territory.is_active,
        "color": territory.color,
        "sort_order": territory.sort_order
    }


@router.delete("/{territory_id}")
async def delete_territory(
    territory_id: UUID,
    session: Session = Depends(get_session)
):
    """Territory sil"""
    territory = session.get(TerritoryInfo, territory_id)
    if not territory:
        raise HTTPException(404, "Territory bulunamadı")
    
    # Kullanımda mı kontrol et (optional - gelecekte eklenebilir)
    # Şimdilik direkt silme izni ver
    
    session.delete(territory)
    session.commit()
    
    return {"success": True, "message": "Territory silindi"}


@router.post("/reorder")
async def reorder_territories(
    territory_ids: List[str],
    session: Session = Depends(get_session)
):
    """Territory sıralamasını güncelle"""
    for idx, territory_id_str in enumerate(territory_ids):
        territory_id = UUID(territory_id_str)
        territory = session.get(TerritoryInfo, territory_id)
        if territory:
            territory.sort_order = idx + 1
            session.add(territory)
    
    session.commit()
    return {"success": True, "message": "Sıralama güncellendi"}
