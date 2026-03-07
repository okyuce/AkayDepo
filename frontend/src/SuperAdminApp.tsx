import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { useThemeStore } from './stores/themeStore';
import { initTheme } from './stores/themeStore';
import { APP_VERSION } from './config/version';
import SuperAdminLoginPage from './pages/SuperAdminLoginPage';
import DepotManagementPage from './pages/DepotManagementPage';
import GlobalUsersPage from './pages/GlobalUsersPage';

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

function SuperAdminNavbar() {
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'light': return <SunIcon />;
      case 'dark': return <MoonIcon />;
      default: return <MonitorIcon />;
    }
  };

  const linkClasses = (active: boolean) =>
    'px-3 py-2 rounded-md text-sm font-medium transition ' +
    (active ? 'bg-blue-700 text-white' : 'text-blue-100 hover:bg-blue-500');

  return (
    <nav className="bg-blue-600 dark:bg-gray-800 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-6">
            <Link to="/" className="flex items-center space-x-2 text-xl font-bold hover:text-blue-200 transition">
              <span className="text-yellow-300">Super Admin</span>
              <span>AkayDepo</span>
              <span className="text-sm text-blue-200 font-normal">v{APP_VERSION}</span>
            </Link>

            {user && (
              <nav className="flex space-x-4">
                <Link to="/depots" className={linkClasses(location.pathname === '/depots')}>
                  Depo Tanımları
                </Link>
                <Link to="/users" className={linkClasses(location.pathname === '/users')}>
                  Kullanıcı Yönetimi
                </Link>
              </nav>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {user && (
              <>
                <span className="text-sm">superadmin</span>
                <button
                  onClick={() => {
                    const next = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light';
                    setTheme(next);
                  }}
                  className="p-2 rounded-md hover:bg-blue-500 dark:hover:bg-gray-700 transition"
                  title={`Tema: ${theme === 'light' ? 'Açık' : theme === 'dark' ? 'Koyu' : 'Sistem'}`}
                >
                  {getThemeIcon()}
                </button>
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

function SuperAdminRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (user?.role !== 'superadmin') {
    useAuthStore.getState().logout();
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
}

function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <SuperAdminNavbar />
      <div className="max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-8 text-center">
          Sistem Yönetimi
        </h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            to="/depots"
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
            to="/users"
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

function DepotsPage() {
  return <DepotManagementPage navbarOverride={<SuperAdminNavbar />} />;
}

function UsersPage() {
  return <GlobalUsersPage navbarOverride={<SuperAdminNavbar />} />;
}

function SuperAdminApp() {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    initTheme();
    checkAuth();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<SuperAdminLoginPage />} />
        <Route
          path="/"
          element={
            <SuperAdminRoute>
              <DashboardPage />
            </SuperAdminRoute>
          }
        />
        <Route
          path="/depots"
          element={
            <SuperAdminRoute>
              <DepotsPage />
            </SuperAdminRoute>
          }
        />
        <Route
          path="/users"
          element={
            <SuperAdminRoute>
              <UsersPage />
            </SuperAdminRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default SuperAdminApp;
