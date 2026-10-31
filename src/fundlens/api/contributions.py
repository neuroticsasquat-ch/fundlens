"""What the two `/contributions` routes share: their parameters, and the itemized reader's
answers and failures as HTTP (spec §7.2)."""

from typing import Annotated

from fastapi import HTTPException, Query

from fundlens.api.itemized import (
    BadCursor,
    BuildGone,
    CycleNotLive,
    ItemizedReader,
    Recipient,
)
from fundlens.api.schemas import Contribution, ContributionPage

# Required: a page is one cycle's partition (ADR-0006). FEC cycles are even years from 1980.
CycleParam = Annotated[int, Query(ge=1980, multiple_of=2)]
CursorParam = Annotated[str | None, Query(description="`next_cursor` of the previous page.")]


def contributions_page(
    itemized: ItemizedReader,
    recipient: Recipient,
    recipient_id: str,
    *,
    cycle: int,
    cursor: str | None,
    page_size: int,
) -> ContributionPage:
    try:
        page = itemized.contributions(
            cycle, recipient, recipient_id, cursor=cursor, limit=page_size
        )
    except CycleNotLive:
        raise HTTPException(404, f"No published build covers cycle {cycle}.") from None
    except BadCursor:
        raise HTTPException(400, "The cursor is not one this API issued.") from None
    except BuildGone:
        raise HTTPException(
            410,
            "The data this cursor pages through has been replaced by a newer build."
            " Start again from the first page, without a cursor.",
        ) from None
    return ContributionPage(
        contributions=[
            Contribution.model_validate(row | {"source_record_id": str(row["source_record_id"])})
            for row in page.rows
        ],
        next_cursor=page.next_cursor,
    )
