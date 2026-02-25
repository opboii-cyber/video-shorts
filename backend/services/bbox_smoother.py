"""
bbox_smoother.py — Crop-Window Smoothing & Calculation
=======================================================

Purpose:
  Raw per-frame face detections jump around due to detector noise,
  slight head movements, and missed frames.  Directly cropping to
  those raw positions produces jarring "camera jitter".

  This module provides two smoothing strategies:
    1. **Kalman Filter** (default) — optimal for Gaussian noise,
       models velocity so it can predict through brief dropouts.
    2. **Exponential Moving Average (EMA)** — simpler, lower latency,
       good fallback when Kalman is overkill.

  It also includes `CropWindowCalculator` which takes a smoothed
  face-centre and computes the final 9:16 crop rectangle, clamped
  so it never exceeds the source frame boundaries.

Architecture:
  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
  │ FaceTracker  │────▶│ BBoxSmoother │────▶│ CropWindowCalc   │
  │ (raw coords) │     │ (smooth xy)  │     │ (9:16 rectangle) │
  └──────────────┘     └──────────────┘     └──────────────────┘

Dependencies:
  pip install numpy
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np

# Import tuneable constants
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    KALMAN_PROCESS_NOISE,
    KALMAN_MEASUREMENT_NOISE,
    EMA_ALPHA,
    NO_FACE_FREEZE_FRAMES,
    TARGET_ASPECT_W,
    TARGET_ASPECT_H,
)


# ═════════════════════════════════════════════════════════════
# 1. KALMAN FILTER  (1-D, applied independently to X and Y)
# ═════════════════════════════════════════════════════════════

class KalmanFilter1D:
    """
    Minimal 1-D Kalman filter with a constant-velocity model.

    State vector:  [position, velocity]
    Measurement:   [position]

    This is intentionally simple — a 1-D filter per axis is faster
    and more interpretable than a full 4-D tracker for our use case.
    """

    def __init__(
        self,
        process_noise: float = KALMAN_PROCESS_NOISE,
        measurement_noise: float = KALMAN_MEASUREMENT_NOISE,
    ):
        # ── State: [position, velocity] ──────────────────────
        self.x = np.array([0.0, 0.0])  # state estimate

        # ── Error covariance matrix (2×2) ────────────────────
        # Start with high uncertainty so the filter adapts quickly
        self.P = np.eye(2) * 1000.0

        # ── State transition matrix ──────────────────────────
        # Assumes constant velocity between frames:
        #   position_new = position_old + velocity × dt
        #   velocity_new = velocity_old
        # dt is normalised to 1.0 (one frame step)
        self.F = np.array([
            [1.0, 1.0],   # pos += vel
            [0.0, 1.0],   # vel stays
        ])

        # ── Measurement matrix ───────────────────────────────
        # We only observe position, not velocity
        self.H = np.array([[1.0, 0.0]])

        # ── Process noise covariance ─────────────────────────
        # How much we expect the true state to deviate from our
        # constant-velocity model per frame
        self.Q = np.array([
            [process_noise, 0.0],
            [0.0, process_noise],
        ])

        # ── Measurement noise covariance ─────────────────────
        # How noisy we expect the face-detector output to be
        self.R = np.array([[measurement_noise]])

        self._initialised = False

    def predict(self) -> float:
        """
        Predict the next state (one frame forward).
        Returns the predicted position.
        """
        # x̂ = F × x
        self.x = self.F @ self.x
        # P̂ = F × P × Fᵀ + Q
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x[0]

    def update(self, measurement: float) -> float:
        """
        Incorporate a new measurement and return the corrected
        position estimate.

        Args:
            measurement: Observed face-centre coordinate (x or y).

        Returns:
            Smoothed position after Kalman correction.
        """
        if not self._initialised:
            # First measurement → snap to it instead of filtering
            self.x[0] = measurement
            self._initialised = True
            return measurement

        # ── Predict step ─────────────────────────────────────
        self.predict()

        # ── Innovation (measurement residual) ────────────────
        z = np.array([measurement])
        y = z - self.H @ self.x  # how far off our prediction was

        # ── Innovation covariance ────────────────────────────
        S = self.H @ self.P @ self.H.T + self.R

        # ── Kalman gain ──────────────────────────────────────
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # ── Correct the state estimate ───────────────────────
        self.x = self.x + (K @ y).flatten()

        # ── Update error covariance ──────────────────────────
        I = np.eye(2)
        self.P = (I - K @ self.H) @ self.P

        return self.x[0]

    @property
    def position(self) -> float:
        """Current smoothed position estimate."""
        return self.x[0]

    @property
    def velocity(self) -> float:
        """Current estimated velocity (pixels per frame)."""
        return self.x[1]


# ═════════════════════════════════════════════════════════════
# 2. EXPONENTIAL MOVING AVERAGE  (simpler fallback)
# ═════════════════════════════════════════════════════════════

class EMAFilter:
    """
    Simple Exponential Moving Average filter.

    smoothed = α × measurement + (1 - α) × smoothed_prev

    Pros:  Zero-latency, trivial to implement, very fast.
    Cons:  No velocity model, so it lags behind fast movements.
    """

    def __init__(self, alpha: float = EMA_ALPHA):
        """
        Args:
            alpha: Smoothing factor (0-1).
                   Lower = smoother (more lag).
                   Higher = snappier (less smoothing).
        """
        self.alpha = alpha
        self._value: Optional[float] = None

    def update(self, measurement: float) -> float:
        """Apply EMA and return the smoothed value."""
        if self._value is None:
            self._value = measurement  # initialise on first call
        else:
            self._value = self.alpha * measurement + (1 - self.alpha) * self._value
        return self._value

    @property
    def value(self) -> Optional[float]:
        """Current smoothed value."""
        return self._value


# ═════════════════════════════════════════════════════════════
# 3. BBOX SMOOTHER  (combines filters for X and Y axes)
# ═════════════════════════════════════════════════════════════

class BBoxSmoother:
    """
    Smooths the (cx, cy) centre of a face bounding box across frames.

    Uses either Kalman or EMA filters (one per axis).
    Handles "no detection" frames by freezing the last known position
    for up to `NO_FACE_FREEZE_FRAMES`, then slowly drifting to centre.

    Usage:
        smoother = BBoxSmoother(method="kalman")
        for frame_idx, face in detections:
            cx, cy = smoother.update(face.centre if face else None)
    """

    def __init__(self, method: str = "kalman"):
        """
        Args:
            method: "kalman" or "ema".
        """
        if method == "kalman":
            self._filter_x = KalmanFilter1D()
            self._filter_y = KalmanFilter1D()
        elif method == "ema":
            self._filter_x = EMAFilter()
            self._filter_y = EMAFilter()
        else:
            raise ValueError(f"Unknown smoothing method: {method!r}")

        self._method = method
        self._no_face_count = 0          # consecutive frames with no detection
        self._last_cx: Optional[float] = None
        self._last_cy: Optional[float] = None

    def update(
        self,
        centre: Optional[Tuple[int, int]],
        frame_width: int = 1920,
        frame_height: int = 1080,
    ) -> Tuple[float, float]:
        """
        Feed a new face-centre observation (or None if no face found).

        Args:
            centre:       (cx, cy) in pixels, or None if no face detected.
            frame_width:  Width of the source frame (for centre fallback).
            frame_height: Height of the source frame (for centre fallback).

        Returns:
            (smoothed_cx, smoothed_cy) in pixels.
        """
        if centre is not None:
            # ── Face detected — reset the no-face counter ────
            self._no_face_count = 0
            cx, cy = float(centre[0]), float(centre[1])
            smoothed_cx = self._filter_x.update(cx)
            smoothed_cy = self._filter_y.update(cy)

        else:
            # ── No face detected ─────────────────────────────
            self._no_face_count += 1

            if self._no_face_count <= NO_FACE_FREEZE_FRAMES:
                # Freeze at last known position (Kalman will predict
                # forward using velocity; EMA just holds)
                if self._method == "kalman":
                    smoothed_cx = self._filter_x.predict()
                    smoothed_cy = self._filter_y.predict()
                else:
                    # EMA has no predict — just reuse last value
                    smoothed_cx = self._last_cx or frame_width / 2
                    smoothed_cy = self._last_cy or frame_height / 2
            else:
                # Too many misses — slowly drift toward frame centre
                # This prevents the crop from being stuck in a corner
                fallback_cx = frame_width / 2
                fallback_cy = frame_height / 2
                smoothed_cx = self._filter_x.update(fallback_cx)
                smoothed_cy = self._filter_y.update(fallback_cy)

        self._last_cx = smoothed_cx
        self._last_cy = smoothed_cy
        return (smoothed_cx, smoothed_cy)

    def reset(self):
        """Reset the smoother state for a new video."""
        self.__init__(method=self._method)


# ═════════════════════════════════════════════════════════════
# 4. CROP WINDOW CALCULATOR
# ═════════════════════════════════════════════════════════════

@dataclass
class CropWindow:
    """
    The final 9:16 crop rectangle in absolute pixel coordinates.

    Attributes:
        x:      Left edge of the crop (pixels)
        y:      Top edge of the crop (pixels)
        width:  Crop width (pixels)
        height: Crop height (pixels)
    """
    x: int
    y: int
    width: int
    height: int


class CropWindowCalculator:
    """
    Computes a 9:16 crop window centred on a given (cx, cy) point,
    clamped to stay within the source frame boundaries.

    The crop dimensions are calculated to be as large as possible
    while maintaining 9:16 and fitting inside the source frame.

    Example for a 1920×1080 (16:9) source:
      • Max height = 1080
      • Width for 9:16 at height 1080 = 1080 × (9/16) = 607.5 → 608
      • So the crop is 608 × 1080

    This is then scaled to the target output resolution (e.g. 1080×1920)
    during final FFmpeg encoding.
    """

    def __init__(
        self,
        frame_width: int,
        frame_height: int,
        aspect_w: int = TARGET_ASPECT_W,
        aspect_h: int = TARGET_ASPECT_H,
    ):
        """
        Pre-compute the crop dimensions once (they don't change
        between frames — only the position moves).

        Args:
            frame_width:  Source video width in pixels.
            frame_height: Source video height in pixels.
            aspect_w:     Target aspect width  (default 9).
            aspect_h:     Target aspect height (default 16).
        """
        self.frame_w = frame_width
        self.frame_h = frame_height

        target_ratio = aspect_w / aspect_h  # 0.5625 for 9:16

        # ── Determine crop size ──────────────────────────────
        # Try fitting by height first (usually the constraint for
        # landscape → portrait conversion)
        crop_h = frame_height
        crop_w = int(crop_h * target_ratio)

        if crop_w > frame_width:
            # Frame is too narrow → fit by width instead
            crop_w = frame_width
            crop_h = int(crop_w / target_ratio)

        # Ensure even dimensions (required by most video codecs)
        self.crop_w = crop_w - (crop_w % 2)
        self.crop_h = crop_h - (crop_h % 2)

    def compute(self, cx: float, cy: float) -> CropWindow:
        """
        Compute the crop rectangle centred on (cx, cy).

        The rectangle is clamped so it stays fully inside the
        source frame — no out-of-bounds regions.

        Args:
            cx: Smoothed face-centre X (pixels).
            cy: Smoothed face-centre Y (pixels).

        Returns:
            CropWindow with clamped integer coordinates.
        """
        # ── Centre the crop on the face ──────────────────────
        x = int(cx - self.crop_w / 2)
        y = int(cy - self.crop_h / 2)

        # ── Clamp to frame boundaries ────────────────────────
        x = max(0, min(x, self.frame_w - self.crop_w))
        y = max(0, min(y, self.frame_h - self.crop_h))

        return CropWindow(x=x, y=y, width=self.crop_w, height=self.crop_h)
