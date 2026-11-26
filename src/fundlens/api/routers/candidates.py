"""`GET /v1/candidates/{candidate_id}`: a candidate page, and the contributions their
committees received (spec §7.2).

A candidate alias, a person's second id for the same race (NEU-2127), answers with a 301 to the id
holding their money (`gold.candidate_redirect`), cacheable like any other response, as a merged
donor's id does. Every redirect resolves in one hop.
"""

from collections import defaultdict
from typing import get_args

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from psycopg import Connection
from psycopg.rows import TupleRow, dict_row

from fundlens.api.contributions import CursorParam, CycleParam, contributions_page
from fundlens.api.deps import Conn, Itemized, PageSize
from fundlens.api.outside_spending import outside_spending_columns, pop_outside_spending
from fundlens.api.reported import pop_reported, reported_columns
from fundlens.api.schemas import (
    Candidate,
    CandidateCycle,
    ContributionPage,
    GiftSize,
    GiftSizeBucket,
    LeadershipPac,
    TopDonor,
    problem_responses,
)

router = APIRouter(prefix="/v1")

GIFT_SIZE_BUCKETS: tuple[str, ...] = get_args(GiftSizeBucket.__value__)

MOVED: dict[int | str, dict[str, object]] = {
    301: {
        "description": "The id is an alias of another candidate's: `Location` names the id"
        " holding their money."
    }
}


def redirect(
    conn: Connection[TupleRow], candidate_id: str, request: Request, rest: str = ""
) -> Response:
    """A 301 to `/v1/candidates/<id it is an alias of><rest>`, the query kept; a 404 when the id
    is no candidate's."""
    row = conn.execute(
        "SELECT candidate_id FROM gold.candidate_redirect WHERE old_candidate_id = %s",
        (candidate_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"No candidate {candidate_id}.")
    query = f"?{request.url.query}" if request.url.query else ""
    # Relative, so it holds behind whatever host and scheme the edge serves.
    return RedirectResponse(f"/v1/candidates/{row[0]}{rest}{query}", status_code=301)


@router.get(
    "/candidates/{candidate_id}",
    response_model=Candidate,
    responses=MOVED | problem_responses(404, 422, 503),
)
def get_candidate(conn: Conn, request: Request, candidate_id: str) -> Candidate | Response:
    candidate = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT candidate_id, name, party, office, state, district"
            " FROM gold.candidate WHERE candidate_id = %s",
            (candidate_id,),
        )
        .fetchone()
    )
    if candidate is None:
        return redirect(conn, candidate_id, request)
    donors = conn.cursor(row_factory=dict_row).execute(
        "SELECT cycle, rank, donor_id, display_name, amount"
        " FROM gold.candidate_top_donor WHERE candidate_id = %s ORDER BY cycle, rank",
        (candidate_id,),
    )
    top_donors: defaultdict[int, list[TopDonor]] = defaultdict(list)
    for row in donors:
        top_donors[row.pop("cycle")].append(TopDonor(**row))
    buckets = conn.cursor(row_factory=dict_row).execute(
        "SELECT cycle, bucket, amount, donors FROM gold.candidate_gift_size"
        " WHERE candidate_id = %s"
        " ORDER BY cycle, array_position(%s::text[], bucket)",
        (candidate_id, list(GIFT_SIZE_BUCKETS)),
    )
    gift_sizes: defaultdict[int, list[GiftSize]] = defaultdict(list)
    for row in buckets:
        gift_sizes[row.pop("cycle")].append(GiftSize(**row))
    cycles = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT candidate_cycle.cycle, candidate_cycle.race_id, race.slug AS race_slug,"
            " candidate_cycle.total_individual, candidate_cycle.total_committee,"
            " candidate_cycle.total_jfc_transfers,"
            " candidate_cycle.self_funding,"
            f" {outside_spending_columns('candidate_cycle')},"
            " candidate_cycle.contributor_count,"
            f" {reported_columns('candidate_cycle')},"
            " candidate_cycle.reported_includes_converted_committee,"
            " candidate_cycle.itemized_total, candidate_cycle.coverage"
            " FROM gold.candidate_cycle"
            " LEFT JOIN gold.race USING (race_id)"
            " WHERE candidate_cycle.candidate_id = %s"
            " ORDER BY candidate_cycle.cycle DESC",
            (candidate_id,),
        )
        .fetchall()
    )
    # Their leadership PACs, sponsored under this id or an alias redirecting to it (every-FEC-dollar
    # spec §7.7): the partial index on sponsor_candidate_id finds the few rows.
    leadership_pacs = conn.cursor(row_factory=dict_row).execute(
        "SELECT committee_cycle.committee_id, committee.name,"
        " array_agg(committee_cycle.cycle ORDER BY committee_cycle.cycle DESC) AS cycles"
        " FROM gold.committee_cycle JOIN gold.committee USING (committee_id)"
        " WHERE committee_cycle.sponsor_candidate_id = ANY(%s::text[] || ARRAY("
        "SELECT old_candidate_id FROM gold.candidate_redirect WHERE candidate_id = %s))"
        " GROUP BY committee_cycle.committee_id, committee.name"
        " ORDER BY max(committee_cycle.cycle) DESC, committee_cycle.committee_id",
        ([candidate_id], candidate_id),
    )
    return Candidate(
        **candidate,
        leadership_pacs=[LeadershipPac(**row) for row in leadership_pacs],
        cycles=[
            CandidateCycle(
                reported=reported,
                outside_spending=outside,
                **row,
                top_donors=top_donors[row["cycle"]],
                gift_sizes=gift_sizes[row["cycle"]],
            )
            for row in cycles
            # Popped first, so `row` holds neither's columns when it is spread.
            for reported in [pop_reported(row)]
            for outside in [pop_outside_spending(row)]
        ],
    )


@router.get(
    "/candidates/{candidate_id}/contributions",
    response_model=ContributionPage,
    responses=MOVED | problem_responses(400, 404, 410, 422, 503),
)
def get_candidate_contributions(
    conn: Conn,
    itemized: Itemized,
    page_size: PageSize,
    request: Request,
    candidate_id: str,
    cycle: CycleParam,
    cursor: CursorParam = None,
) -> ContributionPage | Response:
    """The contributions the candidate's principal and authorized committees received in
    `cycle`, newest first."""
    found = conn.execute(
        "SELECT 1 FROM gold.candidate WHERE candidate_id = %s", (candidate_id,)
    ).fetchone()
    if found is None:
        return redirect(conn, candidate_id, request, "/contributions")
    return contributions_page(
        itemized, "candidate_id", candidate_id, cycle=cycle, cursor=cursor, page_size=page_size
    )
