"""`GET /v1/donors/{donor_id}`: a resolved donor's page, and every contribution they made
(spec §7.2).

A donor_id merged away by a later resolution answers with a 301 to the id it became
(`gold.donor_redirect`, spec §6.6), cacheable like any other response, so an old link keeps
working. Every redirect resolves in one hop.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request, Response
from fastapi.responses import RedirectResponse
from psycopg import Connection
from psycopg.rows import TupleRow, class_row, dict_row

from fundlens.api.contributions import CursorParam, OptionalCycleParam, as_contribution_page
from fundlens.api.deps import Conn, Itemized, PageSize
from fundlens.api.schemas import (
    ContributionPage,
    Donor,
    DonorCycle,
    DonorTopRecipient,
    problem_responses,
)

router = APIRouter(prefix="/v1")

# gold's donor_id is a bigint; a larger one would fail in Postgres, not as a 422.
DonorId = Annotated[int, Path(ge=1, le=2**63 - 1)]
MOVED: dict[int | str, dict[str, object]] = {
    301: {"description": "The donor was merged into another: `Location` names the id it became."}
}


def redirect(
    conn: Connection[TupleRow], donor_id: int, request: Request, rest: str = ""
) -> Response:
    """A 301 to `/v1/donors/<id it was merged into><rest>`, the query kept; a 404 when no donor
    ever had the id."""
    row = conn.execute(
        "SELECT donor_id FROM gold.donor_redirect WHERE old_donor_id = %s", (donor_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"No donor {donor_id}.")
    query = f"?{request.url.query}" if request.url.query else ""
    # Relative, so it holds behind whatever host and scheme the edge serves.
    return RedirectResponse(f"/v1/donors/{row[0]}{rest}{query}", status_code=301)


@router.get(
    "/donors/{donor_id}",
    response_model=Donor,
    responses=MOVED | problem_responses(404, 422, 503),
)
def get_donor(conn: Conn, request: Request, donor_id: DonorId) -> Donor | Response:
    donor = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT donor_id, display_name, employer, occupation, city, state, zip5,"
            " total_all_cycles, first_cycle, last_cycle, contributor_key_count"
            " FROM gold.donor WHERE donor_id = %s",
            (donor_id,),
        )
        .fetchone()
    )
    if donor is None:
        return redirect(conn, donor_id, request)
    cycles = (
        conn.cursor(row_factory=class_row(DonorCycle))
        .execute(
            "SELECT cycle, amount, contribution_count"
            " FROM gold.donor_cycle WHERE donor_id = %s ORDER BY cycle DESC",
            (donor_id,),
        )
        .fetchall()
    )
    top_recipients = (
        conn.cursor(row_factory=class_row(DonorTopRecipient))
        .execute(
            "SELECT rank, recipient_kind, recipient_id, name, amount"
            " FROM gold.donor_top_recipient WHERE donor_id = %s ORDER BY rank",
            (donor_id,),
        )
        .fetchall()
    )
    return Donor(**donor, cycles=cycles, top_recipients=top_recipients)


@router.get(
    "/donors/{donor_id}/contributions",
    response_model=ContributionPage,
    responses=MOVED | problem_responses(400, 404, 410, 422, 503),
)
def get_donor_contributions(
    conn: Conn,
    itemized: Itemized,
    page_size: PageSize,
    request: Request,
    donor_id: DonorId,
    cycle: OptionalCycleParam = None,
    cursor: CursorParam = None,
) -> ContributionPage | Response:
    """Every contribution the donor made under each of their name, employer and address
    variants, in `cycle` or in every cycle, newest cycle first and newest first within it."""
    found = conn.execute("SELECT 1 FROM gold.donor WHERE donor_id = %s", (donor_id,)).fetchone()
    if found is None:
        return redirect(conn, donor_id, request, "/contributions")
    return as_contribution_page(
        lambda: itemized.donor_contributions(donor_id, cycle=cycle, cursor=cursor, limit=page_size)
    )
