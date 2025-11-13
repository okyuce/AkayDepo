# CYCLE_MANAGEMENT.md

Döngü (Cycle) sistemi, günlük sipariş akışının yönetimi için temel mekanizmadır.

## Döngü Kavramı

Her Excel yüklemesi **yeni bir döngü** başlatır:
- **Döngü-1:** 14:00 çekimi (ilk sipariş)
- **Döngü-2:** 16:00 çekimi (revizyon + yeni siparişler)
- **Döngü-3:** 17:00 çekimi (kapanış)

### Önemli Prensipler
1. **Bağımsızlık:** Her döngü kendi istasyon planını oluşturur
2. **Tamamlanma Şartı:** Yeni döngü başlatmak için önceki döngü tamamlanmalı
3. **Revizyon Tracking:** Cycle-to-cycle değişiklikler otomatik tespit edilir

---

## Döngü Durumları

| Durum | Açıklama |
|-------|----------|
| `active` | Aktif döngü, fişler hazırlanıyor |
| `completed` | Tüm fişler tamamlandı, döngü bitti |
| `archived` | Eski döngü, arşivlendi |

---

## Döngü Yaşam Döngüsü

### 1. Döngü Başlatma (Excel Import)

**Adımlar:**
1. Sistem kullanıcısı Excel dosyasını yükler
2. `run_time` seçer: "14:00", "16:00", "17:00"
3. Sistem kontrol eder:
   - Önceki döngü tamamlandı mı? (gri fiş var mı?)
   - Eğer gri fiş varsa → UYARI göster

**API:**
```
POST /v1/cycles/import
Body: {
  "file": <Excel>,
  "run_time": "14:00",
  "plan_date": "2025-11-07"
}
```

**Sistem İşlemleri:**
1. Yeni `cycle` kaydı oluştur (status: "active")
2. Excel verilerini parse et
3. Territories, dealers, products tablolarını güncelle (upsert)
4. Orders ve order_lines oluştur (cycle_id ile ilişkilendir)
5. Revizyon tespiti (eğer önceki döngü varsa)

---

### 2. Revizyon Tespiti

**Algoritma:**
```python
def detect_revisions(cycle_from, cycle_to):
    # Aynı sipariş kodu + bayi kodu olan siparişleri bul
    orders_from = get_orders(cycle_from)
    orders_to = get_orders(cycle_to)
    
    for order_to in orders_to:
        order_from = find_matching_order(orders_from, order_to)
        
        if order_from:
            # Ürün bazında karşılaştırma
            for line_to in order_to.lines:
                line_from = find_matching_line(order_from.lines, line_to.product_id)
                
                if line_from:
                    delta = line_to.qty_carton - line_from.qty_carton
                    
                    if delta != 0:
                        create_revision_diff(
                            cycle_from_id=cycle_from.id,
                            cycle_to_id=cycle_to.id,
                            product_id=line_to.product_id,
                            qty_old=line_from.qty_carton,
                            qty_new=line_to.qty_carton,
                            qty_change=delta,
                            change_type="addition" if delta > 0 else "reduction"
                        )
                else:
                    # Yeni ürün
                    create_revision_diff(
                        change_type="new_product",
                        qty_change=line_to.qty_carton
                    )
```

---

### 3. Planlama

**Adımlar:**
1. Depocu sayısı gir (örn: 5)
2. Sistem territory'leri yük dengesine göre dağıtır
3. Dengesizlik kontrolü:
   - Ortalama yük = Toplam karton / İstasyon sayısı
   - Eşik = Ortalama yük × 1.5
   - Eğer bir territory > Eşik → UYARI
4. Kullanıcı seçeneği:
   - [Önerilen istasyon sayısını kabul et]
   - [Devam et]
   - [Manuel ayarla]

**API:**
```
POST /v1/cycles/{cycle_id}/plan
Body: {
  "worker_count": 5,
  "force_station_count": null,
  "method": "greedy"
}
```

---

### 4. Fiş Üretimi

**Sistem İşlemleri:**
1. Her istasyon için territory'leri al
2. Her territory'nin bayilerini sırala (BayiRutSırası)
3. Her bayi için bir `loadsheet` oluştur:
   - `package_number`: Territory + bayi sırası (T07-B01)
   - `cycle_id`: İlgili döngü
   - `status`: "pending"

**Revizyon Fişi:**
- Eğer `revision_diff` var ise:
  - İkinci bir loadsheet oluştur (is_revision=true)
  - `package_number`: T07-B01-R (suffix: -R)
  - `parent_loadsheet_id`: Orjinal fişin ID'si

---

### 5. Tablet Görünümü

**Depocu İşlemleri:**
1. Kendi istasyonunun fişlerini görür
2. Territory bazlı gruplama
3. Fiş kartlarına tıklayarak detay görür
4. "Yükleme Tamamlandı" butonuna basar
5. Fiş yeşile döner (status: "loaded")

**Territory Tamamlanma:**
- Bir territory'nin tüm fişleri "loaded" olduğunda:
  - Sayım güncellenir (C1 → C2)
  - Territory "completed" olarak işaretlenir

---

### 6. Döngü Tamamlanma

**Şartlar:**
1. Tüm fişler "loaded" (yeşil) olmalı
2. Veya eksik fişler "cancelled" olmalı
3. Gri fiş kaldığı sürece yeni döngü başlatılamaz

**Kontrol:**
```
GET /v1/cycles/{cycle_id}/status

Response: {
  "can_start_next_cycle": false,  # pending > 0 ise false
  "pending_loadsheets": 3,
  "warnings": ["3 fiş henüz tamamlanmadı"]
}
```

**Eksik Fişleri İptal:**
```
POST /v1/cycles/{cycle_id}/cancel-pending

# Tüm pending fişleri "cancelled" yap
# can_start_next_cycle = true
```

---

## Döngü Senaryoları

### Senaryo 1: Standart Akış (Revizyon Yok)

```
14:00 - Döngü-1
├─ Excel import
├─ İstasyon planı (5 istasyon)
├─ Fiş üretimi (53 fiş)
├─ Depocular çalışır
├─ Tüm fişler yeşil
└─ Döngü-1 completed

16:00 - Döngü-2
├─ Excel import (yeni siparişler)
├─ Revizyon kontrolü: YOK
├─ YENİ istasyon planı (6 istasyon, daha fazla sipariş)
├─ Fiş üretimi (61 fiş)
├─ Depocular çalışır
├─ Tüm fişler yeşil
└─ Döngü-2 completed

17:00 - Döngü-3 (Kapanış)
├─ Excel import (son siparişler)
├─ Revizyon kontrolü: VAR (12 revizyon)
├─ YENİ istasyon planı (6 istasyon)
├─ Fiş üretimi (68 fiş + 12 revizyon fişi)
├─ Depocular çalışır
├─ Tüm fişler yeşil
└─ Döngü-3 completed → KAPANIŞ RAPORU
```

---

### Senaryo 2: Revizyon Var

```
14:00 - Döngü-1
├─ Bayi: NUR BAKKAL
│   └─ PL Midnight: 2 karton
└─ Fiş: T07-B01 (pending)

16:00 - Döngü-2
├─ Revizyon tespiti:
│   └─ Bayi: NUR BAKKAL
│       ├─ PL Midnight: 2 → 5 (+3)
│       └─ MLR Edge: 0 → 10 (+10, yeni)
│
├─ İki fiş oluşturulur:
│   ├─ T07-B01 (orjinal, 14:00'dan kalma, zaten yeşil)
│   └─ T07-B01-R (revizyon, pending)
│
└─ Depocu işlemi:
    ├─ Orjinal paket hazır
    ├─ Revizyon fişini açar
    ├─ +3 PL Midnight ekler
    ├─ +10 MLR Edge ekler
    └─ Revizyon fişi yeşil
```

---

### Senaryo 3: Gri Fiş Kaldı (Hata)

```
14:00 - Döngü-1
├─ 53 fiş oluşturuldu
├─ 50 fiş yeşil
└─ 3 fiş gri (pending)

16:00 - Yeni Excel yüklenmeye çalışılıyor
├─ Sistem kontrolü:
│   └─ can_start_next_cycle = false
│
└─ UYARI:
    "Döngü-1 tamamlanmadı. 3 fiş henüz yüklenmedi."
    
    Seçenekler:
    [1] Eksik fişleri göster ve tamamla
    [2] Eksik fişleri iptal et
    [3] İptal (yeni döngü başlatma)
```

**Kullanıcı Seçeneği 2:**
```
POST /v1/cycles/{cycle_1_id}/cancel-pending

# 3 fiş "cancelled" yapılır
# can_start_next_cycle = true
# Şimdi Döngü-2 başlatılabilir
```

---

## Döngü İstatistikleri

### Örnek Rapor (Döngü-3, 17:00 Kapanış)

```
╔═══════════════════════════════════════════════════════╗
║ 17:00 KAPANIŞ RAPORU                                 ║
╠═══════════════════════════════════════════════════════╣
║ Tarih: 07.11.2025                                    ║
║ Toplam Döngü: 3                                      ║
║                                                       ║
║ DÖNGÜ-1 (14:00):                                     ║
║ - Sipariş: 53                                        ║
║ - Bayi: 53                                           ║
║ - Karton: 1675                                       ║
║ - İstasyon: 5                                        ║
║ - Revizyon: 0                                        ║
║                                                       ║
║ DÖNGÜ-2 (16:00):                                     ║
║ - Sipariş: 61 (+8 yeni)                             ║
║ - Bayi: 58 (+5 yeni)                                ║
║ - Karton: 1842 (+167)                               ║
║ - İstasyon: 6                                        ║
║ - Revizyon: 3                                        ║
║                                                       ║
║ DÖNGÜ-3 (17:00 - KAPANIŞ):                          ║
║ - Sipariş: 68 (+7 yeni)                             ║
║ - Bayi: 61 (+3 yeni)                                ║
║ - Karton: 1892 (+50)                                ║
║ - İstasyon: 6                                        ║
║ - Revizyon: 12                                       ║
║                                                       ║
║ GENEL TOPLAM:                                        ║
║ - Hazır Paket: 61 + 15 revizyon = 76 paket          ║
║ - Toplam Karton: 1892                               ║
║ - Eksik/İptal: 0                                    ║
║                                                       ║
║ ✅ Transfer için hazır                               ║
║ Araç yükleme saati: 08:00 (ertesi gün)              ║
╚═══════════════════════════════════════════════════════╝
```

---

## Veritabanı İlişkileri

```sql
-- Döngü
cycles
  ├─ orders (cycle_id)
  │   └─ order_lines
  │
  ├─ station_assignments (cycle_id)
  │   └─ loadsheets (cycle_id, assignment_id)
  │       └─ loadsheet_lines
  │
  └─ revision_diffs (cycle_from_id, cycle_to_id)

-- Örnek sorgular

-- Döngü-2'nin tüm revizyonları
SELECT * FROM revision_diffs
WHERE cycle_to_id = 'cycle-2-uuid';

-- Döngü-1'in tamamlanma durumu
SELECT 
  COUNT(*) FILTER (WHERE status = 'pending') as pending,
  COUNT(*) FILTER (WHERE status = 'loaded') as loaded,
  COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled
FROM loadsheets
WHERE cycle_id = 'cycle-1-uuid';
```

---

## Best Practices

### 1. Döngü Başlatma
- ✅ Önceki döngü tamamlanmış mı kontrol et
- ✅ Excel validasyonu yap (zorunlu kolonlar)
- ✅ Revizyon tespiti otomatik çalışsın
- ❌ Manuel revizyon fişi oluşturma

### 2. Planlama
- ✅ Dengesizlik uyarısını her zaman göster
- ✅ Kullanıcıya seçenek sun (zorla kabul ettirme)
- ✅ Territory numaralarını tutarlı tut (T01, T07...)
- ❌ Önceki döngünün istasyon planını kopyalama

### 3. Fiş Yönetimi
- ✅ Paket numarasını unique yap (cycle_id + package_number)
- ✅ Revizyon fişini orjinal fişe bağla (parent_loadsheet_id)
- ✅ Durum geçişlerini logla (pending → loaded)
- ❌ Yeşil fişi tekrar griye çevirme

### 4. Tamamlanma
- ✅ Gri fiş varsa yeni döngü başlatma
- ✅ Eksik fişleri iptal etme seçeneği sun
- ✅ Kapanış raporunu otomatik oluştur
- ❌ Döngüyü zorla kapatma

---

## Hata Durumları

### Hata 1: Önceki Döngü Tamamlanmamış
**Durum:** Döngü-1'de 3 gri fiş var, Döngü-2 başlatılmaya çalışılıyor

**Çözüm:**
1. UYARI göster: "Döngü-1 tamamlanmadı"
2. Seçenekler sun: [Tamamla] [İptal Et] [Vazgeç]
3. Kullanıcı "İptal Et" seçerse → gri fişleri "cancelled" yap
4. Döngü-2 başlatılabilir

---

### Hata 2: Excel Format Hatası
**Durum:** Yüklenen Excel'de zorunlu kolonlar eksik

**Çözüm:**
1. Validasyon hatası döndür
2. Eksik kolonları listele
3. Döngü oluşturma

---

### Hata 3: Büyük Territory
**Durum:** Sanayi (524 karton) tek başına çok büyük

**Çözüm:**
1. Dengesizlik uyarısı göster
2. Önerilen istasyon sayısını hesapla (6 yerine 5)
3. Kullanıcı kararı bekle
4. Kabul ederse → 6 istasyon aç

---

## Özet

Döngü sistemi sayesinde:
- ✅ Günde 3 farklı sipariş çekimi yönetilebilir
- ✅ Revizyonlar otomatik tespit edilir
- ✅ Her döngü bağımsız çalışır
- ✅ Tamamlanma kuralları zorlanır
- ✅ Gri fiş kalmaz (ya tamamlanır ya iptal edilir)
