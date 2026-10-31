"""The `fundlens` command line: one entry point for every pipeline step and service (spec §5.1).

Each step arrives with its own ticket as a subcommand on `app`, wrapped in `step`. This module
owns the shared callback, which handles `--version` and sets up logging and crash reporting
before any subcommand runs, the `step` wrapper itself, `health`, `api` and the hidden
`crash-test` the Coolify runbook fires.
"""

import functools
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated

import boto3
import psycopg
import sentry_sdk
import typer
import uvicorn
from botocore.config import Config
from botocore.exceptions import ClientError
from opentelemetry import trace

from fundlens import __version__, paths
from fundlens.api.app import openapi_json
from fundlens.fec import extract as fec_extract
from fundlens.fec.files import CATALOGUE
from fundlens.heartbeat import JobFamily, heartbeat_for
from fundlens.load import gold as gold_load
from fundlens.logging import configure_logging
from fundlens.publish import cloudflare
from fundlens.publish import gold as gold_publish
from fundlens.r2 import R2
from fundlens.settings import Settings, get_settings
from fundlens.telemetry import init_sentry, pipeline_integrations
from fundlens.transform import runner
from fundlens.transform import seats as seat_calendar

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


@app.command()
def api(
    host: Annotated[str, typer.Option(help="Interface to bind.")] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="Port to listen on.")] = 8000,
    export_openapi: Annotated[
        bool,
        typer.Option(
            "--export-openapi",
            help="Print the OpenAPI document (the frontend's contract) and exit, serving nothing.",
        ),
    ] = False,
) -> None:
    """Serve the public JSON API (spec §7.2) with uvicorn; the `api` service's command."""
    if export_openapi:
        # Stdout carries only the document: logging is on stderr, so `> openapi.json` is clean.
        typer.echo(openapi_json(get_settings()))
        return
    # Crash reporting is already on from the callback; sentry-sdk enables its FastAPI and
    # Starlette integrations by itself, so an unhandled request error reaches Bugsink.
    uvicorn.run(
        "fundlens.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        # Behind Coolify's Traefik and Cloudflare: take the client and scheme from their headers.
        proxy_headers=True,
        forwarded_allow_ips="*",
        # Keep the callback's JSON logging rather than uvicorn's own formatters.
        log_config=None,
    )


def _new_build_id() -> str:
    return paths.format_build_id(datetime.now(UTC))


@app.command()
# No family: the weekly monitor is `run`'s, the scheduled entry. A backfill extract run by hand
# would otherwise push it up and hide a missed Sunday.
@step("extract")
def extract(
    cycle: Annotated[int, typer.Option(help="The cycle, by its even year.")],
    file: Annotated[
        str | None,
        typer.Option(help=f"Only this file ({', '.join(CATALOGUE)}); writes no marker."),
    ] = None,
    build_id: Annotated[
        str | None,
        typer.Option(help="The build the `extracted` marker is for. Default: one starting now."),
    ] = None,
) -> None:
    """Download the cycle's FEC bulk zips into R2 bronze, skipping any unchanged since the
    last download (spec §5.1)."""
    if file is not None and file not in CATALOGUE:
        raise typer.BadParameter(f"not one of {', '.join(CATALOGUE)}", param_hint="--file")
    if file is not None and CATALOGUE[file].first_cycle > cycle:
        first = CATALOGUE[file].first_cycle
        raise typer.BadParameter(
            f"FEC publishes no {file} file before {first}", param_hint="--file"
        )
    settings = get_settings()
    results = fec_extract.extract(
        cycle,
        R2.from_settings(settings),
        build_id=build_id or _new_build_id(),
        data_dir=settings.data_dir,
        base_url=settings.fec_bulk_url,
        file=file,
    )
    for result in results:
        outcome = "downloaded" if result.downloaded else "unchanged"
        typer.echo(f"{result.file}: {outcome} {result.key}")


@app.command()
@step("seats")
def seats(
    cycle: Annotated[int, typer.Option(help="The cycle, by its even year.")],
    report: Annotated[
        bool,
        typer.Option(
            "--report",
            help="Also list the cycle's `cn` filings that match no seat, and record them in"
            " app.unmatched_filing.",
        ),
    ] = False,
    build_id: Annotated[
        str | None,
        typer.Option(help="The build the `race` partition is for. Default: one starting now."),
    ] = None,
) -> None:
    """Generate the cycle's seat calendar and write it as the `race` silver partition
    (spec §5.2)."""
    try:
        seat_calendar.check_cycle(cycle)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--cycle") from exc
    settings = get_settings()
    store = R2.from_settings(settings)
    build = build_id or _new_build_id()
    if report:
        with psycopg.connect(settings.database_url) as conn:
            try:
                result = seat_calendar.seats(
                    cycle, store, build_id=build, data_dir=settings.data_dir, conn=conn
                )
            except FileNotFoundError as exc:
                typer.echo(f"{exc}: run `fundlens extract --cycle {cycle} --file cn`", err=True)
                raise typer.Exit(1) from exc
    else:
        result = seat_calendar.seats(cycle, store, build_id=build, data_dir=settings.data_dir)
    for office, name in seat_calendar.OFFICE_NAMES.items():
        races = [race for race in result.races if race.office == office]
        if races:
            specials = sum(race.is_special for race in races)
            typer.echo(f"{name}: {len(races)} races ({specials} special)")
    typer.echo(f"wrote {result.key}")
    if result.unmatched is not None:
        for filing in result.unmatched:
            typer.echo(
                f"unmatched: {filing.candidate_id} {filing.office}"
                f" {filing.state}-{filing.district or '(blank)'}"
            )
        typer.echo(f"{len(result.unmatched)} unmatched filings recorded")


@app.command()
@step("transform")
def transform(
    cycle: Annotated[int, typer.Option(help="The cycle, by its even year.")],
    build_id: Annotated[
        str | None,
        typer.Option(help="The build the silver partitions are for. Default: one starting now."),
    ] = None,
) -> None:
    """Build the cycle's silver tables from its bronze zips, check them, and upload them
    (spec §5.3). Run `fundlens seats --report` first: a check reads its unmatched filings."""
    try:
        seat_calendar.check_cycle(cycle)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--cycle") from exc
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        try:
            result = runner.transform(
                cycle,
                R2.from_settings(settings),
                build_id=build_id or _new_build_id(),
                data_dir=settings.data_dir,
                sql_dir=settings.sql_dir,
                limits=runner.Limits.from_settings(settings),
                conn=conn,
            )
        except FileNotFoundError as exc:
            typer.echo(f"{exc}: run `fundlens extract --cycle {cycle}`", err=True)
            raise typer.Exit(1) from exc
    for table, rows in result.row_counts.items():
        typer.echo(f"{table}: {rows} rows")
    for key in result.keys:
        typer.echo(f"wrote {key}")


@app.command()
# No family, like `extract`: a hand backfill must not push the weekly monitor up.
@step("load")
def load(
    cycle: Annotated[int, typer.Option(help="The cycle, by its even year.")],
    build_id: Annotated[
        str | None,
        typer.Option(help="The transformed build to load. Default: the newest one."),
    ] = None,
) -> None:
    """Build the Postgres schema `gold_build` from the cycle's silver partitions, check it, and
    write the `loaded` marker (spec §5.5); `fundlens publish` swaps it in."""
    try:
        seat_calendar.check_cycle(cycle)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--cycle") from exc
    settings = get_settings()
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        try:
            result = gold_load.load(
                cycle,
                R2.from_settings(settings),
                build_id=build_id,
                data_dir=settings.data_dir,
                sql_dir=settings.sql_dir,
                limits=runner.Limits.from_settings(settings),
                conn=conn,
            )
        except FileNotFoundError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
    for table, rows in result.row_counts.items():
        typer.echo(f"{table}: {rows} rows")
    typer.echo(
        f"loaded build {result.build_id} into gold_build"
        f" (aggregates {result.aggregate_s:.2f} s, copy {result.copy_s:.2f} s)"
    )


@app.command()
@step("publish", family="publish")
def publish(
    cycle: Annotated[
        int | None, typer.Option(help="The cycle whose loaded build goes live.")
    ] = None,
    rollback: Annotated[
        bool,
        typer.Option("--rollback", help="Swap the previous build back in instead (no --cycle)."),
    ] = False,
) -> None:
    """Swap the loaded gold build in atomically, purge the Cloudflare zone, write the
    `published` marker and prune old silver builds (spec §5.5). `--rollback` swaps the previous
    build back and purges again."""
    if rollback and cycle is not None:
        raise typer.BadParameter("--rollback takes no --cycle", param_hint="--cycle")
    if not rollback and cycle is None:
        raise typer.BadParameter("--cycle is required", param_hint="--cycle")
    settings = get_settings()
    purge = cloudflare.purge_for(settings)
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        if rollback:
            try:
                rolled = gold_publish.rollback(conn, purge=purge)
            except gold_publish.NothingToRollBack as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(1) from exc
            typer.echo(f"rolled back: build {rolled.build_id} is live")
            typer.echo(f"build {rolled.previous_build_id} is now gold_prev")
            return
        assert cycle is not None
        try:
            seat_calendar.check_cycle(cycle)
        except ValueError as exc:
            raise typer.BadParameter(str(exc), param_hint="--cycle") from exc
        try:
            result = gold_publish.publish(
                cycle,
                R2.from_settings(settings),
                conn=conn,
                data_dir=settings.data_dir,
                purge=purge,
            )
        except gold_publish.NothingToPublish as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
    swapped = "published" if result.swapped else "finished publishing"
    typer.echo(f"{swapped} build {result.build_id} of {cycle}")
    typer.echo(f"previous build: {result.previous_build_id or 'none'}")
    typer.echo(f"cloudflare purge: {'done' if result.purged else 'skipped (not configured)'}")
    typer.echo(f"pruned {result.pruned.builds} silver builds ({result.pruned.objects} objects)")


@app.command("crash-test", hidden=True)
@step("crash-test", family="weekly")
def crash_test(
    recover: Annotated[
        bool, typer.Option("--recover", help="Succeed instead, pushing the monitor back up.")
    ] = False,
) -> None:
    """Crash on purpose, to prove a step's crash reaches Bugsink and the `fundlens/weekly`
    monitor (docs/runbooks/coolify-setup.md)."""
    if not recover:
        raise RuntimeError("deliberate crash from `fundlens crash-test`")
