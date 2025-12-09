/**
 * Stock Distribution Page
 * İstasyon bazlı ürün stok yönetimi
 */
import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import { apiService } from '../services/api';
import * as XLSX from 'xlsx';

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

type StockMode = 'set' | 'add' | 'subtract';

export default function StockDistributionPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('');
  const [stationName, setStationName] = useState('');
  const [products, setProducts] = useState<Product[]>([]);
  const [originalProducts, setOriginalProducts] = useState<Product[]>([]);  // Orijinal stoklar
  const [mode, setMode] = useState<StockMode>('set');
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
        setOriginalProducts(data.products);  // Orijinal stokları sakla
      })
      .catch(err => {
        console.error('Stok yükleme hatası:', err);
        showToast('Stok bilgileri yüklenemedi', 'error');
      })
      .finally(() => setLoading(false));
  }, [selectedStationId]);

  // Mod değiştiğinde input'ları ayarla
  useEffect(() => {
    if (mode === 'set') {
      // Set modunda orijinal değerleri göster
      setProducts([...originalProducts]);
    } else {
      // Ekleme/Eksiltme modunda sıfırla
      setProducts(originalProducts.map(p => ({
        ...p,
        quantity_carton: 0,
        quantity_pack: 0
      })));
    }
  }, [mode, originalProducts]);

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
      // Mode'a göre hesaplama yap
      const updatedProducts = products.map(p => {
        const original = originalProducts.find(op => op.product_id === p.product_id);
        if (!original) return p;

        let finalCarton = p.quantity_carton;
        let finalPack = p.quantity_pack;

        if (mode === 'add') {
          // Ekleme: orijinal + girilen
          finalCarton = original.quantity_carton + p.quantity_carton;
          finalPack = original.quantity_pack + p.quantity_pack;
        } else if (mode === 'subtract') {
          // Eksiltme: orijinal - girilen
          finalCarton = original.quantity_carton - p.quantity_carton;
          finalPack = original.quantity_pack - p.quantity_pack;
        }
        // mode === 'set' ise zaten p.quantity_carton ve p.quantity_pack kullanılır

        return {
          product_id: p.product_id,
          quantity_carton: finalCarton,
          quantity_pack: finalPack
        };
      });

      await apiService.updateStationInventory(selectedStationId, updatedProducts);
      showToast('Stoklar başarıyla güncellendi!', 'success');
      
      // Sayfayı yenile
      const data = await apiService.getStationInventory(selectedStationId);
      setProducts(data.products);
      setOriginalProducts(data.products);
      
      // Normal moda dön
      setMode('set');
    } catch (err) {
      console.error('Kaydetme hatası:', err);
      showToast('Stoklar kaydedilemedi', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    // Hiçbir şey yapmadan normal moda dön
    setMode('set');
  };

  const handleExportExcel = () => {
    if (!selectedStationId || products.length === 0) {
      showToast('Aktif istasyon ya da ürün yok', 'error');
      return;
    }

    const rows = products.map((p) => ({
      'Ürün Kodu': p.product_code,
      'Ürün Adı': p.product_name,
      'Karton': p.quantity_carton,
      'Paket': p.quantity_pack,
      'Toplam (Krt)': Number((p.quantity_carton + (p.quantity_pack / 10)).toFixed(1)),
      'Son Güncelleme': p.updated_at ? new Date(p.updated_at).toLocaleString('tr-TR') : ''
    }));

    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'StokDagilimi');

    const now = new Date();
    const pad = (n: number) => n.toString().padStart(2, '0');
    const ts = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}`;
    const safeStation = stationName.replace(/[^\w\-]+/g, '_');
    const filename = `StokDagilimi_${safeStation}_${ts}.xlsx`;

    XLSX.writeFile(wb, filename);
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
              <div className="flex space-x-3">
                <button
                  onClick={handleExportExcel}
                  disabled={!selectedStationId || loading}
                  className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 font-semibold"
                >
                  Excel İndir
                </button>
                {mode !== 'set' && (
                  <button
                    onClick={handleCancel}
                    disabled={saving || loading}
                    className="px-6 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 disabled:bg-gray-400 font-semibold"
                  >
                    İptal
                  </button>
                )}
                <button
                  onClick={handleSave}
                  disabled={saving || loading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
                >
                  {saving ? 'Kaydediliyor...' : 'Kaydet'}
                </button>
              </div>
            </div>

            {/* Mod Seçimi */}
            <div className="mb-4 flex items-center space-x-4">
              <span className="text-sm font-medium text-gray-700">Mod:</span>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="set"
                  checked={mode === 'set'}
                  onChange={(e) => setMode(e.target.value as StockMode)}
                  className="w-4 h-4 text-blue-600"
                />
                <span className="text-sm text-gray-700">Set (Normal)</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="add"
                  checked={mode === 'add'}
                  onChange={(e) => setMode(e.target.value as StockMode)}
                  className="w-4 h-4 text-green-600"
                />
                <span className="text-sm text-gray-700">Ekleme (+)</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="subtract"
                  checked={mode === 'subtract'}
                  onChange={(e) => setMode(e.target.value as StockMode)}
                  className="w-4 h-4 text-red-600"
                />
                <span className="text-sm text-gray-700">Eksiltme (-)</span>
              </label>
            </div>

            {/* Mod Açıklaması */}
            <div className="mb-4 text-sm text-gray-600 bg-gray-50 p-3 rounded">
              {mode === 'set' && '❏ Normal mod: Girdiğiniz değer direkt stoğa set edilir.'}
              {mode === 'add' && '➕ Ekleme modu: Girdiğiniz değer mevcut stoğa eklenir.'}
              {mode === 'subtract' && '➖ Eksiltme modu: Girdiğiniz değer mevcut stoktan çıkarılır.'}
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
