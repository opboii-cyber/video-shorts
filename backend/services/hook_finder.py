"""
hook_finder.py — LLM Hook Curation Service  (Step 2)
=====================================================

Analyses a timestamped transcript using an LLM (Claude 3.5 Sonnet
or GPT-4o) to identify the most engaging 30-60 second segment
that would make a viral short.

The LLM evaluates segments for:
  • Emotional hooks (surprise, humor, controversy)
  • Key insights or "aha moments"
  • High-energy delivery or debate
  • Self-contained narratives (makes sense without context)
"""

import json
import logging
import os
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, OPENAI_API_KEY


# ═════════════════════════════════════════════════════════════
# 1. PROMPT ENGINEERING
# ═════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a viral content expert who identifies the most engaging moments in long-form video transcripts. Your job is to find the single best 30-60 second continuous segment that would make a compelling vertical short (TikTok/Reels/Shorts).

CRITERIA for the best segment:
1. **Hook Power**: Opens with something attention-grabbing (a bold claim, question, surprising fact, or emotional moment)
2. **Self-Contained**: Makes sense without any prior context — a viewer scrolling should immediately understand and be hooked
3. **Emotional Resonance**: Contains humor, surprise, controversy, inspiration, or a key insight
4. **Clean Boundaries**: Starts and ends at natural speech boundaries (not mid-sentence)
5. **Engagement Potential**: Would make someone stop scrolling, watch to the end, and possibly share

RULES:
- The segment MUST be continuous (no gaps)
- Duration MUST be between 30 and 60 seconds
- Use the exact timestamps from the transcript
- Pick the start_time from the beginning of a segment and end_time from the end of a segment
- Provide a short catchy title for the clip (max 10 words)
- Explain briefly WHY this segment is the best hook"""

USER_PROMPT_TEMPLATE = """Here is the timestamped transcript. Each segment has a start time, end time, and text.

TRANSCRIPT:
{transcript_text}

Analyse this transcript and identify the SINGLE BEST 30-60 second continuous segment for a viral short.

Respond ONLY with valid JSON in this exact format:
{{
  "start_time": <float>,
  "end_time": <float>,
  "title": "<catchy title for the short>",
  "reason": "<1-2 sentences explaining why this is the best hook>"
}}"""


def _format_transcript_for_llm(transcript: Dict) -> str:
    """
    Format transcript segments into a readable string for the LLM.

    Format: [MM:SS - MM:SS] Text content here...
    """
    lines = []
    for seg in transcript.get("segments", []):
        start_m, start_s = divmod(seg["start"], 60)
        end_m, end_s = divmod(seg["end"], 60)
        lines.append(
            f"[{int(start_m):02d}:{start_s:05.2f} - {int(end_m):02d}:{end_s:05.2f}] "
            f"{seg['text']}"
        )
    return "\n".join(lines)


def _parse_llm_response(response_text: str) -> Dict:
    """
    Extract JSON from the LLM response, handling markdown code blocks
    and extra text that models sometimes include.
    """
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)

    # Try to find raw JSON object
    json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(0)

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}\nRaw: {response_text}")

    # Validate required fields
    required = ["start_time", "end_time", "title", "reason"]
    for field in required:
        if field not in result:
            raise ValueError(f"Missing required field '{field}' in LLM response")

    # Validate duration
    duration = result["end_time"] - result["start_time"]
    if duration < 15 or duration > 90:
        logger.warning(f"Hook duration {duration:.1f}s is outside 30-60s range, proceeding anyway")

    return result


# ═════════════════════════════════════════════════════════════
# 2. CLAUDE (Anthropic) — Primary LLM
# ═════════════════════════════════════════════════════════════

async def _find_hook_with_claude(transcript_text: str) -> Dict:
    """
    Use Claude 3.5 Sonnet to find the best hook segment.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ImportError("anthropic package required: pip install anthropic")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    logger.info("Sending transcript to Claude 3.5 Sonnet...")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(transcript_text=transcript_text),
            }
        ],
    )

    response_text = message.content[0].text
    logger.info(f"Claude response: {response_text[:200]}...")

    return _parse_llm_response(response_text)


# ═════════════════════════════════════════════════════════════
# 3. GPT-4o (OpenAI) — Fallback LLM
# ═════════════════════════════════════════════════════════════

async def _find_hook_with_gpt(transcript_text: str) -> Dict:
    """
    Use GPT-4o to find the best hook segment.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required: pip install openai")

    client = OpenAI(api_key=OPENAI_API_KEY)

    logger.info("Sending transcript to GPT-4o...")

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        temperature=0.3,  # low temp for consistent JSON output
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(transcript_text=transcript_text),
            },
        ],
        response_format={"type": "json_object"},  # force JSON mode
    )

    response_text = response.choices[0].message.content
    logger.info(f"GPT-4o response: {response_text[:200]}...")

    return _parse_llm_response(response_text)


# ═════════════════════════════════════════════════════════════
# 4. PUBLIC API
# ═════════════════════════════════════════════════════════════

async def find_hook(
    transcript: Dict,
    preferred_llm: str = "auto",
) -> Dict:
    """
    Analyse a transcript and find the most engaging 30-60s segment.

    Auto-selects LLM based on available API keys:
      1. Claude (if ANTHROPIC_API_KEY is set)
      2. GPT-4o (if OPENAI_API_KEY is set)

    Args:
        transcript:    Whisper output with "segments" list.
        preferred_llm: "claude", "gpt", or "auto" (default).

    Returns:
        dict with:
          - start_time (float): Clip start in seconds
          - end_time (float):   Clip end in seconds
          - title (str):        Catchy title for the short
          - reason (str):       Why this segment was chosen
    """
    transcript_text = _format_transcript_for_llm(transcript)

    if not transcript_text.strip():
        raise ValueError("Transcript is empty — cannot find hook")

    logger.info(f"Finding hook in transcript ({len(transcript.get('segments', []))} segments)")

    # Auto-select LLM
    if preferred_llm == "auto":
        if ANTHROPIC_API_KEY:
            preferred_llm = "claude"
        elif OPENAI_API_KEY:
            preferred_llm = "gpt"
        else:
            raise ValueError(
                "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
            )

    # Call the selected LLM
    if preferred_llm == "claude":
        result = await _find_hook_with_claude(transcript_text)
    elif preferred_llm == "gpt":
        result = await _find_hook_with_gpt(transcript_text)
    else:
        raise ValueError(f"Unknown LLM: {preferred_llm}")

    logger.info(
        f"Hook found: {result['start_time']:.1f}s → {result['end_time']:.1f}s "
        f"({result['end_time'] - result['start_time']:.1f}s) — \"{result['title']}\""
    )

    return result
