/**
 * SuperAdmin Dashboard
 * Sadece Depo Tanımları ve Kullanıcı Yönetimi
 */
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';

export default function SuperAdminPage() {
  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-8 text-center">
          Sistem Yönetimi
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            to="/superadmin/depots"
            className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 hover:shadow-lg transition border-l-4 border-blue-500"
          >
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Depo Tanımları
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Depo ekleme, düzenleme ve başlatma işlemleri
            </p>
          </Link>

          <Link
            to="/superadmin/users"
            className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 hover:shadow-lg transition border-l-4 border-green-500"
          >
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Kullanıcı Yönetimi
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Tüm depolardaki kullanıcıları yönetme, şifre sıfırlama
            </p>
          </Link>
        </div>
      </div>
    </div>
  );
}
