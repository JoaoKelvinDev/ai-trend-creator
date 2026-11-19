"""Workers package."""

from backend.app.workers.celery_app import celery_app
from backend.app.workers.tasks import (
    discovery_task,
    scoring_task,
    scripting_task,
    storyboarding_task,
    asset_generation_task,
    rendering_task,
    quality_check_task,
    telegram_notify_task,
    export_task,
    daily_discovery_task,
    cleanup_old_assets_task,
)

__all__ = [
    "celery_app",
    "discovery_task",
    "scoring_task",
    "scripting_task",
    "storyboarding_task",
    "asset_generation_task",
    "rendering_task",
    "quality_check_task",
    "telegram_notify_task",
    "export_task",
    "daily_discovery_task",
    "cleanup_old_assets_task",
]