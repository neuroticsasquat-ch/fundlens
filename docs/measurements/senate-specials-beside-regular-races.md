# Senate specials held beside a regular race: whose filings stand in the special

Measured for [NEU-2319](https://linear.app/neuroticsasquatch/issue/NEU-2319) (milestone M4
Backfill and independent expenditures). NEU-2060's backfill found 2018's Minnesota and
Mississippi specials with no candidate and $0, their candidates in the regular race beside them:
`cn` doesn't say which race a filing is for, both races file for the cycle's year, and
`02_candidate.sql` sent every filing for a seat to its regular race. This document lists, from
FEC's election results, the filings of each of `specials.csv`'s seven specials held beside a
regular race, and fixes the file NEU-2319 ships: `src/fundlens/fec/seats/special_candidates.csv`.

| What | Value |
| --- | --- |
| Run | 2026-11-15, 01:06–01:20 UTC, in the local `app` container (`uv run --no-project --with openpyxl`) |
| Code | `main` at `0bfd09198c11cb2f347a86e35604ec5d1451423c` |
| `federalelections2018.xlsx` | `https://www.fec.gov/documents/2706/federalelections2018.xlsx`, sheet `2018 US Senate Results by State`, SHA-256 `f2c42311862b4927…` |
| `federalelections2020.xlsx` | `https://www.fec.gov/documents/4228/federalelections2020.xlsx`, sheet `12. US Senate Results by State`, SHA-256 `5073b6d2c76c86c9…` |
| `federalelections2022.xlsx` | `https://www.fec.gov/documents/5676/federalelections2022.xlsx`, sheet `7. US Senate Results by State`, SHA-256 `cdb258ea23803e50…` |
| `2024congressgecands.xlsx` | `https://www.fec.gov/documents/5548/2024congressgecands.xlsx`, sheets `CA SEN Spec Gen Ballot 2024`, `CA General Ballot 2024` and `NE General Ballot 2024`, SHA-256 `b142427552dd9f5b…` |
| `cn` | `https://www.fec.gov/files/bulk-downloads/<cycle>/cn<yy>.zip` for 2018, 2020, 2022, 2024, downloaded 2026-11-15T01:08Z (SHA-256 `fba6302a…`, `f0229bb4…`, `5e939648…`, `abe6afcc…`) |
| `weball` | `…/<cycle>/weball<yy>.zip`, FEC's candidate summary, for each filing's total receipts (`TTL_RECEIPTS`), downloaded 2026-11-15T01:08Z (`1a0dbf7a…`, `82f381f3…`, `b9e09a03…`, `0550d343…`) |

## Headline

- **FEC's results list each special's candidates apart from the regular race's, with their FEC
  id.** 2018–2022's `Federal Elections` sheets mark a special's rows `S-UNEXPIRED TERM` and the
  regular race's `S-FULL TERM`. 2024 has no `Federal Elections` yet, only the general-election
  ballots, where the specials are their own sheet (California) or an `UNEXPIRED TERM` block
  (Nebraska).
- **54 filings stand in a special, $275,395,869 of receipts**: 2018 MN 11 ($15,929,518), 2018 MS
  4 ($13,708,430), 2020 GA 21 ($227,139,325), 2022 OK 16 ($12,459,136), 2024 NE 2 ($6,159,461).
  Before NEU-2319 all of it counted in the regular race.
- **Every candidate of both California specials ran in the regular race too**, under one id and
  one committee: 2022's 10 (Padilla, Meuser, Bradley, Elist, Ursich, O'Dowd, Hall, Bradford,
  Parker, Ratliff; $21,315,974) and 2024's 2 (Schiff and Garvey, $68,505,330). Their money can't
  be split, so they stand in the regular race, the full term, and are listed with `race` `regular`.
  Those two specials have no candidate, by design.
- **2 results rows are turned down**, both 2018 MN write-ins: Stephen A. Emery's id `S8MN00339`
  is in no `cn` (his filing is `S8MN00669`, in the regular race), and the row for Mike Kuitu gives
  `S8MN00438`, Al Franken's, which `cn` files for 2020. As in NEU-2293, a row is used only after
  name checks.

## Method

For each of the seven specials:

1. Read the state's Senate rows from the results: the special's (`S-UNEXPIRED TERM`, or 2024's
   special sheet and `UNEXPIRED TERM` block) and the regular race's.
2. Keep a special's row only when its id is a `cn` filing that stands this cycle
   (`transform.seats.stands`: the cycle's year or the odd year before it) for the Senate in that
   state, and the results' surname, accents folded, is in the `cn` name.
3. A kept id the results list in the regular race too is `race` `regular`; any other is
   `special`. `note` is the results' name and row.

The script is under [Reproducing](#reproducing).

## Filings in neither race's results

A standing Senate filing for one of these seats that the results list in neither race (one that
filed but did not reach the ballot) stays in the regular race, as before. There are 118, holding
$41,531,428, nearly all of it 2024's, whose ballots list only the general election's candidates:

| Special | Filings | Receipts | Largest |
| --- | ---: | ---: | --- |
| 2018 MN | 4 | $0 | |
| 2018 MS | 1 | $75,313 | Jason Shelton `S8MS00303`, $75,313 |
| 2020 GA | 10 | $177,817 | Edward Terry `S0GA00419`, $140,274 |
| 2022 CA | 27 | $478,699 | Chris Theodore `S2CA01193`, $233,250 |
| 2022 OK | 1 | $0 | |
| 2024 CA | 68 | $40,724,860 | Katie Porter `S4CA00522`, $32,527,821; Barbara Lee `S4CA00589`, $5,809,488 |
| 2024 NE | 7 | $74,739 | John Weaver `S4NE00215`, $56,974 |

Porter and Lee ran in both of 2024's California primaries, so would stand in the regular race
anyway. Weaver lost the special's Republican primary to Pete Ricketts, so belongs in the special;
he and the rest of 2024's special-primary candidates can be added when FEC publishes
`Federal Elections 2024`.

## Reproducing

From the repo root, with the files above under `data/neu2319/` (`cn<yy>/cn.txt` and
`weball<yy>/weball<yy>.txt` unzipped), in the `app` container:

```
uv run --no-project --with openpyxl python data/neu2319/measure.py data/neu2319 > out.csv
```

Each `out.csv` row with `decision` `special` or `both: …` is a `special_candidates.csv` row
(`race` `special` or `regular`).

```python
"""NEU-2319: the filings of each Senate special held beside a regular race, from FEC's results.

Run in the app container from the repo root:
    uv run --no-project --with openpyxl python data/neu2319/measure.py data/neu2319
"""

import csv
import sys
import unicodedata
from pathlib import Path

import openpyxl

DIR = Path(sys.argv[1])

# (cycle, state) -> the results workbook and sheets the special and the regular race are in.
RESULTS = {
    2018: ("federalelections2018.xlsx", "2018 US Senate Results by State"),
    2020: ("federalelections2020.xlsx", "12. US Senate Results by State"),
    2022: ("federalelections2022.xlsx", "7. US Senate Results by State"),
}
BALLOTS_2024 = "2024congressgecands.xlsx"
SPECIALS = [(2018, "MN"), (2018, "MS"), (2020, "GA"), (2022, "CA"), (2022, "OK"), (2024, "CA"), (2024, "NE")]


def text(cell: object) -> str:
    return "" if cell is None else str(cell).replace("\xa0", " ").strip()


def fold(name: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c)
    ).upper()


def results_rows(cycle: int, state: str):
    """(term, id, "Surname, Given", source) for each candidate row of `state`'s Senate races."""
    if cycle in RESULTS:
        name, sheet = RESULTS[cycle]
        ws = openpyxl.load_workbook(DIR / name, read_only=True)[sheet]
        for n, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = [text(c) for c in row]
            if cells[1] != state or not cells[4].startswith("S"):
                continue
            district = cells[3].upper()
            term = "special" if "UNEXPIRED" in district else "regular" if "FULL" in district else None
            if term:
                yield term, cells[4], cells[8], f"{name} row {n}"
        return
    wb = openpyxl.load_workbook(DIR / BALLOTS_2024, read_only=True)
    sheets = [f"{state} General Ballot 2024"]
    if state == "CA":
        sheets.insert(0, "CA SEN Spec Gen Ballot 2024")
    for sheet in sheets:
        term = "special" if "Spec" in sheet else "regular"
        for n, row in enumerate(wb[sheet].iter_rows(values_only=True), start=1):
            cells = [text(c) for c in row]
            if cells[0] == state and cells[3].startswith("S"):
                yield term, cells[3], cells[7], f"{BALLOTS_2024} sheet '{sheet}' row {n}"
            elif cells[2].upper() == "UNEXPIRED TERM":
                term = "special"
            elif cells[2].upper() == "FULL TERM":
                term = "regular"


def read_cn(cycle: int) -> dict[str, list[str]]:
    with open(DIR / f"cn{cycle % 100:02d}" / "cn.txt", encoding="latin-1") as f:
        return {r[0]: r for r in csv.reader(f, delimiter="|", quoting=csv.QUOTE_NONE) if r}


def read_receipts(cycle: int) -> dict[str, float]:
    yy = f"{cycle % 100:02d}"
    with open(DIR / f"weball{yy}" / f"weball{yy}.txt", encoding="latin-1") as f:
        return {r[0]: float(r[5] or 0) for r in csv.reader(f, delimiter="|", quoting=csv.QUOTE_NONE) if r}


out = csv.writer(sys.stdout)
out.writerow(["cycle", "state", "candidate_id", "results_name", "cn_name", "decision", "receipts", "source"])
for cycle, state in SPECIALS:
    cn, receipts = read_cn(cycle), read_receipts(cycle)
    rows = list(results_rows(cycle, state))
    regular = {cid for term, cid, _, _ in rows if term == "regular"}
    seen: set[str] = set()
    for term, cid, results_name, source in rows:
        surname = results_name.split(",")[0]
        if term != "special" or cid in seen:
            continue
        seen.add(cid)
        filing = cn.get(cid)
        if filing is None:
            decision = "turned down: not in cn"
        elif not (filing[5] == "S" and filing[4] == state and filing[3] in {str(cycle - 1), str(cycle)}):
            decision = f"turned down: cn files {filing[5]} {filing[4]} {filing[3]}"
        elif fold(surname) not in fold(filing[1]):
            decision = f"turned down: surname {surname} not in cn name"
        elif cid in regular:
            decision = "both: stands in the regular race"
        else:
            decision = "special"
        out.writerow([cycle, state, cid, results_name, filing[1] if filing else "", decision,
                      f"{receipts.get(cid, 0):.2f}", source])
```
