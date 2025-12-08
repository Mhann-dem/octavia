import os
from celery import Celery

redis_url = os.environ.get("REDIS_BROKER_URL", "redis://redis:6379/0")

celery_app = Celery(
    "octavia",
    broker=redis_url,
    backend=os.environ.get("CELERY_RESULT_BACKEND", redis_url),
)

# Basic recommended configuration; override via environment variables as needed
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks from the app package
celery_app.autodiscover_tasks(["app"], force=True)

if __name__ == "__main__":
    print("Celery app configured. Run workers with: celery -A app.celery_app.celery_app worker --loglevel=info")
