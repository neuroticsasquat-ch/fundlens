"""Gold's outside-spending columns as the API's `OutsideSpending` objects (every-FEC-dollar spec
§6.5).

`race`, `race_candidate` and `candidate_cycle` carry each kind flat, one column per kind and side;
a response nests them under `outside_spending`. v1's `ie_support` and `ie_oppose` stay flat on the
response as well, unchanged, so they are read here and not removed from the row.
"""

from typing import Any, LiteralString

from fundlens.api.schemas import OutsideSpending, SupportOppose

# The columns `pop_outside_spending` removes from a row: the kinds NEU-2168 added.
ADDED_COLUMNS: tuple[LiteralString, ...] = (
    "communication_cost_support",
    "communication_cost_oppose",
    "party_coordinated",
    "electioneering",
)

# `committee.type` of a non-committee spender: a Form 5 (I), Form 7 (C) or Form 9 (E) filer
# (every-FEC-dollar spec §6.1).
NON_COMMITTEE_TYPES = ("I", "C", "E")


def outside_spending_columns(table: LiteralString, *, ie: bool = True) -> LiteralString:
    """`table`'s outside-spending columns, for a SELECT list: those `pop_outside_spending` reads,
    `ie_support` and `ie_oppose` left out when not `ie`, for a list that already names them."""
    columns: tuple[LiteralString, ...] = (("ie_support", "ie_oppose") if ie else ()) + ADDED_COLUMNS
    # The column names are this module's literals, never a request's, so the SQL is all code.
    return ", ".join(f"{table}.{column}" for column in columns)


def pop_outside_spending(row: dict[str, Any]) -> OutsideSpending:
    """`row`'s outside spending by kind, its added kinds' columns removed from it."""
    added = {column: row.pop(column) for column in ADDED_COLUMNS}
    return OutsideSpending(
        independent_expenditure=SupportOppose(support=row["ie_support"], oppose=row["ie_oppose"]),
        communication_cost=SupportOppose(
            support=added["communication_cost_support"],
            oppose=added["communication_cost_oppose"],
        ),
        party_coordinated=added["party_coordinated"],
        electioneering_communication=added["electioneering"],
    )
