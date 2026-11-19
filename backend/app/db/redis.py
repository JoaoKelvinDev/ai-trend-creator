"""Conexão Redis assíncrona."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from redis.asyncio import Redis, ConnectionPool

from backend.app.core.config import get_settings


_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


def get_redis_pool() -> ConnectionPool:
    """Retorna ou cria pool de conexões Redis."""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


def get_redis_client() -> Redis:
    """Retorna cliente Redis."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(connection_pool=get_redis_pool())
    return _redis_client


async def get_redis() -> Redis:
    """Dependency para FastAPI - fornece cliente Redis."""
    return get_redis_client()


@asynccontextmanager
async def get_redis_context() -> AsyncGenerator[Redis, None]:
    """Context manager para uso fora de requests."""
    client = get_redis_client()
    try:
        yield client
    finally:
        pass  # Pool gerencia conexões


async def init_redis() -> None:
    """Testa conexão Redis."""
    client = get_redis_client()
    await client.ping()


async def close_redis() -> None:
    """Fecha conexões Redis."""
    global _redis_pool, _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None