import json
import logging
from typing import Dict, List, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps room names (e.g., 'hospital_123', 'chat_456') to set of WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = set()
        self.active_connections[room].add(websocket)
        logger.info(f"WebSocket connected to room '{room}'. Total rooms: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            self.active_connections[room].discard(websocket)
            if not self.active_connections[room]:
                del self.active_connections[room]
        logger.info(f"WebSocket disconnected from room '{room}'")

    async def broadcast_to_room(self, room: str, event_type: str, payload: Any):
        if room not in self.active_connections:
            return
            
        message = {
            "event": event_type,
            "data": payload
        }
        
        # Make a copy of connections to prevent mutation during iteration
        sockets = list(self.active_connections[room])
        for socket in sockets:
            try:
                await socket.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending message to socket in room {room}: {e}")
                # Clean up stale connection
                self.disconnect(socket, room)

# Global connection manager instance
manager = ConnectionManager()

def ws_broadcast(room: str, event_type: str, payload: Any):
    """
    Synchronous helper to enqueue websocket broadcasts.
    We can run it in background tasks or import the manager directly.
    """
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        loop.create_task(manager.broadcast_to_room(room, event_type, payload))
    else:
        # Fallback if no loop is running (e.g. startup/shutdown/sync context)
        asyncio.run(manager.broadcast_to_room(room, event_type, payload))
