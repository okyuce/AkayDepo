# DATA_MODEL

Veri modeli özetidir. PostgreSQL hedeflenmiştir.

## Tablolar

### territories
- id (pk, uuid)
- code (text, unique) — Excel `Territory`
- name (text) — ayrıştırılabilirse `TERR030707-Sille` içinden
- display_number (text) — "T01", "T07", "T27" (paket numaralandırma için)
- created_at, updated_at

### dealers
- id (pk, uuid)
- code (text, unique) — Excel `BayiKodu`
- name (text) — `BayiAdı`
- position_code (text) — `Pozisyon`
- route_order (int) — `BayiRutSırası`
- territory_id (fk -> territories)

### products
- id (pk, uuid)
- code (text, unique) — `ÜrünKodu`
- name (text) — `ÜrünAdı`
- pack_per_carton (int) — 1 karton = 10 paket (sabit dönüşüm kuralı)

### cycles
- id (pk, uuid)
- cycle_no (int) — 1, 2, 3 (14:00, 16:00, 17:00)
- run_time (text) — "14:00", "16:00", "17:00"
- plan_date (date)
- imported_at (timestamp)
- status (text) — "active", "completed", "archived"
- completed_at (timestamp, nullable)

### orders
- id (pk, uuid)
- cycle_id (fk -> cycles) — hangi döngüde oluşturuldu
- external_order_code (text) — `SiparişKodu`
- payment_type (text) — `ÖdemeTipi`
- order_date (date) — `SiparişTarihi`
- delivery_date (date) — `TeslimatTarihi`
- territory_id (fk)
- dealer_id (fk)
- revision_group_id (uuid) — aynı siparişin versiyonlarını gruplamak için
- revision_no (int) — 1,2,3…
- source_sheet (text) — Recipe2 / Recip1
- imported_at (timestamp)

### order_lines
- id (pk, uuid)
- order_id (fk)
- product_id (fk)
- qty_carton (int) — `Karton`
- qty_pack (int) — `Paket`

### stations
- id (pk, uuid)
- name (text) — İstasyon-1,2,…
- active (bool)
- worker_id (nullable, fk) — depo görevlisi (opsiyonel)

### station_assignments
- id (pk, uuid)
- cycle_id (fk -> cycles) — hangi döngüde oluşturuldu
- plan_date (date)
- station_id (fk)
- territory_id (fk)
- load_rank (int) — sayım sırası (1..k)
- target_total_carton (int)
- target_total_pack (int)

### loadsheets
- id (pk, uuid)
- cycle_id (fk -> cycles) — hangi döngüde oluşturuldu
- assignment_id (fk -> station_assignments)
- dealer_id (fk)
- sheet_no (text)
- package_number (text) — "T07-B01", "T07-B01-R" (revizyon için -R suffix)
- status (enum: pending, loaded, cancelled, error)
- is_revision (bool) DEFAULT false — revizyon fişi mi?
- parent_loadsheet_id (uuid, nullable) — revizyon ise orjinal fişin ID'si
- printed_at, loaded_at

### loadsheet_lines
- id (pk, uuid)
- loadsheet_id (fk)
- product_id (fk)
- qty_carton (int)
- qty_pack (int)

### load_counters
- id (pk, uuid)
- assignment_id (fk)
- count_index (int) — C1..Ck
- remaining_carton (int)
- remaining_pack (int)
- note (text)

### revision_diffs
- id (pk, uuid)
- cycle_from_id (fk -> cycles) — önceki döngü
- cycle_to_id (fk -> cycles) — yeni döngü
- order_code (text) — `SiparişKodu`
- dealer_id (fk -> dealers)
- product_id (fk -> products)
- qty_old_carton (int) — önceki miktar
- qty_new_carton (int) — yeni miktar
- qty_change_carton (int) — new - old (pozitif=artış, negatif=azalış)
- change_type (text) — "addition", "reduction", "new_product", "removed_product"
- created_at (timestamp)

## İndeksler
- `cycles(plan_date, status)`
- `orders(external_order_code, revision_no, cycle_id)`
- `dealers(code)`, `products(code)`, `territories(code)`
- `loadsheets(cycle_id, status, is_revision)`
- `revision_diffs(cycle_from_id, cycle_to_id, dealer_id)`
