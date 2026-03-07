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
from app.api.auth import get_current_user
from app.models import StationInventory, StockMovement, Station, Product, Loadsheet, Territory, StationAssignment, Dealer

router = APIRouter()

@router.get("/station/{station_id}")
async def get_station_inventory(
    station_id: UUID,
    current_user: dict = Depends(get_current_user),
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
            "updated_at": (inv.updated_at.isoformat() if (inv and getattr(inv, 'updated_at', None)) else None)
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
    current_user: dict = Depends(get_current_user),
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
            # Önceki değerleri kaydet
            before_carton = existing.quantity_carton
            before_pack = existing.quantity_pack

            # Güncelle
            existing.quantity_carton = qty_carton
            existing.quantity_pack = qty_pack
            existing.updated_at = datetime.now()
            session.add(existing)

            # Stok hareket logu kaydet (sadece değişiklik varsa)
            if before_carton != qty_carton or before_pack != qty_pack:
                diff_carton = qty_carton - before_carton
                diff_pack = qty_pack - before_pack
                movement_type = "manual_add" if (diff_carton > 0 or diff_pack > 0) else "manual_remove"

                movement = StockMovement(
                    station_id=station_id,
                    product_id=product_id,
                    loadsheet_id=None,
                    movement_type=movement_type,
                    quantity_carton=abs(diff_carton),
                    quantity_pack=abs(diff_pack),
                    before_carton=before_carton,
                    before_pack=before_pack,
                    after_carton=qty_carton,
                    after_pack=qty_pack,
                    note="Manuel stok düzenleme"
                )
                session.add(movement)
        else:
            # Yeni kayıt
            new_inv = StationInventory(
                station_id=station_id,
                product_id=product_id,
                quantity_carton=qty_carton,
                quantity_pack=qty_pack
            )
            new_inv.updated_at = datetime.now()
            session.add(new_inv)

            # İlk kayıt için hareket logu (sıfırdan ekleme)
            if qty_carton > 0 or qty_pack > 0:
                movement = StockMovement(
                    station_id=station_id,
                    product_id=product_id,
                    loadsheet_id=None,
                    movement_type="manual_add",
                    quantity_carton=qty_carton,
                    quantity_pack=qty_pack,
                    before_carton=0,
                    before_pack=0,
                    after_carton=qty_carton,
                    after_pack=qty_pack,
                    note="İlk stok girişi"
                )
                session.add(movement)

    session.commit()

    return {"success": True, "message": "Stoklar güncellendi"}


@router.get("/station/{station_id}/movements")
async def get_stock_movements(
    station_id: UUID,
    product_id: UUID = None,
    loadsheet_id: UUID = None,
    movement_type: str = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    İstasyonun stok hareketlerini getir

    Filtreler:
    - product_id: Belirli ürün
    - loadsheet_id: Belirli fiş
    - movement_type: deduction, refund, manual_add, manual_remove
    - limit: Maksimum kayıt sayısı (varsayılan 100)
    """
    # İstasyon kontrolü
    station = session.get(Station, station_id)
    if not station:
        raise HTTPException(404, "İstasyon bulunamadı")

    # Query oluştur
    query = select(StockMovement).where(StockMovement.station_id == station_id)

    if product_id:
        query = query.where(StockMovement.product_id == product_id)
    if loadsheet_id:
        query = query.where(StockMovement.loadsheet_id == loadsheet_id)
    if movement_type:
        query = query.where(StockMovement.movement_type == movement_type)

    query = query.order_by(StockMovement.created_at.desc()).limit(limit)

    movements = session.exec(query).all()

    # Ürün bilgilerini al
    product_ids = list(set(m.product_id for m in movements))
    products = {}
    if product_ids:
        prods = session.exec(select(Product).where(Product.id.in_(product_ids))).all()
        products = {str(p.id): {"code": p.code, "name": p.name} for p in prods}

    result = []
    for m in movements:
        prod = products.get(str(m.product_id), {})
        result.append({
            "id": str(m.id),
            "product_id": str(m.product_id),
            "product_code": prod.get("code", ""),
            "product_name": prod.get("name", ""),
            "loadsheet_id": str(m.loadsheet_id) if m.loadsheet_id else None,
            "movement_type": m.movement_type,
            "quantity_carton": m.quantity_carton,
            "quantity_pack": m.quantity_pack,
            "before_carton": m.before_carton,
            "before_pack": m.before_pack,
            "after_carton": m.after_carton,
            "after_pack": m.after_pack,
            "created_at": m.created_at.isoformat(),
            "note": m.note
        })

    return {
        "station_id": str(station_id),
        "station_name": station.name,
        "movements": result,
        "count": len(result)
    }


@router.get("/movements/loadsheet/{loadsheet_id}")
async def get_movements_by_loadsheet(
    loadsheet_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Belirli bir fişe ait tüm stok hareketlerini getir"""
    movements = session.exec(
        select(StockMovement)
        .where(StockMovement.loadsheet_id == loadsheet_id)
        .order_by(StockMovement.created_at.desc())
    ).all()

    # Ürün bilgilerini al
    product_ids = list(set(m.product_id for m in movements))
    products = {}
    if product_ids:
        prods = session.exec(select(Product).where(Product.id.in_(product_ids))).all()
        products = {str(p.id): {"code": p.code, "name": p.name} for p in prods}

    result = []
    for m in movements:
        prod = products.get(str(m.product_id), {})
        result.append({
            "id": str(m.id),
            "station_id": str(m.station_id),
            "product_id": str(m.product_id),
            "product_code": prod.get("code", ""),
            "product_name": prod.get("name", ""),
            "movement_type": m.movement_type,
            "quantity_carton": m.quantity_carton,
            "quantity_pack": m.quantity_pack,
            "before_carton": m.before_carton,
            "before_pack": m.before_pack,
            "after_carton": m.after_carton,
            "after_pack": m.after_pack,
            "created_at": m.created_at.isoformat(),
            "note": m.note
        })

    return {
        "loadsheet_id": str(loadsheet_id),
        "movements": result,
        "count": len(result)
    }


@router.get("/territories/cycle/{cycle_id}")
async def get_territories_by_cycle(
    cycle_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Döngüye ait territory listesini getir
    StationAssignment üzerinden cycle'a bağlı territory'leri döndürür
    """
    # Bu cycle'daki assignment'lardan unique territory'leri al
    assignments = session.exec(
        select(StationAssignment.territory_id)
        .where(StationAssignment.cycle_id == cycle_id)
        .distinct()
    ).all()

    territory_ids = list(set(assignments))
    if not territory_ids:
        return []

    territories = session.exec(
        select(Territory)
        .where(Territory.id.in_(territory_ids))
        .order_by(Territory.name)
    ).all()

    return [{"id": str(t.id), "name": t.name} for t in territories]


@router.get("/movements/cycle/{cycle_id}")
async def get_movements_by_cycle(
    cycle_id: UUID,
    station_id: UUID = None,
    territory_id: UUID = None,
    dealer_id: UUID = None,
    movement_type: str = None,
    sku: str = None,
    limit: int = 500,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Döngüye ait tüm stok hareketlerini getir

    Filtreler:
    - station_id: Belirli istasyon
    - territory_id: Belirli territory
    - dealer_id: Belirli bayi
    - movement_type: deduction, refund, manual_add, manual_remove
    - sku: Ürün kodu (product_code) filtresi
    - limit: Maksimum kayıt sayısı (varsayılan 500)
    - offset: Sayfalama için başlangıç
    """
    # Döngüye ait loadsheet'leri bul
    loadsheet_query = select(Loadsheet.id).where(Loadsheet.cycle_id == cycle_id)
    loadsheet_ids = [ls_id for ls_id in session.exec(loadsheet_query).all()]

    if not loadsheet_ids:
        return {"cycle_id": str(cycle_id), "movements": [], "count": 0, "total": 0}

    # Base query
    query = select(StockMovement).where(StockMovement.loadsheet_id.in_(loadsheet_ids))

    # Filtreler
    if station_id:
        query = query.where(StockMovement.station_id == station_id)

    if territory_id:
        # Territory'ye ait loadsheet'leri bul (Loadsheet -> StationAssignment -> territory_id)
        territory_loadsheet_query = (
            select(Loadsheet.id)
            .join(StationAssignment, Loadsheet.assignment_id == StationAssignment.id)
            .where(
                Loadsheet.cycle_id == cycle_id,
                StationAssignment.territory_id == territory_id
            )
        )
        territory_loadsheet_ids = [ls_id for ls_id in session.exec(territory_loadsheet_query).all()]
        if territory_loadsheet_ids:
            query = query.where(StockMovement.loadsheet_id.in_(territory_loadsheet_ids))
        else:
            return {"cycle_id": str(cycle_id), "movements": [], "count": 0, "total": 0, "limit": limit, "offset": offset}

    if movement_type:
        query = query.where(StockMovement.movement_type == movement_type)

    if sku:
        # SKU (ürün kodu) ile eşleşen ürünleri bul - virgülle ayrılmış birden fazla SKU desteklenir
        sku_list = [s.strip() for s in sku.split(',') if s.strip()]
        if sku_list:
            from sqlalchemy import or_
            sku_conditions = [Product.code == s for s in sku_list]
            product_query = select(Product.id).where(or_(*sku_conditions))
            matching_product_ids = [p_id for p_id in session.exec(product_query).all()]
            if matching_product_ids:
                query = query.where(StockMovement.product_id.in_(matching_product_ids))
            else:
                return {"cycle_id": str(cycle_id), "movements": [], "count": 0, "total": 0, "limit": limit, "offset": offset}

    if dealer_id:
        # Bayiye ait loadsheet'leri bul
        dealer_loadsheet_query = select(Loadsheet.id).where(
            Loadsheet.cycle_id == cycle_id,
            Loadsheet.dealer_id == dealer_id
        )
        dealer_loadsheet_ids = [ls_id for ls_id in session.exec(dealer_loadsheet_query).all()]
        if dealer_loadsheet_ids:
            query = query.where(StockMovement.loadsheet_id.in_(dealer_loadsheet_ids))
        else:
            # Bayi için loadsheet yoksa boş döndür
            return {"cycle_id": str(cycle_id), "movements": [], "count": 0, "total": 0, "limit": limit, "offset": offset}

    # Toplam sayı - tüm filtreler uygulanmalı
    count_query = select(StockMovement.id).where(StockMovement.loadsheet_id.in_(loadsheet_ids))
    if station_id:
        count_query = count_query.where(StockMovement.station_id == station_id)
    if territory_id:
        territory_loadsheet_query = (
            select(Loadsheet.id)
            .join(StationAssignment, Loadsheet.assignment_id == StationAssignment.id)
            .where(
                Loadsheet.cycle_id == cycle_id,
                StationAssignment.territory_id == territory_id
            )
        )
        territory_ls_ids = [ls_id for ls_id in session.exec(territory_loadsheet_query).all()]
        if territory_ls_ids:
            count_query = count_query.where(StockMovement.loadsheet_id.in_(territory_ls_ids))
    if dealer_id:
        dealer_ls_query = select(Loadsheet.id).where(
            Loadsheet.cycle_id == cycle_id,
            Loadsheet.dealer_id == dealer_id
        )
        dealer_ls_ids = [ls_id for ls_id in session.exec(dealer_ls_query).all()]
        if dealer_ls_ids:
            count_query = count_query.where(StockMovement.loadsheet_id.in_(dealer_ls_ids))
    if movement_type:
        count_query = count_query.where(StockMovement.movement_type == movement_type)
    if sku:
        sku_list = [s.strip() for s in sku.split(',') if s.strip()]
        if sku_list:
            from sqlalchemy import or_
            sku_conditions = [Product.code == s for s in sku_list]
            product_query = select(Product.id).where(or_(*sku_conditions))
            matching_product_ids = [p_id for p_id in session.exec(product_query).all()]
            if matching_product_ids:
                count_query = count_query.where(StockMovement.product_id.in_(matching_product_ids))

    total = len(session.exec(count_query).all())

    # Sıralama ve sayfalama
    query = query.order_by(StockMovement.created_at.desc()).offset(offset).limit(limit)
    movements = session.exec(query).all()

    # İlişkili verileri al
    product_ids = list(set(m.product_id for m in movements))
    station_ids_list = list(set(m.station_id for m in movements))
    loadsheet_ids_list = list(set(m.loadsheet_id for m in movements if m.loadsheet_id))

    products = {}
    if product_ids:
        prods = session.exec(select(Product).where(Product.id.in_(product_ids))).all()
        products = {str(p.id): {"code": p.code, "name": p.name} for p in prods}

    stations = {}
    if station_ids_list:
        stats = session.exec(select(Station).where(Station.id.in_(station_ids_list))).all()
        stations = {str(s.id): s.name for s in stats}

    loadsheets = {}
    dealer_ids_set = set()
    if loadsheet_ids_list:
        lss = session.exec(select(Loadsheet).where(Loadsheet.id.in_(loadsheet_ids_list))).all()
        for ls in lss:
            loadsheets[str(ls.id)] = {
                "package_number": ls.package_number,
                "sheet_no": ls.sheet_no,
                "dealer_id": str(ls.dealer_id) if ls.dealer_id else None
            }
            if ls.dealer_id:
                dealer_ids_set.add(ls.dealer_id)

    # Bayi bilgilerini al
    dealers = {}
    if dealer_ids_set:
        dealer_list = session.exec(select(Dealer).where(Dealer.id.in_(list(dealer_ids_set)))).all()
        dealers = {str(d.id): {"code": d.code, "name": d.name} for d in dealer_list}

    # Territory bilgisi için loadsheet -> assignment -> territory ilişkisini kullan
    loadsheet_territories = {}
    if loadsheet_ids_list:
        # Loadsheet'lerin assignment'larını al
        loadsheet_assignment_query = (
            select(Loadsheet.id, StationAssignment.territory_id)
            .join(StationAssignment, Loadsheet.assignment_id == StationAssignment.id)
            .where(Loadsheet.id.in_(loadsheet_ids_list))
        )
        ls_assignments = session.exec(loadsheet_assignment_query).all()
        territory_ids = list(set(la[1] for la in ls_assignments))
        if territory_ids:
            terrs = session.exec(select(Territory).where(Territory.id.in_(territory_ids))).all()
            terr_map = {str(t.id): t.name for t in terrs}
            for la in ls_assignments:
                loadsheet_territories[str(la[0])] = terr_map.get(str(la[1]), "")

    result = []
    for m in movements:
        prod = products.get(str(m.product_id), {})
        ls = loadsheets.get(str(m.loadsheet_id), {}) if m.loadsheet_id else {}
        dealer_id = ls.get("dealer_id")
        dealer = dealers.get(dealer_id, {}) if dealer_id else {}
        result.append({
            "id": str(m.id),
            "station_id": str(m.station_id),
            "station_name": stations.get(str(m.station_id), ""),
            "territory_name": loadsheet_territories.get(str(m.loadsheet_id), "") if m.loadsheet_id else "",
            "product_id": str(m.product_id),
            "product_code": prod.get("code", ""),
            "product_name": prod.get("name", ""),
            "loadsheet_id": str(m.loadsheet_id) if m.loadsheet_id else None,
            "package_number": ls.get("package_number", ""),
            "sheet_no": ls.get("sheet_no", ""),
            "dealer_id": dealer_id,
            "dealer_code": dealer.get("code", ""),
            "dealer_name": dealer.get("name", ""),
            "movement_type": m.movement_type,
            "quantity_carton": m.quantity_carton,
            "quantity_pack": m.quantity_pack,
            "before_carton": m.before_carton,
            "before_pack": m.before_pack,
            "after_carton": m.after_carton,
            "after_pack": m.after_pack,
            "created_at": m.created_at.isoformat(),
            "note": m.note
        })

    return {
        "cycle_id": str(cycle_id),
        "movements": result,
        "count": len(result),
        "total": total,
        "limit": limit,
        "offset": offset
    }
