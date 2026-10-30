"""Cache headers and the build-id cache behind the `ETag` (spec §7.2)."""

from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient

from fundlens.api.cache import CACHE_CONTROL, NO_STORE, BuildIdCache, CacheHeaders
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


def test_a_client_error_is_cacheable_too() -> None:
    response = make_client().get("/v1/nothing-here")

    assert response.status_code == 404
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
    cache = BuildIdCache(lambda: reads.pop(0), ttl=60, clock=clock)

    assert cache.get() == BUILD_ID
    clock.now = 59.9
    assert cache.get() == BUILD_ID
    clock.now = 60.0
    assert cache.get() == "20261109T030000Z"


def test_no_build_is_cached_like_any_other_answer() -> None:
    reads: list[str | None] = [None, BUILD_ID]
    clock = Clock()
    cache = BuildIdCache(lambda: reads.pop(0), ttl=60, clock=clock)

    assert cache.get() is None
    assert cache.get() is None
    clock.now = 60.0
    assert cache.get() == BUILD_ID
