"""`GET /v1/committees/{committee_id}`: a committee page, and its itemized receipts (spec §7.2)."""

from collections import defaultdict

from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from fundlens.api.contributions import CursorParam, CycleParam, contributions_page
from fundlens.api.deps import Conn, Itemized, PageSize
from fundlens.api.schemas import (
    Committee,
    CommitteeCycle,
    CommitteeTopRecipient,
    ContributionPage,
    TopDonor,
    problem_responses,
)

router = APIRouter(prefix="/v1")


@router.get("/committees/{committee_id}", responses=problem_responses(404, 422, 503))
def get_committee(conn: Conn, committee_id: str) -> Committee:
    committee = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT committee_id, name, type, designation, party, connected_org, is_conduit"
            " FROM gold.committee WHERE committee_id = %s",
            (committee_id,),
        )
        .fetchone()
    )
    if committee is None:
        raise HTTPException(404, f"No committee {committee_id}.")
    recipients = conn.cursor(row_factory=dict_row).execute(
        "SELECT cycle, rank, recipient_kind, recipient_id, name, amount"
        " FROM gold.committee_top_recipient WHERE committee_id = %s ORDER BY cycle, rank",
        (committee_id,),
    )
    top_recipients: defaultdict[int, list[CommitteeTopRecipient]] = defaultdict(list)
    for row in recipients:
        top_recipients[row.pop("cycle")].append(CommitteeTopRecipient(**row))
    donors = conn.cursor(row_factory=dict_row).execute(
        "SELECT cycle, rank, donor_id, display_name, amount"
        " FROM gold.committee_top_donor WHERE committee_id = %s ORDER BY cycle, rank",
        (committee_id,),
    )
    top_donors: defaultdict[int, list[TopDonor]] = defaultdict(list)
    for row in donors:
        top_donors[row.pop("cycle")].append(TopDonor(**row))
    cycles = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT cycle, total_individual, self_funding, total_from_committees,"
            " total_to_candidates, ie_total"
            " FROM gold.committee_cycle WHERE committee_id = %s ORDER BY cycle DESC",
            (committee_id,),
        )
        .fetchall()
    )
    return Committee(
        **committee,
        cycles=[
            CommitteeCycle(
                **row,
                top_recipients=top_recipients[row["cycle"]],
                top_donors=top_donors[row["cycle"]],
            )
            for row in cycles
        ],
    )


@router.get(
    "/committees/{committee_id}/contributions", responses=problem_responses(400, 404, 410, 422, 503)
)
def get_committee_contributions(
    conn: Conn,
    itemized: Itemized,
    page_size: PageSize,
    committee_id: str,
    cycle: CycleParam,
    cursor: CursorParam = None,
) -> ContributionPage:
    """The contributions the committee received in `cycle`, newest first."""
    found = conn.execute(
        "SELECT 1 FROM gold.committee WHERE committee_id = %s", (committee_id,)
    ).fetchone()
    if found is None:
        raise HTTPException(404, f"No committee {committee_id}.")
    return contributions_page(
        itemized,
        "recipient_committee_id",
        committee_id,
        cycle=cycle,
        cursor=cursor,
        page_size=page_size,
    )
