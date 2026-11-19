"""Rotas para candidatos a vídeo (placeholder - implementar nas Etapas 2-3)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.candidates import CandidateResponse
from backend.app.schemas.base import PaginatedResponse

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=PaginatedResponse[CandidateResponse])
async def list_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[CandidateResponse]:
    """Lista candidatos com ranking e status."""
    # TODO: Implementar na Etapa 2
    return PaginatedResponse.create(items=[], total=0, page=page, page_size=page_size)


@router.post("/{candidate_id}/produce", response_model=CandidateResponse)
async def produce_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> CandidateResponse:
    """Solicita produção de vídeo para um candidato (respeita quota diária)."""
    # TODO: Implementar nas Etapas 3-5
    raise HTTPException(status_code=501, detail="Não implementado - aguardar Etapas 3-5")


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> CandidateResponse:
    """Obtém detalhes de um candidato."""
    # TODO: Implementar na Etapa 2
    raise HTTPException(status_code=501, detail="Não implementado - aguardar Etapa 2")