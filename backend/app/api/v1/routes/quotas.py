"""Rotas para uso de quotas diárias."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.schemas.base import BaseSchema
from backend.app.domain.policies.quotas import quota_policy, timezone_policy

router = APIRouter(prefix="/quotas", tags=["quotas"])


class QuotaUsageResponse(BaseSchema):
    """Resposta de uso de quota."""
    local_date: str
    candidates_created: int
    candidates_remaining: int
    limit: int
    regenerations: dict[str, int]


@router.get("", response_model=QuotaUsageResponse)
async def get_quota_usage(
    db: AsyncSession = Depends(get_db_session),
) -> QuotaUsageResponse:
    """Retorna uso de quota do dia atual (fuso local)."""
    # TODO: Implementar consulta real ao banco (tabela daily_quotas)
    today = timezone_policy.today_local()
    # Placeholder - implementar na Etapa 1/2
    return QuotaUsageResponse(
        local_date=today.isoformat(),
        candidates_created=0,
        candidates_remaining=quota_policy.limits.daily_candidates,
        limit=quota_policy.limits.daily_candidates,
        regenerations={},
    )