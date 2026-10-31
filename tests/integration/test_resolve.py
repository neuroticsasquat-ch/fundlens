"""`fundlens resolve --full` on the fixture cycle: its contributor keys into clusters, the model
into MinIO, under a DuckDB memory limit (spec §6.3–§6.4, §12)."""

import json
import logging
from pathlib import Path

import duckdb
import pytest
from splink import DuckDBAPI
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.r2 import R2
from fundlens.resolve import model
from fundlens.resolve.cluster import cluster
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.test_transform import BUILD, put_bronze, seats_report, transform

MODEL = "20261031T040000Z"
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
            [str(part / "*.parquet")],
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
    assert marker.row_counts == {"cluster": fec_fixture.expected()["silver"]["contributor"]}
    logged = [record.getMessage() for record in caplog.records]
    for phase in ("load", "train", "cluster", "save"):
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
