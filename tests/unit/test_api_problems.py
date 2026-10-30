"""Errors as RFC 9457 problem details (spec §7.2)."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from fundlens.api.cache import NO_STORE
from fundlens.api.problems import PROBLEM_JSON, install_problem_handlers


def make_client() -> TestClient:
    app = FastAPI()
    install_problem_handlers(app)

    @app.get("/teapot")
    def teapot() -> None:  # pyright: ignore[reportUnusedFunction]
        raise HTTPException(418, "Short and stout.", headers={"Retry-After": "60"})

    @app.get("/cycles/{cycle}")
    def cycle(cycle: int) -> int:  # pyright: ignore[reportUnusedFunction]
        return cycle

    @app.get("/boom")
    def boom() -> None:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("boom")

    # Starlette re-raises an unhandled exception after the handler's response by default.
    return TestClient(app, raise_server_exceptions=False)


def test_an_unknown_route_is_a_404_problem() -> None:
    response = make_client().get("/nowhere")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
    }


def test_an_http_exception_keeps_its_detail_and_headers() -> None:
    response = make_client().get("/teapot")

    assert response.status_code == 418
    assert response.json()["title"] == "I'm a Teapot"
    assert response.json()["detail"] == "Short and stout."
    assert response.headers["retry-after"] == "60"


def test_a_validation_error_is_a_422_problem_listing_the_errors() -> None:
    response = make_client().get("/cycles/not-a-year")

    body = response.json()
    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    assert body["title"] == "Unprocessable Content"
    assert [error["loc"] for error in body["errors"]] == [["path", "cycle"]]


def test_an_unhandled_exception_is_an_uncached_500_problem() -> None:
    response = make_client().get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["detail"] == "The server failed to answer this request."
    assert response.headers["cache-control"] == NO_STORE
