"""Enums do domínio - definições de tipos e estados."""

from enum import Enum


class TrendSource(str, Enum):
    """Fontes de descoberta de tendências."""
    YOUTUBE = "youtube"
    RSS = "rss"
    MANUAL = "manual"


class TrendLanguage(str, Enum):
    """Idiomas suportados."""
    PT = "pt"
    EN = "en"
    ES = "es"


class CandidateStatus(str, Enum):
    """Status do candidato a vídeo."""
    DISCOVERED = "discovered"
    SCORED = "scored"
    SELECTED = "selected"
    SCRIPTED = "scripted"
    STORYBOARDED = "storyboarded"
    GENERATING_ASSETS = "generating_assets"
    RENDERING = "rendering"
    QUALITY_CHECK = "quality_check"
    PENDING_APPROVAL = "pending_approval"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    READY_FOR_MANUAL_POST = "ready_for_manual_post"
    MANUALLY_PUBLISHED = "manually_published"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"


class VideoState(str, Enum):
    """Estados do projeto de vídeo (máquina de estados)."""
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


class ApprovalDecision(str, Enum):
    """Decisões de aprovação no Telegram."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"


class VisualKind(str, Enum):
    """Tipos de elementos visuais no storyboard."""
    LOCAL_AI_IMAGE = "local_ai_image"
    ORIGINAL_MOTION_GRAPHIC = "original_motion_graphic"
    LICENSED_USER_ASSET = "licensed_user_asset"
    TEXT_CARD = "text_card"
    LOCAL_AI_VIDEO = "local_ai_video"  # Futuro, desabilitado por padrão


class JobKind(str, Enum):
    """Tipos de jobs assíncronos."""
    DISCOVERY = "discovery"
    SCORING = "scoring"
    SCRIPTING = "scripting"
    STORYBOARDING = "storyboarding"
    ASSET_GENERATION = "asset_generation"
    RENDERING = "rendering"
    QUALITY_CHECK = "quality_check"
    TELEGRAM_NOTIFY = "telegram_notify"
    EXPORT = "export"


class JobStatus(str, Enum):
    """Status de execução de job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class PublicationMode(str, Enum):
    """Modos de publicação no TikTok."""
    ASSISTED = "assisted"
    OFFICIAL = "official"


class PublicationStatus(str, Enum):
    """Status de publicação."""
    PENDING = "pending"
    EXPORTED = "exported"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class NicheCategory(str, Enum):
    """Categorias de nicho configuráveis."""
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


class MediaAssetKind(str, Enum):
    """Tipos de assets de mídia."""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO_CLIP = "video_clip"
    THUMBNAIL = "thumbnail"
    SUBTITLE = "subtitle"
    MANIFEST = "manifest"


class LicenseType(str, Enum):
    """Tipos de licença conhecidos."""
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


# Transições permitidas da máquina de estados (AGENTS.md seção 6)
ALLOWED_TRANSITIONS: dict[VideoState, list[VideoState]] = {
    VideoState.DISCOVERED: [VideoState.SCORED, VideoState.FAILED_TERMINAL],
    VideoState.SCORED: [VideoState.SELECTED, VideoState.FAILED_TERMINAL],
    VideoState.SELECTED: [VideoState.SCRIPTED, VideoState.FAILED_TERMINAL],
    VideoState.SCRIPTED: [VideoState.STORYBOARDED, VideoState.FAILED_TERMINAL],
    VideoState.STORYBOARDED: [VideoState.GENERATING_ASSETS, VideoState.FAILED_TERMINAL],
    VideoState.GENERATING_ASSETS: [VideoState.RENDERING, VideoState.FAILED_RETRYABLE, VideoState.FAILED_TERMINAL],
    VideoState.RENDERING: [VideoState.QUALITY_CHECK, VideoState.FAILED_RETRYABLE, VideoState.FAILED_TERMINAL],
    VideoState.QUALITY_CHECK: [VideoState.PENDING_APPROVAL, VideoState.FAILED_RETRYABLE, VideoState.FAILED_TERMINAL],
    VideoState.PENDING_APPROVAL: [
        VideoState.REJECTED,
        VideoState.REVISION_REQUESTED,
        VideoState.APPROVED,
        VideoState.FAILED_TERMINAL,
    ],
    VideoState.REVISION_REQUESTED: [
        VideoState.GENERATING_ASSETS,
        VideoState.RENDERING,
        VideoState.QUALITY_CHECK,
        VideoState.PENDING_APPROVAL,
        VideoState.FAILED_TERMINAL,
    ],
    VideoState.APPROVED: [
        VideoState.READY_FOR_MANUAL_POST,
        VideoState.PUBLISHING,  # Somente se official habilitado
        VideoState.FAILED_TERMINAL,
    ],
    VideoState.READY_FOR_MANUAL_POST: [VideoState.MANUALLY_PUBLISHED, VideoState.FAILED_TERMINAL],
    VideoState.PUBLISHING: [VideoState.PUBLISHED, VideoState.FAILED_RETRYABLE, VideoState.FAILED_TERMINAL],
    # Estados terminais
    VideoState.REJECTED: [],
    VideoState.MANUALLY_PUBLISHED: [],
    VideoState.PUBLISHED: [],
    VideoState.FAILED_RETRYABLE: [VideoState.DISCOVERED],  # Retry vai para estado anterior apropriado
    VideoState.FAILED_TERMINAL: [],
}


def is_valid_transition(from_state: VideoState, to_state: VideoState) -> bool:
    """Verifica se uma transição de estado é permitida."""
    return to_state in ALLOWED_TRANSITIONS.get(from_state, [])


def get_allowed_next_states(state: VideoState) -> list[VideoState]:
    """Retorna estados permitidos a partir do estado atual."""
    return ALLOWED_TRANSITIONS.get(state, [])