"""Testes unitários para TelegramApprovalProvider."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from backend.app.providers.approvals.base import ApprovalDecision, ApprovalRequest
from backend.app.providers.approvals.telegram import PendingApproval, TelegramApprovalProvider


class TestTelegramApprovalProvider:
    """Testes para o provedor de aprovação via Telegram."""

    @pytest.fixture
    def mock_settings(self):
        """Mock das configurações para testes."""
        with patch("backend.app.providers.approvals.telegram.get_settings") as mock:
            settings = MagicMock()
            settings.TELEGRAM_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
            settings.TELEGRAM_ALLOWED_USER_IDS = [123456789]
            settings.TELEGRAM_ALLOWED_CHAT_IDS = [-1001234567890]
            settings.TELEGRAM_POLLING_ENABLED = True
            mock.return_value = settings
            yield mock

    @pytest.fixture
    def provider(self, mock_settings):
        """Instancia o provider com configurações de teste."""
        return TelegramApprovalProvider()

    @pytest.fixture
    def sample_approval_request(self):
        """Cria uma ApprovalRequest de exemplo."""
        return ApprovalRequest(
            approval_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            video_path=Path("/fake/video.mp4"),
            thumbnail_path=Path("/fake/thumb.jpg"),
            title="Vídeo de teste",
            niche="tecnologia",
            duration_seconds=30.0,
            caption="Legenda do vídeo",
            hashtags=["#tech", "#ia"],
            sources_summary="Fonte: YouTube",
            license_warnings=[],
            trace_id="test-trace-123",
        )

    def test_provider_initialization(self, provider):
        """Testa se o provider inicializa corretamente."""
        assert provider.provider_name == "telegram"
        assert provider.cost_class == "zero"
        assert provider._allowed_user_ids == {123456789}
        assert provider._allowed_chat_ids == {-1001234567890}
        assert not provider._started

    def test_provider_requires_token(self, mock_settings):
        """Testa se falha quando token não configurado."""
        mock_settings.return_value.TELEGRAM_BOT_TOKEN = ""
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN não configurado"):
            TelegramApprovalProvider()

    def test_provider_requires_user_whitelist(self, mock_settings):
        """Testa se falha quando whitelist de usuários não configurada."""
        mock_settings.return_value.TELEGRAM_ALLOWED_USER_IDS = []
        with pytest.raises(ValueError, match="TELEGRAM_ALLOWED_USER_IDS não configurado"):
            TelegramApprovalProvider()

    def test_provider_requires_chat_whitelist(self, mock_settings):
        """Testa se falha quando whitelist de chats não configurada."""
        mock_settings.return_value.TELEGRAM_ALLOWED_CHAT_IDS = []
        with pytest.raises(ValueError, match="TELEGRAM_ALLOWED_CHAT_IDS não configurado"):
            TelegramApprovalProvider()

    @pytest.mark.asyncio
    async def test_start_creates_bot_and_dispatcher(self, provider):
        """Testa se start() cria bot e dispatcher."""
        with patch("backend.app.providers.approvals.telegram.Bot") as mock_bot_class, \
             patch("backend.app.providers.approvals.telegram.Dispatcher") as mock_dp_class, \
             patch("asyncio.create_task") as mock_create_task:

            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_bot.get_me = AsyncMock(return_value=MagicMock(id=123, username="test_bot"))
            mock_bot.delete_webhook = AsyncMock()

            mock_dp = MagicMock()
            mock_dp_class.return_value = mock_dp
            mock_dp.include_router = MagicMock()

            await provider.start()

            assert provider._started is True
            assert provider._bot is mock_bot
            assert provider._dp is mock_dp
            mock_bot.delete_webhook.assert_called_once_with(drop_pending_updates=True)
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_closes_bot(self, provider):
        """Testa se stop() fecha o bot corretamente."""
        mock_bot = AsyncMock()
        mock_bot.session.close = AsyncMock()
        provider._bot = mock_bot
        provider._started = True

        # Não criar polling task real - apenas testar que session.close é chamado
        provider._polling_task = None

        await provider.stop()

        assert provider._started is False
        mock_bot.session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_for_approval_requires_started(self, provider, sample_approval_request):
        """Testa se send_for_approval inicia o bot se necessário."""
        with patch.object(provider, "start", new_callable=AsyncMock) as mock_start:
            mock_start.return_value = None
            # Não podemos testar o envio real sem mockar o bot completamente
            # Mas verificamos que start é chamado
            provider._started = False
            # O método falhará porque video_path não existe, mas start deve ser chamado
            try:
                await provider.send_for_approval(sample_approval_request)
            except Exception:
                pass
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_for_approval_fails_if_video_not_exists(self, provider, sample_approval_request):
        """Testa se falha quando arquivo de vídeo não existe."""
        provider._started = True
        provider._bot = AsyncMock()

        result = await provider.send_for_approval(sample_approval_request)

        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_decision_returns_decision(self, provider, sample_approval_request):
        """Testa se wait_for_decision retorna a decisão."""
        approval_id = sample_approval_request.approval_id

        # Criar pending mock
        pending = PendingApproval(
            request=sample_approval_request,
            event=asyncio.Event(),
        )
        decision = ApprovalDecision(
            approval_id=approval_id,
            action="approve",
            feedback="Teste",
            actor_id=123456789,
            decided_at="2026-01-01T00:00:00Z",
        )
        pending.decision = decision
        pending.event.set()

        provider._pending[approval_id] = pending

        result = await provider.wait_for_decision(approval_id, timeout_seconds=1)

        assert result is not None
        assert result.action == "approve"

    @pytest.mark.asyncio
    async def test_wait_for_decision_timeout(self, provider, sample_approval_request):
        """Testa timeout em wait_for_decision."""
        approval_id = sample_approval_request.approval_id

        pending = PendingApproval(
            request=sample_approval_request,
            event=asyncio.Event(),
        )
        provider._pending[approval_id] = pending

        result = await provider.wait_for_decision(approval_id, timeout_seconds=0)

        assert result is not None
        assert result.action == "timeout"

    @pytest.mark.asyncio
    async def test_cancel_approval(self, provider, sample_approval_request):
        """Testa cancelamento de aprovação pendente."""
        approval_id = sample_approval_request.approval_id

        pending = PendingApproval(
            request=sample_approval_request,
            event=asyncio.Event(),
            message_id=123,
            chat_id=-1001234567890,
        )
        provider._pending[approval_id] = pending
        provider._bot = AsyncMock()
        provider._bot.delete_message = AsyncMock()

        result = await provider.cancel_approval(approval_id)

        assert result is True
        assert pending.decision is not None
        assert pending.decision.action == "cancel"
        provider._bot.delete_message.assert_called_once_with(-1001234567890, 123)

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        """Testa health_check."""
        provider._started = True
        mock_bot = AsyncMock()
        mock_bot.get_me = AsyncMock(return_value=MagicMock(id=123))
        provider._bot = mock_bot

        result = await provider.health_check()

        assert result is True
        mock_bot.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_fails_when_not_started(self, provider):
        """Testa health_check quando não iniciado."""
        provider._started = False
        result = await provider.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_close_clears_pending(self, provider, sample_approval_request):
        """Testa se close limpa pendências."""
        approval_id = sample_approval_request.approval_id
        pending = PendingApproval(
            request=sample_approval_request,
            event=asyncio.Event(),
        )
        provider._pending[approval_id] = pending
        provider._started = True

        with patch.object(provider, "stop", new_callable=AsyncMock) as mock_stop:
            await provider.close()
            mock_stop.assert_called_once()

        assert len(provider._pending) == 0

    def test_is_allowed(self, provider):
        """Testa verificação de whitelist."""
        assert provider._is_allowed(123456789, -1001234567890) is True
        assert provider._is_allowed(999999999, -1001234567890) is False
        assert provider._is_allowed(123456789, -999999999999) is False
        assert provider._is_allowed(999999999, -999999999999) is False

    @pytest.mark.asyncio
    async def test_send_export_notification_success(self, provider):
        """Testa envio de notificação de exportação."""
        project_id = uuid4()
        provider._started = True
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()
        provider._bot = mock_bot

        result = await provider.send_export_notification(project_id, "/exports/test")

        assert result is True
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert str(project_id) in call_args.kwargs.get("text", "")
        assert "/exports/test" in call_args.kwargs.get("text", "")

    @pytest.mark.asyncio
    async def test_send_export_notification_not_started(self, provider):
        """Testa notificação quando bot não iniciado."""
        provider._started = False
        result = await provider.send_export_notification(uuid4(), "/exports/test")
        assert result is False


class TestPendingApproval:
    """Testes para a dataclass PendingApproval."""

    @pytest.fixture
    def sample_approval_request(self):
        """Cria uma ApprovalRequest de exemplo."""
        return ApprovalRequest(
            approval_id=uuid4(),
            project_id=uuid4(),
            revision=1,
            video_path=Path("/fake/video.mp4"),
            thumbnail_path=Path("/fake/thumb.jpg"),
            title="Vídeo de teste",
            niche="tecnologia",
            duration_seconds=30.0,
            caption="Legenda do vídeo",
            hashtags=["#tech", "#ia"],
            sources_summary="Fonte: YouTube",
            license_warnings=[],
            trace_id="test-trace-123",
        )

    def test_creation(self, sample_approval_request):
        """Testa criação básica."""
        event = asyncio.Event()
        pending = PendingApproval(
            request=sample_approval_request,
            event=event,
            message_id=123,
            chat_id=-1001234567890,
        )

        assert pending.request == sample_approval_request
        assert pending.event is event
        assert pending.decision is None
        assert pending.message_id == 123
        assert pending.chat_id == -1001234567890
        assert pending.request_revision_pending is False