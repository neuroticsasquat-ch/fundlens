"""The FEC bulk files fundlens reads: the single catalogue of them (spec §4).

A bulk file comes in one of two formats (`Format`):

- `zip`: a zip holding one pipe-delimited text file with no header row. Its column names come
  from FEC's data dictionaries (`data_dictionaries/<name>_header_file.csv`), vendored under
  `headers/` and refreshed by `task fec:headers` (`fundlens.fec.refresh_headers`).
- `csv`: a comma-separated file, not zipped, whose first line is a header row. That row must be
  the entry's `columns` exactly, in order; extract and transform both check it
  (`read_csv_header`).

Its URL below `FEC_BULK_URL` is the entry's `url_pattern`, in one of three shapes: per cycle in
the cycle's folder (`2024/committee_summary_2024.csv`), per cycle under `data.fec.gov/`
(`data.fec.gov/leadership2024.csv`), or an undated file, one for every cycle
(`data.fec.gov/lobbyist.csv`). A zip with no pattern is at `<cycle>/<name><yy>.zip`. A file this
catalogue does not list is neither downloaded nor read.
"""

import csv
import string
from dataclasses import dataclass
from datetime import date
from importlib.resources import files as package_files
from pathlib import Path
from typing import Literal

FecFile = Literal["cm", "cn", "ccl", "indiv", "pas2", "oth"]

# How a bulk file is published: a zipped pipe-delimited text file, or a CSV with a header row.
Format = Literal["zip", "csv"]

# The placeholders a `url_pattern` may hold: the cycle in four digits, and in two.
_URL_FIELDS = frozenset({"yyyy", "yy"})
# How far `read_csv_header` reads looking for the end of the header row.
CSV_HEADER_BYTES = 64 * 1024

# The DuckDB type each column is cast to after it is read as VARCHAR (spec §5.3), from FEC's
# data dictionaries. Dates stay VARCHAR: FEC writes them MMDDYYYY, and `sql/silver/` parses them.
VARCHAR = "VARCHAR"
YEAR = "SMALLINT"  # NUMBER(4)
AMOUNT = "DECIMAL(14,2)"  # NUMBER(14,2)
# SUB_ID is NUMBER(19): unsigned, because a 19-digit id can pass BIGINT's 9.2e18.
SUB_ID = "UBIGINT"
FILE_NUM = "BIGINT"  # NUMBER(22), in practice seven digits
LINKAGE_ID = "BIGINT"  # NUMBER(12)


def _varchar(*names: str) -> dict[str, str]:
    return dict.fromkeys(names, VARCHAR)


# `indiv` and `oth` share one layout; `pas2` adds CAND_ID after OTHER_ID.
_ITEMIZED_HEAD = _varchar(
    "CMTE_ID",
    "AMNDT_IND",
    "RPT_TP",
    "TRANSACTION_PGI",
    "IMAGE_NUM",
    "TRANSACTION_TP",
    "ENTITY_TP",
    "NAME",
    "CITY",
    "STATE",
    "ZIP_CODE",
    "EMPLOYER",
    "OCCUPATION",
    "TRANSACTION_DT",
) | {"TRANSACTION_AMT": AMOUNT, "OTHER_ID": VARCHAR}
_ITEMIZED_TAIL = _varchar("TRAN_ID") | {
    "FILE_NUM": FILE_NUM,
    "MEMO_CD": VARCHAR,
    "MEMO_TEXT": VARCHAR,
    "SUB_ID": SUB_ID,
}


@dataclass(frozen=True)
class BulkFile:
    """One catalogued bulk file. An entry that cannot work raises `ValueError` when it is made,
    so a bad entry fails at import and not at its first extract.

    It holds a dict, so it does not hash: anything that caches by entry caches by `name`.
    """

    name: FecFile
    # The first cycle FEC publishes this file for.
    first_cycle: int
    # The text file inside a zip; None for a CSV. A zip is opened by this name, never as "its one
    # file": the `indiv` zip also holds the same rows again, split by date under `by_date/`.
    member: str | None
    # Column name → DuckDB type, in file order. A zip's vendored header, and a CSV's header row,
    # must name the same columns in the same order.
    columns: dict[str, str]
    # The folder inside the zip that holds `member`'s rows again, split into several files: read
    # in its place only when the two disagree in size (`transform.runner.copy_bulk`, NEU-2321).
    split_dir: str | None = None
    format: Format = "zip"
    # The file's URL below the base URL: a `str.format` template whose only placeholders are
    # `{yyyy}` and `{yy}`, with the file's name written out. None, for a zip only, means
    # `{yyyy}/<name>{yy}.zip`.
    url_pattern: str | None = None

    def __post_init__(self) -> None:
        if self.format == "zip" and self.member is None:
            raise ValueError(f"{self.name}: a zip needs the member it is read from")
        if self.format == "csv":
            if self.member is not None or self.split_dir is not None:
                raise ValueError(f"{self.name}: a CSV has no member or split folder")
            if not self.url_pattern:
                raise ValueError(f"{self.name}: a CSV needs a URL pattern")
        if self.url_pattern is not None:
            for _, field, spec, conversion in string.Formatter().parse(self.url_pattern):
                if field is not None and (field not in _URL_FIELDS or spec or conversion):
                    raise ValueError(
                        f"{self.name}: URL pattern {self.url_pattern!r} may hold only"
                        " {yyyy} and {yy}"
                    )

    @property
    def header_file(self) -> str | None:
        """The data dictionary's header file, vendored under `headers/` by the same name; None
        for a CSV, whose header row is in the file itself."""
        return f"{self.name}_header_file.csv" if self.format == "zip" else None

    def url(self, base_url: str, cycle: int) -> str:
        """The file for `cycle`: `url_pattern` below `base_url`, e.g. `.../2024/indiv24.zip`."""
        pattern = (
            f"{{yyyy}}/{self.name}{{yy}}.zip" if self.url_pattern is None else self.url_pattern
        )
        path = pattern.format(yyyy=f"{cycle:04d}", yy=f"{cycle % 100:02d}")
        return f"{base_url.rstrip('/')}/{path}"

    def header(self) -> list[str]:
        """The column names, in file order: a zip's from its vendored header file; a CSV's are
        its `columns`, which its header row must be."""
        if self.header_file is None:
            return list(self.columns)
        text = package_files("fundlens.fec").joinpath("headers", self.header_file).read_text()
        return text.strip().split(",")


CATALOGUE: dict[FecFile, BulkFile] = {
    file.name: file
    for file in (
        BulkFile(
            "cm",
            1980,
            "cm.txt",
            _varchar(
                "CMTE_ID",
                "CMTE_NM",
                "TRES_NM",
                "CMTE_ST1",
                "CMTE_ST2",
                "CMTE_CITY",
                "CMTE_ST",
                "CMTE_ZIP",
                "CMTE_DSGN",
                "CMTE_TP",
                "CMTE_PTY_AFFILIATION",
                "CMTE_FILING_FREQ",
                "ORG_TP",
                "CONNECTED_ORG_NM",
                "CAND_ID",
            ),
        ),
        BulkFile(
            "cn",
            1980,
            "cn.txt",
            _varchar("CAND_ID", "CAND_NAME", "CAND_PTY_AFFILIATION")
            | {"CAND_ELECTION_YR": YEAR}
            | _varchar(
                "CAND_OFFICE_ST",
                "CAND_OFFICE",
                "CAND_OFFICE_DISTRICT",
                "CAND_ICI",
                "CAND_STATUS",
                "CAND_PCC",
                "CAND_ST1",
                "CAND_ST2",
                "CAND_CITY",
                "CAND_ST",
                "CAND_ZIP",
            ),
        ),
        # Earlier cycles link candidates and committees through `cn.CAND_PCC` and `cm.CAND_ID`.
        BulkFile(
            "ccl",
            2000,
            "ccl.txt",
            {
                "CAND_ID": VARCHAR,
                "CAND_ELECTION_YR": YEAR,
                "FEC_ELECTION_YR": YEAR,
                "CMTE_ID": VARCHAR,
                "CMTE_TP": VARCHAR,
                "CMTE_DSGN": VARCHAR,
                "LINKAGE_ID": LINKAGE_ID,
            },
        ),
        # FEC's 2022 zip, as published on 2026-11-08, holds an `itcont.txt` cut off mid-row at
        # 37% of its `by_date/` files' bytes (NEU-2321). `pas2` and `oth` have no such folder.
        BulkFile(
            "indiv", 1980, "itcont.txt", _ITEMIZED_HEAD | _ITEMIZED_TAIL, split_dir="by_date/"
        ),
        BulkFile(
            "pas2", 1980, "itpas2.txt", _ITEMIZED_HEAD | {"CAND_ID": VARCHAR} | _ITEMIZED_TAIL
        ),
        BulkFile("oth", 1980, "itoth.txt", _ITEMIZED_HEAD | _ITEMIZED_TAIL),
    )
}


def read_csv_header(path: Path) -> list[str]:
    """The first line of the file at `path`, parsed as one CSV record.

    Reads at most `CSV_HEADER_BYTES` looking for the line's end, and decodes with replacement,
    so a zip, an HTML page or an empty file gives a list no entry's columns equal instead of
    raising. A BOM is kept: FEC sends none, and one would be a difference worth failing on.
    """
    with path.open("rb") as src:
        head = src.read(CSV_HEADER_BYTES)
    line, newline, _ = head.partition(b"\n")
    if not newline and len(head) == CSV_HEADER_BYTES:
        return []
    text = line.decode("utf-8", errors="replace").removesuffix("\r")
    try:
        empty: list[str] = []
        return next(csv.reader([text]), empty)
    except csv.Error:
        return []


def files_for(cycle: int) -> list[BulkFile]:
    """The catalogued files FEC publishes for `cycle`, in catalogue order."""
    return [file for file in CATALOGUE.values() if file.first_cycle <= cycle]


def current_cycle(today: date) -> int:
    """The cycle still being filed on `today`: the next even year from today's (spec §5.6)."""
    return today.year + today.year % 2
