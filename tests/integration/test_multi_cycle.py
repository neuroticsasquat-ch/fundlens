"""Two cycles in gold at once (NEU-2059, spec §3.4, §4): the 2024 fixture cycle and a tiny 1998 one,
which FEC publishes no `ccl` for, transformed, resolved together, and each loaded and published
in turn, so the second load rebuilds gold from both cycles' live builds.

Here too a backfill-pending table (NEU-2352): `independent_expenditure` stands in, put on
`paths.BACKFILL_PENDING` and its partition deleted from one build or both, and the load and the
dataset snapshot read a cycle whose build lacks it as having no rows of it."""

from collections.abc import Generator, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, LiteralString

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.api.app import create_app
from fundlens.publish import dataset
from fundlens.publish import gold as gold_publish
from fundlens.publish.dataset import DATASET_TABLES, BuildNotReady, Manifest
from fundlens.publish.dataset_schema import columns
from fundlens.publish.gold import NothingToPublish
from fundlens.r2 import R2
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.conftest import (
    Snapshot,
    bucket_name,
    build_snapshot,
    copy_files,
    empty_store,
    point_cli_at,
    restore,
    scratch_database,
)
from tests.integration.test_api_donors import silver_rows
from tests.integration.test_api_routes import ok
from tests.integration.test_dataset import DOCS, OVERRIDES
from tests.integration.test_resolve import MEMORY_LIMIT, MODEL, resolve
from tests.integration.test_transform import (
    BUILD,
    local_silver,
    parquet_rows,
    put_bronze,
    reported_rows,
    seats_report,
    transform,
)

FIXTURE_CYCLE = fec_fixture.CYCLE
EARLY = 1998
# A second build of 2024, published after both cycles are live.
REBUILT = "20261105T030000Z"
CALDER, PARRISH = "H8MD05201", "H8MD05202"
CALDER_COMMITTEE, PARRISH_COMMITTEE = "C00298001", "C00298002"
# The 2024 fixture's party committee, filed in 1998 under a shorter name.
BOTH_CYCLES_COMMITTEE = "C00800203"
# The Musk case's two 1998 gifts (tests/fixtures/fec/1998/indiv.csv).
MUSK_1998 = (4199810000000000001, 4199810000000000002)
EXPECTED = fec_fixture.expected()


def _publish(cycle: int, store: R2, data_dir: Path) -> None:
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        gold_publish.publish(
            cycle, store, conn=conn, data_dir=data_dir, purge=None, sleep=lambda _: None
        )


def _load_and_publish(cycle: int, build_id: str, store: R2) -> None:
    result = CliRunner().invoke(cli.app, ["load", "--cycle", str(cycle), "--build-id", build_id])
    assert result.exit_code == 0, result.output
    _publish(cycle, store, get_settings().data_dir)


@pytest.fixture(scope="module")
def two_cycles(
    transformed_snapshot: Snapshot,
    migrated_template: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Snapshot]:
    """The 2024 fixture cycle (`transformed_snapshot`) and 1998, both transformed as build
    `BUILD`, resolved together as model `MODEL`, then 2024 loaded and published, then 1998."""

    def steps(env: pytest.MonkeyPatch) -> None:
        store = R2.from_settings(get_settings())
        put_bronze(store, EARLY)
        seats_report(EARLY)
        result = transform(EARLY)
        assert result.exit_code == 0, result.output
        env.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
        get_settings.cache_clear()
        resolved = resolve("--full", "--build-id", MODEL)
        assert resolved.exit_code == 0, resolved.output
        for cycle in (FIXTURE_CYCLE, EARLY):
            _load_and_publish(cycle, BUILD, store)

    yield from build_snapshot(
        "two-cycles",
        tmp_path_factory,
        template=migrated_template,
        steps=steps,
        parent=transformed_snapshot,
    )


@pytest.fixture(scope="module")
def client(two_cycles: Snapshot) -> Iterator[TestClient]:
    """The API over a copy of the two-cycle database and the snapshot's silver, read only."""
    with scratch_database(template=two_cycles.database) as conninfo:
        settings = get_settings().model_copy(
            update={"database_url": conninfo, "data_dir": two_cycles.data_dir}
        )
        with TestClient(create_app(settings)) as client:
            yield client


def _all_pages(client: TestClient, url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        page = ok(client.get(url, params={"cursor": cursor} if cursor else None))
        rows += page["contributions"]
        cursor = page["next_cursor"]
        if cursor is None:
            return rows


def test_a_1998_candidate_links_to_its_committee_without_ccl(
    two_cycles: Snapshot, client: TestClient
) -> None:
    links = parquet_rows(
        paths.local_path(
            two_cycles.data_dir,
            f"{paths.silver_partition('candidate_committee_link', EARLY, BUILD)}/{paths.part(0)}",
        )
    )
    race = ok(client.get(f"/v1/races/{EARLY}/house/MD-05"))

    # CALDER through her `cn` row's principal committee, PARRISH through his committee's `cm` row.
    assert {
        (row["candidate_id"], row["committee_id"], row["designation"], row["linkage_id"])
        for row in links
    } == {(CALDER, CALDER_COMMITTEE, "P", None), (PARRISH, PARRISH_COMMITTEE, "P", None)}
    assert {
        candidate["candidate_id"]: (
            candidate["principal_committee_id"],
            candidate["total_individual"],
            candidate["total_committee"],
        )
        for candidate in race["candidates"]
    } == {CALDER: (CALDER_COMMITTEE, 1000, 2000), PARRISH: (PARRISH_COMMITTEE, 750, 0)}
    assert (race["total_individual"], race["total_committee"]) == (1750, 2000)


def test_cycles_lists_both_cycles_with_their_own_totals(client: TestClient) -> None:
    races = {cycle: ok(client.get(f"/v1/cycles/{cycle}/races")) for cycle in (FIXTURE_CYCLE, EARLY)}

    assert ok(client.get("/v1/cycles")) == [
        {
            "cycle": FIXTURE_CYCLE,
            "race_count": len(races[FIXTURE_CYCLE]),
            "contribution_count": EXPECTED["silver"]["contribution"],
            "total_amount": EXPECTED["contributions"]["total_amount"],
        },
        {
            "cycle": EARLY,
            "race_count": len(races[EARLY]),
            "contribution_count": 3,
            "total_amount": 2250,
        },
    ]
    assert all(race["cycle"] == EARLY for race in races[EARLY])


def test_meta_names_each_cycles_live_build(client: TestClient) -> None:
    meta = ok(client.get("/v1/meta"))

    assert {cycle: entry["build_id"] for cycle, entry in meta["cycles"].items()} == {
        str(EARLY): BUILD,
        str(FIXTURE_CYCLE): BUILD,
    }
    assert "ccl" not in meta["cycles"][str(EARLY)]["source_dates"]


def test_the_musk_donor_page_shows_rows_from_both_cycles(
    two_cycles: Snapshot, client: TestClient
) -> None:
    [musk] = {
        donor_id
        for donor_id, *_ in silver_rows(
            two_cycles.data_dir,
            EARLY,
            BUILD,
            f"source_record_id IN ({', '.join(map(str, MUSK_1998))})",
        )
    }

    donor = ok(client.get(f"/v1/donors/{musk}"))
    rows = _all_pages(client, f"/v1/donors/{musk}/contributions")

    assert (donor["first_cycle"], donor["last_cycle"]) == (EARLY, FIXTURE_CYCLE)
    assert [cycle["cycle"] for cycle in donor["cycles"]] == [FIXTURE_CYCLE, EARLY]
    assert {row["cycle"] for row in rows} == {FIXTURE_CYCLE, EARLY}
    assert {row["source_record_id"] for row in rows if row["cycle"] == EARLY} == {
        str(sub_id) for sub_id in MUSK_1998
    }
    assert donor["total_all_cycles"] == sum(cycle["amount"] for cycle in donor["cycles"])


def test_a_committee_of_both_cycles_is_one_committee_named_as_its_newest_cycle_names_it(
    client: TestClient,
) -> None:
    committee = ok(client.get(f"/v1/committees/{BOTH_CYCLES_COMMITTEE}"))

    assert committee["name"] == "OLD LINE REPUBLICAN COMMITTEE"
    assert [cycle["cycle"] for cycle in committee["cycles"]] == [FIXTURE_CYCLE, EARLY]
    [early] = [cycle for cycle in committee["cycles"] if cycle["cycle"] == EARLY]
    assert early["total_individual"] == 500


def _copy_build(store: R2, cycle: int, source: str, target: str) -> None:
    """Every silver partition and the `transformed` marker of `source`, as build `target`: a new
    build of the cycle, as far as `load` and `publish` can tell, without transforming again."""
    for key in store.list_keys("silver/"):
        if paths.cycle_of(key) == cycle and paths.build_of(key) == source:
            new_key = key.replace(f"/build={source}/", f"/build={target}/")
            store.client.copy_object(
                Bucket=store.bucket, Key=new_key, CopySource={"Bucket": store.bucket, "Key": key}
            )
    marker = paths.marker(cycle, source, "transformed")
    store.put(paths.marker(cycle, target, "transformed"), store.get(marker))


def test_publishing_a_new_2024_build_leaves_1998_live(
    two_cycles: Snapshot, store: R2, cli_env: Path, migrated_db: str
) -> None:
    restore(two_cycles, store=store, data_dir=cli_env, conninfo=migrated_db)
    _copy_build(store, FIXTURE_CYCLE, BUILD, REBUILT)

    result = CliRunner().invoke(
        cli.app, ["load", "--cycle", str(FIXTURE_CYCLE), "--build-id", REBUILT]
    )
    assert result.exit_code == 0, result.output
    # gold_build holds 2024's load, so 1998's publish refuses it rather than swap it in.
    with pytest.raises(NothingToPublish):
        _publish(EARLY, store, cli_env)
    _publish(FIXTURE_CYCLE, store, cli_env)

    with psycopg.connect(migrated_db) as conn:
        row = conn.execute("SELECT cycles FROM gold.meta").fetchone()
    assert row is not None
    assert {cycle: entry["build_id"] for cycle, entry in row[0].items()} == {
        str(EARLY): BUILD,
        str(FIXTURE_CYCLE): REBUILT,
    }
    assert markers.read_live(store) == {EARLY: BUILD, FIXTURE_CYCLE: REBUILT}
    settings = get_settings().model_copy(update={"database_url": migrated_db})
    with TestClient(create_app(settings)) as client:
        page = ok(client.get(f"/v1/committees/{CALDER_COMMITTEE}/contributions?cycle={EARLY}"))
        assert [row["source_record_id"] for row in page["contributions"]] == [str(MUSK_1998[0])]
        assert [cycle["cycle"] for cycle in ok(client.get("/v1/cycles"))] == [FIXTURE_CYCLE, EARLY]


def test_a_load_with_no_manifest_keeps_every_cycle_live_gold_holds(
    two_cycles: Snapshot, store: R2, cli_env: Path, migrated_db: str
) -> None:
    """Gold published before `markers/live.json` existed: the live `gold.meta.cycles` stands in,
    and a cycle carried over keeps the download dates its live build was transformed from."""
    restore(two_cycles, store=store, data_dir=cli_env, conninfo=migrated_db)
    store.delete_keys([paths.LIVE_BUILDS])
    # A newer download of 2024, not yet transformed, is not what 2024's live build serves.
    newer = paths.bronze_zip(FIXTURE_CYCLE, "cm", date(2026, 11, 11))
    store.put(newer, b"")
    with psycopg.connect(migrated_db) as conn:
        [(live,)] = conn.execute("SELECT cycles FROM gold.meta").fetchall()

    result = CliRunner().invoke(cli.app, ["load", "--cycle", str(EARLY), "--build-id", BUILD])

    assert result.exit_code == 0, result.output
    with psycopg.connect(migrated_db) as conn:
        [(staged,)] = conn.execute("SELECT cycles FROM gold_build.meta").fetchall()
    assert staged == live


def test_before_2008_reported_totals_are_webks_committees_and_weballs_candidates(
    two_cycles: Snapshot,
) -> None:
    """1998 has no committee_summary: a committee's reported total is its webk row, a
    candidate's its weball row, and the columns only committee_summary has are null
    (every-FEC-dollar spec §4.1, §4.2)."""
    expected = EXPECTED["reported_totals"]
    committees = local_silver(two_cycles.data_dir, "reported_total", EARLY)
    candidates = local_silver(two_cycles.data_dir, "candidate_reported_total", EARLY)

    assert reported_rows(committees, "committee_id") == expected["reported_total"][EARLY]
    assert reported_rows(candidates, "candidate_id") == expected["candidate_reported_total"][EARLY]
    assert {row["cycle"] for row in [*committees, *candidates]} == {EARLY}


def test_before_2008_gold_takes_a_candidates_weball_row_and_has_no_coverage(
    two_cycles: Snapshot,
) -> None:
    """A 1998 candidate's reported figures are their weball row as filed, not their committees'
    sum; no file before 2008 has an itemized figure, so no coverage, reconciliation or unitemized
    gift-size row (every-FEC-dollar spec §4.3 to §4.7). `oppexp` starts in 2004, so a 1998
    committee, candidate and race has a NULL total_operating_expenditures, never 0, and no category,
    top-payee, payee-cycle or top-payer row (§5.5); 2024's beside it keep theirs. Nor has it an
    electioneering figure (§6.5)."""
    columns = EXPECTED["reported_totals"]["columns"]
    weball = EXPECTED["reported_totals"]["candidate_reported_total"][EARLY]
    webk = EXPECTED["reported_totals"]["reported_total"][EARLY]
    with (
        scratch_database(template=two_cycles.database) as conninfo,
        psycopg.connect(conninfo) as conn,
    ):
        candidates = conn.execute(
            "SELECT candidate_id, reported_source_file, reported_receipts,"
            " reported_cash_on_hand_end, coverage, reported_includes_converted_committee"
            " FROM gold.candidate_cycle WHERE cycle = %s",
            (EARLY,),
        ).fetchall()
        committees = conn.execute(
            "SELECT committee_id, reported_source_file, reported_receipts, coverage"
            " FROM gold.committee_cycle WHERE cycle = %s AND reported_source_file IS NOT NULL",
            (EARLY,),
        ).fetchall()
        later = conn.execute(
            "SELECT (SELECT count(*) FROM gold.reconciliation WHERE cycle = %s),"
            " (SELECT count(*) FROM gold.candidate_gift_size"
            "  WHERE cycle = %s AND bucket = 'unitemized')",
            (EARLY, EARLY),
        ).fetchone()
        [spending_early, spending_current] = conn.execute(
            "SELECT"
            " (SELECT count(total_operating_expenditures) FROM gold.committee_cycle"
            "  WHERE cycle = c.cycle)"
            " + (SELECT count(total_operating_expenditures) FROM gold.candidate_cycle"
            "  WHERE cycle = c.cycle)"
            " + (SELECT count(total_operating_expenditures) FROM gold.race WHERE cycle = c.cycle)"
            " + (SELECT count(*) FROM gold.committee_spending_category WHERE cycle = c.cycle)"
            " + (SELECT count(*) FROM gold.committee_top_payee WHERE cycle = c.cycle)"
            " + (SELECT count(*) FROM gold.payee_cycle WHERE cycle = c.cycle)"
            " + (SELECT count(*) FROM gold.payee_top_payer WHERE cycle = c.cycle)"
            " FROM (VALUES (%s), (2024)) AS c(cycle) ORDER BY c.cycle",
            (EARLY,),
        ).fetchall()
        # No electioneering file before 2010 (§6.5): NULL, never 0, on every committee, candidate
        # and race, while each outside_spending_total is a figure.
        [electioneering_early, electioneering_current] = conn.execute(
            "SELECT"
            " (SELECT count(electioneering_total) FROM gold.committee_cycle WHERE cycle = c.cycle)"
            " + (SELECT count(electioneering) FROM gold.candidate_cycle WHERE cycle = c.cycle)"
            " + (SELECT count(electioneering) FROM gold.race WHERE cycle = c.cycle),"
            " (SELECT count(*) FROM gold.race"
            "  WHERE cycle = c.cycle AND outside_spending_total IS NULL)"
            " FROM (VALUES (%s), (2024)) AS c(cycle) ORDER BY c.cycle",
            (EARLY,),
        ).fetchall()

    receipts, cash = columns.index("receipts"), columns.index("cash_on_hand_end")
    assert {row[0]: row[1:] for row in candidates} == {
        candidate_id: (
            "weball",
            weball[candidate_id][receipts],
            weball[candidate_id][cash],
            None,
            False,
        )
        for candidate_id in (CALDER, PARRISH)
    }
    assert {row[0]: row[1:] for row in committees} == {
        committee_id: ("webk", row[receipts], None) for committee_id, row in webk.items()
    }
    assert later == (0, 0)
    assert spending_early == (0,)
    assert spending_current[0] > 0
    assert electioneering_early == (0, 0)
    assert electioneering_current[0] > 0
    assert electioneering_current[1] == 0


# What a 1996-2006 `webk` row lacks and `committee_summary` has (every-FEC-dollar spec §4.7).
ONLY_FROM_2008 = {
    "period_start",
    "debts_owed_to",
    "individual_itemized",
    "individual_unitemized",
    "party_contributions",
    "operating_expenditures",
    "federal_funds",
}


def test_a_1998_committee_page_has_webks_figures_and_null_only_where_webk_has_none(
    client: TestClient,
) -> None:
    """The API answers a pre-2008 committee with its reported totals as `webk` filed them, None for
    the measures no file before 2008 has, never the whole object, and no coverage (NEU-2145)."""
    [cycle] = ok(client.get(f"/v1/committees/{CALDER_COMMITTEE}"))["cycles"]
    [both_newest, both_early] = ok(client.get(f"/v1/committees/{BOTH_CYCLES_COMMITTEE}"))["cycles"]
    columns = EXPECTED["reported_totals"]["columns"]
    filed = EXPECTED["reported_totals"]["reported_total"][EARLY]

    # CALDER's campaign committee files no webk row in 1998 (spec §4.1); the party committee does.
    assert cycle["reported"] is None
    reported = both_early["reported"]
    assert reported == {
        column: value.isoformat() if isinstance(value, date) else value
        for column, value in zip(columns, filed[BOTH_CYCLES_COMMITTEE], strict=True)
    }
    assert reported["source_file"] == "webk"
    # The party committee also leaves its candidate contribution and loan lines blank, as filed.
    blank = {column for column, value in reported.items() if value is None}
    candidate_lines = {"candidate_contributions", "candidate_loans", "candidate_loan_repayments"}
    assert blank - candidate_lines == ONLY_FROM_2008
    assert (both_early["coverage"], both_newest["reported"]["source_file"]) == (
        None,
        "committee_summary",
    )


def test_a_pac_page_has_every_measure_webk_files_before_2008(client: TestClient) -> None:
    [cycle] = ok(client.get("/v1/committees/C00298003"))["cycles"]

    assert {
        column for column, value in cycle["reported"].items() if value is None
    } == ONLY_FROM_2008
    assert cycle["coverage"] is None


def test_a_resolved_candidate_page_has_its_gift_sizes_in_bucket_order(client: TestClient) -> None:
    """Each donor's net gifts to the candidate decide their bucket (spec §4.6): BRANNIGAN's 2024
    six, FEC's unitemized lump first; CALDER's 1998 the five itemized only, adding up to his
    individual money, since no file before 2008 has an unitemized figure."""
    [brannigan] = ok(client.get("/v1/candidates/S4MD00111"))["cycles"]
    [calder] = ok(client.get(f"/v1/candidates/{CALDER}"))["cycles"]

    assert {
        row["bucket"]: [row["amount"], row["donors"]] for row in brannigan["gift_sizes"]
    } == EXPECTED["gold_reported"]["gift_sizes"]["S4MD00111"]
    assert [row["bucket"] for row in brannigan["gift_sizes"]] == [
        "unitemized",
        "200_or_less",
        "under_500",
        "under_1000",
        "under_2000",
        "2000_or_more",
    ]
    assert [row["bucket"] for row in calder["gift_sizes"]] == [
        "200_or_less",
        "under_500",
        "under_1000",
        "under_2000",
        "2000_or_more",
    ]
    assert sum(row["amount"] for row in calder["gift_sizes"]) == calder["total_individual"]
    assert calder["reported"]["source_file"] == "weball"


# The stand-in backfill-pending table: a dataset table, not resolved, which the 2024 fixture has
# rows of and 1998 none.
PENDING = "independent_expenditure"
DAY = date(2026, 11, 22)


def _partition(cycle: int) -> str:
    return paths.silver_partition(PENDING, cycle, BUILD) + "/"


def test_transform_writes_a_partition_with_no_rows_for_a_cycle_with_none(
    two_cycles: Snapshot,
) -> None:
    """A silver model always writes its partition, so a build lacking one only ever means it was
    built before the table existed."""
    parts = {
        cycle: two_cycles.store.list_keys(_partition(cycle)) for cycle in (FIXTURE_CYCLE, EARLY)
    }
    local = {cycle: paths.local_path(two_cycles.data_dir, key) for cycle, [key] in parts.items()}

    assert all(key.endswith(".parquet") for keys in parts.values() for key in keys)
    assert parquet_rows(local[FIXTURE_CYCLE])
    assert parquet_rows(local[EARLY]) == []
    assert columns(local[EARLY]) == columns(local[FIXTURE_CYCLE])


@dataclass(frozen=True)
class Copy:
    """A copy of `two_cycles` of the module's own: its bucket, database and `DATA_DIR`."""

    store: R2
    conninfo: str
    data_dir: Path
    source: R2


@pytest.fixture(scope="module")
def copied(two_cycles: Snapshot, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Copy]:
    """`two_cycles`, copied once for the backfill-pending tests: each deletes partitions from its
    bucket and puts them back (`_without`), so none restores the whole state."""
    data_dir = tmp_path_factory.mktemp("backfill-pending")
    store = empty_store(bucket_name("backfill-pending"))
    try:
        copy_files(two_cycles, store=store, data_dir=data_dir)
        with scratch_database(template=two_cycles.database) as conninfo:
            yield Copy(store, conninfo, data_dir, two_cycles.store)
    finally:
        store.delete_prefix("")


@contextmanager
def _without(copy: Copy, cycles: Sequence[int], *, stray: bytes | None = None) -> Generator[None]:
    """`PENDING`'s partition of each of `cycles` deleted from R2, its local cache left as it is
    (R2 decides what a build holds); with `stray`, one object of those bytes put in its place that
    is not Parquet. Put back as it was on exit."""
    deleted = [key for cycle in cycles for key in copy.store.list_keys(_partition(cycle))]
    strays = [_partition(cycle) + "notes.txt" for cycle in cycles] if stray is not None else []
    try:
        copy.store.delete_keys(deleted)
        for key in strays:
            copy.store.put(key, stray or b"")
        yield
    finally:
        copy.store.delete_keys(strays)
        for key in deleted:
            copy.store.client.copy_object(
                Bucket=copy.store.bucket,
                Key=key,
                CopySource={"Bucket": copy.source.bucket, "Key": key},
            )


def _pending(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "BACKFILL_PENDING", frozenset({PENDING}))


@pytest.fixture
def load_env(copied: Copy, monkeypatch: pytest.MonkeyPatch) -> Iterator[Copy]:
    """The CLI pointed at `copied`, its database holding no `gold_build`."""
    point_cli_at(
        monkeypatch, conninfo=copied.conninfo, data_dir=copied.data_dir, bucket=copied.store.bucket
    )
    with psycopg.connect(copied.conninfo, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS gold_build CASCADE")
    yield copied
    get_settings.cache_clear()


def _load_1998() -> Result:
    return CliRunner().invoke(cli.app, ["load", "--cycle", str(EARLY), "--build-id", BUILD])


# Each cycle's independent-expenditure figures in gold: per candidate, per committee, and the
# race top-committee rows that come from independent expenditures.
_IE_FIGURES: dict[str, LiteralString] = {
    "candidate": "SELECT candidate_id, ie_support, ie_oppose FROM {schema}.candidate_cycle"
    " WHERE cycle = %s ORDER BY candidate_id",
    "committee": "SELECT committee_id, ie_total FROM {schema}.committee_cycle"
    " WHERE cycle = %s ORDER BY committee_id",
    "top": "SELECT top.race_id, top.committee_id, top.amount"
    " FROM {schema}.race_top_committee AS top JOIN {schema}.race USING (race_id)"
    " WHERE race.cycle = %s AND top.kind = 'ie' ORDER BY top.race_id, top.committee_id",
}


def _ie_figures(conninfo: str, schema: str, cycle: int) -> dict[str, list[tuple[Any, ...]]]:
    with psycopg.connect(conninfo) as conn:
        return {
            name: conn.execute(
                sql.SQL(query).format(schema=sql.Identifier(schema)), (cycle,)
            ).fetchall()
            for name, query in _IE_FIGURES.items()
        }


def _none(figures: dict[str, list[tuple[Any, ...]]]) -> bool:
    """Whether `figures` are a cycle's with no independent expenditures."""
    return (
        all(row[1:] == (0, 0) for row in figures["candidate"])
        and all(row[1:] == (0,) for row in figures["committee"])
        and not figures["top"]
    )


@pytest.mark.parametrize("lacking", [(FIXTURE_CYCLE,), (EARLY,), (FIXTURE_CYCLE, EARLY)], ids=str)
def test_a_cycle_whose_build_lacks_a_backfill_pending_table_loads_with_no_rows_of_it(
    load_env: Copy, monkeypatch: pytest.MonkeyPatch, lacking: tuple[int, ...]
) -> None:
    """Whichever build lacks it, the loaded one or another cycle's live one; and when no build has
    it, through the view typed from its committed schema."""
    _pending(monkeypatch)
    with _without(load_env, lacking):
        result = _load_1998()

    assert result.exit_code == 0, result.output
    for cycle in (FIXTURE_CYCLE, EARLY):
        loaded = _ie_figures(load_env.conninfo, "gold_build", cycle)
        live = _ie_figures(load_env.conninfo, "gold", cycle)
        assert loaded["candidate"], cycle
        if cycle in lacking:
            assert _none(loaded), cycle
        else:
            assert loaded == live, cycle
    # Not vacuous: the 2024 fixture's live gold has independent expenditures.
    assert not _none(_ie_figures(load_env.conninfo, "gold", FIXTURE_CYCLE))


def test_a_build_lacking_a_table_not_backfill_pending_fails_the_load(load_env: Copy) -> None:
    with _without(load_env, [FIXTURE_CYCLE]):
        result = _load_1998()

    assert result.exit_code == 1
    assert f"no silver {PENDING} partition for build {BUILD} of {FIXTURE_CYCLE}" in result.output
    with psycopg.connect(load_env.conninfo) as conn:
        [(staged,)] = conn.execute("SELECT to_regnamespace('gold_build')").fetchall()
    assert staged is None


def test_a_backfill_pending_partition_holding_no_parquet_fails_the_load(
    load_env: Copy, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pending(monkeypatch)
    with _without(load_env, [FIXTURE_CYCLE], stray=b"not parquet"):
        result = _load_1998()

    assert result.exit_code == 1
    assert (
        f"the silver {PENDING} partition of build {BUILD} of {FIXTURE_CYCLE} holds no Parquet"
        in result.output
    )
    with psycopg.connect(load_env.conninfo) as conn:
        [(staged,)] = conn.execute("SELECT to_regnamespace('gold_build')").fetchall()
    assert staged is None


@pytest.fixture
def public() -> Iterator[R2]:
    """An empty public bucket of the test's own."""
    bucket = empty_store(bucket_name("public-pending"))
    yield bucket
    bucket.delete_prefix("")


def _snapshot(copy: Copy, public: R2) -> Manifest:
    with psycopg.connect(copy.conninfo, autocommit=True) as conn:
        dataset.snapshot(
            conn,
            copy.store,
            public,
            snapshot_date=DAY,
            data_dir=copy.data_dir,
            overrides_path=OVERRIDES,
            docs_dir=DOCS,
            workers=4,
        )
    return Manifest.model_validate_json(public.get(paths.dataset_snapshot(DAY) + dataset.MANIFEST))


def _cycles_of(manifest: Manifest, table: str) -> set[str]:
    return {file.path.split("/")[1] for file in manifest.tables[table].files}


def test_a_snapshot_lists_a_backfill_pending_table_with_the_cycles_that_have_it(
    copied: Copy, public: R2, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pending(monkeypatch)
    with _without(copied, [EARLY]):
        manifest = _snapshot(copied, public)

    [part] = copied.store.list_keys(_partition(FIXTURE_CYCLE))
    assert set(manifest.cycles) == {FIXTURE_CYCLE, EARLY}
    assert _cycles_of(manifest, PENDING) == {f"cycle={FIXTURE_CYCLE}"}
    assert manifest.tables[PENDING].rows == len(
        parquet_rows(paths.local_path(copied.data_dir, part))
    )
    for table in DATASET_TABLES:
        if table != PENDING:
            assert _cycles_of(manifest, table) == {f"cycle={FIXTURE_CYCLE}", f"cycle={EARLY}"}


def test_a_snapshot_with_no_build_of_a_backfill_pending_table_lists_it_empty(
    copied: Copy, public: R2, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pending(monkeypatch)
    with _without(copied, [FIXTURE_CYCLE, EARLY]):
        manifest = _snapshot(copied, public)

    assert (manifest.tables[PENDING].rows, manifest.tables[PENDING].files) == (0, [])


@pytest.mark.parametrize(
    ("pending", "stray", "match"),
    [
        (False, None, f"has no {PENDING}"),
        (True, b"not parquet", f"has no {PENDING}"),
    ],
    ids=["not backfill-pending", "no Parquet"],
)
def test_a_snapshot_refuses_a_missing_table_not_backfill_pending_or_a_partition_of_no_parquet(
    copied: Copy,
    public: R2,
    monkeypatch: pytest.MonkeyPatch,
    pending: bool,
    stray: bytes | None,
    match: str,
) -> None:
    if pending:
        _pending(monkeypatch)
    with _without(copied, [EARLY], stray=stray), pytest.raises(BuildNotReady, match=match):
        _snapshot(copied, public)

    assert not public.list_keys(paths.dataset_snapshot(DAY))
