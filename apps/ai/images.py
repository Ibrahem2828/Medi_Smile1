# apps/ai/images.py
"""
Validation and sanitisation of patient dental photos before AI analysis.

Every upload is decoded with Pillow (never trusting the client's filename or
Content-Type), bounded in bytes and pixels, rotated according to EXIF, scaled
down to a sane working size and re-encoded. Re-encoding strips all metadata —
phone photos routinely carry GPS coordinates and device identifiers, which
must not be stored with medical data.
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

# Pillow format name -> (MIME type, save format)
_ALLOWED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def _max_bytes() -> int:
    return int(getattr(settings, "AI_IMAGE_MAX_BYTES", 10 * 1024 * 1024))


def _max_pixels() -> int:
    return int(getattr(settings, "AI_IMAGE_MAX_PIXELS", 40_000_000))


def _max_side() -> int:
    return int(getattr(settings, "AI_IMAGE_MAX_SIDE", 2048))


@dataclass(frozen=True)
class SanitizedImage:
    content: bytes
    content_type: str
    width: int
    height: int
    sha256: str

    @property
    def extension(self) -> str:
        return {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[self.content_type]


def sanitize_image(uploaded_file) -> SanitizedImage:
    """
    Validate an uploaded file and return a clean, metadata-free re-encoding.
    Raises ``serializers.ValidationError`` with a user-facing message.
    """
    size = getattr(uploaded_file, "size", None)
    if size is None or size <= 0:
        raise serializers.ValidationError(_("The uploaded image is empty."))
    if size > _max_bytes():
        raise serializers.ValidationError(
            _("The image is too large (maximum %(mb)d MB).") % {"mb": _max_bytes() // (1024 * 1024)}
        )

    raw = uploaded_file.read()
    try:
        # Header-only parse: size is known before any pixel data is decoded,
        # so decompression bombs are rejected cheaply.
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            width, height = probe.size
            if fmt not in _ALLOWED_FORMATS:
                raise serializers.ValidationError(_("Unsupported image format. Use JPEG, PNG or WebP."))
            if width * height > _max_pixels():
                raise serializers.ValidationError(_("The image resolution is too high."))
            probe.verify()

        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            img = ImageOps.exif_transpose(img)
            if max(img.size) > _max_side():
                img.thumbnail((_max_side(), _max_side()), Image.Resampling.LANCZOS)

            content_type = _ALLOWED_FORMATS[fmt]
            out = io.BytesIO()
            if content_type == "image/png":
                img.save(out, format="PNG", optimize=True)
            elif content_type == "image/webp":
                img.save(out, format="WEBP", quality=92)
            else:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(out, format="JPEG", quality=92, optimize=True)
            final_width, final_height = img.size
    except serializers.ValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise serializers.ValidationError(_("The uploaded file is not a valid image."))

    content = out.getvalue()
    return SanitizedImage(
        content=content,
        content_type=content_type,
        width=final_width,
        height=final_height,
        sha256=hashlib.sha256(content).hexdigest(),
    )
