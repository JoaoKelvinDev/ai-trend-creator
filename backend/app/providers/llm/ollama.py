"""Provedor LLM via Ollama local."""

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from backend.app.core.config import get_settings
from backend.app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaLLMProvider(LLMProvider):
    """Provedor que usa Ollama local para inferência."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ):
        settings = get_settings()
        self._base_url = base_url or settings.OLLAMA_BASE_URL
        self._model = model or settings.OLLAMA_MODEL
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def cost_class(self) -> str:
        return "zero"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout),
            )
        return self._client

    async def generate_structured(
        self,
        schema: type[BaseModel],
        prompt: str,
        context: dict[str, Any] | None = None,
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> BaseModel:
        """Gera resposta estruturada via Ollama com schema JSON."""
        client = await self._get_client()

        # Construir prompt com instruções de schema
        schema_json = schema.model_json_schema()
        system_prompt = self._build_system_prompt(schema_json, context)

        payload = {
            "model": self._model,
            "prompt": f"{system_prompt}\n\n{prompt}",
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 2048,
            },
        }

        try:
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extrair JSON da resposta
            content = data.get("response", "").strip()
            if not content:
                raise ValueError("Resposta vazia do Ollama")

            # Parsear e validar
            parsed = json.loads(content)
            return schema.model_validate(parsed)

        except json.JSONDecodeError as e:
            logger.error("Falha ao parsear JSON do Ollama", extra={"content": content[:500]})
            raise ValueError(f"Resposta não é JSON válido: {e}")
        except httpx.HTTPError as e:
            logger.error("Erro HTTP chamando Ollama", extra={"error": str(e)})
            raise
        except Exception as e:
            logger.error("Erro inesperado no Ollama", extra={"error": str(e)})
            raise

    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Gera texto livre via Ollama."""
        client = await self._get_client()

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 1024,
            },
        }

        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    async def health_check(self) -> bool:
        """Verifica se Ollama está rodando e modelo está disponível."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return any(self._model in m for m in models)
        except Exception as e:
            logger.warning("Health check Ollama falhou", extra={"error": str(e)})
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_system_prompt(self, schema_json: dict[str, Any], context: dict[str, Any] | None) -> str:
        """Constrói prompt de sistema com schema e contexto."""
        parts = [
            "Você é um assistente que responde APENAS com JSON válido.",
            "O JSON deve seguir exatamente este schema:",
            json.dumps(schema_json, ensure_ascii=False, indent=2),
            "",
            "REGRAS OBRIGATÓRIAS:",
            "1. Responda APENAS com o objeto JSON - sem markdown, sem explicações",
            "2. Todos os campos obrigatórios do schema devem estar presentes",
            "3. Tipos devem corresponder exatamente ao schema",
            "4. Enums devem usar valores válidos do schema",
            "5. Se não souber um valor, use null (se opcional) ou valor padrão razoável",
        ]

        if context:
            parts.extend([
                "",
                "CONTEXTO ADICIONAL:",
                json.dumps(context, ensure_ascii=False, indent=2),
            ])

        return "\n".join(parts)