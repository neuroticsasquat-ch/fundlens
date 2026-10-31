"""`fundlens resolve --full` on the fixture cycle: its contributor keys into clusters, the model
into MinIO, under a DuckDB memory limit (spec §6.3–§6.4, §12)."""

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

import duckdb
import psycopg
import pytest
from splink import DuckDBAPI
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.r2 import R2
from fundlens.resolve import crosswalk, model
from fundlens.resolve.cluster import cluster
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.test_transform import BUILD, put_bronze, seats_report, transform

MODEL = "20261031T040000Z"
AGAIN = "20261107T040000Z"
# Well under what DuckDB would take by itself: the run has to fit, or spill, inside it.
MEMORY_LIMIT = "256MB"
# The hard cases linkage leaves alone: resolution/overrides.yaml merges and splits these.
FOR_OVERRIDES = frozenset({"merge_override", "split_override"})


def resolve(*args: str) -> Result:
    return CliRunner().invoke(cli.app, ["resolve", *args])


@pytest.fixture
def transformed(store: R2, cli_env: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The fixture cycle transformed as build `BUILD`, with the pipeline's DuckDB memory limit
    set; the `DATA_DIR`."""
    put_bronze(store)
    seats_report()
    result = transform()
    assert result.exit_code == 0, result.output
    monkeypatch.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
    get_settings.cache_clear()
    return cli_env


def clusters(data_dir: Path) -> dict[str, str]:
    """Each contributor key's cluster, from resolution's working file."""
    with duckdb.connect(paths.resolution_database(data_dir), read_only=True) as con:
        return dict(con.execute("SELECT contributor_key, cluster_id FROM cluster").fetchall())


def keys_by_sub_id(data_dir: Path) -> dict[int, str]:
    """Each counted contribution's contributor key, from the transformed silver."""
    part = paths.local_path(data_dir, paths.silver_partition("contribution", 2024, BUILD))
    with duckdb.connect() as con:
        rows = con.execute(
            "SELECT source_record_id, contributor_key"
            " FROM read_parquet(?, hive_partitioning = false)",
            [str(part / "**" / "*.parquet")],
        ).fetchall()
    return {int(sub_id): key for sub_id, key in rows}


def partition(groups: dict[str, str]) -> set[frozenset[str]]:
    members: dict[str, set[str]] = {}
    for key, group in groups.items():
        members.setdefault(group, set()).add(key)
    return {frozenset(keys) for keys in members.values()}


def test_resolve_full_clusters_the_fixture_as_its_donors(transformed: Path) -> None:
    result = resolve("--full", "--build-id", MODEL)

    assert result.exit_code == 0, result.output
    expected = fec_fixture.expected()
    key_of = keys_by_sub_id(transformed)
    donor_keys = {
        name: {key_of[sub_id] for sub_id in donor["sub_ids"]}
        for name, donor in expected["donors"].items()
    }
    found = clusters(transformed)
    # Every key is one donor's, so a key outside the planted donors is a donor of its own: the
    # keys less those the planted donors share make the fixture's distinct donors.
    shared = sum(len(keys) - 1 for keys in donor_keys.values())
    assert len(found) - shared == expected["distinct_donors"]
    reserved = {
        key
        for name, keys in donor_keys.items()
        if expected["donors"][name]["resolved_by"] in FOR_OVERRIDES
        for key in keys
    }
    donor_of = {key: name for name, keys in donor_keys.items() for key in keys}
    truth = {key: donor_of.get(key, key) for key in found if key not in reserved}
    linked = {key: cluster_id for key, cluster_id in found.items() if key not in reserved}
    # Linkage puts every donor's keys together, and nobody else's with them.
    assert partition(linked) == partition(truth)
    assert not {found[key] for key in reserved} & set(linked.values())
    assert len({found[key] for key in donor_keys["musk_case"]}) == 1
    assert len(donor_keys["musk_case"]) == 4
    md, tx = donor_keys["same_name_md"], donor_keys["same_name_tx"]
    assert {found[key] for key in md}.isdisjoint(found[key] for key in tx)


def test_resolve_full_saves_a_model_that_reloads_without_training(
    store: R2, transformed: Path
) -> None:
    result = resolve("--full", "--build-id", MODEL)

    assert result.exit_code == 0, result.output
    key = paths.resolution_model(MODEL)
    local = paths.local_path(transformed, key)
    assert store.get(key) == local.read_bytes()
    saved = json.loads(store.get(key))
    run = clusters(transformed)
    with duckdb.connect() as con:
        con.execute(f"ATTACH '{paths.resolution_database(transformed)}' AS run (READ_ONLY)")
        con.execute("CREATE TABLE contributor AS FROM run.contributor")
        con.execute("DETACH run")
        reloaded = model.linker(DuckDBAPI(con), "contributor", saved)
        settings = get_settings()
        cluster(
            reloaded,
            con,
            match_threshold=settings.resolve_match_threshold,
            cluster_threshold=settings.resolve_cluster_threshold,
        )
        again = dict(con.execute("SELECT contributor_key, cluster_id FROM cluster").fetchall())
    assert partition(again) == partition(run)


def test_resolve_full_marks_the_cycle_resolved_and_logs_each_phase(
    store: R2, transformed: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="fundlens.resolve")

    result = resolve("--full", "--build-id", MODEL)

    assert result.exit_code == 0, result.output
    marker = markers.read("resolved", store, cycle=2024, build_id=BUILD)
    assert marker is not None
    silver = fec_fixture.expected()["silver"]
    assert marker.row_counts == {
        "cluster": silver["contributor"],
        "contribution": silver["contribution"],
    }
    logged = [record.getMessage() for record in caplog.records]
    for phase in ("load", "train", "cluster", "save", "crosswalk", "silver"):
        assert any(message.startswith(f"resolve {phase}: ") for message in logged), phase
    # The run's connection had the limit, and kept to it: DuckDB fails a query that exceeds it.
    assert "DuckDB memory limit: 244.1 MiB" in result.output
    assert "priors (too few keys to train on)" in result.output


def test_resolve_full_with_nothing_transformed_says_to_transform(cli_env: Path) -> None:
    result = resolve("--full")

    assert result.exit_code == 1
    assert "run `fundlens transform`" in result.output


def test_resolve_without_full_is_a_usage_error(cli_env: Path) -> None:
    result = resolve()

    assert result.exit_code == 2
    assert "--full" in result.output


def crosswalk_rows(conninfo: str) -> list[tuple[Any, ...]]:
    with psycopg.connect(conninfo) as conn:
        return conn.execute("SELECT * FROM app.crosswalk ORDER BY contributor_key").fetchall()


def drawn(conninfo: str) -> tuple[int, bool]:
    with psycopg.connect(conninfo) as conn:
        row = conn.execute("SELECT last_value, is_called FROM app.donor_id_seq").fetchone()
    assert row is not None
    return row[0], row[1]


def test_resolve_full_gives_each_cluster_one_donor_id_and_a_rerun_changes_none(
    transformed: Path, migrated_db: str
) -> None:
    first = resolve("--full", "--build-id", MODEL)
    assert first.exit_code == 0, first.output
    rows, sequence = crosswalk_rows(migrated_db), drawn(migrated_db)
    silver = paths.local_path(transformed, "silver")
    written = {part: part.stat().st_mtime_ns for part in silver.rglob("*.parquet")}

    again = resolve("--full", "--build-id", AGAIN)

    assert again.exit_code == 0, again.output
    found = clusters(transformed)
    assert len(rows) == len(found)
    donor_of = {key: donor_id for key, donor_id, _, _ in rows}
    # One id per cluster, and one cluster per id.
    assert partition({key: str(donor_id) for key, donor_id in donor_of.items()}) == partition(found)
    assert {build_id for *_, build_id in rows} == {MODEL}
    assert crosswalk_rows(migrated_db) == rows
    assert drawn(migrated_db) == sequence
    assert "crosswalk: 0 new donors, 0 keys re-pointed, 0 redirects" in again.output
    # Nothing changed, so no cycle's silver was rewritten.
    assert {part: part.stat().st_mtime_ns for part in silver.rglob("*.parquet")} == written


def test_moving_a_fixture_key_into_a_heavier_cluster_redirects_its_id_alone(
    transformed: Path, migrated_db: str
) -> None:
    result = resolve("--full", "--build-id", MODEL)
    assert result.exit_code == 0, result.output
    key_of = keys_by_sub_id(transformed)
    donors = fec_fixture.expected()["donors"]
    musk = {key_of[sub_id] for sub_id in donors["musk_case"]["sub_ids"]}
    [moved] = {key_of[sub_id] for sub_id in donors["same_name_tx"]["sub_ids"]}
    # A cluster of one: moving its only key leaves its id carried by nobody.
    found = clusters(transformed)
    assert [key for key, group in found.items() if group == found[moved]] == [moved]
    before = dict((key, donor_id) for key, donor_id, *_ in crosswalk_rows(migrated_db))
    [musk_id] = {before[key] for key in musk}

    with (
        duckdb.connect(paths.resolution_database(transformed)) as con,
        psycopg.connect(migrated_db, autocommit=True) as conn,
    ):
        con.execute(
            "UPDATE cluster SET cluster_id = (SELECT any_value(cluster_id) FROM cluster"
            " WHERE contributor_key = $musk) WHERE contributor_key = $moved",
            {"musk": next(iter(musk)), "moved": moved},
        )
        assigned = crosswalk.assign(
            con, conn, build_id=AGAIN, scratch=paths.scratch_dir(transformed)
        )
        redirects = dict(
            conn.execute("SELECT old_donor_id, donor_id FROM app.donor_redirect").fetchall()
        )

    after = dict((key, donor_id) for key, donor_id, *_ in crosswalk_rows(migrated_db))
    assert redirects == {before[moved]: musk_id}
    assert {after[key] for key in musk | {moved}} == {musk_id}
    assert {key: after[key] for key in after if key != moved} == {
        key: before[key] for key in before if key != moved
    }
    assert assigned == crosswalk.Assigned(keys=len(before), new_donors=0, repointed=1, redirects=1)


def test_resolve_full_writes_donor_ids_onto_bucketed_silver(
    store: R2, transformed: Path, migrated_db: str
) -> None:
    prefix = paths.silver_partition("contribution", 2024, BUILD)
    before = keys_by_sub_id(transformed)

    result = resolve("--full", "--build-id", MODEL)

    assert result.exit_code == 0, result.output
    donor_of = {key: donor_id for key, donor_id, *_ in crosswalk_rows(migrated_db)}
    bucketed = re.compile(re.escape(prefix) + r"/bucket=[0-9a-f]{2}/part-\d{4}\.parquet")
    keys = store.list_keys(prefix + "/")
    assert keys
    assert all(bucketed.fullmatch(key) for key in keys), keys
    local = paths.local_path(transformed, prefix)
    assert sorted(
        p.relative_to(transformed).as_posix() for p in local.rglob("*.parquet")
    ) == sorted(keys)
    with duckdb.connect() as con:
        rows = con.execute(
            "SELECT source_record_id, contributor_key, donor_id,"
            " regexp_extract(filename, 'bucket=([0-9a-f]{2})/', 1)"
            " FROM read_parquet(?, hive_partitioning = false, filename = true)",
            [str(local / "**" / "*.parquet")],
        ).fetchall()
        contributors = con.execute(
            "SELECT contributor_key, donor_id FROM read_parquet(?, hive_partitioning = false)",
            [
                str(
                    paths.local_path(
                        transformed, paths.silver_partition("contributor", 2024, BUILD)
                    )
                    / "*.parquet"
                )
            ],
        ).fetchall()
    assert len(rows) == len(before) == fec_fixture.expected()["silver"]["contribution"]
    assert {int(sub_id): key for sub_id, key, _, _ in rows} == before
    assert all(donor_id == donor_of[key] for _, key, donor_id, _ in rows)
    assert all(bucket == f"{donor_id % paths.BUCKETS:02x}" for *_, donor_id, bucket in rows)
    assert dict(contributors) == donor_of


def test_a_rewrite_that_died_in_r2_stops_load_and_a_new_transform_recovers_it(
    store: R2, transformed: Path
) -> None:
    result = resolve("--full", "--build-id", MODEL)
    assert result.exit_code == 0, result.output
    sentinel = paths.rewrite_sentinel(2024, BUILD)
    # As a rewrite leaves R2 when it dies among the parts, on a box whose cache is gone.
    store.put(sentinel, b"")
    store.put(f"{paths.silver_partition('contribution', 2024, BUILD)}/{paths.part(0)}", b"stale")
    shutil.rmtree(paths.local_path(transformed, "silver"))

    loaded = CliRunner().invoke(cli.app, ["load", "--cycle", "2024", "--build-id", BUILD])
    stuck = resolve("--full", "--build-id", AGAIN)

    assert loaded.exit_code == 1
    assert "died part way: run `fundlens resolve --full` again" in loaded.output
    assert stuck.exit_code == 1
    assert "run `fundlens transform --cycle 2024" in str(stuck.exception)
    assert transform().exit_code == 0
    assert not store.exists(sentinel)
    assert store.list_keys(paths.silver_partition("contribution", 2024, BUILD) + "/") == [
        f"{paths.silver_partition('contribution', 2024, BUILD)}/{paths.part(0)}"
    ]
    recovered = resolve("--full", "--build-id", AGAIN)
    assert recovered.exit_code == 0, recovered.output
    assert len(keys_by_sub_id(transformed)) == fec_fixture.expected()["silver"]["contribution"]
