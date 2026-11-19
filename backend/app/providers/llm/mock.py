"""Provedor LLM mock para testes determinísticos."""

import logging
from typing import Any, TypeVar

from pydantic import BaseModel

from backend.app.providers.llm.base import LLMProvider

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class MockLLMProvider(LLMProvider):
    """Provedor mock que retorna respostas fixas para testes."""

    def __init__(
        self,
        responses: dict[type[BaseModel], BaseModel] | None = None,
        default_response: BaseModel | None = None,
        should_fail: bool = False,
    ):
        self._responses = responses or {}
        self._default_response = default_response
        self._should_fail = should_fail
        self._call_log: list[dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_id(self) -> str:
        return "mock-model-v1"

    @property
    def cost_class(self) -> str:
        return "zero"

    async def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        context: dict[str, Any] | None = None,
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> T:
        self._call_log.append({
            "schema": schema.__name__,
            "prompt": prompt[:200],
            "context_keys": list(context.keys()) if context else [],
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        if self._should_fail:
            raise RuntimeError("MockLLMProvider configured to fail")

        # Buscar resposta específica para este schema
        if schema in self._responses:
            return self._responses[schema]

        # Usar resposta padrão se fornecida
        if self._default_response and isinstance(self._default_response, schema):
            return self._default_response

        # Gerar resposta válida baseada no schema (valores padrão)
        return self._generate_default(schema)

    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        self._call_log.append({
            "type": "text",
            "prompt": prompt[:200],
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        if self._should_fail:
            raise RuntimeError("MockLLMProvider configured to fail")

        return "Resposta mock gerada para teste."

    async def health_check(self) -> bool:
        return not self._should_fail

    async def close(self) -> None:
        pass

    def _generate_default(self, schema: type[T]) -> T:
        """Gera instância com valores padrão baseados no schema."""
        from datetime import datetime
        from uuid import uuid4

        # Valores padrão por tipo de campo
        defaults = {}
        for field_name, field_info in schema.model_fields.items():
            annotation = field_info.annotation
            default = field_info.default

            if default is not None and default != ...:
                defaults[field_name] = default
            elif hasattr(annotation, "__origin__"):  # Optional, List, etc.
                origin = annotation.__origin__
                if origin is list:
                    defaults[field_name] = []
                elif origin is dict:
                    defaults[field_name] = {}
            elif annotation is str:
                defaults[field_name] = f"mock_{field_name}"
            elif annotation is int:
                defaults[field_name] = 1
            elif annotation is float:
                defaults[field_name] = 1.0
            elif annotation is bool:
                defaults[field_name] = True
            elif annotation is datetime:
                defaults[field_name] = datetime.now()
            elif "UUID" in str(annotation):
                defaults[field_name] = uuid4()
            else:
                defaults[field_name] = None

        return schema.model_validate(defaults)

    def set_response(self, schema: type[BaseModel], response: BaseModel) -> None:
        """Define resposta específica para um schema."""
        self._responses[schema] = response

    def set_default_response(self, response: BaseModel) -> None:
        """Define resposta padrão."""
        self._default_response = response

    def set_should_fail(self, should_fail: bool) -> None:
        """Configura se deve falhar."""
        self._should_fail = should_fail

    def get_call_log(self) -> list[dict[str, Any]]:
        return self._call_log

    def clear_call_log(self) -> None:
        self._call_log.clear()