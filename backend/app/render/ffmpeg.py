"""FFmpeg video renderer for AI Trend Creator - local, cost-free rendering."""

import asyncio
import concurrent.futures
import hashlib
import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.schemas.render import RenderPreset, DEFAULT_RENDER_PRESET

logger = logging.getLogger(__name__)


@dataclass
class RenderConfig:
    """Configuration for video rendering."""
    preset: RenderPreset = field(default_factory=lambda: DEFAULT_RENDER_PRESET)
    width: int = 1080
    height: int = 1920
    fps: int = 30
    target_duration_ms: int = 30000
    background_audio_path: Path | None = None
    background_audio_volume: float = 0.1
    force_cpu: bool = False


@dataclass
class RenderResult:
    """Result of video rendering."""
    video_path: Path
    thumbnail_path: Path
    sha256: str
    duration_ms: int
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str
    file_size_bytes: int
    ffmpeg_cmd: str
    render_time_ms: int


class FFmpegRenderer:
    """FFmpeg-based video renderer with thread pool for Windows compatibility."""

    def __init__(
        self,
        output_dir: Path | None = None,
        config: RenderConfig | None = None,
        project_root: str | None = None,
    ):
        """
        Args:
            output_dir: Directory for rendered videos
            config: Render configuration
            project_root: Project root directory for subprocess cwd (Windows compat)
        """
        import os
        settings = get_settings()
        self._output_dir = output_dir or Path(settings.LOCAL_STORAGE_ROOT) / "exports"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._config = config or RenderConfig()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self._project_root = project_root or os.getcwd()

    def _run_ffmpeg_sync(self, cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
        """Execute FFmpeg synchronously in thread pool."""
        try:
            import os
            if cwd is None:
                cwd = os.getcwd()
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,  # 5 min max render
                cwd=cwd,
            )
            return (
                result.returncode,
                result.stdout.decode("utf-8", errors="replace"),
                result.stderr.decode("utf-8", errors="replace"),
            )
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def _run_ffprobe_sync(self, cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
        """Execute ffprobe synchronously in thread pool."""
        try:
            import os
            if cwd is None:
                cwd = os.getcwd()
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                cwd=cwd,
            )
            return (
                result.returncode,
                result.stdout.decode("utf-8", errors="replace"),
                result.stderr.decode("utf-8", errors="replace"),
            )
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def _calculate_sha256(self, file_path: Path) -> str:
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    async def render_video(
        self,
        scene_files: list[Path],
        audio_path: Path,
        subtitle_path: Path | None = None,
        thumbnail_time_ms: int = 1000,
    ) -> RenderResult:
        """
        Render final video from scenes, audio, and optional subtitles.

        Args:
            scene_files: List of image/video files for each scene (in order)
            audio_path: Path to narration audio file
            subtitle_path: Optional SRT/ASS subtitle file
            thumbnail_time_ms: Time to extract thumbnail

        Returns:
            RenderResult with video metadata
        """
        start_time = time.perf_counter()

        # Generate unique output filename
        file_id = uuid.uuid4().hex[:12]
        video_path = self._output_dir / f"render_{file_id}.mp4"
        thumbnail_path = self._output_dir / f"thumb_{file_id}.jpg"
        video_path_posix = video_path.as_posix()
        thumbnail_path_posix = thumbnail_path.as_posix()

        # Build filter complex for concatenating scenes with zoom/pan
        filter_parts = []
        input_files = []

        # Add scene inputs (use as_posix for Windows compatibility)
        for i, scene_file in enumerate(scene_files):
            input_files.extend(["-i", scene_file.as_posix()])

        # Add audio input
        input_files.extend(["-i", audio_path.as_posix()])

        # Add subtitle input if provided
        subtitle_input_idx = len(scene_files)
        if subtitle_path and subtitle_path.exists():
            input_files.extend(["-i", subtitle_path.as_posix()])

        # Calculate duration per scene to match target
        total_scenes = len(scene_files)
        scene_duration_ms = self._config.target_duration_ms // total_scenes

        # Build filter graph
        filter_idx = 0
        last_output = ""

        for i, scene_file in enumerate(scene_files):
            input_idx = i
            # Scale and pad to target resolution with zoom/pan effect
            filter_parts.append(
                f"[{input_idx}:v]scale={self._config.width}:{self._config.height}:force_original_aspect_ratio=decrease,"
                f"pad={self._config.width}:{self._config.height}:(ow-iw)/2:(oh-ih)/2,"
                f"zoompan=z='min(zoom+0.0015,1.2)':d={scene_duration_ms // (1000 // self._config.fps)}:s={self._config.width}x{self._config.height}:fps={self._config.fps}[v{i}]"
            )
            last_output = f"[v{i}]"

        # Concatenate all scene videos
        if total_scenes > 1:
            concat_inputs = "".join(f"[v{i}]" for i in range(total_scenes))
            filter_parts.append(f"{concat_inputs}concat=n={total_scenes}:v=1:a=0[video_out]")
            video_output = "[video_out]"
        else:
            video_output = "[v0]"

        # Add subtitles if provided (use as_posix for Windows)
        if subtitle_path and subtitle_path.exists():
            filter_parts.append(f"{video_output}subtitles='{subtitle_path.as_posix()}'[video_sub]")
            video_output = "[video_sub]"

        filter_complex = ";".join(filter_parts)

        # Build FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            *input_files,
            "-filter_complex", filter_complex,
            "-map", video_output,
            "-map", f"{len(scene_files)}:a",  # audio from narration
            "-c:v", self._config.preset.video_codec,
            *self._config.preset.video_codec_params,
            "-c:a", self._config.preset.audio_codec,
            "-b:a", self._config.preset.audio_bitrate,
            "-r", str(self._config.preset.fps),
            "-pix_fmt", self._config.preset.pixel_format,
            "-movflags", self._config.preset.movflags,
            "-shortest",  # stop at shortest stream (audio)
            video_path_posix,
        ]

        # Log command for reproducibility
        ffmpeg_cmd_str = " ".join(cmd)
        logger.info("Iniciando renderização FFmpeg", extra={
            "scenes": total_scenes,
            "target_duration_ms": self._config.target_duration_ms,
            "output": str(video_path),
            "cmd": ffmpeg_cmd_str,
        })

        # Execute in thread pool
        loop = asyncio.get_event_loop()
        returncode, stdout, stderr = await loop.run_in_executor(
            self._executor,
            self._run_ffmpeg_sync,
            cmd,
            self._project_root,
        )

        render_time_ms = int((time.perf_counter() - start_time) * 1000)

        if returncode != 0:
            logger.error("FFmpeg falhou", extra={"stderr": stderr, "cmd": ffmpeg_cmd_str})
            raise RuntimeError(f"FFmpeg falhou (exit {returncode}): {stderr}")

        if not video_path.exists():
            raise RuntimeError(f"FFmpeg não gerou arquivo de saída: {video_path}")

        # Extract thumbnail
        await self._extract_thumbnail(video_path, thumbnail_path, thumbnail_time_ms)

        # Validate with ffprobe
        video_info = await self._probe_video(video_path)

        # Calculate hash and size
        sha256 = self._calculate_sha256(video_path)
        file_size = video_path.stat().st_size

        return RenderResult(
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            sha256=sha256,
            duration_ms=video_info["duration_ms"],
            width=video_info["width"],
            height=video_info["height"],
            fps=video_info["fps"],
            video_codec=video_info["video_codec"],
            audio_codec=video_info["audio_codec"],
            file_size_bytes=file_size,
            ffmpeg_cmd=ffmpeg_cmd_str,
            render_time_ms=render_time_ms,
        )

    async def _extract_thumbnail(
        self,
        video_path: Path,
        thumbnail_path: Path,
        time_ms: int,
    ) -> None:
        """Extract thumbnail from video at specified time."""
        time_sec = time_ms / 1000.0
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(time_sec),
            "-i", video_path.as_posix(),
            "-vframes", "1",
            "-vf", f"scale={self._config.width}:{self._config.height}:force_original_aspect_ratio=decrease,pad={self._config.width}:{self._config.height}:(ow-iw)/2:(oh-ih)/2",
            thumbnail_path.as_posix(),
        ]

        loop = asyncio.get_event_loop()
        returncode, stdout, stderr = await loop.run_in_executor(
            self._executor,
            self._run_ffmpeg_sync,
            cmd,
            self._project_root,
        )

        if returncode != 0 or not thumbnail_path.exists():
            logger.warning("Falha ao extrair thumbnail", extra={"stderr": stderr})
            # Create placeholder if extraction fails
            if not thumbnail_path.exists():
                from PIL import Image
                img = Image.new("RGB", (self._config.width, self._config.height), (30, 30, 30))
                img.save(thumbnail_path, "JPEG", quality=85)

    async def _probe_video(self, video_path: Path) -> dict[str, Any]:
        """Probe video file for metadata using ffprobe."""
        # Get video stream info - order: codec_name, width, height, r_frame_rate
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path.as_posix(),
        ]

        loop = asyncio.get_event_loop()
        returncode, stdout, stderr = await loop.run_in_executor(
            self._executor,
            self._run_ffprobe_sync,
            cmd,
            self._project_root,
        )

        video_info = {
            "width": self._config.width,
            "height": self._config.height,
            "fps": float(self._config.preset.fps),
            "video_codec": self._config.preset.video_codec,
            "audio_codec": self._config.preset.audio_codec,
            "duration_ms": self._config.target_duration_ms,
        }

        if returncode == 0 and stdout:
            lines = [l.strip() for l in stdout.strip().split("\n") if l.strip()]
            # Expected order: codec_name, width, height, r_frame_rate
            if len(lines) >= 4:
                # Line 0: codec_name
                if lines[0] in ("h264", "libx264", "hevc", "libx265", "mpeg4", "av1"):
                    video_info["video_codec"] = lines[0]
                # Line 1: width
                if lines[1].isdigit():
                    video_info["width"] = int(lines[1])
                # Line 2: height
                if lines[2].isdigit():
                    video_info["height"] = int(lines[2])
                # Line 3: r_frame_rate
                if "/" in lines[3]:
                    try:
                        num, den = lines[3].split("/")
                        video_info["fps"] = float(num) / float(den) if float(den) > 0 else video_info["fps"]
                    except ValueError:
                        pass

        # Get duration and audio codec
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path.as_posix(),
        ]

        returncode, stdout, stderr = await loop.run_in_executor(
            self._executor,
            self._run_ffprobe_sync,
            cmd,
            self._project_root,
        )

        if returncode == 0 and stdout:
            lines = [l.strip() for l in stdout.strip().split("\n") if l.strip()]
            # First line is duration
            if lines:
                try:
                    video_info["duration_ms"] = int(float(lines[0]) * 1000)
                except (ValueError, IndexError):
                    pass
            # Find audio codec (aac, mp3, etc.)
            for line in lines:
                if line in ("aac", "libfdk_aac", "mp3", "libmp3lame", "opus", "vorbis"):
                    video_info["audio_codec"] = line
                    break

        return video_info

    async def health_check(self) -> bool:
        """Check if FFmpeg and ffprobe are available."""
        try:
            for cmd in [["ffmpeg", "-version"], ["ffprobe", "-version"]]:
                loop = asyncio.get_event_loop()
                returncode, stdout, stderr = await loop.run_in_executor(
                    self._executor,
                    self._run_ffmpeg_sync if cmd[0] == "ffmpeg" else self._run_ffprobe_sync,
                    cmd,
                )
                if returncode != 0:
                    return False
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close thread pool."""
        self._executor.shutdown(wait=True)