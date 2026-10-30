"""The Kuma push wire shape: `GET <url>?status=up|down&msg=…[&ping=…]`."""

from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import SecretStr

from fundlens.heartbeat import MAX_MESSAGE, Heartbeat, heartbeat_for
from fundlens.settings import get_settings

PUSH = "https://kuma.example/api/push/s3cr3tTok"


def params(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_start_sends_nothing_and_ok_reports_the_duration() -> None:
    sent: list[str] = []
    clock = Clock()
    heartbeat = Heartbeat(PUSH, send=sent.append, clock=clock)

    heartbeat.start()
    assert sent == []
    clock.now += 1.5
    heartbeat.ok("transform: ok")

    assert len(sent) == 1
    assert sent[0].startswith(PUSH + "?")
    assert params(sent[0]) == {"status": "up", "msg": "transform: ok", "ping": "1500"}


def test_ok_without_start_carries_no_duration() -> None:
    sent: list[str] = []

    Heartbeat(PUSH, send=sent.append).ok()

    assert params(sent[0]) == {"status": "up", "msg": "ok"}


def test_fail_pushes_down_with_the_message_and_no_duration() -> None:
    sent: list[str] = []
    heartbeat = Heartbeat(PUSH, send=sent.append)

    heartbeat.start()
    heartbeat.fail("load: OperationalError: connection refused")

    assert params(sent[0]) == {
        "status": "down",
        "msg": "load: OperationalError: connection refused",
    }


def test_message_is_url_encoded_and_truncated() -> None:
    sent: list[str] = []

    Heartbeat(PUSH, send=sent.append).fail("a&b=c " + "x" * 500)

    msg = params(sent[0])["msg"]
    assert len(msg) == MAX_MESSAGE
    assert msg.startswith("a&b=c ")
    assert "a%26b%3Dc" in sent[0]


def test_the_query_replaces_one_pasted_from_kuma() -> None:
    sent: list[str] = []

    Heartbeat(f"{PUSH}?status=up&msg=OK&ping=", send=sent.append).fail("boom")

    assert params(sent[0]) == {"status": "down", "msg": "boom"}


@pytest.mark.parametrize("url", [None, ""])
def test_an_unset_url_sends_nothing(url: str | None) -> None:
    sent: list[str] = []
    heartbeat = Heartbeat(url, send=sent.append)

    heartbeat.start()
    heartbeat.ok()
    heartbeat.fail("boom")

    assert sent == []


def test_a_push_that_cannot_get_out_is_swallowed_without_logging_the_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def unreachable(url: str) -> None:
        raise OSError("no route to host")

    heartbeat = Heartbeat(PUSH, send=unreachable)
    heartbeat.ok()
    heartbeat.fail("boom")

    assert "kuma push (up) failed: OSError: no route to host" in caplog.text
    assert "kuma push (down) failed" in caplog.text
    assert "s3cr3tTok" not in caplog.text


def test_each_family_pushes_to_its_own_monitor() -> None:
    sent: list[str] = []
    settings = get_settings().model_copy(
        update={
            "kuma_push_weekly": SecretStr("https://kuma.example/api/push/weekly"),
            "kuma_push_publish": SecretStr("https://kuma.example/api/push/publish"),
        }
    )

    for family in ("weekly", "publish"):
        heartbeat_for(family, settings, send=sent.append).ok()

    assert [urlsplit(url).path for url in sent] == ["/api/push/weekly", "/api/push/publish"]


def test_a_job_with_no_family_or_no_url_is_silent() -> None:
    settings = get_settings().model_copy(update={"kuma_push_weekly": None})

    sent: list[str] = []

    heartbeat_for(None, settings, send=sent.append).ok()
    heartbeat_for("weekly", settings, send=sent.append).ok()

    assert sent == []
