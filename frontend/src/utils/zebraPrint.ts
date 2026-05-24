/**
 * zebraPrint — AkayPrintBT iOS köprü uygulamasını URL scheme ile tetikler.
 *
 * Akış:
 *   1. Backend'ten kısa ömürlü print token al
 *   2. ZPL fetch URL'i kur (api/.../zpl?token=...)
 *   3. `akayprintbt://print?url=...&x-success=akaydepo://...&x-error=...` URL'ini aç
 *   4. iPad arka plana düşer → AkayPrintBT açılır → ZPL fetch + BT basım
 *   5. Job bitince callback URL ile geri döner (visibility değişikliğiyle de tespit edilir)
 *
 * Bu modül sadece iPad/iOS Safari için anlamlıdır. Diğer platformlarda
 * `akayprintbt://` açılamaz; visibility değişmez ve `installed: false` döner.
 */

export interface ZebraPrintOptions {
  /** API base URL — apiService.baseURL üzerinden gelir. */
  apiBaseUrl: string;
  /** Bu fişin ID'si. */
  loadsheetId: string;
  /** Backend'ten alınan kısa ömürlü print token. */
  printToken: string;
  /** Kopya sayısı (default 1). */
  copies?: number;
  /** Belirli yazıcıya basmak için Zebra serial. Yoksa app'in default'u kullanılır. */
  serial?: string;
}

export interface ZebraPrintResult {
  /**
   * Triggered: URL scheme çağrıldı (Safari → AkayPrintBT geçişi tespit edildi).
   * False ise AkayPrintBT yüklü değil olabilir.
   */
  appOpened: boolean;
  /** Tetiklenen tam URL — log için. */
  triggeredUrl: string;
}

/**
 * ZPL'i AkayPrintBT'ye gönder.
 *
 * Resolve eder: app açıldı mı? (visibility değişikliği gözlemlenir, 1500ms timeout).
 * Reject etmez — başarısızlık `appOpened: false` ile döner.
 */
export function triggerZebraPrint(opts: ZebraPrintOptions): Promise<ZebraPrintResult> {
  const { apiBaseUrl, loadsheetId, printToken, copies, serial } = opts;

  // ZPL endpoint URL'i (iPad bunu fetch eder).
  const zplUrl = `${apiBaseUrl}/v1/loadsheets/${loadsheetId}/zpl?token=${encodeURIComponent(printToken)}`;

  // AkayPrintBT URL scheme'i.
  const u = new URL('akayprintbt://print');
  u.searchParams.set('url', zplUrl);
  if (copies && copies > 1) u.searchParams.set('copies', String(copies));
  if (serial) u.searchParams.set('serial', serial);

  // x-success / x-error callback URL'leri henüz tanımlı değil — AkayDepo PWA
  // olduğu için kendi URL scheme'i yok. İleride native app'e dönerse buraya eklenir.
  // Şimdilik visibility değişikliğine güveniyoruz.

  const triggeredUrl = u.toString();

  return new Promise((resolve) => {
    let resolved = false;
    const finish = (appOpened: boolean) => {
      if (resolved) return;
      resolved = true;
      document.removeEventListener('visibilitychange', onVis);
      clearTimeout(timer);
      resolve({ appOpened, triggeredUrl });
    };

    const onVis = () => {
      // Tab arka plana düşmüşse AkayPrintBT açılmış demektir.
      if (document.visibilityState === 'hidden') {
        finish(true);
      }
    };
    document.addEventListener('visibilitychange', onVis);

    // 1500ms içinde visibility değişmediyse app yüklü değil sayılır.
    const timer = setTimeout(() => finish(false), 1500);

    // URL scheme'i tetikle.
    window.location.href = triggeredUrl;
  });
}
