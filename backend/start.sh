#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Production Entrypoint Script
# ═══════════════════════════════════════════════════════════════
# Usage: ./start.sh [web|worker]

ROLE=$1

if [ "$ROLE" = "web" ]; then
    echo "Starting FastAPI Web Server..."
    # Apply Alembic migrations here in the future if needed
    # python -m alembic upgrade head
    
    # Start Uvicorn
    exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

elif [ "$ROLE" = "worker" ]; then
    echo "Starting Celery Video Processing Worker..."
    # Start Celery
    exec celery -A celery_app worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-2}

else
    echo "Error: Unknown role '$ROLE'"
    echo "Usage: ./start.sh [web|worker]"
    exit 1
fi
