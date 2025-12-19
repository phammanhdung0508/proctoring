"""
WebSocket Connection Manager

This module manages WebSocket connections for real-time video streaming
and proctoring communication.

Technology: FastAPI WebSockets with async/await
"""

import json
from typing import Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from app.utils.json_utils import convert_numpy_types


class ConnectionManager:
    """
    Manages active WebSocket connections for proctoring sessions.

    Handles:
        - Connection lifecycle (connect, disconnect)
        - Session tracking
        - Message broadcasting
        - Connection state management

    Attributes:
        active_connections: Dict mapping session_ids to WebSocket connections
        connection_metadata: Dict storing metadata for each connection
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Map session_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

        # Store metadata for each connection
        self.connection_metadata: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str, metadata: Optional[Dict] = None) -> None:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection to accept
            session_id: Unique session identifier
            metadata: Optional metadata about the connection
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.connection_metadata[session_id] = metadata or {}

        print(f"[CONNECT] WebSocket connected: {session_id}")
        print(f"[INFO] Active connections: {len(self.active_connections)}")

    def disconnect(self, session_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            session_id: Session identifier to disconnect
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            del self.connection_metadata[session_id]
            print(f"[DISCONNECT] WebSocket disconnected: {session_id}")
            print(f"[INFO] Active connections: {len(self.active_connections)}")

    async def send_message(self, session_id: str, message: Dict) -> bool:
        """
        Send a message to a specific session.

        Args:
            session_id: Target session identifier
            message: Message dictionary to send (will be JSON serialized)

        Returns:
            True if message sent successfully, False otherwise
        """
        if session_id not in self.active_connections:
            print(f"[WARNING] Session not found: {session_id}")
            return False

        try:
            # Convert NumPy types to Python native types for JSON serialization
            message = convert_numpy_types(message)

            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
            return True
        except WebSocketDisconnect:
            print(f"[WARNING] Connection lost while sending to {session_id}")
            self.disconnect(session_id)
            return False
        except Exception as e:
            print(f"[ERROR] Error sending message to {session_id}: {e}")
            return False

    async def send_text(self, session_id: str, text: str) -> bool:
        """
        Send a text message to a specific session.

        Args:
            session_id: Target session identifier
            text: Text message to send

        Returns:
            True if message sent successfully, False otherwise
        """
        if session_id not in self.active_connections:
            return False

        try:
            websocket = self.active_connections[session_id]
            await websocket.send_text(text)
            return True
        except Exception as e:
            print(f"[ERROR] Error sending text to {session_id}: {e}")
            self.disconnect(session_id)
            return False

    async def broadcast(self, message: Dict, exclude: Optional[List[str]] = None) -> None:
        """
        Broadcast a message to all active connections.

        Args:
            message: Message dictionary to broadcast
            exclude: Optional list of session_ids to exclude from broadcast
        """
        exclude = exclude or []
        disconnected = []

        # Convert NumPy types to Python native types for JSON serialization
        message = convert_numpy_types(message)

        for session_id, websocket in self.active_connections.items():
            if session_id in exclude:
                continue

            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(session_id)
            except Exception as e:
                print(f"[ERROR] Broadcast error to {session_id}: {e}")
                disconnected.append(session_id)

        # Clean up disconnected sessions
        for session_id in disconnected:
            self.disconnect(session_id)

    def get_active_sessions(self) -> List[str]:
        """
        Get list of active session IDs.

        Returns:
            List of session identifiers
        """
        return list(self.active_connections.keys())

    def get_session_metadata(self, session_id: str) -> Optional[Dict]:
        """
        Get metadata for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            Metadata dictionary or None if session not found
        """
        return self.connection_metadata.get(session_id)

    def update_session_metadata(self, session_id: str, metadata: Dict) -> bool:
        """
        Update metadata for a session.

        Args:
            session_id: Session identifier
            metadata: Metadata to update

        Returns:
            True if updated successfully, False if session not found
        """
        if session_id not in self.connection_metadata:
            return False

        self.connection_metadata[session_id].update(metadata)
        return True

    def is_connected(self, session_id: str) -> bool:
        """
        Check if a session is currently connected.

        Args:
            session_id: Session identifier

        Returns:
            True if connected, False otherwise
        """
        return session_id in self.active_connections

    def get_connection_count(self) -> int:
        """
        Get the number of active connections.

        Returns:
            Number of active connections
        """
        return len(self.active_connections)

    async def close_all(self) -> None:
        """Close all active connections gracefully."""
        print("[SHUTDOWN] Closing all WebSocket connections...")

        for session_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.close(code=1000, reason="Server shutdown")
            except Exception as e:
                print(f"[WARNING] Error closing connection {session_id}: {e}")

        self.active_connections.clear()
        self.connection_metadata.clear()
        print("[SUCCESS] All connections closed")


# Global connection manager instance
manager = ConnectionManager()
