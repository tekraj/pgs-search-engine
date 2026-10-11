"""Input validation for the checked-in Nepal geography seed."""

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

DATABASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = DATABASE_DIR / "data" / "nepal_geography.json"
SPEC = importlib.util.spec_from_file_location(
    "seed_geography", DATABASE_DIR / "scripts" / "seed_geography.py"
)
assert SPEC is not None and SPEC.loader is not None
SEED_GEOGRAPHY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEED_GEOGRAPHY)
validate_geography = SEED_GEOGRAPHY.validate_geography


@pytest.fixture()
def geography() -> dict[str, Any]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def test_checked_in_geography_has_expected_counts_and_parent_links(
    geography: dict[str, Any],
) -> None:
    validate_geography(geography)


@pytest.mark.parametrize(
    ("level", "expected"),
    [("provinces", 7), ("districts", 77), ("local_bodies", 753)],
)
def test_rejects_wrong_count(
    geography: dict[str, Any], level: str, expected: int
) -> None:
    broken = copy.deepcopy(geography)
    broken[level].pop()

    with pytest.raises(ValueError, match=f"Expected {expected}"):
        validate_geography(broken)


@pytest.mark.parametrize("level", ["provinces", "districts", "local_bodies"])
def test_rejects_duplicate_codes(geography: dict[str, Any], level: str) -> None:
    broken = copy.deepcopy(geography)
    broken[level][1]["code"] = broken[level][0]["code"]

    with pytest.raises(ValueError, match="Duplicate"):
        validate_geography(broken)


def test_rejects_district_with_unknown_province(geography: dict[str, Any]) -> None:
    broken = copy.deepcopy(geography)
    broken["districts"][0]["province_code"] = "UNKNOWN"

    with pytest.raises(ValueError, match="unknown provinces"):
        validate_geography(broken)


def test_rejects_local_body_with_unknown_district(geography: dict[str, Any]) -> None:
    broken = copy.deepcopy(geography)
    broken["local_bodies"][0]["district_code"] = "UNKNOWN"

    with pytest.raises(ValueError, match="unknown districts"):
        validate_geography(broken)
