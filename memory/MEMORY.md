# AkayDepo — Hafıza İndeksi

> Kalıcı kararlar ve gerçekler. Her madde tek satır + ilgili nota işaret eder.
> Ayrıntılı notlar bu klasörde ayrı `.md` dosyaları olarak tutulur.
> (Sabit proje bilgisi — yapı, portlar, deploy — kök `CLAUDE.md`'dedir.)

- [Lokal geliştirme](lokal-gelistirme.md) — `.env.local`'e sabit IP yazma, mDNS adı kullan (3 kez bozdu); servisleri çalıştırma komutları
- [Yazdırma mimarisi](yazdirma-mimarisi.md) — app'siz Wi-Fi tek-tık için Zebra ZD421 + Cloud Connect; TE210 neden elendi; AkayPrintBT Zebra MFi kilidi
- [Zebra bulut yazdırma](zebra-bulut-yazdirma.md) — Konya ZD421 buluta kayıtlı (seri `D6J245109380`, tenant `oyuce@fnf1.com.tr`); ZSU tuzakları + backend entegrasyon adımları
- [Şema değişikliği ve deploy](sema-degisikligi-ve-deploy.md) — **alembic prod'da otomatik çalışmaz**; kolon eklerken startup güvencesi + savunmacı migration şart
- [Sipariş Kontrolü (kapanış)](siparis-kontrol-kapanis.md) — karşılaştırma anahtarı `BayiKodu`; sadece iptaller otomatik; `TERR0307` prefix'i Konya'ya özel değil
