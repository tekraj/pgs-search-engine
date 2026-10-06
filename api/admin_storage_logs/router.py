from fastapi import APIRouter, Depends, Query

from core.dependencies import require_roles

from admin_storage_logs.service import (
    get_logs,
)


router = APIRouter()


@router.get(
    "/logs",
    dependencies=[
        Depends(require_roles("admin"))
    ],
)
def logs(
    level: str | None = Query(
        default=None
    ),

    service: str | None = Query(
        default=None
    ),

    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
):

    return get_logs(
        level=level,
        service=service,
        limit=limit,
    )