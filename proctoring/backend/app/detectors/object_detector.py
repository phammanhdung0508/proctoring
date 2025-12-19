"""
Object Detection Module - Stream 2

This module scans the workspace for prohibited items and unauthorized persons
using YOLOv8 object detection.

Technology: YOLOv8 (Ultralytics)
"""

import asyncio
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
from ultralytics import YOLO

from app.config import settings

# Fix for PyTorch 2.6+ weights_only security change
# Patch ultralytics module to use weights_only=False for model loading
# This is safe for official YOLOv8 models from Ultralytics
try:
    import ultralytics.nn.tasks

    # Store original torch.load
    _original_torch_load = torch.load

    def _patched_torch_load(f, *args, **kwargs):
        """Patched torch.load that uses weights_only=False for YOLOv8 models."""
        kwargs['weights_only'] = False
        return _original_torch_load(f, *args, **kwargs)

    # Patch in ultralytics.nn.tasks module namespace
    ultralytics.nn.tasks.torch.load = _patched_torch_load

    # Also patch globally for safety
    torch.load = _patched_torch_load

    print("[INFO] Successfully patched torch.load for YOLOv8 compatibility")
except Exception as e:
    print(f"[WARNING] Could not patch torch.load: {e}")


class ObjectDetector:
    """
    Detects forbidden objects and persons using YOLOv8.

    Detects:
        - Forbidden objects: cell phones, books, smart watches
        - Secondary persons: unauthorized individuals in frame

    Attributes:
        model: YOLOv8 model instance
        forbidden_classes: Dict mapping class names to object types
        person_class_id: COCO dataset class ID for 'person'
    """

    def __init__(self, model_path: str = None):
        """
        Initialize YOLOv8 model.

        Args:
            model_path: Path to YOLOv8 weights file.
                       If None, uses path from settings.
        """
        # Use provided path or default from settings
        if model_path is None:
            model_path = settings.YOLO_MODEL_PATH

        # Store original requested path for logging
        requested_path = model_path

        # Check if model file exists, download if not
        model_file = Path(model_path)
        if not model_file.exists():
            print(f"[WARNING] Model file not found: {model_path}")
            print(f"[INFO] Falling back to YOLOv8-nano (yolov8n.pt)...")
            # This will auto-download from Ultralytics
            model_path = "yolov8n.pt"

        # Load YOLOv8 model
        print(f"[YOLO-INIT] Loading model: {model_path}")
        self.model = YOLO(model_path)

        # Log which model was actually loaded
        actual_model = Path(model_path).name
        if requested_path != model_path:
            print(f"[YOLO-INIT] Using fallback model: {actual_model} (requested: {Path(requested_path).name})")
        else:
            print(f"[YOLO-INIT] Successfully loaded: {actual_model}")

        # Store model path for later reference
        self.model_path = model_path

        # COCO dataset class mappings for forbidden items
        # Reference: https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml
        self.forbidden_classes = {
            "cell phone": "phone",
            "phone": "phone",
            "book": "book",
            "laptop": "laptop",  # Optional: some exams allow laptops
            # Add more forbidden items as needed
        }

        # COCO class ID for person detection
        self.person_class_id = 0

    async def detect(self, frame: np.ndarray) -> Dict:
        """
        Detect objects and persons in the frame.

        This method runs in an async context to allow concurrent processing
        but performs synchronous inference internally.

        Args:
            frame: Input video frame (BGR format from OpenCV)

        Returns:
            Dictionary containing:
                - person_count (int): Number of persons detected
                - forbidden_items (List[Dict]): List of forbidden objects detected
                - all_detections (List[Dict]): All detections for debugging
                - confidence (float): Average confidence score
        """
        # Run detection in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._detect_sync, frame)
        return result

    def _detect_sync(self, frame: np.ndarray) -> Dict:
        """
        Synchronous detection method (runs in thread pool).

        Args:
            frame: Input video frame (BGR format)

        Returns:
            Detection results dictionary
        """
        # Run YOLOv8 inference with very low confidence to see everything
        results = self.model(
            frame,
            imgsz=640,  # Input size
            conf=0.01,  # Very low to see all detections
            verbose=False,  # Suppress output
        )

        # Log ALL raw detections first
        raw_detections = []
        for result in results:
            boxes = result.boxes.data.cpu().numpy()
            for box in boxes:
                x1, y1, x2, y2, confidence, class_id = box
                class_name = result.names[int(class_id)]
                raw_detections.append((class_name, float(confidence)))

        if raw_detections:
            print(f"[RAW-YOLO] Found {len(raw_detections)} total detections:")
            for name, conf in sorted(raw_detections, key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {name}: {conf:.3f}")

        # Parse detections
        person_count = 0
        forbidden_items = []
        all_detections = []
        total_confidence = 0.0
        detection_count = 0

        # Process all detections (filter by confidence threshold)
        for result in results:
            boxes = result.boxes.data.cpu().numpy()

            for box in boxes:
                # Parse box data: [x1, y1, x2, y2, confidence, class_id]
                x1, y1, x2, y2, confidence, class_id = box
                class_id = int(class_id)
                class_name = result.names[class_id]

                # Skip if below confidence threshold
                if confidence < settings.YOLO_CONFIDENCE:
                    continue

                # Track confidence
                total_confidence += confidence
                detection_count += 1

                # Count persons
                if class_id == self.person_class_id and confidence > settings.PERSON_CONFIDENCE:
                    person_count += 1

                # Check for forbidden items
                if class_name in self.forbidden_classes:
                    forbidden_items.append(
                        {
                            "object": self.forbidden_classes[class_name],
                            "confidence": float(confidence),
                            "bbox": [int(x1), int(y1), int(x2), int(y2)],
                            "class_name": class_name,
                        }
                    )

                # Store all detections
                all_detections.append(
                    {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": float(confidence),
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    }
                )

        # Calculate average confidence
        avg_confidence = total_confidence / detection_count if detection_count > 0 else 0.0

        # Debug logging to see what YOLO detects
        print(f"[YOLO-DEBUG] Detected {len(all_detections)} objects (threshold: {settings.YOLO_CONFIDENCE}):")
        for det in all_detections:  # Show all detections
            forbidden_marker = " [FORBIDDEN]" if det['class_name'] in self.forbidden_classes else ""
            print(f"  - {det['class_name']} (conf: {det['confidence']:.2f}){forbidden_marker}")

        return {
            "person_count": person_count,
            "forbidden_items": forbidden_items,
            "all_detections": all_detections,
            "confidence": float(avg_confidence),
        }

    def set_confidence_threshold(self, threshold: float) -> None:
        """
        Update the confidence threshold for detections.

        Args:
            threshold: New confidence threshold (0.0 to 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            settings.YOLO_CONFIDENCE = threshold
        else:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")

    def add_forbidden_class(self, class_name: str, label: str) -> None:
        """
        Add a new forbidden object class.

        Args:
            class_name: YOLO/COCO class name (e.g., "laptop")
            label: Display label for the object (e.g., "laptop")
        """
        self.forbidden_classes[class_name] = label

    def remove_forbidden_class(self, class_name: str) -> None:
        """
        Remove a forbidden object class.

        Args:
            class_name: YOLO/COCO class name to remove
        """
        if class_name in self.forbidden_classes:
            del self.forbidden_classes[class_name]

    def get_model_info(self) -> Dict:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        return {
            "model_type": "YOLOv8",
            "model_path_configured": settings.YOLO_MODEL_PATH,
            "model_path_actual": self.model_path,
            "model_name": Path(self.model_path).name,
            "confidence_threshold": settings.YOLO_CONFIDENCE,
            "person_confidence": settings.PERSON_CONFIDENCE,
            "forbidden_classes": list(self.forbidden_classes.keys()),
        }
