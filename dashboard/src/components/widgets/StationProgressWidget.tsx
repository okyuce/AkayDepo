import { Link } from 'react-router-dom';

interface StationSummary {
  station_id: string;
  station_name: string;
  territory_count: number;
  total_carton: number;
  completed_carton: number;
  progress_percent: number;
}

interface Props {
  stations: StationSummary[];
}

const gradients = [
  'from-violet-500 to-purple-600',
  'from-cyan-500 to-blue-600',
  'from-emerald-500 to-green-600',
  'from-amber-500 to-orange-600',
  'from-rose-500 to-pink-600',
  'from-indigo-500 to-blue-600',
];

export default function StationProgressWidget({ stations }: Props) {
  if (stations.length === 0) {
    return (
      <div className="card p-6 animate-fade-in">
        <div className="flex items-center gap-4 mb-6">
          <div className="stat-icon gradient-emerald">
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800">İstasyonlar</h3>
            <p className="text-sm text-gray-500">İstasyon ilerleme durumu</p>
          </div>
        </div>
        <div className="text-center py-12">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <p className="text-gray-600 font-medium">Plan olusturulmamis</p>
          <p className="text-sm text-gray-400 mt-1">İstasyon ataması yapılmadı</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6 animate-fade-in">
      <div className="flex items-center gap-4 mb-6">
        <div className="stat-icon gradient-emerald">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">İstasyonlar</h3>
          <p className="text-sm text-gray-500">{stations.length} istasyon aktif</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {stations.map((station, index) => (
          <Link
            key={station.station_id}
            to={`/station/${station.station_id}`}
            className="group block"
          >
            <div className="relative overflow-hidden rounded-2xl bg-white border border-gray-100 p-5 transition-all duration-300 hover:shadow-lg hover:border-gray-200 hover:-translate-y-1">
              {/* Gradient Header */}
              <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${gradients[index % gradients.length]}`} />

              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradients[index % gradients.length]} flex items-center justify-center text-white font-bold text-sm shadow-lg`}>
                    {station.station_name.replace('İstasyon-', 'S').replace('AnaStok', 'AS')}
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 group-hover:text-violet-600 transition-colors">
                      {station.station_name}
                    </h4>
                    <p className="text-xs text-gray-500">{station.territory_count} bölge</p>
                  </div>
                </div>
                <div className={`text-lg font-bold ${
                  station.progress_percent >= 100 ? 'text-emerald-600' :
                  station.progress_percent >= 50 ? 'text-violet-600' :
                  'text-amber-600'
                }`}>
                  %{station.progress_percent}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mb-3">
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-gradient-to-r ${gradients[index % gradients.length]} progress-bar rounded-full`}
                    style={{ width: `${Math.min(station.progress_percent, 100)}%` }}
                  />
                </div>
              </div>

              {/* Stats */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-1 text-gray-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                  <span>{station.completed_carton.toLocaleString('tr-TR')} / {station.total_carton.toLocaleString('tr-TR')}</span>
                </div>
                <span className="text-xs text-gray-400">karton</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
