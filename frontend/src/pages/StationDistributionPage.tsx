/**
 * Station Distribution Page
 * İstasyon bazlı ürün takip tablosu - Anlık stok, Kalan ve Hazırlanan miktarları
 */
import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import Navbar from '../components/Navbar';

interface Station {
  id: string;
  name: string;
}

interface Territory {
  id: string;
  code: string;
  display_number: string;
  name: string;
}

interface TerritoryTracking {
  territory_id: string;
  territory_display: string;
  remaining_carton: number;
  remaining_pack: number;
  remaining_total: number;
  prepared_carton: number;
  prepared_pack: number;
  prepared_total: number;
}

interface ProductTracking {
  product_code: string;
  product_name: string;
  stock_carton: number;
  stock_pack: number;
  stock_total: number;
  territories: TerritoryTracking[];
}


interface TrackingData {
  station_id: string;
  station_name: string;
  territories: Territory[];
  products: ProductTracking[];
}

export default function StationDistributionPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('');
  const [trackingData, setTrackingData] = useState<TrackingData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [cycleId, setCycleId] = useState<string | null>(null);

  useEffect(() => {
    loadActiveCycle();
  }, []);

  const loadActiveCycle = async () => {
    try {
      const activeData = await apiService.getActivecycle();
      if (activeData.has_active_cycle && activeData.cycle) {
        setCycleId(activeData.cycle.id);
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
        // İstasyonları parse et - backend'den station_id geliyor
        const stationList = plan.stations.map((s: any) => ({
          id: s.station_id,
          name: s.station_name
        }));
        setStations(stationList);
        // İlk istasyonu otomatik seçme - kullanıcı manuel seçsin
      }
    } catch (err) {
      console.error('İstasyonlar yüklenemedi:', err);
    }
  };

  const loadStationTracking = async (stationId: string) => {
    if (!cycleId) return;
    
    setIsLoading(true);
    try {
      const data = await apiService.getStationTracking(stationId, cycleId);
      setTrackingData(data);
    } catch (err) {
      console.error('Takip verisi yüklenemedi:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStationChange = (stationId: string) => {
    setSelectedStationId(stationId);
    if (stationId) {
      loadStationTracking(stationId);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-6">İstasyon Dağılımı</h1>

          {!cycleId ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800">
                Aktif döngü bulunamadı. Lütfen önce Excel yükleyip plan oluşturun.
              </p>
            </div>
          ) : stations.length === 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800">
                Plan bulunamadı. Lütfen planlama oluşturun.
              </p>
            </div>
          ) : (
            <>
              {/* İstasyon Seçimi */}
              <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex justify-between items-center">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      İstasyon Seçin
                    </label>
                    <select
                      value={selectedStationId}
                      onChange={(e) => handleStationChange(e.target.value)}
                      className="w-full md:w-64 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">İstasyon Seçiniz...</option>
                      {stations.map((station) => (
                        <option key={station.id} value={station.id}>
                          {station.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <button
                    onClick={() => loadActiveCycle()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
                  >
                    Yenile
                  </button>
                </div>
              </div>

              {/* Takip Tablosu - Ürün Kodu | Anlık Stok | Territory Kalan/Hazırlanan */}
              {!selectedStationId ? (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                  <p className="text-center text-blue-800">
                    Lütfen yukarıdaki listeden bir istasyon seçin.
                  </p>
                </div>
              ) : isLoading ? (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <p className="text-center text-gray-500">Yüklüyor...</p>
                </div>
              ) : trackingData ? (
                <div className="bg-white rounded-lg shadow-md overflow-hidden">
                  {/* Header */}
                  <div className="bg-blue-600 text-white p-4">
                    <h2 className="text-xl font-bold">{trackingData.station_name}</h2>
                    <p className="text-sm mt-1">
                      Ürün Sayısı: <span className="font-semibold">{trackingData.products.length}</span>
                      {' • '}
                      Territory Sayısı: <span className="font-semibold">{trackingData.territories.length}</span>
                    </p>
                  </div>

                  {/* Takip Tablosu */}
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-gray-100">
                        <tr>
                          <th rowSpan={2} className="px-4 py-3 text-left text-sm font-bold text-gray-900 border border-gray-300">
                            Ürün Kodu
                          </th>
                          <th rowSpan={2} className="px-4 py-3 text-center text-sm font-bold text-gray-900 border border-gray-300 bg-blue-50">
                            Anlık Stok
                          </th>
                          {trackingData.territories.map((territory) => (
                            <th key={territory.id} colSpan={2} className="px-4 py-2 text-center text-sm font-bold text-gray-900 border border-gray-300">
                              {territory.code}
                            </th>
                          ))}
                        </tr>
                        <tr>
                          {trackingData.territories.map((territory) => (
                            <>
                              <th key={`${territory.id}-remaining`} className="px-3 py-2 text-center text-xs font-medium text-gray-700 border border-gray-300 bg-yellow-50">
                                Kalan
                              </th>
                              <th key={`${territory.id}-prepared`} className="px-3 py-2 text-center text-xs font-medium text-gray-700 border border-gray-300 bg-green-50">
                                Hazırlanan
                              </th>
                            </>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {trackingData.products.map((product, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-4 py-2 text-sm font-medium text-gray-900 border border-gray-300">
                              {product.product_code}
                            </td>
                            <td className="px-4 py-2 text-center text-sm font-semibold text-blue-700 border border-gray-300 bg-blue-50">
                              {product.stock_total.toFixed(1).replace(/\.0$/, '')}
                            </td>
                            {product.territories.map((tData) => (
                              <>
                                <td key={`${tData.territory_id}-remaining`} className="px-3 py-2 text-center text-sm border border-gray-300 bg-yellow-50">
                                  {tData.remaining_total > 0 ? tData.remaining_total.toFixed(1).replace(/\.0$/, '') : '0'}
                                </td>
                                <td key={`${tData.territory_id}-prepared`} className="px-3 py-2 text-center text-sm border border-gray-300 bg-green-50">
                                  {tData.prepared_total > 0 ? tData.prepared_total.toFixed(1).replace(/\.0$/, '') : '0'}
                                </td>
                              </>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-200">
                        <tr>
                          <td className="px-4 py-3 text-sm font-bold text-gray-900 border border-gray-300">
                            Toplam
                          </td>
                          <td className="px-4 py-3 text-center text-sm font-bold text-blue-700 border border-gray-300 bg-blue-50">
                            {trackingData.products.reduce((sum, p) => sum + p.stock_total, 0).toFixed(1).replace(/\.0$/, '')}
                          </td>
                          {trackingData.territories.map((territory) => {
                            const remainingTotal = trackingData.products.reduce((sum, product) => {
                              const tData = product.territories.find(t => t.territory_id === territory.id);
                              return sum + (tData?.remaining_total || 0);
                            }, 0);
                            const preparedTotal = trackingData.products.reduce((sum, product) => {
                              const tData = product.territories.find(t => t.territory_id === territory.id);
                              return sum + (tData?.prepared_total || 0);
                            }, 0);
                            return (
                              <>
                                <td key={`${territory.id}-remaining-total`} className="px-3 py-3 text-center text-sm font-bold text-gray-900 border border-gray-300 bg-yellow-50">
                                  {remainingTotal.toFixed(1).replace(/\.0$/, '')}
                                </td>
                                <td key={`${territory.id}-prepared-total`} className="px-3 py-3 text-center text-sm font-bold text-gray-900 border border-gray-300 bg-green-50">
                                  {preparedTotal.toFixed(1).replace(/\.0$/, '')}
                                </td>
                              </>
                            );
                          })}
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
