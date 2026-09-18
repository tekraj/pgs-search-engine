"""Query normalization helpers for the search engine."""

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_WHITESPACE_RE = re.compile(r"\s+")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

_PLACE_MAP_FILE = Path(__file__).parent / "data" / "en_ne_places.json"


@lru_cache(maxsize=1)
def get_place_map() -> dict[str, str]:
    with _PLACE_MAP_FILE.open(encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def get_reverse_place_map() -> dict[str, str]:
    return {value: key for key, value in get_place_map().items()}


@lru_cache(maxsize=1)
def get_romanized_ne_words() -> frozenset[str]:
    return frozenset(get_place_map()) | {
        "namaste",
        "dhanyavad",
        "dhanyabad",
        "khana",
        "pani",
        "momo",
        "momos",
        "chowmein",
        "thakali",
        "newa",
        "sherpa",
        "tamang",
        "gurung",
        "magar",
        "limbu",
        "tharu",
        "nepali",
    }


def _is_latin_script(text: str) -> bool:
    latin = sum(1 for ch in text if _is_latin(ch))
    other = sum(1 for ch in text if not _is_latin(ch) and unicodedata.category(ch).startswith("L"))
    if latin + other == 0:
        return True
    return latin >= other


def _is_latin(ch: str) -> bool:
    try:
        return unicodedata.name(ch).startswith("LATIN")
    except ValueError:
        return False


def normalize_query(query: str) -> str:
    """Normalize a raw search query."""
    normalized = _WHITESPACE_RE.sub(" ", query.strip())
    normalized = unicodedata.normalize("NFC", normalized)
    if _is_latin_script(normalized):
        return normalized.lower()
    return normalized


def detect_language(query: str) -> str:
    """Detect the language used by a search query."""
    text = normalize_query(query)
    if not text:
        return "unknown"

    has_latin = any(_is_latin(ch) for ch in text)
    has_devanagari = bool(_DEVANAGARI_RE.search(text))

    if has_latin and has_devanagari:
        return "mixed"
    if has_devanagari:
        return "ne"
    if not has_latin:
        return "unknown"

    if _is_romanized_nepali(text):
        return "ne"
    return "en"


def _is_romanized_nepali(text: str) -> bool:
    if text in get_place_map() or text in get_romanized_ne_words():
        return True
    tokens = text.split()
    return bool(tokens) and all(token in get_romanized_ne_words() for token in tokens)


def expand_query_terms(query: str) -> list[str]:
    """Expand a query into search terms and variants."""
    normalized = normalize_query(query)
    terms = [normalized]
    place_map = get_place_map()
    reverse_place_map = get_reverse_place_map()
    candidates = [normalized, *normalized.split()]
    for candidate in candidates:
        equivalent = place_map.get(candidate) or reverse_place_map.get(candidate)
        if equivalent:
            terms.append(equivalent)
    return list(dict.fromkeys(terms))