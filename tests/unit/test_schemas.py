"""Testes unitários para schemas Pydantic."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.schemas.trends import (
    TrendCandidateV1,
    TrendSignals,
    TrendAssessmentV1,
    TrendMetrics,
)
from backend.app.schemas.candidates import (
    ContentPlanV1,
    ScriptV1,
    NarrationSegment,
)
from backend.app.schemas.storyboard import (
    StoryboardSceneV1,
    StoryboardV1,
    AssetRequestV1,
)
from backend.app.schemas.render import RenderResultV1
from backend.app.schemas.quality import QualityReportV1, QualityIssueSchema
from backend.app.schemas.approval import ApprovalDecisionV1, ApprovalRequestV1
from backend.app.schemas.publication import PublicationRequestV1, PublicationResultV1
from backend.app.domain.enums import (
    TrendSource, TrendLanguage, NicheCategory,
    CandidateStatus, VideoState, ApprovalDecision,
    VisualKind, MediaAssetKind, PublicationMode, PublicationStatus,
)


# ──────────────────────────────────────────────
# Testes TrendCandidateV1
# ──────────────────────────────────────────────

class TestTrendCandidateV1:
    def test_valid_candidate(self):
        candidate = TrendCandidateV1(
            trace_id=uuid4(),
            trend_id=uuid4(),
            source=TrendSource.RSS,
            external_id="test-123",
            title="Tendência válida",
            url="https://example.com/video",
            observed_at=datetime.now(timezone.utc),
            metrics=TrendMetrics(views=1000),
            language=TrendLanguage.PT,
            canonical_key="test-canonical-key-123",
        )
        assert candidate.title == "Tendência válida"
        assert candidate.source == TrendSource.RSS
        assert candidate.canonical_key == "test-canonical-key-123"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            TrendCandidateV1(
                trace_id=uuid4(),
                trend_id=uuid4(),
                source=TrendSource.RSS,
                external_id="test-123",
                title="Teste",
                url="not-a-url",
                observed_at=datetime.now(timezone.utc),
                canonical_key="test-canonical-key-123",
            )

    def test_empty_title_raises(self):
        with pytest.raises(ValueError):
            TrendCandidateV1(
                trace_id=uuid4(),
                trend_id=uuid4(),
                source=TrendSource.RSS,
                external_id="test-123",
                title="",
                url="https://example.com",
                observed_at=datetime.now(timezone.utc),
                canonical_key="test-canonical-key-123",
            )


# ──────────────────────────────────────────────
# Testes TrendSignals
# ──────────────────────────────────────────────

class TestTrendSignals:
    def test_valid_signals(self):
        signals = TrendSignals(
            growth=80.0,
            niche_fit=90.0,
            engagement=70.0,
            recency=85.0,
            production_feasibility=95.0,
        )
        assert signals.growth == 80.0

    def test_weighted_score_calculation(self):
        signals = TrendSignals(
            growth=100.0,
            niche_fit=100.0,
            engagement=100.0,
            recency=100.0,
            production_feasibility=100.0,
        )
        # 0.35*100 + 0.25*100 + 0.20*100 + 0.10*100 + 0.10*100 = 100
        assert signals.weighted_score() == 100.0

    def test_weighted_score_partial(self):
        signals = TrendSignals(
            growth=80.0,
            niche_fit=90.0,
            engagement=70.0,
            recency=85.0,
            production_feasibility=95.0,
        )
        expected = 0.35*80 + 0.25*90 + 0.20*70 + 0.10*85 + 0.10*95
        assert abs(signals.weighted_score() - expected) < 0.01

    def test_invalid_signal_range_raises(self):
        with pytest.raises(ValueError):
            TrendSignals(growth=150.0, niche_fit=50, engagement=50, recency=50, production_feasibility=50)

        with pytest.raises(ValueError):
            TrendSignals(growth=-10.0, niche_fit=50, engagement=50, recency=50, production_feasibility=50)


# ──────────────────────────────────────────────
# Testes TrendAssessmentV1
# ──────────────────────────────────────────────

class TestTrendAssessmentV1:
    def test_valid_assessment(self):
        assessment = TrendAssessmentV1(
            trace_id=uuid4(),
            trend_id=uuid4(),
            score=85.5,
            confidence=0.9,
            signals=TrendSignals(growth=80, niche_fit=90, engagement=70, recency=85, production_feasibility=95),
            rationale="Boa tendência com alto engagement",
            model_version="llama3.1:8b-instruct-q4_K_M",
        )
        assert assessment.score == 85.5
        assert assessment.confidence == 0.9

    def test_invalid_score_range_raises(self):
        with pytest.raises(ValueError):
            TrendAssessmentV1(
                trace_id=uuid4(),
                trend_id=uuid4(),
                score=150.0,  # Inválido
                confidence=0.9,
                signals=TrendSignals(growth=50, niche_fit=50, engagement=50, recency=50, production_feasibility=50),
                rationale="Teste",
                model_version="test",
            )


# ──────────────────────────────────────────────
# Testes ContentPlanV1
# ──────────────────────────────────────────────

class TestContentPlanV1:
    def test_valid_plan(self):
        plan = ContentPlanV1(
            trace_id=uuid4(),
            candidate_id=uuid4(),
            niche=NicheCategory.TECNOLOGIA,
            target_audience="Desenvolvedores interessados em IA",
            angle="Como a IA está transformando o desenvolvimento",
            hook="Você sabia que 80% do código pode ser gerado por IA?",
            key_claims=["IA gera código", "Produtividade aumenta 2x"],
            evidence_refs=["https://example.com/study"],
            duration_target_seconds=30,
            style="informativo_dinamico",
        )
        assert plan.niche == NicheCategory.TECNOLOGIA
        assert len(plan.key_claims) == 2


# ──────────────────────────────────────────────
# Testes ScriptV1 e NarrationSegment
# ──────────────────────────────────────────────

class TestScriptV1:
    def test_valid_script(self):
        script = ScriptV1(
            trace_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            narration_segments=[
                NarrationSegment(
                    segment_id="seg-1",
                    text="Olá, bem-vindos ao vídeo de hoje.",
                    start_estimate_ms=0,
                    duration_estimate_ms=3000,
                ),
                NarrationSegment(
                    segment_id="seg-2",
                    text="Hoje vamos falar sobre IA.",
                    start_estimate_ms=3000,
                    duration_estimate_ms=5000,
                ),
            ],
            title="IA no Desenvolvimento",
            caption="Descubra como a IA está mudando o jogo #IA #Tech",
            hashtags=["IA", "Tech", "Desenvolvimento"],
            duration_estimate_seconds=30.0,
        )
        assert len(script.narration_segments) == 2
        assert script.duration_estimate_seconds == 30.0


# ──────────────────────────────────────────────
# Testes StoryboardSceneV1
# ──────────────────────────────────────────────

class TestStoryboardSceneV1:
    def test_valid_scene(self):
        scene = StoryboardSceneV1(
            scene_id="scene-1",
            order=0,
            start_ms=0,
            duration_ms=5000,
            narration_segment="Olá, bem-vindos",
            visual_kind=VisualKind.LOCAL_AI_IMAGE,
            visual_prompt="Futuristic AI coding interface",
            overlay_text="IA no Desenvolvimento",
            transition="fade",
            provenance="generated",
        )
        assert scene.visual_kind == VisualKind.LOCAL_AI_IMAGE
        assert scene.duration_ms == 5000

    def test_invalid_duration_raises(self):
        with pytest.raises(ValueError):
            StoryboardSceneV1(
                scene_id="scene-1",
                order=0,
                start_ms=0,
                duration_ms=0,  # Inválido
                visual_kind=VisualKind.TEXT_CARD,
            )


# ──────────────────────────────────────────────
# Testes StoryboardV1
# ──────────────────────────────────────────────

class TestStoryboardV1:
    def test_valid_storyboard(self):
        storyboard = StoryboardV1(
            trace_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            scenes=[
                StoryboardSceneV1(
                    scene_id="scene-1",
                    order=0,
                    start_ms=0,
                    duration_ms=5000,
                    visual_kind=VisualKind.TEXT_CARD,
                ),
                StoryboardSceneV1(
                    scene_id="scene-2",
                    order=1,
                    start_ms=5000,
                    duration_ms=5000,
                    visual_kind=VisualKind.LOCAL_AI_IMAGE,
                ),
            ],
            total_duration_ms=10000,
        )
        assert len(storyboard.scenes) == 2
        assert storyboard.total_duration_ms == 10000


# ──────────────────────────────────────────────
# Testes AssetRequestV1
# ──────────────────────────────────────────────

class TestAssetRequestV1:
    def test_valid_asset_request(self):
        request = AssetRequestV1(
            project_id=uuid4(),
            scene_id="scene-2",
            kind=MediaAssetKind.IMAGE,
            prompt="Futuristic AI coding interface, neon colors",
            width=1080,
            height=1920,
            seed=42,
        )
        assert request.width == 1080
        assert request.height == 1920
        assert request.seed == 42


# ──────────────────────────────────────────────
# Testes RenderResultV1
# ──────────────────────────────────────────────

class TestRenderResultV1:
    def test_valid_render_result(self):
        result = RenderResultV1(
            trace_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            video_uri="/data/exports/video.mp4",
            sha256="a" * 64,
            thumbnail_uri="/data/exports/thumb.jpg",
            duration_ms=30000,
            video_codec="h264",
            audio_codec="aac",
            width=1080,
            height=1920,
            file_size_bytes=5000000,
            ffmpeg_cmd="ffmpeg -i ...",
            render_time_ms=15000,
        )
        assert result.width == 1080
        assert result.height == 1920


# ──────────────────────────────────────────────
# Testes QualityReportV1
# ──────────────────────────────────────────────

class TestQualityReportV1:
    def test_valid_quality_report(self):
        report = QualityReportV1(
            trace_id=uuid4(),
            project_id=uuid4(),
            passed=True,
            checks_performed=[],
            issues=[],
            warnings=[],
        )
        assert report.passed is True


# ──────────────────────────────────────────────
# Testes ApprovalDecisionV1
# ──────────────────────────────────────────────

class TestApprovalDecisionV1:
    def test_valid_approval_decision(self):
        decision = ApprovalDecisionV1(
            trace_id=uuid4(),
            approval_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            video_sha256="a" * 64,
            actor_id=123456789,
            decision=ApprovalDecision.APPROVE,
            feedback="Vídeo aprovado",
        )
        assert decision.decision == ApprovalDecision.APPROVE

    def test_revision_decision_requires_feedback(self):
        decision = ApprovalDecisionV1(
            trace_id=uuid4(),
            approval_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            video_sha256="a" * 64,
            actor_id=123456789,
            decision=ApprovalDecision.REQUEST_REVISION,
            feedback="Mudar a cor do texto",
        )
        assert decision.feedback == "Mudar a cor do texto"


# ──────────────────────────────────────────────
# Testes ApprovalRequestV1
# ──────────────────────────────────────────────

class TestApprovalRequestV1:
    def test_valid_approval_request(self):
        request = ApprovalRequestV1(
            trace_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            approval_id=uuid4(),
            video_sha256="a" * 64,
            title="Título do vídeo",
            niche="tecnologia",
            duration_seconds=30,
            sources_summary="Fonte: YouTube Trending",
            caption="Legenda do vídeo",
            hashtags=["tech", "ia"],
            ai_disclosure="Conteúdo gerado por IA",
        )
        assert request.niche == "tecnologia"


# ──────────────────────────────────────────────
# Testes PublicationRequestV1
# ──────────────────────────────────────────────

class TestPublicationRequestV1:
    def test_valid_publication_request(self):
        request = PublicationRequestV1(
            trace_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            video_sha256="a" * 64,
            destination="tiktok",
            mode=PublicationMode.ASSISTED,
            caption="Legenda para TikTok",
            hashtags=["tech", "ia"],
        )
        assert request.mode == PublicationMode.ASSISTED


# ──────────────────────────────────────────────
# Testes PublicationResultV1
# ──────────────────────────────────────────────

class TestPublicationResultV1:
    def test_valid_publication_result_assisted(self):
        result = PublicationResultV1(
            trace_id=uuid4(),
            mode=PublicationMode.ASSISTED,
            status=PublicationStatus.EXPORTED,
            export_path="/data/exports/package.zip",
        )
        assert result.mode == PublicationMode.ASSISTED
        assert result.status == PublicationStatus.EXPORTED

    def test_valid_publication_result_official(self):
        result = PublicationResultV1(
            trace_id=uuid4(),
            mode=PublicationMode.OFFICIAL,
            status=PublicationStatus.PUBLISHED,
            external_id="tiktok-123456",
        )
        assert result.mode == PublicationMode.OFFICIAL
        assert result.external_id == "tiktok-123456"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])