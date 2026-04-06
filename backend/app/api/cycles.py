"""
Cycles API Router
Döngü yönetimi endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select, func
from sqlalchemy import case
from datetime import date
from typing import Optional
from uuid import UUID

from app.core.database import get_session
from app.core.cache import cache_get, cache_set, cache_delete_pattern
from app.models import Cycle, Loadsheet, StationAssignment
from app.services.cycle_manager import CycleManager
from app.services.excel_parser import ExcelParser, ExcelParseError
from app.api.auth import get_current_user, require_depot, verify_depot_access

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

        # Cache temizle
        cache_delete_pattern(f"active_cycle:{depot_id}")

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
    depot_id = current_user.get("depot_id")
    verify_depot_access(cycle, depot_id, "Döngü")

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

        # Batch'teki unique bayi sayısı
        dealer_stmt = select(func.count(func.distinct(Order.dealer_id))).where(
            Order.cycle_id == cycle_id,
            Order.import_batch == x.batch_number
        )
        dealer_count = session.exec(dealer_stmt).one() or 0

        result_list.append({
            "id": str(x.id),
            "batch_number": x.batch_number,
            "filename": x.filename,
            "file_size": x.file_size,
            "uploaded_at": x.uploaded_at.isoformat(),
            "plan_date": str(cycle.plan_date),
            "first_delivery_time": first_time,
            "last_delivery_time": last_time,
            "dealer_count": dealer_count
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
    depot_id = current_user.get("depot_id")
    verify_depot_access(cycle, depot_id, "Döngü")

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

    try:
        from sqlmodel import text

        # TÜM verileri sil - SADECE BU DEPOYA AİT
        # SQL DELETE ile doğrudan sil (autoflush sorununu önler)
        # Sıralama: önce child tablolar, sonra parent tablolar
        # ÖNEMLİ: Cycle_id üzerinden silme yapıyoruz (depot_id NULL olabilir)

        depot_id_str = str(depot_id)

        # Bu deponun cycle_id'lerini bul
        cycle_rows = session.execute(text(
            "SELECT id FROM cycles WHERE depot_id = :did"
        ), {"did": depot_id_str}).fetchall()
        cycle_ids = [str(r[0]) for r in cycle_rows]

        if cycle_ids:
            cycle_id_list = ",".join(f"'{cid}'" for cid in cycle_ids)

            # 1. StockMovement (loadsheet -> cycle üzerinden)
            session.execute(text(
                f"DELETE FROM stock_movements WHERE loadsheet_id IN "
                f"(SELECT id FROM loadsheets WHERE cycle_id IN ({cycle_id_list}))"
            ))
            # Ayrıca depot_id ile de sil (loadsheet'siz manual hareketler)
            session.execute(text("DELETE FROM stock_movements WHERE depot_id = :did"), {"did": depot_id_str})

            # 2. LoadsheetLine (loadsheet -> cycle üzerinden)
            session.execute(text(
                f"DELETE FROM loadsheet_lines WHERE loadsheet_id IN "
                f"(SELECT id FROM loadsheets WHERE cycle_id IN ({cycle_id_list}))"
            ))

            # 3. Loadsheet
            session.execute(text(
                f"DELETE FROM loadsheets WHERE cycle_id IN ({cycle_id_list})"
            ))

            # 4. StationAssignment (cycle_id üzerinden — FK violation fix)
            session.execute(text(
                f"DELETE FROM station_assignments WHERE cycle_id IN ({cycle_id_list})"
            ))

            # 5. OrderLine (order -> cycle üzerinden)
            session.execute(text(
                f"DELETE FROM order_lines WHERE order_id IN "
                f"(SELECT id FROM orders WHERE cycle_id IN ({cycle_id_list}))"
            ))

            # 6. Order
            session.execute(text(
                f"DELETE FROM orders WHERE cycle_id IN ({cycle_id_list})"
            ))

            # 7. LoadCounter
            session.execute(text("DELETE FROM load_counters WHERE depot_id = :did"), {"did": depot_id_str})

            # 8. RevisionDiff
            session.execute(text("DELETE FROM revision_diffs WHERE depot_id = :did"), {"did": depot_id_str})

            # 9. CycleImport
            session.execute(text(
                f"DELETE FROM cycle_imports WHERE cycle_id IN ({cycle_id_list})"
            ))

            # 10. Cycle
            session.execute(text(
                f"DELETE FROM cycles WHERE id IN ({cycle_id_list})"
            ))
        else:
            # Cycle yoksa bile depot'a ait diğer verileri temizle
            session.execute(text("DELETE FROM stock_movements WHERE depot_id = :did"), {"did": depot_id_str})
            session.execute(text("DELETE FROM load_counters WHERE depot_id = :did"), {"did": depot_id_str})
            session.execute(text("DELETE FROM revision_diffs WHERE depot_id = :did"), {"did": depot_id_str})

        # 11. Dealer
        session.execute(text("DELETE FROM dealers WHERE depot_id = :did"), {"did": depot_id_str})

        # 12. Territory
        session.execute(text("DELETE FROM territories WHERE depot_id = :did"), {"did": depot_id_str})

        session.commit()

        # Cache temizle
        cache_delete_pattern(f"active_cycle:{depot_id_str}")

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
    """En son aktif döngüyü getir (depo bazlı) - Redis cache 10s"""
    depot_id = current_user.get("depot_id")

    # Cache kontrolü
    cache_key = f"active_cycle:{depot_id or 'all'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    # DEPOT FİLTRESİ
    stmt = select(Cycle).where(
        Cycle.status == "active"
    )
    if depot_id:
        stmt = stmt.where(Cycle.depot_id == depot_id)
    stmt = stmt.order_by(Cycle.imported_at.desc())

    cycle = session.exec(stmt).first()

    if not cycle:
        result = {"cycle": None, "has_active_cycle": False}
        cache_set(cache_key, result, ttl=10)
        return result

    # Tek SQL sorgusu ile sayım (tüm satırları çekme)
    counts_stmt = select(
        func.count(Loadsheet.id),
        func.sum(case((Loadsheet.status == "loaded", 1), else_=0)),
        func.sum(case((Loadsheet.status == "pending", 1), else_=0)),
    ).where(Loadsheet.cycle_id == cycle.id)
    counts_row = session.exec(counts_stmt).first()
    total = counts_row[0] or 0
    completed = counts_row[1] or 0
    pending = counts_row[2] or 0

    # Plan var mı - sadece varlık kontrolü
    has_plan_stmt = select(StationAssignment.id).where(StationAssignment.cycle_id == cycle.id).limit(1)
    has_plan = session.exec(has_plan_stmt).first() is not None

    result = {
        "has_active_cycle": True,
        "cycle": {
            "id": str(cycle.id),
            "cycle_no": cycle.cycle_no,
            "run_time": cycle.run_time,
            "plan_date": str(cycle.plan_date),
            "status": cycle.status,
            "has_plan": has_plan,
            "total_loadsheets": total,
            "completed_loadsheets": completed,
            "pending_loadsheets": pending
        }
    }
    cache_set(cache_key, result, ttl=10)
    return result


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
