"""Subtitle generation for AI Trend Creator - SRT/ASS format."""

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SubtitleSegment:
    """Single subtitle segment with timing."""
    index: int
    start_ms: int
    end_ms: int
    text: str
    style: str | None = None  # For ASS styling


@dataclass
class SubtitleConfig:
    """Configuration for subtitle generation."""
    format: str = "srt"  # "srt" or "ass"
    font_name: str = "Arial"
    font_size: int = 48
    font_color: str = "&HFFFFFF"  # ASS format (BBGGRR)
    outline_color: str = "&H000000"
    outline_width: int = 2
    shadow_color: str = "&H000000"
    shadow_offset: tuple[int, int] = (2, 2)
    margin_v: int = 80  # Vertical margin from bottom
    alignment: int = 2  # ASS alignment (2 = bottom center)
    max_chars_per_line: int = 42
    max_lines: int = 2


class SubtitleGenerator:
    """Generates SRT and ASS subtitle files from narration segments."""

    def __init__(self, config: SubtitleConfig | None = None):
        self._config = config or SubtitleConfig()

    def generate_srt(self, segments: list[SubtitleSegment], output_path: Path) -> Path:
        """Generate SRT subtitle file."""
        lines = []

        for seg in segments:
            start_time = self._ms_to_srt_time(seg.start_ms)
            end_time = self._ms_to_srt_time(seg.end_ms)

            # Wrap text if too long
            wrapped_text = self._wrap_text(seg.text)

            lines.append(str(seg.index))
            lines.append(f"{start_time} --> {end_time}")
            lines.append(wrapped_text)
            lines.append("")  # Empty line between entries

        content = "\n".join(lines)
        output_path.write_text(content, encoding="utf-8")
        logger.debug("SRT gerado", extra={"path": str(output_path), "segments": len(segments)})
        return output_path

    def generate_ass(self, segments: list[SubtitleSegment], output_path: Path) -> Path:
        """Generate ASS subtitle file with styling."""
        c = self._config

        # ASS header
        header = f"""[Script Info]
Title: AI Trend Creator Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{c.font_name},{c.font_size},{c.font_color},{c.font_color},{c.outline_color},{c.shadow_color},0,0,0,0,100,100,0,0,1,{c.outline_width},{c.shadow_offset[0]},{c.alignment},20,20,{c.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        for seg in segments:
            start_time = self._ms_to_ass_time(seg.start_ms)
            end_time = self._ms_to_ass_time(seg.end_ms)

            # Apply per-segment style if provided
            style = seg.style or "Default"
            text = self._wrap_text_ass(seg.text)

            events.append(
                f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}"
            )

        content = header + "\n".join(events) + "\n"
        output_path.write_text(content, encoding="utf-8")
        logger.debug("ASS gerado", extra={"path": str(output_path), "segments": len(segments)})
        return output_path

    def generate(
        self,
        segments: list[SubtitleSegment],
        output_path: Path,
        format: str | None = None,
    ) -> Path:
        """Generate subtitle file in specified format."""
        fmt = format or self._config.format

        if fmt.lower() == "ass":
            return self.generate_ass(segments, output_path)
        else:
            return self.generate_srt(segments, output_path)

    def _ms_to_srt_time(self, ms: int) -> str:
        """Convert milliseconds to SRT time format (HH:MM:SS,mmm)."""
        hours = ms // 3_600_000
        minutes = (ms % 3_600_000) // 60_000
        seconds = (ms % 60_000) // 1000
        milliseconds = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def _ms_to_ass_time(self, ms: int) -> str:
        """Convert milliseconds to ASS time format (H:MM:SS.cc)."""
        hours = ms // 3_600_000
        minutes = (ms % 3_600_000) // 60_000
        seconds = (ms % 60_000) // 1000
        centiseconds = (ms % 1000) // 10
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    def _wrap_text(self, text: str) -> str:
        """Wrap text to max chars per line and max lines."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            if len(test_line) <= self._config.max_chars_per_line:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        # Truncate to max lines
        if len(lines) > self._config.max_lines:
            lines = lines[:self._config.max_lines]
            # Add ellipsis to last line
            lines[-1] = lines[-1][:self._config.max_chars_per_line - 3] + "..."

        return "\n".join(lines)

    def _wrap_text_ass(self, text: str) -> str:
        """Wrap text for ASS format (uses \\N for line breaks)."""
        wrapped = self._wrap_text(text)
        return wrapped.replace("\n", "\\N")

    @staticmethod
    def create_segments_from_narration(
        narration_segments: list[dict[str, Any]],
        words_per_minute: int = 150,
    ) -> list[SubtitleSegment]:
        """
        Create subtitle segments from narration segments with estimated timing.

        Args:
            narration_segments: List of dicts with 'text' and optionally 'duration_ms'
            words_per_minute: Speaking rate for timing estimation

        Returns:
            List of SubtitleSegment with calculated timings
        """
        segments = []
        current_time = 0

        for i, seg_data in enumerate(narration_segments):
            text = seg_data.get("text", "").strip()
            if not text:
                continue

            # Use provided duration or estimate from word count
            if "duration_ms" in seg_data and seg_data["duration_ms"]:
                duration = seg_data["duration_ms"]
            else:
                word_count = len(text.split())
                duration = int((word_count / words_per_minute) * 60 * 1000)
                # Minimum duration for readability
                duration = max(duration, 2000)

            segments.append(SubtitleSegment(
                index=i + 1,
                start_ms=current_time,
                end_ms=current_time + duration,
                text=text,
                style=seg_data.get("style"),
            ))
            current_time += duration

        return segments