/**
 * Excel Upload Page
 * Excel dosyası yükleme ve planlama oluşturma sayfası
 */
import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import Navbar from '../components/Navbar';

export default function ExcelUploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [numStations, setNumStations] = useState(5);
  const [isUploading, setIsUploading] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [planResult, setPlanResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPlanLocked, setIsPlanLocked] = useState(false);

  // Sayfa yüklenince son cycle ve planı kontrol et
  useEffect(() => {
    loadLatestCycle();
  }, []);

  const loadLatestCycle = async () => {
    try {
      setIsLoading(true);
      
      // Bugünkü aktif cycle'i getir
      const activeData = await apiService.getActivecycle();
      
      if (activeData.has_active_cycle && activeData.cycle) {
        const cycle = activeData.cycle;
        setCycleId(cycle.id);
        localStorage.setItem('latest_cycle_id', cycle.id);
        
        // Plan var mı kontrol et
        if (cycle.has_plan) {
          try {
            const plan = await apiService.getPlan(cycle.id);
            if (plan && plan.stations) {
              // Plan formatını dönüştür
              const formattedPlan = {
                total_territories: plan.stations.reduce((sum: number, s: any) => 
                  sum + s.territories.length, 0),
                num_stations: plan.stations.length,
                assignments: plan.stations.map((s: any) => ({
                  station_name: s.station_name,
                  territories: s.territories.map((t: any) => 
                    `${t.display_number}-${t.territory_code.split('-')[1]}`),
                  total_carton: s.total_carton
                })),
                unbalanced_territories: []
              };
              setPlanResult(formattedPlan);
              
              // Plan lock durumunu kontrol et
              const lockStatus = localStorage.getItem('plan_locked_' + cycle.id);
              if (lockStatus === 'true') {
                setIsPlanLocked(true);
              }
            }
          } catch (err) {
            console.error('Plan yüklenemedi:', err);
          }
        }
      }
    } catch (err) {
      console.error('Aktif cycle yüklenemedi:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Lütfen bir dosya seçin');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const result = await apiService.importCycle(selectedFile);
      setCycleId(result.cycle_id);
      localStorage.setItem('latest_cycle_id', result.cycle_id);
      alert('Excel başarıyla yüklendi! Şimdi planlama oluşturun.');
    } catch (err: any) {
      console.error('Upload error:', err);
      let errorMsg = 'Yükleme başarısız';
      
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map((e: any) => e.msg || e).join(', ');
        } else {
          errorMsg = err.response.data.detail;
        }
      }
      
      setError(errorMsg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleNewCycle = async () => {
    if (!window.confirm('Yeni döngü başlatmak için mevcut bekleyen fişler iptal edilecek. Devam etmek istiyor musunuz?')) {
      return;
    }

    if (!cycleId) {
      // Cycle yoksa temizle
      setCycleId(null);
      setPlanResult(null);
      setIsPlanLocked(false);
      localStorage.removeItem('latest_cycle_id');
      // Tüm lock'ları temizle
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('plan_locked_')) {
          localStorage.removeItem(key);
        }
      });
      return;
    }

    try {
      // Pending fişleri iptal et
      await apiService.cancelPendingLoadsheets(cycleId);
      
      // State'i temizle
      setCycleId(null);
      setPlanResult(null);
      setSelectedFile(null);
      setIsPlanLocked(false);
      
      // LocalStorage temizle
      localStorage.removeItem('latest_cycle_id');
      if (cycleId) {
        localStorage.removeItem('plan_locked_' + cycleId);
      }
      
      alert('Yeni döngü başlatmaya hazır! Excel dosyası yükleyebilirsiniz.');
    } catch (err: any) {
      console.error('Yeni döngü başlatma hatası:', err);
      alert('Hata: ' + (err.response?.data?.detail || 'Bekleyen fişler iptal edilemedi'));
    }
  };

  const handleCreatePlan = async () => {
    if (!cycleId) {
      setError('Önce Excel dosyası yüklemelisiniz');
      return;
    }

    setIsPlanning(true);
    setError(null);

    try {
      const result = await apiService.createPlan(cycleId, numStations);
      console.log('Plan result:', result);
      
      // Backend'den gelen formatı frontend formatına dönüştür
      const formattedPlan = {
        total_territories: result.stations?.reduce((sum: number, s: any) => 
          sum + (s.territories?.length || 0), 0) || 0,
        num_stations: result.station_count || numStations,
        assignments: result.stations?.map((s: any) => ({
          station_name: s.station_name,
          territories: s.territories?.map((t: any) => 
            `${t.display_number}-${t.territory_code.split('-')[1]}`
          ) || [],
          total_carton: s.total_carton
        })) || [],
        unbalanced_territories: result.warnings?.filter((w: any) => 
          w.type === 'unbalanced_load'
        ).map((w: any) => ({
          territory_code: w.territory,
          total_carton: w.carton,
          suggested_stations: w.suggested_station_count
        })) || []
      };
      
      setPlanResult(formattedPlan);
      alert('Planlama başarıyla oluşturuldu!');
    } catch (err: any) {
      console.error('Planning error:', err);
      let errorMsg = 'Planlama oluşturma başarısız';
      
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map((e: any) => e.msg || e).join(', ');
        } else {
          errorMsg = err.response.data.detail;
        }
      }
      
      setError(errorMsg);
    } finally {
      setIsPlanning(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Excel Yükleme ve Planlama</h1>
          
          {cycleId && (
            <button
              onClick={handleNewCycle}
              className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 font-semibold"
            >
              Yeni Döngü Başlat
            </button>
          )}
        </div>

        {/* Mevcut Durum Bilgisi */}
        {cycleId && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h2 className="font-semibold text-blue-900 mb-2">ℹ️ Mevcut Döngü</h2>
            <p className="text-sm text-blue-800">
              Bugünkü aktif döngü yüklü. 
              {planResult ? ' Plan oluşturulmuş ve görüntüleniyor.' : ' Planlama oluşturmak için aşağıdaki butona basın.'}
            </p>
            <p className="text-xs text-blue-600 mt-1">
              Yeni döngü başlatmak için sağ üstteki "Yeni Döngü Başlat" butonuna basın.
            </p>
          </div>
        )}

        {/* Excel Upload */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">1. Excel Dosyası Yükle</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Excel Dosyası Seç (PMI ISMS)
              </label>
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100"
              />
              {selectedFile && (
                <p className="mt-2 text-sm text-gray-600">
                  Seçili: {selectedFile.name}
                </p>
              )}
            </div>

            <button
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
            >
              {isUploading ? 'Yükleniyor...' : 'Excel Yükle'}
            </button>

            {cycleId && (
              <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
                ✓ Döngü oluşturuldu: {cycleId}
              </div>
            )}
          </div>
        </div>

        {/* Create Plan */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">2. Planlama Oluştur</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                İstasyon Sayısı
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={numStations}
                onChange={(e) => setNumStations(parseInt(e.target.value))}
                className="w-32 px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <button
              onClick={handleCreatePlan}
              disabled={!cycleId || isPlanning || isPlanLocked}
              className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-400"
            >
              {isPlanning ? 'Oluşturuluyor...' : isPlanLocked ? 'Plan Kilitli' : planResult ? 'Yeni Plan Oluştur' : 'Planlama Oluştur'}
            </button>
            
            {isPlanLocked && (
              <p className="text-sm text-gray-600 mt-2">
                🔒 Plan kilitli. Yeni plan oluşturmak için "Yeni Döngü Başlat" butonuna basın.
              </p>
            )}
            
            {!isPlanLocked && planResult && (
              <p className="text-sm text-blue-600 mt-2">
                ℹ️ İstasyon sayısını değiştirip "Yeni Plan Oluştur" butonuna basarak farklı plan oluşturabilirsiniz.
              </p>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Plan Result */}
        {planResult && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Planlama Sonucu</h2>
              
              {!isPlanLocked ? (
                <button
                  onClick={async () => {
                    if (window.confirm('Planı kilitledikten sonra değiştiremezsiniz. Fişler oluşturulacak. Emin misiniz?')) {
                      try {
                        // Fişleri oluştur (loadsheet generation backend'de zaten yapılıyor)
                        setIsPlanLocked(true);
                        localStorage.setItem('plan_locked_' + cycleId, 'true');
                        alert('✅ Plan kilitlendi! Fişler oluşturuldu. Artık değiştirilemez.');
                      } catch (err) {
                        alert('Hata: Plan kilitlenemedi.');
                      }
                    }
                  }}
                  className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 text-sm font-semibold"
                >
                  Planı Onayla ve Kilitle
                </button>
              ) : (
                <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
                  🔒 Plan Kilitli
                </span>
              )}
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Toplam Territory</p>
                  <p className="text-2xl font-bold">{planResult.total_territories}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">İstasyon Sayısı</p>
                  <p className="text-2xl font-bold">{planResult.num_stations}</p>
                </div>
              </div>

              {planResult.unbalanced_territories?.length > 0 && (
                <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
                  <p className="font-semibold">⚠ Dengesiz Territory'ler:</p>
                  <ul className="list-disc list-inside mt-2">
                    {planResult.unbalanced_territories.map((t: any) => (
                      <li key={t.territory_code}>
                        {t.territory_code} - {t.total_carton} karton
                        {t.suggested_stations && ` (Önerilen: ${t.suggested_stations} istasyon)`}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-4">
                <h3 className="font-semibold mb-2">İstasyon Atamaları:</h3>
                <div className="space-y-2">
                  {planResult.assignments?.map((assignment: any) => (
                    <div key={assignment.station_name} className="border rounded p-3">
                      <p className="font-medium">{assignment.station_name}</p>
                      <p className="text-sm text-gray-600">
                        {assignment.territories.join(', ')} - 
                        <span className="font-semibold ml-1">{assignment.total_carton} karton</span>
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
