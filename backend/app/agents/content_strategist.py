"""Content Strategist - Agente LLM para plano de conteúdo (ContentPlanV1)."""

import json
import logging
from typing import Any
from uuid import UUID, uuid4

from backend.app.providers.factory import get_provider_factory
from backend.app.schemas.candidates import ContentPlanV1
from backend.app.schemas.trends import TrendAssessmentV1
from backend.app.providers.llm.base import LLMProvider
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Prompt template versionado
CONTENT_STRATEGIST_PROMPT_V1 = """Você é um estrategista de conteúdo para TikTok/Reels/Shorts.
Sua tarefa: criar um plano de conteúdo original baseado em uma tendência avaliada.

REGRAS OBRIGATÓRIAS:
1. NÃO copie o título ou texto da tendência original. Crie ângulo NOVO e ORIGINAL.
2. O gancho (hook) deve prender nos primeiros 3 segundos: pergunta, dado surpreendente, contradição.
3. Público-alvo: descreva em 1 frase (ex: "devs juniores curiosos sobre IA", "pessoas interessadas em saúde preventiva").
4. Afirmações-chave (key_claims): máximo 5, fact-checkables, baseadas na tendência mas não copiadas.
5. Evidências: cite fontes da avaliação (evidence_refs do assessment).
6. Duração alvo: 15-60s (padrão 30s).
7. Hashtags: 3-5 relevantes, sem promessa de alcance.
8. Retorne APENAS JSON válido, sem markdown, sem texto extra.

FORMATO DE SAÍDA (JSON):
{
  "niche": "tecnologia|ciencia|saude|financas|educacao|entretenimento|esportes|moda|viagens|culinaria|outros",
  "target_audience": "descrição do público (5-500 chars)",
  "angle": "ângulo editorial único (10-1000 chars)",
  "hook": "gancho de abertura (5-300 chars)",
  "key_claims": ["claim 1", "claim 2", ...],
  "evidence_refs": ["ref 1", "ref 2", ...],
  "duration_target_seconds": 30,
  "style": "informativo_dinamico|educativo|storytelling|listicle|debate",
  "hashtags": ["#tag1", "#tag2", ...]
}"""


class ContentStrategistLLMOutput(BaseModel):
    """Schema para saída estruturada do LLM no ContentStrategist."""
    niche: str = Field(description="Categoria do nicho")
    target_audience: str = Field(min_length=5, max_length=500)
    angle: str = Field(min_length=10, max_length=1000)
    hook: str = Field(min_length=5, max_length=300)
    key_claims: list[str] = Field(min_length=1, max_length=5)
    evidence_refs: list[str] = Field(default_factory=list)
    duration_target_seconds: int = Field(default=30, ge=15, le=60)
    style: str = Field(default="informativo_dinamico")
    hashtags: list[str] = Field(default_factory=list, max_length=10)


class ContentStrategist:
    """Agente que usa LLM para gerar ContentPlanV1 a partir de candidato + assessment."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self._llm = llm_provider or get_provider_factory().get_llm_provider()
        self._prompt_version = "1.0"

    async def create_plan(
        self,
        candidate_title: str,
        candidate_url: str,
        assessment: TrendAssessmentV1,
        niche_hint: str | None = None,
    ) -> ContentPlanV1:
        """
        Cria plano de conteúdo baseado na tendência e avaliação.

        Args:
            candidate_title: Título da tendência original
            candidate_url: URL da tendência
            assessment: TrendAssessmentV1 com score, signals, rationale
            niche_hint: Dica de nicho (opcional)

        Returns:
            ContentPlanV1 com plano estruturado
        """
        # Preparar contexto para o LLM
        context = self._build_context(candidate_title, candidate_url, assessment, niche_hint)

        try:
            # Chamar LLM com structured output
            result = await self._llm.generate_structured(
                schema=ContentStrategistLLMOutput,
                prompt=CONTENT_STRATEGIST_PROMPT_V1,
                context=context,
                temperature=0.5,  # Criatividade moderada
            )

            # Construir ContentPlanV1
            return self._build_plan(candidate_title, candidate_url, assessment, result)

        except Exception as e:
            logger.error("Erro na criação do plano de conteúdo", extra={"error": str(e)})
            # Fallback determinístico
            return self._fallback_plan(candidate_title, candidate_url, assessment, niche_hint)

    def _build_context(
        self,
        candidate_title: str,
        candidate_url: str,
        assessment: TrendAssessmentV1,
        niche_hint: str | None,
    ) -> dict[str, Any]:
        """Constrói contexto para o LLM."""
        signals = assessment.signals
        return {
            "tendencia_original": {
                "titulo": candidate_title,
                "url": candidate_url,
            },
            "avaliacao": {
                "score": assessment.score,
                "confidence": assessment.confidence,
                "rationale": assessment.rationale,
                "signals": {
                    "growth": signals.growth,
                    "niche_fit": signals.niche_fit,
                    "engagement": signals.engagement,
                    "recency": signals.recency,
                    "production_feasibility": signals.production_feasibility,
                },
                "missing_signals": assessment.missing_signals,
                "safety_flags": assessment.safety_flags,
                "evidence_refs": assessment.evidence_refs,
            },
            "niche_hint": niche_hint,
            "restricoes": {
                "max_duration_seconds": 60,
                "min_duration_seconds": 15,
                "max_key_claims": 5,
                "max_hashtags": 5,
                "proibido_copiar_titulo_original": True,
                "proibido_prometer_viralizacao": True,
            },
        }

    def _build_plan(
        self,
        candidate_title: str,
        candidate_url: str,
        assessment: TrendAssessmentV1,
        llm_result: ContentStrategistLLMOutput,
    ) -> ContentPlanV1:
        """Constrói ContentPlanV1 a partir do resultado do LLM."""
        data = llm_result.model_dump()

        # Validar niche
        from backend.app.domain.enums import NicheCategory
        try:
            niche = NicheCategory(data["niche"])
        except ValueError:
            niche = NicheCategory.OUTROS

        return ContentPlanV1(
            trace_id=uuid4(),
            candidate_id=assessment.trend_id,  # Usando trend_id como proxy
            niche=niche,
            target_audience=data["target_audience"],
            angle=data["angle"],
            hook=data["hook"],
            key_claims=data["key_claims"],
            evidence_refs=data["evidence_refs"],
            duration_target_seconds=data["duration_target_seconds"],
            style=data["style"],
            hashtags=data["hashtags"],
        )

    def _fallback_plan(
        self,
        candidate_title: str,
        candidate_url: str,
        assessment: TrendAssessmentV1,
        niche_hint: str | None,
    ) -> ContentPlanV1:
        """Plano determinístico quando LLM falha."""
        from backend.app.domain.enums import NicheCategory

        # Inferir niche
        niche = NicheCategory.OUTROS
        if niche_hint:
            try:
                niche = NicheCategory(niche_hint)
            except ValueError:
                pass
        elif assessment.signals.niche_fit > 70:
            # Tentar inferir do rationale
            rationale_lower = assessment.rationale.lower()
            for n in NicheCategory:
                if n.value in rationale_lower:
                    niche = n
                    break

        # Claims baseados nos evidence_refs
        key_claims = []
        for ref in assessment.evidence_refs[:3]:
            key_claims.append(f"Tendência relacionada a: {ref}")

        if not key_claims:
            key_claims = ["Tendência em alta no nicho identificado"]

        return ContentPlanV1(
            trace_id=uuid4(),
            candidate_id=assessment.trend_id,
            niche=niche,
            target_audience="Público interessado em novidades do nicho",
            angle=f"Análise acessível sobre {candidate_title[:50]} com perspectiva prática",
            hook=f"Você sabia que {candidate_title[:50].lower()} está mudando o jogo?",
            key_claims=key_claims,
            evidence_refs=assessment.evidence_refs,
            duration_target_seconds=30,
            style="informativo_dinamico",
            hashtags=[f"#{niche.value}", "#tendencias", "#novidades"],
        )


async def create_content_plan_use_case(candidate_id: UUID) -> ContentPlanV1:
    """Caso de uso para criar plano de conteúdo (chamado pelo orchestrator)."""
    from backend.app.db.session import get_db_context
    from backend.app.db.models import ContentCandidate

    async with get_db_context() as db:
        candidate = await db.get(ContentCandidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidato {candidate_id} não encontrado")

        # Buscar assessment do evidence_json
        evidence = candidate.evidence_json or {}
        from backend.app.schemas.trends import TrendAssessmentV1, TrendSignals
        signals = TrendSignals(**evidence.get("signals", {}))
        assessment = TrendAssessmentV1(
            trace_id=uuid4(),
            trend_id=candidate.cluster_id,  # proxy
            score=candidate.score,
            confidence=candidate.confidence,
            signals=signals,
            missing_signals=evidence.get("missing_signals", []),
            rationale=candidate.rationale or "",
            safety_flags=evidence.get("safety_flags", []),
            evidence_refs=evidence.get("evidence_refs", []),
            model_version=evidence.get("model_version", "unknown"),
        )

    strategist = ContentStrategist()
    niche_hint = evidence.get("signals", {}).get("niche_fit", None)
    # Não temos niche direto, usar cluster se disponível
    return await strategist.create_plan(
        candidate_title="Tendência",  # Seria melhor buscar do cluster
        candidate_url="",
        assessment=assessment,
        niche_hint=None,
    )