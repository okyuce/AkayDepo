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

---

## Kalıcı Hafıza & Oturum Kuralları

> Oturumlar-arası hafıza içindir. Yukarıdaki proje bilgisi korunur; burası çalışma disiplinini tanımlar.

- **`WORKLOG.md`** — oturum oturum "ne yaptık / nerede kaldık". SessionStart hook'u oturum başında son kayıtları + hafıza indeksini otomatik yükler.
- **`memory/MEMORY.md`** — kalıcı kararlar/gerçekler indeksi (+ ayrı `.md` not dosyaları).
- **`worklog-archive/`** — WORKLOG büyüyünce eski kayıtların aylık arşivi.

### Kurallar
1. Oturum başında **WORKLOG.md**'nin en üstteki kaydını oku; kaldığımız yerden devam et.
2. **Her önemli adımdan sonra OTOMATİK** WORKLOG'a en üste kayıt ekle (`tarih · ne yapıldı · kararlar · sıradaki adım`). Önemli = görev/özellik bitti · çalışan kod/deploy · commit · teknik/mimari karar · bug fix · yön değişimi · engel · "kaydet" denmesi. Önemli değil (yazma) = okuma/arama/keşif, değişiklik yapmayan sohbet, tutmayan deneme. Pusula: *"Sonraki oturum bunu bilmeli mi?"*
3. Kalıcı karar çıkarsa `memory/`'ye not + **MEMORY.md**'ye tek satır indeks ekle.
4. **Arşivle:** WORKLOG 12+ kayıt olunca eskileri `worklog-archive/YYYY-MM.md`'ye taşı, aktifte son ~10 kalsın.
5. **Ara:** Eski bilgi için tüm arşivi yükleme — `worklog-archive/` içinde `grep` / `read` ile hedefli ara.
6. Yukarıdaki **"Önemli Kurallar" geçerli:** veritabanına dokunma (`backend/akaydepo.db` + production DB), deploy'da sadece `api`/`web` rebuild, commit mesajları Türkçe, "Generated with Claude Code" ekleme, commit/push/deploy öncesi onay al.
