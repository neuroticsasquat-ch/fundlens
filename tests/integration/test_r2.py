"""The R2 client against the dev compose's MinIO, R2's stand-in (spec §13)."""

import hashlib
import os
from pathlib import Path

import pytest

from fundlens.r2 import MULTIPART_BYTES, R2

MB = 1024 * 1024


def random_file(path: Path, size: int) -> str:
    """Write `size` random bytes to `path`; their sha256."""
    data = os.urandom(size)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(MB):
            digest.update(chunk)
    return digest.hexdigest()


def test_a_100_mb_file_goes_up_in_parts_and_comes_back_whole(store: R2, tmp_path: Path) -> None:
    source = tmp_path / "big.bin"
    expected = random_file(source, 100 * MB)

    store.put("bronze/big.bin", source)
    downloaded = store.download_to("bronze/big.bin", tmp_path / "cache" / "big.bin")

    # A multipart upload's ETag ends in `-<parts>`: 64 MB + 36 MB.
    head = store.client.head_object(Bucket=store.bucket, Key="bronze/big.bin")
    assert head["ETag"].strip('"').endswith("-2")
    assert sha256(downloaded) == expected
    assert not (tmp_path / "cache" / "big.bin.part").exists()


def test_put_get_exists(store: R2) -> None:
    assert not store.exists("markers/a.json")

    store.put("markers/a.json", b'{"ok": true}')

    assert store.exists("markers/a.json")
    assert store.get("markers/a.json") == b'{"ok": true}'


def test_metadata_put_with_an_object_reads_back_from_bytes_and_files(
    store: R2, tmp_path: Path
) -> None:
    meta = {"source-last-modified": "Fri, 30 Oct 2026 05:43:50 GMT", "source-size": "3"}
    local = tmp_path / "cm.zip"
    local.write_bytes(b"zip")

    store.put("bronze/a.zip", b"zip", metadata=meta)
    store.put("bronze/b.zip", local, metadata=meta)
    store.put("bronze/c.zip", b"zip")

    assert store.metadata("bronze/a.zip") == meta
    assert store.metadata("bronze/b.zip") == meta
    assert store.metadata("bronze/c.zip") == {}


def test_a_missing_object_is_file_not_found(store: R2, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        store.get("nope")
    with pytest.raises(FileNotFoundError):
        store.metadata("nope")
    with pytest.raises(FileNotFoundError):
        store.download_to("nope", tmp_path / "nope")
    assert not (tmp_path / "nope.part").exists()


def test_list_keys_takes_a_prefix(store: R2) -> None:
    for key in ("s/build=1/a", "s/build=1/b", "s/build=10/a", "t/a"):
        store.put(key, b"x")

    assert store.list_keys("s/build=1/") == ["s/build=1/a", "s/build=1/b"]
    assert store.list_keys("s/") == ["s/build=1/a", "s/build=1/b", "s/build=10/a"]


def test_upload_dir_keeps_the_relative_layout(store: R2, tmp_path: Path) -> None:
    (tmp_path / "bucket=00").mkdir()
    (tmp_path / "part-0000.parquet").write_bytes(b"a")
    (tmp_path / "bucket=00" / "part-0000.parquet").write_bytes(b"b")

    keys = store.upload_dir(tmp_path, "silver/contribution/cycle=2024/build=X/")

    assert keys == [
        "silver/contribution/cycle=2024/build=X/bucket=00/part-0000.parquet",
        "silver/contribution/cycle=2024/build=X/part-0000.parquet",
    ]
    assert store.get(keys[0]) == b"b"


def test_atomic_publish_moves_every_object_including_multipart_ones(
    store: R2, tmp_path: Path
) -> None:
    # Over the threshold, so it was uploaded in parts and is copied in parts: the MinIO/R2
    # parity edge case spec §13 leaves to this ticket.
    big = tmp_path / "part-0001.parquet"
    expected = random_file(big, MULTIPART_BYTES + MB)
    store.put("tmp/build=1/part-0000.parquet", b"small")
    store.put("tmp/build=1/part-0001.parquet", big)

    published = store.atomic_publish("tmp/build=1", "final/build=1")

    assert published == ["final/build=1/part-0000.parquet", "final/build=1/part-0001.parquet"]
    assert store.list_keys("final/") == published
    assert store.list_keys("tmp/") == []
    assert store.get("final/build=1/part-0000.parquet") == b"small"
    copied = store.download_to("final/build=1/part-0001.parquet", tmp_path / "copied")
    assert sha256(copied) == expected


def test_atomic_publish_retried_after_a_crash_keeps_what_was_already_moved(store: R2) -> None:
    # The first attempt moved part-0000 and died before deleting part-0001's source.
    store.put("final/build=1/part-0000.parquet", b"a")
    store.put("final/build=1/part-0001.parquet", b"b")
    store.put("tmp/build=1/part-0001.parquet", b"b")

    store.atomic_publish("tmp/build=1", "final/build=1")

    assert store.list_keys("final/") == [
        "final/build=1/part-0000.parquet",
        "final/build=1/part-0001.parquet",
    ]
    assert store.list_keys("tmp/") == []


def test_atomic_publish_refuses_an_empty_source(store: R2) -> None:
    store.put("final/build=1/part-0000.parquet", b"live")

    with pytest.raises(ValueError, match="nothing to publish"):
        store.atomic_publish("tmp/build=1", "final/build=1")
    assert store.exists("final/build=1/part-0000.parquet")


def test_delete_prefix_batches_past_a_thousand(store: R2) -> None:
    for i in range(1001):
        store.put(f"many/{i:04d}", b"")

    assert store.delete_prefix("many/") == 1001
    assert store.list_keys("many/") == []
