"""The FEC bulk file catalogue and its vendored headers (spec §4)."""

import io
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, cast, get_args

import pytest

from fundlens.fec.files import (
    AMOUNT,
    CATALOGUE,
    CSV_HEADER_BYTES,
    VARCHAR,
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
    ],
)
def test_a_files_url_follows_fecs_pattern(name: FecFile, cycle: int, url: str) -> None:
    assert CATALOGUE[name].url(BASE, cycle) == url
    assert CATALOGUE[name].url(BASE + "/", cycle) == url


def test_files_for_leaves_out_files_fec_did_not_yet_publish() -> None:
    assert [file.name for file in files_for(1998)] == ["cm", "cn", "indiv", "pas2", "oth"]
    assert [file.name for file in files_for(2000)] == list(get_args(FecFile))


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
