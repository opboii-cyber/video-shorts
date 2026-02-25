"""
process.py — Video Processing Orchestrator Router
===================================================

Handles:
  POST /api/process — run the full pipeline on an uploaded video:
    1. (Optional) Transcribe if not already done
    2. Find the best hook via LLM
    3. Crop the video to 9:16
    4. Return the result
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.transcription import transcribe_video
from services.hook_finder import find_hook
from services.cropping_engine import CroppingEngine

logger = logging.getLogger(__name__)
router = APIRouter()


class ProcessRequest(BaseModel):
    """Request body for the processing endpoint."""
    video_path: str
    # Optional: skip LLM hook finding and use manual timestamps
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    # Optional: pre-computed transcript (skip re-transcription)
    transcript: Optional[dict] = None
    # LLM preference: "auto", "claude", "gpt"
    preferred_llm: str = "auto"


class ProcessResponse(BaseModel):
    """Response from the processing endpoint."""
    status: str
    output_path: str
    transcript: dict
    hook: dict
    message: str


@router.post("/process", response_model=ProcessResponse)
async def process_video(req: ProcessRequest):
    """
    Full pipeline orchestrator:
    1. Transcribe (if transcript not provided)
    2. Find hook (if start/end not provided)
    3. Crop to 9:16 vertical short
    4. Return result
    """
    # ── Validate input ───────────────────────────────────────
    if not os.path.exists(req.video_path):
        raise HTTPException(404, f"Video not found: {req.video_path}")

    # ── Step 1: Transcribe ───────────────────────────────────
    if req.transcript:
        transcript = req.transcript
        logger.info("Using provided transcript")
    else:
        logger.info("Step 1: Transcribing video...")
        try:
            transcript = await transcribe_video(req.video_path)
        except Exception as e:
            raise HTTPException(500, f"Transcription failed: {str(e)}")

    # ── Step 2: Find hook ────────────────────────────────────
    if req.start_time is not None and req.end_time is not None:
        hook = {
            "start_time": req.start_time,
            "end_time": req.end_time,
            "title": "Manual selection",
            "reason": "User-specified timestamps",
        }
        logger.info(f"Using manual timestamps: {req.start_time}s → {req.end_time}s")
    else:
        logger.info("Step 2: Finding best hook with LLM...")
        try:
            hook = await find_hook(transcript, preferred_llm=req.preferred_llm)
        except Exception as e:
            raise HTTPException(500, f"Hook finding failed: {str(e)}")

    # ── Step 3: Crop to vertical ─────────────────────────────
    logger.info("Step 3: Cropping to vertical short...")
    try:
        with CroppingEngine() as engine:
            output_path = engine.process_streaming(
                video_path=req.video_path,
                start_time=hook["start_time"],
                end_time=hook["end_time"],
            )
    except Exception as e:
        raise HTTPException(500, f"Video cropping failed: {str(e)}")

    return ProcessResponse(
        status="success",
        output_path=output_path,
        transcript=transcript,
        hook=hook,
        message=f"Generated vertical short: {hook['title']}",
    )
