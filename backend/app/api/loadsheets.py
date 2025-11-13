"""
Loadsheets API Router
Tablet için fiş yönetimi endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.database import get_session
from app.core.websocket import manager
from app.models import (
    Loadsheet, LoadsheetLine, Station, StationAssignment, 
    Territory, Dealer, Product, LoadCounter
)

router = APIRouter()

@router.get("/station/{station_id}")
async def get_station_loadsheets(
    station_id: UUID,
    cycle_id: Optional[UUID] = None,
    session: Session = Depends(get_session)
):
    """
    İstasyonun fişlerini getir (Tablet görünümü için)
    
    Args:
        station_id: İstasyon ID
        cycle_id: Döngü ID (opsiyonel, yoksa son aktif döngü)
    """
    try:
        # Cycle belirle
        if not cycle_id:
            from app.models import Cycle
            stmt = select(Cycle).where(Cycle.status == "active").order_by(Cycle.imported_at.desc())
            cycle = session.exec(stmt).first()
            if not cycle:
                raise HTTPException(404, "Aktif döngü bulunamadı")
            cycle_id = cycle.id
        
        # Station assignments al
        stmt = select(StationAssignment).where(
            StationAssignment.cycle_id == cycle_id,
            StationAssignment.station_id == station_id
        )
        assignments = session.exec(stmt).all()
        
        if not assignments:
            return {
                "station_id": str(station_id),
                "cycle_id": str(cycle_id),
                "territories": [],
                "total_carton": 0,
                "completed_carton": 0
            }
        
        # Territory bazında fişleri grupla
        territories_data = []
        total_carton = 0
        completed_carton = 0
        
        for assignment in assignments:
            territory = session.get(Territory, assignment.territory_id)
            
            # Bu territory'nin fişleri - route_order ile sırala
            stmt = (
                select(Loadsheet)
                .join(Dealer, Loadsheet.dealer_id == Dealer.id)
                .where(Loadsheet.assignment_id == assignment.id)
                .order_by(Dealer.route_order)
            )
            loadsheets = session.exec(stmt).all()
            
            # Fiş detayları
            loadsheet_data = []
            territory_completed = 0
            
            for ls in loadsheets:
                dealer = session.get(Dealer, ls.dealer_id)
                
                # Toplam karton hesapla
                stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == ls.id)
                lines = session.exec(stmt).all()
                ls_total_carton = sum(line.qty_carton + (line.qty_pack / 10) for line in lines)
                
                loadsheet_data.append({
                    "id": str(ls.id),
                    "package_number": ls.package_number,
                    "dealer_code": dealer.code if dealer else "",
                    "dealer_name": dealer.name if dealer else "",
                    "route_order": dealer.route_order if dealer else 0,
                    "total_carton": round(ls_total_carton, 1),
                    "status": ls.status,
                    "batch_number": ls.batch_number,
                    "loadsheet_type": ls.loadsheet_type,
                    "completed_at": ls.completed_at.isoformat() if ls.completed_at else None,
                    "is_revision": ls.is_revision,
                    "parent_loadsheet_id": str(ls.parent_loadsheet_id) if ls.parent_loadsheet_id else None,
                    "loaded_at": ls.loaded_at.isoformat() if ls.loaded_at else None
                })
                
                if ls.status == "loaded":
                    territory_completed += ls_total_carton
            
            territory_total = assignment.target_total_carton
            progress_percent = int((territory_completed / territory_total * 100)) if territory_total > 0 else 0
            
            territories_data.append({
                "territory_code": territory.code if territory else "",
                "display_number": territory.display_number if territory else "",
                "name": territory.name if territory else "",
                "total_carton": territory_total,
                "completed_carton": round(territory_completed, 1),
                "progress_percent": progress_percent,
                "status": "completed" if progress_percent == 100 else "in_progress",
                "loadsheets": loadsheet_data
            })
            
            total_carton += territory_total
            completed_carton += territory_completed
        
        # Genel progress
        overall_progress = int((completed_carton / total_carton * 100)) if total_carton > 0 else 0
        
        return {
            "station_id": str(station_id),
            "cycle_id": str(cycle_id),
            "total_carton": total_carton,
            "completed_carton": round(completed_carton, 1),
            "remaining_carton": round(total_carton - completed_carton, 1),
            "progress_percent": overall_progress,
            "territories": territories_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Fişler getirme hatası: {str(e)}")


@router.get("/{loadsheet_id}")
async def get_loadsheet_detail(
    loadsheet_id: UUID,
    session: Session = Depends(get_session)
):
    """Fiş detayı"""
    loadsheet = session.get(Loadsheet, loadsheet_id)
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    
    # Dealer
    dealer = session.get(Dealer, loadsheet.dealer_id)
    
    # Territory
    assignment = session.get(StationAssignment, loadsheet.assignment_id)
    territory = session.get(Territory, assignment.territory_id) if assignment else None
    
    # Lines
    stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == loadsheet_id)
    lines = session.exec(stmt).all()
    
    lines_data = []
    total_carton = 0
    
    for line in lines:
        product = session.get(Product, line.product_id)
        line_total = line.qty_carton + (line.qty_pack / 10)
        total_carton += line_total
        
        lines_data.append({
            "product_code": product.code if product else "",
            "product_name": product.name if product else "",
            "qty_carton": line.qty_carton,
            "qty_pack": line.qty_pack
        })
    
    # Revizyon ise değişiklikleri hesapla
    changes = None
    if loadsheet.is_revision and loadsheet.parent_loadsheet_id:
        changes = []
        for line in lines:
            product = session.get(Product, line.product_id)
            change_type = "addition" if line.qty_carton > 0 else "reduction"
            
            changes.append({
                "product_code": product.code if product else "",
                "product_name": product.name if product else "",
                "qty_change_carton": line.qty_carton,
                "change_type": change_type
            })
    
    return {
        "id": str(loadsheet.id),
        "package_number": loadsheet.package_number,
        "dealer": {
            "code": dealer.code if dealer else "",
            "name": dealer.name if dealer else "",
            "route_order": dealer.route_order if dealer else 0
        },
        "territory": {
            "code": territory.code if territory else "",
            "display_number": territory.display_number if territory else "",
            "name": territory.name if territory else ""
        },
        "lines": lines_data,
        "total_carton": round(total_carton, 1),
        "status": loadsheet.status,
        "is_revision": loadsheet.is_revision,
        "parent_loadsheet_id": str(loadsheet.parent_loadsheet_id) if loadsheet.parent_loadsheet_id else None,
        "changes": changes,
        "loaded_at": loadsheet.loaded_at.isoformat() if loadsheet.loaded_at else None
    }


@router.post("/{loadsheet_id}/complete")
async def complete_loadsheet(
    loadsheet_id: UUID,
    session: Session = Depends(get_session)
):
    """Fişi tamamla (Yükleme Tamamlandı)"""
    loadsheet = session.get(Loadsheet, loadsheet_id)
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    
    # Durumu güncelle
    loadsheet.status = "loaded"
    loadsheet.loaded_at = datetime.utcnow()
    loadsheet.completed_at = datetime.utcnow()
    session.add(loadsheet)
    session.commit()
    
    # Territory tamamlandı mı kontrol et
    assignment = session.get(StationAssignment, loadsheet.assignment_id)
    stmt = select(Loadsheet).where(Loadsheet.assignment_id == assignment.id)
    all_loadsheets = session.exec(stmt).all()
    
    territory_completed = all(ls.status == "loaded" for ls in all_loadsheets)
    
    # WebSocket bildirimi gönder
    await manager.notify_loadsheet_completed(
        station_id=assignment.station_id,
        loadsheet_id=loadsheet_id,
        package_number=loadsheet.package_number,
        territory_completed=territory_completed
    )
    
    return {
        "loadsheet_id": str(loadsheet_id),
        "status": "loaded",
        "loaded_at": loadsheet.loaded_at.isoformat(),
        "territory_completed": territory_completed
    }
