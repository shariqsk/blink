"""Eye analysis using Eye Aspect Ratio (EAR)."""

import math
from dataclasses import dataclass
from typing import Optional

from loguru import logger


@dataclass
class EyeMetrics:
    """Eye analysis metrics."""

    left_ear: float
    right_ear: float
    avg_ear: float
    left_open: bool
    right_open: bool
    both_open: bool


class EyeAnalyzer:
    """Analyzes eye openness using Eye Aspect Ratio."""

    def __init__(
        self,
        ear_threshold: float = 0.21,
        consecutive_frames: int = 2,
        smooth_window: int = 5,
        adaptive_baseline: bool = True,
        baseline_alpha: float = 0.12,
    ):
        """Initialize eye analyzer.

        Args:
            ear_threshold: EAR threshold below which eye is considered closed.
            consecutive_frames: Number of consecutive frames below threshold to confirm closure.
            smooth_window: Rolling window size for median smoothing to fight jitter/reflections.
            adaptive_baseline: If True, continually learn an open-eye baseline to auto-adjust threshold.
            baseline_alpha: EMA factor for baseline updates (0-1). Lower = slower adaptation.
        """
        self.ear_threshold = ear_threshold
        self.consecutive_frames = consecutive_frames
        self._left_close_counter = 0
        self._right_close_counter = 0
        self.smooth_window = max(1, smooth_window)
        self._left_history: list[float] = []
        self._right_history: list[float] = []
        self.adaptive_baseline = adaptive_baseline
        self._baseline_ear: float | None = None
        self.baseline_alpha = max(0.01, min(1.0, baseline_alpha))

    def compute_ear(self, eye_landmarks: list[tuple[float, float]]) -> float:
        """Compute Eye Aspect Ratio from 6 eye landmarks.

        EAR formula: (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        where p1-p6 are the 6 eye landmarks in order.

        Args:
            eye_landmarks: List of 6 (x, y) normalized coordinates.

        Returns:
            Eye Aspect Ratio value.
        """
        if len(eye_landmarks) != 6:
            logger.warning(f"Expected 6 eye landmarks, got {len(eye_landmarks)}")
            return 0.0

        # Extract points
        p1, p2, p3, p4, p5, p6 = eye_landmarks

        # Compute vertical distances
        vertical_dist_1 = math.sqrt(
            (p2[0] - p6[0]) ** 2 + (p2[1] - p6[1]) ** 2
        )
        vertical_dist_2 = math.sqrt(
            (p3[0] - p5[0]) ** 2 + (p3[1] - p5[1]) ** 2
        )

        # Compute horizontal distance
        horizontal_dist = math.sqrt(
            (p1[0] - p4[0]) ** 2 + (p1[1] - p4[1]) ** 2
        )

        # Compute EAR
        if horizontal_dist == 0:
            return 0.0

        ear = (vertical_dist_1 + vertical_dist_2) / (2 * horizontal_dist)
        return ear

    def analyze_eyes(
        self,
        left_eye_landmarks: list[tuple[float, float]],
        right_eye_landmarks: list[tuple[float, float]],
    ) -> Optional[EyeMetrics]:
        """Analyze both eyes and compute metrics.

        Args:
            left_eye_landmarks: Left eye landmarks.
            right_eye_landmarks: Right eye landmarks.

        Returns:
            EyeMetrics with analysis results.
        """
        # Compute EAR for each eye
        left_ear_raw = self.compute_ear(left_eye_landmarks)
        right_ear_raw = self.compute_ear(right_eye_landmarks)

        # Smooth to reduce jitter (glasses glare / small-eye noise)
        left_ear = self._smooth(self._left_history, left_ear_raw)
        right_ear = self._smooth(self._right_history, right_ear_raw)
        avg_ear = (left_ear + right_ear) / 2

        # Continuously adapt baseline when both eyes confidently open
        if self.adaptive_baseline and left_ear > 0 and right_ear > 0:
            self._update_baseline(avg_ear)
            self._maybe_update_threshold()

        # Determine if eyes are open (with hysteresis)
        left_open = self._is_eye_open(left_ear, self._left_close_counter)
        right_open = self._is_eye_open(right_ear, self._right_close_counter)

        # Update counters
        if left_ear < self.ear_threshold:
            self._left_close_counter = min(
                self._left_close_counter + 1, self.consecutive_frames
            )
        else:
            self._left_close_counter = max(self._left_close_counter - 1, 0)

        if right_ear < self.ear_threshold:
            self._right_close_counter = min(
                self._right_close_counter + 1, self.consecutive_frames
            )
        else:
            self._right_close_counter = max(self._right_close_counter - 1, 0)

        return EyeMetrics(
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            left_open=left_open,
            right_open=right_open,
            both_open=left_open and right_open,
        )

    def _is_eye_open(self, ear: float, counter: int) -> bool:
        """Determine if eye is open using hysteresis.

        Args:
            ear: Eye Aspect Ratio.
            counter: Current close counter.

        Returns:
            True if eye is open.
        """
        # Eye is closed if below threshold for consecutive frames
        if counter >= self.consecutive_frames:
            return False

        # Eye is open if above threshold
        if ear >= self.ear_threshold:
            return True

        # Otherwise, maintain current state
        return True

    def reset_state(self) -> None:
        """Reset eye state counters."""
        self._left_close_counter = 0
        self._right_close_counter = 0
        logger.debug("Eye analyzer state reset")
        self._left_history.clear()
        self._right_history.clear()
        self._baseline_ear = None

    def calibrate_threshold(self, ear_samples: list[float]) -> float:
        """Calibrate EAR threshold from baseline samples.

        Args:
            ear_samples: List of EAR values from normal eye state.

        Returns:
            Calibrated EAR threshold (typically 60-70% of average).
        """
        if not ear_samples:
            logger.warning("No EAR samples for calibration")
            return self.ear_threshold

        avg_ear = sum(ear_samples) / len(ear_samples)
        std_ear = math.sqrt(sum((x - avg_ear) ** 2 for x in ear_samples) / len(ear_samples))

        # Threshold is avg - 1.5 * std (to account for natural variation)
        calibrated_threshold = max(0.15, avg_ear - 1.5 * std_ear)

        logger.info(
            f"Calibrated EAR threshold: {calibrated_threshold:.3f} "
            f"(avg: {avg_ear:.3f}, std: {std_ear:.3f})"
        )

        self.ear_threshold = calibrated_threshold
        return calibrated_threshold

    def get_threshold(self) -> float:
        """Get current EAR threshold."""
        return self.ear_threshold

    def set_threshold(self, threshold: float) -> None:
        """Set EAR threshold.

        Args:
            threshold: New EAR threshold.
        """
        self.ear_threshold = max(0.1, min(0.4, threshold))
        logger.info(f"EAR threshold set to {self.ear_threshold:.3f}")

    # -------- internal helpers --------
    def _smooth(self, history: list[float], value: float) -> float:
        """Median-smooth EAR to reduce noise from glasses or landmark jitter."""
        history.append(value)
        if len(history) > self.smooth_window:
            history.pop(0)
        sorted_vals = sorted(history)
        mid = len(sorted_vals) // 2
        if len(sorted_vals) % 2 == 1:
            return sorted_vals[mid]
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2

    def _update_baseline(self, avg_ear: float) -> None:
        """Update running open-eye baseline using EMA when eyes look open."""
        if avg_ear <= 0:
            return
        if self._baseline_ear is None:
            self._baseline_ear = avg_ear
        else:
            self._baseline_ear = (1 - self.baseline_alpha) * self._baseline_ear + self.baseline_alpha * avg_ear

    def _maybe_update_threshold(self) -> None:
        """Adapt threshold to user's face while keeping safe bounds."""
        if self._baseline_ear is None:
            return
        # Use 70% of baseline as threshold; clamp to reasonable physiological range
        adaptive = max(0.12, min(0.35, self._baseline_ear * 0.7))
        if abs(adaptive - self.ear_threshold) >= 0.005:
            self.ear_threshold = adaptive
            logger.debug(f"Adaptive EAR threshold -> {self.ear_threshold:.3f} (baseline {self._baseline_ear:.3f})")
