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
from fundlens.fec.extract import Extracted, extract
from fundlens.fec.files import FecFile
from fundlens.r2 import R2
from fundlens.settings import get_settings
from tests.fake_fec import FakeFec
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
    for name in FILES:
        fec.serve(cycle, name)


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


def test_the_cli_extracts_six_files_once_and_a_second_run_uploads_nothing(
    fec: FakeFec, store: R2, cli_env: Path
) -> None:
    publish_all(fec, 2024)
    args = ["extract", "--cycle", "2024", "--build-id", BUILD]

    first = CliRunner().invoke(cli.app, args)

    assert first.exit_code == 0, first.output
    uploaded = bronze(store)
    assert sorted(re.sub(r"/[^/]+\.zip$", "", key) for key in uploaded) == sorted(
        f"bronze/cycle=2024/{name}" for name in FILES
    )
    assert all(re.search(r"/\d{4}-\d{2}-\d{2}\.zip$", key) for key in uploaded)
    assert len(fec.gets()) == 6
    assert markers.exists("extracted", store, cycle=2024, build_id=BUILD)
    # 2024 is a historical cycle: nothing of it stays on disk.
    assert local_files(cli_env) == []

    fec.requests.clear()
    second = CliRunner().invoke(cli.app, args)

    assert second.exit_code == 0, second.output
    assert fec.gets() == []
    assert [method for method, _ in fec.requests] == ["HEAD"] * 6
    assert bronze(store) == uploaded
    assert second.output.count("unchanged") == 6


def test_the_cli_rejects_a_file_the_catalogue_does_not_list(
    fec: FakeFec, store: R2, cli_env: Path
) -> None:
    result = CliRunner().invoke(cli.app, ["extract", "--cycle", "2024", "--file", "oppexp"])

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


def test_a_cycle_before_ccl_existed_extracts_the_other_five(
    fec: FakeFec, store: R2, tmp_path: Path
) -> None:
    publish_all(fec, 1998)

    results = run_extract(fec, store, tmp_path, cycle=1998)

    assert [result.file for result in results] == ["cm", "cn", "indiv", "pas2", "oth"]
    assert "/1998/ccl98.zip" not in [path for _, path in fec.requests]
    with pytest.raises(ValueError, match="no ccl file before 2000"):
        run_extract(fec, store, tmp_path, cycle=1998, file="ccl")


def test_the_cli_rejects_a_file_fec_did_not_yet_publish_for_the_cycle(
    fec: FakeFec, store: R2, cli_env: Path
) -> None:
    result = CliRunner().invoke(cli.app, ["extract", "--cycle", "1998", "--file", "ccl"])

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
