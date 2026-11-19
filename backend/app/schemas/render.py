"""Schemas para renderização e qualidade (AGENTS.md seção 8)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.base import BaseSchema, TracedSchema, WithProjectId, WithRevision
from backend.app.domain.enums import VideoState


class RenderResultV1(TracedSchema, WithProjectId, WithRevision):
    """
    Resultado da renderização final (AGENTS.md: RenderResultV1).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    video_uri: str = Field(description="Caminho do MP4 final")
    sha256: str = Field(min_length=64, max_length=64, description="Hash do vídeo final")
    thumbnail_uri: str = Field(description="Caminho do thumbnail")
    duration_ms: int = Field(gt=0, description="Duração real em ms")
    video_codec: str = Field(description="Codec de vídeo (h264, libx264, etc)")
    audio_codec: str = Field(description="Codec de áudio (aac, libfdk_aac, etc)")
    width: int = Field(gt=0, description="Largura em pixels")
    height: int = Field(gt=0, description="Altura em pixels")
    fps: float = Field(default=30.0, gt=0)
    file_size_bytes: int = Field(ge=0)
    ffmpeg_cmd: str = Field(description="Comando FFmpeg usado para reprodução")
    render_time_ms: int = Field(ge=0, description="Tempo de renderização em ms")


class RenderPreset(BaseSchema):
    """Preset de configuração FFmpeg."""
    name: str
    video_codec: str = "libx264"
    video_codec_params: list[str] = Field(default_factory=lambda: ["-preset", "medium", "-crf", "23"])
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    fps: int = 30
    pixel_format: str = "yuv420p"
    profile: str = "high"
    level: str = "4.1"
    movflags: str = "+faststart"


# Presets padrão
DEFAULT_RENDER_PRESET = RenderPreset(
    name="tiktok_vertical_1080x1920",
    video_codec="libx264",
    video_codec_params=["-preset", "medium", "-crf", "23", "-profile:v", "high", "-level", "4.1"],
    audio_codec="aac",
    audio_bitrate="128k",
    fps=30,
    pixel_format="yuv420p",
)

NVENC_RENDER_PRESET = RenderPreset(
    name="tiktok_vertical_nvenc",
    video_codec="h264_nvenc",
    video_codec_params=["-preset", "p4", "-cq", "23", "-profile:v", "high", "-level", "4.1"],
    audio_codec="aac",
    audio_bitrate="128k",
    fps=30,
    pixel_format="yuv420p",
)


class RenderRequest(TracedSchema, WithProjectId, WithRevision):
    """Request para renderização."""
    preset_name: str = "tiktok_vertical_1080x1920"
    force_cpu: bool = False


class VideoProjectResponse(BaseSchema):
    """Resposta da API para projeto de vídeo."""
    id: UUID
    candidate_id: UUID
    revision: int
    state: VideoState
    target_duration_seconds: int
    video_hash: Optional[str] = None
    render_result: Optional[RenderResultV1] = None
    quality_report: Optional["QualityReportResponse"] = None
    created_at: datetime
    updated_at: datetime


# Forward ref
from backend.app.schemas.quality import QualityReportResponse
VideoProjectResponse.model_rebuild()