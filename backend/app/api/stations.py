"""
Stations API Router
İstasyon detayları endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from uuid import UUID
from typing import Dict, List, Optional
from pydantic import BaseModel
import re

from app.core.database import get_session
from app.models import (
    StationAssignment, Territory, Order, OrderLine, 
    Product, Dealer, Station, Loadsheet, LoadsheetLine, StationInventory
)
from app.models.user import User

router = APIRouter()


class CreateStationRequest(BaseModel):
    """İstasyon oluşturma isteği - isim otomatik oluşturulur"""
    pass  # İsim parametresi yok, otomatik oluşturulacak


def get_next_station_number(session: Session) -> int:
    """Sonraki istasyon numarasını bul (boşlukları doldur, yoksa sıradan devam et)"""
    # Tüm istasyonları al
    stmt = select(Station).order_by(Station.name)
    stations = session.exec(stmt).all()
    
    if not stations:
        return 1
    
    # İstasyon isimlerinden numaraları çıkar (İstasyon-1, İstasyon-2 gibi)
    numbers = []
    pattern = r'İstasyon-(\d+)'
    
    for station in stations:
        match = re.match(pattern, station.name)
        if match:
            numbers.append(int(match.group(1)))
    
    if not numbers:
        return 1
    
    numbers.sort()
    
    # Önce boşlukları kontrol et
    for i in range(1, numbers[-1]):
        if i not in numbers:
            return i
    
    # Boşluk yoksa sıradan devam et
    return numbers[-1] + 1


def create_tablet_user(station_number: int, station_id: UUID, session: Session) -> User:
    """İstasyon için tablet kullanıcısı oluştur"""
    username = f"tablet{station_number}"
    
    # Kullanıcı zaten var mı kontrol et
    stmt = select(User).where(User.username == username)
    existing_user = session.exec(stmt).first()
    
    if existing_user:
        # Mevcut kullanıcıyı güncelle
        existing_user.station_id = station_id
        existing_user.is_active = True
        session.add(existing_user)
        return existing_user
    
    # Yeni kullanıcı oluştur
    user = User(
        username=username,
        role="tablet",
        station_id=station_id,
        is_active=True
    )
    user.set_password("tablet123")  # Default şifre
    session.add(user)
    return user

@router.get("/")
async def list_stations(session: Session = Depends(get_session)):
    stations = session.exec(select(Station)).all()
    return [{"id": str(s.id), "name": s.name, "active": s.active} for s in stations]

@router.post("/")
async def create_station(session: Session = Depends(get_session)):
    """
    Yeni istasyon oluştur (otomatik isimlendirme)
    İstasyon adı: İstasyon-1, İstasyon-2, ...
    Her istasyon için tablet kullanıcısı otomatik oluşturulur: tablet1, tablet2, ...
    """
    # Sonraki istasyon numarasını bul
    station_number = get_next_station_number(session)
    station_name = f"İstasyon-{station_number}"
    
    # İstasyon oluştur
    station = Station(name=station_name, active=True)
    session.add(station)
    session.flush()  # ID'yi almak için flush
    
    # Tablet kullanıcısı oluştur
    tablet_user = create_tablet_user(station_number, station.id, session)
    
    session.commit()
    session.refresh(station)
    
    return {
        "id": str(station.id),
        "name": station.name,
        "active": station.active,
        "tablet_user": tablet_user.username
    }

@router.delete("/{station_id}")
async def delete_station(station_id: UUID, session: Session = Depends(get_session)):
    """
    İstasyon sil
    İlgili tablet kullanıcısı da silinir
    """
    station = session.get(Station, station_id)
    if not station:
        raise HTTPException(404, "İstasyon bulunamadı")
    
    # İlgili tablet kullanıcısını bul ve sil
    stmt = select(User).where(
        User.station_id == station_id,
        User.role == "tablet"
    )
    tablet_users = session.exec(stmt).all()
    
    for user in tablet_users:
        session.delete(user)
    
    # İstasyonu sil
    session.delete(station)
    session.commit()
    
    return {
        "success": True,
        "deleted_users": [user.username for user in tablet_users]
    }

@router.put("/{station_id}")
async def update_station(station_id: UUID, payload: Dict, session: Session = Depends(get_session)):
    station = session.get(Station, station_id)
    if not station:
        raise HTTPException(404, "İstasyon bulunamadı")
    if "active" in payload:
        station.active = payload["active"]
    if "name" in payload:
        station.name = payload["name"]
    session.add(station)
    session.commit()
    session.refresh(station)
    return {"id": str(station.id), "name": station.name, "active": station.active}


@router.get("/{station_id}/distribution/{cycle_id}")
async def get_station_distribution(
    station_id: UUID,
    cycle_id: UUID,
    session: Session = Depends(get_session)
):
    """
    İstasyon bazında detaylı ürün dağılımı (Excel formatı)
    Her ürün bir satır, her territory bir kolon
    """
    try:
        # İstasyon bilgisi
        station = session.get(Station, station_id)
        if not station:
            raise HTTPException(404, "İstasyon bulunamadı")
        
        # Bu istasyonun assignment'larını al
        stmt = select(StationAssignment).where(
            StationAssignment.cycle_id == cycle_id,
            StationAssignment.station_id == station_id
        )
        assignments = session.exec(stmt).all()
        
        if not assignments:
            return {
                "station_id": str(station_id),
                "station_name": station.name,
                "territories": [],
                "products": [],
                "grand_total": 0
            }
        
        # Territory'leri topla
        territory_ids = [a.territory_id for a in assignments]
        territories = []
        territory_map = {}
        
        for assignment in assignments:
            territory = session.get(Territory, assignment.territory_id)
            if territory:
                territories.append({
                    "id": str(territory.id),
                    "code": territory.code,
                    "display_number": territory.display_number,
                    "name": territory.name,
                    "full_name": f"{territory.display_number}-{territory.name}"
                })
                territory_map[str(territory.id)] = territory
        
        # Cycle'daki tüm ürünleri al (sadece bu cycle'da kullanılan ürünler)
        # Excel'deki sıraya göre sırala
        stmt = (
            select(Product)
            .join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, Order.id == OrderLine.order_id)
            .where(Order.cycle_id == cycle_id)
            .distinct()
            .order_by(Product.display_order, Product.code)
        )
        all_products = session.exec(stmt).all()
        
        # Bu territory'lerdeki tüm order'ları al
        stmt = select(Order).where(
            Order.cycle_id == cycle_id,
            Order.territory_id.in_(territory_ids)
        )
        orders = session.exec(stmt).all()
        
        # Ürün bazında territory'lere göre dağılımı hesapla
        # Structure: {product_code: {territory_id: {carton, pack}}}
        product_distribution = {}
        
        # Önce tüm ürünleri 0 ile başlat
        for product in all_products:
            product_distribution[product.code] = {
                "product_name": product.name,
                "territories": {},
                "total_carton": 0,
                "total_pack": 0
            }
        
        # Siparişlerdeki miktarları ekle
        for order in orders:
            # Order lines'ı al
            stmt = select(OrderLine).where(OrderLine.order_id == order.id)
            lines = session.exec(stmt).all()
            
            for line in lines:
                product = session.get(Product, line.product_id)
                if not product:
                    continue
                
                product_code = product.code
                territory_id = str(order.territory_id)
                
                if territory_id not in product_distribution[product_code]["territories"]:
                    product_distribution[product_code]["territories"][territory_id] = {
                        "carton": 0,
                        "pack": 0
                    }
                
                # Miktarları ekle
                product_distribution[product_code]["territories"][territory_id]["carton"] += line.qty_carton
                product_distribution[product_code]["territories"][territory_id]["pack"] += line.qty_pack
                
                # Toplam
                product_distribution[product_code]["total_carton"] += line.qty_carton
                product_distribution[product_code]["total_pack"] += line.qty_pack
        
        # Response hazırla - Excel sırasını koru (all_products zaten display_order'a göre sıralı)
        products_list = []
        grand_total_carton = 0
        
        # all_products sırasını kullan (display_order'a göre sıralı)
        for product in all_products:
            product_code = product.code
            data = product_distribution.get(product_code)
            if not data:
                continue
            # Her territory için miktar
            territory_quantities = []
            for territory in territories:
                t_id = territory["id"]
                if t_id in data["territories"]:
                    carton = data["territories"][t_id]["carton"]
                    pack = data["territories"][t_id]["pack"]
                    total = carton + (pack / 10)
                else:
                    carton = 0
                    pack = 0
                    total = 0
                
                territory_quantities.append({
                    "territory_id": t_id,
                    "territory_display": territory["display_number"],
                    "carton": carton,
                    "pack": pack,
                    "total_carton": round(total, 1)
                })
            
            total_carton = data["total_carton"] + (data["total_pack"] / 10)
            grand_total_carton += total_carton
            
            products_list.append({
                "product_code": product_code,
                "product_name": data["product_name"],
                "territories": territory_quantities,
                "total_carton": data["total_carton"],
                "total_pack": data["total_pack"],
                "total_carton_equivalent": round(total_carton, 1)
            })
        
        # Sayım hesaplamaları (Excel'deki gibi) - Ürün bazında
        # Sayım1: Tüm territory'lerin satır toplamı
        # Sayım2: İlk territory hariç
        # Sayım3: İlk 2 territory hariç
        # vs...
        
        # Her ürün için sayımları hesapla
        product_counts = []
        for product in products_list:
            product_count = {
                "product_code": product["product_code"],
                "counts": []
            }
            
            # Her sayım için (territory sayısı kadar)
            for start_idx in range(len(territories)):
                count_total = 0
                
                # Bu sayımda dahil olan territory'ler (start_idx'ten sona kadar)
                for idx in range(start_idx, len(territories)):
                    territory = territories[idx]
                    t_id = territory["id"]
                    territory_data = next((t for t in product["territories"] if t["territory_id"] == t_id), None)
                    if territory_data:
                        count_total += territory_data["total_carton"]
                
                product_count["counts"].append(round(count_total, 1))
            
            product_counts.append(product_count)
        
        # Toplam satırı için sayımlar
        total_counts = []
        for start_idx in range(len(territories)):
            count_total = 0
            for idx in range(start_idx, len(territories)):
                territory = territories[idx]
                t_id = territory["id"]
                # Tüm ürünler için bu territory'nin toplamını ekle
                for product in products_list:
                    territory_data = next((t for t in product["territories"] if t["territory_id"] == t_id), None)
                    if territory_data:
                        count_total += territory_data["total_carton"]
            total_counts.append(round(count_total, 1))
        
        return {
            "station_id": str(station_id),
            "station_name": station.name,
            "territories": territories,
            "products": products_list,
            "grand_total": round(grand_total_carton, 1),
            "product_counts": product_counts,
            "total_counts": total_counts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Dağılım getirme hatası: {str(e)}")


@router.get("/{station_id}/tracking/{cycle_id}")
async def get_station_tracking(
    station_id: UUID,
    cycle_id: UUID,
    session: Session = Depends(get_session)
):
    """
    İstasyon bazlı ürün takip tablosu:
    - Ürün kodu
    - Anlık stok (StationInventory'den)
    - Her territory için: Kalan ve Hazırlanan miktarları
    Kalan: Henüz tamamlanmamış loadsheet'lerdeki miktar
    Hazırlanan: Tamamlanmış loadsheet'lerdeki miktar
    """
    try:
        # İstasyon bilgisi
        station = session.get(Station, station_id)
        if not station:
            raise HTTPException(404, "İstasyon bulunamadı")
        
        # Bu istasyonun assignment'larını al
        stmt = select(StationAssignment).where(
            StationAssignment.cycle_id == cycle_id,
            StationAssignment.station_id == station_id
        )
        assignments = session.exec(stmt).all()
        
        if not assignments:
            return {
                "station_id": str(station_id),
                "station_name": station.name,
                "territories": [],
                "products": []
            }
        
        # Territory'leri topla
        territory_ids = [a.territory_id for a in assignments]
        territories = []
        
        for assignment in assignments:
            territory = session.get(Territory, assignment.territory_id)
            if territory:
                territories.append({
                    "id": str(territory.id),
                    "code": territory.code,
                    "display_number": territory.display_number,
                    "name": territory.name
                })
        
        # Cycle'daki tüm ürünleri al (display_order'a göre sıralı)
        stmt = (
            select(Product)
            .join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, Order.id == OrderLine.order_id)
            .where(Order.cycle_id == cycle_id)
            .distinct()
            .order_by(Product.display_order, Product.code)
        )
        all_products = session.exec(stmt).all()
        
        # İstasyon stoklarını al
        stmt = select(StationInventory).where(StationInventory.station_id == station_id)
        inventories = session.exec(stmt).all()
        inventory_map = {
            str(inv.product_id): {
                "carton": inv.quantity_carton,
                "pack": inv.quantity_pack
            }
            for inv in inventories
        }
        
        # Bu istasyonun loadsheet'lerini al (assignment_id üzerinden)
        assignment_ids = [a.id for a in assignments]
        # Assignment map oluştur (assignment_id -> territory_id)
        assignment_territory_map = {a.id: a.territory_id for a in assignments}
        
        stmt = select(Loadsheet).where(
            Loadsheet.cycle_id == cycle_id,
            Loadsheet.assignment_id.in_(assignment_ids)
        )
        loadsheets = session.exec(stmt).all()
        
        # Ürün bazında territory'lere göre kalan ve hazırlanan hesapla
        # Structure: {product_id: {territory_id: {remaining, prepared}}}
        product_tracking = {}
        
        for product in all_products:
            product_tracking[str(product.id)] = {
                "product_code": product.code,
                "product_name": product.name,
                "territories": {}
            }
        
        # Loadsheet'lerdeki miktarları hesapla
        for loadsheet in loadsheets:
            # Territory ID'yi assignment'ından al
            territory_id = str(assignment_territory_map.get(loadsheet.assignment_id))
            
            # Loadsheet lines'ı al
            stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == loadsheet.id)
            lines = session.exec(stmt).all()
            
            for line in lines:
                product_id = str(line.product_id)
                if product_id not in product_tracking:
                    continue
                
                if territory_id not in product_tracking[product_id]["territories"]:
                    product_tracking[product_id]["territories"][territory_id] = {
                        "remaining_carton": 0,
                        "remaining_pack": 0,
                        "prepared_carton": 0,
                        "prepared_pack": 0
                    }
                
                # Loadsheet tamamlanmışsa hazırlanan'a, değilse kalan'a ekle
                if loadsheet.completed_at:
                    product_tracking[product_id]["territories"][territory_id]["prepared_carton"] += line.qty_carton
                    product_tracking[product_id]["territories"][territory_id]["prepared_pack"] += line.qty_pack
                else:
                    product_tracking[product_id]["territories"][territory_id]["remaining_carton"] += line.qty_carton
                    product_tracking[product_id]["territories"][territory_id]["remaining_pack"] += line.qty_pack
        
        # Response hazırla
        products_list = []
        for product in all_products:
            product_id = str(product.id)
            tracking_data = product_tracking.get(product_id)
            if not tracking_data:
                continue
            
            # Stok bilgisi
            inventory = inventory_map.get(product_id, {"carton": 0, "pack": 0})
            
            # Her territory için kalan ve hazırlanan
            territory_data = []
            for territory in territories:
                t_id = territory["id"]
                t_data = tracking_data["territories"].get(t_id, {
                    "remaining_carton": 0,
                    "remaining_pack": 0,
                    "prepared_carton": 0,
                    "prepared_pack": 0
                })
                
                # Karton eşdeğeri hesapla
                remaining_total = t_data["remaining_carton"] + (t_data["remaining_pack"] / 10)
                prepared_total = t_data["prepared_carton"] + (t_data["prepared_pack"] / 10)
                
                territory_data.append({
                    "territory_id": t_id,
                    "territory_display": territory["display_number"],
                    "remaining_carton": t_data["remaining_carton"],
                    "remaining_pack": t_data["remaining_pack"],
                    "remaining_total": round(remaining_total, 1),
                    "prepared_carton": t_data["prepared_carton"],
                    "prepared_pack": t_data["prepared_pack"],
                    "prepared_total": round(prepared_total, 1)
                })
            
            products_list.append({
                "product_code": tracking_data["product_code"],
                "product_name": tracking_data["product_name"],
                "stock_carton": inventory["carton"],
                "stock_pack": inventory["pack"],
                "stock_total": round(inventory["carton"] + (inventory["pack"] / 10), 1),
                "territories": territory_data
            })
        
        return {
            "station_id": str(station_id),
            "station_name": station.name,
            "territories": territories,
            "products": products_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Takip verisi getirme hatası: {str(e)}")
