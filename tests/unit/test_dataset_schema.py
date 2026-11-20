"""The dataset's JSON Schemas from a Parquet file's columns and `columns.yaml` (NEU-2065)."""

from pathlib import Path

import duckdb
import pytest

from fundlens.load import gold
from fundlens.publish import dataset_schema
from fundlens.publish.dataset import MANIFEST_TABLES
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


DATASET_DOCS = Path(__file__).resolve().parents[2] / "docs" / "dataset"


@pytest.mark.parametrize("table", MANIFEST_TABLES)
def test_a_committed_schemas_columns_type_an_empty_view_as_the_file_has_them(table: str) -> None:
    committed = dataset_schema.committed_columns(DATASET_DOCS, table)

    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA silver")
        gold._empty_view(con, table, DATASET_DOCS)  # pyright: ignore[reportPrivateUsage]
        described = con.execute(f"DESCRIBE silver.{table}").fetchall()
        [(rows,)] = con.execute(f"SELECT count(*) FROM silver.{table}").fetchall()

    assert committed
    assert [(name, kind) for name, kind, *_ in described] == committed
    assert rows == 0


def test_a_table_with_no_committed_schema_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        dataset_schema.committed_columns(tmp_path, "race")


def test_a_column_no_build_of_the_load_has_reads_as_null(tmp_path: Path) -> None:
    # Every build transformed before organization_receipt.is_returned_cost existed (NEU-2402):
    # union_by_name cannot add a column no file has, so the view adds it from the committed schema.
    # A table the dataset does not publish (jfc_attribution) is left as its files have it.
    receipts, attributions = tmp_path / "organization_receipt", tmp_path / "jfc_attribution"
    receipts.mkdir()
    attributions.mkdir()
    with duckdb.connect() as con:
        con.execute(
            f"COPY (SELECT 2024 AS cycle, 'C1' AS recipient_committee_id, 500 AS amount)"
            f" TO {literal(receipts / 'part-0.parquet')}"
        )
        con.execute(f"COPY (SELECT 2024 AS cycle) TO {literal(attributions / 'part-0.parquet')}")
        gold._register_silver(  # pyright: ignore[reportPrivateUsage]
            con,
            {"organization_receipt": [receipts], "jfc_attribution": [attributions]},
            docs_dir=DATASET_DOCS,
        )
        [(amount, returned)] = con.execute(
            "SELECT amount, is_returned_cost FROM silver.organization_receipt"
        ).fetchall()
        described = {
            name: kind
            for name, kind, *_ in con.execute("DESCRIBE silver.organization_receipt").fetchall()
        }
        attribution_columns = [
            name for name, *_ in con.execute("DESCRIBE silver.jfc_attribution").fetchall()
        ]

    assert (amount, returned) == (500, None)
    assert described["is_returned_cost"] == "BOOLEAN"
    assert described.keys() >= {
        name for name, _ in dataset_schema.committed_columns(DATASET_DOCS, "organization_receipt")
    }
    assert attribution_columns == ["cycle", "donor_id"]
