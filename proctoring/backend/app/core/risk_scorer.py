"""
Risk Scoring Module

This module calculates risk scores based on detection results from all
three streams (gaze, objects, behavior) using weighted scoring algorithms.

Technology: Weighted scoring with configurable thresholds
"""

from typing import Dict, List

from app.config import settings


class RiskScorer:
    """
    Calculates risk scores based on detection results.

    Applies weighted scoring to different violation types:
        - Secondary person: 10 points
        - Forbidden object: 8 points
        - Gaze deviation: 4 points
        - Multiple concurrent violations: ×1.5 multiplier

    Score range: 0-100 (capped)

    Attributes:
        secondary_person_weight: Weight for extra person detection
        forbidden_object_weight: Weight for forbidden object detection
        gaze_deviation_weight: Weight for gaze deviation
        multiple_violations_multiplier: Multiplier for concurrent violations
    """

    def __init__(
        self,
        secondary_person_weight: int = None,
        forbidden_object_weight: int = None,
        screen_deviation_base_weight: int = None,
        screen_deviation_extended_weight: int = None,
        screen_deviation_critical_weight: int = None,
        multiple_violations_multiplier: float = None,
    ):
        """
        Initialize the Risk Scorer.

        Args:
            secondary_person_weight: Weight for extra person detection (HIGH alert)
            forbidden_object_weight: Weight for forbidden object detection (HIGH alert)
            screen_deviation_base_weight: Weight for 3-10s screen deviation (HIGH alert)
            screen_deviation_extended_weight: Weight for 10-20s screen deviation (HIGH alert)
            screen_deviation_critical_weight: Weight for 20+s screen deviation (CRITICAL alert)
            multiple_violations_multiplier: Multiplier for concurrent violations

        If any parameter is None, uses value from settings.
        """
        self.secondary_person_weight = (
            secondary_person_weight or settings.SECONDARY_PERSON_WEIGHT
        )
        self.forbidden_object_weight = (
            forbidden_object_weight or settings.FORBIDDEN_OBJECT_WEIGHT
        )
        self.screen_deviation_base_weight = (
            screen_deviation_base_weight or settings.SCREEN_DEVIATION_BASE_WEIGHT
        )
        self.screen_deviation_extended_weight = (
            screen_deviation_extended_weight or settings.SCREEN_DEVIATION_EXTENDED_WEIGHT
        )
        self.screen_deviation_critical_weight = (
            screen_deviation_critical_weight or settings.SCREEN_DEVIATION_CRITICAL_WEIGHT
        )
        self.multiple_violations_multiplier = (
            multiple_violations_multiplier or settings.MULTIPLE_VIOLATIONS_MULTIPLIER
        )

    def calculate_score(self, detection_results: Dict) -> Dict:
        """
        Calculate risk score from detection results.

        Args:
            detection_results: Dictionary containing results from all detectors:
                {
                    "gaze": {...},           # Results from GazeDetector
                    "objects": {...},        # Results from ObjectDetector
                    "behavior": {...}        # Results from BehaviorAnalyzer
                }

        Returns:
            Dictionary containing:
                - risk_score (float): Final risk score (0-100)
                - violation_count (int): Number of concurrent violations
                - violations (List[str]): List of detected violations
                - alert_level (str): Alert severity level
                - recommendations (List[str]): Recommended actions
                - details (Dict): Detailed scoring breakdown
        """
        # Extract detection results
        gaze_results = detection_results.get("gaze", {})
        object_results = detection_results.get("objects", {})
        behavior_results = detection_results.get("behavior", {})

        # Initialize scoring variables
        base_score = 0.0
        violations = []
        violation_count = 0

        # Score gaze deviation (time-based weighting for screen deviation)
        if gaze_results.get("deviation", False):
            deviation_duration = gaze_results.get("deviation_duration", 0.0)

            # Only alert if duration exceeds minimum threshold
            if deviation_duration >= settings.GAZE_DEVIATION_DURATION:
                # Apply time-based weighting
                if deviation_duration >= settings.GAZE_CRITICAL_DURATION:  # 20+ seconds
                    screen_weight = self.screen_deviation_critical_weight
                    duration_label = f"for {deviation_duration:.1f}s (CRITICAL)"
                elif deviation_duration >= settings.GAZE_EXTENDED_DURATION:  # 10-20 seconds
                    screen_weight = self.screen_deviation_extended_weight
                    duration_label = f"for {deviation_duration:.1f}s (extended)"
                else:  # 3-10 seconds (base threshold)
                    screen_weight = self.screen_deviation_base_weight
                    duration_label = f"for {deviation_duration:.1f}s"

                base_score += screen_weight
                violations.append(f"Looking at another screen {duration_label}")
                violation_count += 1

        # Score forbidden objects
        forbidden_items = object_results.get("forbidden_items", [])
        if forbidden_items:
            # Weight based on number and confidence of forbidden items
            for item in forbidden_items:
                base_score += self.forbidden_object_weight * item.get("confidence", 1.0)
                violations.append(f"Forbidden object detected: {item.get('object', 'unknown')}")
            violation_count += 1

        # Score secondary persons
        person_count = object_results.get("person_count", 0)
        if person_count > 1:
            # Each additional person adds weight
            extra_persons = person_count - 1
            base_score += self.secondary_person_weight * extra_persons
            violations.append(f"Multiple persons detected: {person_count}")
            violation_count += 1

        # Apply multiplier if multiple concurrent violations
        if violation_count > 1:
            base_score *= self.multiple_violations_multiplier

        # Add behavior pattern score
        pattern_score = behavior_results.get("pattern_score", 0.0)
        base_score += pattern_score

        # Cap score at 100
        final_score = min(base_score, 100.0)

        # Determine alert level
        alert_level = self._determine_alert_level(final_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            final_score, violations, behavior_results
        )

        # Calculate screen deviation contribution with time-based weight
        screen_contribution = 0
        if gaze_results.get("deviation", False):
            deviation_duration = gaze_results.get("deviation_duration", 0.0)
            # Only count contribution if duration exceeds minimum threshold
            if deviation_duration >= settings.GAZE_DEVIATION_DURATION:
                if deviation_duration >= settings.GAZE_CRITICAL_DURATION:
                    screen_contribution = self.screen_deviation_critical_weight
                elif deviation_duration >= settings.GAZE_EXTENDED_DURATION:
                    screen_contribution = self.screen_deviation_extended_weight
                else:
                    screen_contribution = self.screen_deviation_base_weight

        # Create detailed breakdown
        details = {
            "base_score": float(base_score),
            "screen_deviation_contribution": screen_contribution,
            "screen_deviation_duration": gaze_results.get("deviation_duration", 0.0),
            "object_contribution": sum(
                self.forbidden_object_weight * item.get("confidence", 1.0)
                for item in forbidden_items
            ),
            "person_contribution": (
                self.secondary_person_weight * max(0, person_count - 1)
            ),
            "behavior_contribution": pattern_score,
            "multiplier_applied": violation_count > 1,
            "person_count": person_count,
            "forbidden_items_count": len(forbidden_items),
        }

        return {
            "risk_score": float(final_score),
            "violation_count": violation_count,
            "violations": violations,
            "alert_level": alert_level,
            "recommendations": recommendations,
            "details": details,
        }

    def _determine_alert_level(self, score: float) -> str:
        """
        Determine alert severity level based on score.

        Args:
            score: Risk score (0-100)

        Returns:
            Alert level: "low", "medium", "high", or "critical"
        """
        if score >= 80:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 20:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        score: float,
        violations: List[str],
        behavior_results: Dict,
    ) -> List[str]:
        """
        Generate recommended actions based on risk score and violations.

        Args:
            score: Risk score
            violations: List of detected violations
            behavior_results: Behavior analysis results

        Returns:
            List of recommended actions
        """
        recommendations = []

        if score >= 80:
            recommendations.append("Immediate intervention required")
            recommendations.append("Flag session for manual review")
            recommendations.append("Consider terminating session")
        elif score >= 50:
            recommendations.append("Issue warning to candidate")
            recommendations.append("Increase monitoring intensity")
            recommendations.append("Log incident for review")
        elif score >= 20:
            recommendations.append("Monitor situation closely")
            recommendations.append("Log for pattern analysis")
        else:
            recommendations.append("Continue normal monitoring")

        # Add specific recommendations based on violations
        if any("Multiple persons" in v for v in violations):
            recommendations.append("Verify candidate identity")
            recommendations.append("Request room scan")

        if any("Forbidden object" in v for v in violations):
            recommendations.append("Request removal of prohibited items")
            recommendations.append("Verify workspace compliance")

        # Add behavioral pattern recommendations
        analysis_summary = behavior_results.get("analysis_summary", "")
        if "Frequent gaze deviations" in analysis_summary:
            recommendations.append("Investigate frequent attention shifts")

        if "Repeated forbidden object" in analysis_summary:
            recommendations.append("Persistent object violation - escalate")

        return recommendations

    def update_weights(
        self,
        secondary_person_weight: int = None,
        forbidden_object_weight: int = None,
        gaze_deviation_weight: int = None,
        multiple_violations_multiplier: float = None,
    ) -> None:
        """
        Update scoring weights dynamically.

        Args:
            secondary_person_weight: New weight for extra person detection
            forbidden_object_weight: New weight for forbidden object detection
            gaze_deviation_weight: New weight for gaze deviation
            multiple_violations_multiplier: New multiplier for concurrent violations
        """
        if secondary_person_weight is not None:
            self.secondary_person_weight = secondary_person_weight

        if forbidden_object_weight is not None:
            self.forbidden_object_weight = forbidden_object_weight

        if gaze_deviation_weight is not None:
            self.gaze_deviation_weight = gaze_deviation_weight

        if multiple_violations_multiplier is not None:
            self.multiple_violations_multiplier = multiple_violations_multiplier

    def get_scoring_config(self) -> Dict:
        """
        Get current scoring configuration.

        Returns:
            Dictionary with current weights and multipliers
        """
        return {
            "secondary_person_weight": self.secondary_person_weight,
            "forbidden_object_weight": self.forbidden_object_weight,
            "gaze_deviation_weight": self.gaze_deviation_weight,
            "multiple_violations_multiplier": self.multiple_violations_multiplier,
        }
