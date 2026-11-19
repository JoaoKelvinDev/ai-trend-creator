"""Exceções customizadas da aplicação."""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Exceção base da aplicação."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# ──────────────────────────────────────────────
# Erros de Configuração
# ──────────────────────────────────────────────

class ConfigurationError(AppException):
    """Erro de configuração inválida."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", 500, details)


class CostControlViolationError(AppException):
    """Violação de controle de custo (R$ 0)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "COST_CONTROL_VIOLATION", 403, details)


# ──────────────────────────────────────────────
# Erros de Validação
# ──────────────────────────────────────────────

class ValidationError(AppException):
    """Erro de validação de entrada."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", 422, details)
        if field:
            self.details["field"] = field


class SchemaValidationError(AppException):
    """Erro de validação de schema Pydantic."""

    def __init__(self, message: str, errors: list, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SCHEMA_VALIDATION_ERROR", 422, details)
        self.details["validation_errors"] = errors


# ──────────────────────────────────────────────
# Erros de Recurso
# ──────────────────────────────────────────────

class NotFoundError(AppException):
    """Recurso não encontrado."""

    def __init__(self, resource: str, identifier: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"{resource} não encontrado: {identifier}",
            "NOT_FOUND",
            404,
            details or {"resource": resource, "identifier": identifier},
        )


class ConflictError(AppException):
    """Conflito de recurso (ex: duplicata)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT", 409, details)


# ──────────────────────────────────────────────
# Erros de Estado / Workflow
# ──────────────────────────────────────────────

class InvalidStateTransitionError(AppException):
    """Transição de estado inválida."""

    def __init__(
        self,
        current_state: str,
        attempted_state: str,
        allowed_states: list[str],
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Transição inválida: {current_state} -> {attempted_state}. Permitidos: {allowed_states}"
        super().__init__(message, "INVALID_STATE_TRANSITION", 400, details)
        self.details.update({
            "current_state": current_state,
            "attempted_state": attempted_state,
            "allowed_states": allowed_states,
        })


class QuotaExceededError(AppException):
    """Quota diária excedida."""

    def __init__(self, quota_type: str, limit: int, current: int, details: Optional[Dict[str, Any]] = None):
        message = f"Quota {quota_type} excedida: {current}/{limit}"
        super().__init__(message, "QUOTA_EXCEEDED", 429, details)
        self.details.update({
            "quota_type": quota_type,
            "limit": limit,
            "current": current,
        })


class ApprovalRequiredError(AppException):
    """Aprovação humana necessária antes de prosseguir."""

    def __init__(self, resource_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Aprovação necessária para {resource_id}",
            "APPROVAL_REQUIRED",
            403,
            details or {"resource_id": resource_id},
        )


# ──────────────────────────────────────────────
# Erros de Provedores Externos
# ──────────────────────────────────────────────

class ProviderError(AppException):
    """Erro genérico de provedor externo."""

    def __init__(
        self,
        provider: str,
        message: str,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True,
    ):
        super().__init__(message, f"{provider.upper()}_ERROR", status_code, details)
        self.details.update({"provider": provider, "retryable": retryable})


class ProviderUnavailableError(ProviderError):
    """Provedor indisponível."""

    def __init__(self, provider: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(provider, f"Provedor {provider} indisponível", 503, details, retryable=True)


class ProviderQuotaExceededError(ProviderError):
    """Quota do provedor excedida."""

    def __init__(self, provider: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(provider, f"Quota do provedor {provider} excedida", 429, details, retryable=False)


class ProviderInvalidResponseError(ProviderError):
    """Resposta inválida do provedor."""

    def __init__(self, provider: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(provider, f"Resposta inválida de {provider}: {message}", 502, details, retryable=False)


# ──────────────────────────────────────────────
# Erros de Processamento de Mídia
# ──────────────────────────────────────────────

class MediaProcessingError(AppException):
    """Erro no processamento de mídia (FFmpeg, etc)."""

    def __init__(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "MEDIA_PROCESSING_ERROR", 500, details)
        self.details.update({"operation": operation})


class AssetGenerationError(MediaProcessingError):
    """Erro na geração de asset (imagem, áudio, vídeo)."""

    def __init__(
        self,
        asset_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(f"generate_{asset_type}", message, details)
        self.details.update({"asset_type": asset_type})
        self.code = "ASSET_GENERATION_ERROR"


class RenderError(MediaProcessingError):
    """Erro na renderização final do vídeo."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("render", message, details)
        self.code = "RENDER_ERROR"


# ──────────────────────────────────────────────
# Erros de Telegram
# ────────────────────────────────────────────__

class TelegramError(AppException):
    """Erro na API do Telegram."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, retryable: bool = True):
        super().__init__(message, "TELEGRAM_ERROR", 502, details)
        self.details.update({"retryable": retryable})


class TelegramUnauthorizedError(TelegramError):
    """Bot não autorizado ou token inválido."""

    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__("Bot Telegram não autorizado", details, retryable=False)
        self.status_code = 401
        self.code = "TELEGRAM_UNAUTHORIZED"


class TelegramForbiddenError(TelegramError):
    """Usuário/chat não permitido."""

    def __init__(self, user_id: int, chat_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Acesso negado para user_id={user_id}, chat_id={chat_id}",
            details or {"user_id": user_id, "chat_id": chat_id},
            retryable=False,
        )
        self.status_code = 403
        self.code = "TELEGRAM_FORBIDDEN"


# ──────────────────────────────────────────────
# Erros de TikTok
# ──────────────────────────────────────────────

class TikTokError(AppException):
    """Erro na API do TikTok."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "TIKTOK_ERROR", 502, details)


class TikTokNotEligibleError(TikTokError):
    """Conta/app não elegível para publicação direta."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Não elegível para publicação direta: {reason}", details)
        self.code = "TIKTOK_NOT_ELIGIBLE"
        self.status_code = 403


# ──────────────────────────────────────────────
# Mapeamento para handlers FastAPI
# ────────────────────────

EXCEPTION_STATUS_MAP = {
    ConfigurationError: 500,
    CostControlViolationError: 403,
    ValidationError: 422,
    SchemaValidationError: 422,
    NotFoundError: 404,
    ConflictError: 409,
    InvalidStateTransitionError: 400,
    QuotaExceededError: 429,
    ApprovalRequiredError: 403,
    ProviderError: 502,
    ProviderUnavailableError: 503,
    ProviderQuotaExceededError: 429,
    ProviderInvalidResponseError: 502,
    MediaProcessingError: 500,
    AssetGenerationError: 500,
    RenderError: 500,
    TelegramError: 502,
    TelegramUnauthorizedError: 401,
    TelegramForbiddenError: 403,
    TikTokError: 502,
    TikTokNotEligibleError: 403,
}