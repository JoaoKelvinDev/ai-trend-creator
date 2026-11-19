"""Configuração do Celery para workers assíncronos."""

from celery import Celery
from backend.app.core.config import get_settings

settings = get_settings()

# Criar app Celery
celery_app = Celery(
    "ai_trend_creator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "backend.app.workers.tasks",
    ],
)

# Configurações
celery_app.conf.update(
    # Serialização
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone=settings.APP_TIMEZONE,
    enable_utc=True,

    # Task routing
    task_routes={
        "backend.app.workers.tasks.discovery_task": {"queue": "discovery"},
        "backend.app.workers.tasks.scoring_task": {"queue": "scoring"},
        "backend.app.workers.tasks.scripting_task": {"queue": "scripting"},
        "backend.app.workers.tasks.storyboarding_task": {"queue": "storyboarding"},
        "backend.app.workers.tasks.asset_generation_task": {"queue": "assets"},
        "backend.app.workers.tasks.rendering_task": {"queue": "rendering"},
        "backend.app.workers.tasks.quality_check_task": {"queue": "quality"},
        "backend.app.workers.tasks.telegram_notify_task": {"queue": "notifications"},
        "backend.app.workers.tasks.export_task": {"queue": "export"},
    },

    # Worker config
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result backend
    result_expires=86400,  # 24h
    result_compression="gzip",

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Beat schedule (scheduler)
    beat_schedule={
        # Descoberta diária às 6h no fuso local
        "daily-discovery": {
            "task": "backend.app.workers.tasks.daily_discovery_task",
            "schedule": 86400.0,  # 24h - ajustado pelo scheduler real
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["backend.app.workers"])


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task de debug."""
    print(f"Request: {self.request!r}")


if __name__ == "__main__":
    celery_app.start()