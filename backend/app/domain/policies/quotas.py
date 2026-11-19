"""Políticas de quota e limites diários."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from backend.app.core.config import get_settings
from backend.app.domain.enums import VideoState


@dataclass(frozen=True)
class QuotaLimits:
    """Limites de quota configuráveis."""
    daily_candidates: int = 2
    max_regenerations_per_candidate: int = 2
    max_retry_attempts: int = 3


@dataclass
class DailyQuotaUsage:
    """Uso de quota diária."""
    local_date: date
    candidates_created: int = 0
    regenerations_used: dict[str, int] = None  # candidate_id -> count

    def __post_init__(self):
        if self.regenerations_used is None:
            self.regenerations_used = {}


class QuotaPolicy:
    """Política de aplicação de quotas diárias."""

    def __init__(self, limits: Optional[QuotaLimits] = None):
        settings = get_settings()
        self.limits = limits or QuotaLimits(
            daily_candidates=settings.APP_CANDIDATE_LIMIT_PER_DAY,
            max_regenerations_per_candidate=settings.APP_MAX_REGENERATIONS_PER_CANDIDATE,
        )

    def can_create_candidate(self, usage: DailyQuotaUsage) -> tuple[bool, Optional[str]]:
        """Verifica se pode criar novo candidato hoje."""
        if usage.candidates_created >= self.limits.daily_candidates:
            return False, f"Limite diário de {self.limits.daily_candidates} candidatos atingido"
        return True, None

    def can_regenerate(self, usage: DailyQuotaUsage, candidate_id: str) -> tuple[bool, Optional[str]]:
        """Verifica se pode regenerar candidato específico."""
        current = usage.regenerations_used.get(candidate_id, 0)
        if current >= self.limits.max_regenerations_per_candidate:
            return False, f"Limite de {self.limits.max_regenerations_per_candidate} regenerações atingido para este candidato"
        return True, None

    def record_candidate_created(self, usage: DailyQuotaUsage) -> None:
        """Registra criação de candidato."""
        usage.candidates_created += 1

    def record_regeneration(self, usage: DailyQuotaUsage, candidate_id: str) -> None:
        """Registra regeneração de candidato."""
        usage.regenerations_used[candidate_id] = usage.regenerations_used.get(candidate_id, 0) + 1

    def get_remaining_candidates(self, usage: DailyQuotaUsage) -> int:
        """Retorna candidatos restantes para hoje."""
        return max(0, self.limits.daily_candidates - usage.candidates_created)

    def get_remaining_regenerations(self, usage: DailyQuotaUsage, candidate_id: str) -> int:
        """Retorna regenerações restantes para um candidato."""
        current = usage.regenerations_used.get(candidate_id, 0)
        return max(0, self.limits.max_regenerations_per_candidate - current)


class TimezonePolicy:
    """Política de fuso horário para quotas diárias."""

    def __init__(self, timezone_str: str = "America/Sao_Paulo"):
        self.timezone_str = timezone_str
        # Usar zoneinfo (Python 3.9+)
        try:
            from zoneinfo import ZoneInfo
            self.tz = ZoneInfo(timezone_str)
        except Exception:
            # Fallback para UTC se zoneinfo falhar
            import datetime
            self.tz = timezone.utc

    def now_local(self) -> datetime:
        """Retorna datetime atual no fuso configurado."""
        return datetime.now(self.tz)

    def today_local(self) -> date:
        """Retorna data de hoje no fuso configurado."""
        return self.now_local().date()

    def is_same_local_day(self, dt: datetime, reference: Optional[datetime] = None) -> bool:
        """Verifica se dois datetimes estão no mesmo dia local."""
        ref = reference or self.now_local()
        # Converter ambos para o fuso local
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        return dt.astimezone(self.tz).date() == ref.astimezone(self.tz).date()

    def get_day_bounds(self, local_date: Optional[date] = None) -> tuple[datetime, datetime]:
        """Retorna início e fim do dia local em UTC."""
        target_date = local_date or self.today_local()
        start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=self.tz)
        end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=self.tz)
        return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


# Instâncias globais para uso fácil
quota_policy = QuotaPolicy()
timezone_policy = TimezonePolicy()