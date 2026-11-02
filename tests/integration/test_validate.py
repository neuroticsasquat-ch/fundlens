"""`fundlens dime` and `fundlens validate` on the fixture cycle: the DIME file into MinIO, the
resolved donors scored against it into `app.resolution_quality`, and `load` carrying the figures
into `gold_build.meta` (NEU-2054 §8.3, ADR-0009)."""

import csv
from pathlib import Path
from typing import Any

import duckdb
import psycopg
import pytest
from psycopg.rows import dict_row
from typer.testing import CliRunner, Result

from fundlens import cli, paths
from fundlens.r2 import R2
from fundlens.resolve.validate import DIME_VERSION
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.integration.test_load import load, rows
from tests.integration.test_resolve import (
    AGAIN,
    FIXTURE_OVERRIDES,
    MODEL,
    keys_by_sub_id,
    resolve,
)

# A fixture, imported so this module's tests can request it.
from tests.integration.test_resolve import transformed as transformed
from tests.unit.test_fec_fixture import DIME, counted, dime_cids, signed

EXPECTED = fec_fixture.expected()
VALIDATION = EXPECTED["validation"]
TOP = VALIDATION["top"]["limit"]


def run(*args: str) -> Result:
    return CliRunner().invoke(cli.app, list(args))


def dime(path: Path = DIME) -> Result:
    return run("dime", "--cycle", "2024", "--import", str(path))


def validate(*args: str) -> Result:
    return run("validate", "--cycle", "2024", "--top", str(TOP), *args)


@pytest.fixture
def resolved(transformed: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The fixture cycle resolved with the fixture overrides, as model `AGAIN`; the `DATA_DIR`.

    Twice, as the overrides runbook does: the split names a donor_id, which only a first run
    without overrides hands out.
    """
    first = resolve("--full", "--build-id", MODEL)
    assert first.exit_code == 0, first.output
    monkeypatch.setenv("OVERRIDES_PATH", str(FIXTURE_OVERRIDES))
    get_settings.cache_clear()
    again = resolve("--full", "--build-id", AGAIN)
    assert again.exit_code == 0, again.output
    return transformed


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


def test_load_before_validation_leaves_the_figures_null(resolved: Path, migrated_db: str) -> None:
    result = load()

    assert result.exit_code == 0, result.output
    [meta] = rows(migrated_db, "meta")
    columns = ("precision", "recall", "precision_top", "recall_top", "matched_rows", "dime_version")
    assert [meta[column] for column in columns] == [None] * len(columns)
    assert f"quality: not validated for model {AGAIN}" in result.output


def test_validate_before_resolve_says_to_resolve(transformed: Path) -> None:
    assert dime().exit_code == 0

    result = validate()

    assert result.exit_code == 1
    assert "resolve --full" in result.output


def test_validate_without_the_dime_file_names_the_runbook(resolved: Path) -> None:
    result = validate()

    assert result.exit_code == 1
    assert "docs/runbooks/refreshing-dime.md" in result.output
