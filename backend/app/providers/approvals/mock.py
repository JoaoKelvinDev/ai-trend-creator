"""Provedor de aprovação mock para testes."""

import asyncio
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from backend.app.providers.approvals.base import ApprovalProvider, ApprovalDecision, ApprovalRequest

logger = logging.getLogger(__name__)


class MockApprovalProvider(ApprovalProvider):
    """Provedor mock que simula aprovação automática ou programada."""

    def __init__(
        self,
        default_action: str = "approve",
        delay_seconds: float = 0.1,
        should_fail: bool = False,
    ):
        self._default_action = default_action
        self._delay = delay_seconds
        self._should_fail = should_fail
        self._pending: dict[UUID, ApprovalRequest] = {}
        self._decisions: dict[UUID, ApprovalDecision] = {}
        self._events: dict[UUID, asyncio.Event] = {}

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def cost_class(self) -> str:
        return "zero"

    async def send_for_approval(self, request: ApprovalRequest) -> bool:
        if self._should_fail:
            return False

        self._pending[request.approval_id] = request
        self._events[request.approval_id] = asyncio.Event()

        # Simular decisão assíncrona
        asyncio.create_task(self._auto_decide(request.approval_id))

        logger.info("Mock: solicitação de aprovação enviada", extra={"approval_id": str(request.approval_id)})
        return True

    async def _auto_decide(self, approval_id: UUID) -> None:
        await asyncio.sleep(self._delay)

        request = self._pending.get(approval_id)
        if not request:
            return

        # Feedback baseado na ação
        feedback_map = {
            "approve": "Aprovado automaticamente pelo mock",
            "reject": "Rejeitado automaticamente pelo mock",
            "request_revision": "Revisão solicitada: ajustar tom do roteiro",
        }

        decision = ApprovalDecision(
            approval_id=approval_id,
            action=self._default_action,
            feedback=feedback_map.get(self._default_action),
            actor_id=999999,  # Mock user
            decided_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        )

        self._decisions[approval_id] = decision
        if approval_id in self._events:
            self._events[approval_id].set()

        logger.info("Mock: decisão automática", extra={"approval_id": str(approval_id), "action": self._default_action})

    async def wait_for_decision(self, approval_id: UUID, timeout_seconds: int = 3600) -> ApprovalDecision | None:
        if approval_id not in self._events:
            return None

        try:
            await asyncio.wait_for(self._events[approval_id].wait(), timeout=timeout_seconds)
            return self._decisions.get(approval_id)
        except asyncio.TimeoutError:
            return None

    async def cancel_approval(self, approval_id: UUID) -> bool:
        if approval_id in self._pending:
            del self._pending[approval_id]
        if approval_id in self._events:
            self._events[approval_id].set()
        return True

    async def health_check(self) -> bool:
        return not self._should_fail

    async def send_export_notification(self, project_id: UUID, export_path: str) -> bool:
        """Simula envio de notificação de exportação."""
        logger.info("Mock: notificação de exportação", extra={
            "project_id": str(project_id),
            "export_path": export_path,
        })
        return True

    async def close(self) -> None:
        pass

    def set_default_action(self, action: str) -> None:
        """Define ação padrão: 'approve', 'reject', 'request_revision'."""
        if action in ("approve", "reject", "request_revision"):
            self._default_action = action

    def set_should_fail(self, should_fail: bool) -> None:
        self._should_fail = should_fail

    def get_pending_count(self) -> int:
        return len(self._pending)