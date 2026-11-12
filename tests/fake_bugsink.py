"""A Sentry SDK pointed at a fake transport: what the pipeline would have sent to Bugsink."""

from collections.abc import Generator
from contextlib import contextmanager

import sentry_sdk
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from fundlens.telemetry import pipeline_integrations


class FakeTransport(Transport):
    """Keeps every event the SDK would have sent to Bugsink."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, object]] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        event = envelope.get_event()
        if event is not None:
            self.events.append(dict(event))


@contextmanager
def fake_bugsink() -> Generator[FakeTransport]:
    """A live SDK with the pipeline's own integrations, delivering to a fake transport."""
    transport = FakeTransport()
    sentry_sdk.init(
        dsn="https://key@bugsink.example/1",
        transport=transport,
        integrations=pipeline_integrations(),
    )
    try:
        yield transport
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.get_global_scope().set_client(None)
