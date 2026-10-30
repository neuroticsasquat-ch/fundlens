"""The seat calendar (spec §5.2): seat counts, Senate classes, specials, `race_id` and `slug`."""

from collections import Counter
from pathlib import Path

import pytest

from fundlens.transform import seats
from fundlens.transform.seats import Filing, Race
from tests.fake_fec import zipped

CN_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/fec/2026/cn.txt"

# Seats of the states each census moved most, from the 1970 census's (in force 1972–1980) to the
# 2020 census's (from 2022), with Montana's at-large seat splitting in 2022.
EXPECTED_HOUSE = {
    1980: {"CA": 43, "TX": 24, "NY": 39, "FL": 15, "MT": 2},
    1982: {"CA": 45, "TX": 27, "NY": 34, "FL": 19, "MT": 2},
    1992: {"CA": 52, "TX": 30, "NY": 31, "FL": 23, "MT": 1},
    2002: {"CA": 53, "TX": 32, "NY": 29, "FL": 25, "MT": 1},
    2012: {"CA": 53, "TX": 36, "NY": 27, "FL": 27, "MT": 1},
    2022: {"CA": 52, "TX": 38, "NY": 26, "FL": 28, "MT": 2},
}


def counts(cycle: int) -> Counter[str]:
    """Races by kind: `voting`, `delegate`, `senate`, `senate-special`, `president`."""
    delegates = {"AS", "DC", "GU", "MP", "PR", "VI"}
    kinds: Counter[str] = Counter()
    for race in seats.races_for(cycle):
        if race.office == "H":
            kinds["delegate" if race.state in delegates else "voting"] += 1
        elif race.office == "S":
            kinds["senate-special" if race.is_special else "senate"] += 1
        else:
            kinds["president"] += 1
    return kinds


@pytest.mark.parametrize("cycle", range(1980, 2028, 2))
def test_every_cycle_has_435_voting_house_seats(cycle: int) -> None:
    assert sum(seats.house_seats(cycle).values()) == 435
    assert counts(cycle)["voting"] == 435
    assert len(seats.house_seats(cycle)) == 50


@pytest.mark.parametrize("cycle", range(1980, 2028, 2))
def test_each_cycle_follows_the_reapportionment_in_force(cycle: int) -> None:
    in_force = max(first for first in EXPECTED_HOUSE if first <= cycle)
    house = seats.house_seats(cycle)

    assert {state: house[state] for state in EXPECTED_HOUSE[in_force]} == EXPECTED_HOUSE[in_force]


@pytest.mark.parametrize(
    ("cycle", "delegates"),
    # Puerto Rico's commissioner is elected every four years; the Northern Marianas from 2008.
    [(1980, 5), (1982, 4), (2006, 4), (2008, 6), (2010, 5), (2024, 6), (2026, 5)],
)
def test_delegate_seats(cycle: int, delegates: int) -> None:
    assert counts(cycle)["delegate"] == delegates


def test_2024_has_every_house_seat_35_senate_races_and_president() -> None:
    races = {race.slug: race for race in seats.races_for(2024)}

    assert counts(2024) == {
        "voting": 435,
        "delegate": 6,
        # Class 1's 33 seats, and the California and Nebraska specials.
        "senate": 33,
        "senate-special": 2,
        "president": 1,
    }
    assert races["2024/house/MD-05"].race_id == "2024-H-MD-05"
    assert races["2024/senate/MD"].race_id == "2024-S-MD-00"
    assert races["2024/senate/NE-special"].race_id == "2024-S-NE-00-special"
    assert races["2024/president/US"].race_id == "2024-P-US-00"
    assert races["2024/house/AK-00"].district == "00"
    assert races["2024/house/PR-00"].office == "H"


def test_race_ids_and_slugs_are_unique_in_every_cycle() -> None:
    for cycle in range(1980, 2028, 2):
        races = seats.races_for(cycle)
        assert len({race.race_id for race in races}) == len(races)
        assert len({race.slug for race in races}) == len(races)


def test_president_is_up_only_every_fourth_year() -> None:
    assert [cycle for cycle in range(1980, 2028, 2) if counts(cycle)["president"]] == list(
        range(1980, 2028, 4)
    )


def test_senate_classes_rotate_every_six_years() -> None:
    assert [seats.senate_class(cycle) for cycle in (1980, 1982, 1984, 2018, 2020, 2022, 2024)] == [
        3,
        1,
        2,
        1,
        2,
        3,
        1,
    ]
    # Over any three consecutive cycles every state elects both its senators, once each.
    for start in (1980, 2020, 2022):
        up = Counter(
            race.state
            for cycle in (start, start + 2, start + 4)
            for race in seats.races_for(cycle)
            if race.office == "S" and not race.is_special
        )
        assert len(up) == 50
        assert set(up.values()) == {2}
    assert [counts(cycle)["senate"] for cycle in (2018, 2020, 2022)] == [33, 33, 34]


def test_montana_regains_its_second_district_in_2022() -> None:
    def districts(cycle: int, state: str) -> list[str]:
        return [r.district for r in seats.races_for(cycle) if r.office == "H" and r.state == state]

    assert districts(2020, "MT") == ["00"]
    assert districts(2022, "MT") == ["01", "02"]
    assert districts(2020, "WV") == ["01", "02", "03"]
    assert districts(2022, "WV") == ["01", "02"]
    assert "2022/house/MT-01" in {race.slug for race in seats.races_for(2022)}


def test_a_special_beside_the_regular_race_for_the_same_state() -> None:
    california = [r for r in seats.races_for(2022) if r.office == "S" and r.state == "CA"]

    assert [(r.race_id, r.slug) for r in california] == [
        ("2022-S-CA-00", "2022/senate/CA"),
        ("2022-S-CA-00-special", "2022/senate/CA-special"),
    ]


def test_a_house_special_names_its_district() -> None:
    assert Race(2024, "H", "NY", "03", is_special=True).slug == "2024/house/NY-03-special"


def test_a_special_naming_no_seat_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    def specials() -> list[dict[str, str]]:
        return [{"cycle": "2024", "office": "H", "state": "MD", "district": "09", "note": ""}]

    monkeypatch.setattr(seats, "_specials", specials)

    with pytest.raises(ValueError, match="2024 H MD-09 is no seat"):
        seats.races_for(2024)


@pytest.mark.parametrize("cycle", [2025, 1970])
def test_a_cycle_the_tables_do_not_cover_is_refused(cycle: int) -> None:
    with pytest.raises(ValueError):
        seats.races_for(cycle)


def test_read_filings_keeps_the_cycles_candidates_only() -> None:
    filings = seats.read_filings(zipped("cn.txt", CN_FIXTURE.read_text()), 2026)

    # The 2028 senator and presidential candidate are standing in a later cycle.
    assert [filing.candidate_id for filing in filings] == [
        "H6MD05101",
        "H6MD09102",
        "H6AK00103",
        "H6DC00104",
        "S6GA00105",
        "S6OH00106",
    ]
    assert filings[1] == Filing("H6MD09102", "H", "MD", "09")


def test_only_a_filing_for_no_seat_is_unmatched() -> None:
    races = seats.races_for(2026)
    filings = [
        Filing("H6MD05101", "H", "MD", "05"),
        Filing("H6MD09102", "H", "MD", "09"),
        # An unpadded district is still district 5; a blank Senate one is still `00`.
        Filing("H6MD05109", "H", "MD", "5"),
        Filing("S6OH00106", "S", "OH", ""),
        # 2026 elects class 2, which Maryland is not in, and has no presidential race.
        Filing("S6MD00110", "S", "MD", "00"),
        Filing("P60000111", "P", "US", "00"),
    ]

    assert [f.candidate_id for f in seats.unmatched(filings, races)] == [
        "H6MD09102",
        "S6MD00110",
        "P60000111",
    ]
