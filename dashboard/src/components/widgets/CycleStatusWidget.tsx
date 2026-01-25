interface CycleInfo {
  id: string;
  cycle_no: number;
  run_time: string;
  plan_date: string;
  status: string;
  last_completion_time: string | null;
}

interface Props {
  cycle: CycleInfo | null;
  lastImport: {
    filename: string;
    uploaded_at: string;
    batch_number: number;
  } | null;
}

export default function CycleStatusWidget({ cycle, lastImport }: Props) {
  if (!cycle) {
    return (
      <div className="card p-6 animate-fade-in">
        <div className="flex items-center gap-4 mb-6">
          <div className="stat-icon gradient-purple">
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800">Aktif Döngü</h3>
            <p className="text-sm text-gray-500">Döngü bilgileri</p>
          </div>
        </div>
        <div className="text-center py-8">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
          </div>
          <p className="text-gray-600 font-medium">Aktif döngü bulunamadı</p>
          <p className="text-sm text-gray-400 mt-1">Excel yüklenerek yeni döngü başlatılabilir</p>
        </div>
      </div>
    );
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('tr-TR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('tr-TR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="card p-6 animate-fade-in">
      <div className="flex items-center gap-4 mb-6">
        <div className="stat-icon gradient-purple">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Aktif Döngü</h3>
          <p className="text-sm text-gray-500">Döngü #{cycle.cycle_no}</p>
        </div>
        <div className="ml-auto">
          <span className={`px-4 py-1.5 rounded-full text-sm font-medium ${
            cycle.status === 'active'
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-gray-100 text-gray-700'
          }`}>
            {cycle.status === 'active' ? 'Aktif' : cycle.status}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-xl p-4">
          <p className="text-xs text-violet-600 font-medium uppercase tracking-wide mb-1">Plan Tarihi</p>
          <p className="text-lg font-bold text-gray-800">{formatDate(cycle.plan_date)}</p>
        </div>
        <div className="bg-gradient-to-br from-cyan-50 to-blue-50 rounded-xl p-4">
          <p className="text-xs text-cyan-600 font-medium uppercase tracking-wide mb-1">Son Tamamlanan Yükleme Fiş Saati</p>
          <p className="text-lg font-bold text-gray-800">
            {cycle.last_completion_time ? formatTime(cycle.last_completion_time) : '---'}
          </p>
        </div>
      </div>

      {lastImport && (
        <div className="border-t border-gray-100 pt-4">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-3">Son Excel Yükleme</p>
          <div className="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-800 truncate" title={lastImport.filename}>
                {lastImport.filename}
              </p>
              <p className="text-xs text-gray-500">
                Batch #{lastImport.batch_number} • {formatDateTime(lastImport.uploaded_at)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
