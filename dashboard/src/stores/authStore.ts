/**
 * Dashboard Auth Store
 * Zustand ile authentication state yonetimi
 */
import { create } from 'zustand';
import { apiService } from '../services/api';

interface User {
  username: string;
  role: string;
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
  token: localStorage.getItem('dashboard_token'),
  isAuthenticated: !!localStorage.getItem('dashboard_token'),
  isLoading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiService.login(username, password);
      const { access_token } = response;

      localStorage.setItem('dashboard_token', access_token);

      // Kullanici bilgilerini al
      const user = await apiService.getMe();

      // Admin kontrolu
      if (user.role !== 'admin') {
        localStorage.removeItem('dashboard_token');
        set({
          error: 'Bu panele sadece yoneticiler girebilir',
          isLoading: false,
        });
        throw new Error('Yetkisiz erisim');
      }

      set({
        user,
        token: access_token,
        isAuthenticated: true,
        isLoading: false,
      });

      return user;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Giris basarisiz'
        : 'Giris basarisiz';
      set({
        error: errorMessage,
        isLoading: false,
      });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('dashboard_token');
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      error: null,
    });
  },

  checkAuth: async () => {
    const token = localStorage.getItem('dashboard_token');
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    try {
      const user = await apiService.getMe();

      // Admin kontrolu
      if (user.role !== 'admin') {
        localStorage.removeItem('dashboard_token');
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        });
        return;
      }

      set({
        user,
        token,
        isAuthenticated: true,
      });
    } catch {
      localStorage.removeItem('dashboard_token');
      set({
        user: null,
        token: null,
        isAuthenticated: false,
      });
    }
  },
}));
