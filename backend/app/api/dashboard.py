"""
Dashboard API Router
Yonetici dashboard icin ozet veriler
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import Optional
from datetime import datetime
from collections import defaultdict
import json

from app.core.database import get_session
from app.api.auth import get_current_user, verify_depot_access
from app.models import (
    Depot, Cycle, Loadsheet, LoadsheetLine, Station, StationAssignment,
    Territory, Dealer, CycleImport, Product, Order, OrderLine
)

router = APIRouter()


def require_admin(current_user: dict = Depends(get_current_user)):
    """Admin yetkisi kontrolu"""
    if current_user.get("role") not in ("admin", "superadmin"):
        raise HTTPException(403, "Bu endpoint sadece yoneticiler icin")
    return current_user


def calculate_territory_loads(cycle_id, session: Session) -> dict:
    """
    Territory bazinda toplam karton hesapla (OrderLine'dan, ana depo ile ayni)
    int() ile kesilir - ana depo'daki target_total_carton ile birebir ayni

    Returns:
        {territory_id: total_carton (int)}
    """
    # Dongudeki tum order'lari al
    stmt = select(Order).where(Order.cycle_id == cycle_id)
    orders = session.exec(stmt).all()

    territory_loads = {}

    for order in orders:
        territory_id = str(order.territory_id)

        # Order lines'i al
        stmt = select(OrderLine).where(OrderLine.order_id == order.id)
        lines = session.exec(stmt).all()

        # Toplam karton hesapla (paket dahil: 10 paket = 1 karton)
        total_carton = 0
        for line in lines:
            total_carton += line.qty_carton + (line.qty_pack / 10)

        # Territory toplama ekle
        if territory_id not in territory_loads:
            territory_loads[territory_id] = 0
        territory_loads[territory_id] += total_carton

    # Her territory icin int() ile kes (ana depo ile ayni)
    return {tid: int(val) for tid, val in territory_loads.items()}


def get_effective_loadsheets(loadsheets: list, session: Session) -> dict:
    """
    Bayi bazinda efektif fisleri hesapla.
    Her bayi icin son batch aktif, onceki batch'ler revizyon (iptal) olarak kabul edilir.

    Returns:
        {
            dealer_id: {
                'active': Loadsheet,  # Son batch (aktif fis)
                'revisions': [Loadsheet],  # Onceki batch'ler (revizyonlar)
                'all': [Loadsheet]  # Tum fisler
            }
        }
    """
    dealer_loadsheets = defaultdict(list)
    for ls in loadsheets:
        dealer_loadsheets[str(ls.dealer_id)].append(ls)

    result = {}
    for dealer_id, ls_list in dealer_loadsheets.items():
        # Batch numarasina gore sirala
        sorted_ls = sorted(ls_list, key=lambda x: x.batch_number)

        # Son batch aktif, oncekiler revizyon
        active = sorted_ls[-1] if sorted_ls else None
        revisions = sorted_ls[:-1] if len(sorted_ls) > 1 else []

        result[dealer_id] = {
            'active': active,
            'revisions': revisions,
            'all': sorted_ls
        }

    return result


@router.get("/multi-depot/summary")
async def get_multi_depot_summary(
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_admin)
):
    """
    Tum aktif depolarin yukleme fisi ozeti.
    Multi-depot genel gorunum icin.
    """
    # Aktif depolari al
    stmt = select(Depot).where(Depot.is_active == True).order_by(Depot.code)
    depots = session.exec(stmt).all()

    depot_list = []
    for depot in depots:
        # Bu deponun aktif dongusunu bul
        stmt = select(Cycle).where(
            Cycle.status == "active",
            Cycle.depot_id == depot.id
        ).order_by(Cycle.imported_at.desc())
        cycle = session.exec(stmt).first()

        depot_info = {
            "depot_code": depot.code,
            "depot_name": depot.name,
            "depot_city": depot.city,
            "has_active_cycle": cycle is not None,
            "cycle_no": None,
            "run_time": None,
            "loadsheet_stats": {
                "total": 0,
                "completed": 0,
                "pending": 0,
                "revision_cancelled": 0,
                "completion_percentage": 0
            },
            "last_completion_time": None
        }

        if cycle:
            depot_info["cycle_no"] = cycle.cycle_no
            depot_info["run_time"] = cycle.run_time

            # Fis istatistikleri
            stmt = select(Loadsheet).where(Loadsheet.cycle_id == cycle.id)
            loadsheets = session.exec(stmt).all()

            effective = get_effective_loadsheets(loadsheets, session)
            active_loadsheets = [e['active'] for e in effective.values() if e['active']]

            total = len(active_loadsheets)
            completed = len([ls for ls in active_loadsheets if ls.status == "loaded"])
            pending = len([ls for ls in active_loadsheets if ls.status == "pending"])

            revision_count = sum(len(e['revisions']) for e in effective.values())

            depot_info["loadsheet_stats"] = {
                "total": total,
                "completed": completed,
                "pending": pending,
                "revision_cancelled": revision_count,
                "completion_percentage": round((completed / total * 100) if total > 0 else 0, 1)
            }

            # Son tamamlanan fisin zamani
            stmt = select(func.max(Loadsheet.loaded_at)).where(
                Loadsheet.cycle_id == cycle.id,
                Loadsheet.status == "loaded"
            )
            last_loaded_at = session.exec(stmt).first()
            depot_info["last_completion_time"] = last_loaded_at.isoformat() if last_loaded_at else None

        depot_list.append(depot_info)

    return {
        "depots": depot_list,
        "last_updated": datetime.now().isoformat()
    }


@router.get("/depot/{depot_code}/summary")
async def get_depot_summary(
    depot_code: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_admin)
):
    """
    Belirli bir deponun detay ozeti.
    Mevcut /summary endpoint'inin depot_code parametreli versiyonu.
    """
    # Depoyu bul
    stmt = select(Depot).where(Depot.code == depot_code)
    depot = session.exec(stmt).first()
    if not depot:
        raise HTTPException(404, "Depo bulunamadi")

    # Depo erişim kontrolü
    depot_id = current_user.get("depot_id")
    if depot_id and str(depot.id) != str(depot_id):
        raise HTTPException(403, "Bu depoya erisim yetkiniz yok")

    # Aktif donguyu bul (bu depo icin)
    stmt = select(Cycle).where(
        Cycle.status == "active",
        Cycle.depot_id == depot.id
    ).order_by(Cycle.imported_at.desc())
    cycle = session.exec(stmt).first()

    cycle_data = None
    loadsheet_stats = {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "revision_cancelled": 0,
        "completion_percentage": 0
    }
    station_summary = []
    last_import = None

    if cycle:
        # Son tamamlanan fisin zamanini bul
        stmt = select(func.max(Loadsheet.loaded_at)).where(
            Loadsheet.cycle_id == cycle.id,
            Loadsheet.status == "loaded"
        )
        last_loaded_at = session.exec(stmt).first()

        cycle_data = {
            "id": str(cycle.id),
            "cycle_no": cycle.cycle_no,
            "run_time": cycle.run_time,
            "last_completion_time": last_loaded_at.isoformat() if last_loaded_at else None,
            "plan_date": str(cycle.plan_date),
            "status": cycle.status
        }

        # Fis istatistikleri
        stmt = select(Loadsheet).where(Loadsheet.cycle_id == cycle.id)
        loadsheets = session.exec(stmt).all()

        effective = get_effective_loadsheets(loadsheets, session)
        active_loadsheets = [e['active'] for e in effective.values() if e['active']]
        revision_count = sum(len(e['revisions']) for e in effective.values())

        total = len(active_loadsheets)
        completed = len([ls for ls in active_loadsheets if ls.status == "loaded"])
        pending = len([ls for ls in active_loadsheets if ls.status == "pending"])

        loadsheet_stats = {
            "total": total,
            "completed": completed,
            "pending": pending,
            "revision_cancelled": revision_count,
            "completion_percentage": round((completed / total * 100) if total > 0 else 0, 1)
        }

        # Istasyon ozeti
        stmt = select(StationAssignment).where(StationAssignment.cycle_id == cycle.id)
        assignments = session.exec(stmt).all()

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

        for station_id, data in station_data.items():
            station_assignment_ids = [
                a.id for a in assignments if str(a.station_id) == station_id
            ]
            station_loadsheets = [ls for ls in loadsheets if ls.assignment_id in station_assignment_ids]
            station_effective = get_effective_loadsheets(station_loadsheets, session)

            total_carton = 0
            completed_carton = 0
            for dealer_data in station_effective.values():
                active_ls = dealer_data['active']
                if active_ls:
                    stmt = select(
                        func.sum(LoadsheetLine.qty_carton),
                        func.sum(LoadsheetLine.qty_pack)
                    ).where(LoadsheetLine.loadsheet_id == active_ls.id)
                    result = session.exec(stmt).first()
                    carton = (result[0] or 0) if result else 0
                    pack = (result[1] or 0) if result else 0
                    ls_total = int(carton + (pack / 10))
                    total_carton += ls_total
                    if active_ls.status == "loaded":
                        completed_carton += ls_total

            data["total_carton"] = total_carton
            data["completed_carton"] = completed_carton
            data["progress_percent"] = round(
                (completed_carton / total_carton * 100) if total_carton > 0 else 0,
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
        "depot_code": depot.code,
        "depot_name": depot.name,
        "cycle": cycle_data,
        "loadsheet_stats": loadsheet_stats,
        "station_summary": station_summary,
        "last_import": last_import,
        "last_updated": datetime.now().isoformat()
    }


@router.get("/summary")
async def get_dashboard_summary(
    session: Session = Depends(get_session),
    current_user: dict = Depends(require_admin)
):
    """
    Dashboard ozet bilgileri

    Returns:
        - Aktif dongu bilgisi
        - Fis istatistikleri (revizyon mantigi ile)
        - Istasyon ozeti
        - Son import bilgisi
    """
    # Aktif donguyu bul
    depot_id = current_user.get("depot_id")
    stmt = select(Cycle).where(
        Cycle.status == "active"
    )
    if depot_id:
        stmt = stmt.where(Cycle.depot_id == depot_id)
    stmt = stmt.order_by(Cycle.imported_at.desc())
    cycle = session.exec(stmt).first()

    cycle_data = None
    loadsheet_stats = {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "revision_cancelled": 0,  # Revizyon nedeniyle iptal
        "completion_percentage": 0
    }
    station_summary = []
    last_import = None

    if cycle:
        # Son tamamlanan fisin zamanini bul
        stmt = select(func.max(Loadsheet.loaded_at)).where(
            Loadsheet.cycle_id == cycle.id,
            Loadsheet.status == "loaded"
        )
        last_loaded_at = session.exec(stmt).first()

        cycle_data = {
            "id": str(cycle.id),
            "cycle_no": cycle.cycle_no,
            "run_time": cycle.run_time,
            "last_completion_time": last_loaded_at.isoformat() if last_loaded_at else None,
            "plan_date": str(cycle.plan_date),
            "status": cycle.status
        }

        # Fis istatistikleri
        stmt = select(Loadsheet).where(Loadsheet.cycle_id == cycle.id)
        loadsheets = session.exec(stmt).all()

        # Bayi bazinda efektif fisleri hesapla
        effective = get_effective_loadsheets(loadsheets, session)

        # Sadece aktif fisleri say (revizyonlar haric)
        active_loadsheets = [e['active'] for e in effective.values() if e['active']]
        revision_count = sum(len(e['revisions']) for e in effective.values())

        total = len(active_loadsheets)
        completed = len([ls for ls in active_loadsheets if ls.status == "loaded"])
        pending = len([ls for ls in active_loadsheets if ls.status == "pending"])

        loadsheet_stats = {
            "total": total,
            "completed": completed,
            "pending": pending,
            "revision_cancelled": revision_count,
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

        # Her istasyon icin toplam ve tamamlanan koli hesapla (aktif fislerden)
        for station_id, data in station_data.items():
            # Bu istasyonun assignment ID'lerini bul
            station_assignment_ids = [
                a.id for a in assignments if str(a.station_id) == station_id
            ]

            # Bu istasyonun fislerini bul (assignment uzerinden)
            station_loadsheets = [ls for ls in loadsheets if ls.assignment_id in station_assignment_ids]
            station_effective = get_effective_loadsheets(station_loadsheets, session)

            # Toplam ve tamamlanan karton (aktif fislerden - revizyon haric)
            total_carton = 0
            completed_carton = 0
            for dealer_data in station_effective.values():
                active_ls = dealer_data['active']
                if active_ls:
                    # Aktif fisin koli miktari (LoadsheetLine'dan)
                    stmt = select(
                        func.sum(LoadsheetLine.qty_carton),
                        func.sum(LoadsheetLine.qty_pack)
                    ).where(LoadsheetLine.loadsheet_id == active_ls.id)
                    result = session.exec(stmt).first()
                    carton = (result[0] or 0) if result else 0
                    pack = (result[1] or 0) if result else 0
                    ls_total = int(carton + (pack / 10))
                    total_carton += ls_total
                    if active_ls.status == "loaded":
                        completed_carton += ls_total

            data["total_carton"] = total_carton
            data["completed_carton"] = completed_carton
            data["progress_percent"] = round(
                (completed_carton / total_carton * 100) if total_carton > 0 else 0,
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
        "last_updated": datetime.now().isoformat()
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
        - Fisler listesi (revizyon bilgisi ile)
    """
    station = session.get(Station, station_id)
    if not station:
        raise HTTPException(404, "Istasyon bulunamadi")
    depot_id = current_user.get("depot_id")
    verify_depot_access(station, depot_id, "Istasyon")

    # Station'ın depot_id'sini kullan (dashboard kullanıcısı depot_id=NULL olabilir)
    effective_depot_id = depot_id or station.depot_id

    # Aktif donguyu bul
    if cycle_id:
        cycle = session.get(Cycle, cycle_id)
        if cycle:
            verify_depot_access(cycle, depot_id, "Döngü")
    else:
        stmt = select(Cycle).where(Cycle.status == "active")
        if effective_depot_id:
            stmt = stmt.where(Cycle.depot_id == effective_depot_id)
        stmt = stmt.order_by(Cycle.imported_at.desc())
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

    # Bayi bazinda efektif fisleri hesapla
    effective = get_effective_loadsheets(all_loadsheets, session)

    territories = []
    for assignment in assignments:
        territory = session.get(Territory, assignment.territory_id)
        if territory:
            # Bu assignment'a ait fisler
            territory_loadsheets = [ls for ls in all_loadsheets if ls.assignment_id == assignment.id]
            territory_effective = get_effective_loadsheets(territory_loadsheets, session)

            # Sadece aktif fisleri say
            active_ls_list = [e['active'] for e in territory_effective.values() if e['active']]
            total_ls = len(active_ls_list)
            completed_ls = len([ls for ls in active_ls_list if ls.status == "loaded"])

            # Toplam ve tamamlanan koli (aktif fislerden - revizyon haric)
            total_carton = 0
            completed_carton = 0
            for dealer_data in territory_effective.values():
                active_ls = dealer_data['active']
                if active_ls:
                    stmt = select(
                        func.sum(LoadsheetLine.qty_carton),
                        func.sum(LoadsheetLine.qty_pack)
                    ).where(LoadsheetLine.loadsheet_id == active_ls.id)
                    result = session.exec(stmt).first()
                    carton = (result[0] or 0) if result else 0
                    pack = (result[1] or 0) if result else 0
                    ls_total = int(carton + (pack / 10))
                    total_carton += ls_total
                    if active_ls.status == "loaded":
                        completed_carton += ls_total

            territories.append({
                "territory_code": territory.code,
                "display_number": territory.display_number,
                "total_loadsheets": total_ls,
                "completed_loadsheets": completed_ls,
                "total_carton": total_carton,
                "completed_carton": completed_carton
            })

    # Loadsheet listesi (bayi bazinda gruplanmis)
    loadsheet_list = []
    for dealer_id, dealer_data in effective.items():
        active_ls = dealer_data['active']
        if not active_ls:
            continue

        dealer = session.get(Dealer, dealer_id)

        # Toplam koli ve paket
        stmt = select(
            func.sum(LoadsheetLine.qty_carton),
            func.sum(LoadsheetLine.qty_pack)
        ).where(LoadsheetLine.loadsheet_id == active_ls.id)
        result = session.exec(stmt).first()
        total_carton = result[0] or 0 if result else 0
        total_pack = result[1] or 0 if result else 0

        # Rut numarasi dealer'in route_order'indan geliyor
        route_number = dealer.route_order if dealer else None

        # Revizyon bilgisi
        has_revision = len(dealer_data['revisions']) > 0
        revision_count = len(dealer_data['revisions'])

        loadsheet_list.append({
            "id": str(active_ls.id),
            "sheet_no": active_ls.sheet_no,
            "route_number": route_number,
            "dealer_name": dealer.name if dealer else "Bilinmeyen",
            "dealer_code": dealer.code if dealer else "",
            "status": active_ls.status,
            "total_carton": total_carton,
            "total_pack": total_pack,
            "batch_number": active_ls.batch_number,
            "has_revision": has_revision,
            "revision_count": revision_count
        })

    # Route number'a gore sirala
    loadsheet_list.sort(key=lambda x: x['route_number'] or 999)

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
    Territory detay bilgisi - Bayiler ve siparisler (revizyon destegi ile)

    Returns:
        - Territory bilgisi
        - Bayi listesi ve siparis durumlari
    """
    # Territory bul (depot filtresi ile)
    depot_id = current_user.get("depot_id")
    stmt = select(Territory).where(Territory.code == territory_code)
    if depot_id:
        stmt = stmt.where(Territory.depot_id == depot_id)
    territory = session.exec(stmt).first()
    if not territory:
        raise HTTPException(404, "Territory bulunamadi")

    # Aktif donguyu bul
    if cycle_id:
        cycle = session.get(Cycle, cycle_id)
        if cycle:
            verify_depot_access(cycle, depot_id, "Döngü")
    else:
        stmt = select(Cycle).where(Cycle.status == "active")
        if depot_id:
            stmt = stmt.where(Cycle.depot_id == depot_id)
        stmt = stmt.order_by(Cycle.imported_at.desc())
        cycle = session.exec(stmt).first()

    if not cycle:
        raise HTTPException(404, "Aktif dongu bulunamadi")

    # Bu territory'deki bayileri bul
    stmt = select(Dealer).where(Dealer.territory_id == territory.id)
    dealers = session.exec(stmt).all()

    dealer_list = []
    for dealer in dealers:
        # Bayi icin TUM fisleri bul (tum batch'ler)
        stmt = select(Loadsheet).where(
            Loadsheet.cycle_id == cycle.id,
            Loadsheet.dealer_id == dealer.id
        ).order_by(Loadsheet.batch_number)
        all_dealer_loadsheets = session.exec(stmt).all()

        if not all_dealer_loadsheets:
            # Fis yoksa bekliyor olarak ekle
            dealer_list.append({
                "dealer_code": dealer.code,
                "dealer_name": dealer.name,
                "route_order": dealer.route_order,
                "loadsheet_id": None,
                "status": "bekliyor",
                "total_carton": 0,
                "total_pack": 0,
                "products": [],
                "has_revision": False,
                "revision_count": 0,
                "loadsheets": []
            })
            continue

        # Son batch aktif, oncekiler revizyon
        active_ls = all_dealer_loadsheets[-1]
        revision_ls_list = all_dealer_loadsheets[:-1] if len(all_dealer_loadsheets) > 1 else []

        # Onceki batch'in urunlerini al (fark hesaplamak icin)
        prev_products = {}
        if revision_ls_list:
            prev_ls = revision_ls_list[-1]  # Son revizyon
            stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == prev_ls.id)
            prev_lines = session.exec(stmt).all()
            for line in prev_lines:
                prev_products[str(line.product_id)] = {
                    'qty_carton': line.qty_carton,
                    'qty_pack': line.qty_pack
                }

        # Aktif fisin satirlarini al
        stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == active_ls.id)
        lines = session.exec(stmt).all()

        products = []
        for line in lines:
            product = session.get(Product, line.product_id)

            # Fark hesapla
            prev = prev_products.get(str(line.product_id), {'qty_carton': 0, 'qty_pack': 0})
            change_carton = line.qty_carton - prev['qty_carton'] if revision_ls_list else None
            change_pack = line.qty_pack - prev['qty_pack'] if revision_ls_list else None

            # Eger revizyon yoksa veya fark 0 ise None yap
            if change_carton == 0:
                change_carton = None
            if change_pack == 0:
                change_pack = None

            products.append({
                "product_code": product.code if product else "?",
                "product_name": product.name if product else "Bilinmeyen",
                "quantity_carton": line.qty_carton,
                "quantity_pack": line.qty_pack,
                "change_carton": change_carton,
                "change_pack": change_pack
            })

        # Toplam karton ve paket hesapla
        total_carton = sum(p["quantity_carton"] for p in products)
        total_pack = sum(p["quantity_pack"] for p in products)

        # Tum loadsheet'lerin ozet bilgisi
        loadsheet_summaries = []
        for idx, ls in enumerate(all_dealer_loadsheets):
            is_active = (idx == len(all_dealer_loadsheets) - 1)
            stmt = select(
                func.sum(LoadsheetLine.qty_carton),
                func.sum(LoadsheetLine.qty_pack)
            ).where(LoadsheetLine.loadsheet_id == ls.id)
            result = session.exec(stmt).first()
            ls_carton = result[0] or 0 if result else 0
            ls_pack = result[1] or 0 if result else 0

            loadsheet_summaries.append({
                "id": str(ls.id),
                "batch_number": ls.batch_number,
                "status": ls.status,
                "total_carton": ls_carton,
                "total_pack": ls_pack,
                "is_active": is_active,
                "is_revision": not is_active
            })

        dealer_list.append({
            "dealer_code": dealer.code,
            "dealer_name": dealer.name,
            "route_order": dealer.route_order,
            "loadsheet_id": str(active_ls.id),
            "status": active_ls.status,
            "total_carton": total_carton,
            "total_pack": total_pack,
            "products": products,
            "has_revision": len(revision_ls_list) > 0,
            "revision_count": len(revision_ls_list),
            "loadsheets": loadsheet_summaries
        })

    # Route order'a gore sirala
    dealer_list.sort(key=lambda x: x['route_order'] or 999)

    return {
        "territory_code": territory.code,
        "territory_name": territory.code,
        "dealers": dealer_list
    }
