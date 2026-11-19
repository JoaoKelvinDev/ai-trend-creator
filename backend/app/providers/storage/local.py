"""Implementação de storage local no filesystem."""

import hashlib
import json
import logging
import mimetypes
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from backend.app.core.config import get_settings
from backend.app.providers.storage.base import AssetMetadata, AssetStore

logger = logging.getLogger(__name__)


class LocalAssetStore(AssetStore):
    """Armazenamento local com metadados em JSON sidecar."""

    def __init__(self, root_dir: Path | None = None):
        settings = get_settings()
        self._root = root_dir or Path(settings.LOCAL_STORAGE_ROOT) / "assets"
        self._root.mkdir(parents=True, exist_ok=True)
        self._metadata_dir = self._root / ".metadata"
        self._metadata_dir.mkdir(exist_ok=True)

    @property
    def store_type(self) -> str:
        return "local"

    async def put(self, file_path: Path, *, asset_id: UUID, kind: str, metadata: dict[str, Any]) -> AssetMetadata:
        """Copia arquivo para storage e salva metadados."""
        # Determinar extensão
        ext = file_path.suffix or self._guess_extension(metadata.get("mime_type"))
        dest_path = self._root / kind / f"{asset_id}{ext}"
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copiar arquivo
        shutil.copy2(file_path, dest_path)

        # Calcular hash
        sha256 = self._calculate_sha256(dest_path)
        size_bytes = dest_path.stat().st_size
        mime_type = metadata.get("mime_type") or mimetypes.guess_type(dest_path.name)[0] or "application/octet-stream"

        # Extrair dimensões se imagem/vídeo
        width = metadata.get("width")
        height = metadata.get("height")
        duration_ms = metadata.get("duration_ms")

        # Preparar metadados
        meta = AssetMetadata(
            asset_id=asset_id,
            kind=kind,
            sha256=sha256,
            mime_type=mime_type,
            size_bytes=size_bytes,
            width=width,
            height=height,
            duration_ms=duration_ms,
            provider=metadata.get("provider", "unknown"),
            model=metadata.get("model", "unknown"),
            license_ref=metadata.get("license_ref", "unknown"),
            created_at=datetime.now(timezone.utc).isoformat(),
            extra={k: v for k, v in metadata.items() if k not in (
                "width", "height", "duration_ms", "provider", "model", "license_ref", "mime_type"
            )},
        )

        # Salvar metadados sidecar
        self._save_metadata(asset_id, meta)

        logger.info("Asset armazenado", extra={"asset_id": str(asset_id), "path": str(dest_path), "size": size_bytes})
        return meta

    async def get(self, asset_id: UUID) -> Path | None:
        """Retorna caminho do arquivo se existir."""
        # Procurar arquivo com qualquer extensão
        for ext in [".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".mp4", ".mov", ".srt", ".ass", ".json", ".txt"]:
            path = self._root / "*" / f"{asset_id}{ext}"
            matches = list(self._root.glob(f"*/{asset_id}{ext}"))
            if matches:
                return matches[0]
        return None

    async def delete(self, asset_id: UUID) -> bool:
        """Remove arquivo e metadados."""
        deleted = False
        # Remover arquivo
        for ext in [".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".mp4", ".mov", ".srt", ".ass", ".json", ".txt"]:
            matches = list(self._root.glob(f"*/{asset_id}{ext}"))
            for path in matches:
                path.unlink(missing_ok=True)
                deleted = True

        # Remover metadados
        meta_path = self._metadata_dir / f"{asset_id}.json"
        if meta_path.exists():
            meta_path.unlink()
            deleted = True

        return deleted

    async def get_metadata(self, asset_id: UUID) -> AssetMetadata | None:
        """Lê metadados do sidecar JSON."""
        meta_path = self._metadata_dir / f"{asset_id}.json"
        if not meta_path.exists():
            return None

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return AssetMetadata(**data)
        except Exception as e:
            logger.warning("Erro ao ler metadados", extra={"asset_id": str(asset_id), "error": str(e)})
            return None

    async def list_by_project(self, project_id: UUID) -> list[AssetMetadata]:
        """Lista assets filtrando por project_id no metadata extra."""
        results = []
        for meta_path in self._metadata_dir.glob("*.json"):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                if data.get("extra", {}).get("owner_project_id") == str(project_id):
                    results.append(AssetMetadata(**data))
            except Exception:
                continue
        return results

    async def health_check(self) -> bool:
        """Verifica se diretório é gravável."""
        try:
            test_file = self._root / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
            return True
        except Exception:
            return False

    def _save_metadata(self, asset_id: UUID, metadata: AssetMetadata) -> None:
        """Salva metadados como JSON."""
        meta_path = self._metadata_dir / f"{asset_id}.json"
        # Converter para dict serializável
        data = {
            "asset_id": str(metadata.asset_id),
            "kind": metadata.kind,
            "sha256": metadata.sha256,
            "mime_type": metadata.mime_type,
            "size_bytes": metadata.size_bytes,
            "width": metadata.width,
            "height": metadata.height,
            "duration_ms": metadata.duration_ms,
            "provider": metadata.provider,
            "model": metadata.model,
            "license_ref": metadata.license_ref,
            "created_at": metadata.created_at,
            "extra": metadata.extra,
        }
        meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _calculate_sha256(self, file_path: Path) -> str:
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _guess_extension(self, mime_type: str | None) -> str:
        if not mime_type:
            return ".bin"
        ext = mimetypes.guess_extension(mime_type)
        return ext or ".bin"