"""Políticas de qualidade e validação de saída."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from backend.app.domain.enums import VideoState


class QualityCheck(str, Enum):
    """Checks de qualidade obrigatórios."""
    RESOLUTION = "resolution"
    ASPECT_RATIO = "aspect_ratio"
    DURATION = "duration"
    VIDEO_CODEC = "video_codec"
    AUDIO_CODEC = "audio_codec"
    AUDIO_STREAM = "audio_stream"
    FILE_INTEGRITY = "file_integrity"
    NO_CORRUPTION = "no_corruption"
    SAFE_MARGINS = "safe_margins"
    SUBTITLES_SYNC = "subtitles_sync"


class QualitySeverity(str, Enum):
    """Severidade de problemas de qualidade."""
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


@dataclass(frozen=True)
class QualityThresholds:
    """Thresholds de qualidade configuráveis."""
    target_width: int = 1080
    target_height: int = 1920
    target_aspect_ratio: float = 9/16  # 0.5625
    aspect_ratio_tolerance: float = 0.02
    min_duration_seconds: float = 15.0
    max_duration_seconds: float = 60.0
    target_fps: int = 30
    allowed_video_codecs: tuple[str, ...] = ("h264", "libx264", "h264_nvenc")
    allowed_audio_codecs: tuple[str, ...] = ("aac", "libfdk_aac")
    min_audio_bitrate_kbps: int = 64
    max_file_size_mb: int = 100


@dataclass
class QualityIssue:
    """Problema de qualidade detectado."""
    check: QualityCheck
    severity: QualitySeverity
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class QualityReport:
    """Relatório de qualidade completo."""
    passed: bool
    checks_performed: list[QualityCheck] = field(default_factory=list)
    issues: list[QualityIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def blocking_issues(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == QualitySeverity.BLOCKING]

    @property
    def warning_issues(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == QualitySeverity.WARNING]

    def add_issue(self, issue: QualityIssue) -> None:
        self.issues.append(issue)
        if issue.severity == QualitySeverity.BLOCKING:
            self.passed = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class QualityPolicy:
    """Política de validação de qualidade de vídeo."""

    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        self.thresholds = thresholds or QualityThresholds()

    def create_report(self) -> QualityReport:
        """Cria relatório vazio."""
        return QualityReport(passed=True)

    def check_resolution(self, report: QualityReport, width: int, height: int) -> None:
        """Valida resolução do vídeo."""
        report.checks_performed.append(QualityCheck.RESOLUTION)

        if width < self.thresholds.target_width or height < self.thresholds.target_height:
            report.add_issue(QualityIssue(
                check=QualityCheck.RESOLUTION,
                severity=QualitySeverity.BLOCKING,
                message=f"Resolução abaixo do alvo: {width}x{height} < {self.thresholds.target_width}x{self.thresholds.target_height}",
                expected=f">= {self.thresholds.target_width}x{self.thresholds.target_height}",
                actual=f"{width}x{height}",
            ))
        elif width != self.thresholds.target_width or height != self.thresholds.target_height:
            report.add_warning(f"Resolução não padrão: {width}x{height} (alvo: {self.thresholds.target_width}x{self.thresholds.target_height})")

    def check_aspect_ratio(self, report: QualityReport, width: int, height: int) -> None:
        """Valida proporção de aspecto (9:16)."""
        report.checks_performed.append(QualityCheck.ASPECT_RATIO)

        if height == 0:
            report.add_issue(QualityIssue(
                check=QualityCheck.ASPECT_RATIO,
                severity=QualitySeverity.BLOCKING,
                message="Altura zero - proporção inválida",
            ))
            return

        actual_ratio = width / height
        expected = self.thresholds.target_aspect_ratio
        tolerance = self.thresholds.aspect_ratio_tolerance

        if abs(actual_ratio - expected) > tolerance:
            report.add_issue(QualityIssue(
                check=QualityCheck.ASPECT_RATIO,
                severity=QualitySeverity.BLOCKING,
                message=f"Proporção fora da tolerância: {actual_ratio:.4f} (esperado ~{expected:.4f} ±{tolerance})",
                expected=f"{expected:.4f} ±{tolerance}",
                actual=f"{actual_ratio:.4f}",
            ))

    def check_duration(self, report: QualityReport, duration_seconds: float) -> None:
        """Valida duração do vídeo."""
        report.checks_performed.append(QualityCheck.DURATION)

        if duration_seconds < self.thresholds.min_duration_seconds:
            report.add_issue(QualityIssue(
                check=QualityCheck.DURATION,
                severity=QualitySeverity.BLOCKING,
                message=f"Vídeo muito curto: {duration_seconds:.1f}s < {self.thresholds.min_duration_seconds}s",
                expected=f">= {self.thresholds.min_duration_seconds}s",
                actual=f"{duration_seconds:.1f}s",
            ))
        elif duration_seconds > self.thresholds.max_duration_seconds:
            report.add_issue(QualityIssue(
                check=QualityCheck.DURATION,
                severity=QualitySeverity.BLOCKING,
                message=f"Vídeo muito longo: {duration_seconds:.1f}s > {self.thresholds.max_duration_seconds}s",
                expected=f"<= {self.thresholds.max_duration_seconds}s",
                actual=f"{duration_seconds:.1f}s",
            ))

    def check_video_codec(self, report: QualityReport, codec: str) -> None:
        """Valida codec de vídeo."""
        report.checks_performed.append(QualityCheck.VIDEO_CODEC)

        codec_lower = codec.lower()
        if not any(allowed in codec_lower for allowed in self.thresholds.allowed_video_codecs):
            report.add_issue(QualityIssue(
                check=QualityCheck.VIDEO_CODEC,
                severity=QualitySeverity.BLOCKING,
                message=f"Codec de vídeo não permitido: {codec}",
                expected=f"um de: {', '.join(self.thresholds.allowed_video_codecs)}",
                actual=codec,
            ))

    def check_audio_codec(self, report: QualityReport, codec: str) -> None:
        """Valida codec de áudio."""
        report.checks_performed.append(QualityCheck.AUDIO_CODEC)

        codec_lower = codec.lower()
        if not any(allowed in codec_lower for allowed in self.thresholds.allowed_audio_codecs):
            report.add_issue(QualityIssue(
                check=QualityCheck.AUDIO_CODEC,
                severity=QualitySeverity.BLOCKING,
                message=f"Codec de áudio não permitido: {codec}",
                expected=f"um de: {', '.join(self.thresholds.allowed_audio_codecs)}",
                actual=codec,
            ))

    def check_audio_stream(self, report: QualityReport, has_audio: bool, bitrate_kbps: Optional[int] = None) -> None:
        """Valida presença e qualidade do stream de áudio."""
        report.checks_performed.append(QualityCheck.AUDIO_STREAM)

        if not has_audio:
            report.add_issue(QualityIssue(
                check=QualityCheck.AUDIO_STREAM,
                severity=QualitySeverity.BLOCKING,
                message="Vídeo sem stream de áudio",
            ))
            return

        if bitrate_kbps and bitrate_kbps < self.thresholds.min_audio_bitrate_kbps:
            report.add_warning(f"Bitrate de áudio baixo: {bitrate_kbps} kbps (mín: {self.thresholds.min_audio_bitrate_kbps} kbps)")

    def check_file_integrity(self, report: QualityReport, file_size_bytes: int, ffprobe_ok: bool) -> None:
        """Valida integridade do arquivo via ffprobe."""
        report.checks_performed.append(QualityCheck.FILE_INTEGRITY)
        report.checks_performed.append(QualityCheck.NO_CORRUPTION)

        if not ffprobe_ok:
            report.add_issue(QualityIssue(
                check=QualityCheck.NO_CORRUPTION,
                severity=QualitySeverity.BLOCKING,
                message="ffprobe falhou - arquivo possivelmente corrompido",
            ))

        max_bytes = self.thresholds.max_file_size_mb * 1024 * 1024
        if file_size_bytes > max_bytes:
            report.add_issue(QualityIssue(
                check=QualityCheck.FILE_INTEGRITY,
                severity=QualitySeverity.BLOCKING,
                message=f"Arquivo excede tamanho máximo: {file_size_bytes / (1024*1024):.1f} MB > {self.thresholds.max_file_size_mb} MB",
                expected=f"<= {self.thresholds.max_file_size_mb} MB",
                actual=f"{file_size_bytes / (1024*1024):.1f} MB",
            ))

    def check_safe_margins(self, report: QualityReport, has_safe_margins: bool) -> None:
        """Valida margens de segurança para UI do TikTok."""
        report.checks_performed.append(QualityCheck.SAFE_MARGINS)

        if not has_safe_margins:
            report.add_warning("Margens de segurança não verificadas - texto/elementos podem ser cortados pela UI do TikTok")

    def check_subtitles_sync(self, report: QualityReport, subtitle_file: Optional[str], video_duration: float) -> None:
        """Valida sincronização de legendas (básico)."""
        report.checks_performed.append(QualityCheck.SUBTITLES_SYNC)

        if not subtitle_file:
            report.add_warning("Arquivo de legenda não fornecido")
            return

        # TODO: Implementar verificação real de sincronização SRT/ASS vs duração
        # Por enquanto, apenas verificar se arquivo existe
        import os
        if not os.path.exists(subtitle_file):
            report.add_issue(QualityIssue(
                check=QualityCheck.SUBTITLES_SYNC,
                severity=QualitySeverity.BLOCKING,
                message=f"Arquivo de legenda não encontrado: {subtitle_file}",
            ))

    def run_all_checks(
        self,
        *,
        width: int,
        height: int,
        duration_seconds: float,
        video_codec: str,
        audio_codec: str,
        has_audio: bool,
        audio_bitrate_kbps: Optional[int],
        file_size_bytes: int,
        ffprobe_ok: bool,
        has_safe_margins: bool = False,
        subtitle_file: Optional[str] = None,
    ) -> QualityReport:
        """Executa todos os checks de qualidade."""
        report = self.create_report()

        self.check_resolution(report, width, height)
        self.check_aspect_ratio(report, width, height)
        self.check_duration(report, duration_seconds)
        self.check_video_codec(report, video_codec)
        self.check_audio_codec(report, audio_codec)
        self.check_audio_stream(report, has_audio, audio_bitrate_kbps)
        self.check_file_integrity(report, file_size_bytes, ffprobe_ok)
        self.check_safe_margins(report, has_safe_margins)
        self.check_subtitles_sync(report, subtitle_file, duration_seconds)

        return report


# Instância global
quality_policy = QualityPolicy()