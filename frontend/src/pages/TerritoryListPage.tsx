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

  const handleToggleActive = async (territory: Territory) => {
    try {
      await apiService.updateTerritory(territory.id, {
        is_active: !territory.is_active
      });
      loadTerritories();
    } catch (err) {
      console.error('Güncelleme hatası:', err);
      alert('Territory güncellenemedi');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold">Territory Tanımları</h1>
            
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={(e) => setShowInactive(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-700">Pasif territory'leri göster</span>
            </label>
          </div>

          {isLoading ? (
            <div className="bg-white rounded-lg shadow-md p-6">
              <p className="text-center text-gray-500">Yükleniyor...</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Görünüm
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      İsim
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Kod
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Durum
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      İşlemler
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {territories.map((territory) => (
                    <tr key={territory.id} className={territory.is_active ? '' : 'bg-gray-50'}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                          {territory.display_number}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{territory.name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{territory.code}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span
                          className={`inline-flex px-2 py-1 text-xs leading-5 font-semibold rounded-full ${
                            territory.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {territory.is_active ? 'Aktif' : 'Pasif'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                        <button
                          onClick={() => handleToggleActive(territory)}
                          className={`${
                            territory.is_active
                              ? 'text-red-600 hover:text-red-900'
                              : 'text-green-600 hover:text-green-900'
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
                <div className="text-center py-8 text-gray-500">
                  Gösterilecek territory yok
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
