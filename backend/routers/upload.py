"""
upload.py — Video Upload Router  (Step 1)
==========================================

Handles:
  POST /api/upload — accept a video file or YouTube URL, extract
  audio, transcribe, and return the timestamped transcript.
"""

import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import UPLOAD_DIR, MAX_CLIP_DURATION_S
from services.transcription import transcribe_video

logger = logging.getLogger(__name__)
router = APIRouter()

# Max upload size: 500 MB
MAX_UPLOAD_BYTES = 500 * 1024 * 1024

ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}


async def _save_upload(file: UploadFile) -> str:
    """Save uploaded file to disk and return the path."""
    ext = Path(file.filename or "video.mp4").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    video_id = uuid.uuid4().hex[:12]
    save_path = UPLOAD_DIR / f"{video_id}{ext}"

    # Stream to disk (avoid loading entire file into memory)
    total = 0
    with open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                os.remove(save_path)
                raise HTTPException(413, "File too large (max 500 MB)")
            f.write(chunk)

    logger.info(f"Saved upload: {save_path} ({total / 1024 / 1024:.1f} MB)")
    return str(save_path)


async def _download_youtube(url: str) -> str:
    """Download a YouTube video using yt-dlp."""
    video_id = uuid.uuid4().hex[:12]
    output_path = str(UPLOAD_DIR / f"yt_{video_id}.mp4")

    cmd = [
        "yt-dlp",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_path,
        "--no-playlist",
        "--max-filesize", "500M",
        url,
    ]

    logger.info(f"Downloading YouTube video: {url}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise HTTPException(400, f"YouTube download failed: {result.stderr[:200]}")

    if not os.path.exists(output_path):
        raise HTTPException(500, "Download completed but output file not found")

    return output_path


@router.post("/upload")
async def upload_video(
    file: Optional[UploadFile] = File(None),
    youtube_url: Optional[str] = Form(None),
):
    """
    Accept a video via file upload or YouTube URL.

    Pipeline:
    1. Save the file or download from YouTube.
    2. Transcribe the audio using Whisper.
    3. Return the transcript + video path for processing.
    """
    # ── Validate input ───────────────────────────────────────
    if not file and not youtube_url:
        raise HTTPException(400, "Provide either a file or youtube_url")

    # ── Step 1: Get the video file ───────────────────────────
    if file and file.filename:
        video_path = await _save_upload(file)
        source = "upload"
    else:
        video_path = await _download_youtube(youtube_url)
        source = "youtube"

    # ── Step 2: Transcribe ───────────────────────────────────
    try:
        transcript = await transcribe_video(video_path)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(500, f"Transcription failed: {str(e)}")

    return {
        "status": "success",
        "source": source,
        "video_path": video_path,
        "transcript": transcript,
    }
