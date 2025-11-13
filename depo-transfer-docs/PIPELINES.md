# PIPELINES

## Koşu Zamanları
- ISMS veri çekimi: her gün **14:00** ve **16:00**
- Dosyalar: `Recip1` (ilk), `Recipe2` (ikinci/son)

## Adımlar
1. Excel doğrulama (sheet adları, zorunlu kolonlar)
2. Normalize (boş başlıkları at, tip dönüşümleri)
3. Yükle: territories, dealers, products (upsert)
4. Sipariş ve satırlar (revision_group_id, revision_no)
5. Revizyon farkı üret (Recipe2 ⊖ Recip1)
6. Fiş üretimi (territory -> istasyon -> dealer -> ürünler)
7. PDF render ve yazdırma kuyruğu
8. Log & audit

## Hatalar
- Eksik kolon -> 400
- Duplicated order code + same revision -> merge policy
