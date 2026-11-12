"""`GET /v1/committees/{committee_id}`: a committee page, its itemized receipts and its independent
expenditures (spec §7.2)."""

from collections import defaultdict

from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from fundlens.api.contributions import CursorParam, CycleParam, contributions_page, read_page
from fundlens.api.deps import Conn, Itemized, PageSize
from fundlens.api.schemas import (
    Committee,
    CommitteeCycle,
    CommitteeTopRecipient,
    ContributionPage,
    IndependentExpenditure,
    IndependentExpenditurePage,
    TopDonor,
    TopOrganization,
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
    organizations = conn.cursor(row_factory=dict_row).execute(
        "SELECT cycle, rank, name, organization_key, amount"
        " FROM gold.committee_top_organization WHERE committee_id = %s ORDER BY cycle, rank",
        (committee_id,),
    )
    top_organizations: defaultdict[int, list[TopOrganization]] = defaultdict(list)
    for row in organizations:
        top_organizations[row.pop("cycle")].append(TopOrganization(**row))
    cycles = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT cycle, total_individual, self_funding, total_from_committees,"
            " total_from_organizations, total_to_candidates, total_returned_by_candidates,"
            " total_non_contribution_account, total_refunds, ie_total"
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
                top_organizations=top_organizations[row["cycle"]],
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


@router.get(
    "/committees/{committee_id}/independent-expenditures",
    responses=problem_responses(400, 404, 410, 422, 503),
)
def get_committee_independent_expenditures(
    conn: Conn,
    itemized: Itemized,
    page_size: PageSize,
    committee_id: str,
    cycle: CycleParam,
    cursor: CursorParam = None,
) -> IndependentExpenditurePage:
    """The independent expenditures the committee made in `cycle`, for and against candidates,
    newest first: the rows its `ie_total` sums."""
    found = conn.execute(
        "SELECT 1 FROM gold.committee WHERE committee_id = %s", (committee_id,)
    ).fetchone()
    if found is None:
        raise HTTPException(404, f"No committee {committee_id}.")
    page = read_page(
        lambda: itemized.independent_expenditures(
            cycle, committee_id, cursor=cursor, limit=page_size
        )
    )
    # A page's candidates' names: one primary-key lookup of at most a page of ids.
    names: dict[str, str | None] = dict(
        conn.execute(
            "SELECT candidate_id, name FROM gold.candidate WHERE candidate_id = ANY(%s)",
            ([row["candidate_id"] for row in page.rows if row["candidate_id"] is not None],),
        ).fetchall()
    )
    return IndependentExpenditurePage(
        expenditures=[
            IndependentExpenditure.model_validate(
                row
                | {
                    "source_record_id": str(row["source_record_id"]),
                    "candidate_name": names.get(row["candidate_id"] or ""),
                }
            )
            for row in page.rows
        ],
        next_cursor=page.next_cursor,
    )
