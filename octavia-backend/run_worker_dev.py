#!/usr/bin/env python
"""
Start Celery worker with in-memory broker for local development.
This allows testing async job processing without a real Redis server.
"""
import os
import sys

# Set environment variables for in-memory broker
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"

from app.celery_tasks import app

if __name__ == "__main__":
    print("Starting Celery worker with in-memory broker (development mode)...")
    print("Note: This is for local testing only. Use Redis for production.")
    print()
    
    # Start worker
    app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--time-limit=1800',  # 30 minutes
        '--soft-time-limit=1500',  # 25 minutes
    ])
