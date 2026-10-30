"""The FEC bulk files fundlens reads: the single catalogue of them (spec §4).

Each is a pipe-delimited zip with no header row, published per cycle at
`<FEC_BULK_URL>/<cycle>/<name><yy>.zip`. Its column names come from FEC's data dictionaries
(`data_dictionaries/<name>_header_file.csv`), vendored under `headers/` and refreshed by
`task fec:headers` (`fundlens.fec.refresh_headers`). A file this catalogue does not list is
neither downloaded nor read.
"""

from dataclasses import dataclass
from datetime import date
from importlib.resources import files as package_files
from typing import Literal

FecFile = Literal["cm", "cn", "ccl", "indiv", "pas2", "oth"]

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
    name: FecFile
    # The first cycle FEC publishes this file for.
    first_cycle: int
    # The text file inside the zip. A zip is opened by this name, never as "its one file": the
    # `indiv` zip also holds the same rows again, split by date under `by_date/`.
    member: str
    # Column name → DuckDB type, in file order; the vendored header must name the same columns.
    columns: dict[str, str]

    @property
    def header_file(self) -> str:
        """The data dictionary's header file, vendored under `headers/` by the same name."""
        return f"{self.name}_header_file.csv"

    def url(self, base_url: str, cycle: int) -> str:
        """The zip for `cycle`: `<base>/<cycle>/<name><yy>.zip`, e.g. `.../2024/indiv24.zip`."""
        return f"{base_url.rstrip('/')}/{cycle}/{self.name}{cycle % 100:02d}.zip"

    def header(self) -> list[str]:
        """The column names in the vendored header file, in file order."""
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
        BulkFile("indiv", 1980, "itcont.txt", _ITEMIZED_HEAD | _ITEMIZED_TAIL),
        BulkFile(
            "pas2", 1980, "itpas2.txt", _ITEMIZED_HEAD | {"CAND_ID": VARCHAR} | _ITEMIZED_TAIL
        ),
        BulkFile("oth", 1980, "itoth.txt", _ITEMIZED_HEAD | _ITEMIZED_TAIL),
    )
}


def files_for(cycle: int) -> list[BulkFile]:
    """The catalogued files FEC publishes for `cycle`, in catalogue order."""
    return [file for file in CATALOGUE.values() if file.first_cycle <= cycle]


def current_cycle(today: date) -> int:
    """The cycle still being filed on `today`: the next even year from today's (spec §5.6)."""
    return today.year + today.year % 2
