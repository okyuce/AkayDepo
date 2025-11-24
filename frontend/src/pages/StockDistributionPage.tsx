/**
 * Stock Distribution Page
 * İstasyon bazlı ürün stok yönetimi
 */
import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import { apiService } from '../services/api';

interface Product {
  product_id: string;
  product_code: string;
  product_name: string;
  quantity_carton: number;
  quantity_pack: number;
  updated_at: string | null;
}

interface Station {
  id: string;
  name: string;
  active: boolean;
}

export default function StockDistributionPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('');
  const [stationName, setStationName] = useState('');
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // İstasyonları yükle
  useEffect(() => {
    apiService.listStations().then(setStations).catch(console.error);
  }, []);

  // İstasyon seçildiğinde stoklarını yükle
  useEffect(() => {
    if (!selectedStationId) {
      setProducts([]);
      return;
    }

    setLoading(true);
    apiService.getStationInventory(selectedStationId)
      .then(data => {
        setStationName(data.station_name);
        setProducts(data.products);
      })
      .catch(err => {
        console.error('Stok yükleme hatası:', err);
        showToast('Stok bilgileri yüklenemedi', 'error');
      })
      .finally(() => setLoading(false));
  }, [selectedStationId]);

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleQuantityChange = (productId: string, field: 'quantity_carton' | 'quantity_pack', value: string) => {
    const numValue = parseInt(value) || 0;
    setProducts(prev => prev.map(p =>
      p.product_id === productId ? { ...p, [field]: numValue } : p
    ));
  };

  const handleSave = async () => {
    if (!selectedStationId) return;

    setSaving(true);
    try {
      await apiService.updateStationInventory(
        selectedStationId,
        products.map(p => ({
          product_id: p.product_id,
          quantity_carton: p.quantity_carton,
          quantity_pack: p.quantity_pack
        }))
      );
      showToast('Stoklar başarıyla güncellendi!', 'success');
    } catch (err) {
      console.error('Kaydetme hatası:', err);
      showToast('Stoklar kaydedilemedi', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      {/* Toast */}
      {toast && (
        <div className={`fixed top-20 right-6 z-50 px-6 py-3 rounded-lg shadow-lg ${
          toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white font-medium transition-all`}>
          {toast.message}
        </div>
      )}

      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Stok Dağılımı</h1>

        {/* İstasyon Seçimi */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            İstasyon Seçin
          </label>
          <select
            value={selectedStationId}
            onChange={(e) => setSelectedStationId(e.target.value)}
            className="w-full md:w-96 px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">-- İstasyon Seçin --</option>
            {stations.map(s => (
              <option key={s.id} value={s.id}>
                {s.name} {!s.active && '(Pasif)'}
              </option>
            ))}
          </select>
        </div>

        {/* Stok Tablosu */}
        {selectedStationId && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">
                {stationName} - Ürün Stokları
              </h2>
              <button
                onClick={handleSave}
                disabled={saving || loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
              >
                {saving ? 'Kaydediliyor...' : 'Kaydet'}
              </button>
            </div>

            {loading ? (
              <div className="text-center py-8 text-gray-500">Yükleniyor...</div>
            ) : products.length === 0 ? (
              <div className="text-center py-8 text-gray-500">Henüz ürün yok</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ürün Kodu
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ürün Adı
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Karton
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Paket
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Son Güncelleme
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {products.map((product) => (
                      <tr key={product.product_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {product.product_code}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700">
                          {product.product_name}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <input
                            type="number"
                            min="0"
                            value={product.quantity_carton}
                            onChange={(e) => handleQuantityChange(product.product_id, 'quantity_carton', e.target.value)}
                            className="w-24 px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <input
                            type="number"
                            min="0"
                            value={product.quantity_pack}
                            onChange={(e) => handleQuantityChange(product.product_id, 'quantity_pack', e.target.value)}
                            className="w-24 px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {product.updated_at ? new Date(product.updated_at).toLocaleString('tr-TR') : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
