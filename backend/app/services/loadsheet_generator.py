"""
Loadsheet Generator Service
Fiş oluşturma ve paket numarası üretimi
"""
from typing import List, Dict
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
    
    def generate_loadsheets_for_cycle(self, cycle_id: UUID) -> int:
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
            dealer_batches = self._get_dealer_batches_for_territory(cycle_id, assignment.territory_id)
            
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
    
    def _get_dealer_batches_for_territory(self, cycle_id: UUID, territory_id: UUID) -> List[tuple]:
        """
        Bir territory için tüm dealer+batch kombinasyonlarını al
        
        Returns:
            List[(dealer_id, batch_number, order)]: (dealer, batch, order) tuple'ları
        """
        # Bu territory için tüm order'ları al (batch ve dealer'a göre sıralı)
        stmt = select(Order).join(Dealer).where(
            Order.cycle_id == cycle_id,
            Order.territory_id == territory_id
        ).order_by(Dealer.route_order, Order.import_batch)
        
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
            revision_diff=revision_diff
        )
        self.session.add(loadsheet)
        self.session.flush()  # ID için
        
        # Order lines'ı loadsheet lines'a kopyala
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
        İki order arasındaki farkları hesapla
        
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
        
        # Farkları hesapla
        diffs = []
        total_diff_carton = 0
        
        # Tüm ürünleri kontrol et (hem yeni hem eski)
        all_product_ids = set(current_map.keys()) | set(previous_map.keys())
        
        for product_id in all_product_ids:
            current_qty = current_map.get(product_id)
            previous_qty = previous_map.get(product_id)
            
            current_carton = current_qty.qty_carton if current_qty else 0
            previous_carton = previous_qty.qty_carton if previous_qty else 0
            
            diff_carton = current_carton - previous_carton
            
            if diff_carton != 0:
                product = self.session.get(Product, product_id)
                diffs.append({
                    "product_id": str(product_id),
                    "product_code": product.code if product else "",
                    "product_name": product.name if product else "",
                    "previous_qty": previous_carton,
                    "current_qty": current_carton,
                    "diff": diff_carton
                })
                total_diff_carton += diff_carton
        
        # Loadsheet tipi belirle
        if total_diff_carton > 0:
            loadsheet_type = "revision_increase"
        elif total_diff_carton < 0:
            loadsheet_type = "revision_decrease"
        else:
            loadsheet_type = "normal"  # Fark yok
        
        revision_diff_json = json.dumps(diffs) if diffs else None
        
        return revision_diff_json, loadsheet_type
