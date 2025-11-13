# WORKLIST

Bu listedeki fazları **sırayla** uygulayın. Her faz tamamlandığında `DONE` etiketi ekleyin. Kod ajanları için bu belge tek otoritedir.

## FAZ 0 – Proje İskeleleri
- [ ] Repo iskeleti (backend `fastapi`, frontend `react-vite`, `docker-compose`)
- [ ] Ortak `/.env.example` şablonu
- [ ] `make` komutları (dev, test, lint, format, up/down)

## FAZ 1 – Veri Modeli & Migrasyonlar
- [ ] `DATA_MODEL.md` şemasına göre PostgreSQL tabloları
- [ ] Alembic migrasyonları
- [ ] Örnek veriler için `seed` scripti

## FAZ 2 – Döngü Sistemi + ISMS İçe Aktarım
- [ ] Cycles tablosu ve döngü yönetimi (bağımsız döngüler)
- [ ] `PIPELINES.md` gereği Excel içe aktarımı (Recipe2, Recip1)
- [ ] Döngü tamamlanma kontrolü (gri fiş olmamalı)
- [ ] Revizyon tespiti (cycle-to-cycle diff)
- [ ] `revision_diffs` tablosu ve değişiklik tracking
- [ ] `EXCEL_MAPPING.md` doğrulama testleri
- [ ] Paket→Karton dönüşümü (1 karton = 10 paket)

## FAZ 3 – Planlama & İstasyon Paylaştırma
- [ ] `UI_SPEC.md` ve `ALGO_STATIONS.md` göre istasyon sayısı = aktif depo görevlisi
- [ ] Territory yük dengesi (ürün toplamları yakın) — greedy heuristik
- [ ] Dengesizlik kontrolü (büyük territory tespiti, eşik: avg × 1.5)
- [ ] Kullanıcı uyarısı ve istasyon sayısı önerisi
- [ ] Sayım döngüsü (C1..Ck) hesaplayıcı
- [ ] Territory numaralandırma (T01, T07, T27...)
- [ ] Paket numarası üretimi (T07-B01, T07-B01-R)

## FAZ 4 – API'ler
- [ ] `BACKEND_API_SPEC.md` tüm endpoint'leri
- [ ] Döngü API'leri (import, status, cancel-pending)
- [ ] Planlama API'leri (plan, warnings)
- [ ] Tablet API'leri (station fişleri, progress)
- [ ] Revizyon API'leri (diff, changes)
- [ ] Sayım API'leri (counters)
- [ ] WebSocket ile canlı durum (loadsheet_completed, territory_completed)

## FAZ 5 – Tablet Arayüzü (React)
- [ ] Excel yükleme paneli (drag & drop, run_time seçimi)
- [ ] Döngü tamamlanma uyarısı (gri fiş kontrolü)
- [ ] Planlama paneli (depocu sayısı, dengesizlik uyarısı)
- [ ] Tablet görünümü (istasyon bazlı filtreleme)
- [ ] Territory gruplama ve progress bar
- [ ] Fiş kartları (T07-B01 gösterimi, renk kodları)
- [ ] Fiş detay modalı (standart + revizyon)
- [ ] Revizyon fişi gösterimi (yeşil/kırmızı değişiklikler)
- [ ] Sayım görüntüleme (C1→C2→C3 + progress)
- [ ] "Yükleme Tamamlandı" butonu işlevi
- [ ] WebSocket entegrasyonu (canlı güncelleme)

## FAZ 6 – Testler
- [ ] `TEST_PLAN.md` Smoke testleri
- [ ] Döngü tamamlanma kuralları testi
- [ ] Revizyon diff hesaplama testi
- [ ] Dengesizlik kontrolü testi
- [ ] Paket numarası üretimi testi
- [ ] Sayım döngüsü hesaplama testi
- [ ] Örnek veriyle uçtan uca test (e-sipariş.xlsx)
- [ ] Performans (100k satıra kadar)

## FAZ 7 – Dağıtım
- [ ] `DEPLOYMENT.md` (Docker, Compose, prod notları)
- [ ] Versiyonlama & Sürüm notları
