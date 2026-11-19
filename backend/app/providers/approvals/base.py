"""Interface base para provedores de aprovação (Telegram, CLI, etc.)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ApprovalRequest:
    """Solicitação de aprovação a ser enviada."""
    approval_id: UUID
    project_id: UUID
    revision: int
    video_path: Path
    thumbnail_path: Path | None
    title: str
    niche: str
    duration_seconds: float
    caption: str
    hashtags: list[str]
    sources_summary: str
    license_warnings: list[str]
    trace_id: str


@dataclass(frozen=True)
class ApprovalDecision:
    """Decisão de aprovação recebida."""
    approval_id: UUID
    action: str  # "approve", "reject", "request_revision"
    feedback: str | None
    actor_id: int
    decided_at: str


class ApprovalProvider(ABC):
    """Interface para provedores de aprovação humana."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provedor (ex: 'telegram', 'cli', 'mock')."""
        pass

    @property
    @abstractmethod
    def cost_class(self) -> str:
        """Classe de custo: 'zero' | 'paid'."""
        pass

    @abstractmethod
    async def send_for_approval(self, request: ApprovalRequest) -> bool:
        """
        Envia vídeo para aprovação humana.

        Returns:
            True se enviado com sucesso
        """
        pass

    @abstractmethod
    async def wait_for_decision(self, approval_id: UUID, timeout_seconds: int = 3600) -> ApprovalDecision | None:
        """
        Aguarda decisão (para polling/sync).
        Retorna None se timeout.
        """
        pass

    @abstractmethod
    async def cancel_approval(self, approval_id: UUID) -> bool:
        """Cancela solicitação pendente."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se provedor está disponível."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Libera recursos."""
        pass