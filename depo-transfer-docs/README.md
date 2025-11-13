# Depo Transfer Uygulaması – Dokümantasyon

Bu depo transfer sistemi, PMI ISMS siparişlerinden gelen veriyi (gün içinde 14:00 ve 16:00 çekimleri), depo istasyon planlamasına dönüştürür, istasyon bazlı **yükleme fişleri** üretir ve her yüklemeyi sayım (count) döngülerinde takip eder. Bu klasördeki `.md` belgeler **kaynak sözleşmeler** olup geliştirme sürecinde kanoniktir.

- Kaynak Excel: `e-sipariş.xlsx`
- Veri sayfaları: `Recipe2` (güncel), `Recip1` (revizyon/önceki), `Hazırlık`, `Sipariş Yazdır`
- Toplam sipariş: **53**, bayi: **53**, territory: **14**, satır: **532**
- Territory örnekleri: TERR030701-Bosna-Hersek, TERR030702-Kadınlarpazarı, TERR030703-Sanayi, TERR030704-Mevlana, TERR030705-Meram, TERR030707-Sille, TERR030708-Form, TERR030709-Şeker-Tekke

> Hedef: **Web tabanlı** (React) bir arayüz ve **FastAPI + PostgreSQL** arka uç ile; döngü sistemi, istasyon planlama, revizyon farkları, sayım döngüleri ve tablet üzerinden fiş gösterimi.

## Temel Konseptler
- **Döngü Sistemi:** Her Excel yüklemesi (14:00, 16:00, 17:00) bağımsız bir döngü oluşturur
- **Revizyon Tracking:** Cycle-to-cycle değişiklikler otomatik tespit edilir
- **Paket Numarası:** T07-B01 formatında (Territory + Bayi sırası)
- **Sayım Döngüsü:** C1→C2→C3 (territory bazında)
- **Dönüşüm:** 1 Karton = 10 Paket

## Doküman Sıralaması
1. `README.md` (bu dosya) — Genel bakış
2. `CYCLE_MANAGEMENT.md` — Döngü sistemi detayları (ÖNEM: İlk oku!)
3. `DATA_MODEL.md` — Veritabanı şeması
4. `ALGO_STATIONS.md` — İstasyon paylaştırma algoritması
5. `UI_SPEC.md` — Tablet arayüzü ve React bileşenleri
6. `BACKEND_API_SPEC.md` — API endpoint'leri
7. `WORKLIST.md` — Fazlar ve geliştirme sıralaması

İlk kuruluma ve sıralı çalışmaya `WORKLIST.md` üzerinden başlayın.
