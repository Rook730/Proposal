"""Appendix images: pictures and drawings attached to a proposal.

Files are kept in projects/<folder>/images/ under a new name each time one is added, and are never changed or
deleted by the app, so an issued revision always prints the pictures it was issued with. Photos are scaled down
(longest side MAX_SIDE pixels) and saved as JPEG so a phone photo does not make the PDF large; PNG drawings and
SVG files are kept as they are (PNG is scaled down only when larger than MAX_SIDE).
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path

ALLOWED = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
MAX_SIDE = 2000
JPEG_QUALITY = 85


def normalize(data: bytes, suffix: str) -> tuple[bytes, str]:
    """Return (bytes, extension) ready to store. Raises ValueError for unsupported files."""
    suffix = suffix.lower()
    if suffix not in ALLOWED:
        raise ValueError(f"{suffix or 'this file type'} is not supported; use PNG, JPG, GIF or SVG")
    if suffix == ".svg":
        return data, ".svg"
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception as e:  # noqa: BLE001  Pillow raises several error types for bad files
        raise ValueError(f"not a readable image ({e})") from None
    if suffix == ".gif":
        suffix = ".png"                                  # first frame only
    im = ImageOps.exif_transpose(im)                     # phone photos: apply the camera rotation
    if max(im.size) > MAX_SIDE:
        im.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    if suffix in (".jpg", ".jpeg"):
        im.convert("RGB").save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return out.getvalue(), ".jpg"
    im.save(out, "PNG", optimize=True)
    return out.getvalue(), ".png"


def add_image(folder: Path, data: bytes, original_name: str) -> str:
    """Store an image in folder (created if needed); returns the stored file name."""
    body, ext = normalize(data, Path(original_name).suffix)
    folder.mkdir(parents=True, exist_ok=True)
    stem = "".join(c if c.isalnum() else "_" for c in Path(original_name).stem)[:40].strip("_") or "image"
    name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
    (folder / name).write_bytes(body)
    return name
