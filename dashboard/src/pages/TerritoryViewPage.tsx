import { useCallback, useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService, TerritoryDetail } from '../services/api';
import { usePolling } from '../hooks/usePolling';

export default function TerritoryViewPage() {
  const { territoryCode } = useParams<{ territoryCode: string }>();
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [expandedDealers, setExpandedDealers] = useState<Set<string>>(new Set());

  useEffect(() => {
    apiService.getActiveCycle().then((res) => {
      if (res.has_active_cycle && res.cycle) {
        setCycleId(res.cycle.id);
      }
    });
  }, []);

  const fetchTerritoryDetail = useCallback(async () => {
    if (!territoryCode || !cycleId) return null;
    return apiService.getTerritoryDetail(territoryCode, cycleId);
  }, [territoryCode, cycleId]);

  const { data, isLoading, error, lastUpdated, refresh } = usePolling<TerritoryDetail | null>({
    fetchFn: fetchTerritoryDetail,
    interval: 30000,
    enabled: !!territoryCode && !!cycleId,
  });

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const toggleDealer = (dealerCode: string) => {
    setExpandedDealers(prev => {
      const newSet = new Set(prev);
      if (newSet.has(dealerCode)) {
        newSet.delete(dealerCode);
      } else {
        newSet.add(dealerCode);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    if (data) {
      setExpandedDealers(new Set(data.dealers.map(d => d.dealer_code)));
    }
  };

  const collapseAll = () => {
    setExpandedDealers(new Set());
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'loaded':
        return <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">Tamamlandi</span>;
      case 'pending':
        return <span className="px-3 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">Bekliyor</span>;
      case 'cancelled':
        return <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">Iptal</span>;
      case 'bekliyor':
        return <span className="px-3 py-1 bg-gray-100 text-gray-500 text-xs font-medium rounded-full">Fis Yok</span>;
      default:
        return <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <Link to="/" className="inline-flex items-center gap-2 text-violet-600 hover:text-violet-800 font-medium transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Dashboard'a Don
          </Link>
        </div>

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-cyan-500/30">
                {territoryCode?.slice(-2)}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-800">
                  Bolge: {territoryCode}
                </h1>
                <p className="text-gray-500 mt-1">Bayi siparisleri ve durumu</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {lastUpdated && (
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-500 bg-white rounded-xl px-4 py-2 shadow-sm">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                {formatTime(lastUpdated)}
              </div>
            )}
            <button
              onClick={refresh}
              disabled={isLoading}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 disabled:from-violet-400 disabled:to-purple-500 text-white rounded-xl shadow-lg shadow-violet-500/30 transition-all duration-200"
            >
              <svg
                className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span className="font-medium">Yenile</span>
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-red-600">Hata: {error.message}</p>
          </div>
        )}

        {/* Loading */}
        {isLoading && !data && (
          <div className="flex items-center justify-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg animate-pulse">
              <svg className="w-8 h-8 text-white animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
          </div>
        )}

        {/* Content */}
        {data && (
          <div className="space-y-6">
            {/* Summary Card */}
            <div className="card p-6 animate-fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="stat-icon gradient-cyan">
                    <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-800">Bayi Listesi</h2>
                    <p className="text-sm text-gray-500">{data.dealers.length} bayi</p>
                  </div>
                </div>

                {/* Expand/Collapse All Buttons */}
                {data.dealers.length > 0 && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={expandAll}
                      className="px-3 py-1.5 text-sm font-medium text-violet-600 hover:text-violet-800 hover:bg-violet-50 rounded-lg transition-colors"
                    >
                      Tumunu Ac
                    </button>
                    <button
                      onClick={collapseAll}
                      className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      Tumunu Kapat
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Dealers */}
            {data.dealers.length === 0 ? (
              <div className="card p-8 text-center animate-fade-in">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                  </svg>
                </div>
                <p className="text-gray-500">Bu bolgede bayi bulunamadi</p>
              </div>
            ) : (
              <div className="space-y-4">
                {[...data.dealers]
                  .sort((a, b) => (a.route_order || 999) - (b.route_order || 999))
                  .map((dealer) => {
                  const isExpanded = expandedDealers.has(dealer.dealer_code);
                  const productCount = dealer.products.length;

                  return (
                    <div
                      key={dealer.dealer_code}
                      className="card overflow-hidden animate-fade-in transition-all duration-300"
                    >
                      {/* Collapsible Header */}
                      <button
                        onClick={() => toggleDealer(dealer.dealer_code)}
                        className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center gap-4">
                          {/* Rut Numarasi */}
                          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-violet-500/30">
                            {dealer.route_order || '-'}
                          </div>
                          <div className="text-left">
                            <h3 className="text-lg font-semibold text-gray-800">
                              {dealer.dealer_name}
                            </h3>
                            <p className="text-sm text-gray-500">{dealer.dealer_code}</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          {/* Summary Stats */}
                          <div className="hidden sm:flex items-center gap-4">
                            <div className="text-right">
                              <p className="text-xs text-gray-500">Urun</p>
                              <p className="font-semibold text-gray-800">{productCount}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-xs text-gray-500">Krt</p>
                              <p className="font-semibold text-gray-800">{dealer.total_carton}</p>
                            </div>
                            {dealer.total_pack > 0 && (
                              <div className="text-right">
                                <p className="text-xs text-gray-500">Pkt</p>
                                <p className="font-semibold text-amber-600">{dealer.total_pack}</p>
                              </div>
                            )}
                          </div>

                          {getStatusBadge(dealer.status)}

                          {/* Expand/Collapse Icon */}
                          <div className={`w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>
                            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>
                      </button>

                      {/* Mobile Summary (visible when collapsed) */}
                      {!isExpanded && (
                        <div className="sm:hidden px-5 pb-4 flex items-center gap-4 text-sm">
                          <span className="text-gray-500">{productCount} urun</span>
                          <span className="text-gray-300">|</span>
                          <span className="font-medium text-gray-800">{dealer.total_carton} krt</span>
                          {dealer.total_pack > 0 && (
                            <>
                              <span className="text-gray-300">|</span>
                              <span className="font-medium text-amber-600">{dealer.total_pack} pkt</span>
                            </>
                          )}
                        </div>
                      )}

                      {/* Expandable Content */}
                      <div
                        className={`transition-all duration-300 overflow-hidden ${
                          isExpanded ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0'
                        }`}
                      >
                        <div className="px-5 pb-5 border-t border-gray-100">
                          {dealer.products.length > 0 ? (
                            <div className="overflow-x-auto mt-4">
                              <table className="w-full">
                                <thead>
                                  <tr className="border-b border-gray-200">
                                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Urun Adi</th>
                                    <th className="text-right py-3 px-4 text-sm font-semibold text-gray-600">Krt</th>
                                    <th className="text-right py-3 px-4 text-sm font-semibold text-gray-600">Pkt</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {dealer.products.map((product, idx) => (
                                    <tr key={idx} className="border-b border-gray-100 hover:bg-violet-50/50 transition-colors">
                                      <td className="py-3 px-4 text-gray-800">{product.product_name}</td>
                                      <td className="py-3 px-4 text-right font-medium text-gray-800">{product.quantity_carton}</td>
                                      <td className="py-3 px-4 text-right">
                                        {product.quantity_pack > 0 ? (
                                          <span className="font-medium text-amber-600">{product.quantity_pack}</span>
                                        ) : (
                                          <span className="text-gray-400">-</span>
                                        )}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                                <tfoot>
                                  <tr className="bg-gradient-to-r from-violet-50 to-purple-50">
                                    <td className="py-3 px-4 font-semibold text-gray-700">Toplam</td>
                                    <td className="py-3 px-4 text-right font-bold text-violet-700">{dealer.total_carton}</td>
                                    <td className="py-3 px-4 text-right font-bold text-amber-600">{dealer.total_pack > 0 ? dealer.total_pack : '-'}</td>
                                  </tr>
                                </tfoot>
                              </table>
                            </div>
                          ) : (
                            <div className="mt-4 p-4 bg-gray-50 rounded-xl text-center">
                              <p className="text-sm text-gray-500 italic">Siparis bulunamadi</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
