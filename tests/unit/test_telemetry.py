"""Release and environment for Bugsink, read from what OTel itself was given."""

from typing import Any

import pytest
from pydantic import SecretStr

from fundlens import telemetry
from fundlens.settings import Settings, get_settings
from fundlens.telemetry import (
    init_sentry,
    parse_resource_attributes,
    pipeline_integrations,
    resolve_telemetry,
)

SHA = "0123456789abcdef0123456789abcdef01234567"
PROD_ATTRS = (
    f"service.name=fundlens-pipeline,deployment.environment=production,service.version={SHA}"
)


def _settings(**update: Any) -> Settings:
    return get_settings().model_copy(update=update)


def test_parse_resource_attributes_splits_pairs_and_percent_decodes() -> None:
    assert parse_resource_attributes("a=1, b = two%2Cparts ,,junk,c=") == {
        "a": "1",
        "b": "two,parts",
        "c": "",
    }


def test_release_and_environment_are_otels_own_resource_attributes() -> None:
    resolved = resolve_telemetry(PROD_ATTRS)

    assert resolved.release == SHA
    assert resolved.environment == "production"


def test_unset_attributes_fall_back_to_unknown_and_development() -> None:
    resolved = resolve_telemetry("service.name=fundlens-pipeline")

    assert resolved.release == "unknown"
    assert resolved.environment == "development"


@pytest.fixture
def sdk_init(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def init(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(telemetry.sentry_sdk, "init", init)
    return calls


def test_init_sentry_passes_the_resolved_pair_to_the_sdk(sdk_init: list[dict[str, Any]]) -> None:
    integrations = pipeline_integrations()

    init_sentry(
        _settings(
            sentry_dsn=SecretStr("https://key@bugsink.example/1"),
            otel_resource_attributes=PROD_ATTRS,
        ),
        integrations,
    )

    assert len(sdk_init) == 1
    assert sdk_init[0]["dsn"] == "https://key@bugsink.example/1"
    assert sdk_init[0]["release"] == SHA
    assert sdk_init[0]["environment"] == "production"
    assert sdk_init[0]["integrations"] == integrations


def test_init_sentry_without_a_dsn_leaves_the_sdk_alone(sdk_init: list[dict[str, Any]]) -> None:
    init_sentry(_settings(sentry_dsn=None), pipeline_integrations())

    assert sdk_init == []


def test_exporting_without_version_and_environment_warns(
    sdk_init: list[dict[str, Any]], caplog: pytest.LogCaptureFixture
) -> None:
    init_sentry(
        _settings(
            otel_exporter_otlp_endpoint="http://signoz:4318",
            otel_resource_attributes="service.name=fundlens-pipeline",
        ),
        pipeline_integrations(),
    )

    assert "lacks service.version or deployment.environment" in caplog.text
