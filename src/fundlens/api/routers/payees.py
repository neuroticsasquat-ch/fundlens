"""`GET /v1/payees/{payee_id}`: a payee page, its totals by cycle and the committees that paid it
most in one (every-FEC-dollar spec §5.4, §5.5; ADR-0012).

Only a key with a page has a `payee_id`: a person's key and a name that names nobody have none,
so their ids are unknown, as any other is. An itemized list of a payee's payments is not served:
it would scan every committee's partition of the cycle, and the top payers answer who pays them.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from psycopg.rows import class_row, dict_row

from fundlens.api.deps import Conn
from fundlens.api.schemas import Payee, PayeeCycle, PayeeTopPayer, problem_responses

router = APIRouter(prefix="/v1")

# The first 16 hexadecimal characters, lower case, of the SHA-256 of the payee key (spec §5.4).
PayeeId = Annotated[str, Path(pattern="^[0-9a-f]{16}$")]
PayeeCycleParam = Annotated[
    int | None,
    Query(ge=1980, multiple_of=2, description="The payee's last cycle, if left out."),
]


@router.get("/payees/{payee_id}", responses=problem_responses(404, 422, 503))
def get_payee(conn: Conn, payee_id: PayeeId, cycle: PayeeCycleParam = None) -> Payee:
    payee = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT payee_id, payee_key, display_name, city, state, total_all_cycles,"
            " first_cycle, last_cycle FROM gold.payee WHERE payee_id = %s",
            (payee_id,),
        )
        .fetchone()
    )
    if payee is None:
        raise HTTPException(404, f"No payee {payee_id}.")
    cycles = (
        conn.cursor(row_factory=class_row(PayeeCycle))
        .execute(
            "SELECT cycle, total, committee_count"
            " FROM gold.payee_cycle WHERE payee_id = %s ORDER BY cycle DESC",
            (payee_id,),
        )
        .fetchall()
    )
    payers_cycle: int = payee["last_cycle"] if cycle is None else cycle
    top_payers = (
        conn.cursor(row_factory=class_row(PayeeTopPayer))
        .execute(
            "SELECT payer.rank, payer.committee_id, committee.name AS committee_name,"
            " payer.candidate_id, candidate.name AS candidate_name, payer.amount"
            " FROM gold.payee_top_payer AS payer"
            " LEFT JOIN gold.committee USING (committee_id)"
            " LEFT JOIN gold.candidate USING (candidate_id)"
            " WHERE payer.payee_id = %s AND payer.cycle = %s ORDER BY payer.rank",
            (payee_id, payers_cycle),
        )
        .fetchall()
    )
    return Payee(**payee, cycles=cycles, cycle=payers_cycle, top_payers=top_payers)
