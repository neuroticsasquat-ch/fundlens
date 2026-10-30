"""The OpenAPI document is the frontend's contract (spec §7.2): every route is in it, and every
response it describes is typed down to its leaves, so the generated client has no `unknown`."""

from typing import Any, cast

from fundlens.api.app import create_app
from fundlens.settings import get_settings

ROUTES = {
    "/healthz",
    "/v1/meta",
    "/v1/cycles",
    "/v1/cycles/{cycle}/races",
    "/v1/races/{cycle}/{office}/{place}",
    "/v1/candidates/{candidate_id}",
    "/v1/committees/{committee_id}",
    "/v1/search",
}


def openapi() -> dict[str, Any]:
    return create_app(get_settings()).openapi()


def untyped(node: object, where: str) -> list[str]:
    """Every place under `node` that admits any JSON at all: no `type`, `$ref` or
    composition, or an object with neither properties nor a typed `additionalProperties`."""
    if not isinstance(node, dict):
        return []
    schema = cast(dict[str, Any], node)
    found: list[str] = []
    if not schema.keys() & {"type", "$ref", "anyOf", "oneOf", "allOf", "enum", "const"}:
        found.append(where)
    if schema.get("type") == "object" and "properties" not in schema:
        additional = schema.get("additionalProperties")
        if not isinstance(additional, dict) or not additional:
            found.append(where)
    for key, value in schema.items():
        if key == "properties":
            for name, prop in value.items():
                found += untyped(prop, f"{where}.{name}")
        elif key in {"items", "additionalProperties"}:
            found += untyped(value, f"{where}[{key}]")
        elif key in {"anyOf", "oneOf", "allOf"}:
            for i, option in enumerate(value):
                found += untyped(option, f"{where}|{i}")
    return found


def test_every_route_is_documented_with_a_typed_200() -> None:
    document = openapi()

    assert set(document["paths"]) == ROUTES
    for path, item in document["paths"].items():
        schema = item["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert schema.keys() & {"$ref", "type"}, path
        assert untyped(schema, path) == []


def test_no_schema_admits_untyped_json() -> None:
    schemas = openapi()["components"]["schemas"]

    assert [where for name, schema in schemas.items() for where in untyped(schema, name)] == []


def test_errors_are_documented_as_problem_details() -> None:
    paths = openapi()["paths"]

    races = paths["/v1/races/{cycle}/{office}/{place}"]["get"]["responses"]
    assert set(races) == {"200", "404", "422", "503"}
    assert races["404"]["content"]["application/problem+json"]["schema"] == {
        "$ref": "#/components/schemas/Problem"
    }
    assert races["422"]["content"]["application/problem+json"]["schema"] == {
        "$ref": "#/components/schemas/ValidationProblem"
    }
