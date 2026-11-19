"""Modelos SQLAlchemy 2.x - Tabelas do AGENTS.md seção 7."""

import enum
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UUIDMixin, utc_now
from backend.app.domain.enums import (
    TrendSource,
    TrendLanguage,
    NicheCategory,
    CandidateStatus,
    VideoState,
    ApprovalDecision,
    VisualKind,
    JobKind,
    JobStatus,
    PublicationMode,
    PublicationStatus,
    MediaAssetKind,
    LicenseType,
)


# ──────────────────────────────────────────────
# Enums para SQLAlchemy (valores string)
# ──────────────────────────────────────────────

class TrendSourceEnum(enum.Enum):
    YOUTUBE = "youtube"
    RSS = "rss"
    MANUAL = "manual"


class TrendLanguageEnum(enum.Enum):
    PT = "pt"
    EN = "en"
    ES = "es"


class NicheCategoryEnum(enum.Enum):
    TECNOLOGIA = "tecnologia"
    CIENCIA = "ciencia"
    SAUDE = "saude"
    FINANCAS = "financas"
    EDUCACAO = "educacao"
    ENTRETENIMENTO = "entretenimento"
    ESPORTES = "esportes"
    MODA = "moda"
    VIAGENS = "viagens"
    CULINARIA = "culinaria"
    OUTROS = "outros"


class CandidateStatusEnum(enum.Enum):
    discovered = "discovered"
    scored = "scored"
    selected = "selected"
    scripted = "scripted"
    storyboarded = "storyboarded"
    generating_assets = "generating_assets"
    rendering = "rendering"
    quality_check = "quality_check"
    pending_approval = "pending_approval"
    rejected = "rejected"
    revision_requested = "revision_requested"
    approved = "approved"
    ready_for_manual_post = "ready_for_manual_post"
    manually_published = "manually_published"
    failed_retryable = "failed_retryable"
    failed_terminal = "failed_terminal"


class VideoStateEnum(enum.Enum):
    DISCOVERED = "DISCOVERED"
    SCORED = "SCORED"
    SELECTED = "SELECTED"
    SCRIPTED = "SCRIPTED"
    STORYBOARDED = "STORYBOARDED"
    GENERATING_ASSETS = "GENERATING_ASSETS"
    RENDERING = "RENDERING"
    QUALITY_CHECK = "QUALITY_CHECK"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REJECTED = "REJECTED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    APPROVED = "APPROVED"
    READY_FOR_MANUAL_POST = "READY_FOR_MANUAL_POST"
    MANUALLY_PUBLISHED = "MANUALLY_PUBLISHED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"


class ApprovalDecisionEnum(enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"


# VisualKind is imported from domain.enums, use it directly


class JobKindEnum(enum.Enum):
    DISCOVERY = "discovery"
    SCORING = "scoring"
    SCRIPTING = "scripting"
    STORYBOARDING = "storyboarding"
    ASSET_GENERATION = "asset_generation"
    RENDERING = "rendering"
    QUALITY_CHECK = "quality_check"
    TELEGRAM_NOTIFY = "telegram_notify"
    EXPORT = "export"


class JobStatusEnum(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class PublicationModeEnum(enum.Enum):
    ASSISTED = "assisted"
    OFFICIAL = "official"


class PublicationStatusEnum(enum.Enum):
    PENDING = "pending"
    EXPORTED = "exported"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class MediaAssetKindEnum(enum.Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO_CLIP = "video_clip"
    THUMBNAIL = "thumbnail"
    SUBTITLE = "subtitle"
    MANIFEST = "manifest"


class LicenseTypeEnum(enum.Enum):
    CC0 = "CC0"
    CC_BY = "CC-BY"
    CC_BY_SA = "CC-BY-SA"
    CC_BY_NC = "CC-BY-NC"
    GPL_3_0 = "GPL-3.0"
    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    CUSTOM = "custom"
    UNKNOWN = "unknown"
    PROPRIETARY = "proprietary"


# ──────────────────────────────────────────────
# Modelos
# ──────────────────────────────────────────────

class Niche(Base, UUIDMixin, TimestampMixin):
    """niches - Categorias de nicho configuráveis."""
    __tablename__ = "niches"

    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    weight: Mapped[float] = mapped_column(default=1.0, nullable=False)
    restrictions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    trend_clusters = relationship("TrendCluster", back_populates="niche")


class SourceConfig(Base, UUIDMixin, TimestampMixin):
    """source_configs - Configurações de fontes de descoberta."""
    __tablename__ = "source_configs"

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    configuration_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", name="uq_source_config_provider"),
        Index("ix_source_config_provider_enabled", "provider", "enabled"),
    )


class TrendItem(Base, UUIDMixin, TimestampMixin):
    """trend_items - Tendências coletadas."""
    __tablename__ = "trend_items"

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(10), default="pt", nullable=False)
    niche_guess: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "source_id", name="uq_trend_item_provider_source"),
        Index("ix_trend_item_discovered_niche", "discovered_at", "niche_guess"),
    )

    # Relationships
    snapshots = relationship("TrendSnapshot", back_populates="trend_item", cascade="all, delete-orphan")
    cluster_items = relationship("TrendClusterItem", back_populates="trend_item", cascade="all, delete-orphan")


class TrendSnapshot(Base, UUIDMixin):
    """trend_snapshots - Snapshots de métricas para calcular growth (imutáveis)."""
    __tablename__ = "trend_snapshots"

    trend_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trend_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    likes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shares: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_metrics_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    trend_item = relationship("TrendItem", back_populates="snapshots")

    __table_args__ = (
        Index("ix_trend_snapshot_item_captured", "trend_item_id", "captured_at"),
    )


class TrendCluster(Base, UUIDMixin, TimestampMixin):
    """trend_clusters - Clusters de tendências relacionadas."""
    __tablename__ = "trend_clusters"

    cluster_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    niche_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("niches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    niche = relationship("Niche", back_populates="trend_clusters")
    items = relationship("TrendClusterItem", back_populates="cluster", cascade="all, delete-orphan")
    candidates = relationship("ContentCandidate", back_populates="cluster")


class TrendClusterItem(Base, UUIDMixin, TimestampMixin):
    """trend_cluster_items - Associação cluster <-> trend_item."""
    __tablename__ = "trend_cluster_items"

    cluster_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trend_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trend_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trend_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    cluster = relationship("TrendCluster", back_populates="items")
    trend_item = relationship("TrendItem", back_populates="cluster_items")

    __table_args__ = (
        UniqueConstraint("cluster_id", "trend_item_id", name="uq_cluster_item"),
    )


class ContentCandidate(Base, UUIDMixin, TimestampMixin):
    """content_candidates - Candidatos selecionados para produção."""
    __tablename__ = "content_candidates"

    cluster_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trend_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    selected_for_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        Enum(CandidateStatusEnum, native_enum=False),
        default=CandidateStatusEnum.discovered.value,
        nullable=False,
        index=True,
    )

    # Relationships
    cluster = relationship("TrendCluster", back_populates="candidates")
    video_projects = relationship("VideoProject", back_populates="candidate", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_candidate_date_status", "selected_for_date", "status"),
    )


class VideoProject(Base, UUIDMixin, TimestampMixin):
    """video_projects - Projetos de vídeo (máquina de estados)."""
    __tablename__ = "video_projects"

    candidate_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("content_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state: Mapped[str] = mapped_column(
        Enum(VideoStateEnum, native_enum=False),
        default=VideoStateEnum.DISCOVERED.value,
        nullable=False,
        index=True,
    )
    target_duration_s: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    video_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA256
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Optimistic lock

    # Relationships
    candidate = relationship("ContentCandidate", back_populates="video_projects")
    scripts = relationship("Script", back_populates="project", cascade="all, delete-orphan")
    scenes = relationship("StoryboardScene", back_populates="project", cascade="all, delete-orphan")
    assets = relationship("MediaAsset", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")
    approval_requests = relationship("ApprovalRequest", back_populates="project", cascade="all, delete-orphan")
    publication_jobs = relationship("PublicationJob", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("candidate_id", "revision", name="uq_project_candidate_revision"),
        Index("ix_project_candidate_state", "candidate_id", "state"),
    )


class Script(Base, UUIDMixin, TimestampMixin):
    """scripts - Roteiros das versões."""
    __tablename__ = "scripts"

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    outline_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    script_text: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    duration_estimate_s: Mapped[float] = mapped_column(nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="scripts")

    __table_args__ = (
        UniqueConstraint("project_id", "revision", name="uq_script_project_revision"),
    )


class StoryboardScene(Base, UUIDMixin, TimestampMixin):
    """storyboard_scenes - Cenas do storyboard."""
    __tablename__ = "storyboard_scenes"

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    visual_kind: Mapped[VisualKind] = mapped_column(
        Enum(VisualKind, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    project = relationship("VideoProject", back_populates="scenes")
    asset = relationship("MediaAsset", back_populates="scenes")

    __table_args__ = (
        UniqueConstraint("project_id", "revision", "order_index", name="uq_scene_project_rev_order"),
        Index("ix_scene_project_rev", "project_id", "revision"),
    )


class MediaAsset(Base, UUIDMixin, TimestampMixin):
    """media_assets - Assets de mídia gerados."""
    __tablename__ = "media_assets"

    owner_project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[MediaAssetKind] = mapped_column(
        Enum(MediaAssetKind, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    license_ref: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="assets")
    scenes = relationship("StoryboardScene", back_populates="asset")

    __table_args__ = (
        Index("ix_asset_project_kind", "owner_project_id", "kind"),
    )


class Job(Base, UUIDMixin, TimestampMixin):
    """jobs - Jobs assíncronos (Celery/workers)."""
    __tablename__ = "jobs"

    kind: Mapped[str] = mapped_column(
        Enum(JobKindEnum, native_enum=False),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(JobStatusEnum, native_enum=False),
        default=JobStatusEnum.PENDING.value,
        nullable=False,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)

    # Relationships
    project = relationship("VideoProject", back_populates="jobs")

    __table_args__ = (
        Index("ix_job_kind_status", "kind", "status"),
    )


class ApprovalRequest(Base, UUIDMixin, TimestampMixin):
    """approval_requests - Solicitações de aprovação no Telegram."""
    __tablename__ = "approval_requests"

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    video_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )

    # Relationships
    project = relationship("VideoProject", back_populates="approval_requests")
    decisions = relationship("ApprovalDecision", back_populates="approval_request", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "revision", name="uq_approval_project_revision"),
    )


class ApprovalDecision(Base, UUIDMixin, TimestampMixin):
    """approval_decisions - Decisões de aprovação."""
    __tablename__ = "approval_decisions"

    approval_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(
        Enum(ApprovalDecisionEnum, native_enum=False),
        nullable=False,
    )
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    approval_request = relationship("ApprovalRequest", back_populates="decisions")


class PublicationJob(Base, UUIDMixin, TimestampMixin):
    """publication_jobs - Jobs de publicação/exportação."""
    __tablename__ = "publication_jobs"

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    destination: Mapped[str] = mapped_column(String(50), default="tiktok", nullable=False)
    mode: Mapped[str] = mapped_column(
        Enum(PublicationModeEnum, native_enum=False),
        default=PublicationModeEnum.ASSISTED.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(PublicationStatusEnum, native_enum=False),
        default=PublicationStatusEnum.PENDING.value,
        nullable=False,
        index=True,
    )
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    exported_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    project = relationship("VideoProject", back_populates="publication_jobs")

    __table_args__ = (
        UniqueConstraint("project_id", "revision", "destination", name="uq_pub_project_rev_dest"),
    )


class WorkflowEvent(Base, UUIDMixin, TimestampMixin):
    """workflow_events - Eventos de auditoria (event sourcing leve)."""
    __tablename__ = "workflow_events"

    aggregate_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_workflow_aggregate_occurred", "aggregate_id", "occurred_at"),
    )


class DailyQuota(Base, UUIDMixin, TimestampMixin):
    """daily_quotas - Quotas diárias por data local."""
    __tablename__ = "daily_quotas"

    local_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    candidates_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    regen_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_calls_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ModelRegistry(Base, UUIDMixin, TimestampMixin):
    """model_registry - Registro de modelos e licenças."""
    __tablename__ = "model_registry"

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    health_status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)

    __table_args__ = (
        UniqueConstraint("provider", "model_id", "version", name="uq_model_registry"),
    )