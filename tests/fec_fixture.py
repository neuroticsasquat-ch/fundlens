"""The synthetic fixture cycle: readable CSVs in, FEC bulk zips out (spec §12).

`tests/fixtures/fec/<cycle>/<file>.csv` holds each bulk file by hand: a header row naming the
vendored FEC columns, then the rows, with `#` comment lines saying which case each block plants.
`zips` writes them in FEC's own layout (one member per zip, pipe-delimited, unquoted, no header
row) for the fake FEC server to serve, so a test or `task db:seed` runs the real `extract` on
them. `expected.yaml` beside them records what the pipeline must make of them.
"""

import csv
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml

from fundlens.fec.files import CATALOGUE, FecFile, files_for
from tests.fake_fec import FakeFec, zipped

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CYCLE = 2024

# The one member each FEC bulk zip holds.
MEMBERS: dict[FecFile, str] = {
    "cm": "cm.txt",
    "cn": "cn.txt",
    "ccl": "ccl.txt",
    "indiv": "itcont.txt",
    "pas2": "itpas2.txt",
    "oth": "itoth.txt",
}


def fixture_dir(cycle: int = CYCLE) -> Path:
    return FIXTURES / "fec" / str(cycle)


def read_rows(file: FecFile, directory: Path | None = None) -> list[dict[str, str]]:
    """One bulk file's rows from `<file>.csv`, keyed by FEC column name.

    Raises `ValueError` unless the header row is the vendored header exactly and every row has
    one value per column: a fixture that drifts from FEC's layout fails here, not in a transform.
    """
    path = (directory or fixture_dir()) / f"{file}.csv"
    lines = [line for line in path.read_text().splitlines() if not line.startswith("#")]
    reader = csv.DictReader(lines)
    columns = CATALOGUE[file].header()
    if reader.fieldnames != columns:
        raise ValueError(f"{path}: header is not the vendored {file} header")
    rows = list(reader)
    for n, row in enumerate(rows, start=1):
        # DictReader files surplus values under `None` and pads a short row with `None`s.
        if None in row or None in row.values():
            raise ValueError(f"{path}: data row {n} has not {len(columns)} values")
        if any("|" in value for value in row.values()):
            raise ValueError(f"{path}: data row {n} holds a `|`, FEC's delimiter")
    return rows


def bulk_text(file: FecFile, directory: Path | None = None) -> str:
    """`<file>.csv` as FEC writes it: pipe-delimited, unquoted, no header row."""
    columns = CATALOGUE[file].header()
    return "".join(
        "|".join(row[column] for column in columns) + "\n" for row in read_rows(file, directory)
    )


def zips(cycle: int = CYCLE) -> dict[FecFile, bytes]:
    """Every bulk zip FEC publishes for `cycle`, built from its fixture CSVs."""
    return {
        bulk.name: zipped(MEMBERS[bulk.name], bulk_text(bulk.name, fixture_dir(cycle)))
        for bulk in files_for(cycle)
    }


def serve(fec: FakeFec, cycle: int = CYCLE) -> None:
    """Publish the fixture cycle's zips on the fake FEC server."""
    for name, body in zips(cycle).items():
        fec.serve(cycle, name, body)


class RaceTotals(TypedDict):
    candidate_count: int
    total_individual: int
    total_committee: int
    ie_support: int
    ie_oppose: int


class CandidateTotals(TypedDict):
    race_id: str | None
    total_individual: int
    total_committee: int
    self_funding: int
    ie_support: int
    ie_oppose: int


class CommitteeTotals(TypedDict):
    total_individual: int
    self_funding: int
    total_from_committees: int
    total_to_candidates: int
    ie_total: int


class Donor(TypedDict):
    bonica_cid: int
    resolved_by: str
    amount: int
    sub_ids: list[int]


class Expected(TypedDict):
    cycle: int
    rows: dict[str, int]
    silver: dict[str, int]
    contributions: dict[str, Any]
    unmatched_filings: list[str]
    races: dict[str, RaceTotals]
    candidates: dict[str, CandidateTotals]
    committees: dict[str, CommitteeTotals]
    donors: dict[str, Donor]
    distinct_donors: int


def expected(cycle: int = CYCLE) -> Expected:
    """The cycle's `expected.yaml`: the totals, counts and donor groupings the fixture plants."""
    return cast(Expected, yaml.safe_load((fixture_dir(cycle) / "expected.yaml").read_text()))
