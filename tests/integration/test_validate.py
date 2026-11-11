"""`fundlens dime` and `fundlens validate` on the fixture cycle: the DIME file into MinIO, the
resolved donors scored against it into `app.resolution_quality`, and `load` carrying the figures
into `gold_build.meta` (NEU-2054 §8.3, ADR-0009); and `fundlens diagnose` taking the working
file's wrong pairs apart (NEU-2182)."""

import csv
import re
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from typer.testing import CliRunner, Result

from fundlens import cli, paths
from fundlens.api.app import create_app
from fundlens.r2 import R2
from fundlens.resolve import adjudicate as adjudication
from fundlens.resolve.validate import DIME_VERSION
from fundlens.settings import Settings, get_settings
from tests import fec_fixture
from tests.fake_adjudicator import FakeAdjudicator
from tests.integration.conftest import (
    cli_pointed_at,
    database_name,
    empty_store,
    scratch_database,
)
from tests.integration.test_load import load, rows
from tests.integration.test_resolve import (
    AGAIN,
    FIXTURE_OVERRIDES,
    MEMORY_LIMIT,
    MODEL,
    clusters,
    donor_keys,
    keys_by_sub_id,
    resolve,
)

# A fixture, imported so this module's tests can request it.
from tests.integration.test_resolve import transformed as transformed
from tests.integration.test_transform import put_bronze, seats_report, transform
from tests.unit.test_fec_fixture import DIME, counted, dime_cids, signed

EXPECTED = fec_fixture.expected()
VALIDATION = EXPECTED["validation"]
TOP = VALIDATION["top"]["limit"]
# The deployed release OTel names for the second resolve, which its run record keeps.
RELEASE = "0123456789abcdef0123456789abcdef01234567"
# The bucket the module's resolved state is built in once, and copied from for each test.
SNAPSHOT_BUCKET = "fundlens-test-snapshot"


def run(*args: str) -> Result:
    return CliRunner().invoke(cli.app, list(args))


def dime(path: Path = DIME) -> Result:
    return run("dime", "--cycle", "2024", "--import", str(path))


def validate(*args: str) -> Result:
    return run("validate", "--cycle", "2024", "--top", str(TOP), *args)


def resolved_env(env: pytest.MonkeyPatch) -> None:
    """The settings the second resolve runs under, and every test after it: the pipeline's DuckDB
    memory limit, the fixture overrides and the release OTel names."""
    env.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
    env.setenv("OVERRIDES_PATH", str(FIXTURE_OVERRIDES))
    env.setenv("OTEL_RESOURCE_ATTRIBUTES", f"service.version={RELEASE}")
    get_settings.cache_clear()


@dataclass(frozen=True)
class Snapshot:
    """The fixture cycle resolved: its `DATA_DIR`, database and bucket."""

    data_dir: Path
    database: str
    store: R2


@pytest.fixture(scope="module")
def snapshot(
    migrated_template: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Snapshot]:
    """The fixture cycle transformed, then resolved with the fixture overrides and the fake
    model's verdicts as model `AGAIN`, once for the module (NEU-2267), in a bucket, database and
    `DATA_DIR` of its own, which `resolved` copies for each test.

    Resolved twice, as the overrides runbook does: the split names a donor_id, which only a first
    run without overrides hands out, and `adjudicate` chooses from the clusters of a run before it.
    """
    data_dir = tmp_path_factory.mktemp("resolved")
    bucket = empty_store(SNAPSHOT_BUCKET)
    with scratch_database(template=migrated_template) as conninfo:
        try:
            with cli_pointed_at(
                conninfo=conninfo, data_dir=data_dir, bucket=SNAPSHOT_BUCKET
            ) as env:
                put_bronze(bucket)
                seats_report()
                transform_run = transform()
                assert transform_run.exit_code == 0, transform_run.output
                env.setenv("DUCKDB_MEMORY_LIMIT", MEMORY_LIMIT)
                get_settings.cache_clear()
                first = resolve("--full", "--build-id", MODEL)
                assert first.exit_code == 0, first.output
                client = FakeAdjudicator()

                def client_for(settings: Settings) -> FakeAdjudicator:
                    return client

                env.setattr(adjudication, "client_for", client_for)
                adjudicated = run("adjudicate")
                assert adjudicated.exit_code == 0, adjudicated.output
                resolved_env(env)
                again = resolve("--full", "--build-id", AGAIN)
                assert again.exit_code == 0, again.output
            yield Snapshot(data_dir, database_name(conninfo), bucket)
        finally:
            bucket.delete_prefix("")


@pytest.fixture
def resolved(
    snapshot: Snapshot,
    store: R2,
    cli_env: Path,
    migrated_db: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """The fixture cycle resolved as `snapshot` left it, copied into the test's own bucket,
    database and `DATA_DIR`, which the test may change; the `DATA_DIR`."""
    shutil.copytree(snapshot.data_dir, cli_env, dirs_exist_ok=True)
    for key in snapshot.store.list_keys(""):
        store.client.copy_object(
            Bucket=store.bucket, Key=key, CopySource={"Bucket": snapshot.store.bucket, "Key": key}
        )
    # The test's database, under its own name, made over as a copy of the snapshot's.
    name = sql.Identifier(database_name(migrated_db))
    with psycopg.connect(make_conninfo(migrated_db, dbname="postgres"), autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(name))
        conn.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                name, sql.Identifier(snapshot.database)
            )
        )
    resolved_env(monkeypatch)
    return cli_env


def quality(conninfo: str) -> dict[str, dict[str, Any]]:
    with psycopg.connect(conninfo) as conn:
        found = (
            conn.cursor(row_factory=dict_row)
            .execute("SELECT * FROM app.resolution_quality ORDER BY scope")
            .fetchall()
        )
    return {row["scope"]: row for row in found}


def pairs(keys: int) -> int:
    return keys * (keys - 1) // 2


def expected_pairs(data_dir: Path, cids: set[str] | None = None) -> int:
    """The true pairs among the counted contributions' keys, from DIME's labels: each person's
    distinct keys, two at a time, over the persons in `cids` (every one when None)."""
    key_of = keys_by_sub_id(data_dir)
    keys: dict[str, set[str]] = {}
    for sub_id, cid in dime_cids().items():
        if cids is None or cid in cids:
            keys.setdefault(cid, set()).add(key_of[sub_id])
    return sum(pairs(len(held)) for held in keys.values())


def top_cids() -> set[str]:
    """The `TOP` DIME persons with the most counted dollars, ties to the lower `cid`."""
    cids = dime_cids()
    dollars: dict[str, int] = {}
    for row in counted():
        cid = cids[int(row["SUB_ID"])]
        dollars[cid] = dollars.get(cid, 0) + signed(row)
    ranked = sorted(dollars, key=lambda cid: (-dollars[cid], cid))
    return set(ranked[:TOP])


def test_dime_import_archives_the_file_and_writes_the_slim_parquet(
    store: R2, cli_env: Path
) -> None:
    result = dime()

    assert result.exit_code == 0, result.output
    matched = VALIDATION["matched_rows"]
    assert f"rows kept: {matched}" in result.output
    assert store.get(paths.reference_dime_raw(DIME_VERSION, 2024)) == DIME.read_bytes()
    parquet = paths.local_path(cli_env, paths.reference_dime(DIME_VERSION, 2024))
    assert store.get(paths.reference_dime(DIME_VERSION, 2024)) == parquet.read_bytes()
    with duckdb.connect() as con:
        [(count,)] = con.execute("SELECT count(*) FROM read_parquet(?)", [str(parquet)]).fetchall()
    assert count == matched


def test_validate_scores_the_fixture_as_expected_yaml_says(
    resolved: Path, migrated_db: str
) -> None:
    assert dime().exit_code == 0

    result = validate()

    assert result.exit_code == 0, result.output
    found = quality(migrated_db)
    assert set(found) == {"overall", "top"}
    true_pairs = expected_pairs(resolved)
    top_pairs = expected_pairs(resolved, top_cids())
    # The planted hard cases make pairs to find in both scopes, so 1.0 is a finding, not a default.
    assert true_pairs > 0 and top_pairs > 0
    scopes: list[tuple[str, fec_fixture.Scores, int]] = [
        ("overall", VALIDATION["overall"], true_pairs),
        ("top", VALIDATION["top"], top_pairs),
    ]
    for scope, figures, pairs_in_scope in scopes:
        row = found[scope]
        assert (row["model_version"], row["cycle"], row["dime_version"]) == (
            AGAIN,
            2024,
            VALIDATION["dime_version"],
        )
        assert (float(row["precision"]), float(row["recall"])) == (
            figures["precision"],
            figures["recall"],
        )
        assert row["contribution_rows"] == EXPECTED["silver"]["contribution"]
        assert row["matched_rows"] == VALIDATION["matched_rows"]
        assert row["correct_pairs"] == row["predicted_pairs"] == row["true_pairs"] == pairs_in_scope
    assert found["overall"]["labelled_keys"] == VALIDATION["labelled_keys"]
    assert (found["overall"]["top_limit"], found["top"]["top_limit"]) == (None, TOP)
    assert (
        f"overall     1.0000    1.0000 {VALIDATION['labelled_keys']:>10} {true_pairs:>12}"
        in result.output
    )
    assert f"top {TOP}" in result.output
    contributions = EXPECTED["silver"]["contribution"]
    assert f"matched {VALIDATION['matched_rows']} of {contributions}" in result.output
    assert f"model {AGAIN}, DIME v{DIME_VERSION}" in result.output


def test_validating_again_rewrites_the_same_two_rows(resolved: Path, migrated_db: str) -> None:
    assert dime().exit_code == 0
    assert validate().exit_code == 0
    first = quality(migrated_db)

    again = validate()

    assert again.exit_code == 0, again.output
    second = quality(migrated_db)
    assert set(second) == {"overall", "top"}
    for scope in second:
        assert second[scope]["validated_at"] > first[scope]["validated_at"]
        moved = {"validated_at"}
        assert {k: v for k, v in second[scope].items() if k not in moved} == {
            k: v for k, v in first[scope].items() if k not in moved
        }


def test_a_label_that_no_longer_joins_leaves_its_contribution_unmatched(
    resolved: Path, migrated_db: str, tmp_path: Path
) -> None:
    with DIME.open(newline="") as f:
        table = list(csv.reader(f))
    column = table[0].index("efec.transaction.id.orig")
    table[1][column] = "SA11AI.NOWHERE"
    altered = tmp_path / "contribDB_2024.csv"
    with altered.open("w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(table)
    assert dime(altered).exit_code == 0

    result = validate()

    assert result.exit_code == 0, result.output
    assert quality(migrated_db)["overall"]["matched_rows"] == VALIDATION["matched_rows"] - 1


def test_dimes_cents_still_meet_the_bulk_files_whole_dollars(
    resolved: Path, migrated_db: str, tmp_path: Path
) -> None:
    # FEC's bulk file drops cents that DIME keeps: 260.25 in DIME is 260 in bronze.
    with DIME.open(newline="") as f:
        table = list(csv.reader(f))
    column = table[0].index("amount")
    table[1][column] = f"{table[1][column]}.25"
    altered = tmp_path / "contribDB_2024.csv"
    with altered.open("w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(table)
    assert dime(altered).exit_code == 0

    result = validate()

    assert result.exit_code == 0, result.output
    assert quality(migrated_db)["overall"]["matched_rows"] == VALIDATION["matched_rows"]


def test_load_carries_the_live_models_figures_into_meta(resolved: Path, migrated_db: str) -> None:
    assert dime().exit_code == 0
    assert validate().exit_code == 0

    result = load()

    assert result.exit_code == 0, result.output
    [meta] = rows(migrated_db, "meta")
    figures = VALIDATION["overall"], VALIDATION["top"]
    assert [
        float(meta[column]) for column in ("precision", "recall", "precision_top", "recall_top")
    ] == [
        figures[0]["precision"],
        figures[0]["recall"],
        figures[1]["precision"],
        figures[1]["recall"],
    ]
    assert (meta["matched_rows"], meta["dime_version"]) == (
        VALIDATION["matched_rows"],
        VALIDATION["dime_version"],
    )
    assert "quality: precision 1.0000 recall 1.0000 (top 1.0000/1.0000)" in result.output
    # The fixture overrides' merge and split, and the fake model's one confident merge.
    assert (
        meta["model_version"],
        meta["resolver_version"],
        meta["overrides_count"],
        meta["adjudications_applied"],
    ) == (AGAIN, RELEASE, 2, 1)
    assert f"resolution: release {RELEASE}, 2 overrides, 1 adjudications applied" in (result.output)


def test_meta_serves_the_fixture_builds_figures(resolved: Path, migrated_db: str) -> None:
    assert dime().exit_code == 0
    assert validate().exit_code == 0
    assert load().exit_code == 0
    # The publish swap, without its purge or marker: the fixture build is live.
    with psycopg.connect(migrated_db, autocommit=True) as conn:
        conn.execute("ALTER SCHEMA gold_build RENAME TO gold")
        conn.execute("UPDATE gold.meta SET published_at = now()")
    settings = get_settings().model_copy(update={"database_url": migrated_db})

    with TestClient(create_app(settings)) as client:
        response = client.get("/v1/meta")

    assert response.status_code == 200, response.text
    body = response.json()
    overall, top = VALIDATION["overall"], VALIDATION["top"]
    assert {
        key: body[key] for key in body if key not in ("build_id", "published_at", "cycles")
    } == {
        "resolver_version": RELEASE,
        "model_version": AGAIN,
        "overrides_count": 2,
        "adjudications_applied": 1,
        "precision": overall["precision"],
        "recall": overall["recall"],
        "precision_top": top["precision"],
        "recall_top": top["recall"],
        "matched_rows": VALIDATION["matched_rows"],
        "dime_version": VALIDATION["dime_version"],
    }


def test_load_of_a_model_without_a_run_record_leaves_its_fields_null(
    resolved: Path, migrated_db: str, store: R2
) -> None:
    # As the model trained before NEU-2056 is: saved, with no record beside it.
    store.delete_keys([paths.resolution_run(AGAIN)])

    result = load()

    assert result.exit_code == 0, result.output
    [meta] = rows(migrated_db, "meta")
    assert meta["model_version"] == AGAIN
    columns = ("resolver_version", "overrides_count", "adjudications_applied")
    assert [meta[column] for column in columns] == [None] * len(columns)
    assert "resolution: " not in result.output


def test_load_before_validation_leaves_the_figures_null(resolved: Path, migrated_db: str) -> None:
    result = load()

    assert result.exit_code == 0, result.output
    [meta] = rows(migrated_db, "meta")
    columns = ("precision", "recall", "precision_top", "recall_top", "matched_rows", "dime_version")
    assert [meta[column] for column in columns] == [None] * len(columns)
    assert f"quality: not validated for model {AGAIN}" in result.output
    # What the run applied does not wait for validation.
    assert (meta["model_version"], meta["overrides_count"]) == (AGAIN, 2)


def test_validating_the_working_files_clusters_writes_nothing(
    resolved: Path, migrated_db: str
) -> None:
    assert dime().exit_code == 0
    # A cap under the Musk case's four keys cuts it in two: pairs DIME holds that the clusters
    # do not.
    capped = run("recluster", "--max-keys", "3")
    assert capped.exit_code == 0, capped.output

    result = validate("--clusters")

    assert result.exit_code == 0, result.output
    assert quality(migrated_db) == {}
    last = result.output.strip().splitlines()[-1]
    assert last == f"clusters from {paths.resolution_database(resolved)}; nothing written"
    overall = next(line for line in result.output.splitlines() if line.startswith("overall"))
    precision, recall = (float(figure) for figure in overall.split()[1:3])
    assert precision == 1.0
    assert recall < 1.0


def test_validating_clusters_without_a_working_file_says_to_resolve(resolved: Path) -> None:
    assert dime().exit_code == 0
    paths.resolution_database(resolved).unlink()

    result = validate("--clusters")

    assert result.exit_code == 1
    assert "run `fundlens resolve --full`" in result.output


def test_validating_clusters_that_miss_a_labelled_key_says_to_resolve(
    resolved: Path, migrated_db: str
) -> None:
    assert dime().exit_code == 0
    with duckdb.connect(paths.resolution_database(resolved)) as con:
        con.execute(
            "DELETE FROM cluster WHERE contributor_key = (SELECT min(contributor_key) FROM cluster)"
        )

    result = validate("--clusters")

    assert result.exit_code == 1
    assert "1 labelled contributor keys are in no cluster of" in result.output
    assert "run `fundlens resolve --full`" in result.output
    assert quality(migrated_db) == {}


def test_validate_before_resolve_says_to_resolve(transformed: Path) -> None:
    assert dime().exit_code == 0

    result = validate()

    assert result.exit_code == 1
    assert "resolve --full" in result.output


def test_validate_without_the_dime_file_names_the_runbook(resolved: Path) -> None:
    result = validate()

    assert result.exit_code == 1
    assert "docs/runbooks/refreshing-dime.md" in result.output


DIRECT_PATTERN = ["null", "exact", "exact", "exact", "differ"]


def diagnose(*args: str) -> Result:
    return run("diagnose", "--cycle", "2024", *args)


def test_diagnose_finds_a_planted_direct_and_chained_wrong_pair_and_writes_nothing(
    resolved: Path, migrated_db: str
) -> None:
    assert dime().exit_code == 0
    assert validate().exit_code == 0
    before = quality(migrated_db)
    clean = diagnose()
    assert clean.exit_code == 0, clean.output
    assert re.search(r"pairs: (\d+) predicted, \1 correct, 0 wrong", clean.output), clean.output
    # DESMOND into BEATRICE's cluster: a wrong pair with the bridge, which has an edge to him,
    # and one with BEATRICE, which has none.
    [beatrice, bridge] = sorted(donor_keys(resolved, "chain_end_beatrice"))
    [desmond] = donor_keys(resolved, "chain_end_desmond")
    target = clusters(resolved)[beatrice]
    with duckdb.connect(paths.resolution_database(resolved)) as con:
        con.execute(
            "UPDATE cluster SET cluster_id = $target WHERE contributor_key = $key",
            {"target": target, "key": desmond},
        )

    result = diagnose("--sample", "5")

    assert result.exit_code == 0, result.output
    assert re.search(r"pairs: \d+ predicted, \d+ correct, 2 wrong", result.output), result.output
    lines = result.output.splitlines()

    def wrong(label: str) -> int:
        [line] = [line for line in lines if line.startswith(f"{label} ")]
        return int(line[len(label) :].split()[0])

    assert wrong("chained") == 1
    assert (
        sum(wrong(band) for band in ("direct 0.95–0.99", "direct 0.99–0.999", "direct ≥ 0.999"))
        == 1
    )
    # Both wrong pairs are in one three-key cluster.
    assert wrong("3–5") == 2
    # The direct one, bridge and DESMOND: no first name on the bridge, occupations that differ.
    [pattern] = [line.split() for line in lines if line.split()[:5] == DIRECT_PATTERN]
    assert int(pattern[5]) == 1
    sampled = [line for line in lines if line.startswith("sample ")]
    assert len(sampled) == 2
    assert all(f"cluster {target} (3 keys)" in line for line in sampled)
    assert any(line.endswith(", chained") for line in sampled)
    assert all(f"  {key} cid " in result.output for key in (beatrice, bridge, desmond))
    assert result.output.rstrip().endswith(
        f"clusters from {paths.resolution_database(resolved)}; nothing written"
    )
    assert quality(migrated_db) == before


def test_diagnose_without_a_working_file_says_to_resolve(resolved: Path, migrated_db: str) -> None:
    paths.resolution_database(resolved).unlink()

    result = diagnose()

    assert result.exit_code == 1
    assert "run `fundlens resolve --full`" in result.output
