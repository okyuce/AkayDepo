# EXCEL_MAPPING

Kaynak dosya: `e-sipariş.xlsx`

## Sheet: Recipe2 (güncel çekim)
- Pozisyon -> dealers.position_code
- Territory -> territories.code
- SiparişKodu -> orders.external_order_code
- BayiKodu -> dealers.code
- BayiAdı -> dealers.name
- ÜrünKodu -> products.code
- ÜrünAdı -> products.name
- Paket -> order_lines.qty_pack
- Karton -> order_lines.qty_carton
- ÖdemeTipi -> orders.payment_type
- SiparişTarihi -> orders.order_date
- TeslimatTarihi -> orders.delivery_date
- BayiRutSırası -> dealers.route_order

Toplam satır: **532**, Territory sayısı: **14**

## Sheet: Recip1 (revizyon/önceki çekim)
- Aynı kolon şeması beklenir. Diff: Recipe2 ⊖ Recip1

## Sheet: Hazırlık
- İstasyon & depo görevlisi listesi (operasyon alanı)
- Territory bazlı ürün toplamları için hazırlık alanı

## Sheet: Sipariş Yazdır
- Fiş şablonu alanları (bayi adres/kod ve ürün listesi)
- Hem karton hem paket kolonları bulunur.

> Not: Excel’in değişken alanları girişte normalize edilmelidir (örn. boş sütunlar, `Unnamed` başlıklar).
