import json
import logging
import sys

from fundlens.logging import JsonFormatter, RedactingFilter, redact_push_token


def _record(msg: str, *args: object) -> logging.LogRecord:
    return logging.LogRecord("fundlens.test", logging.INFO, __file__, 1, msg, args, None)


def test_formatter_emits_one_json_object() -> None:
    line = JsonFormatter().format(_record("loaded %d rows", 3))

    entry = json.loads(line)
    assert entry["level"] == "INFO"
    assert entry["logger"] == "fundlens.test"
    assert entry["message"] == "loaded 3 rows"
    assert entry["ts"].endswith("+00:00")


def test_formatter_includes_the_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            "fundlens.test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
        )

    entry = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in entry["exc_info"]


def test_redacts_kuma_push_token() -> None:
    url = "https://kuma.example/api/push/s3cr3tTok?status=up&msg=OK"

    assert redact_push_token(url) == "https://kuma.example/api/push/REDACTED?status=up&msg=OK"


def test_filter_scrubs_token_passed_as_argument() -> None:
    record = _record("HTTP Request: GET %s", "https://kuma.example/api/push/s3cr3tTok?status=up")

    assert RedactingFilter().filter(record)
    assert "s3cr3tTok" not in record.getMessage()
