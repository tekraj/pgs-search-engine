from pgs_search.query.embeddings import get_query_vector


def test_get_query_vector_returns_list():
    vector = get_query_vector("hospital budget")
    assert isinstance(vector, list)


def test_get_query_vector_length_is_384():
    vector = get_query_vector("hospital budget")
    assert len(vector) == 384


def test_get_query_vector_items_are_floats():
    vector = get_query_vector("hospital budget")
    assert all(isinstance(item, float) for item in vector)