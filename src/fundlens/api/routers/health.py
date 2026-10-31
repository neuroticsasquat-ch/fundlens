"""`GET /healthz`: Postgres and the silver volume reachable (spec §7.2)."""

import logging

import psycopg
from fastapi import APIRouter, HTTPException

from fundlens.api.deps import AppSettings, PoolDep
from fundlens.api.schemas import Health, problem_responses
from fundlens.paths import local_path

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/healthz", responses=problem_responses(503))
def healthz(pool: PoolDep, settings: AppSettings) -> Health:
    # The pool, not a `Conn`: a connection the pool cannot supply is this check failing, a 503,
    # rather than the dependency failing and the request ending as a 500.
    try:
        with pool.connection() as conn:
            conn.execute("SELECT 1")
    except psycopg.Error as exc:  # PoolTimeout included
        log.warning("healthz: postgres unreachable: %s", exc)
        raise HTTPException(503, "Postgres is unreachable.") from None
    silver = local_path(settings.data_dir, "silver")
    if not silver.is_dir():
        log.warning("healthz: silver volume missing at %s", silver)
        raise HTTPException(503, f"The silver volume is not mounted at {silver}.")
    return Health(postgres="ok", silver="ok")
