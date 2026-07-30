---
name: yazdirma-mimarisi
description: Yazıcı/yazdırma mimarisi — app'siz Wi-Fi/Ethernet tek-tık için Zebra Link-OS Weblink; ZD421 vs ZD621 Ethernet farkı; SGD komutları; Zebra CA sertifika şartı; TE210 neden elendi
metadata:
  type: project
---

13 depoya **app'siz, ağ üzerinden tek-tık print** hedefi için mimari yön: **Zebra Link-OS + Weblink (Cloud Connect)**. Yazıcı buluta/sunucuya **kendisi outbound** bağlanır → lokal agent yok. Bizim `generate_loadsheet_zpl` çıktısı aynen kullanılır.

## Model seçimi — ⚠️ 2026-07-21'de DÜZELTİLDİ

- ✅ **ZD421 tam Link-OS** (Link-OS Basic değil) → Cloud Connect/Weblink **destekliyor, ek lisans gerekmiyor**. Kaynak: zebra.com/cloud-connect — *"available on all Link-OS printers, excluding Link-OS Basic models"*.
- ⚠️ **ZD421'de Ethernet DAHİLİ DEĞİL** — fabrika opsiyonu ya da sahada takılan modül. Resmi parça no: **Ethernet `P1112640-015`** · Seri `P1112640-016` · Wi-Fi 802.11ac (diğer ülkeler) `P1112640-017C`. (Zebra ZD421 parts catalog PDF)
- 🔴 **ÖNCEKİ NOT YANLIŞTI:** "ZD621 sadece hız/ekran, ek fayda yok" **hatalı**. ZD421/ZD621 kullanıcı kılavuzu s.19: **ZD621'de Internal Ethernet Print Server STANDART dahil**, ZD421'de değil. Modül ~$300 ise **ZD621 toplamda daha ucuz olabilir** — alım öncesi ZD621 fiyatı ile "ZD421 + P1112640-015" toplamı mutlaka karşılaştırılmalı.
- ⛔ ZD220/ZD230/ZT111 = Link-OS **Basic** → Weblink YOK.
- ⛔ ZD411 = 2 inç (~56mm) → 72mm etiket (`^PW576`) sığmaz.
- ⛔ TSC TE210: ZPL emülasyonu var ama **buluttan iş çekemez** (sadece raw 9100) → her sahada agent şart, elendi.
- Mevcut **AkayPrintBT** iOS app Apple MFi + `com.zebra.rawport`'a kilitli → sadece Zebra Bluetooth.

## İki farklı "Cloud Connect" — karıştırma
| | **Genel Weblink** `weblink.ip.conn[1\|2].*` | **Visibility Agent** `weblink.zebra_connector.*` |
|---|---|---|
| Bağlanır | **Bizim kendi sunucumuz / seçtiğimiz URL** | Zebra'nın telemetri bulutu (varsayılan AÇIK) |
| Bizim kullanacağımız | ✅ **Bu** | opt-out edilebilir, ilgisiz |

## Kurulum — asgari komut seti (docs.zebra.com ZPL/SGD PG ile doğrulandı)
```
! U1 setvar "weblink.ip.conn1.location" "https://sunucu.example.com:443/zebra/weblink/"
! U1 setvar "device.reset" ""
```
- URL **https:// zorunlu** (wss:// değil), port+path dahil, max 2048 karakter. Host, sertifikanın CN/SAN'ı ile **birebir** eşleşmeli — IP kullanma.
- Diğer: `weblink.ip.conn1.retry_interval` (1-600, vars. 10) · `retry_interval_random_max` (vars. 120, filo reconnect jitter'ı) · `weblink.ip.conn1.proxy` ("[http|https]://[user:pass@]domain[:port]/", vars. port **1080**) · `weblink.ip.conn1.authentication.add "server user pass"`.
- **Düzeltmeler:** `weblink.enable` ve `weblink.printer_reset_required` ve `num_connections` **salt-okunur (getvar)**. Bağlantı sınırı için `maximum_simultaneous_connections` (1-100, vars. 10). **`authentication.entity` diye bir komut YOK.**
- Doğrulama: `weblink.logging.max_entries`→"100", sonra `! U1 getvar "weblink"` → logda **`[conn1.nn] Successfully connected`** aranır.

## 🔴 Tuzaklar (kurulumu bunlar bozar)
1. **Zebra CA sertifika şartı — self-hosted için kritik açık risk.** Zebra troubleshooting (güncel) hâlâ *"Was the server's certificate issued by Zebra and is it signed by the Zebra Certificate Authority?"* diyor. Prosedür: OpenSSL CSR → **softpm@zebra.com**'a e-posta → Zebra imzalar. **Let's Encrypt / public CA'nın kabul edilip edilmediği DOĞRULANMADI** — kendi sunucu yolunu seçmeden önce laboratuvarda test şart. TLS 1.2 destekleniyor.
2. **Saat/NTP.** Sertifika doğrulaması yazıcının saatini kullanır. ZD421'in **pilsiz RTC'si güç kesilince firmware build tarihine döner** → "certificate expired/not yet valid". `ip.dhcp.ntp.enable` **varsayılan "off"** → `! U1 setvar "ip.dhcp.ntp.enable" "on"` + ağda DHCP option 42.
3. **Dil ayarı ZPL olmalı.** "Line Print" modundaysa yazıcı konfigürasyon dosyasını ayar olarak işlemez, **kağıda basar**.
4. **Modül takınca firmware güncelle.** Zebra: modüllerin kendi iç firmware'i var, ana firmware ile senkron olmalı.
5. Firewall: sadece **outbound** 443 (URL'deki port) yeter; inbound açmaya gerek yok. `ip.firewall.whitelist_in` inbound içindir, Weblink ile ilgisizdir.

## İki entegrasyon yolu
- **①a Zebra SendFileToPrinter** (Zebra Data Services): developer.zebra.com hesabı → Apps → Add App → **Consumer Key**; My Devices → Add Device → **enrollment string** (içinde `weblink.ip.conn1.location` + `r=<kod>`) yazıcıya gönderilir → cihaz My Devices'ta otomatik belirir. Kimlik = **Tenant Account Number** (hesap) + **yazıcı seri no** (`sn` parametresi, çoklu gönderim destekli). Endpoint: `https://api.zebra.com/v2/devices/printers/send`, header `apikey` + `tenant`. Ücret: **günde ~100 çağrı ücretsiz, sonra $0.01/başarılı çağrı** (birincil kaynak 403 verdi, portalda teyit edilmeli).
- **①b Kendi Weblink sunucumuz**: resmen belgeli — techdocs.zebra.com/link-os/2-14/webservices; resmi örnek kod **ZebraDevs/LinkOS-Webservices-Samples** (Java), topluluk **elops/zebra_ws_print** (Python). Sürekli $0 ama **Zebra CA şartı (tuzak #1)** operasyonel maliyeti artırıyor.
- **Hacim notu:** ~250 fiş/depo/döngü × 3 döngü × 13 depo → ①a'da yılda **$3.6k-11k**. Kota ilk depoda biter.
- ⛔ **Zebra Browser Print bulut DEĞİL** — PC'ye lokal ajan kurar, aynı ağda olmak şart. Bizim senaryoyu çözmez.

## Kurulum modeli
İlk bootstrap fiziksel (Ethernet+DHCP; IP için FEED+CANCEL 2sn → Network Config etiketi). Ayarlar: ZSU "Open Communication With Printer", Printer Setup mobil app (BLE), USB'den dosya, ya da ağa girdikten sonra **raw 9100'e SGD göndererek uzaktan**. Sonrası Weblink Configuration Channel (JSON-SGD) ile uzaktan yönetilebilir.

Bkz. [[akaydepo-prod-deploy]].
