"""Storyboarder - Agente LLM para geração de storyboard (StoryboardV1)."""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from backend.app.providers.factory import get_provider_factory
from backend.app.schemas.candidates import ScriptV1
from backend.app.schemas.storyboard import (
    StoryboardV1,
    StoryboardSceneV1,
    LicenseEntry,
)
from backend.app.providers.llm.base import LLMProvider
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoryboardResult:
    scenes_count: int


# Prompt template versionado
STORYBOARDER_PROMPT_V1 = """Você é um diretor de storyboard para TikTok/Reels/Shorts (formato vertical 9:16, 15-60s).
Sua tarefa: criar storyboard COMPLETO baseado no roteiro (ScriptV1).

ESTRUTURA OBRIGATÓRIA:
1. CENAS: Lista ordenada de cenas com timing sincronizado à narração
2. TIPOS VISUAIS: local_ai_image | original_motion_graphic | licensed_user_asset | text_card
3. PROMPTS: Para cenas de IA, prompt detalhado para geração de imagem
4. TEXTOS OVERLAY: Textos sincronizados com narração
5. TRANSIÇÕES: cut | fade | slide | zoom
6. MANIFESTO DE LICENÇAS: Para cada asset gerado

REGRAS OBRIGATÓRIAS:
- Duração total das cenas deve bater com duration_estimate_seconds do script (±5%)
- Cada segmento de narração deve ter cena correspondente
- Cenas de text_card para títulos, ganchos, CTAs
- Cenas de original_motion_graphic para gráficos/dados (template programático)
- Cenas de local_ai_image para ilustrações conceituais (ComfyUI)
- NÃO use local_ai_video (desabilitado no MVP)
- Retorne APENAS JSON válido, sem markdown, sem texto extra.

FORMATO DE SAÍDA (JSON):
{
  "scenes": [
    {
      "scene_id": "scene_1",
      "order": 0,
      "start_ms": 0,
      "duration_ms": 5000,
      "narration_segment": "Texto do segmento 1...",
      "visual_kind": "text_card",
      "visual_prompt": null,
      "overlay_text": "Título na tela",
      "transition": "fade"
    },
    {
      "scene_id": "scene_2",
      "order": 1,
      "start_ms": 5000,
      "duration_ms": 8000,
      "narration_segment": "Texto do segmento 2...",
      "visual_kind": "local_ai_image",
      "visual_prompt": "Illustration of AI generating content, futuristic style, vertical 9:16",
      "overlay_text": "Dado chave",
      "transition": "cut"
    }
  ],
  "total_duration_ms": 30000,
  "license_manifest": [
    {
      "asset_id": "scene_1",
      "license_type": "CC0",
      "license_url": null,
      "author": null,
      "version": null,
      "commercial_use_allowed": true,
      "attribution_required": false,
      "attribution_text": null
    }
  ]
}"""


class StoryboarderLLMOutput(BaseModel):
    """Schema para saída estruturada do LLM no Storyboarder."""
    scenes: list[dict[str, Any]] = Field(min_length=1, description="Cenas do storyboard")
    total_duration_ms: int = Field(gt=0, description="Duração total em ms")
    license_manifest: list[dict[str, Any]] = Field(default_factory=list, description="Manifesto de licenças")


class Storyboarder:
    """Agente que usa LLM para gerar StoryboardV1 a partir de ScriptV1."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self._llm = llm_provider or get_provider_factory().get_llm_provider()
        self._prompt_version = "1.0"

    async def create_storyboard(self, script: ScriptV1) -> StoryboardV1:
        """
        Cria storyboard completo baseado no roteiro.

        Args:
            script: ScriptV1 com narração, textos na tela, duração estimada

        Returns:
            StoryboardV1 com cenas estruturadas
        """
        # Preparar contexto para o LLM
        context = self._build_context(script)

        try:
            # Chamar LLM com structured output
            result = await self._llm.generate_structured(
                schema=StoryboarderLLMOutput,
                prompt=STORYBOARDER_PROMPT_V1,
                context=context,
                temperature=0.3,  # Baixa temperatura para consistência visual
            )

            # Construir StoryboardV1
            return self._build_storyboard(script, result)

        except Exception as e:
            logger.error("Erro na criação do storyboard", extra={"error": str(e), "script_id": str(script.trace_id)})
            # Fallback determinístico
            return self._fallback_storyboard(script)

    def _build_context(self, script: ScriptV1) -> dict[str, Any]:
        """Constrói contexto para o LLM."""
        narration_text = " ".join([seg.text for seg in script.narration_segments])
        return {
            "roteiro": {
                "title": script.title,
                "duration_estimate_seconds": script.duration_estimate_seconds,
                "narration_segments": [
                    {
                        "segment_id": seg.segment_id,
                        "text": seg.text,
                        "start_estimate_ms": seg.start_estimate_ms,
                        "duration_estimate_ms": seg.duration_estimate_ms,
                        "scene_id": seg.scene_id,
                    }
                    for seg in script.narration_segments
                ],
                "on_screen_text": [
                    {
                        "text_id": txt.text_id,
                        "text": txt.text,
                        "start_ms": txt.start_ms,
                        "duration_ms": txt.duration_ms,
                        "position": txt.position,
                        "style": txt.style,
                    }
                    for txt in script.on_screen_text
                ],
                "hashtags": script.hashtags,
            },
            "restricoes": {
                "target_duration_seconds": script.duration_estimate_seconds,
                "tolerance_percent": 5,
                "vertical_format": True,
                "aspect_ratio": "9:16",
                "resolution_target": "1080x1920",
                "visual_kinds_allowed": [
                    "local_ai_image",
                    "original_motion_graphic",
                    "licensed_user_asset",
                    "text_card",
                ],
                "transitions_allowed": ["cut", "fade", "slide", "zoom"],
                "proibido_local_ai_video": True,
                "licencas_preferidas": ["CC0", "CC-BY", "CC-BY-SA"],
            },
        }

    def _build_storyboard(self, script: ScriptV1, llm_result: StoryboarderLLMOutput) -> StoryboardV1:
        """Constrói StoryboardV1 a partir do resultado do LLM."""
        data = llm_result.model_dump()

        # Converter cenas
        scenes = []
        for scene_data in data["scenes"]:
            scene = StoryboardSceneV1(
                scene_id=scene_data["scene_id"],
                order=scene_data["order"],
                start_ms=scene_data["start_ms"],
                duration_ms=scene_data["duration_ms"],
                narration_segment=scene_data.get("narration_segment"),
                visual_kind=scene_data["visual_kind"],
                visual_prompt=scene_data.get("visual_prompt"),
                overlay_text=scene_data.get("overlay_text"),
                transition=scene_data.get("transition", "cut"),
                provenance="generated",
            )
            scenes.append(scene)

        # Converter manifesto de licenças
        license_manifest = []
        for lic_data in data.get("license_manifest", []):
            # Garantir que asset_id seja UUID válido
            if "asset_id" in lic_data and isinstance(lic_data["asset_id"], str):
                try:
                    lic_data["asset_id"] = UUID(lic_data["asset_id"])
                except ValueError:
                    lic_data["asset_id"] = uuid4()
            license_manifest.append(LicenseEntry(**lic_data))

        return StoryboardV1(
            trace_id=uuid4(),
            project_id=script.project_id,
            revision=script.revision,
            scenes=scenes,
            total_duration_ms=data["total_duration_ms"],
            license_manifest=license_manifest,
        )

    def _fallback_storyboard(self, script: ScriptV1) -> StoryboardV1:
        """Storyboard determinístico quando LLM falha."""
        scenes = []

        # Mapear segmentos de narração para cenas
        for i, seg in enumerate(script.narration_segments):
            # Determinar tipo visual baseado no conteúdo
            if i == 0:
                visual_kind = "text_card"
                visual_prompt = None
                overlay_text = script.title[:100] if script.title else "Título"
            elif i == len(script.narration_segments) - 1:
                visual_kind = "text_card"
                visual_prompt = None
                overlay_text = "Siga para mais conteúdo!"
            else:
                visual_kind = "original_motion_graphic"
                visual_prompt = f"Abstract visualization for: {seg.text[:100]}"
                overlay_text = None

            scene = StoryboardSceneV1(
                scene_id=seg.scene_id or f"scene_{i+1}",
                order=i,
                start_ms=seg.start_estimate_ms,
                duration_ms=seg.duration_estimate_ms,
                narration_segment=seg.text,
                visual_kind=visual_kind,
                visual_prompt=visual_prompt,
                overlay_text=overlay_text,
                transition="cut" if i == 0 else "fade",
                provenance="generated",
            )
            scenes.append(scene)

        # Calcular duração total
        total_duration = sum(s.duration_ms for s in scenes)

        # Manifesto de licenças (todos CC0 - programáticos)
        license_manifest = [
            LicenseEntry(
                asset_id=uuid4(),  # Gerar novo UUID para cada asset
                license_type="CC0",
                commercial_use_allowed=True,
                attribution_required=False,
            )
            for s in scenes
        ]

        return StoryboardV1(
            trace_id=uuid4(),
            project_id=script.project_id,
            revision=script.revision,
            scenes=scenes,
            total_duration_ms=total_duration,
            license_manifest=license_manifest,
        )


async def create_storyboard_use_case(project_id: UUID) -> StoryboardResult:
    """Caso de uso para criar storyboard (chamado pelo orchestrator)."""
    from backend.app.db.session import get_db_context
    from backend.app.db.models import VideoProject, Script
    from sqlalchemy import select

    async with get_db_context() as db:
        project = await db.get(VideoProject, project_id)
        if not project:
            raise ValueError(f"Projeto {project_id} não encontrado")

        # Buscar script mais recente para este projeto (revisão do script pode diferir da do projeto)
        result = await db.execute(
            select(Script).where(
                Script.project_id == project_id,
            ).order_by(Script.created_at.desc())
        )
        script_model = result.scalars().first()
        if not script_model:
            raise ValueError(f"Script não encontrado para projeto {project_id}")

        # Converter Script model para ScriptV1
        from backend.app.schemas.candidates import ScriptV1, NarrationSegment, OnScreenText, ClaimSource
        import json

        # Reconstruir narration_segments do script_text
        narration_text = script_model.script_text
        narration_segments = []
        outline = script_model.outline_json or {}

        if script_model.citations_json:
            citations = script_model.citations_json.get("claim_sources", [])
        else:
            citations = []

        # Usar os key_claims do outline como guia para segmentos
        key_claims = outline.get("key_claims", [])
        if key_claims:
            for i, claim in enumerate(key_claims):
                seg_start = i * (script_model.duration_estimate_s * 1000 // max(1, len(key_claims)))
                seg_duration = script_model.duration_estimate_s * 1000 // max(1, len(key_claims))
                narration_segments.append(NarrationSegment(
                    segment_id=f"s{i+1}",
                    text=claim,
                    start_estimate_ms=seg_start,
                    duration_estimate_ms=seg_duration,
                    scene_id=f"scene_{i+1}",
                ))
        else:
            # Fallback: um segmento único
            narration_segments.append(NarrationSegment(
                segment_id="s1",
                text=narration_text[:500],
                start_estimate_ms=0,
                duration_estimate_ms=int(script_model.duration_estimate_s * 1000),
                scene_id="scene_1",
            ))

        # Reconstruir on_screen_text do outline
        on_screen_text = []
        hook = outline.get("hook", "")
        angle = outline.get("angle", "")
        if hook:
            on_screen_text.append(OnScreenText(
                text_id="t1",
                text=hook[:100],
                start_ms=0,
                duration_ms=5000,
                position="top",
                style="highlight",
            ))
        if angle:
            on_screen_text.append(OnScreenText(
                text_id="t2",
                text=angle[:100],
                start_ms=5000,
                duration_ms=10000,
                position="center",
                style="default",
            ))

        # Reconstruir claim_sources
        claim_sources = []
        for cs in citations:
            claim_sources.append(ClaimSource(
                claim=cs.get("claim", ""),
                source_url=cs.get("source_url"),
                source_title=cs.get("source_title"),
                source_type=cs.get("source_type", "other"),
                verified=cs.get("verified", False),
                confidence=cs.get("confidence", 0.5),
            ))

        script_v1 = ScriptV1(
            trace_id=uuid4(),
            project_id=project_id,
            revision=project.revision,
            narration_segments=narration_segments,
            on_screen_text=on_screen_text,
            title=outline.get("hook", "Sem título")[:150],
            caption=script_model.script_text[:2200],
            hashtags=outline.get("hashtags", []),
            claim_sources=claim_sources,
            duration_estimate_seconds=script_model.duration_estimate_s,
        )

    # Usar o Storyboarder agent
    storyboarder = Storyboarder()
    storyboard = await storyboarder.create_storyboard(script_v1)

    # Persistir storyboard no banco
    async with get_db_context() as db:
        project = await db.get(VideoProject, project_id)
        if not project:
            raise ValueError(f"Projeto {project_id} não encontrado")

        # Salvar cenas
        from backend.app.db.models import StoryboardScene
        for scene in storyboard.scenes:
            visual_kind_value = scene.visual_kind.value if hasattr(scene.visual_kind, 'value') else str(scene.visual_kind)
            scene_model = StoryboardScene(
                project_id=project_id,
                revision=project.revision,
                order_index=scene.order,
                start_ms=scene.start_ms,
                duration_ms=scene.duration_ms,
                visual_kind=visual_kind_value,
                prompt=scene.visual_prompt,
            )
            db.add(scene_model)

        project.state = "STORYBOARDED"
        await db.commit()

    return StoryboardResult(scenes_count=len(storyboard.scenes))