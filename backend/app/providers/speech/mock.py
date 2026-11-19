"""Provedor de síntese de fala mock para testes."""

import hashlib
import logging
import uuid
import wave
from pathlib import Path
from typing import Any

from backend.app.providers.speech.base import SpeechProvider, SpeechResult, SpeechSpec

logger = logging.getLogger(__name__)


class MockSpeechProvider(SpeechProvider):
    """Provedor mock que gera áudio WAV silencioso para testes."""

    def __init__(self, output_dir: Path | None = None, should_fail: bool = False):
        from backend.app.core.config import get_settings
        settings = get_settings()
        self._output_dir = output_dir or Path(settings.LOCAL_STORAGE_ROOT) / "assets" / "speech_mocks"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._should_fail = should_fail
        self._call_count = 0
        self._sample_rate = 22050

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_id(self) -> str:
        return "mock-tts-v1"

    @property
    def cost_class(self) -> str:
        return "zero"

    @property
    def license(self) -> str:
        return "CC0"

    async def synthesize(self, spec: SpeechSpec) -> SpeechResult:
        self._call_count += 1

        if self._should_fail:
            raise RuntimeError("MockSpeechProvider configured to fail")

        # Estimar duração: ~150 palavras por minuto = ~2.5 palavras/seg
        words = len(spec.text.split())
        estimated_duration_sec = max(1.0, words / 2.5 / spec.speed)
        duration_ms = int(estimated_duration_sec * 1000)

        # Gerar WAV silencioso (zeros)
        num_samples = int(self._sample_rate * estimated_duration_sec)
        audio_data = b"\x00" * (num_samples * 2)  # 16-bit mono

        file_id = uuid.uuid4().hex[:12]
        file_path = self._output_dir / f"mock_speech_{file_id}.wav"

        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self._sample_rate)
            wf.writeframes(audio_data)

        # Calcular hash
        sha256 = self._calculate_sha256(file_path)

        return SpeechResult(
            audio_path=file_path,
            sha256=sha256,
            mime_type="audio/wav",
            duration_ms=duration_ms,
            sample_rate=self._sample_rate,
            provider=self.provider_name,
            model=self.model_id,
            voice=spec.voice,
            license_ref=self.license,
            metadata={
                "mock_call": self._call_count,
                "text_length": len(spec.text),
                "words": words,
                "speed": spec.speed,
                "provenance": "mock",
            },
        )

    def _calculate_sha256(self, file_path: Path) -> str:
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    async def health_check(self) -> bool:
        return not self._should_fail

    async def close(self) -> None:
        pass

    def get_available_voices(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "mock-voice-pt",
                "name": "Mock Portuguese",
                "language": "pt-BR",
                "gender": "neutral",
                "license": "CC0",
            },
            {
                "id": "mock-voice-en",
                "name": "Mock English",
                "language": "en-US",
                "gender": "neutral",
                "license": "CC0",
            },
        ]

    def set_should_fail(self, should_fail: bool) -> None:
        self._should_fail = should_fail

    def get_call_count(self) -> int:
        return self._call_count