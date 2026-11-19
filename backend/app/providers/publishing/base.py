"""Interface base para provedores de publicação/exportação."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class PublicationPackage:
    """Pacote pronto para publicação."""
    project_id: UUID
    revision: int
    video_path: Path
    thumbnail_path: Path | None
    caption: str
    hashtags: list[str]
    privacy_settings: dict[str, Any]
    export_dir: Path
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PublicationResult:
    """Resultado de publicação/exportação."""
    success: bool
    mode: str  # "assisted" | "official"
    external_id: str | None
    export_path: str | None
    error: str | None
    evidence: dict[str, Any]


class Publisher(ABC):
    """Interface para publicadores (Assisted, Official TikTok API)."""

    @property
    @abstractmethod
    def publisher_name(self) -> str:
        """Nome do publicador (ex: 'assisted', 'tiktok_official')."""
        pass

    @property
    @abstractmethod
    def cost_class(self) -> str:
        """Classe de custo: 'zero' | 'paid'."""
        pass

    @property
    @abstractmethod
    def mode(self) -> str:
        """Modo: 'assisted' | 'official'."""
        pass

    @abstractmethod
    async def prepare_package(self, package: PublicationPackage) -> PublicationResult:
        """
        Prepara pacote de publicação.

        Para 'assisted': cria pasta com vídeo, thumbnail, caption.txt, instruções
        Para 'official': faz upload via API
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se publicador está disponível."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Libera recursos."""
        pass