"""
Stations API Router
İstasyon detayları endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from uuid import UUID
from typing import Dict, List

from app.core.database import get_session
from app.models import (
    StationAssignment, Territory, Order, OrderLine, 
    Product, Dealer, Station
)

router = APIRouter()


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
