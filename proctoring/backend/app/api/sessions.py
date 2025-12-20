"""
Sessions API Endpoints

This module provides REST endpoints for managing proctoring sessions.
"""

import time
from typing import Dict, List

from fastapi import APIRouter, HTTPException, status, WebSocketDisconnect

from app.services.websocket_manager import manager

router = APIRouter()


@router.get("/", response_model=Dict)
async def get_all_sessions():
    """
    Get all active sessions.

    Returns:
        List of active session IDs and their metadata.
    """
    sessions = manager.get_active_sessions()
    session_list = []

    for session_id in sessions:
        metadata = manager.get_session_metadata(session_id)
        session_list.append({
            "session_id": session_id,
            "metadata": metadata,
            "is_connected": manager.is_connected(session_id)
        })

    return {
        "count": len(sessions),
        "sessions": session_list,
        "timestamp": time.time()
    }


@router.get("/{session_id}", response_model=Dict)
async def get_session_details(session_id: str):
    """
    Get details for a specific session.

    Args:
        session_id: The ID of the session to retrieve.

    Returns:
        Session details including metadata.
    """
    if not manager.is_connected(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    metadata = manager.get_session_metadata(session_id)
    return {
        "session_id": session_id,
        "metadata": metadata,
        "status": "active",
        "timestamp": time.time()
    }


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_session(session_id: str):
    """
    Terminate an active session.

    Args:
        session_id: The ID of the session to terminate.
    """
    if not manager.is_connected(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    # Attempt to close the WebSocket connection gracefully
    websocket = manager.active_connections.get(session_id)
    if websocket:
        try:
            await websocket.close(code=1000, reason="Terminated by API")
        except Exception as e:
            # If we can't close it, force disconnect
            print(f"Error closing websocket for session {session_id}: {e}")
            manager.disconnect(session_id)
    else:
        # Should not happen if is_connected is true, but just in case
        manager.disconnect(session_id)
