"""Gold's `reported_*` columns as the API's `reported` objects (every-FEC-dollar spec §4.4).

`committee_cycle` and `candidate_cycle` carry reported totals flat, one `reported_<field>` column
each; a response nests them under `reported`, which is None where FEC's files have no row
(`reported_source_file` NULL). A row's single missing measure stays None inside the object: the
rest are still reported totals worth returning (NEU-2145).
"""

from typing import Any, LiteralString, cast

from fundlens.api.schemas import RaceCandidateReported, ReportedTotals

REPORTED_FIELDS = tuple(ReportedTotals.model_fields)
RACE_CANDIDATE_REPORTED_FIELDS = tuple(RaceCandidateReported.model_fields)


def reported_columns(
    table: LiteralString, fields: tuple[str, ...] = REPORTED_FIELDS
) -> LiteralString:
    """`table`'s `reported_<field>` columns, for a SELECT list."""
    # The field names are the schemas' own, never a request's, so the SQL is still all code.
    return cast(LiteralString, ", ".join(f"{table}.reported_{field}" for field in fields))


def pop_reported(row: dict[str, Any]) -> ReportedTotals | None:
    """`row`'s `reported_<field>` values, removed from it, as a `ReportedTotals`."""
    values = {field: row.pop(f"reported_{field}") for field in REPORTED_FIELDS}
    return None if values["source_file"] is None else ReportedTotals(**values)


def pop_race_candidate_reported(row: dict[str, Any]) -> RaceCandidateReported | None:
    """`row`'s `reported_<field>` values, removed from it, as a `RaceCandidateReported`."""
    values = {field: row.pop(f"reported_{field}") for field in RACE_CANDIDATE_REPORTED_FIELDS}
    return None if values["source_file"] is None else RaceCandidateReported(**values)
