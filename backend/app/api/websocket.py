"""
WebSocket API Router
Real-time bağlantılar için WebSocket endpoint'leri
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket import manager

router = APIRouter()


@router.websocket("/station/{station_id}")
async def websocket_station(websocket: WebSocket, station_id: str):
    """
    İstasyon tablet'i için WebSocket bağlantısı
    
    Args:
        station_id: İstasyon UUID
    """
    await manager.connect_station(websocket, station_id)
    try:
        while True:
            # Heartbeat bekle (client ping gönderir)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_station(websocket, station_id)


@router.websocket("/cycle")
async def websocket_cycle(websocket: WebSocket):
    """
    Döngü izleme için WebSocket bağlantısı (admin dashboard)
    
    Tüm istasyonların güncellemelerini dinler
    """
    await manager.connect_cycle_listener(websocket)
    try:
        while True:
            # Heartbeat bekle
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_cycle_listener(websocket)
