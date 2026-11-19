"""Provedor de descoberta via importação manual (JSON/CSV)."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.providers.discovery.base import DiscoveryProvider, DiscoveryResult
from backend.app.schemas.trends import TrendCandidateV1, TrendSource

logger = logging.getLogger(__name__)


class ManualDiscoveryProvider(DiscoveryProvider):
    """Provedor que importa tendências de arquivos JSON/CSV locais."""

    def __init__(self, import_dir: Path | None = None):
        settings = get_settings()
        self._import_dir = import_dir or Path(settings.LOCAL_STORAGE_ROOT) / "imports"
        self._import_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source(self) -> TrendSource:
        return TrendSource.MANUAL

    @property
    def cost_class(self) -> str:
        return "zero"

    async def fetch_trends(self, *, since: datetime | None = None, limit: int = 50) -> DiscoveryResult:
        """Importa tendências de arquivos na pasta de importação."""
        start_time = datetime.now()
        all_trends: list[TrendCandidateV1] = []
        errors: list[str] = []
        source_calls: dict[str, int] = {}

        # Buscar arquivos .json e .csv
        for file_path in self._import_dir.glob("*.json"):
            try:
                trends, calls = await self._import_json(file_path, since, limit)
                all_trends.extend(trends)
                source_calls[str(file_path)] = calls
            except Exception as e:
                logger.warning("Erro ao importar JSON", extra={"file": str(file_path), "error": str(e)})
                errors.append(f"{file_path.name}: {type(e).__name__}: {e}")

        for file_path in self._import_dir.glob("*.csv"):
            try:
                trends, calls = await self._import_csv(file_path, since, limit)
                all_trends.extend(trends)
                source_calls[str(file_path)] = calls
            except Exception as e:
                logger.warning("Erro ao importar CSV", extra={"file": str(file_path), "error": str(e)})
                errors.append(f"{file_path.name}: {type(e).__name__}: {e}")

        # Ordenar por data de publicação (mais recentes primeiro)
        all_trends.sort(key=lambda t: t.published_at or datetime.min, reverse=True)

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return DiscoveryResult(
            trends=all_trends[:limit],
            errors=errors,
            duration_ms=duration_ms,
            source_calls=source_calls,
        )

    async def _import_json(self, file_path: Path, since: datetime | None, limit: int) -> tuple[list[TrendCandidateV1], int]:
        """Importa tendências de arquivo JSON."""
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)

        # Suportar tanto array quanto objeto com chave "trends"
        items = data if isinstance(data, list) else data.get("trends", [])

        trends: list[TrendCandidateV1] = []
        for item in items[:limit]:
            try:
                trend = self._parse_item(item, str(file_path))
                if trend and (since is None or trend.published_at is None or trend.published_at >= since):
                    trends.append(trend)
            except Exception as e:
                logger.debug("Erro ao parsear item JSON", extra={"error": str(e)})
                continue

        return trends, 1

    async def _import_csv(self, file_path: Path, since: datetime | None, limit: int) -> tuple[list[TrendCandidateV1], int]:
        """Importa tendências de arquivo CSV."""
        trends: list[TrendCandidateV1] = []

        with file_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if len(trends) >= limit:
                    break
                try:
                    trend = self._parse_item(row, str(file_path))
                    if trend and (since is None or trend.published_at is None or trend.published_at >= since):
                        trends.append(trend)
                except Exception as e:
                    logger.debug("Erro ao parsear linha CSV", extra={"error": str(e)})
                    continue

        return trends, 1

    def _parse_item(self, item: dict[str, Any], source_ref: str) -> TrendCandidateV1 | None:
        """Converte dicionário em TrendCandidateV1."""
        # Campos obrigatórios
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        external_id = str(item.get("external_id", item.get("id", url))).strip()

        if not title or not url:
            return None

        # Data de publicação
        published_at = None
        for date_key in ("published_at", "published", "date", "created_at"):
            date_str = item.get(date_key)
            if date_str:
                try:
                    published_at = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                    break
                except Exception:
                    continue

        # Métricas
        metrics: dict[str, Any] = {}
        for metric_key in ("views", "likes", "comments", "shares", "watch_time_avg_sec"):
            value = item.get(metric_key)
            if value is not None:
                try:
                    metrics[metric_key] = float(value) if "avg" in metric_key else int(value)
                except (ValueError, TypeError):
                    pass

        # Categoria
        category = item.get("category") or item.get("niche")
        if category:
            category = str(category).lower()

        # Idioma
        language = str(item.get("language", "pt")).lower()

        return self.normalize_trend(
            external_id=external_id,
            title=title,
            url=url,
            published_at=published_at,
            metrics=metrics or None,
            language=language,
            category=category,
            raw_data={"source_file": source_ref, "original_keys": list(item.keys())},
        )

    async def health_check(self) -> bool:
        """Sempre saudável - leitura local."""
        return True

    def create_sample_files(self) -> None:
        """Cria arquivos de exemplo para documentação."""
        sample_json = self._import_dir / "sample_trends.json"
        if not sample_json.exists():
            sample_data = {
                "trends": [
                    {
                        "title": "Nova IA Generativa Revoluciona Criação de Vídeo",
                        "url": "https://example.com/artigo/ia-video-2026",
                        "external_id": "ia-video-2026-001",
                        "published_at": "2026-11-15T10:00:00Z",
                        "category": "tecnologia",
                        "language": "pt",
                        "views": 150000,
                        "likes": 12000,
                        "comments": 800,
                    },
                    {
                        "title": "Descoberta Científica: Novo Material Supercondutor",
                        "url": "https://example.com/ciencia/supercondutor-2026",
                        "external_id": "supercondutor-2026-002",
                        "published_at": "2026-11-16T14:30:00Z",
                        "category": "ciencia",
                        "language": "pt",
                        "views": 89000,
                        "likes": 5400,
                        "comments": 320,
                    },
                ]
            }
            sample_json.write_text(json.dumps(sample_data, indent=2, ensure_ascii=False))

        sample_csv = self._import_dir / "sample_trends.csv"
        if not sample_csv.exists():
            csv_content = """title,url,external_id,published_at,category,language,views,likes,comments
"Tendência de Moda: Roupas Sustentáveis","https://example.com/moda/sustentavel","moda-sustentavel-001","2026-11-17T09:00:00Z","moda","pt",45000,3200,180
"Viagem: Destinos Secretos no Brasil","https://example.com/viagens/destinos-secretos","viagens-secretos-001","2026-11-17T11:00:00Z","viagens","pt",67000,4100,250
"""
            sample_csv.write_text(csv_content)


# Importar config aqui para evitar circular import
from backend.app.core.config import get_settings