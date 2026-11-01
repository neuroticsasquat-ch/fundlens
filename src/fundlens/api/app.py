"""The public, read-only JSON API at `api.fundlens.org` (spec §7.2).

A factory rather than a module-level app, so importing this module reads no settings and a test
can build an app against its own database. `fundlens api` serves it with uvicorn, and
`fundlens api --export-openapi` prints `openapi_json`, which the frontend's client is generated
from.
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fundlens import __version__
from fundlens.api.cache import CacheHeaders, TtlCache, read_build_id
from fundlens.api.cors import DefaultAllowOrigin
from fundlens.api.itemized import ItemizedReader, read_live_builds
from fundlens.api.problems import install_problem_handlers
from fundlens.api.routers import (
    candidates,
    committees,
    cycles,
    donors,
    health,
    meta,
    races,
    search,
)
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
            app.state.build_ids = TtlCache(partial(read_build_id, pool))
            live_builds = TtlCache(partial(read_live_builds, pool))
            app.state.itemized = ItemizedReader(settings.data_dir, live_builds.get)
            try:
                yield
            finally:
                app.state.itemized.close()

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
    for module in (health, meta, cycles, races, candidates, committees, donors, search):
        app.include_router(module.router)
    return app


def openapi_json(settings: Settings | None = None) -> str:
    """The app's OpenAPI document as the repo's `openapi.json` holds it (spec §7.2).

    Keys sorted, so the same routes and schemas always print the same bytes and CI's drift
    check compares contracts, not dict orderings. Building the app opens no connection.
    """
    return json.dumps(create_app(settings).openapi(), indent=2, sort_keys=True)
