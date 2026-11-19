"""Schemas para aprovação via Telegram (AGENTS.md seção 8)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.base import BaseSchema, TracedSchema, WithProjectId
from backend.app.domain.enums import ApprovalDecision, VideoState


class ApprovalDecisionV1(TracedSchema):
    """
    Decisão de aprovação (AGENTS.md: ApprovalDecisionV1).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    approval_id: UUID
    project_id: UUID
    revision: int
    video_sha256: str = Field(min_length=64, max_length=64, description="Hash do vídeo aprovado")
    actor_id: int = Field(description="Telegram user ID do decisor")
    decision: ApprovalDecision
    feedback: Optional[str] = Field(default=None, max_length=1000, description="Feedback se revisão solicitada")
    decided_at: datetime = Field(default_factory=lambda: datetime.now(tz=None).replace(tzinfo=None))


class ApprovalRequestV1(TracedSchema, WithProjectId):
    """
    Request de aprovação enviado ao Telegram (AGENTS.md seção 5.8).

    Schema versão 1.0.
    """
    schema_version: str = Field(default="1.0")
    approval_id: UUID
    revision: int
    video_sha256: str
    title: str
    niche: str
    duration_seconds: int
    sources_summary: str = Field(description="Resumo das fontes e justificativa")
    caption: str
    hashtags: list[str]
    ai_disclosure: str = Field(description="Aviso de conteúdo gerado por IA")
    rights_warnings: list[str] = Field(default_factory=list, description="Alertas de direitos")
    telegram_message_id: Optional[int] = None
    telegram_chat_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class ApprovalStatusResponse(BaseSchema):
    """Status de uma solicitação de aprovação."""
    approval_id: UUID
    project_id: UUID
    revision: int
    status: str  # pending|approved|rejected|revision_requested|expired
    decision: Optional[ApprovalDecision] = None
    feedback: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


class ApprovalCallbackData(BaseSchema):
    """Dados compactos no callback_data do botão Telegram."""
    approval_id: UUID
    action: ApprovalDecision
    version: int = 1  # Para invalidar callbacks antigos


class TelegramNotificationRequest(BaseSchema):
    """Request para enviar notificação no Telegram."""
    chat_id: int
    message: str
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    buttons: Optional[list[dict]] = None  # Inline keyboard buttons