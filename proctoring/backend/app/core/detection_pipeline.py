"""
Detection Pipeline Orchestrator

This module orchestrates all detection streams (gaze, objects, behavior)
and coordinates risk scoring for comprehensive analysis.

Technology: Async/await with concurrent processing
"""

import asyncio
import time
from typing import Dict, Optional

import numpy as np

from app.config import settings
from app.core.risk_scorer import RiskScorer
from app.detectors.behavior_analyzer import BehaviorAnalyzer
from app.detectors.gaze_detector import GazeDetector
from app.detectors.object_detector import ObjectDetector
from app.preprocessing.image_preprocessor import (
    ImagePreprocessor,
    ROIExtractor,
    AdaptiveFrameSampler,
)


class DetectionPipeline:
    """
    Orchestrates all detection modules for comprehensive frame analysis.

    Coordinates three detection streams:
        1. Gaze detection (MediaPipe Face Mesh)
        2. Object detection (YOLOv8)
        3. Behavior analysis (temporal patterns)

    Then aggregates results and calculates risk scores.

    Attributes:
        gaze_detector: GazeDetector instance
        object_detector: ObjectDetector instance
        behavior_analyzer: BehaviorAnalyzer instance
        risk_scorer: RiskScorer instance
        preprocessor: ImagePreprocessor for frame enhancement
        roi_extractor: ROIExtractor for focused processing
        frame_sampler: AdaptiveFrameSampler for intelligent frame selection
        enable_preprocessing: Flag to enable/disable preprocessing
    """

    def __init__(
        self,
        gaze_detector: Optional[GazeDetector] = None,
        object_detector: Optional[ObjectDetector] = None,
        behavior_analyzer: Optional[BehaviorAnalyzer] = None,
        risk_scorer: Optional[RiskScorer] = None,
        enable_preprocessing: bool = True,
        enable_roi: bool = False,  # ROI disabled by default (may affect face detection)
        enable_adaptive_sampling: bool = True,
    ):
        """
        Initialize the detection pipeline with advanced preprocessing.

        Args:
            gaze_detector: Optional pre-initialized GazeDetector
            object_detector: Optional pre-initialized ObjectDetector
            behavior_analyzer: Optional pre-initialized BehaviorAnalyzer
            risk_scorer: Optional pre-initialized RiskScorer
            enable_preprocessing: Enable CLAHE and bilateral filtering
            enable_roi: Enable ROI extraction (experimental)
            enable_adaptive_sampling: Enable motion-based adaptive sampling

        If any detector is None, creates a new instance with default settings.
        """
        # Initialize detectors
        self.gaze_detector = gaze_detector or GazeDetector()
        self.object_detector = object_detector or ObjectDetector()
        self.behavior_analyzer = behavior_analyzer or BehaviorAnalyzer()
        self.risk_scorer = risk_scorer or RiskScorer()

        # Initialize preprocessing modules (Phase 1 optimizations)
        self.enable_preprocessing = enable_preprocessing
        self.preprocessor = ImagePreprocessor(
            enable_clahe=enable_preprocessing,
            enable_bilateral=enable_preprocessing,
            enable_gamma=False,  # Gamma correction disabled by default
        )

        self.roi_extractor = ROIExtractor(
            roi_ratio=0.7,  # Extract top 70% of frame
            enable_roi=enable_roi,
        )

        self.frame_sampler = AdaptiveFrameSampler(
            motion_threshold=10.0,  # Moderate sensitivity
            min_fps=2.0,  # Minimum 2 FPS
            max_fps=10.0,  # Maximum 10 FPS
        )
        self.enable_adaptive_sampling = enable_adaptive_sampling

        # Performance tracking
        self._processing_times = []
        self._preprocessing_times = []
        self._skipped_frames = 0

    async def process_frame(
        self,
        frame: np.ndarray,
        session_id: str,
        timestamp: Optional[float] = None,
    ) -> Dict:
        """
        Process a single frame through all detection streams with preprocessing.

        Processing Pipeline:
        1. Adaptive frame sampling (motion-based)
        2. Image preprocessing (CLAHE, bilateral filtering)
        3. ROI extraction (optional)
        4. Concurrent detection (gaze + objects)
        5. Behavior analysis
        6. Risk scoring

        Args:
            frame: Video frame (BGR format from OpenCV)
            session_id: Unique session identifier
            timestamp: Optional timestamp for the frame (uses current time if None)

        Returns:
            Dictionary containing:
                - gaze: Gaze detection results
                - objects: Object detection results
                - behavior: Behavior analysis results
                - risk: Risk scoring results
                - metadata: Processing metadata (timestamp, duration, preprocessing info)
        """
        start_time = time.time()
        timestamp = timestamp or start_time

        # Phase 1 Optimization: Adaptive Frame Sampling
        # Skip frames with low motion to reduce processing load
        if self.enable_adaptive_sampling:
            should_process, sampling_info = self.frame_sampler.should_process_frame(
                frame, timestamp
            )
            if not should_process:
                self._skipped_frames += 1
                # Return cached results or minimal processing
                return self._get_skipped_frame_results(
                    session_id, timestamp, sampling_info
                )
        else:
            sampling_info = {"enabled": False}

        try:
            preprocess_start = time.time()

            # Phase 1 Optimization: Image Preprocessing
            # Apply CLAHE and bilateral filtering for better detection
            if self.enable_preprocessing:
                processed_frame = self.preprocessor.preprocess(frame)
            else:
                processed_frame = frame

            # Phase 1 Optimization: ROI Extraction (optional)
            # Extract region of interest for focused processing
            roi_frame, roi_info = self.roi_extractor.extract_roi(processed_frame)

            preprocess_time = time.time() - preprocess_start
            self._preprocessing_times.append(preprocess_time)

            # Run all detectors concurrently for maximum performance
            # Use ROI frame for detection
            gaze_task = self.gaze_detector.detect(roi_frame)
            object_task = self.object_detector.detect(roi_frame)

            # Execute both tasks concurrently
            gaze_results, object_results = await asyncio.gather(
                gaze_task, object_task, return_exceptions=True
            )

            # Handle potential exceptions
            if isinstance(gaze_results, Exception):
                print(f"[WARNING] Gaze detection error: {gaze_results}")
                gaze_results = self._get_default_gaze_results()

            if isinstance(object_results, Exception):
                print(f"[WARNING] Object detection error: {object_results}")
                object_results = self._get_default_object_results()

            # Prepare detection results for behavior analyzer
            detection_results = {
                "gaze": gaze_results,
                "objects": object_results,
            }

            # Run behavior analysis (updates session history)
            behavior_results = await self.behavior_analyzer.analyze(
                frame, session_id, detection_results
            )

            # Add behavior results to detection results
            detection_results["behavior"] = behavior_results

            # Calculate risk score
            risk_results = self.risk_scorer.calculate_score(detection_results)

            # Calculate processing time
            processing_time = time.time() - start_time
            self._processing_times.append(processing_time)

            # Keep only last 100 processing times for performance stats
            if len(self._processing_times) > 100:
                self._processing_times.pop(0)

            # Construct final results with preprocessing info
            results = {
                "gaze": gaze_results,
                "objects": object_results,
                "behavior": behavior_results,
                "risk": risk_results,
                "metadata": {
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "processing_time_ms": processing_time * 1000,
                    "preprocessing_time_ms": preprocess_time * 1000,
                    "detection_time_ms": (processing_time - preprocess_time) * 1000,
                    "avg_processing_time_ms": self._get_avg_processing_time(),
                    "avg_preprocessing_time_ms": self._get_avg_preprocessing_time(),
                    "frame_within_timeout": processing_time < settings.FRAME_PROCESSING_TIMEOUT,
                    "preprocessing": {
                        "enabled": self.enable_preprocessing,
                        "config": self.preprocessor.get_config(),
                        "roi": roi_info,
                        "sampling": sampling_info,
                    },
                    "performance": {
                        "total_frames": self.frame_sampler.frame_count if self.enable_adaptive_sampling else 0,
                        "processed_frames": self.frame_sampler.processed_count if self.enable_adaptive_sampling else 0,
                        "skipped_frames": self._skipped_frames,
                    },
                },
            }

            return results

        except Exception as e:
            print(f"[ERROR] Pipeline processing error: {e}")
            # Return error results
            return self._get_error_results(session_id, timestamp, str(e))

    async def process_frame_batch(
        self,
        frames: list[np.ndarray],
        session_id: str,
    ) -> list[Dict]:
        """
        Process multiple frames concurrently for batch processing.

        Args:
            frames: List of video frames
            session_id: Unique session identifier

        Returns:
            List of results dictionaries (one per frame)
        """
        tasks = [
            self.process_frame(frame, session_id, time.time() + i * 0.05)
            for i, frame in enumerate(frames)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions in batch results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[WARNING] Batch frame {i} processing error: {result}")
                processed_results.append(
                    self._get_error_results(session_id, time.time(), str(result))
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_session_summary(self, session_id: str) -> Dict:
        """
        Get comprehensive session summary.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with session statistics and behavior patterns
        """
        behavior_stats = self.behavior_analyzer.get_session_stats(session_id)

        return {
            "session_id": session_id,
            "behavior_statistics": behavior_stats,
            "scoring_config": self.risk_scorer.get_scoring_config(),
            "performance": {
                "avg_processing_time_ms": self._get_avg_processing_time(),
                "total_frames_processed": len(self._processing_times),
            },
        }

    def clear_session(self, session_id: str) -> None:
        """
        Clear all data for a specific session.

        Args:
            session_id: Unique session identifier
        """
        self.behavior_analyzer.clear_session(session_id)
        print(f"[SUCCESS] Cleared session: {session_id}")

    def clear_all_sessions(self) -> None:
        """Clear all session data."""
        self.behavior_analyzer.clear_all_sessions()
        self._processing_times.clear()
        print("[SUCCESS] Cleared all sessions")

    def get_pipeline_info(self) -> Dict:
        """
        Get information about the pipeline configuration.

        Returns:
            Dictionary with pipeline details
        """
        return {
            "detectors": {
                "gaze": "MediaPipe Face Mesh + PnP",
                "objects": self.object_detector.get_model_info(),
                "behavior": {
                    "window_size": self.behavior_analyzer.window_size,
                    "active_sessions": len(self.behavior_analyzer.session_history),
                },
            },
            "risk_scorer": self.risk_scorer.get_scoring_config(),
            "performance": {
                "avg_processing_time_ms": self._get_avg_processing_time(),
                "target_fps": settings.TARGET_FPS,
                "timeout_ms": settings.FRAME_PROCESSING_TIMEOUT * 1000,
            },
        }

    def _get_avg_processing_time(self) -> float:
        """
        Calculate average processing time in milliseconds.

        Returns:
            Average processing time in ms
        """
        if not self._processing_times:
            return 0.0
        return (sum(self._processing_times) / len(self._processing_times)) * 1000

    def _get_avg_preprocessing_time(self) -> float:
        """
        Calculate average preprocessing time in milliseconds.

        Returns:
            Average preprocessing time in ms
        """
        if not self._preprocessing_times:
            return 0.0
        # Keep only last 100 times
        if len(self._preprocessing_times) > 100:
            self._preprocessing_times = self._preprocessing_times[-100:]
        return (sum(self._preprocessing_times) / len(self._preprocessing_times)) * 1000

    def _get_skipped_frame_results(
        self,
        session_id: str,
        timestamp: float,
        sampling_info: Dict
    ) -> Dict:
        """
        Generate results for skipped frames (adaptive sampling).

        When a frame is skipped due to low motion, we return minimal
        results to maintain the response structure without full processing.

        Args:
            session_id: Session identifier
            timestamp: Frame timestamp
            sampling_info: Sampling information from adaptive sampler

        Returns:
            Minimal results dictionary for skipped frame
        """
        return {
            "gaze": self._get_default_gaze_results(),
            "objects": self._get_default_object_results(),
            "behavior": {
                "repeated_deviations": 0,
                "repeated_objects": 0,
                "pattern_score": 0.0,
                "avg_person_count": 0.0,
                "analysis_summary": "Frame skipped (low motion)",
                "window_frames": 0,
            },
            "risk": {
                "risk_score": 0.0,
                "violation_count": 0,
                "violations": [],
                "alert_level": "none",
                "recommendations": [],
                "details": {},
            },
            "metadata": {
                "session_id": session_id,
                "timestamp": timestamp,
                "processing_time_ms": 0.0,
                "preprocessing_time_ms": 0.0,
                "detection_time_ms": 0.0,
                "avg_processing_time_ms": self._get_avg_processing_time(),
                "avg_preprocessing_time_ms": self._get_avg_preprocessing_time(),
                "frame_within_timeout": True,
                "frame_skipped": True,
                "preprocessing": {
                    "enabled": self.enable_preprocessing,
                    "sampling": sampling_info,
                },
                "performance": {
                    "total_frames": self.frame_sampler.frame_count,
                    "processed_frames": self.frame_sampler.processed_count,
                    "skipped_frames": self._skipped_frames,
                    "skip_ratio": sampling_info.get("skip_ratio", 0.0),
                },
            },
        }

    def _get_default_gaze_results(self) -> Dict:
        """
        Get default gaze results for error handling.

        Returns:
            Default gaze results dictionary
        """
        return {
            "face_detected": False,
            "deviation": False,
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "deviation_duration": 0.0,
            "landmarks_count": 0,
            "confidence": 0.0,
        }

    def _get_default_object_results(self) -> Dict:
        """
        Get default object results for error handling.

        Returns:
            Default object results dictionary
        """
        return {
            "person_count": 0,
            "forbidden_items": [],
            "all_detections": [],
            "confidence": 0.0,
        }

    def _get_error_results(
        self,
        session_id: str,
        timestamp: float,
        error_message: str,
    ) -> Dict:
        """
        Generate error results structure.

        Args:
            session_id: Session identifier
            timestamp: Timestamp when error occurred
            error_message: Error description

        Returns:
            Error results dictionary
        """
        return {
            "gaze": self._get_default_gaze_results(),
            "objects": self._get_default_object_results(),
            "behavior": {
                "repeated_deviations": 0,
                "repeated_objects": 0,
                "pattern_score": 0.0,
                "avg_person_count": 0.0,
                "analysis_summary": "Error in analysis",
                "window_frames": 0,
            },
            "risk": {
                "risk_score": 0.0,
                "violation_count": 0,
                "violations": [],
                "alert_level": "error",
                "recommendations": ["System error - review logs"],
                "details": {},
            },
            "metadata": {
                "session_id": session_id,
                "timestamp": timestamp,
                "processing_time_ms": 0.0,
                "avg_processing_time_ms": 0.0,
                "frame_within_timeout": False,
                "error": error_message,
            },
        }
