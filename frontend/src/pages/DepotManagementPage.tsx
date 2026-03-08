/**
 * Depot Management Page
 * SuperAdmin - Depo CRUD ve başlatma
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { apiService } from '../services/api';

interface Depot {
  id: string;
  code: string;
  name: string;
  city: string;
  is_active: boolean;
  user_count: number;
  station_count: number;
}

export default function DepotManagementPage({ navbarOverride }: { navbarOverride?: React.ReactNode }) {
  const [depots, setDepots] = useState<Depot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Yeni depo formu
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [newCity, setNewCity] = useState('');

  // Başlatma dialog
  const [initDepotId, setInitDepotId] = useState<string | null>(null);
  const [workerCount, setWorkerCount] = useState(5);
  const [initLoading, setInitLoading] = useState(false);

  useEffect(() => {
    loadDepots();
  }, []);

  const loadDepots = async () => {
    try {
      setLoading(true);
      const data = await apiService.getDepots();
      setDepots(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Depolar yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDepot = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiService.createDepot({ code: newCode.toUpperCase(), name: newName, city: newCity });
      setShowCreateForm(false);
      setNewCode('');
      setNewName('');
      setNewCity('');
      setSuccess('Depo oluşturuldu');
      loadDepots();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Depo oluşturulamadı');
    }
  };

  const handleInitDepot = async () => {
    if (!initDepotId) return;
    try {
      setInitLoading(true);
      const result = await apiService.initDepot(initDepotId, workerCount);
      setInitDepotId(null);
      setSuccess(
        `Depo başlatıldı: Admin=${result.created.admin_user}, Tablet=${result.created.tablet_users.join(', ')}`
      );
      loadDepots();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Depo başlatılamadı');
    } finally {
      setInitLoading(false);
    }
  };

  const handleToggleActive = async (depot: Depot) => {
    try {
      await apiService.updateDepot(depot.id, { is_active: !depot.is_active });
      loadDepots();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Güncelleme başarısız');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {navbarOverride || <Navbar />}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center space-x-4">
            <Link to={navbarOverride ? '/' : '/superadmin'} className="text-blue-600 dark:text-blue-400 hover:underline text-sm">
              SuperAdmin
            </Link>
            <span className="text-gray-400">/</span>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Depo Yönetimi</h1>
          </div>
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
          >
            Yeni Depo
          </button>
        </div>

        {error && (
          <div className="bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded mb-4">
            {error}
            <button onClick={() => setError(null)} className="float-right font-bold">x</button>
          </div>
        )}

        {success && (
          <div className="bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300 px-4 py-3 rounded mb-4">
            {success}
            <button onClick={() => setSuccess(null)} className="float-right font-bold">x</button>
          </div>
        )}

        {/* Yeni Depo Formu */}
        {showCreateForm && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Yeni Depo Oluştur</h3>
            <form onSubmit={handleCreateDepot} className="flex space-x-4 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kod</label>
                <input
                  type="text"
                  value={newCode}
                  onChange={(e) => setNewCode(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 w-24"
                  placeholder="VAN"
                  required
                  maxLength={10}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ad</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 w-48"
                  placeholder="Van Deposu"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Şehir</label>
                <input
                  type="text"
                  value={newCity}
                  onChange={(e) => setNewCity(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 w-36"
                  placeholder="Van"
                  required
                />
              </div>
              <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 text-sm">
                Oluştur
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="bg-gray-400 text-white px-4 py-2 rounded-md hover:bg-gray-500 text-sm"
              >
                İptal
              </button>
            </form>
          </div>
        )}

        {/* Depo Başlatma Dialog */}
        {initDepotId && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
              <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Depo Başlat</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                Bu işlem admin kullanıcı, tablet kullanıcıları, istasyonlar ve AnaStok oluşturacaktır.
              </p>
              <p className="text-xs text-red-500 dark:text-red-400 mb-4">
                Mevcut kullanıcı ve istasyonlar silinip yeniden oluşturulacaktır!
              </p>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Depocu (Tablet) Sayısı
                </label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={workerCount}
                  onChange={(e) => setWorkerCount(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Her depocu için 1 tablet kullanıcısı ve 1 istasyon oluşturulur.
                </p>
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={handleInitDepot}
                  disabled={initLoading}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 text-sm"
                >
                  {initLoading ? 'Başlatılıyor...' : 'Başlat'}
                </button>
                <button
                  onClick={() => setInitDepotId(null)}
                  className="flex-1 bg-gray-400 text-white py-2 rounded-md hover:bg-gray-500 text-sm"
                >
                  İptal
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Depo Tablosu */}
        {loading ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">Yükleniyor...</div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Kod</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Ad</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Şehir</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Kullanıcı</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">İstasyon</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Durum</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">İşlem</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {depots.map((depot) => (
                  <tr key={depot.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-gray-100">{depot.code}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{depot.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{depot.city}</td>
                    <td className="px-4 py-3 text-sm text-center text-gray-900 dark:text-gray-100">{depot.user_count}</td>
                    <td className="px-4 py-3 text-sm text-center text-gray-900 dark:text-gray-100">{depot.station_count}</td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggleActive(depot)}
                        className={`text-xs px-2 py-1 rounded-full ${
                          depot.is_active
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        {depot.is_active ? 'Aktif' : 'Pasif'}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setInitDepotId(depot.id)}
                        className={`text-white text-xs px-3 py-1 rounded ${
                          depot.user_count === 0
                            ? 'bg-orange-500 hover:bg-orange-600'
                            : 'bg-gray-500 hover:bg-gray-600'
                        }`}
                      >
                        {depot.user_count === 0 ? 'Başlat' : 'Yeniden Başlat'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
