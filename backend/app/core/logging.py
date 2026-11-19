"""Configuração de logging estruturado em JSON."""

import logging
import logging.config
import sys
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

from backend.app.core.config import get_settings


class SensitiveDataFilter(logging.Filter):
    """Filtra dados sensíveis dos logs."""

    SENSITIVE_KEYS = {
        "password", "secret", "token", "key", "api_key", "apikey",
        "authorization", "auth", "credential", "private",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        # Filtrar args se for dict
        if hasattr(record, "args") and isinstance(record.args, dict):
            record.args = self._sanitize_dict(record.args)
        # Filtrar message se for dict
        if isinstance(record.msg, dict):
            record.msg = self._sanitize_dict(record.msg)
        return True

    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            else:
                sanitized[key] = value
        return sanitized


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Formatter JSON customizado com campos padrão."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)

        # Campos padrão
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Trace ID se disponível (adicionado via contextvars no middleware)
        if hasattr(record, "trace_id"):
            log_record["trace_id"] = record.trace_id
        if hasattr(record, "workflow_id"):
            log_record["workflow_id"] = record.workflow_id
        if hasattr(record, "project_id"):
            log_record["project_id"] = record.project_id


def setup_logging() -> None:
    """Configura logging global da aplicação."""
    settings = get_settings()

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if settings.LOG_FORMAT == "json":
        formatter_class = CustomJsonFormatter
        fmt = "%(timestamp)s %(level)s %(logger)s %(message)s"
    else:
        formatter_class = logging.Formatter
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": formatter_class,
                "format": fmt,
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "filters": {
            "sensitive_filter": {
                "()": SensitiveDataFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "filters": ["sensitive_filter"],
                "level": log_level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
        "loggers": {
            "uvicorn": {"level": "INFO", "propagate": True},
            "uvicorn.error": {"level": "INFO", "propagate": True},
            "uvicorn.access": {"level": "WARNING", "propagate": True},
            "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
            "sqlalchemy.pool": {"level": "WARNING", "propagate": True},
            "celery": {"level": "INFO", "propagate": True},
            "httpx": {"level": "WARNING", "propagate": True},
            "httpcore": {"level": "WARNING", "propagate": True},
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Retorna logger configurado."""
    return logging.getLogger(name)