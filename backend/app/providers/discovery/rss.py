"""Provedor de descoberta via feeds RSS."""

import asyncio
import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx

from backend.app.core.config import get_settings
from backend.app.providers.discovery.base import DiscoveryProvider, DiscoveryResult
from backend.app.schemas.trends import TrendCandidateV1, TrendSource

logger = logging.getLogger(__name__)


class RSSDiscoveryProvider(DiscoveryProvider):
    """Provedor que coleta tendências de feeds RSS autorizados."""

    def __init__(self, feed_urls: list[str] | None = None):
        self._feed_urls = feed_urls or get_settings().rss_feeds
        self._client: httpx.AsyncClient | None = None

    @property
    def source(self) -> TrendSource:
        return TrendSource.RSS

    @property
    def cost_class(self) -> str:
        return "zero"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"User-Agent": "AI-Trend-Creator/0.1 RSS Fetcher"},
            )
        return self._client

    async def fetch_trends(self, *, since: datetime | None = None, limit: int = 50) -> DiscoveryResult:
        """Busca tendências dos feeds RSS configurados."""
        start_time = datetime.now()
        all_trends: list[TrendCandidateV1] = []
        errors: list[str] = []
        source_calls: dict[str, int] = {}

        client = await self._get_client()

        for feed_url in self._feed_urls:
            try:
                feed_trends, call_count = await self._fetch_feed(client, feed_url, since, limit)
                all_trends.extend(feed_trends)
                source_calls[feed_url] = call_count

                if len(all_trends) >= limit:
                    all_trends = all_trends[:limit]
                    break

            except Exception as e:
                logger.warning("Erro ao processar feed RSS", extra={"feed": feed_url, "error": str(e)})
                errors.append(f"{feed_url}: {type(e).__name__}: {e}")

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return DiscoveryResult(
            trends=all_trends[:limit],
            errors=errors,
            duration_ms=duration_ms,
            source_calls=source_calls,
        )

    async def _fetch_feed(
        self,
        client: httpx.AsyncClient,
        feed_url: str,
        since: datetime | None,
        limit: int,
    ) -> tuple[list[TrendCandidateV1], int]:
        """Busca e parseia um único feed RSS."""
        # Validar URL para prevenir SSRF
        parsed = urlparse(feed_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Esquema não permitido: {parsed.scheme}")

        response = await client.get(feed_url)
        response.raise_for_status()
        source_calls = 1

        # Parsear com feedparser (thread-safe)
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, response.text)

        trends: list[TrendCandidateV1] = []
        for entry in feed.entries[:limit]:
            try:
                trend = self._parse_entry(entry, feed_url)
                if trend and (since is None or trend.published_at is None or trend.published_at >= since):
                    trends.append(trend)
            except Exception as e:
                logger.debug("Erro ao parsear entry RSS", extra={"error": str(e)})
                continue

        return trends, source_calls

    def _parse_entry(self, entry: Any, feed_url: str) -> TrendCandidateV1 | None:
        """Converte entry do feedparser em TrendCandidateV1."""
        # Extrair campos com fallbacks
        title = getattr(entry, "title", "").strip()
        if not title:
            return None

        link = getattr(entry, "link", "").strip()
        if not link:
            return None

        # ID externo: usar link ou guid
        external_id = getattr(entry, "id", link)
        if not external_id:
            external_id = link

        # Data de publicação
        published_at = None
        for date_field in ("published_parsed", "updated_parsed"):
            parsed = getattr(entry, date_field, None)
            if parsed:
                try:
                    published_at = datetime(*parsed[:6])
                    break
                except Exception:
                    pass

        # Métricas - RSS não tem, mas podemos extrair se houver extensões
        metrics: dict[str, Any] = {}
        # Algumas feeds têm contadores em extensões
        for metric_key in ("views", "likes", "comments"):
            value = getattr(entry, metric_key, None)
            if value is not None:
                try:
                    metrics[metric_key] = int(value)
                except (ValueError, TypeError):
                    pass

        # Categoria/nicho - tentar extrair de tags
        category = None
        tags = getattr(entry, "tags", [])
        if tags:
            first_tag = tags[0].get("term", "").lower()
            # Mapear tags comuns para nossos nichos
            niche_map = {
                "tech": "tecnologia", "technology": "tecnologia",
                "science": "ciencia", "health": "saude",
                "finance": "financas", "education": "educacao",
                "entertainment": "entretenimento", "sports": "esportes",
                "fashion": "moda", "travel": "viagens", "food": "culinaria",
            }
            category = niche_map.get(first_tag)

        return self.normalize_trend(
            external_id=external_id,
            title=title,
            url=link,
            published_at=published_at,
            metrics=metrics or None,
            language="pt",
            category=category,
            raw_data={"feed_url": feed_url, "entry_keys": list(entry.keys())},
        )

    async def health_check(self) -> bool:
        """Verifica se pelo menos um feed RSS está acessível."""
        if not self._feed_urls:
            return True  # Sem feeds configurados = OK

        client = await self._get_client()
        for feed_url in self._feed_urls[:3]:  # Testar apenas os primeiros 3
            try:
                response = await client.head(feed_url, timeout=10.0)
                if response.status_code < 400:
                    return True
            except Exception:
                continue
        return False

    async def close(self) -> None:
        """Fecha conexões HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None