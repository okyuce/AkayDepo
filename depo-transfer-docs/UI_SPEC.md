# UI_SPEC (React)

## Sayfalar

### 1. Excel Yükleme Paneli (Sistem Kullanıcısı)
**Kişiler:** Sistem kullanıcısı (ISMS'den Excel çeken kişi)

**Özellikler:**
- Excel dosyası yükleme (drag & drop)
- Run time seçimi: 14:00, 16:00, 17:00
- Döngü durumu kontrolü ("Döngü-1 tamamlanmadı" uyarısı)
- Eksik fişleri iptal etme seçeneği

### 2. Planlama Paneli (Sistem Kullanıcısı)
**Yükleme sonrası:**
- Depocu sayısı girişi (varsayılan: 5)
- "Planı Oluştur" butonu
- Dengesizlik uyarısı (büyük territory tespiti)
  - Önerilen istasyon sayısı
  - Kullanıcı seçenekleri: [Kabul Et] [Devam Et] [Manuel]
- İstasyon kartları: toplam karton, territory listesi, dengeleme oranı

### 3. Tablet Görünümü (Depocu)
**Kişiler:** Depo görevlileri (istasyon başında)

**Özellikler:**
- **İstasyon bazlı filtreleme:** Depocu sadece kendi istasyonunu görür
- **Döngü bilgisi:** "Döngü-2 (16:00)" badge'i
- **Progress bar:** Genel ilerleme (yüzde)
- **Sayım detayı:** C1→C2→C3 (kalan karton)
- **Territory gruplama:** Her territory接ılabilir/kapatılabilir

**Territory Kart Bilgileri:**
- Territory adı + paket numarası öneki ("T07-Sille")
- Toplam karton
- Progress bar (territory bazında)
- Durum: Tamamlandı/Devam Ediyor

**Fiş Kartları:**
```
┌─────────────────────────────────────┐
│ 📦 T07-B01                        │
│ TERR030707-Sille | NUR BAKKAL      │
│ D3J005897                           │
│ 28 Karton | Rut: 24                 │
│                                     │
│ [FİŞ DETAY] [✔️ YÜKLEME TAMAMLANDI] │
└─────────────────────────────────────┘
```

**Durum Renkleri:**
- ⬜ **GRİ:** Henüz başlanmadı (pending)
- ✅ **YEŞİL:** Yükleme tamamlandı (loaded)
- 🟧 **TURUNCU:** Revizyon fişi (is_revision = true)
- 🔴 **KIRMIZI:** Hata var (error)
- ❌ **İPTAL:** İptal edildi (cancelled)

**Revizyon Fişi Gösterimi:**
- Orjinal fiş + revizyon fişi yan yana
- Orjinal fiş yeşil (zaten hazırlanmış)
- Revizyon fişi gri/turuncu (henüz hazırlanmamış)
- Badge: "🔄 REVİZYON"

### 4. Fiş Detay Modal (Tablet)
**Tıklama sonrası:**

**Standart Fiş:**
```
╔════════════════════════════════════════╗
║ FİŞ: T07-B01                          ║
║ Paket: T07-B01                         ║
╠════════════════════════════════════════╣
║ NUR BAKKAL-BAHRİ DEMİR              ║
║ Bayi Kodu: D3J005897                  ║
╠════════════════════════════════════════╣
║ Ürün            | Karton | Paket      ║
║────────────────────────────────────────║
║ PL Midnight     |   2    |   0        ║
║ MLR Touch       |   2    |   0        ║
║ MLR Edge        |   8    |   0        ║
╠════════════════════════════════════════╣
║ TOPLAM: 12 Karton                     ║
╠════════════════════════════════════════╣
║ [✔️ YÜKLEME TAMAMLANDI]              ║
╚════════════════════════════════════════╝
```

**Revizyon Fişi:**
```
╔════════════════════════════════════════╗
║ REVİZYON FİŞİ | T07-B01-R          ║
║ 🔄 16:00 Güncellemesi                 ║
╠════════════════════════════════════════╣
║ BAYİ: D3J005897 - NUR BAKKAL         ║
╠════════════════════════════════════════╣
║ DEĞİŞİKLİKLER:                     ║
║                                        ║
║ 🟢 PL Midnight      | +3 Karton | EKLE ║
║ 🔴 MLR Touch        | -1 Karton | ÇIKAR║
║ 🟢 MLR Edge         | +2 Karton | EKLE ║
║                                        ║
╠════════════════════════════════════════╣
║ NET DEĞİŞİKLİK: +4 Karton            ║
╠════════════════════════════════════════╣
║ ⚠️ Azaltma için paketi açın         ║
║                                        ║
║ [✔️ REVİZYON TAMAMLANDI]              ║
╚════════════════════════════════════════╝
```

### 5. Sayım Görüntüleme (Tablet)
**Hybrid Model:** Progress bar + C1→C2 detayı

**Özellikler:**
- Genel progress bar (İstasyon toplamı)
- Territory bazında progress bar
- C1→C2→C3 sayım detayı (kalan karton)
- Canlı güncelleme (WebSocket)

## React Bileşenleri

### Ana Bileşenler
- `ExcelUploadPanel` — Excel yükleme arayüzü
- `PlanningPanel` — İstasyon planlama, depocu sayısı girişi
- `UnbalancedLoadWarning` — Dengesizlik uyarı modalı
- `StationCard` — İstasyon özet kartı
- `TabletView` — Depocu tablet arayüzü (istasyon bazlı)
- `TerritoryGroup` — Territory gruplama bileşeni
- `LoadsheetTile` — Fiş kartı (küçük)
- `LoadsheetModal` — Fiş detay modalı
- `RevisionBadge` — Revizyon badge'i ("🔄 REV")
- `CounterDisplay` — Sayım gösterimi (C1→C2→C3)
- `ProgressBar` — İlerleme çubuğu (genel + territory)
- `PackageNumberChip` — Paket numarası (T07-B01)

## Durum Yönetimi

### Döngü Tamamlanma Kuralları
**Yeni döngü başlatmak için:**
1. Tüm fişler "loaded" (yeşil) olmalı
2. Veya eksik fişler "cancelled" olarak işaretlenmeli
3. Gri fiş kaldığı sürece yeni döngü başlatılamaz

**Eksik Fiş Uyarısı:**
```
┌─────────────────────────────────────────┐
│ ⚠️  UYARI: Döngü-1 Tamamlanmadı        │
├─────────────────────────────────────────┤
│ 3 fiş henüz yüklenmedi (GRİ)           │
│                                         │
│ Yeni döngü başlatmak için:             │
│ - Tüm fişler YEŞİL olmalı              │
│ - Veya eksik fişleri iptal et          │
│                                         │
│ [Eksik Fişleri Göster] [İptal Et]     │
└─────────────────────────────────────────┘
```

## Offline Durum
**Not:** Uygulama online olacak, offline çalışma olmayacak.

**Bağlantı Koptuğunda:**
- Kırmızı uyarı banner: "⚠️ İnternet bağlantısı kesildi"
- Tüm butonlar devre dışı bırakılır
- Otomatik yeniden bağlanma denemesi (5 sn aralıkla)
