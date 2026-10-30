"""`fundlens transform` on the fixture cycle, against MinIO bronze and a migrated Postgres
(spec §5.3)."""

import io
import zipfile
from collections.abc import Iterator, Mapping
from datetime import date
from pathlib import Path

import duckdb
import pytest
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.fec.files import FecFile, files_for
from fundlens.paths import SilverTable
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import ChecksFailed
from tests import fec_fixture
from tests.fake_fec import zipped
from tests.integration.conftest import TEST_BUCKET

BUILD = "20261030T030000Z"
TABLES: tuple[SilverTable, ...] = ("committee", "candidate", "candidate_committee_link")
# The fixture's filing for Maryland's 9th district, which the 2020 census did not draw.
BAD = "H4MD09109"


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
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    yield tmp_path / "data"
    get_settings.cache_clear()


def put_bronze(store: R2, cycle: int = 2024, texts: Mapping[FecFile, str] | None = None) -> None:
    """Every file of `cycle` in bronze: the fixture's, or the text `texts` gives for it."""
    texts = texts or {}
    for bulk in files_for(cycle):
        text = texts.get(bulk.name, fec_fixture.bulk_text(bulk.name))
        body = zipped(fec_fixture.MEMBERS[bulk.name], text)
        store.put(paths.bronze_zip(cycle, bulk.name, date(2026, 10, 30)), body)


def run(*args: str) -> Result:
    return CliRunner().invoke(cli.app, [*args, "--build-id", BUILD])


def seats_report(cycle: int = 2024) -> None:
    result = run("seats", "--cycle", str(cycle), "--report")
    assert result.exit_code == 0, result.output


def transform(cycle: int = 2024) -> Result:
    return run("transform", "--cycle", str(cycle))


def read_silver(
    store: R2, table: SilverTable, tmp_path: Path, cycle: int = 2024
) -> list[dict[str, object]]:
    """The rows of one uploaded silver partition, fetched back from MinIO."""
    key = f"{paths.silver_partition(table, cycle, BUILD)}/{paths.part(0)}"
    local = store.download_to(key, tmp_path / "fetched" / f"{table}.parquet")
    with duckdb.connect() as con:
        # The file's own columns: DuckDB would otherwise add `build` from a hive-style path.
        cursor = con.execute(f"SELECT * FROM read_parquet('{local}', hive_partitioning = false)")
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def uploaded_silver(store: R2) -> list[str]:
    """Every silver key but the `race` partition `seats` writes."""
    return [key for key in store.list_keys("silver/") if not key.startswith("silver/race/")]


def test_transform_writes_the_fixture_tables_and_the_marker(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    expected = fec_fixture.expected()
    counts = {table: expected["silver"][table] for table in TABLES}
    marker = markers.read("transformed", store, cycle=2024, build_id=BUILD)
    assert marker is not None
    assert marker.row_counts == counts
    for table in TABLES:
        assert f"{table}: {counts[table]} rows" in result.output
        assert len(read_silver(store, table, tmp_path)) == counts[table]

    committees = read_silver(store, "committee", tmp_path)
    assert list(committees[0]) == [
        "cycle",
        "committee_id",
        "source",
        "jurisdiction",
        "name",
        "treasurer",
        "street",
        "city",
        "state",
        "zip",
        "designation",
        "type",
        "party",
        "filing_frequency",
        "org_type",
        "connected_org",
        "candidate_id",
        "is_conduit",
    ]
    conduits = {row["committee_id"] for row in committees if row["is_conduit"]}
    assert conduits == set(expected["contributions"]["earmarked"])
    assert {(row["source"], row["jurisdiction"], row["cycle"]) for row in committees} == {
        ("fec", "US", 2024)
    }

    candidates = read_silver(store, "candidate", tmp_path)
    assert list(candidates[0]) == [
        "cycle",
        "candidate_id",
        "source",
        "jurisdiction",
        "name",
        "party",
        "election_year",
        "office",
        "state",
        "district",
        "incumbent_challenger_open",
        "status",
        "principal_committee_id",
        "race_id",
    ]
    assert {row["candidate_id"]: row["race_id"] for row in candidates} == {
        candidate_id: totals["race_id"] for candidate_id, totals in expected["candidates"].items()
    }

    links = read_silver(store, "candidate_committee_link", tmp_path)
    assert list(links[0]) == [
        "cycle",
        "candidate_id",
        "committee_id",
        "source",
        "jurisdiction",
        "committee_type",
        "designation",
        "linkage_id",
    ]
    # OKAFOR's principal and authorized committees.
    designations = {row["committee_id"]: row["designation"] for row in links}
    assert (designations["C00800103"], designations["C00800113"]) == ("P", "A")


def test_the_race_check_fails_until_the_bad_district_is_an_unmatched_filing(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    put_bronze(store)

    # No `seats --report` yet: app.unmatched_filing does not hold the filing.
    failed = transform()

    assert isinstance(failed.exception, ChecksFailed)
    assert "silver_candidate_race.sql" in str(failed.exception)
    assert BAD in str(failed.exception)
    assert uploaded_silver(store) == []
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)

    seats_report()
    result = transform()

    assert result.exit_code == 0, result.output
    fenwick = [
        row for row in read_silver(store, "candidate", tmp_path) if row["candidate_id"] == BAD
    ]
    assert fenwick == [fenwick[0] | {"district": "09", "race_id": None}]


def test_a_duplicated_committee_aborts_the_run_before_any_upload(store: R2, cli_env: Path) -> None:
    cm = fec_fixture.bulk_text("cm")
    put_bronze(store, texts={"cm": cm + cm.splitlines(keepends=True)[2]})
    seats_report()

    result = transform()

    assert isinstance(result.exception, ChecksFailed)
    assert "silver_committee_key.sql" in str(result.exception)
    # The other checks pass: only the duplicate is reported.
    assert "silver_candidate_race.sql" not in str(result.exception)
    assert uploaded_silver(store) == []
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)
    assert not (cli_env / "silver" / "committee").exists()


def test_a_zip_is_read_by_its_member_name_not_as_its_only_file(store: R2, cli_env: Path) -> None:
    put_bronze(store)
    # FEC's `indiv` zip holds the same rows twice, the second time split by date under
    # `by_date/`. Read as well, a copy like this would trip the committee key check.
    cm = fec_fixture.bulk_text("cm")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("cm.txt", cm)
        archive.writestr("by_date/cm_2024.txt", cm)
    store.put(paths.bronze_zip(2024, "cm", date(2026, 10, 31)), buffer.getvalue())
    seats_report()

    result = transform()

    assert result.exit_code == 0, result.output
    assert "committee: 17 rows" in result.output


def test_a_filing_for_a_seat_with_a_special_beside_it_joins_the_regular_race(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # Nebraska elects a regular class 1 senator and fills its class 2 seat in 2024.
    nebraska = "S4NE00120|DOE, JANE|DEM|2024|NE|S|00|C|C||1 MAIN ST||OMAHA|NE|68102\n"
    put_bronze(store, texts={"cn": fec_fixture.bulk_text("cn") + nebraska})
    seats_report()

    assert transform().exit_code == 0
    races = {
        row["candidate_id"]: row["race_id"] for row in read_silver(store, "candidate", tmp_path)
    }
    assert races["S4NE00120"] == "2024-S-NE-00"


def test_a_filing_for_a_lone_special_joins_it_and_a_later_cycles_filing_joins_nothing(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    # Ohio's 2026 Senate race is only the special: neither of its classes is up.
    cn = (
        "S6OH00130|ROE, SAM|REP|2026|OH|S|00|C|C||1 HIGH ST||COLUMBUS|OH|43215\n"
        # Registered in the 2026 file for the 2028 race: it stands in no 2026 race, and the
        # race check leaves it alone.
        "S8MD00140|LOE, KIM|DEM|2028|MD|S|00|C|C||2 HIGH ST||BALTIMORE|MD|21201\n"
    )
    put_bronze(
        store, 2026, texts={"cm": "", "cn": cn, "ccl": "", "indiv": "", "pas2": "", "oth": ""}
    )

    result = transform(2026)

    assert result.exit_code == 0, result.output
    candidates = read_silver(store, "candidate", tmp_path, cycle=2026)
    assert {row["candidate_id"]: row["race_id"] for row in candidates} == {
        "S6OH00130": "2026-S-OH-00-special",
        "S8MD00140": None,
    }


def test_a_pair_linked_for_two_elections_keeps_this_cycles_link(
    store: R2, cli_env: Path, tmp_path: Path
) -> None:
    later = "P40000101|2028|2024|C00800101|P|P|124000000099\n"
    put_bronze(store, texts={"ccl": fec_fixture.bulk_text("ccl") + later})
    seats_report()

    assert transform().exit_code == 0
    links = read_silver(store, "candidate_committee_link", tmp_path)
    assert len(links) == fec_fixture.expected()["silver"]["candidate_committee_link"]
    hargrove = [row["linkage_id"] for row in links if row["candidate_id"] == "P40000101"]
    assert hargrove == [124000000001]


def test_transform_without_bronze_says_to_extract(store: R2, cli_env: Path) -> None:
    result = transform()

    assert result.exit_code == 1
    assert "fundlens extract --cycle 2024" in result.output
    assert not markers.exists("transformed", store, cycle=2024, build_id=BUILD)


def test_an_odd_cycle_is_a_usage_error(store: R2, cli_env: Path) -> None:
    assert transform(2025).exit_code == 2
