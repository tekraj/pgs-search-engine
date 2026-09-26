import os
from typing import Any, Protocol, cast

from dotenv import load_dotenv

from embedding import generate_embedding


load_dotenv()


class OpenSearchClientLike(Protocol):
    def search(self, *, index: str | None, body: dict[str, Any]) -> dict[str, Any]: ...


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def get_opensearch_client() -> OpenSearchClientLike:
    host = os.getenv("OPENSEARCH_HOST", "localhost")
    port = _get_int_env("OPENSEARCH_PORT", 9200)

    try:
        from opensearchpy import OpenSearch
    except ImportError as exc:  # pragma: no cover - optional dependency for local scripts
        raise RuntimeError(
            "opensearch-py is required to use the OpenSearch vector search client."
        ) from exc

    client = OpenSearch(
        hosts=[
            {
                "host": host,
                "port": port,
            }
        ]
    )
    return cast(OpenSearchClientLike, client)


def vector_search_opensearch(
    query: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    client = get_opensearch_client()
    query_embedding = generate_embedding(query)
    index_name = os.getenv("OPENSEARCH_INDEX", "documents")

    search_body: dict[str, Any] = {
        "size": top_k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_embedding,
                    "k": top_k,
                }
            }
        },
    }

    response = client.search(
        index=index_name,
        body=search_body,
    )

    results: list[dict[str, Any]] = []

    for rank, hit in enumerate(response["hits"]["hits"], start=1):
        source = cast(dict[str, Any], hit["_source"])
        results.append(
            {
                "document_id": source["document_id"],
                "vector_score": float(hit["_score"]),
                "rank": rank,
            }
        )

    return results