import logging
import os
from pathlib import Path, PurePosixPath

from django import template
from django.conf import settings
from PIL import Image, ImageOps

register = template.Library()
logger = logging.getLogger(__name__)


THUMBNAIL_MAX_SIZE = 640
THUMBNAIL_QUALITY = 82
THUMBNAIL_ROOT = "_thumbnails"


def _thumbnail_name(original_name: str, max_size: int) -> str:
    """Return a deterministic media-relative thumbnail name."""
    source = PurePosixPath(original_name)
    thumb_filename = f"{source.name}.{max_size}.jpg"
    return str(PurePosixPath(THUMBNAIL_ROOT) / source.parent / thumb_filename)


def _prepare_for_jpeg(image: Image.Image) -> Image.Image:
    """Convert an image to RGB while preserving transparency on white."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background

    if image.mode != "RGB":
        return image.convert("RGB")

    return image


@register.simple_tag
def thumbnail_url(image_field, max_size=THUMBNAIL_MAX_SIZE):
    """
    Create (once) and return the URL of a lightweight JPEG thumbnail.

    The original ImageField file is never modified. Thumbnails are stored
    under MEDIA_ROOT/_thumbnails/... and are regenerated only if the source
    image is newer than the thumbnail.
    """
    if not image_field:
        return ""

    try:
        original_name = image_field.name
        if not original_name:
            return ""

        max_size = int(max_size)
        source_path = Path(image_field.path)

        if not source_path.is_file():
            logger.warning("Thumbnail source does not exist: %s", source_path)
            return image_field.url

        thumb_name = _thumbnail_name(original_name, max_size)
        thumb_path = Path(settings.MEDIA_ROOT) / Path(thumb_name)

        source_mtime = source_path.stat().st_mtime
        if thumb_path.is_file() and thumb_path.stat().st_mtime >= source_mtime:
            return image_field.storage.url(thumb_name)

        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = thumb_path.with_name(f".{thumb_path.name}.{os.getpid()}.tmp")

        try:
            with Image.open(source_path) as source:
                image = ImageOps.exif_transpose(source)
                resampling = getattr(Image, "Resampling", Image)
                image.thumbnail((max_size, max_size), resampling.LANCZOS)
                image = _prepare_for_jpeg(image)
                image.save(
                    temp_path,
                    format="JPEG",
                    quality=THUMBNAIL_QUALITY,
                    optimize=True,
                )

            os.replace(temp_path, thumb_path)
            os.utime(thumb_path, (source_mtime, source_mtime))
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

        return image_field.storage.url(thumb_name)

    except Exception:
        logger.exception("Could not create thumbnail for %r", image_field)
        try:
            return image_field.url
        except Exception:
            return ""
