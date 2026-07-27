/**
 * Auth Store
 * Zustand ile authentication state yönetimi
 */
import { create } from 'zustand';
import { apiService } from '../services/api';

interface User {
  username: string;
  role: string;
  station_id?: string | null;
  full_name?: string | null;
  user_id?: string;
  depot_id?: string | null;
  depot_code?: string | null;
  depot_name?: string | null;
  depot_city?: string | null;
  online_print_enabled?: boolean;  // Zebra bulut yazdırma bu depoda etkin mi
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  depotCode: string | null;
  depotName: string | null;

  login: (username: string, password: string, depotCode?: string) => Promise<User>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('auth_token'),
  isAuthenticated: !!localStorage.getItem('auth_token'),
  isLoading: false,
  error: null,
  depotCode: localStorage.getItem('selected_depot_code'),
  depotName: localStorage.getItem('selected_depot_name'),

  login: async (username: string, password: string, depotCode?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiService.login(username, password, depotCode);
      const { access_token } = response;

      localStorage.setItem('auth_token', access_token);
      if (depotCode) {
        localStorage.setItem('selected_depot_code', depotCode);
      }

      // Kullanıcı bilgilerini al
      const user = await apiService.getMe();

      // Depo bilgisini sakla
      if (user.depot_name) {
        localStorage.setItem('selected_depot_name', user.depot_name);
      }

      set({
        user,
        token: access_token,
        isAuthenticated: true,
        isLoading: false,
        depotCode: user.depot_code || depotCode || null,
        depotName: user.depot_name || null,
      });

      return user;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Giriş başarısız',
        isLoading: false,
      });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('auth_token');
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      error: null,
      depotCode: localStorage.getItem('selected_depot_code'),
      depotName: null,
    });
  },

  checkAuth: async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      set({ isAuthenticated: false, user: null, isLoading: false });
      return;
    }

    set({ isLoading: true });
    try {
      const user = await apiService.getMe();
      if (user.depot_name) {
        localStorage.setItem('selected_depot_name', user.depot_name);
      }
      set({
        user,
        token,
        isAuthenticated: true,
        isLoading: false,
        depotCode: user.depot_code || null,
        depotName: user.depot_name || null,
      });
    } catch (error) {
      localStorage.removeItem('auth_token');
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
}));
