/**
 * Navbar Component
 * Üst menü - kullanıcı bilgisi ve logout
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useThemeStore } from '../stores/themeStore';
import { APP_VERSION } from '../config/version';

// Theme Icons
const SunIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
);

const MoonIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
  </svg>
);

const MonitorIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [isDefinitionsOpen, setIsDefinitionsOpen] = useState(false);
  const [isThemeOpen, setIsThemeOpen] = useState(false);
  const themeDropdownRef = useRef<HTMLDivElement>(null);
  const definitionsDropdownRef = useRef<HTMLDivElement>(null);

  // Dropdown dışına tıklama ile kapatma
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (themeDropdownRef.current && !themeDropdownRef.current.contains(event.target as Node)) {
        setIsThemeOpen(false);
      }
      if (definitionsDropdownRef.current && !definitionsDropdownRef.current.contains(event.target as Node)) {
        setIsDefinitionsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return <SunIcon />;
      case 'dark':
        return <MoonIcon />;
      default:
        return <MonitorIcon />;
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const linkClasses = (active: boolean) =>
    'px-3 py-2 rounded-md text-sm font-medium transition ' +
    (active ? 'bg-blue-700 text-white' : 'text-blue-100 hover:bg-blue-500');

  return (
    <nav className="bg-blue-600 dark:bg-gray-800 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-6">
            {user?.depot_city && (
              <span className="text-yellow-300 text-2xl font-extrabold tracking-wide mr-1">{user.depot_city.toUpperCase()}</span>
            )}
            <Link to="/" className="flex items-center space-x-2 text-xl font-bold hover:text-blue-200 transition">
              <span>AkayDepo</span>
              <span className="text-sm text-blue-200 font-normal">v{APP_VERSION}</span>
            </Link>

            {user && (
              <nav className="flex space-x-4">
                {/* Admin kullanıcılar için menü */}
                {['admin', 'superadmin'].includes(user.role) && (
                  <>
                    <Link
                      to="/territory-assignment"
                      className={linkClasses(location.pathname === '/territory-assignment')}
                    >
                      Territory Atama
                    </Link>
                    <Link
                      to="/"
                      className={linkClasses(location.pathname === '/')}
                    >
                      Planlama
                    </Link>
                    <Link
                      to="/stock-distribution"
                      className={linkClasses(location.pathname === '/stock-distribution')}
                    >
                      Stok Dağılımı
                    </Link>
                  </>
                )}

                {/* Tüm kullanıcılar için İstasyon Dağılımı */}
                <Link
                  to="/distribution"
                  className={linkClasses(location.pathname === '/distribution')}
                >
                  İstasyon Dağılımı
                </Link>

                {/* Tüm kullanıcılar için Yükleme Fişleri */}
                <Link
                  to="/loadsheets"
                  className={linkClasses(location.pathname === '/loadsheets')}
                >
                  Yükleme Fişleri
                </Link>

                {/* Admin kullanıcılar için Stok Hareketleri */}
                {['admin', 'superadmin'].includes(user.role) && (
                  <Link
                    to="/stock-movements"
                    className={linkClasses(location.pathname === '/stock-movements')}
                  >
                    Stok Hareketleri
                  </Link>
                )}
              </nav>
            )}
          </div>
          
          <div className="flex items-center space-x-4">
            {user && (
              <>
                {/* Tanımlar Dropdown - SAĞDA (sadece admin) */}
                {['admin', 'superadmin'].includes(user.role) && (
                  <div className="relative" ref={definitionsDropdownRef}>
                    <button
                      onClick={() => setIsDefinitionsOpen(!isDefinitionsOpen)}
                      className={
                        'px-3 py-2 rounded-md text-sm font-medium transition flex items-center ' +
                        (location.pathname.startsWith('/territories') ||
                         location.pathname.startsWith('/product-order') ||
                         location.pathname.startsWith('/change-password')
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
                      <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-700 rounded-md shadow-lg z-10">
                        <Link
                          to="/territories"
                          onClick={() => setIsDefinitionsOpen(false)}
                          className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-gray-600 rounded-md"
                        >
                          Territory Tanımları
                        </Link>
                        <Link
                          to="/product-order"
                          onClick={() => setIsDefinitionsOpen(false)}
                          className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-gray-600 rounded-md"
                        >
                          Ürün Sıralaması
                        </Link>
                        <Link
                          to="/change-password"
                          onClick={() => setIsDefinitionsOpen(false)}
                          className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-gray-600 rounded-md"
                        >
                          🔒 Şifremi Değiştir
                        </Link>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Tablet kullanıcıları için şifre değiştir linki */}
                {user.role === 'tablet' && (
                  <Link
                    to="/change-password"
                    className="text-sm text-blue-100 hover:text-white transition"
                  >
                    🔒 Şifremi Değiştir
                  </Link>
                )}
                
                <span className="text-sm">
                  👤 {user.username}
                </span>

                {/* Theme Toggle */}
                <div className="relative" ref={themeDropdownRef}>
                  <button
                    onClick={() => setIsThemeOpen(!isThemeOpen)}
                    className="p-2 rounded-md hover:bg-blue-500 dark:hover:bg-gray-700 transition"
                    title={`Tema: ${theme === 'light' ? 'Açık' : theme === 'dark' ? 'Koyu' : 'Sistem'}`}
                  >
                    {getThemeIcon()}
                  </button>

                  {isThemeOpen && (
                    <div className="absolute right-0 mt-2 w-36 bg-white dark:bg-gray-700 rounded-md shadow-lg z-50">
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setTheme('light'); setIsThemeOpen(false); }}
                        className={`flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-gray-600 rounded-t-md cursor-pointer ${theme === 'light' ? 'bg-blue-50 dark:bg-gray-600' : ''}`}
                      >
                        <SunIcon /> <span className="ml-2">Açık</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setTheme('dark'); setIsThemeOpen(false); }}
                        className={`flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-gray-600 cursor-pointer ${theme === 'dark' ? 'bg-blue-50 dark:bg-gray-600' : ''}`}
                      >
                        <MoonIcon /> <span className="ml-2">Koyu</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setTheme('system'); setIsThemeOpen(false); }}
                        className={`flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-gray-600 rounded-b-md cursor-pointer ${theme === 'system' ? 'bg-blue-50 dark:bg-gray-600' : ''}`}
                      >
                        <MonitorIcon /> <span className="ml-2">Sistem</span>
                      </button>
                    </div>
                  )}
                </div>

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
