/**
 * Stok Hareketleri Sayfası
 * Döngü bazlı stok hareket loglarını görüntüleme ve filtreleme
 */
import { useState, useEffect, useRef } from 'react';
import { apiService } from '../services/api';
import * as XLSX from 'xlsx';
import Navbar from '../components/Navbar';

interface Movement {
  id: string;
  station_id: string;
  station_name: string;
  territory_name: string;
  product_id: string;
  product_code: string;
  product_name: string;
  loadsheet_id: string | null;
  package_number: string;
  sheet_no: string;
  movement_type: string;
  quantity_carton: number;
  quantity_pack: number;
  before_carton: number;
  before_pack: number;
  after_carton: number;
  after_pack: number;
  created_at: string;
  note: string | null;
}

interface Station {
  id: string;
  name: string;
}

interface Territory {
  id: string;
  name: string;
}

interface Dealer {
  id: string;
  name: string;
}

interface Product {
  id: string;
  code: string;
  name: string;
}

const MOVEMENT_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  deduction: { label: 'Düşüm', color: 'bg-red-100 text-red-800' },
  refund: { label: 'İade', color: 'bg-green-100 text-green-800' },
  manual_add: { label: 'Manuel Ekleme', color: 'bg-blue-100 text-blue-800' },
  manual_remove: { label: 'Manuel Çıkarma', color: 'bg-orange-100 text-orange-800' },
};

export default function StockMovementsPage() {
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [cycleName, setCycleName] = useState<string>('');
  const [movements, setMovements] = useState<Movement[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  // Filtreler
  const [stationFilter, setStationFilter] = useState<string>('');
  const [territoryFilter, setTerritoryFilter] = useState<string>('');
  const [dealerFilter, setDealerFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [selectedSkus, setSelectedSkus] = useState<string[]>([]);
  const [skuDropdownOpen, setSkuDropdownOpen] = useState(false);
  const skuDropdownRef = useRef<HTMLDivElement>(null);

  // Dropdown verileri
  const [stations, setStations] = useState<Station[]>([]);
  const [territories, setTerritories] = useState<Territory[]>([]);
  const [allTerritories, setAllTerritories] = useState<Territory[]>([]);
  const [stationTerritoryMap, setStationTerritoryMap] = useState<Record<string, string[]>>({});
  const [dealers, setDealers] = useState<Dealer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);

  // Sayfalama
  const [page, setPage] = useState(0);
  const pageSize = 100;

  // Aktif döngüyü ve istasyonları yükle
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const response = await apiService.getActivecycle();
        if (response?.has_active_cycle && response.cycle) {
          const cycle = response.cycle;
          setCycleId(cycle.id);
          setCycleName(`Döngü ${cycle.cycle_no} - ${cycle.run_time}`);

          // Territory listesini cycle'dan al (doğru ID'ler için)
          const territoryList = await apiService.getTerritoriesByCycle(cycle.id);
          const mappedTerritories = territoryList.map((t: { id: string; name: string }) => ({ id: t.id, name: t.name }));
          setAllTerritories(mappedTerritories);
          setTerritories(mappedTerritories);

          // Plan'dan station-territory eşleşmesini al
          const plan = await apiService.getPlan(cycle.id);
          const stationTerritoryMapping: Record<string, string[]> = {};
          plan.stations?.forEach((s: { station_id: string; territories?: { territory_code: string }[] }) => {
            const territoryNames = s.territories?.map((t: { territory_code: string }) => {
              // territory_code format: "TERR030713-Büsan" -> "Büsan"
              const parts = t.territory_code.split('-');
              return parts.length > 1 ? parts.slice(1).join('-') : t.territory_code;
            }) || [];
            stationTerritoryMapping[s.station_id] = territoryNames;
          });
          setStationTerritoryMap(stationTerritoryMapping);
        }

        const stationList = await apiService.listStations();
        setStations(stationList.filter(s => s.active));

        // Ürün listesini yükle
        const productList = await apiService.getProductOrder();
        setProducts(productList.map((p: { id: string; code: string; name: string }) => ({
          id: p.id,
          code: p.code,
          name: p.name
        })));
      } catch (error) {
        console.error('Veri yükleme hatası:', error);
      }
    };

    loadInitialData();
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

  // İstasyon filtresi değiştiğinde territory'leri filtrele
  useEffect(() => {
    if (!stationFilter) {
      // Tüm territory'leri göster
      setTerritories(allTerritories);
    } else {
      // Seçilen istasyonun territory'lerini filtrele
      const territoryNames = stationTerritoryMap[stationFilter] || [];
      const filtered = allTerritories.filter(t => territoryNames.includes(t.name));
      setTerritories(filtered);
    }
    // Territory filtresi sıfırla (seçili territory artık listede olmayabilir)
    setTerritoryFilter('');
  }, [stationFilter, allTerritories, stationTerritoryMap]);

  // Hareketleri yükle
  useEffect(() => {
    const loadMovements = async () => {
      if (!cycleId) return;

      setLoading(true);
      try {
        const params: Record<string, string | number> = {
          limit: pageSize,
          offset: page * pageSize,
        };

        if (stationFilter) params.station_id = stationFilter;
        if (territoryFilter) params.territory_id = territoryFilter;
        if (dealerFilter) params.dealer_id = dealerFilter;
        if (typeFilter) params.movement_type = typeFilter;
        if (selectedSkus.length > 0) params.sku = selectedSkus.join(',');

        const data = await apiService.getStockMovementsByCycle(cycleId, params);
        setMovements(data.movements);
        setTotal(data.total);

        // Bayi listesini movements'tan oluştur (unique)
        const uniqueDealers: Record<string, string> = {};
        data.movements.forEach((m) => {
          if (m.dealer_id && m.dealer_name) {
            uniqueDealers[m.dealer_id] = m.dealer_name;
          }
        });
        setDealers(Object.entries(uniqueDealers).map(([id, name]) => ({ id, name })));
      } catch (error) {
        console.error('Hareket yükleme hatası:', error);
      } finally {
        setLoading(false);
      }
    };

    loadMovements();
  }, [cycleId, stationFilter, territoryFilter, dealerFilter, typeFilter, selectedSkus, page]);

  // Filtre değiştiğinde sayfayı sıfırla
  const handleFilterChange = (setter: (val: string) => void, value: string) => {
    setter(value);
    setPage(0);
  };

  // Excel export
  const handleExport = async () => {
    if (!cycleId) return;

    try {
      // Tüm verileri al (limit yüksek)
      const params: Record<string, string | number> = { limit: 10000 };
      if (stationFilter) params.station_id = stationFilter;
      if (territoryFilter) params.territory_id = territoryFilter;
      if (typeFilter) params.movement_type = typeFilter;
      if (selectedSkus.length > 0) params.sku = selectedSkus.join(',');

      const data = await apiService.getStockMovementsByCycle(cycleId, params);

      const exportData = data.movements.map((m) => ({
        'Tarih': new Date(m.created_at).toLocaleString('tr-TR'),
        'İstasyon': m.station_name,
        'Territory': m.territory_name,
        'Ürün Kodu': m.product_code,
        'Ürün Adı': m.product_name,
        'Fiş No': m.package_number || '-',
        'Hareket Tipi': MOVEMENT_TYPE_LABELS[m.movement_type]?.label || m.movement_type,
        'Miktar (Karton)': m.movement_type.includes('add') || m.movement_type === 'refund'
          ? `+${m.quantity_carton}`
          : `-${m.quantity_carton}`,
        'Miktar (Paket)': m.movement_type.includes('add') || m.movement_type === 'refund'
          ? `+${m.quantity_pack}`
          : `-${m.quantity_pack}`,
        'Önceki Stok': `${m.before_carton} krt / ${m.before_pack} pkt`,
        'Sonraki Stok': `${m.after_carton} krt / ${m.after_pack} pkt`,
        'Not': m.note || '',
      }));

      const ws = XLSX.utils.json_to_sheet(exportData);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Stok Hareketleri');

      // Kolon genişlikleri
      ws['!cols'] = [
        { wch: 18 }, // Tarih
        { wch: 12 }, // İstasyon
        { wch: 15 }, // Territory
        { wch: 12 }, // Ürün Kodu
        { wch: 25 }, // Ürün Adı
        { wch: 15 }, // Fiş No
        { wch: 15 }, // Hareket Tipi
        { wch: 12 }, // Miktar Karton
        { wch: 12 }, // Miktar Paket
        { wch: 18 }, // Önceki
        { wch: 18 }, // Sonraki
        { wch: 20 }, // Not
      ];

      XLSX.writeFile(wb, `stok_hareketleri_${new Date().toISOString().slice(0, 10)}.xlsx`);
    } catch (error) {
      console.error('Export hatası:', error);
      alert('Excel export başarısız!');
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Stok Hareketleri</h1>
          <p className="text-gray-600">{cycleName}</p>
        </div>
        <button
          onClick={handleExport}
          disabled={movements.length === 0}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Excel
        </button>
      </div>

      {/* Filtreler */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          {/* SKU Filtresi - Çoktan Seçmeli */}
          <div className="relative" ref={skuDropdownRef}>
            <label className="block text-sm font-medium text-gray-700 mb-1">SKU</label>
            <button
              type="button"
              onClick={() => setSkuDropdownOpen(!skuDropdownOpen)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-left bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 flex justify-between items-center"
            >
              <span className={selectedSkus.length === 0 ? 'text-gray-400' : 'text-gray-900'}>
                {selectedSkus.length === 0 ? 'Seçiniz...' : `${selectedSkus.length} ürün seçili`}
              </span>
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {skuDropdownOpen && (
              <div className="absolute z-50 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
                <div className="p-2 border-b border-gray-200">
                  <button
                    type="button"
                    onClick={() => { setSelectedSkus([]); setPage(0); }}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    Temizle
                  </button>
                </div>
                {products.map((p) => (
                  <label
                    key={p.id}
                    className="flex items-center px-3 py-2 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedSkus.includes(p.code)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedSkus([...selectedSkus, p.code]);
                        } else {
                          setSelectedSkus(selectedSkus.filter(s => s !== p.code));
                        }
                        setPage(0);
                      }}
                      className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm">
                      <span className="font-medium">{p.code}</span>
                      <span className="text-gray-500 ml-1">- {p.name}</span>
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* İstasyon Filtresi */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">İstasyon</label>
            <select
              value={stationFilter}
              onChange={(e) => handleFilterChange(setStationFilter, e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Tümü</option>
              {stations.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          {/* Territory Filtresi */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Territory</label>
            <select
              value={territoryFilter}
              onChange={(e) => handleFilterChange(setTerritoryFilter, e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Tümü</option>
              {territories.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

          {/* Bayi Filtresi */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Bayi</label>
            <select
              value={dealerFilter}
              onChange={(e) => handleFilterChange(setDealerFilter, e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Tümü</option>
              {dealers.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          {/* Hareket Tipi Filtresi */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hareket Tipi</label>
            <select
              value={typeFilter}
              onChange={(e) => handleFilterChange(setTypeFilter, e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Tümü</option>
              <option value="deduction">Düşüm</option>
              <option value="refund">İade</option>
              <option value="manual_add">Manuel Ekleme</option>
              <option value="manual_remove">Manuel Çıkarma</option>
            </select>
          </div>

          {/* Toplam */}
          <div className="flex items-end">
            <div className="text-sm text-gray-600">
              Toplam: <span className="font-semibold text-gray-800">{total}</span> hareket
            </div>
          </div>
        </div>
      </div>

      {/* Tablo */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Yükleniyor...</div>
        ) : movements.length === 0 ? (
          <div className="p-8 text-center text-gray-500">Hareket bulunamadı</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tarih</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">İstasyon</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Territory</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ürün</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fiş No</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tip</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Miktar</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Önceki</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sonraki</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {movements.map((m) => {
                  const typeInfo = MOVEMENT_TYPE_LABELS[m.movement_type] || { label: m.movement_type, color: 'bg-gray-100 text-gray-800' };
                  const isPositive = m.movement_type === 'refund' || m.movement_type === 'manual_add';

                  return (
                    <tr key={m.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                        {formatDate(m.created_at)}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                        {m.station_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                        {m.territory_name}
                      </td>
                      <td className="px-4 py-3 text-sm whitespace-nowrap">
                        <div className="font-medium text-gray-900">{m.product_code}</div>
                        <div className="text-gray-500 text-xs">{m.product_name}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                        {m.package_number || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${typeInfo.color}`}>
                          {typeInfo.label}
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-sm text-right font-medium whitespace-nowrap ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                        {isPositive ? '+' : '-'}{m.quantity_carton} krt
                        {m.quantity_pack > 0 && <span className="text-gray-400 ml-1">/ {m.quantity_pack} pkt</span>}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-gray-500 whitespace-nowrap">
                        {m.before_carton} / {m.before_pack}
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-gray-900 font-medium whitespace-nowrap">
                        {m.after_carton} / {m.after_pack}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Sayfa {page + 1} / {totalPages}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
              >
                Önceki
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
              >
                Sonraki
              </button>
            </div>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
