"""Provedor de imagem mock para testes determinísticos."""

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from backend.app.providers.images.base import ImageProvider, ImageResult, ImageSpec

logger = logging.getLogger(__name__)


class MockImageProvider(ImageProvider):
    """Provedor mock que gera imagens placeholder determinísticas."""

    def __init__(self, output_dir: Path | None = None, should_fail: bool = False):
        from backend.app.core.config import get_settings
        settings = get_settings()
        self._output_dir = output_dir or Path(settings.LOCAL_STORAGE_ROOT) / "assets" / "mocks"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._should_fail = should_fail
        self._call_count = 0

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_id(self) -> str:
        return "mock-image-v1"

    @property
    def cost_class(self) -> str:
        return "zero"

    @property
    def license(self) -> str:
        return "CC0"

    async def generate_image(self, spec: ImageSpec) -> ImageResult:
        self._call_count += 1

        if self._should_fail:
            raise RuntimeError("MockImageProvider configured to fail")

        # Criar imagem placeholder colorida baseada no seed
        seed = spec.seed or self._call_count
        import random
        rng = random.Random(seed)

        color = (rng.randint(50, 200), rng.randint(50, 200), rng.randint(50, 200))
        img = Image.new("RGB", (spec.width, spec.height), color)

        # Adicionar texto indicando que é mock
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        except Exception:
            font = ImageFont.load_default()

        text = f"MOCK IMAGE #{self._call_count}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (spec.width - text_w) // 2
        y = (spec.height - text_h) // 2

        # Sombra
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 180))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        # Salvar
        file_id = uuid.uuid4().hex[:12]
        file_path = self._output_dir / f"mock_image_{file_id}.png"
        img.save(file_path, format="PNG")

        # Calcular hash
        sha256 = self._calculate_sha256(file_path)

        return ImageResult(
            image_path=file_path,
            sha256=sha256,
            mime_type="image/png",
            width=img.width,
            height=img.height,
            provider=self.provider_name,
            model=self.model_id,
            license_ref=self.license,
            metadata={
                "mock_call": self._call_count,
                "prompt": spec.prompt[:200],
                "seed": spec.seed,
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

    def set_should_fail(self, should_fail: bool) -> None:
        self._should_fail = should_fail

    def get_call_count(self) -> int:
        return self._call_count