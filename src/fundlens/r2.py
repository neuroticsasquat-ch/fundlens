"""The one client every pipeline step reads and writes R2 through (ADR-0002).

R2 in prod, MinIO in dev and CI: both speak S3, so this is plain boto3 pointed at `R2_ENDPOINT`.
Keys are the strings `paths` builds.
"""

import io
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import ClientError

from fundlens.settings import Settings

if TYPE_CHECKING:
    # Dev-only stubs (see `cli`): quoted wherever an annotation is evaluated at runtime.
    from mypy_boto3_s3 import S3Client

# Objects above this go up (and are copied) in parts of this size.
MULTIPART_BYTES = 64 * 1024 * 1024

# The most keys one DeleteObjects request takes.
DELETE_BATCH = 1000

_TRANSFER = TransferConfig(multipart_threshold=MULTIPART_BYTES, multipart_chunksize=MULTIPART_BYTES)


def _dir(prefix: str) -> str:
    # A directory-style prefix, so `build=1` never matches the objects under `build=10`.
    return prefix.rstrip("/") + "/"


def _not_found(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey")


class R2:
    """One bucket of R2 (or MinIO)."""

    def __init__(self, client: "S3Client", bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    @classmethod
    def from_settings(cls, settings: Settings, bucket: str | None = None) -> "R2":
        """The private data bucket, or `bucket` (the public dataset one, say)."""
        client: S3Client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
            # boto3 >= 1.36 sends CRC checksums on every upload by default, which R2 has not
            # always accepted; only where the operation requires one keeps R2 and MinIO alike.
            config=Config(
                retries={"mode": "standard"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )
        return cls(client, bucket or settings.r2_bucket)

    def get(self, key: str) -> bytes:
        """The object at `key`. Raises `FileNotFoundError` when there is none."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if _not_found(exc):
                raise FileNotFoundError(key) from exc
            raise
        return response["Body"].read()

    def put(self, key: str, body: bytes | Path, metadata: Mapping[str, str] | None = None) -> None:
        """Write `body` (bytes, or a local file) to `key`, in parts above `MULTIPART_BYTES`.

        `metadata` is stored as the object's user metadata (`metadata` reads it back). S3
        lowercases its keys, so give them in lower case.
        """
        extra = {"Metadata": dict(metadata)} if metadata else None
        if isinstance(body, Path):
            self.client.upload_file(str(body), self.bucket, key, ExtraArgs=extra, Config=_TRANSFER)
        else:
            self.client.upload_fileobj(
                io.BytesIO(body), self.bucket, key, ExtraArgs=extra, Config=_TRANSFER
            )

    def metadata(self, key: str) -> dict[str, str]:
        """The user metadata `put` stored with `key`. Raises `FileNotFoundError` when there is
        no object."""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if _not_found(exc):
                raise FileNotFoundError(key) from exc
            raise
        return response.get("Metadata", {})

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if _not_found(exc):
                return False
            raise
        return True

    def list_keys(self, prefix: str) -> list[str]:
        """Every key starting with `prefix`, in key order.

        Not `list`: as a method name it would shadow the builtin in the annotations below it.
        """
        return list(self._iter_keys(prefix))

    def _iter_keys(self, prefix: str) -> Iterator[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                # Always present on a listed object; the stubs mark every field optional.
                if "Key" in obj:
                    yield obj["Key"]

    def download_to(self, key: str, path: Path) -> Path:
        """Download `key` to `path`, which appears only once the download is whole.

        Via a `.part` file beside it, so a run that dies mid-download leaves nothing at `path`
        that a later one could take for a cached copy.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".part")
        try:
            self.client.download_file(self.bucket, key, str(partial), Config=_TRANSFER)
        except ClientError as exc:
            partial.unlink(missing_ok=True)
            if _not_found(exc):
                raise FileNotFoundError(key) from exc
            raise
        partial.replace(path)
        return path

    def upload_dir(self, local: Path, prefix: str) -> list[str]:
        """Upload every file under `local` to the same relative key under `prefix`."""
        keys: list[str] = []
        for file in sorted(p for p in local.rglob("*") if p.is_file()):
            key = _dir(prefix) + file.relative_to(local).as_posix()
            self.put(key, file)
            keys.append(key)
        return keys

    def delete_prefix(self, prefix: str) -> int:
        """Delete every key starting with `prefix`; the number deleted."""
        return self._delete(self.list_keys(prefix))

    def _delete(self, keys: list[str]) -> int:
        for start in range(0, len(keys), DELETE_BATCH):
            batch = keys[start : start + DELETE_BATCH]
            response = self.client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
            )
            if errors := response.get("Errors"):
                raise RuntimeError(f"R2 refused to delete {len(errors)} keys, first: {errors[0]}")
        return len(keys)

    def atomic_publish(self, tmp_prefix: str, final_prefix: str) -> list[str]:
        """Move everything under `tmp_prefix` to `final_prefix`; the keys now under the latter.

        S3 has no rename, so this copies each object and then deletes the originals. It is
        atomic per object, **not across objects**: a reader listing `final_prefix` mid-publish
        sees some of the parts. Readers therefore never discover a build by listing; they resolve
        it from `gold.meta`, which names a build only after its publish has finished (spec §3.4).

        Safe to retry after a crash: objects already moved are no longer under `tmp_prefix` and
        are left alone, and the rest are copied again. Large objects are copied in parts
        server-side (UploadPartCopy, which MinIO and R2 both support).
        """
        source = _dir(tmp_prefix)
        target = _dir(final_prefix)
        keys = self.list_keys(source)
        if not keys:
            # Publishing nothing is a bug upstream, not a no-op to wave through.
            raise ValueError(f"nothing to publish under {source}")
        published: list[str] = []
        for key in keys:
            dest = target + key.removeprefix(source)
            self.client.copy(
                {"Bucket": self.bucket, "Key": key}, self.bucket, dest, Config=_TRANSFER
            )
            published.append(dest)
        self._delete(keys)
        return published
