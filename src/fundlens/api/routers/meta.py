"""`GET /v1/meta`: the live gold build (spec §7.2)."""

import psycopg
from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from fundlens.api.deps import Conn
from fundlens.api.schemas import Meta, problem_responses

router = APIRouter(prefix="/v1")

NO_GOLD = "No gold build has been published yet."


@router.get("/meta", responses=problem_responses(503))
def get_meta(conn: Conn) -> Meta:
    try:
        row = (
            conn.cursor(row_factory=dict_row)
            .execute(
                "SELECT build_id, published_at, resolver_version, model_version, precision,"
                " recall, cycles FROM gold.meta"
            )
            .fetchone()
        )
    except psycopg.errors.UndefinedTable:
        raise HTTPException(503, NO_GOLD) from None
    if row is None:
        raise HTTPException(503, NO_GOLD)
    return Meta.model_validate(row)
