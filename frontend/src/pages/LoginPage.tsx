/**
 * Login Page
 * Kullanıcı giriş sayfası - Depo seçimi ile
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { apiService } from '../services/api';

interface DepotOption {
  code: string;
  name: string;
  city: string;
}

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [depotCode, setDepotCode] = useState(
    localStorage.getItem('selected_depot_code') || ''
  );
  const [depots, setDepots] = useState<DepotOption[]>([]);
  const [depotsLoading, setDepotsLoading] = useState(true);
  const { login, isLoading, error } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    apiService
      .getPublicDepots()
      .then((data) => {
        setDepots(data);
        // Eğer kayıtlı depo kodu listede yoksa temizle
        const saved = localStorage.getItem('selected_depot_code');
        if (saved && !data.find((d) => d.code === saved)) {
          setDepotCode('');
        }
      })
      .catch(() => {
        // Depo listesi alınamazsa devam et
      })
      .finally(() => setDepotsLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const user = await login(username, password, depotCode || undefined);

      // Superadmin ise superadmin paneline yönlendir
      if (user?.role === 'superadmin') {
        navigate('/superadmin');
      } else if (user?.role === 'tablet') {
        navigate('/loadsheets');
      } else {
        navigate('/');
      }
    } catch {
      // Error handled in store
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
      <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-900 dark:text-gray-100">
          AkayDepo Giriş
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Depo
            </label>
            {depotsLoading ? (
              <div className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-sm">
                Depolar yükleniyor...
              </div>
            ) : (
              <select
                value={depotCode}
                onChange={(e) => setDepotCode(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                required
              >
                <option value="">-- Depo Seçin --</option>
                {depots.map((depot) => (
                  <option key={depot.code} value={depot.code}>
                    {depot.code} - {depot.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Kullanıcı Adı
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Şifre
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              required
            />
          </div>

          {error && (
            <div className="bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400"
          >
            {isLoading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
          </button>
        </form>
      </div>
    </div>
  );
}
