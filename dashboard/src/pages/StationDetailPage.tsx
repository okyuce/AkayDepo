import { useCallback, useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService, StationDetail } from '../services/api';
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

  useEffect(() => {
    apiService.getActiveCycle().then((res) => {
      if (res.has_active_cycle && res.cycle) {
        setCycleId(res.cycle.id);
      }
    });
  }, []);

  const fetchStationDetail = useCallback(async () => {
    if (!stationId || !cycleId) return null;
    return apiService.getStationDetail(stationId, cycleId);
  }, [stationId, cycleId]);

  const { data, isLoading, error, lastUpdated, refresh } = usePolling<StationDetail | null>({
    fetchFn: fetchStationDetail,
    interval: 30000,
    enabled: !!stationId && !!cycleId,
  });

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'loaded':
        return <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">Tamamlandi</span>;
      case 'pending':
        return <span className="px-3 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">Bekliyor</span>;
      case 'cancelled':
        return <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">Iptal</span>;
      default:
        return <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <Link to="/" className="inline-flex items-center gap-2 text-violet-600 hover:text-violet-800 font-medium transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Dashboard'a Don
          </Link>
        </div>

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">
              {data?.station_name || 'Istasyon Detay'}
            </h1>
            <p className="text-gray-500 mt-1">Bolge ve rut detaylari</p>
          </div>

          <div className="flex items-center gap-4">
            {lastUpdated && (
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500 bg-white rounded-xl px-4 py-2 shadow-sm">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                {formatTime(lastUpdated)}
              </div>
            )}
            <button
              onClick={refresh}
              disabled={isLoading}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 disabled:from-violet-400 disabled:to-purple-500 text-white rounded-xl shadow-lg shadow-violet-500/30 transition-all duration-200"
            >
              <svg
                className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
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
                  <h2 className="text-lg font-semibold text-gray-800">Atanan Bolgeler</h2>
                  <p className="text-sm text-gray-500">{data.territories.length} bolge</p>
                </div>
              </div>

              {data.territories.length === 0 ? (
                <p className="text-gray-500 text-center py-8">Bu istasyona bolge atanmamis</p>
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
                            <p className="text-gray-500 text-xs">Fis</p>
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

            {/* Loadsheets Table */}
            <div className="card p-6 animate-fade-in">
              <div className="flex items-center gap-4 mb-6">
                <div className="stat-icon gradient-cyan">
                  <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-800">Rutlar</h2>
                  <p className="text-sm text-gray-500">{data.loadsheets.length} rut</p>
                </div>
              </div>

              {data.loadsheets.length === 0 ? (
                <p className="text-gray-500 text-center py-8">Bu istasyona rut atanmamis</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-center py-3 px-4 text-sm font-semibold text-gray-600 w-20">Rut No</th>
                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Bayi</th>
                        <th className="text-center py-3 px-4 text-sm font-semibold text-gray-600">Krt</th>
                        <th className="text-center py-3 px-4 text-sm font-semibold text-gray-600">Pkt</th>
                        <th className="text-center py-3 px-4 text-sm font-semibold text-gray-600">Durum</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.loadsheets
                        .sort((a, b) => (a.route_number || 0) - (b.route_number || 0))
                        .map((ls) => (
                        <tr key={ls.id} className="border-b border-gray-100 hover:bg-violet-50/50 transition-colors">
                          <td className="py-3 px-4 text-center">
                            <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 text-white font-bold text-lg shadow-md">
                              {ls.route_number || '-'}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="font-medium text-gray-800">{ls.dealer_name}</div>
                            <div className="text-xs text-gray-500">{ls.dealer_code}</div>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span className="font-semibold text-gray-800">{ls.total_carton}</span>
                          </td>
                          <td className="py-3 px-4 text-center">
                            {ls.total_pack > 0 ? (
                              <span className="px-2 py-1 bg-amber-100 text-amber-700 text-sm font-medium rounded-lg">{ls.total_pack}</span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-center">{getStatusBadge(ls.status)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
