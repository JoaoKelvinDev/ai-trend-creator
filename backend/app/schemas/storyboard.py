"""Schemas para storyboard e assets (AGENTS.md seção 8)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from backend.app.schemas.base import BaseSchema, TracedSchema, WithProjectId, WithRevision
from backend.app.domain.enums import VisualKind, MediaAssetKind, LicenseType


class StoryboardSceneV1(BaseSchema):
    """Cena individual do storyboard (AGENTS.md seção 5.5)."""
    scene_id: str = Field(description="ID único da cena")
    order: int = Field(ge=0, description="Ordem na sequência")
    start_ms: int = Field(ge=0, description="Início em milissegundos")
    duration_ms: int = Field(gt=0, description="Duração em milissegundos")
    narration_segment: Optional[str] = Field(default=None, description="Texto de narração deste segmento")
    visual_kind: VisualKind = Field(description="Tipo de elemento visual")
    visual_prompt: Optional[str] = Field(default=None, max_length=2000, description="Prompt para geração de imagem/vídeo")
    overlay_text: Optional[str] = Field(default=None, max_length=200, description="Texto sobreposto na cena")
    asset_ref: Optional[UUID] = Field(default=None, description="Referência ao asset gerado")
    transition: str = Field(default="cut", description="Transição: cut|fade|slide|zoom")
    provenance: str = Field(default="generated", description="Origem: generated|licensed|template|user_provided")


class StoryboardV1(TracedSchema, WithProjectId, WithRevision):
    """
    Storyboard completo (AGENTS.md: StoryboardV1).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    scenes: list[StoryboardSceneV1] = Field(min_length=1, description="Cenas em ordem")
    total_duration_ms: int = Field(gt=0, description="Duração total em ms")
    license_manifest: list["LicenseEntry"] = Field(default_factory=list, description="Manifesto de licenças dos assets")


class LicenseEntry(BaseSchema):
    """Entrada de licença no manifesto."""
    asset_id: UUID
    license_type: LicenseType
    license_url: Optional[HttpUrl] = None
    author: Optional[str] = None
    version: Optional[str] = None
    commercial_use_allowed: bool = True
    attribution_required: bool = False
    attribution_text: Optional[str] = None


class AssetRequestV1(TracedSchema, WithProjectId):
    """
    Request para geração de asset (AGENTS.md: AssetRequestV1).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    scene_id: str
    kind: MediaAssetKind
    prompt: str = Field(min_length=1, max_length=2000)
    width: int = Field(default=1080, ge=640, le=2048)
    height: int = Field(default=1920, ge=640, le=2048)
    seed: Optional[int] = Field(default=None, ge=0, description="Seed para reprodutibilidade")
    style_reference: Optional[UUID] = Field(default=None, description="Asset de referência de estilo")
    negative_prompt: Optional[str] = Field(default=None, max_length=1000)
    steps: Optional[int] = Field(default=None, ge=1, le=100)
    cfg_scale: Optional[float] = Field(default=None, ge=1.0, le=20.0)


class AssetResultV1(TracedSchema):
    """
    Resultado de geração de asset (AGENTS.md: AssetResultV1).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    asset_id: UUID
    uri: str = Field(description="Caminho/localização do arquivo")
    sha256: str = Field(min_length=64, max_length=64, description="Hash SHA256 do arquivo")
    provider: str = Field(description="Provedor: comfyui|piper|template|mock")
    model_id: str = Field(description="ID do modelo usado")
    license_id: str = Field(description="Referência à licença")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadados extras (dims, duration, etc)")
    width: Optional[int] = None
    height: Optional[int] = None
    duration_ms: Optional[int] = None
    mime_type: Optional[str] = None


class MediaAssetResponse(BaseSchema):
    """Resposta da API para asset de mídia."""
    id: UUID
    project_id: UUID
    kind: MediaAssetKind
    uri: str
    sha256: str
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration_ms: Optional[int] = None
    provider: str
    model_id: str
    license_ref: str
    created_at: datetime