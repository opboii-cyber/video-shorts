"""
jobs.py — Job Status Router  (Phase 4)
========================================

Handles:
  POST /api/jobs         — create a new processing job
  GET  /api/jobs         — list user's jobs
  GET  /api/jobs/{id}    — get specific job status
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models import Job, User, JobStatus
from middleware.auth_middleware import get_current_user, CurrentUser
from routers.payments import get_or_create_user

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateJobRequest(BaseModel):
    video_path: str
    source_type: str = "upload"
    youtube_url: Optional[str] = None


@router.post("/jobs")
async def create_job(
    req: CreateJobRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new video processing job and queue it.
    Checks credits before accepting.
    """
    db_user = get_or_create_user(db, user)

    # Check credits
    if db_user.credits_remaining <= 0:
        raise HTTPException(
            402,
            "No credits remaining. Please upgrade your plan.",
        )

    if not os.path.exists(req.video_path):
        raise HTTPException(404, f"Video not found: {req.video_path}")

    # Create job record
    job = Job(
        user_id=db_user.id,
        input_path=req.video_path,
        source_type=req.source_type,
        youtube_url=req.youtube_url,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch to Celery worker
    try:
        from services.tasks import process_video_task
        process_video_task.delay(job.id)
        logger.info(f"Job queued: {job.id}")
    except Exception as e:
        # If Celery/Redis not available, log warning
        logger.warning(f"Could not queue job (Celery unavailable): {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = "Queue unavailable. Try using /api/process instead."
        db.commit()

    return {
        "job_id": job.id,
        "status": job.status,
        "message": "Job created and queued for processing",
    }


@router.get("/jobs")
async def list_jobs(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    per_page: int = 20,
):
    """List all jobs for the authenticated user."""
    db_user = get_or_create_user(db, user)

    offset = (page - 1) * per_page
    jobs = (
        db.query(Job)
        .filter(Job.user_id == db_user.id)
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    total = db.query(Job).filter(Job.user_id == db_user.id).count()

    return {
        "jobs": [
            {
                "id": j.id,
                "status": j.status,
                "progress": j.progress,
                "title": j.hook_title or "Processing...",
                "output_path": j.output_path,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "duration": j.duration_seconds,
                "error": j.error_message,
            }
            for j in jobs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the status of a specific job."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user.id,
    ).first()

    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "id": job.id,
        "status": job.status,
        "progress": job.progress,
        "title": job.hook_title,
        "input_path": job.input_path,
        "output_path": job.output_path,
        "transcript": job.transcript_json,
        "hook": job.hook_json,
        "error": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "duration": job.duration_seconds,
    }
