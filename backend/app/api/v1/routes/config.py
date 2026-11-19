"""Rota de configuração pública (sem segredos)."""

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.schemas.base import BaseSchema

router = APIRouter(prefix="/config", tags=["config"])


class PublicConfigResponse(BaseSchema):
    """Configurações públicas não sensíveis."""
    app_env: str
    app_timezone: str
    app_host: str
    app_port: int
    candidate_limit_per_day: int
    max_regenerations_per_candidate: int
    auto_publish: bool
    tiktok_direct_post_enabled: bool
    local_video_diffusion_enabled: bool
    paid_providers_enabled: bool
    external_billing_enabled: bool
    llm_provider: str
    image_provider: str
    speech_provider: str
    youtube_enabled: bool
    rss_enabled: bool
    telegram_enabled: bool
    tiktok_publish_mode: str


@router.get("", response_model=PublicConfigResponse)
async def get_public_config() -> PublicConfigResponse:
    """Retorna configurações públicas (sem segredos)."""
    settings = get_settings()
    return PublicConfigResponse(
        app_env=settings.APP_ENV,
        app_timezone=settings.APP_TIMEZONE,
        app_host=settings.APP_HOST,
        app_port=settings.APP_PORT,
        candidate_limit_per_day=settings.APP_CANDIDATE_LIMIT_PER_DAY,
        max_regenerations_per_candidate=settings.APP_MAX_REGENERATIONS_PER_CANDIDATE,
        auto_publish=settings.APP_AUTO_PUBLISH,
        tiktok_direct_post_enabled=settings.APP_TIKTOK_DIRECT_POST_ENABLED,
        local_video_diffusion_enabled=settings.APP_LOCAL_VIDEO_DIFFUSION_ENABLED,
        paid_providers_enabled=settings.APP_ALLOW_PAID_PROVIDERS,
        external_billing_enabled=settings.APP_EXTERNAL_BILLING_ENABLED,
        llm_provider=settings.LLM_PROVIDER,
        image_provider=settings.IMAGE_PROVIDER,
        speech_provider=settings.SPEECH_PROVIDER,
        youtube_enabled=settings.YOUTUBE_ENABLED,
        rss_enabled=settings.RSS_ENABLED,
        telegram_enabled=settings.TELEGRAM_ENABLED,
        tiktok_publish_mode=settings.TIKTOK_PUBLISH_MODE,
    )