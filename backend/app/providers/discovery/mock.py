"""Provedor de descoberta mock para testes determinísticos."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.app.providers.discovery.base import DiscoveryProvider, DiscoveryResult
from backend.app.schemas.trends import TrendCandidateV1, TrendSource

logger = logging.getLogger(__name__)


class MockDiscoveryProvider(DiscoveryProvider):
    """Provedor mock que retorna trends fixos para testes."""

    def __init__(self, trends: list[TrendCandidateV1] | None = None, should_fail: bool = False):
        self._trends = trends or self._default_trends()
        self._should_fail = should_fail
        self._call_count = 0

    @property
    def source(self) -> TrendSource:
        return TrendSource.MANUAL  # Mock usa source manual

    @property
    def cost_class(self) -> str:
        return "zero"

    def _default_trends(self) -> list[TrendCandidateV1]:
        """Retorna trends padrão para testes."""
        now = datetime.now(timezone.utc)
        return [
            self.normalize_trend(
                external_id="mock-trend-1",
                title="Inteligência Artificial Generativa Avança em 2026",
                url="https://example.com/ia-generativa-2026",
                published_at=now,
                metrics={"views": 250000, "likes": 18000, "comments": 1200, "shares": 300},
                language="pt",
                category="tecnologia",
                raw_data={"fixture": True, "mock": True},
            ),
            self.normalize_trend(
                external_id="mock-trend-2",
                title="Nova Descoberta em Computação Quântica",
                url="https://example.com/quantum-2026",
                published_at=now,
                metrics={"views": 180000, "likes": 12000, "comments": 800, "shares": 200},
                language="pt",
                category="ciencia",
                raw_data={"fixture": True, "mock": True},
            ),
            self.normalize_trend(
                external_id="mock-trend-3",
                title="Tendências de Saúde: Medicina Personalizada",
                url="https://example.com/saude-personalizada-2026",
                published_at=now,
                metrics={"views": 95000, "likes": 6000, "comments": 450, "shares": 150},
                language="pt",
                category="saude",
                raw_data={"fixture": True, "mock": True},
            ),
        ]

    async def fetch_trends(self, *, since: datetime | None = None, limit: int = 50) -> DiscoveryResult:
        """Retorna trends mock fixos."""
        self._call_count += 1

        if self._should_fail:
            return DiscoveryResult(
                trends=[],
                errors=["Mock configured to fail"],
                duration_ms=1,
                source_calls={"mock": self._call_count},
            )

        filtered = self._trends
        if since:
            filtered = [t for t in filtered if t.published_at is None or t.published_at >= since]

        return DiscoveryResult(
            trends=filtered[:limit],
            errors=[],
            duration_ms=1,
            source_calls={"mock": self._call_count},
        )

    async def health_check(self) -> bool:
        return not self._should_fail

    def set_trends(self, trends: list[TrendCandidateV1]) -> None:
        """Define trends customizados para o teste."""
        self._trends = trends

    def set_should_fail(self, should_fail: bool) -> None:
        """Configura se deve falhar."""
        self._should_fail = should_fail

    def get_call_count(self) -> int:
        return self._call_count