"""The Splink model of spec §6.3 and the clusters of §6.4, on contributors made up here.

The fixture cycle is too small to train on (`model.train`), so training is tested on a
synthetic population large enough for random sampling and EM to mean something: donors with one
to three contributor keys each, a later key reporting another occupation, no employer, or a
neighbouring ZIP.
"""

import random
from collections.abc import Iterator
from itertools import combinations
from typing import Any

import duckdb
import pytest
from splink import DuckDBAPI

from fundlens.resolve import model
from fundlens.resolve.cluster import cluster, cluster_fingerprint

COLUMNS = (
    "contributor_key",
    "first_name",
    "last_name",
    "first_initial",
    "last_name_soundex",
    "zip5",
    "zip3",
    "city",
    "state",
    "employer_norm",
    "occupation_norm",
)
DONORS = 4000
EMPLOYER_EXACT_PRIOR = 0.6


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("ROBERT", "R163"),
        ("RUPERT", "R163"),
        ("ASHCRAFT", "A261"),
        ("TYMCZAK", "T522"),
        ("PFISTER", "P236"),
        ("HONEYMAN", "H555"),
        ("LEE", "L000"),
        ("O'BRIEN", "O165"),
        ("", None),
        (None, None),
    ],
)
def test_soundex_is_american_soundex(name: str | None, code: str | None) -> None:
    assert model.soundex(name) == code


def test_the_fingerprint_is_the_members_whatever_their_order() -> None:
    keys = ["MARLOWE, AUGUSTINE|90250|ASTRAX|CEO", "MARLOWE, AUGUSTINE R|78701|ASTRAX|"]
    assert cluster_fingerprint(keys) == cluster_fingerprint(reversed(keys))
    assert cluster_fingerprint(keys) != cluster_fingerprint(keys[:1])
    assert len(cluster_fingerprint(keys)) == 40


def _population() -> tuple[list[tuple[str | None, ...]], dict[str, int]]:
    """Synthetic contributor rows, and the donor behind each key."""
    rng = random.Random(7)
    firsts = [f"F{a}{b}{c}" for a in "ABCDEFGHIJKLMNOP" for b in "AEIOU" for c in "LMNRST"]
    lasts = [
        f"L{a}{b}{c}{d}" for a in "BCDFGHKLMN" for b in "AEIOU" for c in "LMNRST" for d in "AEIOU"
    ]
    zips = [f"{z:05d}" for z in rng.sample(range(10000, 99999), 400)]
    employers = [f"EMPLOYER {i}" for i in range(300)]
    occupations = [f"OCCUPATION {i}" for i in range(60)]
    rows: list[tuple[str | None, ...]] = []
    donor_of: dict[str, int] = {}
    for donor in range(DONORS):
        first, last, home = rng.choice(firsts), rng.choice(lasts), rng.choice(zips)
        employer, occupation = rng.choice(employers), rng.choice(occupations)
        for variant in range(rng.choice([1, 1, 1, 2, 2, 3])):
            zip5, employer_norm, occupation_norm = home, employer, occupation
            if variant:
                change = rng.random()
                if change < 0.3:
                    occupation_norm = rng.choice(occupations)
                elif change < 0.5:
                    employer_norm = None
                elif change < 0.6:
                    zip5 = home[:3] + f"{rng.randint(0, 99):02d}"
            key = f"{last}, {first}|{zip5}|{employer_norm or ''}|{occupation_norm}"
            if key in donor_of:
                continue
            donor_of[key] = donor
            city, state = f"CITY {zip5[:3]}", f"S{int(zip5[:2]) % 50}"
            rows.append(
                (key, first, last, first[0], model.soundex(last), zip5, zip5[:3], city, state)
                + (employer_norm, occupation_norm)
            )
    return rows, donor_of


@pytest.fixture
def population() -> Iterator[tuple[duckdb.DuckDBPyConnection, dict[str, int]]]:
    rows, donor_of = _population()
    with duckdb.connect() as con:
        con.execute(
            "CREATE TABLE contributor ("
            + ", ".join(f"{column} VARCHAR" for column in COLUMNS)
            + ")"
        )
        con.executemany(f"INSERT INTO contributor VALUES ({', '.join('?' * len(COLUMNS))})", rows)
        yield con, donor_of


def _m(saved: dict[str, Any], comparison: str, label: str) -> float:
    [level] = [
        level
        for c in saved["comparisons"]
        if c["output_column_name"] == comparison
        for level in c["comparison_levels"]
        if level.get("label_for_charts") == label
    ]
    return level["m_probability"]


def _pairs(groups: dict[str, Any]) -> set[frozenset[str]]:
    members: dict[Any, list[str]] = {}
    for key, group in groups.items():
        members.setdefault(group, []).append(key)
    return {frozenset(pair) for keys in members.values() for pair in combinations(keys, 2)}


def test_training_estimates_u_and_m_and_finds_each_donors_keys(
    population: tuple[duckdb.DuckDBPyConnection, dict[str, int]],
) -> None:
    con, donor_of = population
    linker = model.linker(DuckDBAPI(con), "contributor", model.settings())

    assert model.train(linker, keys=len(donor_of), min_training_keys=len(donor_of))

    # EM moved m off its prior (`model._employer`).
    trained = linker.misc.save_model_to_json()
    assert _m(trained, "employer_norm", "Exact match on employer_norm") != EMPLOYER_EXACT_PRIOR
    cluster(linker, con, match_threshold=0.9, cluster_threshold=0.95)
    clusters = dict(con.execute("SELECT contributor_key, cluster_id FROM cluster").fetchall())
    found, truth = _pairs(clusters), _pairs(dict(donor_of))
    assert len(found & truth) / len(truth) >= 0.95
    assert len(found & truth) / len(found) >= 0.9


def test_too_few_keys_keep_the_priors(
    population: tuple[duckdb.DuckDBPyConnection, dict[str, int]],
) -> None:
    con, donor_of = population
    linker = model.linker(DuckDBAPI(con), "contributor", model.settings())

    assert not model.train(linker, keys=len(donor_of), min_training_keys=len(donor_of) + 1)

    saved = linker.misc.save_model_to_json()
    assert _m(saved, "employer_norm", "Exact match on employer_norm") == EMPLOYER_EXACT_PRIOR
    # Only the share of matching pairs was estimated, from the deterministic rules.
    default = model.settings().probability_two_random_records_match
    assert saved["probability_two_random_records_match"] != default
