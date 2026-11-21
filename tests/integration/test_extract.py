"""`fundlens extract` from a fake FEC server into MinIO bronze (spec §3.4, §5.1; ADR-0002)."""

import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import get_args
from urllib.error import HTTPError

import pytest
from typer.testing import CliRunner

from fundlens import cli, markers, paths
from fundlens.fec.extract import (
    LAST_MODIFIED,
    SIZE,
    DownloadError,
    Extracted,
    extract,
    extract_file,
)
from fundlens.fec.files import CATALOGUE, BulkFile, FecFile
from fundlens.r2 import R2
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.fake_fec import FakeFec, zipped
from tests.fec_fixture import SAMPLE, SAMPLE_UNDATED
from tests.integration.conftest import TEST_BUCKET

BUILD = "20261030T030000Z"
# 2026 is the current cycle on both dates, so its zips stay on disk; 2024's do not.
TODAY = date(2026, 10, 30)
NEXT_WEEK = date(2026, 11, 6)
FILES: tuple[FecFile, ...] = get_args(FecFile)


@pytest.fixture
def fec() -> Iterator[FakeFec]:
    with FakeFec().running() as fake:
        yield fake


def publish_all(fec: FakeFec, cycle: int) -> None:
    """Every catalogued file at its URL: a zip of one line, a CSV of its header row alone."""
    for bulk in CATALOGUE.values():
        if bulk.format == "zip":
            fec.serve(cycle, bulk.name)
        else:
            fec_fixture.publish(fec, bulk, cycle, fec_fixture.csv_text(bulk, ()).encode())


def run_extract(
    fec: FakeFec,
    store: R2,
    data_dir: Path,
    *,
    cycle: int = 2026,
    file: FecFile | None = None,
    today: date = TODAY,
    sleeps: list[float] | None = None,
) -> list[Extracted]:
    return extract(
        cycle,
        store,
        build_id=BUILD,
        data_dir=data_dir,
        base_url=fec.url,
        file=file,
        today=today,
        sleep=(sleeps if sleeps is not None else []).append,
    )


def bronze(store: R2) -> dict[str, str]:
    """Every bronze key with its ETag and upload time, both of which a re-upload changes."""
    listed = store.client.list_objects_v2(Bucket=store.bucket, Prefix="bronze/")
    return {
        obj["Key"]: f"{obj.get('ETag')}@{obj.get('LastModified')}"
        for obj in listed.get("Contents", [])
        if "Key" in obj
    }


def local_files(data_dir: Path) -> list[Path]:
    return sorted(p for p in (data_dir / "bronze").rglob("*") if p.is_file())


@pytest.fixture
def cli_env(monkeypatch: pytest.MonkeyPatch, fec: FakeFec, tmp_path: Path) -> Iterator[Path]:
    """Point the CLI's settings at the fake FEC, the test bucket and a scratch `DATA_DIR`."""

    def leave_logging_alone(level: str) -> None:
        # The callback reconfigures the root logger, which would outlive the test.
        pass

    monkeypatch.setattr(cli, "configure_logging", leave_logging_alone)
    monkeypatch.setenv("FEC_BULK_URL", fec.url)
    monkeypatch.setenv("R2_BUCKET", TEST_BUCKET)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_the_cli_extracts_every_file_once_and_a_second_run_uploads_nothing(
    fec: FakeFec, store: R2, cli_env: Path
) -> None:
    publish_all(fec, 2024)
    args = ["extract", "--cycle", "2024", "--build-id", BUILD]

    first = CliRunner().invoke(cli.app, args)

    assert first.exit_code == 0, first.output
    uploaded = bronze(store)
    assert sorted(re.sub(r"/[^/]+\.(zip|csv)$", "", key) for key in uploaded) == sorted(
        f"bronze/cycle=2024/{name}" for name in FILES
    )
    # The summary files with the rest (NEU-2142): two zips, and a CSV kept as a CSV.
    assert sorted(fec.gets()) == sorted(
        [
            *(f"/2024/{name}24.zip" for name in FILES if name != "committee_summary"),
            "/2024/committee_summary_2024.csv",
        ]
    )
    assert all(re.search(r"/\d{4}-\d{2}-\d{2}\.(zip|csv)$", key) for key in uploaded)
    assert [key.rsplit("/", 1)[0] for key in uploaded if key.endswith(".csv")] == [
        "bronze/cycle=2024/committee_summary"
    ]
    assert markers.exists("extracted", store, cycle=2024, build_id=BUILD)
    # 2024 is a historical cycle: nothing of it stays on disk.
    assert local_files(cli_env) == []

    fec.requests.clear()
    second = CliRunner().invoke(cli.app, args)

    assert second.exit_code == 0, second.output
    assert fec.gets() == []
    assert [method for method, _ in fec.requests] == ["HEAD"] * len(FILES)
    assert bronze(store) == uploaded
    assert second.output.count("unchanged") == len(FILES)


def test_the_cli_rejects_a_file_the_catalogue_does_not_list(
    fec: FakeFec, store: R2, cli_env: Path
) -> None:
    # `webl`, FEC's House/Senate current campaigns, is a file fundlens never reads
    # (every-FEC-dollar spec §3.2).
    result = CliRunner().invoke(cli.app, ["extract", "--cycle", "2024", "--file", "webl"])

    assert result.exit_code == 2
    assert fec.requests == []


def test_the_current_cycle_keeps_its_zips_on_disk(fec: FakeFec, store: R2, tmp_path: Path) -> None:
    publish_all(fec, 2026)

    results = run_extract(fec, store, tmp_path)

    assert all(result.downloaded for result in results)
    assert local_files(tmp_path) == sorted(
        paths.local_path(tmp_path, result.key) for result in results
    )


def test_a_missing_local_copy_of_the_current_cycle_comes_back_from_r2_not_fec(
    fec: FakeFec, store: R2, tmp_path: Path
) -> None:
    fec.serve(2026, "cm")
    [first] = run_extract(fec, store, tmp_path, file="cm")
    local = paths.local_path(tmp_path, first.key)
    local.unlink()
    fec.requests.clear()

    [again] = run_extract(fec, store, tmp_path, file="cm")

    assert not again.downloaded
    assert fec.gets() == []
    assert local.read_bytes() == store.get(first.key)


def test_a_changed_file_is_downloaded_again_under_the_new_date(
    fec: FakeFec, store: R2, tmp_path: Path
) -> None:
    publish_all(fec, 2026)
    first = {result.file: result for result in run_extract(fec, store, tmp_path)}
    fec.serve(2026, "indiv", last_modified="Fri, 06 Nov 2026 05:40:00 GMT")
    fec.requests.clear()

    second = {result.file: result for result in run_extract(fec, store, tmp_path, today=NEXT_WEEK)}

    assert second["indiv"].downloaded
    assert second["indiv"].key == paths.bronze_zip(2026, "indiv", NEXT_WEEK)
    assert fec.gets() == ["/2026/indiv26.zip"]
    assert all(not second[name].downloaded for name in FILES if name != "indiv")
    # Both downloads stay in R2; on disk only the newer one is kept.
    assert store.exists(first["indiv"].key)
    assert sorted((tmp_path / "bronze/cycle=2026/indiv").iterdir()) == [
        paths.local_path(tmp_path, second["indiv"].key)
    ]


def test_a_server_error_is_retried_with_backoff(fec: FakeFec, store: R2, tmp_path: Path) -> None:
    path = fec.serve(2024, "cm")
    fec.failures[path] = [503, 502]
    sleeps: list[float] = []

    [result] = run_extract(fec, store, tmp_path, cycle=2024, file="cm", sleeps=sleeps)

    assert result.downloaded
    assert sleeps == [2.0, 4.0]
    assert fec.gets() == [path] * 3


def test_a_file_fec_does_not_have_fails_at_once_and_writes_no_marker(
    fec: FakeFec, store: R2, tmp_path: Path
) -> None:
    publish_all(fec, 2024)
    del fec.files["/2024/oth24.zip"]
    sleeps: list[float] = []

    with pytest.raises(HTTPError) as raised:
        run_extract(fec, store, tmp_path, cycle=2024, sleeps=sleeps)

    assert raised.value.code == 404
    assert sleeps == []
    assert not markers.exists("extracted", store, cycle=2024, build_id=BUILD)


def test_one_file_on_its_own_writes_no_marker(fec: FakeFec, store: R2, tmp_path: Path) -> None:
    fec.serve(2024, "cn")

    [result] = run_extract(fec, store, tmp_path, cycle=2024, file="cn")

    assert list(bronze(store)) == [result.key]
    assert not markers.exists("extracted", store, cycle=2024, build_id=BUILD)


def test_a_cycle_extracts_only_the_files_fec_published_for_it(
    fec: FakeFec, store: R2, tmp_path: Path
) -> None:
    publish_all(fec, 1998)

    results = run_extract(fec, store, tmp_path, cycle=1998)

    # No `ccl` before 2000, no `committee_summary` before 2008 (spec §3.1).
    assert [result.file for result in results] == [
        "cm",
        "cn",
        "indiv",
        "pas2",
        "oth",
        "weball",
        "webk",
    ]
    requested = [path for _, path in fec.requests]
    assert "/1998/ccl98.zip" not in requested
    assert "/1998/committee_summary_1998.csv" not in requested
    with pytest.raises(ValueError, match="no ccl file before 2000"):
        run_extract(fec, store, tmp_path, cycle=1998, file="ccl")


def test_the_cli_rejects_a_file_fec_did_not_yet_publish_for_the_cycle(
    fec: FakeFec, store: R2, cli_env: Path
) -> None:
    result = CliRunner().invoke(cli.app, ["extract", "--cycle", "1998", "--file", "ccl"])

    assert result.exit_code == 2
    assert fec.requests == []


def test_the_cli_rejects_oppexp_before_fec_published_it(
    fec: FakeFec, store: R2, cli_env: Path
) -> None:
    # FEC publishes operating expenditures from 2004 (every-FEC-dollar spec §3.1).
    result = CliRunner().invoke(cli.app, ["extract", "--cycle", "2002", "--file", "oppexp"])

    assert result.exit_code == 2
    assert fec.requests == []


def test_a_cut_short_local_copy_of_the_current_cycle_is_fetched_again_from_r2(
    fec: FakeFec, store: R2, tmp_path: Path
) -> None:
    fec.serve(2026, "cm")
    [first] = run_extract(fec, store, tmp_path, file="cm")
    local = paths.local_path(tmp_path, first.key)
    local.write_bytes(local.read_bytes()[:10])

    [again] = run_extract(fec, store, tmp_path, file="cm")

    assert not again.downloaded
    assert local.read_bytes() == store.get(first.key)


def test_a_cycle_that_rolled_over_leaves_the_disk(fec: FakeFec, store: R2, tmp_path: Path) -> None:
    fec.serve(2026, "cm")
    fec.serve(2028, "cm")
    [old] = run_extract(fec, store, tmp_path, file="cm")
    assert paths.local_path(tmp_path, old.key).exists()

    # The first extract of 2027: 2028 is now the current cycle and 2026 a historical one.
    [new] = run_extract(fec, store, tmp_path, cycle=2028, file="cm", today=date(2027, 1, 3))

    assert local_files(tmp_path) == [paths.local_path(tmp_path, new.key)]
    assert store.exists(old.key)


def test_a_failed_upload_leaves_no_historical_zip_on_disk(
    fec: FakeFec, store: R2, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fec.serve(2024, "cm")

    def refuse(*args: object, **kwargs: object) -> None:
        raise RuntimeError("R2 is down")

    monkeypatch.setattr(store, "put", refuse)

    with pytest.raises(RuntimeError, match="R2 is down"):
        run_extract(fec, store, tmp_path, cycle=2024, file="cm")

    assert local_files(tmp_path) == []


# The CSV format (NEU-2138), through `extract_file` with the test-only entries: one per cycle in
# the cycle's folder, one undated.
CSVS = pytest.mark.parametrize("sample", [SAMPLE, SAMPLE_UNDATED], ids=["per_cycle", "undated"])
SAMPLE_BODY = fec_fixture.bulk_body(SAMPLE, fec_fixture.SAMPLE_FILE)
NEXT_WEEKS_LAST_MODIFIED = "Fri, 06 Nov 2026 05:40:00 GMT"


def extract_csv(
    fec: FakeFec,
    store: R2,
    data_dir: Path,
    sample: BulkFile,
    *,
    cycle: int = 2024,
    today: date = TODAY,
    sleeps: list[float] | None = None,
) -> Extracted:
    return extract_file(
        sample,
        cycle,
        store,
        data_dir=data_dir,
        base_url=fec.url,
        today=today,
        sleep=(sleeps if sleeps is not None else []).append,
    )


@CSVS
def test_a_csv_is_downloaded_once_and_again_only_when_it_changes(
    fec: FakeFec, store: R2, tmp_path: Path, sample: BulkFile
) -> None:
    path = fec_fixture.publish(fec, sample, 2024, SAMPLE_BODY)

    first = extract_csv(fec, store, tmp_path, sample)

    assert first.downloaded
    assert first.key == f"bronze/cycle=2024/{sample.name}/2026-10-30.csv"
    assert fec.gets() == [path]
    assert store.get(first.key) == SAMPLE_BODY
    metadata = store.metadata(first.key)
    assert (metadata[LAST_MODIFIED], metadata[SIZE]) == (
        "Fri, 30 Oct 2026 05:43:50 GMT",
        str(len(SAMPLE_BODY)),
    )

    fec.requests.clear()
    unchanged = extract_csv(fec, store, tmp_path, sample)

    assert not unchanged.downloaded
    assert unchanged.key == first.key
    assert fec.gets() == []
    assert list(bronze(store)) == [first.key]

    fec_fixture.publish(fec, sample, 2024, SAMPLE_BODY, last_modified=NEXT_WEEKS_LAST_MODIFIED)
    changed = extract_csv(fec, store, tmp_path, sample, today=NEXT_WEEK)

    assert changed.downloaded
    assert changed.key == paths.bronze_csv(2024, sample.name, NEXT_WEEK)
    assert sorted(bronze(store)) == [first.key, changed.key]


@CSVS
@pytest.mark.parametrize(
    "body",
    [
        b"<!DOCTYPE html><html><body>Not found</body></html>\n",
        zipped("sample.txt", "C00000001|NAME|1.00|20241016\n"),
        SAMPLE_BODY.replace(b"CMTE_NM", b"CMTE_NAME", 1),
    ],
    ids=["html", "zip", "renamed_column"],
)
def test_a_response_that_is_not_the_catalogued_csv_is_refused(
    fec: FakeFec, store: R2, tmp_path: Path, sample: BulkFile, body: bytes
) -> None:
    fec_fixture.publish(fec, sample, 2024, body)
    sleeps: list[float] = []

    with pytest.raises(DownloadError, match="header row"):
        extract_csv(fec, store, tmp_path, sample, sleeps=sleeps)

    assert len(sleeps) == 4
    assert bronze(store) == {}
    assert local_files(tmp_path) == []


def test_an_undated_csv_is_kept_under_each_cycle_extracted(
    fec: FakeFec, store: R2, tmp_path: Path
) -> None:
    path = fec_fixture.publish(fec, SAMPLE_UNDATED, 2024, SAMPLE_BODY)

    of_2024 = extract_csv(fec, store, tmp_path, SAMPLE_UNDATED, cycle=2024)
    of_2026 = extract_csv(fec, store, tmp_path, SAMPLE_UNDATED, cycle=2026)

    assert path == "/data.fec.gov/sample.csv"
    assert fec.gets() == [path, path]
    assert sorted(bronze(store)) == [
        "bronze/cycle=2024/sample_undated/2026-10-30.csv",
        "bronze/cycle=2026/sample_undated/2026-10-30.csv",
    ]
    assert of_2024.downloaded and of_2026.downloaded

    fec.requests.clear()
    again = extract_csv(fec, store, tmp_path, SAMPLE_UNDATED, cycle=2024)

    assert not again.downloaded
    assert fec.gets() == []


@CSVS
def test_only_the_current_cycles_csv_stays_on_disk(
    fec: FakeFec, store: R2, tmp_path: Path, sample: BulkFile
) -> None:
    fec_fixture.publish(fec, sample, 2024, SAMPLE_BODY)
    fec_fixture.publish(fec, sample, 2026, SAMPLE_BODY)

    extract_csv(fec, store, tmp_path, sample, cycle=2024)
    current = extract_csv(fec, store, tmp_path, sample, cycle=2026)

    assert local_files(tmp_path) == [paths.local_path(tmp_path, current.key)]
