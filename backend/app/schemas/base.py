"""Schemas base e utilitários para contratos Pydantic v2."""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Schema base com configurações padrão."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        ser_mode="json",
    )


class TimestampedSchema(BaseSchema):
    """Schema com timestamps padrão."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=None).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=None).replace(tzinfo=None))


class IdentifiedSchema(TimestampedSchema):
    """Schema com ID UUID."""

    id: UUID = Field(default_factory=uuid4)


class TracedSchema(BaseSchema):
    """Schema com trace_id para observabilidade."""

    trace_id: UUID = Field(default_factory=uuid4, description="ID de rastreamento distribuído")
    schema_version: str = Field(default="1.0", description="Versão do schema")


T = TypeVar("T", bound=BaseSchema)


class PaginatedResponse(BaseSchema, Generic[T]):
    """Resposta paginada genérica."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ErrorResponse(BaseSchema):
    """Resposta de erro padronizada."""

    error: dict[str, Any]

    @classmethod
    def from_exception(cls, exc: Exception, code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[dict] = None) -> "ErrorResponse":
        return cls(error={
            "code": code,
            "message": str(exc),
            "status_code": status_code,
            "details": details or {},
        })


class HealthResponse(BaseSchema):
    """Resposta de health check."""

    status: str
    service: str = "ai-trend-creator"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=None).replace(tzinfo=None))
    checks: dict[str, bool] = Field(default_factory=dict)


class ReadyResponse(HealthResponse):
    """Resposta de readiness check com dependências."""

    dependencies: dict[str, str] = Field(default_factory=dict)


# ──────────────────────────────────────────────
# Mixins comuns
# ──────────────────────────────────────────────

class WithTraceId(BaseSchema):
    trace_id: UUID = Field(default_factory=uuid4)


class WithWorkflowId(BaseSchema):
    workflow_id: UUID = Field(default_factory=uuid4)


class WithProjectId(BaseSchema):
    project_id: UUID


class WithRevision(BaseSchema):
    revision: int = Field(default=1, ge=1, description="Número da revisão (incrementa a cada regeneração)")


# ──────────────────────────────────────────────
# Validadores comuns
# ──────────────────────────────────────────────

def validate_positive_int(v: int) -> int:
    if v <= 0:
        raise ValueError("Deve ser um inteiro positivo")
    return v


def validate_non_empty_str(v: str) -> str:
    if not v or not v.strip():
        raise ValueError("String não pode ser vazia")
    return v.strip()


def validate_uuid_str(v: str) -> UUID:
    try:
        return UUID(v)
    except ValueError:
        raise ValueError("UUID inválido")


# ──────────────────────────────────────────────
# Tipos de resposta de API
# ──────────────────────────────────────────────

class APIResponse(BaseSchema, Generic[T]):
    """Wrapper padrão de resposta da API."""

    success: bool = True
    data: Optional[T] = None
    error: Optional[dict[str, Any]] = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T, meta: Optional[dict] = None) -> "APIResponse[T]":
        return cls(success=True, data=data, meta=meta or {})

    @classmethod
    def fail(cls, code: str, message: str, status_code: int = 400, details: Optional[dict] = None) -> "APIResponse[None]":
        return cls(success=False, data=None, error={
            "code": code,
            "message": message,
            "status_code": status_code,
            "details": details or {},
        })


# ──────────────────────────────────────────────
# Exportações
# ──────────────────────────────────────────────

__all__ = [
    "BaseSchema",
    "TimestampedSchema",
    "IdentifiedSchema",
    "TracedSchema",
    "PaginatedResponse",
    "ErrorResponse",
    "HealthResponse",
    "ReadyResponse",
    "WithTraceId",
    "WithWorkflowId",
    "WithProjectId",
    "WithRevision",
    "APIResponse",
]