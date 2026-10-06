from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import json
import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from core.config import settings
from auth.router import router as auth_router
from user_search.router import router as user_search_router
from geo.router import router as geo_router
from admin_monitoring.router import router as admin_monitoring_router
from admin_domains.router import router as admin_domains_router
from admin_storage_logs.router import router as admin_storage_logs_router

app = FastAPI(title="PGS Search Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

p = settings.api_v1_prefix
app.include_router(auth_router, prefix=f"{p}/auth", tags=["Auth"])
app.include_router(user_search_router, prefix=f"{p}/user", tags=["User Search"])
app.include_router(geo_router, prefix=f"{p}/user/geo", tags=["Geo"])
app.include_router(admin_monitoring_router, prefix=f"{p}/admin", tags=["Admin Monitoring"])
app.include_router(admin_domains_router, prefix=f"{p}/admin/domains", tags=["Domain Management"])
app.include_router(admin_storage_logs_router, prefix=f"{p}/admin", tags=["Storage & Logs"])


@app.get("/")
def hello_world():
    return {"message": "Hello, World!"}

@app.get("/health")
def health():
    return {"status": "ok"}



