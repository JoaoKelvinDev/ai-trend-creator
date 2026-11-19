"""Pacote de banco de dados."""

from backend.app.db.session import (
    get_db_session,
    get_db_context,
    init_db,
    close_db,
    get_engine,
    get_session_factory,
)
from backend.app.db.redis import (
    get_redis,
    get_redis_context,
    init_redis,
    close_redis,
    get_redis_client,
)
from backend.app.db.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, utc_now
from backend.app.db.models import (
    Niche,
    SourceConfig,
    TrendItem,
    TrendSnapshot,
    TrendCluster,
    TrendClusterItem,
    ContentCandidate,
    VideoProject,
    Script,
    StoryboardScene,
    MediaAsset,
    Job,
    ApprovalRequest,
    ApprovalDecision,
    PublicationJob,
    WorkflowEvent,
    DailyQuota,
    ModelRegistry,
)

__all__ = [
    # Session
    "get_db_session",
    "get_db_context",
    "init_db",
    "close_db",
    "get_engine",
    "get_session_factory",
    # Redis
    "get_redis",
    "get_redis_context",
    "init_redis",
    "close_redis",
    "get_redis_client",
    # Base
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "utc_now",
    # Models
    "Niche",
    "SourceConfig",
    "TrendItem",
    "TrendSnapshot",
    "TrendCluster",
    "TrendClusterItem",
    "ContentCandidate",
    "VideoProject",
    "Script",
    "StoryboardScene",
    "MediaAsset",
    "Job",
    "ApprovalRequest",
    "ApprovalDecision",
    "PublicationJob",
    "WorkflowEvent",
    "DailyQuota",
    "ModelRegistry",
]