"""Schemas para descoberta e análise de tendências (AGENTS.md seção 8)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from backend.app.schemas.base import BaseSchema, TracedSchema, WithTraceId
from backend.app.domain.enums import TrendSource, TrendLanguage, NicheCategory


class TrendMetrics(BaseSchema):
    """Métricas observadas de uma tendência."""
    views: Optional[int] = Field(default=None, ge=0)
    likes: Optional[int] = Field(default=None, ge=0)
    comments: Optional[int] = Field(default=None, ge=0)
    shares: Optional[int] = Field(default=None, ge=0)
    watch_time_avg_sec: Optional[float] = Field(default=None, ge=0)
    growth_rate: Optional[float] = Field(default=None, description="Taxa de crescimento estimada")


class TrendCandidateV1(TracedSchema):
    """
    Candidato a tendência descoberto (AGENTS.md: TrendCandidateV1).

    Schema versão 1.0 - Contrato entre Discovery e Trend Analyst.
    """
    schema_version: str = Field(default="1.0")
    trend_id: UUID = Field(description="ID único da tendência no nosso sistema")
    source: TrendSource = Field(description="Fonte de origem")
    external_id: str = Field(description="ID externo na plataforma de origem")
    title: str = Field(min_length=1, max_length=500, description="Título original")
    url: HttpUrl = Field(description="URL canônica do conteúdo")
    observed_at: datetime = Field(description="Quando foi observado/coletado (UTC)")
    published_at: Optional[datetime] = Field(default=None, description="Quando foi publicado originalmente (UTC)")
    metrics: TrendMetrics = Field(default_factory=TrendMetrics, description="Métricas observadas")
    missing_metrics: list[str] = Field(default_factory=list, description="Lista de métricas não disponíveis")
    language: TrendLanguage = Field(default=TrendLanguage.PT, description="Idioma detectado")
    category: Optional[NicheCategory] = Field(default=None, description="Categoria/nicho estimado")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Dados brutos da API fonte")
    canonical_key: str = Field(description="Chave canônica para deduplicação (hash fonte:external_id)")


class TrendSnapshotV1(TracedSchema):
    """Snapshot de métricas em um momento (para calcular growth)."""
    schema_version: str = Field(default="1.0")
    trend_item_id: UUID
    captured_at: datetime
    metrics: TrendMetrics
    raw_metrics_json: dict[str, Any] = Field(default_factory=dict)


class TrendClusterV1(TracedSchema):
    """Cluster de tendências relacionadas."""
    schema_version: str = Field(default="1.0")
    cluster_id: UUID
    cluster_key: str = Field(description="Chave de agrupamento (ex: topic hash)")
    title: str = Field(description="Título representativo do cluster")
    niche_id: Optional[UUID] = None
    trend_item_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=None).replace(tzinfo=None))


class TrendSignals(BaseSchema):
    """Sinais normalizados 0-100 para scoring (AGENTS.md seção 5.2)."""
    growth: float = Field(ge=0, le=100, description="Crescimento de popularidade")
    niche_fit: float = Field(ge=0, le=100, description="Adequação ao nicho")
    engagement: float = Field(ge=0, le=100, description="Engajamento relativo")
    recency: float = Field(ge=0, le=100, description="Recência")
    production_feasibility: float = Field(ge=0, le=100, description="Viabilidade de produção")

    def weighted_score(self) -> float:
        """Calcula score ponderado conforme fórmula do AGENTS.md."""
        return (
            0.35 * self.growth +
            0.25 * self.niche_fit +
            0.20 * self.engagement +
            0.10 * self.recency +
            0.10 * self.production_feasibility
        )


class TrendAssessmentV1(TracedSchema, WithTraceId):
    """
    Avaliação de tendência pelo Analyst (AGENTS.md: TrendAssessmentV1).

    Schema versão 1.0 - Saída do Trend Analyst.
    """
    schema_version: str = Field(default="1.0")
    trend_id: UUID
    score: float = Field(ge=0, le=100, description="Score final 0-100")
    confidence: float = Field(ge=0, le=1, description="Confiança na avaliação")
    signals: TrendSignals
    missing_signals: list[str] = Field(default_factory=list, description="Sinais não disponíveis")
    rationale: str = Field(min_length=10, description="Justificativa textual da avaliação")
    safety_flags: list[str] = Field(default_factory=list, description="Alertas de segurança/direitos")
    evidence_refs: list[str] = Field(default_factory=list, description="Referências às evidências")
    model_version: str = Field(description="Versão do modelo LLM usado")


class TrendItemResponse(BaseSchema):
    """Resposta da API para tendência coletada."""
    id: UUID
    provider: TrendSource
    source_id: str
    title: str
    url: HttpUrl
    published_at: Optional[datetime]
    discovered_at: datetime
    language: TrendLanguage
    niche_guess: Optional[NicheCategory]
    latest_metrics: TrendMetrics
    cluster_id: Optional[UUID] = None
    assessment: Optional[TrendAssessmentV1] = None


# ──────────────────────────────────────────────
# Request/Response para API
# ──────────────────────────────────────────────

class DiscoveryRunRequest(BaseSchema):
    """Request para execução manual de descoberta."""
    sources: list[TrendSource] = Field(default_factory=lambda: [TrendSource.RSS, TrendSource.MANUAL])
    force_refresh: bool = False


class DiscoveryRunResponse(BaseSchema):
    """Response de execução de descoberta."""
    trace_id: UUID
    trends_found: int
    trends_new: int
    trends_updated: int
    clusters_created: int
    duration_ms: int
    errors: list[str] = Field(default_factory=list)


class TrendsListParams(BaseSchema):
    """Parâmetros para listagem de tendências."""
    source: Optional[TrendSource] = None
    niche: Optional[NicheCategory] = None
    min_score: Optional[float] = Field(default=None, ge=0, le=100)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)