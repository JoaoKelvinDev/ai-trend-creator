"""Rotas para status de publicação (placeholder - implementar na Etapa 7)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.publication import PublicationJobResponse
from backend.app.schemas.base import PaginatedResponse

router = APIRouter(prefix="/publications", tags=["publications"])


@router.get("", response_model=PaginatedResponse[PublicationJobResponse])
async def list_publications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[PublicationJobResponse]:
    """Lista status de exportação/publicação."""
    # TODO: Implementar na Etapa 7
    return PaginatedResponse.create(items=[], total=0, page=page, page_size=page_size)