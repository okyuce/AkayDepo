"""
Station Planner Service
İstasyon planlama ve territory dağıtımı (ALGO_STATIONS.md)
"""
from typing import List, Dict, Tuple, Optional
from uuid import UUID
from sqlmodel import Session, select
from app.models import Territory, Order, OrderLine, Station, StationAssignment, Cycle
from datetime import date

class StationPlanner:
    """İstasyon planlama servisi"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_plan(
        self,
        cycle_id: UUID,
        worker_count: int,
        force_station_count: Optional[int] = None,
        method: str = "greedy"
    ) -> Dict:
        """
        İstasyon planı oluştur
        
        Args:
            cycle_id: Döngü ID
            worker_count: Depocu sayısı
            force_station_count: Zorla istasyon sayısı (None = otomatik)
            method: "greedy" veya "ilp"
            
        Returns:
            Plan detayları ve uyarılar
        """
        # Cycle bilgisi al
        cycle = self.session.get(Cycle, cycle_id)
        if not cycle:
            raise Exception("Döngü bulunamadı")
        
        # Territory'leri ve yüklerini hesapla
        territory_loads = self._calculate_territory_loads(cycle_id)
        
        if not territory_loads:
            raise Exception("Döngüde sipariş bulunamadı")
        
        # Dengesizlik kontrolü
        total_carton = sum(territory_loads.values())
        avg_carton = total_carton / worker_count
        threshold = avg_carton * 1.5
        
        warnings = []
        suggested_station_count = worker_count
        
        # Büyük territory kontrolü
        for territory_code, carton in territory_loads.items():
            if carton > threshold:
                suggested_station_count = int(total_carton / 335) + 1  # 335 = hedef ortalama
                warnings.append({
                    "type": "unbalanced_load",
                    "territory": territory_code,
                    "carton": carton,
                    "threshold": threshold,
                    "suggested_station_count": suggested_station_count,
                    "message": f"{territory_code.split('-')[-1]} çok büyük ({carton:.1f} karton). {suggested_station_count} istasyon açılması öneriliyor."
                })
                break
        
        # İstasyon sayısını belirle
        station_count = force_station_count if force_station_count else worker_count
        
        # Greedy algoritma ile dağıt
        if method == "greedy":
            assignments = self._greedy_distribution(territory_loads, station_count)
        else:
            raise NotImplementedError("ILP henüz implement edilmedi")
        
        # Veritabanına kaydet
        self._save_assignments(cycle_id, cycle.plan_date, assignments)
        
        # Response hazırla
        stations_data = []
        for station_idx, territories in enumerate(assignments, 1):
            station_total = sum(territory_loads[t] for t in territories)
            
            # Territory detayları
            territory_details = []
            for territory_code in territories:
                stmt = select(Territory).where(Territory.code == territory_code)
                territory = self.session.exec(stmt).first()
                
                # Bayi sayısı
                dealer_count = self._get_dealer_count_for_territory(cycle_id, territory_code)
                
                territory_details.append({
                    "territory_code": territory_code,
                    "display_number": territory.display_number if territory else "T00",
                    "carton": round(territory_loads[territory_code], 1),
                    "dealer_count": dealer_count
                })
            
            stations_data.append({
                "station_name": f"İstasyon-{station_idx}",
                "total_carton": round(station_total, 1),
                "territories": territory_details
            })
        
        return {
            "plan_id": str(cycle_id),
            "cycle_id": str(cycle_id),
            "total_carton": round(total_carton, 1),
            "avg_carton_per_station": round(avg_carton, 1),
            "station_count": station_count,
            "stations": stations_data,
            "warnings": warnings
        }
    
    def _calculate_territory_loads(self, cycle_id: UUID) -> Dict[str, float]:
        """
        Döngüdeki her territory için toplam karton hesapla
        
        Returns:
            {territory_code: total_carton}
        """
        # Döngünün tüm order'larını al
        stmt = select(Order).where(Order.cycle_id == cycle_id)
        orders = self.session.exec(stmt).all()
        
        territory_loads = {}
        
        for order in orders:
            # Territory code'u al
            territory = self.session.get(Territory, order.territory_id)
            if not territory:
                continue
            
            # Order lines'ı al
            stmt = select(OrderLine).where(OrderLine.order_id == order.id)
            lines = self.session.exec(stmt).all()
            
            # Toplam karton hesapla (paket dahil: 1 karton = 10 paket)
            total_carton = 0
            for line in lines:
                total_carton += line.qty_carton + (line.qty_pack / 10)
            
            # Territory toplama ekle
            if territory.code not in territory_loads:
                territory_loads[territory.code] = 0
            territory_loads[territory.code] += total_carton
        
        return territory_loads
    
    def _greedy_distribution(
        self, 
        territory_loads: Dict[str, float], 
        station_count: int
    ) -> List[List[str]]:
        """
        Greedy load balancing algoritması (ALGO_STATIONS.md)
        
        Args:
            territory_loads: {territory_code: carton}
            station_count: İstasyon sayısı
            
        Returns:
            [[territory_code, ...], ...] (istasyon başına territory listesi)
        """
        # Territory'leri azalan sırada sırala
        sorted_territories = sorted(
            territory_loads.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # İstasyon kovaları (her biri territory listesi + toplam yük)
        stations = [{"territories": [], "total": 0.0} for _ in range(station_count)]
        
        # Her territory'yi en az yüklü istasyona ata
        for territory_code, carton in sorted_territories:
            # En az yüklü istasyonu bul
            min_station = min(stations, key=lambda s: s["total"])
            
            # Territory'yi ata
            min_station["territories"].append(territory_code)
            min_station["total"] += carton
        
        # Sadece territory listelerini döndür
        return [station["territories"] for station in stations]
    
    def _save_assignments(
        self,
        cycle_id: UUID,
        plan_date: date,
        assignments: List[List[str]]
    ):
        """İstasyon atamalarını veritabanına kaydet"""
        # Önce bu cycle için mevcut atamaları sil - Raw SQL ile cascade delete
        from sqlalchemy import text
        
        # 1. Loadsheet_lines'ı sil
        self.session.execute(
            text("""
                DELETE FROM loadsheet_lines 
                WHERE loadsheet_id IN (
                    SELECT id FROM loadsheets 
                    WHERE assignment_id IN (
                        SELECT id FROM station_assignments 
                        WHERE cycle_id = :cycle_id
                    )
                )
            """),
            {"cycle_id": str(cycle_id)}
        )
        
        # 2. Loadsheets'ı sil
        self.session.execute(
            text("""
                DELETE FROM loadsheets 
                WHERE assignment_id IN (
                    SELECT id FROM station_assignments 
                    WHERE cycle_id = :cycle_id
                )
            """),
            {"cycle_id": str(cycle_id)}
        )
        
        # 3. Station assignments'ı sil
        self.session.execute(
            text("DELETE FROM station_assignments WHERE cycle_id = :cycle_id"),
            {"cycle_id": str(cycle_id)}
        )
        
        self.session.commit()
        
        # İstasyonları al veya oluştur
        for idx, territories in enumerate(assignments, 1):
            # İstasyon adı
            station_name = f"İstasyon-{idx}"
            
            # İstasyon var mı kontrol et
            stmt = select(Station).where(Station.name == station_name)
            station = self.session.exec(stmt).first()
            
            if not station:
                station = Station(name=station_name, active=True)
                self.session.add(station)
                self.session.flush()
            
            # Her territory için assignment oluştur
            for rank, territory_code in enumerate(territories, 1):
                # Territory ID bul
                stmt = select(Territory).where(Territory.code == territory_code)
                territory = self.session.exec(stmt).first()
                
                if not territory:
                    continue
                
                # Territory'nin toplam kartonunu hesapla
                territory_loads = self._calculate_territory_loads(cycle_id)
                total_carton = territory_loads.get(territory_code, 0)
                
                # Assignment oluştur
                assignment = StationAssignment(
                    cycle_id=cycle_id,
                    plan_date=plan_date,
                    station_id=station.id,
                    territory_id=territory.id,
                    load_rank=rank,
                    target_total_carton=int(total_carton),
                    target_total_pack=0  # Şimdilik 0, gerekirse hesaplanır
                )
                self.session.add(assignment)
        
        self.session.commit()
    
    def _get_dealer_count_for_territory(self, cycle_id: UUID, territory_code: str) -> int:
        """Bir territory'de kaç bayi var?"""
        stmt = select(Territory).where(Territory.code == territory_code)
        territory = self.session.exec(stmt).first()
        
        if not territory:
            return 0
        
        # Bu territory'nin order'larından unique dealer sayısı
        stmt = select(Order).where(
            Order.cycle_id == cycle_id,
            Order.territory_id == territory.id
        )
        orders = self.session.exec(stmt).all()
        
        unique_dealers = set(order.dealer_id for order in orders)
        return len(unique_dealers)
