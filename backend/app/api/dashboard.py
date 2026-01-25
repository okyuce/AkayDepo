"""
Dashboard API Router
Yonetici dashboard icin ozet veriler
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import Optional
from datetime import datetime

from app.core.database import get_session
from app.api.auth import get_current_user
from app.models import (
    Cycle, Loadsheet, LoadsheetLine, Station, StationAssignment,
    Territory, Dealer, CycleImport
)

router = APIRouter()


def require_admin(current_user: dict = Depends(get_current_user)):
    """Admin yetkisi kontrolu"""
    if current_user.get("role") != "admin":
        raise HTTPException(403, "Bu endpoint sadece yoneticiler icin")
    return current_user


@router.get("/summary")
async def get_dashboard_summary(
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_admin)
):
    """
    Dashboard ozet bilgileri

    Returns:
        - Aktif dongu bilgisi
        - Fis istatistikleri
        - Istasyon ozeti
        - Son import bilgisi
    """
    # Aktif donguyu bul
    stmt = select(Cycle).where(
        Cycle.status == "active"
    ).order_by(Cycle.imported_at.desc())
    cycle = session.exec(stmt).first()

    cycle_data = None
    loadsheet_stats = {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "cancelled": 0,
        "completion_percentage": 0
    }
    station_summary = []
    last_import = None

    if cycle:
        cycle_data = {
            "id": str(cycle.id),
            "cycle_no": cycle.cycle_no,
            "run_time": cycle.run_time,
            "plan_date": str(cycle.plan_date),
            "status": cycle.status
        }

        # Fis istatistikleri
        stmt = select(Loadsheet).where(Loadsheet.cycle_id == cycle.id)
        loadsheets = session.exec(stmt).all()

        total = len(loadsheets)
        completed = len([ls for ls in loadsheets if ls.status == "loaded"])
        pending = len([ls for ls in loadsheets if ls.status == "pending"])
        cancelled = len([ls for ls in loadsheets if ls.status == "cancelled"])

        loadsheet_stats = {
            "total": total,
            "completed": completed,
            "pending": pending,
            "cancelled": cancelled,
            "completion_percentage": round((completed / total * 100) if total > 0 else 0, 1)
        }

        # Istasyon ozeti
        stmt = select(StationAssignment).where(StationAssignment.cycle_id == cycle.id)
        assignments = session.exec(stmt).all()

        # Istasyonlara gore grupla
        station_data = {}
        for assignment in assignments:
            station_id = str(assignment.station_id)
            if station_id not in station_data:
                station = session.get(Station, assignment.station_id)
                station_data[station_id] = {
                    "station_id": station_id,
                    "station_name": station.name if station else f"Istasyon-{assignment.load_rank}",
                    "territory_count": 0,
                    "total_carton": 0,
                    "completed_carton": 0,
                    "loadsheet_ids": []
                }
            station_data[station_id]["territory_count"] += 1
            station_data[station_id]["total_carton"] += assignment.target_total_carton

        # Her istasyon icin tamamlanan koli hesapla
        for station_id, data in station_data.items():
            # Bu istasyonun assignment ID'lerini bul
            station_assignment_ids = [
                a.id for a in assignments if str(a.station_id) == station_id
            ]

            # Bu istasyonun fislerini bul (assignment uzerinden)
            completed_carton = 0
            for ls in loadsheets:
                if ls.assignment_id in station_assignment_ids and ls.status == "loaded":
                    # Loadsheet satirlarindan toplam koli hesapla
                    stmt = select(func.sum(LoadsheetLine.qty_carton)).where(
                        LoadsheetLine.loadsheet_id == ls.id
                    )
                    result = session.exec(stmt).first()
                    completed_carton += result or 0

            data["completed_carton"] = completed_carton
            data["progress_percent"] = round(
                (completed_carton / data["total_carton"] * 100) if data["total_carton"] > 0 else 0,
                1
            )

        station_summary = sorted(station_data.values(), key=lambda x: x["station_name"])

        # Son import
        stmt = select(CycleImport).where(
            CycleImport.cycle_id == cycle.id
        ).order_by(CycleImport.uploaded_at.desc())
        last_ci = session.exec(stmt).first()

        if last_ci:
            last_import = {
                "filename": last_ci.filename,
                "uploaded_at": last_ci.uploaded_at.isoformat(),
                "batch_number": last_ci.batch_number
            }

    return {
        "cycle": cycle_data,
        "loadsheet_stats": loadsheet_stats,
        "station_summary": station_summary,
        "last_import": last_import,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/station/{station_id}")
async def get_station_detail(
    station_id: str,
    cycle_id: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_admin)
):
    """
    Istasyon detay bilgisi

    Returns:
        - Istasyon bilgisi
        - Atanan territory'ler
        - Fisler listesi
    """
    station = session.get(Station, station_id)
    if not station:
        raise HTTPException(404, "Istasyon bulunamadi")

    # Aktif donguyu bul
    if cycle_id:
        cycle = session.get(Cycle, cycle_id)
    else:
        stmt = select(Cycle).where(Cycle.status == "active").order_by(Cycle.imported_at.desc())
        cycle = session.exec(stmt).first()

    if not cycle:
        raise HTTPException(404, "Aktif dongu bulunamadi")

    # Territory bilgileri
    stmt = select(StationAssignment).where(
        StationAssignment.cycle_id == cycle.id,
        StationAssignment.station_id == station_id
    )
    assignments = session.exec(stmt).all()

    # Bu istasyonun tum fislerini al (assignment uzerinden)
    assignment_ids = [a.id for a in assignments]
    stmt = select(Loadsheet).where(
        Loadsheet.cycle_id == cycle.id,
        Loadsheet.assignment_id.in_(assignment_ids)
    ).order_by(Loadsheet.sheet_no)
    all_loadsheets = session.exec(stmt).all()

    territories = []
    for assignment in assignments:
        territory = session.get(Territory, assignment.territory_id)
        if territory:
            # Bu assignment'a ait fisler
            territory_loadsheets = [ls for ls in all_loadsheets if ls.assignment_id == assignment.id]

            total_ls = len(territory_loadsheets)
            completed_ls = len([ls for ls in territory_loadsheets if ls.status == "loaded"])

            # Toplam koli
            total_carton = 0
            completed_carton = 0
            for ls in territory_loadsheets:
                stmt = select(func.sum(LoadsheetLine.qty_carton)).where(
                    LoadsheetLine.loadsheet_id == ls.id
                )
                carton = session.exec(stmt).first() or 0
                total_carton += carton
                if ls.status == "loaded":
                    completed_carton += carton

            territories.append({
                "territory_code": territory.code,
                "display_number": territory.display_number,
                "total_loadsheets": total_ls,
                "completed_loadsheets": completed_ls,
                "total_carton": total_carton,
                "completed_carton": completed_carton
            })

    loadsheet_list = []
    for ls in all_loadsheets:
        dealer = session.get(Dealer, ls.dealer_id)

        # Toplam koli ve paket
        stmt = select(
            func.sum(LoadsheetLine.qty_carton),
            func.sum(LoadsheetLine.qty_pack)
        ).where(LoadsheetLine.loadsheet_id == ls.id)
        result = session.exec(stmt).first()
        total_carton = result[0] or 0 if result else 0
        total_pack = result[1] or 0 if result else 0

        # Rut numarasi dealer'in route_order'indan geliyor
        route_number = dealer.route_order if dealer else None

        loadsheet_list.append({
            "id": str(ls.id),
            "sheet_no": ls.sheet_no,
            "route_number": route_number,
            "dealer_name": dealer.name if dealer else "Bilinmeyen",
            "dealer_code": dealer.code if dealer else "",
            "status": ls.status,
            "total_carton": total_carton,
            "total_pack": total_pack
        })

    return {
        "station_id": str(station.id),
        "station_name": station.name,
        "territories": territories,
        "loadsheets": loadsheet_list
    }


@router.get("/territory/{territory_code}")
async def get_territory_detail(
    territory_code: str,
    cycle_id: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_admin)
):
    """
    Territory detay bilgisi - Bayiler ve siparisler

    Returns:
        - Territory bilgisi
        - Bayi listesi ve siparis durumlari
    """
    # Territory bul
    stmt = select(Territory).where(Territory.code == territory_code)
    territory = session.exec(stmt).first()
    if not territory:
        raise HTTPException(404, "Territory bulunamadi")

    # Aktif donguyu bul
    if cycle_id:
        cycle = session.get(Cycle, cycle_id)
    else:
        stmt = select(Cycle).where(Cycle.status == "active").order_by(Cycle.imported_at.desc())
        cycle = session.exec(stmt).first()

    if not cycle:
        raise HTTPException(404, "Aktif dongu bulunamadi")

    # Bu territory'deki bayileri bul
    stmt = select(Dealer).where(Dealer.territory_id == territory.id)
    dealers = session.exec(stmt).all()

    dealer_list = []
    for dealer in dealers:
        # Bayi icin fis bul
        stmt = select(Loadsheet).where(
            Loadsheet.cycle_id == cycle.id,
            Loadsheet.dealer_id == dealer.id
        )
        loadsheet = session.exec(stmt).first()

        products = []
        status = "bekliyor"
        loadsheet_id = None

        if loadsheet:
            loadsheet_id = str(loadsheet.id)
            status = loadsheet.status

            # Fis satirlari
            stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == loadsheet.id)
            lines = session.exec(stmt).all()

            from app.models import Product
            for line in lines:
                product = session.get(Product, line.product_id)
                products.append({
                    "product_code": product.code if product else "?",
                    "product_name": product.name if product else "Bilinmeyen",
                    "quantity_carton": line.qty_carton,
                    "quantity_pack": line.qty_pack
                })

        # Toplam karton ve paket hesapla
        total_carton = sum(p["quantity_carton"] for p in products)
        total_pack = sum(p["quantity_pack"] for p in products)

        dealer_list.append({
            "dealer_code": dealer.code,
            "dealer_name": dealer.name,
            "route_order": dealer.route_order,
            "loadsheet_id": loadsheet_id,
            "status": status,
            "total_carton": total_carton,
            "total_pack": total_pack,
            "products": products
        })

    return {
        "territory_code": territory.code,
        "territory_name": territory.code,  # TerritoryInfo'dan alinabilir
        "dealers": dealer_list
    }
