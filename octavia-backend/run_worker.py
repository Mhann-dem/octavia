#!/usr/bin/env python
"""Celery worker startup script."""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.celery_tasks import app as celery_app

if __name__ == "__main__":
    # Start worker with concurrency settings
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=4",  # Number of worker processes
        "--queues=urgent,default,low",  # Listen to all queues
        "--time-limit=1800",  # 30 minute hard limit per task
        "--soft-time-limit=1500",  # 25 minute soft limit
        "--max-tasks-per-child=1000",  # Restart worker after 1000 tasks
    ])
