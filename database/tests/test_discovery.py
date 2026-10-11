"""Domain discovery: host filtering, the Nepali-content check and the DB round trip."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from pgs_db.discovery import (
    Verified,
    candidate_hosts,
    category_for,
    discover_domains,
    is_blocked,
    looks_nepali,
    normalize_host,
)
from pgs_db.enums import DomainCategory, DomainPriority, DomainStatus
from pgs_db.models import CrawledDocument, Domain


def test_normalize_host() -> None:
    assert normalize_host("WWW.Example.com.np.") == "example.com.np"
    assert normalize_host("127.0.0.1") is None
    assert normalize_host("localhost") is None
    assert normalize_host("bad_host.np") is None


def test_blocked_and_category() -> None:
    assert is_blocked("m.facebook.com") and not is_blocked("notfacebook.com")
    assert category_for("pokharamun.gov.np") == DomainCategory.GOVERNMENT
    assert category_for("tu.edu.np") == DomainCategory.EDUCATION
    assert category_for("example.np") == DomainCategory.OTHER


def test_looks_nepali() -> None:
    assert looks_nepali('<html lang="ne"><body>x</body></html>')
    assert looks_nepali("नेपाल " * 60)
    assert looks_nepali("Nepal news from Kathmandu and Pokhara")
    assert not looks_nepali("<html lang='en'>Welcome to a shop</html>")


def _doc(url: str, host: str, external: list[str]) -> CrawledDocument:
    return CrawledDocument(
        url=url,
        normalized_url=url,
        host=host,
        external_links=external,
        content_hash="h" + url,
        fetched_at=datetime.now(UTC),
    )


def test_candidates_and_registration(session: Session) -> None:
    session.add(Domain(domain="known.com.np"))
    session.add_all(
        [
            _doc(
                "https://a.np/1", "a.np", ["https://www.newsite.com.np/x", "https://facebook.com/a"]
            ),
            _doc("https://b.np/1", "b.np", ["http://newsite.com.np/", "https://known.com.np/"]),
            _doc("https://c.np/1", "c.np", ["https://nepalishop.com/"]),
        ]
    )
    session.flush()

    hosts = candidate_hosts(session, days=30, limit=10)
    assert hosts[0] == "newsite.com.np"  # .np first, linked from two sites
    assert "nepalishop.com" in hosts
    assert "known.com.np" not in hosts and "facebook.com" not in hosts

    def verify(host: str, *, require_nepali_content: bool) -> Verified | None:
        if host == "nepalishop.com":
            return None
        return Verified(host, category_for(host), "New Site")

    report = discover_domains(session, verify=verify)
    assert report["added_hosts"] == ["newsite.com.np"]
    row = session.scalar(select(Domain).where(Domain.domain == "newsite.com.np"))
    assert row is not None
    assert (row.status, row.priority) == (DomainStatus.PENDING, DomainPriority.LOW)
    assert row.category == DomainCategory.COMMERCIAL and row.website_name == "New Site"
    # Registered hosts are no longer candidates.
    assert "newsite.com.np" not in candidate_hosts(session, days=30, limit=10)
