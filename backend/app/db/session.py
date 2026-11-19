"""Sessão de banco de dados assíncrona."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from backend.app.core.config import get_settings


# Engine global (criado uma vez)
_engine = None
_session_factory = None


def get_engine():
    """Retorna ou cria engine assíncrono."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # SQLite não suporta connect_args com options; PostgreSQL sim
        is_sqlite = settings.DATABASE_URL.startswith("sqlite")
        connect_args = {} if is_sqlite else {"options": "-c timezone=UTC"}
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.is_development,
            poolclass=NullPool if settings.is_development else None,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retorna factory de sessões."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para FastAPI - fornece sessão de banco."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager para uso fora de requests (workers, scripts)."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Inicializa banco (criar tabelas se não existirem)."""
    # Em produção, usar Alembic migrations
    # Aqui apenas para desenvolvimento
    from backend.app.db.base import Base
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Fecha conexões do banco."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None