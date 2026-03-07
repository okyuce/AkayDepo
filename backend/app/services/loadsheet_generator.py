"""
Loadsheet Generator Service
Fiş oluşturma ve paket numarası üretimi
"""
from typing import List, Dict, Optional
from uuid import UUID
from sqlmodel import Session, select
from app.models import (
    StationAssignment, Loadsheet, LoadsheetLine,
    Order, OrderLine, Dealer, Territory, Product, Station
)

# AnaStok için minimum karton limiti
MAIN_STOCK_THRESHOLD = 300

class LoadsheetGenerator:
    """Fiş üretici"""

    def __init__(self, session: Session):
        self.session = session
        self._main_stock_station = None
        self._main_stock_assignments = {}  # territory_id -> assignment cache
        self._depot_id = None

    def _get_main_stock_station(self) -> Optional[Station]:
        """AnaStok istasyonunu al (cache)"""
        if self._main_stock_station is None:
            stmt = select(Station).where(Station.is_main_stock == True)
            if self._depot_id:
                stmt = stmt.where(Station.depot_id == self._depot_id)
            self._main_stock_station = self.session.exec(stmt).first()
        return self._main_stock_station

    def _get_dealer_total_cartons(self, cycle_id: UUID, dealer_id: UUID) -> float:
        """Bayinin döngüdeki toplam sipariş miktarını hesapla (karton)"""
        stmt = select(Order).where(
            Order.cycle_id == cycle_id,
            Order.dealer_id == dealer_id
        )
        orders = self.session.exec(stmt).all()

        total_cartons = 0.0
        for order in orders:
            lines = self.session.exec(
                select(OrderLine).where(OrderLine.order_id == order.id)
            ).all()
            for line in lines:
                total_cartons += line.qty_carton + (line.qty_pack / 10)

        return total_cartons

    def _get_or_create_main_stock_assignment(
        self, cycle_id: UUID, territory_id: UUID, plan_date
    ) -> Optional[StationAssignment]:
        """AnaStok için territory assignment al veya oluştur"""
        main_stock = self._get_main_stock_station()
        if not main_stock:
            return None

        # Cache kontrol
        cache_key = (cycle_id, territory_id)
        if cache_key in self._main_stock_assignments:
            return self._main_stock_assignments[cache_key]

        # Mevcut assignment var mı?
        assignment = self.session.exec(
            select(StationAssignment).where(
                StationAssignment.cycle_id == cycle_id,
                StationAssignment.station_id == main_stock.id,
                StationAssignment.territory_id == territory_id
            )
        ).first()

        if not assignment:
            # Yeni assignment oluştur
            assignment = StationAssignment(
                cycle_id=cycle_id,
                plan_date=plan_date,
                station_id=main_stock.id,
                territory_id=territory_id,
                load_rank=1,
                target_total_carton=0,
                target_total_pack=0,
                depot_id=self._depot_id
            )
            self.session.add(assignment)
            self.session.flush()

        self._main_stock_assignments[cache_key] = assignment
        return assignment

    def generate_loadsheets_for_cycle(self, cycle_id: UUID, only_batch: Optional[int] = None, depot_id: str = None) -> int:
        """
        Bir döngü için tüm fişleri oluştur (multi-batch desteği ile)

        Args:
            cycle_id: Döngü ID

        Returns:
            int: Oluşturulan fiş sayısı
        """
        self._depot_id = depot_id
        from app.models import Cycle

        # Döngü bilgisini al (plan_date için)
        cycle = self.session.get(Cycle, cycle_id)
        if not cycle:
            raise Exception("Döngü bulunamadı.")

        # Döngünün station assignments'ını al (AnaStok hariç - normal istasyonlar)
        main_stock = self._get_main_stock_station()
        stmt = select(StationAssignment).where(StationAssignment.cycle_id == cycle_id)
        if main_stock:
            stmt = stmt.where(StationAssignment.station_id != main_stock.id)
        assignments = self.session.exec(stmt).all()

        if not assignments:
            raise Exception("İstasyon planı bulunamadı. Önce plan oluşturun.")

        loadsheet_count = 0

        # Dealer toplam kartonlarını cache'le (performans için)
        dealer_cartons_cache = {}

        # Her assignment için fişler oluştur
        for assignment in assignments:
            # Bu territory için tüm dealer'ları ve batch'leri al
            dealer_batches = self._get_dealer_batches_for_territory(cycle_id, assignment.territory_id, only_batch=only_batch)

            # Territory bilgisi
            territory = self.session.get(Territory, assignment.territory_id)

            # Her dealer+batch kombinasyonu için fiş oluştur
            dealer_index = {}
            main_stock_dealer_index = {}  # AnaStok için ayrı index

            for dealer_id, batch_number, order in dealer_batches:
                # Bayi toplam kartonunu hesapla (cache ile)
                if dealer_id not in dealer_cartons_cache:
                    dealer_cartons_cache[dealer_id] = self._get_dealer_total_cartons(cycle_id, dealer_id)
                dealer_total = dealer_cartons_cache[dealer_id]

                # 300+ karton mu? AnaStok'a yönlendir
                if dealer_total >= MAIN_STOCK_THRESHOLD and main_stock:
                    # AnaStok assignment'ı al veya oluştur
                    main_stock_assignment = self._get_or_create_main_stock_assignment(
                        cycle_id, assignment.territory_id, cycle.plan_date
                    )
                    if main_stock_assignment:
                        # AnaStok için dealer index
                        if dealer_id not in main_stock_dealer_index:
                            main_stock_dealer_index[dealer_id] = len(main_stock_dealer_index) + 1
                        idx = main_stock_dealer_index[dealer_id]

                        # Paket numarası (AnaStok için)
                        package_number = f"{territory.display_number}-B{idx:02d}"

                        # Loadsheet oluştur (AnaStok assignment ile)
                        loadsheet_count += self._create_loadsheet_for_order(
                            cycle_id=cycle_id,
                            assignment=main_stock_assignment,
                            dealer_id=dealer_id,
                            order=order,
                            package_number=package_number,
                            batch_number=batch_number
                        )
                        continue  # Normal istasyona ekleme

                # Normal istasyon için
                if dealer_id not in dealer_index:
                    dealer_index[dealer_id] = len(dealer_index) + 1
                idx = dealer_index[dealer_id]

                # Paket numarası: T07-B01 (dealer index'e göre)
                package_number = f"{territory.display_number}-B{idx:02d}"

                # Loadsheet oluştur
                loadsheet_count += self._create_loadsheet_for_order(
                    cycle_id=cycle_id,
                    assignment=assignment,
                    dealer_id=dealer_id,
                    order=order,
                    package_number=package_number,
                    batch_number=batch_number
                )

        self.session.commit()
        return loadsheet_count
    
    def _get_dealer_batches_for_territory(self, cycle_id: UUID, territory_id: UUID, only_batch: Optional[int] = None) -> List[tuple]:
        """
        Bir territory için tüm dealer+batch kombinasyonlarını al
        
        Returns:
            List[(dealer_id, batch_number, order)]: (dealer, batch, order) tuple'ları
        """
        # Bu territory için tüm order'ları al (batch ve dealer'a göre sıralı)
        stmt = select(Order).join(Dealer).where(
            Order.cycle_id == cycle_id,
            Order.territory_id == territory_id
        )
        if only_batch is not None:
            stmt = stmt.where(Order.import_batch == only_batch)
        stmt = stmt.order_by(Dealer.route_order, Order.import_batch)
        
        orders = self.session.exec(stmt).all()
        
        # (dealer_id, batch_number, order) tuple listesi
        result = []
        for order in orders:
            result.append((order.dealer_id, order.import_batch, order))
        
        return result
    
    def _create_loadsheet_for_order(
        self,
        cycle_id: UUID,
        assignment: StationAssignment,
        dealer_id: UUID,
        order: Order,
        package_number: str,
        batch_number: int
    ) -> int:
        """
        Bir order için loadsheet oluştur (revizyon tespiti ile)
        
        Returns:
            int: Oluşturulan fiş sayısı (1)
        """
        # Revizyon mu kontrol et
        is_revision = order.is_revision
        loadsheet_type = "normal"
        revision_diff = None
        
        if is_revision and order.previous_order_id:
            # Önceki order ile karşılaştır ve diff hesapla
            revision_diff, loadsheet_type = self._calculate_revision_diff(order.id, order.previous_order_id)
            
            # ÖNEMLİ: Önceki fişi iptal et ve eğer tamamlanmışsa stoka iade et
            self._cancel_previous_loadsheet(cycle_id, dealer_id, order.previous_order_id, assignment.station_id)
        
        # Idempotency: Aynı dealer + batch için zaten fiş varsa atla
        from app.models import Loadsheet as Ls
        exists = self.session.exec(
            select(Ls).where(Ls.cycle_id==cycle_id, Ls.dealer_id==dealer_id, Ls.batch_number==batch_number)
        ).first()
        if exists:
            return 0

        # Loadsheet oluştur
        loadsheet = Loadsheet(
            cycle_id=cycle_id,
            assignment_id=assignment.id,
            dealer_id=dealer_id,
            sheet_no=f"{cycle_id}-{package_number}-B{batch_number}",
            package_number=package_number,
            batch_number=batch_number,
            status="pending",
            loadsheet_type=loadsheet_type,
            revision_diff=revision_diff,
            depot_id=self._depot_id,
            is_revision=is_revision
        )
        self.session.add(loadsheet)
        self.session.flush()  # ID için
        
        # Order lines'ı loadsheet lines'a kopyala
        # YENİ MANTIK: Her fişte order'ın tam içeriğini göster (fark hesaplama yok)
        # Revizyon bilgisi sadece referans için revision_diff'te saklanır
        stmt = select(OrderLine).where(OrderLine.order_id == order.id)
        order_lines = self.session.exec(stmt).all()
        
        for line in order_lines:
            loadsheet_line = LoadsheetLine(
                loadsheet_id=loadsheet.id,
                product_id=line.product_id,
                qty_carton=line.qty_carton,
                qty_pack=line.qty_pack
            )
            self.session.add(loadsheet_line)
        
        return 1
    
    def _calculate_revision_diff(self, current_order_id: UUID, previous_order_id: UUID) -> tuple:
        """
        İki order arasındaki farkları hesapla (karton + paket dönüşümüyle)
        
        Returns:
            (revision_diff_json, loadsheet_type): (JSON farklar, "revision_increase" veya "revision_decrease")
        """
        import json
        
        # Şu anki order lines
        stmt = select(OrderLine).where(OrderLine.order_id == current_order_id)
        current_lines = self.session.exec(stmt).all()
        
        # Önceki order lines
        stmt = select(OrderLine).where(OrderLine.order_id == previous_order_id)
        previous_lines = self.session.exec(stmt).all()
        
        # Ürün bazlı map oluştur
        current_map = {line.product_id: line for line in current_lines}
        previous_map = {line.product_id: line for line in previous_lines}
        
        # Farkları hesapla (temel birim: paket)
        diffs = []
        total_diff_packs = 0
        
        # Tüm ürünleri kontrol et (hem yeni hem eski)
        all_product_ids = set(current_map.keys()) | set(previous_map.keys())
        
        for product_id in all_product_ids:
            cur = current_map.get(product_id)
            prev = previous_map.get(product_id)
            
            cur_packs = (cur.qty_carton * 10 + cur.qty_pack) if cur else 0
            prev_packs = (prev.qty_carton * 10 + prev.qty_pack) if prev else 0
            diff_packs = cur_packs - prev_packs
            
            if diff_packs != 0:
                # Karton + paket olarak ayrıştır
                sign = 1 if diff_packs > 0 else -1
                abs_packs = abs(diff_packs)
                diff_carton = (abs_packs // 10) * sign
                diff_pack = (abs_packs % 10) * sign
                product = self.session.get(Product, product_id)
                diffs.append({
                    "product_id": str(product_id),
                    "product_code": product.code if product else "",
                    "product_name": product.name if product else "",
                    "previous_carton": prev.qty_carton if prev else 0,
                    "previous_pack": prev.qty_pack if prev else 0,
                    "current_carton": cur.qty_carton if cur else 0,
                    "current_pack": cur.qty_pack if cur else 0,
                    "diff_carton": diff_carton,
                    "diff_pack": diff_pack
                })
                total_diff_packs += diff_packs
        
        # Loadsheet tipi belirle (paket toplamına göre)
        if total_diff_packs > 0:
            loadsheet_type = "revision_increase"
        elif total_diff_packs < 0:
            loadsheet_type = "revision_decrease"
        else:
            loadsheet_type = "normal"  # Fark yok
        
        revision_diff_json = json.dumps(diffs) if diffs else None
        
        return revision_diff_json, loadsheet_type
    
    def _cancel_previous_loadsheet(self, cycle_id: UUID, dealer_id: UUID, previous_order_id: UUID, station_id: UUID):
        """
        Önceki fişi iptal et ve eğer tamamlanmışsa stoka iade et
        
        Args:
            cycle_id: Döngü ID
            dealer_id: Bayi ID
            previous_order_id: Önceki order ID
            station_id: İstasyon ID
        """
        from app.models import Loadsheet, StationInventory, StockMovement
        from datetime import datetime
        
        # Önceki order'a ait fişi bul
        # Önceki order'dan oluşan loadsheet'i bulmak için dealer_id ve cycle_id kullan
        # Not: Aynı dealer için birden fazla batch olabilir, önceki batch'i bul
        stmt = select(Loadsheet).join(
            Order, Loadsheet.dealer_id == Order.dealer_id
        ).where(
            Loadsheet.cycle_id == cycle_id,
            Loadsheet.dealer_id == dealer_id,
            Order.id == previous_order_id
        )
        
        # Alternatif: Daha basit yöntem - aynı dealer için önceki batch'teki fiş
        # Önceki batch numarasını order'dan al
        prev_order = self.session.get(Order, previous_order_id)
        if not prev_order:
            return
        
        prev_batch = prev_order.import_batch
        
        # Önceki fişi bul
        stmt = select(Loadsheet).where(
            Loadsheet.cycle_id == cycle_id,
            Loadsheet.dealer_id == dealer_id,
            Loadsheet.batch_number == prev_batch
        )
        previous_loadsheet = self.session.exec(stmt).first()
        
        if not previous_loadsheet:
            print(f"UYARI: Önceki fiş bulunamadı - dealer: {dealer_id}, batch: {prev_batch}")
            return
        
        # Eğer fiş zaten iptal ise, tekrar işleme gerek yok
        if previous_loadsheet.status == "cancelled":
            return
        
        # Eğer fiş tamamlanmışsa (completed_at != null), stoka iade et
        if previous_loadsheet.completed_at is not None:
            print(f"INFO: İptal edilen fiş tamamlanmıştı, stoka iade ediliyor - {previous_loadsheet.id}")
            
            # Loadsheet lines'ları al
            stmt = select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == previous_loadsheet.id)
            lines = self.session.exec(stmt).all()
            
            # Her ürün için stoka iade et (pack-equivalent ile atomik)
            for line in lines:
                # Stok kaydını bul
                stmt = select(StationInventory).where(
                    StationInventory.station_id == station_id,
                    StationInventory.product_id == line.product_id
                )
                inventory = self.session.exec(stmt).first()
                
                # Upsert: Kayıt yoksa 0'dan oluştur
                if not inventory:
                    inventory = StationInventory(
                        station_id=station_id,
                        product_id=line.product_id,
                        quantity_carton=0,
                        quantity_pack=0
                    )
                    print(f"INFO: StationInventory kaydı yoktu, iade için oluşturuldu (station={station_id}, product={line.product_id})")
                    self.session.add(inventory)
                    self.session.flush()
                
                # Önceki stok durumunu kaydet (hareket logu için)
                before_carton = inventory.quantity_carton
                before_pack = inventory.quantity_pack

                # Mevcut toplam ve iade miktarını paket eşdeğerine çevir
                total_packs_equiv = inventory.quantity_carton * 10 + inventory.quantity_pack
                refund_packs_equiv = line.qty_carton * 10 + line.qty_pack
                new_total = total_packs_equiv + refund_packs_equiv

                # Normalize ederek geri yaz
                inventory.quantity_carton = new_total // 10
                inventory.quantity_pack = new_total % 10
                inventory.updated_at = datetime.now()
                self.session.add(inventory)

                # Stok hareket logu kaydet (refund)
                movement = StockMovement(
                    station_id=station_id,
                    product_id=line.product_id,
                    loadsheet_id=previous_loadsheet.id,
                    movement_type="refund",
                    quantity_carton=line.qty_carton,
                    quantity_pack=line.qty_pack,
                    before_carton=before_carton,
                    before_pack=before_pack,
                    after_carton=inventory.quantity_carton,
                    after_pack=inventory.quantity_pack,
                    note="Revizyon nedeniyle iade"
                )
                self.session.add(movement)

                print(f"  - Ürün {line.product_id}: +{line.qty_carton} karton, +{line.qty_pack} paket (toplam={new_total} pack)")
        else:
            print(f"INFO: İptal edilen fiş tamamlanmamış, stoka dokunulmadı - {previous_loadsheet.id}")
        
        # Fişi iptal et ve zaman damgalarını temizle (hazırlanan hesaplarından düşmesi için)
        previous_loadsheet.status = "cancelled"
        previous_loadsheet.completed_at = None
        previous_loadsheet.loaded_at = None
        self.session.add(previous_loadsheet)
        print(f"INFO: Fiş iptal edildi - {previous_loadsheet.id}")
