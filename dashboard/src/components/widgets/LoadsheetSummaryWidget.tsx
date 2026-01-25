interface LoadsheetStats {
  total: number;
  completed: number;
  pending: number;
  cancelled: number;
  completion_percentage: number;
}

interface Props {
  stats: LoadsheetStats;
}

export default function LoadsheetSummaryWidget({ stats }: Props) {
  const { total, completed, pending, cancelled, completion_percentage } = stats;

  return (
    <div className="card p-6 animate-fade-in">
      <div className="flex items-center gap-4 mb-6">
        <div className="stat-icon gradient-cyan">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Fis Durumu</h3>
          <p className="text-sm text-gray-500">Toplam {total} fis</p>
        </div>
      </div>

      {total === 0 ? (
        <div className="text-center py-8">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <p className="text-gray-600 font-medium">Henuz fis olusturulmamis</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Progress Circle */}
          <div className="flex items-center gap-6">
            <div className="relative w-28 h-28">
              <svg className="w-28 h-28 transform -rotate-90">
                <circle
                  cx="56"
                  cy="56"
                  r="48"
                  stroke="#e5e7eb"
                  strokeWidth="12"
                  fill="none"
                />
                <circle
                  cx="56"
                  cy="56"
                  r="48"
                  stroke="url(#progressGradient)"
                  strokeWidth="12"
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray={`${completion_percentage * 3.02} 302`}
                  className="transition-all duration-1000"
                />
                <defs>
                  <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#7c3aed" />
                    <stop offset="100%" stopColor="#06b6d4" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-2xl font-bold text-gray-800">%{completion_percentage}</span>
              </div>
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-500 mb-2">Tamamlanma Orani</p>
              <p className="text-3xl font-bold text-gray-800">{completed}<span className="text-lg text-gray-400">/{total}</span></p>
              <p className="text-sm text-gray-500 mt-1">fis tamamlandi</p>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gradient-to-br from-emerald-50 to-green-50 rounded-xl p-4 text-center">
              <div className="w-10 h-10 mx-auto mb-2 rounded-lg bg-emerald-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-2xl font-bold text-emerald-600">{completed}</p>
              <p className="text-xs text-emerald-600 font-medium">Tamamlandi</p>
            </div>

            <div className="bg-gradient-to-br from-amber-50 to-yellow-50 rounded-xl p-4 text-center">
              <div className="w-10 h-10 mx-auto mb-2 rounded-lg bg-amber-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-2xl font-bold text-amber-600">{pending}</p>
              <p className="text-xs text-amber-600 font-medium">Bekliyor</p>
            </div>

            <div className="bg-gradient-to-br from-red-50 to-rose-50 rounded-xl p-4 text-center">
              <div className="w-10 h-10 mx-auto mb-2 rounded-lg bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <p className="text-2xl font-bold text-red-600">{cancelled}</p>
              <p className="text-xs text-red-600 font-medium">Iptal</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
