# Gün sonu Sipariş Kontrolü (kapanış Excel'i) — tasarım kararları

Menü: **Sipariş Kontrol** → `/siparis-kontrol` (admin).
Kod: `backend/app/services/closing_checker.py`, `api/closing_check.py`.

## Neden var

Gün içindeki parçalı Excel'ler **artımlı** — her dosya yalnızca o pull anına
kadarki yeni/değişmiş siparişleri taşır. Revizyon yeni kodla gelir (sistem
yakalar), ama **iptal hiçbir dosyada iz bırakmaz**. Akşamki kapanış Excel'i
günün tamamını içerdiği için eksik bayiler = iptal edilmiş siparişler.

## EN ÖNEMLİ KARAR: anahtar `BayiKodu`, `SiparişKodu` DEĞİL

Kapanış her bayi için **yalnızca son revizyonu** tutar. Sipariş koduna göre
karşılaştırmak eskimiş revizyonları "iptal" sanar — 26.11.2025 verisinde
**6 yanlış pozitif**, `Konya20260822`'de 4. Bayi bazında ikisi de temiz çıkıyor.

`SiparişKodu = BayiKodu(9 hane) + 6 hane`, son hane revizyon sayacı (…21→22→23).
5 veri setinde %100 tutuyor **ama algoritma buna bağlı değil** — `BayiKodu`
zaten ayrı kolonda geliyor.

## Dört vaka — sadece A otomatik

| | Durum | Aksiyon |
|---|---|---|
| A | Bizde var, kapanışta yok | **İPTAL** → fiş iptal + tamamlanmışsa stok iadesi |
| B | Kapanışta var, bizde yok | Sadece rapor |
| C | Sipariş kodu farklı | Sadece rapor (kaçırılmış revizyon) |
| D | Kod aynı, miktar farklı | Sadece rapor |

**Karar (kullanıcı, 31.08.2026):** B/C/D otomatik işlenmez — gün sonunda
plan/istasyon dağılımını yeniden çalıştırmak riskli.

## 13 depo tuzakları (kod bunları biliyor)

- **`TERR0307` prefix'i Konya'ya ÖZEL DEĞİL.** Konya `TERR0307`01–27,
  Seydişehir `TERR0307`17/18/19 — prefix eşleştirmesi yanlış deponun dosyasını
  kabul ederdi. Sahiplik **tam kod üyeliğiyle** belirlenir; karşılaştırma
  bölge adı değişebildiği için numara kısmıyla yapılır
  (`TERR030702-Eski-Garaj` / `-Kadınlarpazarı` aynı bölge).
- **Superadmin `depot_id=NULL` iken `verify_depot_access` kontrolü ATLIYOR.**
  Bu yüzden endpoint `require_depot` kullanır (depo seçmemiş superadmin 403).
- **13 deponun 8'inde yalnızca "Park" istasyonu var** (AGR/BIT/CIH/DOG/ERE/
  HAK/MUS/NIG/VAN) → hiç fiş üretilmez. Kod "fiş üretilmemiş" deyip atlar.
- Stok hareketlerine `depot_id` **açıkça** yazılır. (Mevcut
  `loadsheets.py:/cancel` yazmıyor — startup backfill yanlış depoya atayabilir.)

## Kapsam kuralı: zaman aralığı değil, batch kapsaması

Bir `import_batch`'in canlı bayilerinin *hiçbiri* kapanışta yoksa dosya günün
tamamını kapsamıyordur. Zaman aralığı kuralı (`min ≤ döngü_min`) gerçek
iptallerde yanlış alarm veriyordu; batch kuralı vermiyor.

İlgili: [[sema-degisikligi-ve-deploy]]
