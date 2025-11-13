# AkayDepo - Depo Transfer Yönetim Sistemi

PMI ISMS sipariş verilerini yöneten, territory bazlı istasyon planlama ve tablet üzerinden fiş görüntüleme sistemi.

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Docker Desktop (Mac için)
- Make (zaten yüklü)

### İlk Kurulum

```bash
# 1. Servisleri başlat
make up

# 2. Veritabanı migrasyonunu çalıştır (FAZ 1'den sonra)
make migrate

# 3. Test verisi yükle
make seed
```

### Erişim

- **Frontend:** http://localhost:8000
- **Backend API:** http://localhost:8001
- **API Docs:** http://localhost:8001/docs

## 📋 Make Komutları

```bash
make help       # Tüm komutları göster
make up         # Servisleri başlat (arka planda)
make down       # Servisleri durdur
make dev        # Geliştirme modunda başlat (logları göster)
make logs       # Tüm logları izle
make logs-api   # Sadece API logları
make logs-web   # Sadece Frontend logları
make migrate    # Veritabanı migrasyonu
make seed       # Test verisi yükle
make reset-db   # Veritabanını sıfırla
make test       # Testleri çalıştır
make clean      # Temizlik yap
```

## 🏗 Proje Yapısı

```
AkayDepo/
├── backend/              # FastAPI Backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── models/      # SQLModel modelleri
│   │   ├── services/    # İş mantığı
│   │   ├── core/        # Config, auth
│   │   └── main.py
│   ├── alembic/         # Migrasyonlar
│   └── requirements.txt
│
├── frontend/            # React + Vite Frontend
│   ├── src/
│   │   ├── components/  # React bileşenleri
│   │   ├── pages/       # Sayfalar
│   │   ├── hooks/       # Custom hooks
│   │   └── services/    # API çağrıları
│   └── package.json
│
├── depo-transfer-docs/  # Dokümantasyon
│   ├── README.md
│   ├── CYCLE_MANAGEMENT.md
│   ├── DATA_MODEL.md
│   ├── BACKEND_API_SPEC.md
│   └── ...
│
├── docker-compose.yml
├── Makefile
└── .env.example
```

## 📚 Dokümantasyon

Detaylı dokümantasyon için `depo-transfer-docs/` klasörüne bakın.

**Önemli Dosyalar:**
- `CYCLE_MANAGEMENT.md` - Döngü sistemi (İLK OKU!)
- `DATA_MODEL.md` - Veritabanı şeması
- `BACKEND_API_SPEC.md` - API referansı
- `UI_SPEC.md` - Frontend spesifikasyonu
- `WORKLIST.md` - Geliştirme fazları

## 🔧 Geliştirme

### Hot Reload

Kod değişiklikleriniz otomatik olarak yansır:
- **Backend:** FastAPI `--reload` ile çalışır
- **Frontend:** Vite HMR (Hot Module Replacement)

### Veritabanı

```bash
# Migration oluştur
docker-compose exec api alembic revision --autogenerate -m "açıklama"

# Migration uygula
make migrate

# Veritabanını sıfırla
make reset-db
```

## 🎯 Geliştirme Fazları

- [x] **FAZ 0:** Proje İskeleti ✅
- [x] **FAZ 1:** Veri Modeli & Migrasyonlar ✅
- [x] **FAZ 2:** Excel Import + Döngü Sistemi ✅
- [x] **FAZ 3:** İstasyon Planlama ✅
- [x] **FAZ 4:** Backend API'ler (Auth, Loadsheets, Counters, WebSocket) ✅
- [x] **FAZ 5:** Tablet Arayüzü (React Pages & Components) ✅
- [x] **FAZ 6:** Testler (Backend Unit Tests) ✅
- [x] **FAZ 7:** Deployment (Production Docker, Nginx, SSL Guide) ✅

## 🐳 Docker Servisleri

- **api** (8001): FastAPI Backend
- **web** (8000): React Frontend
- **db** (5432): PostgreSQL 14
- **redis** (6379): Redis 7

## 🔑 Test Kullanıcıları

Sistem JWT authentication kullanır. Test kullanıcıları:

- **Admin:** `admin` / `admin123`
- **Tablet 1:** `tablet1` / `tablet123`
- **Tablet 2:** `tablet2` / `tablet123`
- **Tablet 3:** `tablet3` / `tablet123`
- **Tablet 4:** `tablet4` / `tablet123`
- **Tablet 5:** `tablet5` / `tablet123`

## 📡 API Endpoints

### Auth
- `POST /v1/auth/login` - Giriş yap
- `GET /v1/auth/me` - Kullanıcı bilgisi
- `POST /v1/auth/logout` - Çıkış

### Cycles
- `POST /v1/cycles/import` - Excel yükle
- `GET /v1/cycles/{id}/status` - Döngü durumu
- `POST /v1/cycles/{id}/cancel-pending` - Bekleyenleri iptal et

### Planning
- `POST /v1/cycles/{id}/plan` - Planlama oluştur
- `GET /v1/cycles/{id}/plan` - Planlama getir

### Loadsheets (Tablet)
- `GET /v1/loadsheets/station/{station_id}` - İstasyon fişleri
- `GET /v1/loadsheets/{id}` - Fiş detayı
- `POST /v1/loadsheets/{id}/complete` - Fişi tamamla

### Counters
- `POST /v1/counters/` - Sayaç okuma kaydet
- `GET /v1/counters/cycle/{cycle_id}` - Döngü sayaçları
- `GET /v1/counters/station/{station_id}/latest` - Son sayaç

### WebSocket
- `WS /ws/station/{station_id}` - İstasyon real-time updates
- `WS /ws/cycle` - Döngü izleme (admin)

API dokümantasyonu için: http://localhost:8001/docs

## 📝 Notlar

- Port değişikliği: Frontend 8000, Backend 8001
- 1 Karton = 10 Paket (dönüşüm kuralı)
- Döngü sistemi: 14:00, 16:00, 17:00 (3 çekim)
- Paket numarası formatı: T07-B01 (Territory display number + Dealer sequence)
- WebSocket real-time updates için kullanılır

## 🚀 Production Deployment

Production deployment için `DEPLOYMENT.md` dosyasına bakın.

```bash
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## 📞 Destek

Sorular için: `depo-transfer-docs/` klasöründeki ilgili MD dosyasına bakın.
