"""An `indiv` zip's `by_date/` files read in place of an `itcont.txt` that disagrees with them
(`transform.runner.copy_bulk`, NEU-2321)."""

import io
import logging
import zipfile

import pytest

from fundlens.fec.files import CATALOGUE
from fundlens.transform.runner import copy_bulk

INDIV = CATALOGUE["indiv"]
ROWS = b"C001|A|1\nC002|B|2\nC003|C|3\n"


def zip_of(members: dict[str, bytes]) -> zipfile.ZipFile:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return zipfile.ZipFile(buffer)


def copied(members: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zip_of(members) as archive:
        copy_bulk(archive, INDIV, out, source="indiv.zip")
    return out.getvalue()


def test_a_zip_without_split_files_is_read_from_its_member() -> None:
    assert copied({"itcont.txt": ROWS}) == ROWS


def test_split_files_that_agree_in_size_leave_the_member_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The same bytes, so the same size, in another order: read, they would reorder the rows.
    reordered = b"C003|C|3\nC001|A|1\nC002|B|2\n"

    out = copied({"itcont.txt": ROWS, "by_date/itcont_2.txt": reordered})

    assert out == ROWS
    assert not caplog.records


def test_a_member_that_disagrees_is_replaced_by_its_split_files_in_name_order(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    # Cut off mid-row, as FEC's 2022 `itcont.txt` is; the second file ends without a newline,
    # and the first is listed after the second in the zip.
    out = copied(
        {
            "itcont.txt": ROWS[:12],
            "by_date/itcont_2.txt": b"C003|C|3",
            "by_date/itcont_1.txt": b"C001|A|1\nC002|B|2\n",
        }
    )

    assert out == ROWS
    assert [record.getMessage() for record in caplog.records] == [
        f"indiv.zip: itcont.txt holds 12 bytes but by_date/ {len(ROWS) - 1}; reading by_date/"
    ]


def test_a_split_file_without_a_final_newline_does_not_join_the_next_files_first_row() -> None:
    out = copied(
        {
            "itcont.txt": b"",
            "by_date/itcont_1.txt": b"C001|A|1",
            "by_date/itcont_2.txt": b"C002|B|2\n",
        }
    )

    assert out == b"C001|A|1\nC002|B|2\n"


def test_a_file_without_a_split_dir_ignores_a_folder_of_the_same_name() -> None:
    cm = b"C001|X\n"
    out = io.BytesIO()
    with zip_of({"cm.txt": cm, "by_date/cm_2024.txt": b"C002|Y\n"}) as archive:
        copy_bulk(archive, CATALOGUE["cm"], out, source="cm.zip")

    assert out.getvalue() == cm
