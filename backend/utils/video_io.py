"""
video_io.py — FFmpeg & OpenCV Video I/O Utilities
===================================================

This module handles all low-level video read/write operations,
wrapping FFmpeg subprocess calls and OpenCV capture/release.

Design philosophy:
  • Use FFmpeg (subprocess) for anything involving encoding, muxing,
    or seeking — it's 5-10× faster than cv2.VideoWriter and supports
    hardware acceleration.
  • Use OpenCV only for frame-by-frame READING and in-memory pixel
    manipulation (it's great at that).
  • All FFmpeg commands are built as lists (not shell strings) for
    safety and cross-platform compatibility.

Dependencies:
  • FFmpeg must be installed and on PATH
  • pip install opencv-python-headless numpy
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# Import config
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    FFMPEG_VCODEC,
    FFMPEG_CRF,
    FFMPEG_PRESET,
    FFMPEG_ACODEC,
    FFMPEG_AUDIO_BITRATE,
    FFMPEG_PIX_FMT,
    OUTPUT_WIDTH,
    OUTPUT_HEIGHT,
    TEMP_DIR,
)

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════
# 1. VIDEO METADATA  (ffprobe)
# ═════════════════════════════════════════════════════════════

def read_video_metadata(video_path: str) -> Dict:
    """
    Probe a video file and return its key properties.

    Uses ffprobe (part of FFmpeg) to extract metadata without
    decoding the entire file — runs in milliseconds.

    Args:
        video_path: Path to the video file.

    Returns:
        dict with keys:
          - width     (int):   Frame width in pixels
          - height    (int):   Frame height in pixels
          - fps       (float): Frames per second
          - duration  (float): Duration in seconds
          - codec     (str):   Video codec name
          - num_frames(int):   Total number of frames (estimated)

    Raises:
        FileNotFoundError: If the video file doesn't exist.
        RuntimeError:      If ffprobe fails.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",                    # suppress banner
        "-print_format", "json",           # output as JSON
        "-show_format",                    # file-level info (duration)
        "-show_streams",                   # stream-level info (w, h, fps)
        video_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    probe = json.loads(result.stdout)

    # Find the first video stream
    video_stream = None
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    if video_stream is None:
        raise RuntimeError("No video stream found in file")

    # ── Parse FPS from the r_frame_rate fraction ─────────────
    # e.g. "30000/1001" for 29.97 fps, or "30/1" for 30 fps
    fps_str = video_stream.get("r_frame_rate", "30/1")
    num, den = map(int, fps_str.split("/"))
    fps = num / den if den != 0 else 30.0

    # ── Duration: prefer stream-level, fallback to format-level
    duration = float(
        video_stream.get("duration")
        or probe.get("format", {}).get("duration", 0)
    )

    # ── Frame count ──────────────────────────────────────────
    num_frames = int(video_stream.get("nb_frames", 0))
    if num_frames == 0:
        num_frames = int(fps * duration)  # estimate

    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "fps": round(fps, 4),
        "duration": round(duration, 4),
        "codec": video_stream.get("codec_name", "unknown"),
        "num_frames": num_frames,
    }


# ═════════════════════════════════════════════════════════════
# 2. SUBCLIP EXTRACTION  (fast seek, no re-encode)
# ═════════════════════════════════════════════════════════════

def extract_subclip(
    input_path: str,
    start_s: float,
    end_s: float,
    output_path: Optional[str] = None,
) -> str:
    """
    Cut a segment from a video WITHOUT re-encoding (stream copy).

    Uses FFmpeg's input seeking (-ss before -i) for near-instant
    operation regardless of file size.

    Args:
        input_path:  Source video file.
        start_s:     Start time in seconds.
        end_s:       End time in seconds.
        output_path: Where to write the clip. If None, auto-generates
                     a path in TEMP_DIR.

    Returns:
        Path to the extracted subclip.
    """
    if output_path is None:
        ext = Path(input_path).suffix or ".mp4"
        output_path = str(TEMP_DIR / f"subclip_{start_s:.1f}_{end_s:.1f}{ext}")

    duration = end_s - start_s

    cmd = [
        "ffmpeg",
        "-y",                              # overwrite output
        "-ss", f"{start_s:.4f}",           # seek BEFORE input (fast)
        "-i", input_path,
        "-t", f"{duration:.4f}",           # duration of clip
        "-c", "copy",                      # stream copy — no re-encode
        "-avoid_negative_ts", "make_zero", # fix timestamp issues
        output_path,
    ]

    logger.info(f"Extracting subclip: {start_s:.1f}s → {end_s:.1f}s")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg subclip extraction failed:\n{result.stderr}")

    return output_path


# ═════════════════════════════════════════════════════════════
# 3. AUDIO EXTRACTION
# ═════════════════════════════════════════════════════════════

def extract_audio(
    video_path: str,
    output_path: Optional[str] = None,
    format: str = "aac",
) -> str:
    """
    Extract the audio track from a video file.

    The audio is needed to re-mux with the cropped video frames
    at the end of the pipeline.

    Args:
        video_path:  Source video.
        output_path: Where to save audio. Auto-generated if None.
        format:      Audio format (aac, mp3, wav).

    Returns:
        Path to the extracted audio file.
    """
    ext_map = {"aac": ".aac", "mp3": ".mp3", "wav": ".wav"}
    ext = ext_map.get(format, ".aac")

    if output_path is None:
        stem = Path(video_path).stem
        output_path = str(TEMP_DIR / f"{stem}_audio{ext}")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",                             # no video
        "-acodec", "copy" if format == "aac" else format,
        output_path,
    ]

    logger.info(f"Extracting audio → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed:\n{result.stderr}")

    return output_path


# ═════════════════════════════════════════════════════════════
# 4. FRAME READING  (OpenCV)
# ═════════════════════════════════════════════════════════════

class VideoFrameReader:
    """
    Generator-based frame reader using OpenCV.

    Yields frames one at a time to keep memory usage constant
    regardless of video length.

    Usage:
        reader = VideoFrameReader("clip.mp4")
        for idx, frame in reader:
            # frame is a BGR numpy array (H×W×3)
            process(frame)
        reader.release()
    """

    def __init__(self, video_path: str):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def __iter__(self):
        """Yield (frame_index, frame_bgr) tuples."""
        idx = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            yield idx, frame
            idx += 1

    def release(self):
        """Release the OpenCV capture object."""
        if self.cap.isOpened():
            self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.release()


# ═════════════════════════════════════════════════════════════
# 5. CROPPED VIDEO RENDERING  (FFmpeg pipe)
# ═════════════════════════════════════════════════════════════

def render_cropped_video(
    cropped_frames: List[np.ndarray],
    fps: float,
    audio_path: Optional[str],
    output_path: str,
    output_width: int = OUTPUT_WIDTH,
    output_height: int = OUTPUT_HEIGHT,
) -> str:
    """
    Encode a list of cropped frames (+ audio) into the final MP4.

    Strategy:
      1. Pipe raw frames to FFmpeg via stdin (avoids writing thousands
         of intermediate PNG/JPEG files to disk).
      2. FFmpeg scales to the target resolution, encodes with H.264,
         and muxes in the audio track.

    This is significantly faster than cv2.VideoWriter because:
      • FFmpeg uses optimised ASM codecs (libx264)
      • We can set CRF/preset for quality-vs-speed tradeoff
      • Hardware acceleration is available if configured

    Args:
        cropped_frames: List of BGR numpy arrays (all same size).
        fps:            Frames per second for the output.
        audio_path:     Path to audio file to mux in. None = silent.
        output_path:    Where to write the final MP4.
        output_width:   Target output width  (default 1080).
        output_height:  Target output height (default 1920).

    Returns:
        The output_path (for convenience / chaining).
    """
    if not cropped_frames:
        raise ValueError("No frames to render")

    # Get dimensions of the cropped frames (before scaling)
    in_h, in_w = cropped_frames[0].shape[:2]

    # ── Build the FFmpeg command ─────────────────────────────
    cmd = [
        "ffmpeg",
        "-y",                                       # overwrite
        # ── Video input: raw frames piped via stdin ──────────
        "-f", "rawvideo",                            # input format
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",                         # OpenCV uses BGR
        "-s", f"{in_w}x{in_h}",                     # input dimensions
        "-r", str(fps),                              # input framerate
        "-i", "pipe:0",                              # read from stdin
    ]

    # ── Optional audio input ─────────────────────────────────
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])

    # ── Video encoding settings ──────────────────────────────
    cmd.extend([
        "-vf", f"scale={output_width}:{output_height}",  # scale to 1080×1920
        "-c:v", FFMPEG_VCODEC,
        "-crf", FFMPEG_CRF,
        "-preset", FFMPEG_PRESET,
        "-pix_fmt", FFMPEG_PIX_FMT,
    ])

    # ── Audio encoding settings ──────────────────────────────
    if audio_path and os.path.exists(audio_path):
        cmd.extend([
            "-c:a", FFMPEG_ACODEC,
            "-b:a", FFMPEG_AUDIO_BITRATE,
            "-shortest",                             # trim to shortest stream
        ])

    cmd.append(output_path)

    logger.info(f"Rendering {len(cropped_frames)} frames → {output_path}")

    # ── Open FFmpeg process and pipe frames ──────────────────
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Write each frame's raw bytes to FFmpeg's stdin
    for frame in cropped_frames:
        try:
            process.stdin.write(frame.tobytes())
        except BrokenPipeError:
            break

    process.stdin.close()
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg encoding failed:\n{stderr.decode()}")

    logger.info(f"✓ Rendered vertical short: {output_path}")
    return output_path


# ═════════════════════════════════════════════════════════════
# 6. STREAMING RENDER  (lower memory — writes frames as they come)
# ═════════════════════════════════════════════════════════════

class StreamingVideoWriter:
    """
    Write frames to FFmpeg one at a time via a persistent pipe.

    Unlike render_cropped_video() which needs ALL frames in memory,
    this class streams frames as they're produced — keeping memory
    usage proportional to a single frame (~6 MB for 1080p).

    Usage:
        writer = StreamingVideoWriter("out.mp4", fps=30, ...)
        for frame in frames:
            writer.write(frame)
        writer.close()
    """

    def __init__(
        self,
        output_path: str,
        fps: float,
        input_width: int,
        input_height: int,
        audio_path: Optional[str] = None,
        output_width: int = OUTPUT_WIDTH,
        output_height: int = OUTPUT_HEIGHT,
    ):
        self.output_path = output_path
        self._frame_count = 0

        # Build FFmpeg command (same as render_cropped_video)
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{input_width}x{input_height}",
            "-r", str(fps),
            "-i", "pipe:0",
        ]

        if audio_path and os.path.exists(audio_path):
            cmd.extend(["-i", audio_path])

        cmd.extend([
            "-vf", f"scale={output_width}:{output_height}",
            "-c:v", FFMPEG_VCODEC,
            "-crf", FFMPEG_CRF,
            "-preset", FFMPEG_PRESET,
            "-pix_fmt", FFMPEG_PIX_FMT,
        ])

        if audio_path and os.path.exists(audio_path):
            cmd.extend([
                "-c:a", FFMPEG_ACODEC,
                "-b:a", FFMPEG_AUDIO_BITRATE,
                "-shortest",
            ])

        cmd.append(output_path)

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def write(self, frame: np.ndarray):
        """Write a single BGR frame to the output."""
        try:
            self._process.stdin.write(frame.tobytes())
            self._frame_count += 1
        except BrokenPipeError:
            stderr = self._process.stderr.read().decode()
            raise RuntimeError(f"FFmpeg pipe broken after {self._frame_count} frames:\n{stderr}")

    def close(self) -> str:
        """Finalise the video file. Returns the output path."""
        self._process.stdin.close()
        _, stderr = self._process.communicate()

        if self._process.returncode != 0:
            raise RuntimeError(f"FFmpeg encoding failed:\n{stderr.decode()}")

        logger.info(f"✓ Streamed {self._frame_count} frames → {self.output_path}")
        return self.output_path

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
