"""Trend Analyst - Agente LLM para avaliação e scoring de tendências."""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from backend.app.providers.factory import get_provider_factory
from backend.app.schemas.trends import (
    TrendAssessmentV1,
    TrendCandidateV1,
    TrendSignals,
    TrendSource,
)
from backend.app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)


# Pydantic model for LLM structured output
class TrendAnalystLLMOutput(BaseModel):
    """Schema para saída estruturada do LLM no TrendAnalyst."""
    signals: dict[str, float] = Field(description="Sinais de avaliação")
    missing_signals: list[str] = Field(default_factory=list, description="Sinais não calculáveis")
    score: float = Field(ge=0, le=100, description="Score final 0-100")
    confidence: float = Field(ge=0, le=1, description="Confiança 0-1")
    rationale: str = Field(min_length=20, description="Justificativa")
    safety_flags: list[str] = Field(default_factory=list, description="Alertas de segurança")
    evidence_refs: list[str] = Field(default_factory=list, description="Referências de evidências")


# Prompt template versionado
TREND_ANALYST_PROMPT_V1 = """Você é um analista de tendências para criação de conteúdo viral em TikTok/Reels/Shorts.
Sua tarefa: avaliar uma tendência candidata e retornar um JSON estruturado com score 0-100.

CRITÉRIOS DE AVALIAÇÃO (cada um 0-100):
1. GROWTH (peso 35%): Crescimento real de popularidade. Use views/likes/comments/shares e data de publicação.
   - Alto: crescimento exponencial recente, viralizando agora
   - Médio: crescimento estável, boa tração
   - Baixo: estagnado, antigo, poucas métricas

2. NICHE_FIT (peso 25%): Adequação aos nichos configurados (tecnologia, ciência, saúde, finanças, educação, entretenimento, esportes, moda, viagens, culinária).
   - Alto: encaixa perfeitamente em nicho de alto interesse
   - Médio: encaixa em nicho moderado
   - Baixo: fora de nicho ou nicho saturado/baixo interesse

3. ENGAGEMENT (peso 20%): Engajamento relativo (likes+comments+shares / views).
   - Alto: >5% taxa de engajamento
   - Médio: 1-5%
   - Baixo: <1% ou métricas ausentes

4. RECENCY (peso 10%): Quão recente é a tendência.
   - Alto: < 48h
   - Médio: 2-7 dias
   - Baixo: > 7 dias

5. PRODUCTION_FEASIBILITY (peso 10%): Viabilidade de produzir vídeo 15-45s com recursos locais (Ollama, templates, FFmpeg, TTS).
   - Alto: tema visual, fact-based, fácil ilustrar com gráficos/imagens/templates
   - Médio: requer alguma criatividade mas factível
   - Baixo: requer filmagem real, atores, locações, licenças complexas

REGRAS OBRIGATÓRIAS:
- SE métricas faltarem (views/likes/comments), REDUZA confidence e marque em missing_signals
- NÃO invente números. Use apenas dados fornecidos.
- Penalize: duplicação, fatos não verificáveis, violação de direitos, clickbait óbvio, médico/financeiro sem fonte forte.
- O score final é a média ponderada dos 5 critérios.
- Retorne APENAS JSON válido, sem markdown, sem texto extra.

FORMATO DE SAÍDA (JSON):
{{
  "signals": {{
    "growth": 0-100,
    "niche_fit": 0-100,
    "engagement": 0-100,
    "recency": 0-100,
    "production_feasibility": 0-100
  }},
  "missing_signals": ["lista de sinais não calculáveis por falta de dados"],
  "score": 0-100,
  "confidence": 0.0-1.0,
  "rationale": "Justificativa textual em português (mín 20 chars)",
  "safety_flags": ["alertas de segurança/direitos"],
  "evidence_refs": ["referências às evidências usadas"]
}}"""


class TrendAnalyst:
    """Agente que usa LLM para avaliar tendências e gerar TrendAssessmentV1."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self._llm = llm_provider or get_provider_factory().get_llm_provider()
        self._prompt_version = "1.0"

    async def assess_trend(self, candidate: TrendCandidateV1) -> TrendAssessmentV1:
        """
        Avalia uma tendência candidata e retorna assessment estruturado.

        Args:
            candidate: TrendCandidateV1 com dados da tendência

        Returns:
            TrendAssessmentV1 com score, confidence, signals, rationale
        """
        # Preparar contexto para o LLM
        context = self._build_context(candidate)

        try:
            # Chamar LLM com structured output usando Pydantic model
            result = await self._llm.generate_structured(
                schema=TrendAnalystLLMOutput,
                prompt=TREND_ANALYST_PROMPT_V1,
                context=context,
                temperature=0.3,
            )

            # Validar e construir assessment
            return self._build_assessment(candidate, result.model_dump())

        except Exception as e:
            logger.error("Erro na avaliação da tendência", extra={"error": str(e), "candidate_id": str(candidate.trend_id)})
            # Fallback: assessment baseado em regras determinísticas
            return self._fallback_assessment(candidate)

    def _build_context(self, candidate: TrendCandidateV1) -> str:
        """Constrói contexto textual para o LLM."""
        # Handle both enum and string cases
        source_value = candidate.source.value if hasattr(candidate.source, 'value') else str(candidate.source)
        language_value = candidate.language.value if hasattr(candidate.language, 'value') else str(candidate.language)
        category_value = candidate.category.value if candidate.category and hasattr(candidate.category, 'value') else (str(candidate.category) if candidate.category else None)

        parts = [
            f"TÍTULO: {candidate.title}",
            f"FONTE: {source_value}",
            f"URL: {candidate.url}",
            f"PUBLICADO EM: {candidate.published_at.isoformat() if candidate.published_at else 'Desconhecido'}",
            f"OBSERVADO EM: {candidate.observed_at.isoformat()}",
            f"IDIOMA: {language_value}",
            f"CATEGORIA: {category_value or 'Não identificado'}",
        ]

        # Métricas
        metrics = candidate.metrics
        if metrics.views is not None:
            parts.append(f"VIEWS: {metrics.views:,}")
        if metrics.likes is not None:
            parts.append(f"LIKES: {metrics.likes:,}")
        if metrics.comments is not None:
            parts.append(f"COMMENTS: {metrics.comments:,}")
        if metrics.shares is not None:
            parts.append(f"SHARES: {metrics.shares:,}")

        # Calcular taxa de engajamento se possível
        if metrics.views and metrics.views > 0:
            engagement_total = (metrics.likes or 0) + (metrics.comments or 0) + (metrics.shares or 0)
            engagement_rate = (engagement_total / metrics.views) * 100
            parts.append(f"TAXA ENGAJAMENTO: {engagement_rate:.2f}%")

        # Métricas faltantes
        if candidate.missing_metrics:
            parts.append(f"MÉTRICAS FALTANTES: {', '.join(candidate.missing_metrics)}")

        # Raw data resumido
        if candidate.raw_data:
            raw_summary = {k: v for k, v in candidate.raw_data.items() if k in ("channel_title", "tags", "duration")}
            if raw_summary:
                parts.append(f"DADOS EXTRAS: {json.dumps(raw_summary, ensure_ascii=False)}")

        return "\n".join(parts)

    def _build_assessment(self, candidate: TrendCandidateV1, llm_result: dict[str, Any]) -> TrendAssessmentV1:
        """Constrói TrendAssessmentV1 a partir do resultado do LLM."""
        signals_data = llm_result["signals"]
        signals = TrendSignals(**signals_data)

        # Validar score ponderado bate com signals
        calculated_score = signals.weighted_score()
        llm_score = llm_result["score"]
        # Usar o score do LLM mas logar divergência
        if abs(calculated_score - llm_score) > 5.0:
            logger.warning("Score LLM diverge do calculado", extra={
                "llm_score": llm_score,
                "calculated": calculated_score,
                "candidate_id": str(candidate.trend_id),
            })

        return TrendAssessmentV1(
            trace_id=uuid4(),
            trend_id=candidate.trend_id,
            score=llm_score,
            confidence=llm_result["confidence"],
            signals=signals,
            missing_signals=llm_result.get("missing_signals", []),
            rationale=llm_result["rationale"],
            safety_flags=llm_result.get("safety_flags", []),
            evidence_refs=llm_result.get("evidence_refs", []),
            model_version=self._llm.model_name if hasattr(self._llm, "model_name") else "unknown",
        )

    def _fallback_assessment(self, candidate: TrendCandidateV1) -> TrendAssessmentV1:
        """Assessment determinístico quando LLM falha."""
        metrics = candidate.metrics

        # Growth: baseado em views e recência
        growth = 30.0
        if metrics.views:
            if metrics.views > 100000:
                growth = 80.0
            elif metrics.views > 10000:
                growth = 60.0
            elif metrics.views > 1000:
                growth = 40.0

        # Recency
        recency = 50.0
        if candidate.published_at:
            days_old = (datetime.now(timezone.utc) - candidate.published_at).days
            if days_old <= 2:
                recency = 90.0
            elif days_old <= 7:
                recency = 70.0
            elif days_old <= 30:
                recency = 40.0
            else:
                recency = 20.0

        # Engagement
        engagement = 30.0
        if metrics.views and metrics.views > 0:
            engagement_total = (metrics.likes or 0) + (metrics.comments or 0) + (metrics.shares or 0)
            rate = (engagement_total / metrics.views) * 100
            if rate > 5:
                engagement = 90.0
            elif rate > 1:
                engagement = 60.0
            elif rate > 0.1:
                engagement = 40.0

        # Niche fit - handle both enum and string
        category_value = candidate.category.value if candidate.category and hasattr(candidate.category, 'value') else (str(candidate.category) if candidate.category else None)
        niche_fit = 50.0
        high_value_niches = {"tecnologia", "ciencia", "saude", "financas", "educacao"}
        if category_value and category_value in high_value_niches:
            niche_fit = 80.0

        # Production feasibility
        production_feasibility = 70.0  # Default bom para templates/gráficos
        if category_value and category_value in {"esportes", "moda", "viagens"}:
            production_feasibility = 50.0  # Mais difícil sem footage real

        signals = TrendSignals(
            growth=growth,
            niche_fit=niche_fit,
            engagement=engagement,
            recency=recency,
            production_feasibility=production_feasibility,
        )

        missing = list(candidate.missing_metrics)
        if not candidate.published_at:
            missing.append("published_at")

        confidence = 0.5
        if len(missing) == 0:
            confidence = 0.7
        elif len(missing) >= 3:
            confidence = 0.3

        score = signals.weighted_score()

        return TrendAssessmentV1(
            trace_id=uuid4(),
            trend_id=candidate.trend_id,
            score=score,
            confidence=confidence,
            signals=signals,
            missing_signals=missing,
            rationale=f"Avaliação fallback determinística. Growth: {growth:.0f}, Niche: {niche_fit:.0f}, Engagement: {engagement:.0f}, Recency: {recency:.0f}, Production: {production_feasibility:.0f}. Score ponderado: {score:.1f}",
            safety_flags=[],
            evidence_refs=[str(candidate.url)],
            model_version="fallback-deterministic",
        )


async def assess_cluster_trends(cluster_id: UUID) -> list[TrendAssessmentV1]:
    """Avalia todas as tendências de um cluster."""
    from backend.app.db.models import TrendClusterItem, TrendItem
    from backend.app.db.session import get_db_context

    async with get_db_context() as db:
        # Buscar trends do cluster
        result = await db.execute(
            TrendItem.__table__.select().join(
                TrendClusterItem, TrendClusterItem.trend_item_id == TrendItem.id
            ).where(TrendClusterItem.cluster_id == cluster_id)
        )
        trend_items = result.mappings().all()

    if not trend_items:
        return []

    # Converter para TrendCandidateV1
    candidates = []
    for t in trend_items:
        from backend.app.schemas.trends import TrendMetrics, TrendLanguage, NicheCategory
        candidate = TrendCandidateV1(
            trace_id=uuid4(),
            trend_id=t["id"],
            source=TrendSource(t["provider"]),
            external_id=t["source_id"],
            title=t["title"],
            url=t["original_url"],
            observed_at=t["discovered_at"],
            published_at=t["published_at"],
            metrics=TrendMetrics(),
            language=TrendLanguage(t["language"]),
            category=NicheCategory(t["niche_guess"]) if t["niche_guess"] else None,
            canonical_key=t["canonical_key"],
        )
        candidates.append(candidate)

    # Avaliar cada uma
    analyst = TrendAnalyst()
    assessments = []
    for candidate in candidates:
        assessment = await analyst.assess_trend(candidate)
        assessments.append(assessment)

    return assessments