"""Orquestrador de workflow - gerencia transições de estado e execução de etapas."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from uuid import UUID

from backend.app.domain.policies.states import VideoState, state_machine, StateTransitionResult, optimistic_lock
from backend.app.db.models import VideoProject, Job, WorkflowEvent
from backend.app.db.session import get_db_session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkflowStepResult:
    """Resultado de uma etapa do workflow."""
    success: bool
    next_state: VideoState | None = None
    error: str | None = None
    output: dict[str, Any] | None = None


class WorkflowOrchestrator:
    """Orquestra a execução do pipeline de criação de vídeo."""

    def __init__(self):
        self._step_handlers: dict[VideoState, Callable[[VideoProject, dict[str, Any]], Awaitable[WorkflowStepResult]]] = {}
        self._running = False

    def register_handler(self, state: VideoState, handler: Callable[[VideoProject, dict[str, Any]], Awaitable[WorkflowStepResult]]) -> None:
        """Registra handler para uma etapa/estado."""
        self._step_handlers[state] = handler
        logger.debug("Handler registrado", extra={"state": state.value, "handler": handler.__name__})

    async def execute_step(
        self,
        project_id: UUID,
        target_state: VideoState,
        context: dict[str, Any] | None = None,
    ) -> WorkflowStepResult:
        """Executa uma etapa específica do workflow."""
        ctx = context or {}

        async with get_db_session() as db:
            # Carregar projeto com lock otimista
            project = await db.get(VideoProject, project_id)
            if not project:
                return WorkflowStepResult(success=False, error=f"Projeto {project_id} não encontrado")

            # Verificar transição válida
            current_state = VideoState(project.state)
            transition = state_machine.transition(current_state, target_state)
            if not transition.success:
                return WorkflowStepResult(success=False, error=transition.error)

            # Verificar lock otimista
            lock_key = f"project:{project_id}"
            lock_ok, new_version = optimistic_lock.check_and_increment(lock_key, project.version)
            if not lock_ok:
                return WorkflowStepResult(
                    success=False,
                    error=f"Conflito de concorrência: versão esperada {project.version}, atual {new_version}"
                )

            # Atualizar estado para RUNNING
            project.state = target_state.value
            project.version = new_version
            project.updated_at = datetime.now(timezone.utc)

            # Registrar job
            job = Job(
                kind=self._state_to_job_kind(target_state),
                project_id=project_id,
                status="running",
                attempts=1,
                idempotency_key=f"{project_id}:{target_state.value}:{new_version}",
            )
            db.add(job)

            # Registrar evento
            event = WorkflowEvent(
                aggregate_id=project_id,
                event_type=f"state_transition:{current_state.value}->{target_state.value}",
                payload_json={"context": ctx, "version": new_version},
            )
            db.add(event)

            await db.commit()

        try:
            # Executar handler
            handler = self._step_handlers.get(target_state)
            if not handler:
                raise RuntimeError(f"Nenhum handler registrado para estado {target_state.value}")

            result = await handler(project, ctx)

            # Atualizar resultado
            async with get_db_session() as db:
                project = await db.get(VideoProject, project_id)
                job = await db.execute(
                    Job.__table__.select().where(Job.idempotency_key == f"{project_id}:{target_state.value}:{new_version}")
                )
                job = job.scalar_one_or_none()

                if result.success:
                    project.state = (result.next_state or target_state).value
                    project.version = optimistic_lock.increment_version(lock_key)
                    if job:
                        job.status = "completed"
                        job.finished_at = datetime.now(timezone.utc)
                else:
                    project.state = VideoState.FAILED_RETRYABLE.value
                    if job:
                        job.status = "failed"
                        job.finished_at = datetime.now(timezone.utc)
                        job.error_type = type(result.error).__name__ if result.error else "UnknownError"

                project.updated_at = datetime.now(timezone.utc)

                # Evento de resultado
                event = WorkflowEvent(
                    aggregate_id=project_id,
                    event_type=f"step_result:{target_state.value}",
                    payload_json={"success": result.success, "error": result.error, "output": result.output},
                )
                db.add(event)

                await db.commit()

            return result

        except Exception as e:
            logger.exception("Erro ao executar etapa", extra={"project_id": str(project_id), "state": target_state.value})

            async with get_db_session() as db:
                project = await db.get(VideoProject, project_id)
                job = await db.execute(
                    Job.__table__.select().where(Job.idempotency_key == f"{project_id}:{target_state.value}:{new_version}")
                )
                job = job.scalar_one_or_none()

                project.state = VideoState.FAILED_RETRYABLE.value
                project.updated_at = datetime.now(timezone.utc)
                if job:
                    job.status = "failed"
                    job.finished_at = datetime.now(timezone.utc)
                    job.error_type = type(e).__name__

                event = WorkflowEvent(
                    aggregate_id=project_id,
                    event_type=f"step_error:{target_state.value}",
                    payload_json={"error": str(e), "type": type(e).__name__},
                )
                db.add(event)

                await db.commit()

            return WorkflowStepResult(success=False, error=str(e))

    async def execute_pipeline(
        self,
        project_id: UUID,
        initial_state: VideoState,
        target_final_state: VideoState,
        context: dict[str, Any] | None = None,
    ) -> list[WorkflowStepResult]:
        """Executa pipeline completo de estados."""
        results = []
        current = initial_state

        # Validar sequência
        valid, error = state_machine.validate_sequence([initial_state, target_final_state])
        if not valid:
            # Se não é transição direta, calcular caminho
            path = self._find_path(initial_state, target_final_state)
            if not path:
                return [WorkflowStepResult(success=False, error=f"Caminho inválido: {error}")]
        else:
            path = [initial_state, target_final_state]

        for i, next_state in enumerate(path[1:], 1):
            ctx = {**(context or {}), "step_index": i, "total_steps": len(path) - 1}
            result = await self.execute_step(project_id, next_state, ctx)
            results.append(result)

            if not result.success:
                logger.warning("Pipeline interrompido por falha", extra={
                    "project_id": str(project_id),
                    "failed_state": next_state.value,
                    "error": result.error,
                })
                break

        return results

    def _find_path(self, from_state: VideoState, to_state: VideoState) -> list[VideoState] | None:
        """Encontra caminho válido entre estados (BFS simples)."""
        from collections import deque

        queue = deque([(from_state, [from_state])])
        visited = {from_state}

        while queue:
            current, path = queue.popleft()
            if current == to_state:
                return path

            for next_state in state_machine.get_next_states(current):
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [next_state]))

        return None

    def _state_to_job_kind(self, state: VideoState) -> str:
        """Mapeia estado para tipo de job."""
        mapping = {
            VideoState.DISCOVERED: "discovery",
            VideoState.SCORED: "scoring",
            VideoState.SELECTED: "scoring",
            VideoState.SCRIPTED: "scripting",
            VideoState.STORYBOARDED: "storyboarding",
            VideoState.GENERATING_ASSETS: "asset_generation",
            VideoState.RENDERING: "rendering",
            VideoState.QUALITY_CHECK: "quality_check",
            VideoState.PENDING_APPROVAL: "telegram_notify",
            VideoState.READY_FOR_MANUAL_POST: "export",
        }
        return mapping.get(state, "unknown")


# Instância global
workflow_orchestrator = WorkflowOrchestrator()