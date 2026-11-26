"""`GET /v1/committees/{committee_id}`: a committee page, its itemized receipts, its independent
expenditures and its operating expenditures (spec §7.2; every-FEC-dollar spec §5)."""

from collections import defaultdict
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from psycopg.rows import dict_row

from fundlens.api.contributions import CursorParam, CycleParam, contributions_page, read_page
from fundlens.api.deps import Conn, Itemized, PageSize
from fundlens.api.itemized import Sort
from fundlens.api.reported import pop_reported, reported_columns
from fundlens.api.schemas import (
    Committee,
    CommitteeCycle,
    CommitteeTopRecipient,
    ContributionPage,
    IndependentExpenditure,
    IndependentExpenditurePage,
    OperatingExpenditure,
    OperatingExpenditurePage,
    SpendingByCategory,
    SpendingCategory,
    Sponsor,
    TopDonor,
    TopOrganization,
    TopPayee,
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
    categories = conn.cursor(row_factory=dict_row).execute(
        "SELECT cycle, category, amount FROM gold.committee_spending_category"
        " WHERE committee_id = %s ORDER BY cycle, amount DESC, category",
        (committee_id,),
    )
    spending_by_category: defaultdict[int, list[SpendingByCategory]] = defaultdict(list)
    for row in categories:
        spending_by_category[row.pop("cycle")].append(SpendingByCategory(**row))
    payees = conn.cursor(row_factory=dict_row).execute(
        "SELECT cycle, rank, name, payee_key, payee_id, amount"
        " FROM gold.committee_top_payee WHERE committee_id = %s ORDER BY cycle, rank",
        (committee_id,),
    )
    top_payees: defaultdict[int, list[TopPayee]] = defaultdict(list)
    for row in payees:
        top_payees[row.pop("cycle")].append(TopPayee(**row))
    cycles = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT cycle, total_individual, self_funding, total_from_committees,"
            " total_from_organizations, total_to_candidates, total_returned_by_candidates,"
            " total_non_contribution_account, total_refunds, ie_total,"
            " communication_cost_total, party_coordinated_total, electioneering_total,"
            " outside_spending_total,"
            f" {reported_columns('committee_cycle')}, itemized_total, coverage,"
            " total_operating_expenditures, is_leadership_pac, is_lobbyist_pac,"
            # The sponsor's id, an alias resolved to the id holding their money, so a page's
            # link lands on it with no 301.
            " coalesce("
            "(SELECT candidate_id FROM gold.candidate_redirect"
            " WHERE old_candidate_id = committee_cycle.sponsor_candidate_id),"
            " sponsor_candidate_id) AS sponsor_candidate_id,"
            " sponsor_name, bundled_total"
            " FROM gold.committee_cycle WHERE committee_id = %s ORDER BY cycle DESC",
            (committee_id,),
        )
        .fetchall()
    )
    return Committee(
        **committee,
        cycles=[
            CommitteeCycle(
                reported=reported,
                sponsor=sponsor,
                **row,
                spending_by_category=spending_by_category[row["cycle"]],
                top_payees=top_payees[row["cycle"]],
                top_recipients=top_recipients[row["cycle"]],
                top_donors=top_donors[row["cycle"]],
                top_organizations=top_organizations[row["cycle"]],
            )
            for row in cycles
            # Popped first, so `row` holds no `reported_*` column when it is spread.
            for reported in [pop_reported(row)]
            for sponsor in [_pop_sponsor(row)]
        ],
    )


def _pop_sponsor(row: dict[str, Any]) -> Sponsor | None:
    """`row`'s sponsor columns, removed from it, as a `Sponsor`; None when it names nobody."""
    candidate_id, name = row.pop("sponsor_candidate_id"), row.pop("sponsor_name")
    if candidate_id is None and name is None:
        return None
    return Sponsor(candidate_id=candidate_id, name=name)


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


@router.get(
    "/committees/{committee_id}/expenditures",
    responses=problem_responses(400, 404, 410, 422, 503),
)
def get_committee_expenditures(
    conn: Conn,
    itemized: Itemized,
    page_size: PageSize,
    committee_id: str,
    cycle: CycleParam,
    category: Annotated[
        SpendingCategory | None, Query(description="Only the payments of this spending category.")
    ] = None,
    sort: Annotated[
        Sort, Query(description="`date`, newest first, or `amount`, largest first.")
    ] = "date",
    cursor: CursorParam = None,
) -> OperatingExpenditurePage:
    """The operating expenditures the committee itemized in `cycle`, each with the sub-items that
    itemize it nested under it: a card bill with its charges. Only `counted` rows add up to its
    total_operating_expenditures. `category` keeps the payments of that category, their sub-items
    whatever theirs, so a category's counted rows add up to its `spending_by_category` amount."""
    found = conn.execute(
        "SELECT 1 FROM gold.committee WHERE committee_id = %s", (committee_id,)
    ).fetchone()
    if found is None:
        raise HTTPException(404, f"No committee {committee_id}.")
    page = read_page(
        lambda: itemized.operating_expenditures(
            cycle, committee_id, category=category, sort=sort, cursor=cursor, limit=page_size
        )
    )
    # Each payee key's page: one unique-key lookup of the page's keys, sub-items' included.
    keys = {row["payee_key"] for row in _with_sub_items(page.rows) if row["payee_key"] is not None}
    payee_ids: dict[str, str] = dict(
        conn.execute(
            "SELECT payee_key, payee_id FROM gold.payee WHERE payee_key = ANY(%s)", (list(keys),)
        ).fetchall()
    )
    return OperatingExpenditurePage(
        expenditures=[_expenditure(row, payee_ids) for row in page.rows],
        next_cursor=page.next_cursor,
    )


def _with_sub_items(rows: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """`rows` and every sub-item under them."""
    for row in rows:
        yield row
        yield from _with_sub_items(row["sub_items"])


def _expenditure(row: dict[str, Any], payee_ids: dict[str, str]) -> OperatingExpenditure:
    return OperatingExpenditure.model_validate(
        row
        | {
            "source_record_id": str(row["source_record_id"]),
            "payee_id": payee_ids.get(row["payee_key"] or ""),
            "sub_items": [_expenditure(sub_item, payee_ids) for sub_item in row["sub_items"]],
        }
    )
