"""FEC bulk text rewritten as UTF-8 before DuckDB reads it (`transform.runner.copy_as_utf8`,
NEU-2069)."""

import io
from pathlib import Path

import duckdb
import pytest

from fundlens.transform.runner import copy_as_utf8

# One line in each encoding FEC's bulk text mixes: the bytes a filer sent, and the name they mean.
LINES: list[tuple[bytes, str]] = [
    (b"C001|SMITH, JOHN|x\n", "SMITH, JOHN"),
    # UTF-8, as on line 2375 of the 2024 `cn` file.
    (b"C002|SOLAGES, CARRI\xc3\x89|x\n", "SOLAGES, CARRIÉ"),
    # A Windows-1252 curly apostrophe.
    (b"C003|O\x92BRIEN, PAT|x\n", "O’BRIEN, PAT"),
    # A byte Windows-1252 leaves undefined: read as latin-1.
    (b"C004|X\x81Y|x\n", "X\x81Y"),
]
MIXED = b"".join(raw for raw, _ in LINES)


def utf8(data: bytes, chunk_bytes: int = 1024) -> bytes:
    out = io.BytesIO()
    copy_as_utf8(io.BytesIO(data), out, chunk_bytes=chunk_bytes)
    return out.getvalue()


def test_each_line_is_decoded_in_its_own_encoding() -> None:
    expected = "".join(f"C00{n}|{name}|x\n" for n, (_, name) in enumerate(LINES, start=1))

    assert utf8(MIXED).decode("utf-8") == expected


def test_utf8_text_is_copied_byte_for_byte_with_or_without_a_final_newline() -> None:
    text = "C001|SOLAGES, CARRIÉ|x\nC002|ÅSE|y".encode()

    assert utf8(text) == text


@pytest.mark.parametrize("chunk_bytes", [1, 2, 3, 5, 7, 16])
def test_a_line_split_across_blocks_is_decoded_whole(chunk_bytes: int) -> None:
    assert utf8(MIXED, chunk_bytes) == utf8(MIXED)


def test_duckdb_reads_every_line_back(tmp_path: Path) -> None:
    text = tmp_path / "bulk.txt"
    text.write_bytes(utf8(MIXED))

    with duckdb.connect() as con:
        rows = con.execute(
            f"SELECT name FROM read_csv('{text}', delim = '|', quote = '', escape = '',"
            " header = false, auto_detect = false,"
            " columns = {'id': 'VARCHAR', 'name': 'VARCHAR', 'x': 'VARCHAR'}, encoding = 'utf-8')"
            " ORDER BY id"
        ).fetchall()

    assert [name for (name,) in rows] == [name for _, name in LINES]
