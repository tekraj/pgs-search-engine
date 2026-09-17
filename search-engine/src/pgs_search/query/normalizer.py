"""Query normalization helpers for the search engine."""

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

EN_NE_PLACE_MAP: dict[str, str] = {
    "kathmandu": "काठमाडौं",
    "pokhara": "पोखरा",
    "lalitpur": "ललितपुर",
    "patan": "पाटन",
    "bhaktapur": "भक्तपुर",
    "bharatpur": "भरतपुर",
    "biratnagar": "विराटनगर",
    "birgunj": "वीरगञ्ज",
    "janakpur": "जनकपुर",
    "hetauda": "हेटौडा",
    "butwal": "बुटवल",
    "dharan": "धरान",
    "nepalgunj": "नेपालगञ्ज",
    "itahari": "इटहरी",
    "gorkha": "गोरखा",
    "chitwan": "चितवन",
    "lumbini": "लुम्बिनी",
    "mustang": "मुस्ताङ",
    "manang": "मनाङ",
    "jomsom": "जोमसोम",
    "ilam": "इलाम",
    "kirtipur": "कीर्तिपुर",
    "dhulikhel": "धुलिखेल",
    "banepa": "बनेपा",
    "bandipur": "बन्दीपुर",
    "thamel": "ठमेल",
    "nagarkot": "नगरकोट",
    "namche bazaar": "नाम्चे बजार",
    "everest": "सगरमाथा",
    "sagarmatha": "सगरमाथा",
    "annapurna": "अन्नपूर्ण",
    "dhaulagiri": "धौलागिरी",
    "makalu": "मकालु",
    "langtang": "लाङटाङ",
    "rara": "रारा",
    "swayambhunath": "स्वयम्भूनाथ",
    "pashupatinath": "पशुपतिनाथ",
    "boudhanath": "बौद्धनाथ",
    "sauraha": "सौराहा",
    "tansen": "तानसेन",
    "lumle": "लुम्ले",
    "syangja": "स्याङ्जा",
    "palpa": "पाल्पा",
    "kavre": "काभ्रे",
    "nuwakot": "नुवाकोट",
    "dolpa": "डोल्पा",
    "jumla": "जुम्ला",
}

_NE_EN_PLACE_MAP: dict[str, str] = {value: key for key, value in EN_NE_PLACE_MAP.items()}

_ROMANIZED_NE_WORDS: set[str] = set(EN_NE_PLACE_MAP) | {
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
    if text in EN_NE_PLACE_MAP or text in _ROMANIZED_NE_WORDS:
        return True
    tokens = text.split()
    return bool(tokens) and all(token in _ROMANIZED_NE_WORDS for token in tokens)


def expand_query_terms(query: str) -> list[str]:
    """Expand a query into search terms and variants."""
    normalized = normalize_query(query)
    terms = [normalized]
    candidates = [normalized, *normalized.split()]
    for candidate in candidates:
        equivalent = EN_NE_PLACE_MAP.get(candidate) or _NE_EN_PLACE_MAP.get(candidate)
        if equivalent:
            terms.append(equivalent)
    return list(dict.fromkeys(terms))
