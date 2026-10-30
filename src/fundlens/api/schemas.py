"""Pydantic response models: the OpenAPI contract the frontend's client is generated from."""

from datetime import datetime

from pydantic import BaseModel, JsonValue


class Problem(BaseModel):
    """An RFC 9457 problem details document (`application/problem+json`)."""

    type: str
    title: str
    status: int
    detail: str


class Health(BaseModel):
    postgres: str
    silver: str


class Meta(BaseModel):
    """The live gold build (`gold.meta`, spec §7.1)."""

    build_id: str
    published_at: datetime
    resolver_version: str
    model_version: str
    precision: float | None
    recall: float | None
    # cycle → its live build_id and source download dates. Left loose until the gold build
    # writes it (NEU-2040 types it).
    cycles: dict[str, JsonValue]


def problem_responses(*statuses: int) -> dict[int | str, dict[str, object]]:
    """A route's `responses=` entry documenting `statuses` as problem details."""
    return {
        status: {"model": Problem, "content": {"application/problem+json": {}}}
        for status in statuses
    }
