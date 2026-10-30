"""Every error the API returns as an RFC 9457 problem details document (spec §7.2).

Routes raise `HTTPException` as usual; the handlers here render it, FastAPI's request
validation errors, and any unhandled exception as `application/problem+json`. No route defines
its own problem `type`, so each is `about:blank` and its `title` is the status phrase, as the
RFC prescribes for that case.

A query against a `gold` table is a 503, not a 500, while there is no `gold` schema: before the
first publish the API is waiting for data, not failing. A table missing from a live `gold` is a
bug, and stays a 500 that reaches Sentry.
"""

from collections.abc import Mapping
from functools import partial
from http import HTTPStatus
from typing import Any

import psycopg
from anyio import to_thread
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from fundlens.api.cache import NO_STORE
from fundlens.api.schemas import PROBLEM_JSON
from fundlens.load.db import Pool

NO_GOLD = "No gold build has been published yet."


class ProblemResponse(JSONResponse):
    media_type = PROBLEM_JSON


def problem(
    status: int,
    detail: str,
    *,
    headers: Mapping[str, str] | None = None,
    **extensions: Any,
) -> ProblemResponse:
    return ProblemResponse(
        {
            "type": "about:blank",
            "title": HTTPStatus(status).phrase,
            "status": status,
            "detail": detail,
            **extensions,
        },
        status_code=status,
        headers=headers,
    )


# Typed `Exception`, not the subclass each handles: Starlette's handler type takes the base
# class, and a narrower parameter would not be assignable to it.
async def _http_exception(request: Request, exc: Exception) -> ProblemResponse:
    assert isinstance(exc, StarletteHTTPException)
    return problem(exc.status_code, str(exc.detail), headers=exc.headers)


async def _validation_error(request: Request, exc: Exception) -> ProblemResponse:
    assert isinstance(exc, RequestValidationError)
    return problem(
        HTTPStatus.UNPROCESSABLE_CONTENT,
        "The request's parameters are invalid.",
        errors=jsonable_encoder(exc.errors()),
    )


def _gold_exists(pool: Pool) -> bool:
    with pool.connection() as conn:
        return (
            conn.execute("SELECT 1 FROM pg_namespace WHERE nspname = 'gold'").fetchone() is not None
        )


async def _no_gold(request: Request, exc: Exception) -> ProblemResponse:
    assert isinstance(exc, psycopg.errors.UndefinedTable)
    if await to_thread.run_sync(partial(_gold_exists, request.app.state.pool)):
        # Re-raised to the server-error handler: a 500, and Sentry hears of it.
        raise exc
    return problem(HTTPStatus.SERVICE_UNAVAILABLE, NO_GOLD)


async def _unhandled(request: Request, exc: Exception) -> ProblemResponse:
    # Starlette re-raises the exception after this response is sent, so Sentry still reports it.
    # The response leaves before the cache-header middleware sees it, so it says no-store itself.
    return problem(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "The server failed to answer this request.",
        headers={"Cache-Control": NO_STORE},
    )


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(psycopg.errors.UndefinedTable, _no_gold)
    app.add_exception_handler(Exception, _unhandled)
