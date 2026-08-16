# Lokal geliştirme ortamı (AkayDepo)

> Kalıcı karar. Ayrıntılı oturum kaydı: `WORKLOG.md` 2026-08-16.

## Kural: `.env.local`'e sabit IP YAZMA

`frontend/.env.local` içindeki `VITE_API_URL`'e makinenin o anki IP'sini yazmak
**üç kez** lokal ortamı bozdu (`10.129.47.100` → `192.168.1.3` → `192.168.1.36`).
DHCP adresi değiştirince sayfa açılıyor ama hiçbir API çağrısı gitmiyor —
sorun servis değil, konfigürasyon.

Doğrusu Bonjour/mDNS adı:

```
VITE_API_URL=http://oguzs-macbook-pro.local:8001
VITE_WS_URL=ws://oguzs-macbook-pro.local:8001
```

Bu ad Mac'te `127.0.0.1`'e, ağdaki iPad/tabletten makinenin güncel IP'sine
çözümlenir. IP değişse de çalışmaya devam eder.
Adı doğrulamak için: `scutil --get LocalHostName`.

`backend/.env` → `CORS_ORIGINS` listesinde de aynı ad bulunmalı
(8000 / 8050 / 8100 portları). Her iki dosya da git'e girmez.

## Servisleri çalıştırma (lokalde Docker yok)

```bash
# Backend — 8001  (--reload ŞART; bir kez 14 gün --reload'suz bayat kod döndü)
cd backend && venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Frontend — 8000
cd frontend && npm run dev
```

PostgreSQL (`akaydepo`, kullanıcı `okyuce`) ve Redis lokalde native çalışıyor,
Docker yok. Portlar: api 8001 · web 8000 · dashboard 8050 · superadmin 8100.

## Bilinen pürüz

Vite dev sunucusu `http://oguzs-macbook-pro.local:8000` isteğine **403** döner
(Vite host koruması). Sayfayı isimle açmak gerekirse `vite.config.ts`'e
`server.allowedHosts` eklenmeli — tracked dosya, dokunulmadı.
Tabletler sayfayı IP ile açıyor; API çağrısı zaten sabit isme gidiyor.
