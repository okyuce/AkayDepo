"""
Cycle Manager Service
Döngü oluşturma, tamamlanma kontrolü, revizyon tespiti
"""
from datetime import date, datetime
from typing import Optional, Dict, List
from uuid import UUID, uuid4
from sqlmodel import Session, select
from app.models import (
    Cycle, Territory, Dealer, Product, Order, OrderLine, RevisionDiff
)
from app.services.excel_parser import ExcelParser, extract_territory_info
import pandas as pd

class CycleManager:
    """Döngü yönetimi"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_cycle(
        self, 
        run_time: str, 
        plan_date: date,
        excel_content: bytes
    ) -> Cycle:
        """
        Yeni döngü oluştur ve Excel verisini import et
        
        Args:
            run_time: "14:00", "16:00", "17:00"
            plan_date: Planlama tarihi
            excel_content: Excel dosyası bytes
            
        Returns:
            Cycle: Oluşturulan döngü
        """
        # Önceki döngü tamamlanmış mı kontrol et
        can_start, warnings = self.can_start_new_cycle(plan_date)
        if not can_start:
            raise Exception(f"Yeni döngü başlatılamaz: {', '.join(warnings)}")
        
        # Cycle no hesapla
        cycle_no = self._get_next_cycle_no(plan_date)
        
        # Cycle oluştur
        cycle = Cycle(
            cycle_no=cycle_no,
            run_time=run_time,
            plan_date=plan_date,
            status="active"
        )
        self.session.add(cycle)
        self.session.commit()
        self.session.refresh(cycle)
        
        # Excel'i parse et ve import et
        parser = ExcelParser(excel_content, sheet_name='Recipe2')
        df = parser.validate_and_parse()
        
        # Verileri import et
        self._import_territories(df)
        self._import_dealers(df)
        self._import_products(df)
        self._import_orders(df, cycle.id)
        
        # Revizyon tespiti (eğer önceki döngü varsa)
        if cycle_no > 1:
            self._detect_revisions(cycle.id, plan_date)
        
        return cycle
    
    def can_start_new_cycle(self, plan_date: date) -> tuple[bool, List[str]]:
        """
        Yeni döngü başlatılabilir mi kontrol et
        
        Returns:
            (can_start, warnings): (True/False, uyarı listesi)
        """
        # Aynı gün için aktif döngü var mı?
        stmt = select(Cycle).where(
            Cycle.plan_date == plan_date,
            Cycle.status == "active"
        )
        active_cycles = self.session.exec(stmt).all()
        
        if not active_cycles:
            return True, []
        
        # Son aktif döngünün durumunu kontrol et
        last_cycle = active_cycles[-1]
        
        # Pending fişleri say
        from app.models import Loadsheet
        stmt = select(Loadsheet).where(
            Loadsheet.cycle_id == last_cycle.id,
            Loadsheet.status == "pending"
        )
        pending_count = len(self.session.exec(stmt).all())
        
        if pending_count > 0:
            return False, [f"Döngü-{last_cycle.cycle_no} tamamlanmadı. {pending_count} fiş henüz yüklenmedi."]
        
        return True, []
    
    def complete_cycle(self, cycle_id: UUID) -> Cycle:
        """Döngüyü tamamla"""
        cycle = self.session.get(Cycle, cycle_id)
        if not cycle:
            raise Exception("Döngü bulunamadı")
        
        cycle.status = "completed"
        cycle.completed_at = datetime.utcnow()
        self.session.add(cycle)
        self.session.commit()
        self.session.refresh(cycle)
        
        return cycle
    
    def cancel_pending_loadsheets(self, cycle_id: UUID) -> int:
        """
        Döngüdeki tüm pending fişleri iptal et
        
        Returns:
            int: İptal edilen fiş sayısı
        """
        from app.models import Loadsheet
        stmt = select(Loadsheet).where(
            Loadsheet.cycle_id == cycle_id,
            Loadsheet.status == "pending"
        )
        pending_sheets = self.session.exec(stmt).all()
        
        for sheet in pending_sheets:
            sheet.status = "cancelled"
            self.session.add(sheet)
        
        self.session.commit()
        return len(pending_sheets)
    
    def _get_next_cycle_no(self, plan_date: date) -> int:
        """Aynı gün için bir sonraki cycle no'yu hesapla"""
        stmt = select(Cycle).where(Cycle.plan_date == plan_date)
        cycles = self.session.exec(stmt).all()
        
        if not cycles:
            return 1
        
        return max(c.cycle_no for c in cycles) + 1
    
    def _import_territories(self, df: pd.DataFrame):
        """Territory'leri import et (upsert)"""
        unique_territories = df['Territory'].unique()
        
        for territory_code in unique_territories:
            # Zaten var mı kontrol et
            stmt = select(Territory).where(Territory.code == territory_code)
            existing = self.session.exec(stmt).first()
            
            if not existing:
                # Yeni territory oluştur
                display_number, name = extract_territory_info(territory_code)
                territory = Territory(
                    code=territory_code,
                    name=name,
                    display_number=display_number
                )
                self.session.add(territory)
        
        self.session.commit()
    
    def _import_dealers(self, df: pd.DataFrame):
        """Bayileri import et (upsert)"""
        # Unique dealers
        dealers_df = df[['BayiKodu', 'BayiAdı', 'Pozisyon', 'BayiRutSırası', 'Territory']].drop_duplicates('BayiKodu')
        
        for _, row in dealers_df.iterrows():
            # Territory id bul
            stmt = select(Territory).where(Territory.code == row['Territory'])
            territory = self.session.exec(stmt).first()
            if not territory:
                continue
            
            # Dealer var mı kontrol et
            stmt = select(Dealer).where(Dealer.code == row['BayiKodu'])
            existing = self.session.exec(stmt).first()
            
            if not existing:
                dealer = Dealer(
                    code=row['BayiKodu'],
                    name=row['BayiAdı'],
                    position_code=row['Pozisyon'],
                    route_order=int(row['BayiRutSırası']),
                    territory_id=territory.id
                )
                self.session.add(dealer)
        
        self.session.commit()
    
    def _import_products(self, df: pd.DataFrame):
        """Ürünleri import et (upsert)"""
        unique_products = df[['ÜrünKodu', 'ÜrünAdı']].drop_duplicates('ÜrünKodu')
        
        for _, row in unique_products.iterrows():
            stmt = select(Product).where(Product.code == row['ÜrünKodu'])
            existing = self.session.exec(stmt).first()
            
            if not existing:
                product = Product(
                    code=row['ÜrünKodu'],
                    name=row['ÜrünAdı'],
                    pack_per_carton=10  # Sabit kural
                )
                self.session.add(product)
        
        self.session.commit()
    
    def _import_orders(self, df: pd.DataFrame, cycle_id: UUID):
        """Siparişleri ve satırları import et"""
        # Siparişleri grupla
        for order_code, order_group in df.groupby('SiparişKodu'):
            first_row = order_group.iloc[0]
            
            # Territory ve Dealer id'lerini bul
            stmt = select(Territory).where(Territory.code == first_row['Territory'])
            territory = self.session.exec(stmt).first()
            
            stmt = select(Dealer).where(Dealer.code == first_row['BayiKodu'])
            dealer = self.session.exec(stmt).first()
            
            if not territory or not dealer:
                continue
            
            # Order oluştur
            order = Order(
                cycle_id=cycle_id,
                external_order_code=order_code,
                payment_type=first_row['ÖdemeTipi'],
                order_date=first_row['SiparişTarihi'].date(),
                delivery_date=first_row['TeslimatTarihi'].date(),
                territory_id=territory.id,
                dealer_id=dealer.id,
                revision_group_id=uuid4(),  # İlk versiyon için yeni ID
                revision_no=1,
                source_sheet='Recipe2'
            )
            self.session.add(order)
            self.session.flush()  # Order ID'si için
            
            # Order lines oluştur
            for _, line_row in order_group.iterrows():
                stmt = select(Product).where(Product.code == line_row['ÜrünKodu'])
                product = self.session.exec(stmt).first()
                
                if not product:
                    continue
                
                order_line = OrderLine(
                    order_id=order.id,
                    product_id=product.id,
                    qty_carton=int(line_row['Karton']),
                    qty_pack=int(line_row['Paket'])
                )
                self.session.add(order_line)
        
        self.session.commit()
    
    def _detect_revisions(self, current_cycle_id: UUID, plan_date: date):
        """
        Revizyon tespiti - önceki döngü ile karşılaştır
        Bu FAZ 2'de placeholder, FAZ 3'te implement edilecek
        """
        # TODO: Implement revision detection
        pass
