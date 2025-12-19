"""
Configuration management for the AI Proctoring System.

All configuration parameters are centralized here for easy management.
"""

import os
from typing import Optional


class Settings:
    """Application settings and configuration."""

    # Application
    APP_NAME: str = "AI Proctoring System"
    VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend
    ]

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./proctoring.db"
    )

    # Detection Thresholds
    # Gaze detection - Two-tier system
    # Minor deviation (no alert): slight looking away from camera
    MINOR_YAW_THRESHOLD: float = 30.0  # degrees
    MINOR_PITCH_THRESHOLD: float = 25.0  # degrees

    # Screen deviation (HIGH alert): looking at another screen/monitor
    SCREEN_YAW_THRESHOLD: float = 45.0  # degrees (looking at side monitor)
    SCREEN_PITCH_THRESHOLD: float = 35.0  # degrees (looking down at phone/notes)

    # Time-based thresholds for screen deviation
    GAZE_DEVIATION_DURATION: float = 3.0   # seconds before HIGH alert (base)
    GAZE_EXTENDED_DURATION: float = 10.0   # seconds for extended violation (higher weight)
    GAZE_CRITICAL_DURATION: float = 20.0   # seconds for critical violation (highest weight)

    # Object detection
    YOLO_MODEL_PATH: str = "models/yolov8m.pt"  # Medium model for better detection
    YOLO_CONFIDENCE: float = 0.25  # Higher confidence for yolov8m
    PERSON_CONFIDENCE: float = 0.5

    # Behavior analysis
    WINDOW_SIZE: int = 200  # frames for sliding window
    TARGET_FPS: int = 20

    # Risk scoring weights (HIGH-only system: 50+ for HIGH, 80+ for CRITICAL)
    SECONDARY_PERSON_WEIGHT: int = 60  # HIGH alert for multiple faces
    FORBIDDEN_OBJECT_WEIGHT: int = 70  # HIGH alert for phone/forbidden items

    # Screen deviation weights (time-based)
    SCREEN_DEVIATION_BASE_WEIGHT: int = 50      # 3-10s: HIGH alert (base)
    SCREEN_DEVIATION_EXTENDED_WEIGHT: int = 70  # 10-20s: HIGH alert (extended)
    SCREEN_DEVIATION_CRITICAL_WEIGHT: int = 90  # 20+s: CRITICAL alert (very serious)

    MINOR_DEVIATION_WEIGHT: int = 0   # No alert for minor gaze deviations
    MULTIPLE_VIOLATIONS_MULTIPLIER: float = 1.3  # Reduced multiplier for CRITICAL threshold

    # File paths
    MODELS_DIR: str = "models"
    DATA_DIR: str = "data"
    SESSIONS_DIR: str = "data/sessions"
    INCIDENTS_DIR: str = "data/incidents"

    # Performance
    MAX_CONCURRENT_SESSIONS: int = 10
    FRAME_PROCESSING_TIMEOUT: float = 5.0  # seconds


# Global settings instance
settings = Settings()
