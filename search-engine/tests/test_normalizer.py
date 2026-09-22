from pgs_search.query.normalizer import (
    detect_language,
    expand_query_terms,
    get_place_map,
    lemmatize_query,
    normalize_query,
)


def test_normalize_collapses_whitespace():
    assert normalize_query("  Hello   World  ") == "hello world"
    assert normalize_query("kathmandu    valley") == "kathmandu valley"


def test_normalize_collapses_tabs_and_newlines():
    assert normalize_query("Kathmandu\tPokhara") == "kathmandu pokhara"
    assert normalize_query("Kathmandu\nPokhara\nRiver") == "kathmandu pokhara river"


def test_normalize_strips_leading_and_trailing_whitespace():
    assert normalize_query("   kathmandu   ") == "kathmandu"


def test_normalize_lowercases_english():
    assert normalize_query("KATHMANDU") == "kathmandu"
    assert normalize_query("Pokhara Valley") == "pokhara valley"


def test_normalize_leaves_nepali_case_untouched():
    assert normalize_query("काठमाडौं") == "काठमाडौं"
    assert normalize_query("सगरमाथा") == "सगरमाथा"


def test_normalize_empty_query():
    assert normalize_query("") == ""
    assert normalize_query("   ") == ""
    assert normalize_query("\t\n") == ""


def test_normalize_mixed_language_preserves_devanagari():
    assert normalize_query("kathmandu नेपाल") == "kathmandu नेपाल"


def test_detect_language_english():
    assert detect_language("best trekking route") == "en"
    assert detect_language("himalayan trails") == "en"
    assert detect_language("tourist guide pokhara") == "en"


def test_detect_language_nepali():
    assert detect_language("काठमाडौं") == "ne"
    assert detect_language("सगरमाथा") == "ne"


def test_detect_language_romanized_nepali():
    assert detect_language("kathmandu") == "ne"
    assert detect_language("namaste") == "ne"
    assert detect_language("kathmandu pokhara") == "ne"
    assert detect_language("namche bazaar") == "ne"


def test_detect_language_mixed():
    assert detect_language("kathmandu नेपाल") == "mixed"
    assert detect_language("best trek नेपाल") == "mixed"


def test_detect_language_unknown():
    assert detect_language("") == "unknown"
    assert detect_language("привет") == "unknown"
    assert detect_language("你好") == "unknown"


def test_expand_query_terms_adds_nepali_place():
    terms = expand_query_terms("  Kathmandu ")
    assert "kathmandu" in terms
    assert "काठमाडौं" in terms


def test_get_place_map_loads_json():
    place_map = get_place_map()

    assert isinstance(place_map, dict)
    assert place_map
    assert place_map["kathmandu"] == "काठमाडौं"


def test_expand_nepali_place_adds_english():
    terms = expand_query_terms("काठमाडौं")
    assert "काठमाडौं" in terms
    assert "kathmandu" in terms


def test_expand_all_places_have_equivalents():
    place_map = get_place_map()
    for name in place_map:
        terms = expand_query_terms(name)
        assert place_map[name] in terms


def test_expand_query_terms_keeps_original_and_adds_stemmed_variant():
    terms = expand_query_terms("himalayan trails")
    assert terms[0] == "himalayan trails"
    assert len(terms) == 2


def test_expand_mixed_language_query():
    terms = expand_query_terms("kathmandu नेपाल")
    assert "kathmandu नेपाल" in terms
    assert "काठमाडौं" in terms


def test_expand_empty_query():
    assert expand_query_terms("") == [""]
    assert expand_query_terms("   ") == [""]


def test_lemmatize_stems_english_words():
    assert lemmatize_query("running") == "run"


def test_lemmatize_preserves_nepali_unchanged():
    assert lemmatize_query("काठमाडौं") == "काठमाडौं"


def test_expand_query_terms_includes_stemmed_variant():
    terms = expand_query_terms("running")
    assert "running" in terms
    assert "run" in terms
