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
  const [isPlanLocked, setIsPlanLocked] = useState(false);
  const [imports, setImports] = useState<{id:string;batch_number:number;filename:string;file_size:number;uploaded_at:string;plan_date?:string;first_delivery_time?:string;last_delivery_time?:string}[]>([]);
  const [isPlanButtonDisabled, setIsPlanButtonDisabled] = useState(false); // Planlama butonu disable durumu
  const [needsPlanning, setNeedsPlanning] = useState(false); // Excel yüklendi, planlama bekleniyor
  const [toast, setToast] = useState<{message: string; type: 'success' | 'error'} | null>(null);
  const [isAutoPlanning, setIsAutoPlanning] = useState(true); // Otomatik planlama modu

  // Sayfa yüklenince son cycle ve planı kontrol et + auto planning kontrolü
  useEffect(() => {
    loadLatestCycle();
    // Auto planning modunu kontrol et
    apiService.getAssignmentsConfig().then(cfg => {
      setIsAutoPlanning(cfg.auto_planning_enabled);
    }).catch(() => {});
  }, []);

  // cycleId değiştiğinde import geçmişini çek
  useEffect(() => {
    if (!cycleId) { setImports([]); return; }
    apiService.getCycleImports(cycleId)
      .then(data => {
        console.log('Import geçmişi:', data);
        setImports(data);
      })
      .catch(err => {
        console.error('Import geçmişi yüklenemedi:', err);
        setImports([]);
      });
  }, [cycleId]);

  const loadLatestCycle = async () => {
    try {
      // Bugünkü aktif cycle'i getir
      const activeData = await apiService.getActivecycle();
      
      if (activeData.has_active_cycle && activeData.cycle) {
        const cycle = activeData.cycle;
        setCycleId(cycle.id);
        localStorage.setItem('latest_cycle_id', cycle.id);

        // İstasyon sayısı kilitliyse input'u kilitle
        if (typeof cycle.fixed_station_count === 'number' && cycle.fixed_station_count > 0) {
          setNumStations(cycle.fixed_station_count);
          setIsPlanLocked(true);
        }
        
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
              
              // Plan butonu disable durumunu kontrol et
              const planButtonStatus = localStorage.getItem('plan_button_disabled_' + cycle.id);
              if (planButtonStatus === 'true') {
                setIsPlanButtonDisabled(true);
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
      // no-op
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
      // Yükleme geçmişini yenile
      try { const list = await apiService.getCycleImports(result.cycle_id); setImports(list); } catch {}
      
      // Yeni Excel yüklendi - planlama yapana kadar Excel yüklemeyi engelle
      setNeedsPlanning(true);
      setIsPlanButtonDisabled(false); // Planlama butonunu aktif et
      localStorage.removeItem('plan_button_disabled_' + result.cycle_id);
      
      setToast({ message: 'Excel başarıyla yüklendi! Şimdi planlama oluşturun.', type: 'success' });
      setTimeout(() => setToast(null), 3000);
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
      
      // Toast mesajı göster
      setToast({ message: errorMsg, type: 'error' });
      setTimeout(() => setToast(null), 3000);
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
      setImports([]);
      setNeedsPlanning(false);
      setIsPlanButtonDisabled(false); // Plan butonunu tekrar aktif et
      
      // LocalStorage temizle
      localStorage.removeItem('latest_cycle_id');
      if (cycleId) {
        localStorage.removeItem('plan_locked_' + cycleId);
        localStorage.removeItem('plan_button_disabled_' + cycleId);
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
      
      // İlk plan sonrası kilitle - sadece henüz kilitli değilse
      if (!isPlanLocked) {
        setIsPlanLocked(true);
        localStorage.setItem('plan_locked_' + cycleId, 'true');
      }
      
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
      
      // Plan oluşturuldu - Excel yüklemeye izin ver, planlama butonunu disable et
      setNeedsPlanning(false);
      setIsPlanButtonDisabled(true);
      localStorage.setItem('plan_button_disabled_' + cycleId, 'true');
      
      setToast({ message: 'Planlama başarıyla oluşturuldu!', type: 'success' });
      setTimeout(() => setToast(null), 3000);
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
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <Navbar />
      
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg ${
          toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white font-medium animate-fade-in`}>
          {toast.message}
        </div>
      )}
      
      <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Excel Yükleme ve Planlama</h1>
          
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
          <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-4 mb-6">
            <h2 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">ℹ️ Mevcut Döngü</h2>
            <p className="text-sm text-blue-800 dark:text-blue-300">
              Bugünkü aktif döngü yüklü.
              {planResult ? ' Plan oluşturulmuş ve görüntüleniyor.' : ' Planlama oluşturmak için aşağıdaki butona basın.'}
            </p>
            <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
              Yeni döngü başlatmak için sağ üstteki "Yeni Döngü Başlat" butonuna basın.
            </p>
          </div>
        )}

        {/* Excel Upload + Yükleme Geçmişi */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">1. Excel Dosyası Yükle</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Upload Form */}
            <div className="md:col-span-2 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Excel Dosyası Seç (PMI ISMS)
                </label>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileChange}
                  disabled={needsPlanning}
                  className={`block w-full text-sm text-gray-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-md file:border-0
                    file:text-sm file:font-semibold
                    file:bg-blue-50 file:text-blue-700
                    hover:file:bg-blue-100
                    ${needsPlanning ? 'opacity-50 cursor-not-allowed' : ''}`}
                />
                {selectedFile && (
                  <p className="mt-2 text-sm text-gray-600">
                    Seçili: {selectedFile.name}
                  </p>
                )}
              </div>

              <button
                onClick={handleUpload}
                disabled={!selectedFile || isUploading || needsPlanning}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
              >
                {isUploading ? 'Yüklüyor...' : 'Excel Yükle'}
              </button>

              {cycleId && (
                <div className="bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300 px-4 py-3 rounded">
                  ✓ Döngü oluşturuldu: {cycleId}
                </div>
              )}
            </div>

            {/* Import History */}
            <div>
              <h3 className="font-semibold mb-2 text-gray-900 dark:text-gray-100">Yükleme Geçmişi</h3>
              <div className="max-h-56 overflow-y-auto border dark:border-gray-600 rounded">
                {imports.length === 0 ? (
                  <div className="p-3 text-sm text-gray-500 dark:text-gray-400">Henüz yükleme yok</div>
                ) : (
                  <ul className="divide-y dark:divide-gray-600">
                    {imports.map((it) => {
                      // Tarih-saat formatı oluştur
                      let dateInfo = '';
                      if (it.plan_date) {
                        const date = new Date(it.plan_date);
                        const dateStr = date.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' });
                        
                        if (it.first_delivery_time && it.last_delivery_time) {
                          dateInfo = `${dateStr} ${it.first_delivery_time} - ${it.last_delivery_time}`;
                        } else {
                          dateInfo = dateStr;
                        }
                      }
                      
                      return (
                        <li key={it.id} className="p-3 text-sm">
                          <p className="font-medium truncate text-gray-900 dark:text-gray-100" title={it.filename}>{it.filename}</p>
                          {dateInfo && (
                            <p className="text-gray-600 dark:text-gray-400 text-xs mt-1">{dateInfo}</p>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Create Plan */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">2. Planlama Oluştur</h2>

          <div className="space-y-4">
            {/* İstasyon sayısı sadece otomatik modda görünsün */}
            {isAutoPlanning ? (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  İstasyon Sayısı
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={numStations}
                  onChange={(e) => setNumStations(parseInt(e.target.value))}
                  disabled={isPlanLocked}
                  className={`w-32 px-3 py-2 border rounded-md ${isPlanLocked ? 'bg-gray-100 dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400' : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100'}`}
                />
                {isPlanLocked && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">🔒 İstasyon sayısı ilk plandan sonra kilitlendi. Yeni Excel yükleyip Planlama'yı tekrar çalıştırabilirsiniz.</p>
                )}
              </div>
            ) : (
              <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-3">
                <p className="text-sm text-blue-800 dark:text-blue-300">
                  <strong>📌 Manuel Mod:</strong> İstasyon atamaları "Territory Atama" sayfasından yönetiliyor.
                </p>
              </div>
            )}

            <button
              onClick={handleCreatePlan}
              disabled={!cycleId || isPlanning || isPlanButtonDisabled}
              className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-400"
            >
              {isPlanning ? 'Oluşturuluyor...' : isPlanLocked ? 'Planlamayı Güncelle' : planResult ? 'Yeni Plan Oluştur' : 'Planlama Oluştur'}
            </button>
            
            {isPlanButtonDisabled && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                ℹ️ Plan oluşturuldu. Yeni Excel yükledikten sonra planlamayı tekrar çalıştırabilirsiniz.
              </p>
            )}

            {isPlanLocked && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                🔒 İstasyon sayısı kilitli. Yeni Excel yükledikten sonra bu butonla planlamayı tekrar çalıştırabilirsiniz.
              </p>
            )}

            {!isPlanLocked && planResult && (
              <p className="text-sm text-blue-600 dark:text-blue-400 mt-2">
                ℹ️ İstasyon sayısını belirledikten sonra tekrar değiştirilebilir. İlk planlamadan sonra kilitlenecektir.
              </p>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Plan Result */}
        {planResult && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Planlama Sonucu</h2>
              {/* Kilitleme butonu kaldırıldı - revizyon sistemi için */}
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Toplam Territory</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{planResult.total_territories}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">İstasyon Sayısı</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{planResult.num_stations}</p>
                </div>
              </div>

              {planResult.unbalanced_territories?.length > 0 && (
                <div className="bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-400 dark:border-yellow-700 text-yellow-700 dark:text-yellow-300 px-4 py-3 rounded">
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
                <h3 className="font-semibold mb-2 text-gray-900 dark:text-gray-100">İstasyon Atamaları:</h3>
                <div className="space-y-2">
                  {planResult.assignments?.map((assignment: any) => (
                    <div key={assignment.station_name} className="border dark:border-gray-600 rounded p-3">
                      <p className="font-medium text-gray-900 dark:text-gray-100">{assignment.station_name}</p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
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
