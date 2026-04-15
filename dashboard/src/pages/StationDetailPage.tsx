import { useCallback, useState, useEffect, Fragment } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService, StationDetail, StationTracking } from '../services/api';
import { usePolling } from '../hooks/usePolling';

const gradients = [
  'from-violet-500 to-purple-600',
  'from-cyan-500 to-blue-600',
  'from-emerald-500 to-green-600',
  'from-amber-500 to-orange-600',
  'from-rose-500 to-pink-600',
];

export default function StationDetailPage() {
  const { stationId } = useParams<{ stationId: string }>();
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [trackingData, setTrackingData] = useState<StationTracking | null>(null);
  const [trackingLoading, setTrackingLoading] = useState(false);

  // Station detail'den doğru cycle_id'yi al (backend station'ın depot'una göre buluyor)
  const fetchStationDetail = useCallback(async () => {
    if (!stationId) return null;
    const detail = await apiService.getStationDetail(stationId);
    // Backend'den dönen doğru cycle_id'yi kaydet
    if (detail?.cycle_id && detail.cycle_id !== cycleId) {
      setCycleId(detail.cycle_id);
    }
    return detail;
  }, [stationId, cycleId]);

  const { data, isLoading, error, lastUpdated, refresh } = usePolling<StationDetail | null>({
    fetchFn: fetchStationDetail,
    interval: 30000,
    enabled: !!stationId,
  });

  // Tracking verisini cycle_id belirlendiğinde çek
  useEffect(() => {
    if (stationId && cycleId) {
      setTrackingLoading(true);
      apiService.getStationTracking(stationId, cycleId)
        .then(setTrackingData)
        .catch(console.error)
        .finally(() => setTrackingLoading(false));
    }
  }, [stationId, cycleId]);

  const handleRefresh = () => {
    refresh();
    if (stationId && cycleId) {
      setTrackingLoading(true);
      apiService.getStationTracking(stationId, cycleId)
        .then(setTrackingData)
        .catch(console.error)
        .finally(() => setTrackingLoading(false));
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatNumber = (num: number) => {
    return num.toFixed(1).replace(/\.0$/, '');
  };

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <div className="mb-6 flex items-center gap-3">
          <Link to="/" className="inline-flex items-center gap-2 text-violet-600 hover:text-violet-800 font-medium transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Dashboard'a Dön
          </Link>
          {(() => {
            const depotName = localStorage.getItem('dashboard_current_depot_name');
            const depotCode = localStorage.getItem('dashboard_current_depot');
            if (depotName || depotCode) {
              return (
                <>
                  <span className="text-gray-300">|</span>
                  <Link to={`/depot/${depotCode}`} className="px-3 py-1 rounded-lg bg-violet-50 text-violet-700 text-sm font-medium hover:bg-violet-100 transition-colors">
                    {depotName || depotCode}
                  </Link>
                </>
              );
            }
            return null;
          })()}
        </div>

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">
              {data?.station_name || 'İstasyon Detay'}
            </h1>
            <p className="text-gray-500 mt-1">Bölge ve ürün dağılımı</p>
          </div>

          <div className="flex items-center gap-4">
            {lastUpdated && (
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500 bg-white rounded-xl px-4 py-2 shadow-sm">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                {formatTime(lastUpdated)}
              </div>
            )}
            <button
              onClick={handleRefresh}
              disabled={isLoading || trackingLoading}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 disabled:from-violet-400 disabled:to-purple-500 text-white rounded-xl shadow-lg shadow-violet-500/30 transition-all duration-200"
            >
              <svg
                className={`w-4 h-4 ${isLoading || trackingLoading ? 'animate-spin' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span className="font-medium">Yenile</span>
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-red-600">Hata: {error.message}</p>
          </div>
        )}

        {/* Loading */}
        {isLoading && !data && (
          <div className="flex items-center justify-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg animate-pulse">
              <svg className="w-8 h-8 text-white animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
          </div>
        )}

        {/* Content */}
        {data && (
          <div className="space-y-6">
            {/* Territories */}
            <div className="card p-6 animate-fade-in">
              <div className="flex items-center gap-4 mb-6">
                <div className="stat-icon gradient-emerald">
                  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-800">Atanan Bölgeler</h2>
                  <p className="text-sm text-gray-500">{data.territories.length} bölge</p>
                </div>
              </div>

              {data.territories.length === 0 ? (
                <p className="text-gray-500 text-center py-8">Bu istasyona bölge atanmamış</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.territories.map((territory, index) => (
                    <Link
                      key={territory.territory_code}
                      to={`/territory/${territory.territory_code}`}
                      className="group block"
                    >
                      <div className="relative overflow-hidden rounded-2xl bg-white border border-gray-100 p-5 transition-all duration-300 hover:shadow-lg hover:border-gray-200 hover:-translate-y-1">
                        <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${gradients[index % gradients.length]}`} />

                        <div className="flex items-center gap-3 mb-3">
                          <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradients[index % gradients.length]} flex items-center justify-center text-white font-bold text-sm shadow-lg`}>
                            {territory.display_number}
                          </div>
                          <div>
                            <h4 className="font-semibold text-gray-800 group-hover:text-violet-600 transition-colors">
                              {territory.territory_code}
                            </h4>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                          <div className="bg-gray-50 rounded-lg p-2 text-center">
                            <p className="text-gray-500 text-xs">Fiş</p>
                            <p className="font-semibold text-gray-800">{territory.completed_loadsheets}/{territory.total_loadsheets}</p>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-2 text-center">
                            <p className="text-gray-500 text-xs">Karton</p>
                            <p className="font-semibold text-gray-800">{territory.completed_carton}/{territory.total_carton}</p>
                          </div>
                        </div>

                        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full bg-gradient-to-r ${gradients[index % gradients.length]} progress-bar rounded-full`}
                            style={{
                              width: `${territory.total_carton > 0
                                ? (territory.completed_carton / territory.total_carton * 100)
                                : 0}%`
                            }}
                          />
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* İstasyon Dağılım Tablosu */}
            <div className="card p-6 animate-fade-in">
              <div className="flex items-center gap-4 mb-6">
                <div className="stat-icon gradient-cyan">
                  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-800">Ürün Dağılımı</h2>
                  <p className="text-sm text-gray-500">
                    {trackingData ? `${trackingData.products.length} ürün • ${trackingData.territories.length} bölge` : 'Yükleniyor...'}
                  </p>
                </div>
              </div>

              {trackingLoading && !trackingData ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-10 h-10 rounded-xl bg-cyan-100 flex items-center justify-center">
                    <svg className="w-5 h-5 text-cyan-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </div>
                </div>
              ) : trackingData && trackingData.products.length > 0 ? (
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
                          <Fragment key={territory.id}>
                            <th className="px-3 py-2 text-center text-xs font-medium text-gray-700 border border-gray-300 bg-yellow-50">
                              Kalan
                            </th>
                            <th className="px-3 py-2 text-center text-xs font-medium text-gray-700 border border-gray-300 bg-green-50">
                              Hazırlanan
                            </th>
                          </Fragment>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {trackingData.products.map((product, idx) => {
                        const totalRemaining = product.territories.reduce(
                          (sum, t) => sum + t.remaining_total, 0
                        );
                        const isStockInsufficient = totalRemaining > product.stock_total;
                        const stockDifference = product.stock_total - totalRemaining;

                        return (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-4 py-2 text-sm font-medium text-gray-900 border border-gray-300">
                              <div className="flex justify-between items-center">
                                <span>{product.product_code}</span>
                                {stockDifference !== 0 && (
                                  <span className={`text-xs font-bold ${
                                    stockDifference < 0 ? 'text-red-600' : 'text-green-600'
                                  }`}>
                                    {stockDifference > 0 ? '+' : ''}{formatNumber(stockDifference)}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className={`px-4 py-2 text-center text-sm font-semibold border border-gray-300 ${
                              isStockInsufficient
                                ? 'bg-red-600 text-white'
                                : 'bg-blue-50 text-blue-700'
                            }`}>
                              {formatNumber(product.stock_total)}
                            </td>
                            {product.territories.map((tData) => (
                              <Fragment key={tData.territory_id}>
                                <td className="px-3 py-2 text-center text-sm border border-gray-300 bg-yellow-50">
                                  {tData.remaining_total > 0 ? formatNumber(tData.remaining_total) : '0'}
                                </td>
                                <td className="px-3 py-2 text-center text-sm border border-gray-300 bg-green-50">
                                  {tData.prepared_total > 0 ? formatNumber(tData.prepared_total) : '0'}
                                </td>
                              </Fragment>
                            ))}
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot className="bg-gray-200">
                      <tr>
                        <td className="px-4 py-3 text-sm font-bold text-gray-900 border border-gray-300">
                          Toplam
                        </td>
                        <td className="px-4 py-3 text-center text-sm font-bold text-blue-700 border border-gray-300 bg-blue-50">
                          {formatNumber(trackingData.products.reduce((sum, p) => sum + p.stock_total, 0))}
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
                            <Fragment key={territory.id}>
                              <td className="px-3 py-3 text-center text-sm font-bold text-gray-900 border border-gray-300 bg-yellow-50">
                                {formatNumber(remainingTotal)}
                              </td>
                              <td className="px-3 py-3 text-center text-sm font-bold text-gray-900 border border-gray-300 bg-green-50">
                                {formatNumber(preparedTotal)}
                              </td>
                            </Fragment>
                          );
                        })}
                      </tr>
                    </tfoot>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Ürün dağılım verisi bulunamadı</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
