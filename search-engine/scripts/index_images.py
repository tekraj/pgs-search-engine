import argparse
import json
from pathlib import Path

from pgs_search.client.opensearch import get_opensearch_client
from pgs_search.config import settings
from pgs_search.ingestion.image_indexer import (
    build_image_document,
    extract_text_from_image,
    iter_images,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-dir", required=True, type=Path)
    parser.add_argument("--metadata-json", type=Path, default=None)
    args = parser.parse_args()

    if not args.images_dir.exists():
        raise SystemExit(f"Images directory not found: {args.images_dir}")

    metadata: dict = {}
    if args.metadata_json:
        if not args.metadata_json.exists():
            raise SystemExit(f"Metadata file not found: {args.metadata_json}")
        metadata = json.loads(args.metadata_json.read_text(encoding="utf-8"))

    image_paths = iter_images(args.images_dir)
    if not image_paths:
        raise SystemExit(f"No images found under {args.images_dir}")

    client = get_opensearch_client()

    for i, image_path in enumerate(image_paths, start=1):
        print(f"[{i}/{len(image_paths)}] OCR: {image_path.name}")
        ocr_text = extract_text_from_image(image_path)
        meta = metadata.get(image_path.name, {})

        document = build_image_document(
            image_path,
            ocr_text,
            alt_text=meta.get("alt_text", ""),
            surrounding_context=meta.get("surrounding_context", ""),
            parent_page_url=meta.get("parent_page_url", ""),
            domain=meta.get("domain", ""),
        )

        response = client.index(
            index=settings.opensearch_index,
            id=document.document_id,
            body=document.model_dump(mode="json", exclude_none=True),
            refresh=True,
        )
        print(f"  Indexed {document.document_id}: {document.title} -> {response['result']}")

    print(f"\nIndexed {len(image_paths)} image documents into '{settings.opensearch_index}'.")


if __name__ == "__main__":
    main()
