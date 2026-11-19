"""Interface base para provedores de geração de imagem."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ImageSpec:
    """Especificação para geração de imagem."""
    prompt: str
    width: int = 1080
    height: int = 1920
    seed: int | None = None
    negative_prompt: str | None = None
    steps: int | None = None
    cfg_scale: float | None = None
    style_reference: str | None = None  # Path para image reference
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ImageResult:
    """Resultado de geração de imagem."""
    image_path: Path
    sha256: str
    mime_type: str
    width: int
    height: int
    provider: str
    model: str
    license_ref: str
    metadata: dict[str, Any] | None = None


class ImageProvider(ABC):
    """Interface para provedores de imagem (ComfyUI, Template, Mock)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provedor (ex: 'comfyui', 'template', 'mock')."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """ID do modelo/checkpoint sendo usado."""
        pass

    @property
    @abstractmethod
    def cost_class(self) -> str:
        """Classe de custo: 'zero' | 'paid'."""
        pass

    @property
    @abstractmethod
    def license(self) -> str:
        """Licença do modelo/checkpoint (ex: 'CC0', 'CC-BY-NC-4.0', 'custom')."""
        pass

    @abstractmethod
    async def generate_image(self, spec: ImageSpec) -> ImageResult:
        """
        Gera imagem conforme especificação.

        Args:
            spec: Especificação da imagem (prompt, dimensões, seed, etc.)

        Returns:
            ImageResult com caminho do arquivo, hash, metadados

        Raises:
            RuntimeError: Se geração falhar
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se o provedor está disponível."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Libera recursos."""
        pass