# AkayDepo - PMI ISMS Sipariş Yönetim Sistemi

Tobacco ürünleri için depo yönetimi, sipariş dağıtımı ve tablet tabanlı yükleme takip sistemi.

## Proje Yapısı

```
├── backend/          # FastAPI + SQLModel
├── frontend/         # React 18 + TypeScript + Vite + TailwindCSS
├── docker-compose.yml
└── docker-compose.prod.yml
```

## Teknolojiler

- **Backend:** FastAPI, SQLModel, PostgreSQL, Redis, Celery
- **Frontend:** React 18, TypeScript, Vite, TailwindCSS
- **Infra:** Docker Compose, Nginx

## Lokal Geliştirme

```bash
# Backend (port 8001)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Frontend (port 8000)
cd frontend
npm run dev
```

PostgreSQL lokal olarak çalışıyor (Docker yok).

## Production Deployment

- **Sunucu:** 193.106.196.60
- **Proje dizini:** /opt/akaydepo
- **Environment:** .env.prod dosyası kullanılır

```bash
# Sunucuda güncelleme
cd /opt/akaydepo
git pull origin main
docker-compose -f docker-compose.prod.yml --env-file .env.prod build api web
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d api web
```

## Önemli Kurallar

1. **Veritabanı verilerine dokunma!** - Deployment sırasında sadece api ve web container'ları rebuild et
2. **Commit mesajları Türkçe** olmalı
3. **TypeScript strict mode** aktif - kullanılmayan değişkenler hata verir
4. **"Generated with Claude Code" yazma** - commit mesajlarına ekleme

## Ana Modüller

- **Cycles:** Döngü yönetimi (Excel import)
- **Loadsheets:** Yükleme fişleri
- **Stations:** İstasyon yönetimi
- **Territories:** Bölge atamaları
- **Products:** Ürün kataloğu
- **Dealers:** Bayi yönetimi

## API Portları

- Backend API: 8001
- Frontend Dev: 8000
- Production Nginx: 8005
