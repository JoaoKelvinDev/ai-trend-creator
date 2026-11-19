"""Interface base para provedores de descoberta de tendências."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from backend.app.schemas.trends import TrendCandidateV1, TrendSource


@dataclass(frozen=True)
class DiscoveryResult:
    """Resultado de uma execução de descoberta."""
    trends: list[TrendCandidateV1]
    errors: list[str]
    duration_ms: int
    source_calls: dict[str, int]


class DiscoveryProvider(ABC):
    """Interface para provedores de descoberta (YouTube, RSS, Manual, Mock)."""

    @property
    @abstractmethod
    def source(self) -> TrendSource:
        """Identificador da fonte (youtube, rss, manual)."""
        pass

    @property
    @abstractmethod
    def cost_class(self) -> str:
        """Classe de custo: 'zero' | 'paid'. Usado para bloqueio R$ 0."""
        pass

    @abstractmethod
    async def fetch_trends(self, *, since: datetime | None = None, limit: int = 50) -> DiscoveryResult:
        """
        Busca tendências da fonte.

        Args:
            since: Buscar apenas itens mais recentes que este timestamp
            limit: Máximo de itens a retornar

        Returns:
            DiscoveryResult com trends, erros, duração e contagem de chamadas
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se o provedor está saudável e acessível."""
        pass

    def normalize_trend(
        self,
        *,
        external_id: str,
        title: str,
        url: str,
        published_at: datetime | None,
        metrics: dict[str, Any] | None = None,
        language: str = "pt",
        category: str | None = None,
        raw_data: dict[str, Any] | None = None,
    ) -> TrendCandidateV1:
        """Helper para normalizar trend item em TrendCandidateV1."""
        from uuid import uuid4
        import hashlib

        metrics_obj = metrics or {}
        missing = []
        for key in ("views", "likes", "comments", "shares"):
            if key not in metrics_obj or metrics_obj[key] is None:
                missing.append(key)

        # Gerar canonical_key para deduplicação: hash da fonte + external_id
        canonical_key = hashlib.sha256(f"{self.source.value}:{external_id}".encode()).hexdigest()[:32]

        return TrendCandidateV1(
            trace_id=uuid4(),
            trend_id=uuid4(),
            source=self.source,
            external_id=external_id,
            title=title[:500],
            url=url,
            observed_at=datetime.now(),
            published_at=published_at,
            metrics=metrics_obj,
            missing_metrics=missing,
            language=language,
            category=category,
            raw_data=raw_data or {},
            canonical_key=canonical_key,
        )