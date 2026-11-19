"""Dependências comuns da API v1."""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from backend.app.db.session import get_db_session
from backend.app.db.redis import get_redis
from backend.app.core.config import get_settings


async def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> int:
    """
    Extrai user_id do header (para desenvolvimento/local).
    Em produção, validar JWT ou session.
    """
    if x_user_id is None:
        # Desenvolvimento: usar ID fixo
        return 123456789
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID inválido",
        )


async def verify_telegram_secret(
    x_telegram_secret: str | None = Header(default=None, alias="X-Telegram-Secret"),
) -> bool:
    """Verifica secret do webhook Telegram."""
    settings = get_settings()
    if not settings.TELEGRAM_ENABLED:
        return True  # Skip se não habilitado
    if not settings.TELEGRAM_BOT_TOKEN:
        return True
    # TODO: Implementar verificação real do secret
    return True


# Re-exportar dependências de banco
__all__ = [
    "get_db_session",
    "get_redis",
    "get_current_user_id",
    "verify_telegram_secret",
]