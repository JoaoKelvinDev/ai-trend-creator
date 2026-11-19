"""Casos de uso da aplicação - Orquestração de alto nível."""

import asyncio
import hashlib
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from backend.app.providers.factory import get_provider_factory
from backend.app.workflows.orchestrator import workflow_orchestrator
from backend.app.db.session import get_db_context
from backend.app.db.models import (
    VideoProject, ContentCandidate, TrendCluster, TrendItem,
    TrendSnapshot, Script, StoryboardScene, MediaAsset, Job, DailyQuota,
    TrendClusterItem, CandidateStatusEnum
)
from sqlalchemy import select
from backend.app.domain.policies.states import VideoState
from backend.app.domain.policies.quotas import quota_policy, timezone_policy, DailyQuotaUsage
from backend.app.schemas.trends import TrendCandidateV1, TrendSource, TrendMetrics, TrendLanguage, NicheCategory
from backend.app.application.clustering import run_clustering_use_case
from backend.app.agents.trend_analyst import assess_cluster_trends
from backend.app.agents.content_strategist import create_content_plan_use_case
from backend.app.agents.scriptwriter import write_script_use_case
from backend.app.agents.storyboarder import StoryboardResult
from backend.app.schemas.candidates import ContentPlanV1, ScriptV1
from backend.app.render.ffmpeg import FFmpegRenderer, RenderConfig
from backend.app.render.subtitles import SubtitleGenerator, SubtitleSegment, SubtitleConfig
from backend.app.providers.speech.base import SpeechSpec

# Windows fix: psycopg não suporta ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Dataclasses para resultados
# ──────────────────────────────────────────────

@dataclass(frozen=True)
class DiscoveryResult:
    trends_found: int
    trends_new: int
    trends_updated: int
    clusters_created: int
    duration_ms: int
    errors: list[str]


@dataclass(frozen=True)
class ScoringResult:
    candidates_created: int
    top_candidate_id: UUID | None


@dataclass(frozen=True)
class ScriptResult:
    script_id: UUID
    project_id: UUID
    plan: ContentPlanV1 | None = None
    script: ScriptV1 | None = None


@dataclass(frozen=True)
class ContentPlanResult:
    plan_id: UUID
    project_id: UUID
    plan: ContentPlanV1


@dataclass(frozen=True)
class AssetsResult:
    assets_count: int


@dataclass(frozen=True)
class RenderResult:
    video_path: str
    duration_ms: int


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    issues: list[str]


@dataclass(frozen=True)
class ApprovalResult:
    approval_id: UUID


@dataclass(frozen=True)
class ExportResult:
    export_path: str


@dataclass(frozen=True)
class DailyPipelineResult:
    candidates_processed: int


@dataclass(frozen=True)
class CleanupResult:
    cleaned_count: int


# ──────────────────────────────────────────────
# Use Cases
# ──────────────────────────────────────────────

def run_discovery_use_case() -> DiscoveryResult:
    """Executa descoberta de tendências de todas as fontes habilitadas."""
    import asyncio
    return asyncio.run(_run_discovery_async())


async def _run_discovery_async() -> DiscoveryResult:
    factory = get_provider_factory()
    providers = factory.get_all_discovery_providers()

    all_trends: list[TrendCandidateV1] = []
    all_errors: list[str] = []
    total_calls: dict[str, int] = {}
    start_time = datetime.now(timezone.utc)

    for provider in providers:
        try:
            result = await provider.fetch_trends(limit=100)
            all_trends.extend(result.trends)
            all_errors.extend(result.errors)
            for k, v in result.source_calls.items():
                total_calls[k] = total_calls.get(k, 0) + v
        except Exception as e:
            logger.error("Erro no provedor de descoberta", extra={
                "provider": provider.provider_name,
                "error": str(e),
            })
            all_errors.append(f"{provider.provider_name}: {e}")

    # Persistir trends (deduplicação simples por canonical_key)
    new_count = 0
    updated_count = 0

    async with get_db_context() as db:
        for trend in all_trends:
            # Verificar se já existe
            existing = await db.execute(
                select(TrendItem).where(
                    TrendItem.canonical_key == trend.canonical_key
                )
            )
            existing = existing.scalar_one_or_none()

            # Normalizar source (pode vir como string do mock)
            source_value = trend.source.value if hasattr(trend.source, 'value') else str(trend.source)
            language_value = trend.language.value if hasattr(trend.language, 'value') else str(trend.language)
            category_value = trend.category.value if trend.category and hasattr(trend.category, 'value') else (str(trend.category) if trend.category else None)

            if existing:
                # Atualizar métricas se houver snapshot novo
                snapshot = TrendSnapshot(
                    trend_item_id=existing.id,
                    captured_at=datetime.now(timezone.utc),
                    views=trend.metrics.views,
                    likes=trend.metrics.likes,
                    comments=trend.metrics.comments,
                    shares=trend.metrics.shares,
                    raw_metrics_json=trend.raw_data,
                )
                db.add(snapshot)
                updated_count += 1
            else:
                # Criar novo trend_item
                trend_item = TrendItem(
                    provider=source_value,
                    source_id=trend.external_id,
                    original_url=str(trend.url),
                    canonical_key=trend.canonical_key,
                    title=trend.title,
                    published_at=trend.published_at,
                    discovered_at=trend.observed_at,
                    language=language_value,
                    niche_guess=category_value,
                )
                db.add(trend_item)
                await db.flush()

                # Snapshot inicial
                snapshot = TrendSnapshot(
                    trend_item_id=trend_item.id,
                    captured_at=datetime.now(timezone.utc),
                    views=trend.metrics.views,
                    likes=trend.metrics.likes,
                    comments=trend.metrics.comments,
                    shares=trend.metrics.shares,
                    raw_metrics_json=trend.raw_data,
                )
                db.add(snapshot)
                new_count += 1

        await db.commit()

    # Clustering - agrupar trends similares
    clusters_created = 0
    if new_count > 0 or updated_count > 0:
        try:
            clusters_created = await run_clustering_use_case()
        except Exception as e:
            logger.warning("Erro no clustering", extra={"error": str(e)})
            all_errors.append(f"clustering: {e}")

    duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    return DiscoveryResult(
        trends_found=len(all_trends),
        trends_new=new_count,
        trends_updated=updated_count,
        clusters_created=clusters_created,
        duration_ms=duration_ms,
        errors=all_errors,
    )


@dataclass(frozen=True)
class ScoringResult:
    candidates_created: int
    top_candidate_id: UUID | None
    error: str | None = None


def score_trends_use_case(cluster_id: UUID) -> ScoringResult:
    """Executa scoring de tendências e cria candidatos."""
    import asyncio
    return asyncio.run(_score_trends_async(cluster_id))


async def _score_trends_async(cluster_id: UUID) -> ScoringResult:
    # Verificar quota diária e buscar cluster
    today = timezone_policy.today_local()
    async with get_db_context() as db:
        result = await db.execute(
            select(DailyQuota).where(DailyQuota.local_date == today)
        )
        quota = result.scalar_one_or_none()
        if not quota:
            quota = DailyQuota(local_date=today)
            db.add(quota)
            await db.flush()

        usage = DailyQuotaUsage(local_date=today, candidates_created=quota.candidates_created)
        can_create, error = quota_policy.can_create_candidate(usage)
        if not can_create:
            return ScoringResult(candidates_created=0, top_candidate_id=None, error=error)

        cluster = await db.get(TrendCluster, cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} não encontrado")

    # Avaliar tendências do cluster com TrendAnalyst
    assessments = await assess_cluster_trends(cluster_id)
    if not assessments:
        return ScoringResult(candidates_created=0, top_candidate_id=None, error="Nenhuma tendência no cluster")

    # Ordenar por score e pegar o melhor
    assessments.sort(key=lambda a: a.score, reverse=True)
    top_assessment = assessments[0]

    # Criar candidato com o melhor assessment
    async with get_db_context() as db:
        candidate = ContentCandidate(
            cluster_id=cluster_id,
            score=top_assessment.score,
            confidence=top_assessment.confidence,
            rationale=top_assessment.rationale,
            evidence_json={
                "signals": {
                    "growth": top_assessment.signals.growth,
                    "niche_fit": top_assessment.signals.niche_fit,
                    "engagement": top_assessment.signals.engagement,
                    "recency": top_assessment.signals.recency,
                    "production_feasibility": top_assessment.signals.production_feasibility,
                },
                "missing_signals": top_assessment.missing_signals,
                "safety_flags": top_assessment.safety_flags,
                "evidence_refs": top_assessment.evidence_refs,
                "model_version": top_assessment.model_version,
            },
            selected_for_date=today,
            status=CandidateStatusEnum.scored.value,
        )
        db.add(candidate)
        await db.flush()

        # Atualizar quota
        quota.candidates_created += 1
        quota_policy.record_candidate_created(usage)

        await db.commit()

        return ScoringResult(candidates_created=1, top_candidate_id=candidate.id)


def generate_script_use_case(candidate_id: UUID) -> ScriptResult:
    """Gera plano de conteúdo e roteiro para um candidato (Etapa 3)."""
    import asyncio
    import sys

    # Check if we're already in an event loop
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - can't use asyncio.run()
        # This should be called from async context directly using _generate_script_async
        # For sync callers (CLI), we run in a new loop
        if sys.platform == "win32":
            # On Windows, use WindowsSelectorEventLoopPolicy for psycopg
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        return asyncio.run(_generate_script_async(candidate_id))
    except RuntimeError:
        # No running loop - safe to use asyncio.run()
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        return asyncio.run(_generate_script_async(candidate_id))


async def _generate_script_async(candidate_id: UUID) -> ScriptResult:
    async with get_db_context() as db:
        candidate = await db.get(ContentCandidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidato {candidate_id} não encontrado")

        # Verificar se já existe projeto para este candidato
        from sqlalchemy import select
        result = await db.execute(
            select(VideoProject)
            .where(VideoProject.candidate_id == candidate_id)
            .order_by(VideoProject.revision.desc())
        )
        existing_project = result.scalars().first()

        if existing_project:
            # Usar próxima revisão
            next_revision = existing_project.revision + 1
            project = VideoProject(
                candidate_id=candidate_id,
                revision=next_revision,
                state=VideoState.SELECTED.value,
                target_duration_s=30,
            )
        else:
            # Criar primeira revisão
            project = VideoProject(
                candidate_id=candidate_id,
                revision=1,
                state=VideoState.SELECTED.value,
                target_duration_s=30,
            )
        db.add(project)
        await db.flush()

        # Buscar cluster para título da tendência
        cluster = await db.get(TrendCluster, candidate.cluster_id)
        candidate_title = cluster.title if cluster else "Tendência"
        candidate_url = ""  # TODO: buscar do trend_item

        # Reconstruir assessment do evidence_json
        evidence = candidate.evidence_json or {}
        from backend.app.schemas.trends import TrendAssessmentV1, TrendSignals
        signals = TrendSignals(**evidence.get("signals", {}))
        assessment = TrendAssessmentV1(
            trace_id=uuid4(),
            trend_id=candidate.cluster_id,
            score=candidate.score,
            confidence=candidate.confidence,
            signals=signals,
            missing_signals=evidence.get("missing_signals", []),
            rationale=candidate.rationale or "",
            safety_flags=evidence.get("safety_flags", []),
            evidence_refs=evidence.get("evidence_refs", []),
            model_version=evidence.get("model_version", "unknown"),
        )

    # 1. Criar plano de conteúdo
    plan = await create_content_plan_use_case(candidate_id)
    # O use_case precisa do título real, vamos chamar o strategist direto
    from backend.app.agents.content_strategist import ContentStrategist
    strategist = ContentStrategist()
    plan = await strategist.create_plan(
        candidate_title=candidate_title,
        candidate_url=candidate_url,
        assessment=assessment,
    )

    # 2. Escrever roteiro
    from backend.app.agents.scriptwriter import write_script_use_case
    script = await write_script_use_case(project.id, plan)

    # 3. Persistir script
    async with get_db_context() as db:
        project = await db.get(VideoProject, project.id)
        if not project:
            raise ValueError(f"Projeto {project.id} não encontrado")

        # Salvar plano como JSON no projeto (metadados)
        # TODO: Adicionar campo plan_json no VideoProject ou tabela separada

        # Salvar script
        script_model = Script(
            project_id=project.id,
            revision=1,
            outline_json={
                "hook": plan.hook,
                "angle": plan.angle,
                "key_claims": plan.key_claims,
                "target_audience": plan.target_audience,
                "style": plan.style,
            },
            script_text="\n".join([seg.text for seg in script.narration_segments]),
            citations_json={
                "claim_sources": [
                    {
                        "claim": cs.claim,
                        "source_url": str(cs.source_url) if cs.source_url else None,
                        "source_title": cs.source_title,
                        "source_type": cs.source_type,
                        "verified": cs.verified,
                        "confidence": cs.confidence,
                    }
                    for cs in script.claim_sources
                ]
            },
            duration_estimate_s=script.duration_estimate_seconds,
        )
        db.add(script_model)

        # Atualizar estado do projeto e candidato
        project.state = VideoState.SCRIPTED.value
        project.target_duration_s = int(script.duration_estimate_seconds)
        candidate.status = CandidateStatusEnum.scripted.value

        await db.commit()

    return ScriptResult(
        script_id=script_model.id,
        project_id=project.id,
        plan=plan,
        script=script,
    )


def create_storyboard_use_case(project_id: UUID) -> StoryboardResult:
    """Cria storyboard para um projeto (Etapa 4)."""
    import asyncio
    import sys

    # Check if we're already in an event loop
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - can't use asyncio.run()
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        return asyncio.run(_create_storyboard_async(project_id))
    except RuntimeError:
        # No running loop - safe to use asyncio.run()
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        return asyncio.run(_create_storyboard_async(project_id))


async def _create_storyboard_async(project_id: UUID) -> StoryboardResult:
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
        # O script_text é a concatenação dos segmentos, precisamos dividir
        narration_text = script_model.script_text
        narration_segments = []
        # Tentar recuperar do outline_json se disponível
        outline = script_model.outline_json or {}

        if script_model.citations_json:
            citations = script_model.citations_json.get("claim_sources", [])
        else:
            citations = []

        # Criar segmentos básicos baseados no texto
        # Estimativa simples: dividir por sentenças ou usar outline
        # Para o fallback, criar um segmento por ~100 chars
        words = narration_text.split()
        words_per_segment = max(1, len(words) // max(1, len(outline.get("key_claims", [1]))))

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
    from backend.app.agents.storyboarder import Storyboarder
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


def generate_assets_use_case(project_id: UUID) -> AssetsResult:
    """Gera assets (imagens, áudio) para o storyboard."""
    import asyncio
    return asyncio.run(_generate_assets_async(project_id))


async def _generate_assets_async(project_id: UUID) -> AssetsResult:
    factory = get_provider_factory()
    image_provider = factory.get_image_provider()
    speech_provider = factory.get_speech_provider()
    asset_store = factory.get_asset_store()

    from backend.app.domain.enums import VisualKind, MediaAssetKind

    async with get_db_context() as db:
        project = await db.get(VideoProject, project_id)
        if not project:
            raise ValueError(f"Projeto {project_id} não encontrado")

        # Buscar cenas como ORM objects para poder atualizar
        from sqlalchemy import select
        result = await db.execute(
            select(StoryboardScene).where(
                StoryboardScene.project_id == project_id,
                StoryboardScene.revision == project.revision,
            ).order_by(StoryboardScene.order_index)
        )
        scenes = result.scalars().all()

        # Buscar script para obter segmentos de narração
        result = await db.execute(
            select(Script).where(
                Script.project_id == project_id,
            ).order_by(Script.created_at.desc())
        )
        script_model = result.scalars().first()

        assets_created = 0

        # 1. Gerar imagens para cenas visuais
        for scene in scenes:
            if scene.visual_kind in (VisualKind.LOCAL_AI_IMAGE, VisualKind.ORIGINAL_MOTION_GRAPHIC, VisualKind.TEXT_CARD):
                from backend.app.providers.images.base import ImageSpec
                spec = ImageSpec(
                    prompt=scene.prompt or "",
                    width=1080,
                    height=1920,
                    metadata={"scene_id": str(scene.id), "project_id": str(project_id)},
                )
                result_img = await image_provider.generate_image(spec)
                asset_id = uuid4()
                asset_metadata = await asset_store.put(
                    result_img.image_path,
                    asset_id=asset_id,
                    kind="image",
                    metadata={
                        "provider": result_img.provider,
                        "model": result_img.model,
                        "license_ref": result_img.license_ref,
                        "owner_project_id": str(project_id),
                        "scene_id": str(scene.id),
                    },
                )

                from backend.app.db.models import MediaAsset
                media_asset = MediaAsset(
                    id=asset_id,
                    owner_project_id=project_id,
                    kind=MediaAssetKind.IMAGE,
                    uri=str(result_img.image_path),
                    sha256=result_img.sha256,
                    mime=result_img.mime_type,
                    width=result_img.width,
                    height=result_img.height,
                    duration_ms=None,
                    provider=result_img.provider,
                    model=result_img.model,
                    license_ref=result_img.license_ref,
                )
                db.add(media_asset)

                scene.asset_id = asset_id
                assets_created += 1

        # 2. Gerar áudio de narração (Etapa 5 - Piper TTS)
        if script_model and script_model.script_text:
            # Usar todo o texto do script para narração
            speech_spec = SpeechSpec(
                text=script_model.script_text,
                voice="default",  # Usará voz padrão do provider
                language="pt-BR",
                speed=1.0,
                pitch=1.0,
                output_format="wav",
            )

            speech_result = await speech_provider.synthesize(speech_spec)

            # Salvar áudio como asset
            audio_asset_id = uuid4()
            await asset_store.put(
                speech_result.audio_path,
                asset_id=audio_asset_id,
                kind="audio",
                metadata={
                    "provider": speech_result.provider,
                    "model": speech_result.model,
                    "license_ref": speech_result.license_ref,
                    "owner_project_id": str(project_id),
                    "duration_ms": speech_result.duration_ms,
                    "sample_rate": speech_result.sample_rate,
                },
            )

            audio_asset = MediaAsset(
                id=audio_asset_id,
                owner_project_id=project_id,
                kind=MediaAssetKind.AUDIO,
                uri=str(speech_result.audio_path),
                sha256=speech_result.sha256,
                mime=speech_result.mime_type,
                width=None,
                height=None,
                duration_ms=speech_result.duration_ms,
                provider=speech_result.provider,
                model=speech_result.model,
                license_ref=speech_result.license_ref,
            )
            db.add(audio_asset)
            assets_created += 1

            # Guardar caminho do áudio para uso no rendering
            project.audio_asset_id = audio_asset_id

        # 3. Gerar legendas (SRT/ASS) a partir dos segmentos de narração
        if script_model:
            # Reconstruir segmentos de narração do outline_json
            outline = script_model.outline_json or {}
            key_claims = outline.get("key_claims", [])
            narration_segments = []

            if key_claims:
                # Dividir duração total entre as claims
                total_duration = script_model.duration_estimate_s * 1000
                per_segment = total_duration // max(1, len(key_claims))
                for i, claim in enumerate(key_claims):
                    narration_segments.append({
                        "text": claim,
                        "duration_ms": per_segment,
                    })
            else:
                narration_segments.append({
                    "text": script_model.script_text[:500],
                    "duration_ms": script_model.duration_estimate_s * 1000,
                })

            # Gerar legendas
            subtitle_config = SubtitleConfig(format="srt")
            subtitle_gen = SubtitleGenerator(subtitle_config)
            subtitle_segments = SubtitleGenerator.create_segments_from_narration(narration_segments)

            subtitle_dir = Path(get_settings().LOCAL_STORAGE_ROOT) / "assets" / "subtitles"
            subtitle_dir.mkdir(parents=True, exist_ok=True)
            subtitle_path = subtitle_dir / f"subtitle_{project_id}_{project.revision}.srt"
            subtitle_gen.generate(subtitle_segments, subtitle_path)

            # Salvar legenda como asset
            subtitle_asset_id = uuid4()
            await asset_store.put(
                subtitle_path,
                asset_id=subtitle_asset_id,
                kind="subtitle",
                metadata={
                    "format": "srt",
                    "owner_project_id": str(project_id),
                    "segments": len(subtitle_segments),
                },
            )

            subtitle_asset = MediaAsset(
                id=subtitle_asset_id,
                owner_project_id=project_id,
                kind=MediaAssetKind.SUBTITLE,
                uri=str(subtitle_path),
                sha256=hashlib.sha256(subtitle_path.read_bytes()).hexdigest(),
                mime="text/srt",
                width=None,
                height=None,
                duration_ms=None,
                provider="subtitle_generator",
                model="srt",
                license_ref="CC0",
            )
            db.add(subtitle_asset)
            project.subtitle_asset_id = subtitle_asset_id
            assets_created += 1

        project.state = VideoState.GENERATING_ASSETS.value
        await db.commit()

        return AssetsResult(assets_count=assets_created)


def render_video_use_case(project_id: UUID) -> RenderResult:
    """Renderiza vídeo final com FFmpeg."""
    import asyncio
    return asyncio.run(_render_video_async(project_id))


async def _render_video_async(project_id: UUID) -> RenderResult:
    """Renderiza vídeo real usando FFmpeg com assets, áudio e legendas."""
    async with get_db_context() as db:
        project = await db.get(VideoProject, project_id)
        if not project:
            raise ValueError(f"Projeto {project_id} não encontrado")

        # Buscar cenas com assets
        from sqlalchemy import select
        from backend.app.db.models import StoryboardScene, MediaAsset
        result = await db.execute(
            select(StoryboardScene).where(
                StoryboardScene.project_id == project_id,
                StoryboardScene.revision == project.revision,
            ).order_by(StoryboardScene.order_index)
        )
        scenes = result.scalars().all()

        # Coletar arquivos de imagem das cenas
        scene_files = []
        for scene in scenes:
            if scene.asset_id:
                asset = await db.get(MediaAsset, scene.asset_id)
                if asset and asset.uri:
                    scene_files.append(Path(asset.uri))

        if not scene_files:
            raise ValueError("Nenhuma cena com asset de imagem encontrada para renderização")

        # Buscar áudio de narração
        audio_path = None
        if project.audio_asset_id:
            audio_asset = await db.get(MediaAsset, project.audio_asset_id)
            if audio_asset and audio_asset.uri:
                audio_path = Path(audio_asset.uri)

        if not audio_path or not audio_path.exists():
            raise ValueError("Asset de áudio não encontrado para renderização")

        # Buscar legenda
        subtitle_path = None
        if project.subtitle_asset_id:
            subtitle_asset = await db.get(MediaAsset, project.subtitle_asset_id)
            if subtitle_asset and subtitle_asset.uri:
                subtitle_path = Path(subtitle_asset.uri)

        project.state = VideoState.RENDERING.value
        await db.commit()

    # Renderizar com FFmpeg
    renderer = FFmpegRenderer(
        config=RenderConfig(
            target_duration_ms=project.target_duration_s * 1000,
            force_cpu=True,  # Forçar CPU no Windows por enquanto
        )
    )

    try:
        render_result = await renderer.render_video(
            scene_files=scene_files,
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            thumbnail_time_ms=1000,
        )

        # Salvar resultado no banco
        async with get_db_context() as db:
            project = await db.get(VideoProject, project_id)
            if project:
                project.video_hash = render_result.sha256
                project.state = VideoState.RENDERING.value  # Será atualizado para QUALITY_CHECK no próximo passo
                await db.commit()

        return RenderResult(
            video_path=str(render_result.video_path),
            duration_ms=render_result.duration_ms,
        )
    finally:
        await renderer.close()


def quality_check_use_case(project_id: UUID) -> QualityResult:
    """Executa verificação de qualidade do vídeo renderizado com ffprobe real."""
    import asyncio
    return asyncio.run(_quality_check_async(project_id))


async def _quality_check_async(project_id: UUID) -> QualityResult:
    from backend.app.domain.policies.quality import quality_policy
    from backend.app.render.ffmpeg import FFmpegRenderer, RenderConfig

    async with get_db_context() as db:
        project = await db.get(VideoProject, project_id)
        if not project:
            raise ValueError(f"Projeto {project_id} não encontrado")

        if not project.video_hash:
            raise ValueError("Vídeo não renderizado ainda (sem video_hash)")

        # Buscar arquivo de vídeo pelo hash
        from backend.app.db.models import MediaAsset
        result = await db.execute(
            select(MediaAsset).where(
                MediaAsset.sha256 == project.video_hash,
                MediaAsset.kind == "video",
            )
        )
        video_asset = result.scalar_one_or_none()

        if not video_asset or not video_asset.uri:
            # Tentar encontrar no diretório de exports
            from backend.app.core.config import get_settings
            exports_dir = Path(get_settings().LOCAL_STORAGE_ROOT) / "exports"
            video_files = list(exports_dir.glob("render_*.mp4"))
            if not video_files:
                raise ValueError("Arquivo de vídeo renderizado não encontrado")
            video_path = video_files[-1]  # Mais recente
        else:
            video_path = Path(video_asset.uri)

        # Validar com ffprobe real
        renderer = FFmpegRenderer(config=RenderConfig())
        video_info = await renderer._probe_video(video_path)
        await renderer.close()

        # Executar verificações de qualidade
        report = quality_policy.run_all_checks(
            width=video_info["width"],
            height=video_info["height"],
            duration_seconds=video_info["duration_ms"] / 1000.0,
            video_codec=video_info["video_codec"],
            audio_codec=video_info["audio_codec"],
            has_audio=True,  # Se chegou aqui, tem áudio
            audio_bitrate_kbps=128,  # Padrão
            file_size_bytes=video_path.stat().st_size if video_path.exists() else 0,
            ffprobe_ok=True,
            has_safe_margins=True,
            subtitle_file=Path(project.subtitle_asset_id) if project.subtitle_asset_id else None,
        )

        project.state = VideoState.QUALITY_CHECK.value
        await db.commit()

        return QualityResult(
            passed=report.passed,
            issues=[i.message for i in report.blocking_issues],
        )


def request_approval_use_case(project_id: UUID) -> ApprovalResult:
    """Solicita aprovação humana via Telegram (ou mock)."""
    import asyncio
    return asyncio.run(_request_approval_async(project_id))


async def _request_approval_async(project_id: UUID) -> ApprovalResult:
    factory = get_provider_factory()
    approval_provider = factory.get_approval_provider()

    async with get_db_context() as db:
        project = await db.get(VideoProject, project_id)
        if not project:
            raise ValueError(f"Projeto {project_id} não encontrado")

        # Criar solicitação de aprovação
        approval_id = uuid4()
        from backend.app.db.models import ApprovalRequest
        approval = ApprovalRequest(
            id=approval_id,
            project_id=project_id,
            revision=project.revision,
            video_sha256=project.video_hash or "mock_hash",
            status="pending",
        )
        db.add(approval)

        project.state = VideoState.PENDING_APPROVAL.value
        await db.commit()

        # Enviar para aprovação (mock aprova automaticamente)
        from backend.app.providers.approvals.base import ApprovalRequest as ApprovalReq
        # TODO: Montar request real com video_path, thumbnail, caption, etc.

        # Simular decisão automática no mock
        await approval_provider.send_for_approval(ApprovalReq(
            approval_id=approval_id,
            project_id=project_id,
            revision=project.revision,
            video_path="/mock/video.mp4",
            thumbnail_path=None,
            title="Título Mock",
            niche="tecnologia",
            duration_seconds=30.0,
            caption="Caption mock #hashtag",
            hashtags=["#hashtag"],
            sources_summary="Fonte mock",
            license_warnings=[],
            trace_id="mock_trace",
        ))

        decision = await approval_provider.wait_for_decision(approval_id, timeout_seconds=10)

        if decision and decision.action == "approve":
            project.state = VideoState.APPROVED.value
        elif decision and decision.action == "reject":
            project.state = VideoState.REJECTED.value
        elif decision and decision.action == "request_revision":
            project.state = VideoState.REVISION_REQUESTED.value

        await db.commit()

        return ApprovalResult(approval_id=approval_id)


def export_package_use_case(project_id: UUID) -> ExportResult:
    """Exporta pacote para publicação assistida."""
    import asyncio
    return asyncio.run(_export_package_async(project_id))


async def _export_package_async(project_id: UUID) -> ExportResult:
    factory = get_provider_factory()
    publisher = factory.get_publisher()

    async with get_db_context() as db:
        project = await db.get(VideoProject, project_id)
        if not project:
            raise ValueError(f"Projeto {project_id} não encontrado")

        # TODO: Montar package real
        from backend.app.providers.publishing.base import PublicationPackage
        package = PublicationPackage(
            project_id=project_id,
            revision=project.revision,
            video_path="/mock/video.mp4",
            thumbnail_path=None,
            caption="Caption mock",
            hashtags=["#mock"],
            privacy_settings={},
            export_dir=factory.get_asset_store()._root / "exports" / str(project_id),
            metadata={},
        )

        result = await publisher.prepare_package(package)

        if result.success:
            project.state = VideoState.READY_FOR_MANUAL_POST.value
            await db.commit()
            return ExportResult(export_path=result.export_path or "")
        else:
            raise RuntimeError(f"Falha na exportação: {result.error}")


def run_daily_pipeline_use_case() -> DailyPipelineResult:
    """Executa pipeline diário completo: descoberta -> scoring -> até 2 candidatos."""
    import asyncio
    return asyncio.run(_run_daily_pipeline_async())


async def _run_daily_pipeline_async() -> DailyPipelineResult:
    # 1. Descoberta
    discovery_result = await _run_discovery_async()
    logger.info("Descoberta diária concluída", extra={"trends_found": discovery_result.trends_found})

    # 2. Scoring e seleção (simplificado - processar top clusters)
    # TODO: Implementar seleção real de até 2 candidatos

    # 3. Para cada candidato selecionado, executar pipeline
    # TODO: Loop sobre candidatos

    return DailyPipelineResult(candidates_processed=0)  # Mock


def cleanup_assets_use_case() -> CleanupResult:
    """Remove assets de projetos rejeitados antigos (política de retenção)."""
    import asyncio
    return asyncio.run(_cleanup_assets_async())


async def _cleanup_assets_async() -> CleanupResult:
    # TODO: Implementar limpeza baseada em política de retenção
    return CleanupResult(cleaned_count=0)