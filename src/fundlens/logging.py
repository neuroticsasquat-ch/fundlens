"""Logging setup shared by every entrypoint: one JSON object per line on stderr, and the
credential redaction that goes with it.

Both the CLI and the API configure the root logger here, so the redacting filter cannot be
installed on one and forgotten on the other. Depends on nothing else in the package.
"""

import json
import logging
import re
from datetime import UTC, datetime

_PUSH_TOKEN = re.compile(r"(/api/push/)[^/?#&\s'\"]+")


def redact_push_token(text: str) -> str:
    """Replace the token in any Uptime Kuma `/api/push/<token>` path in `text` with `REDACTED`.

    The token is the push monitor's only credential: whoever holds it can push `status=up` and
    hide a failed job.
    """
    return _PUSH_TOKEN.sub(r"\1REDACTED", text)


class RedactingFilter(logging.Filter):
    """Scrubs credentials out of every log record, whoever emitted it.

    A filter rather than a rule about how *we* log, because the loudest leak is library code:
    `httpx` and `urllib3` log full request URLs, and a Kuma push URL carries its token in the
    path. Rewrites `record.msg` and drops `record.args` because the credential can be in
    either; collapsing them into the final message is the only way to scrub both in one pass.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = redact_push_token(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per record, so SigNoz and `docker logs | jq` read the same thing."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, str] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging(level: str) -> None:
    """Configure the root logger with `JsonFormatter` and install `RedactingFilter`."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    # On the handler, not on the root logger: a filter attached to a logger is not consulted
    # for records propagating up from its children, so `httpx`'s own logger would sail past it.
    handler.addFilter(RedactingFilter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
