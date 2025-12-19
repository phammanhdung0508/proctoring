"""
Image Preprocessing Module

Implements advanced image processing techniques for optimal detection:
1. CLAHE (Contrast Limited Adaptive Histogram Equalization) - Better detection in varying lighting
2. ROI (Region of Interest) Extraction - Focus on face region for faster processing
3. Adaptive Frame Sampling - Process frames based on motion detection

Technology: OpenCV image processing algorithms
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple
from app.config import settings


class ImagePreprocessor:
    """
    Preprocesses video frames using advanced image processing techniques
    to optimize detection performance and accuracy.

    Implements:
        - CLAHE for lighting normalization
        - Bilateral filtering for noise reduction
        - Gamma correction for exposure adjustment
        - ROI extraction for focused processing

    Attributes:
        clahe: CLAHE object for adaptive histogram equalization
        enable_clahe: Flag to enable/disable CLAHE preprocessing
        enable_bilateral: Flag to enable/disable bilateral filtering
        enable_gamma: Flag to enable/disable gamma correction
        gamma_value: Gamma correction value (default: 1.2)
    """

    def __init__(
        self,
        enable_clahe: bool = True,
        enable_bilateral: bool = True,
        enable_gamma: bool = False,
        gamma_value: float = 1.2,
        clahe_clip_limit: float = 2.0,
        clahe_tile_size: Tuple[int, int] = (8, 8),
    ):
        """
        Initialize the image preprocessor.

        Args:
            enable_clahe: Enable CLAHE preprocessing
            enable_bilateral: Enable bilateral filtering for noise reduction
            enable_gamma: Enable gamma correction
            gamma_value: Gamma value for correction (>1 brightens, <1 darkens)
            clahe_clip_limit: CLAHE clipping limit (higher = more contrast)
            clahe_tile_size: Grid size for CLAHE (smaller = more local adaptation)
        """
        self.enable_clahe = enable_clahe
        self.enable_bilateral = enable_bilateral
        self.enable_gamma = enable_gamma
        self.gamma_value = gamma_value

        # Initialize CLAHE
        # CLAHE improves detection in varying lighting conditions by:
        # - Normalizing brightness across the frame
        # - Enhancing local contrast in dark/bright regions
        # - Reducing the impact of shadows and highlights
        self.clahe = cv2.createCLAHE(
            clipLimit=clahe_clip_limit,
            tileGridSize=clahe_tile_size
        )

        # Build gamma correction lookup table
        if self.enable_gamma:
            self.gamma_lut = self._build_gamma_lut(gamma_value)
        else:
            self.gamma_lut = None

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply all enabled preprocessing techniques to the frame.

        Processing pipeline:
        1. Gamma correction (optional) - Adjust overall exposure
        2. Bilateral filtering (optional) - Reduce noise while preserving edges
        3. CLAHE - Normalize lighting and enhance contrast

        Args:
            frame: Input frame in BGR format

        Returns:
            Preprocessed frame in BGR format
        """
        preprocessed = frame.copy()

        # Step 1: Gamma correction (adjusts overall brightness/exposure)
        if self.enable_gamma and self.gamma_lut is not None:
            preprocessed = self._apply_gamma_correction(preprocessed)

        # Step 2: Bilateral filtering (reduces noise while preserving edges)
        # This is particularly useful for webcam feeds with sensor noise
        if self.enable_bilateral:
            preprocessed = cv2.bilateralFilter(
                preprocessed,
                d=5,  # Diameter of pixel neighborhood
                sigmaColor=50,  # Filter sigma in color space
                sigmaSpace=50   # Filter sigma in coordinate space
            )

        # Step 3: CLAHE (enhances local contrast in LAB color space)
        # LAB color space separates luminance (L) from color (A, B)
        # This allows contrast enhancement without color distortion
        if self.enable_clahe:
            preprocessed = self._apply_clahe(preprocessed)

        return preprocessed

    def _apply_clahe(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

        CLAHE enhances contrast locally rather than globally:
        - Divides image into small tiles (e.g., 8x8)
        - Applies histogram equalization to each tile
        - Limits contrast amplification to avoid noise amplification
        - Interpolates between tiles for smooth results

        Benefits for detection:
        - Better face detection in poor lighting
        - Improved landmark detection in shadows
        - More consistent performance across lighting conditions

        Args:
            frame: Input frame in BGR format

        Returns:
            Frame with enhanced contrast in BGR format
        """
        # Convert to LAB color space
        # L channel: Lightness (0-100)
        # A channel: Green to Red (-128 to 127)
        # B channel: Blue to Yellow (-128 to 127)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

        # Split channels
        l, a, b = cv2.split(lab)

        # Apply CLAHE only to L channel (lightness)
        # This preserves color information while enhancing contrast
        l = self.clahe.apply(l)

        # Merge channels back
        enhanced_lab = cv2.merge([l, a, b])

        # Convert back to BGR
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        return enhanced_bgr

    def _apply_gamma_correction(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply gamma correction to adjust image brightness.

        Gamma correction applies a power-law transformation:
        Output = Input ^ (1/gamma)

        - gamma > 1: Brightens the image (useful for underexposed frames)
        - gamma < 1: Darkens the image (useful for overexposed frames)
        - gamma = 1: No change

        Args:
            frame: Input frame in BGR format

        Returns:
            Gamma-corrected frame in BGR format
        """
        return cv2.LUT(frame, self.gamma_lut)

    def _build_gamma_lut(self, gamma: float) -> np.ndarray:
        """
        Build lookup table for gamma correction.

        Pre-computing the lookup table allows O(1) gamma correction
        instead of O(pixels) power operations.

        Args:
            gamma: Gamma value for correction

        Returns:
            256-element lookup table for gamma correction
        """
        inv_gamma = 1.0 / gamma
        lut = np.array([
            ((i / 255.0) ** inv_gamma) * 255
            for i in range(256)
        ]).astype(np.uint8)
        return lut

    def update_gamma(self, gamma: float) -> None:
        """
        Update gamma correction value and rebuild lookup table.

        Args:
            gamma: New gamma value
        """
        self.gamma_value = gamma
        self.gamma_lut = self._build_gamma_lut(gamma)

    def get_config(self) -> Dict:
        """
        Get current preprocessing configuration.

        Returns:
            Dictionary with current settings
        """
        return {
            "clahe_enabled": self.enable_clahe,
            "bilateral_enabled": self.enable_bilateral,
            "gamma_enabled": self.enable_gamma,
            "gamma_value": self.gamma_value,
            "techniques": [
                "CLAHE" if self.enable_clahe else None,
                "Bilateral Filter" if self.enable_bilateral else None,
                "Gamma Correction" if self.enable_gamma else None,
            ],
        }


class ROIExtractor:
    """
    Extracts Region of Interest (ROI) from frames for focused processing.

    ROI extraction improves performance by:
    - Reducing the area that needs to be processed
    - Focusing computational resources on relevant regions
    - Enabling higher resolution processing of key areas

    For proctoring, the ROI is typically the upper portion of the frame
    where the face and upper body are located.

    Attributes:
        roi_ratio: Ratio of frame height to extract from top (0.0 to 1.0)
        enable_roi: Flag to enable/disable ROI extraction
    """

    def __init__(
        self,
        roi_ratio: float = 0.7,
        enable_roi: bool = True,
    ):
        """
        Initialize ROI extractor.

        Args:
            roi_ratio: Ratio of frame height to extract from top (0.0-1.0)
                      0.7 means extract top 70% of frame
            enable_roi: Enable/disable ROI extraction
        """
        self.roi_ratio = roi_ratio
        self.enable_roi = enable_roi

    def extract_roi(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Extract region of interest from frame.

        ROI extraction focuses on the upper portion of the frame where
        the face typically appears in proctoring scenarios.

        Benefits:
        - Faster processing (smaller frame size)
        - Better detection accuracy (less background clutter)
        - Lower memory usage
        - Higher effective resolution for face region

        Args:
            frame: Input frame in BGR format

        Returns:
            Tuple of (roi_frame, roi_info)
            - roi_frame: Extracted ROI or original frame if disabled
            - roi_info: Dictionary with ROI coordinates and metadata
        """
        if not self.enable_roi:
            h, w = frame.shape[:2]
            return frame, {
                "enabled": False,
                "original_size": (w, h),
                "roi_size": (w, h),
                "offset": (0, 0),
            }

        h, w = frame.shape[:2]

        # Calculate ROI coordinates
        # Extract top portion of frame (where face is typically located)
        roi_height = int(h * self.roi_ratio)
        y_start = 0
        y_end = roi_height
        x_start = 0
        x_end = w

        # Extract ROI
        roi_frame = frame[y_start:y_end, x_start:x_end]

        # Return ROI and metadata
        roi_info = {
            "enabled": True,
            "original_size": (w, h),
            "roi_size": (x_end - x_start, y_end - y_start),
            "offset": (x_start, y_start),
            "coordinates": (x_start, y_start, x_end, y_end),
            "reduction_ratio": roi_height / h,
        }

        return roi_frame, roi_info

    def map_coordinates_to_original(
        self,
        x: int,
        y: int,
        roi_info: Dict
    ) -> Tuple[int, int]:
        """
        Map coordinates from ROI back to original frame.

        When detections are made on ROI, their coordinates need to be
        mapped back to the original frame coordinate system.

        Args:
            x: X coordinate in ROI
            y: Y coordinate in ROI
            roi_info: ROI metadata from extract_roi()

        Returns:
            Tuple of (x_original, y_original) in original frame coordinates
        """
        if not roi_info.get("enabled", False):
            return x, y

        offset_x, offset_y = roi_info["offset"]
        return x + offset_x, y + offset_y


class AdaptiveFrameSampler:
    """
    Implements adaptive frame sampling based on motion detection.

    Adaptive sampling optimizes processing by:
    - Skipping frames when little motion is detected
    - Processing more frames during high activity
    - Reducing average processing load without missing events

    Uses frame differencing to detect motion:
    - Compares current frame with previous frame
    - Calculates amount of change
    - Adjusts sampling rate dynamically

    Attributes:
        prev_frame: Previous frame for motion comparison
        frame_count: Total frames received
        processed_count: Frames actually processed
        motion_threshold: Threshold for motion detection
        min_fps: Minimum processing rate
        max_fps: Maximum processing rate
    """

    def __init__(
        self,
        motion_threshold: float = 10.0,
        min_fps: float = 2.0,
        max_fps: float = 10.0,
    ):
        """
        Initialize adaptive frame sampler.

        Args:
            motion_threshold: Threshold for motion detection (0-255)
                            Higher values require more motion to process frame
            min_fps: Minimum processing rate (frames per second)
            max_fps: Maximum processing rate (frames per second)
        """
        self.motion_threshold = motion_threshold
        self.min_fps = min_fps
        self.max_fps = max_fps

        self.prev_frame = None
        self.prev_gray = None
        self.frame_count = 0
        self.processed_count = 0
        self.last_process_time = 0.0

    def should_process_frame(
        self,
        frame: np.ndarray,
        current_time: float
    ) -> Tuple[bool, Dict]:
        """
        Determine if frame should be processed based on motion detection.

        Motion detection algorithm:
        1. Convert frame to grayscale
        2. Calculate absolute difference with previous frame
        3. Compute mean absolute difference (motion score)
        4. Compare with threshold
        5. Adjust sampling rate based on motion level

        Benefits:
        - Reduces processing during static periods
        - Maintains responsiveness during activity
        - Balances performance and detection accuracy
        - Adapts to different scenarios automatically

        Args:
            frame: Input frame in BGR format
            current_time: Current timestamp in seconds

        Returns:
            Tuple of (should_process, motion_info)
            - should_process: Boolean indicating if frame should be processed
            - motion_info: Dictionary with motion detection metadata
        """
        self.frame_count += 1

        # Convert to grayscale for motion detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise impact
        gray_blur = cv2.GaussianBlur(gray, (21, 21), 0)

        # First frame - always process
        if self.prev_gray is None:
            self.prev_frame = frame.copy()
            self.prev_gray = gray_blur
            self.last_process_time = current_time
            self.processed_count += 1
            return True, {
                "motion_score": 0.0,
                "motion_detected": True,
                "reason": "first_frame",
                "frame_number": self.frame_count,
                "processed_count": self.processed_count,
            }

        # Calculate frame difference (motion detection)
        frame_diff = cv2.absdiff(self.prev_gray, gray_blur)

        # Calculate mean difference (motion score)
        # Higher score = more motion
        motion_score = float(np.mean(frame_diff))

        # Determine if motion exceeds threshold
        motion_detected = motion_score > self.motion_threshold

        # Calculate time since last processed frame
        time_since_last = current_time - self.last_process_time

        # Adaptive sampling logic:
        # 1. Always process if motion detected
        # 2. Process at min_fps even without motion (prevent missing slow changes)
        # 3. Never exceed max_fps
        min_interval = 1.0 / self.max_fps
        max_interval = 1.0 / self.min_fps

        should_process = False
        reason = ""

        if motion_detected:
            # Motion detected - process if we haven't exceeded max_fps
            if time_since_last >= min_interval:
                should_process = True
                reason = "motion_detected"
        else:
            # No motion - process at min_fps to catch slow changes
            if time_since_last >= max_interval:
                should_process = True
                reason = "min_fps_interval"

        # Update state if processing
        if should_process:
            self.prev_frame = frame.copy()
            self.prev_gray = gray_blur
            self.last_process_time = current_time
            self.processed_count += 1

        # Return decision and metadata
        motion_info = {
            "motion_score": motion_score,
            "motion_detected": motion_detected,
            "motion_threshold": self.motion_threshold,
            "should_process": should_process,
            "reason": reason,
            "frame_number": self.frame_count,
            "processed_count": self.processed_count,
            "skip_ratio": 1.0 - (self.processed_count / self.frame_count),
            "time_since_last": time_since_last,
        }

        return should_process, motion_info

    def reset(self) -> None:
        """Reset sampler state (for new session)."""
        self.prev_frame = None
        self.prev_gray = None
        self.frame_count = 0
        self.processed_count = 0
        self.last_process_time = 0.0

    def get_statistics(self) -> Dict:
        """
        Get sampling statistics.

        Returns:
            Dictionary with sampling metrics
        """
        return {
            "total_frames": self.frame_count,
            "processed_frames": self.processed_count,
            "skipped_frames": self.frame_count - self.processed_count,
            "skip_ratio": 1.0 - (self.processed_count / self.frame_count) if self.frame_count > 0 else 0.0,
            "effective_fps_reduction": f"{(1.0 - (self.processed_count / self.frame_count) if self.frame_count > 0 else 0.0) * 100:.1f}%",
        }
