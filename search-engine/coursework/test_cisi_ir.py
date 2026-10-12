from sklearn.feature_extraction.text import TfidfVectorizer

from cisi_ir import Record, evaluate, parse_records, rank_documents


def test_parse_records_uses_title_abstract_and_body_only() -> None:
    content = (
        ".I 1\n.T\nInformation retrieval\n.A\nSearch systems\n.W\n"
        "Find relevant documents\n.B\nIgnored metadata\n"
    )

    records = parse_records(content)

    assert records == [
        Record(1, "Information retrieval Search systems Find relevant documents")
    ]


def test_rank_and_evaluate_relevant_document() -> None:
    documents = [Record(1, "information retrieval systems"), Record(2, "baking bread recipes")]
    queries = [Record(1, "information retrieval")]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(document.text for document in documents)

    ranked = rank_documents(vectorizer, matrix, documents, queries[0].text, limit=2)
    metrics = evaluate(vectorizer, matrix, documents, queries, {1: {1}}, cutoff=1)

    assert ranked[0][0].record_id == 1
    assert metrics == {
        "MAP": 1.0,
        "MRR": 1.0,
        "P@1": 1.0,
        "Recall@1": 1.0,
        "evaluated_queries": 1.0,
    }