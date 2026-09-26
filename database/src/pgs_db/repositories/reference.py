"""Read helpers over the gazetteer and domains for ETL stage 4 (geo-tagging).

The ETL spec (`ETL/spark/README.md` §4 stage 4) resolves a page to a place two ways:

- **Domain rules** -- a site that belongs to a local body (`pokharamun.gov.np`) tags
  every page it serves. `geo_for_domain` answers that from `domains.local_body_id`,
  and `link_domains_to_local_bodies` fills that column from the gazetteer's
  `local_bodies.website`.
- **Gazetteer matching** -- scan the text for any of the 837 place names.
  `gazetteer` exports them in one list for Spark to broadcast to its executors.

Both return codes in the shape `save_page`'s `geo_location` block expects.
"""

from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from ..enums import GeoTagMethod
from ..models import District, Domain, LocalBody, Province


def site_host(url_or_host: str | None) -> str | None:
    """`http://www.pokharamun.gov.np/` or `WWW.Pokharamun.gov.np` -> `pokharamun.gov.np`."""
    if not url_or_host:
        return None
    value = url_or_host.strip().lower()
    host = urlsplit(value if "//" in value else f"//{value}").hostname
    if not host:
        return None
    return host.removeprefix("www.")


class ReferenceRepository:
    """Gazetteer and domain lookups for one SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def gazetteer(self) -> list[dict[str, Any]]:
        """Every province, district and local body with its names and parent codes.

        One flat list, provinces first, so Spark can broadcast it once and match
        `name_en` / `name_ne` in page text. Each entry carries the codes of every
        level above it, ready to become a `geo_location` block.
        """
        entries: list[dict[str, Any]] = []
        for p in self.session.scalars(select(Province).order_by(Province.code)):
            entries.append(
                {
                    "level": "province",
                    "code": p.code,
                    "name_en": p.name_en,
                    "name_ne": p.name_ne,
                    "province_code": p.code,
                    "district_code": None,
                    "municipality_id": None,
                }
            )
        for d in self.session.scalars(select(District).order_by(District.code)):
            entries.append(
                {
                    "level": "district",
                    "code": d.code,
                    "name_en": d.name_en,
                    "name_ne": d.name_ne,
                    "province_code": d.province_code,
                    "district_code": d.code,
                    "municipality_id": None,
                }
            )
        local_bodies = self.session.scalars(
            select(LocalBody).options(joinedload(LocalBody.district)).order_by(LocalBody.code)
        )
        for lb in local_bodies:
            entries.append(
                {
                    "level": "local_body",
                    "code": lb.code,
                    "name_en": lb.name_en,
                    "name_ne": lb.name_ne,
                    "type": lb.type,
                    "province_code": lb.district.province_code,
                    "district_code": lb.district_code,
                    "municipality_id": lb.code,
                }
            )
        return entries

    def geo_for_domain(self, domain_id: int | None) -> dict[str, Any] | None:
        """The `geo_location` block for a page on a local body's own site, or None.

        Returned with `method=DOMAIN` and `confidence=1.0`, so it can go straight into
        the `save_page` payload. None when the domain is unknown or not linked to a
        local body (news sites, national portals, ...).
        """
        if domain_id is None:
            return None
        local_body = self.session.scalar(
            select(LocalBody)
            .join(Domain, Domain.local_body_id == LocalBody.id)
            .where(Domain.id == domain_id)
            .options(joinedload(LocalBody.district))
        )
        if local_body is None:
            return None
        return {
            "province_code": local_body.district.province_code,
            "district_code": local_body.district_code,
            "municipality_id": local_body.code,
            "method": GeoTagMethod.DOMAIN.value,
            "confidence": 1.0,
        }

    def link_domains_to_local_bodies(self) -> int:
        """Set `domains.local_body_id` where the domain is a local body's website.

        Matches on host with `www.` ignored, and only fills rows that are still
        unlinked, so an admin's manual link is never overwritten. Safe to re-run
        after new domains are registered. Returns the number of domains linked.
        """
        by_host: dict[str, int] = {}
        for lb_id, website in self.session.execute(
            select(LocalBody.id, LocalBody.website).where(LocalBody.website.is_not(None))
        ):
            host = site_host(website)
            if host:
                by_host[host] = lb_id

        linked = 0
        unlinked = self.session.execute(
            select(Domain.id, Domain.domain).where(Domain.local_body_id.is_(None))
        ).all()
        for domain_id, domain in unlinked:
            lb_id = by_host.get(site_host(domain) or "")
            if lb_id is not None:
                self.session.execute(
                    update(Domain).where(Domain.id == domain_id).values(local_body_id=lb_id)
                )
                linked += 1
        return linked
