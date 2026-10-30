"""The public, read-only JSON API at `api.fundlens.org` (spec §7.2).

A factory rather than a module-level app, so importing this module reads no settings and a test
can build an app against its own database. `fundlens api` serves it with uvicorn.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fundlens import __version__
from fundlens.api.cache import BuildIdCache, CacheHeaders, read_build_id
from fundlens.api.cors import DefaultAllowOrigin
from fundlens.api.problems import install_problem_handlers
from fundlens.api.routers import health, meta
from fundlens.load.db import create_pool
from fundlens.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        # Opened without waiting for a first connection: the API starts while Postgres is still
        # coming up, and `/healthz` says so until it is.
        with create_pool(settings.database_url) as pool:
            app.state.pool = pool
            app.state.build_ids = BuildIdCache(partial(read_build_id, pool))
            yield

    app = FastAPI(title="fundlens", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    install_problem_handlers(app)
    app.add_middleware(CacheHeaders)
    app.add_middleware(DefaultAllowOrigin, origin=settings.cors_origins[0])
    # Added last, so it is outermost and answers a preflight before anything else runs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
    )
    app.include_router(health.router)
    app.include_router(meta.router)
    return app
