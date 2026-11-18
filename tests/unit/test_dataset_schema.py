"""The dataset's JSON Schemas from a Parquet file's columns and `columns.yaml` (NEU-2065)."""

from pathlib import Path

import duckdb
import pytest

from fundlens.publish import dataset_schema
from fundlens.publish.dataset_schema import SchemaDocsError, TableDoc
from fundlens.transform.runner import literal

DOC = TableDoc(
    description="One race.\n",
    key=["race_id"],
    columns={"race_id": "The race.", "cycle": "Its cycle.", "is_special": "A special election."},
)
FOUND = [("race_id", "VARCHAR"), ("cycle", "BIGINT"), ("is_special", "BOOLEAN")]


@pytest.mark.parametrize(
    ("duckdb_type", "expected"),
    [
        ("VARCHAR", {"type": "string"}),
        ("UBIGINT", {"type": "integer"}),
        ("DOUBLE", {"type": "number"}),
        ("DECIMAL(14,2)", {"type": "number"}),
        ("DATE", {"type": "string", "format": "date"}),
        ("TIMESTAMP WITH TIME ZONE", {"type": "string", "format": "date-time"}),
        ("BOOLEAN", {"type": "boolean"}),
    ],
)
def test_a_duckdb_type_maps_to_its_json_type(duckdb_type: str, expected: dict[str, str]) -> None:
    assert dataset_schema.json_type(duckdb_type) == expected


def test_an_unmapped_type_fails_rather_than_being_guessed() -> None:
    with pytest.raises(SchemaDocsError, match="INTERVAL"):
        dataset_schema.json_type("INTERVAL")


def test_a_schema_keeps_the_files_column_order_and_allows_nulls() -> None:
    schema = dataset_schema.table_schema("race", FOUND, DOC)

    assert schema["$id"] == "https://data.fundlens.org/v1/schema/race.json"
    assert schema["description"] == "One race."
    assert schema["x-key"] == ["race_id"]
    assert list(schema["properties"]) == schema["required"] == ["race_id", "cycle", "is_special"]
    assert schema["properties"]["cycle"] == {
        "description": "Its cycle.",
        "type": ["integer", "null"],
        "x-duckdb-type": "BIGINT",
    }
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize(
    ("found", "key", "message"),
    [
        ([*FOUND, ("slug", "VARCHAR")], ["race_id"], "columns without a description: slug"),
        (FOUND[:2], ["race_id"], "described columns the file lacks: is_special"),
        (FOUND, ["race_id", "office"], "key columns the file lacks: office"),
    ],
)
def test_a_column_the_docs_and_the_file_disagree_on_fails(
    found: list[tuple[str, str]], key: list[str], message: str
) -> None:
    doc = DOC.model_copy(update={"key": key})

    with pytest.raises(SchemaDocsError, match=message):
        dataset_schema.table_schema("race", found, doc)


def test_columns_are_the_files_own_not_its_hive_partition(tmp_path: Path) -> None:
    partition = tmp_path / "race" / "cycle=2024"
    partition.mkdir(parents=True)
    parquet = partition / "part-0000.parquet"
    with duckdb.connect() as con:
        con.execute(f"COPY (SELECT 'H-2024-CA-12' AS race_id) TO {literal(parquet)}")

    assert dataset_schema.columns(parquet) == [("race_id", "VARCHAR")]


def test_the_docs_must_describe_exactly_the_datasets_tables(tmp_path: Path) -> None:
    docs = tmp_path / "columns.yaml"
    docs.write_text("race:\n  description: One race.\n  key: []\n  columns: {}\n")

    with pytest.raises(SchemaDocsError, match=r"missing \['donor'\], not in the dataset none"):
        dataset_schema.generate({"race": tmp_path / "r.parquet", "donor": tmp_path / "d"}, docs)


def test_differences_name_changed_missing_and_stale_schemas(tmp_path: Path) -> None:
    (tmp_path / "schema").mkdir()
    (tmp_path / "schema" / "race.json").write_text("{}\n")
    (tmp_path / "schema" / "dropped.json").write_text("{}\n")
    generated = {"schema/race.json": "{}\n", "schema/donor.json": "{}\n"}

    assert dataset_schema.differences(tmp_path, generated) == [
        "schema/donor.json",
        "schema/dropped.json",
    ]

    dataset_schema.write(tmp_path, generated)

    assert dataset_schema.differences(tmp_path, generated) == []
