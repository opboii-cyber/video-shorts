"""
celery_app.py — Celery Configuration
======================================

Configures Celery with Redis as broker for async video processing.

Usage:
    # Start worker:
    celery -A celery_app worker --loglevel=info

    # Start with concurrency limit (CPU-bound):
    celery -A celery_app worker --loglevel=info --concurrency=2
"""

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery instance
celery_app = Celery(
    "video_shorts",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["services.tasks"],
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task settings
    task_track_started=True,          # report when task starts
    task_time_limit=600,              # hard kill after 10 min
    task_soft_time_limit=540,         # soft limit at 9 min
    worker_max_tasks_per_child=10,    # restart worker after 10 tasks (memory leak prevention)
    worker_prefetch_multiplier=1,     # don't prefetch (tasks are heavy)

    # Result backend
    result_expires=3600,              # results expire after 1 hour
)
