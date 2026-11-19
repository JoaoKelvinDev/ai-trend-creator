"""Interface base para armazenamento de assets."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AssetMetadata:
    """Metadados de um asset armazenado."""
    asset_id: UUID
    kind: str
    sha256: str
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    duration_ms: int | None
    provider: str
    model: str
    license_ref: str
    created_at: str
    extra: dict[str, Any]


class AssetStore(ABC):
    """Interface para armazenamento de assets (local, S3, etc.)."""

    @property
    @abstractmethod
    def store_type(self) -> str:
        """Tipo de storage (ex: 'local', 's3')."""
        pass

    @abstractmethod
    async def put(self, file_path: Path, *, asset_id: UUID, kind: str, metadata: dict[str, Any]) -> AssetMetadata:
        """Armazena arquivo e retorna metadados."""
        pass

    @abstractmethod
    async def get(self, asset_id: UUID) -> Path | None:
        """Recupera caminho do arquivo local (ou faz download se remoto)."""
        pass

    @abstractmethod
    async def delete(self, asset_id: UUID) -> bool:
        """Remove asset. Retorna True se existia."""
        pass

    @abstractmethod
    async def get_metadata(self, asset_id: UUID) -> AssetMetadata | None:
        """Retorna metadados sem baixar arquivo."""
        pass

    @abstractmethod
    async def list_by_project(self, project_id: UUID) -> list[AssetMetadata]:
        """Lista assets de um projeto."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se storage está acessível."""
        pass