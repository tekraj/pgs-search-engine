from typing import Any

from opensearchpy import OpenSearch

DEFAULT_DATE_FIELD = "scraped_at"


DEFAULT_CONTENT_TYPE_FIELD = "content_type"

GEO_FIELD_MAP = {
    "province_code": "geo_location.province_code",
    "district_code": "geo_location.district_code",
    "municipality_id": "geo_location.municipality_id",
    "ward_number": "geo_location.ward_number",
}

REGION_LEVEL_FIELDS = {
    "province": ("geo_location.province_code", "geo_location.province_name_en"),
    "district": ("geo_location.district_code", "geo_location.district_name_en"),
    "municipality": ("geo_location.municipality_id", "geo_location.municipality_name_en"),
}


def _get_nested(source: dict[str, Any], dotted_field: str) -> Any:
    """Pull a dotted-path value out of a nested dict, e.g.
    "geo_location.province_name_en" -> source["geo_location"]["province_name_en"].
    Returns None if any part of the path is missing.
    """
    value: Any = source
    for part in dotted_field.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


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

    def count_by_region(
        self,
        level: str,
        province_code: str | None = None,
        district_code: str | None = None,
        content_type: str | None = None,
        query: str | None = None,
        size: int = 1000,
    ) -> list[dict[str, Any]]:
        """Document counts grouped by region, for map-view aggregation
        (e.g. a choropleth or marker density map).

        `level` is one of "province", "district", "municipality" --
        which code field to group by. `province_code`/`district_code`
        scope the count to within a parent region (e.g. district
        counts within a single province, for drill-down zoom), same
        as the geo filters on `browse()`.

        Returns a list sorted by count descending:
            [{"code": "D39", "name": "Kaski", "count": 47}, ...]

        `name` is None if no document in that bucket had the name
        field populated (e.g. ETL hasn't backfilled it yet).
        """
        if level not in REGION_LEVEL_FIELDS:
            raise ValueError(
                f"Unknown level {level!r}, expected one of {sorted(REGION_LEVEL_FIELDS)}"
            )

        code_field, name_field = REGION_LEVEL_FIELDS[level]

        filter_clauses = self._build_filters(
            province_code=province_code,
            district_code=district_code,
            municipality_id=None,
            ward_number=None,
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

        body = {
            "size": 0,
            "query": {"bool": bool_query},
            "aggs": {
                "by_region": {
                    "terms": {"field": code_field, "size": size},
                    "aggs": {
                        "sample_doc": {
                            "top_hits": {"size": 1, "_source": [name_field]}
                        }
                    },
                }
            },
        }

        response = self.client.search(index=self.index, body=body)

        buckets = response["aggregations"]["by_region"]["buckets"]
        results = []
        for bucket in buckets:
            sample_hits = bucket["sample_doc"]["hits"]["hits"]
            name = None
            if sample_hits:
                name = _get_nested(sample_hits[0]["_source"], name_field)
            results.append(
                {
                    "code": bucket["key"],
                    "name": name,
                    "count": bucket["doc_count"],
                }
            )

        return sorted(results, key=lambda r: r["count"], reverse=True)

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
