"""What the `/contributions` routes share: their parameters, and the itemized reader's answers
and failures as HTTP (spec §7.2)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import HTTPException, Query

from fundlens.api.itemized import (
    BadCursor,
    BuildGone,
    CycleNotLive,
    ItemizedReader,
    Page,
    Recipient,
)
from fundlens.api.schemas import Contribution, ContributionPage

# Required: a page is one cycle's partition (ADR-0006). FEC cycles are even years from 1980.
CycleParam = Annotated[int, Query(ge=1980, multiple_of=2)]
# A donor's contributions are one bucket file per cycle, so every cycle is still a bounded scan.
OptionalCycleParam = Annotated[
    int | None, Query(ge=1980, multiple_of=2, description="Every cycle, newest first, if left out.")
]
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
    return as_contribution_page(
        lambda: itemized.contributions(
            cycle, recipient, recipient_id, cursor=cursor, limit=page_size
        )
    )


def as_contribution_page(read: Callable[[], Page]) -> ContributionPage:
    """The page `read` returns, its failures as problems."""
    try:
        page = read()
    except CycleNotLive as exc:
        raise HTTPException(404, f"No published build covers cycle {exc.args[0]}.") from None
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
