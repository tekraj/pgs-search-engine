"""Load Nepal's administrative geography: 7 provinces, 77 districts, 753 local bodies.

The data lives in ``data/nepal_geography.json``, committed alongside this script so
seeding never depends on the network. Safe to run more than once: every row is
upserted on its ``code``, so re-running refreshes names without creating duplicates.

Usage:  python scripts/seed_geography.py
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from pgs_db import make_session_factory
from pgs_db.enums import LocalBodyType
from pgs_db.models import District, LocalBody, Province

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "nepal_geography.json"

EXPECTED_PROVINCES = 7
EXPECTED_DISTRICTS = 77
EXPECTED_LOCAL_BODIES = 753


def validate_geography(data: dict[str, list[dict[str, Any]]]) -> None:
    """Validate geography counts, unique codes, and parent relationships."""
    provinces = data.get("provinces", [])
    districts = data.get("districts", [])
    local_bodies = data.get("local_bodies", [])

    if len(provinces) != EXPECTED_PROVINCES:
        raise ValueError(f"Expected {EXPECTED_PROVINCES} provinces, got {len(provinces)}")

    if len(districts) != EXPECTED_DISTRICTS:
        raise ValueError(f"Expected {EXPECTED_DISTRICTS} districts, got {len(districts)}")

    if len(local_bodies) != EXPECTED_LOCAL_BODIES:
        raise ValueError(
            f"Expected {EXPECTED_LOCAL_BODIES} local bodies, got {len(local_bodies)}"
        )

    province_codes = {row["code"] for row in provinces}

    if len(province_codes) != len(provinces):
        raise ValueError("Duplicate province codes found")

    district_codes = {row["code"] for row in districts}

    if len(district_codes) != len(districts):
        raise ValueError("Duplicate district codes found")

    local_body_codes = {row["code"] for row in local_bodies}

    if len(local_body_codes) != len(local_bodies):
        raise ValueError("Duplicate local-body codes found")

    invalid_district_parents = {
        row["province_code"]
        for row in districts
        if row["province_code"] not in province_codes
    }

    if invalid_district_parents:
        raise ValueError(
            f"Districts reference unknown provinces: {sorted(invalid_district_parents)}"
        )

    invalid_local_body_parents = {
        row["district_code"]
        for row in local_bodies
        if row["district_code"] not in district_codes
    }

    if invalid_local_body_parents:
        raise ValueError(
            "Local bodies reference unknown districts: "
            f"{sorted(invalid_local_body_parents)}"
        )

def upsert(
    session: Session,
    model: type[Province] | type[District] | type[LocalBody],
    rows: list[dict[str, Any]],
    update: list[str],
) -> None:
    """Insert rows, refreshing `update` columns on any row whose `code` already exists."""
    stmt = insert(model).values(rows)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=[model.code],
            set_={col: getattr(stmt.excluded, col) for col in update},
        )
    )


def main() -> None:
    data: dict[str, list[dict[str, Any]]] = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    validate_geography(data)

    # `wards` is stored as `ward_count`; the type string becomes the enum so an unknown
    # value fails here rather than in Postgres.
    local_bodies = [
        {k: v for k, v in row.items() if k != "wards"}
        | {"type": LocalBodyType(row["type"]), "ward_count": row.get("wards")}
        for row in data["local_bodies"]
    ]

    session_factory = make_session_factory()
    with session_factory.begin() as session:
        # Order matters: districts reference provinces.code, local bodies reference districts.code.
        upsert(session, Province, data["provinces"], ["name_en", "name_ne"])
        upsert(session, District, data["districts"], ["province_code", "name_en", "name_ne"])
        upsert(
            session,
            LocalBody,
            local_bodies,
            ["district_code", "type", "name_en", "name_ne", "website", "ward_count"],
        )

    # Devanagari is deliberately kept out of stdout: Windows consoles default to cp1252
    # and would raise UnicodeEncodeError on an otherwise successful seed.
    print(
        f"Seeded {len(data['provinces'])} provinces, "
        f"{len(data['districts'])} districts, "
        f"{len(local_bodies)} local bodies"
    )


if __name__ == "__main__":
    main()
