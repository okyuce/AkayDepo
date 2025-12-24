/**
 * Territory Assignment Page (Manual Mapping)
 * - Pool of territories on top
 * - Station columns below with drag & drop
 */
import { useEffect, useMemo, useState } from 'react';
import Navbar from '../components/Navbar';
import { apiService } from '../services/api';

interface Territory {
  id: string;
  code: string;
  name: string;
  display_number: string;
  is_active: boolean;
}

interface Station { id: string; name: string; active: boolean }

const STATION_COLORS = [
  '#E67E22', // orange
  '#3498DB', // blue
  '#F1C40F', // yellow
  '#2ECC71', // green
  '#9B59B6', // purple
  '#1ABC9C', // teal
  '#E74C3C', // red
];

export default function TerritoryAssignmentPage() {
  const [territories, setTerritories] = useState<Territory[]>([]);
  const [stations, setStations] = useState<Station[]>([]);
  const [autoPlanning, setAutoPlanning] = useState(true);
  const [assignments, setAssignments] = useState<Record<string, string | null>>({}); // territory_code -> station_id or null
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [, setShowAddStation] = useState(false);
  const [, setNewStationName] = useState('');
  const [hasActiveCycle, setHasActiveCycle] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'error' | 'success' } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const [territoryList, cfg, activeCycle] = await Promise.all([
          apiService.getTerritories(false),
          apiService.getAssignmentsConfig(),
          apiService.getActivecycle(),
        ]);
        setTerritories(territoryList);
        setStations(cfg.stations);
        setAutoPlanning(cfg.auto_planning_enabled);
        setHasActiveCycle(activeCycle.has_active_cycle && activeCycle.cycle?.has_plan);
        // build map
        const map: Record<string, string | null> = {};
        territoryList.forEach((t: Territory) => (map[t.code] = null));
        cfg.assignments.forEach((a) => { map[a.territory_code] = a.station_id; });
        setAssignments(map);
      } catch (e: any) {
        console.error('Yükleme hatası:', e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const poolTerritories = useMemo(() => territories.filter(t => !assignments[t.code]), [territories, assignments]);
  const byStation = useMemo(() => {
    const m: Record<string, Territory[]> = {};
    stations.forEach(s => m[s.id] = []);
    territories.forEach(t => {
      const sid = assignments[t.code];
      if (sid && m[sid]) m[sid].push(t);
    });
    return m;
  }, [territories, assignments, stations]);

  const onDragStart = (ev: React.DragEvent, code: string) => {
    ev.dataTransfer.setData('text/plain', code);
  };

  const onDropToStation = (ev: React.DragEvent, stationId: string) => {
    const code = ev.dataTransfer.getData('text/plain');
    if (!code) return;
    setAssignments(prev => ({ ...prev, [code]: stationId }));
  };
  const onDropToPool = (ev: React.DragEvent) => {
    const code = ev.dataTransfer.getData('text/plain');
    if (!code) return;
    setAssignments(prev => ({ ...prev, [code]: null }));
  };

  const handleSave = async () => {
    setSaving(true);
    
    // Manuel modda validasyon yap
    if (!autoPlanning) {
      const activeCodes = territories.filter(t => t.is_active).map(t => t.code);
      const unassigned = activeCodes.filter(code => !assignments[code]);
      if (unassigned.length > 0) {
        alert('Boşta (atanmamış) territory var. Lütfen tüm territory\'leri atayın.');
        setSaving(false);
        return;
      }
    }
    
    try {
      const payload = {
        auto_planning_enabled: autoPlanning,
        assignments: autoPlanning ? [] : Object.entries(assignments)
          .filter(([, sid]) => !!sid)
          .map(([territoryCode, sid]) => ({ territory_code: territoryCode, station_id: sid as string })),
      };
      await apiService.saveAssignmentsConfig(payload);
      alert(autoPlanning ? 'Otomatik planlama aktif edildi' : 'Manuel atamalar kaydedildi');
    } catch (e: any) {
      if (e?.response?.data?.error === 'unassigned_territories') {
        alert('Boşta (atanmamış) territory var: ' + e.response.data.territories.join(', '));
      } else {
        alert('Kayıt hatası');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Tüm atamaları sıfırlamak istiyor musunuz?')) return;
    await apiService.resetAssignments();
    const map: Record<string, string | null> = {};
    territories.forEach(t => map[t.code] = null);
    setAssignments(map);
  };

  const handleAddStation = async () => {
    try {
      const newStation = await apiService.createStation();
      setStations(prev => [...prev, newStation]);
      setNewStationName('');
      setShowAddStation(false);
      
      // Başarı mesajı göster
      const message = newStation.tablet_user 
        ? `${newStation.name} oluşturuldu! Kullanıcı: ${newStation.tablet_user} (Şifre: tablet123)`
        : `${newStation.name} başarıyla oluşturuldu!`;
      setToast({ message, type: 'success' });
      setTimeout(() => setToast(null), 5000);
    } catch (e: any) {
      const errorMsg = e?.response?.data?.detail || 'İstasyon oluşturma hatası';
      setToast({ message: errorMsg, type: 'error' });
      setTimeout(() => setToast(null), 3000);
    }
  };

  const handleDeleteStation = async (stationId: string) => {
    if (!confirm('Bu istasyonu silmek istediğinize emin misiniz? İlgili tüm atamalar da silinecektir.')) return;
    try {
      await apiService.deleteStation(stationId);
      setStations(prev => prev.filter(s => s.id !== stationId));
      // Bu istasyonun atamalarını temizle
      setAssignments(prev => {
        const n = { ...prev } as Record<string, string | null>;
        Object.entries(n).forEach(([code, sid]) => { if (sid === stationId) n[code] = null; });
        return n;
      });
    } catch (e: any) {
      alert('İstasyon silme hatası');
    }
  };

  const toggleStationActive = async (s: Station) => {
    const updated = await apiService.updateStation(s.id, { active: !s.active });
    setStations(prev => prev.map(p => p.id === s.id ? updated : p));
    if (!updated.active) {
      // drop its territories to pool locally
      setAssignments(prev => {
        const n = { ...prev } as Record<string, string | null>;
        Object.entries(n).forEach(([code, sid]) => { if (sid === s.id) n[code] = null; });
        return n;
      });
    }
  };

  if (loading) return (<div className="min-h-screen bg-gray-100"><Navbar /><div className="p-6">Yükleniyor...</div></div>);

  return (
    <div className="min-h-screen bg-gray-100" onDragOver={(e) => e.preventDefault()}>
      <Navbar />
      
      {/* Toast Notification */}
      {toast && (
        <div className="fixed top-20 right-6 z-50 transition-all duration-300 ease-in-out">
          <div className={`rounded-lg shadow-lg p-4 max-w-md ${
            toast.type === 'error' ? 'bg-red-50 border-2 border-red-500' : 'bg-green-50 border-2 border-green-500'
          }`}>
            <div className="flex items-start">
              <div className="flex-1">
                <p className={`text-sm font-medium ${
                  toast.type === 'error' ? 'text-red-800' : 'text-green-800'
                }`}>
                  {toast.message}
                </p>
              </div>
              <button
                onClick={() => setToast(null)}
                className={`ml-3 flex-shrink-0 ${
                  toast.type === 'error' ? 'text-red-500 hover:text-red-700' : 'text-green-500 hover:text-green-700'
                }`}
              >
                <span className="text-xl">×</span>
              </button>
            </div>
          </div>
        </div>
      )}
      
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">Territory Atama</h1>
          <div className="flex items-center space-x-4">
            {/* Toggle Switch for Auto/Manual Mode */}
            <div className="flex items-center space-x-3">
              <span className={`text-sm font-medium ${!autoPlanning ? 'text-blue-600' : 'text-gray-500'}`}>Manuel</span>
              <button
                onClick={() => {
                  // Aktif döngü varsa her iki yönde de mod değiştirmeyi engelle
                  if (hasActiveCycle) {
                    const message = autoPlanning 
                      ? '⚠️ Aktif döngü var! Manuel moda geçmek için önce "Yeni Döngü Başlat" butonuna tıklayın.'
                      : '⚠️ Aktif döngü var! Otomatik moda geçmek için önce "Yeni Döngü Başlat" butonuna tıklayın.';
                    setToast({ message, type: 'error' });
                    setTimeout(() => setToast(null), 5000);
                    return;
                  }
                  setAutoPlanning(!autoPlanning);
                }}
                disabled={hasActiveCycle}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                  hasActiveCycle ? 'bg-gray-400 cursor-not-allowed' : (autoPlanning ? 'bg-blue-600' : 'bg-gray-300')
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    autoPlanning ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <span className={`text-sm font-medium ${autoPlanning ? 'text-blue-600' : 'text-gray-500'}`}>Otomatik</span>
            </div>
            <button
              disabled={saving}
              onClick={handleSave}
              className="px-4 py-2 rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >Kaydet</button>
            <button onClick={handleReset} disabled={autoPlanning} className={`px-4 py-2 rounded-md text-white ${autoPlanning ? 'bg-gray-400 cursor-not-allowed' : 'bg-red-500 hover:bg-red-600'}`}>Sıfırla</button>
          </div>
        </div>

        {/* Info Message */}
        {autoPlanning && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p className="text-blue-800 text-sm">
              <strong>Otomatik Mod:</strong> İstasyon atamaları devre dışı. Plan oluşturulduğunda sistem otomatik olarak territory\'leri istasyonlara dağıtacak.
            </p>
          </div>
        )}

        {/* Pool */}
        <div className={`bg-white rounded-lg shadow p-4 mb-6 ${autoPlanning ? 'opacity-50' : ''}`} onDrop={autoPlanning ? undefined : onDropToPool}>
          <h2 className="font-semibold mb-3">Territory</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {poolTerritories.map(t => (
              <div key={t.code}
                   draggable={!autoPlanning}
                   onDragStart={(e) => onDragStart(e, t.code)}
                   className="px-3 py-1 rounded border text-sm bg-gray-100 cursor-move text-gray-800">
                {t.display_number} {t.name}
              </div>
            ))}
            {poolTerritories.length === 0 && (
              <div className="text-gray-500 text-sm">Havuz boş</div>
            )}
          </div>
        </div>

        {/* Add Station Button */}
        {!autoPlanning && (
          <div className="mb-4">
            <button
              onClick={handleAddStation}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center space-x-2"
            >
              <span>+ Yeni İstasyon Ekle</span>
              <span className="text-xs text-green-100">(Otomatik isimlendirilir)</span>
            </button>
          </div>
        )}

        {/* Stations */}
        <div className="space-y-4">
          {stations.map((s, idx) => (
            <div key={s.id} className="bg-white rounded-lg shadow">
              <div className="flex items-center justify-between px-4 py-2 rounded-t" style={{ backgroundColor: STATION_COLORS[idx % STATION_COLORS.length], color: '#fff' }}>
                <div className="font-bold">{s.name}</div>
                <div className="flex items-center space-x-3">
                  <label className="flex items-center space-x-2 text-sm">
                    <input type="checkbox" checked={s.active} onChange={() => toggleStationActive(s)} disabled={autoPlanning} />
                    <span>Aktif</span>
                  </label>
                  {!autoPlanning && (
                    <button
                      onClick={() => handleDeleteStation(s.id)}
                      className="px-2 py-1 bg-red-600 hover:bg-red-700 rounded text-xs font-semibold"
                      title="İstasyonu Sil"
                    >
                      × Sil
                    </button>
                  )}
                </div>
              </div>
              <div className="p-4 min-h-[64px]" onDrop={(e) => !autoPlanning && s.active ? onDropToStation(e, s.id) : undefined} onDragOver={(e) => e.preventDefault()}>
                <div className="flex flex-wrap gap-3">
                  {byStation[s.id]?.map(t => (
                    <div key={t.code}
                         draggable={!autoPlanning}
                         onDragStart={(e) => onDragStart(e, t.code)}
                         className="px-3 py-1 rounded border text-sm cursor-move"
                         style={{ backgroundColor: STATION_COLORS[idx % STATION_COLORS.length] + '33', borderColor: STATION_COLORS[idx % STATION_COLORS.length], color: '#333' }}
                    >
                      {t.display_number} {t.name}
                    </div>
                  ))}
                  {(!byStation[s.id] || byStation[s.id].length === 0) && (
                    <div className="text-gray-400 text-sm">Sürükleyip bırakın…</div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}