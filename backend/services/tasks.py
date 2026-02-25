"""
tasks.py — Celery Async Tasks
================================

Wraps the video processing pipeline as a Celery task for
background / queue-based execution.

Usage from API:
    from services.tasks import process_video_task
    result = process_video_task.delay(job_id)
"""

import logging
from datetime import datetime, timezone

from celery_app import celery_app
from database import SessionLocal
from models import Job, User, JobStatus

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def process_video_task(self, job_id: str):
    """
    Celery task: run the full video processing pipeline.

    Updates the Job record at each stage so the frontend
    can display real-time progress.

    Args:
        job_id: The Job.id to process.
    """
    db = SessionLocal()

    try:
        # ── Load the job ─────────────────────────────────────
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job not found: {job_id}")
            return {"error": "Job not found"}

        job.status = JobStatus.TRANSCRIBING.value
        job.started_at = datetime.now(timezone.utc)
        job.progress = 10
        db.commit()

        # ── Step 1: Transcribe ───────────────────────────────
        logger.info(f"[{job_id}] Step 1: Transcribing...")
        import asyncio
        from services.transcription import transcribe_video

        transcript = asyncio.get_event_loop().run_until_complete(
            transcribe_video(job.input_path)
        )
        job.transcript_json = transcript
        job.progress = 30
        db.commit()

        # ── Step 2: Find hook ────────────────────────────────
        job.status = JobStatus.FINDING_HOOK.value
        job.progress = 40
        db.commit()

        logger.info(f"[{job_id}] Step 2: Finding hook...")
        from services.hook_finder import find_hook

        hook = asyncio.get_event_loop().run_until_complete(
            find_hook(transcript)
        )
        job.hook_json = hook
        job.hook_title = hook.get("title", "Untitled")
        job.progress = 50
        db.commit()

        # ── Step 3: Crop to vertical ────────────────────────
        job.status = JobStatus.CROPPING.value
        job.progress = 60
        db.commit()

        logger.info(f"[{job_id}] Step 3: Cropping...")
        from services.cropping_engine import CroppingEngine

        with CroppingEngine() as engine:
            output_path = engine.process_streaming(
                video_path=job.input_path,
                start_time=hook["start_time"],
                end_time=hook["end_time"],
            )

        # ── Step 4: Finalize ─────────────────────────────────
        job.status = JobStatus.COMPLETED.value
        job.output_path = output_path
        job.progress = 100
        job.completed_at = datetime.now(timezone.utc)
        job.duration_seconds = hook["end_time"] - hook["start_time"]

        # Deduct credits
        user = db.query(User).filter(User.id == job.user_id).first()
        if user and user.credits_remaining > 0:
            user.credits_remaining -= 1

        db.commit()

        logger.info(f"[{job_id}] ✓ Completed: {output_path}")
        return {"status": "completed", "output_path": output_path}

    except Exception as e:
        logger.error(f"[{job_id}] Failed: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.progress = 0
        db.commit()

        # Retry on transient failures
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {"status": "failed", "error": str(e)}

    finally:
        db.close()
