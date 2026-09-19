from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR
from app.domain.models import FashionAsset, WardrobeItem
from app.fashion.services import FashionNotFound


FASHION_MEDIA_DIR = DATA_DIR / "fashion"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 12_000_000
ALLOWED_INPUT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class InvalidFashionImage(ValueError):
    pass


def _safe_path(storage_key: str, *, thumbnail: bool = False) -> Path:
    # O valor vem do banco, mas ainda rejeitamos separadores para que um banco
    # corrompido nunca transforme a rota de mídia em leitura arbitrária de arquivo.
    if not storage_key or Path(storage_key).name != storage_key:
        raise FashionNotFound("Imagem não encontrada")
    suffix = ".thumb.webp" if thumbnail else ".webp"
    if not storage_key.endswith(".webp"):
        raise FashionNotFound("Imagem não encontrada")
    name = storage_key.removesuffix(".webp") + suffix
    path = FASHION_MEDIA_DIR / name
    if path.resolve().parent != FASHION_MEDIA_DIR.resolve():
        raise FashionNotFound("Imagem não encontrada")
    return path


def store_image(db: Session, owner_id: int, content: bytes, claimed_content_type: str | None) -> FashionAsset:
    if not content:
        raise InvalidFashionImage("Envie uma imagem.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise InvalidFashionImage("A imagem excede o limite de 10 MB.")
    if claimed_content_type and claimed_content_type.lower() not in ALLOWED_INPUT_TYPES:
        raise InvalidFashionImage("Use uma imagem JPEG, PNG ou WebP.")
    try:
        with Image.open(io.BytesIO(content)) as source:
            source.verify()
        with Image.open(io.BytesIO(content)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidFashionImage("O arquivo não contém uma imagem válida.") from exc
    if image.width <= 0 or image.height <= 0 or image.width * image.height > MAX_PIXELS:
        raise InvalidFashionImage("A imagem excede as dimensões permitidas.")

    FASHION_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid4().hex}.webp"
    image_path = _safe_path(storage_key)
    thumb_path = _safe_path(storage_key, thumbnail=True)
    # WebP reencodado elimina EXIF. Arquivo temporário + replace evita deixar um
    # arquivo parcialmente gravado sendo servido por outra requisição.
    for target, rendered in ((image_path, image), (thumb_path, image.copy())):
        if target == thumb_path:
            rendered.thumbnail((360, 360))
        temporary = target.with_suffix(target.suffix + ".tmp")
        rendered.save(temporary, format="WEBP", quality=88, method=6)
        os.replace(temporary, target)

    asset = FashionAsset(
        owner_id=owner_id,
        storage_key=storage_key,
        mime_type="image/webp",
        width=image.width,
        height=image.height,
        byte_size=image_path.stat().st_size,
        sha256=hashlib.sha256(content).hexdigest(),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def resolve_asset(db: Session, owner_id: int, asset_id: int) -> FashionAsset:
    asset = db.get(FashionAsset, asset_id)
    if asset is None or asset.owner_id != owner_id:
        raise FashionNotFound("Imagem não encontrada")
    return asset


def remove_asset(db: Session, owner_id: int, asset_id: int) -> None:
    asset = resolve_asset(db, owner_id, asset_id)
    linked = db.query(WardrobeItem).filter_by(image_asset_id=asset.id).count()
    if linked:
        raise InvalidFashionImage("A imagem ainda está vinculada a uma peça.")
    paths = (_safe_path(asset.storage_key), _safe_path(asset.storage_key, thumbnail=True))
    db.delete(asset)
    db.commit()
    for path in paths:
        path.unlink(missing_ok=True)
