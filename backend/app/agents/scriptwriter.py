"""Scriptwriter - Agente LLM para roteiro completo (ScriptV1)."""

import json
import logging
from typing import Any
from uuid import UUID, uuid4

from backend.app.providers.factory import get_provider_factory
from backend.app.schemas.candidates import (
    ContentPlanV1,
    ScriptV1,
    NarrationSegment,
    OnScreenText,
    ClaimSource,
)
from backend.app.providers.llm.base import LLMProvider
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Prompt template versionado
SCRIPTWRITER_PROMPT_V1 = """Você é um roteirista para TikTok/Reels/Shorts (formato vertical, 15-60s).
Sua tarefa: escrever roteiro COMPLETO baseado no plano de conteúdo.

ESTRUTURA OBRIGATÓRIA:
1. NARRAÇÃO: Segmentos com texto, tempo estimado (ms), cena correspondente
2. TEXTO NA TELA (overlay): Textos sincronizados com narração, posição, estilo
3. TÍTULO: Para thumbnail/capa (5-150 chars)
4. LEGENDA: Para publicação (10-2200 chars), inclui hashtags do plano
5. FONTES (claim_sources): Para CADA key_claim do plano, cite fonte verificável

REGRAS OBRIGATÓRIAS:
- NÃO invente fatos, dados, estudos, citações. Use apenas o que está no plano/evidências.
- Se não há fonte para um claim, marque verified=false, confidence=0.3
- Narração: linguagem natural, falada, frases curtas, ritmo para TTS
- Texto na tela: complementa narração, não repete. Máx 200 chars por texto.
- Duração total estimada deve bater com duration_target_seconds (±10%)
- Hashtags: usar as do plano + 1-2 contextualizadas
- Retorne APENAS JSON válido, sem markdown, sem texto extra.

FORMATO DE SAÍDA (JSON):
{
  "narration_segments": [
    {"segment_id": "s1", "text": "Texto narrado...", "start_estimate_ms": 0, "duration_estimate_ms": 5000, "scene_id": "scene_1"},
    {"segment_id": "s2", "text": "Mais texto...", "start_estimate_ms": 5000, "duration_estimate_ms": 8000, "scene_id": "scene_2"}
  ],
  "on_screen_text": [
    {"text_id": "t1", "text": "Título na tela", "start_ms": 0, "duration_ms": 5000, "position": "top", "style": "highlight"},
    {"text_id": "t2", "text": "Dado chave", "start_ms": 5000, "duration_ms": 8000, "position": "center", "style": "default"}
  ],
  "title": "Título do vídeo (5-150 chars)",
  "caption": "Legenda completa com hashtags (10-2200 chars)",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "claim_sources": [
    {"claim": "Afirmação do plano", "source_url": "https://...", "source_title": "Título fonte", "source_type": "news|study|official|expert|other", "verified": true, "confidence": 0.8}
  ],
  "duration_estimate_seconds": 30.0
}"""


class ScriptwriterLLMOutput(BaseModel):
    """Schema para saída estruturada do LLM no Scriptwriter."""
    narration_segments: list[dict[str, Any]] = Field(min_length=1, description="Segmentos de narração")
    on_screen_text: list[dict[str, Any]] = Field(default_factory=list, description="Textos na tela")
    title: str = Field(min_length=5, max_length=150)
    caption: str = Field(min_length=10, max_length=2200)
    hashtags: list[str] = Field(default_factory=list, max_length=10)
    claim_sources: list[dict[str, Any]] = Field(default_factory=list, description="Fontes para claims")
    duration_estimate_seconds: float = Field(gt=0)


class Scriptwriter:
    """Agente que usa LLM para gerar ScriptV1 a partir de ContentPlanV1."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self._llm = llm_provider or get_provider_factory().get_llm_provider()
        self._prompt_version = "1.0"

    async def write_script(self, plan: ContentPlanV1) -> ScriptV1:
        """
        Escreve roteiro completo baseado no plano de conteúdo.

        Args:
            plan: ContentPlanV1 com niche, angle, hook, key_claims, etc.

        Returns:
            ScriptV1 com roteiro estruturado
        """
        # Preparar contexto para o LLM
        context = self._build_context(plan)

        try:
            # Chamar LLM com structured output
            result = await self._llm.generate_structured(
                schema=ScriptwriterLLMOutput,
                prompt=SCRIPTWRITER_PROMPT_V1,
                context=context,
                temperature=0.4,  # Equilíbrio criatividade/precisão
            )

            # Construir ScriptV1
            return self._build_script(plan, result)

        except Exception as e:
            logger.error("Erro na escrita do roteiro", extra={"error": str(e), "plan_id": str(plan.trace_id)})
            # Fallback determinístico
            return self._fallback_script(plan)

    def _build_context(self, plan: ContentPlanV1) -> dict[str, Any]:
        """Constrói contexto para o LLM."""
        # Handle both enum and string cases for niche
        niche_value = plan.niche.value if hasattr(plan.niche, 'value') else str(plan.niche)
        return {
            "plano_conteudo": {
                "niche": niche_value,
                "target_audience": plan.target_audience,
                "angle": plan.angle,
                "hook": plan.hook,
                "key_claims": plan.key_claims,
                "evidence_refs": plan.evidence_refs,
                "duration_target_seconds": plan.duration_target_seconds,
                "style": plan.style,
                "hashtags": plan.hashtags,
            },
            "restricoes": {
                "min_duration_seconds": 15,
                "max_duration_seconds": 60,
                "target_duration_seconds": plan.duration_target_seconds,
                "narration_language": "pt-BR",
                "vertical_format": True,
                "tts_friendly": True,  # Frases curtas, pontuação clara
                "proibido_inventar_fatos": True,
                "proibido_copiar_texto_fonte": True,
            },
        }

    def _build_script(self, plan: ContentPlanV1, llm_result: ScriptwriterLLMOutput) -> ScriptV1:
        """Constrói ScriptV1 a partir do resultado do LLM."""
        data = llm_result.model_dump()

        # Converter narration_segments
        narration_segments = []
        for seg in data["narration_segments"]:
            narration_segments.append(NarrationSegment(**seg))

        # Converter on_screen_text
        on_screen_text = []
        for txt in data.get("on_screen_text", []):
            on_screen_text.append(OnScreenText(**txt))

        # Converter claim_sources
        claim_sources = []
        for cs in data.get("claim_sources", []):
            claim_sources.append(ClaimSource(**cs))

        return ScriptV1(
            trace_id=uuid4(),
            project_id=plan.candidate_id,  # Será sobrescrito pelo use_case
            revision=1,
            narration_segments=narration_segments,
            on_screen_text=on_screen_text,
            title=data["title"],
            caption=data["caption"],
            hashtags=data["hashtags"],
            claim_sources=claim_sources,
            duration_estimate_seconds=data["duration_estimate_seconds"],
        )

    def _fallback_script(self, plan: ContentPlanV1) -> ScriptV1:
        """Roteiro determinístico quando LLM falha."""
        # Narração baseada no hook + angle + claims
        narration_text = f"{plan.hook} {plan.angle} "
        for i, claim in enumerate(plan.key_claims[:3]):
            narration_text += f" Ponto {i+1}: {claim}. "
        narration_text += " Compartilhe se achou útil!"

        # Estimar duração: ~150 palavras/minuto = 2.5 palavras/seg
        words = len(narration_text.split())
        duration_est = max(15, min(60, words / 2.5))

        narration_segments = [
            NarrationSegment(
                segment_id="s1",
                text=narration_text,
                start_estimate_ms=0,
                duration_estimate_ms=int(duration_est * 1000),
                scene_id="scene_1",
            )
        ]

        on_screen_text = [
            OnScreenText(
                text_id="t1",
                text=plan.title[:100] if hasattr(plan, 'title') else plan.hook[:100],
                start_ms=0,
                duration_ms=5000,
                position="top",
                style="highlight",
            ),
            OnScreenText(
                text_id="t2",
                text="\n".join(plan.key_claims[:2]),
                start_ms=5000,
                duration_ms=10000,
                position="center",
                style="default",
            ),
        ]

        claim_sources = []
        for i, claim in enumerate(plan.key_claims):
            evidence_ref = plan.evidence_refs[i] if i < len(plan.evidence_refs) else ""
            claim_sources.append(ClaimSource(
                claim=claim,
                source_url=evidence_ref if evidence_ref.startswith("http") else None,
                source_title="Fonte da tendência" if evidence_ref else "Não verificado",
                source_type="other",
                verified=bool(evidence_ref and evidence_ref.startswith("http")),
                confidence=0.7 if evidence_ref else 0.3,
            ))

        hashtags = plan.hashtags + [f"#{plan.niche.value}"] if f"#{plan.niche.value}" not in plan.hashtags else plan.hashtags

        return ScriptV1(
            trace_id=uuid4(),
            project_id=plan.candidate_id,
            revision=1,
            narration_segments=narration_segments,
            on_screen_text=on_screen_text,
            title=f"{plan.hook[:100]}",
            caption=f"{plan.angle[:200]}\n\n{' '.join(hashtags)}",
            hashtags=hashtags[:10],
            claim_sources=claim_sources,
            duration_estimate_seconds=duration_est,
        )


async def write_script_use_case(project_id: UUID, plan: ContentPlanV1) -> ScriptV1:
    """Caso de uso para escrever roteiro (chamado pelo orchestrator)."""
    writer = Scriptwriter()
    script = await writer.write_script(plan)
    # Atualizar project_id correto
    script.project_id = project_id
    return script