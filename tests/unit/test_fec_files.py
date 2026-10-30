"""The FEC bulk file catalogue and its vendored headers (spec §4)."""

from datetime import date
from typing import get_args

import pytest

from fundlens.fec.files import CATALOGUE, FecFile, current_cycle, files_for

BASE = "https://www.fec.gov/files/bulk-downloads"


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
