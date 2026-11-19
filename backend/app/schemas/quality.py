"""Schemas para relatório de qualidade (AGENTS.md seção 8)."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.base import BaseSchema, TracedSchema, WithProjectId
from backend.app.domain.policies.quality import QualityCheck, QualitySeverity


class QualityIssueSchema(BaseSchema):
    """Problema de qualidade serializável."""
    check: QualityCheck
    severity: QualitySeverity
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None


class QualityReportV1(TracedSchema, WithProjectId):
    """
    Relatório de qualidade (AGENTS.md: QualityReportV1).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    passed: bool
    checks_performed: list[QualityCheck] = Field(default_factory=list)
    issues: list[QualityIssueSchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QualityReportResponse(BaseSchema):
    """Resposta da API para relatório de qualidade."""
    project_id: UUID
    passed: bool
    checks_performed: list[str]
    issues: list[QualityIssueSchema]
    warnings: list[str]
    checked_at: str  # ISO format


class QualityCheckRequest(TracedSchema, WithProjectId):
    """Request para executar quality check."""
    video_path: str
    subtitle_path: Optional[str] = None
    check_safe_margins: bool = True