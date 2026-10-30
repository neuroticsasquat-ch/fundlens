"""A MinIO bucket of the integration tests' own, standing in for R2."""

from collections.abc import Iterator

import pytest
from botocore.exceptions import ClientError

from fundlens.r2 import R2
from fundlens.settings import get_settings

# Not `R2_BUCKET`: the dev seed writes there, and every test here empties its bucket afterwards.
TEST_BUCKET = "fundlens-test"


@pytest.fixture
def store() -> Iterator[R2]:
    """An empty MinIO bucket of its own, emptied again after the test."""
    r2 = R2.from_settings(get_settings(), bucket=TEST_BUCKET)
    try:
        r2.client.create_bucket(Bucket=TEST_BUCKET)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
            raise
    r2.delete_prefix("")
    yield r2
    r2.delete_prefix("")
