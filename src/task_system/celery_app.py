"""Celery application configuration."""
from celery import Celery
from src.core.config import settings

# Create Celery app
celery_app = Celery(
    "account_automation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.task_system.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # 24 hours
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "test-proxies-every-hour": {
        "task": "src.task_system.tasks.test_all_proxies_task",
        "schedule": 3600.0,  # Every hour
    },
}
