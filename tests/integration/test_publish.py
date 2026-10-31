"""`fundlens publish` and `--rollback` against MinIO and a Postgres database of their own
(spec §5.5, NEU-2039 §4.2–§4.6, §6)."""

import logging
import threading
from functools import partial
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row
from typer.testing import CliRunner, Result

from fundlens import cli, markers, paths
from fundlens.paths import SilverTable
from fundlens.publish import cloudflare
from fundlens.publish import gold as gold_publish
from fundlens.publish.cloudflare import PurgeFailed, purge_zone
from fundlens.publish.gold import PURGE_DELAY_SECONDS, NothingToPublish, NothingToRollBack
from fundlens.r2 import R2
from fundlens.settings import get_settings
from tests.fake_cloudflare import OK, TOKEN, UPSTREAM, ZONE, FakeCloudflare
from tests.integration.test_transform import put_bronze

B0, B1, B2, B3 = (f"2026103{n}T030000Z" for n in range(4))
CYCLE = 2024


def run(*args: str) -> Result:
    return CliRunner().invoke(cli.app, list(args))


def transform(build_id: str, *, seats: bool = True) -> None:
    if seats:
        assert (
            run("seats", "--cycle", str(CYCLE), "--report", "--build-id", build_id).exit_code == 0
        )
    result = run("transform", "--cycle", str(CYCLE), "--build-id", build_id)
    assert result.exit_code == 0, result.output


def load(build_id: str) -> None:
    result = run("load", "--cycle", str(CYCLE), "--build-id", build_id)
    assert result.exit_code == 0, result.output


class Recorder:
    """The fake Cloudflare and the injected sleep, with the order of their calls."""

    def __init__(self, *responses: Any) -> None:
        self.cloudflare = FakeCloudflare(*responses)
        self.events: list[str] = []

    def post(self, url: str, headers: Any, body: bytes) -> Any:
        self.events.append("post")
        return self.cloudflare(url, headers, body)

    def sleep(self, seconds: float) -> None:
        self.events.append(f"sleep {seconds:g}")

    @property
    def purge(self) -> Any:
        return partial(purge_zone, ZONE, TOKEN, post=self.post, sleep=self.sleep)


def publish(conn: psycopg.Connection[Any], store: R2, data_dir: Path, recorder: Recorder) -> Any:
    return gold_publish.publish(
        CYCLE, store, conn=conn, data_dir=data_dir, purge=recorder.purge, sleep=recorder.sleep
    )


def meta(conninfo: str, schema: str) -> dict[str, Any] | None:
    with psycopg.connect(conninfo) as conn:
        if not gold_publish._schema_exists(conn, schema):  # pyright: ignore[reportPrivateUsage]
            return None
        try:
            return (
                conn.cursor(row_factory=dict_row)
                .execute(sql.SQL("SELECT * FROM {}.meta").format(sql.Identifier(schema)))
                .fetchone()
            )
        except psycopg.errors.UndefinedTable:
            return None


def tables(conninfo: str, schema: str) -> list[str]:
    with psycopg.connect(conninfo) as conn:
        rows = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = %s ORDER BY 1", (schema,)
        ).fetchall()
    return [row[0] for row in rows]


def schemas(conninfo: str) -> set[str]:
    with psycopg.connect(conninfo) as conn:
        rows = conn.execute(
            "SELECT nspname FROM pg_namespace WHERE nspname LIKE 'gold%'"
        ).fetchall()
    return {row[0] for row in rows}


def silver_builds(store: R2, table: SilverTable) -> set[str]:
    return {
        build
        for key in store.list_keys(paths.silver_cycle_dir(table, CYCLE))
        if (build := paths.build_of(key)) is not None
    }


@pytest.fixture
def conn(migrated_db: str, cli_env: Path) -> Any:
    with psycopg.connect(migrated_db, autocommit=True) as connection:
        yield connection


def test_the_first_publish_swaps_the_build_in_and_purges_after_the_cache_window(
    store: R2, cli_env: Path, migrated_db: str, conn: Any
) -> None:
    put_bronze(store)
    transform(B1)
    load(B1)
    recorder = Recorder(OK)

    result = publish(conn, store, cli_env, recorder)

    assert (result.build_id, result.previous_build_id, result.swapped, result.purged) == (
        B1,
        None,
        True,
        True,
    )
    live = meta(migrated_db, "gold")
    assert live is not None
    assert live["build_id"] == B1
    assert live["published_at"] is not None
    assert schemas(migrated_db) == {"gold", "gold_prev"}
    assert tables(migrated_db, "gold_prev") == []
    published = markers.read("published", store, cycle=CYCLE, build_id=B1)
    loaded = markers.read("loaded", store, cycle=CYCLE, build_id=B1)
    assert published is not None and loaded is not None
    assert published.row_counts == loaded.row_counts
    assert result.marker == published
    [(url, headers, body)] = recorder.cloudflare.posts
    assert url == f"https://api.cloudflare.com/client/v4/zones/{ZONE}/purge_cache"
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert body == b'{"purge_everything": true}'
    assert recorder.events == [f"sleep {PURGE_DELAY_SECONDS:g}", "post"]
    assert PURGE_DELAY_SECONDS == 75
    assert result.pruned == gold_publish.Pruned(0, 0)


class Poller(threading.Thread):
    """Reads the live build id over and over on its own autocommit connection, as the API does."""

    def __init__(self, conninfo: str) -> None:
        super().__init__(daemon=True)
        self.conninfo = conninfo
        self.seen: set[str] = set()
        self.errors: list[BaseException] = []
        self.reads = 0
        # Set once the first read is in, so the swap happens under a reader that is already polling.
        self.ready = threading.Event()
        self.stop = threading.Event()

    def run(self) -> None:
        try:
            with psycopg.connect(self.conninfo, autocommit=True, prepare_threshold=None) as conn:
                while not self.stop.is_set():
                    row = conn.execute("SELECT build_id FROM gold.meta").fetchone()
                    self.reads += 1
                    if row is not None:
                        self.seen.add(row[0])
                    self.ready.set()
        except BaseException as exc:
            self.errors.append(exc)
        finally:
            self.ready.set()


def test_a_second_publish_moves_the_first_to_gold_prev_and_a_reader_never_errors(
    store: R2, cli_env: Path, migrated_db: str, conn: Any
) -> None:
    put_bronze(store)
    transform(B1)
    load(B1)
    publish(conn, store, cli_env, Recorder(OK))
    transform(B2)
    load(B2)
    poller = Poller(migrated_db)
    poller.start()
    assert poller.ready.wait(timeout=10)

    result = publish(conn, store, cli_env, Recorder(OK))

    poller.stop.set()
    poller.join(timeout=10)
    assert poller.errors == []
    assert poller.reads > 0
    assert poller.seen == {B1, B2}
    assert (result.build_id, result.previous_build_id, result.swapped) == (B2, B1, True)
    live, previous = meta(migrated_db, "gold"), meta(migrated_db, "gold_prev")
    assert live is not None and previous is not None
    assert (live["build_id"], previous["build_id"]) == (B2, B1)
    assert schemas(migrated_db) == {"gold", "gold_prev"}
    assert markers.exists("published", store, cycle=CYCLE, build_id=B2)


def test_publish_prunes_silver_builds_older_than_the_previous_live_one(
    store: R2, cli_env: Path, migrated_db: str, conn: Any
) -> None:
    put_bronze(store)
    transform(B1)
    load(B1)
    publish(conn, store, cli_env, Recorder(OK))
    # Transformed after B1 went live (the first publish, with no previous build, prunes everything
    # older than B1): an old build id someone re-ran, the next build, and one after that.
    transform(B0, seats=False)
    transform(B3, seats=False)
    transform(B2)
    load(B2)
    assert silver_builds(store, "contribution") == {B0, B1, B2, B3}
    assert (cli_env / "silver" / "contribution" / f"cycle={CYCLE}" / f"build={B0}").exists()

    result = publish(conn, store, cli_env, Recorder(OK))

    assert result.pruned.builds == 1
    assert result.pruned.objects == 6
    assert silver_builds(store, "contribution") == {B1, B2, B3}
    assert silver_builds(store, "race") == {B1, B2}
    assert not (cli_env / "silver" / "contribution" / f"cycle={CYCLE}" / f"build={B0}").exists()
    assert (cli_env / "silver" / "contribution" / f"cycle={CYCLE}" / f"build={B1}").exists()
    # The run history stays.
    assert markers.exists("transformed", store, cycle=CYCLE, build_id=B0)


def test_rollback_restores_the_previous_build_and_a_second_rollback_undoes_it(
    store: R2, cli_env: Path, migrated_db: str, conn: Any
) -> None:
    put_bronze(store)
    transform(B1)
    load(B1)
    publish(conn, store, cli_env, Recorder(OK))
    transform(B2)
    load(B2)
    publish(conn, store, cli_env, Recorder(OK))
    recorder = Recorder(OK)

    rolled = gold_publish.rollback(conn, purge=recorder.purge, sleep=recorder.sleep)

    assert (rolled.build_id, rolled.previous_build_id) == (B1, B2)
    live, previous = meta(migrated_db, "gold"), meta(migrated_db, "gold_prev")
    assert live is not None and previous is not None
    assert (live["build_id"], previous["build_id"]) == (B1, B2)
    assert recorder.events == [f"sleep {PURGE_DELAY_SECONDS:g}", "post"]
    assert schemas(migrated_db) == {"gold", "gold_prev"}
    # Both builds were published; neither marker moves.
    assert markers.exists("published", store, cycle=CYCLE, build_id=B1)
    assert markers.exists("published", store, cycle=CYCLE, build_id=B2)

    again = gold_publish.rollback(conn, purge=recorder.purge, sleep=recorder.sleep)

    assert (again.build_id, again.previous_build_id) == (B2, B1)
    live = meta(migrated_db, "gold")
    assert live is not None and live["build_id"] == B2
    assert len(recorder.cloudflare.posts) == 2


def test_a_failed_purge_leaves_the_build_live_and_a_rerun_finishes_the_publish(
    store: R2, cli_env: Path, migrated_db: str, conn: Any
) -> None:
    put_bronze(store)
    transform(B1)
    load(B1)
    failing = Recorder(UPSTREAM)

    with pytest.raises(PurgeFailed):
        publish(conn, store, cli_env, failing)

    assert len(failing.cloudflare.posts) == 3
    live = meta(migrated_db, "gold")
    assert live is not None and live["build_id"] == B1
    assert not markers.exists("published", store, cycle=CYCLE, build_id=B1)
    assert "gold_build" not in schemas(migrated_db)

    recorder = Recorder(OK)
    result = publish(conn, store, cli_env, recorder)

    assert (result.build_id, result.swapped, result.purged) == (B1, False, True)
    assert result.previous_build_id is None
    assert len(recorder.cloudflare.posts) == 1
    assert markers.exists("published", store, cycle=CYCLE, build_id=B1)
    live = meta(migrated_db, "gold")
    assert live is not None and live["build_id"] == B1

    # Finished: there is nothing left to resume.
    with pytest.raises(NothingToPublish):
        publish(conn, store, cli_env, Recorder(OK))


def test_a_failed_purge_exits_non_zero_from_the_cli(
    store: R2, cli_env: Path, migrated_db: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    put_bronze(store)
    transform(B1)
    load(B1)
    monkeypatch.setenv("CLOUDFLARE_ZONE_ID", ZONE)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", TOKEN)
    get_settings.cache_clear()
    monkeypatch.setattr(cloudflare, "http_post", FakeCloudflare(UPSTREAM))
    # The CLI sleeps for real; neither wait is what this test is about.
    monkeypatch.setattr(cloudflare, "RETRY_SECONDS", 0.0)
    monkeypatch.setattr(gold_publish, "PURGE_DELAY_SECONDS", 0.0)

    result = run("publish", "--cycle", str(CYCLE))

    assert result.exit_code != 0
    assert isinstance(result.exception, PurgeFailed)
    live = meta(migrated_db, "gold")
    assert live is not None and live["build_id"] == B1
    assert not markers.exists("published", store, cycle=CYCLE, build_id=B1)


def test_publish_with_nothing_loaded_says_to_load(store: R2, cli_env: Path, conn: Any) -> None:
    result = run("publish", "--cycle", str(CYCLE))

    assert result.exit_code == 1
    assert f"fundlens load --cycle {CYCLE}" in result.output
    assert not markers.exists("published", store, cycle=CYCLE, build_id=B1)


def test_rollback_with_no_previous_build_is_an_error(cli_env: Path, conn: Any) -> None:
    result = run("publish", "--rollback")

    assert result.exit_code == 1
    assert "nothing to roll back" in result.output
    with pytest.raises(NothingToRollBack):
        gold_publish.rollback(conn, purge=None, sleep=lambda s: None)


def test_publish_needs_exactly_one_of_cycle_and_rollback(cli_env: Path) -> None:
    assert run("publish").exit_code == 2
    assert run("publish", "--rollback", "--cycle", str(CYCLE)).exit_code == 2
    assert run("publish", "--cycle", "2025").exit_code == 2


def test_an_unconfigured_zone_skips_the_purge_without_waiting(
    store: R2, cli_env: Path, migrated_db: str, caplog: pytest.LogCaptureFixture
) -> None:
    put_bronze(store)
    transform(B1)
    load(B1)
    assert get_settings().cloudflare_zone_id is None
    caplog.set_level(logging.INFO, logger="fundlens.publish.gold")

    result = run("publish", "--cycle", str(CYCLE))

    assert result.exit_code == 0, result.output
    assert f"published build {B1} of {CYCLE}" in result.output
    assert "cloudflare purge: skipped (not configured)" in result.output
    assert "cloudflare purge skipped: not configured" in caplog.text
    live = meta(migrated_db, "gold")
    assert live is not None and live["build_id"] == B1
    assert markers.exists("published", store, cycle=CYCLE, build_id=B1)
