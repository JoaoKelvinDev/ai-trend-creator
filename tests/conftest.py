"""Configuração global de testes (pytest)."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.core.config import get_settings, Settings
from backend.app.db.base import Base
from backend.app.db.session import get_db_session
from backend.app.db.redis import get_redis
from backend.app.main import create_app


# ──────────────────────────────────────────────
# Settings de teste
# ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Configurações para testes (usar SQLite em memória)."""
    return Settings(
        APP_ENV="testing",
        APP_TIMEZONE="UTC",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/1",  # Será mockado
        LOCAL_STORAGE_ROOT="./test_data",
        APP_CANDIDATE_LIMIT_PER_DAY=2,
        APP_MAX_REGENERATIONS_PER_CANDIDATE=2,
        APP_ALLOW_PAID_PROVIDERS=False,
        APP_EXTERNAL_BILLING_ENABLED=False,
        APP_TIKTOK_DIRECT_POST_ENABLED=False,
        APP_LOCAL_VIDEO_DIFFUSION_ENABLED=False,
        LLM_PROVIDER="mock",
        IMAGE_PROVIDER="mock",
        SPEECH_PROVIDER="mock",
        YOUTUBE_ENABLED=False,
        RSS_ENABLED=False,
        TELEGRAM_ENABLED=False,
        LOG_LEVEL="DEBUG",
    )


# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Event loop para testes assíncronos."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine(test_settings: Settings):
    """Engine de teste (SQLite em memória)."""
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco para cada teste."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


# ──────────────────────────────────────────────
# App e Client
# ──────────────────────────────────────────────

@pytest.fixture(scope="function")
def app(test_settings: Settings, db_session: AsyncSession):
    """App FastAPI com overrides de dependências."""
    app = create_app()

    # Override get_db_session
    async def override_get_db():
        yield db_session

    # Override get_redis (mock)
    class MockRedis:
        async def ping(self): return True
        async def get(self, key): return None
        async def set(self, key, value, ex=None): return True
        async def delete(self, *keys): return True
        async def exists(self, key): return False

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis] = lambda: MockRedis()

    yield app

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(app) -> TestClient:
    """TestClient síncrono."""
    return TestClient(app)


@pytest.fixture(scope="function")
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient para testes assíncronos."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ──────────────────────────────────────────────
# Fixtures de dados
# ──────────────────────────────────────────────

@pytest.fixture
def sample_trend_candidate():
    """Fixture de TrendCandidateV1 para testes."""
    from backend.app.schemas.trends import TrendCandidateV1, TrendMetrics
    from backend.app.domain.enums import TrendSource, TrendLanguage, NicheCategory
    from datetime import datetime, timezone

    return TrendCandidateV1(
        trace_id=uuid4(),
        trend_id=uuid4(),
        source=TrendSource.RSS,
        external_id="test-123",
        title="Tendência de teste",
        url="https://example.com/video",
        observed_at=datetime.now(timezone.utc),
        published_at=datetime.now(timezone.utc),
        metrics=TrendMetrics(views=10000, likes=500),
        missing_metrics=["comments", "shares"],
        language=TrendLanguage.PT,
        category=NicheCategory.TECNOLOGIA,
    )


@pytest.fixture
def sample_trend_signals():
    """Fixture de TrendSignals para testes."""
    from backend.app.schemas.trends import TrendSignals

    return TrendSignals(
        growth=80.0,
        niche_fit=90.0,
        engagement=70.0,
        recency=85.0,
        production_feasibility=95.0,
    )