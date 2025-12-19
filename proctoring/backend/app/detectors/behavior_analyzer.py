"""
Behavior Analysis Module - Stream 3

This module performs temporal pattern analysis to detect repeated
suspicious behaviors and behavioral anomalies.

Technology: Temporal pattern analysis with sliding windows
"""

import asyncio
from collections import defaultdict, deque
from typing import Dict, List

import numpy as np

from app.config import settings


class BehaviorAnalyzer:
    """
    Analyzes behavioral patterns over time to detect suspicious activities.

    Tracks:
        - Repeated violations in timewindows
        - Behavioral pattern anomalies
        - Session-specific baselines

    Attributes:
        session_history: Dict storing detection history per session
        window_size: Number of frames to analyze (sliding window)
    """

    def __init__(self, window_size: int = None):
        """
        Initialize the Behavior Analyzer.

        Args:
            window_size: Number of frames in sliding window.
                        If None, uses value from settings.
        """
        # Session-specific history storage
        # Format: {session_id: {"gaze_deviations": deque, "objects": deque, ...}}
        self.session_history: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: {
                "gaze_deviations": deque(maxlen=window_size or settings.WINDOW_SIZE),
                "forbidden_objects": deque(maxlen=window_size or settings.WINDOW_SIZE),
                "person_counts": deque(maxlen=window_size or settings.WINDOW_SIZE),
                "timestamps": deque(maxlen=window_size or settings.WINDOW_SIZE),
            }
        )

        self.window_size = window_size or settings.WINDOW_SIZE

    async def analyze(self, frame: np.ndarray, session_id: str, detection_results: Dict = None) -> Dict:
        """
        Analyze behavioral patterns for a session.

        Args:
            frame: Current video frame (not used directly, placeholder for future)
            session_id: Unique session identifier
            detection_results: Optional pre-computed detection results to analyze

        Returns:
            Dictionary containing:
                - repeated_deviations (int): Count of repeated gaze deviations
                - repeated_objects (int): Count of repeated object detections
                - pattern_score (float): Behavioral pattern anomaly score
                - avg_person_count (float): Average person count in window
                - analysis_summary (str): Human-readable summary
        """
        # Run analysis in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._analyze_sync, session_id, detection_results
        )
        return result

    def _analyze_sync(self, session_id: str, detection_results: Dict = None) -> Dict:
        """
        Synchronous analysis method (runs in thread pool).

        Args:
            session_id: Unique session identifier
            detection_results: Detection results to analyze

        Returns:
            Analysis results dictionary
        """
        history = self.session_history[session_id]

        # If detection results provided, update history
        if detection_results:
            self._update_history(session_id, detection_results)

        # Analyze patterns
        gaze_deviations = list(history["gaze_deviations"])
        forbidden_objects = list(history["forbidden_objects"])
        person_counts = list(history["person_counts"])

        # Count repeated violations
        repeated_deviations = sum(1 for d in gaze_deviations if d)
        repeated_objects = sum(1 for o in forbidden_objects if len(o) > 0)

        # Calculate average person count
        avg_person_count = (
            np.mean(person_counts) if person_counts else 0.0
        )

        # Calculate pattern anomaly score
        pattern_score = self._calculate_pattern_score(
            repeated_deviations, repeated_objects, avg_person_count
        )

        # Generate summary
        summary = self._generate_summary(
            repeated_deviations, repeated_objects, avg_person_count
        )

        return {
            "repeated_deviations": repeated_deviations,
            "repeated_objects": repeated_objects,
            "pattern_score": pattern_score,
            "avg_person_count": float(avg_person_count),
            "analysis_summary": summary,
            "window_frames": len(gaze_deviations),
        }

    def _update_history(self, session_id: str, detection_results: Dict) -> None:
        """
        Update session history with new detection results.

        Args:
            session_id: Unique session identifier
            detection_results: Detection results from gaze and object detectors
        """
        import time

        history = self.session_history[session_id]

        # Extract relevant data from detection results
        gaze_deviation = detection_results.get("gaze", {}).get("deviation", False)
        forbidden_items = detection_results.get("objects", {}).get("forbidden_items", [])
        person_count = detection_results.get("objects", {}).get("person_count", 0)

        # Append to history queues
        history["gaze_deviations"].append(gaze_deviation)
        history["forbidden_objects"].append(forbidden_items)
        history["person_counts"].append(person_count)
        history["timestamps"].append(time.time())

    def _calculate_pattern_score(
        self,
        repeated_deviations: int,
        repeated_objects: int,
        avg_person_count: float,
    ) -> float:
        """
        Calculate behavioral pattern anomaly score.

        Args:
            repeated_deviations: Number of gaze deviations in window
            repeated_objects: Number of object detections in window
            avg_person_count: Average person count

        Returns:
            Pattern score (0-100)
        """
        # Calculate score based on frequency of violations
        deviation_ratio = repeated_deviations / self.window_size if self.window_size > 0 else 0
        object_ratio = repeated_objects / self.window_size if self.window_size > 0 else 0

        # Weight the components
        score = (
            (deviation_ratio * 30)  # Gaze deviations contribute 30%
            + (object_ratio * 40)  # Objects contribute 40%
            + (max(0, avg_person_count - 1) * 30)  # Extra persons contribute 30%
        )

        return min(score, 100.0)

    def _generate_summary(
        self,
        repeated_deviations: int,
        repeated_objects: int,
        avg_person_count: float,
    ) -> str:
        """
        Generate human-readable analysis summary.

        Args:
            repeated_deviations: Number of gaze deviations
            repeated_objects: Number of object detections
            avg_person_count: Average person count

        Returns:
            Summary string
        """
        summaries = []

        if repeated_deviations > self.window_size * 0.3:
            summaries.append("Frequent gaze deviations detected")

        if repeated_objects > self.window_size * 0.2:
            summaries.append("Repeated forbidden object detections")

        if avg_person_count > 1.5:
            summaries.append("Multiple persons frequently present")

        if not summaries:
            return "Normal behavior"

        return "; ".join(summaries)

    def get_session_stats(self, session_id: str) -> Dict:
        """
        Get statistics for a specific session.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with session statistics
        """
        if session_id not in self.session_history:
            return {"error": "Session not found"}

        history = self.session_history[session_id]

        return {
            "session_id": session_id,
            "total_frames_analyzed": len(history["gaze_deviations"]),
            "total_gaze_deviations": sum(1 for d in history["gaze_deviations"] if d),
            "total_object_detections": sum(
                len(obj) for obj in history["forbidden_objects"]
            ),
            "avg_person_count": float(np.mean(list(history["person_counts"])))
            if history["person_counts"]
            else 0.0,
        }

    def clear_session(self, session_id: str) -> None:
        """
        Clear history for a specific session.

        Args:
            session_id: Unique session identifier
        """
        if session_id in self.session_history:
            del self.session_history[session_id]

    def clear_all_sessions(self) -> None:
        """Clear history for all sessions."""
        self.session_history.clear()
