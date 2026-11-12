"""Cache headers and the build-id cache behind the `ETag` (spec §7.2)."""

import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient

from fundlens.api.cache import CACHE_CONTROL, NO_STORE, CacheHeaders, TtlCache
from fundlens.api.problems import install_problem_handlers

BUILD_ID = "20261102T030000Z"


class FixedBuildIds:
    def __init__(self, build_id: str | None) -> None:
        self.build_id = build_id

    def get(self) -> str | None:
        return self.build_id


def make_client(build_id: str | None = BUILD_ID) -> TestClient:
    app = FastAPI()
    install_problem_handlers(app)
    app.add_middleware(CacheHeaders)
    app.state.build_ids = FixedBuildIds(build_id)

    @app.get("/v1/thing")
    def thing() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"ok": "yes"}

    @app.get("/healthz")
    def healthz() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"ok": "yes"}

    @app.get("/v1/down")
    def down() -> None:  # pyright: ignore[reportUnusedFunction]
        raise HTTPException(503, "down")

    @app.get("/v1/missing")
    def missing() -> None:  # pyright: ignore[reportUnusedFunction]
        raise HTTPException(404, "no such committee")

    @app.get("/v1/bad-cursor")
    def bad_cursor() -> None:  # pyright: ignore[reportUnusedFunction]
        raise HTTPException(400, "bad cursor")

    @app.get("/v1/gone")
    def gone() -> None:  # pyright: ignore[reportUnusedFunction]
        raise HTTPException(410, "gone")

    @app.get("/v1/number/{n}")
    def number(n: int) -> int:  # pyright: ignore[reportUnusedFunction]
        return n

    @app.get("/v1/own")
    def own(response: Response) -> None:  # pyright: ignore[reportUnusedFunction]
        response.headers["Cache-Control"] = "private"

    return TestClient(app)


def test_a_response_is_cacheable_with_the_build_as_its_etag() -> None:
    response = make_client().get("/v1/thing")

    assert response.headers["cache-control"] == CACHE_CONTROL
    assert response.headers["etag"] == f'"{BUILD_ID}"'


def test_no_etag_before_any_build_is_published() -> None:
    response = make_client(build_id=None).get("/v1/thing")

    assert response.headers["cache-control"] == CACHE_CONTROL
    assert "etag" not in response.headers


@pytest.mark.parametrize("path", ["/v1/nothing-here", "/v1/missing"])
def test_a_not_found_is_never_cached(path: str) -> None:
    # Routes change on deploy and a deploy purges nothing, so a cached 404 for a path the old
    # image did not serve would outlive the deploy that adds it.
    response = make_client().get(path)

    assert response.status_code == 404
    assert response.headers["cache-control"] == NO_STORE
    assert "etag" not in response.headers


@pytest.mark.parametrize(
    ("path", "status"), [("/v1/bad-cursor", 400), ("/v1/gone", 410), ("/v1/number/x", 422)]
)
def test_other_client_errors_stay_cacheable(path: str, status: int) -> None:
    response = make_client().get(path)

    assert response.status_code == status
    assert response.headers["cache-control"] == CACHE_CONTROL


def test_healthz_is_never_cached() -> None:
    response = make_client().get("/healthz")

    assert response.headers["cache-control"] == NO_STORE
    assert "etag" not in response.headers


def test_a_server_error_is_never_cached() -> None:
    response = make_client().get("/v1/down")

    assert response.status_code == 503
    assert response.headers["cache-control"] == NO_STORE
    assert "etag" not in response.headers


def test_a_route_that_sets_cache_control_keeps_it() -> None:
    response = make_client().get("/v1/own")

    assert response.headers["cache-control"] == "private"


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_build_id_is_read_once_per_ttl() -> None:
    reads: list[str | None] = [BUILD_ID, "20261109T030000Z"]
    clock = Clock()
    cache = TtlCache(lambda: reads.pop(0), ttl=60, clock=clock)

    assert cache.get() == BUILD_ID
    clock.now = 59.9
    assert cache.get() == BUILD_ID
    clock.now = 60.0
    assert cache.get() == "20261109T030000Z"


def test_no_build_is_cached_like_any_other_answer() -> None:
    reads: list[str | None] = [None, BUILD_ID]
    clock = Clock()
    cache = TtlCache(lambda: reads.pop(0), ttl=60, clock=clock)

    assert cache.get() is None
    assert cache.get() is None
    clock.now = 60.0
    assert cache.get() == BUILD_ID
