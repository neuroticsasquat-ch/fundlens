"""`GET /v1/cycles` and `GET /v1/cycles/{cycle}/races` (spec §7.2)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from psycopg.rows import class_row

from fundlens.api.deps import Conn
from fundlens.api.schemas import Cycle, Office, RaceSummary, problem_responses

router = APIRouter(prefix="/v1")

RACE_COLUMNS = (
    "race_id, cycle, office, state, district, is_special, slug, candidate_count,"
    " total_individual, total_committee, ie_support, ie_oppose"
)


@router.get("/cycles", responses=problem_responses(503))
def list_cycles(conn: Conn) -> list[Cycle]:
    """Every cycle in gold, newest first."""
    return (
        conn.cursor(row_factory=class_row(Cycle))
        .execute(
            "SELECT cycle, race_count, contribution_count, total_amount"
            " FROM gold.cycle ORDER BY cycle DESC"
        )
        .fetchall()
    )


@router.get("/cycles/{cycle}/races", responses=problem_responses(404, 422, 503))
def list_races(
    conn: Conn,
    cycle: int,
    office: Annotated[Office | None, Query(description="H, S or P, as in `office`.")] = None,
    state: Annotated[str | None, Query(pattern=r"^[A-Z]{2}$")] = None,
) -> list[RaceSummary]:
    """A cycle's races: President, then Senate, then House, each by state and district."""
    races = (
        conn.cursor(row_factory=class_row(RaceSummary))
        .execute(
            f"SELECT {RACE_COLUMNS} FROM gold.race"
            " WHERE cycle = %(cycle)s"
            " AND (%(office)s::text IS NULL OR office = %(office)s)"
            " AND (%(state)s::text IS NULL OR state = %(state)s)"
            " ORDER BY array_position(ARRAY['P', 'S', 'H'], office), state, district, is_special",
            {"cycle": cycle, "office": office, "state": state},
        )
        .fetchall()
    )
    # An empty answer for a cycle gold has is a filter that matched nothing; for any other
    # cycle it is a 404, so a mistyped cycle is not cached as a cycle with no races.
    if (
        not races
        and conn.execute("SELECT 1 FROM gold.cycle WHERE cycle = %s", (cycle,)).fetchone() is None
    ):
        raise HTTPException(404, f"No cycle {cycle}.")
    return races
