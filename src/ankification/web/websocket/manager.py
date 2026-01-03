"""WebSocket connection manager."""

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Accept and register a WebSocket connection.

        Args:
            websocket: WebSocket connection
            connection_id: Unique ID for this connection (e.g., job_id or user_id)
        """
        await websocket.accept()
        if connection_id not in self.active_connections:
            self.active_connections[connection_id] = []
        self.active_connections[connection_id].append(websocket)

    def disconnect(self, websocket: WebSocket, connection_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
            connection_id: ID of the connection
        """
        if connection_id in self.active_connections:
            if websocket in self.active_connections[connection_id]:
                self.active_connections[connection_id].remove(websocket)
            if not self.active_connections[connection_id]:
                del self.active_connections[connection_id]

    async def send_message(
        self, message: dict[str, Any], connection_id: str
    ) -> None:
        """Send a message to all connections with the given ID.

        Args:
            message: Message data to send
            connection_id: ID of connections to send to
        """
        if connection_id not in self.active_connections:
            return

        message_text = json.dumps(message)
        disconnected = []

        for connection in self.active_connections[connection_id]:
            try:
                await connection.send_text(message_text)
            except Exception:
                # Connection is dead, mark for removal
                disconnected.append(connection)

        # Clean up dead connections
        for connection in disconnected:
            self.disconnect(connection, connection_id)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all active connections.

        Args:
            message: Message data to send
        """
        message_text = json.dumps(message)
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_text(message_text)
                except Exception:
                    # Ignore errors for broadcast
                    pass


# Global connection manager instance
manager = ConnectionManager()
