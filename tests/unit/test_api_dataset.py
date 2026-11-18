"""`api.dataset.summarize`: a snapshot's manifest as `GET /v1/dataset` lists it (spec §9)."""

from datetime import date

from fundlens.api.dataset import PUBLIC_URL, summarize
from fundlens.api.schemas import DatasetPart
from fundlens.publish.dataset import Manifest, ManifestFile, ManifestTable


def file(path: str, size: int) -> ManifestFile:
    return ManifestFile(path=path, sha256="0" * 64, bytes=size)


MANIFEST = Manifest(
    snapshot_date=date(2026, 11, 22),
    build_id="20261122T030000Z",
    cycles={2022: "20261001T030000Z", 2024: "20261122T030000Z"},
    tables={
        "contribution": ManifestTable(
            rows=30,
            files=[
                file("contribution/cycle=2022/bucket-00-part-0000.parquet", 5),
                file("contribution/cycle=2024/bucket-00-part-0000.parquet", 10),
                file("contribution/cycle=2024/bucket-01-part-0000.parquet", 20),
            ],
        ),
        "race": ManifestTable(
            rows=4,
            files=[
                file("race/cycle=2022/part-0000.parquet", 1),
                file("race/cycle=2024/part-0000.parquet", 2),
            ],
        ),
        "donor": ManifestTable(rows=7, files=[file("donor.parquet", 3)]),
    },
    overrides=file("overrides.yaml", 9),
    precision=0.97,
    recall=None,
)


def test_a_snapshot_is_listed_with_its_tables_in_the_manifests_order() -> None:
    snapshot = summarize(MANIFEST)

    assert snapshot.snapshot_date == date(2026, 11, 22)
    assert snapshot.url == f"{PUBLIC_URL}2026-11-22/"
    assert snapshot.build_id == "20261122T030000Z"
    assert snapshot.cycles == [2024, 2022]
    assert [table.name for table in snapshot.tables] == ["contribution", "race", "donor"]
    assert (snapshot.precision, snapshot.recall) == (0.97, None)
    assert (snapshot.license, snapshot.attribution) == (MANIFEST.license, MANIFEST.attribution)


def test_each_cycles_files_are_one_part_and_a_lone_file_is_linked_itself() -> None:
    contribution, race, donor = summarize(MANIFEST).tables

    assert (contribution.rows, contribution.files, contribution.bytes) == (30, 3, 35)
    assert contribution.parts == [
        # One file: the file, which a browser can download.
        DatasetPart(
            cycle=2022, path="contribution/cycle=2022/bucket-00-part-0000.parquet", files=1, bytes=5
        ),
        # More: the directory, its files listed in the manifest.
        DatasetPart(cycle=2024, path="contribution/cycle=2024/", files=2, bytes=30),
    ]
    assert [part.path for part in race.parts] == [
        "race/cycle=2022/part-0000.parquet",
        "race/cycle=2024/part-0000.parquet",
    ]
    assert donor.parts == [DatasetPart(cycle=None, path="donor.parquet", files=1, bytes=3)]
