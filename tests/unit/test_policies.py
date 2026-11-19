"""Testes unitários para políticas (quotas, estados, qualidade)."""

import pytest
from datetime import date, datetime, timezone
from uuid import uuid4

from backend.app.domain.policies.quotas import QuotaPolicy, QuotaLimits, DailyQuotaUsage, TimezonePolicy
from backend.app.domain.policies.states import StateMachine, VideoState, OptimisticLock
from backend.app.domain.policies.quality import (
    QualityPolicy,
    QualityThresholds,
    QualityReport,
    QualityCheck,
    QualitySeverity,
)


# ──────────────────────────────────────────────
# Testes de QuotaPolicy
# ──────────────────────────────────────────────

class TestQuotaPolicy:
    """Testes para política de quotas diárias."""

    def test_can_create_candidate_within_limit(self):
        policy = QuotaPolicy(QuotaLimits(daily_candidates=2))
        usage = DailyQuotaUsage(local_date=date.today(), candidates_created=1)
        can, error = policy.can_create_candidate(usage)
        assert can is True
        assert error is None

    def test_cannot_create_candidate_at_limit(self):
        policy = QuotaPolicy(QuotaLimits(daily_candidates=2))
        usage = DailyQuotaUsage(local_date=date.today(), candidates_created=2)
        can, error = policy.can_create_candidate(usage)
        assert can is False
        assert "Limite diário" in error

    def test_cannot_create_candidate_over_limit(self):
        policy = QuotaPolicy(QuotaLimits(daily_candidates=2))
        usage = DailyQuotaUsage(local_date=date.today(), candidates_created=3)
        can, error = policy.can_create_candidate(usage)
        assert can is False

    def test_can_regenerate_within_limit(self):
        policy = QuotaPolicy(QuotaLimits(max_regenerations_per_candidate=2))
        usage = DailyQuotaUsage(local_date=date.today(), regenerations_used={"cand-1": 1})
        can, error = policy.can_regenerate(usage, "cand-1")
        assert can is True

    def test_cannot_regenerate_at_limit(self):
        policy = QuotaPolicy(QuotaLimits(max_regenerations_per_candidate=2))
        usage = DailyQuotaUsage(local_date=date.today(), regenerations_used={"cand-1": 2})
        can, error = policy.can_regenerate(usage, "cand-1")
        assert can is False
        assert "Limite de" in error

    def test_record_candidate_created_increments(self):
        policy = QuotaPolicy()
        usage = DailyQuotaUsage(local_date=date.today(), candidates_created=0)
        policy.record_candidate_created(usage)
        assert usage.candidates_created == 1

    def test_record_regeneration_increments(self):
        policy = QuotaPolicy()
        usage = DailyQuotaUsage(local_date=date.today(), regenerations_used={})
        policy.record_regeneration(usage, "cand-1")
        assert usage.regenerations_used["cand-1"] == 1
        policy.record_regeneration(usage, "cand-1")
        assert usage.regenerations_used["cand-1"] == 2

    def test_get_remaining_candidates(self):
        policy = QuotaPolicy(QuotaLimits(daily_candidates=2))
        usage = DailyQuotaUsage(local_date=date.today(), candidates_created=1)
        assert policy.get_remaining_candidates(usage) == 1

    def test_get_remaining_regenerations(self):
        policy = QuotaPolicy(QuotaLimits(max_regenerations_per_candidate=2))
        usage = DailyQuotaUsage(local_date=date.today(), regenerations_used={"cand-1": 1})
        assert policy.get_remaining_regenerations(usage, "cand-1") == 1


# ──────────────────────────────────────────────
# Testes de TimezonePolicy
# ──────────────────────────────────────────────

class TestTimezonePolicy:
    """Testes para política de fuso horário."""

    def test_today_local_returns_date(self):
        policy = TimezonePolicy("UTC")
        today = policy.today_local()
        assert isinstance(today, date)

    def test_is_same_local_day_same_day(self):
        policy = TimezonePolicy("UTC")
        dt1 = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)
        dt2 = datetime(2026, 11, 17, 20, 0, tzinfo=timezone.utc)
        assert policy.is_same_local_day(dt1, dt2) is True

    def test_is_same_local_day_different_day(self):
        policy = TimezonePolicy("UTC")
        dt1 = datetime(2026, 11, 17, 23, 0, tzinfo=timezone.utc)
        dt2 = datetime(2026, 11, 18, 1, 0, tzinfo=timezone.utc)
        assert policy.is_same_local_day(dt1, dt2) is False

    def test_get_day_bounds_returns_utc(self):
        policy = TimezonePolicy("UTC")
        start, end = policy.get_day_bounds(date(2026, 11, 17))
        assert start.tzinfo == timezone.utc
        assert end.tzinfo == timezone.utc
        assert start.hour == 0
        assert end.hour == 23


# ──────────────────────────────────────────────
# Testes de StateMachine
# ──────────────────────────────────────────────

class TestStateMachine:
    """Testes para máquina de estados."""

    def setup_method(self):
        self.machine = StateMachine()

    def test_valid_transition_discovered_to_scored(self):
        result = self.machine.transition(VideoState.DISCOVERED, VideoState.SCORED)
        assert result.success is True
        assert result.new_state == VideoState.SCORED

    def test_valid_transition_scored_to_selected(self):
        result = self.machine.transition(VideoState.SCORED, VideoState.SELECTED)
        assert result.success is True

    def test_valid_transition_selected_to_scripted(self):
        result = self.machine.transition(VideoState.SELECTED, VideoState.SCRIPTED)
        assert result.success is True

    def test_valid_transition_scripted_to_storyboarded(self):
        result = self.machine.transition(VideoState.SCRIPTED, VideoState.STORYBOARDED)
        assert result.success is True

    def test_valid_transition_storyboarded_to_generating(self):
        result = self.machine.transition(VideoState.STORYBOARDED, VideoState.GENERATING_ASSETS)
        assert result.success is True

    def test_valid_transition_generating_to_rendering(self):
        result = self.machine.transition(VideoState.GENERATING_ASSETS, VideoState.RENDERING)
        assert result.success is True

    def test_valid_transition_rendering_to_quality_check(self):
        result = self.machine.transition(VideoState.RENDERING, VideoState.QUALITY_CHECK)
        assert result.success is True

    def test_valid_transition_quality_check_to_pending_approval(self):
        result = self.machine.transition(VideoState.QUALITY_CHECK, VideoState.PENDING_APPROVAL)
        assert result.success is True

    def test_valid_transition_pending_approval_to_approved(self):
        result = self.machine.transition(VideoState.PENDING_APPROVAL, VideoState.APPROVED)
        assert result.success is True

    def test_valid_transition_pending_approval_to_rejected(self):
        result = self.machine.transition(VideoState.PENDING_APPROVAL, VideoState.REJECTED)
        assert result.success is True

    def test_valid_transition_pending_approval_to_revision(self):
        result = self.machine.transition(VideoState.PENDING_APPROVAL, VideoState.REVISION_REQUESTED)
        assert result.success is True

    def test_invalid_transition_discovered_to_approved(self):
        result = self.machine.transition(VideoState.DISCOVERED, VideoState.APPROVED)
        assert result.success is False
        assert "Transição inválida" in result.error

    def test_invalid_transition_approved_to_discovered(self):
        result = self.machine.transition(VideoState.APPROVED, VideoState.DISCOVERED)
        assert result.success is False

    def test_same_state_transition(self):
        result = self.machine.transition(VideoState.SCORED, VideoState.SCORED)
        assert result.success is True
        assert result.new_state == VideoState.SCORED

    def test_force_transition_allows_invalid(self):
        result = self.machine.transition(VideoState.DISCOVERED, VideoState.APPROVED, force=True)
        assert result.success is True

    def test_is_terminal_rejected(self):
        assert self.machine.is_terminal(VideoState.REJECTED) is True

    def test_is_terminal_manually_published(self):
        assert self.machine.is_terminal(VideoState.MANUALLY_PUBLISHED) is True

    def test_is_not_terminal_scored(self):
        assert self.machine.is_terminal(VideoState.SCORED) is False

    def test_is_failure_state_retryable(self):
        assert self.machine.is_failure_state(VideoState.FAILED_RETRYABLE) is True

    def test_is_failure_state_terminal(self):
        assert self.machine.is_failure_state(VideoState.FAILED_TERMINAL) is True

    def test_is_not_failure_state_scored(self):
        assert self.machine.is_failure_state(VideoState.SCORED) is False

    def test_is_approval_state(self):
        assert self.machine.is_approval_state(VideoState.PENDING_APPROVAL) is True
        assert self.machine.is_approval_state(VideoState.APPROVED) is False

    def test_is_revision_state(self):
        assert self.machine.is_revision_state(VideoState.REVISION_REQUESTED) is True
        assert self.machine.is_revision_state(VideoState.PENDING_APPROVAL) is False

    def test_get_revision_target_state(self):
        target = self.machine.get_revision_target_state(VideoState.REVISION_REQUESTED)
        assert target == VideoState.GENERATING_ASSETS

    def test_validate_sequence_valid(self):
        states = [
            VideoState.DISCOVERED,
            VideoState.SCORED,
            VideoState.SELECTED,
            VideoState.SCRIPTED,
            VideoState.STORYBOARDED,
            VideoState.GENERATING_ASSETS,
            VideoState.RENDERING,
            VideoState.QUALITY_CHECK,
            VideoState.PENDING_APPROVAL,
            VideoState.APPROVED,
        ]
        valid, error = self.machine.validate_sequence(states)
        assert valid is True
        assert error is None

    def test_validate_sequence_invalid(self):
        states = [
            VideoState.DISCOVERED,
            VideoState.APPROVED,  # Inválido
        ]
        valid, error = self.machine.validate_sequence(states)
        assert valid is False
        assert "Transição inválida" in error


# ──────────────────────────────────────────────
# Testes de OptimisticLock
# ──────────────────────────────────────────────

class TestOptimisticLock:
    """Testes para controle de concorrência otimista."""

    def setup_method(self):
        self.lock = OptimisticLock()

    def test_get_version_new_entity(self):
        version = self.lock.get_version("entity-1")
        assert version == 0

    def test_increment_version(self):
        v1 = self.lock.increment_version("entity-1")
        v2 = self.lock.increment_version("entity-1")
        assert v1 == 1
        assert v2 == 2

    def test_check_and_increment_success(self):
        self.lock.increment_version("entity-1")  # v=1
        success, new_v = self.lock.check_and_increment("entity-1", 1)
        assert success is True
        assert new_v == 2

    def test_check_and_increment_failure_wrong_version(self):
        self.lock.increment_version("entity-1")  # v=1
        success, current_v = self.lock.check_and_increment("entity-1", 5)
        assert success is False
        assert current_v == 1


# ──────────────────────────────────────────────
# Testes de QualityPolicy
# ──────────────────────────────────────────────

class TestQualityPolicy:
    """Testes para política de qualidade."""

    def setup_method(self):
        self.policy = QualityPolicy()

    def test_check_resolution_pass(self):
        report = self.policy.create_report()
        self.policy.check_resolution(report, 1080, 1920)
        assert report.passed is True
        assert len(report.issues) == 0

    def test_check_resolution_fail_below_target(self):
        report = self.policy.create_report()
        self.policy.check_resolution(report, 720, 1280)
        assert report.passed is False
        assert any(i.check == QualityCheck.RESOLUTION and i.severity == QualitySeverity.BLOCKING for i in report.issues)

    def test_check_aspect_ratio_pass(self):
        report = self.policy.create_report()
        self.policy.check_aspect_ratio(report, 1080, 1920)
        assert report.passed is True

    def test_check_aspect_ratio_fail(self):
        report = self.policy.create_report()
        self.policy.check_aspect_ratio(report, 1920, 1080)  # Landscape
        assert report.passed is False
        assert any(i.check == QualityCheck.ASPECT_RATIO for i in report.issues)

    def test_check_duration_pass(self):
        report = self.policy.create_report()
        self.policy.check_duration(report, 30.0)
        assert report.passed is True

    def test_check_duration_fail_too_short(self):
        report = self.policy.create_report()
        self.policy.check_duration(report, 10.0)
        assert report.passed is False
        assert any(i.check == QualityCheck.DURATION for i in report.issues)

    def test_check_duration_fail_too_long(self):
        report = self.policy.create_report()
        self.policy.check_duration(report, 90.0)
        assert report.passed is False

    def test_check_video_codec_pass(self):
        report = self.policy.create_report()
        self.policy.check_video_codec(report, "h264")
        assert report.passed is True

    def test_check_video_codec_fail(self):
        report = self.policy.create_report()
        self.policy.check_video_codec(report, "vp9")
        assert report.passed is False
        assert any(i.check == QualityCheck.VIDEO_CODEC for i in report.issues)

    def test_check_audio_stream_pass(self):
        report = self.policy.create_report()
        self.policy.check_audio_stream(report, True, 128)
        assert report.passed is True

    def test_check_audio_stream_fail_no_audio(self):
        report = self.policy.create_report()
        self.policy.check_audio_stream(report, False)
        assert report.passed is False
        assert any(i.check == QualityCheck.AUDIO_STREAM for i in report.issues)

    def test_run_all_checks_pass(self):
        report = self.policy.run_all_checks(
            width=1080,
            height=1920,
            duration_seconds=30.0,
            video_codec="h264",
            audio_codec="aac",
            has_audio=True,
            audio_bitrate_kbps=128,
            file_size_bytes=5_000_000,
            ffprobe_ok=True,
            has_safe_margins=True,
            subtitle_file=None,
        )
        assert report.passed is True
        assert len(report.checks_performed) > 0

    def test_run_all_checks_fail_multiple(self):
        report = self.policy.run_all_checks(
            width=720,
            height=1280,  # Resolução baixa
            duration_seconds=10.0,  # Curto demais
            video_codec="vp9",  # Codec inválido
            audio_codec="aac",
            has_audio=False,  # Sem áudio
            audio_bitrate_kbps=None,
            file_size_bytes=50_000_000,  # Grande demais
            ffprobe_ok=False,  # Corrompido
            has_safe_margins=False,
            subtitle_file=None,
        )
        assert report.passed is False
        assert len(report.blocking_issues) >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])