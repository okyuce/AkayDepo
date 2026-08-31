/**
 * Gün Sonu Sipariş Kontrolü
 *
 * Gün içinde gelen parçalı Excel'ler artımlıdır: bayi siparişini iptal
 * ettiğinde hiçbir dosyada iz kalmaz. Akşam gelen "kapanış" Excel'i günün
 * tamamını içerdiğinden, eksik kalan bayiler iptal edilmiş siparişlerdir.
 *
 * İki adım: önce analiz (hiçbir şey değişmez), sonra kullanıcı onayıyla
 * iptallerin fişlere uygulanması.
 */
import { useEffect, useRef, useState } from 'react';
import { apiService } from '../services/api';
import type { ClosingApplyResult, ClosingHistoryItem, ClosingReport } from '../services/api';
import Navbar from '../components/Navbar';

interface BlockInfo {
  message: string;
  reasons: string[];
  needsConfirm: boolean;
}

export default function ClosingCheckPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [report, setReport] = useState<ClosingReport | null>(null);
  const [applyResult, setApplyResult] = useState<ClosingApplyResult | null>(null);
  const [block, setBlock] = useState<BlockInfo | null>(null);
  const [history, setHistory] = useState<ClosingHistoryItem[]>([]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = () => {
    apiService.getClosingHistory().then(setHistory).catch(() => setHistory([]));
  };

  const resetResults = () => {
    setReport(null);
    setApplyResult(null);
    setBlock(null);
  };

  const pickFile = (file: File | undefined) => {
    if (!file) return;
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setBlock({ message: 'Sadece Excel dosyaları desteklenir (.xlsx, .xls)', reasons: [], needsConfirm: false });
      return;
    }
    setSelectedFile(file);
    resetResults();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  const handleAnalyze = async (force = false) => {
    if (!selectedFile) return;
    setIsAnalyzing(true);
    resetResults();
    try {
      const data = await apiService.analyzeClosing(selectedFile, force);
      setReport(data);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (detail && typeof detail === 'object' && detail.message) {
        setBlock({
          message: detail.message,
          reasons: detail.reasons || [],
          needsConfirm: Boolean(detail.needs_confirm),
        });
      } else {
        setBlock({
          message: typeof detail === 'string' ? detail : 'Kontrol yapılamadı',
          reasons: [],
          needsConfirm: false,
        });
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApply = async () => {
    if (!report) return;
    const n = report.summary.cancelled;
    if (!window.confirm(
      `${n} siparişin fişi İPTAL edilecek. Tamamlanmış fişlerin ürünleri stoka geri eklenecek.\n\nDevam edilsin mi?`
    )) return;

    setIsApplying(true);
    try {
      const res = await apiService.applyClosing(report.check_id);
      setApplyResult(res);
      setReport({ ...report, status: 'applied' });
      loadHistory();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setBlock({
        message: detail?.message || (typeof detail === 'string' ? detail : 'İptaller uygulanamadı'),
        reasons: detail?.reasons || [],
        needsConfirm: false,
      });
    } finally {
      setIsApplying(false);
    }
  };

  const s = report?.summary;
  const hasFindings = !!s && (s.cancelled || s.missing_orders || s.missed_revisions || s.qty_diffs);

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <Navbar />

      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Gün Sonu Sipariş Kontrolü
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
            Günün tamamını kapsayan <strong>kapanış</strong> Excel'ini yükleyin. Sistem dosyayı
            doğrular, aktif döngüyle karşılaştırır ve gün içinde kaçırdığımız iptalleri bulur.
          </p>

          {/* ---------------- Yükleme ---------------- */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
              1. Kapanış Excel'ini Yükle
            </h2>

            <div
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
              onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                isDragging
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
                  : selectedFile
                    ? 'border-green-400 dark:border-green-600 bg-green-50 dark:bg-green-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500'
              }`}
            >
              {selectedFile ? (
                <div className="py-2">
                  <p className="text-sm font-medium text-green-700 dark:text-green-300">{selectedFile.name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </p>
                </div>
              ) : (
                <p className="py-4 text-sm text-gray-600 dark:text-gray-400">
                  Kapanış Excel'ini sürükleyip bırakın veya seçin
                </p>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={(e) => pickFile(e.target.files?.[0])}
                className="hidden"
              />
              <div className="flex items-center justify-center gap-3 mt-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 hover:bg-gray-300 dark:hover:bg-gray-600"
                >
                  Dosya Seç
                </button>
                <button
                  type="button"
                  onClick={() => handleAnalyze(false)}
                  disabled={!selectedFile || isAnalyzing}
                  className={`px-6 py-2.5 rounded-lg text-sm font-semibold text-white ${
                    !selectedFile || isAnalyzing
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {isAnalyzing ? 'Kontrol ediliyor...' : 'Kontrol Et'}
                </button>
              </div>
            </div>
          </div>

          {/* ---------------- Engel / uyarı ---------------- */}
          {block && (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-5 mb-6">
              <h3 className="font-semibold text-red-900 dark:text-red-200 mb-2">
                {block.needsConfirm ? '⚠️ Onay gerekiyor' : '⛔ Dosya kullanılamaz'}
              </h3>
              <p className="text-sm text-red-800 dark:text-red-300 mb-2">{block.message}</p>
              {block.reasons.length > 0 && (
                <ul className="list-disc list-inside text-sm text-red-800 dark:text-red-300 space-y-1">
                  {block.reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
              {block.needsConfirm && (
                <button
                  onClick={() => handleAnalyze(true)}
                  disabled={isAnalyzing}
                  className="mt-4 px-5 py-2 rounded-lg text-sm font-semibold bg-orange-600 text-white hover:bg-orange-700 disabled:bg-gray-400"
                >
                  Dosyanın doğruluğundan eminim, devam et
                </button>
              )}
            </div>
          )}

          {/* ---------------- Rapor ---------------- */}
          {report && s && (
            <>
              <div className={`rounded-lg p-5 mb-6 border ${
                hasFindings
                  ? 'bg-orange-50 dark:bg-orange-900/30 border-orange-300 dark:border-orange-700'
                  : 'bg-green-50 dark:bg-green-900/30 border-green-300 dark:border-green-700'
              }`}>
                <p className={`text-lg font-semibold ${
                  hasFindings ? 'text-orange-900 dark:text-orange-200' : 'text-green-900 dark:text-green-200'
                }`}>
                  {report.message}
                </p>
                <p className="text-xs mt-2 text-gray-600 dark:text-gray-400">
                  Döngü-{report.cycle.cycle_no} · {report.cycle.batch_count} Excel yüklemesi ·
                  {' '}{s.cycle_dealers} bayi · kapanışta {s.closing_dealers} bayi · dosya: {report.filename}
                </p>
                {report.warnings.map((w, i) => (
                  <p key={i} className="text-xs mt-1 text-orange-700 dark:text-orange-300">⚠ {w}</p>
                ))}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
                <StatCard label="İptal edilmiş" value={s.cancelled} tone={s.cancelled ? 'red' : 'green'} />
                <StatCard label="Kaçırılmış revizyon" value={s.missed_revisions} tone={s.missed_revisions ? 'orange' : 'gray'} />
                <StatCard label="Miktar farkı" value={s.qty_diffs} tone={s.qty_diffs ? 'orange' : 'gray'} />
                <StatCard label="Yüklenmemiş sipariş" value={s.missing_orders} tone={s.missing_orders ? 'orange' : 'gray'} />
                <StatCard label="Birebir tutan" value={s.matched} tone="green" />
              </div>

              {/* A — iptaller + uygula */}
              {report.cancelled.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                      İptal edilmiş siparişler ({report.cancelled.length})
                    </h2>
                    {report.status === 'analyzed' && !applyResult && (
                      <button
                        onClick={handleApply}
                        disabled={isApplying}
                        className="px-6 py-2.5 rounded-lg text-sm font-semibold text-white bg-red-600 hover:bg-red-700 disabled:bg-gray-400"
                      >
                        {isApplying ? 'Uygulanıyor...' : 'İptalleri Uygula'}
                      </button>
                    )}
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-700/50 text-gray-600 dark:text-gray-300">
                        <tr>
                          <Th>Bölge</Th><Th>Paket No</Th><Th>Bayi</Th><Th>Sipariş</Th>
                          <Th>Saat</Th><Th className="text-right">Karton</Th>
                          <Th className="text-right">Paket</Th><Th>Fiş Durumu</Th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {report.cancelled.map((c) => (
                          <tr key={c.dealer_code} className="text-gray-800 dark:text-gray-200">
                            <Td>{c.territory_no}</Td>
                            <Td>{c.package_number || '—'}</Td>
                            <Td>
                              <span className="font-medium">{c.dealer_name}</span>
                              <span className="block text-xs text-gray-500 dark:text-gray-400">{c.dealer_code}</span>
                            </Td>
                            <Td className="font-mono text-xs">{c.order_code}</Td>
                            <Td>{c.order_time}</Td>
                            <Td className="text-right">{c.carton}</Td>
                            <Td className="text-right">{c.pack}</Td>
                            <Td>
                              {c.note ? (
                                <span className="text-xs text-gray-500 dark:text-gray-400">{c.note}</span>
                              ) : c.was_loaded ? (
                                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-200">
                                  Yüklenmiş — stok iade edilecek
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-200">
                                  Bekliyor
                                </span>
                              )}
                            </Td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Uygulama sonucu */}
              {applyResult && (
                <div className="bg-green-50 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-lg p-5 mb-6">
                  <p className="text-lg font-semibold text-green-900 dark:text-green-200">{applyResult.message}</p>
                  {(applyResult.skipped?.length ?? 0) > 0 && (
                    <ul className="mt-2 list-disc list-inside text-sm text-green-800 dark:text-green-300">
                      {applyResult.skipped!.map((k, i) => (
                        <li key={i}>{k.dealer_code} — {k.reason}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {report.already_cancelled.length > 0 && (
                <InfoBox title={`Daha önce iptal edilmiş (${report.already_cancelled.length})`}>
                  {report.already_cancelled.map((c) => (
                    <li key={c.dealer_code}>
                      {c.dealer_code} — {c.dealer_name} ({c.note})
                    </li>
                  ))}
                </InfoBox>
              )}

              {/* C — kaçırılmış revizyonlar */}
              {report.missed_revisions.length > 0 && (
                <WarnBox title={`Kaçırılmış revizyonlar (${report.missed_revisions.length})`}
                  note="Kapanışta sipariş kodu farklı. Otomatik işlem YAPILMADI — elle kontrol edin.">
                  {report.missed_revisions.map((r) => (
                    <li key={r.dealer_code}>
                      <span className="font-medium">{r.dealer_code} {r.dealer_name}</span>
                      {r.package_number ? ` · ${r.package_number}` : ''} ·{' '}
                      <span className="font-mono text-xs">{r.db_order_code} → {r.closing_order_code}</span>
                      {r.changes.length > 0 && (
                        <span className="block text-xs ml-4">
                          {r.changes.map((c) => (
                            `${c.product_code}: ${c.old_carton}k${c.old_pack}p → ${c.new_carton}k${c.new_pack}p`
                          )).join(' | ')}
                        </span>
                      )}
                    </li>
                  ))}
                </WarnBox>
              )}

              {/* D — miktar farkları */}
              {report.qty_diffs.length > 0 && (
                <WarnBox title={`Miktar farkları (${report.qty_diffs.length})`}
                  note="Sipariş kodu aynı ama miktarlar değişmiş. Otomatik işlem YAPILMADI.">
                  {report.qty_diffs.map((r) => (
                    <li key={r.dealer_code}>
                      <span className="font-medium">{r.dealer_code} {r.dealer_name}</span>
                      <span className="block text-xs ml-4">
                        {r.changes.map((c) => (
                          `${c.product_code}: ${c.old_carton}k${c.old_pack}p → ${c.new_carton}k${c.new_pack}p`
                        )).join(' | ')}
                      </span>
                    </li>
                  ))}
                </WarnBox>
              )}

              {/* B — hiç yüklenmemiş siparişler */}
              {report.missing_orders.length > 0 && (
                <WarnBox title={`Hiç yüklenmemiş siparişler (${report.missing_orders.length})`}
                  note="Kapanışta var ama sistemde yok — bir Excel atlanmış olabilir. Otomatik işlem YAPILMADI.">
                  {report.missing_orders.map((r) => (
                    <li key={r.dealer_code}>
                      {r.dealer_code} — {r.dealer_name} · {r.territory_code} ·{' '}
                      {r.carton} karton {r.pack} paket · {r.order_time}
                    </li>
                  ))}
                </WarnBox>
              )}
            </>
          )}

          {/* ---------------- Geçmiş ---------------- */}
          {history.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">Kontrol Geçmişi</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-gray-600 dark:text-gray-300">
                    <tr>
                      <Th>Tarih</Th><Th>Dosya</Th><Th>Plan Günü</Th>
                      <Th>Durum</Th><Th className="text-right">İptal</Th><Th>Uygulayan</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {history.map((h) => (
                      <tr key={h.id} className="text-gray-800 dark:text-gray-200">
                        <Td>{new Date(h.uploaded_at).toLocaleString('tr-TR')}</Td>
                        <Td>{h.filename}</Td>
                        <Td>{h.plan_date || '—'}</Td>
                        <Td>
                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            h.status === 'applied'
                              ? 'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-200'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                          }`}>
                            {h.status === 'applied' ? 'Uygulandı' : 'Sadece analiz'}
                          </span>
                        </Td>
                        <Td className="text-right">{h.cancelled_count}</Td>
                        <Td>{h.applied_by || '—'}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 text-left font-semibold ${className}`}>{children}</th>;
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 align-top ${className}`}>{children}</td>;
}

function StatCard({ label, value, tone }: { label: string; value: number; tone: 'red' | 'orange' | 'green' | 'gray' }) {
  const tones = {
    red: 'bg-red-50 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-800 dark:text-red-200',
    orange: 'bg-orange-50 dark:bg-orange-900/30 border-orange-300 dark:border-orange-700 text-orange-800 dark:text-orange-200',
    green: 'bg-green-50 dark:bg-green-900/30 border-green-300 dark:border-green-700 text-green-800 dark:text-green-200',
    gray: 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300',
  };
  return (
    <div className={`rounded-lg border p-3 ${tones[tone]}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs mt-0.5">{label}</div>
    </div>
  );
}

function WarnBox({ title, note, children }: { title: string; note: string; children: React.ReactNode }) {
  return (
    <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-300 dark:border-orange-700 rounded-lg p-5 mb-6">
      <h3 className="font-semibold text-orange-900 dark:text-orange-200">{title}</h3>
      <p className="text-xs text-orange-700 dark:text-orange-300 mb-2">{note}</p>
      <ul className="list-disc list-inside text-sm text-orange-900 dark:text-orange-200 space-y-1">{children}</ul>
    </div>
  );
}

function InfoBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg p-5 mb-6">
      <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-2">{title}</h3>
      <ul className="list-disc list-inside text-sm text-gray-700 dark:text-gray-300 space-y-1">{children}</ul>
    </div>
  );
}
