"""
Celery Application Configuration.

This module initializes the Celery application used for background processing
(e.g., PDF extraction and AI validation).
"""

from __future__ import annotations

import os
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rrb_alp_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configure Celery for JSON serialization and UTC timezone
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_cancel_long_running_tasks_on_connection_loss=True,
)

# Auto-discover tasks in all installed apps
celery_app.autodiscover_tasks(["app.pdf"])
