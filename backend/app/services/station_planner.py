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
        self._depot_id = None

    def create_plan(
        self,
        cycle_id: UUID,
        worker_count: int,
        force_station_count: Optional[int] = None,
        method: str = "greedy",
        depot_id: str = None
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
        self._depot_id = depot_id

        # Cycle bilgisi al
        cycle = self.session.get(Cycle, cycle_id)
        if not cycle:
            raise Exception("Döngü bulunamadı")
        
        # İstasyon sayısını kilitle / kullan
        fixed_count = getattr(cycle, 'fixed_station_count', None)
        if fixed_count is None:
            station_count = force_station_count if force_station_count else worker_count
            # Eğer model attribute'u yoksa (eski kod), direkt station_count kullan; varsa alanı set et
            if hasattr(cycle, 'fixed_station_count'):
                cycle.fixed_station_count = station_count
                self.session.add(cycle)
                self.session.commit()
        else:
            station_count = fixed_count

        # Territory'leri ve yüklerini hesapla
        territory_loads = self._calculate_territory_loads(cycle_id)
        
        if not territory_loads:
            raise Exception("Döngüde sipariş bulunamadı")
        
        # Dengesizlik kontrolü
        total_carton = sum(territory_loads.values())
        avg_carton = total_carton / station_count
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
        
        from sqlmodel import select
        from app.models import StationAssignment, Territory, Order

# Manuel planlama açık mı?
        from app.models import PlanningConfig, StationTerritoryMap, TerritoryInfo
        cfg = self.session.exec(select(PlanningConfig).where(PlanningConfig.depot_id == self._depot_id)).first() if self._depot_id else self.session.exec(select(PlanningConfig)).first()
        manual_mode = bool(cfg and not cfg.auto_planning_enabled)

        existing_assignments = self.session.exec(
            select(StationAssignment).where(StationAssignment.cycle_id == cycle_id)
        ).all()

        if manual_mode:
            # Manual mapping uygula: aktif istasyonlar için mapping'i oku ve SADECE YENİ territory'leri ata
            # Mevcut assignment'ları KORUYORUZ (loadsheet foreign key nedeniyle)
            
            mappings = self.session.exec(select(StationTerritoryMap)).all()
            # Aktif istasyon seti
            active_station_ids = {s.id for s in self.session.exec(select(Station).where(Station.active == True, Station.depot_id == self._depot_id)).all()} if self._depot_id else {s.id for s in self.session.exec(select(Station).where(Station.active == True)).all()}

            by_station: Dict[UUID, List[str]] = {}
            for m in mappings:
                if m.station_id in active_station_ids:
                    by_station.setdefault(m.station_id, []).append(m.territory_code)

            # Zaten atanmış territory'leri bul
            assigned_territory_ids = {a.territory_id for a in existing_assignments}
            assigned_codes = set()
            for tid in assigned_territory_ids:
                t = self.session.get(Territory, tid)
                if t:
                    assigned_codes.add(t.code)

            # Her istasyon için SADECE YENİ territory'leri ekle
            from app.models import Territory as TerritoryModel
            for station_id, codes in by_station.items():
                station = self.session.get(Station, station_id)
                for rank, code in enumerate(codes, start=1):
                    # Zaten atanmışsa skip
                    if code in assigned_codes:
                        continue
                    
                    territory = self.session.exec(select(TerritoryModel).where(TerritoryModel.code == code)).first()
                    if not territory:
                        continue
                    total_carton = int(self._calculate_territory_loads(cycle_id).get(code, 0))
                    self.session.add(StationAssignment(
                        cycle_id=cycle_id,
                        plan_date=cycle.plan_date,
                        station_id=station.id,
                        territory_id=territory.id,
                        load_rank=rank,
                        target_total_carton=total_carton,
                        target_total_pack=0,
                    ))
            self.session.commit()
        else:
            if not existing_assignments:
                # İlk planlama - yeni dağıtım (greedy)
                if method == "greedy":
                    assignments = self._greedy_distribution(territory_loads, station_count)
                else:
                    raise NotImplementedError("ILP henüz implement edilmedi")
                self._save_assignments_incremental(cycle_id, cycle.plan_date, assignments, station_count)
            else:
                # İnkremental planlama - sadece yeni territory'leri dağıt
                latest_batch = self.session.exec(
                    select(Order.import_batch).where(Order.cycle_id==cycle_id).order_by(Order.import_batch.desc())
                ).first()
                if latest_batch is None:
                    raise Exception("Geçerli batch bulunamadı")
                
                # Yeni batch'teki territory'leri bul
                new_territory_codes = self._get_territories_for_batch(cycle_id, latest_batch)
                
                # Zaten atanmış territory'leri filtrele
                assigned_territory_ids = {a.territory_id for a in existing_assignments}
                assigned_codes = set()
                for tid in assigned_territory_ids:
                    t = self.session.get(Territory, tid)
                    if t:
                        assigned_codes.add(t.code)
                
                # Atanmamış territory'leri bul
                to_assign_codes = [code for code in new_territory_codes if code not in assigned_codes]
                
                if to_assign_codes:
                    # Mevcut istasyon yüklerini hesapla
                    station_loads = self._calculate_current_station_loads(cycle_id, station_count)
                    
                    # Yeni territory'ler için yükleri hesapla
                    territory_batch_loads = self._calculate_territory_loads_for_batch(cycle_id, latest_batch, to_assign_codes)
                    
                    # İnkremental dağıtım - mevcut yüklere göre en az yüklü istasyonlara dağıt
                    incremental_assignments = self._greedy_distribution_with_initial(station_loads, territory_batch_loads, station_count)
                    
                    # Sadece yeni territory'leri kaydet
                    self._save_assignments_incremental(cycle_id, cycle.plan_date, incremental_assignments, station_count)
        
        # Tüm assignment'ların target_total_carton değerlerini güncelle (güncel yüklerle)
        all_assignments = self.session.exec(
            select(StationAssignment).where(StationAssignment.cycle_id == cycle_id)
        ).all()
        
        for assignment in all_assignments:
            territory = self.session.get(Territory, assignment.territory_id)
            if territory:
                # Güncel yükü hesapla ve güncelle
                current_load = territory_loads.get(territory.code, 0)
                assignment.target_total_carton = int(current_load)
        
        self.session.commit()
        
        # Response hazırla - tüm mevcut assignment'lardan
        stations_data = []
        all_assignments = self.session.exec(
            select(StationAssignment).where(StationAssignment.cycle_id == cycle_id)
        ).all()
        
        # İstasyon bazında grupla
        from collections import defaultdict
        by_station = defaultdict(list)
        for sa in all_assignments:
            by_station[sa.station_id].append(sa)
        
        # Her istasyon için detay hazırla
        for station_idx in range(1, station_count + 1):
            station_name = f"İstasyon-{station_idx}"
            stmt = select(Station).where(Station.name == station_name)
            station = self.session.exec(stmt).first()
            
            if not station:
                continue
                
            station_assignments = by_station.get(station.id, [])
            
            territory_details = []
            station_total = 0.0
            
            for sa in station_assignments:
                territory = self.session.get(Territory, sa.territory_id)
                if not territory:
                    continue
                
                # Territory yükü
                territory_carton = territory_loads.get(territory.code, 0)
                station_total += territory_carton
                
                # Bayi sayısı
                dealer_count = self._get_dealer_count_for_territory(cycle_id, territory.code)
                
                territory_details.append({
                    "territory_code": territory.code,
                    "display_number": territory.display_number,
                    "carton": round(territory_carton, 1),
                    "dealer_count": dealer_count
                })
            
            stations_data.append({
                "station_name": station_name,
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
    
    def _save_assignments_incremental(
        self,
        cycle_id: UUID,
        plan_date: date,
        assignments: List[List[str]],
        station_count: int
    ):
        """Atamaları silmeden, yalnızca yeni territory'ler için kayıt ekle."""
        from sqlmodel import select
        
        # İstasyonları al veya oluştur (kilitli istasyon sayısı kadar)
        for idx in range(1, station_count + 1):
            station_name = f"İstasyon-{idx}"
            stmt = select(Station).where(Station.name == station_name)
            station = self.session.exec(stmt).first()
            if not station:
                station = Station(name=station_name, active=True, depot_id=self._depot_id)
                self.session.add(station)
                self.session.flush()
        
        # Mevcut assignment'ları set olarak al (territory_id bazlı)
        existing = set()
        from app.models import StationAssignment, Territory
        for sa in self.session.exec(select(StationAssignment).where(StationAssignment.cycle_id==cycle_id)).all():
            existing.add(sa.territory_id)
        
        # Assignment ekle
        for idx, territories in enumerate(assignments, 1):
            # İstasyon id'yi getir
            station_name = f"İstasyon-{idx}"
            station = self.session.exec(select(Station).where(Station.name==station_name)).first()
            for rank, territory_code in enumerate(territories, 1):
                territory = self.session.exec(select(Territory).where(Territory.code==territory_code)).first()
                if not territory or territory.id in existing:
                    continue
                # Territory toplam karton (tüm cycle) — sadece gösterim amaçlı
                total_carton = self._calculate_territory_loads(cycle_id).get(territory_code, 0)
                assignment = StationAssignment(
                    cycle_id=cycle_id,
                    plan_date=plan_date,
                    station_id=station.id,
                    territory_id=territory.id,
                    load_rank=rank,
                    target_total_carton=int(total_carton),
                    target_total_pack=0,
                    depot_id=self._depot_id
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

    def _get_territories_for_batch(self, cycle_id: UUID, batch: int) -> List[str]:
        """Belirli batch'te yer alan territory code listesi"""
        from sqlmodel import select
        from app.models import Order, Territory
        territory_ids = set()
        orders = self.session.exec(select(Order).where(Order.cycle_id==cycle_id, Order.import_batch==batch)).all()
        for o in orders:
            territory_ids.add(o.territory_id)
        codes = []
        for tid in territory_ids:
            t = self.session.get(Territory, tid)
            if t:
                codes.append(t.code)
        return codes

    def _calculate_territory_loads_for_batch(self, cycle_id: UUID, batch: int, only_codes: Optional[List[str]] = None) -> Dict[str, float]:
        """Belirli batch için territory yüklerini (karton) hesapla."""
        from sqlmodel import select
        from app.models import Order, OrderLine, Territory
        orders = self.session.exec(select(Order).where(Order.cycle_id==cycle_id, Order.import_batch==batch)).all()
        by_tid = {}
        for o in orders:
            if only_codes:
                t = self.session.get(Territory, o.territory_id)
                if not t or t.code not in only_codes:
                    continue
            by_tid.setdefault(o.territory_id, []).append(o.id)
        loads: Dict[str, float] = {}
        for tid, order_ids in by_tid.items():
            lines = self.session.exec(select(OrderLine).where(OrderLine.order_id.in_(order_ids))).all()
            total_carton = 0.0
            for l in lines:
                total_carton += l.qty_carton + (l.qty_pack/10)
            t = self.session.get(Territory, tid)
            if t:
                loads[t.code] = total_carton
        return loads

    def _calculate_current_station_loads(self, cycle_id: UUID, station_count: int) -> List[float]:
        """Mevcut istasyonların TÜM batch'ler için toplam yüklerini döndür."""
        from sqlmodel import select
        from app.models import Station, StationAssignment, Territory, Order, OrderLine
        
        totals = [0.0 for _ in range(station_count)]
        
        for idx in range(1, station_count + 1):
            station_name = f"İstasyon-{idx}"
            station = self.session.exec(select(Station).where(Station.name==station_name)).first()
            if not station:
                continue
            
            # Bu istasyonun tüm territory'leri
            sas = self.session.exec(
                select(StationAssignment).where(
                    StationAssignment.cycle_id==cycle_id, 
                    StationAssignment.station_id==station.id
                )
            ).all()
            territory_ids = [sa.territory_id for sa in sas]
            
            if not territory_ids:
                continue
            
            # Tüm batch'lerdeki siparişleri topla
            for tid in territory_ids:
                orders = self.session.exec(
                    select(Order).where(
                        Order.cycle_id==cycle_id, 
                        Order.territory_id==tid
                    )
                ).all()
                
                for order in orders:
                    lines = self.session.exec(
                        select(OrderLine).where(OrderLine.order_id==order.id)
                    ).all()
                    
                    for line in lines:
                        totals[idx-1] += line.qty_carton + (line.qty_pack / 10)
        
        return totals
    
    def _greedy_distribution_with_initial(
        self,
        initial_station_loads: List[float],
        territory_loads: Dict[str, float],
        station_count: int
    ) -> List[List[str]]:
        """
        Mevcut istasyon yüklerine göre yeni territory'leri dağıt.
        
        Args:
            initial_station_loads: Her istasyonun mevcut yükü [station_1_load, station_2_load, ...]
            territory_loads: Yeni territory'lerin yükleri {territory_code: carton}
            station_count: İstasyon sayısı
            
        Returns:
            [[territory_code, ...], ...] (istasyon başına YENİ territory listesi)
        """
        # Territory'leri azalan sırada sırala
        sorted_territories = sorted(
            territory_loads.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # İstasyon kovaları - mevcut yüklerle başla
        stations = [
            {"territories": [], "total": initial_station_loads[i] if i < len(initial_station_loads) else 0.0}
            for i in range(station_count)
        ]
        
        # Her territory'yi en az yüklü istasyona ata
        for territory_code, carton in sorted_territories:
            # En az yüklü istasyonu bul
            min_station = min(stations, key=lambda s: s["total"])
            
            # Territory'yi ata
            min_station["territories"].append(territory_code)
            min_station["total"] += carton
        
        # Sadece yeni territory listelerini döndür
        return [station["territories"] for station in stations]
