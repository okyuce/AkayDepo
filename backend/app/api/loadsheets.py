"""
Loadsheets API Router
Tablet için fiş yönetimi endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
import jwt

from app.core.database import get_session
from app.core.websocket import manager
from app.api.auth import (
    get_current_user, verify_depot_access,
    SECRET_KEY, ALGORITHM,
)
from app.models import (
    Loadsheet, LoadsheetLine, Station, StationAssignment,
    Territory, Dealer, Product, LoadCounter, TerritoryInfo
)
from app.services.zpl_generator import generate_loadsheet_zpl
from app.services.zebra_cloud import send_zpl, ZebraCloudError

router = APIRouter()

# ZPL print token'ı kısa ömürlü — sadece tek ZPL fetch için.
PRINT_TOKEN_TTL_SECONDS = 600
PRINT_TOKEN_TYPE = "loadsheet-zpl"

def _get_territory_display_name(session: Session, territory: Territory, depot_id) -> str:
    """TerritoryInfo master tablosundan doğru territory adını al"""
    if not territory:
        return ""
    stmt = select(TerritoryInfo).where(TerritoryInfo.code == territory.code)
    if depot_id:
        stmt = stmt.where(TerritoryInfo.depot_id == depot_id)
    ti = session.exec(stmt).first()
    return ti.name if ti else territory.name

@router.get("/station/{station_id}")
async def get_station_loadsheets(
    station_id: UUID,
    cycle_id: Optional[UUID] = None,
    import_batch: Optional[int] = None,
    sku: Optional[str] = None,
    sku_match: Optional[str] = "or",
    sku_qty_type: Optional[str] = None,
    sku_qty_value: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    İstasyonun fişlerini getir (Tablet görünümü için)

    Args:
        station_id: İstasyon ID
        cycle_id: Döngü ID (opsiyonel, yoksa son aktif döngü)
        sku: Virgülle ayrılmış ürün kodları (opsiyonel)
        sku_match: 'or' veya 'and' - SKU eşleşme modu (varsayılan: or)
        sku_qty_type: 'carton' veya 'pack' - miktar tipi filtresi
        sku_qty_value: Tam miktar değeri (opsiyonel, yoksa >0 yeterli)
    """
    try:
        from app.models import Cycle
        depot_id = current_user.get("depot_id")

        # Station depo kontrolü
        station = session.get(Station, station_id)
        if not station:
            raise HTTPException(404, "İstasyon bulunamadı")
        verify_depot_access(station, depot_id, "İstasyon")

        # Cycle belirle
        if cycle_id:
            cycle = session.get(Cycle, cycle_id)
            if not cycle:
                raise HTTPException(404, "Döngü bulunamadı")
            verify_depot_access(cycle, depot_id, "Döngü")
        else:
            stmt = select(Cycle).where(Cycle.status == "active")
            if depot_id:
                stmt = stmt.where(Cycle.depot_id == depot_id)
            stmt = stmt.order_by(Cycle.imported_at.desc())
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
        
        # SKU filtresi için ürün kodlarını parse et
        sku_codes = []
        if sku:
            sku_codes = [s.strip().upper() for s in sku.split(',') if s.strip()]
        sku_match_mode = sku_match.lower() if sku_match else "or"

        # Sipariş tarihlerini al (dealer_id + batch_number -> order_date)
        from app.models import Order
        order_stmt = select(Order).where(Order.cycle_id == cycle_id)
        orders = session.exec(order_stmt).all()
        order_date_map = {}
        for o in orders:
            key = (str(o.dealer_id), o.import_batch)
            if key not in order_date_map:
                order_date_map[key] = o.order_date

        # Territory bazında fişleri grupla
        territories_data = []
        total_carton = 0
        completed_carton = 0

        for assignment in assignments:
            territory = session.get(Territory, assignment.territory_id)
            
            # Bu territory'nin fişleri - opsiyonel import_batch filtresi ve parent dahil etme
            base_stmt = (
                select(Loadsheet)
                .join(Dealer, Loadsheet.dealer_id == Dealer.id)
                .where(Loadsheet.assignment_id == assignment.id)
                .order_by(Dealer.route_order)
            )
            if import_batch is not None:
                base_stmt = base_stmt.where(Loadsheet.batch_number == import_batch)
            base_loadsheets = session.exec(base_stmt).all()

            parent_ids: set = set()
            extra_parents = []
            if import_batch is not None:
                for bls in base_loadsheets:
                    if getattr(bls, "is_revision", False) and getattr(bls, "parent_loadsheet_id", None):
                        parent_ids.add(bls.parent_loadsheet_id)
                if parent_ids:
                    parent_stmt = select(Loadsheet).where(Loadsheet.id.in_(parent_ids))
                    extra_parents = session.exec(parent_stmt).all()

            # Birleştir (tekrarları önle)
            loadsheets_map = {ls.id: ls for ls in base_loadsheets}
            for pls in extra_parents:
                loadsheets_map[pls.id] = pls
            loadsheets = list(loadsheets_map.values())
            
            # Fiş detayları
            loadsheet_data = []
            territory_completed = 0
            
            for ls in loadsheets:
                dealer = session.get(Dealer, ls.dealer_id)

                # Toplam karton ve paket hesapla
                stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == ls.id)
                lines = session.exec(stmt).all()

                # SKU filtresi uygula
                if sku_codes:
                    # Bu loadsheet'teki ürün kodlarını ve miktarlarını al
                    line_product_map = {}
                    for line in lines:
                        product = session.get(Product, line.product_id)
                        if product:
                            line_product_map[product.code.upper()] = {
                                "carton": line.qty_carton,
                                "pack": line.qty_pack
                            }

                    def sku_matches(sku_code: str) -> bool:
                        if sku_code not in line_product_map:
                            return False
                        if not sku_qty_type:
                            return True  # Sadece SKU varlığı yeterli
                        qty = line_product_map[sku_code]
                        if sku_qty_type == "carton":
                            if sku_qty_value is not None:
                                return qty["carton"] == sku_qty_value
                            return qty["carton"] > 0
                        elif sku_qty_type == "pack":
                            if sku_qty_value is not None:
                                return qty["pack"] == sku_qty_value
                            return qty["pack"] > 0
                        return True

                    if sku_match_mode == "and":
                        if not all(sku_matches(sku_code) for sku_code in sku_codes):
                            continue
                    else:
                        if not any(sku_matches(sku_code) for sku_code in sku_codes):
                            continue

                ls_total_carton = sum(line.qty_carton for line in lines)
                ls_total_pack = sum(line.qty_pack for line in lines)
                ls_total_carton_equiv = sum(line.qty_carton + (line.qty_pack / 10) for line in lines)

                # Sipariş tarihini bul
                od = order_date_map.get((str(ls.dealer_id), ls.batch_number))

                loadsheet_data.append({
                    "id": str(ls.id),
                    "package_number": ls.package_number,
                    "dealer_code": dealer.code if dealer else "",
                    "dealer_name": dealer.name if dealer else "",
                    "route_order": dealer.route_order if dealer else 0,
                    "total_carton": ls_total_carton,
                    "total_pack": ls_total_pack,
                    "status": ls.status,
                    "batch_number": ls.batch_number,
                    "loadsheet_type": ls.loadsheet_type,
                    "completed_at": ls.completed_at.isoformat() if ls.completed_at else None,
                    "is_revision": ls.is_revision,
                    "parent_loadsheet_id": str(ls.parent_loadsheet_id) if ls.parent_loadsheet_id else None,
                    "loaded_at": ls.loaded_at.isoformat() if ls.loaded_at else None,
                    "included_as_parent": (ls.id in parent_ids) if import_batch is not None else False,
                    "order_date": od.isoformat() if od else None,
                    "cancelled_by_revision": ls.cancelled_by_revision
                })
                
                if ls.status == "loaded":
                    territory_completed += ls_total_carton_equiv
            
            territory_total = assignment.target_total_carton
            progress_percent = int((territory_completed / territory_total * 100)) if territory_total > 0 else 0
            
            # Sıralama:
            # - import_batch verildiyse: parent önce, sonra batch_number ASC, ardından tamamlanmayan üstte
            # - aksi halde: tamamlanmayanlar üstte, ardından batch_number ASC
            def _is_completed(item):
                return (item.get("completed_at") is not None) or (item.get("status") in ["loaded", "cancelled"])
            if import_batch is not None:
                loadsheet_data.sort(key=lambda x: (not x.get("included_as_parent", False), x["batch_number"], _is_completed(x)))
            else:
                loadsheet_data.sort(key=lambda x: (_is_completed(x), x["batch_number"]))
            
            territories_data.append({
                "territory_code": territory.code if territory else "",
                "display_number": territory.display_number if territory else "",
                "name": _get_territory_display_name(session, territory, depot_id) if territory else "",
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
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Fiş detayı"""
    loadsheet = session.get(Loadsheet, loadsheet_id)
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    depot_id = current_user.get("depot_id")
    verify_depot_access(loadsheet, depot_id, "Fiş")

    # Dealer
    dealer = session.get(Dealer, loadsheet.dealer_id)
    
    # Territory
    assignment = session.get(StationAssignment, loadsheet.assignment_id)
    territory = session.get(Territory, assignment.territory_id) if assignment else None
    
    # Lines - depo bazlı sıraya göre sırala
    from app.api.product_order import get_depot_order_map
    depot_order = get_depot_order_map(session, depot_id)

    stmt = (
        select(LoadsheetLine)
        .where(LoadsheetLine.loadsheet_id == loadsheet_id)
    )
    lines = session.exec(stmt).all()

    # Önceki fiş miktarlarını al (revizyon veya aynı bayi için önceki batch)
    parent_lines_map = {}
    has_previous = False

    if loadsheet.is_revision and loadsheet.parent_loadsheet_id:
        # Revizyon fişi - parent loadsheet ile karşılaştır
        parent_lines = session.exec(
            select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == loadsheet.parent_loadsheet_id)
        ).all()
        for pl in parent_lines:
            parent_lines_map[str(pl.product_id)] = {
                "qty_carton": pl.qty_carton,
                "qty_pack": pl.qty_pack
            }
        has_previous = True
    else:
        # Revizyon değilse, aynı dealer ve cycle için önceki batch'te fiş var mı kontrol et
        previous_loadsheet = session.exec(
            select(Loadsheet)
            .where(
                Loadsheet.cycle_id == loadsheet.cycle_id,
                Loadsheet.dealer_id == loadsheet.dealer_id,
                Loadsheet.batch_number < loadsheet.batch_number,
                Loadsheet.id != loadsheet.id
            )
            .order_by(Loadsheet.batch_number.desc())
        ).first()

        if previous_loadsheet:
            parent_lines = session.exec(
                select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == previous_loadsheet.id)
            ).all()
            for pl in parent_lines:
                parent_lines_map[str(pl.product_id)] = {
                    "qty_carton": pl.qty_carton,
                    "qty_pack": pl.qty_pack
                }
            has_previous = True

    lines_data = []
    total_carton = 0
    changes = [] if has_previous else None
    processed_product_ids = set()

    for line in lines:
        product = session.get(Product, line.product_id)
        line_total = line.qty_carton + (line.qty_pack / 10)
        total_carton += line_total
        processed_product_ids.add(str(line.product_id))

        # Değişim hesapla (önceki fiş varsa)
        qty_change_carton = None
        qty_change_pack = None
        if has_previous:
            parent_qty = parent_lines_map.get(str(line.product_id), {"qty_carton": 0, "qty_pack": 0})
            qty_change_carton = line.qty_carton - parent_qty["qty_carton"]
            qty_change_pack = line.qty_pack - parent_qty["qty_pack"]

            # changes listesine de ekle (mevcut yapıyı koru)
            if qty_change_carton != 0 or qty_change_pack != 0:
                change_type = "addition" if qty_change_carton > 0 else "reduction"
                changes.append({
                    "product_code": product.code if product else "",
                    "product_name": product.name if product else "",
                    "qty_change_carton": qty_change_carton,
                    "qty_change_pack": qty_change_pack,
                    "change_type": change_type
                })

        lines_data.append({
            "product_code": product.code if product else "",
            "product_name": product.name if product else "",
            "qty_carton": line.qty_carton,
            "qty_pack": line.qty_pack,
            "qty_change_carton": qty_change_carton,
            "qty_change_pack": qty_change_pack,
            "display_order": depot_order.get(str(line.product_id), product.display_order if product else 999)
        })

    # Önceki fişte olup yeni fişte olmayan ürünleri ekle (komple iptal edilenler)
    if has_previous:
        for product_id_str, parent_qty in parent_lines_map.items():
            if product_id_str not in processed_product_ids:
                product = session.get(Product, product_id_str)
                qty_change_carton = 0 - parent_qty["qty_carton"]
                qty_change_pack = 0 - parent_qty["qty_pack"]

                # changes listesine ekle
                if qty_change_carton != 0 or qty_change_pack != 0:
                    changes.append({
                        "product_code": product.code if product else "",
                        "product_name": product.name if product else "",
                        "qty_change_carton": qty_change_carton,
                        "qty_change_pack": qty_change_pack,
                        "change_type": "removed"
                    })

                lines_data.append({
                    "product_code": product.code if product else "",
                    "product_name": product.name if product else "",
                    "qty_carton": 0,
                    "qty_pack": 0,
                    "qty_change_carton": qty_change_carton,
                    "qty_change_pack": qty_change_pack,
                    "display_order": depot_order.get(product_id_str, product.display_order if product else 999)
                })

    # Tüm ürünleri display_order'a göre sırala
    lines_data.sort(key=lambda x: (x.get("display_order", 999), x.get("product_code", "")))

    # Response'dan display_order'ı kaldır (frontend'e gitmesine gerek yok)
    for line in lines_data:
        line.pop("display_order", None)

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
            "name": _get_territory_display_name(session, territory, depot_id) if territory else ""
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
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Fişi tamamla (Yükleme Tamamlandı) ve stoktan düş"""
    from app.models import StationInventory, StockMovement

    # SELECT FOR UPDATE - Race condition önleme
    loadsheet = session.exec(
        select(Loadsheet).where(Loadsheet.id == loadsheet_id).with_for_update()
    ).first()
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    depot_id_check = current_user.get("depot_id")
    verify_depot_access(loadsheet, depot_id_check, "Fiş")

    # İdempotency: Zaten tamamlanmış fişi tekrar işleme alma
    if loadsheet.status == "loaded":
        assignment = session.get(StationAssignment, loadsheet.assignment_id)
        stmt = select(Loadsheet).where(Loadsheet.assignment_id == assignment.id)
        all_loadsheets = session.exec(stmt).all()
        territory_completed = all(ls.status == "loaded" for ls in all_loadsheets)

        return {
            "loadsheet_id": str(loadsheet_id),
            "status": "loaded",
            "loaded_at": loadsheet.loaded_at.isoformat() if loadsheet.loaded_at else None,
            "territory_completed": territory_completed,
            "already_completed": True
        }

    # Durumu HEMEN güncelle ve commit et - race condition önleme
    # Böylece eşzamanlı ikinci istek status="loaded" görür ve yukarıdaki idempotency kontrolüne takılır
    loadsheet.status = "loaded"
    loadsheet.loaded_at = datetime.now()
    loadsheet.completed_at = datetime.now()
    session.add(loadsheet)
    session.commit()
    session.refresh(loadsheet)
    
    # STOK DÜŞÜRME: Pack-equivalent ile atomik düşüm (1 karton = 10 paket)
    assignment = session.get(StationAssignment, loadsheet.assignment_id)
    if assignment:
        # Loadsheet lines'ı al
        stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == loadsheet_id)
        lines = session.exec(stmt).all()
        
        for line in lines:
            # Mevcut stok kaydını bul
            stmt = select(StationInventory).where(
                StationInventory.station_id == assignment.station_id,
                StationInventory.product_id == line.product_id
            )
            inventory = session.exec(stmt).first()
            
            # Upsert: Kayıt yoksa 0'dan oluştur
            if not inventory:
                from app.models import StationInventory as SI
                inventory = SI(
                    station_id=assignment.station_id,
                    product_id=line.product_id,
                    quantity_carton=0,
                    quantity_pack=0
                )
                print(f"INFO: StationInventory kaydı yoktu, oluşturuldu (station={assignment.station_id}, product={line.product_id})")
                session.add(inventory)
                session.flush()
            
            # Önceki stok durumunu kaydet (hareket logu için)
            before_carton = inventory.quantity_carton
            before_pack = inventory.quantity_pack

            # Toplam stok ve talep edilen miktarı paket eşdeğerine çevir
            total_packs_equiv = inventory.quantity_carton * 10 + inventory.quantity_pack
            demand_packs_equiv = line.qty_carton * 10 + line.qty_pack
            new_total = total_packs_equiv - demand_packs_equiv

            # UYARI: Negatif olabilir, engellemiyoruz ama loglayalım
            if new_total < 0:
                print(f"UYARI: {assignment.station_id} / ürün {line.product_id} için stok yetersiz: {total_packs_equiv} -> {new_total}")

            # Normalize ederek geri yaz (karton, paket)
            inventory.quantity_carton = new_total // 10
            inventory.quantity_pack = new_total % 10
            inventory.updated_at = datetime.now()
            session.add(inventory)

            # Stok hareket logu kaydet
            movement = StockMovement(
                station_id=assignment.station_id,
                product_id=line.product_id,
                loadsheet_id=loadsheet_id,
                movement_type="deduction",
                quantity_carton=line.qty_carton,
                quantity_pack=line.qty_pack,
                before_carton=before_carton,
                before_pack=before_pack,
                after_carton=inventory.quantity_carton,
                after_pack=inventory.quantity_pack
            )
            session.add(movement)
    
    session.commit()

    # Cache temizle - aktif cycle sayıları değişti
    from app.core.cache import cache_delete_pattern
    cache_delete_pattern(f"active_cycle:{depot_id_check}")

    # Territory tamamlandı mı kontrol et
    assignment = session.get(StationAssignment, loadsheet.assignment_id)
    stmt = select(Loadsheet).where(Loadsheet.assignment_id == assignment.id)
    all_loadsheets = session.exec(stmt).all()

    territory_completed = all(ls.status == "loaded" for ls in all_loadsheets)
    
    # WebSocket bildirimi gönder
    depot_id = current_user.get("depot_id") or "default"
    await manager.notify_loadsheet_completed(
        station_id=assignment.station_id,
        loadsheet_id=loadsheet_id,
        package_number=loadsheet.package_number,
        territory_completed=territory_completed,
        depot_id=str(depot_id)
    )
    
    return {
        "loadsheet_id": str(loadsheet_id),
        "status": "loaded",
        "loaded_at": loadsheet.loaded_at.isoformat(),
        "territory_completed": territory_completed
    }


@router.post("/{loadsheet_id}/cancel")
async def cancel_loadsheet(
    loadsheet_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Fişi iptal et (sadece admin). Tamamlanmış fişlerde stok geri eklenir."""
    from app.models import StationInventory, StockMovement

    # Sadece admin
    if current_user.get("role") not in ("admin", "superadmin"):
        raise HTTPException(403, "Bu işlem sadece admin kullanıcılar için geçerlidir")

    loadsheet = session.exec(
        select(Loadsheet).where(Loadsheet.id == loadsheet_id).with_for_update()
    ).first()
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    depot_id = current_user.get("depot_id")
    verify_depot_access(loadsheet, depot_id, "Fiş")

    if loadsheet.status == "cancelled":
        return {"loadsheet_id": str(loadsheet_id), "status": "cancelled", "already_cancelled": True}

    was_loaded = loadsheet.status == "loaded"

    # Tamamlanmış fişse stok geri ekle
    if was_loaded:
        assignment = session.get(StationAssignment, loadsheet.assignment_id)
        if assignment:
            stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == loadsheet_id)
            lines = session.exec(stmt).all()

            for line in lines:
                stmt = select(StationInventory).where(
                    StationInventory.station_id == assignment.station_id,
                    StationInventory.product_id == line.product_id
                )
                inventory = session.exec(stmt).first()

                if not inventory:
                    inventory = StationInventory(
                        station_id=assignment.station_id,
                        product_id=line.product_id,
                        quantity_carton=0,
                        quantity_pack=0
                    )
                    session.add(inventory)
                    session.flush()

                before_carton = inventory.quantity_carton
                before_pack = inventory.quantity_pack

                # Stok geri ekle (ters yönde)
                total_packs_equiv = inventory.quantity_carton * 10 + inventory.quantity_pack
                return_packs_equiv = line.qty_carton * 10 + line.qty_pack
                new_total = total_packs_equiv + return_packs_equiv

                inventory.quantity_carton = new_total // 10
                inventory.quantity_pack = new_total % 10
                inventory.updated_at = datetime.now()
                session.add(inventory)

                # Stok hareket logu - iade
                movement = StockMovement(
                    station_id=assignment.station_id,
                    product_id=line.product_id,
                    loadsheet_id=loadsheet_id,
                    movement_type="cancel_return",
                    quantity_carton=line.qty_carton,
                    quantity_pack=line.qty_pack,
                    before_carton=before_carton,
                    before_pack=before_pack,
                    after_carton=inventory.quantity_carton,
                    after_pack=inventory.quantity_pack
                )
                session.add(movement)

    loadsheet.status = "cancelled"
    loadsheet.completed_at = None
    loadsheet.loaded_at = None
    session.add(loadsheet)
    session.commit()

    return {"loadsheet_id": str(loadsheet_id), "status": "cancelled", "stock_returned": was_loaded}


@router.post("/{loadsheet_id}/uncancel")
async def uncancel_loadsheet(
    loadsheet_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """İptal edilen fişi geri al (sadece admin). Fiş pending durumuna döner."""
    # Sadece admin
    if current_user.get("role") not in ("admin", "superadmin"):
        raise HTTPException(403, "Bu işlem sadece admin kullanıcılar için geçerlidir")

    loadsheet = session.exec(
        select(Loadsheet).where(Loadsheet.id == loadsheet_id).with_for_update()
    ).first()
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    depot_id = current_user.get("depot_id")
    verify_depot_access(loadsheet, depot_id, "Fiş")

    if loadsheet.status != "cancelled":
        raise HTTPException(400, "Bu fiş iptal durumunda değil")

    loadsheet.status = "pending"
    session.add(loadsheet)
    session.commit()

    return {"loadsheet_id": str(loadsheet_id), "status": "pending"}


# ---------------------------------------------------------------------------
# Zebra (AkayPrintBT) entegrasyonu
# ---------------------------------------------------------------------------

@router.post("/{loadsheet_id}/print-token")
async def issue_print_token(
    loadsheet_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Kısa ömürlü ZPL fetch token'ı üret.

    iPad'deki AkayPrintBT app'i `?token=...` ile ZPL endpoint'ini çağırırken
    Authorization header gönderemediği için, Bearer ile çağrılan bu endpoint'ten
    kısa ömürlü (≤2 dk) JWT alınır. Frontend bu token'ı `akayprintbt://print?url=`
    parametresine gömer.
    """
    loadsheet = session.get(Loadsheet, loadsheet_id)
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    depot_id = current_user.get("depot_id")
    verify_depot_access(loadsheet, depot_id, "Fiş")

    payload = {
        "type": PRINT_TOKEN_TYPE,
        "ls": str(loadsheet_id),
        "uid": current_user.get("user_id"),
        "depot_id": depot_id,
        "exp": datetime.now() + timedelta(seconds=PRINT_TOKEN_TTL_SECONDS),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "token": token,
        "expires_in": PRINT_TOKEN_TTL_SECONDS,
        "loadsheet_id": str(loadsheet_id),
    }


def _verify_print_token(token: str, loadsheet_id: UUID) -> dict:
    """ZPL print token'ı doğrula. Aksi halde 401."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Print token süresi dolmuş")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Geçersiz print token")

    if payload.get("type") != PRINT_TOKEN_TYPE:
        raise HTTPException(401, "Yanlış token tipi")
    if payload.get("ls") != str(loadsheet_id):
        raise HTTPException(403, "Token bu fiş için değil")
    return payload


@router.get("/{loadsheet_id}/zpl")
async def get_loadsheet_zpl(
    loadsheet_id: UUID,
    token: str = Query(..., description="Print token (zorunlu, /print-token'den alınır)"),
    session: Session = Depends(get_session),
):
    """
    Fiş için ham ZPL döndür. text/plain; charset=utf-8.

    Auth: yalnızca `?token=<short-jwt>` desteklenir. iPad'deki AkayPrintBT URL
    fetch'te Authorization header gönderemediği için Bearer auth bu endpoint'te
    desteklenmiyor. Tarayıcıdan test için önce /print-token al, sonra ?token=...
    ile çağır.
    """
    payload = _verify_print_token(token, loadsheet_id)
    depot_id: Optional[str] = payload.get("depot_id")

    loadsheet = session.get(Loadsheet, loadsheet_id)
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    if depot_id:
        verify_depot_access(loadsheet, depot_id, "Fiş")

    try:
        zpl = generate_loadsheet_zpl(session, loadsheet_id, depot_id)
    except KeyError:
        raise HTTPException(404, "Fiş bulunamadı")

    # printed_at güncelle (sadece ilk başarılı render'da set et).
    if loadsheet.printed_at is None:
        loadsheet.printed_at = datetime.now()
        session.add(loadsheet)
        session.commit()

    return Response(
        content=zpl,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "X-Loadsheet-Id": str(loadsheet_id),
        },
    )


# ---------------------------------------------------------------------------
# Zebra bulut yazdırma (Online Print — SendFileToPrinter)
# ---------------------------------------------------------------------------

@router.post("/{loadsheet_id}/cloud-print")
async def cloud_print_loadsheet(
    loadsheet_id: UUID,
    serial: Optional[str] = Query(None, description="Yazıcı seri no (yoksa .env varsayılanı)"),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Fişi Zebra Data Services üzerinden doğrudan yazıcıya bas ("Online Print").

    ZPL, Bluetooth yolundaki ile **birebir aynı** `generate_loadsheet_zpl` ile
    üretilir; tek fark taşıma katmanı — app/BT yerine bulut. Yazıcı seri no
    verilmezse `.env`'deki varsayılan kullanılır (lokal test için).
    """
    loadsheet = session.get(Loadsheet, loadsheet_id)
    if not loadsheet:
        raise HTTPException(404, "Fiş bulunamadı")
    depot_id = current_user.get("depot_id")
    verify_depot_access(loadsheet, depot_id, "Fiş")

    try:
        zpl = generate_loadsheet_zpl(session, loadsheet_id, depot_id)
    except KeyError:
        raise HTTPException(404, "Fiş bulunamadı")

    try:
        result = send_zpl(zpl, serial=serial, filename=f"fis-{loadsheet.package_number or loadsheet_id}.zpl")
    except ZebraCloudError as exc:
        raise HTTPException(502, str(exc))

    # printed_at — BT yolundaki ile aynı davranış (sadece ilk basımda set edilir).
    if loadsheet.printed_at is None:
        loadsheet.printed_at = datetime.now()
        session.add(loadsheet)
        session.commit()

    return {
        "status": "sent",
        "loadsheet_id": str(loadsheet_id),
        "printer_serial": result.serial,
        "zebra_status": result.status_code,
        "zebra_guid": result.guid,
        "zebra_response": result.body[:400],
    }
