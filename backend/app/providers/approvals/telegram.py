"""Provedor de aprovação via Telegram Bot (long polling)."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.default import DefaultBotProperties

from backend.app.providers.approvals.base import ApprovalProvider, ApprovalDecision, ApprovalRequest
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PendingApproval:
    """Aprovação pendente aguardando decisão."""
    request: ApprovalRequest
    event: asyncio.Event
    decision: ApprovalDecision | None = None
    message_id: int | None = None
    chat_id: int | None = None
    created_at: float = field(default_factory=time.time)


class TelegramApprovalProvider(ApprovalProvider):
    """
    Provedor de aprovação via Telegram Bot API.

    Usa long polling (compatível com desenvolvimento local sem HTTPS).
    Requer TELEGRAM_BOT_TOKEN e whitelist de usuários/chats.
    """

    def __init__(self, settings=None):
        if settings is None:
            settings = get_settings()

        if not settings.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN não configurado")

        if not settings.TELEGRAM_ALLOWED_USER_IDS:
            raise ValueError("TELEGRAM_ALLOWED_USER_IDS não configurado (whitelist obrigatória)")

        if not settings.TELEGRAM_ALLOWED_CHAT_IDS:
            raise ValueError("TELEGRAM_ALLOWED_CHAT_IDS não configurado (whitelist obrigatória)")

        self._token = settings.TELEGRAM_BOT_TOKEN
        self._allowed_user_ids = set(settings.TELEGRAM_ALLOWED_USER_IDS)
        self._allowed_chat_ids = set(settings.TELEGRAM_ALLOWED_CHAT_IDS)
        self._polling_enabled = settings.TELEGRAM_POLLING_ENABLED

        self._bot: Bot | None = None
        self._dp: Dispatcher | None = None
        self._router = Router()
        self._pending: dict[UUID, PendingApproval] = {}
        self._polling_task: asyncio.Task | None = None
        self._started = False

        # Registrar handlers
        self._register_handlers()

    @property
    def provider_name(self) -> str:
        return "telegram"

    @property
    def cost_class(self) -> str:
        return "zero"

    def _register_handlers(self) -> None:
        """Registra handlers do bot."""

        @self._router.callback_query(F.data.startswith("approve:"))
        async def on_approve(callback: types.CallbackQuery):
            await self._handle_callback(callback, "approve")

        @self._router.callback_query(F.data.startswith("reject:"))
        async def on_reject(callback: types.CallbackQuery):
            await self._handle_callback(callback, "reject")

        @self._router.callback_query(F.data.startswith("revision:"))
        async def on_revision(callback: types.CallbackQuery):
            await self._handle_callback(callback, "request_revision")

        @self._router.message(Command("cancel"))
        async def on_cancel(message: types.Message):
            await self._handle_cancel(message)

        @self._router.message(Command("status"))
        async def on_status(message: types.Message):
            await self._handle_status(message)

    async def _handle_callback(self, callback: types.CallbackQuery, action: str) -> None:
        """Processa callback dos botões de aprovação."""
        # Verificar whitelist
        if not self._is_allowed(callback.from_user.id, callback.message.chat.id):
            await callback.answer("❌ Usuário não autorizado", show_alert=True)
            return

        # Extrair approval_id do callback_data (formato: "approve:uuid")
        try:
            approval_id = UUID(callback.data.split(":", 1)[1])
        except (IndexError, ValueError):
            await callback.answer("❌ ID inválido", show_alert=True)
            return

        pending = self._pending.get(approval_id)
        if not pending:
            await callback.answer("❌ Solicitação não encontrada ou expirada", show_alert=True)
            return

        # Verificar se já foi decidida
        if pending.decision is not None:
            await callback.answer("✅ Já foi decidido", show_alert=True)
            return

        # Para revisão, pedir feedback via mensagem
        if action == "request_revision":
            await callback.answer("📝 Envie o feedback como resposta a esta mensagem")
            # O feedback será capturado pelo handler de mensagem
            # Armazenar ação pendente
            pending.request_revision_pending = True
            return

        # Criar decisão
        feedback_map = {
            "approve": "Aprovado via Telegram",
            "reject": "Rejeitado via Telegram",
        }

        decision = ApprovalDecision(
            approval_id=approval_id,
            action=action,
            feedback=feedback_map.get(action),
            actor_id=callback.from_user.id,
            decided_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        )

        pending.decision = decision
        pending.event.set()

        # Atualizar mensagem
        status_emoji = "✅" if action == "approve" else "❌"
        status_text = "APROVADO" if action == "approve" else "REJEITADO"

        await callback.message.edit_text(
            f"{callback.message.html_text}\n\n{status_emoji} <b>{status_text}</b> por {callback.from_user.full_name}",
            parse_mode=ParseMode.HTML,
            reply_markup=None,
        )
        await callback.answer(f"{status_emoji} {status_text}")

        logger.info("Decisão Telegram", extra={
            "approval_id": str(approval_id),
            "action": action,
            "user_id": callback.from_user.id,
        })

    async def _handle_cancel(self, message: types.Message) -> None:
        """Handler para /cancel."""
        if not self._is_allowed(message.from_user.id, message.chat.id):
            return

        # Cancelar aprovações pendentes neste chat
        cancelled = 0
        for approval_id, pending in list(self._pending.items()):
            if pending.chat_id == message.chat.id and pending.decision is None:
                decision = ApprovalDecision(
                    approval_id=approval_id,
                    action="cancel",
                    feedback="Cancelado pelo usuário via /cancel",
                    actor_id=message.from_user.id,
                    decided_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                )
                pending.decision = decision
                pending.event.set()
                cancelled += 1

        await message.reply(f"✅ {cancelled} solicitação(ões) cancelada(s)")

    async def _handle_status(self, message: types.Message) -> None:
        """Handler para /status."""
        if not self._is_allowed(message.from_user.id, message.chat.id):
            return

        pending_count = sum(1 for p in self._pending.values() if p.decision is None)
        total_count = len(self._pending)

        await message.reply(
            f"📊 <b>Status do Bot</b>\n"
            f"Pendentes: {pending_count}\n"
            f"Total processadas: {total_count}",
            parse_mode=ParseMode.HTML,
        )

    def _is_allowed(self, user_id: int, chat_id: int) -> bool:
        """Verifica se usuário e chat estão na whitelist."""
        return user_id in self._allowed_user_ids and chat_id in self._allowed_chat_ids

    async def start(self) -> None:
        """Inicia o bot (long polling)."""
        if self._started:
            return

        self._bot = Bot(
            token=self._token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self._dp = Dispatcher()
        self._dp.include_router(self._router)

        # Deletar webhook se existir (garantir polling)
        await self._bot.delete_webhook(drop_pending_updates=True)

        if self._polling_enabled:
            self._polling_task = asyncio.create_task(self._dp.start_polling(self._bot))
            logger.info("Telegram bot iniciado (long polling)")

        self._started = True

    async def stop(self) -> None:
        """Para o bot."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        if self._bot:
            await self._bot.session.close()

        self._started = False
        logger.info("Telegram bot parado")

    async def send_for_approval(self, request: ApprovalRequest) -> bool:
        """Envia vídeo para aprovação no Telegram."""
        if not self._started:
            await self.start()

        # Verificar arquivos
        if not request.video_path.exists():
            logger.error("Arquivo de vídeo não encontrado", extra={"path": str(request.video_path)})
            return False

        # Criar teclado inline
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Aprovar", callback_data=f"approve:{request.approval_id}"),
                InlineKeyboardButton(text="❌ Rejeitar", callback_data=f"reject:{request.approval_id}"),
            ],
            [
                InlineKeyboardButton(text="📝 Solicitar Revisão", callback_data=f"revision:{request.approval_id}"),
            ],
        ])

        # Preparar caption
        caption = (
            f"🎬 <b>Nova Aprovação de Vídeo</b>\n\n"
            f"<b>ID:</b> <code>{request.approval_id}</code>\n"
            f"<b>Projeto:</b> <code>{request.project_id}</code> (rev {request.revision})\n"
            f"<b>Título:</b> {request.title}\n"
            f"<b>Nich:</b> {request.niche}\n"
            f"<b>Duração:</b> {request.duration_seconds:.1f}s\n\n"
            f"<b>Legenda:</b>\n{request.caption}\n\n"
            f"<b>Hashtags:</b> {' '.join(request.hashtags)}\n\n"
            f"<b>Fontes:</b> {request.sources_summary}\n"
        )
        if request.license_warnings:
            caption += f"\n<b>⚠️ Avisos:</b> {'; '.join(request.license_warnings)}"

        # Enviar vídeo + thumbnail
        chat_id = list(self._allowed_chat_ids)[0]  # Primeiro chat permitido

        try:
            video_file = FSInputFile(request.video_path)

            if request.thumbnail_path and request.thumbnail_path.exists():
                # Enviar vídeo com thumbnail
                sent_message = await self._bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=caption,
                    reply_markup=keyboard,
                    supports_streaming=True,
                )
            else:
                sent_message = await self._bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=caption,
                    reply_markup=keyboard,
                    supports_streaming=True,
                )

            # Armazenar aprovação pendente
            pending = PendingApproval(
                request=request,
                event=asyncio.Event(),
                message_id=sent_message.message_id,
                chat_id=chat_id,
            )
            self._pending[request.approval_id] = pending

            logger.info("Solicitação enviada ao Telegram", extra={
                "approval_id": str(request.approval_id),
                "chat_id": chat_id,
                "message_id": sent_message.message_id,
            })
            return True

        except Exception as e:
            logger.exception("Erro ao enviar para Telegram", extra={
                "approval_id": str(request.approval_id),
                "error": str(e),
            })
            return False

    async def wait_for_decision(self, approval_id: UUID, timeout_seconds: int = 3600) -> ApprovalDecision | None:
        """Aguarda decisão do usuário."""
        pending = self._pending.get(approval_id)
        if not pending:
            return None

        try:
            await asyncio.wait_for(pending.event.wait(), timeout=timeout_seconds)
            return pending.decision
        except asyncio.TimeoutError:
            # Timeout - marcar como expirada
            if pending.decision is None:
                decision = ApprovalDecision(
                    approval_id=approval_id,
                    action="timeout",
                    feedback=f"Timeout após {timeout_seconds}s sem decisão",
                    actor_id=0,
                    decided_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                )
                pending.decision = decision
                logger.warning("Timeout de aprovação", extra={"approval_id": str(approval_id)})
            return pending.decision

    async def cancel_approval(self, approval_id: UUID) -> bool:
        """Cancela solicitação pendente."""
        pending = self._pending.get(approval_id)
        if not pending:
            return False

        if pending.decision is None:
            # Tentar deletar mensagem do Telegram
            if self._bot and pending.chat_id and pending.message_id:
                try:
                    await self._bot.delete_message(pending.chat_id, pending.message_id)
                except Exception:
                    pass  # Ignorar erro se mensagem já foi deletada

            decision = ApprovalDecision(
                approval_id=approval_id,
                action="cancel",
                feedback="Cancelado pelo sistema",
                actor_id=0,
                decided_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            )
            pending.decision = decision
            pending.event.set()

        return True

    async def health_check(self) -> bool:
        """Verifica se bot está respondendo."""
        if not self._started or not self._bot:
            return False
        try:
            me = await self._bot.get_me()
            return me is not None
        except Exception:
            return False

    async def close(self) -> None:
        """Libera recursos."""
        await self.stop()
        self._pending.clear()


# Adicionar atributo ao PendingApproval para revisão pendente
PendingApproval.__annotations__['request_revision_pending'] = bool
PendingApproval.request_revision_pending = False