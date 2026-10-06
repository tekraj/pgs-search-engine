from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings

from auth.router import router as auth_router
from user_search.router import router as user_search_router
from geo.router import router as geo_router

from admin_monitoring.router import (
    router as admin_monitoring_router
)

from admin_domains.router import (
    router as admin_domains_router
)

from admin_storage_logs.router import (
    router as admin_storage_logs_router
)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


p = settings.api_v1_prefix


# Authentication
app.include_router(
    auth_router,
    prefix=f"{p}/auth",
    tags=["Auth"],
)


# User Search
app.include_router(
    user_search_router,
    prefix=f"{p}/user",
    tags=["User Search"],
)


# Geo
app.include_router(
    geo_router,
    prefix=f"{p}/user/geo",
    tags=["Geo"],
)


# Admin Monitoring
app.include_router(
    admin_monitoring_router,
    prefix=f"{p}/admin",
    tags=["Admin Monitoring"],
)


# Admin Domains
app.include_router(
    admin_domains_router,
    prefix=f"{p}/admin/domains",
    tags=["Domain Management"],
)


# Admin Storage / Logs
app.include_router(
    admin_storage_logs_router,
    prefix=f"{p}/admin",
    tags=["Storage & Logs"],
)


@app.get("/")
def hello_world():

    return {
        "message": "PGS Search Engine API"
    }


@app.get("/health")
def health():

    return {
        "status": "ok"
    }