# AkayDepo — Çalışma Günlüğü (WORKLOG)

> En yeni kayıt **en üstte**. Format: `tarih · ne yapıldı · kararlar · sıradaki adım`.
> Oturum başında SessionStart hook'u son kayıtları + hafıza indeksini otomatik yükler.

---

## 2026-06-13 — Yükleme fişine RUT (rut sırası) bilgisi eklendi
- **Yapıldı:** Müşteri talebi — yazdırılan yükleme fişinin **en üstüne** büyük puntoyla `RUT N` (Rut Sırası = `route_order`, karttaki büyük badge) eklendi. Her iki yazdırma yolu güncellendi: iOS→ZPL (`backend/app/services/zpl_generator.py`: `build_label_data` artık `dealer.route_order` çekiyor, `build_zpl` FIŞ-N'den önce ortalanmış `RUT N` font 56 basıyor) ve Android/PC→PNG (`frontend/src/components/PrintLabel.tsx`: `PrintLabelData.route_order` + 30px render, `LoadsheetListPage.tsx` print verisine `loadsheet.route_order` aktarılıyor).
- **Karar:** `route_order` 0/yoksa RUT satırı hiç basılmaz (eski fişler bozulmaz). Yerleşim: en üstte büyük (FIŞ'ten büyük) — kullanıcı seçti.
- **Doğrulama:** ZPL unit testleri 17 passed (RUT var/yok + `route_order` çekme için yeni testler eklendi); frontend `tsc --noEmit` temiz.
- **Sıradaki adım:** Onay sonrası deploy (`api` + `web` rebuild). İdeal: önce gerçek fişle iOS/AkayPrintBT yolu test edilsin.

## 2026-06-10 — Konya: yanlış Excel import'u (batch 6) canlıdan kaldırıldı
- **Yapıldı:** Konya Deposu aktif döngüsünde (cycle `86259fe7-...-490d671`, 10.06.2026) yanlışlıkla yüklenen `Excel.b436411e-ebc8-4385-983e-82db1e5c1998.xlsx` (batch 6, 255 bayi, 08:32-15:46 tüm günün kümülatif tekrarı) canlı DB'den silindi: 3.059 `order_lines` + 255 `orders` + 1 `cycle_imports` kaydı, tek transaction'da. Kullanıcı onayı alındı.
- **Güvenlik:** Silme öncesi tam yedek: sunucuda `/home/okyuce/akaydepo-yedek-20260610-batch6-silme-oncesi.sql.gz` (1.3 MB). Batch 6'dan hiç loadsheet üretilmediği (planlama güncellenmediği) ve dış referans olmadığı doğrulandı; batch 1-5 ve fişler (254 loaded / 2 pending / 5 cancelled) dokunulmadı.
- **Karar:** Böyle bir iptal için UI/endpoint yok — gerekirse "son batch'i geri al" özelliği ileride eklenebilir.
- **Sıradaki adım:** Konya planlamaya batch 1-5 ile devam edebilir; yeni Excel yüklenirse batch 6 olarak devam eder.

## 2026-06-09 — Kalıcı hafıza iskeleti kuruldu
- **Yapıldı:** Oturumlar-arası hafıza altyapısı eklendi — mevcut `CLAUDE.md`'nin (PMI ISMS proje bağlamı) sonuna "Kalıcı Hafıza & Oturum Kuralları" bölümü (içerik **dokunulmadan**), `WORKLOG.md`, `memory/`, `worklog-archive/` ve SessionStart hook'u. Mevcut `Bash(curl:*)` izni korundu.
- **Dokunulmadı:** `backend/akaydepo.db` (uygulama veritabanı).
- **Karar:** Hafıza dosyaları henüz commit edilmedi — istenince commit edilir.
- **Sıradaki adım:** Normal AkayDepo geliştirmesine devam.
