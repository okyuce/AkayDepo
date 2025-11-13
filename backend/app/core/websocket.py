"""
WebSocket Manager
Real-time güncellemeler için WebSocket yöneticisi
"""
from typing import Dict, Set
from fastapi import WebSocket
from uuid import UUID
import json


class ConnectionManager:
    """WebSocket bağlantılarını yönet"""
    
    def __init__(self):
        # Station ID -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Cycle listeners (tüm istasyonlar için)
        self.cycle_listeners: Set[WebSocket] = set()
    
    async def connect_station(self, websocket: WebSocket, station_id: str):
        """İstasyon tablet'ini bağla"""
        await websocket.accept()
        if station_id not in self.active_connections:
            self.active_connections[station_id] = set()
        self.active_connections[station_id].add(websocket)
    
    async def connect_cycle_listener(self, websocket: WebSocket):
        """Döngü izleyicisi bağla (admin dashboard için)"""
        await websocket.accept()
        self.cycle_listeners.add(websocket)
    
    def disconnect_station(self, websocket: WebSocket, station_id: str):
        """İstasyon tablet'ini ayır"""
        if station_id in self.active_connections:
            self.active_connections[station_id].discard(websocket)
            if not self.active_connections[station_id]:
                del self.active_connections[station_id]
    
    def disconnect_cycle_listener(self, websocket: WebSocket):
        """Döngü izleyicisini ayır"""
        self.cycle_listeners.discard(websocket)
    
    async def broadcast_to_station(self, station_id: str, message: dict):
        """Belirli istasyona mesaj gönder"""
        station_id_str = str(station_id)
        if station_id_str in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[station_id_str]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Kopan bağlantıları temizle
            for conn in disconnected:
                self.active_connections[station_id_str].discard(conn)
    
    async def broadcast_to_cycle(self, message: dict):
        """Tüm döngü izleyicilerine mesaj gönder"""
        disconnected = set()
        for connection in self.cycle_listeners:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Kopan bağlantıları temizle
        for conn in disconnected:
            self.cycle_listeners.discard(conn)
    
    async def notify_loadsheet_completed(self, station_id: UUID, loadsheet_id: UUID, 
                                        package_number: str, territory_completed: bool):
        """Fiş tamamlandı bildirimi"""
        message = {
            "type": "loadsheet_completed",
            "station_id": str(station_id),
            "loadsheet_id": str(loadsheet_id),
            "package_number": package_number,
            "territory_completed": territory_completed
        }
        
        # İstasyona bildir
        await self.broadcast_to_station(str(station_id), message)
        
        # Cycle listeners'a bildir
        await self.broadcast_to_cycle(message)
    
    async def notify_counter_reading(self, station_id: UUID, counter_value: int):
        """Sayaç okuma bildirimi"""
        message = {
            "type": "counter_reading",
            "station_id": str(station_id),
            "counter_value": counter_value
        }
        
        # Cycle listeners'a bildir
        await self.broadcast_to_cycle(message)
    
    async def notify_cycle_completed(self, cycle_id: UUID):
        """Döngü tamamlandı bildirimi"""
        message = {
            "type": "cycle_completed",
            "cycle_id": str(cycle_id)
        }
        
        # Tüm bağlantılara bildir
        for station_connections in self.active_connections.values():
            for connection in station_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass
        
        await self.broadcast_to_cycle(message)


# Global singleton
manager = ConnectionManager()
