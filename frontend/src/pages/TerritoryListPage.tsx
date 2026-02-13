/**
 * Territory Tanımları Sayfası
 * Territory listesi görüntüleme ve yönetimi
 */
import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import Navbar from '../components/Navbar';

interface Territory {
  id: string;
  code: string;
  name: string;
  display_number: string;
  is_active: boolean;
  color: string | null;
  sort_order: number;
}

export default function TerritoryListPage() {
  const [territories, setTerritories] = useState<Territory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingTerritory, setEditingTerritory] = useState<Territory | null>(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    display_number: '',
    color: ''
  });
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    loadTerritories();
  }, [showInactive]);

  const loadTerritories = async () => {
    setIsLoading(true);
    try {
      const data = await apiService.getTerritories(showInactive);
      setTerritories(data);
    } catch (err) {
      console.error('Territory yükleme hatası:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleToggleActive = async (territory: Territory) => {
    try {
      await apiService.updateTerritory(territory.id, {
        is_active: !territory.is_active
      });
      loadTerritories();
      showToast('Territory durumu güncellendi', 'success');
    } catch (err) {
      console.error('Güncelleme hatası:', err);
      showToast('Territory güncellenemedi', 'error');
    }
  };

  const handleOpenModal = (territory?: Territory) => {
    if (territory) {
      setEditingTerritory(territory);
      setFormData({
        code: territory.code,
        name: territory.name,
        display_number: territory.display_number,
        color: territory.color || ''
      });
    } else {
      setEditingTerritory(null);
      setFormData({ code: '', name: '', display_number: '', color: '' });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingTerritory(null);
    setFormData({ code: '', name: '', display_number: '', color: '' });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.code || !formData.name || !formData.display_number) {
      showToast('Tüm alanları doldurun', 'error');
      return;
    }

    try {
      if (editingTerritory) {
        // Güncelleme
        await apiService.updateTerritory(editingTerritory.id, {
          code: formData.code,
          name: formData.name,
          display_number: formData.display_number,
          color: formData.color ? formData.color : undefined
        });
        showToast('Territory güncellendi', 'success');
      } else {
        // Yeni oluştur
        await apiService.createTerritory({
          code: formData.code,
          name: formData.name,
          display_number: formData.display_number,
          color: formData.color || undefined
        });
        showToast('Territory oluşturuldu', 'success');
      }
      handleCloseModal();
      loadTerritories();
    } catch (err: any) {
      console.error('Kaydetme hatası:', err);
      const errorMsg = typeof err?.response?.data?.detail === 'string' 
        ? err.response.data.detail 
        : 'Kaydetme hatası';
      showToast(errorMsg, 'error');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <Navbar />
      
      {/* Toast */}
      {toast && (
        <div className={`fixed top-20 right-6 z-50 px-6 py-3 rounded-lg shadow-lg ${
          toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white font-medium transition-all`}>
          {toast.message}
        </div>
      )}

      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Territory Tanımları</h1>

            <div className="flex items-center space-x-4">
              <button
                onClick={() => handleOpenModal()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-semibold"
              >
                + Yeni Territory
              </button>

              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={showInactive}
                  onChange={(e) => setShowInactive(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Pasif territory'leri göster</span>
              </label>
            </div>
          </div>

          {isLoading ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <p className="text-center text-gray-500 dark:text-gray-400">Yükleniyor...</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-600">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Görünüm
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      İsim
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Kod
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Durum
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      İşlemler
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-600">
                  {territories.map((territory) => (
                    <tr key={territory.id} className={territory.is_active ? '' : 'bg-gray-50 dark:bg-gray-700'}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300">
                          {territory.display_number}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{territory.name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500 dark:text-gray-400">{territory.code}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span
                          className={`inline-flex px-2 py-1 text-xs leading-5 font-semibold rounded-full ${
                            territory.is_active
                              ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300'
                              : 'bg-gray-100 dark:bg-gray-600 text-gray-800 dark:text-gray-300'
                          }`}
                        >
                          {territory.is_active ? 'Aktif' : 'Pasif'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium space-x-3">
                        <button
                          onClick={() => handleOpenModal(territory)}
                          className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300"
                        >
                          Düzenle
                        </button>
                        <button
                          onClick={() => handleToggleActive(territory)}
                          className={`${
                            territory.is_active
                              ? 'text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300'
                              : 'text-green-600 dark:text-green-400 hover:text-green-900 dark:hover:text-green-300'
                          }`}
                        >
                          {territory.is_active ? 'Pasif Yap' : 'Aktif Yap'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {territories.length === 0 && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  Gösterilecek territory yok
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
              {editingTerritory ? 'Territory Düzenle' : 'Yeni Territory'}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Kod *
                </label>
                <input
                  type="text"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="örn: TERR030702-Kadınlarpazarı"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  İsim *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="örn: Merkez"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Görünüm Numarası *
                </label>
                <input
                  type="text"
                  value={formData.display_number}
                  onChange={(e) => setFormData({ ...formData, display_number: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="örn: T28"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Renk (Opsiyonel)
                </label>
                <input
                  type="color"
                  value={formData.color || '#3B82F6'}
                  onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                  className="w-full h-10 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-4 py-2 bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-400 dark:hover:bg-gray-500"
                >
                  İptal
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-semibold"
                >
                  {editingTerritory ? 'Güncelle' : 'Oluştur'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
