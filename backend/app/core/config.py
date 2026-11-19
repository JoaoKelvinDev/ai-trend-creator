"""Configuração central da aplicação usando Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação carregadas do .env"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ──────────────────────────────────────────────
    # Aplicação
    # ──────────────────────────────────────────────
    APP_ENV: str = Field(default="development", description="Ambiente: development|staging|production")
    APP_TIMEZONE: str = Field(default="America/Sao_Paulo", description="Fuso horário IANA")
    APP_HOST: str = Field(default="127.0.0.1", description="Host do servidor")
    APP_PORT: int = Field(default=8000, description="Porta do servidor")

    # Controles de segurança e custo (R$ 0 obrigatório)
    APP_AUTO_PUBLISH: bool = Field(default=False, description="Publicação automática no TikTok")
    APP_CANDIDATE_LIMIT_PER_DAY: int = Field(default=2, ge=1, le=10, description="Limite de candidatos por dia")
    APP_MAX_REGENERATIONS_PER_CANDIDATE: int = Field(default=2, ge=0, le=5, description="Máximo de regenerações por candidato")
    APP_ALLOW_PAID_PROVIDERS: bool = Field(default=False, description="Permitir provedores pagos")
    APP_EXTERNAL_BILLING_ENABLED: bool = Field(default=False, description="Billing externo habilitado")
    APP_TIKTOK_DIRECT_POST_ENABLED: bool = Field(default=False, description="Post direto no TikTok habilitado")
    APP_LOCAL_VIDEO_DIFFUSION_ENABLED: bool = Field(default=False, description="Geração local de vídeo por difusão")

    # ──────────────────────────────────────────────
    # Banco de Dados e Filas
    # ──────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://app:app@127.0.0.1:5432/ai_trend_creator",
        description="URL de conexão PostgreSQL"
    )
    REDIS_URL: str = Field(default="redis://127.0.0.1:6379/0", description="URL de conexão Redis")
    LOCAL_STORAGE_ROOT: Path = Field(default=Path("./data"), description="Raiz do storage local")

    # ──────────────────────────────────────────────
    # Provedores de IA (Locais)
    # ──────────────────────────────────────────────
    LLM_PROVIDER: str = Field(default="ollama", description="Provedor LLM: ollama|mock")
    OLLAMA_BASE_URL: str = Field(default="http://127.0.0.1:11434", description="URL base do Ollama")
    OLLAMA_MODEL: str = Field(default="llama3.1:8b-instruct-q4_K_M", description="Modelo Ollama")

    IMAGE_PROVIDER: str = Field(default="comfyui_or_template", description="Provedor imagem: comfyui|template|mock")
    COMFYUI_URL: str = Field(default="http://127.0.0.1:8188", description="URL do ComfyUI")

    SPEECH_PROVIDER: str = Field(default="piper_local", description="Provedor speech: piper_local|mock")
    PIPER_VOICE: str = Field(default="pt_BR-faber-medium", description="Voz Piper")
    PIPER_BINARY_PATH: Path = Field(default=Path("./bin/piper"), description="Caminho do binário Piper")

    # ──────────────────────────────────────────────
    # Descoberta de Tendências
    # ──────────────────────────────────────────────
    YOUTUBE_ENABLED: bool = Field(default=False, description="Habilitar YouTube Data API")
    YOUTUBE_API_KEY: str = Field(default="", description="Chave da YouTube Data API")

    RSS_ENABLED: bool = Field(default=True, description="Habilitar feeds RSS")
    RSS_ALLOWED_FEEDS: List[str] = Field(default=[], description="URLs RSS permitidas")

    MANUAL_IMPORT_ENABLED: bool = Field(default=True, description="Habilitar importação manual")

    # ──────────────────────────────────────────────
    # Telegram Bot (Aprovação)
    # ──────────────────────────────────────────────
    TELEGRAM_ENABLED: bool = Field(default=False, description="Habilitar bot Telegram")
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Token do bot Telegram")
    TELEGRAM_ALLOWED_USER_IDS: Any = Field(default=[], description="User IDs permitidos")
    TELEGRAM_ALLOWED_CHAT_IDS: Any = Field(default=[], description="Chat IDs permitidos")
    TELEGRAM_POLLING_ENABLED: bool = Field(default=True, description="Usar long polling")
    TELEGRAM_WEBHOOK_URL: str = Field(default="", description="URL do webhook (se não polling)")

    # ──────────────────────────────────────────────
    # TikTok Publicação
    # ──────────────────────────────────────────────
    TIKTOK_PUBLISH_MODE: str = Field(default="assisted", description="Modo: assisted|official")
    TIKTOK_CLIENT_KEY: str = Field(default="", description="Client Key TikTok")
    TIKTOK_CLIENT_SECRET: str = Field(default="", description="Client Secret TikTok")
    TIKTOK_REDIRECT_URI: str = Field(default="http://127.0.0.1:8000/api/v1/auth/tiktok/callback")

    # ──────────────────────────────────────────────
    # Observabilidade
    # ──────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO", description="Nível de log")
    LOG_FORMAT: str = Field(default="json", description="Formato: json|text")
    METRICS_ENABLED: bool = Field(default=False, description="Habilitar métricas Prometheus")

    # ──────────────────────────────────────────────
    # Validators para parsing de CSV env vars
    # ──────────────────────────────────────────────
    @field_validator("RSS_ALLOWED_FEEDS", mode="before")
    @classmethod
    def parse_rss_feeds(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [feed.strip() for feed in v.split(",") if feed.strip()]
        return v

    @field_validator("TELEGRAM_ALLOWED_USER_IDS", "TELEGRAM_ALLOWED_CHAT_IDS", mode="before")
    @classmethod
    def parse_ids(cls, v: Any) -> List[int]:
        if v is None:
            return []
        if isinstance(v, list):
            return [int(x) for x in v if str(x).isdigit() or (str(x).startswith('-') and str(x)[1:].isdigit())]
        if isinstance(v, str):
            # Remove colchetes se houver [123, 456]
            cleaned = v.strip()
            if cleaned.startswith('[') and cleaned.endswith(']'):
                cleaned = cleaned[1:-1]
            return [int(x.strip()) for x in cleaned.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return []

    # ──────────────────────────────────────────────
    # Propriedades computadas
    # ──────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def rss_feeds(self) -> List[str]:
        return self.RSS_ALLOWED_FEEDS

    @property
    def allowed_user_ids(self) -> List[int]:
        return self.TELEGRAM_ALLOWED_USER_IDS

    @property
    def allowed_chat_ids(self) -> List[int]:
        return self.TELEGRAM_ALLOWED_CHAT_IDS

    def validate_cost_controls(self) -> List[str]:
        """Valida se controles de custo zero estão ativos. Retorna lista de violações."""
        violations = []
        if self.APP_ALLOW_PAID_PROVIDERS:
            violations.append("APP_ALLOW_PAID_PROVIDERS deve ser false (R$ 0 obrigatório)")
        if self.APP_EXTERNAL_BILLING_ENABLED:
            violations.append("APP_EXTERNAL_BILLING_ENABLED deve ser false")
        if self.APP_TIKTOK_DIRECT_POST_ENABLED and not self._is_official_publish_eligible():
            violations.append("APP_TIKTOK_DIRECT_POST_ENABLED requer elegibilidade oficial verificada")
        if self.APP_LOCAL_VIDEO_DIFFUSION_ENABLED:
            violations.append("APP_LOCAL_VIDEO_DIFFUSION_ENABLED deve ser false no MVP")
        return violations

    def _is_official_publish_eligible(self) -> bool:
        """Verifica se publicação oficial está elegível (placeholder para validação real)."""
        # TODO: Implementar verificação real de elegibilidade TikTok
        return bool(self.TIKTOK_CLIENT_KEY and self.TIKTOK_CLIENT_SECRET)


@lru_cache
def get_settings() -> Settings:
    """Retorna instância singleton das configurações."""
    return Settings()