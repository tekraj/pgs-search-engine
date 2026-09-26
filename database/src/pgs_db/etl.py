"""The Bronze -> Silver loop, ready to call from Spark or Airflow.

The ETL supplies only the transform: a function from one Bronze row to a §5.2
payload (`docs/bronze-silver-contract.md` §3). Everything around it -- claiming
rows, one transaction per page, domain geo rules, deduplication, marking rows
PROCESSED or FAILED -- is done here, the same way every time:

    from pgs_db import make_session_factory
    from pgs_db.etl import process_bronze_batch, process_stored_file_batch

    Session = make_session_factory()
    while (result := process_bronze_batch(Session, transform_page)).claimed:
        print(result)
    process_stored_file_batch(Session, transform_pdf)   # PDFs / images in MinIO

A transform that raises marks just that row FAILED with the error; the batch
carries on. A transform whose virus scan flags the payload raises `Infected`
instead, after moving the object to the quarantine bucket: the row is recorded in
`quarantined_files` and parked as QUARANTINED, never FAILED. Run `SilverRepository.release_stale` on a schedule to recover rows
from workers that died mid-batch.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from .models import CrawledDocument, Page, StoredFile
from .repositories.reference import ReferenceRepository
from .repositories.silver import SilverRepository

PageTransform = Callable[[CrawledDocument], Mapping[str, Any]]
FileTransform = Callable[[StoredFile], Mapping[str, Any]]

# Long enough to diagnose, short enough not to bloat the queue tables.
_MAX_ERROR_LENGTH = 2000


class Infected(Exception):
    """Raise from a transform when ClamAV flags the payload.

    Move the object to the quarantine bucket first, then raise with where it went:

        verdict = clamav.scan(data)
        if verdict.infected:
            path = move_to_quarantine(stored.storage_path)
            raise Infected(verdict.signature, path, scanner_version=verdict.version)
    """

    def __init__(
        self, threat_signature: str, quarantine_path: str, *, scanner_version: str | None = None
    ) -> None:
        super().__init__(f"{threat_signature} (isolated at {quarantine_path})")
        self.threat_signature = threat_signature
        self.quarantine_path = quarantine_path
        self.scanner_version = scanner_version


@dataclass
class BatchResult:
    """What one batch did. `errors` maps a Bronze row id to why it failed."""

    claimed: int = 0
    saved: int = 0
    duplicates: int = 0
    quarantined: int = 0
    failed: int = 0
    errors: dict[int, str] = field(default_factory=dict)


def process_bronze_batch(
    session_factory: sessionmaker[Session],
    transform: PageTransform,
    *,
    limit: int = 100,
    dedup: bool = True,
    domain_geo: bool = True,
) -> BatchResult:
    """Claim up to `limit` crawled pages, transform and save each, then mark it.

    `content_hash` and `sim_hash` come from the Bronze row unless the payload
    sets them. See `_save_one` for `dedup` and `domain_geo`.
    """
    with session_factory() as s, s.begin():
        claimed = SilverRepository(s).claim_bronze(limit)

    result = BatchResult(claimed=len(claimed))
    for doc in claimed:

        def save(repo: SilverRepository, payload: Mapping[str, Any], doc=doc) -> int:
            saved = repo.save_page(
                payload,
                crawled_document_id=doc.id,
                domain_id=doc.domain_id,
                content_hash=payload.get("content_hash") or doc.content_hash,
                sim_hash=payload.get("sim_hash", doc.sim_hash),
            )
            repo.mark_bronze_processed([doc.id])
            return saved.id

        _save_one(
            session_factory,
            result,
            row_id=doc.id,
            domain_id=doc.domain_id,
            build=lambda doc=doc: transform(doc),
            save=save,
            quarantine=lambda repo, inf, doc=doc: repo.quarantine(
                crawled_document_id=doc.id,
                threat_signature=inf.threat_signature,
                quarantine_path=inf.quarantine_path,
                scanner_version=inf.scanner_version,
            ),
            mark_failed=SilverRepository.mark_bronze_failed,
            dedup=dedup,
            domain_geo=domain_geo,
        )
    return result


def process_stored_file_batch(
    session_factory: sessionmaker[Session],
    transform: FileTransform,
    *,
    limit: int = 100,
    dedup: bool = True,
    domain_geo: bool = True,
) -> BatchResult:
    """`process_bronze_batch` for files in MinIO (PDFs, images, docs).

    The transform reads the file at `stored_file.storage_path` and returns the
    payload; the file's `sha256` is the content hash unless the payload sets
    one. The domain is the one of the page that linked the file, if known.
    """
    with session_factory() as s, s.begin():
        claimed = SilverRepository(s).claim_stored_files(limit)
        domains = {
            f.id: (f.crawled_document.domain_id if f.crawled_document else None) for f in claimed
        }

    result = BatchResult(claimed=len(claimed))
    for stored in claimed:
        domain_id = domains[stored.id]

        def save(
            repo: SilverRepository,
            payload: Mapping[str, Any],
            stored=stored,
            domain_id=domain_id,
        ) -> int:
            saved = repo.save_page(
                payload,
                stored_file_id=stored.id,
                domain_id=domain_id,
                content_hash=payload.get("content_hash") or stored.sha256,
            )
            repo.mark_stored_files_processed([stored.id])
            return saved.id

        _save_one(
            session_factory,
            result,
            row_id=stored.id,
            domain_id=domain_id,
            build=lambda stored=stored: transform(stored),
            save=save,
            quarantine=lambda repo, inf, stored=stored: repo.quarantine(
                stored_file_id=stored.id,
                threat_signature=inf.threat_signature,
                quarantine_path=inf.quarantine_path,
                scanner_version=inf.scanner_version,
            ),
            mark_failed=SilverRepository.mark_stored_file_failed,
            dedup=dedup,
            domain_geo=domain_geo,
        )
    return result


def _save_one(
    session_factory: sessionmaker[Session],
    result: BatchResult,
    *,
    row_id: int,
    domain_id: int | None,
    build: Callable[[], Mapping[str, Any]],
    save: Callable[[SilverRepository, Mapping[str, Any]], int],
    quarantine: Callable[[SilverRepository, Infected], object],
    mark_failed: Callable[[SilverRepository, int, str], None],
    dedup: bool,
    domain_geo: bool,
) -> None:
    """Transform, save and mark one row in a single transaction; on error, mark it FAILED.

    `domain_geo`: a payload with no `geo_location` on a local body's own site is
    tagged with that local body (ETL stage 4 domain rule).
    `dedup`: the page is folded into an older page with the same content hash,
    or within 3 SimHash bits (ETL stage 3); a page whose content no longer
    matches its old original is unfolded.
    """
    try:
        payload = dict(build())
        with session_factory() as s, s.begin():
            repo = SilverRepository(s)
            if domain_geo and payload.get("geo_location") is None:
                geo = ReferenceRepository(s).geo_for_domain(domain_id)
                if geo is not None:
                    payload["geo_location"] = geo
            page_id = save(repo, payload)
            if dedup and _fold_duplicate(repo, page_id):
                result.duplicates += 1
        result.saved += 1
    except Infected as infected:
        with session_factory() as s, s.begin():
            quarantine(SilverRepository(s), infected)
        result.quarantined += 1
    except Exception as exc:  # noqa: BLE001 -- any transform/save error parks the row
        message = f"{type(exc).__name__}: {exc}"[:_MAX_ERROR_LENGTH]
        with session_factory() as s, s.begin():
            mark_failed(SilverRepository(s), row_id, message)
        result.failed += 1
        result.errors[row_id] = message


def _fold_duplicate(repo: SilverRepository, page_id: int) -> bool:
    """Point the page at an older original if one exists. Returns True if folded.

    Only older pages are candidates, so two pages can never end up pointing at
    each other.
    """
    page = repo.session.get(Page, page_id)
    assert page is not None
    original = repo.find_exact_duplicate(page.content_hash, exclude_page_id=page.id)
    if (original is None or original.id > page.id) and page.sim_hash is not None:
        near = [
            p for p, _ in repo.find_near_duplicates(page.sim_hash, exclude_page_id=page.id)
            if p.id < page.id
        ]
        original = near[0] if near else None
    if original is not None and original.id < page.id:
        repo.mark_duplicate_of(page.id, original.id)
        return True
    page.duplicate_of_id = None
    return False
