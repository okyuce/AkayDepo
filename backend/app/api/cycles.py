"""
Cycles API Router
Döngü yönetimi endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from datetime import date
from typing import Optional
from uuid import UUID

from app.core.database import get_session
from app.models import Cycle, Loadsheet, StationAssignment
from app.services.cycle_manager import CycleManager
from app.services.excel_parser import ExcelParser, ExcelParseError

router = APIRouter()

@router.post("/import")
async def import_cycle(
    file: UploadFile = File(...),
    run_time: str = Form(...),
    plan_date: str = Form(...),
    session: Session = Depends(get_session)
):
    """
    Excel dosyası yükle ve yeni döngü oluştur
    
    Args:
        file: Excel dosyası
        run_time: "14:00", "16:00", "17:00"
        plan_date: "2025-11-07"
    """
    try:
        # Dosya formatı kontrolü
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(400, "Sadece Excel dosyaları desteklenir (.xlsx, .xls)")
        
        # Dosyayı oku
        content = await file.read()
        
        # Tarihi parse et
        plan_date_obj = date.fromisoformat(plan_date)
        
        # Cycle Manager ile import et
        manager = CycleManager(session)
        cycle, batch_number = manager.create_cycle(run_time, plan_date_obj, content)
        
        # İstatistikleri hesapla
        parser = ExcelParser(content)
        parser.validate_and_parse()
        stats = parser.get_statistics()

        # Import geçmişini kaydet
        import hashlib
        from app.models import CycleImport
        file_hash = hashlib.sha256(content).hexdigest()
        ci = CycleImport(
            cycle_id=cycle.id,
            batch_number=batch_number,
            filename=file.filename or "excel.xlsx",
            file_size=len(content),
            file_hash=file_hash,
        )
        session.add(ci)
        session.commit()
        
        return {
            "cycle_id": str(cycle.id),
            "cycle_no": cycle.cycle_no,
            "run_time": cycle.run_time,
            "plan_date": str(cycle.plan_date),
            "status": cycle.status,
            "batch_number": batch_number,
            **stats
        }
        
    except ExcelParseError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Import hatası: {str(e)}")


@router.get("/{cycle_id}/imports")
async def list_cycle_imports(
    cycle_id: UUID,
    session: Session = Depends(get_session)
):
    """Bir döngüdeki Excel import geçmişini sırayla getirir"""
    from app.models import CycleImport
    from sqlmodel import select
    stmt = select(CycleImport).where(CycleImport.cycle_id == cycle_id).order_by(CycleImport.batch_number)
    items = session.exec(stmt).all()
    return [
        {
            "id": str(x.id),
            "batch_number": x.batch_number,
            "filename": x.filename,
            "file_size": x.file_size,
            "uploaded_at": x.uploaded_at.isoformat()
        }
        for x in items
    ]

@router.get("/{cycle_id}/status")
async def get_cycle_status(
    cycle_id: UUID,
    session: Session = Depends(get_session)
):
    """Döngü durumu"""
    cycle = session.get(Cycle, cycle_id)
    if not cycle:
        raise HTTPException(404, "Döngü bulunamadı")
    
    # Fiş istatistikleri
    stmt = select(Loadsheet).where(Loadsheet.cycle_id == cycle_id)
    loadsheets = session.exec(stmt).all()
    
    total = len(loadsheets)
    completed = len([ls for ls in loadsheets if ls.status == "loaded"])
    pending = len([ls for ls in loadsheets if ls.status == "pending"])
    cancelled = len([ls for ls in loadsheets if ls.status == "cancelled"])
    
    can_start_next = pending == 0
    warnings = []
    if pending > 0:
        warnings.append(f"{pending} fiş henüz tamamlanmadı")
    
    return {
        "cycle_id": str(cycle.id),
        "cycle_no": cycle.cycle_no,
        "run_time": cycle.run_time,
        "plan_date": str(cycle.plan_date),
        "status": cycle.status,
        "total_loadsheets": total,
        "completed_loadsheets": completed,
        "pending_loadsheets": pending,
        "cancelled_loadsheets": cancelled,
        "can_start_next_cycle": can_start_next,
        "warnings": warnings
    }


@router.post("/{cycle_id}/cancel-pending")
async def cancel_pending(
    cycle_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Döngüdeki tüm pending fişleri iptal et ve döngüyü tamamla
    Bu endpoint 'Yeni Döngü Başlat' butonu için kullanılır.
    """
    cycle = session.get(Cycle, cycle_id)
    if not cycle:
        raise HTTPException(404, "Döngü bulunamadı")
    
    manager = CycleManager(session)
    
    # Pending fişleri iptal et
    cancelled_count = manager.cancel_pending_loadsheets(cycle_id)
    
    # Döngüyü tamamla (completed status)
    manager.complete_cycle(cycle_id)
    
    return {
        "cycle_id": str(cycle_id),
        "cancelled_count": cancelled_count,
        "cycle_completed": True,
        "can_start_next_cycle": True
    }


@router.get("/active")
async def get_active_cycle(
    session: Session = Depends(get_session)
):
    """En son aktif döngüyü getir (tarih bağımsız)"""
    # En son aktif cycle'i bul (tarih filtresi olmadan)
    stmt = select(Cycle).where(
        Cycle.status == "active"
    ).order_by(Cycle.imported_at.desc())
    
    cycle = session.exec(stmt).first()
    
    if not cycle:
        return {"cycle": None, "has_active_cycle": False}
    
    # Fiş istatistikleri
    stmt = select(Loadsheet).where(Loadsheet.cycle_id == cycle.id)
    loadsheets = session.exec(stmt).all()
    
    total = len(loadsheets)
    completed = len([ls for ls in loadsheets if ls.status == "loaded"])
    pending = len([ls for ls in loadsheets if ls.status == "pending"])
    
    # Plan var mı kontrol et
    stmt = select(StationAssignment).where(StationAssignment.cycle_id == cycle.id)
    has_plan = session.exec(stmt).first() is not None
    
    return {
        "has_active_cycle": True,
        "cycle": {
            "id": str(cycle.id),
            "cycle_no": cycle.cycle_no,
            "run_time": cycle.run_time,
            "plan_date": str(cycle.plan_date),
            "status": cycle.status,
            "fixed_station_count": getattr(cycle, 'fixed_station_count', None),
            "has_plan": has_plan,
            "total_loadsheets": total,
            "completed_loadsheets": completed,
            "pending_loadsheets": pending
        }
    }


@router.get("/{cycle_id}/revisions")
async def get_revisions(
    cycle_id: UUID,
    session: Session = Depends(get_session)
):
    """Döngünün revizyonlarını getir (FAZ 3'te implement edilecek)"""
    return {
        "cycle_id": str(cycle_id),
        "revisions": [],
        "message": "Revizyon tespiti FAZ 3'te implement edilecek"
    }
