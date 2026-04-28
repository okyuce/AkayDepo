/**
 * printShare — DOM elemanını PNG'ye render edip Web Share API ile paylaşır.
 * Zebra Setup Utility v3 paylaşılan PNG'yi yakalayıp Bluetooth ile yazıcıya gönderir.
 *
 * Akış:
 *   1. html2canvas ile element → canvas
 *   2. canvas.toBlob → File (image/png)
 *   3. navigator.share({ files: [file] })
 * Web Share API yoksa veya dosya paylaşımı desteklenmiyorsa → PNG dosyasını indirir.
 */
import html2canvas from 'html2canvas';

export interface PrintShareOptions {
  filename?: string;
  title?: string;
  text?: string;
}

export async function renderAndShare(
  element: HTMLElement,
  opts: PrintShareOptions = {}
): Promise<{ shared: boolean; downloaded: boolean; reason?: string }> {
  const filename = opts.filename || `etiket-${Date.now()}.png`;
  const title = opts.title || 'Yükleme Fişi';
  const text = opts.text || 'Yükleme fişi etiketi';

  const canvas = await html2canvas(element, {
    backgroundColor: '#ffffff',
    scale: 1,
    useCORS: true,
    logging: false,
  });

  const blob: Blob | null = await new Promise((resolve) =>
    canvas.toBlob((b) => resolve(b), 'image/png', 1.0)
  );
  if (!blob) {
    throw new Error('PNG render edilemedi');
  }

  const file = new File([blob], filename, { type: 'image/png' });

  // Web Share API (iOS 15+) — Setup Utility Share Sheet'te listelenir
  const nav = navigator as Navigator & {
    canShare?: (data: ShareData) => boolean;
    share?: (data: ShareData) => Promise<void>;
  };
  if (nav.share && nav.canShare && nav.canShare({ files: [file] })) {
    try {
      await nav.share({ files: [file], title, text });
      return { shared: true, downloaded: false };
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        return { shared: false, downloaded: false, reason: 'user_cancelled' };
      }
      // Share başarısız oldu; download fallback'ine düş
    }
  }

  // Fallback: PNG'yi indir
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);

  return { shared: false, downloaded: true, reason: 'web_share_unavailable' };
}
