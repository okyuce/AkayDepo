# Şema değişikliği ve deploy — ALEMBIC PROD'DA OTOMATİK ÇALIŞMAZ

> Her yeni kolon/tablo eklemeden önce bu notu oku. 31.08.2026'da kapanış
> kontrolü eklenirken bulundu ve iki gerçek hataya yol açacaktı.

## Gerçek

`docker-compose.prod.yml`'de `api` servisi doğrudan **gunicorn** başlatıyor;
**hiçbir yerde `alembic upgrade head` yok.** CLAUDE.md'deki deploy prosedüründe
de yok (`git pull` + `build` + `up -d`).

`main.py` startup'ında `create_db_and_tables()` (= `SQLModel.metadata.create_all`)
çalışıyor. Bu:
- **YENİ TABLO oluşturur** ✅ (ve SQLModel `foreign_key=`'den **FK'ları da kurar**)
- **MEVCUT TABLOYA KOLON EKLEMEZ** ❌

## Sonuç: mevcut tabloya kolon eklersen

Migration elle çalıştırılmazsa o tabloya giden **her SELECT patlar** —
SQLModel modeldeki tüm kolonları listeliyor. `loadsheets`'e kolon eklemek
tablet dahil tüm uygulamayı düşürür.

## Kural

1. **Alembic migration yaz** (denetim izi + doğru şema).
2. **AYRICA `main.py` startup'ına idempotent güvence koy:**
   ```python
   session.execute(text(
       "ALTER TABLE <tablo> ADD COLUMN IF NOT EXISTS <kolon> <tip> NOT NULL DEFAULT <x>"
   ))
   ```
   try/except içinde, `create_db_and_tables()`'tan hemen sonra.
   Örnek: `loadsheets.cancelled_by_closing` (bkz. `main.py` lifespan).
3. **Migration'ı savunmacı yaz** — güvence zaten eklemiş olabilir:
   `sa.inspect(op.get_bind())` ile kolon/tablo/index varlığını kontrol et,
   varsa atla. Yoksa sonradan `alembic upgrade head` "already exists" ile patlar.
4. **Migration'daki FK'ları `create_all` ile eşitle.** `create_all` FK kuruyor,
   elle yazılan migration kurmazsa iki ortam arasında şema farkı oluşur.
5. **Yeni tablo cycle'a bağlıysa** `cycles.py:/cancel-pending` ("Yeni Döngü
   Başlat") silme sırasına ekle — `cycles` DELETE'inden ÖNCE. Unutulursa
   FK ihlaliyle yeni döngü başlatılamaz.

## TUZAK: 8 gunicorn worker'ı create_all'da YARIŞIYOR

Prod'da `api` 8 worker ile çalışıyor ve **her worker lifespan'i ayrı çalıştırıyor.**
Yaratılacak **yeni bir tablo** varsa hepsi aynı anda `CREATE TABLE` deniyor ve
Postgres şunu veriyor:

```
psycopg2.errors.UniqueViolation: duplicate key value violates unique
constraint "pg_type_typname_nsp_index"
[ERROR] Application startup failed. Exiting.
[ERROR] Worker (pid:7) exited with code 3
```

31.08.2026 deploy'unda gerçekleşti: 5 worker çöktü, gunicorn yeniden başlattı,
ikinci denemede tablo zaten var olduğu için açıldılar → **~13 saniye kapasite
düşüşü**, veri kaybı yok. Lokalde `mp.Barrier` ile birebir üretildi:
eski yol **7/8 worker çöküyor**, advisory lock'lu yeni yol **8/8 sağlam**.

**Çözüm — `main.py:_schema_lock()`:** tüm DDL `pg_advisory_lock` içinde,
tek worker yapar, diğerleri bekler. Yeni bir şema işi eklerken **oraya** ekle,
lifespan'e doğrudan DDL yazma.

## Test etme yöntemi

Migration'sız bir DB kopyası oluştur, `TestClient(app)` ile lifespan'i çalıştır,
kolonun/tablonun oluştuğunu ve mevcut endpoint'lerin 200 döndüğünü doğrula:
```bash
createdb -T akaydepo akaydepo_deploytest   # migration YOK
DATABASE_URL=...akaydepo_deploytest python test_deploy.py
```
İlgili: [[siparis-kontrol-kapanis]], [[lokal-gelistirme]]
