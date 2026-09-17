from pathlib import Path

import pytest
from PIL import Image

from pgs_search.ingestion.image_indexer import (
    SUPPORTED_EXTENSIONS,
    build_image_document,
    extract_text_from_image,
    iter_images,
)


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    path = tmp_path / "notice.png"
    Image.new("RGB", (10, 10), color="white").save(path)
    return path


def test_extract_text_from_image_returns_ocr_output(sample_image, monkeypatch):
    monkeypatch.setattr(
        "pgs_search.ingestion.image_indexer.pytesseract.image_to_string",
        lambda img, lang: "  Road closure notice  ",
    )
    assert extract_text_from_image(sample_image) == "Road closure notice"


def test_extract_text_from_image_returns_empty_string_on_missing_file(tmp_path):
    missing_path = tmp_path / "missing.png"
    assert extract_text_from_image(missing_path) == ""


def test_build_image_document_combines_ocr_and_metadata(sample_image):
    document = build_image_document(
        sample_image,
        "Road closure notice",
        alt_text="Notice about road closure",
        surrounding_context="Municipality announced road maintenance work.",
        parent_page_url="https://example.gov.np/notices/1",
        domain="example.gov.np",
    )
    assert document.content_type == "image"
    assert document.document_id == "img_notice"
    assert "Road closure notice" in document.searchable_text
    assert "Municipality announced" in document.searchable_text
    assert document.source_url == "https://example.gov.np/notices/1"
    assert document.domain == "example.gov.np"


def test_build_image_document_falls_back_to_filename_title(sample_image):
    document = build_image_document(sample_image, "")
    assert document.title == "notice"
    assert document.source_url.startswith("file://")
    assert document.language == "unknown"


def test_build_image_document_detects_english_language(sample_image):
    document = build_image_document(sample_image, "Road maintenance notice")
    assert document.language == "en"


def test_build_image_document_detects_nepali_language(sample_image):
    document = build_image_document(sample_image, "सडक मर्मत सूचना")
    assert document.language == "ne"


def test_build_image_document_prefers_alt_text_for_title(sample_image):
    document = build_image_document(
        sample_image, "some ocr text", alt_text="Custom title from alt text"
    )
    assert document.title == "Custom title from alt text"


def test_iter_images_finds_supported_extensions_recursively(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "sub" / "b.png").write_bytes(b"")
    (tmp_path / "ignore.txt").write_bytes(b"")

    found = iter_images(tmp_path)

    assert {p.name for p in found} == {"a.jpg", "b.png"}
    assert SUPPORTED_EXTENSIONS  # sanity: the constant is non-empty and importable
