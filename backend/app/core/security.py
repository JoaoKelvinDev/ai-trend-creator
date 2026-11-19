"""Segurança: validação de entrada, sanitização, rate limiting básico."""

import html
import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class SafeUrl(BaseModel):
    """URL validada contra SSRF e esquemas perigosos."""

    url: str

    ALLOWED_SCHEMES = {"http", "https"}
    BLOCKED_HOSTS = {
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
    }
    BLOCKED_PRIVATE_RANGES = [
        re.compile(r"^10\."),
        re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\."),
        re.compile(r"^192\.168\."),
        re.compile(r"^127\."),
        re.compile(r"^169\.254\."),
        re.compile(r"^::1$"),
        re.compile(r"^fe80::"),
    ]

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        parsed = urlparse(v)

        # Esquema permitido
        if parsed.scheme not in cls.ALLOWED_SCHEMES:
            raise ValueError(f"Esquema não permitido: {parsed.scheme}. Use http ou https")

        # Host não pode ser localhost/privado
        hostname = parsed.hostname or ""
        if hostname.lower() in cls.BLOCKED_HOSTS:
            raise ValueError(f"Host bloqueado: {hostname}")

        # Verificar ranges privados
        for pattern in cls.BLOCKED_PRIVATE_RANGES:
            if pattern.match(hostname):
                raise ValueError(f"Endereço IP privado/bloqueado: {hostname}")

        # Porta padrão ou explícita (não portas suspeitas)
        port = parsed.port
        if port and port not in (80, 443, 8080, 8443):
            # Permitir mas logar warning
            pass

        return v


def sanitize_html(text: str) -> str:
    """Escapa HTML para prevenir XSS."""
    return html.escape(text, quote=True)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitiza nome de arquivo para storage seguro."""
    # Remover path traversal
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")
    # Remover caracteres de controle
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    # Limitar tamanho
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:max_length - len(ext) - 1] + ("." + ext if ext else "")
    return filename


def validate_no_shell_injection(text: str) -> str:
    """Valida que texto não contém injeção de shell."""
    dangerous = [";", "&", "|", "`", "$(", "${", ">", "<", "\n", "\r"]
    for char in dangerous:
        if char in text:
            raise ValueError(f"Caractere perigoso detectado: {repr(char)}")
    return text


class RateLimiter:
    """Rate limiter simples em memória (para desenvolvimento)."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        import time
        now = time.time()
        if key not in self._requests:
            self._requests[key] = []

        # Limpar requisições antigas
        self._requests[key] = [t for t in self._requests[key] if now - t < self.window_seconds]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def reset(self, key: str) -> None:
        self._requests.pop(key, None)


# Instância global para uso em desenvolvimento
dev_rate_limiter = RateLimiter(max_requests=200, window_seconds=60)