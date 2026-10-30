"""The seat calendar: every seat up in a cycle, the race universe (spec §5.2).

A race exists from the first day of its cycle, before anyone files for it, so races come from
these vendored tables under `fundlens/fec/seats/` and never from filings. A filing that matches
no seat is reported (`--report`) and recorded in `app.unmatched_filing`; it never creates a race.

- `apportionment.csv` (state, seats, first_cycle): House seats per state from each census since
  1970, from the Census Bureau's historical apportionment table. A census's seats first apply to
  the cycle two years after it (the 2020 census to 2022).
- `senate_classes.csv` (state, class): the two Senate classes each state elects, from senate.gov.
- `delegates.csv` (state, first_cycle, term_years): the non-voting House seats. Puerto Rico's
  resident commissioner serves four years, so is up only in presidential cycles.
- `specials.csv` (cycle, office, state, district, note): hand-maintained, seeded with the Senate
  specials of 2018 to 2026. `cn` does not mark a filing as for a special, so `--report` catches
  a missing one only when it is a Senate special in a state with no regular race that cycle; a
  House special, or one beside a regular race, matches the regular seat and must be added by hand.

`race_id` and `slug` are the M2 shared contract: `{cycle}-{office}-{state}-{district}[-special]`
and `{cycle}/{house|senate|president}/{STATE}[-{DD}][-special]`.
"""

import csv
import io
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from importlib.resources import files as package_files
from pathlib import Path
from typing import Literal

import duckdb
from psycopg import Connection
from psycopg.rows import TupleRow

from fundlens import paths
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2

type Office = Literal["H", "S", "P"]

OFFICE_NAMES: dict[Office, str] = {"H": "house", "S": "senate", "P": "president"}
# The order races are listed and written in.
_OFFICE_ORDER: dict[Office, int] = {"P": 0, "S": 1, "H": 2}

# Federal: the FEC's rules and ids (CONTEXT.md, Jurisdiction).
JURISDICTION = "US"
# The state FEC files a presidential candidate under.
NATIONAL = "US"
# The district of an at-large House seat, a delegate's seat, and every Senate and President seat.
AT_LARGE = "00"

# The first cycle the vendored apportionment covers: the 1970 census's.
FIRST_CYCLE = 1972

_RACE_COLUMNS = (
    "race_id VARCHAR, cycle INTEGER, jurisdiction VARCHAR, office VARCHAR, state VARCHAR,"
    " district VARCHAR, is_special BOOLEAN, slug VARCHAR"
)


@dataclass(frozen=True)
class Race:
    cycle: int
    office: Office
    state: str
    district: str
    is_special: bool = False

    @property
    def seat(self) -> tuple[str, str, str]:
        """What a filing names: (office, state, district)."""
        return (self.office, self.state, self.district)

    @property
    def race_id(self) -> str:
        race_id = f"{self.cycle}-{self.office}-{self.state}-{self.district}"
        return f"{race_id}-special" if self.is_special else race_id

    @property
    def slug(self) -> str:
        # Only a House seat names its district, at-large `00` included.
        place = f"{self.state}-{self.district}" if self.office == "H" else self.state
        special = "-special" if self.is_special else ""
        return f"{self.cycle}/{OFFICE_NAMES[self.office]}/{place}{special}"


@dataclass(frozen=True)
class Filing:
    """One candidate's `cn` row, with the office, state and district as filed."""

    candidate_id: str
    office: str
    state: str
    district: str

    @property
    def seat(self) -> tuple[str, str, str]:
        # FEC pads districts to two digits and files Senate and President as `00`; a blank or
        # unpadded one is read the same way. Anything else is left for the report to show.
        return (self.office, self.state, self.district.strip().zfill(2))


def _read(name: str) -> list[dict[str, str]]:
    text = package_files("fundlens.fec").joinpath("seats", name).read_text()
    return list(csv.DictReader(io.StringIO(text)))


@cache
def _apportionments() -> list[tuple[str, int, int]]:
    return [
        (row["state"], int(row["seats"]), int(row["first_cycle"]))
        for row in _read("apportionment.csv")
    ]


@cache
def _senate_classes() -> dict[str, frozenset[int]]:
    classes: dict[str, set[int]] = {}
    for row in _read("senate_classes.csv"):
        classes.setdefault(row["state"], set()).add(int(row["class"]))
    return {state: frozenset(cls) for state, cls in classes.items()}


@cache
def _delegates() -> list[tuple[str, int, int]]:
    return [
        (row["state"], int(row["first_cycle"]), int(row["term_years"]))
        for row in _read("delegates.csv")
    ]


def _specials() -> list[dict[str, str]]:
    return _read("specials.csv")


def check_cycle(cycle: int) -> None:
    """Raise `ValueError` unless the vendored tables cover `cycle`."""
    if cycle % 2:
        raise ValueError(f"cycle {cycle} is not an even year")
    if cycle < FIRST_CYCLE:
        raise ValueError(f"the seat calendar starts at {FIRST_CYCLE}, not {cycle}")


def house_seats(cycle: int) -> dict[str, int]:
    """Each state's voting House seats under the apportionment in force for `cycle`."""
    check_cycle(cycle)
    in_force: dict[str, tuple[int, int]] = {}
    for state, seats, first_cycle in _apportionments():
        if first_cycle <= cycle and (state not in in_force or first_cycle > in_force[state][1]):
            in_force[state] = (seats, first_cycle)
    return {state: seats for state, (seats, _) in sorted(in_force.items())}


def senate_class(cycle: int) -> int:
    """The Senate class whose regular elections fall in `cycle`."""
    # Class 1 was elected in 2018, class 2 in 2020, class 3 in 2022, and so on every six years.
    return (cycle - 2018) // 2 % 3 + 1


def _districts(seats: int) -> list[str]:
    return [AT_LARGE] if seats == 1 else [f"{n:02d}" for n in range(1, seats + 1)]


def races_for(cycle: int) -> list[Race]:
    """Every race in `cycle`: President, Senate (regular and special), then the House."""
    check_cycle(cycle)
    races: list[Race] = []
    if cycle % 4 == 0:
        races.append(Race(cycle, "P", NATIONAL, AT_LARGE))
    up = senate_class(cycle)
    races += [
        Race(cycle, "S", state, AT_LARGE)
        for state, classes in _senate_classes().items()
        if up in classes
    ]
    for state, seats in house_seats(cycle).items():
        races += [Race(cycle, "H", state, district) for district in _districts(seats)]
    races += [
        Race(cycle, "H", state, AT_LARGE)
        for state, first_cycle, term_years in _delegates()
        if first_cycle <= cycle and cycle % term_years == 0
    ]
    races += _special_races(cycle, {race.seat for race in races})
    return sorted(races, key=lambda r: (_OFFICE_ORDER[r.office], r.state, r.district, r.is_special))


def _special_races(cycle: int, regular: set[tuple[str, str, str]]) -> list[Race]:
    house = {(state, district) for office, state, district in regular if office == "H"}
    specials: list[Race] = []
    for row in _specials():
        if int(row["cycle"]) != cycle:
            continue
        state, district = row["state"], row["district"]
        # A special fills a seat that exists: a Senate seat of a state, or a House district the
        # cycle's apportionment draws. A row naming anything else is a typo in the CSV.
        office: Office
        if row["office"] == "S" and state in _senate_classes() and district == AT_LARGE:
            office = "S"
        elif row["office"] == "H" and (state, district) in house:
            office = "H"
        else:
            raise ValueError(f"specials.csv: {cycle} {row['office']} {state}-{district} is no seat")
        specials.append(Race(cycle, office, state, district, is_special=True))
    ids = [race.race_id for race in specials]
    if len(ids) != len(set(ids)):
        raise ValueError(f"specials.csv: a {cycle} special is listed twice")
    return specials


def write_partition(
    races: Iterable[Race], *, cycle: int, build_id: str, store: R2, data_dir: Path
) -> str:
    """Write the `race` silver partition for one build of `cycle`, locally and to R2; its key."""
    prefix = paths.silver_partition("race", cycle, build_id)
    key = f"{prefix}/{paths.part(0)}"
    local = paths.local_path(data_dir, key)
    local.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        (r.race_id, r.cycle, JURISDICTION, r.office, r.state, r.district, r.is_special, r.slug)
        for r in races
    ]
    with duckdb.connect() as con:
        con.execute(f"CREATE TABLE race ({_RACE_COLUMNS})")
        con.executemany("INSERT INTO race VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        con.table("race").write_parquet(str(local), compression="zstd")
    store.put(key, local)
    return key


def read_filings(cn_zip: bytes, cycle: int) -> list[Filing]:
    """The candidates in a `cn` zip standing in `cycle`.

    The file for a cycle also lists candidates registered for later cycles (a senator up in four
    years) and earlier ones; only a `CAND_ELECTION_YR` of the cycle's even year, or of the odd year
    before it for a special held then, is a filing for one of its seats.
    """
    columns = CATALOGUE["cn"].header()
    at = {name: columns.index(name) for name in columns}
    years = {str(cycle - 1), str(cycle)}
    with zipfile.ZipFile(io.BytesIO(cn_zip)) as archive:
        [member] = archive.namelist()
        # FEC's bulk text is not UTF-8 throughout; latin-1 decodes any byte.
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            # Pipe-delimited and unquoted: a quote in a name is just a character.
            rows = list(csv.reader(text, delimiter="|", quoting=csv.QUOTE_NONE))
    return [
        Filing(
            candidate_id=row[at["CAND_ID"]],
            office=row[at["CAND_OFFICE"]],
            state=row[at["CAND_OFFICE_ST"]],
            district=row[at["CAND_OFFICE_DISTRICT"]],
        )
        for row in rows
        if row and row[at["CAND_ELECTION_YR"]].strip() in years
    ]


def newest_cn(store: R2, cycle: int) -> bytes:
    """The newest bronze `cn` zip for `cycle`. Raises `FileNotFoundError` when there is none."""
    # Keys end in an ISO download date, so key order is download order.
    keys = sorted(store.list_keys(paths.bronze_dir(cycle, "cn")))
    if not keys:
        raise FileNotFoundError(f"no cn file in bronze for {cycle}")
    return store.get(keys[-1])


def unmatched(filings: Iterable[Filing], races: Iterable[Race]) -> list[Filing]:
    """The filings whose (office, state, district) is no seat in `races`."""
    seats = {race.seat for race in races}
    return [filing for filing in filings if filing.seat not in seats]


def record_unmatched(
    conn: Connection[TupleRow], cycle: int, filings: list[Filing], *, seen_at: datetime
) -> None:
    """Make `app.unmatched_filing` hold exactly `filings` for `cycle`.

    A filing already recorded keeps the `seen_at` it was first seen at; one that now matches a
    seat (a special added to the CSV, a district corrected) is removed.
    """
    with conn.transaction():
        conn.execute(
            "DELETE FROM app.unmatched_filing WHERE cycle = %s AND NOT candidate_id = ANY(%s)",
            (cycle, [filing.candidate_id for filing in filings]),
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO app.unmatched_filing"
                " (cycle, candidate_id, office, state, district, seen_at)"
                " VALUES (%s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (cycle, candidate_id) DO UPDATE SET office = EXCLUDED.office,"
                " state = EXCLUDED.state, district = EXCLUDED.district",
                [(cycle, f.candidate_id, f.office, f.state, f.district, seen_at) for f in filings],
            )


@dataclass(frozen=True)
class Seats:
    """What `seats` did: the races written, where, and (with `report`) the unmatched filings."""

    races: list[Race]
    key: str
    unmatched: list[Filing] | None


def seats(
    cycle: int,
    store: R2,
    *,
    build_id: str,
    data_dir: Path,
    conn: Connection[TupleRow] | None = None,
) -> Seats:
    """Generate `cycle`'s seat calendar and write its `race` partition.

    With `conn`, also check the cycle's newest bronze `cn` file against the calendar and record
    the filings that match no seat in `app.unmatched_filing`.
    """
    races = races_for(cycle)
    key = write_partition(races, cycle=cycle, build_id=build_id, store=store, data_dir=data_dir)
    if conn is None:
        return Seats(races, key, None)
    filings = unmatched(read_filings(newest_cn(store, cycle), cycle), races)
    record_unmatched(conn, cycle, filings, seen_at=datetime.now(UTC))
    return Seats(races, key, filings)
