import { useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService, DepotDashboardSummary } from '../services/api';
import { usePolling } from '../hooks/usePolling';
import CycleStatusWidget from '../components/widgets/CycleStatusWidget';
import LoadsheetSummaryWidget from '../components/widgets/LoadsheetSummaryWidget';
import StationProgressWidget from '../components/widgets/StationProgressWidget';
import LoadsheetPieChart from '../components/widgets/LoadsheetPieChart';
import StationBarChart from '../components/widgets/StationBarChart';

export default function DepotDashboardPage() {
  const { depotCode } = useParams<{ depotCode: string }>();

  const fetchData = useCallback(() => {
    if (!depotCode) return Promise.reject(new Error('Depo kodu bulunamadi'));
    return apiService.getDepotSummary(depotCode);
  }, [depotCode]);

  const { data, isLoading, error, lastUpdated, refresh } = usePolling<DepotDashboardSummary>({
    fetchFn: fetchData,
    interval: 30000,
    enabled: !!depotCode,
  });

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb + Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <Link
              to="/"
              className="inline-flex items-center gap-1 text-sm text-violet-600 hover:text-violet-800 mb-2 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Genel Gorunum
            </Link>
            <h1 className="text-3xl font-bold text-gray-800">
              {data?.depot_name || depotCode}
            </h1>
            <p className="text-gray-500 mt-1">Dongu ve fis durumu ozeti</p>
          </div>

          <div className="flex items-center gap-4">
            {lastUpdated && (
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500 bg-white rounded-xl px-4 py-2 shadow-sm">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Son guncelleme: {formatTime(lastUpdated)}
              </div>
            )}

            <button
              onClick={refresh}
              disabled={isLoading}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 disabled:from-violet-400 disabled:to-purple-500 text-white rounded-xl shadow-lg shadow-violet-500/30 transition-all duration-200 hover:shadow-xl hover:-translate-y-0.5"
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

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-3 animate-fade-in">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-red-800">Veri yuklenirken hata olustu</p>
              <p className="text-sm text-red-600">{error.message}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && !data && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/30 animate-pulse">
                <svg className="w-8 h-8 text-white animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <p className="text-gray-500 font-medium">Veriler yukleniyor...</p>
            </div>
          </div>
        )}

        {/* Main Content */}
        {data && (
          <div className="space-y-6">
            {/* Top Row - Cycle Status & Loadsheet Summary */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <CycleStatusWidget cycle={data.cycle} lastImport={data.last_import} />
              <LoadsheetSummaryWidget stats={data.loadsheet_stats} />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <LoadsheetPieChart stats={data.loadsheet_stats} />
              <StationBarChart stations={data.station_summary} />
            </div>

            {/* Station Progress */}
            <StationProgressWidget stations={data.station_summary} />
          </div>
        )}
      </div>
    </div>
  );
}
