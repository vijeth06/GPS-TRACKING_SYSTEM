"""
Socket Manager
==============
WebSocket connection manager for real-time updates.

Uses Socket.IO for bi-directional communication between
the backend and React frontend.
"""

from typing import Dict, Any, List
import json


class SocketManager:
    """
    Manages WebSocket connections and broadcasting.
    
    This is a singleton that maintains active connections and
    provides methods for broadcasting updates to all connected clients.
    
    Events:
    - device_location_update: New GPS location received
    - alert_update: New alert generated
    - device_status_change: Device online/offline status change
    """
    
    def __init__(self):
        self.sio = None  # Will be set by main.py
        self._connected_clients: List[str] = []
    
    def set_socketio(self, sio):
        """Set the Socket.IO server instance."""
        self.sio = sio
    
    async def broadcast_location_update(self, data: Dict[str, Any]):
        """
        Broadcast location update to all connected clients.
        
        Args:
            data: Location update data containing:
                - device_id
                - lat
                - lng
                - speed
                - status
                - timestamp
        """
        if self.sio:
            await self.sio.emit('device_location_update', data)
    
    async def broadcast_alert(self, data: Dict[str, Any]):
        """
        Broadcast alert to all connected clients.
        
        Args:
            data: Alert data containing:
                - id
                - device_id
                - alert_type
                - severity
                - message
                - timestamp
        """
        if self.sio:
            await self.sio.emit('alert_update', data)
    
    async def broadcast_device_status(self, device_id: str, status: str):
        """
        Broadcast device status change.
        
        Args:
            device_id: Device identifier
            status: New status (online, offline, maintenance)
        """
        if self.sio:
            await self.sio.emit('device_status_change', {
                'device_id': device_id,
                'status': status
            })
    
    def add_client(self, sid: str):
        """Register a new client connection."""
        if sid not in self._connected_clients:
            self._connected_clients.append(sid)
    
    def remove_client(self, sid: str):
        """Remove a client connection."""
        if sid in self._connected_clients:
            self._connected_clients.remove(sid)
    
    @property
    def connected_count(self) -> int:
        """Get count of connected clients."""
        return len(self._connected_clients)


# Singleton instance
socket_manager = SocketManager()
