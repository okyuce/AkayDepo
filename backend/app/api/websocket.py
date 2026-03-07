"""
WebSocket API Router
Real-time bağlantılar için WebSocket endpoint'leri (depot izolasyonlu)
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
from app.core.websocket import manager

router = APIRouter()


@router.websocket("/station/{station_id}")
async def websocket_station(
    websocket: WebSocket,
    station_id: str,
    depot_id: Optional[str] = Query(default="default")
):
    """
    İstasyon tablet'i için WebSocket bağlantısı

    Args:
        station_id: İstasyon UUID
        depot_id: Depo UUID (query param)
    """
    d_id = depot_id or "default"
    await manager.connect_station(websocket, station_id, depot_id=d_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_station(websocket, station_id, depot_id=d_id)


@router.websocket("/cycle")
async def websocket_cycle(
    websocket: WebSocket,
    depot_id: Optional[str] = Query(default="default")
):
    """
    Döngü izleme için WebSocket bağlantısı (admin dashboard)
    Sadece bu deponun güncellemelerini dinler

    Args:
        depot_id: Depo UUID (query param)
    """
    d_id = depot_id or "default"
    await manager.connect_cycle_listener(websocket, depot_id=d_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_cycle_listener(websocket, depot_id=d_id)
