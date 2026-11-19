"""Publicador assistido - cria pacote local para publicação manual no TikTok."""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from backend.app.core.config import get_settings
from backend.app.providers.publishing.base import PublicationPackage, PublicationResult, Publisher

logger = logging.getLogger(__name__)


class AssistedPublisher(Publisher):
    """Prepara pacote de exportação para publicação manual pelo usuário."""

    def __init__(self, export_root: Path | None = None):
        settings = get_settings()
        self._export_root = export_root or Path(settings.LOCAL_STORAGE_ROOT) / "exports"
        self._export_root.mkdir(parents=True, exist_ok=True)

    @property
    def publisher_name(self) -> str:
        return "assisted"

    @property
    def cost_class(self) -> str:
        return "zero"

    @property
    def mode(self) -> str:
        return "assisted"

    async def prepare_package(self, package: PublicationPackage) -> PublicationResult:
        """Cria pasta de exportação com tudo necessário para publicação manual."""
        try:
            # Criar diretório de exportação com timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            export_dir = self._export_root / f"tiktok_{package.project_id}_{package.revision}_{timestamp}"
            export_dir.mkdir(parents=True, exist_ok=True)

            # Copiar vídeo
            video_dest = export_dir / f"video_{package.project_id}.mp4"
            shutil.copy2(package.video_path, video_dest)

            # Copiar thumbnail se existir
            thumbnail_dest = None
            if package.thumbnail_path and package.thumbnail_path.exists():
                thumbnail_dest = export_dir / f"thumbnail_{package.project_id}.png"
                shutil.copy2(package.thumbnail_path, thumbnail_dest)

            # Escrever caption.txt
            caption_file = export_dir / "caption.txt"
            caption_content = f"{package.caption}\n\n{' '.join(package.hashtags)}"
            caption_file.write_text(caption_content, encoding="utf-8")

            # Escrever metadata.json
            meta_file = export_dir / "metadata.json"
            metadata = {
                "project_id": str(package.project_id),
                "revision": package.revision,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "mode": self.mode,
                "video_file": video_dest.name,
                "thumbnail_file": thumbnail_dest.name if thumbnail_dest else None,
                "caption": package.caption,
                "hashtags": package.hashtags,
                "privacy_settings": package.privacy_settings,
                "extra": package.metadata,
            }
            meta_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

            # Escrever instruções para o usuário
            instructions_file = export_dir / "INSTRUCTIONS.txt"
            instructions = self._generate_instructions(package, video_dest.name, thumbnail_dest.name if thumbnail_dest else None)
            instructions_file.write_text(instructions, encoding="utf-8")

            logger.info("Pacote de exportação assistida criado", extra={
                "project_id": str(package.project_id),
                "export_dir": str(export_dir),
            })

            return PublicationResult(
                success=True,
                mode=self.mode,
                external_id=None,
                export_path=str(export_dir),
                error=None,
                evidence={
                    "export_dir": str(export_dir),
                    "files": [f.name for f in export_dir.iterdir()],
                },
            )

        except Exception as e:
            logger.error("Falha ao criar pacote assistido", extra={"error": str(e)})
            return PublicationResult(
                success=False,
                mode=self.mode,
                external_id=None,
                export_path=None,
                error=f"{type(e).__name__}: {e}",
                evidence={},
            )

    def _generate_instructions(
        self,
        package: PublicationPackage,
        video_filename: str,
        thumbnail_filename: str | None,
    ) -> str:
        """Gera instruções passo a passo para publicação manual."""
        lines = [
            "═══════════════════════════════════════",
            "  AI TREND CREATOR - PUBLICAÇÃO ASSISTIDA",
            "═══════════════════════════════════════",
            "",
            f"Projeto: {package.project_id} (rev {package.revision})",
            f"Exportado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "ARQUIVOS INCLUÍDOS:",
            f"  ✓ {video_filename} — Vídeo final (MP4 9:16)",
        ]
        if thumbnail_filename:
            lines.append(f"  ✓ {thumbnail_filename} — Thumbnail")
        lines.extend([
            f"  ✓ caption.txt — Legenda + hashtags prontas",
            f"  ✓ metadata.json — Metadados completos",
            "",
            "PASSOS PARA PUBLICAR NO TIKTOK:",
            "",
            "1. Abra o app TikTok no seu celular",
            "2. Toque no botão '+' (criar)",
            "3. Selecione 'Carregar' (canto inferior direito)",
            f"4. Escolha o arquivo: {video_filename}",
            "5. Se houver thumbnail: toque em 'Selecionar capa' e escolha a imagem",
            "6. Copie o texto de 'caption.txt' para a legenda",
            "7. Configure privacidade conforme sua preferência",
            "8. Toque em 'Publicar'",
            "",
            "IMPORTANTE:",
            "• Este vídeo contém conteúdo gerado por IA — marque a opção 'Conteúdo gerado por IA' no TikTok",
            "• Verifique se a legenda e hashtags estão adequadas",
            "• Após publicar, registre o link/ID do vídeo no sistema para auditoria",
            "",
            "ARQUIVOS DE AUDITORIA:",
            f"  • metadata.json — Contém hash do vídeo, provedores, licenças, rastreabilidade",
            f"  • Este pacote fica salvo em: {package.export_dir}",
            "",
            "═══════════════════════════════════════",
        ])
        return "\n".join(lines)

    async def health_check(self) -> bool:
        """Verifica se diretório de exportação é gravável."""
        try:
            test_dir = self._export_root / ".health_check"
            test_dir.mkdir(exist_ok=True)
            (test_dir / "test.txt").write_text("ok")
            shutil.rmtree(test_dir)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        pass