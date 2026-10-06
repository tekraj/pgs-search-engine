from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import require_roles

from admin_domains.schemas import DomainCreate
from admin_domains.service import (
    create_domain,
    list_domains,
    update_domain,
    delete_domain,
)


router = APIRouter()


admin_required = Depends(
    require_roles("admin")
)


@router.post(
    "",
    dependencies=[admin_required],
)
def add_domain(request: DomainCreate):

    try:

        return create_domain(
            domain=request.domain,
            enabled=request.enabled,
            crawl_enabled=request.crawl_enabled,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get(
    "",
    dependencies=[admin_required],
)
def get_domains():

    return list_domains()


@router.patch(
    "/{domain}",
    dependencies=[admin_required],
)
def update(
    domain: str,
    enabled: bool | None = None,
    crawl_enabled: bool | None = None,
):

    try:

        return update_domain(
            domain,
            enabled,
            crawl_enabled,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.delete(
    "/{domain}",
    dependencies=[admin_required],
)
def remove(domain: str):

    try:

        return delete_domain(domain)

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )