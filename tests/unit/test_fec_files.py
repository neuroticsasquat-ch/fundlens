"""The FEC bulk file catalogue and its vendored headers (spec §4)."""

import io
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, cast, get_args

import pytest

from fundlens import paths
from fundlens.fec.files import (
    AMOUNT,
    CATALOGUE,
    COUNT,
    CSV_HEADER_BYTES,
    FILE_NUM,
    SUB_ID,
    VARCHAR,
    YEAR,
    BulkFile,
    FecFile,
    current_cycle,
    files_for,
    read_csv_header,
)

BASE = "https://www.fec.gov/files/bulk-downloads"
COLUMNS = {"CMTE_ID": VARCHAR, "TTL_RECEIPTS": AMOUNT}


def csv_entry(**fields: Any) -> BulkFile:
    """A CSV entry named `sample`, with `fields` in place of the defaults."""
    defaults: dict[str, Any] = {
        "member": None,
        "format": "csv",
        "url_pattern": "{yyyy}/sample_{yyyy}.csv",
    }
    return BulkFile(cast(FecFile, "sample"), 1980, columns=COLUMNS, **(defaults | fields))


def test_every_file_name_has_a_catalogue_entry() -> None:
    assert list(CATALOGUE) == list(get_args(FecFile))
    assert all(name == file.name for name, file in CATALOGUE.items())


@pytest.mark.parametrize("name", get_args(FecFile))
def test_the_vendored_header_names_the_catalogued_columns(name: FecFile) -> None:
    # The vendored copies are what `task fec:headers --check` compares with FEC's live ones, so
    # this holds the catalogue to the live dictionaries.
    file = CATALOGUE[name]

    header = file.header()

    assert len(header) == len(file.columns)
    assert header == list(file.columns)


@pytest.mark.parametrize(
    ("name", "cycle", "url"),
    [
        ("indiv", 2024, f"{BASE}/2024/indiv24.zip"),
        ("pas2", 2026, f"{BASE}/2026/pas226.zip"),
        ("ccl", 2000, f"{BASE}/2000/ccl00.zip"),
        ("cm", 1980, f"{BASE}/1980/cm80.zip"),
        ("weball", 1980, f"{BASE}/1980/weball80.zip"),
        ("webk", 2024, f"{BASE}/2024/webk24.zip"),
        ("committee_summary", 2008, f"{BASE}/2008/committee_summary_2008.csv"),
        ("oppexp", 2004, f"{BASE}/2004/oppexp04.zip"),
        # The 24/48-hour file keeps FEC's name in its URL, not the catalogue's (NEU-2164).
        ("ie_24_48", 2024, f"{BASE}/2024/independent_expenditure_2024.csv"),
        ("ElectioneeringComm", 2010, f"{BASE}/2010/ElectioneeringComm_2010.csv"),
        ("CommunicationCosts", 2024, f"{BASE}/2024/CommunicationCosts_2024.csv"),
        # Under `data.fec.gov/`: the leadership file per cycle, the lobbyist files undated, one
        # URL for every cycle (NEU-2174).
        ("leadership", 2010, f"{BASE}/data.fec.gov/leadership2010.csv"),
        ("leadership", 2024, f"{BASE}/data.fec.gov/leadership2024.csv"),
        ("lobbyist", 2010, f"{BASE}/data.fec.gov/lobbyist.csv"),
        ("lobbyist", 2024, f"{BASE}/data.fec.gov/lobbyist.csv"),
        ("lobbyist_bundle", 2024, f"{BASE}/data.fec.gov/lobbyist_bundle.csv"),
        ("lobbyist_bundle", 2026, f"{BASE}/data.fec.gov/lobbyist_bundle.csv"),
    ],
)
def test_a_files_url_follows_fecs_pattern(name: FecFile, cycle: int, url: str) -> None:
    assert CATALOGUE[name].url(BASE, cycle) == url
    assert CATALOGUE[name].url(BASE + "/", cycle) == url


@pytest.mark.parametrize(
    ("name", "first_cycle"),
    [
        ("cm", 1980),
        ("cn", 1980),
        ("ccl", 2000),
        ("indiv", 1980),
        ("pas2", 1980),
        ("oth", 1980),
        # Every-FEC-dollar spec §3.1: the earliest range FEC's bulk-data page links.
        ("weball", 1980),
        ("webk", 1996),
        ("committee_summary", 2008),
        # FEC publishes operating expenditures from 2004 (every-FEC-dollar spec §3.1).
        ("oppexp", 2004),
        # The outside-spending files, as FEC's bulk-data page linked them on 2026-11-18.
        ("ie_24_48", 2010),
        ("ElectioneeringComm", 2010),
        ("CommunicationCosts", 2010),
        # The leadership file from 2010 (2008's is a 404), and the two undated files from 2010,
        # though they hold filings from 2009 (every-FEC-dollar spec §3.1, §7.1).
        ("leadership", 2010),
        ("lobbyist", 2010),
        ("lobbyist_bundle", 2010),
    ],
)
def test_each_files_first_cycle_is_the_first_fec_publishes(name: FecFile, first_cycle: int) -> None:
    assert CATALOGUE[name].first_cycle == first_cycle
    assert CATALOGUE[name] not in files_for(first_cycle - 2)
    assert CATALOGUE[name] in files_for(first_cycle)


def test_files_for_leaves_out_files_fec_did_not_yet_publish() -> None:
    assert [file.name for file in files_for(1994)] == ["cm", "cn", "indiv", "pas2", "oth", "weball"]
    assert [file.name for file in files_for(1998)] == [
        "cm",
        "cn",
        "indiv",
        "pas2",
        "oth",
        "weball",
        "webk",
    ]
    assert [file.name for file in files_for(2004)] == [
        "cm",
        "cn",
        "ccl",
        "indiv",
        "pas2",
        "oth",
        "weball",
        "webk",
        "oppexp",
    ]
    assert [file.name for file in files_for(2008)] == [
        "cm",
        "cn",
        "ccl",
        "indiv",
        "pas2",
        "oth",
        "weball",
        "webk",
        "committee_summary",
        "oppexp",
    ]
    assert [file.name for file in files_for(2010)] == list(get_args(FecFile))
    assert list(get_args(FecFile))[-6:] == [
        "ie_24_48",
        "ElectioneeringComm",
        "CommunicationCosts",
        "leadership",
        "lobbyist",
        "lobbyist_bundle",
    ]


@pytest.mark.parametrize(
    ("name", "cycle", "member"),
    [
        ("cm", 2024, "cm.txt"),
        ("indiv", 1980, "itcont.txt"),
        ("weball", 1980, "weball80.txt"),
        ("weball", 2024, "weball24.txt"),
        ("webk", 2000, "webk00.txt"),
        ("oppexp", 2024, "oppexp.txt"),
    ],
)
def test_a_zips_member_is_named_for_its_cycle_where_fecs_is(
    name: FecFile, cycle: int, member: str
) -> None:
    assert CATALOGUE[name].member_for(cycle) == member


def test_oppexp_has_its_25_columns_four_of_them_typed() -> None:
    columns = CATALOGUE["oppexp"].columns

    assert len(columns) == 25
    typed = {"RPT_YR": YEAR, "TRANSACTION_AMT": AMOUNT, "SUB_ID": SUB_ID, "FILE_NUM": FILE_NUM}
    assert {name: kind for name, kind in columns.items() if kind != VARCHAR} == typed


@pytest.mark.parametrize(
    ("name", "count", "typed"),
    [
        (
            "ie_24_48",
            23,
            {
                "exp_amo": AMOUNT,
                "agg_amo": AMOUNT,
                "file_num": FILE_NUM,
                "fec_election_yr": YEAR,
                "prev_file_num": FILE_NUM,
            },
        ),
        (
            "ElectioneeringComm",
            19,
            {
                "REPORTED_DISBURSEMENT_AMOUNT": AMOUNT,
                "NUMBER_OF_CANDIDATES": COUNT,
                "CALCULATED_CANDIDATE_SHARE": AMOUNT,
            },
        ),
        (
            "CommunicationCosts",
            25,
            {"TRANSACTION_AMT": AMOUNT, "SUB_ID": SUB_ID, "FILE_NUM": FILE_NUM, "RPT_YR": YEAR},
        ),
    ],
)
def test_the_outside_spending_csvs_have_their_columns_typed(
    name: FecFile, count: int, typed: dict[str, str]
) -> None:
    file = CATALOGUE[name]

    assert file.format == "csv"
    assert file.member is None
    assert len(file.columns) == count
    assert {column: kind for column, kind in file.columns.items() if kind != VARCHAR} == typed


@pytest.mark.parametrize(
    ("name", "columns"),
    [
        (
            "leadership",
            {
                "Committee_Id": VARCHAR,
                "Committee_Name": VARCHAR,
                "Link_Image": VARCHAR,
                "Sponsor_Name": VARCHAR,
                "Cash_on_Hand": AMOUNT,
                "Coverage_End_Date": VARCHAR,
                "Total_Disbursement": AMOUNT,
                "Total_Receipt": AMOUNT,
            },
        ),
        (
            "lobbyist",
            {
                "Link_Image": VARCHAR,
                "Committee_Name": VARCHAR,
                "Committee_Id": VARCHAR,
                "Date_Filed": VARCHAR,
                "Is_Lobbyist": VARCHAR,
            },
        ),
        (
            "lobbyist_bundle",
            {
                "Committee_Id": VARCHAR,
                "Committee_Name": VARCHAR,
                "Link_Image": VARCHAR,
                "Committee_Election_State": VARCHAR,
                "Committee_Election_District": VARCHAR,
                "Report_Type": VARCHAR,
                "Receipt_Date": VARCHAR,
                "Coverage_Start_Date": VARCHAR,
                "Coverage_End_Date": VARCHAR,
                "Quarterly_Contribution": AMOUNT,
                "Semi_Annual_Contribution": AMOUNT,
            },
        ),
    ],
)
def test_the_leadership_and_lobbyist_csvs_have_their_header_rows_columns(
    name: FecFile, columns: dict[str, str]
) -> None:
    # Each header row as FEC served it on 2026-11-25, in order (leadership-lobbyist measurement
    # Q1, NEU-2174); dates stay VARCHAR, DD-MON-YY.
    file = CATALOGUE[name]

    assert file.format == "csv"
    assert file.member is None
    assert list(file.columns.items()) == list(columns.items())


def test_communication_costs_has_the_transaction_key_and_the_other_two_do_not() -> None:
    # The key `transform.runner._drop_fec_repeats` reads a repeated row once by.
    key = {"CMTE_ID", "FILE_NUM", "TRAN_ID", "SUB_ID"}

    assert key <= CATALOGUE["CommunicationCosts"].columns.keys()
    assert not key <= CATALOGUE["ie_24_48"].columns.keys()
    assert not key <= CATALOGUE["ElectioneeringComm"].columns.keys()


def test_no_entrys_view_is_named_as_a_silver_table_or_another_entrys_views() -> None:
    # A file's view is named for its entry, beside silver's tables in one DuckDB schema, and an
    # itemized file's `<name>_published` and `<name>_repeat` beside it: DuckDB refuses a table
    # named as a view (`independent_expenditure`, NEU-2164). DuckDB's names ignore case.
    entries = [name.lower() for name in CATALOGUE]
    silver = {table.lower() for table in get_args(paths.SilverTable)}
    derived = {f"{name}{suffix}" for name in entries for suffix in ("_published", "_repeat")}

    assert len(set(entries)) == len(entries)
    assert not set(entries) & silver
    assert not set(entries) & derived
    assert not derived & silver


def test_only_oppexp_has_a_trailing_delimiter() -> None:
    assert [file.name for file in CATALOGUE.values() if file.trailing_delimiter] == ["oppexp"]


def test_a_csv_has_no_member() -> None:
    with pytest.raises(ValueError, match="not a zip"):
        CATALOGUE["committee_summary"].member_for(2024)


@pytest.mark.parametrize(
    ("today", "cycle"),
    [
        (date(2026, 10, 30), 2026),
        (date(2026, 12, 31), 2026),
        (date(2027, 1, 1), 2028),
        (date(2028, 11, 5), 2028),
    ],
)
def test_the_current_cycle_is_the_next_even_year(today: date, cycle: int) -> None:
    assert current_cycle(today) == cycle


@pytest.mark.parametrize(
    ("pattern", "cycle", "url"),
    [
        ("{yyyy}/committee_summary_{yyyy}.csv", 2024, f"{BASE}/2024/committee_summary_2024.csv"),
        ("data.fec.gov/leadership{yyyy}.csv", 2010, f"{BASE}/data.fec.gov/leadership2010.csv"),
        ("data.fec.gov/lobbyist.csv", 2024, f"{BASE}/data.fec.gov/lobbyist.csv"),
        ("data.fec.gov/lobbyist.csv", 2026, f"{BASE}/data.fec.gov/lobbyist.csv"),
        ("{yyyy}/sample{yy}.csv", 2000, f"{BASE}/2000/sample00.csv"),
    ],
)
def test_a_csvs_url_renders_its_pattern(pattern: str, cycle: int, url: str) -> None:
    file = csv_entry(url_pattern=pattern)

    assert file.url(BASE, cycle) == url
    assert file.url(BASE + "/", cycle) == url


def test_a_zip_with_a_pattern_renders_it() -> None:
    file = BulkFile(
        cast(FecFile, "webk"), 1996, "webk.txt", COLUMNS, url_pattern="{yyyy}/webk{yy}.zip"
    )

    assert file.url(BASE, 2024) == f"{BASE}/2024/webk24.zip"


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"format": "zip", "member": None, "url_pattern": None}, "member"),
        ({"member": "sample.txt"}, "no member"),
        ({"split_dir": "by_date/"}, "no member or split"),
        ({"url_pattern": None}, "URL pattern"),
        ({"url_pattern": ""}, "URL pattern"),
        ({"url_pattern": "{cycle}/sample.csv"}, "only"),
        ({"url_pattern": "{}/sample.csv"}, "only"),
        ({"url_pattern": "{yy:03d}/sample.csv"}, "only"),
        ({"url_pattern": "{yyyy!r}/sample.csv"}, "only"),
        ({"header_from_fec": False}, "header row"),
        ({"trailing_delimiter": True}, "no trailing delimiter"),
        ({"format": "zip", "member": "sample{cycle}.txt", "url_pattern": None}, "only"),
    ],
)
def test_an_entry_that_cannot_work_is_refused_when_made(
    fields: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        csv_entry(**fields)


def test_a_csvs_header_is_its_columns_and_it_has_no_header_file() -> None:
    file = csv_entry()

    assert file.header_file is None
    assert file.header() == ["CMTE_ID", "TTL_RECEIPTS"]
    assert CATALOGUE["cm"].header_file == "cm_header_file.csv"


def test_only_the_summary_zips_headers_are_not_fecs_header_files() -> None:
    # FEC publishes no header file for either (a 404 on 2026-11-05): `task fec:headers` skips
    # them, and their vendored columns are FEC's file descriptions'.
    assert [file.name for file in CATALOGUE.values() if not file.header_from_fec] == [
        "weball",
        "webk",
    ]
    assert CATALOGUE["weball"].header_file == "weball_header_file.csv"
    assert CATALOGUE["webk"].header_file == "webk_header_file.csv"


@pytest.mark.parametrize(
    ("body", "header"),
    [
        (b'CMTE_ID,TTL_RECEIPTS\n"C00000001","1.00"\n', ["CMTE_ID", "TTL_RECEIPTS"]),
        (b"CMTE_ID,TTL_RECEIPTS", ["CMTE_ID", "TTL_RECEIPTS"]),
        (b"CMTE_ID,TTL_RECEIPTS\r\n", ["CMTE_ID", "TTL_RECEIPTS"]),
        # A BOM is kept, so the header is not the catalogued one.
        (b"\xef\xbb\xbfCMTE_ID,TTL_RECEIPTS\n", ["\ufeffCMTE_ID", "TTL_RECEIPTS"]),
        (b"", []),
        (b"x" * CSV_HEADER_BYTES + b"\n", []),
    ],
)
def test_read_csv_header_reads_the_first_line(
    tmp_path: Path, body: bytes, header: list[str]
) -> None:
    path = tmp_path / "file.csv"
    path.write_bytes(body)

    assert read_csv_header(path) == header


def test_read_csv_header_of_a_zip_is_no_entrys_columns(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("cm.txt", "C00000001|NAME\n" * 100)
    path = tmp_path / "cm.zip"
    path.write_bytes(buffer.getvalue())

    assert read_csv_header(path) != list(COLUMNS)
