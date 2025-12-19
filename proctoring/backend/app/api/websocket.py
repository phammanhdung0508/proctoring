"""
WebSocket API Endpoints

This module provides WebSocket endpoints for real-time video streaming
and proctoring analysis.

Technology: FastAPI WebSockets with binary frame transmission
"""

import base64
import json
import time
from typing import Dict

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.detection_pipeline import DetectionPipeline
from app.services.websocket_manager import manager

# Create API router
router = APIRouter()

# Global detection pipeline instance
# Will be initialized in startup event
pipeline: DetectionPipeline = None


def initialize_pipeline():
    """Initialize the detection pipeline."""
    global pipeline
    if pipeline is None:
        print("[INIT] Initializing detection pipeline...")
        # Disable preprocessing temporarily to diagnose detection issues
        pipeline = DetectionPipeline(
            enable_preprocessing=False,
            enable_roi=False,
            enable_adaptive_sampling=True
        )
        print("[SUCCESS] Detection pipeline ready (preprocessing disabled for debugging)")


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time proctoring.

    Protocol:
        Client -> Server: Base64-encoded JPEG frames
        Server -> Client: JSON analysis results

    Args:
        websocket: WebSocket connection
        session_id: Unique session identifier

    Message Format (Client -> Server):
        {
            "type": "frame",
            "data": "base64_encoded_jpeg_data",
            "timestamp": 1234567890.123
        }

    Message Format (Server -> Client):
        {
            "type": "analysis",
            "session_id": "session_123",
            "timestamp": 1234567890.123,
            "gaze": {...},
            "objects": {...},
            "behavior": {...},
            "risk": {...},
            "metadata": {...}
        }
    """
    # Initialize pipeline if not already done
    initialize_pipeline()

    # Accept connection
    await manager.connect(
        websocket,
        session_id,
        metadata={
            "connected_at": time.time(),
            "frames_processed": 0,
        },
    )

    # Send welcome message
    await manager.send_message(
        session_id,
        {
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket connection established",
            "timestamp": time.time(),
        },
    )

    try:
        frames_processed = 0

        while True:
            # Receive message from client
            try:
                # Try to receive JSON first
                data = await websocket.receive_json()

                # Handle different message types
                if data.get("type") == "frame":
                    # Process frame
                    result = await process_frame_message(data, session_id)

                    if result:
                        frames_processed += 1
                        # Update session metadata
                        manager.update_session_metadata(
                            session_id, {"frames_processed": frames_processed}
                        )

                        # Send analysis results back to client
                        response = {
                            "type": "analysis",
                            "session_id": session_id,
                            **result,
                        }
                        print(f"[WS-SEND] Sending analysis to {session_id[:8]}... (risk: {result.get('risk', {}).get('risk_score', 0):.1f})")
                        sent = await manager.send_message(session_id, response)
                        if not sent:
                            print(f"[WS-ERROR] Failed to send message to {session_id[:8]}...")

                elif data.get("type") == "ping":
                    # Respond to ping
                    await manager.send_message(
                        session_id,
                        {
                            "type": "pong",
                            "timestamp": time.time(),
                        },
                    )

                elif data.get("type") == "get_stats":
                    # Send session statistics
                    stats = pipeline.get_session_summary(session_id)
                    await manager.send_message(
                        session_id,
                        {
                            "type": "stats",
                            "session_id": session_id,
                            "data": stats,
                            "timestamp": time.time(),
                        },
                    )

                else:
                    # Unknown message type
                    await manager.send_message(
                        session_id,
                        {
                            "type": "error",
                            "message": f"Unknown message type: {data.get('type')}",
                            "timestamp": time.time(),
                        },
                    )

            except json.JSONDecodeError as e:
                # Try to receive as text (maybe base64 frame directly)
                try:
                    text_data = await websocket.receive_text()
                    # Assume it's a base64-encoded frame
                    result = await process_base64_frame(text_data, session_id)

                    if result:
                        frames_processed += 1
                        await manager.send_message(
                            session_id,
                            {
                                "type": "analysis",
                                "session_id": session_id,
                                **result,
                            },
                        )
                except Exception as text_error:
                    print(f"[ERROR] Error processing text data: {text_error}")
                    await manager.send_message(
                        session_id,
                        {
                            "type": "error",
                            "message": "Invalid frame format",
                            "timestamp": time.time(),
                        },
                    )

    except WebSocketDisconnect:
        print(f"[DISCONNECT] Client disconnected: {session_id}")
        manager.disconnect(session_id)

        # Cleanup session data
        pipeline.clear_session(session_id)

    except Exception as e:
        print(f"[ERROR] WebSocket error for {session_id}: {e}")
        # Send error message to client if still connected
        try:
            await manager.send_message(
                session_id,
                {
                    "type": "error",
                    "message": str(e),
                    "timestamp": time.time(),
                },
            )
        except Exception:
            pass

        manager.disconnect(session_id)
        pipeline.clear_session(session_id)


async def process_frame_message(message: Dict, session_id: str) -> Dict | None:
    """
    Process a frame message from the client.

    Args:
        message: Message containing frame data
        session_id: Session identifier

    Returns:
        Analysis results or None if processing failed
    """
    try:
        # Extract base64-encoded frame
        frame_data = message.get("data")
        if not frame_data:
            print("[WARNING] No frame data in message")
            return None

        print(f"[FRAME] Received frame for session {session_id[:8]}... (size: {len(frame_data)} chars)")

        # Decode base64 to bytes
        frame_bytes = base64.b64decode(frame_data)

        # Convert bytes to numpy array
        nparr = np.frombuffer(frame_bytes, np.uint8)

        # Decode image
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            print("[WARNING] Failed to decode frame")
            return None

        print(f"[DECODE] Frame decoded: {frame.shape}")

        # Process frame through detection pipeline
        timestamp = message.get("timestamp", time.time())
        print("[PROCESS] Processing frame...")
        results = await pipeline.process_frame(frame, session_id, timestamp)

        # Check if frame was skipped
        if results.get("metadata", {}).get("frame_skipped"):
            print("[SKIP] Frame skipped (low motion)")
        else:
            processing_time = results.get('metadata', {}).get('processing_time_ms', 0)
            print(f"[SUCCESS] Frame processed in {processing_time:.1f}ms")

            # Log detection details
            gaze = results.get('gaze', {})
            objects = results.get('objects', {})
            risk = results.get('risk', {})

            print(f"[DETECTION] Face: {gaze.get('face_detected')}, "
                  f"Deviation: {gaze.get('deviation')}, "
                  f"Yaw: {gaze.get('yaw', 0):.1f}°, "
                  f"Pitch: {gaze.get('pitch', 0):.1f}°")
            print(f"[DETECTION] Persons: {objects.get('person_count', 0)}, "
                  f"Forbidden: {len(objects.get('forbidden_items', []))}, "
                  f"Risk: {risk.get('risk_score', 0):.1f}")

        return results

    except Exception as e:
        print(f"[ERROR] Error processing frame message: {e}")
        import traceback
        traceback.print_exc()
        return None


async def process_base64_frame(frame_data: str, session_id: str) -> Dict | None:
    """
    Process a base64-encoded frame directly.

    Args:
        frame_data: Base64-encoded frame string
        session_id: Session identifier

    Returns:
        Analysis results or None if processing failed
    """
    try:
        # Decode base64 to bytes
        frame_bytes = base64.b64decode(frame_data)

        # Convert bytes to numpy array
        nparr = np.frombuffer(frame_bytes, np.uint8)

        # Decode image
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            print("[WARNING] Failed to decode frame")
            return None

        # Process frame through detection pipeline
        results = await pipeline.process_frame(frame, session_id, time.time())

        return results

    except Exception as e:
        print(f"[ERROR] Error processing base64 frame: {e}")
        return None


@router.get("/ws/sessions")
async def get_active_sessions():
    """
    Get list of active WebSocket sessions.

    Returns:
        Dictionary with active session information
    """
    sessions = manager.get_active_sessions()
    session_info = []

    for session_id in sessions:
        metadata = manager.get_session_metadata(session_id)
        session_info.append(
            {
                "session_id": session_id,
                "metadata": metadata,
            }
        )

    return {
        "active_sessions": len(sessions),
        "sessions": session_info,
        "timestamp": time.time(),
    }


@router.get("/ws/pipeline/info")
async def get_pipeline_info():
    """
    Get information about the detection pipeline.

    Returns:
        Pipeline configuration and statistics
    """
    initialize_pipeline()

    return {
        "pipeline": pipeline.get_pipeline_info(),
        "connections": manager.get_connection_count(),
        "timestamp": time.time(),
    }
