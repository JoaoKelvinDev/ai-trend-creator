"""Rotas para auditoria de aprovações (placeholder - implementar na Etapa 6)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.base import PaginatedResponse, BaseSchema
from backend.app.domain.enums import ApprovalDecision

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalAuditItem(BaseSchema):
    """Item de auditoria de aprovação."""
    id: str
    project_id: str
    revision: int
    video_sha256: str
    actor_id: int
    decision: ApprovalDecision
    feedback: str | None
    decided_at: str


@router.get("", response_model=PaginatedResponse[ApprovalAuditItem])
async def list_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[ApprovalAuditItem]:
    """Lista auditoria de decisões de aprovação."""
    # TODO: Implementar na Etapa 6
    return PaginatedResponse.create(items=[], total=0, page=page, page_size=page_size)