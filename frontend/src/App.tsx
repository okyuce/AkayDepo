import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import LoginPage from './pages/LoginPage';
import ExcelUploadPage from './pages/ExcelUploadPage';
import TabletPage from './pages/TabletPage';
import StationDistributionPage from './pages/StationDistributionPage';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
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
            <PrivateRoute>
              <ExcelUploadPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/tablet/:stationId"
          element={
            <PrivateRoute>
              <TabletPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/distribution"
          element={
            <PrivateRoute>
              <StationDistributionPage />
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
