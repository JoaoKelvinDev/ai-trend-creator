"""API v1 - Registro de rotas."""

from fastapi import APIRouter

from backend.app.api.v1.routes import (
    health,
    config,
    trends,
    candidates,
    videos,
    approvals,
    publications,
    quotas,
)

api_router = APIRouter(prefix="/api/v1")

# Health checks (sem prefixo /api/v1) - incluídos diretamente no app principal
# api_router.include_router(health.router)
api_router.include_router(config.router)

# Rotas funcionais
api_router.include_router(trends.router)
api_router.include_router(candidates.router)
api_router.include_router(videos.router)
api_router.include_router(approvals.router)
api_router.include_router(publications.router)
api_router.include_router(quotas.router)