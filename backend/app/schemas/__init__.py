"""Pacote de schemas - contratos Pydantic v2."""

from backend.app.schemas.base import (
    BaseSchema,
    TimestampedSchema,
    IdentifiedSchema,
    TracedSchema,
    PaginatedResponse,
    ErrorResponse,
    HealthResponse,
    ReadyResponse,
    APIResponse,
    WithTraceId,
    WithWorkflowId,
    WithProjectId,
    WithRevision,
)

from backend.app.schemas.trends import (
    TrendCandidateV1,
    TrendSnapshotV1,
    TrendClusterV1,
    TrendSignals,
    TrendAssessmentV1,
    TrendMetrics,
    TrendItemResponse,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
    TrendsListParams,
)

from backend.app.schemas.candidates import (
    ContentPlanV1,
    ScriptV1,
    NarrationSegment,
    OnScreenText,
    ClaimSource,
    CandidateResponse,
)

from backend.app.schemas.storyboard import (
    StoryboardSceneV1,
    StoryboardV1,
    LicenseEntry,
    AssetRequestV1,
    AssetResultV1,
    MediaAssetResponse,
)

from backend.app.schemas.render import (
    RenderResultV1,
    RenderPreset,
    DEFAULT_RENDER_PRESET,
    NVENC_RENDER_PRESET,
    RenderRequest,
    VideoProjectResponse,
)

from backend.app.schemas.quality import (
    QualityReportV1,
    QualityReportResponse,
    QualityIssueSchema,
    QualityCheckRequest,
)

from backend.app.schemas.approval import (
    ApprovalDecisionV1,
    ApprovalRequestV1,
    ApprovalStatusResponse,
    ApprovalCallbackData,
    TelegramNotificationRequest,
)

from backend.app.schemas.publication import (
    PublicationRequestV1,
    PublicationResultV1,
    AssistedExportPackage,
    PublicationJobResponse,
    TikTokOAuthRequest,
    TikTokOAuthCallback,
    TikTokTokenResponse,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampedSchema",
    "IdentifiedSchema",
    "TracedSchema",
    "PaginatedResponse",
    "ErrorResponse",
    "HealthResponse",
    "ReadyResponse",
    "APIResponse",
    "WithTraceId",
    "WithWorkflowId",
    "WithProjectId",
    "WithRevision",
    # Trends
    "TrendCandidateV1",
    "TrendSnapshotV1",
    "TrendClusterV1",
    "TrendSignals",
    "TrendAssessmentV1",
    "TrendMetrics",
    "TrendItemResponse",
    "DiscoveryRunRequest",
    "DiscoveryRunResponse",
    "TrendsListParams",
    # Candidates
    "ContentPlanV1",
    "ScriptV1",
    "NarrationSegment",
    "OnScreenText",
    "ClaimSource",
    "CandidateResponse",
    # Storyboard
    "StoryboardSceneV1",
    "StoryboardV1",
    "LicenseEntry",
    "AssetRequestV1",
    "AssetResultV1",
    "MediaAssetResponse",
    # Render
    "RenderResultV1",
    "RenderPreset",
    "DEFAULT_RENDER_PRESET",
    "NVENC_RENDER_PRESET",
    "RenderRequest",
    "VideoProjectResponse",
    # Quality
    "QualityReportV1",
    "QualityReportResponse",
    "QualityIssueSchema",
    "QualityCheckRequest",
    # Approval
    "ApprovalDecisionV1",
    "ApprovalRequestV1",
    "ApprovalStatusResponse",
    "ApprovalCallbackData",
    "TelegramNotificationRequest",
    # Publication
    "PublicationRequestV1",
    "PublicationResultV1",
    "AssistedExportPackage",
    "PublicationJobResponse",
    "TikTokOAuthRequest",
    "TikTokOAuthCallback",
    "TikTokTokenResponse",
]