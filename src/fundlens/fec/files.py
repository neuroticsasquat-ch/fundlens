"""The FEC bulk files fundlens reads: the single catalogue of them (spec §4).

A bulk file comes in one of two formats (`Format`):

- `zip`: a zip holding one pipe-delimited text file with no header row. Its column names come
  from FEC's data dictionaries (`data_dictionaries/<name>_header_file.csv`), vendored under
  `headers/` and refreshed by `task fec:headers` (`fundlens.fec.refresh_headers`). FEC publishes
  no header file for `weball` or `webk` (a 404 on 2026-11-05): theirs are vendored by hand from
  FEC's file descriptions, and the refresh leaves them alone (`header_from_fec`). A file whose
  lines end with a `|` after their last column (`oppexp`) says so (`trailing_delimiter`).
- `csv`: a comma-separated file, not zipped, whose first line is a header row. That row must be
  the entry's `columns` exactly, in order; extract and transform both check it
  (`read_csv_header`). An entry's name is its DuckDB view's and its bronze folder's, and need
  not be FEC's file name (`ie_24_48`).

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

FecFile = Literal[
    "cm",
    "cn",
    "ccl",
    "indiv",
    "pas2",
    "oth",
    "weball",
    "webk",
    "committee_summary",
    "oppexp",
    "ie_24_48",
    "ElectioneeringComm",
    "CommunicationCosts",
]

# How a bulk file is published: a zipped pipe-delimited text file, or a CSV with a header row.
Format = Literal["zip", "csv"]

# The placeholders a `url_pattern` or `member` may hold: the cycle in four digits, and in two.
_CYCLE_FIELDS = frozenset({"yyyy", "yy"})
# How far `read_csv_header` reads looking for the end of the header row.
CSV_HEADER_BYTES = 64 * 1024

# The DuckDB type each column is cast to after it is read as VARCHAR (spec §5.3), from FEC's
# data dictionaries. Dates stay VARCHAR: the itemized receipt files write them MMDDYYYY, `oppexp`
# and the summary zips MM/DD/YYYY, `committee_summary` and `CommunicationCosts` YYYYMMDD,
# `ie_24_48` and `ElectioneeringComm` DD-MON-YY (`20-APR-24`), and `sql/silver/` parses them.
VARCHAR = "VARCHAR"
YEAR = "SMALLINT"  # NUMBER(4)
AMOUNT = "DECIMAL(14,2)"  # NUMBER(14,2)
PERCENT = "DECIMAL(7,4)"  # NUMBER(7,4)
# SUB_ID is NUMBER(19): unsigned, because a 19-digit id can pass BIGINT's 9.2e18.
SUB_ID = "UBIGINT"
FILE_NUM = "BIGINT"  # NUMBER(22), in practice seven digits
LINKAGE_ID = "BIGINT"  # NUMBER(12)
# A small count: `ElectioneeringComm`'s NUMBER_OF_CANDIDATES, 22 at most in any cycle.
COUNT = "SMALLINT"


def _varchar(*names: str) -> dict[str, str]:
    return dict.fromkeys(names, VARCHAR)


def _amount(*names: str) -> dict[str, str]:
    return dict.fromkeys(names, AMOUNT)


def _format_cycle(pattern: str, cycle: int) -> str:
    return pattern.format(yyyy=f"{cycle:04d}", yy=f"{cycle % 100:02d}")


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
    # file": the `indiv` zip also holds the same rows again, split by date under `by_date/`. It may
    # hold `{yyyy}` and `{yy}`, as `url_pattern` does: `weball24.zip` holds `weball24.txt`.
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
    # Whether a zip's vendored header is FEC's own header file, which `task fec:headers`
    # refreshes; False where FEC publishes none and it was written from FEC's file description.
    header_from_fec: bool = True
    # Whether each line ends with the delimiter after its last column, so that it splits into one
    # field more than `columns`, the last one empty (`oppexp`). The reader takes such a line as it
    # is (`transform.runner.register_bulk`); the fixture builder writes the delimiter.
    trailing_delimiter: bool = False

    def __post_init__(self) -> None:
        if self.format == "zip" and self.member is None:
            raise ValueError(f"{self.name}: a zip needs the member it is read from")
        if self.format == "csv":
            if self.trailing_delimiter:
                raise ValueError(f"{self.name}: a CSV has no trailing delimiter")
            if self.member is not None or self.split_dir is not None:
                raise ValueError(f"{self.name}: a CSV has no member or split folder")
            if not self.url_pattern:
                raise ValueError(f"{self.name}: a CSV needs a URL pattern")
            if not self.header_from_fec:
                raise ValueError(f"{self.name}: a CSV's header row is in the file itself")
        for what, pattern in (("URL pattern", self.url_pattern), ("member", self.member)):
            if pattern is None:
                continue
            for _, field, spec, conversion in string.Formatter().parse(pattern):
                if field is not None and (field not in _CYCLE_FIELDS or spec or conversion):
                    raise ValueError(
                        f"{self.name}: {what} {pattern!r} may hold only {{yyyy}} and {{yy}}"
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
        return f"{base_url.rstrip('/')}/{_format_cycle(pattern, cycle)}"

    def member_for(self, cycle: int) -> str:
        """The text file inside `cycle`'s zip, e.g. `weball24.txt`; `ValueError` for a CSV."""
        if self.member is None:
            raise ValueError(f"{self.name} is not a zip")
        return _format_cycle(self.member, cycle)

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
        # The summary files (every-FEC-dollar spec §3, §4). The two zips' headers are FEC's file
        # descriptions (all candidates; PAC and party summary), read 2026-11-05, and each zip's
        # one member is named for its cycle. Their dates are MM/DD/YYYY, `committee_summary`'s
        # YYYYMMDD; both stay VARCHAR, as the itemized files' do.
        BulkFile(
            "weball",
            1980,
            "weball{yy}.txt",
            _varchar("CAND_ID", "CAND_NAME", "CAND_ICI", "PTY_CD", "CAND_PTY_AFFILIATION")
            | _amount(
                "TTL_RECEIPTS",
                "TRANS_FROM_AUTH",
                "TTL_DISB",
                "TRANS_TO_AUTH",
                "COH_BOP",
                "COH_COP",
                "CAND_CONTRIB",
                "CAND_LOANS",
                "OTHER_LOANS",
                "CAND_LOAN_REPAY",
                "OTHER_LOAN_REPAY",
                "DEBTS_OWED_BY",
                "TTL_INDIV_CONTRIB",
            )
            | _varchar(
                "CAND_OFFICE_ST",
                "CAND_OFFICE_DISTRICT",
                "SPEC_ELECTION",
                "PRIM_ELECTION",
                "RUN_ELECTION",
                "GEN_ELECTION",
            )
            # FEC's spelling. The election results are filled in 1996–2006 only.
            | {"GEN_ELECTION_PRECENT": PERCENT}
            | _amount("OTHER_POL_CMTE_CONTRIB", "POL_PTY_CONTRIB")
            | {"CVG_END_DT": VARCHAR}
            | _amount("INDIV_REFUNDS", "CMTE_REFUNDS"),
            header_from_fec=False,
        ),
        BulkFile(
            "webk",
            1996,
            "webk{yy}.txt",
            _varchar("CMTE_ID", "CMTE_NM", "CMTE_TP", "CMTE_DSGN", "CMTE_FILING_FREQ")
            | _amount(
                "TTL_RECEIPTS",
                "TRANS_FROM_AFF",
                "INDV_CONTRIB",
                "OTHER_POL_CMTE_CONTRIB",
                "CAND_CONTRIB",
                "CAND_LOANS",
                "TTL_LOANS_RECEIVED",
                "TTL_DISB",
                "TRANF_TO_AFF",
                "INDV_REFUNDS",
                "OTHER_POL_CMTE_REFUNDS",
                "CAND_LOAN_REPAY",
                "LOAN_REPAY",
                "COH_BOP",
                "COH_COP",
                "DEBTS_OWED_BY",
                "NONFED_TRANS_RECEIVED",
                "CONTRIB_TO_OTHER_CMTE",
                "IND_EXP",
                "PTY_COORD_EXP",
                "NONFED_SHARE_EXP",
            )
            | {"CVG_END_DT": VARCHAR},
            header_from_fec=False,
        ),
        # The header row is the same in every cycle's file, 2008 to 2026, read 2026-11-18. FEC's
        # file description spells some names differently (`OTH_FED_OPE_EXP`); the row's are
        # these. `Link_Image` is the committee's page on fec.gov.
        BulkFile(
            "committee_summary",
            2008,
            None,
            _varchar(
                "Link_Image",
                "CMTE_ID",
                "CMTE_NM",
                "CMTE_TP",
                "CMTE_DSGN",
                "CMTE_FILING_FREQ",
                "CMTE_ST1",
                "CMTE_ST2",
                "CMTE_CITY",
                "CMTE_ST",
                "CMTE_ZIP",
                "TRES_NM",
                "CAND_ID",
            )
            | {"FEC_ELECTION_YR": YEAR}
            | _amount(
                "INDV_CONTB",
                "PTY_CMTE_CONTB",
                "OTH_CMTE_CONTB",
                "TTL_CONTB",
                "TRANF_FROM_OTHER_AUTH_CMTE",
                "OFFSETS_TO_OP_EXP",
                "OTHER_RECEIPTS",
                "TTL_RECEIPTS",
                "TRANF_TO_OTHER_AUTH_CMTE",
                "OTH_LOAN_REPYMTS",
                "INDV_REF",
                "POL_PTY_CMTE_REF",
                "TTL_CONTB_REF",
                "OTHER_DISB",
                "TTL_DISB",
                "NET_CONTB",
                "NET_OP_EXP",
                "COH_BOP",
            )
            | {"CVG_START_DT": VARCHAR, "COH_COP": AMOUNT, "CVG_END_DT": VARCHAR}
            | _amount(
                "DEBTS_OWED_BY_CMTE",
                "DEBTS_OWED_TO_CMTE",
                "INDV_ITEM_CONTB",
                "INDV_UNITEM_CONTB",
                "OTH_LOANS",
                "TRANF_FROM_NONFED_ACCT",
                "TRANF_FROM_NONFED_LEVIN",
                "TTL_NONFED_TRANF",
                "LOAN_REPYMTS_RECEIVED",
                "OFFSETS_TO_FNDRSG",
                "OFFSETS_TO_LEGAL_ACCTG",
                "FED_CAND_CONTB_REF",
                "TTL_FED_RECEIPTS",
                "SHARED_FED_OP_EXP",
                "SHARED_NONFED_OP_EXP",
                "OTHER_FED_OP_EXP",
                "TTL_OP_EXP",
                "FED_CAND_CMTE_CONTB",
                "INDT_EXP",
                "COORD_EXP_BY_PTY_CMTE",
                "LOANS_MADE",
                "SHARED_FED_ACTVY_FED_SHR",
                "SHARED_FED_ACTVY_NONFED",
                "NON_ALLOC_FED_ELECT_ACTVY",
                "TTL_FED_ELECT_ACTVY",
                "TTL_FED_DISB",
                "CAND_CNTB",
                "CAND_LOAN",
                "TTL_LOANS",
                "OP_EXP",
                "CAND_LOAN_REPYMNT",
                "TTL_LOAN_REPYMTS",
                "OTH_CMTE_REF",
                "TTL_OFFSETS_TO_OP_EXP",
                "EXEMPT_LEGAL_ACCTG_DISB",
                "FNDRSG_DISB",
                "ITEM_REF_REB_RET",
                "SUBTTL_REF_REB_RET",
                "UNITEM_REF_REB_RET",
                "ITEM_OTHER_REF_REB_RET",
                "UNITEM_OTHER_REF_REB_RET",
                "SUBTTL_OTHER_REF_REB_RET",
                "ITEM_OTHER_INCOME",
                "UNITEM_OTHER_INCOME",
                "EXP_PRIOR_YRS_SUBJECT_LIM",
                "EXP_SUBJECT_LIMITS",
                "FED_FUNDS",
                "ITEM_CONVN_EXP_DISB",
                "ITEM_OTHER_DISB",
                "SUBTTL_CONVN_EXP_DISB",
                "TTL_EXP_SUBJECT_LIMITS",
                "UNITEM_CONVN_EXP_DISB",
                "UNITEM_OTHER_DISB",
                "TTL_COMMUNICATION_COST",
                "COH_BOY",
                "COH_COY",
            )
            | {"ORG_TP": VARCHAR},
            format="csv",
            url_pattern="{yyyy}/committee_summary_{yyyy}.csv",
        ),
        # Operating expenditures (every-FEC-dollar spec §3, §5). Not the itemized receipt files'
        # layout, so none of `_ITEMIZED_HEAD` or `_ITEMIZED_TAIL` is reused: `ENTITY_TP` comes
        # after the memo columns, and `SUB_ID` before `FILE_NUM` and `TRAN_ID`, not last; there
        # is no `TRANSACTION_TP`, `EMPLOYER`, `OCCUPATION` or `OTHER_ID`, and `RPT_YR`, the
        # form, schedule and line, `PURPOSE`, `CATEGORY` and `BACK_REF_TRAN_ID` are there
        # instead. Dates are MM/DD/YYYY, not MMDDYYYY. Every line of every cycle, 2004 to 2026,
        # ends with a `|` after `BACK_REF_TRAN_ID`. The zip's one member is `oppexp.txt` in
        # every cycle.
        BulkFile(
            "oppexp",
            2004,
            "oppexp.txt",
            _varchar("CMTE_ID", "AMNDT_IND")
            | {"RPT_YR": YEAR}
            | _varchar(
                "RPT_TP",
                "IMAGE_NUM",
                "LINE_NUM",
                "FORM_TP_CD",
                "SCHED_TP_CD",
                "NAME",
                "CITY",
                "STATE",
                "ZIP_CODE",
                "TRANSACTION_DT",
            )
            | {"TRANSACTION_AMT": AMOUNT}
            | _varchar(
                "TRANSACTION_PGI",
                "PURPOSE",
                "CATEGORY",
                "CATEGORY_DESC",
                "MEMO_CD",
                "MEMO_TEXT",
                "ENTITY_TP",
            )
            | {"SUB_ID": SUB_ID, "FILE_NUM": FILE_NUM}
            | _varchar("TRAN_ID", "BACK_REF_TRAN_ID"),
            trailing_delimiter=True,
        ),
        # FEC's `independent_expenditure_<yyyy>.csv`: the 24/48-hour file (every-FEC-dollar spec
        # §3, §6). It is not catalogued under FEC's name because a file's view is named for its
        # entry, and `independent_expenditure` is silver's table: DuckDB refuses a table named
        # as a view. Its header row is lower case. Its dates are DD-MON-YY (`20-APR-24`), as
        # `ElectioneeringComm`'s are, and `CommunicationCosts`' YYYYMMDD; `exp_date` or
        # `dissem_dt` may be blank, never both.
        BulkFile(
            "ie_24_48",
            2010,
            None,
            _varchar(
                "cand_id",
                "cand_name",
                "spe_id",
                "spe_nam",
                "ele_type",
                "can_office_state",
                "can_office_dis",
                "can_office",
                "cand_pty_aff",
            )
            | {"exp_amo": AMOUNT, "exp_date": VARCHAR, "agg_amo": AMOUNT}
            | _varchar("sup_opp", "pur", "pay")
            | {"file_num": FILE_NUM}
            | _varchar("amndt_ind", "tran_id", "image_num", "receipt_dat")
            | {"fec_election_yr": YEAR, "prev_file_num": FILE_NUM, "dissem_dt": VARCHAR},
            format="csv",
            url_pattern="{yyyy}/independent_expenditure_{yyyy}.csv",
        ),
        # Electioneering communications (every-FEC-dollar spec §3, §6.4). A disbursement for
        # several candidates is one row per candidate, each with its share. Dates are DD-MON-YY.
        BulkFile(
            "ElectioneeringComm",
            2010,
            None,
            _varchar(
                "CANDIDATE_ID",
                "CANDIDATE_NAME",
                "CANDIDATE_OFFICE",
                "CANDIDATE_STATE",
                "CANDIDATE_DISTRICT",
                "COMMITTEE_ID",
                "COMMITTEE_NAME",
                "SB_IMAGE_NUM",
                "PAYEE_NAME",
                "PAYEE_STREET",
                "PAYEE_CITY",
                "PAYEE_STATE",
                "DISBURSEMENT_DESCRIPTION",
                "DISBURSEMENT_DATE",
                "COMMUNICATION_DATE",
                "PUBLIC_DISBURSEMENT_DATE",
            )
            | {
                "REPORTED_DISBURSEMENT_AMOUNT": AMOUNT,
                "NUMBER_OF_CANDIDATES": COUNT,
                "CALCULATED_CANDIDATE_SHARE": AMOUNT,
            },
            format="csv",
            url_pattern="{yyyy}/ElectioneeringComm_{yyyy}.csv",
        ),
        # Communication costs (every-FEC-dollar spec §3, §6.2): `pas2`'s 24F and 24N rows under
        # the same SUB_ID, with the communication's type and class. It carries the itemized
        # files' transaction key, so its view reads a repeated row once
        # (`transform.runner._drop_fec_repeats`). A row of no electronic filing has a negative or
        # blank FILE_NUM and no TRAN_ID. Dates are YYYYMMDD.
        BulkFile(
            "CommunicationCosts",
            2010,
            None,
            _varchar(
                "CMTE_ID",
                "CMTE_NM",
                "CAND_ID",
                "CAND_NAME",
                "CAND_OFFICE",
                "CAND_STATE",
                "CAND_OFFICE_DISTRICT",
                "CAND_PTY_AFFILIATION",
                "TRANSACTION_DT",
            )
            | {"TRANSACTION_AMT": AMOUNT}
            | _varchar(
                "TRANSACTION_TP",
                "COMMUNICATION_TP",
                "COMMUNICATION_CLASS",
                "SUPPORT_OPPOSE_IND",
                "IMAGE_NUM",
                "LINE_NUM",
                "FORM_TP_CD",
                "SCHED_TP_CD",
                "TRAN_ID",
            )
            | {"SUB_ID": SUB_ID, "FILE_NUM": FILE_NUM, "RPT_YR": YEAR}
            | _varchar("CAND_STATE_DESCRIPTION", "CAND_PTY_AFFILIATION_DESCRIPTION", "PURPOSE"),
            format="csv",
            url_pattern="{yyyy}/CommunicationCosts_{yyyy}.csv",
        ),
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
