/**
 * Tablet Page
 * İstasyon tablet görünümü - Fişleri göster ve tamamla
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { apiService } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

interface Loadsheet {
  id: string;
  package_number: string;
  dealer_code: string;
  dealer_name: string;
  total_carton: number;
  total_pack: number;
  status: string;
  is_revision: boolean;
}

interface Territory {
  territory_code: string;
  display_number: string;
  name: string;
  total_carton: number;
  completed_carton: number;
  progress_percent: number;
  status: string;
  loadsheets: Loadsheet[];
}

export default function TabletPage() {
  const { stationId } = useParams<{ stationId: string }>();
  const [territories, setTerritories] = useState<Territory[]>([]);
  const [totalCarton, setTotalCarton] = useState(0);
  const [completedCarton, setCompletedCarton] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [selectedLoadsheet, setSelectedLoadsheet] = useState<string | null>(null);
  const [loadsheetDetail, setLoadsheetDetail] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Verileri yükle
  const loadData = useCallback(async () => {
    if (!stationId) return;

    try {
      const data = await apiService.getStationLoadsheets(stationId);
      setTerritories(data.territories || []);
      setTotalCarton(data.total_carton || 0);
      setCompletedCarton(data.completed_carton || 0);
      setProgressPercent(data.progress_percent || 0);
    } catch (error) {
      console.error('Veri yükleme hatası:', error);
    }
  }, [stationId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // WebSocket dinle
  useWebSocket(`/ws/station/${stationId}`, (message) => {
    if (message.type === 'loadsheet_completed') {
      loadData(); // Fiş tamamlandığında verileri yenile
    }
  });

  // Fiş detayını yükle
  const loadLoadsheetDetail = async (loadsheetId: string) => {
    try {
      const detail = await apiService.getLoadsheetDetail(loadsheetId);
      setLoadsheetDetail(detail);
      setSelectedLoadsheet(loadsheetId);
    } catch (error) {
      console.error('Fiş detay yükleme hatası:', error);
    }
  };

  // Fişi tamamla
  const completeLoadsheet = async (loadsheetId: string) => {
    setIsLoading(true);
    try {
      await apiService.completeLoadsheet(loadsheetId);

      // Anında UI güncelle: tamamlanan fişi alta indir
      setTerritories((prev) => prev.map((t) => ({
        ...t,
        loadsheets: [...t.loadsheets]
          .map((ls) => ls.id === loadsheetId ? { ...ls, status: 'loaded', completed_at: new Date().toISOString() } : ls)
          .sort((a, b) => {
            const aDone = !!(a as any).completed_at || a.status === 'loaded' || a.status === 'cancelled';
            const bDone = !!(b as any).completed_at || b.status === 'loaded' || b.status === 'cancelled';
            return Number(aDone) - Number(bDone);
          })
      })));

      setSelectedLoadsheet(null);
      setLoadsheetDetail(null);
      await loadData();
    } catch (error) {
      console.error('Fiş tamamlama hatası:', error);
      alert('Fiş tamamlama başarısız!');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4">
        <h1 className="text-2xl font-bold">İstasyon {stationId?.slice(0, 8)}</h1>
        <div className="mt-2 flex items-center space-x-6">
          <div>
            <span className="text-sm opacity-80">Toplam:</span>
            <span className="ml-2 font-semibold">{totalCarton} karton</span>
          </div>
          <div>
            <span className="text-sm opacity-80">Tamamlanan:</span>
            <span className="ml-2 font-semibold">{completedCarton} karton</span>
          </div>
          <div>
            <span className="text-sm opacity-80">İlerleme:</span>
            <span className="ml-2 font-semibold">%{progressPercent}</span>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mt-3 bg-blue-400 rounded-full h-3">
          <div
            className="bg-green-400 h-3 rounded-full transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Territory List */}
      <div className="p-4">
        {territories.map((territory) => (
          <div key={territory.territory_code} className="mb-4 bg-white rounded-lg shadow">
            {/* Territory Header */}
            <div className="bg-gray-50 p-3 border-b flex justify-between items-center">
              <div>
                <h2 className="font-bold text-lg">
                  {territory.display_number} - {territory.name}
                </h2>
                <p className="text-sm text-gray-600">{territory.territory_code}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">
                  {territory.completed_carton} / {territory.total_carton} karton
                </p>
                <p className="text-lg font-semibold text-blue-600">
                  %{territory.progress_percent}
                </p>
              </div>
            </div>

            {/* Loadsheets */}
            <div className="divide-y">
              {[...territory.loadsheets]
                .sort((a, b) => {
                  const aDone = !!(a as any).completed_at || a.status === 'loaded' || a.status === 'cancelled';
                  const bDone = !!(b as any).completed_at || b.status === 'loaded' || b.status === 'cancelled';
                  return Number(aDone) - Number(bDone);
                })
                .map((loadsheet) => (
                <button
                  key={loadsheet.id}
                  onClick={() => loadLoadsheetDetail(loadsheet.id)}
                  className={`w-full p-4 text-left hover:bg-gray-50 transition ${
                    loadsheet.status === 'loaded' ? 'bg-green-50' : ''
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <div className="flex-1">
                      <p className="font-semibold text-lg">
                        {loadsheet.package_number}
                        {loadsheet.is_revision && (
                          <span className="ml-2 text-xs bg-orange-500 text-white px-2 py-1 rounded">
                            REVİZYON
                          </span>
                        )}
                      </p>
                      <p className="text-sm text-gray-600">
                        {loadsheet.dealer_code} - {loadsheet.dealer_name}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="flex items-baseline gap-2 justify-end">
                        <p className="text-xl font-bold">{loadsheet.total_carton} krt</p>
                        <p className="text-lg font-semibold text-gray-600">{loadsheet.total_pack} pkt</p>
                      </div>
                      {loadsheet.status === 'loaded' ? (
                        <span className="text-green-600 font-semibold">✓ Tamamlandı</span>
                      ) : (
                        <span className="text-gray-500">Bekliyor</span>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Loadsheet Detail Modal */}
      {selectedLoadsheet && loadsheetDetail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-blue-600 text-white p-4 flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">{loadsheetDetail.package_number}</h2>
                <p className="text-sm opacity-90">
                  {loadsheetDetail.dealer.code} - {loadsheetDetail.dealer.name}
                </p>
              </div>
              <button
                onClick={() => setSelectedLoadsheet(null)}
                className="text-2xl font-bold hover:bg-blue-700 px-3 py-1 rounded"
              >
                ×
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6">
              {/* Territory Info */}
              <div className="mb-4 p-3 bg-gray-50 rounded">
                <p className="text-sm text-gray-600">Territory</p>
                <p className="font-semibold">
                  {loadsheetDetail.territory.display_number} - {loadsheetDetail.territory.name}
                </p>
              </div>

              {/* Revision Notice */}
              {loadsheetDetail.is_revision && loadsheetDetail.changes && (
                <div className="mb-4 p-3 bg-orange-100 border border-orange-300 rounded">
                  <p className="font-semibold text-orange-800 mb-2">⚠ REVİZYON FİŞİ</p>
                  <div className="space-y-1">
                    {loadsheetDetail.changes.map((change: any, idx: number) => (
                      <p key={idx} className="text-sm">
                        {change.product_code}: {change.qty_change_carton > 0 ? '+' : ''}
                        {change.qty_change_carton} karton
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {/* Products */}
              <h3 className="font-semibold mb-3 text-lg">Ürünler</h3>
              <div className="space-y-2 mb-6">
                {loadsheetDetail.lines.map((line: any, idx: number) => (
                  <div key={idx} className="flex justify-between p-3 bg-gray-50 rounded">
                    <div>
                      <p className="font-medium">{line.product_code}</p>
                      <p className="text-sm text-gray-600">{line.product_name}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold relative inline-block">
                        {line.qty_carton} karton
                        {line.qty_pack > 0 && ` + ${line.qty_pack} paket`}
                        {/* Revizyon değişimi gösterimi */}
                        {line.qty_change_carton !== null && line.qty_change_carton !== 0 && (
                          <span
                            className={`absolute -top-2 -right-8 text-xs font-bold ${
                              line.qty_change_carton > 0 ? 'text-green-600' : 'text-red-600'
                            }`}
                          >
                            {line.qty_change_carton > 0 ? '+' : ''}{line.qty_change_carton}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Total */}
              <div className="border-t pt-4 mb-6">
                <div className="flex justify-between items-center text-xl">
                  <span className="font-semibold">TOPLAM</span>
                  <span className="font-bold text-blue-600">
                    {loadsheetDetail.total_carton} karton
                  </span>
                </div>
              </div>

              {/* Complete Button */}
              {loadsheetDetail.status !== 'loaded' && (
                <button
                  onClick={() => completeLoadsheet(loadsheetDetail.id)}
                  disabled={isLoading}
                  className="w-full bg-green-600 text-white py-4 rounded-lg font-bold text-lg hover:bg-green-700 disabled:bg-gray-400"
                >
                  {isLoading ? 'Tamamlanıyor...' : 'YÜKLEME TAMAMLANDI'}
                </button>
              )}

              {loadsheetDetail.status === 'loaded' && (
                <div className="bg-green-100 border border-green-400 text-green-700 p-4 rounded text-center font-semibold">
                  ✓ Bu fiş tamamlandı
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
