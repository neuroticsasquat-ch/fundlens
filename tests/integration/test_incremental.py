"""`fundlens resolve` without `--full` on the fixture cycle's next week: its new contributor keys
resolved against the saved model, every donor_id already given left as it was (spec §6.10,
NEU-2062)."""

import logging
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import psycopg
import pytest
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.resolve import model
from fundlens.resolve.runner import RunRecord, run_record
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.conftest import Snapshot, build_snapshot
from tests.integration.test_resolve import MEMORY_LIMIT, resolve
from tests.integration.test_transform import BUILD, put_bronze
from tests.integration.test_validate import resolved_env

log = logging.getLogger(__name__)

# The fixture cycle's next weekly build.
NEXT = "20261106T030000Z"
# Augustine Marlowe, the fixture's Musk case, in three new ways; Rosalind Fenwick, a donor never
# seen before; and two more gifts from donors whose keys stood.
MARLOWE_NEW = (
    "MARLOWE, AUGUSTINE|90250|ASTRAX|FOUNDER",
    "MARLOWE, AUGUSTINE R|78701|VOLTAIC MOTORS|CEO",
    "MARLOWE, AUGUSTINE|78521|ASTRAX|ENTREPRENEUR",
)
NEWCOMER = "FENWICK, ROSALIND|97201|CASCADE BIOLOGICS|CHEMIST"
ADDED = (
    ("MARLOWE, AUGUSTINE", "HAWTHORNE", "CA", "902501234", "ASTRAX", "FOUNDER", "10012024", "500"),
    ("MARLOWE, AUGUSTINE", "HAWTHORNE", "CA", "90250", "ASTRAX", "FOUNDER", "10082024", "500"),
    ("MARLOWE, AUGUSTINE MR", "HAWTHORNE", "CA", "90250", "ASTRAX", "FOUNDER", "10152024", "500"),
    ("MARLOWE, AUGUSTINE R.", "AUSTIN", "TX", "78701", "VOLTAIC MOTORS", "CEO", "10022024", "1000"),
    (
        "MARLOWE, AUGUSTINE R",
        "AUSTIN",
        "TX",
        "787011111",
        "VOLTAIC MOTORS",
        "CEO",
        "10092024",
        "1000",
    ),
    (
        "MARLOWE, AUGUSTINE",
        "BROWNSVILLE",
        "TX",
        "78521",
        "ASTRAX",
        "ENTREPRENEUR",
        "10032024",
        "250",
    ),
    (
        "MARLOWE, AUGUSTINE",
        "BROWNSVILLE",
        "TX",
        "78521",
        "ASTRAX",
        "ENTREPRENEUR",
        "10102024",
        "250",
    ),
    (
        "FENWICK, ROSALIND",
        "PORTLAND",
        "OR",
        "97201",
        "CASCADE BIOLOGICS",
        "CHEMIST",
        "10042024",
        "300",
    ),
    ("DUBOIS, RAYMOND", "ROCKVILLE", "MD", "20850", "ASTRAX", "ENGINEER", "10052024", "200"),
    ("SMITH, JOHN", "BALTIMORE", "MD", "21201", "RETIRED", "RETIRED", "10062024", "100"),
)


def added_indiv() -> str:
    """The fixture's `indiv` with `ADDED`, each a gift to the fixture's committee C00800102 on its
    Q3 report, as FEC writes the file."""
    columns = CATALOGUE["indiv"].header()
    lines: list[str] = []
    for n, (name, city, state, zip_code, employer, occupation, date, amount) in enumerate(
        ADDED, start=1
    ):
        row = dict.fromkeys(columns, "")
        row |= {
            "CMTE_ID": "C00800102",
            "AMNDT_IND": "N",
            "RPT_TP": "Q3",
            "TRANSACTION_PGI": "G2024",
            "IMAGE_NUM": f"2024000099{n:08d}",
            "TRANSACTION_TP": "15",
            "ENTITY_TP": "IND",
            "NAME": name,
            "CITY": city,
            "STATE": state,
            "ZIP_CODE": zip_code,
            "EMPLOYER": employer,
            "OCCUPATION": occupation,
            "TRANSACTION_DT": date,
            "TRANSACTION_AMT": amount,
            "TRAN_ID": f"SA11AI.9{n:04d}",
            "FILE_NUM": "1701021",
            "SUB_ID": f"42409000000000{n:05d}",
        }
        lines.append("|".join(row[column] for column in columns) + "\n")
    return fec_fixture.bulk_text("indiv") + "".join(lines)


def crosswalk_rows(conninfo: str) -> dict[str, tuple[Any, ...]]:
    """Every `app.crosswalk` row, by key: its donor_id, when and by which build."""
    with psycopg.connect(conninfo) as conn:
        rows = conn.execute(
            "SELECT contributor_key, donor_id, assigned_at, build_id FROM app.crosswalk"
        ).fetchall()
    return {key: tuple(rest) for key, *rest in rows}


def resolve_s(store: R2, build_id: str) -> float:
    """The wall time of the resolve that wrote the fixture cycle's `resolved` marker for
    `build_id`, from the marker."""
    marker = markers.read("resolved", store, cycle=fec_fixture.CYCLE, build_id=build_id)
    assert marker is not None
    started: datetime = marker.started_at
    return (marker.finished_at - started).total_seconds()


@dataclass(frozen=True)
class Incremented:
    """A resolved snapshot, then the fixture cycle's next week transformed and resolved
    incrementally."""

    result: Result
    before: dict[str, tuple[Any, ...]]
    after: dict[str, tuple[Any, ...]]
    # The live model's run record before and after.
    record_before: RunRecord | None
    record_after: RunRecord | None
    full_s: float
    incremental_s: float
    snapshot: Snapshot


def increment(
    rung: str,
    parent: Snapshot,
    *,
    template: str,
    tmp_path_factory: pytest.TempPathFactory,
    configure: Callable[[pytest.MonkeyPatch], None],
) -> Iterator[Incremented]:
    """A session snapshot `rung`: `parent`, its next week transformed as `NEXT` and resolved
    incrementally under the settings `configure` sets, which should be those `parent` resolved
    under."""
    seen: dict[str, Any] = {}

    def steps(env: pytest.MonkeyPatch) -> None:
        configure(env)
        settings = get_settings()
        store = R2.from_settings(settings)
        version = model.live_version(store)
        assert version is not None
        seen["before"] = crosswalk_rows(settings.database_url)
        seen["record_before"] = run_record(store, version)
        put_bronze(store, texts={"indiv": added_indiv()})
        transformed = CliRunner().invoke(
            cli.app, ["transform", "--cycle", str(fec_fixture.CYCLE), "--build-id", NEXT]
        )
        assert transformed.exit_code == 0, transformed.output
        seen["result"] = resolve("--cycle", str(fec_fixture.CYCLE))
        seen["after"] = crosswalk_rows(settings.database_url)
        seen["record_after"] = run_record(store, version)
        seen["full_s"] = resolve_s(store, BUILD)
        seen["incremental_s"] = resolve_s(store, NEXT)

    for snapshot in build_snapshot(
        rung, tmp_path_factory, template=template, steps=steps, parent=parent
    ):
        yield Incremented(
            result=seen["result"],
            before=seen["before"],
            after=seen["after"],
            record_before=seen["record_before"],
            record_after=seen["record_after"],
            full_s=seen["full_s"],
            incremental_s=seen["incremental_s"],
            snapshot=snapshot,
        )


def memory_limit(env: pytest.MonkeyPatch) -> None:
    """The settings `resolved_snapshot` resolved under."""
    env.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
    get_settings.cache_clear()


@pytest.fixture(scope="module")
def incremented(
    resolved_snapshot: Snapshot, migrated_template: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Incremented]:
    yield from increment(
        "incremented",
        resolved_snapshot,
        template=migrated_template,
        tmp_path_factory=tmp_path_factory,
        configure=memory_limit,
    )


@pytest.fixture(scope="module")
def incremented_after_verdicts(
    validated_snapshot: Snapshot, migrated_template: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Incremented]:
    """`increment` on `validated_snapshot`: resolved with the fixture's overrides and a confident
    adjudication merge in place."""
    yield from increment(
        "incremented-after-verdicts",
        validated_snapshot,
        template=migrated_template,
        tmp_path_factory=tmp_path_factory,
        configure=resolved_env,
    )


def test_the_new_keys_take_their_donors_id_and_one_new_person_takes_the_one_new_id(
    incremented: Incremented,
) -> None:
    assert incremented.result.exit_code == 0, incremented.result.output
    before, after = incremented.before, incremented.after
    assert set(after) - set(before) == {*MARLOWE_NEW, NEWCOMER}
    marlowe = {before[key][0] for key in before if key.startswith("MARLOWE, AUGUSTINE")}
    assert len(marlowe) == 1
    assert {after[key][0] for key in MARLOWE_NEW} == marlowe
    new_ids = {row[0] for row in after.values()} - {row[0] for row in before.values()}
    assert new_ids == {after[NEWCOMER][0]}
    assert "crosswalk: 1 new donors, 0 keys re-pointed, 0 redirects" in incremented.result.output
    assert "4 new contributor keys of" in incremented.result.output


def test_no_crosswalk_row_that_stood_changes(incremented: Incremented) -> None:
    assert {key: incremented.after[key] for key in incremented.before} == incremented.before
    assert {incremented.after[key][2] for key in (*MARLOWE_NEW, NEWCOMER)} == {NEXT}


def test_only_the_new_build_is_resolved_and_its_silver_carries_every_donor_id(
    incremented: Incremented,
) -> None:
    snapshot = incremented.snapshot
    marker = markers.read("resolved", snapshot.store, cycle=fec_fixture.CYCLE, build_id=NEXT)
    assert marker is not None
    contributions = fec_fixture.expected()["silver"]["contribution"] + len(ADDED)
    assert marker.row_counts["contribution"] == contributions
    part = paths.local_path(
        snapshot.data_dir, paths.silver_partition("contribution", fec_fixture.CYCLE, NEXT)
    )
    with duckdb.connect() as con:
        [(rows, without)] = con.execute(
            "SELECT count(*), count(*) FILTER (WHERE donor_id IS NULL)"
            " FROM read_parquet(?, hive_partitioning = false)",
            [str(part / "**" / "*.parquet")],
        ).fetchall()
    assert (rows, without) == (contributions, 0)


def test_an_incremental_resolve_neither_trains_nor_scores_every_pair(
    incremented: Incremented,
) -> None:
    # The times are a measurement only. On a fixture this small, fixed costs (DuckDB, the silver
    # rewrite) are most of either run, so their ratio is runner noise: 0.84 locally, 1.04 on CI
    # once (NEU-2340). The work an incremental run skips is what it asserts instead.
    log.info(
        "resolve: full %.2f s, incremental %.2f s (%.2f of full)",
        incremented.full_s,
        incremented.incremental_s,
        incremented.incremental_s / incremented.full_s,
    )
    output = incremented.result.output
    [timings] = [line for line in output.splitlines() if re.match(r"load [\d.]+ s, ", line)]
    phases = re.findall(r"(\w+) [\d.]+ s", timings)
    # No `train` or `model` (the full run's training), and no `cluster` or `recluster` (its
    # scoring of every pair and the components it cuts): only the new keys are linked.
    assert phases == [
        "load",
        "link",
        "attach",
        "overrides",
        "adjudications",
        "save",
        "crosswalk",
        "silver",
    ]
    assert re.search(r"^model \S+: the live model, untrained$", output, re.MULTILINE)


def test_with_no_live_model_an_incremental_resolve_exits_1_naming_the_full_one(
    cli_env: Path,
) -> None:
    # Before anything is read: an empty bucket stands for any state with no live model.
    result = resolve("--cycle", str(fec_fixture.CYCLE))

    assert result.exit_code == 1
    assert "no live model to resolve with: run `fundlens resolve --full`" in result.output


def test_after_overrides_and_verdicts_an_incremental_resolve_moves_no_key_that_stood(
    incremented_after_verdicts: Incremented,
) -> None:
    incremented = incremented_after_verdicts
    assert incremented.result.exit_code == 0, incremented.result.output
    assert {key: incremented.after[key] for key in incremented.before} == incremented.before
    assert "1 new donors, 0 keys re-pointed, 0 redirects" in incremented.result.output
    # The overrides and the adjudication merge still hold, so the record the incremental run writes
    # over the full run's counts them as that one did.
    before, after = incremented.record_before, incremented.record_after
    assert before is not None and after is not None
    assert (after.overrides, after.adjudications) == (before.overrides, before.adjudications)
    assert after.adjudications > 0
    # `adjudicate` goes on choosing among the clusters before adjudication, now with the new keys.
    database = paths.resolution_database(incremented.snapshot.data_dir)
    with duckdb.connect(database, read_only=True) as con:
        [(clustered, unadjudicated, mixed)] = con.execute(
            """
            SELECT
                (SELECT count(*) FROM cluster),
                (SELECT count(*) FROM unadjudicated),
                (SELECT count(*) FROM cluster AS c JOIN unadjudicated AS u USING (contributor_key)
                    WHERE c.cluster_id <> u.cluster_id)
            """
        ).fetchall()
    assert unadjudicated == clustered
    # The keys the adjudication merged sit apart before it.
    assert mixed > 0
