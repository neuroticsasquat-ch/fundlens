"""`GET /v1/committees/{committee_id}`: a committee page (spec §7.2)."""

from collections import defaultdict

from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from fundlens.api.deps import Conn
from fundlens.api.schemas import Committee, CommitteeCycle, CommitteeTopRecipient, problem_responses

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
            CommitteeCycle(**row, top_recipients=top_recipients[row["cycle"]]) for row in cycles
        ],
    )
