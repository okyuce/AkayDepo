/**
 * Navbar Component
 * Üst menü - kullanıcı bilgisi ve logout
 */
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

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
                      className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                        location.pathname === '/' 
                          ? 'bg-blue-700 text-white' 
                          : 'text-blue-100 hover:bg-blue-500'
                      }`}
                    >
                      Planlama
                    </Link>
                    <Link
                      to="/distribution"
                      className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                        location.pathname === '/distribution' 
                          ? 'bg-blue-700 text-white' 
                          : 'text-blue-100 hover:bg-blue-500'
                      }`}
                    >
                      İstasyon Dağılımı
                    </Link>
                  </>
                )}
                
                {/* Tüm kullanıcılar için Yükleme Fişleri */}
                <Link
                  to="/loadsheets"
                  className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                    location.pathname === '/loadsheets' 
                      ? 'bg-blue-700 text-white' 
                      : 'text-blue-100 hover:bg-blue-500'
                  }`}
                >
                  Yükleme Fişleri
                </Link>
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
