#!/usr/bin/env python
"""Celery beat scheduler startup script for periodic tasks."""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.celery_tasks import app as celery_app

if __name__ == "__main__":
    # Start beat scheduler
    celery_app.start([
        "beat",
        "--loglevel=info",
        "--scheduler=celery.beat:PersistentScheduler",  # Persist schedule to disk
    ])
