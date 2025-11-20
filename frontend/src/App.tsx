import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import LoginPage from './pages/LoginPage';
import ExcelUploadPage from './pages/ExcelUploadPage';
import TabletPage from './pages/TabletPage';
import StationDistributionPage from './pages/StationDistributionPage';
import LoadsheetListPage from './pages/LoadsheetListPage';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  // Tablet kullanıcıları Yükleme Fişleri'ne yönlendir
  if (user?.role === 'tablet') {
    return <Navigate to="/loadsheets" />;
  }
  
  return <>{children}</>;
}

function App() {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <AdminRoute>
              <ExcelUploadPage />
            </AdminRoute>
          }
        />
        <Route
          path="/tablet/:stationId"
          element={
            <AdminRoute>
              <TabletPage />
            </AdminRoute>
          }
        />
        <Route
          path="/distribution"
          element={
            <AdminRoute>
              <StationDistributionPage />
            </AdminRoute>
          }
        />
        <Route
          path="/loadsheets"
          element={
            <PrivateRoute>
              <LoadsheetListPage />
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
