"""`GET /v1/races/{cycle}/{office}/{place}`: a race page (spec §7.2).

The path is the race's slug (M2 shared contract), `?special=1` its `-special` suffix:
`/v1/races/2024/senate/MD`, `/v1/races/2024/house/MD-05`, `/v1/races/2024/senate/NE?special=1`.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query
from psycopg.rows import class_row, dict_row

from fundlens.api.deps import Conn
from fundlens.api.outside_spending import (
    NON_COMMITTEE_TYPES,
    outside_spending_columns,
    pop_outside_spending,
)
from fundlens.api.reported import (
    RACE_CANDIDATE_REPORTED_FIELDS,
    pop_race_candidate_reported,
    reported_columns,
)
from fundlens.api.routers.cycles import RACE_COLUMNS
from fundlens.api.schemas import (
    Race,
    RaceCandidate,
    RaceTopCommittee,
    RaceTopDonor,
    RaceTopSpender,
    problem_responses,
)

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
        .execute(
            f"SELECT {RACE_COLUMNS}, {outside_spending_columns('race', ie=False)},"
            " race.outside_spending_total FROM gold.race WHERE slug = %s",
            (slug,),
        )
        .fetchone()
    )
    if race is None:
        raise HTTPException(404, f"No race {slug}.")
    outside_spending = pop_outside_spending(race)
    # The source file and itemized_total are candidate_cycle's, whose figures race_candidate's
    # reported fields and coverage copy (every-FEC-dollar spec §4.4).
    rows = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT race_candidate.candidate_id, race_candidate.name, race_candidate.party,"
            " race_candidate.incumbent_challenger_open, race_candidate.principal_committee_id,"
            " race_candidate.total_individual, race_candidate.total_committee,"
            " race_candidate.total_jfc_transfers, race_candidate.self_funding,"
            f" {outside_spending_columns('race_candidate')},"
            " race_candidate.total_operating_expenditures,"
            " candidate_cycle.reported_source_file,"
            f" {reported_columns('race_candidate', RACE_CANDIDATE_REPORTED_FIELDS[1:])},"
            " candidate_cycle.itemized_total, race_candidate.coverage"
            " FROM gold.race_candidate"
            " LEFT JOIN gold.candidate_cycle"
            " ON candidate_cycle.candidate_id = race_candidate.candidate_id"
            " AND candidate_cycle.cycle = %s"
            " WHERE race_candidate.race_id = %s"
            " ORDER BY race_candidate.total_individual + race_candidate.total_committee"
            " + race_candidate.total_jfc_transfers + race_candidate.self_funding DESC,"
            " race_candidate.candidate_id",
            (race["cycle"], race["race_id"]),
        )
        .fetchall()
    )
    candidates = [
        RaceCandidate(reported=reported, outside_spending=outside, **row)
        for row in rows
        # Popped first, so `row` holds neither's columns when it is spread.
        for reported in [pop_race_candidate_reported(row)]
        for outside in [pop_outside_spending(row)]
    ]
    top_committees = (
        conn.cursor(row_factory=class_row(RaceTopCommittee))
        .execute(
            "SELECT rank, committee_id, name, amount, kind"
            " FROM gold.race_top_committee WHERE race_id = %s ORDER BY rank",
            (race["race_id"],),
        )
        .fetchall()
    )
    # A spender's flag is gold.committee's type, the one its page shows: every spender has a row
    # there (spec §6.5). That is the newest cycle's `cm`, not necessarily the line's cycle's; FEC
    # gives a Form 5, 7 or 9 filer an id of its own, so an id is taken not to change between a
    # committee's type and these (asserted, not measured).
    top_spenders = (
        conn.cursor(row_factory=class_row(RaceTopSpender))
        .execute(
            "SELECT spender.rank, spender.committee_id, spender.name, spender.candidate_id,"
            # Only I, C and E are non-committee spenders (§6.1), so a blank type is not one.
            " coalesce(committee.type <> ALL(%s::text[]), true) AS is_committee,"
            " spender.kind, spender.support_oppose, spender.amount"
            " FROM gold.race_top_spender AS spender"
            " LEFT JOIN gold.committee USING (committee_id)"
            " WHERE spender.race_id = %s ORDER BY spender.rank",
            (list(NON_COMMITTEE_TYPES), race["race_id"]),
        )
        .fetchall()
    )
    top_donors = (
        conn.cursor(row_factory=class_row(RaceTopDonor))
        .execute(
            "SELECT rank, donor_id, display_name, amount, candidates"
            " FROM gold.race_top_donor WHERE race_id = %s ORDER BY rank",
            (race["race_id"],),
        )
        .fetchall()
    )
    return Race(
        **race,
        outside_spending=outside_spending,
        candidates=candidates,
        top_committees=top_committees,
        top_spenders=top_spenders,
        top_donors=top_donors,
    )
