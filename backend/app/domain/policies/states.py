"""Políticas de máquina de estados e transições."""

from dataclasses import dataclass
from typing import Optional

from backend.app.domain.enums import VideoState, ALLOWED_TRANSITIONS, is_valid_transition
from backend.app.core.exceptions import InvalidStateTransitionError


@dataclass(frozen=True)
class StateTransitionResult:
    """Resultado de uma transição de estado."""
    success: bool
    new_state: Optional[VideoState] = None
    error: Optional[str] = None


class StateMachine:
    """Máquina de estados para projetos de vídeo."""

    def __init__(self):
        self.transitions = ALLOWED_TRANSITIONS

    def can_transition(self, from_state: VideoState, to_state: VideoState) -> bool:
        """Verifica se transição é permitida."""
        return is_valid_transition(from_state, to_state)

    def transition(
        self,
        current_state: VideoState,
        target_state: VideoState,
        *,
        force: bool = False,
    ) -> StateTransitionResult:
        """
        Executa transição de estado.

        Args:
            current_state: Estado atual
            target_state: Estado desejado
            force: Se True, permite transições não padrão (uso interno controlado)

        Returns:
            StateTransitionResult com sucesso/erro
        """
        if current_state == target_state:
            return StateTransitionResult(success=True, new_state=current_state)

        if not force and not self.can_transition(current_state, target_state):
            allowed = self.transitions.get(current_state, [])
            return StateTransitionResult(
                success=False,
                error=f"Transição inválida: {current_state.value} -> {target_state.value}. Permitidos: {[s.value for s in allowed]}",
            )

        return StateTransitionResult(success=True, new_state=target_state)

    def get_next_states(self, state: VideoState) -> list[VideoState]:
        """Retorna possíveis próximos estados."""
        return self.transitions.get(state, [])

    def is_terminal(self, state: VideoState) -> bool:
        """Verifica se estado é terminal (sem transições de saída)."""
        return len(self.transitions.get(state, [])) == 0

    def is_failure_state(self, state: VideoState) -> bool:
        """Verifica se estado representa falha."""
        return state in (VideoState.FAILED_RETRYABLE, VideoState.FAILED_TERMINAL)

    def is_approval_state(self, state: VideoState) -> bool:
        """Verifica se estado aguarda aprovação humana."""
        return state == VideoState.PENDING_APPROVAL

    def is_revision_state(self, state: VideoState) -> bool:
        """Verifica se estado é de revisão solicitada."""
        return state == VideoState.REVISION_REQUESTED

    def get_revision_target_state(self, current_state: VideoState) -> VideoState:
        """
        Determina para qual estado voltar após revisão.
        Revisão pode reiniciar de GENERATING_ASSETS ou RENDERING.
        """
        # Por padrão, voltar para GENERATING_ASSETS para regenerar assets
        return VideoState.GENERATING_ASSETS

    def validate_sequence(self, states: list[VideoState]) -> tuple[bool, Optional[str]]:
        """Valida se uma sequência de estados é válida."""
        if not states:
            return False, "Sequência vazia"

        for i in range(len(states) - 1):
            if not self.can_transition(states[i], states[i + 1]):
                return False, f"Transição inválida na posição {i}: {states[i].value} -> {states[i+1].value}"

        return True, None


# Instância global
state_machine = StateMachine()


class OptimisticLock:
    """Controle de concorrência otimista para transições de estado."""

    def __init__(self):
        self._versions: dict[str, int] = {}

    def get_version(self, entity_id: str) -> int:
        return self._versions.get(entity_id, 0)

    def increment_version(self, entity_id: str) -> int:
        new_version = self.get_version(entity_id) + 1
        self._versions[entity_id] = new_version
        return new_version

    def check_and_increment(self, entity_id: str, expected_version: int) -> tuple[bool, int]:
        """
        Verifica versão esperada e incrementa atomicamente.

        Returns:
            (success, new_version)
        """
        current = self.get_version(entity_id)
        if current != expected_version:
            return False, current
        new_version = self.increment_version(entity_id)
        return True, new_version


# Instância global para uso em workers
optimistic_lock = OptimisticLock()