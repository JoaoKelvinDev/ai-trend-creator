"""Provedor de descoberta via YouTube Data API v3."""

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.app.core.config import get_settings
from backend.app.providers.discovery.base import DiscoveryProvider, DiscoveryResult
from backend.app.schemas.trends import TrendCandidateV1, TrendSource

logger = logging.getLogger(__name__)


class YouTubeDiscoveryProvider(DiscoveryProvider):
    """Provedor que coleta tendências via YouTube Data API v3."""

    def __init__(self, api_key: str | None = None, region_code: str = "BR", category_id: str | None = None):
        self._api_key = api_key or get_settings().YOUTUBE_API_KEY
        self._region_code = region_code
        self._category_id = category_id  # None = todas, ou ex: "28" para Science & Technology
        self._client: httpx.AsyncClient | None = None
        self._base_url = "https://www.googleapis.com/youtube/v3"

    @property
    def source(self) -> TrendSource:
        return TrendSource.YOUTUBE

    @property
    def cost_class(self) -> str:
        return "zero"  # YouTube Data API tem quota gratuita

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"User-Agent": "AI-Trend-Creator/0.1 YouTube Fetcher"},
            )
        return self._client

    async def fetch_trends(self, *, since: datetime | None = None, limit: int = 50) -> DiscoveryResult:
        """Busca vídeos populares do YouTube Data API."""
        if not self._api_key:
            return DiscoveryResult(
                trends=[],
                errors=["YouTube API key não configurada"],
                duration_ms=0,
                source_calls={},
            )

        start_time = datetime.now()
        all_trends: list[TrendCandidateV1] = []
        errors: list[str] = []
        source_calls: dict[str, int] = {}

        client = await self._get_client()

        try:
            # Buscar vídeos mais populares
            trends, calls = await self._fetch_most_popular(client, since, limit)
            all_trends.extend(trends)
            source_calls["most_popular"] = calls

        except Exception as e:
            logger.warning("Erro ao buscar YouTube trends", extra={"error": str(e)})
            errors.append(f"youtube: {type(e).__name__}: {e}")

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return DiscoveryResult(
            trends=all_trends[:limit],
            errors=errors,
            duration_ms=duration_ms,
            source_calls=source_calls,
        )

    async def _fetch_most_popular(
        self,
        client: httpx.AsyncClient,
        since: datetime | None,
        limit: int,
    ) -> tuple[list[TrendCandidateV1], int]:
        """Busca vídeos mais populares por região/categoria."""
        params = {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": self._region_code,
            "maxResults": min(limit, 50),  # API limita a 50
            "key": self._api_key,
        }
        if self._category_id:
            params["videoCategoryId"] = self._category_id

        response = await client.get(f"{self._base_url}/videos", params=params)
        response.raise_for_status()
        data = response.json()
        source_calls = 1

        trends: list[TrendCandidateV1] = []
        for item in data.get("items", []):
            try:
                trend = self._parse_video(item)
                if trend and (since is None or trend.published_at is None or trend.published_at >= since):
                    trends.append(trend)
            except Exception as e:
                logger.debug("Erro ao parsear vídeo YouTube", extra={"error": str(e), "video_id": item.get("id")})
                continue

        return trends, source_calls

    def _parse_video(self, item: dict[str, Any]) -> TrendCandidateV1 | None:
        """Converte item da YouTube API em TrendCandidateV1."""
        video_id = item.get("id")
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})

        if not video_id:
            return None

        title = snippet.get("title", "").strip()
        if not title:
            return None

        # URL canônica
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Data de publicação
        published_at = None
        published_str = snippet.get("publishedAt")
        if published_str:
            try:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except Exception:
                pass

        # Métricas
        metrics: dict[str, Any] = {}
        for key, api_key in [("views", "viewCount"), ("likes", "likeCount"), ("comments", "commentCount")]:
            value = statistics.get(api_key)
            if value is not None:
                try:
                    metrics[key] = int(value)
                except (ValueError, TypeError):
                    pass

        # Categoria - mapear categoryId para nosso niche
        category = self._map_category(snippet.get("categoryId"))

        # Tags como raw_data para análise posterior
        tags = snippet.get("tags", [])

        return self.normalize_trend(
            external_id=video_id,
            title=title,
            url=url,
            published_at=published_at,
            metrics=metrics or None,
            language=snippet.get("defaultAudioLanguage", "pt")[:2].lower(),
            category=category,
            raw_data={
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "tags": tags[:20],  # Limitar tags
                "duration": content_details.get("duration"),
                "definition": content_details.get("definition"),
                "caption": content_details.get("caption"),
            },
        )

    def _map_category(self, category_id: str | None) -> str | None:
        """Mapeia YouTube categoryId para nossos nichos."""
        if not category_id:
            return None
        category_map = {
            "1": "entretenimento",      # Film & Animation
            "2": "entretenimento",      # Autos & Vehicles
            "10": "musica",             # Music
            "15": "animais",            # Pets & Animals
            "17": "esportes",           # Sports
            "18": "entretenimento",     # Short Movies
            "19": "entretenimento",     # Travel & Events
            "20": "jogos",              # Gaming
            "21": "entretenimento",     # Videoblogging
            "22": "entretenimento",     # People & Blogs
            "23": "entretenimento",     # Comedy
            "24": "entretenimento",     # Entertainment
            "25": "educacao",           # News & Politics
            "26": "educacao",           # Howto & Style
            "27": "educacao",           # Education
            "28": "tecnologia",         # Science & Technology
            "29": "entretenimento",     # Nonprofits & Activism
            "30": "entretenimento",     # Movies
            "31": "entretenimento",     # Anime/Animation
            "32": "entretenimento",     # Action/Adventure
            "33": "entretenimento",     # Classics
            "34": "entretenimento",     # Comedy
            "35": "entretenimento",     # Documentary
            "36": "entretenimento",     # Drama
            "37": "entretenimento",     # Family
            "38": "entretenimento",     # Foreign
            "39": "entretenimento",     # Horror
            "40": "entretenimento",     # Sci-Fi/Fantasy
            "41": "entretenimento",     # Thriller
            "42": "entretenimento",     # Shorts
            "43": "entretenimento",     # Shows
            "44": "entretenimento",     # Trailers
        }
        return category_map.get(category_id)

    async def health_check(self) -> bool:
        """Verifica se a YouTube API está acessível."""
        if not self._api_key:
            return False
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self._base_url}/videos",
                params={"part": "id", "chart": "mostPopular", "regionCode": self._region_code, "maxResults": 1, "key": self._api_key},
                timeout=10.0,
            )
            return response.status_code < 400
        except Exception:
            return False

    async def close(self) -> None:
        """Fecha conexões HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None