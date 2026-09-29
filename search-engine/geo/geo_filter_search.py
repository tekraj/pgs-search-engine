from typing import Any

from opensearchpy import OpenSearch

# NOTE: confirm this with the ETL team -- their documented Spark output
# schema (ETL/spark/README.md, section 5.2) doesn't show a timestamp
# field on the indexed document. "scraped_at" appears on the raw MinIO
# payload (storage_metadata.scraped_at) but it's not shown carried
# through to the final OpenSearch document. Ask: what field (if any)
# marks when a document was scraped/published, so "latest first" can
# sort on it. Also currently missing from Rabin's gRPC SearchResultItem
# / SearchHit -- needs adding there too once a field name is settled.
DEFAULT_DATE_FIELD = "scraped_at"

# NOTE: same open question as the date field -- content_type doesn't
# clearly appear on ETL's documented final document schema either
# (only "content_type" on the raw MinIO payload's storage_metadata).
# Confirm the real field name with ETL. This matches the
# `content_type` param name already used in Rabin's SearchRequest
# proto (search-engine/proto/search.proto), so no renaming needed
# once the actual field is confirmed.
DEFAULT_CONTENT_TYPE_FIELD = "content_type"

# Geo fields are nested under geo_location in the ETL's documented
# output schema (ETL/spark/README.md, section 5.2). Names match
# Rabin's SearchRequest proto fields exactly (province_code,
# district_code, municipality_id, ward_number).
GEO_FIELD_MAP = {
    "province_code": "geo_location.province_code",
    "district_code": "geo_location.district_code",
    "municipality_id": "geo_location.municipality_id",
    "ward_number": "geo_location.ward_number",
}


class GeoFilteredSearch:
    """Region-bounded document search/browse, newest first.

    Implements Flow B from the architecture spec ("Interactive Map &
    Region-Based Filtering"): given an administrative-boundary filter
    (province/district/municipality), return matching documents with
    the most recently scraped/published ones first.

    Two modes:
      - No `query` passed: pure browse -- e.g. "show me everything
        tagged to Kaski district", sorted strictly by recency.
      - `query` passed: same geo filter, but also matched against text
        (title/description/searchable_text), ranked by relevance with
        recency as a tie-breaker.
    """

    def __init__(
        self,
        client: OpenSearch,
        index: str,
        date_field: str = DEFAULT_DATE_FIELD,
        content_type_field: str = DEFAULT_CONTENT_TYPE_FIELD,
    ):
        self.client = client
        self.index = index
        self.date_field = date_field
        self.content_type_field = content_type_field

    def browse(
        self,
        province_code: str | None = None,
        district_code: str | None = None,
        municipality_id: str | None = None,
        ward_number: int | None = None,
        content_type: str | None = None,
        query: str | None = None,
        k: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return documents matching the given geo/content-type filters.

        Returns a dict shaped to match Rabin's SearchOutput
        (search-engine/src/pgs_search/grpc/pipeline_adapter.py):
            {"total_hits": int, "results": [{"document_id", "score", "source"}, ...]}

        At least one geo filter should normally be passed -- calling
        this with none is equivalent to "browse everything, newest
        first" and is allowed, but is rarely what you want for a
        region-bounded search.
        """
        filter_clauses = self._build_filters(
            province_code=province_code,
            district_code=district_code,
            municipality_id=municipality_id,
            ward_number=ward_number,
            content_type=content_type,
        )

        bool_query: dict[str, Any] = {}
        if query:
            bool_query["must"] = {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "text", "description"],
                    "type": "best_fields",
                }
            }
        else:
            bool_query["must"] = {"match_all": {}}

        if filter_clauses:
            bool_query["filter"] = filter_clauses

        sort_clauses: list[Any] = []
        if query:
            # Relevance first, recency breaks ties.
            sort_clauses.append({"_score": {"order": "desc"}})
        sort_clauses.append(
            {self.date_field: {"order": "desc", "unmapped_type": "date"}}
        )

        body = {
            "size": k,
            "from": offset,
            "query": {"bool": bool_query},
            "sort": sort_clauses,
            "track_total_hits": True,
        }

        response = self.client.search(index=self.index, body=body)

        results = [
            {
                "document_id": hit["_id"],
                "score": hit.get("_score"),
                "source": hit.get("_source", {}),
            }
            for hit in response["hits"]["hits"]
        ]

        return {
            "total_hits": response["hits"]["total"]["value"],
            "results": results,
        }

    def _build_filters(
        self,
        province_code: str | None,
        district_code: str | None,
        municipality_id: str | None,
        ward_number: int | None,
        content_type: str | None,
    ) -> list[dict[str, Any]]:
        geo_values = {
            "province_code": province_code,
            "district_code": district_code,
            "municipality_id": municipality_id,
            "ward_number": ward_number,
        }
        clauses = [
            {"term": {GEO_FIELD_MAP[field]: value}}
            for field, value in geo_values.items()
            if value is not None
        ]

        if content_type is not None:
            clauses.append({"term": {self.content_type_field: content_type}})

        return clauses
