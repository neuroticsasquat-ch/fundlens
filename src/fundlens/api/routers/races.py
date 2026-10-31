"""`GET /v1/races/{cycle}/{office}/{place}`: a race page (spec §7.2).

The path is the race's slug (M2 shared contract), `?special=1` its `-special` suffix:
`/v1/races/2024/senate/MD`, `/v1/races/2024/house/MD-05`, `/v1/races/2024/senate/NE?special=1`.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query
from psycopg.rows import class_row, dict_row

from fundlens.api.deps import Conn
from fundlens.api.routers.cycles import RACE_COLUMNS
from fundlens.api.schemas import Race, RaceCandidate, RaceTopCommittee, problem_responses

router = APIRouter(prefix="/v1")


@router.get("/races/{cycle}/{office}/{place}", responses=problem_responses(404, 422, 503))
def get_race(
    conn: Conn,
    cycle: int,
    office: Literal["house", "senate", "president"],
    place: Annotated[
        str,
        Path(
            pattern=r"^[A-Z]{2}(-[0-9]{2})?$",
            description="The state, and for a House race its district: `MD`, `MD-05`, `US`.",
        ),
    ],
    special: Annotated[bool, Query(description="The special race, not the regular one.")] = False,
) -> Race:
    slug = f"{cycle}/{office}/{place}{'-special' if special else ''}"
    race = (
        conn.cursor(row_factory=dict_row)
        .execute(f"SELECT {RACE_COLUMNS} FROM gold.race WHERE slug = %s", (slug,))
        .fetchone()
    )
    if race is None:
        raise HTTPException(404, f"No race {slug}.")
    candidates = (
        conn.cursor(row_factory=class_row(RaceCandidate))
        .execute(
            "SELECT candidate_id, name, party, incumbent_challenger_open, principal_committee_id,"
            " total_individual, total_committee, self_funding, ie_support, ie_oppose"
            " FROM gold.race_candidate WHERE race_id = %s"
            " ORDER BY total_individual + total_committee + self_funding DESC, candidate_id",
            (race["race_id"],),
        )
        .fetchall()
    )
    top_committees = (
        conn.cursor(row_factory=class_row(RaceTopCommittee))
        .execute(
            "SELECT rank, committee_id, name, amount, kind"
            " FROM gold.race_top_committee WHERE race_id = %s ORDER BY rank",
            (race["race_id"],),
        )
        .fetchall()
    )
    return Race(**race, candidates=candidates, top_committees=top_committees)
