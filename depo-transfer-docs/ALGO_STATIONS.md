# İstasyon Paylaştırma Algoritması

Amaç: Açılacak istasyon sayısı = depo görevlisi sayısı. Territory’ler, istasyonlara **ürün toplamları birbirine yakın** olacak biçimde dağıtılsın.

## 1) Metriği Seç
- Toplam karton (tercih) ve yardımcı metrik olarak toplam paket.
- **Dönüşüm kuralı:** 1 Karton = 10 Paket (sabit oran)
- Territory skor = Σ (Karton + Paket/10) — tüm ürün satırları için

## 2) Heuristik (Hızlı Çözüm)
- Territory'leri skorlarına göre azalan sırala.
- Boş istasyon kovaları oluştur (k adet).
- Her territory'yi, anlık toplamı en düşük olan istasyona ata (greedy load balancing).

### 2.1) Dengesizlik Kontrolü
**Amaç:** Bir territory çok büyükse, istasyon sayısını otomatik artır.

**Algoritma:**
1. Ortalama yük hesapla:
   ```
   Ortalama yük = Toplam karton / İstasyon sayısı
   ```

2. Eşik belirle:
   ```
   Eşik = Ortalama yük × 1.5
   ```

3. Büyük territory tespiti:
   ```
   Eğer bir territory_karton > Eşik ise:
     → UYARI: Dengesiz yük
     → Önerilen istasyon sayısı = ceil(Toplam karton / 335)
   ```

**Örnek:**
```
Toplam: 1675 karton
İstasyon: 5
Ortalama: 335 karton
Eşik: 502.5 karton

TERR030703-Sanayi: 524.6 karton > 502.5
→ UYARI göster
→ Önerilen istasyon sayısı: 6
```

**Kullanıcı Seçenekleri:**
- [1] Önerilen istasyon sayısını kabul et (6 istasyon)
- [2] Mevcut istasyon sayısında devam et (2 depocu aynı istasyonda çalışır)
- [3] Manuel ayarla

## 3) Alternatif: Tamsayılı Programlama (ILP)
- Karar değişkeni: x[t,s] ∈ {0,1} (territory t istasyon s’ye atanır)
- Kısıt: her territory tam 1 istasyona
- Amaç: max yük ile min yük farkını minimize et (veya kareler toplamını)

## 4) Sayım (Counting) Döngüleri
- Her istasyon için C1..Ck sütunları: C(i) = C(i-1) − Yüklenen(i-1)
- Yükleme fişi kapandığında ilgili `remaining_*` güncellenir.
- Bir sonraki fiş hesaplaması önceki `remaining` üzerinden yapılır.

## 5) Revizyon İşleme (Döngüler Arası)
**Prensip:** Her döngü bağımsız istasyon planı oluşturur.

### 5.1) Revizyon Tespiti
- Cycle-to-cycle karşılaştırma (Cycle-2 vs Cycle-1)
- Aynı `SiparişKodu` + `BayiKodu` kontrolü
- Ürün bazında miktar farkı hesaplama:
  ```
  Δ = qty_new_carton - qty_old_carton
  ```

### 5.2) Revizyon Fişi Oluşturma
- Eğer Δ ≠ 0 → İkinci bir fiş oluştur (is_revision = true)
- Revizyon fişi orjinal fişe bağlanır (parent_loadsheet_id)
- Paket numarası: `T07-B01-R` (orjinal: `T07-B01`)

### 5.3) Değişiklik Türleri
- **addition:** Δ > 0 (artış) → Yeşil gösterim
- **reduction:** Δ < 0 (azalış) → Kırmızı gösterim
- **new_product:** Önceki döngüde yoktu → Mavi gösterim
- **removed_product:** Yeni döngüde yok → Üstü çizili

### 5.4) Fiziksel İşlem
- Paketler mühürlü değil → açılabilir
- Azaltma var ise: Depocu paketi açar, ürünü çıkarır
- Tablet'te uyarı: "⚠️ 5 Karton MLR Touch çıkar"
