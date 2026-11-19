"""Rotas para projetos de vídeo (placeholder - implementar nas Etapas 3-7)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.render import VideoProjectResponse
from backend.app.schemas.base import PaginatedResponse

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=PaginatedResponse[VideoProjectResponse])
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[VideoProjectResponse]:
    """Lista projetos de vídeo com estado e versões."""
    # TODO: Implementar na Etapa 3+
    return PaginatedResponse.create(items=[], total=0, page=page, page_size=page_size)


@router.get("/{video_id}", response_model=VideoProjectResponse)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> VideoProjectResponse:
    """Obtém detalhes completos de um projeto de vídeo (estado, versões, QA)."""
    # TODO: Implementar na Etapa 3+
    raise HTTPException(status_code=501, detail="Não implementado - aguardar Etapa 3+")


@router.post("/{video_id}/retry")
async def retry_video(
    video_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Retry controlado de etapa falhada."""
    # TODO: Implementar na Etapa 3+
    raise HTTPException(status_code=501, detail="Não implementado - aguardar Etapa 3+")


@router.post("/{video_id}/request-review")
async def request_review(
    video_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Solicita aprovação no Telegram para um vídeo."""
    # TODO: Implementar na Etapa 6
    raise HTTPException(status_code=501, detail="Não implementado - aguardar Etapa 6")