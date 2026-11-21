"""`GET /v1/reconciliation?cycle=`: the committees whose fundlens figure exceeds FEC's reported one
by more than 1%, a row per measure: itemized receipts (every-FEC-dollar spec §4.5) and operating
expenditures (§5.6). For the methodology page and anyone auditing the data.

Cursor-paginated, 100 rows a page, the largest excess (fundlens - reported) first. The cursor is
the last row's excess and key, so a walk through the pages neither skips nor repeats a row of one
build; it does not hold the build, as the itemized routes' cursors do, since the table is a few
hundred rows of gold, which a publish replaces whole: a walk that spans one sees the new build's
rows from that page on.
"""

import base64
import json
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from fundlens.api.contributions import CursorParam, CycleParam
from fundlens.api.deps import Conn, PageSize
from fundlens.api.schemas import Reconciliation, ReconciliationPage, problem_responses

router = APIRouter(prefix="/v1")


def encode_cursor(excess: Decimal, committee_id: str, measure: str) -> str:
    raw = json.dumps([str(excess), committee_id, measure])
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(token: str) -> tuple[Decimal, str, str]:
    """The cursor's `(excess, committee_id, measure)`; a 400 for one this API did not issue."""
    try:
        excess, committee_id, measure = json.loads(
            base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        )
        if not (isinstance(committee_id, str) and isinstance(measure, str)):
            raise ValueError(token)
        return Decimal(excess), committee_id, measure
    except (ValueError, TypeError, InvalidOperation):
        raise HTTPException(400, "The cursor is not one this API issued.") from None


@router.get("/reconciliation", responses=problem_responses(400, 404, 422, 503))
def list_reconciliation(
    conn: Conn, page_size: PageSize, cycle: CycleParam, cursor: CursorParam = None
) -> ReconciliationPage:
    """A cycle's committees over FEC's reported figure by more than 1%, on any measure, the largest
    excess first. Empty before 2008, whose files have neither reported figure."""
    after = None if cursor is None else decode_cursor(cursor)
    rows = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT reconciliation.committee_id, committee.name, reconciliation.cycle,"
            " reconciliation.measure, reconciliation.fundlens, reconciliation.reported,"
            " reconciliation.ratio,"
            " reconciliation.fundlens - reconciliation.reported AS excess"
            " FROM gold.reconciliation"
            " LEFT JOIN gold.committee USING (committee_id)"
            " WHERE reconciliation.cycle = %(cycle)s"
            " AND (%(excess)s::numeric IS NULL"
            "  OR reconciliation.fundlens - reconciliation.reported < %(excess)s"
            "  OR (reconciliation.fundlens - reconciliation.reported = %(excess)s"
            "   AND (reconciliation.committee_id, reconciliation.measure)"
            "    > (%(committee_id)s, %(measure)s)))"
            " ORDER BY excess DESC, reconciliation.committee_id, reconciliation.measure"
            " LIMIT %(limit)s",
            {
                "cycle": cycle,
                "excess": None if after is None else after[0],
                "committee_id": None if after is None else after[1],
                "measure": None if after is None else after[2],
                "limit": page_size + 1,
            },
        )
        .fetchall()
    )
    # An empty first page for a cycle gold has is a cycle with no such committee; for any other
    # cycle it is a 404, so a mistyped cycle is not cached as a reconciled one.
    if (
        not rows
        and after is None
        and conn.execute("SELECT 1 FROM gold.cycle WHERE cycle = %s", (cycle,)).fetchone() is None
    ):
        raise HTTPException(404, f"No cycle {cycle}.")
    page, more = rows[:page_size], len(rows) > page_size
    last = page[-1] if page else None
    return ReconciliationPage(
        rows=[
            Reconciliation(**{key: value for key, value in row.items() if key != "excess"})
            for row in page
        ],
        next_cursor=(
            encode_cursor(last["excess"], last["committee_id"], last["measure"])
            if more and last is not None
            else None
        ),
    )
