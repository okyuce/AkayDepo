# AkayDepo Deployment Guide

## Production Deployment

### 1. Sunucu Gereksinimleri

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB önerilir)
- 20GB disk alanı
- Ubuntu 20.04 LTS veya üzeri (önerilir)

### 2. İlk Kurulum

#### 2.1 Kodu Sunucuya Kopyala

```bash
git clone https://github.com/your-org/AkayDepo.git
cd AkayDepo
```

#### 2.2 Environment Değişkenlerini Ayarla

```bash
cp .env.prod.example .env.prod
nano .env.prod  # Değişkenleri düzenle
```

**Önemli:** Güvenli şifreler ve secret key'ler kullanın!

```bash
# Güvenli JWT secret oluştur
openssl rand -hex 32

# Güvenli database password oluştur
openssl rand -base64 24
```

#### 2.3 Docker Container'ları Başlat

```bash
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

#### 2.4 Database Migration

```bash
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

#### 2.5 Seed Data (Opsiyonel)

```bash
docker-compose -f docker-compose.prod.yml exec api python seed.py
```

### 3. SSL/HTTPS Kurulumu (Let's Encrypt)

#### 3.1 Certbot Kurulumu

```bash
sudo apt-get update
sudo apt-get install certbot
```

#### 3.2 SSL Sertifikası Al

```bash
sudo certbot certonly --standalone -d your-domain.com
```

#### 3.3 SSL Sertifikalarını Kopyala

```bash
mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
```

#### 3.4 Nginx Config'de HTTPS'i Aktif Et

`nginx/nginx.conf` dosyasında HTTPS server bloğunu uncomment et.

#### 3.5 Nginx'i Yeniden Başlat

```bash
docker-compose -f docker-compose.prod.yml restart nginx
```

#### 3.6 Auto-Renewal Kurulumu

```bash
sudo crontab -e
```

Aşağıdaki satırı ekle:

```
0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/your-domain.com/*.pem /path/to/AkayDepo/nginx/ssl/ && docker-compose -f /path/to/AkayDepo/docker-compose.prod.yml restart nginx
```

### 4. Güvenlik

#### 4.1 Firewall Ayarları

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

#### 4.2 Database Backup

Günlük backup scripti:

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/akaydepo"
mkdir -p $BACKUP_DIR

docker-compose -f /path/to/AkayDepo/docker-compose.prod.yml exec -T db \
  pg_dump -U akaydepo akaydepo | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# 30 günden eski backupları sil
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

Crontab'a ekle:

```bash
0 2 * * * /path/to/backup.sh
```

### 5. Monitoring

#### 5.1 Container Durumu

```bash
docker-compose -f docker-compose.prod.yml ps
```

#### 5.2 Logları İzle

```bash
# Tüm servisleri izle
docker-compose -f docker-compose.prod.yml logs -f

# Sadece API
docker-compose -f docker-compose.prod.yml logs -f api

# Sadece Frontend
docker-compose -f docker-compose.prod.yml logs -f web
```

#### 5.3 Kaynak Kullanımı

```bash
docker stats
```

### 6. Güncelleme

```bash
# Yeni kodu al
git pull

# Container'ları yeniden build et
docker-compose -f docker-compose.prod.yml build

# Servisleri yeniden başlat
docker-compose -f docker-compose.prod.yml up -d

# Migration çalıştır (gerekirse)
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### 7. Rollback

```bash
# Önceki versiyona dön
git checkout PREVIOUS_COMMIT_HASH

# Rebuild ve restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Database migration rollback (gerekirse)
docker-compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

### 8. Troubleshooting

#### Container Çalışmıyor

```bash
# Detaylı log
docker-compose -f docker-compose.prod.yml logs api

# Container içine gir
docker-compose -f docker-compose.prod.yml exec api /bin/bash
```

#### Database Bağlantı Sorunu

```bash
# Database container'ını kontrol et
docker-compose -f docker-compose.prod.yml exec db psql -U akaydepo -d akaydepo

# Connection test
docker-compose -f docker-compose.prod.yml exec api python -c "from app.core.database import engine; print(engine.connect())"
```

#### Disk Alanı Dolu

```bash
# Kullanılmayan Docker objelerini temizle
docker system prune -a --volumes
```

## URL'ler

- Frontend: `http://your-domain.com` veya `https://your-domain.com`
- API: `http://your-domain.com/api/` veya `https://your-domain.com/api/`
- API Docs: `http://your-domain.com/docs` veya `https://your-domain.com/docs`
- WebSocket: `ws://your-domain.com/ws/` veya `wss://your-domain.com/ws/`

## Varsayılan Kullanıcılar

**ÖNEMLİ:** Production'da şifreleri mutlaka değiştirin!

- Admin: `admin` / `admin123`
- Tablet 1-5: `tablet1-5` / `tablet123`

Şifreleri değiştirmek için `backend/app/api/auth.py` dosyasındaki `USERS` dictionary'sini güncelleyin veya database tabanlı kullanıcı sistemi ekleyin.

## Performans Optimizasyonu

### 1. API Workers

`docker-compose.prod.yml` dosyasında:

```yaml
command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

Worker sayısını CPU sayısına göre ayarlayın: `(2 x CPU_CORES) + 1`

### 2. Database Connection Pool

`backend/app/core/database.py` dosyasında:

```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10
)
```

### 3. Redis Cache

Redis kullanımı için `backend/app/services/` altına cache servisleri eklenebilir.

## Destek

Sorunlar için GitHub Issues kullanın veya [email@example.com](mailto:email@example.com) adresine yazın.
