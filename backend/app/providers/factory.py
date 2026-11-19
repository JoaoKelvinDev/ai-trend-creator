"""Factory de providers com validação de custo zero (R$ 0 obrigatório)."""

import logging
from typing import Any
from uuid import UUID

from backend.app.core.config import get_settings
from backend.app.providers.discovery import (
    DiscoveryProvider,
    RSSDiscoveryProvider,
    ManualDiscoveryProvider,
    MockDiscoveryProvider,
    YouTubeDiscoveryProvider,
)
from backend.app.providers.llm import LLMProvider, OllamaLLMProvider, MockLLMProvider
from backend.app.providers.images import ImageProvider, TemplateImageProvider, MockImageProvider
from backend.app.providers.speech import SpeechProvider, MockSpeechProvider, PiperSpeechProvider
from backend.app.providers.storage import AssetStore, LocalAssetStore
from backend.app.providers.approvals import ApprovalProvider, MockApprovalProvider, TelegramApprovalProvider
from backend.app.providers.publishing import Publisher, AssistedPublisher

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory centralizada que instancia providers respeitando CONTROLES DE CUSTO R$ 0."""

    def __init__(self, settings=None):
        self._settings = settings or get_settings()
        self._cache: dict[str, Any] = {}

        # Validar controles de custo na inicialização
        violations = self._settings.validate_cost_controls()
        if violations:
            for v in violations:
                logger.warning("Violação de controle de custo", extra={"violation": v})
            if not self._settings.is_development:
                raise RuntimeError(f"Controles de custo violados: {violations}")

    # ──────────────────────────────────────────────
    # Discovery Providers
    # ──────────────────────────────────────────────

    def get_discovery_provider(self, provider_type: str = "auto", **kwargs) -> DiscoveryProvider:
        """Retorna provedor de descoberta.

        Args:
            provider_type: 'rss', 'manual', 'youtube', 'mock', 'auto'
            **kwargs: Argumentos específicos do provedor
        """
        cache_key = f"discovery:{provider_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if provider_type == "rss":
            provider = RSSDiscoveryProvider(**kwargs)
        elif provider_type == "manual":
            provider = ManualDiscoveryProvider(**kwargs)
        elif provider_type == "youtube":
            provider = YouTubeDiscoveryProvider(**kwargs)
        elif provider_type == "mock":
            provider = MockDiscoveryProvider(**kwargs)
        elif provider_type == "auto":
            # Prioridade: RSS se configurado, senão manual, senão youtube, senão mock
            if self._settings.RSS_ENABLED and self._settings.rss_feeds:
                provider = RSSDiscoveryProvider()
            elif self._settings.MANUAL_IMPORT_ENABLED:
                provider = ManualDiscoveryProvider()
            elif self._settings.YOUTUBE_ENABLED and self._settings.YOUTUBE_API_KEY:
                provider = YouTubeDiscoveryProvider()
            else:
                provider = MockDiscoveryProvider()
        else:
            raise ValueError(f"Tipo de discovery desconhecido: {provider_type}")

        self._validate_cost(provider)
        self._cache[cache_key] = provider
        return provider

    def get_all_discovery_providers(self) -> list[DiscoveryProvider]:
        """Retorna todos os provedores de descoberta habilitados."""
        providers = []

        if self._settings.RSS_ENABLED and self._settings.rss_feeds:
            providers.append(self.get_discovery_provider("rss"))

        if self._settings.MANUAL_IMPORT_ENABLED:
            providers.append(self.get_discovery_provider("manual"))

        if self._settings.YOUTUBE_ENABLED and self._settings.YOUTUBE_API_KEY:
            providers.append(self.get_discovery_provider("youtube"))

        # Sempre ter mock como fallback para testes
        if not providers:
            providers.append(self.get_discovery_provider("mock"))

        return providers

    # ──────────────────────────────────────────────
    # LLM Providers
    # ──────────────────────────────────────────────

    def get_llm_provider(self, provider_type: str = "auto", **kwargs) -> LLMProvider:
        """Retorna provedor LLM."""
        cache_key = f"llm:{provider_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if provider_type == "ollama":
            provider = OllamaLLMProvider(**kwargs)
        elif provider_type == "mock":
            provider = MockLLMProvider(**kwargs)
        elif provider_type == "auto":
            if self._settings.LLM_PROVIDER == "ollama":
                provider = OllamaLLMProvider()
            else:
                provider = MockLLMProvider()
        else:
            raise ValueError(f"Tipo de LLM desconhecido: {provider_type}")

        self._validate_cost(provider)
        self._cache[cache_key] = provider
        return provider

    # ──────────────────────────────────────────────
    # Image Providers
    # ──────────────────────────────────────────────

    def get_image_provider(self, provider_type: str = "auto", **kwargs) -> ImageProvider:
        """Retorna provedor de imagem."""
        cache_key = f"image:{provider_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if provider_type == "comfyui":
            # ComfyUI provider será implementado na Etapa 4
            raise NotImplementedError("ComfyUI provider será implementado na Etapa 4. Use 'template' ou 'mock'.")
        elif provider_type == "template":
            provider = TemplateImageProvider(**kwargs)
        elif provider_type == "mock":
            provider = MockImageProvider(**kwargs)
        elif provider_type == "auto":
            if self._settings.IMAGE_PROVIDER == "comfyui":
                raise NotImplementedError("ComfyUI não implementado ainda. Configure IMAGE_PROVIDER=template ou use mock.")
            elif self._settings.IMAGE_PROVIDER == "template":
                provider = TemplateImageProvider()
            else:
                provider = MockImageProvider()
        else:
            raise ValueError(f"Tipo de image provider desconhecido: {provider_type}")

        self._validate_cost(provider)
        self._cache[cache_key] = provider
        return provider

    # ──────────────────────────────────────────────
    # Speech Providers
    # ──────────────────────────────────────────────

    def get_speech_provider(self, provider_type: str = "auto", **kwargs) -> SpeechProvider:
        """Retorna provedor de TTS."""
        cache_key = f"speech:{provider_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if provider_type == "piper":
            provider = PiperSpeechProvider(**kwargs)
        elif provider_type == "mock":
            provider = MockSpeechProvider(**kwargs)
        elif provider_type == "auto":
            if self._settings.SPEECH_PROVIDER == "piper_local":
                provider = PiperSpeechProvider()
            else:
                provider = MockSpeechProvider()
        else:
            raise ValueError(f"Tipo de speech provider desconhecido: {provider_type}")

        self._validate_cost(provider)
        self._cache[cache_key] = provider
        return provider

    # ──────────────────────────────────────────────
    # Storage
    # ──────────────────────────────────────────────

    def get_asset_store(self) -> AssetStore:
        """Retorna storage de assets (singleton)."""
        if "asset_store" not in self._cache:
            self._cache["asset_store"] = LocalAssetStore()
        return self._cache["asset_store"]

    # ──────────────────────────────────────────────
    # Approval Providers
    # ──────────────────────────────────────────────

    def get_approval_provider(self, provider_type: str = "auto", **kwargs) -> ApprovalProvider:
        """Retorna provedor de aprovação."""
        cache_key = f"approval:{provider_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if provider_type == "telegram":
            provider = TelegramApprovalProvider(settings=self._settings, **kwargs)
        elif provider_type == "mock":
            provider = MockApprovalProvider(**kwargs)
        elif provider_type == "auto":
            if self._settings.TELEGRAM_ENABLED:
                provider = TelegramApprovalProvider(settings=self._settings)
            else:
                provider = MockApprovalProvider()
        else:
            raise ValueError(f"Tipo de approval provider desconhecido: {provider_type}")

        self._validate_cost(provider)
        self._cache[cache_key] = provider
        return provider

    # ──────────────────────────────────────────────
    # Publishing Providers
    # ──────────────────────────────────────────────

    def get_publisher(self, mode: str | None = None) -> Publisher:
        """Retorna publicador baseado no modo."""
        pub_mode = mode or self._settings.TIKTOK_PUBLISH_MODE
        cache_key = f"publisher:{pub_mode}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if pub_mode == "assisted":
            provider = AssistedPublisher()
        elif pub_mode == "official":
            # Official publisher só se elegível
            if not self._settings._is_official_publish_eligible():
                raise RuntimeError("Publicação oficial não elegível - verifique TikTok Client Key/Secret e aprovação de app")
            raise NotImplementedError("Official TikTok publisher será implementado após elegibilidade verificada")
        else:
            raise ValueError(f"Modo de publicação desconhecido: {pub_mode}")

        self._validate_cost(provider)
        self._cache[cache_key] = provider
        return provider

    # ──────────────────────────────────────────────
    # Validação de Custo (R$ 0 OBRIGATÓRIO)
    # ──────────────────────────────────────────────

    def _validate_cost(self, provider: Any) -> None:
        """Valida se provider respeita controle de custo zero."""
        if not hasattr(provider, "cost_class"):
            raise TypeError(f"Provider {type(provider).__name__} não tem atributo 'cost_class'")

        if provider.cost_class != "zero":
            if not self._settings.APP_ALLOW_PAID_PROVIDERS:
                raise RuntimeError(
                    f"Provider {type(provider).__name__} tem cost_class='{provider.cost_class}' "
                    f"mas APP_ALLOW_PAID_PROVIDERS=false (R$ 0 obrigatório). "
                    f"Não é permitido usar providers pagos."
                )
            logger.warning("Provider pago instanciado (ALLOW_PAID_PROVIDERS=true)", extra={
                "provider": type(provider).__name__,
                "cost_class": provider.cost_class,
            })

    # ──────────────────────────────────────────────
    # Utilitários
    # ──────────────────────────────────────────────

    def clear_cache(self) -> None:
        """Limpa cache de providers (útil para testes)."""
        self._cache.clear()

    def get_cached_providers(self) -> dict[str, str]:
        """Retorna lista de providers em cache."""
        return {k: type(v).__name__ for k, v in self._cache.items()}


# Instância singleton
_provider_factory: ProviderFactory | None = None


def get_provider_factory(settings=None) -> ProviderFactory:
    """Retorna instância singleton do factory."""
    global _provider_factory
    if _provider_factory is None:
        _provider_factory = ProviderFactory(settings=settings)
    return _provider_factory


def reset_provider_factory() -> None:
    """Reseta o factory singleton (útil para testes)."""
    global _provider_factory
    _provider_factory = None