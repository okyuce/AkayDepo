/**
 * Navbar Component
 * Üst menü - kullanıcı bilgisi ve logout
 */
import { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [isDefinitionsOpen, setIsDefinitionsOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const linkClasses = (active: boolean) =>
    'px-3 py-2 rounded-md text-sm font-medium transition ' +
    (active ? 'bg-blue-700 text-white' : 'text-blue-100 hover:bg-blue-500');

  return (
    <nav className="bg-blue-600 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-6">
            <Link to="/" className="text-xl font-bold hover:text-blue-200 transition">
              AkayDepo
            </Link>
            
            {user && (
              <nav className="flex space-x-4">
                {/* Admin kullanıcılar için tüm sayfalar */}
                {user.role === 'admin' && (
                  <>
                    <Link
                      to="/"
                      className={linkClasses(location.pathname === '/')}
                    >
                      Planlama
                    </Link>
                    <Link
                      to="/distribution"
                      className={linkClasses(location.pathname === '/distribution')}
                    >
                      İstasyon Dağılımı
                    </Link>
                    <Link
                      to="/stock-distribution"
                      className={linkClasses(location.pathname === '/stock-distribution')}
                    >
                      Stok Dağılımı
                    </Link>
                  </>
                )}
                
                {/* Tüm kullanıcılar için Yükleme Fişleri */}
                <Link
                  to="/loadsheets"
                  className={linkClasses(location.pathname === '/loadsheets')}
                >
                  Yükleme Fişleri
                </Link>
                
                {/* Tanımlar Dropdown - EN SONDA */}
                {user.role === 'admin' && (
                  <div className="relative">
                    <button
                      onClick={() => setIsDefinitionsOpen(!isDefinitionsOpen)}
                      className={
                        'px-3 py-2 rounded-md text-sm font-medium transition flex items-center ' +
                        (location.pathname.startsWith('/territories')
                          ? 'bg-blue-700 text-white'
                          : 'text-blue-100 hover:bg-blue-500')
                      }
                    >
                      Tanımlar
                      <svg className="ml-1 w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                    
                    {isDefinitionsOpen && (
                      <div className="absolute left-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10">
                        <Link
                          to="/territories"
                          onClick={() => setIsDefinitionsOpen(false)}
                          className="block px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 rounded-md"
                        >
                          Territory Tanımları
                        </Link>
                        <Link
                          to="/territory-assignment"
                          onClick={() => setIsDefinitionsOpen(false)}
                          className="block px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 rounded-md"
                        >
                          Territory Atama
                        </Link>
                      </div>
                    )}
                  </div>
                )}
              </nav>
            )}
          </div>
          
          <div className="flex items-center space-x-4">
            {user && (
              <>
                <span className="text-sm">
                  👤 {user.username}
                </span>
                <button
                  onClick={handleLogout}
                  className="bg-red-500 hover:bg-red-600 px-4 py-2 rounded-md text-sm font-medium transition"
                >
                  Çıkış
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
