from geo_filter_search import GeoFilteredSearch
from opensearchpy import OpenSearch

INDEX_NAME = "nepal_test_documents_geo"

# NOTE: "scraped_at" and "content_type" are placeholder field names --
# confirm both with the ETL team once their indexed document schema
# settles. See the NOTEs in geo_filter_search.py (ETL/spark/README.md,
# section 5.2, doesn't show either field on the final indexed document).
DATE_FIELD = "scraped_at"
CONTENT_TYPE_FIELD = "content_type"


# Connect to local OpenSearch
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    use_ssl=False,
    verify_certs=False,
)


# Sample documents across different regions, dates, and content types,
# matching the ETL team's documented geo_location shape
# (ETL/spark/README.md, section 5.2)
documents = [
    {
        "title": "Pokhara Metropolitan City Notice",
        "description": "Official notice regarding municipal administration.",
        "text": "Road maintenance work scheduled in Pokhara this month.",
        "geo_location": {
            "province_code": "P4",
            "province_name_en": "Gandaki Province",
            "district_code": "D39",
            "district_name_en": "Kaski",
            "municipality_id": "MUN75340",
            "municipality_name_en": "Pokhara",
            "ward_number": 5,
        },
        "content_type": "web_page",
        "scraped_at": "2026-09-20T10:00:00Z",
    },
    {
        "title": "Pokhara Tourism Update",
        "description": "New tourism initiatives announced for Pokhara.",
        "text": "Pokhara tourism board launches new trekking routes.",
        "geo_location": {
            "province_code": "P4",
            "province_name_en": "Gandaki Province",
            "district_code": "D39",
            "district_name_en": "Kaski",
            "municipality_id": "MUN75340",
            "municipality_name_en": "Pokhara",
            "ward_number": 5,
        },
        "content_type": "web_page",
        "scraped_at": "2026-09-23T08:00:00Z",
    },
    {
        "title": "Kathmandu Metropolitan Notice",
        "description": "Traffic advisory for Kathmandu valley.",
        "text": "Kathmandu traffic police announce new routes for the festival season.",
        "geo_location": {
            "province_code": "P3",
            "province_name_en": "Bagmati Province",
            "district_code": "D27",
            "district_name_en": "Kathmandu",
            "municipality_id": "MUN27001",
            "municipality_name_en": "Kathmandu Metropolitan City",
            "ward_number": 2,
        },
        "content_type": "web_page",
        "scraped_at": "2026-09-22T09:00:00Z",
    },
    {
        "title": "Kaski District Agriculture Report",
        "description": "Agricultural output report for Kaski district.",
        "text": "Farmers in Kaski district report increased maize yields this season.",
        "geo_location": {
            "province_code": "P4",
            "province_name_en": "Gandaki Province",
            "district_code": "D39",
            "district_name_en": "Kaski",
            "municipality_id": "MUN75341",
            "municipality_name_en": "Annapurna Rural Municipality",
            "ward_number": 1,
        },
        "content_type": "pdf",
        "scraped_at": "2026-09-18T12:00:00Z",
    },
]


def create_index():
    # Always start from a clean index -- this script is meant to be
    # re-run freely, so drop any existing index from a previous run
    # rather than erroring on "already exists".
    if client.indices.exists(index=INDEX_NAME):
        client.indices.delete(index=INDEX_NAME)

    index_body = {
        "mappings": {
            "properties": {
                "title": {"type": "text"},
                "description": {"type": "text"},
                "text": {"type": "text"},
                "scraped_at": {"type": "date"},
                "content_type": {"type": "keyword"},
                "geo_location": {
                    "properties": {
                        "province_code": {"type": "keyword"},
                        "province_name_en": {"type": "keyword"},
                        "district_code": {"type": "keyword"},
                        "district_name_en": {"type": "keyword"},
                        "municipality_id": {"type": "keyword"},
                        "municipality_name_en": {"type": "keyword"},
                        "ward_number": {"type": "integer"},
                    }
                },
            }
        },
    }

    client.indices.create(
        index=INDEX_NAME,
        body=index_body,
    )


def insert_documents():
    for document_id, document in enumerate(documents, start=1):
        client.index(
            index=INDEX_NAME,
            id=document_id,
            body=document,
            refresh=True,
        )


def print_results(label: str, response: dict) -> None:
    print(f"\n{label}")
    print(f"Total hits: {response['total_hits']}")
    print("-" * 60)

    for rank, result in enumerate(response["results"], start=1):
        source = result["source"]
        print(f"{rank}. {source['title']}")
        print(f"   Scraped at: {source['scraped_at']}")
        print(f"   Content type: {source['content_type']}")
        print(f"   Geo: {source['geo_location']}")
        print(f"   Score: {result['score']}")
        print()


def run_geo_browse():
    """Pure geo browse, no text query -- newest first within the region."""
    searcher = GeoFilteredSearch(client=client, index=INDEX_NAME, date_field=DATE_FIELD)

    response = searcher.browse(district_code="D39", k=5)
    print_results("Browse: district_code=D39 (Kaski), newest first", response)


def run_geo_browse_narrower():
    """Narrower geo filter -- down to municipality level."""
    searcher = GeoFilteredSearch(client=client, index=INDEX_NAME, date_field=DATE_FIELD)

    response = searcher.browse(municipality_id="MUN75340", k=5)
    print_results("Browse: municipality_id=MUN75340 (Pokhara Metro), newest first", response)


def run_geo_filtered_text_search():
    """Geo filter combined with a text query -- relevance first, recency
    as the tie-breaker."""
    searcher = GeoFilteredSearch(client=client, index=INDEX_NAME, date_field=DATE_FIELD)

    response = searcher.browse(district_code="D39", query="tourism", k=5)
    print_results("Search 'tourism' within district_code=D39", response)


def run_geo_and_content_type_filter():
    """Geo filter combined with content_type -- e.g. only PDFs in Kaski."""
    searcher = GeoFilteredSearch(client=client, index=INDEX_NAME, date_field=DATE_FIELD)

    response = searcher.browse(district_code="D39", content_type="pdf", k=5)
    print_results("Browse: district_code=D39, content_type=pdf", response)


def run_ward_number_filter():
    """Filter down to a specific ward number (now an int, matching the proto)."""
    searcher = GeoFilteredSearch(client=client, index=INDEX_NAME, date_field=DATE_FIELD)

    response = searcher.browse(district_code="D39", ward_number=5, k=5)
    print_results("Browse: district_code=D39, ward_number=5", response)


def print_region_counts(label: str, results: list[dict]) -> None:
    print(f"\n{label}")
    print("-" * 60)
    for region in results:
        print(f"  {region['code']} ({region['name']}): {region['count']} documents")


def run_district_counts_within_province():
    """Map drill-down: district-level counts within Gandaki Province."""
    searcher = GeoFilteredSearch(client=client, index=INDEX_NAME, date_field=DATE_FIELD)

    results = searcher.count_by_region(level="district", province_code="P4")
    print_region_counts("Document counts by district within province_code=P4", results)


def run_province_counts():
    """Map zoomed out: province-level counts across everything indexed."""
    searcher = GeoFilteredSearch(client=client, index=INDEX_NAME, date_field=DATE_FIELD)

    results = searcher.count_by_region(level="province")
    print_region_counts("Document counts by province (all data)", results)


def main():
    print("Creating geo test index...")
    create_index()

    print("Adding sample geo-tagged documents...")
    insert_documents()

    print("Running geo-filtered searches...")

    run_geo_browse()
    run_geo_browse_narrower()
    run_geo_filtered_text_search()
    run_geo_and_content_type_filter()
    run_ward_number_filter()
    run_province_counts()
    run_district_counts_within_province()


if __name__ == "__main__":
    main()
