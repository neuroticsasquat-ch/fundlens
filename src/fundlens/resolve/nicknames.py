"""The nickname table the first-name comparison reads (NEU-2188, `nicknames.md`).

`nicknames.csv` is upstream's table, vendored byte-identical: one row per canonical name and a
nickname of it (HAROLD has the nickname HAL). `nicknames-excluded.csv` lists the upstream rows
fundlens refuses, each with its reason (AARON and ERIN are two people). The table is read both
ways and less its exclusions, so HAL is HAROLD's and HAROLD is HAL's; two nicknames of one name
(HAL and HARRY) are not linked by it.
"""

import csv
import io
from functools import cache
from importlib.resources import files as package_files

UPSTREAM = "nicknames.csv"
EXCLUDED = "nicknames-excluded.csv"

_RELATIONSHIP = "has_nickname"


def _rows(text: str, source: str, header: list[str]) -> list[tuple[int, list[str]]]:
    reader = csv.reader(io.StringIO(text))
    if next(reader, None) != header:
        raise ValueError(f"{source}: the header must be {','.join(header)}")
    rows = list(enumerate(reader, start=2))
    for line, row in rows:
        if len(row) != len(header):
            raise ValueError(f"{source} line {line}: {len(row)} fields, not {len(header)}")
    return rows


def _pair(source: str, line: int, name: str, other: str) -> frozenset[str]:
    if not name.strip() or not other.strip():
        raise ValueError(f"{source} line {line}: a name is empty")
    if name.upper() == other.upper():
        raise ValueError(f"{source} line {line}: {name!r} is paired with itself")
    return frozenset((name.upper(), other.upper()))


def _pairs(upstream: str, excluded: str) -> set[tuple[str, str]]:
    rows: set[tuple[str, str]] = set()
    linked: set[frozenset[str]] = set()
    for line, row in _rows(upstream, UPSTREAM, ["name1", "relationship", "name2"]):
        name, relationship, other = row
        if relationship != _RELATIONSHIP:
            raise ValueError(f"{UPSTREAM} line {line}: {relationship!r} is not {_RELATIONSHIP}")
        linked.add(_pair(UPSTREAM, line, name, other))
        rows.add((name, other))
    refused: set[frozenset[str]] = set()
    for line, row in _rows(excluded, EXCLUDED, ["name1", "name2", "reason"]):
        name, other, _ = row
        pair = _pair(EXCLUDED, line, name, other)
        # A stale exclusion is a mistake: the upstream row it was written against has changed.
        if (name, other) not in rows:
            raise ValueError(f"{EXCLUDED} line {line}: {UPSTREAM} has no row {name},{other}")
        if pair in refused:
            raise ValueError(f"{EXCLUDED} line {line}: {name},{other} is excluded twice")
        refused.add(pair)
    return {(a, b) for pair in linked - refused for a in pair for b in pair if a != b}


@cache
def pairs() -> set[tuple[str, str]]:
    """Every (name, other) the table links, both directions, uppercased, less the exclusions."""
    package = package_files("fundlens.resolve")
    return _pairs(package.joinpath(UPSTREAM).read_text(), package.joinpath(EXCLUDED).read_text())
