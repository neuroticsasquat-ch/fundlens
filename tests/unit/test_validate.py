"""Resolution scored against DIME: the pairwise counts, the truth filter on a DIME file, and the
newest saved model (NEU-2054 §8.2, ADR-0009)."""

from pathlib import Path

import duckdb
import pytest

from fundlens import paths
from fundlens.resolve import model, validate
from fundlens.resolve.validate import Score
from fundlens.transform.runner import Limits

LIMITS = Limits(memory_limit=None, max_temp_directory_size="1GB", threads=1)


def scored(records: list[tuple[str, int, str]]) -> Score:
    with duckdb.connect() as con:
        con.execute("CREATE TABLE records (contributor_key TEXT, donor_id BIGINT, bonica_cid TEXT)")
        if records:
            con.executemany("INSERT INTO records VALUES (?, ?, ?)", records)
        return validate.score(con, "records")


def test_score_counts_the_pairs_of_a_contingency_table() -> None:
    # d1 holds k1, k2 (c1) and k3 (c2): one correct pair of three predicted. c2 is k3 and k4,
    # which fundlens split: one of the two true pairs found.
    result = scored(
        [("k1", 1, "c1"), ("k2", 1, "c1"), ("k3", 1, "c2"), ("k4", 2, "c2"), ("k5", 3, "c3")]
    )

    assert result == Score(labelled_keys=5, correct_pairs=1, predicted_pairs=3, true_pairs=2)
    assert result.precision == pytest.approx(1 / 3)
    assert result.recall == pytest.approx(1 / 2)


def test_no_records_score_nothing() -> None:
    result = scored([])

    assert result == Score(0, 0, 0, 0)
    assert (result.precision, result.recall) == (None, None)


def test_records_each_alone_have_no_pairs_to_score() -> None:
    result = scored([("k1", 1, "c1"), ("k2", 2, "c2")])

    assert (result.predicted_pairs, result.true_pairs) == (0, 0)
    assert (result.precision, result.recall) == (None, None)


HEADER = (
    "cycle,transaction.id,transaction.type,amount,date,bonica.cid,contributor.name,"
    "contributor.type,bonica.rid,efec.transaction.id.orig,efec.comid.orig"
)
ROWS = [
    # A committee's contribution: not an individual's.
    "2024,t1,15,100,2024-01-02,111,acme pac,C,comm1,SA11AI.1,C00000001",
    # No FEC committee id: a paper filing.
    '2024,t2,15,100,2024-01-02,222,"doe, jane",I,comm1,SA11AI.2,\\N',
    # A state committee's id, not an FEC one.
    '2024,t3,15,100,2024-01-02,333,"doe, jane",I,comm1,SA11AI.3,MD12345',
    # A null amount.
    '2024,t4,15,\\N,2024-01-02,444,"doe, jane",I,comm1,SA11AI.4,C00000001',
    # A date that is no date.
    '2024,t5,15,100,2024-13-45,555,"doe, jane",I,comm1,SA11AI.5,C00000001',
    '2024,t6,15,250.50,2024-03-04,5000002667852691,"roe, rick",I,comm1,SA11AI.6,C00000001',
]


class RecordingStore:
    """The one R2 call `import_dime` makes, recorded."""

    def __init__(self) -> None:
        self.put_keys: list[str] = []

    def put(self, key: str, body: bytes | Path) -> None:
        self.put_keys.append(key)


def test_the_truth_filter_keeps_individual_fec_rows_that_cast(tmp_path: Path) -> None:
    source = tmp_path / "contribDB_2024.csv"
    source.write_text("\n".join([HEADER, *ROWS]) + "\n")
    store = RecordingStore()

    result = validate.import_dime(
        store,  # pyright: ignore[reportArgumentType]
        cycle=2024,
        path=source,
        data_dir=tmp_path / "data",
        limits=LIMITS,
    )

    assert (result.rows_read, result.rows_kept, result.rows_dropped) == (6, 1, 2)
    assert result.cids == 1
    assert store.put_keys == [
        paths.reference_dime("4.0", 2024),
        paths.reference_dime_raw("4.0", 2024),
    ]
    parquet = paths.local_path(tmp_path / "data", paths.reference_dime("4.0", 2024))
    with duckdb.connect() as con:
        rows = con.execute(
            "SELECT transaction_id, cmte_id, tran_id, amount::VARCHAR, date::VARCHAR,"
            " bonica_cid, transaction_type, contributor_name FROM read_parquet(?)",
            [str(parquet)],
        ).fetchall()
    assert rows == [
        (
            "t6",
            "C00000001",
            "SA11AI.6",
            "250.50",
            "2024-03-04",
            "5000002667852691",
            "15",
            "roe, rick",
        )
    ]


def test_a_dime_file_missing_a_column_is_refused_naming_it(tmp_path: Path) -> None:
    source = tmp_path / "contribDB_2024.csv"
    source.write_text(HEADER.replace(",efec.comid.orig", "") + "\n")

    with pytest.raises(ValueError, match="no efec.comid.orig column"):
        validate.import_dime(
            RecordingStore(),  # pyright: ignore[reportArgumentType]
            cycle=2024,
            path=source,
            data_dir=tmp_path / "data",
            limits=LIMITS,
        )


class ListingStore:
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys

    def list_keys(self, prefix: str) -> list[str]:
        return sorted(key for key in self.keys if key.startswith(prefix))


def test_the_latest_model_is_the_newest_saved_version() -> None:
    store = ListingStore(
        [
            paths.resolution_model("20261031T040000Z"),
            paths.resolution_model("20261107T040000Z"),
            "resolution/model/20261114T040000Z.json.part",
        ]
    )

    assert model.latest_version(store) == "20261107T040000Z"  # pyright: ignore[reportArgumentType]
    assert model.latest_version(ListingStore([])) is None  # pyright: ignore[reportArgumentType]
