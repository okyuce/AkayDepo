import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TooltipItem,
} from 'chart.js';
import { apiService, MultiDepotSummary, DepotSummaryItem } from '../services/api';
import { usePolling } from '../hooks/usePolling';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function SummaryCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  const colorClasses: Record<string, string> = {
    violet: 'from-violet-500 to-purple-600 shadow-violet-500/30',
    emerald: 'from-emerald-500 to-green-600 shadow-emerald-500/30',
    amber: 'from-amber-500 to-orange-600 shadow-amber-500/30',
  };

  return (
    <div className="card p-5 animate-fade-in">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${colorClasses[color]} flex items-center justify-center shadow-lg`}>
          <span className="text-white text-lg font-bold">{value}</span>
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-800">{value}</p>
        </div>
      </div>
    </div>
  );
}

function DepotCard({ depot }: { depot: DepotSummaryItem }) {
  const { loadsheet_stats } = depot;
  const { total, completed, pending, revision_cancelled, completion_percentage } = loadsheet_stats;
  const gradientId = `progress-${depot.depot_code}`;

  return (
    <Link
      to={`/depot/${depot.depot_code}`}
      className={`card p-5 animate-fade-in transition-all duration-200 hover:shadow-xl hover:-translate-y-1 cursor-pointer block ${
        !depot.has_active_cycle ? 'opacity-60' : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="stat-icon gradient-cyan">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-gray-800 truncate">{depot.depot_name}</h3>
            {depot.has_active_cycle && depot.cycle_no && (
              <span className="text-xs px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-700 font-medium flex-shrink-0">
                D{depot.cycle_no}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500">
            {depot.has_active_cycle ? `Toplam ${total} fis` : 'Aktif dongu yok'}
            {depot.run_time && ` · ${depot.run_time}`}
          </p>
        </div>
      </div>

      {depot.has_active_cycle && total > 0 ? (
        <>
          {/* Progress Circle + Stats */}
          <div className="flex items-center gap-4 mb-4">
            <div className="relative w-20 h-20 flex-shrink-0">
              <svg className="w-20 h-20 transform -rotate-90">
                <circle cx="40" cy="40" r="34" stroke="#e5e7eb" strokeWidth="8" fill="none" />
                <circle
                  cx="40" cy="40" r="34"
                  stroke={`url(#${gradientId})`}
                  strokeWidth="8"
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray={`${completion_percentage * 2.136} 213.6`}
                  className="transition-all duration-1000"
                />
                <defs>
                  <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#7c3aed" />
                    <stop offset="100%" stopColor="#06b6d4" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-sm font-bold text-gray-800">%{completion_percentage}</span>
              </div>
            </div>
            <div className="flex-1">
              <p className="text-xs text-gray-500 mb-1">Tamamlanma</p>
              <p className="text-2xl font-bold text-gray-800">{completed}<span className="text-sm text-gray-400">/{total}</span></p>
              <p className="text-xs text-gray-500">fis tamamlandi</p>
            </div>
          </div>

          {/* Mini Stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-gradient-to-br from-emerald-50 to-green-50 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-emerald-600">{completed}</p>
              <p className="text-[10px] text-emerald-600 font-medium">Tamam</p>
            </div>
            <div className="bg-gradient-to-br from-amber-50 to-yellow-50 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-amber-600">{pending}</p>
              <p className="text-[10px] text-amber-600 font-medium">Bekliyor</p>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-blue-600">{revision_cancelled}</p>
              <p className="text-[10px] text-blue-600 font-medium">Revizyon</p>
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-4">
          <div className="w-14 h-14 mx-auto mb-2 rounded-full bg-gray-100 flex items-center justify-center">
            <svg className="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
          </div>
          <p className="text-sm text-gray-500">Dongu yok</p>
        </div>
      )}
    </Link>
  );
}

function DepotBarChart({ depots }: { depots: DepotSummaryItem[] }) {
  const activeDepots = depots.filter(d => d.has_active_cycle && d.loadsheet_stats.total > 0);

  if (activeDepots.length === 0) {
    return null;
  }

  const data = {
    labels: activeDepots.map(d => d.depot_code),
    datasets: [
      {
        label: 'Tamamlanan',
        data: activeDepots.map(d => d.loadsheet_stats.completed),
        backgroundColor: 'rgba(124, 58, 237, 0.9)',
        borderColor: 'rgba(124, 58, 237, 1)',
        borderWidth: 0,
        borderRadius: 6,
        borderSkipped: false,
      },
      {
        label: 'Bekleyen',
        data: activeDepots.map(d => d.loadsheet_stats.pending),
        backgroundColor: 'rgba(251, 191, 36, 0.8)',
        borderColor: 'rgba(251, 191, 36, 1)',
        borderWidth: 0,
        borderRadius: 6,
        borderSkipped: false,
      },
    ],
  };

  const options = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          padding: 20,
          usePointStyle: true,
          pointStyle: 'rect',
          font: {
            size: 12,
            family: "'Inter', sans-serif",
          },
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        titleColor: '#1f2937',
        bodyColor: '#4b5563',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 12,
        mode: 'index' as const,
        intersect: false,
        titleFont: {
          size: 14,
          weight: 'bold' as const,
        },
        callbacks: {
          label: function(context: TooltipItem<'bar'>) {
            const label = context.dataset.label || '';
            const value = context.raw as number;
            return `${label}: ${value} fis`;
          },
        },
      },
    },
    scales: {
      x: {
        stacked: true,
        beginAtZero: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          font: {
            size: 11,
            family: "'Inter', sans-serif",
          },
          stepSize: 1,
        },
        title: {
          display: true,
          text: 'Fis Sayisi',
          font: {
            size: 12,
            family: "'Inter', sans-serif",
            weight: 'normal' as const,
          },
          color: '#6b7280',
        },
      },
      y: {
        stacked: true,
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 12,
            family: "'Inter', sans-serif",
            weight: 'bold' as const,
          },
        },
      },
    },
  };

  const chartHeight = Math.max(200, activeDepots.length * 40 + 80);

  return (
    <div className="card p-6 animate-fade-in">
      <div className="flex items-center gap-4 mb-6">
        <div className="stat-icon gradient-info">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Depo Fis Durumu</h3>
          <p className="text-sm text-gray-500">Depo bazinda tamamlanan / bekleyen fis sayilari</p>
        </div>
      </div>
      <div style={{ height: chartHeight }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}

export default function MultiDepotOverviewPage() {
  const fetchData = useCallback(() => apiService.getMultiDepotSummary(), []);

  const { data, isLoading, error, lastUpdated, refresh } = usePolling<MultiDepotSummary>({
    fetchFn: fetchData,
    interval: 30000,
    enabled: true,
  });

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Ozet hesaplari
  const totalDepots = data?.depots.length ?? 0;
  const activeDepots = data?.depots.filter(d => d.has_active_cycle).length ?? 0;
  const totalCompleted = data?.depots.reduce((sum, d) => sum + d.loadsheet_stats.completed, 0) ?? 0;
  const totalLoadsheets = data?.depots.reduce((sum, d) => sum + d.loadsheet_stats.total, 0) ?? 0;

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Depo Genel Gorunum</h1>
            <p className="text-gray-500 mt-1">Tum depolarin dongu ve fis durumu</p>
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
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <SummaryCard label="Toplam Depo" value={totalDepots} color="violet" />
              <SummaryCard label="Aktif Dongu" value={activeDepots} color="emerald" />
              <SummaryCard label="Tamamlanan / Toplam Fis" value={`${totalCompleted} / ${totalLoadsheets}`} color="amber" />
            </div>

            {/* Bar Chart */}
            <DepotBarChart depots={data.depots} />

            {/* Depot Cards Grid */}
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Depolar</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {data.depots.map(depot => (
                  <DepotCard key={depot.depot_code} depot={depot} />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
