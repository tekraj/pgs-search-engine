"""Domain discovery: grow the `domains` seed list from the links the crawler meets.

The crawler stays on each site (`SameHostOnly`), so a link to another website is only
recorded in `crawled_documents.external_links`. This module turns those links into new
seed rows:

1. `candidate_hosts` -- hosts linked from crawled pages that are not in `domains` yet,
   most-linked first. `.np` hosts come first.
2. `verify_host` -- the website must answer over HTTP(S) with an HTML page, must not
   disallow everything in robots.txt and, unless it is a `.np` host, must look Nepali
   (Devanagari text, `lang="ne"` or repeated mentions of Nepal).
3. `discover_domains` -- registers each verified host as a PENDING, LOW priority domain.
   The scheduled crawl picks it up on its next run; `link_domains_to_local_bodies`
   (the `reference` job) geo-tags it if it is a local government's site.

The checks run from the job's own process, so they refuse non-public addresses (the same
rule as the crawler's `netguard`): the address is resolved once, checked, and the
connection is pinned to it, so a DNS answer cannot change between check and connect.
"""

import http.client
import ipaddress
import re
import socket
import ssl
import time
import urllib.robotparser
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.orm import Session

from .enums import DomainCategory, DomainPriority, DomainStatus
from .repositories import BronzeRepository

USER_AGENT = "PGSSearchBot/1.0 (+domain discovery)"
MAX_BODY_BYTES = 256 * 1024
MAX_REDIRECTS = 3

# Websites that are never Nepali "seeds": platforms and big third parties that every
# page links to. Subdomains are blocked too.
BLOCKED_SUFFIXES = frozenset(
    {
        "facebook.com", "fb.com", "fb.me", "instagram.com", "twitter.com", "x.com",
        "youtube.com", "youtu.be", "linkedin.com", "tiktok.com", "pinterest.com",
        "whatsapp.com", "wa.me", "t.me", "telegram.org", "viber.com", "reddit.com",
        "google.com", "googleapis.com", "gstatic.com", "googletagmanager.com",
        "google-analytics.com", "doubleclick.net", "goo.gl", "bit.ly", "tinyurl.com",
        "wikipedia.org", "wikimedia.org", "github.com", "apple.com", "microsoft.com",
        "amazon.com", "cloudflare.com", "wordpress.com", "wordpress.org", "wp.com",
        "blogspot.com", "medium.com", "archive.org", "w3.org", "schema.org",
        "creativecommons.org", "adobe.com", "paypal.com", "mailchimp.com", "gravatar.com",
        "addthis.com", "sharethis.com", "bing.com", "yahoo.com", "mozilla.org", "gov.uk",
    }
)  # fmt: skip

_HOST_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_LANG_RE = re.compile(r"<html[^>]*\blang\s*=\s*[\"']?([a-zA-Z-]+)", re.I)
_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
_NEPAL_RE = re.compile(r"\b(nepal|kathmandu|pokhara|lalitpur|bhaktapur)\b", re.I)

# Second-level `.np` zones -> the domain category they imply.
_NP_CATEGORY = {
    "gov.np": DomainCategory.GOVERNMENT,
    "edu.np": DomainCategory.EDUCATION,
    "org.np": DomainCategory.NGO,
    "com.np": DomainCategory.COMMERCIAL,
}

# Reads the host of every external link (userinfo and port dropped) in one pass, ranks
# hosts by how many distinct crawled websites link to them and leaves out known domains.
_CANDIDATES_SQL = text(
    r"""
    SELECT h, count(DISTINCT src) AS sources
    FROM (
        SELECT cd.host AS src,
               lower(substring(
                   link from '^[a-zA-Z][a-zA-Z0-9+.-]*://(?:[^/?#@]*@)?([^/?#:@]+)'
               )) AS h
        FROM crawled_documents cd
        CROSS JOIN LATERAL unnest(cd.external_links) AS link
        WHERE cd.external_links IS NOT NULL
          AND cd.fetched_at >= now() - make_interval(days => :days)
    ) links
    WHERE h IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM domains d WHERE d.domain = regexp_replace(links.h, '^www\.', '')
      )
    GROUP BY h
    ORDER BY (h ~ '\.np$') DESC, count(DISTINCT src) DESC, h
    LIMIT :limit
    """
)


@dataclass(frozen=True)
class Verified:
    host: str
    category: DomainCategory
    website_name: str | None


def normalize_host(host: str) -> str | None:
    """Lower-case host without a leading `www.`, or None if it is not a plain DNS name."""
    h = host.strip().lower().rstrip(".")
    if h.startswith("www."):
        h = h[4:]
    try:
        h = h.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if not _HOST_RE.match(h):  # also rejects IP literals and single-label names
        return None
    return h


def is_blocked(host: str) -> bool:
    return any(host == s or host.endswith("." + s) for s in BLOCKED_SUFFIXES)


def is_np(host: str) -> bool:
    return host.endswith(".np")


def category_for(host: str) -> DomainCategory:
    for suffix, category in _NP_CATEGORY.items():
        if host.endswith("." + suffix):
            return category
    return DomainCategory.OTHER


def looks_nepali(html: str) -> bool:
    """Heuristic for a website outside `.np`: Nepali script, `lang="ne"` or Nepal named often."""
    lang = _LANG_RE.search(html)
    if lang and lang.group(1).lower().startswith("ne"):
        return True
    if len(_DEVANAGARI_RE.findall(html)) >= 50:
        return True
    return len(_NEPAL_RE.findall(html)) >= 3


def _public_address(host: str) -> str | None:
    """The host's first address, if every address it resolves to is public."""
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return None
    addresses = [str(i[4][0]) for i in infos]
    if not addresses:
        return None
    if not all(ipaddress.ip_address(a).is_global for a in addresses):
        return None
    return addresses[0]


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """Connects to a pre-checked address instead of resolving the host again."""

    def __init__(self, host: str, address: str, timeout: float) -> None:
        super().__init__(host, timeout=timeout)
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float) -> None:
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self) -> None:
        sock = socket.create_connection((self._address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)  # type: ignore[attr-defined]


def _get(
    scheme: str, host: str, path: str, timeout: float
) -> tuple[int, dict[str, str], bytes, str] | None:
    """GET `scheme://host/path`; follows redirects that stay on the same site.

    Returns (status, headers, body, final host) or None on any network failure or a
    redirect to another website (that website is judged on its own link).
    """
    for _ in range(MAX_REDIRECTS + 1):
        current = normalize_host(host)
        if current is None:
            return None
        address = _public_address(host)
        if address is None:
            return None
        conn_cls = _PinnedHTTPSConnection if scheme == "https" else _PinnedHTTPConnection
        conn = conn_cls(host, address, timeout)
        try:
            conn.request(
                "GET",
                path,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"},
            )
            resp = conn.getresponse()
            headers = {k.lower(): v for k, v in resp.getheaders()}
            if resp.status in (301, 302, 303, 307, 308) and "location" in headers:
                target = urlsplit(headers["location"])
                if target.scheme not in ("", "http", "https"):
                    return None
                next_host = target.hostname or host
                if normalize_host(next_host) != current:
                    return None
                scheme = target.scheme or scheme
                host = next_host
                path = (target.path or "/") + (f"?{target.query}" if target.query else "")
                continue
            body = resp.read(MAX_BODY_BYTES)
            return resp.status, headers, body, host
        except (OSError, http.client.HTTPException, ValueError):
            return None
        finally:
            conn.close()
    return None


def _robots_allow_all(host: str, scheme: str, timeout: float) -> bool:
    """False only when robots.txt exists and disallows the site's root for everyone."""
    got = _get(scheme, host, "/robots.txt", timeout)
    if got is None or got[0] != 200:
        return True  # RFC 9309: a missing robots.txt allows everything
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(got[2].decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch(USER_AGENT, "/") or parser.can_fetch("*", "/")


def verify_host(
    host: str, *, timeout: float = 8.0, require_nepali_content: bool = True
) -> Verified | None:
    """The host as a ready-to-register domain, or None if it fails a check."""
    for scheme in ("https", "http"):
        got = _get(scheme, host, "/", timeout)
        if got is None:
            continue
        status, headers, body, _final = got
        if status >= 400 or "html" not in headers.get("content-type", "").lower():
            return None
        html = body.decode("utf-8", errors="replace")
        if not is_np(host) and require_nepali_content and not looks_nepali(html):
            return None
        if not _robots_allow_all(host, scheme, timeout):
            return None
        title = _TITLE_RE.search(html)
        name = " ".join(unescape(title.group(1)).split())[:255] if title else ""
        return Verified(host=host, category=category_for(host), website_name=name or None)
    return None


def candidate_hosts(session: Session, *, days: int, limit: int) -> list[str]:
    """Normalized, unknown, non-blocked hosts linked from pages crawled in the last `days`."""
    rows = session.execute(_CANDIDATES_SQL, {"days": days, "limit": limit * 5}).all()
    seen: dict[str, None] = {}  # insertion-ordered set; the SQL order is the priority
    for raw, _sources in rows:
        host = normalize_host(raw)
        if host and not is_blocked(host):
            seen.setdefault(host)
    return list(seen)[:limit]


def discover_domains(
    session: Session,
    *,
    days: int = 30,
    limit: int = 200,
    max_seconds: float = 180.0,
    workers: int = 16,
    require_nepali_content: bool = True,
    verify: Callable[..., Verified | None] = verify_host,
) -> dict[str, Any]:
    """Register verified hosts linked from crawled pages as new domains.

    `max_seconds` bounds the network phase: the job holds one open transaction (its
    advisory lock), and `pgs_jobs` connections are cut after 5 minutes idle in
    transaction. Hosts not checked in time are tried again by the next run.
    """
    hosts = candidate_hosts(session, days=days, limit=limit)
    deadline = time.monotonic() + max_seconds
    verified: list[Verified] = []
    checked = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_verify_before, verify, h, deadline, require_nepali_content) for h in hosts
        ]
        for future in as_completed(futures):
            result = future.result()
            if result is not _SKIPPED:
                checked += 1
            if isinstance(result, Verified):
                verified.append(result)

    repo = BronzeRepository(session)
    added: list[str] = []
    for v in sorted(verified, key=lambda v: v.host):
        repo.ensure_domain(
            v.host,
            category=v.category,
            priority=DomainPriority.LOW,
            status=DomainStatus.PENDING,
            website_name=v.website_name,
        )
        added.append(v.host)
    return {
        "candidates": len(hosts),
        "checked": checked,
        "added": len(added),
        "added_hosts": added[:50],
    }


_SKIPPED: Any = object()


def _verify_before(
    verify: Callable[..., Verified | None], host: str, deadline: float, require_nepali: bool
) -> Any:
    if time.monotonic() >= deadline:
        return _SKIPPED
    try:
        return verify(host, require_nepali_content=require_nepali)
    except Exception:  # one bad site must not stop the run
        return None
