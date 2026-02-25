"""
transcription.py — Whisper Transcription Service  (Step 1)
===========================================================

Extracts audio from a video file and transcribes it using the
OpenAI Whisper API to produce a timestamped transcript.

Supports two modes:
  1. OpenAI API (cloud) — faster, requires OPENAI_API_KEY
  2. Local whisper model — free, slower, requires `openai-whisper` pkg

The output format is a list of segments:
  [{"start": 0.0, "end": 3.5, "text": "Hello world"}, ...]
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Import config
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, TEMP_DIR


# ═════════════════════════════════════════════════════════════
# 1. AUDIO EXTRACTION
# ═════════════════════════════════════════════════════════════

def extract_audio_for_transcription(
    video_path: str,
    output_path: Optional[str] = None,
) -> str:
    """
    Extract audio from video as WAV (16kHz mono) — optimal for Whisper.

    Whisper works best with 16kHz mono WAV input.  We let FFmpeg
    handle the conversion regardless of the source format.

    Args:
        video_path:  Path to the source video.
        output_path: Where to save the audio. Auto-generated if None.

    Returns:
        Path to the extracted WAV file.
    """
    if output_path is None:
        stem = Path(video_path).stem
        output_path = str(TEMP_DIR / f"{stem}_whisper.wav")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                    # no video
        "-acodec", "pcm_s16le",   # 16-bit PCM (WAV)
        "-ar", "16000",           # 16 kHz sample rate (Whisper optimal)
        "-ac", "1",               # mono
        output_path,
    ]

    logger.info(f"Extracting audio for transcription → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed:\n{result.stderr}")

    return output_path


# ═════════════════════════════════════════════════════════════
# 2. OPENAI WHISPER API  (cloud — recommended)
# ═════════════════════════════════════════════════════════════

async def transcribe_with_api(audio_path: str) -> Dict:
    """
    Transcribe audio using the OpenAI Whisper API.

    Uses the 'whisper-1' model with verbose_json format to get
    word-level timestamps.

    Args:
        audio_path: Path to the audio file (WAV/MP3/M4A).

    Returns:
        dict with keys:
          - "text": Full transcript text
          - "segments": List of {start, end, text} dicts
          - "language": Detected language code
          - "duration": Audio duration in seconds
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required: pip install openai")

    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY not set. Set it in your .env file or "
            "use transcribe_with_local() instead."
        )

    client = OpenAI(api_key=OPENAI_API_KEY)

    logger.info(f"Sending audio to Whisper API: {audio_path}")

    with open(audio_path, "rb") as audio_file:
        # Use verbose_json for segment-level timestamps
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    # Parse the response into our standard format
    segments = []
    for seg in response.segments:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })

    result = {
        "text": response.text,
        "segments": segments,
        "language": response.language,
        "duration": segments[-1]["end"] if segments else 0.0,
    }

    logger.info(
        f"Transcription complete: {len(segments)} segments, "
        f"language={result['language']}, duration={result['duration']:.1f}s"
    )

    return result


# ═════════════════════════════════════════════════════════════
# 3. LOCAL WHISPER MODEL  (fallback — no API key needed)
# ═════════════════════════════════════════════════════════════

async def transcribe_with_local(
    audio_path: str,
    model_size: str = "base",
) -> Dict:
    """
    Transcribe audio using a local Whisper model.

    This is slower but free.  Models: tiny, base, small, medium, large.

    Args:
        audio_path: Path to the audio file.
        model_size: Whisper model size (default "base" for speed).

    Returns:
        Same format as transcribe_with_api().
    """
    try:
        import whisper
    except ImportError:
        raise ImportError("openai-whisper package required: pip install openai-whisper")

    logger.info(f"Loading local Whisper model: {model_size}")
    model = whisper.load_model(model_size)

    logger.info(f"Transcribing with local model: {audio_path}")
    result = model.transcribe(audio_path, fp16=False)

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return {
        "text": result.get("text", ""),
        "segments": segments,
        "language": result.get("language", "en"),
        "duration": segments[-1]["end"] if segments else 0.0,
    }


# ═════════════════════════════════════════════════════════════
# 4. PUBLIC API  (auto-selects cloud vs local)
# ═════════════════════════════════════════════════════════════

async def transcribe_video(video_path: str) -> Dict:
    """
    Full pipeline: extract audio → transcribe → return transcript.

    Automatically uses OpenAI API if key is set, otherwise falls
    back to local Whisper model.

    Args:
        video_path: Path to the source video file.

    Returns:
        dict with "text", "segments", "language", "duration".
    """
    # Step 1: Extract audio
    audio_path = extract_audio_for_transcription(video_path)

    try:
        # Step 2: Transcribe (auto-select method)
        if OPENAI_API_KEY:
            logger.info("Using OpenAI Whisper API (cloud)")
            transcript = await transcribe_with_api(audio_path)
        else:
            logger.info("No API key found — using local Whisper model")
            transcript = await transcribe_with_local(audio_path)

        return transcript

    finally:
        # Cleanup the temporary audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
