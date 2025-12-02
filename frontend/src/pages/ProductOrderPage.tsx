/**
 * Product Order Page
 * Ürün sıralama yönetimi - Drag & Drop
 */
import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import Navbar from '../components/Navbar';

interface Product {
  id: string;
  code: string;
  name: string;
  display_order: number;
}

export default function ProductOrderPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    setIsLoading(true);
    try {
      const data = await apiService.getProductOrder();
      setProducts(data);
    } catch (err) {
      console.error('Ürünler yüklenemedi:', err);
      showToast('Ürünler yüklenemedi', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    
    if (draggedIndex === null || draggedIndex === index) return;

    // Drag edilen elemanı yeni pozisyona taşı
    const newProducts = [...products];
    const draggedItem = newProducts[draggedIndex];
    newProducts.splice(draggedIndex, 1);
    newProducts.splice(index, 0, draggedItem);
    
    // Display order'ları güncelle
    const updatedProducts = newProducts.map((p, idx) => ({
      ...p,
      display_order: idx + 1
    }));
    
    setProducts(updatedProducts);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload = products.map(p => ({
        id: p.id,
        display_order: p.display_order
      }));
      
      await apiService.updateProductOrder(payload);
      showToast('Ürün sıralaması kaydedildi', 'success');
    } catch (err) {
      console.error('Kaydetme hatası:', err);
      showToast('Kaydetme hatası', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Ürün sıralamasını varsayılan değerlere döndürmek istediğinize emin misiniz?')) {
      return;
    }
    
    setIsSaving(true);
    try {
      await apiService.resetProductOrder();
      await loadProducts();
      showToast('Sıralama varsayılan değerlere döndürüldü', 'success');
    } catch (err) {
      console.error('Reset hatası:', err);
      showToast('Reset hatası', 'error');
    } finally {
      setIsSaving(false);
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

      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-3xl font-bold">Ürün Sıralaması</h1>
              <p className="text-gray-600 mt-2">
                Ürünleri sürükleyerek yükleme fişlerindeki sıralamayı değiştirin
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={handleReset}
                disabled={isSaving}
                className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 disabled:opacity-50 font-semibold"
              >
                Varsayılana Dön
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 font-semibold"
              >
                {isSaving ? 'Kaydediliyor...' : 'Kaydet'}
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="bg-white rounded-lg shadow-md p-6">
              <p className="text-center text-gray-500">Yükleniyor...</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="p-4 bg-gray-50 border-b">
                <div className="grid grid-cols-12 gap-4 font-semibold text-sm text-gray-700">
                  <div className="col-span-1 text-center">Sıra</div>
                  <div className="col-span-4">Ürün Kodu (SKU)</div>
                  <div className="col-span-7">Ürün Adı</div>
                </div>
              </div>
              
              <div className="divide-y divide-gray-200">
                {products.map((product, index) => (
                  <div
                    key={product.id}
                    draggable
                    onDragStart={() => handleDragStart(index)}
                    onDragOver={(e) => handleDragOver(e, index)}
                    onDragEnd={handleDragEnd}
                    className={`grid grid-cols-12 gap-4 p-4 cursor-move hover:bg-gray-50 transition ${
                      draggedIndex === index ? 'opacity-50 bg-blue-50' : ''
                    }`}
                  >
                    <div className="col-span-1 text-center">
                      <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-bold text-sm">
                        {product.display_order}
                      </span>
                    </div>
                    <div className="col-span-4 font-medium text-gray-900">
                      {product.code}
                    </div>
                    <div className="col-span-7 text-gray-600">
                      {product.name}
                    </div>
                  </div>
                ))}
              </div>
              
              {products.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  Gösterilecek ürün yok
                </div>
              )}
            </div>
          )}
          
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>İpucu:</strong> Ürünleri sürükleyerek sıralamayı değiştirebilirsiniz. 
              Değişiklikleri kaydetmek için "Kaydet" butonuna basın.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
