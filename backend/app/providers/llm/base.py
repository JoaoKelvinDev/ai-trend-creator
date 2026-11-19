"""Interface base para provedores de LLM."""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Interface para provedores de LLM (Ollama, Mock, etc.)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provedor (ex: 'ollama', 'mock')."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """ID do modelo sendo usado."""
        pass

    @property
    @abstractmethod
    def cost_class(self) -> str:
        """Classe de custo: 'zero' | 'paid'."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        context: dict[str, Any] | None = None,
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> T:
        """
        Gera resposta estruturada validada pelo schema Pydantic.

        Args:
            schema: Classe Pydantic para validação da resposta
            prompt: Prompt principal
            context: Contexto adicional (dados, exemplos, etc.)
            temperature: Temperatura de geração
            max_tokens: Limite de tokens

        Returns:
            Instância do schema validada

        Raises:
            ValueError: Se resposta não validar contra o schema
        """
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Gera texto livre (para casos não estruturados)."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se o provedor está disponível."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Libera recursos (conexões, etc.)."""
        pass