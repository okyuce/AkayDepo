"""
Excel Parser Service
Excel dosyalarını okur ve veritabanı modelerine dönüştürür
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
from io import BytesIO

class ExcelParseError(Exception):
    """Excel parse hatası"""
    pass

class ExcelParser:
    """Excel dosyasını parse eder"""
    
    # Zorunlu kolonlar (EXCEL_MAPPING.md)
    REQUIRED_COLUMNS = [
        'Pozisyon', 'Territory', 'SiparişKodu', 'BayiKodu', 'BayiAdı',
        'ÜrünKodu', 'ÜrünAdı', 'Paket', 'Karton', 'ÖdemeTipi',
        'SiparişTarihi', 'TeslimatTarihi', 'BayiRutSırası'
    ]
    
    def __init__(self, file_content: bytes, sheet_name: str = None):
        """
        Args:
            file_content: Excel dosyası bytes
            sheet_name: Okunacak sheet adı (None ise ilk sheet okunur)
        """
        self.file_content = file_content
        self.sheet_name = sheet_name
        self.df = None
        
    def validate_and_parse(self) -> pd.DataFrame:
        """
        Excel'i validate et ve parse et
        
        Returns:
            pandas DataFrame
            
        Raises:
            ExcelParseError: Validasyon hatası
        """
        try:
            # Excel oku
            excel_file = pd.ExcelFile(BytesIO(self.file_content))
            
            # Sheet adı belirtilmediyse ilk sheet'i kullan
            if self.sheet_name is None:
                self.sheet_name = excel_file.sheet_names[0]
            
            # Sheet var mı kontrol et
            if self.sheet_name not in excel_file.sheet_names:
                # Sheet bulunamazsa ilk sheet'i dene
                self.sheet_name = excel_file.sheet_names[0]
            
            # Sheet'i oku
            self.df = pd.read_excel(excel_file, sheet_name=self.sheet_name)
            
            # Boş satırları at
            self.df = self.df.dropna(how='all')
            
            # Excel'deki orijinal sırayı koru (satır numarası)
            self.df['_excel_row_index'] = range(len(self.df))
            
            # Zorunlu kolonları kontrol et
            missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in self.df.columns]
            if missing_columns:
                raise ExcelParseError(
                    f"Eksik kolonlar: {', '.join(missing_columns)}"
                )
            
            # Normalize et
            self._normalize_data()
            
            return self.df
            
        except Exception as e:
            if isinstance(e, ExcelParseError):
                raise
            raise ExcelParseError(f"Excel parse hatası: {str(e)}")
    
    def _normalize_data(self):
        """Veriyi normalize et (tip dönüşümleri, temizlik)"""
        # Boş değerleri doldur
        self.df['Paket'] = self.df['Paket'].fillna(0).astype(int)
        self.df['Karton'] = self.df['Karton'].fillna(0).astype(int)
        
        # Tarihleri parse et
        self.df['SiparişTarihi'] = pd.to_datetime(self.df['SiparişTarihi'])
        self.df['TeslimatTarihi'] = pd.to_datetime(self.df['TeslimatTarihi'])
        
        # String kolonları temizle (trim)
        string_columns = ['Territory', 'SiparişKodu', 'BayiKodu', 'BayiAdı', 
                          'ÜrünKodu', 'ÜrünAdı', 'ÖdemeTipi', 'Pozisyon']
        for col in string_columns:
            self.df[col] = self.df[col].astype(str).str.strip()
    
    def get_statistics(self) -> Dict:
        """
        Parse edilen verinin istatistiklerini döndür
        
        Returns:
            Dict: İstatistikler
        """
        if self.df is None:
            return {}
        
        return {
            'total_rows': len(self.df),
            'total_orders': self.df['SiparişKodu'].nunique(),
            'total_dealers': self.df['BayiKodu'].nunique(),
            'total_territories': self.df['Territory'].nunique(),
            'total_products': self.df['ÜrünKodu'].nunique(),
            'territories': self.df['Territory'].unique().tolist()
        }
    
    def get_orders_grouped(self) -> Dict[str, List[Dict]]:
        """
        Siparişleri grupla (SiparişKodu -> satırlar)
        
        Returns:
            Dict: {sipariş_kodu: [satırlar]}
        """
        if self.df is None:
            return {}
        
        orders = {}
        for order_code, group in self.df.groupby('SiparişKodu'):
            orders[order_code] = group.to_dict('records')
        
        return orders
    
    def calculate_territory_totals(self) -> Dict[str, float]:
        """
        Territory bazında toplam karton hesapla (paket dahil)
        
        Returns:
            Dict: {territory_code: total_carton}
        """
        if self.df is None:
            return {}
        
        # Paket → Karton dönüşümü (1 karton = 10 paket)
        self.df['TotalCarton'] = self.df['Karton'] + (self.df['Paket'] / 10)
        
        # Territory bazında topla
        territory_totals = self.df.groupby('Territory')['TotalCarton'].sum().to_dict()
        
        return territory_totals


def extract_territory_info(territory_code: str) -> Tuple[str, str]:
    """
    Territory code'dan display_number ve name çıkar
    
    Args:
        territory_code: "TERR030707-Sille"
        
    Returns:
        (display_number, name): ("T07", "Sille")
    """
    # TERR030707-Sille → 07, Sille
    parts = territory_code.split('-')
    if len(parts) != 2:
        return "T00", territory_code
    
    code_part = parts[0]  # TERR030707
    name_part = parts[1]  # Sille
    
    # Son 2 digit al: 030707 → 07
    if len(code_part) >= 2:
        last_two = code_part[-2:]
        display_number = f"T{last_two}"
    else:
        display_number = "T00"
    
    return display_number, name_part
