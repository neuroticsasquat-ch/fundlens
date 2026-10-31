"""Crash reporting to Bugsink, named with the same build OTel names in SigNoz (spec §10.3).

Ported from upcoming-movies-backend's `telemetry.py`. The NS instrumentation contract requires
Sentry's `release` to equal OTel's `service.version` and Sentry's `environment` to equal OTel's
`deployment.environment`, so an error in Bugsink and a trace in SigNoz name the same build.

OTel reads `OTEL_RESOURCE_ATTRIBUTES` inside `opentelemetry-instrument`, before this process
imports anything of ours, so we cannot hand OTel a value; we can only read the one OTel already
took. That is the only source here. Logs and traces need nothing from this module: the
entrypoints run under `opentelemetry-instrument`, whose instrumentation logging handler ships
the records (never `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED`, which swaps in the SDK's
deprecated handler).
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import unquote

import sentry_sdk
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.logging import LoggingIntegration

from fundlens.settings import Settings

log = logging.getLogger(__name__)

# What OTel's resource reports when `service.version` is not set, and so what Bugsink must say
# too: a better value here than SigNoz holds would break the equality this module exists for.
UNKNOWN_RELEASE = "unknown"
DEFAULT_ENVIRONMENT = "development"


@dataclass(frozen=True)
class Telemetry:
    release: str
    environment: str


def parse_resource_attributes(raw: str) -> dict[str, str]:
    """Parse `OTEL_RESOURCE_ATTRIBUTES` (`k1=v1,k2=v2`, values percent-encoded)."""
    attrs: dict[str, str] = {}
    for pair in raw.split(","):
        key, sep, value = pair.partition("=")
        if sep and key.strip():
            attrs[key.strip()] = unquote(value.strip())
    return attrs


def resolve_telemetry(resource_attributes: str) -> Telemetry:
    attrs = parse_resource_attributes(resource_attributes)
    return Telemetry(
        release=attrs.get("service.version") or UNKNOWN_RELEASE,
        environment=attrs.get("deployment.environment") or DEFAULT_ENVIRONMENT,
    )


def pipeline_integrations() -> list[Integration]:
    """The pipeline's integrations: logging kept as breadcrumbs, never as events.

    A scheduled task reports its crash, not its items (ops ADR-0025): a step that logs a bad
    row and carries on must not turn into an alert per row. The crash itself is captured by
    `cli.step`.
    """
    return [LoggingIntegration(event_level=None)]


def init_sentry(settings: Settings, integrations: Sequence[Integration]) -> Telemetry:
    """Initialise the Sentry SDK (pointed at Bugsink) when `SENTRY_DSN` is set, and log the
    resolved release and environment either way."""
    telemetry = resolve_telemetry(settings.otel_resource_attributes)
    log.info(
        "telemetry: release=%s environment=%s sentry=%s",
        telemetry.release,
        telemetry.environment,
        "on" if settings.sentry_dsn else "off",
    )
    attrs = parse_resource_attributes(settings.otel_resource_attributes)
    if settings.otel_exporter_otlp_endpoint and not (
        "service.version" in attrs and "deployment.environment" in attrs
    ):
        # Exporting without them means SigNoz and Bugsink disagree on the build.
        log.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT is set but OTEL_RESOURCE_ATTRIBUTES lacks "
            "service.version or deployment.environment"
        )
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn.get_secret_value(),
            integrations=list(integrations),
            environment=telemetry.environment,
            release=telemetry.release,
        )
    return telemetry
