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
from app.api.auth import get_current_user, require_depot

router = APIRouter()

@router.post("/import")
async def import_cycle(
    file: UploadFile = File(...),
    run_time: str = Form(...),
    plan_date: str = Form(...),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """Excel dosyası yükle ve yeni döngü oluştur"""
    depot_id = current_user.get("depot_id")
    if not depot_id:
        raise HTTPException(403, "Bu işlem için bir depoya atanmış olmanız gerekir")

    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(400, "Sadece Excel dosyaları desteklenir (.xlsx, .xls)")

        content = await file.read()
        plan_date_obj = date.fromisoformat(plan_date)

        # Aktif döngüde aynı dosya adı var mı kontrol et - DEPOT FİLTRESİ
        from app.models import CycleImport
        stmt = select(Cycle).where(
            Cycle.plan_date == plan_date_obj,
            Cycle.status == "active",
            Cycle.depot_id == depot_id
        ).order_by(Cycle.imported_at.desc())
        active_cycle = session.exec(stmt).first()

        if active_cycle:
            stmt = select(CycleImport).where(
                CycleImport.cycle_id == active_cycle.id,
                CycleImport.filename == file.filename
            )
            existing_import = session.exec(stmt).first()
            if existing_import:
                raise HTTPException(400, "Bu dosya zaten yüklendi")

        # Cycle Manager ile import et - depot_id parametresi
        manager = CycleManager(session)
        cycle, batch_number = manager.create_cycle(run_time, plan_date_obj, content, depot_id=depot_id)

        parser = ExcelParser(content)
        parser.validate_and_parse()
        stats = parser.get_statistics()

        import hashlib
        from app.models import CycleImport
        file_hash = hashlib.sha256(content).hexdigest()
        ci = CycleImport(
            cycle_id=cycle.id,
            batch_number=batch_number,
            filename=file.filename or "excel.xlsx",
            file_size=len(content),
            file_hash=file_hash,
            depot_id=depot_id,
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
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """Bir döngüdeki Excel import geçmişini sırayla getirir"""
    from app.models import CycleImport, Order
    from sqlmodel import select, func

    cycle = session.get(Cycle, cycle_id)
    if not cycle:
        return []

    stmt = select(CycleImport).where(CycleImport.cycle_id == cycle_id).order_by(CycleImport.batch_number)
    items = session.exec(stmt).all()

    result_list = []
    for x in items:
        stmt = select(
            func.min(Order.order_date),
            func.max(Order.order_date)
        ).where(
            Order.cycle_id == cycle_id,
            Order.import_batch == x.batch_number
        )
        result = session.exec(stmt).first()

        first_time = None
        last_time = None
        if result and result[0] and result[1]:
            first_time = result[0].strftime('%H:%M')
            last_time = result[1].strftime('%H:%M')

        result_list.append({
            "id": str(x.id),
            "batch_number": x.batch_number,
            "filename": x.filename,
            "file_size": x.file_size,
            "uploaded_at": x.uploaded_at.isoformat(),
            "plan_date": str(cycle.plan_date),
            "first_delivery_time": first_time,
            "last_delivery_time": last_time
        })

    return result_list

@router.get("/{cycle_id}/status")
async def get_cycle_status(
    cycle_id: UUID,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """Döngü durumu"""
    cycle = session.get(Cycle, cycle_id)
    if not cycle:
        raise HTTPException(404, "Döngü bulunamadı")

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
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Yeni döngü başlat - Döngüye ve DEPOYA özgü verileri sil
    NOT: Station'lar, StationTerritoryMap, StationInventory ve Product'lar korunur!
    """
    depot_id = current_user.get("depot_id")
    if not depot_id:
        raise HTTPException(403, "Bu işlem için bir depoya atanmış olmanız gerekir")

    from app.models import (
        Territory, Dealer, Product, Order, OrderLine,
        Loadsheet, LoadsheetLine, Station, StationAssignment,
        LoadCounter, RevisionDiff, CycleImport
    )
    from app.models.inventory import StockMovement

    try:
        # TÜM verileri sil - SADECE BU DEPOYA AİT
        # Sıralama önemli: önce bağımlı tablolar, sonra parent tablolar

        # 1. StockMovement
        for item in session.exec(select(StockMovement).where(StockMovement.depot_id == depot_id)).all():
            session.delete(item)

        # 2. LoadsheetLine (Loadsheet üzerinden depot filtresi)
        depot_loadsheets = session.exec(select(Loadsheet).where(Loadsheet.depot_id == depot_id)).all()
        depot_loadsheet_ids = [ls.id for ls in depot_loadsheets]
        if depot_loadsheet_ids:
            for item in session.exec(select(LoadsheetLine).where(LoadsheetLine.loadsheet_id.in_(depot_loadsheet_ids))).all():
                session.delete(item)

        # 3. Loadsheet
        for item in depot_loadsheets:
            session.delete(item)

        # 4. StationAssignment
        for item in session.exec(select(StationAssignment).where(StationAssignment.depot_id == depot_id)).all():
            session.delete(item)

        # 5. OrderLine (Order üzerinden depot filtresi)
        depot_orders = session.exec(select(Order).where(Order.depot_id == depot_id)).all()
        depot_order_ids = [o.id for o in depot_orders]
        if depot_order_ids:
            for item in session.exec(select(OrderLine).where(OrderLine.order_id.in_(depot_order_ids))).all():
                session.delete(item)

        # 6. Order
        for item in depot_orders:
            session.delete(item)

        # 7. LoadCounter
        for item in session.exec(select(LoadCounter).where(LoadCounter.depot_id == depot_id)).all():
            session.delete(item)

        # 8. RevisionDiff
        for item in session.exec(select(RevisionDiff).where(RevisionDiff.depot_id == depot_id)).all():
            session.delete(item)

        # 9. CycleImport
        for item in session.exec(select(CycleImport).where(CycleImport.depot_id == depot_id)).all():
            session.delete(item)

        # 10. Cycle
        for item in session.exec(select(Cycle).where(Cycle.depot_id == depot_id)).all():
            session.delete(item)

        # 11. Dealer
        for item in session.exec(select(Dealer).where(Dealer.depot_id == depot_id)).all():
            session.delete(item)

        # 12. Territory
        for item in session.exec(select(Territory).where(Territory.depot_id == depot_id)).all():
            session.delete(item)

        session.commit()

        return {
            "success": True,
            "message": "Döngü verileri silindi. Station'lar, stoklar ve ürünler korundu. Yeni döngü başlatmaya hazır.",
            "can_start_next_cycle": True
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Veri silme hatası: {str(e)}")


@router.get("/active")
async def get_active_cycle(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """En son aktif döngüyü getir (depo bazlı)"""
    depot_id = current_user.get("depot_id")

    # DEPOT FİLTRESİ
    stmt = select(Cycle).where(
        Cycle.status == "active"
    )
    if depot_id:
        stmt = stmt.where(Cycle.depot_id == depot_id)
    stmt = stmt.order_by(Cycle.imported_at.desc())

    cycle = session.exec(stmt).first()

    if not cycle:
        return {"cycle": None, "has_active_cycle": False}

    stmt = select(Loadsheet).where(Loadsheet.cycle_id == cycle.id)
    loadsheets = session.exec(stmt).all()

    total = len(loadsheets)
    completed = len([ls for ls in loadsheets if ls.status == "loaded"])
    pending = len([ls for ls in loadsheets if ls.status == "pending"])

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
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """Döngünün revizyonlarını getir"""
    return {
        "cycle_id": str(cycle_id),
        "revisions": [],
        "message": "Revizyon tespiti FAZ 3'te implement edilecek"
    }
