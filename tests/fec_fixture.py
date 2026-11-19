"""The synthetic fixture cycle: readable CSVs in, FEC bulk files out (spec §12).

`tests/fixtures/fec/<cycle>/<file>.csv` holds each bulk file by hand: a header row naming the
entry's columns (for a zip, the vendored FEC header), then the rows, with `#` comment lines
saying which case each block plants. `bulk_body` writes one in FEC's own layout for its format:

- a zip: one member per zip, named as FEC names it for the cycle, pipe-delimited, unquoted, no
  header row (`zips`);
- a CSV: the header row unquoted, every data field double-quoted with `""` for a quote, LF line
  endings (`csv_text`), as FEC's CSVs were on 2026-11-18.

The fake FEC server serves them at the path each entry's `url()` gives, so a test or
`task db:seed` runs the real `extract` on them. `expected.yaml` beside them records what the
pipeline must make of them.

`SAMPLE` and `SAMPLE_UNDATED` are test-only CSV entries, in no catalogue, that render
`fixtures/fec/csv/sample.csv` (NEU-2138): the extract and transform tests of the CSV format.
"""

import csv
import functools
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypedDict, cast

import yaml

from fundlens.fec.files import AMOUNT, CATALOGUE, VARCHAR, BulkFile, FecFile, files_for
from tests.fake_fec import CSV, ZIP, FakeFec, zipped

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CYCLE = 2024

# One fixture row, keyed by FEC column name. Read-only: `read_rows` hands every caller the same
# cached rows, so a test that changed one would change it for every later test.
type Row = Mapping[str, str]


def fixture_dir(cycle: int = CYCLE) -> Path:
    return FIXTURES / "fec" / str(cycle)


def read_file(bulk: BulkFile, path: Path) -> tuple[Row, ...]:
    """The rows of the fixture file at `path` for `bulk`, keyed by column name.

    Raises `ValueError` unless the header row is `bulk.header()` exactly and every row has one
    value per column, and, for a zip, no value holds a `|`: a fixture that drifts from FEC's
    layout fails here, not in a transform.
    """
    lines = [line for line in path.read_text().splitlines() if not line.startswith("#")]
    reader = csv.DictReader(lines)
    columns = bulk.header()
    if reader.fieldnames != columns:
        raise ValueError(f"{path}: header is not the {bulk.name} header")
    rows = list(reader)
    for n, row in enumerate(rows, start=1):
        # DictReader files surplus values under `None` and pads a short row with `None`s.
        if None in row or None in row.values():
            raise ValueError(f"{path}: data row {n} has not {len(columns)} values")
        if bulk.format == "zip" and any("|" in value for value in row.values()):
            raise ValueError(f"{path}: data row {n} holds a `|`, FEC's delimiter")
    return tuple(MappingProxyType(row) for row in rows)


@functools.cache
def read_rows(file: FecFile, directory: Path | None = None) -> tuple[Row, ...]:
    """One catalogued bulk file's rows from `<file>.csv` (`read_file`), keyed by FEC column name.

    Read once per file and directory, then cached (NEU-2267): the tally in
    `tests/unit/test_fec_fixture.py` reads them inside per-row predicates.
    """
    return read_file(CATALOGUE[file], (directory or fixture_dir()) / f"{file}.csv")


def pipe_text(bulk: BulkFile, rows: tuple[Row, ...]) -> str:
    """`rows` as FEC writes a zip's text: pipe-delimited, unquoted, no header row."""
    columns = bulk.header()
    return "".join("|".join(row[column] for column in columns) + "\n" for row in rows)


def csv_text(bulk: BulkFile, rows: tuple[Row, ...]) -> str:
    """`rows` as FEC writes a CSV: the header row unquoted, every data field quoted with `""`
    for a quote, LF line endings."""

    def quoted(value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    columns = bulk.header()
    lines = [",".join(columns), *(",".join(quoted(row[c]) for c in columns) for row in rows)]
    return "".join(line + "\n" for line in lines)


def body_of(bulk: BulkFile, cycle: int, rows: tuple[Row, ...]) -> bytes:
    """`rows` as FEC serves `bulk` for `cycle`: a zip holding its member, or a CSV."""
    if bulk.format == "csv":
        return csv_text(bulk, rows).encode()
    return zipped(bulk.member_for(cycle), pipe_text(bulk, rows))


def bulk_body(bulk: BulkFile, path: Path, cycle: int = CYCLE) -> bytes:
    """The fixture file at `path` as FEC serves `bulk` for `cycle`: a zip, or a CSV."""
    return body_of(bulk, cycle, read_file(bulk, path))


def publish(fec: FakeFec, bulk: BulkFile, cycle: int, body: bytes, **kwargs: str) -> str:
    """Publish `body` as `bulk` for `cycle` at the path its `url()` gives; that path.

    `kwargs` go to `FakeFec.serve_path` (`last_modified`)."""
    content_type = CSV if bulk.format == "csv" else ZIP
    return fec.serve_path(bulk.url("", cycle), body, content_type=content_type, **kwargs)


def bulk_text(file: FecFile, directory: Path | None = None) -> str:
    """`<file>.csv` as FEC writes it: pipe-delimited, unquoted, no header row."""
    return pipe_text(CATALOGUE[file], read_rows(file, directory))


@functools.cache
def body(file: FecFile, cycle: int = CYCLE) -> bytes:
    """`<file>.csv` of the `cycle` fixture as FEC serves it. Built once per file and cycle, then
    cached, as `read_rows` is."""
    return body_of(CATALOGUE[file], cycle, read_rows(file, fixture_dir(cycle)))


def bodies(cycle: int = CYCLE) -> dict[FecFile, bytes]:
    """Every bulk file FEC publishes for `cycle` as FEC serves it (`body`)."""
    return {bulk.name: body(bulk.name, cycle) for bulk in files_for(cycle)}


def serve(fec: FakeFec, cycle: int = CYCLE) -> None:
    """Publish every file of the fixture cycle on the fake FEC server, each at its URL."""
    for name, body in bodies(cycle).items():
        publish(fec, CATALOGUE[name], cycle, body)


# The CSV format's test-only entries (NEU-2138), both rendering `SAMPLE_FILE`: one per cycle in
# the cycle's folder, one undated. Their names are in no `FecFile`.
SAMPLE_FILE = FIXTURES / "fec" / "csv" / "sample.csv"
SAMPLE_COLUMNS = {
    "CMTE_ID": VARCHAR,
    "CMTE_NM": VARCHAR,
    "TTL_RECEIPTS": AMOUNT,
    "COVERAGE_END_DT": VARCHAR,
}
SAMPLE = BulkFile(
    cast(FecFile, "sample"),
    1980,
    None,
    SAMPLE_COLUMNS,
    format="csv",
    url_pattern="{yyyy}/sample_{yyyy}.csv",
)
SAMPLE_UNDATED = BulkFile(
    cast(FecFile, "sample_undated"),
    1980,
    None,
    SAMPLE_COLUMNS,
    format="csv",
    url_pattern="data.fec.gov/sample.csv",
)


class RaceTotals(TypedDict):
    candidate_count: int
    total_individual: int
    total_committee: int
    total_jfc_transfers: int
    ie_support: int
    ie_oppose: int


class CandidateTotals(TypedDict):
    race_id: str | None
    total_individual: int
    total_committee: int
    total_jfc_transfers: int
    self_funding: int
    ie_support: int
    ie_oppose: int


class CommitteeTotals(TypedDict):
    total_individual: int
    self_funding: int
    total_from_committees: int
    total_to_candidates: int
    ie_total: int


class OrganizationReceipts(TypedDict):
    keys: dict[int, str]
    by_key: dict[str, int]
    by_committee: dict[str, int]
    total_amount: int
    # Per committee, by rank: [organization_key, name, amount] (NEU-2133).
    top_by_committee: dict[str, list[list[str | int]]]
    classified: list[int]


class NonContributionAccount(TypedDict):
    contributions: list[int]
    organization_receipts: list[int]
    by_committee: dict[str, int]
    organizations_by_committee: dict[str, int]


class OtherLines(TypedDict):
    contributions: list[int]
    organization_receipts: list[int]
    by_committee: dict[str, int]
    organizations_by_committee: dict[str, int]


class ReturnedByCandidates(TypedDict):
    disbursements: list[int]
    by_committee: dict[str, int]


class Refunds(TypedDict):
    contributions: list[int]
    organization_receipts: list[int]
    by_committee: dict[str, int]


class Donor(TypedDict):
    bonica_cid: int
    resolved_by: str
    amount: int
    sub_ids: list[int]


class Attributions(TypedDict):
    jfc_committee: dict[int, str | None]
    attribution_only: list[int]


class Scores(TypedDict):
    precision: float
    recall: float


class TopScores(Scores):
    limit: int


class Validation(TypedDict):
    dime_version: str
    matched_rows: int
    labelled_keys: int
    overall: Scores
    top: TopScores


class ReportedTotals(TypedDict):
    # The values each row lists, in silver column order after the key.
    columns: list[str]
    # By cycle, then committee or candidate id: one row of `columns`' values.
    reported_total: dict[int, dict[str, list[Any]]]
    candidate_reported_total: dict[int, dict[str, list[Any]]]


class GoldReported(TypedDict):
    # Per committee: [itemized_total, reported_individual_itemized, reported_cash_on_hand_end,
    # coverage]; per candidate: [reported_receipts, reported_cash_on_hand_end, itemized_total,
    # coverage, reported_includes_converted_committee].
    committees: dict[str, list[Any]]
    candidates: dict[str, list[Any]]
    # Per race: reported_cash_on_hand.
    races: dict[str, int | None]
    # Per committee: [measure, fundlens, reported, ratio].
    reconciliation: dict[str, list[Any]]
    # Per candidate, then bucket: [amount, donors].
    gift_sizes: dict[str, dict[str, list[int | None]]]


class Expected(TypedDict):
    cycle: int
    rows: dict[str, int]
    silver: dict[str, int]
    contributions: dict[str, Any]
    organization_receipts: OrganizationReceipts
    non_contribution_account: NonContributionAccount
    other_lines: OtherLines
    returned_by_candidates: ReturnedByCandidates
    refunds: Refunds
    name_matched: dict[int, str | None]
    # Ranked rows: [recipient_kind, recipient_id, amount] per giver, [kind, committee_id, amount]
    # per race.
    top_recipients: dict[str, list[list[str | int]]]
    race_top_committees: dict[str, list[list[str | int]]]
    unmatched_filings: list[str]
    aliases: dict[str, str]
    races: dict[str, RaceTotals]
    candidates: dict[str, CandidateTotals]
    committees: dict[str, CommitteeTotals]
    donors: dict[str, Donor]
    distinct_donors: int
    attributions: Attributions
    validation: Validation
    reported_totals: ReportedTotals
    gold_reported: GoldReported


@functools.cache
def expected(cycle: int = CYCLE) -> Expected:
    """The cycle's `expected.yaml`: the totals, counts and donor groupings the fixture plants.
    Read once, then cached (NEU-2267): every caller shares it, so none may change it."""
    return cast(Expected, yaml.safe_load((fixture_dir(cycle) / "expected.yaml").read_text()))
