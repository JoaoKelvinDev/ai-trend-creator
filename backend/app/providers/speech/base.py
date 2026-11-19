"""Interface base para provedores de síntese de fala (TTS)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SpeechSpec:
    """Especificação para síntese de fala."""
    text: str
    voice: str
    language: str = "pt-BR"
    speed: float = 1.0
    pitch: float = 1.0
    output_format: str = "wav"  # wav, mp3
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class SpeechResult:
    """Resultado de síntese de fala."""
    audio_path: Path
    sha256: str
    mime_type: str
    duration_ms: int
    sample_rate: int
    provider: str
    model: str
    voice: str
    license_ref: str
    metadata: dict[str, Any] | None = None


class SpeechProvider(ABC):
    """Interface para provedores de TTS (Piper, Mock, etc.)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provedor (ex: 'piper', 'mock')."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """ID do modelo/voz sendo usado."""
        pass

    @property
    @abstractmethod
    def cost_class(self) -> str:
        """Classe de custo: 'zero' | 'paid'."""
        pass

    @property
    @abstractmethod
    def license(self) -> str:
        """Licença do modelo/voz (ex: 'GPL-3.0', 'CC-BY-NC-4.0', 'MIT')."""
        pass

    @abstractmethod
    async def synthesize(self, spec: SpeechSpec) -> SpeechResult:
        """
        Sintetiza fala a partir de texto.

        Args:
            spec: Especificação (texto, voz, idioma, formato)

        Returns:
            SpeechResult com arquivo de áudio, duração, metadados
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

    @abstractmethod
    def get_available_voices(self) -> list[dict[str, Any]]:
        """Retorna vozes disponíveis com metadados (idioma, gênero, licença)."""
        pass