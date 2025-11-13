# AkayDepo - Proje Özeti

## 📋 Genel Bakış

**AkayDepo**, PMI ISMS sipariş verilerini yöneten, territory bazlı istasyon planlama ve tablet üzerinden fiş görüntüleme sistemidir. Günde 3 döngü (14:00, 16:00, 17:00) ile çalışan bu sistem, Excel'den veri import eder, otomatik istasyon planlaması yapar ve tablet arayüzü ile yükleme sürecini takip eder.

## 🏗️ Mimari

### Tech Stack

**Backend:**
- FastAPI (Python 3.11)
- SQLModel (ORM)
- PostgreSQL 14
- Redis 7
- Alembic (migrations)
- JWT Authentication
- WebSocket (real-time)

**Frontend:**
- React 18
- TypeScript
- Vite (build tool)
- Zustand (state management)
- Axios (HTTP client)
- TailwindCSS (styling)
- React Router (routing)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (reverse proxy)
- Let's Encrypt (SSL)

### Servis Mimarisi

```
┌─────────────┐
│   Nginx     │ :80, :443
│  (Proxy)    │
└──────┬──────┘
       │
       ├──────────────┬──────────────┬─────────────┐
       ▼              ▼              ▼             ▼
  ┌────────┐    ┌─────────┐    ┌───────┐   ┌───────┐
  │ React  │    │ FastAPI │    │  DB   │   │ Redis │
  │ :8000  │    │  :8001  │    │ :5432 │   │ :6379 │
  └────────┘    └─────────┘    └───────┘   └───────┘
                     │
                     └─── WebSocket
```

## 📊 Veri Modeli

### Core Entities

1. **Cycle** - Döngü (günde 3 adet)
   - 14:00, 16:00, 17:00 saatlerinde
   - Excel import ile başlar
   - `active`, `completed`, `cancelled` durumları

2. **Territory** - Bölge (14 adet)
   - Display number: T01-T14
   - Dealer'ları gruplar
   - Total load hesaplanır (karton + paket/10)

3. **Dealer** - Bayi (53 adet)
   - Territory'e bağlı
   - Route order ile sıralanır
   - Her dealer için loadsheet oluşturulur

4. **Product** - Ürün (8 adet)
   - 1 Karton = 10 Paket kuralı
   - Order line'larda kullanılır

5. **Station** - İstasyon (5 adet)
   - Greedy algoritma ile dağıtım
   - Load balancing
   - Tablet görünümü

6. **StationAssignment** - İstasyon Atama
   - Territory → Station mapping
   - Cycle bazlı
   - Target load hesaplama

7. **Loadsheet** - Fiş
   - Package number: T07-B01
   - `pending`, `loaded` durumları
   - Revision desteği

8. **LoadCounter** - Sayaç Okuma
   - Araç sayacı
   - Cycle ve station bazlı

## 🔄 İş Akışı

### 1. Excel Import (Cycle Başlangıç)

```
Excel File → Parse → Validate → Create Cycle
    ↓
Territories, Dealers, Products, Orders
```

**Validasyon:**
- Gerekli kolonlar: RECPNO, DEALERCODEetc
- Data types
- Territory totals

### 2. Planlama (Station Assignment)

```
Cycle → Territories with Loads
    ↓
Greedy Algorithm
    ↓
Station Assignments
    ↓
Generate Loadsheets
```

**Algoritma:**
1. Territory'leri load'a göre sırala (büyükten küçüğe)
2. Her territory'yi en az yüklü istasyona ata
3. Unbalance kontrolü (threshold = avg × 1.5)
4. Gerekirse istasyon sayısını arttır

**Loadsheet Üretimi:**
- Dealer route order'a göre sıralama
- Package numbering: T{display_num}-B{seq}
- Her dealer için ayrı fiş

### 3. Tablet Görünümü

```
Station Login → WebSocket Connect
    ↓
Display Territories & Loadsheets
    ↓
Select Loadsheet → Show Detail
    ↓
Mark as Completed → Update DB
    ↓
WebSocket Broadcast → Refresh UI
```

**Özellikler:**
- Real-time progress bar
- Territory-based grouping
- Revision indicator
- Counter reading

### 4. Revision Sistemi

```
Cycle N → Complete
    ↓
Cycle N+1 → Import
    ↓
Compare with Cycle N
    ↓
Detect Changes → Create Revision Loadsheets
```

**Revision Detection:**
- Dealer-Product level diff
- Addition vs Reduction
- Parent loadsheet reference

## 🔐 Authentication

### JWT Token Flow

```
Login (username/password)
    ↓
Generate JWT (exp: 8 hours)
    ↓
Store in localStorage
    ↓
Include in API requests (Bearer token)
    ↓
Verify & Decode on backend
```

**User Roles:**
- `admin` - Full access
- `tablet` - Station-specific access

## 🌐 API Structure

### REST Endpoints

```
/v1/
├── auth/
│   ├── login
│   ├── logout
│   └── me
├── cycles/
│   ├── import
│   ├── {id}/status
│   ├── {id}/cancel-pending
│   └── {id}/plan
├── loadsheets/
│   ├── station/{station_id}
│   ├── {id}
│   └── {id}/complete
└── counters/
    ├── /
    ├── cycle/{cycle_id}
    └── station/{station_id}/latest
```

### WebSocket Channels

```
/ws/
├── station/{station_id}  # Tablet updates
└── cycle                  # Admin dashboard
```

**Message Types:**
- `loadsheet_completed` - Fiş tamamlandı
- `counter_reading` - Sayaç okundu
- `cycle_completed` - Döngü tamamlandı

## 📱 Frontend Pages

### 1. Login Page (`/login`)
- Username/password form
- JWT token storage
- Redirect to dashboard

### 2. Excel Upload Page (`/`)
- File upload
- Cycle creation
- Station planning (num_stations input)
- Plan result display

### 3. Tablet Page (`/tablet/:stationId`)
- Territory list
- Loadsheet cards
- Progress tracking
- Loadsheet detail modal
- Complete button
- WebSocket updates

## 🧪 Testing

### Backend Tests

```
tests/
├── conftest.py         # Fixtures (session, client, auth)
├── test_auth.py        # Auth API tests
└── test_api.py         # Basic API tests
```

**Test Database:** In-memory SQLite

**Fixtures:**
- `session` - DB session
- `client` - TestClient
- `auth_token` - JWT token
- `auth_headers` - Authorization headers

### Frontend Tests

Frontend testleri TODO - Jest + React Testing Library önerilir.

## 🚀 Deployment

### Development

```bash
docker-compose up -d
make migrate
make seed
```

### Production

```bash
# Setup
cp .env.prod.example .env.prod
nano .env.prod  # Edit variables

# Deploy
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Migration
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### SSL/HTTPS

```bash
# Certbot
sudo certbot certonly --standalone -d your-domain.com

# Copy certs
mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/*.pem nginx/ssl/

# Enable HTTPS in nginx.conf
# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

## 📊 Database Schema

### Key Tables

```sql
-- Cycles
cycles (id, status, imported_at)

-- Territories
territories (id, code, display_number, name)

-- Dealers
dealers (id, code, name, territory_id, route_order)

-- Products
products (id, code, name, pack_per_carton)

-- Orders
orders (id, cycle_id, territory_id, dealer_id)

-- Order Lines
order_lines (id, order_id, product_id, qty_carton, qty_pack)

-- Stations
stations (id, name)

-- Station Assignments
station_assignments (id, cycle_id, station_id, territory_id, target_total_carton)

-- Loadsheets
loadsheets (id, assignment_id, dealer_id, package_number, status, is_revision, parent_loadsheet_id, loaded_at)

-- Loadsheet Lines
loadsheet_lines (id, loadsheet_id, product_id, qty_carton, qty_pack)

-- Load Counters
load_counters (id, cycle_id, station_id, counter_value, recorded_at)

-- Revision Diffs
revision_diffs (id, current_cycle_id, previous_cycle_id, dealer_id, product_id, diff_carton, diff_pack)
```

### Relationships

```
Cycle 1──N Order 1──N OrderLine N──1 Product
   │
   └── 1──N StationAssignment N──1 Station
            │
            └── 1──N Loadsheet N──1 Dealer
                      │
                      └── 1──N LoadsheetLine
```

## 🔧 Configuration

### Environment Variables

**Backend (.env):**
```
DATABASE_URL=postgresql://user:pass@db:5432/akaydepo
REDIS_URL=redis://redis:6379/0
JWT_SECRET=your-secret-key
CORS_ORIGINS=http://localhost:8000
ENVIRONMENT=development
```

**Frontend (.env):**
```
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

## 📈 Performance Considerations

### Backend
- **Workers:** 4 uvicorn workers (production)
- **Connection Pool:** pool_size=20, max_overflow=10
- **Redis:** Caching layer (future enhancement)

### Frontend
- **Code Splitting:** Vite automatic chunking
- **Lazy Loading:** React.lazy for routes
- **WebSocket:** Auto-reconnect with exponential backoff

### Database
- **Indexes:** All foreign keys indexed
- **Query Optimization:** SQLModel select() with eager loading

## 🐛 Known Issues & Future Enhancements

### TODO
- [ ] Frontend tests (Jest + RTL)
- [ ] E2E tests (Playwright)
- [ ] Redis caching implementation
- [ ] Database user management (move from hardcoded)
- [ ] Excel template download
- [ ] Historical data export
- [ ] Admin dashboard (cycle monitoring)
- [ ] Email notifications
- [ ] Barcode scanning support

### Limitations
- No authentication for WebSocket (assumes trusted network)
- No rate limiting
- Single database instance (no replication)
- Manual station count input

## 📞 Support & Documentation

- **API Docs:** http://localhost:8001/docs
- **Detailed Specs:** `depo-transfer-docs/` folder
- **Deployment Guide:** `DEPLOYMENT.md`
- **Test Guide:** `backend/tests/README.md`

## 🎯 Key Metrics

- **Total Territories:** 14
- **Total Dealers:** 53
- **Total Products:** 8
- **Stations:** 5 (configurable)
- **Daily Cycles:** 3 (14:00, 16:00, 17:00)
- **Conversion Rate:** 1 Karton = 10 Paket

## 📝 License

Proprietary - Internal use only.
