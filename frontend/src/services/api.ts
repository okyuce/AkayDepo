/**
 * API Service
 * Backend ile iletişim için axios client
 */
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

/**
 * Varsayılan zaman aşımı. Timeout olmadan, tablet ağı koptuğunda istek
 * dakikalarca "yolda" kalıyor ve UI (ör. "Tamamlanıyor..." butonu) kilitleniyordu.
 */
const DEFAULT_TIMEOUT_MS = 30000;
/** Excel import gibi uzun işlemler — nginx proxy_read_timeout (300s) ile uyumlu. */
const LONG_TIMEOUT_MS = 300000;
/**
 * Fiş tamamlama: sunucu normalde ~200ms yanıtlıyor. Kısa tutuluyor çünkü
 * endpoint idempotent — timeout'ta tekrar denemek ve durumu doğrulamak güvenli.
 */
const COMPLETE_TIMEOUT_MS = 12000;
/** Fişin sunucudaki gerçek durumunu sorarken kullanılan süre. */
const STATUS_CHECK_TIMEOUT_MS = 6000;

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: DEFAULT_TIMEOUT_MS,
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
  async login(username: string, password: string, depotCode?: string) {
    const response = await this.client.post('/v1/auth/login', {
      username,
      password,
      depot_code: depotCode || undefined,
    });
    return response.data;
  }

  async getPublicDepots() {
    const response = await this.client.get('/v1/auth/depots/public');
    return response.data as Array<{ code: string; name: string; city: string }>;
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
      timeout: LONG_TIMEOUT_MS,  // binlerce satırlık Excel işlenmesi uzun sürebilir
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
    }, {
      timeout: LONG_TIMEOUT_MS,  // yük dengeleme tüm bayiler üzerinde çalışır
    });
    return response.data;
  }

  async getPlan(cycleId: string) {
    const response = await this.client.get(`/v1/cycles/${cycleId}/plan`);
    return response.data;
  }

  // Loadsheets
  async getStationLoadsheets(
    stationId: string,
    cycleId?: string,
    importBatch?: number,
    sku?: string[],
    skuMatch?: 'or' | 'and',
    skuQtyType?: 'carton' | 'pack',
    skuQtyValue?: number
  ) {
    const params: Record<string, string | number> = {};
    if (cycleId) params.cycle_id = cycleId;
    if (importBatch !== undefined && importBatch !== null) params.import_batch = importBatch;
    if (sku && sku.length > 0) params.sku = sku.join(',');
    if (skuMatch) params.sku_match = skuMatch;
    if (skuQtyType) params.sku_qty_type = skuQtyType;
    if (skuQtyValue !== undefined && skuQtyValue !== null) params.sku_qty_value = skuQtyValue;
    const response = await this.client.get(`/v1/loadsheets/station/${stationId}`, { params });
    return response.data;
  }

  async getLoadsheetDetail(loadsheetId: string) {
    const response = await this.client.get(`/v1/loadsheets/${loadsheetId}`);
    return response.data;
  }

  /**
   * Fişi tamamla — tablet ağı koptuğunda isteğin yolda kaybolmasına dayanıklı.
   *
   * Backend idempotent (`already_completed: true` döner) olduğu için tekrar
   * denemek güvenlidir. Yanıt alınamazsa fişin gerçek durumu sunucuya sorulur:
   * `loaded` ise istek aslında işlenmiş demektir, başarı sayılır.
   */
  async completeLoadsheet(loadsheetId: string) {
    const MAX_ATTEMPTS = 2;
    let lastError: unknown = new Error('Fiş tamamlanamadı');

    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      try {
        const response = await this.client.post(`/v1/loadsheets/${loadsheetId}/complete`, null, {
          timeout: COMPLETE_TIMEOUT_MS,
        });
        return response.data;
      } catch (error) {
        lastError = error;
        if (!this.isRetriableError(error)) throw error;

        // İstek sunucuya ulaşıp sadece yanıtı kaybolmuş olabilir — durumu doğrula
        if (await this.isLoadsheetLoaded(loadsheetId)) {
          return { loadsheet_id: loadsheetId, status: 'loaded', already_completed: true };
        }
        if (attempt < MAX_ATTEMPTS) await sleep(attempt * 1000);
      }
    }

    throw lastError;
  }

  /** Yanıt alınamadıysa (timeout/ağ kopması) veya sunucu geçici hata verdiyse tekrar denenebilir. */
  private isRetriableError(error: any): boolean {
    if (axios.isCancel(error)) return false;
    // Sunucudan yanıt geldiyse sadece geçici sunucu hatalarında tekrar dene;
    // yanıt hiç yoksa (timeout / ağ kopması / bağlantı reddi) tekrar denenebilir.
    if (error?.response) return [502, 503, 504].includes(error.response.status);
    return true;
  }

  /** Fiş sunucuda gerçekten tamamlanmış mı? (yanıtı kaybolan istekleri doğrulamak için) */
  private async isLoadsheetLoaded(loadsheetId: string): Promise<boolean> {
    try {
      const response = await this.client.get(`/v1/loadsheets/${loadsheetId}`, {
        timeout: STATUS_CHECK_TIMEOUT_MS,
      });
      return response.data?.status === 'loaded';
    } catch {
      return false;
    }
  }

  async cancelLoadsheet(loadsheetId: string) {
    const response = await this.client.post(`/v1/loadsheets/${loadsheetId}/cancel`);
    return response.data;
  }

  async uncancelLoadsheet(loadsheetId: string) {
    const response = await this.client.post(`/v1/loadsheets/${loadsheetId}/uncancel`);
    return response.data;
  }

  /** AkayPrintBT (Zebra köprüsü) için kısa ömürlü ZPL fetch token'ı al. */
  async getLoadsheetPrintToken(loadsheetId: string) {
    const response = await this.client.post(`/v1/loadsheets/${loadsheetId}/print-token`);
    return response.data as {
      token: string;
      expires_in: number;
      loadsheet_id: string;
    };
  }

  /** Zebra bulut yazdırma (Online Print) — ZPL backend'den Zebra Data Services'e gider. */
  async cloudPrintLoadsheet(loadsheetId: string, serial?: string) {
    const response = await this.client.post(
      `/v1/loadsheets/${loadsheetId}/cloud-print`,
      null,
      serial ? { params: { serial } } : undefined,
    );
    return response.data as {
      status: string;
      loadsheet_id: string;
      printer_serial: string;
      zebra_status: number;
      zebra_response: string;
    };
  }

  /** API base URL — Zebra fetch URL'i kurmak için. */
  get baseURL(): string {
    return API_BASE_URL;
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

  async getStationTracking(stationId: string, cycleId: string) {
    const response = await this.client.get(`/v1/stations/${stationId}/tracking/${cycleId}`);
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

  async createStation() {
    const response = await this.client.post('/v1/stations/', {});
    return response.data as { id: string; name: string; active: boolean; tablet_user?: string };
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
      stations: { id: string; name: string; active: boolean; is_main_stock?: boolean; is_park?: boolean }[];
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

  async updateTerritory(id: string, data: { code?: string; name?: string; display_number?: string; is_active?: boolean; color?: string }) {
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

  // Product Order
  async getProductOrder() {
    const response = await this.client.get('/v1/product-order/');
    return response.data as Array<{
      id: string;
      code: string;
      name: string;
      display_order: number;
    }>;
  }

  async updateProductOrder(products: Array<{ id: string; display_order: number }>) {
    const response = await this.client.put('/v1/product-order/', { products });
    return response.data;
  }

  async resetProductOrder() {
    const response = await this.client.post('/v1/product-order/reset', {});
    return response.data;
  }

  // Users Management
  async getUsers() {
    const response = await this.client.get('/v1/users/');
    return response.data as Array<{
      id: string;
      username: string;
      full_name: string | null;
      role: string;
      station_id: string | null;
      is_active: boolean;
      created_at: string;
    }>;
  }

  async updateUser(userId: string, data: { full_name?: string | null; is_active?: boolean }) {
    const response = await this.client.patch(`/v1/users/${userId}`, data);
    return response.data;
  }

  async resetUserPassword(userId: string, newPassword: string) {
    const response = await this.client.post(`/v1/users/${userId}/reset-password`, {
      new_password: newPassword,
    });
    return response.data;
  }

  async changePassword(currentPassword: string, newPassword: string) {
    const response = await this.client.post('/v1/users/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  }

  // Depots (SuperAdmin)
  async getDepots() {
    const response = await this.client.get('/v1/depots/');
    return response.data as Array<{
      id: string;
      code: string;
      name: string;
      city: string;
      is_active: boolean;
      user_count: number;
      tablet_count: number;
      station_count: number;
      has_active_cycle: boolean;
      active_cycle_date: string | null;
      created_at: string;
    }>;
  }

  async createDepot(data: { code: string; name: string; city: string }) {
    const response = await this.client.post('/v1/depots/', data);
    return response.data;
  }

  async updateDepot(depotId: string, data: { name?: string; city?: string; is_active?: boolean }) {
    const response = await this.client.put(`/v1/depots/${depotId}`, data);
    return response.data;
  }

  // SuperAdmin Users
  async getSuperadminUsers(depotId?: string) {
    const params: Record<string, string> = {};
    if (depotId) params.depot_id = depotId;
    const response = await this.client.get('/v1/superadmin/users', { params });
    return response.data as Array<{
      id: string;
      username: string;
      full_name: string | null;
      role: string;
      is_active: boolean;
      depot_id: string | null;
      depot_code: string | null;
      depot_name: string | null;
      station_id: string | null;
      station_name: string | null;
      created_at: string;
    }>;
  }

  async createSuperadminUser(data: {
    username: string;
    password: string;
    full_name?: string;
    role: string;
    depot_id?: string;
    station_id?: string;
  }) {
    const response = await this.client.post('/v1/superadmin/users', data);
    return response.data;
  }

  async updateSuperadminUser(userId: string, data: {
    full_name?: string;
    role?: string;
    depot_id?: string;
    station_id?: string;
    is_active?: boolean;
    new_password?: string;
  }) {
    const response = await this.client.put(`/v1/superadmin/users/${userId}`, data);
    return response.data;
  }

  async deactivateSuperadminUser(userId: string) {
    const response = await this.client.delete(`/v1/superadmin/users/${userId}`);
    return response.data;
  }

  async initDepot(depotId: string, workerCount: number) {
    const response = await this.client.post(`/v1/superadmin/depots/${depotId}/init`, {
      worker_count: workerCount,
    });
    return response.data;
  }

  // Stock Movements
  async getTerritoriesByCycle(cycleId: string) {
    const response = await this.client.get(`/v1/inventory/territories/cycle/${cycleId}`);
    return response.data;
  }

  async getStockMovementsByCycle(
    cycleId: string,
    params?: {
      station_id?: string;
      territory_id?: string;
      dealer_id?: string;
      movement_type?: string;
      limit?: number;
      offset?: number;
    }
  ) {
    const response = await this.client.get(`/v1/inventory/movements/cycle/${cycleId}`, { params });
    return response.data as {
      cycle_id: string;
      movements: Array<{
        id: string;
        station_id: string;
        station_name: string;
        territory_name: string;
        product_id: string;
        product_code: string;
        product_name: string;
        loadsheet_id: string | null;
        package_number: string;
        sheet_no: string;
        dealer_id: string | null;
        dealer_code: string;
        dealer_name: string;
        movement_type: string;
        quantity_carton: number;
        quantity_pack: number;
        before_carton: number;
        before_pack: number;
        after_carton: number;
        after_pack: number;
        created_at: string;
        note: string | null;
      }>;
      count: number;
      total: number;
      limit: number;
      offset: number;
    };
  }
}

export const apiService = new ApiService();
