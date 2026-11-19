"""Tasks do Celery para execução assíncrona do pipeline."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from backend.app.workers.celery_app import celery_app
from backend.app.providers.factory import get_provider_factory
from backend.app.workflows.orchestrator import workflow_orchestrator
from backend.app.db.session import get_db_session
from backend.app.db.models import VideoProject, Job, ContentCandidate, DailyQuota
from backend.app.domain.policies.states import VideoState
from backend.app.domain.policies.quotas import quota_policy, timezone_policy, DailyQuotaUsage

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def discovery_task(self, project_id: str | None = None, **kwargs) -> dict[str, Any]:
    """Task: Descoberta de tendências."""
    from backend.app.application.use_cases import run_discovery_use_case

    try:
        result = run_discovery_use_case()
        return {"success": True, "trends_found": result.trends_found}
    except Exception as e:
        logger.exception("Discovery task falhou")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scoring_task(self, project_id: str, **kwargs) -> dict[str, Any]:
    """Task: Scoring e seleção de candidatos."""
    from backend.app.application.use_cases import score_trends_use_case

    try:
        result = score_trends_use_case(UUID(project_id))
        return {"success": True, "candidates_created": result.candidates_created}
    except Exception as e:
        logger.exception("Scoring task falhou")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scripting_task(self, project_id: str, **kwargs) -> dict[str, Any]:
    """Task: Geração de roteiro com LLM."""
    from backend.app.application.use_cases import generate_script_use_case

    try:
        result = generate_script_use_case(UUID(project_id))
        return {"success": True, "script_id": str(result.script_id)}
    except Exception as e:
        logger.exception("Scripting task falhou")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def storyboarding_task(self, project_id: str, **kwargs) -> dict[str, Any]:
    """Task: Criação de storyboard."""
    from backend.app.application.use_cases import create_storyboard_use_case

    try:
        result = create_storyboard_use_case(UUID(project_id))
        return {"success": True, "scenes_count": result.scenes_count}
    except Exception as e:
        logger.exception("Storyboarding task falhou")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def asset_generation_task(self, project_id: str, **kwargs) -> dict[str, Any]:
    """Task: Geração de assets (imagens, áudio)."""
    from backend.app.application.use_cases import generate_assets_use_case

    try:
        result = generate_assets_use_case(UUID(project_id))
        return {"success": True, "assets_generated": result.assets_count}
    except Exception as e:
        logger.exception("Asset generation task falhou")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=180)
def rendering_task(self, project_id: str, **kwargs) -> dict[str, Any]:
    """Task: Renderização do vídeo final."""
    from backend.app.application.use_cases import render_video_use_case

    try:
        result = render_video_use_case(UUID(project_id))
        return {"success": True, "video_path": str(result.video_path)}
    except Exception as e:
        logger.exception("Rendering task falhou")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def quality_check_task(self, project_id: str, **kwargs) -> dict[str, Any]:
    """Task: Verificação de qualidade do vídeo."""
    from backend.app.application.use_cases import quality_check_use_case

    try:
        result = quality_check_use_case(UUID(project_id))
        return {"success": result.passed, "issues": result.issues}
    except Exception as e:
        logger.exception("Quality check task falhou")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def telegram_notify_task(self, project_id: str, **kwargs) -> dict[str, Any]:
    """Task: Enviar para aprovação no Telegram."""
    from backend.app.application.use_cases import request_approval_use_case

    try:
        result = request_approval_use_case(UUID(project_id))
        return {"success": True, "approval_id": str(result.approval_id)}
    except Exception as e:
        logger.exception("Telegram notify task falhou")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def export_task(self, project_id: str, **kwargs) -> dict[str, Any]:
    """Task: Exportar pacote para publicação assistida."""
    from backend.app.application.use_cases import export_package_use_case

    try:
        result = export_package_use_case(UUID(project_id))
        return {"success": True, "export_path": str(result.export_path)}
    except Exception as e:
        logger.exception("Export task falhou")
        raise self.retry(exc=e)


# ──────────────────────────────────────────────
# Tasks Agendadas (Beat)
# ──────────────────────────────────────────────

@celery_app.task(bind=True)
def daily_discovery_task(self) -> dict[str, Any]:
    """Task diária: executar descoberta e iniciar pipeline para até 2 candidatos."""
    from backend.app.application.use_cases import run_daily_pipeline_use_case

    try:
        result = run_daily_pipeline_use_case()
        return {"success": True, "candidates_processed": result.candidates_processed}
    except Exception as e:
        logger.exception("Daily pipeline task falhou")
        return {"success": False, "error": str(e)}


@celery_app.task(bind=True)
def cleanup_old_assets_task(self) -> dict[str, Any]:
    """Task de limpeza: remover assets de projetos rejeitados antigos."""
    from backend.app.application.use_cases import cleanup_assets_use_case

    try:
        result = cleanup_assets_use_case()
        return {"success": True, "cleaned_count": result.cleaned_count}
    except Exception as e:
        logger.exception("Cleanup task falhou")
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────
# Helpers para uso direto (sem Celery)
# ──────────────────────────────────────────────

async def run_discovery_async() -> dict[str, Any]:
    """Executa descoberta de forma assíncrona (para uso em CLI/API)."""
    from backend.app.application.use_cases import run_discovery_use_case
    return run_discovery_use_case()


async def run_scoring_async(project_id: UUID) -> dict[str, Any]:
    """Executa scoring de forma assíncrona."""
    from backend.app.application.use_cases import score_trends_use_case
    return score_trends_use_case(project_id)


async def run_full_pipeline_async(project_id: UUID) -> list[dict[str, Any]]:
    """Executa pipeline completo para um projeto."""
    states = [
        VideoState.SCRIPTED,
        VideoState.STORYBOARDED,
        VideoState.GENERATING_ASSETS,
        VideoState.RENDERING,
        VideoState.QUALITY_CHECK,
        VideoState.PENDING_APPROVAL,
    ]

    results = []
    for state in states:
        result = await workflow_orchestrator.execute_step(project_id, state)
        results.append({
            "state": state.value,
            "success": result.success,
            "error": result.error,
        })
        if not result.success:
            break

    return results