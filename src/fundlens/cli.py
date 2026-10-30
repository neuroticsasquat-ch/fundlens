"""The `fundlens` command line: one entry point for every pipeline step and service (spec §5.1).

Each step arrives with its own ticket as a subcommand on `app`, wrapped in `step`. This module
owns the shared callback, which handles `--version` and sets up logging and crash reporting
before any subcommand runs, the `step` wrapper itself, and `health`.
"""

import functools
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

import boto3
import psycopg
import sentry_sdk
import typer
from botocore.config import Config
from botocore.exceptions import ClientError
from opentelemetry import trace

from fundlens import __version__
from fundlens.heartbeat import JobFamily, heartbeat_for
from fundlens.logging import configure_logging
from fundlens.settings import Settings, get_settings
from fundlens.telemetry import init_sentry, pipeline_integrations

if TYPE_CHECKING:
    # The stubs are a dev dependency, absent from the prod image. A local variable's
    # annotation is never evaluated, so naming it below costs nothing at runtime.
    from mypy_boto3_s3 import S3Client

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

app = typer.Typer(no_args_is_help=True, add_completion=False)

HEALTH_TIMEOUT_SECONDS = 5


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Print the fundlens version and exit.",
        ),
    ] = False,
) -> None:
    """fundlens: federal campaign finance, by race, with resolved donors."""
    # Eager, so `--version` exits before this body reads settings; every subcommand gets
    # logging and crash reporting configured from the environment.
    settings = get_settings()
    configure_logging(settings.log_level)
    # After logging, so its startup line is emitted.
    init_sentry(settings, pipeline_integrations())


def _exception_summary(exc: BaseException) -> str:
    """The exception type and the first line of its text: an alert, not a traceback."""
    lines = str(exc).strip().splitlines()
    return f"{type(exc).__name__}: {lines[0]}" if lines else type(exc).__name__


def step[**P, R](
    name: str, *, family: JobFamily | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Wrap a pipeline command so it reports its crash, and only its crash (spec §5.1).

    Starts the job family's heartbeat, runs the step in an OTel span, and pushes `ok` when it
    returns. On an exception it pushes `fail`, reports the exception once to Bugsink tagged
    `pipeline_mode=<name>`, and re-raises, so the scheduled task still fails and Coolify hears
    it too. A step that ends with `typer.Exit` is not a crash: it pushes by its exit code and
    reports nothing. A step with no `family` has no push monitor of its own and pushes nothing.
    Put it under `@app.command()`, so typer reads the step's own signature.
    """

    def decorate(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            heartbeat = heartbeat_for(family, get_settings())
            heartbeat.start()
            with sentry_sdk.isolation_scope() as scope:
                scope.set_tag("pipeline_mode", name)
                try:
                    # The span records the exception and marks itself failed on the way out.
                    # A no-op unless the command runs under `opentelemetry-instrument`.
                    with tracer.start_as_current_span(f"fundlens {name}"):
                        result = fn(*args, **kwargs)
                except typer.Exit as exc:
                    # A deliberate exit (a step skipping work its marker says is done, say), not
                    # a crash: the exit code decides the push, and Bugsink hears nothing. Caught
                    # ahead of `Exception`, which `typer.Exit` and `typer.Abort` both subclass.
                    if exc.exit_code == 0:
                        heartbeat.ok(f"{name}: ok")
                    else:
                        heartbeat.fail(f"{name}: exited {exc.exit_code}")
                    raise
                except typer.Abort:
                    heartbeat.fail(f"{name}: aborted")
                    raise
                except Exception as exc:
                    log.exception("step %s failed", name)
                    heartbeat.fail(f"{name}: {_exception_summary(exc)}")
                    sentry_sdk.capture_exception(exc)
                    raise
                finally:
                    # The process exits straight after a step; an unflushed event is a lost one.
                    sentry_sdk.flush()
            heartbeat.ok(f"{name}: ok")
            return result

        return wrapper

    return decorate


def _check_postgres(settings: Settings) -> None:
    with psycopg.connect(settings.database_url, connect_timeout=HEALTH_TIMEOUT_SECONDS) as conn:
        conn.execute("SELECT 1")


def _check_r2(settings: Settings) -> None:
    client: S3Client = boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
        region_name="auto",
        config=Config(
            connect_timeout=HEALTH_TIMEOUT_SECONDS,
            read_timeout=HEALTH_TIMEOUT_SECONDS,
            retries={"total_max_attempts": 1},
        ),
    )
    try:
        client.head_bucket(Bucket=settings.r2_bucket)
    except ClientError as exc:
        # A 404 is the store answering and accepting the credentials (bad ones are a 403):
        # reachable. Whether the bucket exists is the pipeline's concern, not the healthcheck's.
        if exc.response.get("Error", {}).get("Code") != "404":
            raise


@app.command()
def health() -> None:
    """Exit 0 iff Postgres and R2 are reachable; the `api` service's healthcheck."""
    settings = get_settings()
    healthy = True
    for service, check in (("postgres", _check_postgres), ("r2", _check_r2)):
        try:
            check(settings)
        except Exception as exc:
            healthy = False
            typer.echo(f"{service}: unreachable ({_exception_summary(exc)})", err=True)
        else:
            typer.echo(f"{service}: ok")
    if not healthy:
        raise typer.Exit(1)
