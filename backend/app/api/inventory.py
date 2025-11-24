"""
Inventory API
İstasyon stok yönetimi
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict
from uuid import UUID
from datetime import datetime

from app.core.database import get_session
from app.models import StationInventory, Station, Product

router = APIRouter()

@router.get("/station/{station_id}")
async def get_station_inventory(
    station_id: UUID,
    session: Session = Depends(get_session)
):
    """İstasyonun tüm ürün stoklarını getir"""
    # İstasyon kontrolü
    station = session.get(Station, station_id)
    if not station:
        raise HTTPException(404, "İstasyon bulunamadı")
    
    # Tüm ürünleri al (display_order'a göre sıralı)
    products = session.exec(
        select(Product).order_by(Product.display_order, Product.code)
    ).all()
    
    # Mevcut stokları al
    inventories = session.exec(
        select(StationInventory).where(StationInventory.station_id == station_id)
    ).all()
    
    # Stokları product_id ile map et
    inventory_map = {str(inv.product_id): inv for inv in inventories}
    
    # Response hazırla
    result = []
    for product in products:
        inv = inventory_map.get(str(product.id))
        result.append({
            "product_id": str(product.id),
            "product_code": product.code,
            "product_name": product.name,
            "quantity_carton": inv.quantity_carton if inv else 0,
            "quantity_pack": inv.quantity_pack if inv else 0,
            "updated_at": inv.updated_at.isoformat() if inv else None
        })
    
    return {
        "station_id": str(station_id),
        "station_name": station.name,
        "products": result
    }

@router.post("/station/{station_id}")
async def update_station_inventory(
    station_id: UUID,
    payload: Dict,
    session: Session = Depends(get_session)
):
    """İstasyon stoklarını güncelle"""
    # İstasyon kontrolü
    station = session.get(Station, station_id)
    if not station:
        raise HTTPException(404, "İstasyon bulunamadı")
    
    products_data: List[Dict] = payload.get("products", [])
    
    for item in products_data:
        product_id = UUID(item.get("product_id"))
        qty_carton = int(item.get("quantity_carton", 0))
        qty_pack = int(item.get("quantity_pack", 0))
        
        # Mevcut kaydı bul
        existing = session.exec(
            select(StationInventory).where(
                StationInventory.station_id == station_id,
                StationInventory.product_id == product_id
            )
        ).first()
        
        if existing:
            # Güncelle
            existing.quantity_carton = qty_carton
            existing.quantity_pack = qty_pack
            existing.updated_at = datetime.utcnow()
            session.add(existing)
        else:
            # Yeni kayıt
            new_inv = StationInventory(
                station_id=station_id,
                product_id=product_id,
                quantity_carton=qty_carton,
                quantity_pack=qty_pack
            )
            session.add(new_inv)
    
    session.commit()
    
    return {"success": True, "message": "Stoklar güncellendi"}
