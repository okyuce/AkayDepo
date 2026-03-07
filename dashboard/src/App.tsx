import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuthStore } from './stores/authStore';
import LoginPage from './pages/LoginPage';
import MultiDepotOverviewPage from './pages/MultiDepotOverviewPage';
import DepotDashboardPage from './pages/DepotDashboardPage';
import StationDetailPage from './pages/StationDetailPage';
import TerritoryViewPage from './pages/TerritoryViewPage';
import Navbar from './components/Navbar';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    checkAuth().finally(() => setChecking(false));
  }, [checkAuth]);

  if (checking || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <>
      <Navbar />
      <main className="pt-16">
        {children}
      </main>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <MultiDepotOverviewPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/depot/:depotCode"
          element={
            <PrivateRoute>
              <DepotDashboardPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/station/:stationId"
          element={
            <PrivateRoute>
              <StationDetailPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/territory/:territoryCode"
          element={
            <PrivateRoute>
              <TerritoryViewPage />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
