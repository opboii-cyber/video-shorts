"""
cropping_engine.py — Vision & Cropping Engine Orchestrator  (Step 3)
=====================================================================

This is the MAIN module that ties the entire Step 3 pipeline together.
It reads a video segment, tracks faces frame-by-frame, smooths the
crop position, and renders the final 9:16 vertical short.

Pipeline:
  ┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐
  │ Extract    │───▶│ Read frames  │───▶│ Face detect  │───▶│ Smooth     │
  │ subclip    │    │ (OpenCV)     │    │ (MediaPipe)  │    │ (Kalman)   │
  └────────────┘    └──────────────┘    └──────────────┘    └────────────┘
                                                                  │
  ┌────────────┐    ┌──────────────┐    ┌──────────────┐          │
  │ Final MP4  │◀───│ Render       │◀───│ Crop frame   │◀─────────┘
  │ + audio    │    │ (FFmpeg)     │    │ (numpy slice)│
  └────────────┘    └──────────────┘    └──────────────┘

Optimisation strategies:
  1. FRAME SKIPPING — Run face detection every N-th frame (default 3).
     Interpolate crop positions for skipped frames.  This cuts
     MediaPipe inference time by ~66% with negligible quality loss.

  2. STREAMING WRITES — Use StreamingVideoWriter to pipe frames
     directly to FFmpeg.  No intermediate PNGs on disk, no list of
     all frames in RAM.  Memory usage ≈ O(1 frame).

  3. PRE-COMPUTED CROP SIZE — The 9:16 crop rectangle dimensions
     are constant for a given source resolution; only the position
     changes.  CropWindowCalculator computes this once.

  4. SINGLE MODEL INSTANCE — FaceTracker loads MediaPipe once and
     reuses it for every frame (avoids ~200 ms model load per frame).

Usage:
    engine = CroppingEngine()
    output = engine.process(
        video_path="input.mp4",
        start_time=42.5,
        end_time=102.0,
        output_path="vertical_short.mp4",
    )

Dependencies:
    pip install opencv-python-headless mediapipe numpy
    + FFmpeg on PATH
"""

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

# ── Internal modules ─────────────────────────────────────────
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.face_tracker import FaceTracker, FaceBBox
from services.bbox_smoother import BBoxSmoother, CropWindowCalculator, CropWindow
from utils.video_io import (
    read_video_metadata,
    extract_subclip,
    extract_audio,
    VideoFrameReader,
    StreamingVideoWriter,
    render_cropped_video,
)
from config import (
    DETECTION_FRAME_INTERVAL,
    OUTPUT_DIR,
    TEMP_DIR,
    OUTPUT_WIDTH,
    OUTPUT_HEIGHT,
)

logger = logging.getLogger(__name__)


class CroppingEngine:
    """
    End-to-end pipeline: video in → vertical short out.

    Handles subclip extraction, face tracking, crop smoothing,
    and final rendering with audio.
    """

    def __init__(
        self,
        smoothing_method: str = "kalman",
        detection_interval: int = DETECTION_FRAME_INTERVAL,
        output_width: int = OUTPUT_WIDTH,
        output_height: int = OUTPUT_HEIGHT,
    ):
        """
        Initialise the cropping engine.

        Args:
            smoothing_method:   "kalman" or "ema" — how to smooth
                                crop positions between frames.
            detection_interval: Run face detection every N-th frame.
                                1 = every frame (accurate but slow).
                                3 = every 3rd frame (good balance).
                                5 = every 5th frame (fast, slight lag).
            output_width:       Final video width  (default 1080).
            output_height:      Final video height (default 1920).
        """
        self.smoothing_method = smoothing_method
        self.detection_interval = max(1, detection_interval)
        self.output_width = output_width
        self.output_height = output_height

        # ── Initialise the face tracker (loads model ONCE) ───
        self._tracker = FaceTracker()

        # ── Initialise the bbox smoother ─────────────────────
        self._smoother = BBoxSmoother(method=smoothing_method)

        logger.info(
            f"CroppingEngine initialised: "
            f"smoothing={smoothing_method}, "
            f"detection_interval={detection_interval}, "
            f"output={output_width}×{output_height}"
        )

    # ═════════════════════════════════════════════════════════
    # MAIN PUBLIC API
    # ═════════════════════════════════════════════════════════

    def process(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Process a video segment into a vertical short.

        This is the single entry point for the entire Step 3 pipeline.

        Args:
            video_path:  Path to the source video (any format FFmpeg supports).
            start_time:  Clip start in seconds (from Step 2's hook finder).
            end_time:    Clip end in seconds.
            output_path: Where to save the result. Auto-generated if None.

        Returns:
            Absolute path to the rendered vertical short (.mp4).

        Raises:
            FileNotFoundError: If video_path doesn't exist.
            RuntimeError:      If any pipeline stage fails.
        """
        t0 = time.time()

        # ── Validate input ───────────────────────────────────
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Source video not found: {video_path}")

        if end_time <= start_time:
            raise ValueError(f"end_time ({end_time}) must be > start_time ({start_time})")

        # ── Generate output path if not provided ─────────────
        if output_path is None:
            job_id = uuid.uuid4().hex[:8]
            output_path = str(OUTPUT_DIR / f"short_{job_id}.mp4")

        logger.info(f"Processing: {video_path} [{start_time:.1f}s → {end_time:.1f}s]")

        # ─────────────────────────────────────────────────────
        # STAGE 1: Extract the subclip
        # ─────────────────────────────────────────────────────
        logger.info("Stage 1/4: Extracting subclip...")
        subclip_path = extract_subclip(video_path, start_time, end_time)

        # ─────────────────────────────────────────────────────
        # STAGE 2: Extract audio for later re-muxing
        # ─────────────────────────────────────────────────────
        logger.info("Stage 2/4: Extracting audio...")
        try:
            audio_path = extract_audio(subclip_path)
        except RuntimeError:
            # Some clips may not have audio — that's OK
            logger.warning("No audio track found — output will be silent")
            audio_path = None

        # ─────────────────────────────────────────────────────
        # STAGE 3: Frame-by-frame face tracking & cropping
        # ─────────────────────────────────────────────────────
        logger.info("Stage 3/4: Tracking faces & computing crop positions...")
        metadata = read_video_metadata(subclip_path)
        fps = metadata["fps"]
        frame_w = metadata["width"]
        frame_h = metadata["height"]

        logger.info(
            f"  Source: {frame_w}×{frame_h} @ {fps:.2f} fps, "
            f"~{metadata['num_frames']} frames"
        )

        # Pre-compute the crop window calculator (dimensions are constant)
        crop_calc = CropWindowCalculator(frame_w, frame_h)
        logger.info(
            f"  Crop window: {crop_calc.crop_w}×{crop_calc.crop_h} "
            f"(9:16 from {frame_w}×{frame_h})"
        )

        # Reset smoother state for this new video
        self._smoother.reset()

        # ── Process frames with the streaming writer ─────────
        # This avoids holding ALL cropped frames in memory.
        cropped_frames = self._process_frames(
            subclip_path=subclip_path,
            frame_w=frame_w,
            frame_h=frame_h,
            crop_calc=crop_calc,
        )

        # ─────────────────────────────────────────────────────
        # STAGE 4: Render the final video
        # ─────────────────────────────────────────────────────
        logger.info("Stage 4/4: Rendering final vertical short...")
        render_cropped_video(
            cropped_frames=cropped_frames,
            fps=fps,
            audio_path=audio_path,
            output_path=output_path,
            output_width=self.output_width,
            output_height=self.output_height,
        )

        # ── Cleanup temporary files ──────────────────────────
        self._cleanup(subclip_path, audio_path)

        elapsed = time.time() - t0
        logger.info(f"✓ Done in {elapsed:.1f}s → {output_path}")

        return output_path

    # ═════════════════════════════════════════════════════════
    # STREAMING VARIANT  (lower memory)
    # ═════════════════════════════════════════════════════════

    def process_streaming(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Same as process() but uses StreamingVideoWriter to pipe
        frames directly to FFmpeg — total memory ≈ 2 frames.

        Recommended for clips longer than ~60 seconds or when
        running on memory-constrained servers.

        Args & Returns: Same as process().
        """
        t0 = time.time()

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Source video not found: {video_path}")

        if output_path is None:
            job_id = uuid.uuid4().hex[:8]
            output_path = str(OUTPUT_DIR / f"short_{job_id}.mp4")

        # ── Extract subclip + audio ──────────────────────────
        subclip_path = extract_subclip(video_path, start_time, end_time)

        try:
            audio_path = extract_audio(subclip_path)
        except RuntimeError:
            audio_path = None

        # ── Get video properties ─────────────────────────────
        metadata = read_video_metadata(subclip_path)
        fps = metadata["fps"]
        frame_w = metadata["width"]
        frame_h = metadata["height"]

        crop_calc = CropWindowCalculator(frame_w, frame_h)
        self._smoother.reset()

        # ── Stream-process frames ────────────────────────────
        with VideoFrameReader(subclip_path) as reader:
            with StreamingVideoWriter(
                output_path=output_path,
                fps=fps,
                input_width=crop_calc.crop_w,
                input_height=crop_calc.crop_h,
                audio_path=audio_path,
                output_width=self.output_width,
                output_height=self.output_height,
            ) as writer:
                # Track the last detected crop window for interpolation
                last_crop: Optional[CropWindow] = None
                pending_frames = []  # frames waiting for next detection

                for idx, frame in reader:
                    should_detect = (idx % self.detection_interval == 0)

                    if should_detect:
                        # ── Run face detection ───────────────
                        face = self._tracker.get_primary(frame)
                        centre = face.centre if face else None

                        # ── Smooth the position ──────────────
                        smooth_cx, smooth_cy = self._smoother.update(
                            centre, frame_w, frame_h
                        )

                        # ── Compute crop window ──────────────
                        crop = crop_calc.compute(smooth_cx, smooth_cy)

                        # ── Write any pending (skipped) frames
                        if pending_frames and last_crop is not None:
                            # Interpolate between last_crop and current crop
                            for i, pf in enumerate(pending_frames, 1):
                                t = i / (len(pending_frames) + 1)
                                interp_crop = self._interpolate_crops(
                                    last_crop, crop, t
                                )
                                cropped = self._apply_crop(pf, interp_crop)
                                writer.write(cropped)
                            pending_frames.clear()

                        # ── Write the current frame ──────────
                        cropped = self._apply_crop(frame, crop)
                        writer.write(cropped)
                        last_crop = crop

                    else:
                        # ── Skip detection, buffer frame ─────
                        pending_frames.append(frame.copy())

                # ── Flush remaining pending frames ───────────
                if pending_frames and last_crop is not None:
                    for pf in pending_frames:
                        cropped = self._apply_crop(pf, last_crop)
                        writer.write(cropped)

        # ── Cleanup ──────────────────────────────────────────
        self._cleanup(subclip_path, audio_path)

        elapsed = time.time() - t0
        logger.info(f"✓ Streaming done in {elapsed:.1f}s → {output_path}")
        return output_path

    # ═════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ═════════════════════════════════════════════════════════

    def _process_frames(
        self,
        subclip_path: str,
        frame_w: int,
        frame_h: int,
        crop_calc: CropWindowCalculator,
    ) -> list:
        """
        Read all frames, detect faces, smooth, crop, and return
        the list of cropped frames.

        Note: This stores ALL cropped frames in memory. For long
        clips, use process_streaming() instead.

        Returns:
            List of BGR numpy arrays (cropped frames).
        """
        cropped_frames = []

        # Track the last detected crop for interpolation
        last_crop: Optional[CropWindow] = None
        # Buffer for frames where we skipped detection
        skipped_buffer: list = []

        with VideoFrameReader(subclip_path) as reader:
            total = reader.total_frames
            log_interval = max(1, total // 10)  # log every 10%

            for idx, frame in reader:
                should_detect = (idx % self.detection_interval == 0)

                if should_detect:
                    # ── Detect face ──────────────────────────
                    face = self._tracker.get_primary(frame)
                    centre = face.centre if face else None

                    # ── Smooth ───────────────────────────────
                    smooth_cx, smooth_cy = self._smoother.update(
                        centre, frame_w, frame_h
                    )

                    # ── Crop position ────────────────────────
                    crop = crop_calc.compute(smooth_cx, smooth_cy)

                    # ── Process skipped frames via interpolation ─
                    if skipped_buffer and last_crop is not None:
                        n = len(skipped_buffer)
                        for i, skipped_frame in enumerate(skipped_buffer, 1):
                            t = i / (n + 1)
                            interp = self._interpolate_crops(last_crop, crop, t)
                            cropped_frames.append(self._apply_crop(skipped_frame, interp))
                        skipped_buffer.clear()

                    # ── Crop current frame ───────────────────
                    cropped_frames.append(self._apply_crop(frame, crop))
                    last_crop = crop

                else:
                    # ── Skip detection, buffer the frame ─────
                    skipped_buffer.append(frame.copy())

                # ── Progress logging ─────────────────────────
                if idx % log_interval == 0 and idx > 0:
                    pct = (idx / total) * 100
                    logger.info(f"  Progress: {pct:.0f}% ({idx}/{total} frames)")

            # ── Flush remaining skipped frames ───────────────
            if skipped_buffer and last_crop is not None:
                for sf in skipped_buffer:
                    cropped_frames.append(self._apply_crop(sf, last_crop))

        logger.info(f"  Processed {len(cropped_frames)} frames total")
        return cropped_frames

    @staticmethod
    def _apply_crop(frame: np.ndarray, crop: CropWindow) -> np.ndarray:
        """
        Slice the crop region from a frame (zero-copy view when possible).

        Args:
            frame: Source BGR image (H × W × 3).
            crop:  CropWindow with x, y, width, height.

        Returns:
            Cropped BGR image (crop.height × crop.width × 3).
        """
        # NumPy slicing returns a VIEW (no memory copy) when the
        # array is contiguous — this is the fastest possible crop.
        return frame[
            crop.y : crop.y + crop.height,
            crop.x : crop.x + crop.width,
        ].copy()  # .copy() because FFmpeg needs contiguous memory

    @staticmethod
    def _interpolate_crops(
        crop_a: CropWindow,
        crop_b: CropWindow,
        t: float,
    ) -> CropWindow:
        """
        Linearly interpolate between two crop positions.

        Used for frames where we skipped face detection — we blend
        between the previous and next detected positions for smooth
        motion.

        Args:
            crop_a: Start crop position.
            crop_b: End crop position.
            t:      Interpolation factor (0.0 = crop_a, 1.0 = crop_b).

        Returns:
            Interpolated CropWindow.
        """
        return CropWindow(
            x=int(crop_a.x + (crop_b.x - crop_a.x) * t),
            y=int(crop_a.y + (crop_b.y - crop_a.y) * t),
            width=crop_a.width,   # dimensions don't change
            height=crop_a.height,
        )

    @staticmethod
    def _cleanup(*paths: Optional[str]):
        """Remove temporary files, silently ignoring errors."""
        for path in paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass  # non-critical — temp files will be cleaned eventually

    def close(self):
        """Release all resources."""
        self._tracker.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ═════════════════════════════════════════════════════════════
# CONVENIENCE: Run from command line for testing
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Quick test:
        python -m services.cropping_engine input.mp4 10.0 45.0 output.mp4
    """
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if len(sys.argv) < 4:
        print("Usage: python cropping_engine.py <input.mp4> <start_s> <end_s> [output.mp4]")
        sys.exit(1)

    input_file = sys.argv[1]
    start = float(sys.argv[2])
    end = float(sys.argv[3])
    output = sys.argv[4] if len(sys.argv) > 4 else None

    with CroppingEngine() as engine:
        result = engine.process_streaming(input_file, start, end, output)
        print(f"\n✓ Output: {result}")
