"""
WebSocket Manager
Real-time güncellemeler için WebSocket yöneticisi (depot izolasyonlu)
"""
from typing import Dict, Set
from fastapi import WebSocket
from uuid import UUID


class ConnectionManager:
    """WebSocket bağlantılarını yönet (depot bazlı izolasyon)"""

    def __init__(self):
        # depot_id -> station_id -> Set[WebSocket]
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}
        # depot_id -> Set[WebSocket] (cycle listeners)
        self.cycle_listeners: Dict[str, Set[WebSocket]] = {}

    async def connect_station(self, websocket: WebSocket, station_id: str, depot_id: str = "default"):
        """İstasyon tablet'ini bağla"""
        await websocket.accept()
        if depot_id not in self.active_connections:
            self.active_connections[depot_id] = {}
        if station_id not in self.active_connections[depot_id]:
            self.active_connections[depot_id][station_id] = set()
        self.active_connections[depot_id][station_id].add(websocket)

    async def connect_cycle_listener(self, websocket: WebSocket, depot_id: str = "default"):
        """Döngü izleyicisi bağla (admin dashboard için)"""
        await websocket.accept()
        if depot_id not in self.cycle_listeners:
            self.cycle_listeners[depot_id] = set()
        self.cycle_listeners[depot_id].add(websocket)

    def disconnect_station(self, websocket: WebSocket, station_id: str, depot_id: str = "default"):
        """İstasyon tablet'ini ayır"""
        depot_conns = self.active_connections.get(depot_id, {})
        if station_id in depot_conns:
            depot_conns[station_id].discard(websocket)
            if not depot_conns[station_id]:
                del depot_conns[station_id]
            if not depot_conns:
                del self.active_connections[depot_id]

    def disconnect_cycle_listener(self, websocket: WebSocket, depot_id: str = "default"):
        """Döngü izleyicisini ayır"""
        if depot_id in self.cycle_listeners:
            self.cycle_listeners[depot_id].discard(websocket)
            if not self.cycle_listeners[depot_id]:
                del self.cycle_listeners[depot_id]

    async def broadcast_to_station(self, station_id: str, message: dict, depot_id: str = "default"):
        """Belirli istasyona mesaj gönder"""
        station_id_str = str(station_id)
        depot_conns = self.active_connections.get(depot_id, {})
        if station_id_str in depot_conns:
            disconnected = set()
            for connection in depot_conns[station_id_str]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)

            for conn in disconnected:
                depot_conns[station_id_str].discard(conn)

    async def broadcast_to_cycle(self, message: dict, depot_id: str = "default"):
        """Depo'nun döngü izleyicilerine mesaj gönder"""
        listeners = self.cycle_listeners.get(depot_id, set())
        disconnected = set()
        for connection in listeners:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            listeners.discard(conn)

    async def notify_loadsheet_completed(self, station_id: UUID, loadsheet_id: UUID,
                                        package_number: str, territory_completed: bool,
                                        depot_id: str = "default"):
        """Fiş tamamlandı bildirimi"""
        message = {
            "type": "loadsheet_completed",
            "station_id": str(station_id),
            "loadsheet_id": str(loadsheet_id),
            "package_number": package_number,
            "territory_completed": territory_completed
        }

        await self.broadcast_to_station(str(station_id), message, depot_id=depot_id)
        await self.broadcast_to_cycle(message, depot_id=depot_id)

    async def notify_counter_reading(self, station_id: UUID, counter_value: int,
                                     depot_id: str = "default"):
        """Sayaç okuma bildirimi"""
        message = {
            "type": "counter_reading",
            "station_id": str(station_id),
            "counter_value": counter_value
        }

        await self.broadcast_to_cycle(message, depot_id=depot_id)

    async def notify_cycle_completed(self, cycle_id: UUID, depot_id: str = "default"):
        """Döngü tamamlandı bildirimi"""
        message = {
            "type": "cycle_completed",
            "cycle_id": str(cycle_id)
        }

        # Bu depodaki tüm istasyonlara bildir
        depot_conns = self.active_connections.get(depot_id, {})
        for station_connections in depot_conns.values():
            for connection in station_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

        await self.broadcast_to_cycle(message, depot_id=depot_id)


# Global singleton
manager = ConnectionManager()
