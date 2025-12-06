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
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('auth_token'),
  isAuthenticated: !!localStorage.getItem('auth_token'),
  isLoading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiService.login(username, password);
      const { access_token } = response;

      localStorage.setItem('auth_token', access_token);

      // Kullanıcı bilgilerini al
      const user = await apiService.getMe();

      set({
        user,
        token: access_token,
        isAuthenticated: true,
        isLoading: false,
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
    });
  },

  checkAuth: async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    try {
      const user = await apiService.getMe();
      set({
        user,
        token,
        isAuthenticated: true,
      });
    } catch (error) {
      localStorage.removeItem('auth_token');
      set({
        user: null,
        token: null,
        isAuthenticated: false,
      });
    }
  },
}));
