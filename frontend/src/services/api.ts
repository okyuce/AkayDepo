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
}

export const apiService = new ApiService();
