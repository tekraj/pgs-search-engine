from opensearchpy import OpenSearch

from pgs_search.config import settings


def search_bm25(
    client: OpenSearch,
    query: str,
    limit: int = 10,
) -> list[dict]:
    body = {
        "size": limit,
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title^3",
                    "description^2",
                    "searchable_text",
                ],
                "type": "best_fields",
            }
        },
    }

    response = client.search(
        index=settings.opensearch_index,
        body=body,
    )

    return response["hits"]["hits"]