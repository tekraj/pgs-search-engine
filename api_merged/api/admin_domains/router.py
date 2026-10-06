from fastapi import APIRouter, Query, HTTPException
from grpc_client import AdminGrpcClient

from admin_domains.schemas import (
    DomainListResponse,
    DomainInfo,
    AddDomainsRequest,
    AddDomainsResponse,
    DomainActionRequest,
    DomainActionResponse,
)

router = APIRouter()

_MOCK_DOMAINS = [
    {
        "domain": "mofaga.gov.np",
        "category": "Government",
        "status": "CRAWLING",
        "discovered_child_links": 4520,
        "scraped_pages": 4100,
        "failed_pages": 12,
        "last_crawled_at": "2026-09-16T22:50:00Z",
        "rate_limit_per_sec": 5,
    },
    {
        "domain": "failedsite.com.np",
        "category": "News",
        "status": "FAILED",
        "discovered_child_links": 120,
        "scraped_pages": 0,
        "failed_pages": 120,
        "last_crawled_at": "2026-09-15T10:00:00Z",
        "rate_limit_per_sec": 2,
    },
]


@router.get("", response_model=DomainListResponse)
def list_domains(
    status: Optional[str] = Query(
        None, description="CRAWLING, FAILED, PENDING, COMPLETED"
    ),
    search_domain: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    """GET /api/v1/admin/domains"""
    results = _MOCK_DOMAINS

    if status:
        results = [d for d in results if d["status"] == status.upper()]
    if search_domain:
        results = [d for d in results if search_domain.lower() in d["domain"].lower()]

    start = (page - 1) * limit
    end = start + limit
    page_results = results[start:end]

    return DomainListResponse(
        total_count=len(results),
        domains=[DomainInfo(**d) for d in page_results],
    )


@router.post("/add", response_model=AddDomainsResponse)
def add_domains(payload: AddDomainsRequest):
    """POST /api/v1/admin/domains/add"""
    # TODO: call gRPC ManageDomain / seed-add equivalent here
    for d in payload.domains:
        _MOCK_DOMAINS.append(
            {
                "domain": d,
                "category": payload.category,
                "status": "PENDING",
                "discovered_child_links": 0,
                "scraped_pages": 0,
                "failed_pages": 0,
                "last_crawled_at": None,
                "rate_limit_per_sec": 5,
            }
        )

    return AddDomainsResponse(
        success=True,
        added_count=len(payload.domains),
        message=f"{len(payload.domains)} domain(s) queued with priority {payload.priority}",
    )


@router.post("/{domain_name}/action", response_model=DomainActionResponse)
def domain_action(domain_name: str, payload: DomainActionRequest):
    """POST /api/v1/admin/domains/{domain_name}/action"""
    domain = next((d for d in _MOCK_DOMAINS if d["domain"] == domain_name), None)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found")

    # TODO: replace with real gRPC ManageDomainRequest call
    action_map = {
        "PAUSE": "PAUSED",
        "RESUME": "CRAWLING",
        "RE_CRAWL": "PENDING",
        "DELETE": "DELETED",
    }
    domain["status"] = action_map[payload.action]

    if payload.action == "DELETE":
        _MOCK_DOMAINS.remove(domain)

    return DomainActionResponse(
        success=True,
        message=f"Action '{payload.action}' applied to {domain_name}",
    )