"""Testes para rotas de health check."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Testes para /health/live e /health/ready."""

    @pytest.mark.asyncio
    async def test_liveness_check(self, async_client: AsyncClient):
        """GET /health/live deve retornar status alive."""
        response = await async_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "ai-trend-creator"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_readiness_check(self, async_client: AsyncClient):
        """GET /health/ready deve verificar dependências."""
        response = await async_client.get("/health/ready")
        # Em testes, DB e Redis são mockados, então deve retornar ready
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ready", "not_ready")
        assert "checks" in data
        assert "dependencies" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
        assert "storage" in data["checks"]


class TestConfigEndpoint:
    """Testes para /api/v1/config."""

    @pytest.mark.asyncio
    async def test_get_public_config(self, async_client: AsyncClient):
        """GET /api/v1/config deve retornar configurações públicas."""
        response = await async_client.get("/api/v1/config")
        assert response.status_code == 200
        data = response.json()
        # Verificar campos obrigatórios
        assert "app_env" in data
        assert "app_timezone" in data
        assert "candidate_limit_per_day" in data
        assert "llm_provider" in data
        assert "image_provider" in data
        assert "speech_provider" in data
        # Não deve expor segredos
        assert "YOUTUBE_API_KEY" not in str(data)
        assert "TELEGRAM_BOT_TOKEN" not in str(data)


class TestRootEndpoint:
    """Teste para endpoint raiz."""

    @pytest.mark.asyncio
    async def test_root(self, async_client: AsyncClient):
        """GET / deve retornar info básica."""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ai-trend-creator"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])