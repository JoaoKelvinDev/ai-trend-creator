"""Provedor de síntese de fala usando Piper TTS (local, custo zero)."""

import asyncio
import concurrent.futures
import hashlib
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.providers.speech.base import SpeechProvider, SpeechResult, SpeechSpec

logger = logging.getLogger(__name__)


class PiperSpeechProvider(SpeechProvider):
    """Provedor Piper TTS - execução local via Python package."""

    def __init__(
        self,
        voice: str = "pt_BR-faber-medium",
        model_dir: Path | None = None,
        output_dir: Path | None = None,
        use_cuda: bool = False,
    ):
        """
        Args:
            voice: ID da voz (ex: 'pt_BR-faber-medium')
            model_dir: Diretório com modelos .onnx e .onnx.json
            output_dir: Diretório para arquivos de áudio gerados
            use_cuda: Usar GPU se disponível
        """
        settings = get_settings()
        self._voice = voice
        self._model_dir = model_dir or Path(settings.LOCAL_STORAGE_ROOT) / "models" / "piper" / voice
        self._output_dir = output_dir or Path(settings.LOCAL_STORAGE_ROOT) / "assets" / "speech"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._use_cuda = use_cuda
        self._sample_rate = 22050  # Piper padrão

        # Verificar arquivos do modelo
        self._model_path = self._model_dir / f"{voice}.onnx"
        self._config_path = self._model_dir / f"{voice}.onnx.json"

        if not self._model_path.exists():
            raise FileNotFoundError(f"Modelo Piper não encontrado: {self._model_path}")
        if not self._config_path.exists():
            raise FileNotFoundError(f"Config Piper não encontrado: {self._config_path}")

        # Ler licença do MODEL_CARD se existir
        self._license = "CC0"  # padrão conhecido para pt_BR-faber-medium
        model_card = self._model_dir / "MODEL_CARD"
        if model_card.exists():
            content = model_card.read_text(encoding="utf-8")
            if "License:" in content:
                for line in content.split("\n"):
                    if line.strip().startswith("License:"):
                        self._license = line.split("License:")[-1].strip()
                        break

        # Thread pool para subprocessos síncronos (Windows compatível)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    @property
    def provider_name(self) -> str:
        return "piper"

    @property
    def model_id(self) -> str:
        return self._voice

    @property
    def cost_class(self) -> str:
        return "zero"

    @property
    def license(self) -> str:
        return self._license

    def _run_piper_sync(self, cmd: list[str], input_text: str) -> tuple[int, str, str]:
        """Executa Piper sincronamente em thread separada."""
        try:
            result = subprocess.run(
                cmd,
                input=input_text.encode("utf-8"),
                capture_output=True,
                timeout=60,
            )
            return result.returncode, result.stdout.decode("utf-8", errors="replace"), result.stderr.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def _run_ffprobe_sync(self, cmd: list[str]) -> tuple[int, str, str]:
        """Executa ffprobe sincronamente em thread separada."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
            )
            return result.returncode, result.stdout.decode("utf-8", errors="replace"), result.stderr.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    async def synthesize(self, spec: SpeechSpec) -> SpeechResult:
        """Sintetiza fala usando Piper TTS via CLI (thread pool para Windows)."""
        # Usar voz da spec se diferente, senão a padrão
        voice = spec.voice if spec.voice != "default" else self._voice

        # Arquivo de saída
        file_id = uuid.uuid4().hex[:12]
        output_file = self._output_dir / f"piper_{voice}_{file_id}.{spec.output_format}"

        # Construir comando Piper
        cmd = [
            "python", "-m", "piper",
            "-m", str(self._model_path),
            "-c", str(self._config_path),
            "-f", str(output_file),
        ]

        if self._use_cuda:
            cmd.append("--cuda")

        if spec.speed != 1.0:
            cmd.extend(["--length-scale", str(1.0 / spec.speed)])

        # Executar Piper via thread pool (compatível com Windows)
        try:
            logger.info("Sintetizando com Piper", extra={
                "voice": voice,
                "text_length": len(spec.text),
                "output": str(output_file),
            })

            loop = asyncio.get_event_loop()
            returncode, stdout, stderr = await loop.run_in_executor(
                self._executor,
                self._run_piper_sync,
                cmd,
                spec.text,
            )

            if returncode != 0:
                raise RuntimeError(f"Piper falhou (exit {returncode}): {stderr}")

        except Exception as e:
            logger.exception("Erro ao executar Piper")
            raise RuntimeError(f"Falha na síntese Piper: {e}")

        # Verificar arquivo gerado
        if not output_file.exists():
            raise RuntimeError(f"Piper não gerou arquivo de saída: {output_file}")

        # Calcular duração e hash
        duration_ms = await self._get_audio_duration(output_file)
        sha256 = self._calculate_sha256(output_file)

        # Determinar MIME type
        mime_type = "audio/wav" if spec.output_format == "wav" else "audio/mpeg"

        return SpeechResult(
            audio_path=output_file,
            sha256=sha256,
            mime_type=mime_type,
            duration_ms=duration_ms,
            sample_rate=self._sample_rate,
            provider=self.provider_name,
            model=self._voice,
            voice=voice,
            license_ref=self.license,
            metadata={
                "text_length": len(spec.text),
                "speed": spec.speed,
                "pitch": spec.pitch,
                "cuda": self._use_cuda,
                "model_path": str(self._model_path),
            },
        )

    async def _get_audio_duration(self, audio_path: Path) -> int:
        """Obtém duração do áudio via ffprobe (thread pool)."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ]
            loop = asyncio.get_event_loop()
            returncode, stdout, stderr = await loop.run_in_executor(
                self._executor,
                self._run_ffprobe_sync,
                cmd,
            )

            if returncode == 0 and stdout:
                duration_sec = float(stdout.strip())
                return int(duration_sec * 1000)
        except Exception:
            pass

        # Fallback: estimar pelo tamanho do arquivo (WAV 16-bit mono 22050Hz)
        # bytes = sample_rate * 2 * channels * duration_sec
        file_size = audio_path.stat().st_size
        estimated_sec = file_size / (self._sample_rate * 2)  # 16-bit mono
        return int(estimated_sec * 1000)

    def _calculate_sha256(self, file_path: Path) -> str:
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    async def health_check(self) -> bool:
        """Verifica se modelo e Piper estão disponíveis."""
        try:
            # Verificar arquivos
            if not self._model_path.exists() or not self._config_path.exists():
                return False

            # Testar Piper com texto curto
            test_file = self._output_dir / f"health_check_{uuid.uuid4().hex[:8]}.wav"
            cmd = [
                "python", "-m", "piper",
                "-m", str(self._model_path),
                "-c", str(self._config_path),
                "-f", str(test_file),
            ]
            loop = asyncio.get_event_loop()
            returncode, stdout, stderr = await loop.run_in_executor(
                self._executor,
                self._run_piper_sync,
                cmd,
                "test",
            )

            # Limpar arquivo de teste
            if test_file.exists():
                test_file.unlink(missing_ok=True)

            return returncode == 0
        except Exception:
            return False

    async def close(self) -> None:
        """Fecha thread pool."""
        self._executor.shutdown(wait=True)

    def get_available_voices(self) -> list[dict[str, Any]]:
        """Retorna vozes disponíveis no diretório de modelos."""
        voices = []
        models_root = self._model_dir.parent

        if models_root.exists():
            for voice_dir in models_root.iterdir():
                if voice_dir.is_dir():
                    model_file = voice_dir / f"{voice_dir.name}.onnx"
                    config_file = voice_dir / f"{voice_dir.name}.onnx.json"
                    if model_file.exists() and config_file.exists():
                        # Tentar ler idioma do config
                        import json
                        try:
                            config = json.loads(config_file.read_text(encoding="utf-8"))
                            language = config.get("language", {}).get("code", "unknown")
                        except Exception:
                            language = "unknown"

                        voices.append({
                            "id": voice_dir.name,
                            "name": voice_dir.name.replace("_", " ").replace("-", " ").title(),
                            "language": language,
                            "gender": "unknown",
                            "license": "CC0",  # Assumindo licença compatível
                        })

        # Se não encontrou nenhuma, retornar a voz padrão
        if not voices:
            voices.append({
                "id": self._voice,
                "name": self._voice.replace("_", " ").replace("-", " ").title(),
                "language": "pt-BR",
                "gender": "neutral",
                "license": self._license,
            })

        return voices