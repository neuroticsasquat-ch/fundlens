"""`GET /v1/meta`: the live gold build (spec §7.2)."""

from typing import Any

from fastapi import APIRouter, HTTPException

from fundlens.api.deps import Conn
from fundlens.api.problems import NO_GOLD
from fundlens.api.schemas import Meta, problem_responses

router = APIRouter(prefix="/v1")

# Columns added to `gold.meta` after NEU-2039 (NEU-2054's figures, NEU-2056's run record), which a
# build loaded by older code has not got. The row is read whole, as JSON, so the API deployed with
# this code still answers for the build published before it, until the next load.
LATER_COLUMNS: dict[str, Any] = dict.fromkeys(
    (
        "precision_top",
        "recall_top",
        "matched_rows",
        "dime_version",
        "overrides_count",
        "adjudications_applied",
    )
)


@router.get("/meta", responses=problem_responses(503))
def get_meta(conn: Conn) -> Meta:
    row = conn.execute("SELECT to_jsonb(meta) FROM gold.meta AS meta").fetchone()
    if row is None:
        raise HTTPException(503, NO_GOLD)
    return Meta.model_validate(LATER_COLUMNS | row[0])
