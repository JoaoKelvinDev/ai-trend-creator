"""Rotas para tendências (Etapa 2 - Discovery & Intelligence)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.session import get_db_session
from backend.app.db.models import TrendItem, TrendSnapshot, TrendCluster, TrendClusterItem, ContentCandidate
from backend.app.schemas.trends import (
    TrendItemResponse,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
    TrendsListParams,
    TrendAssessmentV1,
    TrendSignals,
)
from backend.app.schemas.base import PaginatedResponse
from backend.app.application.use_cases import run_discovery_use_case, score_trends_use_case
from backend.app.application.clustering import run_clustering_use_case
from backend.app.agents.trend_analyst import assess_cluster_trends, TrendAnalyst

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("", response_model=PaginatedResponse[TrendItemResponse])
async def list_trends(
    params: TrendsListParams = Depends(),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[TrendItemResponse]:
    """Lista tendências coletadas com filtros e paginação."""
    query = select(TrendItem).options(
        selectinload(TrendItem.snapshots),
        selectinload(TrendItem.cluster_items).selectinload(TrendClusterItem.cluster),
    )

    # Filtros
    if params.source:
        query = query.where(TrendItem.provider == params.source.value)
    if params.niche:
        query = query.where(TrendItem.niche_guess == params.niche.value)
    if params.date_from:
        query = query.where(TrendItem.discovered_at >= params.date_from)
    if params.date_to:
        query = query.where(TrendItem.discovered_at <= params.date_to)

    # Score mínimo - join com candidates
    if params.min_score is not None:
        subq = select(ContentCandidate.cluster_id).where(ContentCandidate.score >= params.min_score)
        query = query.join(TrendClusterItem, TrendClusterItem.trend_item_id == TrendItem.id).where(
            TrendClusterItem.cluster_id.in_(subq)
        )

    # Ordenação: mais recentes primeiro
    query = query.order_by(desc(TrendItem.discovered_at))

    # Contar total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginação
    offset = (params.page - 1) * params.page_size
    query = query.offset(offset).limit(params.page_size)

    result = await db.execute(query)
    trends = result.scalars().unique().all()

    # Converter para response
    items = []
    for t in trends:
        # Último snapshot
        latest_snapshot = max(t.snapshots, key=lambda s: s.captured_at) if t.snapshots else None
        latest_metrics = None
        if latest_snapshot:
            from backend.app.schemas.trends import TrendMetrics
            latest_metrics = TrendMetrics(
                views=latest_snapshot.views,
                likes=latest_snapshot.likes,
                comments=latest_snapshot.comments,
                shares=latest_snapshot.shares,
            )

        # Cluster e assessment
        cluster_id = None
        assessment = None
        if t.cluster_items:
            cluster_id = t.cluster_items[0].cluster_id
            # Buscar assessment do candidato do cluster
            candidate_result = await db.execute(
                select(ContentCandidate).where(ContentCandidate.cluster_id == cluster_id)
            )
            candidate = candidate_result.scalars().first()
            if candidate:
                assessment = TrendAssessmentV1(
                    trace_id=UUID("00000000-0000-0000-0000-000000000000"),  # placeholder
                    trend_id=t.id,
                    score=candidate.score,
                    confidence=candidate.confidence,
                    signals=TrendSignals(**candidate.evidence_json.get("signals", {})) if candidate.evidence_json.get("signals") else TrendSignals(growth=0, niche_fit=0, engagement=0, recency=0, production_feasibility=0),
                    missing_signals=candidate.evidence_json.get("missing_signals", []),
                    rationale=candidate.rationale,
                    safety_flags=candidate.evidence_json.get("safety_flags", []),
                    evidence_refs=candidate.evidence_json.get("evidence_refs", []),
                    model_version=candidate.evidence_json.get("model_version", "unknown"),
                )

        items.append(TrendItemResponse(
            id=t.id,
            provider=t.provider,
            source_id=t.source_id,
            title=t.title,
            url=t.original_url,
            published_at=t.published_at,
            discovered_at=t.discovered_at,
            language=t.language,
            niche_guess=t.niche_guess,
            latest_metrics=latest_metrics or TrendMetrics(),
            cluster_id=cluster_id,
            assessment=assessment,
        ))

    return PaginatedResponse.create(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/discovery/run", response_model=DiscoveryRunResponse)
async def run_discovery(
    request: DiscoveryRunRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DiscoveryRunResponse:
    """Executa descoberta manual de tendências (idempotente)."""
    # TODO: Implementar filtro por sources do request
    result = run_discovery_use_case()
    return DiscoveryRunResponse(
        trace_id=result.trace_id if hasattr(result, 'trace_id') else UUID("00000000-0000-0000-0000-000000000000"),
        trends_found=result.trends_found,
        trends_new=result.trends_new,
        trends_updated=result.trends_updated,
        clusters_created=result.clusters_created,
        duration_ms=result.duration_ms,
        errors=result.errors,
    )


@router.post("/clustering/run")
async def run_clustering(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Executa clustering manual de tendências."""
    clusters_created = await run_clustering_use_case()
    return {"clusters_created": clusters_created, "status": "completed"}


@router.get("/clusters")
async def list_clusters(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[dict]:
    """Lista clusters de tendências."""
    query = select(TrendCluster).options(
        selectinload(TrendCluster.items).selectinload(TrendClusterItem.trend_item),
        selectinload(TrendCluster.candidates),
    ).order_by(desc(TrendCluster.created_at))

    count_query = select(func.count()).select_from(TrendCluster)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    clusters = result.scalars().unique().all()

    items = []
    for c in clusters:
        # Top trend do cluster
        top_trend = None
        if c.items:
            top_trend = c.items[0].trend_item.title

        items.append({
            "id": str(c.id),
            "cluster_key": c.cluster_key,
            "title": c.title,
            "niche_id": str(c.niche_id) if c.niche_id else None,
            "trends_count": len(c.items),
            "top_trend_title": top_trend,
            "candidates_count": len(c.candidates),
            "created_at": c.created_at.isoformat(),
        })

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/clusters/{cluster_id}")
async def get_cluster(
    cluster_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Obtém detalhes de um cluster com suas tendências e candidatos."""
    result = await db.execute(
        select(TrendCluster).options(
            selectinload(TrendCluster.items).selectinload(TrendClusterItem.trend_item).selectinload(TrendItem.snapshots),
            selectinload(TrendCluster.candidates),
        ).where(TrendCluster.id == cluster_id)
    )
    cluster = result.scalars().first()

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster não encontrado")

    trends = []
    for item in cluster.items:
        t = item.trend_item
        latest_snapshot = max(t.snapshots, key=lambda s: s.captured_at) if t.snapshots else None
        trends.append({
            "id": str(t.id),
            "provider": t.provider,
            "source_id": t.source_id,
            "title": t.title,
            "url": t.original_url,
            "published_at": t.published_at.isoformat() if t.published_at else None,
            "discovered_at": t.discovered_at.isoformat(),
            "language": t.language,
            "niche_guess": t.niche_guess,
            "latest_metrics": {
                "views": latest_snapshot.views if latest_snapshot else None,
                "likes": latest_snapshot.likes if latest_snapshot else None,
                "comments": latest_snapshot.comments if latest_snapshot else None,
                "shares": latest_snapshot.shares if latest_snapshot else None,
            } if latest_snapshot else {},
        })

    candidates = []
    for c in cluster.candidates:
        candidates.append({
            "id": str(c.id),
            "score": c.score,
            "confidence": c.confidence,
            "rationale": c.rationale,
            "status": c.status,
            "selected_for_date": c.selected_for_date.isoformat() if c.selected_for_date else None,
        })

    return {
        "id": str(cluster.id),
        "cluster_key": cluster.cluster_key,
        "title": cluster.title,
        "niche_id": str(cluster.niche_id) if cluster.niche_id else None,
        "trends": trends,
        "candidates": candidates,
        "created_at": cluster.created_at.isoformat(),
    }


@router.post("/clusters/{cluster_id}/assess")
async def assess_cluster(
    cluster_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Executa avaliação (scoring) de todas as tendências de um cluster via LLM."""
    assessments = await assess_cluster_trends(cluster_id)
    return {
        "cluster_id": str(cluster_id),
        "assessments_count": len(assessments),
        "assessments": [
            {
                "trend_id": str(a.trend_id),
                "score": a.score,
                "confidence": a.confidence,
                "signals": {
                    "growth": a.signals.growth,
                    "niche_fit": a.signals.niche_fit,
                    "engagement": a.signals.engagement,
                    "recency": a.signals.recency,
                    "production_feasibility": a.signals.production_feasibility,
                },
                "missing_signals": a.missing_signals,
                "rationale": a.rationale,
                "safety_flags": a.safety_flags,
                "model_version": a.model_version,
            }
            for a in assessments
        ],
    }


@router.post("/clusters/{cluster_id}/score", response_model=dict)
async def score_cluster(
    cluster_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Cria candidato a partir do melhor assessment do cluster (respeita quota diária)."""
    result = score_trends_use_case(cluster_id)
    return {
        "candidates_created": result.candidates_created,
        "top_candidate_id": str(result.top_candidate_id) if result.top_candidate_id else None,
        "error": result.error,
    }


@router.get("/{trend_id}", response_model=TrendItemResponse)
async def get_trend(
    trend_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> TrendItemResponse:
    """Obtém detalhes de uma tendência específica."""
    result = await db.execute(
        select(TrendItem).options(
            selectinload(TrendItem.snapshots),
            selectinload(TrendItem.cluster_items).selectinload(TrendClusterItem.cluster),
        ).where(TrendItem.id == trend_id)
    )
    trend = result.scalars().first()

    if not trend:
        raise HTTPException(status_code=404, detail="Tendência não encontrada")

    latest_snapshot = max(trend.snapshots, key=lambda s: s.captured_at) if trend.snapshots else None
    latest_metrics = None
    if latest_snapshot:
        from backend.app.schemas.trends import TrendMetrics
        latest_metrics = TrendMetrics(
            views=latest_snapshot.views,
            likes=latest_snapshot.likes,
            comments=latest_snapshot.comments,
            shares=latest_snapshot.shares,
        )

    cluster_id = None
    assessment = None
    if trend.cluster_items:
        cluster_id = trend.cluster_items[0].cluster_id
        candidate_result = await db.execute(
            select(ContentCandidate).where(ContentCandidate.cluster_id == cluster_id)
        )
        candidate = candidate_result.scalars().first()
        if candidate:
            assessment = TrendAssessmentV1(
                trace_id=UUID("00000000-0000-0000-0000-000000000000"),
                trend_id=trend.id,
                score=candidate.score,
                confidence=candidate.confidence,
                signals=TrendSignals(**candidate.evidence_json.get("signals", {})) if candidate.evidence_json.get("signals") else TrendSignals(growth=0, niche_fit=0, engagement=0, recency=0, production_feasibility=0),
                missing_signals=candidate.evidence_json.get("missing_signals", []),
                rationale=candidate.rationale,
                safety_flags=candidate.evidence_json.get("safety_flags", []),
                evidence_refs=candidate.evidence_json.get("evidence_refs", []),
                model_version=candidate.evidence_json.get("model_version", "unknown"),
            )

    return TrendItemResponse(
        id=trend.id,
        provider=trend.provider,
        source_id=trend.source_id,
        title=trend.title,
        url=trend.original_url,
        published_at=trend.published_at,
        discovered_at=trend.discovered_at,
        language=trend.language,
        niche_guess=trend.niche_guess,
        latest_metrics=latest_metrics or TrendMetrics(),
        cluster_id=cluster_id,
        assessment=assessment,
    )