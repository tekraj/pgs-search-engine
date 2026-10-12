"""A small, reproducible TF-IDF information-retrieval system for the CISI collection."""

from __future__ import annotations

import argparse
import io
import re
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CISI_URL = "https://ir.dcs.gla.ac.uk/resources/test_collections/cisi/cisi.tar.gz"
DEFAULT_DATA_DIR = Path.home() / ".cache" / "pgs-cisi-ir"
DATA_FILES = {"cisi.all", "cisi.qry", "cisi.rel"}


@dataclass(frozen=True)
class Record:
    record_id: int
    text: str


def parse_records(content: str) -> list[Record]:
    """Parse CISI's marker-delimited document or query format."""
    records: list[Record] = []
    current_id: int | None = None
    fields: dict[str, list[str]] = {}
    current_field: str | None = None

    def save_record() -> None:
        if current_id is None:
            return
        selected_fields = ("T", "A", "W")
        text = " ".join(
            line.strip()
            for field in selected_fields
            for line in fields.get(field, [])
            if line.strip()
        )
        records.append(Record(current_id, text))

    for line in content.splitlines():
        marker = re.match(r"^\.([A-Z])(?:\s+(.*))?$", line)
        if marker:
            code = marker.group(1)
            value = marker.group(2) or ""
            if code == "I":
                save_record()
                match = re.match(r"\d+", value)
                if not match:
                    raise ValueError(f"Invalid CISI record identifier: {value!r}")
                current_id = int(match.group())
                fields = {}
                current_field = None
            elif current_id is not None:
                current_field = code
                fields.setdefault(code, [])
                if value:
                    fields[code].append(value)
        elif current_id is not None and current_field is not None:
            fields.setdefault(current_field, []).append(line)

    save_record()
    return records


def load_collection(data_dir: Path) -> tuple[list[Record], list[Record], dict[int, set[int]]]:
    documents = parse_records((data_dir / "cisi.all").read_text(encoding="latin-1"))
    queries = parse_records(
        (data_dir / "cisi.qry").read_text(encoding="latin-1")
    )
    relevance: dict[int, set[int]] = {}
    for line in (data_dir / "cisi.rel").read_text(encoding="latin-1").splitlines():
        columns = line.split()
        if len(columns) >= 2:
            query_id, document_id = map(int, columns[:2])
            relevance.setdefault(query_id, set()).add(document_id)
    return documents, queries, relevance


def ensure_dataset(data_dir: Path) -> None:
    if all((data_dir / filename).is_file() for filename in DATA_FILES):
        return

    data_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(CISI_URL, headers={"User-Agent": "pgs-cisi-ir-demo/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        archive_bytes = response.read()

    found: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        for member in archive.getmembers():
            filename = Path(member.name).name.lower()
            if filename not in DATA_FILES or not member.isfile():
                continue
            source = archive.extractfile(member)
            if source is None:
                continue
            (data_dir / filename).write_bytes(source.read())
            found.add(filename)

    missing = DATA_FILES - found
    if missing:
        raise RuntimeError(f"CISI archive is missing expected files: {', '.join(sorted(missing))}")


def rank_documents(
    vectorizer: TfidfVectorizer,
    document_matrix: object,
    documents: list[Record],
    query: str,
    limit: int,
) -> list[tuple[Record, float]]:
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, document_matrix).ravel()
    order = np.argsort(-scores, kind="stable")[:limit]
    return [(documents[index], float(scores[index])) for index in order if scores[index] > 0]


def evaluate(
    vectorizer: TfidfVectorizer,
    document_matrix: object,
    documents: list[Record],
    queries: list[Record],
    relevance: dict[int, set[int]],
    cutoff: int,
) -> dict[str, float]:
    average_precisions: list[float] = []
    reciprocal_ranks: list[float] = []
    precisions: list[float] = []
    recalls: list[float] = []

    for query in queries:
        relevant = relevance.get(query.record_id, set())
        if not relevant:
            continue
        ranked = rank_documents(vectorizer, document_matrix, documents, query.text, len(documents))
        hits = [record.record_id in relevant for record, _ in ranked]
        relevant_seen = 0
        precision_sum = 0.0
        reciprocal_rank = 0.0
        for rank, is_relevant in enumerate(hits, start=1):
            if is_relevant:
                relevant_seen += 1
                precision_sum += relevant_seen / rank
                if reciprocal_rank == 0:
                    reciprocal_rank = 1.0 / rank

        average_precisions.append(precision_sum / len(relevant))
        reciprocal_ranks.append(reciprocal_rank)
        top_hits = sum(hits[:cutoff])
        precisions.append(top_hits / cutoff)
        recalls.append(top_hits / len(relevant))

    if not average_precisions:
        raise ValueError("No relevance judgments matched the parsed query IDs")
    return {
        "MAP": float(np.mean(average_precisions)),
        "MRR": float(np.mean(reciprocal_ranks)),
        f"P@{cutoff}": float(np.mean(precisions)),
        f"Recall@{cutoff}": float(np.mean(recalls)),
        "evaluated_queries": float(len(average_precisions)),
    }


def _print_results(query: str, results: Iterable[tuple[Record, float]]) -> None:
    print(f"\nQuery: {query}")
    print("Rank  Score   Document ID  Text")
    print("----  ------  -----------  ----")
    for rank, (record, score) in enumerate(results, start=1):
        excerpt = " ".join(record.text.split())[:180]
        print(f"{rank:>4}  {score:>6.4f}  {record.record_id:>11}  {excerpt}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--query-id", type=int, default=1, help="CISI query ID to display")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    ensure_dataset(args.data_dir)
    documents, queries, relevance = load_collection(args.data_dir)
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    document_matrix = vectorizer.fit_transform(record.text for record in documents)
    print(
        f"Indexed {len(documents)} documents; vocabulary={len(vectorizer.vocabulary_)} "
        f"features; queries={len(queries)}."
    )

    metrics = evaluate(
        vectorizer, document_matrix, documents, queries, relevance, cutoff=args.top_k
    )
    print("\nEvaluation (all queries with relevance judgments):")
    for metric, value in metrics.items():
        formatted_value = int(value) if metric == "evaluated_queries" else f"{value:.4f}"
        print(f"{metric}: {formatted_value}")

    selected_query = next((query for query in queries if query.record_id == args.query_id), None)
    if selected_query is None:
        parser.error(f"query ID {args.query_id} is not present in CISI.QUE")
    results = rank_documents(
        vectorizer, document_matrix, documents, selected_query.text, args.top_k
    )
    _print_results(selected_query.text, results)


if __name__ == "__main__":
    main()