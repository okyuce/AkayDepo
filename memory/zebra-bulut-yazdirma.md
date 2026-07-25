# Zebra bulut yazdırma — Konya ZD421 kaydı ve kurulum gerçekleri

> Kalıcı bilgi. Ayrıntılı mimari gerekçe: [yazdirma-mimarisi.md](yazdirma-mimarisi.md)

## Kayıtlı cihaz (Konya)
- Model **ZD421**, PN `ZD4A042-30EE00EZ`, **seri `D6J245109380`**
- Zebra tenant: **`oyuce@fnf1.com.tr`** (developer.zebra.com → My Devices)
- Enrollment: `?r=bed61b940664760f89a5181cd4858d77`, endpoint `savanna-device.zpc.zebra.com`
- Plan: **Send-File-To-Printer-Free** (günde ~100 çağrı ücretsiz, sonrası $0.01/çağrı)
- Ağ: Ethernet, `WIRED ACTIVE PRINTSRVR`, IP `192.168.10.77`; outbound 443 açık, TLS sorunu çıkmadı
- Enrollment dosyası repo kökünde: `zebra-ZD421.txt`

## Kurulum tuzakları (yaşanmış)
- **ZSU "Doğrudan Haberleşme" USB'den `setvar` komutlarında DONUYOR**; `getvar` sorunsuz.
- Reset sonrası "Unable to open port" — Windows spooler portu tutuyor.
- **Çalışan yöntem:** enrollment'ı yazıcı sürücüsünden dosya olarak gönder
  (Driver Ayarları → Dosya gönder → `C:\temp\zebra-ZD421.txt`). Sessiz çalışır, donmaz.
- **Doğrulama USB'den değil**, portal → My Devices'tan yapılır.
- Bağlantı kanıtı: `! U1 getvar "weblink"` logunda `Successfully connected`.

## Backend entegrasyonu (yapılacak)
1. `Depot` modeline `zebra_tenant_id` + `zebra_api_key`; `Station` modeline `printer_serial`.
2. SendFileToPrinter POST endpoint — `generate_loadsheet_zpl` **aynen** kullanılır;
   header `apikey` + `tenant`, gövde `sn=<printer_serial>`.
3. "Yazdır" butonunda geri-düşüş: `printer_serial` varsa buluttan bas,
   yoksa mevcut AkayPrintBT/BT yolu → diğer 12 depo etkilenmez.
4. Zebra app `akaykonya` oluşturuldu; Consumer Key alınıp `.env.prod`'a girilecek.
