"""The per-process services the routes depend on, created at startup and closed at shutdown."""

from __future__ import annotations

import logging
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from ..auth.throttle import LoginThrottle
from ..auth.tokens import TokenCodec
from ..db.database import Database, PgDatabase
from ..db.search_log import SearchLogSink, SearchLogWriter
from ..grpc.client import GrpcSearchClient, SearchBackend
from ..health.readiness import ReadinessProbe
from .settings import Settings

logger = logging.getLogger(__name__)


PASSWORD_SLOT_WAIT_SECONDS = 3.0


class PasswordWorkers:
    """Caps the Argon2id hashes running at once (they cost ~64 MiB and tens of ms each).

    Routes run on a shared thread pool; without a cap a login flood would hold every
    thread in a hash and starve search. A request waits briefly for a slot, then gets 503.
    """

    def __init__(self, slots: int, wait_seconds: float = PASSWORD_SLOT_WAIT_SECONDS) -> None:
        self._slots = threading.BoundedSemaphore(slots)
        self._wait = wait_seconds

    @contextmanager
    def slot(self) -> Generator[None, None, None]:
        if not self._slots.acquire(timeout=self._wait):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Too many sign-ins in progress. Try again shortly.",
                headers={"Retry-After": "2"},
            )
        try:
            yield
        finally:
            self._slots.release()


@dataclass
class Services:
    settings: Settings
    db: Database
    search: SearchBackend
    # None when API_AUTH_SECRET is unset: the auth and admin endpoints then answer 503.
    tokens: TokenCodec | None
    search_log: SearchLogSink
    readiness: ReadinessProbe
    throttle: LoginThrottle
    passwords: PasswordWorkers

    def close(self) -> None:
        self.search_log.close()
        self.search.close()
        self.db.close()


def build_services(settings: Settings) -> Services:
    db = PgDatabase(settings.database_url.get_secret_value())
    search = GrpcSearchClient(
        settings.search_target,
        timeout_seconds=settings.search_timeout_seconds,
        tls_ca_file=settings.search_grpc_tls_ca_file,
    )
    tokens = (
        TokenCodec(settings.auth_secret.get_secret_value(), settings.token_ttl_seconds)
        if settings.auth_secret is not None
        else None
    )
    if tokens is None:
        logger.warning("API_AUTH_SECRET is not set: login and admin endpoints answer 503")
    return Services(
        settings=settings,
        db=db,
        search=search,
        tokens=tokens,
        search_log=SearchLogWriter(db),
        readiness=ReadinessProbe(db, search),
        throttle=LoginThrottle(db),
        passwords=PasswordWorkers(settings.password_workers),
    )


def get_services(request: Request) -> Services:
    services = getattr(request.app.state, "services", None)
    if not isinstance(services, Services):
        raise RuntimeError("API services are not initialised (lifespan did not run)")
    return services


ServicesDep = Annotated[Services, Depends(get_services)]
