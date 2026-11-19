"""Base declarativa e mixins para modelos SQLAlchemy 2.x."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos."""
    pass


class UUIDMixin:
    """Mixin para ID UUID."""

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Identificador único universal",
    )


class TimestampMixin:
    """Mixin para timestamps created_at/updated_at."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp de criação (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp de atualização (UTC)",
    )


class SoftDeleteMixin:
    """Mixin para soft delete."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp de deleção lógica (UTC)",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# Função helper para timestamps UTC
def utc_now() -> datetime:
    return datetime.now(timezone.utc)