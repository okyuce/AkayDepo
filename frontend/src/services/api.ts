/**
 * API Service
 * Backend ile iletişim için axios client
 */
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

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
        const token = localStorage.getItem('auth_token');
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
          localStorage.removeItem('auth_token');
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

  async logout() {
    const response = await this.client.post('/v1/auth/logout');
    return response.data;
  }

  async getMe() {
    const response = await this.client.get('/v1/auth/me');
    return response.data;
  }

  // Cycles
  async getActivecycle() {
    const response = await this.client.get('/v1/cycles/active');
    return response.data;
  }

  async getCycleImports(cycleId: string) {
    const response = await this.client.get(`/v1/cycles/${cycleId}/imports`);
    return response.data as { id: string; batch_number: number; filename: string; file_size: number; uploaded_at: string }[];
  }

  async importCycle(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Varsayılan değerler
    const now = new Date();
    const hour = now.getHours();
    let runTime = '14:00';
    if (hour >= 16) runTime = '17:00';
    else if (hour >= 14) runTime = '16:00';
    
    const planDate = now.toISOString().split('T')[0]; // YYYY-MM-DD
    
    formData.append('run_time', runTime);
    formData.append('plan_date', planDate);
    
    const response = await this.client.post('/v1/cycles/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async getCycleStatus(cycleId: string) {
    const response = await this.client.get(`/v1/cycles/${cycleId}/status`);
    return response.data;
  }

  async cancelPendingLoadsheets(cycleId: string) {
    const response = await this.client.post(`/v1/cycles/${cycleId}/cancel-pending`);
    return response.data;
  }

  async getCycleRevisions(cycleId: string) {
    const response = await this.client.get(`/v1/cycles/${cycleId}/revisions`);
    return response.data;
  }

  // Planning
  async createPlan(cycleId: string, numStations: number) {
    const response = await this.client.post(`/v1/cycles/${cycleId}/plan`, {
      worker_count: numStations,
    });
    return response.data;
  }

  async getPlan(cycleId: string) {
    const response = await this.client.get(`/v1/cycles/${cycleId}/plan`);
    return response.data;
  }

  // Loadsheets
  async getStationLoadsheets(stationId: string, cycleId?: string) {
    const params = cycleId ? { cycle_id: cycleId } : {};
    const response = await this.client.get(`/v1/loadsheets/station/${stationId}`, {
      params,
    });
    return response.data;
  }

  async getLoadsheetDetail(loadsheetId: string) {
    const response = await this.client.get(`/v1/loadsheets/${loadsheetId}`);
    return response.data;
  }

  async completeLoadsheet(loadsheetId: string) {
    const response = await this.client.post(`/v1/loadsheets/${loadsheetId}/complete`);
    return response.data;
  }

  // Counters
  async saveCounterReading(stationId: string, counterValue: number) {
    const response = await this.client.post('/v1/counters/', {
      station_id: stationId,
      counter_value: counterValue,
    });
    return response.data;
  }

  async getCycleCounters(cycleId: string) {
    const response = await this.client.get(`/v1/counters/cycle/${cycleId}`);
    return response.data;
  }

  async getLatestCounter(stationId: string) {
    const response = await this.client.get(`/v1/counters/station/${stationId}/latest`);
    return response.data;
  }

  // Stations
  async getStationDistribution(stationId: string, cycleId: string) {
    const response = await this.client.get(`/v1/stations/${stationId}/distribution/${cycleId}`);
    return response.data;
  }

  async listStations() {
    const response = await this.client.get('/v1/stations/');
    return response.data as { id: string; name: string; active: boolean }[];
  }

  async updateStation(stationId: string, data: { active?: boolean; name?: string }) {
    const response = await this.client.put(`/v1/stations/${stationId}`, data);
    return response.data as { id: string; name: string; active: boolean };
  }

  async createStation(name: string) {
    const response = await this.client.post('/v1/stations/', { name });
    return response.data as { id: string; name: string; active: boolean };
  }

  async deleteStation(stationId: string) {
    const response = await this.client.delete(`/v1/stations/${stationId}`);
    return response.data;
  }

  // Assignments (manual mapping)
  async getAssignmentsConfig() {
    const response = await this.client.get('/v1/assignments/config');
    return response.data as {
      auto_planning_enabled: boolean;
      stations: { id: string; name: string; active: boolean }[];
      assignments: { station_id: string; territory_code: string }[];
    };
  }

  async saveAssignmentsConfig(payload: {
    auto_planning_enabled: boolean;
    assignments: { station_id: string; territory_code: string }[];
  }) {
    const response = await this.client.post('/v1/assignments/config', payload);
    return response.data;
  }

  async resetAssignments() {
    const response = await this.client.post('/v1/assignments/reset', {});
    return response.data;
  }

  // Territory Info
  async getTerritories(includeInactive: boolean = false) {
    const params = { include_inactive: includeInactive };
    const response = await this.client.get('/v1/territory-info/', { params });
    return response.data;
  }

  async getTerritory(id: string) {
    const response = await this.client.get(`/v1/territory-info/${id}`);
    return response.data;
  }

  async createTerritory(data: { code: string; name: string; display_number: string; color?: string }) {
    const response = await this.client.post('/v1/territory-info/', data);
    return response.data;
  }

  async updateTerritory(id: string, data: { name?: string; display_number?: string; is_active?: boolean; color?: string }) {
    const response = await this.client.put(`/v1/territory-info/${id}`, data);
    return response.data;
  }

  async deleteTerritory(id: string) {
    const response = await this.client.delete(`/v1/territory-info/${id}`);
    return response.data;
  }

  async reorderTerritories(territoryIds: string[]) {
    const response = await this.client.post('/v1/territory-info/reorder', {
      territory_ids: territoryIds,
    });
    return response.data;
  }

  // Inventory
  async getStationInventory(stationId: string) {
    const response = await this.client.get(`/v1/inventory/station/${stationId}`);
    return response.data as {
      station_id: string;
      station_name: string;
      products: Array<{
        product_id: string;
        product_code: string;
        product_name: string;
        quantity_carton: number;
        quantity_pack: number;
        updated_at: string | null;
      }>;
    };
  }

  async updateStationInventory(stationId: string, products: Array<{ product_id: string; quantity_carton: number; quantity_pack: number }>) {
    const response = await this.client.post(`/v1/inventory/station/${stationId}`, {
      products
    });
    return response.data;
  }
}

export const apiService = new ApiService();
