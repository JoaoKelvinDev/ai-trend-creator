"""Rotas de health check."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from backend.app.core.config import get_settings
from backend.app.db.session import get_db_session
from backend.app.db.redis import get_redis
from backend.app.schemas.base import HealthResponse, ReadyResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def liveness_check() -> HealthResponse:
    """
    Liveness probe - verifica se o processo está vivo.
    Não verifica dependências externas.
    """
    settings = get_settings()
    return HealthResponse(
        status="alive",
        service="ai-trend-creator",
        version="0.1.0",
        checks={"process": True},
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> ReadyResponse:
    """
    Readiness probe - verifica se o serviço está pronto para receber tráfego.
    Verifica banco de dados, Redis e provedores essenciais.
    """
    settings = get_settings()
    checks = {}
    dependencies = {}

    # Verificar PostgreSQL
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        checks["database"] = True
        dependencies["database"] = "connected"
    except Exception as e:
        checks["database"] = False
        dependencies["database"] = f"error: {type(e).__name__}: {e}"

    # Verificar Redis
    try:
        await redis.ping()
        checks["redis"] = True
        dependencies["redis"] = "connected"
    except Exception as e:
        checks["redis"] = False
        dependencies["redis"] = f"error: {type(e).__name__}"

    # Verificar storage local
    try:
        storage_root = settings.LOCAL_STORAGE_ROOT
        storage_root.mkdir(parents=True, exist_ok=True)
        test_file = storage_root / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()
        checks["storage"] = True
        dependencies["storage"] = "writable"
    except Exception as e:
        checks["storage"] = False
        dependencies["storage"] = f"error: {type(e).__name__}"

    all_healthy = all(checks.values())
    status = "ready" if all_healthy else "not_ready"

    return ReadyResponse(
        status=status,
        service="ai-trend-creator",
        version="0.1.0",
        checks=checks,
        dependencies=dependencies,
    )