"""
Loadsheet Generator Service
Fiş oluşturma ve paket numarası üretimi
"""
from typing import List, Dict, Optional
from uuid import UUID
from sqlmodel import Session, select
from app.models import (
    StationAssignment, Loadsheet, LoadsheetLine, 
    Order, OrderLine, Dealer, Territory, Product
)

class LoadsheetGenerator:
    """Fiş üretici"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def generate_loadsheets_for_cycle(self, cycle_id: UUID, only_batch: Optional[int] = None) -> int:
        """
        Bir döngü için tüm fişleri oluştur (multi-batch desteği ile)
        
        Args:
            cycle_id: Döngü ID
            
        Returns:
            int: Oluşturulan fiş sayısı
        """
        # Döngünün station assignments'ını al
        stmt = select(StationAssignment).where(StationAssignment.cycle_id == cycle_id)
        assignments = self.session.exec(stmt).all()
        
        if not assignments:
            raise Exception("İstasyon planı bulunamadı. Önce plan oluşturun.")
        
        loadsheet_count = 0
        
        # Her assignment için fişler oluştur
        for assignment in assignments:
            # Bu territory için tüm dealer'ları ve batch'leri al
            dealer_batches = self._get_dealer_batches_for_territory(cycle_id, assignment.territory_id, only_batch=only_batch)
            
            # Territory bilgisi
            territory = self.session.get(Territory, assignment.territory_id)
            
            # Her dealer+batch kombinasyonu için fiş oluştur
            dealer_index = {}
            for dealer_id, batch_number, order in dealer_batches:
                # Dealer index - ilk görüşte set et
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
        from app.models import Loadsheet, StationInventory
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
            
            # Her ürün için stoka iade et
            for line in lines:
                # Stok kaydını bul
                stmt = select(StationInventory).where(
                    StationInventory.station_id == station_id,
                    StationInventory.product_id == line.product_id
                )
                inventory = self.session.exec(stmt).first()
                
                if inventory:
                    # Stoka iade et (düşenler geri eklenir)
                    inventory.quantity_carton += line.qty_carton
                    inventory.quantity_pack += line.qty_pack
                    inventory.updated_at = datetime.utcnow()
                    self.session.add(inventory)
                    
                    print(f"  - Ürün {line.product_id}: +{line.qty_carton} karton, +{line.qty_pack} paket")
        else:
            print(f"INFO: İptal edilen fiş tamamlanmamış, stoka dokunulmadı - {previous_loadsheet.id}")
        
        # Fişi iptal et
        previous_loadsheet.status = "cancelled"
        self.session.add(previous_loadsheet)
        print(f"INFO: Fiş iptal edildi - {previous_loadsheet.id}")
