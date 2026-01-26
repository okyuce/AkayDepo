/**
 * Dashboard API Service
 * Backend ile iletisim icin axios client
 */
import axios, { AxiosInstance } from 'axios';

// Production'da relative URL kullan, development'da localhost:8001
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8001');

export interface DashboardSummary {
  cycle: {
    id: string;
    cycle_no: number;
    run_time: string;
    plan_date: string;
    status: string;
    last_completion_time: string | null;
  } | null;
  loadsheet_stats: {
    total: number;
    completed: number;
    pending: number;
    revision_cancelled: number;
    completion_percentage: number;
  };
  station_summary: Array<{
    station_id: string;
    station_name: string;
    territory_count: number;
    total_carton: number;
    completed_carton: number;
    progress_percent: number;
  }>;
  last_import: {
    filename: string;
    uploaded_at: string;
    batch_number: number;
  } | null;
  last_updated: string;
}

export interface StationDetail {
  station_id: string;
  station_name: string;
  territories: Array<{
    territory_code: string;
    display_number: string;
    total_loadsheets: number;
    completed_loadsheets: number;
    total_carton: number;
    completed_carton: number;
  }>;
  loadsheets: Array<{
    id: string;
    sheet_no: string;
    route_number: number | null;
    dealer_name: string;
    dealer_code: string;
    status: string;
    total_carton: number;
    total_pack: number;
    batch_number: number;
    has_revision: boolean;
    revision_count: number;
  }>;
}

export interface TerritoryTracking {
  territory_id: string;
  territory_display: string;
  remaining_carton: number;
  remaining_pack: number;
  remaining_total: number;
  prepared_carton: number;
  prepared_pack: number;
  prepared_total: number;
}

export interface ProductTracking {
  product_code: string;
  product_name: string;
  stock_carton: number;
  stock_pack: number;
  stock_total: number;
  territories: TerritoryTracking[];
}

export interface StationTracking {
  station_id: string;
  station_name: string;
  territories: Array<{
    id: string;
    code: string;
    display_number: string;
    name: string;
  }>;
  products: ProductTracking[];
}

export interface TerritoryDetail {
  territory_code: string;
  territory_name: string;
  dealers: Array<{
    dealer_code: string;
    dealer_name: string;
    route_order: number | null;
    loadsheet_id: string | null;
    status: string;
    total_carton: number;
    total_pack: number;
    has_revision: boolean;
    revision_count: number;
    products: Array<{
      product_code: string;
      product_name: string;
      quantity_carton: number;
      quantity_pack: number;
      change_carton: number | null;
      change_pack: number | null;
    }>;
    loadsheets: Array<{
      id: string;
      batch_number: number;
      status: string;
      total_carton: number;
      total_pack: number;
      is_active: boolean;
      is_revision: boolean;
    }>;
  }>;
}

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor - Token ekle
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('dashboard_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - 401 durumunda logout
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('dashboard_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(username: string, password: string) {
    const response = await this.client.post('/v1/auth/login', {
      username,
      password,
    });
    return response.data;
  }

  async getMe() {
    const response = await this.client.get('/v1/auth/me');
    return response.data;
  }

  // Dashboard Summary
  async getDashboardSummary(): Promise<DashboardSummary> {
    const response = await this.client.get('/v1/dashboard/summary');
    return response.data;
  }

  // Active Cycle
  async getActiveCycle() {
    const response = await this.client.get('/v1/cycles/active');
    return response.data;
  }

  // Cycle Status
  async getCycleStatus(cycleId: string) {
    const response = await this.client.get(`/v1/cycles/${cycleId}/status`);
    return response.data;
  }

  // Cycle Imports
  async getCycleImports(cycleId: string) {
    const response = await this.client.get(`/v1/cycles/${cycleId}/imports`);
    return response.data;
  }

  // Plan
  async getCyclePlan(cycleId: string) {
    const response = await this.client.get(`/v1/cycles/${cycleId}/plan`);
    return response.data;
  }

  // Stations
  async getStations() {
    const response = await this.client.get('/v1/stations/');
    return response.data;
  }

  // Station Loadsheets
  async getStationLoadsheets(stationId: string, cycleId?: string) {
    const params: Record<string, string> = {};
    if (cycleId) params.cycle_id = cycleId;
    const response = await this.client.get(`/v1/loadsheets/station/${stationId}`, { params });
    return response.data;
  }

  // Station Detail for Dashboard
  async getStationDetail(stationId: string, cycleId: string): Promise<StationDetail> {
    const response = await this.client.get(`/v1/dashboard/station/${stationId}`, {
      params: { cycle_id: cycleId }
    });
    return response.data;
  }

  // Territory Detail for Dashboard
  async getTerritoryDetail(territoryCode: string, cycleId: string): Promise<TerritoryDetail> {
    const response = await this.client.get(`/v1/dashboard/territory/${territoryCode}`, {
      params: { cycle_id: cycleId }
    });
    return response.data;
  }

  // Territories
  async getTerritories() {
    const response = await this.client.get('/v1/territory-info/');
    return response.data;
  }

  // Station Tracking (İstasyon Dağılımı)
  async getStationTracking(stationId: string, cycleId: string): Promise<StationTracking> {
    const response = await this.client.get(`/v1/stations/${stationId}/tracking/${cycleId}`);
    return response.data;
  }
}

export const apiService = new ApiService();
