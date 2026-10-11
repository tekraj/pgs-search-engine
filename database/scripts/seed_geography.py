"""Load Nepal's administrative geography: 7 provinces, 77 districts, 753 local bodies.

The data lives in ``data/nepal_geography.json``, committed alongside this script so
seeding never depends on the network. Safe to run more than once: every row is
upserted on its ``code``, so re-running refreshes names without creating duplicates.

Usage:  python scripts/seed_geography.py
"""

import json
import re
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

_CODE_PATTERNS = {
    "province": re.compile(r"P[1-7]"),
    "district": re.compile(r"D(?:0[1-9]|[1-6][0-9]|7[0-7])"),
    "local body": re.compile(r"MUN\d{3}"),
}


def _required_text(
    row: dict[str, Any],
    field: str,
    location: str,
    *,
    max_length: int,
    pattern: re.Pattern[str] | None = None,
) -> str:
    """Return a required non-empty string or raise a location-specific error."""
    if field not in row:
        raise ValueError(f"{location} is missing required field {field!r}")
    value = row[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location}.{field} must be a non-empty string")
    if len(value) > max_length:
        raise ValueError(f"{location}.{field} exceeds {max_length} characters")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ValueError(f"{location}.{field} has an invalid value: {value!r}")
    return value


def validate_geography(data: Any) -> None:
    """Validate seed structure, fields, codes, types, counts and parent links."""
    if not isinstance(data, dict):
        raise ValueError("Geography data must be a JSON object")

    records: dict[str, list[Any]] = {}
    for level in ("provinces", "districts", "local_bodies"):
        rows = data.get(level)
        if not isinstance(rows, list):
            raise ValueError(f"Geography field {level!r} must be a list")
        records[level] = rows

    provinces = records["provinces"]
    districts = records["districts"]
    local_bodies = records["local_bodies"]

    if len(provinces) != EXPECTED_PROVINCES:
        raise ValueError(f"Expected {EXPECTED_PROVINCES} provinces, got {len(provinces)}")

    if len(districts) != EXPECTED_DISTRICTS:
        raise ValueError(f"Expected {EXPECTED_DISTRICTS} districts, got {len(districts)}")

    if len(local_bodies) != EXPECTED_LOCAL_BODIES:
        raise ValueError(
            f"Expected {EXPECTED_LOCAL_BODIES} local bodies, got {len(local_bodies)}"
        )

    for index, row in enumerate(provinces):
        location = f"provinces[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{location} must be an object")
        _required_text(
            row, "code", location, max_length=4, pattern=_CODE_PATTERNS["province"]
        )
        _required_text(row, "name_en", location, max_length=100)
        _required_text(row, "name_ne", location, max_length=100)

    for index, row in enumerate(districts):
        location = f"districts[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{location} must be an object")
        _required_text(
            row, "code", location, max_length=4, pattern=_CODE_PATTERNS["district"]
        )
        _required_text(row, "province_code", location, max_length=4)
        _required_text(row, "name_en", location, max_length=100)
        _required_text(row, "name_ne", location, max_length=100)

    for index, row in enumerate(local_bodies):
        location = f"local_bodies[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{location} must be an object")
        _required_text(
            row, "code", location, max_length=16, pattern=_CODE_PATTERNS["local body"]
        )
        _required_text(row, "district_code", location, max_length=4)
        _required_text(row, "name_en", location, max_length=150)
        _required_text(row, "name_ne", location, max_length=150)
        body_type = _required_text(row, "type", location, max_length=64)
        try:
            LocalBodyType(body_type)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in LocalBodyType)
            raise ValueError(
                f"{location}.type must be one of: {allowed}; got {body_type!r}"
            ) from exc

        website = row.get("website")
        if website is not None and (not isinstance(website, str) or len(website) > 255):
            raise ValueError(
                f"{location}.website must be a string of at most 255 characters or null"
            )
        wards = row.get("wards")
        if wards is not None and (
            not isinstance(wards, int) or isinstance(wards, bool) or wards <= 0
        ):
            raise ValueError(f"{location}.wards must be a positive integer or null")

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
