# PRINT_TEMPLATES

## NOT: Yazdırma Yok
**Önemli:** Bu projede fiş yazdırma yok. Tablet üzerinden dijital gösterim olacak.

## Paket Etiketi (Fiziksel - Opsiyonel)
**Eğer paketlere etiket yapıştırılacaksa:**

### Format
```
┌─────────────────────────┐
│ PAKET NO: T07-B01       │
│                         │
│ Territory: Sille        │
│ Bayi: NUR BAKKAL        │
│ Kod: D3J005897          │
│ Karton: 28              │
│                         │
│ [QR Code - opsiyonel]   │
└─────────────────────────┘
```

### Etiket Boyutu
- A6 (105x148 mm)
- Veya termal yazıcı 4x6 inch

### Revizyon Paketi Etiketi
```
┌─────────────────────────┐
│ PAKET NO: T07-B01-R     │
│ 🔄 REVİZYON             │ ← Turuncu arka plan
│                         │
│ Territory: Sille        │
│ Bayi: NUR BAKKAL        │
│ +4 Karton               │
└─────────────────────────┘
```

## Tablet Fiş Görünümü (Dijital)

### Standart Fiş (Tablet)
**UI_SPEC.md'deki format kullanılacak:**
- Başlık: Paket No (T07-B01), Territory, Bayi
- Ürün listesi: Karton + Paket kolonları
- Toplam karton
- "Yükleme Tamamlandı" butonu

### Revizyon Fişi (Tablet)
**UI_SPEC.md'deki format kullanılacak:**
- Başlık: "REVİZYON FİŞİ" badge'i
- Paket No: T07-B01-R
- Değişiklik listesi:
  - 🟢 Yeşil: Ekleme (+3 karton)
  - 🔴 Kırmızı: Azaltma (-1 karton)
  - 🔵 Mavi: Yeni ürün
- Net değişiklik: +4 karton
- Azaltma uyarısı (varsa): "⚠️ Paketi açın"
- "Revizyon Tamamlandı" butonu
