"""Entry point da aplicação FastAPI."""

import asyncio
import sys

# Windows: psycopg requer SelectorEventLoop, não ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.core.logging import setup_logging, get_logger
from backend.app.core.exceptions import (
    AppException,
    EXCEPTION_STATUS_MAP,
)
from backend.app.db.session import init_db, close_db
from backend.app.db.redis import init_redis, close_redis
from backend.app.api.v1 import api_router
from backend.app.api.v1.routes import health

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    setup_logging()
    logger.info("Iniciando AI Trend Creator", extra={"version": "0.1.0", "env": settings.APP_ENV})

    # Validar controles de custo
    violations = settings.validate_cost_controls()
    if violations:
        for v in violations:
            logger.warning("Violação de controle de custo", extra={"violation": v})
        if not settings.is_development:
            raise RuntimeError(f"Controles de custo violados: {violations}")

    # Inicializar banco e Redis
    try:
        await init_db()
        logger.info("Banco de dados inicializado")
    except Exception as e:
        logger.error("Falha ao inicializar banco", extra={"error": str(e)})
        if not settings.is_development:
            raise

    try:
        await init_redis()
        logger.info("Redis conectado")
    except Exception as e:
        logger.error("Falha ao conectar Redis", extra={"error": str(e)})
        if not settings.is_development:
            raise

    logger.info("Aplicação pronta", extra={"host": settings.APP_HOST, "port": settings.APP_PORT})

    yield

    # Shutdown
    logger.info("Encerrando aplicação...")
    await close_redis()
    await close_db()
    logger.info("Aplicação encerrada")


def create_app() -> FastAPI:
    """Cria instância da aplicação FastAPI."""
    app = FastAPI(
        title="AI Trend Creator",
        description="Sistema automatizado de descoberta de tendências e produção de vídeos curtos com IA local",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS para desenvolvimento local
    if settings.is_development:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Middleware para trace_id
    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        import uuid
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        status_code = EXCEPTION_STATUS_MAP.get(type(exc), exc.status_code)
        return JSONResponse(
            status_code=status_code,
            content=exc.to_dict(),
            headers={"X-Trace-ID": getattr(request.state, "trace_id", "")},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Erro não tratado", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Erro interno do servidor"}},
            headers={"X-Trace-ID": getattr(request.state, "trace_id", "")},
        )

    # Registrar rotas
    app.include_router(health.router)  # Health checks sem prefixo /api/v1
    app.include_router(api_router)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": "ai-trend-creator",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs" if settings.is_development else "disabled",
        }

    return app


# Instância para uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )