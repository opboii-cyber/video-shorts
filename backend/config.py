"""
config.py — Central Configuration for Video Shorts MVP
=======================================================

All tuneable constants live here so they can be adjusted without
touching business logic.  Values are grouped by subsystem.
"""

import os
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# 1. PATHS
# ─────────────────────────────────────────────────────────────

# Root of the project (one level up from /backend)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Where uploaded originals and temporary clips are stored
UPLOAD_DIR = PROJECT_ROOT / "outputs" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Where final processed shorts are written
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "shorts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Temporary working directory for intermediate frames / audio
TEMP_DIR = PROJECT_ROOT / "outputs" / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# 2. VIDEO / ASPECT RATIO
# ─────────────────────────────────────────────────────────────

# Target output aspect ratio  (width / height)
# 9:16 = 0.5625  →  vertical / portrait
TARGET_ASPECT_W = 9
TARGET_ASPECT_H = 16
TARGET_ASPECT_RATIO = TARGET_ASPECT_W / TARGET_ASPECT_H  # 0.5625

# Default output resolution (1080 × 1920 is standard vertical HD)
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920

# Maximum clip duration in seconds the engine will process
MAX_CLIP_DURATION_S = 120


# ─────────────────────────────────────────────────────────────
# 3. MEDIAPIPE — Face Detection
# ─────────────────────────────────────────────────────────────

# Minimum confidence score to consider a detection valid (0-1)
FACE_DETECTION_CONFIDENCE = 0.5

# Which MediaPipe model to use:
#   0 = short-range (within 2 m) — faster, good for talking-head
#   1 = full-range  (within 5 m) — heavier but handles wider shots
FACE_DETECTION_MODEL = 1


# ─────────────────────────────────────────────────────────────
# 4. CROP SMOOTHING  (Kalman Filter / EMA)
# ─────────────────────────────────────────────────────────────

# Kalman filter process noise — lower = smoother but slower to react
KALMAN_PROCESS_NOISE = 1e-3

# Kalman filter measurement noise — higher = trust predictions more
KALMAN_MEASUREMENT_NOISE = 1e-1

# Exponential Moving Average alpha (fallback smoother)
# Range 0-1: lower = smoother, higher = snappier
EMA_ALPHA = 0.15

# How many consecutive "no-face" frames before we freeze the crop
# window instead of snapping to centre
NO_FACE_FREEZE_FRAMES = 10


# ─────────────────────────────────────────────────────────────
# 5. PERFORMANCE — Frame Skipping
# ─────────────────────────────────────────────────────────────

# Run face detection every N-th frame; interpolate crop positions
# for the frames in between.  Higher = faster but less accurate.
DETECTION_FRAME_INTERVAL = 3

# Number of OpenCV decode threads (0 = auto)
CV2_THREADS = 0


# ─────────────────────────────────────────────────────────────
# 6. FFMPEG / CODEC
# ─────────────────────────────────────────────────────────────

# Codec for the final short  (libx264 is universally compatible)
FFMPEG_VCODEC = "libx264"

# Constant Rate Factor — lower = better quality, bigger file
# 18-23 is a good range for social media
FFMPEG_CRF = "20"

# Encoding preset — slower = better compression
# Options: ultrafast, superfast, veryfast, faster, fast,
#          medium, slow, slower, veryslow
FFMPEG_PRESET = "fast"

# Audio codec for the final output
FFMPEG_ACODEC = "aac"

# Audio bitrate
FFMPEG_AUDIO_BITRATE = "192k"

# Pixel format (yuv420p ensures broad compatibility)
FFMPEG_PIX_FMT = "yuv420p"


# ─────────────────────────────────────────────────────────────
# 7. API KEYS  (loaded from environment)
# ─────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
