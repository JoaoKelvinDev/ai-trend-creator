"""Schemas para publicação (AGENTS.md seção 8)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.base import BaseSchema, TracedSchema, WithProjectId
from backend.app.domain.enums import PublicationMode, PublicationStatus


class PublicationRequestV1(TracedSchema, WithProjectId):
    """
    Request de publicação (AGENTS.md: PublicationRequestV1).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    revision: int
    video_sha256: str = Field(min_length=64, max_length=64)
    destination: str = Field(default="tiktok", description="Plataforma de destino")
    mode: PublicationMode = Field(default=PublicationMode.ASSISTED)
    caption: str = Field(min_length=1, max_length=2200)
    hashtags: list[str] = Field(default_factory=list, max_length=10)
    privacy_options: dict[str, Any] = Field(default_factory=dict)
    approved_at: datetime = Field(default_factory=lambda: datetime.now(tz=None).replace(tzinfo=None))


class PublicationResultV1(TracedSchema):
    """
    Resultado de publicação (AGENTS.md: PublicationResultV1).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    mode: PublicationMode
    status: PublicationStatus
    external_id: Optional[str] = Field(default=None, description="ID do post no TikTok (se official)")
    export_path: Optional[str] = Field(default=None, description="Caminho do pacote exportado (se assisted)")
    failure_code: Optional[str] = None
    evidence: dict[str, Any] = Field(default_factory=dict, description="Evidência da publicação")


class AssistedExportPackage(BaseSchema):
    """Pacote de exportação assistida."""
    video_path: str
    thumbnail_path: str
    caption: str
    hashtags: list[str]
    metadata_json: str  # JSON com metadados completos
    instructions: str = Field(description="Instruções para publicação manual")


class PublicationJobResponse(BaseSchema):
    """Resposta da API para job de publicação."""
    id: UUID
    project_id: UUID
    revision: int
    destination: str
    mode: PublicationMode
    status: PublicationStatus
    external_id: Optional[str] = None
    export_path: Optional[str] = None
    failure_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TikTokOAuthRequest(BaseSchema):
    """Request para iniciar OAuth TikTok."""
    redirect_uri: str
    state: str


class TikTokOAuthCallback(BaseSchema):
    """Callback do OAuth TikTok."""
    code: str
    state: str
    error: Optional[str] = None
    error_description: Optional[str] = None


class TikTokTokenResponse(BaseSchema):
    """Resposta de token TikTok."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int
    token_type: str = "Bearer"
    scope: str
    open_id: Optional[str] = None