"""
face_tracker.py — MediaPipe Face Detection Service
====================================================

This module wraps Google MediaPipe's Face Detection to provide a
clean interface for locating faces in individual video frames.

Key design decisions:
  • The MediaPipe detector is initialised ONCE and reused across all
    frames to avoid the ~200 ms startup cost per instantiation.
  • When multiple faces are detected, we pick the "primary" face
    using a heuristic: largest bounding-box area × proximity to
    frame centre.  This approximates the "active speaker" without
    needing a full speaker-diarisation model.
  • All coordinates are returned in ABSOLUTE PIXELS (not the 0-1
    normalised form that MediaPipe uses internally).

Dependencies:
  pip install mediapipe opencv-python-headless numpy
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

# Import tuneable constants from our central config
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FACE_DETECTION_CONFIDENCE, FACE_DETECTION_MODEL


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────

@dataclass
class FaceBBox:
    """
    Absolute-pixel bounding box for a detected face.

    Attributes:
        x:      Left edge   (pixels from left)
        y:      Top edge    (pixels from top)
        width:  Box width   (pixels)
        height: Box height  (pixels)
        confidence: Detection confidence score (0-1)
    """
    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def centre(self) -> Tuple[int, int]:
        """Return the (cx, cy) centre of the bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        """Return the area in pixels² — used for ranking detections."""
        return self.width * self.height


# ─────────────────────────────────────────────────────────────
# Face Tracker Class
# ─────────────────────────────────────────────────────────────

class FaceTracker:
    """
    Thin wrapper around MediaPipe FaceDetection.

    Usage:
        tracker = FaceTracker()
        faces = tracker.detect(frame)      # → List[FaceBBox]
        primary = tracker.get_primary(frame)  # → Optional[FaceBBox]
        tracker.close()                     # release resources
    """

    def __init__(
        self,
        min_confidence: float = FACE_DETECTION_CONFIDENCE,
        model_selection: int = FACE_DETECTION_MODEL,
    ):
        """
        Initialise the MediaPipe face detector.

        Args:
            min_confidence:  Minimum detection confidence (0–1).
            model_selection: 0 = short-range (<2 m), 1 = full-range (<5 m).
        """
        # ── Store the MediaPipe Face Detection solution ──────
        self._mp_face = mp.solutions.face_detection

        # ── Create the detector (expensive — do this ONCE) ───
        self._detector = self._mp_face.FaceDetection(
            min_detection_confidence=min_confidence,
            model_selection=model_selection,
        )

        # ── Cache the last known primary face for fallback ───
        self._last_primary: Optional[FaceBBox] = None

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray) -> List[FaceBBox]:
        """
        Detect all faces in a BGR frame.

        Args:
            frame: OpenCV BGR image (H × W × 3, dtype=uint8).

        Returns:
            List of FaceBBox in absolute pixel coordinates,
            sorted by descending area (largest first).
        """
        h, w, _ = frame.shape

        # MediaPipe expects RGB input
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._detector.process(rgb)

        if not results.detections:
            return []

        faces: List[FaceBBox] = []

        for detection in results.detections:
            # ── Extract the relative bounding box ────────────
            # MediaPipe returns xmin, ymin, width, height all in
            # normalised 0-1 coordinates relative to frame size.
            bbox = detection.location_data.relative_bounding_box

            # ── Convert to absolute pixel coordinates ────────
            abs_x = max(0, int(bbox.xmin * w))
            abs_y = max(0, int(bbox.ymin * h))
            abs_w = min(int(bbox.width * w), w - abs_x)   # clamp to frame
            abs_h = min(int(bbox.height * h), h - abs_y)

            # ── Extract confidence score ─────────────────────
            score = detection.score[0] if detection.score else 0.0

            faces.append(FaceBBox(
                x=abs_x, y=abs_y,
                width=abs_w, height=abs_h,
                confidence=score,
            ))

        # Sort by area descending — largest face is most likely
        # the primary subject in a talking-head video
        faces.sort(key=lambda f: f.area, reverse=True)
        return faces

    def get_primary(
        self,
        frame: np.ndarray,
        bias_centre: bool = True,
    ) -> Optional[FaceBBox]:
        """
        Detect the single most important face in the frame.

        Selection heuristic (when multiple faces are found):
          score = area_normalised × 0.7  +  centre_proximity × 0.3

        This favours large faces that are near the frame centre —
        a good proxy for the "active speaker" in most video formats.

        Args:
            frame:       BGR image.
            bias_centre: If True, bias selection toward frame centre.

        Returns:
            The primary FaceBBox, or None if no face is detected.
            When None, self._last_primary is preserved for fallback.
        """
        faces = self.detect(frame)

        if not faces:
            # No face found — caller can use self.last_primary as fallback
            return None

        if len(faces) == 1 or not bias_centre:
            # Only one face, or centre bias disabled → return largest
            self._last_primary = faces[0]
            return faces[0]

        # ── Multi-face ranking ───────────────────────────────
        h, w, _ = frame.shape
        frame_cx, frame_cy = w / 2, h / 2

        # Normalise areas so the largest face scores 1.0
        max_area = faces[0].area  # already sorted descending

        best_face = faces[0]
        best_score = -1.0

        for face in faces:
            # Area component (0-1, where 1 = largest)
            area_score = face.area / max_area if max_area > 0 else 0.0

            # Centre-proximity component (0-1, where 1 = dead centre)
            cx, cy = face.centre
            max_dist = np.sqrt(frame_cx**2 + frame_cy**2)  # corner distance
            dist = np.sqrt((cx - frame_cx)**2 + (cy - frame_cy)**2)
            centre_score = 1.0 - (dist / max_dist) if max_dist > 0 else 0.0

            # Weighted combination
            combined = area_score * 0.7 + centre_score * 0.3

            if combined > best_score:
                best_score = combined
                best_face = face

        self._last_primary = best_face
        return best_face

    @property
    def last_primary(self) -> Optional[FaceBBox]:
        """
        The last successfully detected primary face.
        Useful as a fallback when detection fails on a frame.
        """
        return self._last_primary

    def close(self):
        """Release MediaPipe resources."""
        self._detector.close()

    # ── Context manager support ──────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
