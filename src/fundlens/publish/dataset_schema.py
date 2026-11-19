"""The dataset's JSON Schemas, `docs/dataset/schema/<table>.json` (spec §9, NEU-2065).

One schema per table of a snapshot's manifest, each describing one row: its columns as the
Parquet file holds them, typed from the file's own schema, and described from
`docs/dataset/columns.yaml`, which a person writes. The schemas are generated and committed, and
`tests/integration/test_dataset.py` regenerates them from a fresh snapshot of the fixture cycle:
a silver column added, dropped, renamed or retyped without its description and schema updated
fails CI. `task dataset:schema` writes them.

A column's type is DuckDB's reading of the Parquet type (`x-duckdb-type`), mapped to the nearest
JSON type. Every column may be null: DuckDB writes every Parquet column optional, so the files
cannot say which never is.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import duckdb
import yaml
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from fundlens.transform.runner import literal

# What the snapshot publisher serves the schemas under (`v1/schema/`, spec §9).
SCHEMA_DIR = "schema"
COLUMNS = "columns.yaml"
_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_ID = "https://data.fundlens.org/v1/schema/{table}.json"

# DuckDB's type names as `DESCRIBE` gives them, by the JSON type a reader sees. A DECIMAL, a
# DATE and a TIMESTAMP match by their prefix; a type in neither table fails the generation, so a
# new one is mapped here on purpose rather than guessed.
_JSON_TYPES: dict[str, str] = {
    "BOOLEAN": "boolean",
    "TINYINT": "integer",
    "SMALLINT": "integer",
    "INTEGER": "integer",
    "BIGINT": "integer",
    "HUGEINT": "integer",
    "UTINYINT": "integer",
    "USMALLINT": "integer",
    "UINTEGER": "integer",
    "UBIGINT": "integer",
    "FLOAT": "number",
    "DOUBLE": "number",
    "VARCHAR": "string",
}
_PREFIXED: dict[str, dict[str, str]] = {
    "DECIMAL(": {"type": "number"},
    "DATE": {"type": "string", "format": "date"},
    "TIMESTAMP WITH TIME ZONE": {"type": "string", "format": "date-time"},
    "TIMESTAMP": {"type": "string", "format": "date-time"},
}


class SchemaDocsError(Exception):
    """The columns' descriptions and the Parquet files disagree, or a type is unmapped."""


class TableDoc(BaseModel):
    """One table's entry in `columns.yaml`."""

    model_config = ConfigDict(extra="forbid")

    description: str
    # The columns that identify a row, in order; empty for none.
    key: list[str]
    # Every column of the file, in no particular order: the schema keeps the file's.
    columns: dict[str, str]


_DOCS = TypeAdapter(dict[str, TableDoc])


def load_docs(path: Path) -> dict[str, TableDoc]:
    """`columns.yaml`, by table. Raises `SchemaDocsError` when it is not one."""
    try:
        loaded = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise SchemaDocsError(f"{path} is not YAML: {exc}") from exc
    try:
        return _DOCS.validate_python(loaded)
    except ValidationError as exc:
        raise SchemaDocsError(f"{path} does not map each table to its description: {exc}") from exc


def columns(parquet: Path) -> list[tuple[str, str]]:
    """`parquet`'s columns, in file order, as names and DuckDB types. Hive partitioning is off: a
    `cycle=<c>` directory is no column of the file."""
    with duckdb.connect() as con:
        rows = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({literal(parquet)}, hive_partitioning = false)"
        ).fetchall()
    return [(str(name), str(kind)) for name, kind, *_ in rows]


def committed_columns(docs_dir: Path, table: str) -> list[tuple[str, str]]:
    """`table`'s columns as its committed schema records them: each name with its DuckDB type,
    in the file's order; the inverse of `columns`. Raises `FileNotFoundError` when `docs_dir`
    holds no schema for it."""
    schema = json.loads((docs_dir / SCHEMA_DIR / f"{table}.json").read_text())
    return [(str(name), str(prop["x-duckdb-type"])) for name, prop in schema["properties"].items()]


def json_type(duckdb_type: str) -> dict[str, str]:
    """The JSON Schema type of a column DuckDB reads as `duckdb_type`."""
    if duckdb_type in _JSON_TYPES:
        return {"type": _JSON_TYPES[duckdb_type]}
    for prefix, mapped in _PREFIXED.items():
        if duckdb_type.startswith(prefix):
            return dict(mapped)
    raise SchemaDocsError(f"no JSON type for DuckDB's {duckdb_type}: map it in {__name__}")


def table_schema(table: str, found: list[tuple[str, str]], doc: TableDoc) -> dict[str, Any]:
    """The JSON Schema of one row of `table`, whose file holds the columns `found`."""
    names = [name for name, _ in found]
    undocumented = [name for name in names if name not in doc.columns]
    absent = sorted(set(doc.columns) - set(names))
    unknown_key = [name for name in doc.key if name not in names]
    problems = [
        f"{label}: {', '.join(listed)}"
        for label, listed in (
            ("columns without a description", undocumented),
            ("described columns the file lacks", absent),
            ("key columns the file lacks", unknown_key),
        )
        if listed
    ]
    if problems:
        raise SchemaDocsError(f"{COLUMNS}, table {table}: " + "; ".join(problems))
    properties: dict[str, Any] = {}
    for name, kind in found:
        mapped = json_type(kind)
        properties[name] = {
            "description": doc.columns[name].strip(),
            "type": [mapped["type"], "null"],
            **({"format": mapped["format"]} if "format" in mapped else {}),
            "x-duckdb-type": kind,
        }
    return {
        "$schema": _DRAFT,
        "$id": _ID.format(table=table),
        "title": table,
        "description": doc.description.strip(),
        "x-key": doc.key,
        "type": "object",
        "properties": properties,
        "required": names,
        "additionalProperties": False,
    }


def render(schema: Mapping[str, Any]) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def generate(files: Mapping[str, Path], docs_path: Path) -> dict[str, str]:
    """Each table's schema file, by its path below the docs directory
    (`schema/<table>.json`), from one Parquet file of each table in `files`. Raises
    `SchemaDocsError` when `columns.yaml` describes a table `files` lacks, or misses one."""
    docs = load_docs(docs_path)
    missing = sorted(set(files) - set(docs))
    extra = sorted(set(docs) - set(files))
    if missing or extra:
        raise SchemaDocsError(
            f"{COLUMNS} must describe exactly the dataset's tables:"
            f" missing {missing or 'none'}, not in the dataset {extra or 'none'}"
        )
    return {
        f"{SCHEMA_DIR}/{table}.json": render(table_schema(table, columns(path), docs[table]))
        for table, path in sorted(files.items())
    }


def differences(docs_dir: Path, generated: Mapping[str, str]) -> list[str]:
    """The schema files under `docs_dir` that are not as `generated` has them, or that it
    lacks."""
    committed = {
        f"{SCHEMA_DIR}/{path.name}": path.read_text()
        for path in sorted((docs_dir / SCHEMA_DIR).glob("*.json"))
    }
    return sorted(
        name
        for name in set(committed) | set(generated)
        if committed.get(name) != generated.get(name)
    )


def write(docs_dir: Path, generated: Mapping[str, str]) -> None:
    """Make the schema files under `docs_dir` exactly `generated`."""
    schema_dir = docs_dir / SCHEMA_DIR
    schema_dir.mkdir(parents=True, exist_ok=True)
    for stale in schema_dir.glob("*.json"):
        if f"{SCHEMA_DIR}/{stale.name}" not in generated:
            stale.unlink()
    for name, text in generated.items():
        (docs_dir / name).write_text(text)
