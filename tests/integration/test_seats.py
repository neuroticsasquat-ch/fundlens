"""`fundlens seats --report` against MinIO bronze and a migrated Postgres (spec §5.2)."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import duckdb
import psycopg
import pytest
from typer.testing import CliRunner

from fundlens import cli, paths
from fundlens.r2 import R2
from fundlens.settings import get_settings
from tests.fake_fec import zipped
from tests.integration.conftest import TEST_BUCKET

BUILD = "20261030T030000Z"
CN_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/fec/2026/cn.txt"
# The fixture's filing for Maryland's 9th district, which the 2020 census did not draw.
BAD = "H6MD09102"


@pytest.fixture
def cli_env(
    monkeypatch: pytest.MonkeyPatch, store: R2, migrated_db: str, tmp_path: Path
) -> Iterator[Path]:
    """Point the CLI's settings at the test bucket, a migrated database and a scratch
    `DATA_DIR`."""

    def leave_logging_alone(level: str) -> None:
        # The callback reconfigures the root logger, which would outlive the test.
        pass

    monkeypatch.setattr(cli, "configure_logging", leave_logging_alone)
    monkeypatch.setenv("R2_BUCKET", TEST_BUCKET)
    monkeypatch.setenv("DATABASE_URL", migrated_db)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def put_cn(store: R2, text: str, downloaded: date = date(2026, 10, 30)) -> None:
    store.put(paths.bronze_zip(2026, "cn", downloaded), zipped("cn.txt", text))


def report(*extra: str) -> str:
    result = CliRunner().invoke(
        cli.app, ["seats", "--cycle", "2026", "--report", "--build-id", BUILD, *extra]
    )
    assert result.exit_code == 0, result.output
    return result.output


def unmatched_rows(conninfo: str) -> list[tuple[object, ...]]:
    with psycopg.connect(conninfo) as conn:
        return conn.execute(
            "SELECT cycle, candidate_id, office, state, district FROM app.unmatched_filing"
            " ORDER BY candidate_id"
        ).fetchall()


def test_the_report_records_the_bad_district_filing_and_creates_no_race(
    store: R2, cli_env: Path, migrated_db: str
) -> None:
    # An older download that the newest one supersedes: only the newest is read.
    put_cn(store, "H6MD00199|OLD, ROW|DEM|2026|MD|H|11|C|C|C00900099||||MD|\n", date(2026, 10, 1))
    put_cn(store, CN_FIXTURE.read_text())

    output = report()

    assert f"unmatched: {BAD} H MD-09" in output
    assert "1 unmatched filings recorded" in output
    assert unmatched_rows(migrated_db) == [(2026, BAD, "H", "MD", "09")]

    key = f"{paths.silver_partition('race', 2026, BUILD)}/{paths.part(0)}"
    assert store.exists(key)
    local = paths.local_path(cli_env, key)
    # The file's own columns: DuckDB would otherwise add `build` from the hive-style path.
    written = f"read_parquet('{local}', hive_partitioning = false)"
    with duckdb.connect() as con:
        race_ids = {row[0] for row in con.execute(f"SELECT race_id FROM {written}").fetchall()}
        columns = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM {written}").fetchall()]
    assert columns == [
        "race_id",
        "cycle",
        "jurisdiction",
        "office",
        "state",
        "district",
        "is_special",
        "slug",
    ]
    assert "2026-H-MD-09" not in race_ids
    # 435 voting seats, five delegates (no Puerto Rico), class 2's 33 seats and two specials.
    assert len(race_ids) == 435 + 5 + 33 + 2
    assert {"2026-H-MD-05", "2026-S-GA-00", "2026-S-OH-00-special"} <= race_ids


def test_a_filing_that_now_matches_leaves_the_table(
    store: R2, cli_env: Path, migrated_db: str
) -> None:
    put_cn(store, CN_FIXTURE.read_text())
    report()
    with psycopg.connect(migrated_db) as conn:
        [(first_seen,)] = conn.execute("SELECT seen_at FROM app.unmatched_filing").fetchall()

    # The same filing, still unmatched, keeps the time it was first seen.
    report()
    with psycopg.connect(migrated_db) as conn:
        assert conn.execute("SELECT seen_at FROM app.unmatched_filing").fetchall() == [
            (first_seen,)
        ]

    # Corrected to the 8th district, it matches a seat.
    put_cn(store, CN_FIXTURE.read_text().replace("|MD|H|09|", "|MD|H|08|"), date(2026, 11, 6))
    assert "0 unmatched filings recorded" in report()
    assert unmatched_rows(migrated_db) == []


def test_the_report_without_a_cn_download_says_to_extract_it(store: R2, cli_env: Path) -> None:
    result = CliRunner().invoke(cli.app, ["seats", "--cycle", "2026", "--report"])

    assert result.exit_code == 1
    assert "fundlens extract --cycle 2026 --file cn" in result.output


def test_seats_without_the_report_needs_no_database(
    store: R2, cli_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
    get_settings.cache_clear()

    result = CliRunner().invoke(cli.app, ["seats", "--cycle", "2024", "--build-id", BUILD])

    assert result.exit_code == 0, result.output
    assert "house: 441 races (0 special)" in result.output
    assert "senate: 35 races (2 special)" in result.output
    assert "president: 1 races (0 special)" in result.output
    assert store.exists(f"{paths.silver_partition('race', 2024, BUILD)}/{paths.part(0)}")


def test_an_odd_cycle_is_a_usage_error(store: R2, cli_env: Path) -> None:
    result = CliRunner().invoke(cli.app, ["seats", "--cycle", "2025"])

    assert result.exit_code == 2
