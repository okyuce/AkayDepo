/**
 * Loadsheet List Page
 * İstasyon bazında fiş listesi ve detay görünümü
 */
import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import Navbar from '../components/Navbar';

interface Station {
  id: string;
  name: string;
}

interface LoadsheetLine {
  product_code: string;
  product_name: string;
  qty_carton: number;
  qty_pack: number;
}

interface Loadsheet {
  id: string;
  package_number: string;
  dealer_name: string;
  dealer_code: string;
  route_order: number;
  total_carton: number;
  status: string;
  loadsheet_type: string;
  batch_number: number;
  completed_at: string | null;
  lines?: LoadsheetLine[];
  territory?: {
    code: string;
    display_number: string;
    name: string;
  };
}

interface DealerGroup {
  dealer_code: string;
  dealer_name: string;
  route_order: number;
  loadsheets: Loadsheet[];
  cardColor: 'gray' | 'green' | 'orange';
}

export default function LoadsheetListPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('');
  const [loadsheets, setLoadsheets] = useState<Loadsheet[]>([]);
  const [dealerGroups, setDealerGroups] = useState<DealerGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [expandedDealerCode, setExpandedDealerCode] = useState<string | null>(null);

  useEffect(() => {
    loadActiveCycle();
  }, []);

  const loadActiveCycle = async () => {
    try {
      const activeData = await apiService.getActivecycle();
      if (activeData.has_active_cycle && activeData.cycle) {
        setCycleId(activeData.cycle.id);
        if (activeData.cycle.has_plan) {
          await loadStations(activeData.cycle.id);
        }
      }
    } catch (err) {
      console.error('Aktif cycle yüklenemedi:', err);
    }
  };

  const loadStations = async (cycleId: string) => {
    try {
      const plan = await apiService.getPlan(cycleId);
      if (plan && plan.stations) {
        const stationList = plan.stations.map((s: any) => ({
          id: s.station_id,
          name: s.station_name
        }));
        setStations(stationList);
        // İlk istasyonu otomatik seçme - kullanıcı manuel seçsin
      }
    } catch (err) {
      console.error('İstasyonlar yüklenemedi:', err);
    }
  };

  const loadLoadsheets = async (stationId: string) => {
    if (!cycleId) return;
    
    setIsLoading(true);
    try {
      const data = await apiService.getStationLoadsheets(stationId, cycleId);
      // territories içindeki tüm loadsheet'leri düzleştir ve territory bilgisini ekle
      const allLoadsheets: Loadsheet[] = [];
      if (data.territories) {
        data.territories.forEach((territory: any) => {
          if (territory.loadsheets) {
            // Her loadsheet'e territory bilgisini ekle
            const loadsheets = territory.loadsheets.map((ls: any) => ({
              ...ls,
              territory: {
                code: territory.territory_code,
                display_number: territory.display_number,
                name: territory.name
              }
            }));
            allLoadsheets.push(...loadsheets);
          }
        });
      }
      setLoadsheets(allLoadsheets);
      
      // Dealer bazında grupla
      const grouped = groupLoadsheetsByDealer(allLoadsheets);
      setDealerGroups(grouped);
    } catch (err) {
      console.error('Fişler yüklenemedi:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const groupLoadsheetsByDealer = (loadsheets: Loadsheet[]): DealerGroup[] => {
    const groupMap = new Map<string, Loadsheet[]>();
    
    // Dealer code'a göre grupla
    loadsheets.forEach(ls => {
      if (!groupMap.has(ls.dealer_code)) {
        groupMap.set(ls.dealer_code, []);
      }
      groupMap.get(ls.dealer_code)!.push(ls);
    });
    
    // Her grup için renk hesapla
    const groups: DealerGroup[] = [];
    groupMap.forEach((lsList, dealerCode) => {
      // Batch numarasına göre sırala
      lsList.sort((a, b) => a.batch_number - b.batch_number);
      
      const completedCount = lsList.filter(ls => ls.completed_at !== null).length;
      const totalCount = lsList.length;
      
      let cardColor: 'gray' | 'green' | 'orange' = 'gray';
      
      // Kart rengi tamamlanma durumuna göre
      if (completedCount === totalCount) {
        cardColor = 'green';  // Hepsi tamamlandı
      } else if (completedCount > 0 && completedCount < totalCount) {
        cardColor = 'orange'; // Bazıları tamamlandı, bazıları bekliyor
      } else {
        cardColor = 'gray';   // Hiçbiri tamamlanmadı
      }
      
      groups.push({
        dealer_code: dealerCode,
        dealer_name: lsList[0].dealer_name,
        route_order: lsList[0].route_order,
        loadsheets: lsList,
        cardColor
      });
    });
    
    // Route order'a göre sırala
    groups.sort((a, b) => a.route_order - b.route_order);
    
    return groups;
  };

  const handleStationChange = (stationId: string) => {
    setSelectedStationId(stationId);
    if (stationId) {
      loadLoadsheets(stationId);
    }
  };

  const handleDealerCardClick = async (dealerCode: string) => {
    if (expandedDealerCode === dealerCode) {
      setExpandedDealerCode(null);
      return;
    }
    
    // Bu dealer'a ait tüm fişlerin detaylarını yükle
    const group = dealerGroups.find(g => g.dealer_code === dealerCode);
    if (!group) return;
    
    try {
      // Her fiş için detay yükle (paralel)
      const detailPromises = group.loadsheets.map(ls => 
        apiService.getLoadsheetDetail(ls.id)
      );
      const details = await Promise.all(detailPromises);
      
      // Loadsheet'leri güncelle
      const updatedLoadsheets = loadsheets.map(ls => {
        const detail = details.find(d => d.id === ls.id);
        if (detail) {
          return { ...ls, lines: detail.lines, territory: detail.territory };
        }
        return ls;
      });
      setLoadsheets(updatedLoadsheets);
      
      // Dealer groups'u yenile (güncel loadsheets ile)
      const updatedGroups = groupLoadsheetsByDealer(updatedLoadsheets);
      setDealerGroups(updatedGroups);
      
      // Dealer grubu aç
      setExpandedDealerCode(dealerCode);
    } catch (err) {
      console.error('Fiş detayları yüklenemedi:', err);
    }
  };

  const handleCompleteLoadsheet = async (loadsheetId: string) => {
    try {
      await apiService.completeLoadsheet(loadsheetId);
      // Listeyi yenile
      if (selectedStationId) {
        await loadLoadsheets(selectedStationId);
      }
    } catch (err) {
      console.error('Fiş tamamlanamadı:', err);
      alert('Hata: Fiş tamamlanamadı');
    }
  };

  const getCardColorClass = (cardColor: 'gray' | 'green' | 'orange') => {
    switch (cardColor) {
      case 'green':
        return 'bg-green-100 border-green-400';
      case 'orange':
        return 'bg-orange-100 border-orange-400';
      default:
        return 'bg-gray-100 border-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-6">Yükleme Fişleri</h1>

          {!cycleId ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800">
                Aktif döngü bulunamadı. Lütfen önce Excel yükleyip plan oluşturun.
              </p>
            </div>
          ) : stations.length === 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800">
                Plan bulunamadı. Lütfen planlama oluşturun.
              </p>
            </div>
          ) : (
            <>
              {/* İstasyon Seçimi */}
              <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex justify-between items-center">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      İstasyon Seçin
                    </label>
                    <select
                      value={selectedStationId}
                      onChange={(e) => handleStationChange(e.target.value)}
                      className="w-full md:w-64 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">İstasyon Seçiniz...</option>
                      {stations.map((station) => (
                        <option key={station.id} value={station.id}>
                          {station.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <button
                    onClick={() => loadActiveCycle()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
                  >
                    Yenile
                  </button>
                </div>
              </div>

              {/* Fiş Listesi */}
              {!selectedStationId ? (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                  <p className="text-center text-blue-800">
                    Lütfen yukarıdaki listeden bir istasyon seçin.
                  </p>
                </div>
              ) : isLoading ? (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <p className="text-center text-gray-500">Yüklüyor...</p>
                </div>
              ) : dealerGroups.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <p className="text-center text-gray-500">Fiş bulunamadı</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {dealerGroups.map((group) => {
                    const isExpanded = expandedDealerCode === group.dealer_code;

                    return (
                      <div
                        key={group.dealer_code}
                        className={`border-2 rounded-lg overflow-hidden ${getCardColorClass(group.cardColor)}`}
                      >
                        {/* Dealer Card Header */}
                        <div
                          className="p-4 cursor-pointer hover:bg-opacity-80 transition"
                          onClick={() => handleDealerCardClick(group.dealer_code)}
                        >
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className="text-3xl font-bold text-gray-900 bg-white px-3 py-1 rounded">
                                {group.route_order}
                              </span>
                              <div>
                                <h3 className="font-bold text-xl text-gray-900">
                                  {group.dealer_name}
                                </h3>
                                <p className="text-sm text-gray-600 mt-1">
                                  {group.dealer_code}
                                </p>
                                <div className="flex items-center gap-3 mt-2">
                                  <span className={`text-xs px-2 py-1 rounded font-semibold ${
                                    group.loadsheets.length > 1 
                                      ? 'bg-orange-500 text-white' 
                                      : 'bg-white text-gray-800'
                                  }`}>
                                    {group.loadsheets.length} Fiş
                                  </span>
                                  {group.cardColor === 'green' && (
                                    <span className="text-xs text-green-700 font-semibold">✓ Tamam</span>
                                  )}
                                  {group.cardColor === 'orange' && (
                                    <span className="text-xs text-orange-700 font-semibold">⚠ Ek Fiş</span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <span className="text-2xl text-gray-600">
                              {isExpanded ? '▲' : '▼'}
                            </span>
                          </div>
                        </div>

                        {/* Expanded: Tüm fişler */}
                        {isExpanded && (
                          <div className="bg-white border-t-2 border-gray-300 p-4 space-y-6">
                            {group.loadsheets.map((loadsheet) => {
                              const totalCartons = loadsheet.lines?.reduce((sum, line) => sum + line.qty_carton, 0) || 0;
                              const totalPacks = loadsheet.lines?.reduce((sum, line) => sum + (line.qty_pack || 0), 0) || 0;

                              return (
                                <div key={loadsheet.id} className="border-2 border-gray-200 rounded">
                                  {/* Fiş Başlık */}
                                  <div className="bg-gray-50 p-3 flex justify-between items-center">
<div className="flex items-center gap-2">
                                      <span className={loadsheet.batch_number >= 2 ? 'font-bold text-lg bg-orange-100 text-orange-800 px-2 py-0.5 rounded' : 'font-bold text-lg'}>
                                        FIŞ-{loadsheet.batch_number}
                                      </span>
                                      <span className="text-sm text-gray-600 ml-1">{loadsheet.package_number}</span>
                                    </div>
                                    {!loadsheet.completed_at ? (
                                      <button
                                        onClick={() => handleCompleteLoadsheet(loadsheet.id)}
                                        className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 text-sm font-semibold"
                                      >
                                        Tamamla
                                      </button>
                                    ) : (
                                      <span className="text-green-700 font-semibold text-sm">✓ Tamamlandı</span>
                                    )}
                                  </div>

                                  {/* Fiş Detay Tablosu */}
                                  {loadsheet.lines && (
                                    <table className="w-full">
                                      <thead className="bg-gray-100">
                                        <tr>
                                          <th className="text-left p-3 font-bold border-b-2 border-gray-300">Rut Sırası</th>
                                          <th className="text-right p-3 font-bold border-b-2 border-gray-300 w-20">Krt</th>
                                          <th className="text-right p-3 font-bold border-b-2 border-gray-300 w-20">Pkt</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        <tr className="bg-black text-white font-bold">
                                          <td className="p-2">{loadsheet.dealer_name}</td>
                                          <td className="p-2 text-right">{totalCartons}</td>
                                          <td className="p-2 text-right">{totalPacks || ''}</td>
                                        </tr>
                                        <tr>
                                          <td className="p-2" colSpan={3}>{loadsheet.dealer_code}</td>
                                        </tr>
                                        <tr className="bg-black text-white">
                                          <td className="p-2" colSpan={3}>
                                            {loadsheet.territory ? `${loadsheet.territory.code}-${loadsheet.territory.name}` : 'TERR'}
                                          </td>
                                        </tr>
                                        {loadsheet.lines.map((line, idx) => (
                                          <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                                            <td className="p-2">{line.product_name}</td>
                                            <td className="p-2 text-right font-semibold">{line.qty_carton}</td>
                                            <td className="p-2 text-right">{line.qty_pack || ''}</td>
                                          </tr>
                                        ))}
                                        <tr className="bg-gray-100 font-bold border-t-2 border-gray-300">
                                          <td className="p-3">Toplam</td>
                                          <td className="p-3 text-right">{totalCartons}</td>
                                          <td className="p-3 text-right">{totalPacks || ''}</td>
                                        </tr>
                                      </tbody>
                                    </table>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
