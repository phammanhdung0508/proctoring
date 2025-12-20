"""
Reports API Endpoints

This module provides REST endpoints for retrieving proctoring reports.
"""

from typing import Dict
from fastapi import APIRouter, HTTPException, status

# Import from app.api.websocket to get the shared pipeline instance
# Note: We import the module, not the pipeline directly, to ensure we get the latest reference
# However, pipeline is global in websocket.py
from app.api import websocket

router = APIRouter()

@router.get("/{session_id}", response_model=Dict)
async def get_session_report(session_id: str):
    """
    Get a comprehensive report for a specific session.

    Args:
        session_id: The ID of the session to retrieve report for.

    Returns:
        Dictionary containing session statistics and analysis summary.
    """
    # Ensure pipeline is initialized
    websocket.initialize_pipeline()

    if websocket.pipeline is None:
         raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Detection pipeline not initialized"
        )

    try:
        # We assume pipeline keeps history or we can retrieve it.
        # Based on DetectionPipeline implementation, it has a behavior_analyzer
        # which stores session history.

        # Check if session exists in pipeline/analyzer
        # Accessing internal state is not ideal but necessary given the current API
        if session_id not in websocket.pipeline.behavior_analyzer.session_history:
            # Check if it is an active session in manager?
            # Even if active, it should be in history if frames were processed.
            # If no frames processed, it might not be there.
            pass

        report = websocket.pipeline.get_session_summary(session_id)

        # Enrich report with current status
        from app.services.websocket_manager import manager
        if manager.is_connected(session_id):
            report["status"] = "active"
            report["connection_metadata"] = manager.get_session_metadata(session_id)
        else:
            # If not connected, check if we have data.
            # If get_session_summary returned empty/default stats, it might mean session not found.
            # The current implementation of behavior_analyzer.get_session_stats
            # likely returns defaults for unknown sessions.

            # Let's verify if the session effectively exists (has data)
            # Checking behavior_statistics in report
            stats = report.get("behavior_statistics", {})
            if stats.get("total_frames", 0) == 0 and not manager.is_connected(session_id):
                # If 0 frames and not connected, it likely doesn't exist or was empty.
                # We can return 404 or return empty report.
                # Given no persistent DB, returning what we have is safer,
                # but let's signal if it looks completely empty.

                # However, for now, we return what the pipeline gives us.
                report["status"] = "completed"
            else:
                report["status"] = "completed"

        return report

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )
