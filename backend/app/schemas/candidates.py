"""Schemas para candidatos a vídeo e planos de conteúdo (AGENTS.md seção 8)."""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from backend.app.schemas.base import BaseSchema, TracedSchema, WithTraceId, WithProjectId, WithRevision
from backend.app.domain.enums import CandidateStatus, NicheCategory, VideoState


class ContentPlanV1(TracedSchema):
    """
    Plano de conteúdo selecionado (AGENTS.md: ContentPlanV1).

    Schema versão 1.0 - Saída do Content Strategist.
    """
    schema_version: str = Field(default="1.0")
    candidate_id: UUID
    niche: NicheCategory
    target_audience: str = Field(min_length=5, max_length=500, description="Público-alvo descrito")
    angle: str = Field(min_length=10, max_length=1000, description="Ângulo editorial único")
    hook: str = Field(min_length=5, max_length=300, description="Gancho de abertura (primeiros 3s)")
    key_claims: list[str] = Field(min_length=1, max_length=5, description="Afirmações-chave a verificar")
    evidence_refs: list[str] = Field(default_factory=list, description="Referências de evidência para claims")
    duration_target_seconds: int = Field(default=30, ge=15, le=60, description="Duração alvo")
    style: str = Field(default="informativo_dinamico", description="Estilo visual/narrativo")
    hashtags: list[str] = Field(default_factory=list, max_length=10, description="Hashtags sugeridas")


class ScriptV1(TracedSchema, WithProjectId, WithRevision):
    """
    Roteiro completo (AGENTS.md: ScriptV1).

    Schema versão 1.0 - Saída do Scriptwriter.
    """
    schema_version: str = Field(default="1.0")
    narration_segments: list["NarrationSegment"] = Field(min_length=1, description="Segmentos de narração")
    on_screen_text: list["OnScreenText"] = Field(default_factory=list, description="Textos na tela")
    title: str = Field(min_length=5, max_length=150, description="Título do vídeo")
    caption: str = Field(min_length=10, max_length=2200, description="Legenda para publicação")
    hashtags: list[str] = Field(default_factory=list, max_length=10)
    claim_sources: list["ClaimSource"] = Field(default_factory=list, description="Fontes para claims factuais")
    duration_estimate_seconds: float = Field(gt=0, description="Duração estimada pela fala")


class NarrationSegment(BaseSchema):
    """Segmento de narração com tempo estimado."""
    segment_id: str = Field(description="ID único do segmento")
    text: str = Field(min_length=1, max_length=500, description="Texto a ser narrado")
    start_estimate_ms: int = Field(ge=0, description="Início estimado em ms")
    duration_estimate_ms: int = Field(gt=0, description="Duração estimada em ms")
    scene_id: Optional[str] = Field(default=None, description="Cena correspondente no storyboard")


class OnScreenText(BaseSchema):
    """Texto exibido na tela (overlay)."""
    text_id: str
    text: str = Field(min_length=1, max_length=200)
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    position: str = Field(default="center", pattern="^(top|center|bottom|custom)$")
    style: str = Field(default="default", description="Estilo visual: default|highlight|caption")


class ClaimSource(BaseSchema):
    """Fonte para verificação de claim factual."""
    claim: str = Field(description="Afirmação feita no roteiro")
    source_url: Optional[HttpUrl] = None
    source_title: Optional[str] = None
    source_type: str = Field(description="Tipo: study|news|official|expert|other")
    verified: bool = Field(default=False)
    confidence: float = Field(default=0.5, ge=0, le=1)


class CandidateResponse(BaseSchema):
    """Resposta da API para candidato."""
    id: UUID
    cluster_id: UUID
    score: float
    confidence: float
    status: CandidateStatus
    selected_for_date: Optional[date] = None
    niche: NicheCategory
    title: str
    rationale: str
    created_at: datetime
    updated_at: datetime


# Resolve forward references
ScriptV1.model_rebuild()
ContentPlanV1.model_rebuild()