/**
 * Loadsheet List Page
 * İstasyon bazında fiş listesi ve detay görünümü
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { apiService } from '../services/api';
import Navbar from '../components/Navbar';
import { useAuthStore } from '../stores/authStore';

interface Station {
  id: string;
  name: string;
}

interface LoadsheetLine {
  product_code: string;
  product_name: string;
  qty_carton: number;
  qty_pack: number;
  qty_change_carton?: number | null;
  qty_change_pack?: number | null;
}

interface Loadsheet {
  id: string;
  package_number: string;
  dealer_name: string;
  dealer_code: string;
  route_order: number;
  total_carton: number;
  total_pack: number;
  status: string;
  loadsheet_type: string;
  batch_number: number;
  completed_at: string | null;
  lines?: LoadsheetLine[];
  territory?: {
    code: string;
    display_number: string;
    name: string;
  };
  included_as_parent?: boolean;
  order_date?: string | null;
}

interface DealerGroup {
  dealer_code: string;
  dealer_name: string;
  route_order: number;
  loadsheets: Loadsheet[];
  cardColor: 'gray' | 'green' | 'orange' | 'red';
}

interface Product {
  id: string;
  code: string;
  name: string;
}

export default function LoadsheetListPage() {
  const { user } = useAuthStore();
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('');
  const [selectedTerritoryCode, setSelectedTerritoryCode] = useState<string>('');  // Territory filtresi
  const [availableTerritories, setAvailableTerritories] = useState<{code: string; display_number: string; name: string}[]>([]);
  const [imports, setImports] = useState<Array<{ id: string; batch_number: number; filename: string; uploaded_at: string }>>([]);
  const [selectedBatch, setSelectedBatch] = useState<string>(''); // ''=Tümü, '1','2',...
  const [loadsheets, setLoadsheets] = useState<Loadsheet[]>([]);
  const [dealerGroups, setDealerGroups] = useState<DealerGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [expandedDealerCode, setExpandedDealerCode] = useState<string | null>(null);

  // SKU filtresi state'leri
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedSkus, setSelectedSkus] = useState<string[]>([]);
  const [skuDropdownOpen, setSkuDropdownOpen] = useState(false);
  const skuDropdownRef = useRef<HTMLDivElement>(null);
  const [skuQtyType, setSkuQtyType] = useState<'carton' | 'pack' | ''>('');
  const [skuQtyValue, setSkuQtyValue] = useState<string>('');
  const [sortByTerritory, setSortByTerritory] = useState(false);
  const [showScrollTop, setShowScrollTop] = useState(false);

  // Açılan kartın ref'i - scrollIntoView için
  const expandedCardRef = useRef<HTMLDivElement>(null);
  const cardHeaderRef = useRef<HTMLDivElement>(null);
  const [contentMaxHeight, setContentMaxHeight] = useState<string>('70vh');

  const calculateContentHeight = useCallback(() => {
    if (cardHeaderRef.current) {
      const headerRect = cardHeaderRef.current.getBoundingClientRect();
      const headerBottom = headerRect.bottom;
      const available = window.innerHeight - headerBottom - 16; // 16px alt boşluk
      setContentMaxHeight(`${Math.max(available, 200)}px`);
    }
  }, []);

  useEffect(() => {
    if (expandedDealerCode && expandedCardRef.current) {
      // Kartı üste scroll et
      setTimeout(() => {
        expandedCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Scroll bittikten sonra yüksekliği hesapla
        setTimeout(() => calculateContentHeight(), 400);
      }, 50);
    }
  }, [expandedDealerCode, calculateContentHeight]);

  // Pencere boyutu değişince yeniden hesapla
  useEffect(() => {
    if (expandedDealerCode) {
      window.addEventListener('resize', calculateContentHeight);
      return () => window.removeEventListener('resize', calculateContentHeight);
    }
  }, [expandedDealerCode, calculateContentHeight]);

  // Scroll pozisyonunu takip et - yukarı git butonu için
  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 300);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Satır "yapıldı" işaretleme (localStorage'da kalıcı)
  const [completedLines, setCompletedLines] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('completed_lines');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch { return new Set(); }
  });

  const toggleLineCompleted = (loadsheetId: string, productCode: string) => {
    const key = `${loadsheetId}_${productCode}`;
    setCompletedLines(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      localStorage.setItem('completed_lines', JSON.stringify([...next]));
      return next;
    });
  };

  const isLineCompleted = (loadsheetId: string, productCode: string) => {
    return completedLines.has(`${loadsheetId}_${productCode}`);
  };

  useEffect(() => {
    loadActiveCycle();
    loadProducts();
  }, []);

  // SKU dropdown dışına tıklandığında kapat
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (skuDropdownRef.current && !skuDropdownRef.current.contains(event.target as Node)) {
        setSkuDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadProducts = async () => {
    try {
      const productList = await apiService.getProductOrder();
      setProducts(productList.map((p: { id: string; code: string; name: string }) => ({
        id: p.id,
        code: p.code,
        name: p.name
      })));
    } catch (err) {
      console.error('Ürünler yüklenemedi:', err);
    }
  };

  const loadActiveCycle = async () => {
    try {
      const activeData = await apiService.getActivecycle();
        if (activeData.has_active_cycle && activeData.cycle) {
        setCycleId(activeData.cycle.id);
        // Batch listesi (Excel importları)
        const imp = await apiService.getCycleImports(activeData.cycle.id);
        setImports(imp);
        if (activeData.cycle.has_plan) {
          await loadStations(activeData.cycle.id);
        }
      }
    } catch (err) {
      console.error('Aktif cycle yüklenemedi:', err);
    }
  };

  const loadStations = async (cycleId: string) => {
    try {
      const plan = await apiService.getPlan(cycleId);
      if (plan && plan.stations) {
        let stationList = plan.stations.map((s: any) => ({
          id: s.station_id,
          name: s.station_name
        }));
        
        // Tablet kullanıcıları için sadece kendi istasyonlarını göster
        if (user?.role === 'tablet' && user?.station_id) {
          stationList = stationList.filter((s: Station) => s.id === user.station_id);
          
          // Otomatik olarak kendi istasyonunu seç
          if (stationList.length > 0) {
            setSelectedStationId(stationList[0].id);
            loadLoadsheets(stationList[0].id);
          }
        }
        
        setStations(stationList);
      }
    } catch (err) {
      console.error('İstasyonlar yüklenemedi:', err);
    }
  };

  const loadLoadsheets = async (
    stationId: string,
    batchOverride?: string,
    territoryOverride?: string,
    skuOverride?: string[],
    qtyTypeOverride?: '' | 'carton' | 'pack',
    qtyValueOverride?: string
  ) => {
    if (!cycleId) return;

    setIsLoading(true);
    try {
      const batchNum = batchOverride !== undefined ? (batchOverride ? parseInt(batchOverride, 10) : undefined)
        : (selectedBatch ? parseInt(selectedBatch, 10) : undefined);
      const skuList = skuOverride !== undefined ? skuOverride : selectedSkus;
      const qType = qtyTypeOverride !== undefined ? qtyTypeOverride : skuQtyType;
      const qVal = qtyValueOverride !== undefined ? qtyValueOverride : skuQtyValue;
      const data = await apiService.getStationLoadsheets(
        stationId,
        cycleId,
        batchNum,
        skuList.length > 0 ? skuList : undefined,
        skuList.length > 0 ? 'and' : undefined,
        (skuList.length > 0 && qType) ? qType as 'carton' | 'pack' : undefined,
        (skuList.length > 0 && qType && qVal) ? parseInt(qVal, 10) : undefined
      );
      // territories içindeki tüm loadsheet'leri düzleştir ve territory bilgisini ekle
      const allLoadsheets: Loadsheet[] = [];
      if (data.territories) {
        data.territories.forEach((territory: any) => {
          if (territory.loadsheets) {
            // Her loadsheet'e territory bilgisini ekle
            const loadsheets = territory.loadsheets.map((ls: any) => ({
              ...ls,
              territory: {
                code: territory.territory_code,
                display_number: territory.display_number,
                name: territory.name
              },
              included_as_parent: ls.included_as_parent || false
            }));
            allLoadsheets.push(...loadsheets);
          }
        });
      }
      setLoadsheets(allLoadsheets);
      
      // Unique territory'leri çıkar
      const territoriesSet = new Map<string, {code: string; display_number: string; name: string}>();
      allLoadsheets.forEach(ls => {
        if (ls.territory && !territoriesSet.has(ls.territory.code)) {
          territoriesSet.set(ls.territory.code, ls.territory);
        }
      });
      const territories = Array.from(territoriesSet.values());
      // Display number'a göre sırala
      territories.sort((a, b) => a.display_number.localeCompare(b.display_number));
      setAvailableTerritories(territories);
      
      // Territory filtresini uygula (override varsa onu kullan)
      const territoryCode = territoryOverride !== undefined ? territoryOverride : selectedTerritoryCode;
      const filteredLoadsheets = territoryCode 
        ? allLoadsheets.filter(ls => ls.territory?.code === territoryCode)
        : allLoadsheets;
      
      // Dealer bazında grupla
      const grouped = groupLoadsheetsByDealer(filteredLoadsheets);
      setDealerGroups(grouped);
    } catch (err) {
      console.error('Fişler yüklenemedi:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const groupLoadsheetsByDealer = (loadsheets: Loadsheet[]): DealerGroup[] => {
    const groupMap = new Map<string, Loadsheet[]>();
    
    // Dealer code'a göre grupla
    loadsheets.forEach(ls => {
      if (!groupMap.has(ls.dealer_code)) {
        groupMap.set(ls.dealer_code, []);
      }
      groupMap.get(ls.dealer_code)!.push(ls);
    });
    
    // Her grup için renk hesapla
    const groups: DealerGroup[] = [];
    groupMap.forEach((lsList, dealerCode) => {
      // Sıralama: tamamlanmayanlar üstte, tamamlananlar altta; eşitlikte batch numarası küçük önce
      lsList.sort((a, b) => {
        const aDone = (a.completed_at !== null && a.completed_at !== undefined) || a.status === 'loaded' || a.status === 'cancelled';
        const bDone = (b.completed_at !== null && b.completed_at !== undefined) || b.status === 'loaded' || b.status === 'cancelled';
        if (aDone !== bDone) return Number(aDone) - Number(bDone);
        return a.batch_number - b.batch_number;
      });
      
      const completedCount = lsList.filter(ls => ls.completed_at !== null || ls.status === 'loaded').length;
      const totalCount = lsList.length;

      let cardColor: 'gray' | 'green' | 'orange' | 'red' = 'gray';

      // Kart rengi duruma göre
      // Son batch (aktif fiş) iptal edildiyse kırmızı
      const lastBatch = lsList.reduce((prev, curr) => (prev.batch_number > curr.batch_number ? prev : curr));
      if (lastBatch.status === 'cancelled') {
        cardColor = 'red';    // Aktif fiş iptal edildi
      } else if (completedCount === totalCount) {
        cardColor = 'green';  // Hepsi tamamlandı
      } else if (completedCount > 0 && completedCount < totalCount) {
        cardColor = 'orange'; // Bazıları tamamlandı, bazıları bekliyor
      } else {
        cardColor = 'gray';   // Hiçbiri tamamlanmadı
      }
      
      groups.push({
        dealer_code: dealerCode,
        dealer_name: lsList[0].dealer_name,
        route_order: lsList[0].route_order,
        loadsheets: lsList,
        cardColor
      });
    });
    
    // Grupları sırala: tamamlanmamış gruplar (gray/orange) üstte, tamamlanmış (green) altta
    groups.sort((a, b) => {
      const aDone = a.cardColor === 'green' || a.cardColor === 'red';
      const bDone = b.cardColor === 'green' || b.cardColor === 'red';
      if (aDone !== bDone) return Number(aDone) - Number(bDone);
      if (sortByTerritory) {
        const aTerrName = a.loadsheets[0]?.territory?.name || '';
        const bTerrName = b.loadsheets[0]?.territory?.name || '';
        const terrCmp = aTerrName.localeCompare(bTerrName, 'tr');
        if (terrCmp !== 0) return terrCmp;
      }
      return a.route_order - b.route_order;
    });
    
    return groups;
  };

  const handleStationChange = (stationId: string) => {
    setSelectedStationId(stationId);
    // Filtreleri sıfırla
    setSelectedTerritoryCode('');
    setSelectedBatch('');
    setSelectedSkus([]);
    setSkuQtyType('');
    setSkuQtyValue('');
    // Eski verileri temizle (UI yanılmasın)
    setDealerGroups([]);
    setAvailableTerritories([]);
    setLoadsheets([]);
    // Yeni istasyon için batch'i "Tümü" (override) olarak zorla yükle
    if (stationId) {
      loadLoadsheets(stationId, '', '', [], '', '');
    }
  };

  const handleToggleTerritorySort = () => {
    setSortByTerritory(prev => {
      const next = !prev;
      // Mevcut grupları yeniden sırala
      setDealerGroups(groups => {
        const sorted = [...groups].sort((a, b) => {
          const aDone = a.cardColor === 'green' || a.cardColor === 'red';
          const bDone = b.cardColor === 'green' || b.cardColor === 'red';
          if (aDone !== bDone) return Number(aDone) - Number(bDone);
          if (next) {
            const aTerrName = a.loadsheets[0]?.territory?.name || '';
            const bTerrName = b.loadsheets[0]?.territory?.name || '';
            const terrCmp = aTerrName.localeCompare(bTerrName, 'tr');
            if (terrCmp !== 0) return terrCmp;
          }
          return a.route_order - b.route_order;
        });
        return sorted;
      });
      return next;
    });
  };

  const handleTerritoryChange = (territoryCode: string) => {
    setSelectedTerritoryCode(territoryCode);
    // Mevcut loadsheet'leri filtrele
    const filteredLoadsheets = territoryCode 
      ? loadsheets.filter(ls => ls.territory?.code === territoryCode)
      : loadsheets;
    const grouped = groupLoadsheetsByDealer(filteredLoadsheets);
    setDealerGroups(grouped);
  };

  const handleDealerCardClick = async (dealerCode: string) => {
    if (expandedDealerCode === dealerCode) {
      setExpandedDealerCode(null);
      return;
    }
    
    // Bu dealer'a ait tüm fişlerin detaylarını yükle
    const group = dealerGroups.find(g => g.dealer_code === dealerCode);
    if (!group) return;
    
    try {
      // Her fiş için detay yükle (paralel)
      const detailPromises = group.loadsheets.map(ls => 
        apiService.getLoadsheetDetail(ls.id)
      );
      const details = await Promise.all(detailPromises);
      
      // Loadsheet'leri güncelle
      const updatedLoadsheets = loadsheets.map(ls => {
        const detail = details.find(d => d.id === ls.id);
        if (detail) {
          return { ...ls, lines: detail.lines, territory: detail.territory };
        }
        return ls;
      });
      setLoadsheets(updatedLoadsheets);
      
      // Territory filtresini uygula ve dealer groups'u yenile
      const filteredLoadsheets = selectedTerritoryCode 
        ? updatedLoadsheets.filter(ls => ls.territory?.code === selectedTerritoryCode)
        : updatedLoadsheets;
      const updatedGroups = groupLoadsheetsByDealer(filteredLoadsheets);
      setDealerGroups(updatedGroups);
      
      // Dealer grubu aç
      setExpandedDealerCode(dealerCode);
    } catch (err) {
      console.error('Fiş detayları yüklenemedi:', err);
    }
  };

  const handleCompleteLoadsheet = async (loadsheetId: string) => {
    try {
      await apiService.completeLoadsheet(loadsheetId);
      // Listeyi yenile
      if (selectedStationId) {
        await loadLoadsheets(selectedStationId);
      }
    } catch (err) {
      console.error('Fiş tamamlanamadı:', err);
      alert('Hata: Fiş tamamlanamadı');
    }
  };

  const handleCancelLoadsheet = async (loadsheetId: string) => {
    if (!confirm('Bu fişi iptal etmek istediğinize emin misiniz?')) return;
    try {
      await apiService.cancelLoadsheet(loadsheetId);
      if (selectedStationId) await loadLoadsheets(selectedStationId);
    } catch (err) {
      console.error('Fiş iptal edilemedi:', err);
      alert('Hata: Fiş iptal edilemedi');
    }
  };

  const handleUncancelLoadsheet = async (loadsheetId: string) => {
    try {
      await apiService.uncancelLoadsheet(loadsheetId);
      if (selectedStationId) await loadLoadsheets(selectedStationId);
    } catch (err) {
      console.error('İptal geri alınamadı:', err);
      alert('Hata: İptal geri alınamadı');
    }
  };

  const isAdmin = user?.role === 'admin' || user?.role === 'superadmin';

  const getCardColorClass = (cardColor: 'gray' | 'green' | 'orange' | 'red') => {
    switch (cardColor) {
      case 'green':
        return 'bg-green-100 dark:bg-green-900/30 border-green-400 dark:border-green-700';
      case 'orange':
        return 'bg-orange-100 dark:bg-orange-900/30 border-orange-400 dark:border-orange-700';
      case 'red':
        return 'bg-red-100 dark:bg-red-900/30 border-red-400 dark:border-red-700';
      default:
        return 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <Navbar />
      <div className="p-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-6 text-gray-900 dark:text-gray-100">Yükleme Fişleri</h1>

          {!cycleId ? (
            <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700 rounded-lg p-4">
              <p className="text-yellow-800 dark:text-yellow-300">
                Aktif döngü bulunamadı. Lütfen önce Excel yükleyip plan oluşturun.
              </p>
            </div>
          ) : stations.length === 0 ? (
            <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700 rounded-lg p-4">
              <p className="text-yellow-800 dark:text-yellow-300">
                Plan bulunamadı. Lütfen planlama oluşturun.
              </p>
            </div>
          ) : (
            <>
              {/* İstasyon ve Territory Seçimi */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
                <div className="flex justify-between items-center">
                  <div className="flex-1 flex gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        İstasyon Seçin
                      </label>
                      <select
                        value={selectedStationId}
                        onChange={(e) => handleStationChange(e.target.value)}
                        className="w-full md:w-64 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      >
                        <option value="">İstasyon Seçiniz...</option>
                        {stations.map((station) => (
                          <option key={station.id} value={station.id}>
                            {station.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {selectedStationId && (
                      <div className="flex gap-4 flex-wrap">
                        {availableTerritories.length > 0 && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                              Territory Filtrele (Opsiyonel)
                            </label>
                            <select
                          value={selectedTerritoryCode}
                          onChange={(e) => handleTerritoryChange(e.target.value)}
                          className="w-full md:w-48 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        >
                          <option value="">Tüm Territory'ler</option>
                          {availableTerritories.map((territory) => (
                            <option key={territory.code} value={territory.code}>
                              {territory.display_number} - {territory.name}
                            </option>
                          ))}
                        </select>
                      </div>
                        )}
                        {/* Excel (Batch) Filtresi */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Excel (Batch)</label>
                          <select
                            value={selectedBatch}
                            onChange={(e) => { const v = e.target.value; setSelectedBatch(v); if (selectedStationId) loadLoadsheets(selectedStationId, v); }}
                            className="w-full md:w-48 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          >
                            <option value="">Tümü</option>
                            {imports.map(imp => (
                              <option key={imp.id} value={imp.batch_number}>
                                {imp.batch_number}. Excel - {imp.filename}
                              </option>
                            ))}
                          </select>
                        </div>
                        {/* SKU Filtresi */}
                        <div className="relative" ref={skuDropdownRef}>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">SKU Filtresi</label>
                          <button
                            type="button"
                            onClick={() => setSkuDropdownOpen(!skuDropdownOpen)}
                            className="w-48 border border-gray-300 dark:border-gray-600 rounded-md px-4 py-2 text-left bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 flex justify-between items-center"
                          >
                            <span className={selectedSkus.length === 0 ? 'text-gray-400' : 'text-gray-900 dark:text-gray-100'}>
                              {selectedSkus.length === 0 ? 'Seçiniz...' : `${selectedSkus.length} ürün`}
                            </span>
                            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                          {skuDropdownOpen && (
                            <div className="absolute z-50 mt-1 w-72 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-auto">
                              <div className="p-2 border-b border-gray-200 dark:border-gray-600 flex justify-between items-center">
                                <span className="text-xs text-gray-500 dark:text-gray-400">{selectedSkus.length} seçili</span>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSelectedSkus([]);
                                    setSkuQtyType('');
                                    setSkuQtyValue('');
                                    if (selectedStationId) loadLoadsheets(selectedStationId, undefined, undefined, [], '', '');
                                  }}
                                  className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                                >
                                  Temizle
                                </button>
                              </div>
                              {products.map((p) => (
                                <label
                                  key={p.id}
                                  className="flex items-center px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer"
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedSkus.includes(p.code)}
                                    onChange={(e) => {
                                      const newSkus = e.target.checked
                                        ? [...selectedSkus, p.code]
                                        : selectedSkus.filter(s => s !== p.code);
                                      setSelectedSkus(newSkus);
                                      if (selectedStationId) loadLoadsheets(selectedStationId, undefined, undefined, newSkus);
                                    }}
                                    className="mr-2 rounded border-gray-300 dark:border-gray-500 text-blue-600 focus:ring-blue-500"
                                  />
                                  <span className="text-sm">
                                    <span className="font-medium text-gray-900 dark:text-gray-100">{p.code}</span>
                                    <span className="text-gray-500 dark:text-gray-400 ml-1">- {p.name}</span>
                                  </span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                        {/* SKU Miktar Filtresi */}
                        {selectedSkus.length > 0 && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Miktar Filtresi</label>
                            <div className="flex gap-2 items-center">
                              <button
                                type="button"
                                onClick={() => {
                                  const newType = skuQtyType === 'carton' ? '' : 'carton';
                                  setSkuQtyType(newType as any);
                                  if (selectedStationId) loadLoadsheets(selectedStationId, undefined, undefined, undefined, newType as any, skuQtyValue);
                                }}
                                className={`px-3 py-2 rounded-md text-sm font-medium border ${
                                  skuQtyType === 'carton'
                                    ? 'bg-blue-600 text-white border-blue-600'
                                    : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                                }`}
                              >
                                Krt
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  const newType = skuQtyType === 'pack' ? '' : 'pack';
                                  setSkuQtyType(newType as any);
                                  if (selectedStationId) loadLoadsheets(selectedStationId, undefined, undefined, undefined, newType as any, skuQtyValue);
                                }}
                                className={`px-3 py-2 rounded-md text-sm font-medium border ${
                                  skuQtyType === 'pack'
                                    ? 'bg-blue-600 text-white border-blue-600'
                                    : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                                }`}
                              >
                                Pkt
                              </button>
                              {skuQtyType && (
                                <input
                                  type="number"
                                  min="0"
                                  placeholder="Adet"
                                  value={skuQtyValue}
                                  onChange={(e) => {
                                    const v = e.target.value;
                                    setSkuQtyValue(v);
                                    if (selectedStationId) loadLoadsheets(selectedStationId, undefined, undefined, undefined, undefined, v);
                                  }}
                                  className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              )}
                            </div>
                          </div>
                        )}
                        {/* Territory Sıralama */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Sıralama</label>
                          <button
                            type="button"
                            onClick={handleToggleTerritorySort}
                            className={`px-3 py-2 rounded-md text-sm font-medium border whitespace-nowrap ${
                              sortByTerritory
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                            }`}
                          >
                            Territory A-Z
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => loadActiveCycle()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
                  >
                    Yenile
                  </button>
                </div>
              </div>

              {/* Fiş Listesi */}
              {!selectedStationId ? (
                <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-6">
                  <p className="text-center text-blue-800 dark:text-blue-300">
                    Lütfen yukarıdaki listeden bir istasyon seçin.
                  </p>
                </div>
              ) : isLoading ? (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                  <p className="text-center text-gray-500 dark:text-gray-400">Yüklüyor...</p>
                </div>
              ) : dealerGroups.length === 0 ? (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                  <p className="text-center text-gray-500 dark:text-gray-400">Fiş bulunamadı</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {dealerGroups.map((group) => {
                    const isExpanded = expandedDealerCode === group.dealer_code;

                    // Sıralama ve iptal hesaplamaları (IIFE yerine burada)
                    const lastByBatch = group.loadsheets.reduce((prev, curr) =>
                      (prev.batch_number > curr.batch_number ? prev : curr)
                    );
                    const orderByBatch = [...group.loadsheets]
                      .sort((a, b) => a.batch_number - b.batch_number)
                      .map(ls => ls.id);
const sortedLoadsheets = [...group.loadsheets]
                      .sort((a, b) => {
                        const aDone = (a.completed_at !== null && a.completed_at !== undefined) || a.status === 'loaded' || a.status === 'cancelled';
                        const bDone = (b.completed_at !== null && b.completed_at !== undefined) || b.status === 'loaded' || b.status === 'cancelled';
                        if (aDone !== bDone) return Number(aDone) - Number(bDone); // incomplete first
                        return a.batch_number - b.batch_number; // tie-breaker
                      });

                    return (
                      <div
                        key={group.dealer_code}
                        ref={isExpanded ? expandedCardRef : undefined}
                        className={`border-2 rounded-lg overflow-hidden ${getCardColorClass(group.cardColor)}`}
                      >
                        {/* Dealer Card Header */}
                        <div
                          ref={isExpanded ? cardHeaderRef : undefined}
                          className="p-4 cursor-pointer hover:bg-opacity-80 transition"
                          onClick={() => handleDealerCardClick(group.dealer_code)}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex items-center gap-4">
                              <span className="text-3xl font-bold text-gray-900 bg-white dark:bg-gray-200 px-3 py-1 rounded">
                                {group.route_order}
                              </span>
                              <div>
                                <h3 className="font-bold text-xl text-gray-900 dark:text-gray-100">
                                  {group.dealer_name}
                                </h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                  {group.dealer_code}
                                  {group.loadsheets[0]?.territory?.name && (
                                    <span> - {group.loadsheets[0].territory.name}</span>
                                  )}
                                  {group.loadsheets[0]?.order_date && (
                                    <span> - {new Date(group.loadsheets[0].order_date).toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' })} {new Date(group.loadsheets[0].order_date).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}</span>
                                  )}
                                </p>
                                <div className="flex items-center gap-3 mt-2">
                                  <span className={`text-xs px-2 py-1 rounded font-semibold ${
                                    group.loadsheets.length > 1
                                      ? 'bg-orange-500 text-white'
                                      : 'bg-white dark:bg-gray-200 text-gray-800'
                                  }`}>
                                    {group.loadsheets.length} Fiş
                                  </span>
                                  <span className="text-xs px-2 py-1 rounded font-semibold bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200">
                                    {lastByBatch.total_carton || 0} Krt
                                  </span>
                                  {(lastByBatch.total_pack || 0) > 0 && (
                                    <span className="text-xs px-2 py-1 rounded font-semibold bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-200">
                                      {lastByBatch.total_pack || 0} Pkt
                                    </span>
                                  )}
                                  {group.cardColor === 'green' && (
                                    <span className="text-xs text-green-700 dark:text-green-300 font-semibold">✓ Tamam</span>
                                  )}
                                  {group.cardColor === 'orange' && (
                                    <span className="text-xs text-orange-700 dark:text-orange-300 font-semibold">⚠ Ek Fiş</span>
                                  )}
                                  {group.cardColor === 'red' && (
                                    <span className="text-xs text-red-700 dark:text-red-300 font-semibold">❌ İptal</span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <div className="flex flex-col items-end gap-1">
                              {group.loadsheets[0]?.territory?.name && (
                                <span className="font-bold text-xl text-gray-900 dark:text-gray-100">
                                  {group.loadsheets[0].territory.name}
                                </span>
                              )}
                              <span className="text-2xl text-gray-600 dark:text-gray-400">
                                {isExpanded ? '▲' : '▼'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Expanded: Tüm fişler */}
                        {isExpanded && (
                          <div
                            className="bg-white dark:bg-gray-800 border-t-2 border-gray-300 dark:border-gray-600 p-4 space-y-6 overflow-y-auto"
                            style={{ maxHeight: contentMaxHeight }}
                          >
                            {sortedLoadsheets
                              .sort((a, b) => {
                                // Batch filtresi aktifse: parent (included_as_parent) önce, sonra batch ASC, sonra tamamlanmayan üstte
                                if (selectedBatch) {
                                  const ap = a.included_as_parent ? 0 : 1;
                                  const bp = b.included_as_parent ? 0 : 1;
                                  if (ap !== bp) return ap - bp;
                                  if (a.batch_number !== b.batch_number) return a.batch_number - b.batch_number;
                                  const aDone = (a.completed_at !== null && a.completed_at !== undefined) || a.status === 'loaded' || a.status === 'cancelled';
                                  const bDone = (b.completed_at !== null && b.completed_at !== undefined) || b.status === 'loaded' || b.status === 'cancelled';
                                  return Number(aDone) - Number(bDone);
                                }
                                return 0;
                              })
                              .map((loadsheet) => {
                                const totalCartons = loadsheet.lines?.reduce((sum, line) => sum + line.qty_carton, 0) || 0;
                                const totalPacks = loadsheet.lines?.reduce((sum, line) => sum + (line.qty_pack || 0), 0) || 0;
                                
                                // İptal: son batch dışındaki tümü iptal VEYA manuel iptal
                                const isCancelled = loadsheet.id !== lastByBatch.id || loadsheet.status === 'cancelled';
                                // Fiş numarası: batch sırasındaki konum (1'den başlar)
                                const loadsheetNumber = orderByBatch.indexOf(loadsheet.id) + 1;

                                return (
                                <div key={loadsheet.id} className={`border-2 rounded ${
                                  isCancelled ? 'border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/30' : 'border-gray-200 dark:border-gray-600'
                                }`}>
                                  {/* Fiş Başlık */}
                                  <div className={`p-3 flex justify-between items-center ${
                                    isCancelled ? 'bg-red-100 dark:bg-red-900/40' : 'bg-gray-50 dark:bg-gray-700'
                                  }`}>
                                    <div className="flex items-center gap-2">
                                      <span className={`font-bold text-lg px-2 py-0.5 rounded ${
                                        isCancelled
                                          ? 'bg-red-200 dark:bg-red-800 text-red-900 dark:text-red-100'
                                          : loadsheetNumber >= 2
                                            ? 'bg-orange-100 dark:bg-orange-900/50 text-orange-800 dark:text-orange-200'
                                            : 'text-gray-900 dark:text-gray-100'
                                      }`}>
                                        FIŞ-{loadsheetNumber}
                                      </span>
                                      <span className="text-sm text-gray-600 dark:text-gray-400 ml-1">{loadsheet.package_number}</span>
                                      {isCancelled && (
                                        <span className="bg-red-600 text-white text-xs font-bold px-3 py-1 rounded ml-2">
                                          ❌ İPTAL
                                        </span>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                      {isCancelled ? (
                                        <>
                                          <span className="text-red-700 font-semibold text-sm">❌ İptal Edildi</span>
                                          {isAdmin && loadsheet.status === 'cancelled' && (
                                            <button
                                              onClick={(e) => { e.stopPropagation(); handleUncancelLoadsheet(loadsheet.id); }}
                                              className="text-xs px-2 py-1 rounded border border-blue-400 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30"
                                            >
                                              Geri Al
                                            </button>
                                          )}
                                        </>
                                      ) : !loadsheet.completed_at ? (
                                        <>
                                          {isAdmin && (
                                            <button
                                              onClick={(e) => { e.stopPropagation(); handleCancelLoadsheet(loadsheet.id); }}
                                              className="text-xs px-2 py-1 rounded border border-red-400 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                                            >
                                              İptal
                                            </button>
                                          )}
                                          <button
                                            onClick={() => handleCompleteLoadsheet(loadsheet.id)}
                                            className="bg-green-600 text-white px-12 py-3 rounded-md hover:bg-green-700 text-base font-bold"
                                          >
                                            Tamamla
                                          </button>
                                        </>
                                      ) : (
                                        <>
                                          <span className="text-green-700 font-semibold text-sm">✓ Tamamlandı</span>
                                          {isAdmin && (
                                            <button
                                              onClick={(e) => { e.stopPropagation(); handleCancelLoadsheet(loadsheet.id); }}
                                              className="text-xs px-2 py-1 rounded border border-red-400 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                                            >
                                              İptal
                                            </button>
                                          )}
                                        </>
                                      )}
                                    </div>
                                  </div>

                                  {/* Fiş Detay Tablosu */}
                                  {loadsheet.lines && (
                                    <table className="w-full table-fixed">
                                      <thead className="bg-gray-100 dark:bg-gray-700">
                                        <tr>
                                          <th className="text-left p-3 font-bold border-b-2 border-gray-300 dark:border-gray-600 w-3/5 text-gray-900 dark:text-gray-100">Rut Sırası</th>
                                          <th className="text-center p-3 font-bold border-b-2 border-gray-300 dark:border-gray-600 w-1/5 text-gray-900 dark:text-gray-100">Krt</th>
                                          <th className="text-center p-3 font-bold border-b-2 border-gray-300 dark:border-gray-600 w-1/5 text-gray-900 dark:text-gray-100">Pkt</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        <tr className="bg-black text-white font-bold">
                                          <td className="p-2">{loadsheet.dealer_name}</td>
                                          <td className="p-2 text-center">{totalCartons}</td>
                                          <td className="p-2 text-center">{totalPacks || ''}</td>
                                        </tr>
                                        <tr className="bg-white dark:bg-gray-800">
                                          <td className="p-2 text-gray-900 dark:text-gray-100" colSpan={3}>{loadsheet.dealer_code}</td>
                                        </tr>
                                        <tr className="bg-black text-white">
                                          <td className="p-2" colSpan={3}>
                                            {loadsheet.territory ? loadsheet.territory.code : 'TERR'}
                                          </td>
                                        </tr>
                                        {loadsheet.lines.map((line, idx) => {
                                          const done = isLineCompleted(loadsheet.id, line.product_code);
                                          return (
                                          <tr
                                            key={idx}
                                            onClick={() => toggleLineCompleted(loadsheet.id, line.product_code)}
                                            className={`border-b border-gray-200 dark:border-gray-600 cursor-pointer select-none transition-colors ${
                                              done
                                                ? 'bg-green-50 dark:bg-green-900/30'
                                                : idx % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-100 dark:bg-gray-700'
                                            }`}
                                          >
                                            <td className={`p-2 text-sm font-semibold ${done ? 'line-through text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-gray-100'}`}>
                                              {done && <span className="mr-1 no-underline inline-block">✓</span>}
                                              {line.product_name}
                                            </td>
                                            <td className="p-1.5 w-1/5">
                                              <div className={`border rounded px-2 py-1 text-center font-bold text-lg min-h-[2rem] ${
                                                done
                                                  ? 'border-green-400 dark:border-green-600 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-400'
                                                  : 'border-gray-300 dark:border-gray-500 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                                              }`}>
                                                {line.qty_carton || ''}
                                                {line.qty_change_carton !== null && line.qty_change_carton !== undefined && line.qty_change_carton !== 0 && (
                                                  <sup className={`ml-1 text-xs font-bold ${
                                                    line.qty_change_carton > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                                                  }`}>
                                                    {line.qty_change_carton > 0 ? '+' : ''}{line.qty_change_carton}
                                                  </sup>
                                                )}
                                              </div>
                                            </td>
                                            <td className="p-1.5 w-1/5">
                                              <div className={`border rounded px-2 py-1 text-center font-bold text-lg min-h-[2rem] ${
                                                done
                                                  ? 'border-green-400 dark:border-green-600 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-400'
                                                  : 'border-gray-300 dark:border-gray-500 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                                              }`}>
                                                {line.qty_pack || ''}
                                                {line.qty_change_pack !== null && line.qty_change_pack !== undefined && line.qty_change_pack !== 0 && (
                                                  <sup className={`ml-1 text-xs font-bold ${
                                                    line.qty_change_pack > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                                                  }`}>
                                                    {line.qty_change_pack > 0 ? '+' : ''}{line.qty_change_pack}
                                                  </sup>
                                                )}
                                              </div>
                                            </td>
                                          </tr>
                                          );
                                        })}
                                        <tr className="bg-gray-100 dark:bg-gray-700 font-bold border-t-2 border-gray-300 dark:border-gray-600">
                                          <td className="p-3 text-gray-900 dark:text-gray-100">Toplam</td>
                                          <td className="p-3 text-center text-gray-900 dark:text-gray-100">{totalCartons}</td>
                                          <td className="p-3 text-center text-gray-900 dark:text-gray-100">{totalPacks || ''}</td>
                                        </tr>
                                      </tbody>
                                    </table>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Yukarı Git Butonu */}
      {showScrollTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white w-12 h-12 rounded-full shadow-lg flex items-center justify-center text-2xl z-50 transition-opacity"
          aria-label="Yukarı git"
        >
          ↑
        </button>
      )}
    </div>
  );
}
