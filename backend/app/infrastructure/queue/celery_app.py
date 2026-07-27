"""Celery application factory.

Started via `celery -A app.infrastructure.queue.celery_app worker` /
`... beat` (see docker-compose.yml). Task modules register themselves
under `app/infrastructure/queue/tasks/` and are discovered via
`autodiscover_tasks` below — no tasks are defined yet.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "drassist",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
)

celery_app.conf.update(
    task_always_eager=settings.celery.task_always_eager,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=settings.timezone,
    enable_utc=True,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
)

celery_app.autodiscover_tasks(["app.infrastructure.queue.tasks"])
