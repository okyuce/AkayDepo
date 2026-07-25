"""
Zebra Data Services — bulut yazdırma (SendFileToPrinter)

Yazıcı (ZD421, Link-OS Weblink) buluta kendi çıkışlı bağlantısını açar; backend
ZPL'i Zebra'ya POST eder, Zebra işi yazıcıya iter. Depoda agent/app gerekmez.

Sözleşme (developer.zebra.com):
  POST https://api.zebra.com/v2/devices/printers/send
  headers: apikey: <Consumer Key>
  body   : multipart/form-data → sn=<seri no>, zpl_file=<dosya, text/plain>

⚠️ İki tuzak (lokal testte doğrulandı):
  1. `tenant` header'ı GÖNDERİLMEZ. apikey zaten tenant'ı belirliyor; header
     eklenince "Unknown Serial Number ... for tenant 'savanna.akaykonya'" ya da
     500 "Failed to execute sendFile" dönüyor. ZEBRA_TENANT boş bırakılmalı.
  2. Zebra hata durumunda da **HTTP 200** döner; gerçek sonuç gövdedeki
     `responses[0].status` alanındadır (SUCCESS / FAILURE + errorMsg).
"""
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings


class ZebraCloudError(Exception):
    """Bulut yazdırma başarısız — mesaj kullanıcıya gösterilebilir."""


@dataclass
class ZebraPrintResult:
    serial: str
    status_code: int
    body: str
    guid: Optional[str] = None


def is_configured() -> bool:
    """Bulut yazdırma için gerekli anahtar var mı? (tenant opsiyonel — bkz. modül notu)"""
    return bool(settings.ZEBRA_API_KEY)


def resolve_serial(serial: Optional[str] = None) -> str:
    """Kullanılacak yazıcı seri no — açık verilen kazanır, yoksa .env varsayılanı.

    (İleride: Station.printer_serial → Depot varsayılanı → .env)
    """
    resolved = (serial or settings.ZEBRA_PRINTER_SERIAL or "").strip()
    if not resolved:
        raise ZebraCloudError(
            "Yazıcı seri numarası tanımlı değil (ZEBRA_PRINTER_SERIAL)."
        )
    return resolved


def send_zpl(zpl: str, serial: Optional[str] = None, filename: str = "loadsheet.zpl") -> ZebraPrintResult:
    """ZPL'i Zebra bulutuna gönder. Hata durumunda ZebraCloudError fırlatır."""
    if not is_configured():
        raise ZebraCloudError("Zebra bulut yazdırma yapılandırılmamış (ZEBRA_API_KEY).")

    target_serial = resolve_serial(serial)

    files = {
        "sn": (None, target_serial),
        "zpl_file": (filename, zpl.encode("utf-8"), "text/plain"),
    }
    headers = {
        "apikey": settings.ZEBRA_API_KEY,
        "accept": "application/json",
    }
    # Tenant normalde gönderilmez (modül notu). Farklı bir hesapta gerekirse
    # .env'e ZEBRA_TENANT yazılınca eklenir.
    if settings.ZEBRA_TENANT:
        headers["tenant"] = settings.ZEBRA_TENANT

    try:
        with httpx.Client(timeout=settings.ZEBRA_TIMEOUT_SECONDS) as client:
            response = client.post(settings.ZEBRA_API_URL, headers=headers, files=files)
    except httpx.HTTPError as exc:
        raise ZebraCloudError(f"Zebra bulutuna ulaşılamadı: {exc}") from exc

    body = (response.text or "").strip()
    if response.status_code >= 400:
        raise ZebraCloudError(
            f"Zebra bulut hatası ({response.status_code}): {body[:400] or 'gövde boş'}"
        )

    # HTTP 200 ≠ basıldı. Gövdedeki per-yazıcı sonucu kontrol et.
    guid: Optional[str] = None
    try:
        payload = response.json()
    except ValueError:
        raise ZebraCloudError(f"Zebra beklenmedik yanıt verdi: {body[:400]}")

    entries = payload.get("responses") or []
    if not entries:
        raise ZebraCloudError(f"Zebra yanıtında sonuç yok: {body[:400]}")

    entry = entries[0]
    if str(entry.get("status", "")).upper() != "SUCCESS":
        raise ZebraCloudError(
            entry.get("errorMsg") or f"Yazdırma başarısız: {body[:400]}"
        )
    guid = entry.get("guid")

    return ZebraPrintResult(
        serial=target_serial,
        status_code=response.status_code,
        body=body,
        guid=guid,
    )
