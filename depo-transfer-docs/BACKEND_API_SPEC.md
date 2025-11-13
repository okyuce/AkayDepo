# BACKEND_API_SPEC (FastAPI)

## Auth
- JWT Bearer (sadece 2 rol: system_user, warehouse_worker)
- **system_user:** Excel yükleme, planlama
- **warehouse_worker:** Tablet görünümü, fiş işlemleri

## Döngü Yönetimi

### Döngü Başlatma (Excel İçe Aktarım)
```
POST /v1/cycles/import
Auth: system_user

Body: {
  "file": <Excel multipart>,
  "run_time": "14:00" | "16:00" | "17:00",
  "plan_date": "2025-11-07"
}

Response: {
  "cycle_id": "uuid",
  "cycle_no": 2,
  "run_time": "16:00",
  "total_rows": 682,
  "total_orders": 61,
  "total_dealers": 58,
  "total_territories": 14,
  "revisions_detected": 12,
  "new_orders": 8,
  "status": "imported"
}
```

### Döngü Durumu Kontrolü
```
GET /v1/cycles/{cycle_id}/status
Auth: system_user

Response: {
  "cycle_id": "uuid",
  "cycle_no": 1,
  "run_time": "14:00",
  "status": "active", // "active", "completed", "archived"
  "total_loadsheets": 53,
  "completed_loadsheets": 50,
  "pending_loadsheets": 3,
  "cancelled_loadsheets": 0,
  "can_start_next_cycle": false, // pending > 0 ise false
  "warnings": [
    "3 fiş henüz tamamlanmadı"
  ]
}
```

### Eksik Fişleri İptal Etme
```
POST /v1/cycles/{cycle_id}/cancel-pending
Auth: system_user

Response: {
  "cancelled_count": 3,
  "can_start_next_cycle": true
}
```

### Revizyon Diff
```
GET /v1/cycles/{cycle_id}/revisions
Auth: system_user

Response: {
  "cycle_from": {
    "cycle_id": "uuid-1",
    "cycle_no": 1,
    "run_time": "14:00"
  },
  "cycle_to": {
    "cycle_id": "uuid-2",
    "cycle_no": 2,
    "run_time": "16:00"
  },
  "revisions": [
    {
      "order_code": "D3J005897253121",
      "dealer_code": "D3J005897",
      "dealer_name": "NUR BAKKAL",
      "changes": [
        {
          "product_code": "PLMNRCB",
          "product_name": "PL Midnight Blue",
          "qty_old_carton": 2,
          "qty_new_carton": 5,
          "qty_change_carton": 3,
          "change_type": "addition"
        },
        {
          "product_code": "MLFTB",
          "product_name": "MLR Touch",
          "qty_old_carton": 2,
          "qty_new_carton": 1,
          "qty_change_carton": -1,
          "change_type": "reduction"
        }
      ]
    }
  ]
}
```

## Planlama

### İstasyon Planı Oluşturma
```
POST /v1/cycles/{cycle_id}/plan
Auth: system_user

Body: {
  "worker_count": 5,
  "force_station_count": null, // null = otomatik, 6 = zorla 6 istasyon
  "method": "greedy" // "greedy" | "ilp"
}

Response: {
  "plan_id": "uuid",
  "cycle_id": "uuid",
  "total_carton": 1675,
  "avg_carton_per_station": 335,
  "stations": [
    {
      "station_id": "uuid",
      "name": "İstasyon-1",
      "total_carton": 350,
      "territories": [
        {
          "territory_code": "TERR030707-Sille",
          "display_number": "T07",
          "carton": 219.5,
          "dealer_count": 11
        },
        {
          "territory_code": "TERR030727-Sancak",
          "display_number": "T27",
          "carton": 77.5,
          "dealer_count": 2
        }
      ]
    }
  ],
  "warnings": [
    {
      "type": "unbalanced_load",
      "territory_code": "TERR030703-Sanayi",
      "carton": 524.6,
      "threshold": 502.5,
      "suggested_station_count": 6,
      "message": "Sanayi çok büyük. 6 istasyon açılması öneriliyor."
    }
  ]
}
```

### Plan Detayı
```
GET /v1/cycles/{cycle_id}/plan
Auth: system_user

Response: { ...aynı format... }
```

## Tablet API (Depocu)

### İstasyon Fişleri (Progress dahil)
```
GET /v1/loadsheets/station/{station_id}?cycle_id={cycle_id}
Auth: warehouse_worker

Response: {
  "cycle": {
    "cycle_id": "uuid",
    "cycle_no": 2,
    "run_time": "16:00"
  },
  "station": {
    "station_id": "uuid",
    "name": "İstasyon-2",
    "total_carton": 310,
    "completed_carton": 279,
    "remaining_carton": 31,
    "progress_percent": 90
  },
  "territories": [
    {
      "territory_code": "TERR030707-Sille",
      "display_number": "T07",
      "name": "Sille",
      "total_carton": 219.5,
      "completed_carton": 219.5,
      "progress_percent": 100,
      "status": "completed",
      "loadsheets": [
        {
          "id": "uuid",
          "package_number": "T07-B01",
          "dealer_code": "D3J005897",
          "dealer_name": "NUR BAKKAL",
          "route_order": 24,
          "total_carton": 28,
          "status": "loaded",
          "is_revision": false,
          "loaded_at": "2025-11-07T10:30:00Z"
        },
        {
          "id": "uuid-rev",
          "package_number": "T07-B01-R",
          "dealer_code": "D3J005897",
          "dealer_name": "NUR BAKKAL",
          "route_order": 24,
          "total_carton": 4,
          "status": "loaded",
          "is_revision": true,
          "parent_loadsheet_id": "uuid",
          "loaded_at": "2025-11-07T11:00:00Z"
        }
      ]
    },
    {
      "territory_code": "TERR030727-Sancak",
      "display_number": "T27",
      "name": "Sancak",
      "total_carton": 77.5,
      "completed_carton": 42,
      "progress_percent": 54,
      "status": "in_progress",
      "loadsheets": [
        {
          "id": "uuid",
          "package_number": "T27-B01",
          "dealer_code": "D3J007812",
          "dealer_name": "ZAFER BÜFE",
          "route_order": 1,
          "total_carton": 42,
          "status": "loaded",
          "is_revision": false,
          "loaded_at": "2025-11-07T11:15:00Z"
        },
        {
          "id": "uuid",
          "package_number": "T27-B02",
          "dealer_code": "D3J007813",
          "dealer_name": "GÜL BAKKAL",
          "route_order": 2,
          "total_carton": 35.5,
          "status": "pending",
          "is_revision": false
        }
      ]
    }
  ],
  "counters": {
    "C1": 310,
    "C2": 31,
    "C3": null
  }
}
```

### Fiş Detay
```
GET /v1/loadsheets/{loadsheet_id}
Auth: warehouse_worker

Response: {
  "id": "uuid",
  "package_number": "T07-B01",
  "cycle_no": 2,
  "station_name": "İstasyon-2",
  "territory": {
    "code": "TERR030707-Sille",
    "display_number": "T07",
    "name": "Sille"
  },
  "dealer": {
    "code": "D3J005897",
    "name": "NUR BAKKAL-BAHRİ DEMİR",
    "route_order": 24
  },
  "lines": [
    {
      "product_code": "PLMNRCB",
      "product_name": "PL Midnight Blue RCB",
      "qty_carton": 2,
      "qty_pack": 0
    },
    {
      "product_code": "MLFTB",
      "product_name": "MLR Touch KS Box",
      "qty_carton": 2,
      "qty_pack": 0
    }
  ],
  "total_carton": 28,
  "status": "pending",
  "is_revision": false,
  "parent_loadsheet_id": null
}
```

### Revizyon Fişi Detay
```
GET /v1/loadsheets/{loadsheet_id} (is_revision=true)

Response: {
  "id": "uuid-rev",
  "package_number": "T07-B01-R",
  "cycle_no": 2,
  "station_name": "İstasyon-2",
  "territory": {...},
  "dealer": {...},
  "is_revision": true,
  "parent_loadsheet_id": "uuid",
  "changes": [
    {
      "product_code": "PLMNRCB",
      "product_name": "PL Midnight Blue",
      "qty_old_carton": 2,
      "qty_new_carton": 5,
      "qty_change_carton": 3,
      "change_type": "addition" // "addition", "reduction", "new_product"
    },
    {
      "product_code": "MLFTB",
      "product_name": "MLR Touch",
      "qty_old_carton": 2,
      "qty_new_carton": 1,
      "qty_change_carton": -1,
      "change_type": "reduction"
    }
  ],
  "net_change_carton": 4,
  "status": "pending"
}
```

### Yükleme Tamamlama
```
POST /v1/loadsheets/{loadsheet_id}/complete
Auth: warehouse_worker

Response: {
  "loadsheet_id": "uuid",
  "status": "loaded",
  "loaded_at": "2025-11-07T10:30:00Z",
  "updated_counters": {
    "C2": 91.5,
    "remaining_territory_carton": 32.8
  },
  "territory_completed": false
}
```

## Sayım (Counter)

### Sayım Durumu
```
GET /v1/counters/station/{station_id}?cycle_id={cycle_id}
Auth: warehouse_worker

Response: {
  "station_id": "uuid",
  "cycle_id": "uuid",
  "counters": [
    {
      "count_index": 1,
      "label": "C1",
      "carton": 310,
      "note": "Başlangıç"
    },
    {
      "count_index": 2,
      "label": "C2",
      "carton": 91.5,
      "note": "Sille tamamlandı (-219.5)"
    },
    {
      "count_index": 3,
      "label": "C3",
      "carton": null,
      "note": "Henüz başlanmadı"
    }
  ]
}
```

## Canlı Güncellemeler

### WebSocket Bağlantısı
```
WS /v1/ws/station/{station_id}
Auth: warehouse_worker (token query param)

Events:
{
  "type": "loadsheet_completed",
  "data": {
    "loadsheet_id": "uuid",
    "package_number": "T07-B01",
    "status": "loaded"
  }
}

{
  "type": "territory_completed",
  "data": {
    "territory_code": "TERR030707-Sille",
    "completed_carton": 219.5,
    "new_counter": {
      "label": "C2",
      "carton": 91.5
    }
  }
}

{
  "type": "revision_added",
  "data": {
    "loadsheet_id": "uuid-rev",
    "package_number": "T07-B01-R",
    "parent_package_number": "T07-B01"
  }
}
```

### SSE (Alternatif)
```
GET /v1/events/station/{station_id}
Auth: warehouse_worker

Content-Type: text/event-stream

event: loadsheet_completed
data: {"loadsheet_id": "uuid", "status": "loaded"}
```
