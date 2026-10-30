"""The zone purge's wire shape, its retries, and what it never says (NEU-2039 §4.3)."""

import json
from collections.abc import Mapping

import pytest
from pydantic import SecretStr

from fundlens.publish import cloudflare
from fundlens.publish.cloudflare import ATTEMPTS, RETRY_SECONDS, PurgeFailed, Response, purge_zone
from fundlens.settings import get_settings
from tests.fake_cloudflare import DENIED, OK, TOKEN, UPSTREAM, ZONE, FakeCloudflare


def test_purge_posts_purge_everything_with_the_bearer_token() -> None:
    fake = FakeCloudflare(OK)
    slept: list[float] = []

    purge_zone(ZONE, TOKEN, post=fake, sleep=slept.append)

    [(url, headers, body)] = fake.posts
    assert url == f"https://api.cloudflare.com/client/v4/zones/{ZONE}/purge_cache"
    assert headers == {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    assert json.loads(body) == {"purge_everything": True}
    assert slept == []


def test_a_failed_attempt_is_retried_and_a_later_success_is_a_success() -> None:
    fake = FakeCloudflare(UPSTREAM, OK)
    slept: list[float] = []

    purge_zone(ZONE, TOKEN, post=fake, sleep=slept.append)

    assert len(fake.posts) == 2
    assert slept == [RETRY_SECONDS]


def test_three_failures_raise_without_the_token(caplog: pytest.LogCaptureFixture) -> None:
    fake = FakeCloudflare(DENIED)
    slept: list[float] = []

    with pytest.raises(PurgeFailed, match="HTTP 403") as excinfo:
        purge_zone(ZONE, TOKEN, post=fake, sleep=slept.append)

    assert len(fake.posts) == ATTEMPTS
    assert slept == [RETRY_SECONDS] * (ATTEMPTS - 1)
    assert "denied" in str(excinfo.value)
    assert TOKEN not in str(excinfo.value)
    assert TOKEN not in caplog.text
    assert ZONE in caplog.text


def test_a_200_that_does_not_say_success_is_a_failure() -> None:
    fake = FakeCloudflare(Response(200, b'{"success": false, "errors": []}'))

    with pytest.raises(PurgeFailed):
        purge_zone(ZONE, TOKEN, post=fake, sleep=lambda s: None)


def test_a_connection_error_is_retried_like_a_bad_status() -> None:
    calls: list[int] = []

    def unreachable(url: str, headers: Mapping[str, str], body: bytes) -> Response:
        calls.append(1)
        raise OSError("no route to host")

    with pytest.raises(PurgeFailed, match="OSError: no route to host"):
        purge_zone(ZONE, TOKEN, post=unreachable, sleep=lambda s: None)

    assert len(calls) == ATTEMPTS


@pytest.mark.parametrize(
    ("zone", "token"),
    [
        (None, None),
        (ZONE, None),
        (None, SecretStr(TOKEN)),
        ("", SecretStr(TOKEN)),
        (ZONE, SecretStr("")),
    ],
)
def test_purge_for_is_none_unless_both_settings_are_set(
    zone: str | None, token: SecretStr | None
) -> None:
    settings = get_settings().model_copy(
        update={"cloudflare_zone_id": zone, "cloudflare_api_token": token}
    )

    assert cloudflare.purge_for(settings) is None


def test_purge_for_binds_the_zone_and_token(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str]] = []

    def fake_purge_zone(zone_id: str, token: str) -> None:
        seen.append((zone_id, token))

    monkeypatch.setattr(cloudflare, "purge_zone", fake_purge_zone)
    settings = get_settings().model_copy(
        update={"cloudflare_zone_id": ZONE, "cloudflare_api_token": SecretStr(TOKEN)}
    )

    purge = cloudflare.purge_for(settings)

    assert purge is not None
    purge()
    assert seen == [(ZONE, TOKEN)]
