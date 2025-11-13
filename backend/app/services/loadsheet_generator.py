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
        Bir döngü için tüm fişleri oluştur
        
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
            # Territory'nin bayilerini al
            dealers = self._get_dealers_for_territory(cycle_id, assignment.territory_id)
            
            # Territory bilgisi
            territory = self.session.get(Territory, assignment.territory_id)
            
            # Her bayi için fiş oluştur
            for idx, dealer in enumerate(dealers, 1):
                # Paket numarası üret: T07-B01
                package_number = f"{territory.display_number}-B{idx:02d}"
                
                # Order'ı bul
                stmt = select(Order).where(
                    Order.cycle_id == cycle_id,
                    Order.dealer_id == dealer.id
                )
                order = self.session.exec(stmt).first()
                
                if not order:
                    continue
                
                # Loadsheet oluştur
                loadsheet = Loadsheet(
                    cycle_id=cycle_id,
                    assignment_id=assignment.id,
                    dealer_id=dealer.id,
                    sheet_no=f"{cycle_id}-{package_number}",
                    package_number=package_number,
                    status="pending",
                    is_revision=False
                )
                self.session.add(loadsheet)
                self.session.flush()  # ID için
                
                # Order lines'ları loadsheet lines'a kopyala
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
                
                loadsheet_count += 1
        
        self.session.commit()
        return loadsheet_count
    
    def _get_dealers_for_territory(self, cycle_id: UUID, territory_id: UUID) -> List[Dealer]:
        """
        Bir territory'nin bayilerini al (route_order'a göre sıralı)
        
        Returns:
            List[Dealer]: Sıralı bayi listesi
        """
        # Bu territory için order'ları al
        stmt = select(Order).where(
            Order.cycle_id == cycle_id,
            Order.territory_id == territory_id
        )
        orders = self.session.exec(stmt).all()
        
        # Unique dealer ID'leri
        dealer_ids = list(set(order.dealer_id for order in orders))
        
        # Dealer'ları al ve route_order'a göre sırala
        dealers = []
        for dealer_id in dealer_ids:
            dealer = self.session.get(Dealer, dealer_id)
            if dealer:
                dealers.append(dealer)
        
        # Route order'a göre sırala
        dealers.sort(key=lambda d: d.route_order)
        
        return dealers
    
    def generate_revision_loadsheet(
        self,
        parent_loadsheet_id: UUID,
        changes: Dict[UUID, int]  # {product_id: qty_change_carton}
    ) -> Loadsheet:
        """
        Revizyon fişi oluştur
        
        Args:
            parent_loadsheet_id: Orjinal fiş ID
            changes: Ürün değişiklikleri
            
        Returns:
            Loadsheet: Revizyon fişi
        """
        # Parent loadsheet al
        parent = self.session.get(Loadsheet, parent_loadsheet_id)
        if not parent:
            raise Exception("Orjinal fiş bulunamadı")
        
        # Revizyon fişi oluştur
        revision_package_number = f"{parent.package_number}-R"
        
        revision = Loadsheet(
            cycle_id=parent.cycle_id,
            assignment_id=parent.assignment_id,
            dealer_id=parent.dealer_id,
            sheet_no=f"{parent.sheet_no}-R",
            package_number=revision_package_number,
            status="pending",
            is_revision=True,
            parent_loadsheet_id=parent.id
        )
        self.session.add(revision)
        self.session.flush()
        
        # Değişiklikleri loadsheet lines'a ekle
        for product_id, qty_change in changes.items():
            if qty_change == 0:
                continue
            
            line = LoadsheetLine(
                loadsheet_id=revision.id,
                product_id=product_id,
                qty_carton=qty_change,  # Pozitif veya negatif
                qty_pack=0
            )
            self.session.add(line)
        
        self.session.commit()
        self.session.refresh(revision)
        
        return revision
