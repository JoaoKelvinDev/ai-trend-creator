"""Provedor de imagem via templates programáticos (Pillow/SVG) - fallback sem GPU."""

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from backend.app.core.config import get_settings
from backend.app.providers.images.base import ImageProvider, ImageResult, ImageSpec

logger = logging.getLogger(__name__)


class TemplateImageProvider(ImageProvider):
    """Gera imagens programáticas usando Pillow (gráficos, texto, formas).

    Fallback quando ComfyUI não está disponível ou GPU insuficiente.
    Não usa IA generativa - cria visualizações originais determinísticas.
    """

    def __init__(self, output_dir: Path | None = None):
        settings = get_settings()
        self._output_dir = output_dir or Path(settings.LOCAL_STORAGE_ROOT) / "assets" / "templates"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    @property
    def provider_name(self) -> str:
        return "template"

    @property
    def model_id(self) -> str:
        return "pillow-template-v1"

    @property
    def cost_class(self) -> str:
        return "zero"

    @property
    def license(self) -> str:
        return "CC0"  # Gráficos originais programáticos - domínio público

    async def generate_image(self, spec: ImageSpec) -> ImageResult:
        """Gera imagem baseada em template programático."""
        # Determinar tipo de template baseado no prompt/contexto
        template_type = self._infer_template_type(spec)

        if template_type == "text_card":
            image = await self._generate_text_card(spec)
        elif template_type == "gradient_bg":
            image = await self._generate_gradient_background(spec)
        elif template_type == "data_viz":
            image = await self._generate_data_visualization(spec)
        else:
            image = await self._generate_abstract_composition(spec)

        # Salvar
        file_id = uuid.uuid4().hex[:12]
        file_path = self._output_dir / f"template_{template_type}_{file_id}.png"
        image.save(file_path, format="PNG", optimize=True)

        # Calcular hash
        sha256 = self._calculate_sha256(file_path)

        return ImageResult(
            image_path=file_path,
            sha256=sha256,
            mime_type="image/png",
            width=image.width,
            height=image.height,
            provider=self.provider_name,
            model=self.model_id,
            license_ref=self.license,
            metadata={
                "template_type": template_type,
                "prompt": spec.prompt[:200],
                "seed": spec.seed,
                "provenance": "programmatic_template",
            },
        )

    def _infer_template_type(self, spec: ImageSpec) -> str:
        """Infere tipo de template baseado no prompt e metadados."""
        prompt_lower = spec.prompt.lower()
        meta = spec.metadata or {}

        if meta.get("visual_kind") == "text_card" or "text card" in prompt_lower or "titulo" in prompt_lower:
            return "text_card"
        elif meta.get("visual_kind") == "original_motion_graphic" or "grafico" in prompt_lower or "chart" in prompt_lower:
            return "data_viz"
        elif "gradiente" in prompt_lower or "background" in prompt_lower or "fundo" in prompt_lower:
            return "gradient_bg"
        return "abstract"

    async def _generate_text_card(self, spec: ImageSpec) -> Image.Image:
        """Gera card de texto para títulos/legendas."""
        img = Image.new("RGBA", (spec.width, spec.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Fundo com gradiente sutil
        for y in range(spec.height):
            alpha = int(200 * (1 - y / spec.height))
            color = (20, 20, 40, alpha)
            draw.line([(0, y), (spec.width, y)], fill=color)

        # Texto principal
        font_large = self._get_font("DejaVuSans-Bold.ttf", max(48, spec.height // 20))
        font_small = self._get_font("DejaVuSans.ttf", max(24, spec.height // 40))

        # Quebrar texto em linhas
        lines = self._wrap_text(spec.prompt, font_large, spec.width - 100)
        line_height = font_large.getbbox("Ag")[3] + 10
        total_height = len(lines) * line_height
        start_y = (spec.height - total_height) // 2

        for i, line in enumerate(lines):
            y = start_y + i * line_height
            # Sombra
            draw.text((spec.width // 2 + 3, y + 3), line, font=font_large, fill=(0, 0, 0, 180), anchor="mm")
            # Texto principal
            draw.text((spec.width // 2, y), line, font=font_large, fill=(255, 255, 255, 255), anchor="mm")

        return img.convert("RGB")

    async def _generate_gradient_background(self, spec: ImageSpec) -> Image.Image:
        """Gera fundo gradiente abstrato."""
        img = Image.new("RGB", (spec.width, spec.height))
        draw = ImageDraw.Draw(img)

        # Cores baseadas no seed para consistência
        seed = spec.seed or 42
        import random
        rng = random.Random(seed)

        color1 = (rng.randint(20, 80), rng.randint(20, 80), rng.randint(60, 120))
        color2 = (rng.randint(10, 50), rng.randint(60, 120), rng.randint(20, 80))

        for y in range(spec.height):
            ratio = y / spec.height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(0, y), (spec.width, y)], fill=(r, g, b))

        # Adicionar formas geométricas sutis
        for _ in range(5):
            x = rng.randint(0, spec.width)
            y = rng.randint(0, spec.height)
            size = rng.randint(50, 300)
            alpha = rng.randint(20, 60)
            overlay = Image.new("RGBA", (spec.width, spec.height), (0, 0, 0, 0))
            odraw = ImageDraw.Draw(overlay)
            shape_color = (rng.randint(100, 255), rng.randint(100, 255), rng.randint(100, 255), alpha)
            if rng.random() > 0.5:
                odraw.ellipse([x - size, y - size, x + size, y + size], fill=shape_color)
            else:
                odraw.rectangle([x - size, y - size, x + size, y + size], fill=shape_color)
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        return img

    async def _generate_data_visualization(self, spec: ImageSpec) -> Image.Image:
        """Gera visualização de dados simples (barras, linhas)."""
        img = Image.new("RGB", (spec.width, spec.height), (15, 15, 30))
        draw = ImageDraw.Draw(img)

        import random
        rng = random.Random(spec.seed or 123)

        # Gerar dados mock
        num_points = rng.randint(5, 10)
        data = [rng.randint(10, 100) for _ in range(num_points)]
        max_val = max(data)

        # Desenhar gráfico de barras
        bar_width = spec.width // (num_points * 2)
        spacing = spec.width // (num_points + 1)
        bottom = spec.height - 100
        top = 100

        for i, val in enumerate(data):
            x = (i + 1) * spacing
            bar_height = int((val / max_val) * (bottom - top))
            color = (50 + i * 20, 150, 200)
            draw.rectangle(
                [x - bar_width // 2, bottom - bar_height, x + bar_width // 2, bottom],
                fill=color,
            )
            # Valor no topo
            font = self._get_font("DejaVuSans.ttf", 16)
            draw.text((x, bottom - bar_height - 25), str(val), font=font, fill=(255, 255, 255), anchor="mm")

        # Título
        font_title = self._get_font("DejaVuSans-Bold.ttf", 32)
        draw.text((spec.width // 2, 50), "Visualização de Dados", font=font_title, fill=(255, 255, 255), anchor="mm")

        return img

    async def _generate_abstract_composition(self, spec: ImageSpec) -> Image.Image:
        """Gera composição abstrata geométrica."""
        img = Image.new("RGB", (spec.width, spec.height), (10, 10, 20))
        draw = ImageDraw.Draw(img)

        import random
        rng = random.Random(spec.seed or 999)

        # Formas geométricas aleatórias mas determinísticas
        num_shapes = rng.randint(8, 20)
        for _ in range(num_shapes):
            shape_type = rng.choice(["circle", "rect", "triangle", "line"])
            x = rng.randint(0, spec.width)
            y = rng.randint(0, spec.height)
            size = rng.randint(20, 200)
            color = (
                rng.randint(50, 255),
                rng.randint(50, 255),
                rng.randint(50, 255),
                rng.randint(40, 120),
            )

            overlay = Image.new("RGBA", (spec.width, spec.height), (0, 0, 0, 0))
            odraw = ImageDraw.Draw(overlay)

            if shape_type == "circle":
                odraw.ellipse([x - size, y - size, x + size, y + size], fill=color)
            elif shape_type == "rect":
                odraw.rectangle([x - size, y - size // 2, x + size, y + size // 2], fill=color)
            elif shape_type == "triangle":
                odraw.polygon([(x, y - size), (x - size, y + size), (x + size, y + size)], fill=color)
            else:
                width = rng.randint(2, 8)
                odraw.line([x - size, y, x + size, y], fill=color, width=width)

            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        return img

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """Quebra texto em linhas que cabem na largura."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [text]

    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        """Carrega fonte com cache."""
        key = (font_name, size)
        if key not in self._font_cache:
            try:
                # Tentar fontes do sistema
                import os
                font_paths = [
                    f"/usr/share/fonts/truetype/dejavu/{font_name}",
                    f"/usr/share/fonts/TTF/{font_name}",
                    f"C:/Windows/Fonts/{font_name.replace('DejaVuSans', 'DejaVuSans')}",
                ]
                font_path = None
                for p in font_paths:
                    if os.path.exists(p):
                        font_path = p
                        break
                if font_path:
                    self._font_cache[key] = ImageFont.truetype(font_path, size)
                else:
                    self._font_cache[key] = ImageFont.load_default()
            except Exception:
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _calculate_sha256(self, file_path: Path) -> str:
        """Calcula SHA256 do arquivo."""
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        pass