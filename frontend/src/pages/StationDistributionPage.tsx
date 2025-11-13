/**
 * Station Distribution Page
 * İstasyon bazında detaylı dağılım görünümü
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

interface TerritoryQuantity {
  territory_id: string;
  territory_display: string;
  carton: number;
  pack: number;
  total_carton: number;
}

interface ProductRow {
  product_code: string;
  product_name: string;
  territories: TerritoryQuantity[];
  total_carton: number;
  total_pack: number;
  total_carton_equivalent: number;
}

interface DistributionData {
  station_id: string;
  station_name: string;
  territories: Territory[];
  products: ProductRow[];
  grand_total: number;
}

export default function StationDistributionPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('');
  const [distributionData, setDistributionData] = useState<any>(null);
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
        
        // İlk istasyonu otomatik seç
        if (stationList.length > 0) {
          setSelectedStationId(stationList[0].id);
          await loadStationDistribution(stationList[0].id);
        }
      }
    } catch (err) {
      console.error('İstasyonlar yüklenemedi:', err);
    }
  };

  const loadStationDistribution = async (stationId: string) => {
    if (!cycleId) return;
    
    setIsLoading(true);
    try {
      // Backend'den Excel formatında veri al
      const data = await apiService.getStationDistribution(stationId, cycleId);
      setDistributionData(data);
    } catch (err) {
      console.error('Dağılım yüklenemedi:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStationChange = (stationId: string) => {
    setSelectedStationId(stationId);
    loadStationDistribution(stationId);
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

              {/* Dağılım Tablosu - Excel Format (Ürün x Territory Matrix) */}
              {isLoading ? (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <p className="text-center text-gray-500">Yükleniyor...</p>
                </div>
              ) : distributionData ? (
                <div className="bg-white rounded-lg shadow-md overflow-hidden">
                  {/* Header */}
                  <div className="bg-blue-600 text-white p-4">
                    <h2 className="text-xl font-bold">{distributionData.station_name}</h2>
                    <p className="text-sm mt-1">
                      Toplam: <span className="font-semibold">{distributionData.grand_total} karton eşdeğeri</span>
                      {' • '}
                      Ürün Sayısı: <span className="font-semibold">{distributionData.products.length}</span>
                      {' • '}
                      Territory Sayısı: <span className="font-semibold">{distributionData.territories.length}</span>
                    </p>
                  </div>

                  {/* Excel Formatında Matris Tablo */}
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-yellow-100">
                        <tr>
                          <th rowSpan={2} className="px-4 py-3 text-center text-sm font-bold text-gray-900 border border-gray-400 bg-yellow-200">
                            {distributionData.station_name}
                          </th>
                          <th colSpan={distributionData.territories.length} className="px-4 py-2 text-center text-sm font-bold text-gray-900 border border-gray-400">
                            {distributionData.territories.length}
                          </th>
                          <th rowSpan={2} className="px-4 py-3 text-center text-sm font-bold text-gray-900 border border-gray-400 bg-yellow-200">
                            Toplam Çekilecek Stok
                          </th>
                        </tr>
                        <tr>
                          {distributionData.territories.map((territory: any) => (
                            <th key={territory.id} className="px-3 py-2 text-center text-xs font-medium text-gray-700 border border-gray-400">
                              {territory.code}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white">
                        {distributionData.products.map((product, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-4 py-2 text-sm text-gray-900 border border-gray-300">
                              {product.product_code}
                            </td>
                            {distributionData.territories.map((territory) => {
                              const territoryData = product.territories.find(
                                (t) => t.territory_id === territory.id
                              );
                              const value = territoryData?.total_carton || 0;
                              return (
                                <td key={territory.id} className="px-3 py-2 text-center text-sm border border-gray-300">
                                  {value > 0 ? value.toFixed(1).replace(/\.0$/, '') : '0'}
                                </td>
                              );
                            })}
                            <td className="px-4 py-2 text-right text-sm font-semibold text-gray-900 border border-gray-300">
                              {product.total_carton_equivalent.toFixed(1).replace(/\.0$/, '')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-200">
                        <tr>
                          <td className="px-4 py-3 text-sm font-bold text-gray-900 border border-gray-400">
                            toplam
                          </td>
                          {distributionData.territories.map((territory) => {
                            // Her territory'nin toplam kartonunu hesapla
                            const territoryTotal = distributionData.products.reduce((sum, product) => {
                              const territoryData = product.territories.find(
                                (t) => t.territory_id === territory.id
                              );
                              return sum + (territoryData?.total_carton || 0);
                            }, 0);
                            return (
                              <td key={territory.id} className="px-3 py-3 text-center text-sm font-bold text-gray-900 border border-gray-400">
                                {territoryTotal.toFixed(1).replace(/\.0$/, '')}
                              </td>
                            );
                          })}
                          <td className="px-4 py-3 text-right text-sm font-bold text-gray-900 border border-gray-400">
                            {distributionData.grand_total.toFixed(1).replace(/\.0$/, '')}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  {/* Sayım Tablosu - Ürün Bazında */}
                  {distributionData.product_counts && distributionData.product_counts.length > 0 && (
                    <div className="mt-6 bg-white rounded-lg shadow-md overflow-hidden">
                      <div className="bg-yellow-600 text-white p-3">
                        <h3 className="text-lg font-bold">{distributionData.station_name}</h3>
                        <p className="text-sm">Sayım</p>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-sm">
                          <thead className="bg-yellow-100">
                            <tr>
                              <th rowSpan={2} className="px-4 py-3 text-center text-sm font-bold text-gray-900 border border-gray-400">
                                Ürün Kodu
                              </th>
                              {distributionData.product_counts[0]?.counts.map((_: any, idx: number) => (
                                <th key={idx} className="px-3 py-2 text-center text-xs font-medium text-gray-700 border border-gray-400">
                                  Sayım{idx + 1}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="bg-white">
                            {distributionData.product_counts.map((productCount: any, idx: number) => (
                              <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-2 text-sm text-gray-900 border border-gray-300">
                                  {productCount.product_code}
                                </td>
                                {productCount.counts.map((count: number, countIdx: number) => (
                                  <td key={countIdx} className="px-3 py-2 text-center text-sm border border-gray-300">
                                    {count > 0 ? count.toFixed(1).replace(/\.0$/, '') : '0'}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                          <tfoot className="bg-gray-200">
                            <tr>
                              <td className="px-4 py-3 text-sm font-bold text-gray-900 border border-gray-400">
                                toplam
                              </td>
                              {distributionData.total_counts?.map((total: number, idx: number) => (
                                <td key={idx} className="px-3 py-3 text-center text-sm font-bold text-gray-900 border border-gray-400">
                                  {total.toFixed(1).replace(/\.0$/, '')}
                                </td>
                              ))}
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
