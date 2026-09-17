from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image, UnidentifiedImageError

from pgs_search.models.document import SearchDocument
from pgs_search.query.normalizer import detect_language

# Nepali + English in one OCR pass.
OCR_LANGUAGES = "nep+eng"

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}


def extract_text_from_image(image_path: Path) -> str:
    """Run OCR on a single image. Returns an empty string (not an
    error) if OCR fails or the image has no text -- an image with no
    embedded text is still a valid document via metadata alone."""
    try:
        with Image.open(image_path) as img:
            text = pytesseract.image_to_string(img, lang=OCR_LANGUAGES)
        return text.strip()
    except (OSError, UnidentifiedImageError, pytesseract.TesseractError):
        return ""


def build_image_document(
    image_path: Path,
    ocr_text: str,
    *,
    alt_text: str = "",
    surrounding_context: str = "",
    parent_page_url: str = "",
    domain: str = "",
) -> SearchDocument:
    """Build a SearchDocument for an image, matching the same schema
    used for web pages -- content_type distinguishes it at query time.
    """
    searchable_parts = [part for part in (ocr_text, alt_text, surrounding_context) if part]
    searchable_text = " ".join(searchable_parts)

    return SearchDocument(
        document_id=f"img_{image_path.stem}",
        title=alt_text or image_path.stem,
        description=surrounding_context or None,
        searchable_text=searchable_text,
        source_url=parent_page_url or f"file://{image_path}",
        domain=domain,
        language=detect_language(searchable_text) if searchable_text else "unknown",
        content_type="image",
    )


def iter_images(images_dir: Path) -> list[Path]:
    """Find all supported image files under a directory, recursively."""
    return sorted(p for p in images_dir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS)
