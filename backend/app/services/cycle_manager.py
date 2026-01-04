"""
Cycle Manager Service
Döngü oluşturma, tamamlanma kontrolü, revizyon tespiti
"""
from datetime import date, datetime
from typing import Optional, Dict, List
from uuid import UUID, uuid4
from sqlmodel import Session, select
from app.models import (
    Cycle, Territory, Dealer, Product, Order, OrderLine, RevisionDiff,
    Station, StationInventory
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
    ) -> tuple[Cycle, int]:
        """
        Yeni döngü oluştur veya mevcut döngüye append et
        
        Args:
            run_time: "14:00", "16:00", "17:00"
            plan_date: Planlama tarihi
            excel_content: Excel dosyası bytes
            
        Returns:
            Cycle: Oluşturulan veya mevcut döngü
        """
        # Aynı gün için aktif döngü var mı kontrol et
        stmt = select(Cycle).where(
            Cycle.plan_date == plan_date,
            Cycle.status == "active"
        )
        existing_cycle = self.session.exec(stmt).first()
        
        if existing_cycle:
            # APPEND MODE: Mevcut döngüye ekle
            cycle = existing_cycle
            batch_number = self._get_next_batch_number(cycle.id)
        else:
            # YENİ DÖNGÜ: Farklı gün için yeni cycle oluştur
            cycle_no = self._get_next_cycle_no(plan_date)

            cycle = Cycle(
                cycle_no=cycle_no,
                run_time=run_time,
                plan_date=plan_date,
                status="active"
            )
            self.session.add(cycle)
            self.session.commit()
            self.session.refresh(cycle)
            batch_number = 1

            # Yeni döngüde AnaStok envanterini sıfırla
            self._reset_main_stock_inventory()
        
        # Excel'i parse et ve import et
        parser = ExcelParser(excel_content, sheet_name='Recipe2')
        df = parser.validate_and_parse()
        
        # Verileri import et (batch numarası ile)
        self._import_territories(df)
        self._import_dealers(df)
        self._import_products(df)
        self._import_orders(df, cycle.id, batch_number)
        
        # Revizyon tespiti (eğer batch > 1 ise)
        if batch_number > 1:
            self._detect_revisions(cycle.id, batch_number)
        
        return cycle, batch_number
    
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
    
    def _get_next_batch_number(self, cycle_id: UUID) -> int:
        """Döngüdeki bir sonraki batch numarasını hesapla"""
        stmt = select(Order).where(Order.cycle_id == cycle_id)
        orders = self.session.exec(stmt).all()

        if not orders:
            return 1

        max_batch = max(o.import_batch for o in orders)
        return max_batch + 1

    def _reset_main_stock_inventory(self):
        """
        AnaStok istasyonunun envanterini sıfırla.
        Yeni döngü başladığında çağrılır.
        """
        # AnaStok istasyonunu bul
        main_stock = self.session.exec(
            select(Station).where(Station.is_main_stock == True)
        ).first()

        if not main_stock:
            return

        # AnaStok'un tüm envanter kayıtlarını sil veya sıfırla
        inventory_items = self.session.exec(
            select(StationInventory).where(StationInventory.station_id == main_stock.id)
        ).all()

        for item in inventory_items:
            item.quantity_carton = 0
            item.quantity_pack = 0
            self.session.add(item)

        self.session.commit()
        print(f"INFO: AnaStok envanteri sıfırlandı ({len(inventory_items)} kayıt)")

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
        """Ürünleri import et (upsert) - SABİT sıralama kullan"""
        # Sabit ürün sıralaması
        PRODUCT_ORDER = {
            'MLR100': 1, 'MFTB': 2, 'MLFTB': 3, 'MLTBLUE': 4, 'MLTGRAY': 5,
            'MLTONE': 6, 'MLEDGE': 7, 'MLEDBLUE': 8, 'MLEDSLIMS': 9, 'PL100': 10,
            'PLLONGRCB': 11, 'PLRC': 12, 'PLLRC': 13, 'PLABS100': 14, 'PLRSVRCB': 15,
            'PLMNRCB': 16, 'LAB100RCB': 17, 'LARKBRCB': 18, 'CHNB100RCB': 19,
            'CHNAVYBRCB': 20, 'CHMODENAVY': 21, 'MUARCB': 22, 'MUABLU': 23,
            'LM100RCB': 24, 'LMRCB': 25, 'MLROLL50': 26
        }
        
        unique_products = df[['ÜrünKodu', 'ÜrünAdı']].drop_duplicates('ÜrünKodu')
        
        for _, row_data in unique_products.iterrows():
            product_code = row_data['ÜrünKodu']
            stmt = select(Product).where(Product.code == product_code)
            existing = self.session.exec(stmt).first()
            
            # Sabit sıralamadan order al, yoksa 999
            display_order = PRODUCT_ORDER.get(product_code, 999)
            
            if not existing:
                product = Product(
                    code=product_code,
                    name=row_data['ÜrünAdı'],
                    pack_per_carton=10,  # Sabit kural
                    display_order=display_order
                )
                self.session.add(product)
            else:
                # Mevcut ürün varsa isim güncelle, display_order sabit kalsın
                existing.name = row_data['ÜrünAdı']
                existing.display_order = display_order  # Sabit sıra
                self.session.add(existing)
        
        self.session.commit()
    
    def _import_orders(self, df: pd.DataFrame, cycle_id: UUID, batch_number: int = 1):
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
            
            # Aynı bayi + territory + delivery_date ile önceki batch'te sipariş var mı?
            # (Order code batch'e göre değişebilir, ama bayi/tarih kombinasyonu unique)
            is_revision = False
            previous_order = None
            if batch_number > 1:
                stmt = select(Order).where(
                    Order.cycle_id == cycle_id,
                    Order.dealer_id == dealer.id,
                    Order.territory_id == territory.id,
                    Order.delivery_date == first_row['TeslimatTarihi'].date(),
                    Order.import_batch < batch_number
                ).order_by(Order.import_batch.desc())
                previous_order = self.session.exec(stmt).first()
                is_revision = previous_order is not None
            
            # Order oluştur
            order = Order(
                cycle_id=cycle_id,
                external_order_code=order_code,
                payment_type=first_row['ÖdemeTipi'],
                order_date=first_row['SiparişTarihi'],  # datetime olarak sakla
                delivery_date=first_row['TeslimatTarihi'].date(),
                territory_id=territory.id,
                dealer_id=dealer.id,
                import_batch=batch_number,
                is_revision=is_revision,
                previous_order_id=previous_order.id if previous_order else None,
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
    
    def _detect_revisions(self, cycle_id: UUID, batch_number: int):
        """
        Revizyon tespiti - önceki batch ile karşılaştır ve loadsheet tipi belirle
        
        Args:
            cycle_id: Döngü ID
            batch_number: Şu anki batch numarası
        """
        # Bu batch'teki tüm revizyon orderları al
        stmt = select(Order).where(
            Order.cycle_id == cycle_id,
            Order.import_batch == batch_number,
            Order.is_revision == True
        )
        revision_orders = self.session.exec(stmt).all()
        
        for order in revision_orders:
            if not order.previous_order_id:
                continue
            
            # Önceki order'ı al
            previous_order = self.session.get(Order, order.previous_order_id)
            if not previous_order:
                continue
            
            # Ürün bazlı fark hesapla (placeholder - loadsheet oluşturulurken kullanılacak)
            # TODO: Detaylı diff hesaplama loadsheet generator'da yapılacak
            pass
