"""Every error the API returns as an RFC 9457 problem details document (spec §7.2).

Routes raise `HTTPException` as usual; the handlers here render it, FastAPI's request
validation errors, and any unhandled exception as `application/problem+json`. No route defines
its own problem `type`, so each is `about:blank` and its `title` is the status phrase, as the
RFC prescribes for that case.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from fundlens.api.cache import NO_STORE

PROBLEM_JSON = "application/problem+json"


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
    app.add_exception_handler(Exception, _unhandled)
