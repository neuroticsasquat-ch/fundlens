"""`GET /v1/candidates/{candidate_id}`: a candidate page, and the contributions their
committees received (spec §7.2).

A candidate alias, a person's second id for the same race (NEU-2127), answers with a 301 to the id
holding their money (`gold.candidate_redirect`), cacheable like any other response, as a merged
donor's id does. Every redirect resolves in one hop.
"""

from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from psycopg import Connection
from psycopg.rows import TupleRow, dict_row

from fundlens.api.contributions import CursorParam, CycleParam, contributions_page
from fundlens.api.deps import Conn, Itemized, PageSize
from fundlens.api.schemas import (
    Candidate,
    CandidateCycle,
    ContributionPage,
    TopDonor,
    problem_responses,
)

router = APIRouter(prefix="/v1")

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
    cycles = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT candidate_cycle.cycle, candidate_cycle.race_id, race.slug AS race_slug,"
            " candidate_cycle.total_individual, candidate_cycle.total_committee,"
            " candidate_cycle.total_jfc_transfers,"
            " candidate_cycle.self_funding, candidate_cycle.ie_support,"
            " candidate_cycle.ie_oppose, candidate_cycle.contributor_count"
            " FROM gold.candidate_cycle"
            " LEFT JOIN gold.race USING (race_id)"
            " WHERE candidate_cycle.candidate_id = %s"
            " ORDER BY candidate_cycle.cycle DESC",
            (candidate_id,),
        )
        .fetchall()
    )
    return Candidate(
        **candidate,
        cycles=[CandidateCycle(**row, top_donors=top_donors[row["cycle"]]) for row in cycles],
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
