# FEC's leadership PAC, lobbyist/registrant PAC and lobbyist bundling files, 2010–2026

Measured for [NEU-2173](https://linear.app/neuroticsasquatch/issue/NEU-2173) (milestone M4 Leadership
PACs and lobbyist bundling; spec
[`NEU-2173-leadership-lobbyist-measurement-and-spec-section.md`](../specs/NEU-2173-leadership-lobbyist-measurement-and-spec-section.md)).
FEC publishes three files for M4. `leadership<yyyy>.csv` names each leadership PAC and its sponsor.
`lobbyist.csv` lists committees' declarations that a lobbyist or registrant runs them, and
`lobbyist_bundle.csv` holds Form 3L reports of contributions lobbyists bundled to a committee. This
document reads all three, joins them to each cycle's live build, and checks the sponsor names against
OpenFEC's sponsor ids. Its decisions are in project spec §7. Nothing under `sql/`, `frontend/` or
`tests/` changed, and no bronze, silver, gold or marker was written. Its one product besides this
document is `src/fundlens/fec/leadership_sponsors.csv` (Q16).

| What | Value |
| --- | --- |
| Run | 2026-11-25, over SSH on `music-box-dancer`. The blocks were first run in order at 17:57:54–18:02:21 UTC (Q1–Q13), then Q14 at 18:28 and Q15 at 18:29, while the checkpoint was held, and Q16 after it. The outputs below are the final run of every block in order (`all.sh`), 18:37:13–18:38:19 UTC, with Q13 run again at 18:38:52 after a display fix (an image number printed through a float); it read the files and OpenFEC answers cached by the first run, so no figure differs from it |
| Code | `main` at `a552021` (the `pipeline` image built 2026-11-25 16:20 UTC) |
| Container | `pipeline-lvch8zyndujjzkz16ksys8im-20261125T162045` |
| DuckDB | 2.0.0; `Limits(memory_limit='32GB', max_temp_directory_size='60GB', threads=6)` |
| Live builds | 2010 `20261114T020123Z`, 2012 `20261114T180514Z`, 2014 `20261114T182542Z`, 2016 `20261114T184036Z`, 2018 `20261116T001733Z`, 2020 `20261115T033259Z`, 2022 `20261115T173437Z`, 2024 `20261125T021311Z`, 2026 `20261123T224142Z` (`gold.meta.cycles`). Each cycle's silver `committee`, `candidate` and `candidate_committee_link` are those builds'; 2024's `reported_total` too. `allcand` reads every cycle's `candidate`, 1980–2026 |
| `leadership<yyyy>.csv` | `https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership<yyyy>.csv`, each answering 302 to an S3 address. 2024: 120,104 bytes, `Last-Modified: Wed, 25 Nov 2026 10:10:59 GMT`, downloaded 17:51:32 UTC. 2010–2020 were last modified on 2 January 2025, 2022–2026 on 25 November 2026; each cycle's size and time are in Q12's output. 2008, 2009, 2011, 2023 and 2025 answer 404 |
| `lobbyist.csv` | `…/data.fec.gov/lobbyist.csv`: 2,046,415 bytes, `Last-Modified: Wed, 25 Nov 2026 10:11:03 GMT`, downloaded 17:57:58 UTC |
| `lobbyist_bundle.csv` | `…/data.fec.gov/lobbyist_bundle.csv`: 347,542 bytes, `Last-Modified: Wed, 25 Nov 2026 10:11:06 GMT`, downloaded 17:58:00 UTC |
| OpenFEC | `GET https://api.open.fec.gov/v1/committees/?designation=D&cycle=<yyyy>&per_page=100`, every page, for each cycle 2010–2026, then `/v1/committees/?committee_id=…` (50 ids a request) for each of the file's committees that list lacked: 402 committees in all (Q12's output). Read 17:58–18:02 UTC with an api.data.gov key sent in the `X-Api-Key` header. The key is in no script, output or file. `sponsor_candidate_ids` and `sponsor_candidate_list` are on every result |

None of the files is catalogued or in bronze. They lived in the work directory for the run only.
The work directory `/data/fundlens/scratch/measure-leadership-lobbyist-2024` and the scripts'
directory `~/measure-leadership-lobbyist-2024` were deleted at 18:42:49 UTC.

## Headline

- **`leadership<yyyy>.csv` is one row per leadership PAC, and it names the sponsor in text only.**
  2024: 833 rows, 833 committees, every one a committee `cm` designates `D`
  (Q1a, Q2). No bulk file gives the sponsor's candidate id: `ccl` links 18 of 2024's 839 `D`
  committees to any candidate and `cm`'s `CAND_ID` is filled on 16, and of the file's 545 named
  sponsors 538 have neither (Q4i–l). Odd years and 2008 are 404s: the file is even years, 2010–2026
  (Q12).
- **The flag: designation `D` and the file agree at 99% or more both ways in 6 of 9 cycles.**
  2014 (98.58%), 2016 (98.28%) and 2026 (98.83%) miss by 4 to 11 committees (Q12c). The checkpoint
  made a committee a leadership PAC when `cm` designates it `D` or the cycle's file lists it.
- **The sponsor's name: rung 2 (last name and first given name) matches 501 of 2024's 545 named
  sponsors, 460 of them to one person**, the ones the adopted rule links (Q4d, Q12a). Against OpenFEC by id it agrees at 99.19% in 2024 and only
  92.8–98.7% elsewhere (Q12b). By person, a name matching one candidate is right: OpenFEC lists a
  sponsor under their current id, so Schiff's House-era PAC carries his Senate id, and of 2,721
  checked single-person matches across all cycles only 23 name another name, mostly OpenFEC's own
  typos and members' older ids (Q14). The wrong links come from a name matching several ids: Dan
  Sullivan (MA House against AK Senate), Michael Simpson (SC against ID), John Conyers III against
  Jr. (Q14b).
- **The file leaves the sponsor blank on most of the largest leadership PACs.** 288 of 2024's 833
  rows, and OpenFEC names a sponsor for 242 of them, 84%, holding $198.8M of their $208.6M in file
  receipts: Save America (Trump, $99.7M), Jobs, Freedom and Security PAC (Cruz), Heartland Values
  (Thune), MC PAC (McCarthy), Eye of the Tiger (Scalise), Bluegrass (McConnell) (Q5f–g). 73–86% in
  every cycle (Q12b). `cm`'s connected organization holds a fundraising committee's name, not the
  sponsor (Q15).
- **`leadership_sponsors.csv`: 2,582 rows, 2010–2026** (Q16): 2,041 sponsors for blank rows, 255
  ids for names that match no candidate, 286 for names that match several ids, each from OpenFEC's
  sponsor of the committee.
- **`lobbyist.csv` is one row per Form 1 filing, not per committee**: 14,186 rows for 2,774
  committees, filed 2009-03-10 to 2026-11-24, the box `Y` or blank (Q1d–e, Q7). Neither per-cycle
  rule meets the 99% bar against `cm`'s designation `B` in any cycle: the best, "the latest Form 1
  filed by the cycle's end is `Y`", finds 94.5–98.8% of its committees `B`, and `cm` designates 26
  to 445 committees a cycle `B` that the file never lists, mostly super PACs and union and trade
  PACs (Q7f–i). The file is the flag's source, under that rule.
- **`lobbyist_bundle.csv` is one Form 3L report per row and names no lobbyist and no bundler.**
  1,929 rows, 433 recipients, coverage ending 2009-04-30 to 2026-10-14; each row carries a period
  amount and a semi-annual amount (Q1f, Q8). An amendment is another row with no indicator: 87
  (committee, covered period) keys sit on 194 rows, and keeping the latest receipt date, then the
  higher image number, supersedes 107 rows (Q9a–c).
- **The bundled total is the greater of the half-year figure and the innermost reports' period
  amounts**, per committee and half-year. Kept reports nest: a six-month year-end report whose
  period amount equals its semi-annual figure sits beside its quarters, holding 9.16% of the file's
  period dollars (Q9e). Added in, it counts that money twice (2020: $47.0M against $36.8M). Read
  innermost, the halves where the semi-annual figure falls below the periods' sum drop from 55
  ($13.58M) to 8 ($267,586) (Q10c). **2024: $57,262,231 at 84 recipients** (Q10a), every
  recipient's total within its counted individual contributions (Q11).
- **No Bug ticket.** No live figure is wrong. One leadership PAC is credited to a candidate by the
  existing rule, Never Surrender ($495.9M), Trump's principal campaign committee for the cycle
  until it became his leadership PAC: the money was raised as the campaign's, as
  `04_contribution.sql` already documents (Q6).

## How to re-run

On the VM, in `tmux`. Save the setup script below as `setup.py`, each block under its name, and
`run.sh` and `all.sh` beside them. Export an api.data.gov key as `FEC_API_KEY` in that shell (`read
-rs FEC_API_KEY && export FEC_API_KEY`), then run `all.sh`. It runs each block in order and stops at
the first that fails. OpenFEC's answers are cached in the work directory, so a re-run asks for none.
The whole run takes about 5 minutes the first time and 1 minute from the cache.

```bash
#!/bin/sh
# Usage: run.sh qN [extra.py ...]: setup.py, the extras and qN.py into the pipeline container, output
# to qN.out. FEC_API_KEY is passed from this shell's environment, never written anywhere. Exits with
# Python's status, so all.sh stops at a failing block.
P=$(docker ps --format "{{.Names}}" | grep "^${PIPELINE:-pipeline-lvch8zyndujjzkz16ksys8im}" | head -1)
q=$1; shift
cat setup.py "$@" $q.py | docker exec -e FEC_API_KEY -i "$P" python - > $q.raw 2>&1
status=$?
grep -v "^{" $q.raw > $q.out; rm -f $q.raw
echo "EXIT $status $(date -u +%FT%TZ)" >> $q.out
exit $status
```

```bash
#!/bin/sh
# The final run: every block in order, each into its own qN.out.
cd ~/measure-leadership-lobbyist-2024
date -u +"START %FT%TZ" > all.log
./run.sh q1 && ./run.sh q2 && ./run.sh q3 && ./run.sh q4 && ./run.sh q5 && ./run.sh q6 \
 && ./run.sh q7 && ./run.sh q8 && ./run.sh q9 && ./run.sh q10 && ./run.sh q11 && ./run.sh q12 \
 && ./run.sh q13 && ./run.sh q14 && ./run.sh q15 && ./run.sh q16
echo "status $?" >> all.log
date -u +"END %FT%TZ" >> all.log
# Afterwards:
# docker exec "$(docker ps --format '{{.Names}}' | grep '^pipeline-lvch8zyndujjzkz16ksys8im' | head -1)" \
#   rm -rf /data/fundlens/scratch/measure-leadership-lobbyist-2024
```

Run it never beside a pipeline step, and do not merge to `main` while it runs: a deploy restarts
`pipeline`.

Every table's title carries the seconds its query took. Amounts and dates are cast with `TRY_CAST`
and `try_strptime` inside each query, so a cell that fails is counted, not a read error.

### Setup

The setup is `outside-spending-2024.md`'s `show`, `fetch`, `view_csv` and `silver`, with these
additions:

- `lead(cycle)`, `lob()` and `bun()` are the three files typed. `bun` carries the amendment default
  (`kept`), the report's `cycle` and `half` by coverage end, and `days`, the covered period's length.
- `bun_halves()` is the bundled total per committee and half-year, under both readings (Q10).
- `match(cycle)` is the name rule's two rungs against the cycle's silver `candidate`; `ofec(cycle)`
  OpenFEC's sponsors; `agree(cycle)` the two side by side; `residue(cycle, n)` the list rows rung
  `n` would need as first tested (Q5, Q12; superseded by Q16 after the checkpoint).
- `allcand()` is every candidate id any cycle's live build holds, 1980–2026.

```python
import csv
import datetime as dt
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg

from fundlens import paths
from fundlens.fec.extract import USER_AGENT
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import Limits, connect, copy_as_utf8, literal

settings = get_settings()
store = R2.from_settings(settings)
scratch = paths.scratch_dir(settings.data_dir)
work = scratch / "measure-leadership-lobbyist-2024"
work.mkdir(parents=True, exist_ok=True)
con = connect(Limits.from_settings(settings), scratch)
FEC = "https://www.fec.gov/files/bulk-downloads"
OPENFEC = "https://api.open.fec.gov/v1"


def show(title: str, sql: str) -> None:
    """Run `sql` and print its result as a Markdown table, with the seconds it took."""
    start = time.monotonic()
    rel = con.sql(sql)
    rows = rel.fetchall()
    print(f"\n**{title}  ({time.monotonic() - start:.0f} s)**\n")
    print("| " + " | ".join(rel.columns) + " |")
    print("|" + "---|" * len(rel.columns))
    for row in rows:
        cells = (
            str(v) if name in ("cycle", "year", "img") and v is not None
            else f"{v:,.0f}" if isinstance(v, (int, Decimal)) and not isinstance(v, bool)
            else f"{v:.2%}" if isinstance(v, float) else "" if v is None else str(v)
            for name, v in zip(rel.columns, row)
        )
        print("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |")


def fetch(url: str, name: str | None = None) -> Path:
    """One file into `work`, following FEC's redirect; its URL, Last-Modified, size and download
    time printed on every call (kept beside it as `<name>.meta`). Skipped when already there."""
    target = work / (name or Path(url).name)
    meta = target.with_name(target.name + ".meta")
    if not target.exists():
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT})) as response:
            target.write_bytes(response.read())
            meta.write_text(
                f"{url} | Last-Modified: {response.headers.get('Last-Modified')}"
                f" | bytes {target.stat().st_size:,}"
                f" | downloaded {dt.datetime.now(dt.UTC).isoformat(timespec='seconds')}"
            )
    print(meta.read_text())
    return target


def view_csv(name: str, path: Path) -> list[str]:
    """The view `name` over `path` rewritten by `copy_as_utf8`: every column VARCHAR, named by
    the header row as served, in the dialect `register_bulk` reads a catalogued CSV in (a blank
    `""` is NULL). Prints the header and the records whose field count differs from it."""
    text = work / f"{name}.utf8.csv"
    with path.open("rb") as src, text.open("wb") as out:
        copy_as_utf8(src, out)
    with text.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        off = sum(1 for record in reader if len(record) != len(header))
    print(f"{name}: {len(header)} columns: {', '.join(header)}; records of another width: {off}")
    columns = ", ".join(f"{literal(h)}: 'VARCHAR'" for h in header)
    con.execute(
        f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv({literal(text)}, delim = ',',"
        " quote = '\"', escape = '\"', header = true, allow_quoted_nulls = true,"
        f" auto_detect = false, columns = {{{columns}}}, encoding = 'utf-8')"
    )
    return header


def exists(table: str) -> bool:
    return bool(con.execute(
        f"SELECT count(*) FROM duckdb_tables() WHERE table_name = '{table}'").fetchone()[0])


with psycopg.connect(settings.database_url) as pg:
    pg.read_only = True
    META = pg.execute("SELECT cycles FROM gold.meta").fetchone()[0]

# Every even cycle 2010-2026 with a live build (prod has all of them; dev has 2024 alone).
CYCLES = [c for c in range(2010, 2028, 2) if str(c) in META]
ALL_CYCLES = sorted(int(c) for c in META)


def silver(table: str, cycle: int) -> None:
    """The live build's partition of `table` for `cycle` as the view silver_<cycle>.<table>."""
    build = META[str(cycle)]["build_id"]
    con.execute(f"CREATE SCHEMA IF NOT EXISTS silver_{cycle}")
    prefix = paths.silver_partition(table, cycle, build)
    keys = store.list_keys(prefix + "/")
    if not keys:
        raise SystemExit(f"{table} {cycle}: build {build} has no partition")
    for key in keys:
        local = paths.local_path(settings.data_dir, key)
        if not local.exists():
            store.download_to(key, local)
    local = paths.local_path(settings.data_dir, prefix)
    con.execute(f"CREATE OR REPLACE VIEW silver_{cycle}.{table} AS SELECT * FROM read_parquet("
                f"{literal(local / '**' / '*.parquet')}, hive_partitioning = false)")


DMY = "CAST(try_strptime({c}, '%d-%b-%y') AS DATE)"
# lobbyist.csv's Date_Filed: whichever of FEC's date shapes parses (Q1 counts what none does).
ANYDATE = ("CAST(coalesce(try_strptime({c}, '%d-%b-%y'), try_strptime({c}, '%m/%d/%Y'),"
           " try_strptime({c}, '%Y-%m-%d'), try_strptime({c}, '%Y%m%d')) AS DATE)")
AMT = "TRY_CAST({c} AS DECIMAL(14, 2))"

# Names (spec §2): rung 1 compares the normalized name, rung 2 last name and first given name,
# as 03_candidate_committee_link.sql's alias rule and 04_contribution.sql's self-funding test do.
con.execute(r"""
    CREATE OR REPLACE MACRO norm(x) AS trim(regexp_replace(regexp_replace(regexp_replace(
        upper(x), '[^A-Z ]', ' ', 'g'), '\b(JR|SR|II|III|IV|MR|MRS|MS|DR|HON)\b', ' ', 'g'),
        ' +', ' ', 'g'));
    CREATE OR REPLACE MACRO lastn(x) AS regexp_replace(upper(split_part(x, ',', 1)),
        '[^A-Z0-9]', '', 'g');
    CREATE OR REPLACE MACRO firstn(x) AS regexp_replace(upper(split_part(trim(split_part(x, ',', 2)),
        ' ', 1)), '[^A-Z0-9]', '', 'g');
    CREATE OR REPLACE MACRO two_people(x) AS x LIKE '%&%' OR x LIKE '% AND %' OR x LIKE '%/%'
        OR x LIKE '%;%';
""")

LEAD_HEADER = ["Committee_Id", "Committee_Name", "Link_Image", "Sponsor_Name", "Cash_on_Hand",
               "Coverage_End_Date", "Total_Disbursement", "Total_Receipt"]


def lead(cycle: int) -> bool:
    """`lead_<cycle>`: `leadership<cycle>.csv` typed, `rn` its row number. False (and no table)
    when the file's header is not 2024's."""
    if exists(f"lead_{cycle}"):
        return True
    header = view_csv(f"leadraw_{cycle}", fetch(f"{FEC}/data.fec.gov/leadership{cycle}.csv"))
    if header != LEAD_HEADER:
        print(f"leadership{cycle}.csv: header differs from 2024's")
        return False
    con.execute(f"""
        CREATE TABLE lead_{cycle} AS
        SELECT row_number() OVER () AS rn, r.*, trim(Committee_Id) AS cid,
            nullif(trim(Sponsor_Name), '') AS sponsor,
            {AMT.format(c='Cash_on_Hand')} AS coh, {AMT.format(c='Total_Receipt')} AS rcpt,
            {AMT.format(c='Total_Disbursement')} AS disb, {DMY.format(c='Coverage_End_Date')} AS cvg_end
        FROM leadraw_{cycle} AS r""")
    return True


def lob() -> None:
    """`lob`: lobbyist.csv typed; `rn` its row number, `filed` Date_Filed, `y` Is_Lobbyist = 'Y'."""
    if exists("lob"):
        return
    view_csv("lobraw", fetch(f"{FEC}/data.fec.gov/lobbyist.csv"))
    con.execute(f"""
        CREATE TABLE lob AS
        SELECT row_number() OVER () AS rn, r.*, trim(Committee_Id) AS cid,
            {ANYDATE.format(c='Date_Filed')} AS filed, coalesce(Is_Lobbyist = 'Y', false) AS y
        FROM lobraw AS r""")


def bun() -> None:
    """`bun`: lobbyist_bundle.csv typed. `rn` its row number; `img` the image number ending
    `Link_Image`; `cs`, `ce` the covered period, `rdt` Receipt_Date; `q` the period amount, `s` the
    semi-annual amount; `cycle` and `half` (e.g. 2024-1) by `ce`. `kept` is the amendment default
    (spec §1.1): among rows of one committee with the same coverage start and end, the latest
    receipt date, then the higher image number; a row with a blank coverage date is kept alone."""
    if exists("bun"):
        return
    view_csv("bunraw", fetch(f"{FEC}/data.fec.gov/lobbyist_bundle.csv"))
    con.execute(f"""
        CREATE TABLE bun AS
        WITH t AS (
            SELECT row_number() OVER () AS rn, r.*, trim(Committee_Id) AS cid,
                TRY_CAST(regexp_extract(Link_Image, '[?]_?([0-9]+)', 1) AS BIGINT) AS img,
                {DMY.format(c='Coverage_Start_Date')} AS cs, {DMY.format(c='Coverage_End_Date')} AS ce,
                {DMY.format(c='Receipt_Date')} AS rdt,
                {AMT.format(c='Quarterly_Contribution')} AS q,
                {AMT.format(c='Semi_Annual_Contribution')} AS s
            FROM bunraw AS r
        )
        SELECT t.*,
            year(ce) + year(ce) % 2 AS cycle,
            year(ce) || '-' || CASE WHEN month(ce) <= 6 THEN '1' ELSE '2' END AS half,
            date_diff('day', cs, ce) + 1 AS days,
            row_number() OVER (
                PARTITION BY cid, cs, ce, CASE WHEN cs IS NULL OR ce IS NULL THEN rn END
                ORDER BY rdt DESC NULLS LAST, img DESC NULLS LAST, rn DESC) = 1 AS kept
        FROM t""")


def bun_halves() -> None:
    """`bh`: per committee and half-year, from kept reports: `hf` the half-year figure (the
    semi-annual amount on the kept report with the latest coverage end in the half that carries
    one above $0), `ps` the period amounts added, `g` the greater (spec §1.1). The second reading
    (Q9e): `ps_inner` adds only the kept reports whose covered period holds no other kept report
    of the committee (a six-month report beside its quarters adds nothing), `g_inner` the greater
    of `hf` and that; `outer_reports` counts the reports left out."""
    bun()
    if exists("bh"):
        return
    con.execute("""
        CREATE TABLE bh AS
        WITH k AS (
            SELECT a.*, EXISTS (
                SELECT 1 FROM bun AS b
                WHERE b.kept AND b.cid = a.cid AND b.rn <> a.rn AND b.cs >= a.cs AND b.ce <= a.ce
                    AND (b.cs, b.ce) <> (a.cs, a.ce)) AS holds_another
            FROM bun AS a WHERE a.kept AND a.ce IS NOT NULL
        )
        SELECT cid, cycle, half,
            max_by(s, ce) FILTER (WHERE s > 0) AS hf,
            sum(q) AS ps,
            greatest(coalesce(max_by(s, ce) FILTER (WHERE s > 0), 0), coalesce(sum(q), 0)) AS g,
            sum(q) FILTER (WHERE NOT holds_another) AS ps_inner,
            greatest(coalesce(max_by(s, ce) FILTER (WHERE s > 0), 0),
                     coalesce(sum(q) FILTER (WHERE NOT holds_another), 0)) AS g_inner,
            count(*) AS reports, count(*) FILTER (WHERE holds_another) AS outer_reports
        FROM k GROUP BY ALL""")


def cmte(cycle: int) -> None:
    """`cmte_<cycle>`: the cycle's silver committee, its designation and type."""
    if exists(f"cmte_{cycle}"):
        return
    silver("committee", cycle)
    con.execute(f"""CREATE TABLE cmte_{cycle} AS SELECT committee_id AS cid, name, designation,
        type, candidate_id FROM silver_{cycle}.committee""")


def allcmte() -> None:
    """`allcmte`: every CYCLES committee, with its cycle."""
    if exists("allcmte"):
        return
    for c in CYCLES:
        cmte(c)
    con.execute("CREATE TABLE allcmte AS " + " UNION ALL ".join(
        f"SELECT {c} AS cycle, * FROM cmte_{c}" for c in CYCLES))


def cand(cycle: int) -> None:
    """`cand_<cycle>`: the cycle's silver candidate, `person` through `alias_of`, with the three
    name keys."""
    if exists(f"cand_{cycle}"):
        return
    silver("candidate", cycle)
    con.execute(f"""
        CREATE TABLE cand_{cycle} AS
        SELECT candidate_id, coalesce(alias_of, candidate_id) AS person, name, office, state,
            district, race_id, TRY_CAST(election_year AS INTEGER) AS election_year,
            norm(name) AS n1, lastn(name) AS ln, firstn(name) AS fn
        FROM silver_{cycle}.candidate""")


def allcand() -> None:
    """`allcand`: every candidate id fundlens holds in any cycle's live build, its latest name."""
    if exists("allcand"):
        return
    for c in ALL_CYCLES:
        silver("candidate", c)
    con.execute("CREATE TABLE allcand AS SELECT candidate_id, arg_max(name, cycle) AS name,"
                " list(DISTINCT cycle ORDER BY cycle) AS cycles FROM (" + " UNION ALL ".join(
                    f"SELECT {c} AS cycle, candidate_id, name FROM silver_{c}.candidate"
                    for c in ALL_CYCLES) + ") GROUP BY 1")


def rt(cycle: int) -> None:
    """`rt_<cycle>`: the cycle's silver reported_total."""
    if exists(f"rt_{cycle}"):
        return
    silver("reported_total", cycle)
    con.execute(f"CREATE TABLE rt_{cycle} AS SELECT * FROM silver_{cycle}.reported_total")


def match(cycle: int) -> None:
    """`m_<cycle>`: each named sponsor of `lead_<cycle>` against the cycle's candidates, per rung:
    `r<n>` the class ('one', 'one person, several ids', 'several people', 'none'), `r<n>_id` the
    id the rule takes (standing in a race first, then the latest election year, then the lowest
    id; NULL for several people or none), `r<n>_ids` every id matched."""
    if exists(f"m_{cycle}"):
        return
    lead(cycle)
    cand(cycle)

    def rung(n: int, on: str) -> str:
        return f"""
        r{n} AS (
            SELECT s.cid, count(DISTINCT k.person) AS people, count(DISTINCT k.n1) AS names,
                list(DISTINCT k.candidate_id ORDER BY k.candidate_id) AS ids,
                first(k.candidate_id ORDER BY k.race_id IS NOT NULL DESC,
                      k.election_year DESC NULLS LAST, k.candidate_id) AS pick
            FROM s JOIN cand_{cycle} AS k ON {on}
            GROUP BY s.cid)"""

    def cls(n: int) -> str:
        return (f"CASE WHEN r{n}.cid IS NULL THEN 'none' WHEN r{n}.people = 1 THEN 'one'"
                f" WHEN r{n}.names = 1 THEN 'one person, several ids' ELSE 'several people' END")

    con.execute(f"""
        CREATE TABLE m_{cycle} AS
        WITH s AS (SELECT cid, sponsor, norm(sponsor) AS n1, lastn(sponsor) AS ln,
                       firstn(sponsor) AS fn
                   FROM lead_{cycle} WHERE sponsor IS NOT NULL),
        {rung(1, 'k.n1 = s.n1')},
        {rung(2, "k.ln = s.ln AND k.fn = s.fn AND s.fn <> ''")}
        SELECT s.cid, s.sponsor, two_people(s.sponsor) AS two_people,
            {cls(1)} AS r1, CASE WHEN {cls(1)} IN ('one', 'one person, several ids') THEN r1.pick END AS r1_id,
            r1.ids AS r1_ids,
            {cls(2)} AS r2, CASE WHEN {cls(2)} IN ('one', 'one person, several ids') THEN r2.pick END AS r2_id,
            r2.ids AS r2_ids
        FROM s LEFT JOIN r1 USING (cid) LEFT JOIN r2 USING (cid)""")


def openfec(path: str, tag: str, **params: object) -> list[dict]:
    """Every page of an OpenFEC list endpoint, the key from FEC_API_KEY sent in a header (never in
    a URL or a file). Each page cached as work/ofec-<tag>-<page>.json, so a re-run asks for none."""
    results: list[dict] = []
    page = 1
    while True:
        cache = work / f"ofec-{tag}-{page}.json"
        if not cache.exists():
            key = os.environ.get("FEC_API_KEY")
            if not key:
                raise SystemExit("FEC_API_KEY is not set")
            url = f"{OPENFEC}{path}?" + urlencode({**params, "per_page": 100, "page": page},
                                                  doseq=True)
            for attempt in range(5):
                try:
                    with urlopen(Request(url, headers={"User-Agent": USER_AGENT,
                                                       "X-Api-Key": key})) as response:
                        cache.write_bytes(response.read())
                    break
                except HTTPError as e:
                    if e.code != 429 or attempt == 4:
                        raise
                    time.sleep(60)
            time.sleep(0.5)
        body = json.loads(cache.read_text())
        results += body["results"]
        if page >= body["pagination"]["pages"]:
            return results
        page += 1


def ofec(cycle: int) -> None:
    """`of_<cycle>`: OpenFEC's committees designated D for the cycle, and each of
    `leadership<cycle>.csv`'s committees that list lacks fetched by id: `found`, `o_dsgn`,
    `o_ids` (sponsor_candidate_ids) and `o_names`."""
    if exists(f"of_{cycle}"):
        return
    lead(cycle)
    rows = {r["committee_id"]: r for r in openfec("/committees/", f"d-{cycle}",
                                                  designation="D", cycle=cycle)}
    missing = [cid for (cid,) in con.execute(
        f"SELECT DISTINCT cid FROM lead_{cycle} ORDER BY 1").fetchall() if cid not in rows]
    for i in range(0, len(missing), 50):
        for r in openfec("/committees/", f"id-{cycle}-{i}", committee_id=missing[i:i + 50]):
            rows[r["committee_id"]] = r
    out = work / f"of_{cycle}.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cid", "o_dsgn", "o_ids", "o_names"])
        for cid, r in sorted(rows.items()):
            sponsors = r.get("sponsor_candidate_list") or []
            w.writerow([cid, r.get("designation"), "|".join(r.get("sponsor_candidate_ids") or []),
                        "|".join(s.get("sponsor_candidate_name") or "" for s in sponsors)])
    con.execute(f"""
        CREATE TABLE of_{cycle} AS
        SELECT cid, o_dsgn, CASE WHEN o_ids IS NULL THEN [] ELSE string_split(o_ids, '|') END AS o_ids,
            o_names
        FROM read_csv({literal(out)}, header = true, all_varchar = true)""")
    print(f"OpenFEC {cycle}: {len(rows)} committees ({len(missing)} of the file's fetched by id)")


def agree(cycle: int) -> None:
    """`a_<cycle>`: each of `leadership<cycle>.csv`'s committees with its sponsor, both rungs'
    matches and OpenFEC's sponsors; `a<n>` how rung n's id stands against OpenFEC's:
    'agree' (the id is OpenFEC's), 'same person' (another of the matched ids is), 'disagree',
    'rule none' (rung n takes no id; OpenFEC names one), 'OpenFEC none' (OpenFEC names none),
    'OpenFEC lacks' (OpenFEC does not hold the committee)."""
    if exists(f"a_{cycle}"):
        return
    match(cycle)
    ofec(cycle)

    def st(n: int) -> str:
        return f"""CASE WHEN o.cid IS NULL THEN 'OpenFEC lacks'
            WHEN len(o.o_ids) = 0 THEN 'OpenFEC none'
            WHEN m.r{n}_id IS NULL THEN 'rule none'
            WHEN list_contains(o.o_ids, m.r{n}_id) THEN 'agree'
            WHEN list_has_any(o.o_ids, m.r{n}_ids) THEN 'same person'
            ELSE 'disagree' END"""

    con.execute(f"""
        CREATE TABLE a_{cycle} AS
        SELECT l.cid, l.Committee_Name AS name, l.sponsor, l.rcpt, m.two_people,
            m.r1, m.r1_id, m.r1_ids, m.r2, m.r2_id, m.r2_ids,
            o.cid IS NOT NULL AS o_found, o.o_dsgn, o.o_ids, o.o_names,
            CASE WHEN l.sponsor IS NULL THEN NULL ELSE {st(1)} END AS a1,
            CASE WHEN l.sponsor IS NULL THEN NULL ELSE {st(2)} END AS a2
        FROM lead_{cycle} AS l
        LEFT JOIN m_{cycle} AS m USING (cid)
        LEFT JOIN of_{cycle} AS o USING (cid)""")


def residue(cycle: int, n: int) -> None:
    """`res<n>_<cycle>`: the rows `leadership_sponsors.csv` needs for the cycle if rung n is the
    rule: each named sponsor whose rung-n id OpenFEC contradicts ('disagree'), or that rung n
    gives no id and OpenFEC names exactly one person for ('rule none'). `candidate_id` is
    OpenFEC's first id when fundlens holds a candidate under it in some cycle, else blank (the
    row then stops a wrong match). `people` is how many sponsors OpenFEC names."""
    agree(cycle)
    allcand()
    con.execute(f"""
        CREATE OR REPLACE TABLE res{n}_{cycle} AS
        SELECT {cycle} AS cycle, a.cid AS committee_id, a.sponsor AS sponsor_name,
            CASE WHEN ac.candidate_id IS NOT NULL THEN a.o_ids[1] END AS candidate_id,
            'https://www.fec.gov/data/committee/' || a.cid || '/ sponsor ' || a.o_names AS source,
            a.a{n} AS why, a.r{n} AS rule_class, a.r{n}_id AS rule_id, a.o_ids,
            len(list_distinct(string_split(a.o_names, '|'))) AS people, ac.name AS held_name
        FROM a_{cycle} AS a
        LEFT JOIN allcand AS ac ON ac.candidate_id = a.o_ids[1]
        WHERE a.a{n} = 'disagree'
            OR (a.a{n} = 'rule none'
                AND len(list_distinct(string_split(a.o_names, '|'))) = 1)""")


print("builds", {c: META[str(c)]["build_id"] for c in CYCLES},
      "| cycles without a build:", [c for c in range(2010, 2028, 2) if c not in CYCLES],
      "| duckdb", con.execute("SELECT version()").fetchone()[0], "|", Limits.from_settings(settings),
      "| commit", {k: v for k, v in os.environ.items() if "COMMIT" in k or k == "IMAGE_TAG"})
```

## Q1: shape of the three files

All three files are in project spec §3's CSV dialect: header unquoted, every data field
double-quoted, LF endings, no BOM, no record of another width. Every amount and date casts.
`leadership2024.csv` is one row per committee (833), with the sponsor blank on 288 and the coverage
end blank on 19; 13 sponsors name two or three PACs (Merkley three). `lobbyist.csv` has no repeated
key: each row is one filing (`Link_Image`), dated 2009-03-10 to 2026-11-24, the box `Y` on 12,570
rows and blank on 1,616. `lobbyist_bundle.csv` has no fully repeated row; 29 rows have a blank
coverage date, 339 both amounts 0, none a negative amount. Its 34 `Report_Type` strings name the
same report in several ways (`QUARTERLY YEAR END / SEMI-ANN`, `QUARTERLY SEMI-ANNUAL (YE)`), and a
covered period runs from 1 day to 1,128, so Q8 groups reports by length. The image number in
`Link_Image` (`?_202407199661302879+0`) is what Q9 breaks ties by.

```python
# Q1: shape of the three files (2024's leadership file and the two undated ones).
lead(2024)
lob()
bun()
for path in sorted(work.glob("*.csv.meta")):
    print(path.read_text())
for name in ("leadership2024.csv", "lobbyist.csv", "lobbyist_bundle.csv"):
    raw = (work / name).read_bytes()
    print(f"{name}: {len(raw):,} bytes, {raw.count(b'\n'):,} LF, {raw.count(b'\r'):,} CR,"
          f" BOM {raw.startswith(b'\xef\xbb\xbf')}, header line: {raw.split(b'\n', 1)[0]!r}")
    lines = raw.split(b"\n")[1:]
    data = [l for l in lines if l]
    unquoted = sum(1 for l in data if not (l.startswith(b'"') and l.rstrip(b"\r").endswith(b'"')))
    print(f"  data lines {len(data):,}; lines not starting and ending with a quote: {unquoted:,}")

show("Q1a leadership2024.csv: rows, keys, casts", """
    SELECT count(*) AS rows, count(DISTINCT cid) AS committees,
        count(*) - count(DISTINCT cid) AS rows_beyond_one_per_committee,
        count(*) FILTER (WHERE sponsor IS NULL) AS blank_sponsor,
        count(*) FILTER (WHERE Cash_on_Hand IS NOT NULL AND coh IS NULL) AS coh_cast_fail,
        count(*) FILTER (WHERE Total_Receipt IS NOT NULL AND rcpt IS NULL) AS rcpt_cast_fail,
        count(*) FILTER (WHERE Total_Disbursement IS NOT NULL AND disb IS NULL) AS disb_cast_fail,
        count(*) FILTER (WHERE Coverage_End_Date IS NOT NULL AND cvg_end IS NULL) AS date_cast_fail,
        count(*) FILTER (WHERE Coverage_End_Date IS NULL) AS blank_date,
        (SELECT count(*) FROM (SELECT DISTINCT * EXCLUDE (rn) FROM lead_2024)) AS distinct_rows
    FROM lead_2024""")
show("Q1b leadership2024.csv: Coverage_End_Date by value", """
    SELECT cvg_end, count(*) AS rows FROM lead_2024 GROUP BY 1 ORDER BY 2 DESC LIMIT 12""")
show("Q1c leadership2024.csv: sponsor names on several rows", """
    SELECT sponsor, count(*) AS rows, string_agg(cid || ' ' || Committee_Name, '; ') AS committees
    FROM lead_2024 WHERE sponsor IS NOT NULL GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC, 1""")
show("Q1d lobbyist.csv: rows, keys, casts", """
    SELECT count(*) AS rows, count(DISTINCT cid) AS committees,
        count(DISTINCT (cid, Date_Filed, Link_Image)) AS distinct_keys,
        (SELECT count(*) FROM (SELECT DISTINCT * EXCLUDE (rn, filed, y) FROM lob)) AS distinct_rows,
        count(*) FILTER (WHERE Date_Filed IS NOT NULL AND filed IS NULL) AS date_cast_fail,
        count(*) FILTER (WHERE Date_Filed IS NULL) AS blank_date,
        min(filed) AS first_filed, max(filed) AS last_filed,
        any_value(Date_Filed) AS a_date_as_filed
    FROM lob""")
show("Q1e lobbyist.csv: Is_Lobbyist by value", """
    SELECT Is_Lobbyist, count(*) AS rows, count(DISTINCT cid) AS committees FROM lob GROUP BY 1
    ORDER BY 2 DESC""")
show("Q1f lobbyist_bundle.csv: rows, keys, casts", """
    SELECT count(*) AS rows, count(DISTINCT cid) AS committees,
        count(DISTINCT (cid, cs, ce, rdt, Link_Image)) AS distinct_keys,
        (SELECT count(*) FROM (SELECT DISTINCT * EXCLUDE (rn, img, cycle, half, days, kept) FROM bun))
            AS distinct_rows,
        count(*) FILTER (WHERE Quarterly_Contribution IS NOT NULL AND q IS NULL) AS q_cast_fail,
        count(*) FILTER (WHERE Semi_Annual_Contribution IS NOT NULL AND s IS NULL) AS s_cast_fail,
        count(*) FILTER (WHERE Receipt_Date IS NOT NULL AND rdt IS NULL) AS rdt_cast_fail,
        count(*) FILTER (WHERE Coverage_Start_Date IS NOT NULL AND cs IS NULL) AS cs_cast_fail,
        count(*) FILTER (WHERE Coverage_End_Date IS NOT NULL AND ce IS NULL) AS ce_cast_fail,
        count(*) FILTER (WHERE cs IS NULL OR ce IS NULL) AS blank_coverage,
        count(*) FILTER (WHERE img IS NULL) AS no_image_number,
        count(*) FILTER (WHERE q = 0 AND s = 0) AS both_zero,
        count(*) FILTER (WHERE q > 0) AS q_above_0, count(*) FILTER (WHERE s > 0) AS s_above_0,
        count(*) FILTER (WHERE q < 0 OR s < 0) AS negative,
        sum(q) AS q_sum, sum(s) AS s_sum, min(ce) AS first_end, max(ce) AS last_end
    FROM bun""")
show("Q1g lobbyist_bundle.csv: Report_Type by value", """
    SELECT Report_Type, count(*) AS rows, min(days) AS min_days, max(days) AS max_days,
        sum(q) AS q_sum, sum(s) AS s_sum
    FROM bun GROUP BY 1 ORDER BY 2 DESC""")
show("Q1h lobbyist_bundle.csv: election state and district filled", """
    SELECT Committee_Election_State IS NOT NULL AS state_filled,
        Committee_Election_District IS NOT NULL AS district_filled, count(*) AS rows
    FROM bun GROUP BY ALL ORDER BY ALL""")
show("Q1i a sample of each file (first 3 rows)", """
    SELECT 'leadership' AS file, to_json(l) AS row FROM (SELECT * FROM leadraw_2024 LIMIT 3) AS l
    UNION ALL SELECT 'lobbyist', to_json(x) FROM (SELECT * FROM lobraw LIMIT 3) AS x
    UNION ALL SELECT 'bundle', to_json(b) FROM (SELECT * FROM bunraw LIMIT 3) AS b""")
```

Output:

builds {2010: '20261114T020123Z', 2012: '20261114T180514Z', 2014: '20261114T182542Z', 2016: '20261114T184036Z', 2018: '20261116T001733Z', 2020: '20261115T033259Z', 2022: '20261115T173437Z', 2024: '20261125T021311Z', 2026: '20261123T224142Z'} | cycles without a build: [] | duckdb v2.0.0 | Limits(memory_limit='32GB', max_temp_directory_size='60GB', threads=6) | commit {'SOURCE_COMMIT': ''}
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2024.csv | Last-Modified: Wed, 25 Nov 2026 10:10:59 GMT | bytes 120,104 | downloaded 2026-11-25T17:51:32+00:00
leadraw_2024: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/data.fec.gov/lobbyist.csv | Last-Modified: Wed, 25 Nov 2026 10:11:03 GMT | bytes 2,046,415 | downloaded 2026-11-25T17:57:58+00:00
lobraw: 5 columns: Link_Image, Committee_Name, Committee_Id, Date_Filed, Is_Lobbyist; records of another width: 0
https://www.fec.gov/files/bulk-downloads/data.fec.gov/lobbyist_bundle.csv | Last-Modified: Wed, 25 Nov 2026 10:11:06 GMT | bytes 347,542 | downloaded 2026-11-25T17:58:00+00:00
bunraw: 11 columns: Committee_Id, Committee_Name, Link_Image, Committee_Election_State, Committee_Election_District, Report_Type, Receipt_Date, Coverage_Start_Date, Coverage_End_Date, Quarterly_Contribution, Semi_Annual_Contribution; records of another width: 0
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2010.csv | Last-Modified: Thu, 02 Jan 2025 10:13:34 GMT | bytes 61,357 | downloaded 2026-11-25T17:59:10+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2012.csv | Last-Modified: Thu, 02 Jan 2025 10:13:36 GMT | bytes 77,483 | downloaded 2026-11-25T17:59:31+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2014.csv | Last-Modified: Thu, 02 Jan 2025 10:13:38 GMT | bytes 80,944 | downloaded 2026-11-25T17:59:49+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2016.csv | Last-Modified: Thu, 02 Jan 2025 10:13:40 GMT | bytes 84,209 | downloaded 2026-11-25T18:00:11+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2018.csv | Last-Modified: Thu, 02 Jan 2025 10:13:42 GMT | bytes 97,197 | downloaded 2026-11-25T18:00:32+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2020.csv | Last-Modified: Thu, 02 Jan 2025 10:13:44 GMT | bytes 103,560 | downloaded 2026-11-25T18:00:54+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2022.csv | Last-Modified: Wed, 25 Nov 2026 10:10:57 GMT | bytes 109,905 | downloaded 2026-11-25T18:01:20+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2024.csv | Last-Modified: Wed, 25 Nov 2026 10:10:59 GMT | bytes 120,104 | downloaded 2026-11-25T17:51:32+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2026.csv | Last-Modified: Wed, 25 Nov 2026 10:11:01 GMT | bytes 133,894 | downloaded 2026-11-25T18:01:47+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/lobbyist.csv | Last-Modified: Wed, 25 Nov 2026 10:11:03 GMT | bytes 2,046,415 | downloaded 2026-11-25T17:57:58+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/lobbyist_bundle.csv | Last-Modified: Wed, 25 Nov 2026 10:11:06 GMT | bytes 347,542 | downloaded 2026-11-25T17:58:00+00:00
leadership2024.csv: 120,104 bytes, 834 LF, 0 CR, BOM False, header line: b'Committee_Id,Committee_Name,Link_Image,Sponsor_Name,Cash_on_Hand,Coverage_End_Date,Total_Disbursement,Total_Receipt'
  data lines 833; lines not starting and ending with a quote: 0
lobbyist.csv: 2,046,415 bytes, 14,187 LF, 0 CR, BOM False, header line: b'Link_Image,Committee_Name,Committee_Id,Date_Filed,Is_Lobbyist'
  data lines 14,186; lines not starting and ending with a quote: 0
lobbyist_bundle.csv: 347,542 bytes, 1,930 LF, 0 CR, BOM False, header line: b'Committee_Id,Committee_Name,Link_Image,Committee_Election_State,Committee_Election_District,Report_Type,Receipt_Date,Coverage_Start_Date,Coverage_End_Date,Quarterly_Contribution,Semi_Annual_Contribution'
  data lines 1,929; lines not starting and ending with a quote: 0

**Q1a leadership2024.csv: rows, keys, casts  (0 s)**

| rows | committees | rows_beyond_one_per_committee | blank_sponsor | coh_cast_fail | rcpt_cast_fail | disb_cast_fail | date_cast_fail | blank_date | distinct_rows |
|---|---|---|---|---|---|---|---|---|---|
| 833 | 833 | 0 | 288 | 0 | 0 | 0 | 0 | 19 | 833 |

**Q1b leadership2024.csv: Coverage_End_Date by value  (0 s)**

| cvg_end | rows |
|---|---|
| 2024-12-31 | 722 |
|  | 19 |
| 2023-06-30 | 7 |
| 2024-09-30 | 7 |
| 2024-06-30 | 6 |
| 2024-11-25 | 5 |
| 2023-03-31 | 4 |
| 2023-12-31 | 4 |
| 2024-03-31 | 3 |
| 2023-08-16 | 2 |
| 2024-04-30 | 2 |
| 2024-04-15 | 2 |

**Q1c leadership2024.csv: sponsor names on several rows  (0 s)**

| sponsor | rows | committees |
|---|---|---|
| MERKLEY, JEFFREY | 3 | C00743641 BLUE SENATE PAC; C00460972 BLUE WAVE PROJECT; C00605410 CLIMATE CHAMPIONS PAC |
| AGUILAR, PETE | 2 | C00573709 CA LUV PAC (CALIFORNIA LEADERSHIP UNITED FOR VICTORY PAC); C00663609 PROGRESSIVE MAJORITY PAC |
| BROWNLEY, JULIA | 2 | C00567495 JOBS UNITE LABOR AND INDUSTRY IN AMERICA PAC (JULIA PAC); C00868307 PROTECT DEMOCRACY NOW |
| CORNYN, JOHN | 2 | C00387464 ALAMO PAC; C00570861 R SENATE PAC |
| CRAPO, MICHAEL | 2 | C00390674 FREEDOM FUND; C00544270 IDAHO CONSERVATIVE GROWTH FUND |
| DELBENE, SUZAN | 2 | C00844720 DEMOCRATIC MAJORITY FUND; C00576090 EVERGREEN PAC |
| GALLEGO, RUBEN | 2 | C00892752 JUNTOS PAC; C00576975 LATINO LEADERS FOR EQUALITY, GROWTH, OPPORTUNITY, PROGRESSIVE ACTION & CHANGE (LLEGO-PAC) |
| GUTHRIE, S. BRETT | 2 | C00879288 NICE PAC; C00483487 BRINGING REPUBLICAN EXCELLENCE TO TOWN PAC |
| JAYAPAL, PRAMILA | 2 | C00629576 BUILD OUR MOVEMENT PAC; C00685552 MEDICARE FOR ALL |
| KISTNER, TYLER | 2 | C00732925 SKOL PAC; C00809863 SERVICE KNOWLEDGE OATH LEADERSHIP PAC (SKOL PAC) |
| LIEU, TED | 2 | C00589309 BLUE MOMENTUM PAC; C00798579 PROGRESSIVE PAC |
| MCCORMICK, DAVE | 2 | C00851998 PENNSYLVANIA HONOR; C00824474 THE AMERICAN RENEWAL PAC |
| SCOTT, TIMOTHY E. | 2 | C00495887 TOMORROW IS MEANINGFUL PAC; C00827519 TOMORROW IS MEANINGFUL PAC - FEDERAL |

**Q1d lobbyist.csv: rows, keys, casts  (0 s)**

| rows | committees | distinct_keys | distinct_rows | date_cast_fail | blank_date | first_filed | last_filed | a_date_as_filed |
|---|---|---|---|---|---|---|---|---|
| 14,186 | 2,774 | 14,186 | 14,186 | 0 | 0 | 2009-03-10 | 2026-11-24 | 30-NOV-23 |

**Q1e lobbyist.csv: Is_Lobbyist by value  (0 s)**

| Is_Lobbyist | rows | committees |
|---|---|---|
| Y | 12,570 | 2,774 |
|  | 1,616 | 561 |

**Q1f lobbyist_bundle.csv: rows, keys, casts  (0 s)**

| rows | committees | distinct_keys | distinct_rows | q_cast_fail | s_cast_fail | rdt_cast_fail | cs_cast_fail | ce_cast_fail | blank_coverage | no_image_number | both_zero | q_above_0 | s_above_0 | negative | q_sum | s_sum | first_end | last_end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1,929 | 433 | 1,929 | 1,929 | 0 | 0 | 0 | 0 | 0 | 29 | 0 | 339 | 1,260 | 771 | 0 | 307,126,557 | 294,264,771 | 2009-04-30 | 2026-10-14 |

**Q1g lobbyist_bundle.csv: Report_Type by value  (0 s)**

| Report_Type | rows | min_days | max_days | q_sum | s_sum |
|---|---|---|---|---|---|
| OCTOBER QUARTERLY | 349 | 36 | 442 | 83,761,607 | 384,772 |
| JULY QUARTERLY / SEMI-ANNUAL | 255 | 20 | 182 | 38,174,789 | 69,924,158 |
| APRIL QUARTERLY | 240 | 34 | 254 | 36,576,507 | 868,156 |
| QUARTERLY YEAR END / SEMI-ANN | 221 | 33 | 366 | 32,198,263 | 54,176,436 |
| QUARTERLY SEMI-ANNUAL (YE) | 121 | 5 | 1,128 | 189,450 | 31,249,631 |
| QUARTERLY SEMI-ANNUAL (MY) | 96 | 6 | 182 | 342,945 | 4,382,394 |
| PRE-GENERAL | 89 | 2 | 122 | 10,123,100 | 490,240 |
| PRE-PRIMARY | 79 | 1 | 105 | 3,344,721 | 114,775 |
| POST-GENERAL | 77 | 21 | 99 | 7,427,632 | 311,727 |
| JULY QUARTERLY | 65 | 22 | 423 | 3,467,048 | 8,529,530 |
| YEAR-END | 37 | 33 | 366 | 2,179,447 | 5,394,884 |
| QUARTERLY MID-YEAR / SEMI-ANN | 28 | 30 | 184 | 15,560,226 | 19,079,621 |
| AUGUST MONTHLY | 26 | 31 | 31 | 4,866,603 | 0 |
| MAY MONTHLY | 26 | 30 | 31 | 6,151,879 | 0 |
| JULY MONTHLY / SEMI-ANNUAL | 25 | 30 | 182 | 4,418,413 | 71,526,493 |
| APRIL MONTHLY | 24 | 31 | 31 | 19,105,256 | 0 |
| FEBRUARY MONTHLY | 23 | 28 | 31 | 14,158,305 | 0 |
| MARCH MONTHLY | 22 | 28 | 31 | 12,994,604 | 0 |
| MONTHLY SEMI-ANNUAL (YE) | 20 | 30 | 184 | 0 | 7,503,242 |
| OCTOBER MONTHLY | 19 | 30 | 30 | 3,320,315 | 0 |
| JUNE MONTHLY | 17 | 31 | 46 | 1,103,308 | 0 |
| SEPTEMBER MONTHLY | 15 | 31 | 31 | 3,037,317 | 0 |
| MONTHLY YEAR END / SEMI-ANNUAL | 13 | 31 | 184 | 825,612 | 14,476,897 |
| MONTHLY SEMI-ANNUAL (MY) | 11 | 30 | 30 | 0 | 2,192,621 |
| DECEMBER MONTHLY | 6 | 5 | 30 | 111,330 | 0 |
| PRE-RUN-OFF | 5 | 28 | 85 | 547,341 | 0 |
|  | 5 | 90 | 184 | 142,650 | 109,500 |
| NOVEMBER MONTHLY | 5 | 31 | 31 | 301,000 | 0 |
| PRE-SPECIAL | 3 | 63 | 99 | 300,504 | 0 |
| MID-YEAR REPORT | 2 | 91 | 181 | 1,974,276 | 2,013,776 |
| POST-RUN-OFF | 2 | 40 | 40 | 107,827 | 0 |
| POST-SPECIAL | 1 | 40 | 40 | 30,316 | 0 |
| PRE-CONVENTION | 1 | 16 | 16 | 70,500 | 0 |
| JULY MONTHLY | 1 | 30 | 30 | 213,463 | 1,535,918 |

**Q1h lobbyist_bundle.csv: election state and district filled  (0 s)**

| state_filled | district_filled | rows |
|---|---|---|
| False | False | 696 |
| False | True | 8 |
| True | False | 347 |
| True | True | 878 |

**Q1i a sample of each file (first 3 rows)  (0 s)**

| file | row |
|---|---|
| leadership | {"Committee_Id":"C00747766","Committee_Name":"TRUTH TO POWER","Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?C00747766","Sponsor_Name":null,"Cash_on_Hand":"299795.41","Coverage_End_Date":"31-DEC-24","Total_Disbursement":"849234.2","Total_Receipt":"1031005.7"} |
| leadership | {"Committee_Id":"C00432617","Committee_Name":"GENERATION BLUE","Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?C00432617","Sponsor_Name":null,"Cash_on_Hand":"0","Coverage_End_Date":"31-DEC-24","Total_Disbursement":"0","Total_Receipt":"0"} |
| leadership | {"Committee_Id":"C00536540","Committee_Name":"JOBS, FREEDOM, AND SECURITY PAC","Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?C00536540","Sponsor_Name":null,"Cash_on_Hand":"2597995.99","Coverage_End_Date":"31-DEC-24","Total_Disbursement":"1000133.3","Total_Receipt":"3479994.3"} |
| lobbyist | {"Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?_202611249945510988+0","Committee_Name":"150PAC.ORG","Committee_Id":"C00614552","Date_Filed":"24-NOV-26","Is_Lobbyist":"Y"} |
| lobbyist | {"Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?_202611249945512089+0","Committee_Name":"NORTHWESTERN ENERGY MONTANA EMPLOYEE PAC","Committee_Id":"C00068056","Date_Filed":"24-NOV-26","Is_Lobbyist":"Y"} |
| lobbyist | {"Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?_202611249945510939+0","Committee_Name":"SUNRUN INC POLITICAL ACTION COMMITTEE (SUNRUN PAC)","Committee_Id":"C00489302","Date_Filed":"24-NOV-26","Is_Lobbyist":"Y"} |
| bundle | {"Committee_Id":"C00000935","Committee_Name":"DCCC","Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?_202610239945196723+0","Committee_Election_State":null,"Committee_Election_District":null,"Report_Type":"JULY MONTHLY / SEMI-ANNUAL","Receipt_Date":"23-OCT-26","Coverage_Start_Date":"01-JUN-24","Coverage_End_Date":"30-JUN-24","Quarterly_Contribution":"156100","Semi_Annual_Contribution":"6701907.5"} |
| bundle | {"Committee_Id":"C00000935","Committee_Name":"DCCC","Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?_202610239945196866+0","Committee_Election_State":null,"Committee_Election_District":null,"Report_Type":"JULY MONTHLY / SEMI-ANNUAL","Receipt_Date":"23-OCT-26","Coverage_Start_Date":"01-JUN-26","Coverage_End_Date":"30-JUN-26","Quarterly_Contribution":"472275.5","Semi_Annual_Contribution":"16119375.5"} |
| bundle | {"Committee_Id":"C00939710","Committee_Name":"RICK BRATTIN FOR CONGRESS","Link_Image":"http://docquery.fec.gov/cgi-bin/fecimg/?_202610229940903233+0","Committee_Election_State":null,"Committee_Election_District":null,"Report_Type":"OCTOBER QUARTERLY","Receipt_Date":"22-OCT-26","Coverage_Start_Date":"16-JUL-26","Coverage_End_Date":"30-SEP-26","Quarterly_Contribution":"22523.5","Semi_Annual_Contribution":"0"} |
EXIT 0 2026-11-25T18:37:15Z

## Q2: `leadership2024.csv` against designation `D`

Every one of the file's 833 committees is `D` in 2024's `cm`, and `cm` has 6 `D` committees the
file lacks, $1.7M of receipts: 100% and 99.28%, the bar met for 2024. The file holds both of `cm`'s
leadership-PAC types, `Q` (428) and `N` (405). Q12c applies the bar to every cycle.

```python
# Q2: leadership2024.csv against cm's designation D (silver committee, 2024).
lead(2024)
cmte(2024)
rt(2024)
con.execute("""
    CREATE TABLE q2 AS
    SELECT coalesce(l.cid, c.cid) AS cid, l.cid IS NOT NULL AS in_file,
        c.designation = 'D' AS is_d, c.cid IS NOT NULL AS in_cm, c.designation, c.type,
        coalesce(c.name, l.Committee_Name) AS name, r.receipts
    FROM lead_2024 AS l
    FULL JOIN (SELECT * FROM cmte_2024 WHERE designation = 'D') AS d ON d.cid = l.cid
    LEFT JOIN cmte_2024 AS c ON c.cid = coalesce(l.cid, d.cid)
    LEFT JOIN rt_2024 AS r ON r.committee_id = coalesce(l.cid, d.cid)""")
show("Q2a the file's committees against designation D", """
    SELECT CASE WHEN in_file AND is_d THEN 'in both' WHEN in_file AND in_cm THEN 'file only: cm designates otherwise'
                WHEN in_file THEN 'file only: not in cm' ELSE 'cm D only' END AS side,
        count(*) AS committees, sum(receipts) AS receipts
    FROM q2 GROUP BY 1 ORDER BY 1""")
show("Q2b the decision line: agreement both ways (99% bar)", """
    SELECT count(*) FILTER (WHERE in_file AND is_d) AS both,
        count(*) FILTER (WHERE in_file) AS file_committees,
        count(*) FILTER (WHERE is_d) AS cm_d_committees,
        count(*) FILTER (WHERE in_file AND is_d) / count(*) FILTER (WHERE in_file) AS file_in_d,
        count(*) FILTER (WHERE in_file AND is_d) / count(*) FILTER (WHERE is_d) AS d_in_file
    FROM q2""")
show("Q2c file-only committees by designation and type", """
    SELECT designation, type, count(*) AS committees, sum(receipts) AS receipts
    FROM q2 WHERE in_file AND NOT coalesce(is_d, false) GROUP BY ALL ORDER BY 3 DESC""")
show("Q2d cm-D-only committees by type", """
    SELECT type, count(*) AS committees, sum(receipts) AS receipts, count(receipts) AS with_reported_total
    FROM q2 WHERE NOT in_file AND is_d GROUP BY ALL ORDER BY 2 DESC""")
show("Q2e both sides' differing committees, largest receipts first (30)", """
    SELECT cid, name, in_file, designation, type, receipts FROM q2
    WHERE in_file <> coalesce(is_d, false) ORDER BY receipts DESC NULLS LAST, cid LIMIT 30""")
show("Q2f the file's committees by type (in both)", """
    SELECT type, count(*) AS committees, sum(receipts) AS receipts FROM q2 WHERE in_file AND is_d
    GROUP BY ALL ORDER BY 2 DESC""")
```

Output:

**Q2a the file's committees against designation D  (0 s)**

| side | committees | receipts |
|---|---|---|
| cm D only | 6 | 1,702,151 |
| in both | 833 | 857,006,377 |

**Q2b the decision line: agreement both ways (99% bar)  (0 s)**

| both | file_committees | cm_d_committees | file_in_d | d_in_file |
|---|---|---|---|---|
| 833 | 833 | 839 | 100.00% | 99.28% |

**Q2c file-only committees by designation and type  (0 s)**

| designation | type | committees | receipts |
|---|---|---|---|

**Q2d cm-D-only committees by type  (0 s)**

| type | committees | receipts | with_reported_total |
|---|---|---|---|
| N | 4 | 481,012 | 3 |
| H | 1 | 1,172,163 | 1 |
| Q | 1 | 48,976 | 1 |

**Q2e both sides' differing committees, largest receipts first (30)  (0 s)**

| cid | name | in_file | designation | type | receipts |
|---|---|---|---|---|---|
| C00845065 | SOUTHWEST OHIO LEADERSHIP PAC | False | D | H | 1,172,163 |
| C00768101 | MISSION DEMOCRACY PAC | False | D | N | 475,234 |
| C00855767 | LIBERTY HALL PAC | False | D | Q | 48,976 |
| C00720870 | FOUR TOUR PAC | False | D | N | 5,745 |
| C00207993 | FUND FOR A CONSERVATIVE FUTURE II | False | D | N | 33 |
| C00846964 | THE SOVEREIGN PARTY OF SOVEREIGN NATIONALISTS, KNOWN AS THE PEOPLE PARTY | False | D | N |  |

**Q2f the file's committees by type (in both)  (0 s)**

| type | committees | receipts |
|---|---|---|
| Q | 428 | 329,258,255 |
| N | 405 | 527,748,122 |
EXIT 0 2026-11-25T18:37:18Z

## Q3: `leadership2024.csv`'s figures against `reported_total`

The file's three money figures equal `reported_total`'s within $1 for 99.5–100% of the 814
committees both hold; the 19 `reported_total` lacks are the 19 with a blank coverage end. Four
committees differ, and nearly all the difference is one: Never Surrender's $21.0M in the file
against $495.9M in `reported_total`, which holds its whole cycle, its months as Trump's campaign
included; the other three differ by $5,000 to $206,629 (Q3d). The bar is
met, so the figures are not held (Decision 2).

```python
# Q3: leadership2024.csv's figures against silver reported_total (2024).
lead(2024)
rt(2024)
show("Q3a reported_total's grain", """
    SELECT count(*) AS rows, count(DISTINCT committee_id) AS committees FROM rt_2024""")
con.execute("""
    CREATE TABLE q3 AS
    SELECT l.cid, l.Committee_Name, l.rcpt, l.disb, l.coh, l.cvg_end,
        r.committee_id IS NOT NULL AS in_rt, r.receipts, r.disbursements, r.cash_on_hand_end,
        r.period_end
    FROM lead_2024 AS l LEFT JOIN rt_2024 AS r ON r.committee_id = l.cid""")
show("Q3b each figure: equal within $1, different, absent from one side", """
    WITH f AS (
        SELECT 'receipts' AS figure, rcpt AS file, receipts AS rt, in_rt FROM q3
        UNION ALL SELECT 'disbursements', disb, disbursements, in_rt FROM q3
        UNION ALL SELECT 'cash on hand (end)', coh, cash_on_hand_end, in_rt FROM q3
    )
    SELECT figure,
        count(*) FILTER (WHERE abs(file - rt) <= 1) AS equal_within_1,
        count(*) FILTER (WHERE abs(file - rt) > 1) AS different,
        count(*) FILTER (WHERE file IS NULL AND rt IS NOT NULL) AS file_blank,
        count(*) FILTER (WHERE file IS NOT NULL AND rt IS NULL AND in_rt) AS rt_blank,
        count(*) FILTER (WHERE NOT in_rt) AS no_rt_row,
        count(*) FILTER (WHERE file IS NULL AND rt IS NULL AND in_rt) AS both_blank,
        count(*) FILTER (WHERE abs(file - rt) <= 1)
            / nullif(count(*) FILTER (WHERE file IS NOT NULL AND rt IS NOT NULL), 0) AS equal_share_of_both,
        sum(file - rt) FILTER (WHERE abs(file - rt) > 1) AS net_difference
    FROM f GROUP BY 1 ORDER BY 1""")
show("Q3c coverage end against period_end", """
    SELECT CASE WHEN cvg_end = period_end THEN 'equal' WHEN cvg_end IS NULL AND period_end IS NULL THEN 'both blank'
                WHEN cvg_end IS NULL THEN 'file blank' WHEN period_end IS NULL THEN 'rt blank or absent'
                ELSE 'different' END AS end_date, count(*) AS committees
    FROM q3 GROUP BY 1 ORDER BY 2 DESC""")
show("Q3d the largest receipt differences (15)", """
    SELECT cid, Committee_Name, rcpt, receipts, rcpt - receipts AS diff, cvg_end, period_end
    FROM q3 WHERE abs(rcpt - receipts) > 1 ORDER BY abs(rcpt - receipts) DESC LIMIT 15""")
```

Output:

**Q3a reported_total's grain  (0 s)**

| rows | committees |
|---|---|
| 13,994 | 13,994 |

**Q3b each figure: equal within $1, different, absent from one side  (0 s)**

| figure | equal_within_1 | different | file_blank | rt_blank | no_rt_row | both_blank | equal_share_of_both | net_difference |
|---|---|---|---|---|---|---|---|---|
| cash on hand (end) | 814 | 0 | 0 | 0 | 19 | 0 | 100.00% |  |
| disbursements | 811 | 3 | 0 | 0 | 19 | 0 | 99.63% | -468,201,575 |
| receipts | 810 | 4 | 0 | 0 | 19 | 0 | 99.51% | -475,098,216 |

**Q3c coverage end against period_end  (0 s)**

| end_date | committees |
|---|---|
| equal | 814 |
| both blank | 19 |

**Q3d the largest receipt differences (15)  (0 s)**

| cid | Committee_Name | rcpt | receipts | diff | cvg_end | period_end |
|---|---|---|---|---|---|---|
| C00828541 | NEVER SURRENDER, INC. | 20,981,683 | 495,853,270 | -474,871,587 | 2024-12-31 | 2024-12-31 |
| C00850610 | MR PAC | 7,138 | 213,767 | -206,629 | 2024-12-31 | 2024-12-31 |
| C00692715 | HELP ELECT REPUBLICANS NOW | 289,168 | 304,168 | -15,000 | 2024-12-31 | 2024-12-31 |
| C00836064 | CATAPULT PAC | 5,000 | 10,000 | -5,000 | 2024-12-31 | 2024-12-31 |
EXIT 0 2026-11-25T18:37:21Z

## Q4: sponsors and the name rule (2024)

Rung 1 (the normalized full name) gives 405 of 545 named sponsors one id or one person's several,
rung 2 (last name and first given name) 501; no name holds two people. Rung 2 never takes another
id than rung 1 where both take one (Q4e). It fails where the file adds a title or drops a name
(`GARAMENDI, CONGRESSMAN JOHN`, `TURNER, REP MICHAEL R`, `VELAZQUEZ, M.`), uses a name `cn` does not
(`ROCHESTER, LISA` for Blunt Rochester; `RADEWAGEN, AMATA` for Amata), a nickname or misspelling
(`WYDEN, RON` for Ronald, `FEINSTEIN, DIANE`), or names someone not in the cycle's `cn` (former
members: Engel, Capuano, Fattah): 29 sponsors (Q4g). 41 names match one name under several ids (Q4h); Q14 shows several of those are different
people. 108 of rung 2's ids stand in no race of the cycle: senators not up, and former members
still in `cn` (Q4f).

Q4i–l ask whether a bulk file already carries the sponsor's id. `ccl` links 18 of 2024's 839 `D`
committees to a candidate (designation `D`), and `cm`'s `CAND_ID` is filled on 16. Of the file's
545 named sponsors, 538 have neither, and where they do it is mostly a campaign turned leadership
PAC (Never Surrender, Trump) or wrong: `ccl` links Patriot PAC, Pat Ryan's, to four House
candidates it gave to. So the name is the only bulk statement of a sponsor.

```python
# Q4: sponsors and the name rule (2024), against the cycle's silver candidate.
match(2024)
rt(2024)
show("Q4a named and blank sponsors, with receipts", """
    SELECT l.sponsor IS NOT NULL AS named, count(*) AS committees, sum(r.receipts) AS receipts,
        sum(l.rcpt) AS file_receipts
    FROM lead_2024 AS l LEFT JOIN rt_2024 AS r ON r.committee_id = l.cid GROUP BY 1 ORDER BY 1""")
show("Q4b names holding two people", """
    SELECT cid, sponsor FROM m_2024 WHERE two_people ORDER BY sponsor""")
show("Q4c sponsors with several PACs (by normalized name)", """
    SELECT norm(sponsor) AS sponsor, count(*) AS pacs, string_agg(cid, ', ' ORDER BY cid) AS committees
    FROM m_2024 GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC, 1""")
show("Q4d each rung's classes", """
    SELECT 'rung 1: normalized name' AS rung, r1 AS class, count(*) AS sponsors FROM m_2024 GROUP BY ALL
    UNION ALL
    SELECT 'rung 2: last and first given name', r2, count(*) FROM m_2024 GROUP BY ALL
    ORDER BY 1, 3 DESC""")
show("Q4e rung 1 against rung 2", """
    SELECT r1, r2, count(*) AS sponsors,
        count(*) FILTER (WHERE r1_id = r2_id) AS same_id,
        count(*) FILTER (WHERE r1_id IS NOT NULL AND r2_id IS NOT NULL AND r1_id <> r2_id) AS other_id
    FROM m_2024 GROUP BY ALL ORDER BY 3 DESC""")
show("Q4f each rung's taken id: in a race of the cycle, in candidate with no race, none", """
    WITH t AS (
        SELECT 'rung 1' AS rung, r1_id AS id FROM m_2024 UNION ALL SELECT 'rung 2', r2_id FROM m_2024
    )
    SELECT rung, CASE WHEN t.id IS NULL THEN 'no id' WHEN k.race_id IS NOT NULL THEN 'in a race'
                      ELSE 'no race' END AS standing, count(*) AS sponsors
    FROM t LEFT JOIN cand_2024 AS k ON k.candidate_id = t.id GROUP BY ALL ORDER BY ALL""")
show("Q4g every sponsor rung 2 leaves with no id or several people", """
    SELECT cid, sponsor, r1, r2, r2_ids FROM m_2024 WHERE r2_id IS NULL ORDER BY r2, sponsor""")
show("Q4h every sponsor matched one person under several ids (rung 2)", """
    SELECT m.cid, m.sponsor, m.r2_id, m.r2_ids,
        (SELECT string_agg(k.candidate_id || ' ' || k.office || ' ' || coalesce(k.race_id, '-'), '; ')
         FROM cand_2024 AS k WHERE list_contains(m.r2_ids, k.candidate_id)) AS candidates
    FROM m_2024 AS m WHERE r2 = 'one person, several ids' ORDER BY sponsor""")

# Q4i-l: does a bulk file already carry a leadership PAC's sponsor id (ccl, cm's CAND_ID)?
cmte(2024)
silver("candidate_committee_link", 2024)
show("Q4i ccl links to designation-D committees, and cm's CAND_ID on D committees", """
    SELECT 'ccl link designated D' AS source, count(*) AS links, count(DISTINCT committee_id) AS committees
    FROM silver_2024.candidate_committee_link WHERE designation = 'D'
    UNION ALL
    SELECT 'cm D committee with CAND_ID', count(*), count(DISTINCT cid) FROM cmte_2024
    WHERE designation = 'D' AND nullif(trim(candidate_id), '') IS NOT NULL
    UNION ALL
    SELECT 'cm D committees', count(*), count(DISTINCT cid) FROM cmte_2024 WHERE designation = 'D'""")
con.execute("""
    CREATE TABLE bulk_ids AS
    SELECT committee_id AS cid, candidate_id, 'ccl' AS src FROM silver_2024.candidate_committee_link
    WHERE designation = 'D'
    UNION ALL
    SELECT cid, candidate_id, 'cm' FROM cmte_2024
    WHERE designation = 'D' AND nullif(trim(candidate_id), '') IS NOT NULL""")
show("Q4j the file's named sponsors against the bulk ids (rung 2's ids)", """
    SELECT src, CASE WHEN m.cid IS NULL THEN 'sponsor blank in the file'
                     WHEN list_contains(m.r2_ids, b.candidate_id) THEN 'bulk id is the named sponsor'
                     WHEN m.r2_id IS NULL THEN 'name rule has no id'
                     ELSE 'bulk id is someone else' END AS how,
        count(DISTINCT b.cid) AS committees
    FROM bulk_ids AS b LEFT JOIN m_2024 AS m USING (cid)
    WHERE b.cid IN (SELECT cid FROM lead_2024) GROUP BY ALL ORDER BY ALL""")
show("Q4k named sponsors with no bulk id", """
    SELECT count(*) AS named, count(*) FILTER (WHERE cid NOT IN (SELECT cid FROM bulk_ids)) AS no_bulk_id
    FROM m_2024""")
show("Q4l bulk id is someone else, or blank sponsor with a bulk id", """
    SELECT b.src, b.cid, l.Committee_Name, l.sponsor, b.candidate_id,
        (SELECT name FROM cand_2024 WHERE candidate_id = b.candidate_id) AS bulk_name
    FROM bulk_ids AS b JOIN lead_2024 AS l USING (cid) LEFT JOIN m_2024 AS m USING (cid)
    WHERE m.cid IS NULL OR NOT list_contains(coalesce(m.r2_ids, []), b.candidate_id) ORDER BY 2, 5""")
```

Output:

**Q4a named and blank sponsors, with receipts  (0 s)**

| named | committees | receipts | file_receipts |
|---|---|---|---|
| False | 288 | 683,462,657 | 208,576,070 |
| True | 545 | 173,543,720 | 173,332,093 |

**Q4b names holding two people  (0 s)**

| cid | sponsor |
|---|---|

**Q4c sponsors with several PACs (by normalized name)  (0 s)**

| sponsor | pacs | committees |
|---|---|---|
| MERKLEY JEFFREY | 3 | C00460972, C00605410, C00743641 |
| AGUILAR PETE | 2 | C00573709, C00663609 |
| BROWNLEY JULIA | 2 | C00567495, C00868307 |
| CORNYN JOHN | 2 | C00387464, C00570861 |
| CRAPO MICHAEL | 2 | C00390674, C00544270 |
| DELBENE SUZAN | 2 | C00576090, C00844720 |
| GALLEGO RUBEN | 2 | C00576975, C00892752 |
| GUTHRIE S BRETT | 2 | C00483487, C00879288 |
| JAYAPAL PRAMILA | 2 | C00629576, C00685552 |
| KISTNER TYLER | 2 | C00732925, C00809863 |
| LIEU TED | 2 | C00589309, C00798579 |
| MCCORMICK DAVE | 2 | C00824474, C00851998 |
| SCOTT TIMOTHY E | 2 | C00495887, C00827519 |

**Q4d each rung's classes  (0 s)**

| rung | class | sponsors |
|---|---|---|
| rung 1: normalized name | one | 365 |
| rung 1: normalized name | none | 140 |
| rung 1: normalized name | one person, several ids | 40 |
| rung 2: last and first given name | one | 460 |
| rung 2: last and first given name | one person, several ids | 41 |
| rung 2: last and first given name | none | 29 |
| rung 2: last and first given name | several people | 15 |

**Q4e rung 1 against rung 2  (0 s)**

| r1 | r2 | sponsors | same_id | other_id |
|---|---|---|---|---|
| one | one | 354 | 354 | 0 |
| none | one | 106 | 0 | 0 |
| one person, several ids | one person, several ids | 37 | 37 | 0 |
| none | none | 28 | 0 | 0 |
| one | several people | 10 | 0 | 0 |
| none | one person, several ids | 4 | 0 | 0 |
| one person, several ids | several people | 3 | 0 | 0 |
| none | several people | 2 | 0 | 0 |
| one | none | 1 | 0 | 0 |

**Q4f each rung's taken id: in a race of the cycle, in candidate with no race, none  (0 s)**

| rung | standing | sponsors |
|---|---|---|
| rung 1 | in a race | 331 |
| rung 1 | no id | 140 |
| rung 1 | no race | 74 |
| rung 2 | in a race | 393 |
| rung 2 | no id | 44 |
| rung 2 | no race | 108 |

**Q4g every sponsor rung 2 leaves with no id or several people  (0 s)**

| cid | sponsor | r1 | r2 | r2_ids |
|---|---|---|---|---|
| C00835595 | BARNES, JASON | none | none |  |
| C00804153 | BROWN, SHONTEL | none | none |  |
| C00417295 | CAPUANO, MICHAEL E | none | none |  |
| C00544254 | DUCKWORTH, TAMMY | none | none |  |
| C00639435 | ENGEL, ELIOT | none | none |  |
| C00529834 | FARENTHOLD, RANDOLPH BLAKE | none | none |  |
| C00456913 | FATTAH, CHAKA | none | none |  |
| C00433219 | FEINSTEIN, DIANE | none | none |  |
| C00426494 | FORTENBERRY, JEFFREY | none | none |  |
| C00495705 | GARAMENDI, CONGRESSMAN JOHN | none | none |  |
| C00388934 | GRAHAM, DARLINE | none | none |  |
| C00426965 | GRIJALVA, REP. RAUL M | none | none |  |
| C00862581 | IVEY, GLENN | none | none |  |
| C00687699 | LAWSON, AL | none | none |  |
| C00856849 | MCGUIRE, JOHN | none | none |  |
| C00784868 | MOORE, BARRY | none | none |  |
| C00378356 | MORAN, JR., JAMES P. | one | none |  |
| C00484667 | PAULSEN, ERIK MR. | none | none |  |
| C00571208 | PERDUE, DAVID | none | none |  |
| C00706812 | PINNELL, MATT | none | none |  |
| C00479378 | RADEWAGEN, AMATA | none | none |  |
| C00633156 | ROCHESTER, LISA | none | none |  |
| C00534032 | SALMON, MATT | none | none |  |
| C00821959 | SELF, KEITH | none | none |  |
| C00525030 | SEWELL, TERRYCINA ANDREA | none | none |  |
| C00525238 | TURNER, REP MICHAEL R | none | none |  |
| C00351056 | VELAZQUEZ, M. | none | none |  |
| C00690552 | WILT, ROBIN | none | none |  |
| C00392738 | WYDEN, RON | none | none |  |
| C00776492 | BEN-AVI, TYRRELL | one | several people | ['H2NY13146', 'S2NY00374'] |
| C00640029 | DELANEY, JOHN K. | one person, several ids | several people | ['H2MD06195', 'H4NY08050', 'P00006213'] |
| C00768507 | ELLISON, ALLEN | one person, several ids | several people | ['H0FL17159', 'H2FL23278', 'H4FL17037', 'S2FL00458'] |
| C00499798 | HARTZLER, VICKY | one | several people | ['H0MO04086', 'S2MO00593'] |
| C00497842 | JOHNSON, RON | one | several people | ['H4PA64010', 'S0WI00197'] |
| C00778308 | KELLY, JOHN | none | several people | ['H4CA01116', 'H6MS01131'] |
| C00634774 | KENNEDY, JOHN NEELY | one | several people | ['H4TN06192', 'S4LA00065'] |
| C00631994 | LEWIS, JASON | one | several people | ['H6MN02149', 'S0MN00328'] |
| C00517235 | LUJAN, BEN RAY | one | several people | ['H8NM03196', 'S0NM00058'] |
| C00349233 | MENENDEZ, ROBERT | one | several people | ['H2NJ08232', 'S6NJ00289'] |
| C00847095 | MENENDEZ, ROBERT J. | one | several people | ['H2NJ08232', 'S6NJ00289'] |
| C00641142 | MOONEY, ALEXANDER XAVIER | one | several people | ['H4WV02080', 'S4WV00324'] |
| C00888255 | ONDER, ROBERT | none | several people | ['H4MO03221', 'H8MO09146'] |
| C00850610 | ROGERS, MICHAEL | one person, several ids | several people | ['H2AL03032', 'H4MD03180', 'S4MI00595'] |
| C00697698 | ROSE, JOHN | one | several people | ['H8TN06094', 'S4CA00704', 'S4CA00712'] |

**Q4h every sponsor matched one person under several ids (rung 2)  (0 s)**

| cid | sponsor | r2_id | r2_ids | candidates |
|---|---|---|---|---|
| C00525717 | AMASH, JUSTIN | S4MI00694 | ['H0MI03126', 'S4MI00694'] | H0MI03126 H -; S4MI00694 S 2024-S-MI-00 |
| C00492165 | ANDREWS, ROBERT E. MR. | H0NJ01066 | ['H0NJ01066', 'S8NJ00392'] | H0NJ01066 H -; S8NJ00392 S - |
| C00893487 | BELL, WESLEY | H4MO01134 | ['H4MO01134', 'S4MO00250'] | H4MO01134 H 2024-H-MO-01; S4MO00250 S 2024-S-MO-00 |
| C00409276 | BLACKBURN, MARSHA | S8TN00337 | ['H2TN06030', 'S8TN00337'] | H2TN06030 H -; S8TN00337 S 2024-S-TN-00 |
| C00403675 | CONYERS, JOHN | H2MI13261 | ['H2MI13261', 'H6MI01028'] | H2MI13261 H 2024-H-MI-13; H6MI01028 H - |
| C00691915 | CRAMER, KEVIN | S8ND00120 | ['H0ND01026', 'S8ND00120'] | H0ND01026 H -; S8ND00120 S 2024-S-ND-00 |
| C00654186 | CURTIS, JOHN | H8UT03238 | ['H8UT03238', 'S4UT00282'] | H8UT03238 H 2024-H-UT-03; S4UT00282 S 2024-S-UT-00 |
| C00835579 | DAVIS, WENDY | H4IN03158 | ['H0TX21148', 'H4IN03158'] | H0TX21148 H -; H4IN03158 H 2024-H-IN-03 |
| C00880724 | DOWNING, TROY | H4MT02098 | ['H4MT02098', 'S8MT00218'] | H4MT02098 H 2024-H-MT-02; S8MT00218 S - |
| C00710202 | FINKENAUER, ABBY | S2IA00164 | ['H8IA01094', 'S2IA00164'] | H8IA01094 H -; S2IA00164 S - |
| C00853531 | FRATTO, MARIO | H4NY24115 | ['H2NY23152', 'H4NY24115'] | H2NY23152 H -; H4NY24115 H 2024-H-NY-24 |
| C00892752 | GALLEGO, RUBEN | H4AZ07043 | ['H4AZ07043', 'S4AZ00139'] | H4AZ07043 H 2024-H-AZ-03; S4AZ00139 S 2024-S-AZ-00 |
| C00576975 | GALLEGO, RUBEN | H4AZ07043 | ['H4AZ07043', 'S4AZ00139'] | H4AZ07043 H 2024-H-AZ-03; S4AZ00139 S 2024-S-AZ-00 |
| C00481978 | GRAYSON, ALAN MARK | S2FL00581 | ['H6FL08213', 'S2FL00581', 'S6FL00376'] | H6FL08213 H -; S2FL00581 S 2024-S-FL-00; S6FL00376 S - |
| C00497073 | HEINRICH, MARTIN | S2NM00088 | ['H8NM01224', 'S2NM00088'] | H8NM01224 H -; S2NM00088 S 2024-S-NM-00 |
| C00687582 | HICKENLOOPER, JOHN | S0CO00575 | ['P00010520', 'S0CO00575'] | P00010520 P -; S0CO00575 S - |
| C00774588 | JAMES, JOHN | H2MI10150 | ['H2MI10150', 'S8MI00372'] | H2MI10150 H 2024-H-MI-10; S8MI00372 S - |
| C00784694 | KEAN, THOMAS H. JR. | H0NJ07261 | ['H0NJ07261', 'S6NJ00271'] | H0NJ07261 H 2024-H-NJ-07; S6NJ00271 S - |
| C00878389 | KENNEDY, MIKE | H4UT03260 | ['H4UT03260', 'S8UT00242'] | H4UT03260 H 2024-H-UT-03; S8UT00242 S - |
| C00829879 | KENNEDY, RONDA | H0CA26145 | ['H0CA26145', 'S4NV00247'] | H0CA26145 H 2024-H-CA-30; S4NV00247 S 2024-S-NV-00 |
| C00761957 | KIM, ANDY | H8NJ03206 | ['H8NJ03206', 'S4NJ00466'] | H8NJ03206 H 2024-H-NJ-03; S4NJ00466 S 2024-S-NJ-00 |
| C00672667 | LAMB, CONOR | H8PA18181 | ['H8PA18181', 'S2PA00562'] | H8PA18181 H -; S2PA00562 S - |
| C00798405 | MASTERS, BLAKE | H4AZ08124 | ['H4AZ08124', 'S2AZ00372'] | H4AZ08124 H 2024-H-AZ-08; S2AZ00372 S - |
| C00773853 | MEIJER, PETER | S4MI00637 | ['H0MI03308', 'S4MI00637'] | H0MI03308 H -; S4MI00637 S 2024-S-MI-00 |
| C00459925 | MURPHY, CHRISTOPHER | S2CT00132 | ['S2CT00132', 'S4MO00235'] | S2CT00132 S 2024-S-CT-00; S4MO00235 S 2024-S-MO-00 |
| C00507574 | PETERS, GARY | S4MI00355 | ['H8MI09068', 'S4MI00355'] | H8MI09068 H -; S4MI00355 S - |
| C00512855 | ROKITA, THEODORE | H0IN04170 | ['H0IN04170', 'S8IN00189'] | H0IN04170 H -; S8IN00189 S - |
| C00654475 | ROSEN, JACKY | S8NV00156 | ['H6NV03139', 'S8NV00156'] | H6NV03139 H -; S8NV00156 S 2024-S-NV-00 |
| C00764431 | ROSENDALE, MATT | H4MT00050 | ['H4MT00050', 'S8MT00234'] | H4MT00050 H 2024-H-MT-02; S8MT00234 S 2024-S-MT-00 |
| C00569871 | RUIZ, RAUL | H2CA36439 | ['H0CA36177', 'H2CA36439'] | H2CA36439 H 2024-H-CA-25; H0CA36177 H - |
| C00406553 | SANDERS, BERNARD | P40019242 | ['P40019242', 'P60007168', 'S4VT00033'] | P40019242 P 2024-P-US-00; P60007168 P -; S4VT00033 S 2024-S-VT-00 |
| C00846477 | SAPRAICONE, MICHAEL | H4NY03184 | ['H4NY03184', 'S4NY00404'] | H4NY03184 H 2024-H-NY-03; S4NY00404 S 2024-S-NY-00 |
| C00422774 | SCHIFF, ADAM | H0CA27085 | ['H0CA27085', 'S4CA00555'] | H0CA27085 H 2024-H-CA-30; S4CA00555 S 2024-S-CA-00 |
| C00495887 | SCOTT, TIMOTHY E. | P40012155 | ['P40012155', 'S4SC00240'] | P40012155 P 2024-P-US-00; S4SC00240 S - |
| C00827519 | SCOTT, TIMOTHY E. | P40012155 | ['P40012155', 'S4SC00240'] | P40012155 P 2024-P-US-00; S4SC00240 S - |
| C00461996 | SIMPSON, MICHAEL K | H4SC06155 | ['H4SC06155', 'H8ID02064'] | H4SC06155 H 2024-H-SC-06; H8ID02064 H 2024-H-ID-02 |
| C00571182 | SINEMA, KYRSTEN | S8AZ00197 | ['H2AZ09019', 'S8AZ00197'] | H2AZ09019 H -; S8AZ00197 S 2024-S-AZ-00 |
| C00832147 | SLOTKIN, ELISSA | H8MI08102 | ['H8MI08102', 'S4MI00470'] | H8MI08102 H 2024-H-MI-07; S4MI00470 S 2024-S-MI-00 |
| C00780262 | SMILEY, TIFFANY | H4WA04179 | ['H4WA04179', 'S2WA00387'] | H4WA04179 H 2024-H-WA-04; S2WA00387 S - |
| C00571000 | SULLIVAN, DAN | H2MA09254 | ['H2MA09254', 'S4AK00214'] | H2MA09254 H 2024-H-MA-09; S4AK00214 S - |
| C00615492 | WALKER, BRADLEY MARK | H4NC06052 | ['H4NC06052', 'S2NC00307'] | H4NC06052 H 2024-H-NC-06; S2NC00307 S - |

**Q4i ccl links to designation-D committees, and cm's CAND_ID on D committees  (0 s)**

| source | links | committees |
|---|---|---|
| ccl link designated D | 22 | 18 |
| cm D committee with CAND_ID | 16 | 16 |
| cm D committees | 839 | 839 |

**Q4j the file's named sponsors against the bulk ids (rung 2's ids)  (0 s)**

| src | how | committees |
|---|---|---|
| ccl | bulk id is someone else | 1 |
| ccl | bulk id is the named sponsor | 7 |
| ccl | sponsor blank in the file | 4 |
| cm | bulk id is someone else | 1 |
| cm | bulk id is the named sponsor | 6 |
| cm | sponsor blank in the file | 4 |

**Q4k named sponsors with no bulk id  (0 s)**

| named | no_bulk_id |
|---|---|
| 545 | 538 |

**Q4l bulk id is someone else, or blank sponsor with a bulk id  (0 s)**

| src | cid | Committee_Name | sponsor | candidate_id | bulk_name |
|---|---|---|---|---|---|
| ccl | C00398750 | FREEDOM FOR AMERICA (FFA PAC) |  | H8CA20059 | NUNES, DEVIN G. |
| cm | C00398750 | FREEDOM FOR AMERICA (FFA PAC) |  | H8CA20059 | NUNES, DEVIN G. |
| ccl | C00818328 | PAC FOR NEW LEADERSHIP |  | H2CA03157 | KILEY, KEVIN |
| cm | C00818328 | PAC FOR NEW LEADERSHIP |  | H2CA03157 | KILEY, KEVIN |
| ccl | C00828541 | NEVER SURRENDER, INC. |  | P80001571 | TRUMP, DONALD J. |
| cm | C00828541 | NEVER SURRENDER, INC. |  | P80001571 | TRUMP, DONALD J. |
| ccl | C00832576 | PATRIOT PAC | RYAN, PATRICK | H2CA47188 | GARCIA, ROBERT |
| cm | C00832576 | PATRIOT PAC | RYAN, PATRICK | H2CA47188 | GARCIA, ROBERT |
| ccl | C00832576 | PATRIOT PAC | RYAN, PATRICK | H2CO03351 | FRISCH, ADAM |
| ccl | C00832576 | PATRIOT PAC | RYAN, PATRICK | H4CA47119 | WEISS, JOANNA |
| ccl | C00832576 | PATRIOT PAC | RYAN, PATRICK | H4NY22085 | MANNION, JOHN W |
| ccl | C00885319 | COLORADO WESTERN POLITICAL ACTION COMMITTEE |  | H4CO03357 | HURD, JEFFREY |
| cm | C00885319 | COLORADO WESTERN POLITICAL ACTION COMMITTEE |  | H4CO03357 | HURD, JEFFREY |
EXIT 0 2026-11-25T18:37:24Z

## Q5: the check against OpenFEC (2024)

OpenFEC holds all 833 of the file's committees, 801 of them still `D` today and 30 `U` (Q5a). By
id, rung 2's matches agree at 99.19% (489 of 493), rung 1's at 98.49%. The four rung-2
disagreements are each the same person under an id OpenFEC prefers: Sherrod Brown's and Pete
Ricketts's later Senate ids, Haley Stevens's 2026 Senate id, Marlin Stutzman's 2024 House id (Q5d).
43 sponsors rung 2 links to nobody are named by OpenFEC (`rule none`), and 9 PACs OpenFEC names no
sponsor for (Q5b).

**Blank sponsors.** OpenFEC names a sponsor for 242 of the 288 blank rows, 84%, holding
$198,817,151 of their file receipts: Save America (Trump, $99.7M), Never Surrender (Trump), Jobs,
Freedom and Security PAC (Cruz), Heartland Values (Thune), MC PAC (McCarthy), Mr. Southern
Missourian (Jason Smith), Eye of the Tiger (Scalise), Bluegrass (McConnell) (Q5f–g). That is over
the spec's 10% line, so it went to the checkpoint, which filled them (Decision 4). Ten PACs have
two or three sponsors in OpenFEC, nearly all one person's House and Senate ids; two are two people
(Graham, Darline and Lindsey; Letlow, Luke and Julia) (Q5e). OpenFEC lists 14 `D` committees for
2024 the file lacks: the 6 `cm` designates `D` (Q2d) and 8 it designates `P` or `U` (Q5i).

```python
# Q5: the check (2024): OpenFEC's sponsor_candidate_ids per leadership PAC against the rule.
agree(2024)
show("Q5a OpenFEC's answer for the file's committees", """
    SELECT o_found, o_dsgn, sponsor IS NOT NULL AS named, len(o_ids) AS openfec_sponsors,
        count(*) AS committees
    FROM a_2024 GROUP BY ALL ORDER BY ALL""")
show("Q5b each rung against OpenFEC (named sponsors)", """
    SELECT 'rung 1' AS rung, a1 AS against_openfec, count(*) AS sponsors, sum(rcpt) AS file_receipts
    FROM a_2024 WHERE sponsor IS NOT NULL GROUP BY ALL
    UNION ALL
    SELECT 'rung 2', a2, count(*), sum(rcpt) FROM a_2024 WHERE sponsor IS NOT NULL GROUP BY ALL
    ORDER BY 1, 3 DESC""")
show("Q5c the decision line: each rung's matches that agree with OpenFEC (99% bar)", """
    SELECT 'rung 1' AS rung,
        count(*) FILTER (WHERE a1 IN ('agree', 'same person')) AS agree,
        count(*) FILTER (WHERE a1 = 'disagree') AS disagree,
        count(*) FILTER (WHERE a1 IN ('agree', 'same person'))
            / nullif(count(*) FILTER (WHERE a1 IN ('agree', 'same person', 'disagree')), 0) AS agreement,
        count(*) FILTER (WHERE a1 = 'rule none') AS rule_none_openfec_names
    FROM a_2024
    UNION ALL
    SELECT 'rung 2',
        count(*) FILTER (WHERE a2 IN ('agree', 'same person')),
        count(*) FILTER (WHERE a2 = 'disagree'),
        count(*) FILTER (WHERE a2 IN ('agree', 'same person'))
            / nullif(count(*) FILTER (WHERE a2 IN ('agree', 'same person', 'disagree')), 0),
        count(*) FILTER (WHERE a2 = 'rule none')
    FROM a_2024""")
show("Q5d every disagreement, either rung", """
    SELECT cid, sponsor, r1_id, r2_id, o_ids, o_names FROM a_2024
    WHERE 'disagree' IN (a1, a2) ORDER BY sponsor""")
show("Q5e PACs OpenFEC gives several sponsors", """
    SELECT cid, name, sponsor, o_ids, o_names FROM a_2024 WHERE len(o_ids) > 1 ORDER BY cid""")
show("Q5f blank-sponsor PACs OpenFEC names a sponsor for: count and share of the blanks (10% line)", """
    SELECT count(*) FILTER (WHERE len(o_ids) > 0) AS openfec_names, count(*) AS blanks,
        count(*) FILTER (WHERE len(o_ids) > 0) / count(*) AS share,
        sum(rcpt) FILTER (WHERE len(o_ids) > 0) AS their_file_receipts
    FROM a_2024 WHERE sponsor IS NULL""")
show("Q5g those blank-sponsor PACs, largest receipts first (25)", """
    SELECT cid, name, rcpt, o_ids, o_names FROM a_2024 WHERE sponsor IS NULL AND len(o_ids) > 0
    ORDER BY rcpt DESC NULLS LAST LIMIT 25""")
cmte(2024)
show("Q5i OpenFEC's D committees for 2024 that the file lacks", """
    SELECT o.cid, o.o_ids, o.o_names, c.designation AS cm_designation
    FROM of_2024 AS o LEFT JOIN cmte_2024 AS c USING (cid)
    WHERE o.o_dsgn = 'D' AND o.cid NOT IN (SELECT cid FROM lead_2024) ORDER BY o.cid""")
```

Output:

**Q5a OpenFEC's answer for the file's committees  (0 s)**

| o_found | o_dsgn | named | openfec_sponsors | committees |
|---|---|---|---|---|
| True | B | False | 1 | 1 |
| True | D | False | 0 | 36 |
| True | D | False | 1 | 235 |
| True | D | False | 2 | 2 |
| True | D | True | 0 | 3 |
| True | D | True | 1 | 518 |
| True | D | True | 2 | 6 |
| True | D | True | 3 | 1 |
| True | J | False | 0 | 1 |
| True | U | False | 0 | 9 |
| True | U | False | 1 | 4 |
| True | U | True | 0 | 6 |
| True | U | True | 1 | 10 |
| True | U | True | 2 | 1 |

**Q5b each rung against OpenFEC (named sponsors)  (0 s)**

| rung | against_openfec | sponsors | file_receipts |
|---|---|---|---|
| rung 1 | agree | 375 | 123,554,507 |
| rung 1 | rule none | 139 | 40,137,689 |
| rung 1 | same person | 16 | 2,650,264 |
| rung 1 | OpenFEC none | 9 | 3,922,838 |
| rung 1 | disagree | 6 | 3,066,795 |
| rung 2 | agree | 472 | 148,088,829 |
| rung 2 | rule none | 43 | 15,905,235 |
| rung 2 | same person | 17 | 2,795,264 |
| rung 2 | OpenFEC none | 9 | 3,922,838 |
| rung 2 | disagree | 4 | 2,619,928 |

**Q5c the decision line: each rung's matches that agree with OpenFEC (99% bar)  (0 s)**

| rung | agree | disagree | agreement | rule_none_openfec_names |
|---|---|---|---|---|
| rung 1 | 391 | 6 | 98.49% | 139 |
| rung 2 | 489 | 4 | 99.19% | 43 |

**Q5d every disagreement, either rung  (0 s)**

| cid | sponsor | r1_id | r2_id | o_ids | o_names |
|---|---|---|---|---|---|
| C00331694 | BROWN, SHERROD | S6OH00163 | S6OH00163 | ['S6OH00379'] |  |
| C00497842 | JOHNSON, RON | H4PA64010 |  | ['S0WI00197'] | JOHNSON, RON HAROLD MR. |
| C00832501 | RICKETTS, PETE | S6NE00129 | S6NE00129 | ['S4NE00173'] |  |
| C00850610 | ROGERS, MICHAEL | H2AL03032 |  | ['S4MI00595'] | ROGERS, MICHAEL J |
| C00697698 | ROSE, JOHN | S4CA00704 |  | ['H8TN06094'] | ROSE, JOHN W. |
| C00746735 | STEVENS, HALEY | H8MI11254 | H8MI11254 | ['S6MI00426'] | STEVENS, HALEY |
| C00838128 | STUTZMAN, MARLIN |  | H0IN03198 | ['H4IN03174'] |  |

**Q5e PACs OpenFEC gives several sponsors  (0 s)**

| cid | name | sponsor | o_ids | o_names |
|---|---|---|---|---|
| C00388934 | FUND FOR AMERICA'S FUTURE | GRAHAM, DARLINE | ['S0SC00149', 'S6SC04437'] | GRAHAM, DARLINE\|GRAHAM, LINDSEY O. |
| C00633156 | I GOT YOUR BACK PAC | ROCHESTER, LISA | ['H6DE00206', 'S4DE00060'] | BLUNT ROCHESTER, LISA\|BLUNT ROCHESTER, LISA |
| C00638130 | COWBOY PAC |  | ['H6WY00159', 'S4WY00089'] | CHENEY, ELIZABETH MRS.\|CHENEY, ELIZABETH (LIZ) |
| C00672667 | GOOD DAY PAC | LAMB, CONOR | ['H8PA18181', 'S2PA00562'] | LAMB, CONOR\|LAMB, CONOR |
| C00710202 | SPARK PAC | FINKENAUER, ABBY | ['H8IA01094', 'S2IA00164'] | FINKENAUER, ABBY\|FINKENAUER, ABBY |
| C00764761 | START RISING PAC | LETLOW, JULIA | ['H0LA05120', 'H2LA05126', 'S6LA00664'] | LETLOW, LUKE JOSHUA\|LETLOW, JULIA\|LETLOW, JULIA |
| C00802595 | OVERHAUL PAC | COLLINS, MICHAEL | ['H4GA10071', 'S6GA00390'] | COLLINS, MICHAEL A JR\|COLLINS, MICHAEL A JR |
| C00821959 | ALL AMERICAN PAC | SELF, KEITH | ['H2TX00064', 'H2TX03290'] | SELF, KEITH ALAN |
| C00839662 | COYOTE PAC |  | ['H2NC14019', 'S6NC00340'] | NICKEL, WILEY\|NICKEL, WILEY |
| C00862581 | HIGHER GROUND PAC | IVEY, GLENN | ['H2MD04232', 'H2MD04315'] | IVEY, GLENN FREDERICK |

**Q5f blank-sponsor PACs OpenFEC names a sponsor for: count and share of the blanks (10% line)  (0 s)**

| openfec_names | blanks | share | their_file_receipts |
|---|---|---|---|
| 242 | 288 | 84.03% | 198,817,151 |

**Q5g those blank-sponsor PACs, largest receipts first (25)  (0 s)**

| cid | name | rcpt | o_ids | o_names |
|---|---|---|---|---|
| C00762591 | SAVE AMERICA | 99,719,703 | ['P80001571'] | TRUMP, DONALD J. |
| C00828541 | NEVER SURRENDER, INC. | 20,981,683 | ['P80001571'] | TRUMP, DONALD J. |
| C00536540 | JOBS, FREEDOM, AND SECURITY PAC | 3,479,994 | ['S2TX00312'] | CRUZ, RAFAEL EDWARD  TED |
| C00409003 | HEARTLAND VALUES PAC | 3,376,658 | ['S2SD00068'] | THUNE, JOHN R. |
| C00428052 | MAJORITY COMMITTEE PAC--MC PAC | 2,756,607 | ['H6CA22125'] | MCCARTHY, KEVIN |
| C00563726 | MR. SOUTHERN MISSOURIAN IN THE HOUSE PAC | 2,588,921 | ['H4MO08162'] | SMITH, JASON T |
| C00592089 | ELECTING MAJORITY MAKING EFFECTIVE REPUBLICANS PAC | 2,079,972 | ['H4MN06087'] | EMMER, THOMAS EARL JR. |
| C00467431 | THE EYE OF THE TIGER POLITICAL ACTION COMMITTEE | 2,063,973 | ['H0LA01087'] | SCALISE, STEVE MR |
| C00571323 | TOGETHER HOLDING OUR MAJORITY PAC | 1,728,042 | ['S4NC00162'] | TILLIS, THOM R SEN |
| C00542027 | BIG SKY OPPORTUNITY PAC | 1,507,448 | ['S2MT00096'] | DAINES, STEVE |
| C00296640 | REPUBLICAN MAJORITY FUND | 1,367,901 | ['S4AR00103'] | COTTON, THOMAS |
| C00491654 | CITIZENS FOR PROSPERITY IN AMERICA TODAY PAC | 1,336,295 | ['S4PA00121'] | TOOMEY, PATRICK JOSEPH |
| C00719971 | SENATE EAGLE PAC | 1,312,902 | ['S0TN00169'] | HAGERTY, BILL |
| C00844639 | DEMOCRATIC TURNOUT PROJECT PAC | 1,301,646 | ['H0NH02181'] | KUSTER, ANN MCLANE |
| C00235655 | BLUEGRASS COMMITTEE | 1,296,929 | ['S2KY00012'] | MCCONNELL, MITCH |
| C00567545 | BOOTS POLITICAL ACTION COMMITTEE | 1,291,328 | ['S2OK00186'] | MULLIN, MARKWAYNE |
| C00426809 | MADISON PAC; THE | 1,272,549 | ['H8MA02041'] | NEAL, RICHARD E |
| C00540187 | INNOVATION POLITICAL ACTION COMMITTEE | 1,260,703 | ['H4NC10047'] | MCHENRY, PATRICK TIMOTHY |
| C00571174 | SERVE AMERICA PAC | 1,248,264 | ['H4MA06090'] | MOULTON, SETH |
| C00572271 | BUILDING AMERICA'S REPUBLICAN REPRESENTATION PAC | 1,244,415 | ['H0KY06104'] | BARR, GARLAND ANDY |
| C00551853 | OORAH! POLITICAL ACTION COMMITTEE | 1,228,314 | ['S6IN00191'] | YOUNG, TODD CHRISTOPHER |
| C00623512 | IN THE ARENA PAC | 1,208,580 | ['H4AR02141'] | HILL, JAMES FRENCH |
| C00391797 | DIRIGO PAC | 1,197,764 | ['S6ME00159'] | COLLINS, SUSAN M. |
| C00826362 | WINNING FOR AMERICA PAC | 1,188,401 | ['S2MO00544'] | SCHMITT, ERIC |
| C00540146 | FIRST IN FREEDOM PAC | 1,132,836 | ['H2NC08185'] | HUDSON, RICHARD L. JR. |

**Q5i OpenFEC's D committees for 2024 that the file lacks  (0 s)**

| cid | o_ids | o_names | cm_designation |
|---|---|---|---|
| C00083337 | [] |  | U |
| C00207993 | ['S4OK00083'] | INHOFE, JAMES M. SEN. | D |
| C00558437 | ['H4NJ12149'] | COLEMAN, BONNIE WATSON | P |
| C00611400 | ['H4WA04104'] | NEWHOUSE, DAN | U |
| C00708289 | ['H0GA06192'] | GREENE, MARJORIE TAYLOR | P |
| C00720870 | ['H0WA08103'] | JENSEN, JESSE | D |
| C00764415 | ['H0FL13158'] | PAULINA LUNA, ANNA | U |
| C00768101 | ['H2GA14044'] | FLOWERS, MARCUS | D |
| C00768689 | ['H2CT02161'] | FRANCE, MIKE | P |
| C00778159 | ['H4MT01041'] | ZINKE, RYAN K | P |
| C00845065 | [] |  | D |
| C00846964 | ['S6GA00275'] | MCCORMICK, DAVE | D |
| C00855767 | [] |  | D |
| C00890921 | ['H6WY01116'] | RASNER, REID | P |
EXIT 0 2026-11-25T18:37:27Z

## Q6: leadership PACs and the credit rule (2024)

Six leadership PACs are credited to a candidate by `04_contribution.sql`'s `linked` rule, each as
the committee `cn` names principal: Never Surrender ($495,853,270, Trump's campaign until it
became his leadership PAC), and five small ones ($531,455 in all), two of them to their own
sponsor. The rule already documents why: FEC's files show a committee as it stands today, and the
money was raised as the campaign. So the milestone's contract (a leadership PAC's money stays the
PAC's) holds for every committee that was a leadership PAC throughout the cycle; no change.

```python
# Q6: leadership PACs and the credit rule (2024): does 04_contribution.sql's `linked` rule credit
# any leadership PAC to a candidate (a ccl P or A link, or a principal_committee_id)?
match(2024)
cmte(2024)
rt(2024)
silver("candidate_committee_link", 2024)
con.execute("""
    CREATE TABLE q6 AS
    WITH pacs AS (
        SELECT cid, 'file' AS how FROM lead_2024
        UNION SELECT cid, 'cm D' FROM cmte_2024 WHERE designation = 'D'
    ),
    credited AS (
        SELECT link.committee_id AS cid, link.candidate_id, link.designation AS link_dsgn,
            link.committee_id = k.principal_committee_id AS is_principal
        FROM silver_2024.candidate_committee_link AS link
        LEFT JOIN silver_2024.candidate AS k USING (candidate_id)
        WHERE link.designation IN ('P', 'A') OR link.committee_id = k.principal_committee_id
    )
    SELECT p.cid, string_agg(DISTINCT p.how, '+') AS how, c.candidate_id, c.link_dsgn, c.is_principal,
        any_value(m.sponsor) AS sponsor, any_value(m.r2_ids) AS sponsor_ids,
        list_contains(any_value(m.r2_ids), c.candidate_id) AS credited_is_sponsor,
        any_value(r.receipts) AS receipts
    FROM pacs AS p JOIN credited AS c USING (cid)
    LEFT JOIN m_2024 AS m USING (cid)
    LEFT JOIN rt_2024 AS r ON r.committee_id = p.cid
    GROUP BY p.cid, c.candidate_id, c.link_dsgn, c.is_principal""")
show("Q6a leadership PACs the linked rule credits to a candidate", """
    SELECT how, link_dsgn, is_principal, credited_is_sponsor, count(DISTINCT cid) AS pacs,
        sum(receipts) AS receipts
    FROM q6 GROUP BY ALL ORDER BY ALL""")
show("Q6b each of them", """
    SELECT cid, how, candidate_id, link_dsgn, is_principal, sponsor, credited_is_sponsor, receipts
    FROM q6 ORDER BY receipts DESC NULLS LAST, cid""")
```

Output:

**Q6a leadership PACs the linked rule credits to a candidate  (0 s)**

| how | link_dsgn | is_principal | credited_is_sponsor | pacs | receipts |
|---|---|---|---|---|---|
| cm D | D | True |  | 3 | 481,012 |
| cm D+file | D | True | True | 1 | 37,304 |
| file+cm D | D | True | True | 1 | 13,139 |
| file+cm D | D | True |  | 1 | 495,853,270 |

**Q6b each of them  (0 s)**

| cid | how | candidate_id | link_dsgn | is_principal | sponsor | credited_is_sponsor | receipts |
|---|---|---|---|---|---|---|---|
| C00828541 | file+cm D | P80001571 | D | True |  |  | 495,853,270 |
| C00768101 | cm D | H2GA14044 | D | True |  |  | 475,234 |
| C00732958 | cm D+file | H0NC11233 | D | True | CAWTHORN, DAVID MADISON | True | 37,304 |
| C00732925 | file+cm D | H0MN02134 | D | True | KISTNER, TYLER | True | 13,139 |
| C00720870 | cm D | H0WA08103 | D | True |  |  | 5,745 |
| C00207993 | cm D | S4OK00083 | D | True |  |  | 33 |
EXIT 0 2026-11-25T18:37:30Z

## Q7: `lobbyist.csv`

`lobbyist.csv` is a history of declarations: 1,931 of 2,774 committees filed more than one Form 1,
up to 26, and 561 changed their answer, 444 of them from blank to `Y` (Q7a, Q7c). It is dated
from 2009, so it can flag cycles from 2010. 14 committees (24 rows) are in no cycle's committee
table (Q7e).

Against `cm`'s `B`, rule b (the latest filing by the cycle's end is `Y`) finds more of its committees
`B` than rule a (any `Y` by then) in every cycle, but neither meets the bar in any (Q7f). Rule b
finds 94.5–98.8% of its committees `B`; the rest are mostly `U` PACs (2024: 14 `Q`, 3 `N`) and one leadership PAC
(Q7g). The other way is worse: `cm` designates 26 to 445 committees a cycle `B` that never filed a
Form 1 with the box ticked: 80 in 2024, none of them in the file at all, mostly super PACs (`O`),
hybrid PACs (`V`, `W`) and union and trade PACs (Q7h–i); 2012 and 2014 have 445 and 409. The file
committees not in that cycle's `cm` (about 600 to 1,200 a cycle from 2016) are terminated committees whose last
answer stays `Y`; rule b is compared only over committees in the cycle's `cm`. The checkpoint made
the file, under rule b, the flag's source (Decision 6).

The file cannot show what a blank box means; it is read as unticked (asserted, not measured: §3's
fifth asserted fact stands unconfirmed). Rule b's `arg_max(y, (filed, rn))` breaks a tie on the
latest filing day by file order; §7.2 breaks it by the higher image number. Two committees have
such a tie with different answers, and in both the higher image number is ticked (C00396812,
C00640573; read from the file on 2026-11-25), so the two can differ by those two committees.

```python
# Q7: lobbyist.csv: grain, Is_Lobbyist over time, and two per-cycle rules against cm's B.
lob()
allcmte()
show("Q7a rows per committee", """
    SELECT CASE WHEN n = 1 THEN '1' WHEN n <= 5 THEN '2-5' WHEN n <= 10 THEN '6-10' WHEN n <= 15 THEN '11-15'
                ELSE '16+' END AS rows_per_committee, count(*) AS committees, max(n) AS max_rows
    FROM (SELECT cid, count(*) AS n FROM lob GROUP BY 1) GROUP BY 1 ORDER BY 1""")
show("Q7b Is_Lobbyist by filing year", """
    SELECT year(filed) AS year, count(*) FILTER (WHERE y) AS y_rows, count(*) FILTER (WHERE NOT y) AS blank_rows,
        count(DISTINCT cid) AS committees
    FROM lob GROUP BY 1 ORDER BY 1""")
con.execute("""
    CREATE TABLE lob_seq AS
    SELECT cid, string_agg(CASE WHEN y THEN 'Y' ELSE '-' END, '' ORDER BY filed, rn) AS seq, count(*) AS n
    FROM lob GROUP BY 1""")
show("Q7c committees whose value changes over time, by pattern", """
    SELECT CASE WHEN seq NOT LIKE '%-%' THEN 'always Y' WHEN seq NOT LIKE '%Y%' THEN 'always blank'
                WHEN regexp_matches(seq, '^Y+-+$') THEN 'Y then blank'
                WHEN regexp_matches(seq, '^-+Y+$') THEN 'blank then Y'
                ELSE 'changes more than once' END AS pattern,
        count(*) AS committees
    FROM lob_seq GROUP BY 1 ORDER BY 2 DESC""")
show("Q7d the same filing (Link_Image) on several rows", """
    SELECT count(*) AS images_on_several_rows, sum(n) AS their_rows
    FROM (SELECT Link_Image, count(*) AS n FROM lob GROUP BY 1 HAVING count(*) > 1)""")
show("Q7e the file's committees in no cycle's committee table, 2010-2026", """
    SELECT count(DISTINCT cid) AS committees, count(*) AS rows FROM lob
    WHERE cid NOT IN (SELECT cid FROM allcmte)""")
rules = {
    "a: any Y filed by the cycle end": "bool_or(y)",
    "b: latest filing by the cycle end is Y": "arg_max(y, (filed, rn))",
}
parts = []
for c in CYCLES:
    for label, agg in rules.items():
        parts.append(f"""
        SELECT {c} AS cycle, '{label}' AS rule, f.cid AS fcid, b.cid AS bcid, x.cid IS NOT NULL AS in_cm,
            x.designation, x.type
        FROM (SELECT cid FROM lob WHERE filed <= DATE '{c}-12-31' GROUP BY cid HAVING {agg}) AS f
        FULL JOIN (SELECT cid FROM cmte_{c} WHERE designation = 'B') AS b ON b.cid = f.cid
        LEFT JOIN cmte_{c} AS x ON x.cid = coalesce(f.cid, b.cid)""")
con.execute("CREATE TABLE q7 AS " + " UNION ALL ".join(parts))
show("Q7f the decision line: each rule against designation B, per cycle (99% bar both ways)", """
    SELECT cycle, rule,
        count(*) FILTER (WHERE fcid IS NOT NULL AND bcid IS NOT NULL) AS both,
        count(*) FILTER (WHERE fcid IS NOT NULL AND bcid IS NULL AND in_cm) AS file_only_in_cm,
        count(*) FILTER (WHERE fcid IS NOT NULL AND NOT in_cm) AS file_only_not_in_cm,
        count(*) FILTER (WHERE fcid IS NULL) AS cm_b_only,
        count(*) FILTER (WHERE fcid IS NOT NULL AND bcid IS NOT NULL)
            / nullif(count(*) FILTER (WHERE fcid IS NOT NULL AND in_cm), 0) AS file_in_b,
        count(*) FILTER (WHERE fcid IS NOT NULL AND bcid IS NOT NULL)
            / nullif(count(*) FILTER (WHERE bcid IS NOT NULL), 0) AS b_in_file
    FROM q7 GROUP BY ALL ORDER BY rule, cycle""")
show("Q7g file-only committees (in cm) by designation and type, 2024, rule b", """
    SELECT designation, type, count(*) AS committees FROM q7
    WHERE cycle = 2024 AND rule LIKE 'b%' AND fcid IS NOT NULL AND bcid IS NULL AND in_cm
    GROUP BY ALL ORDER BY 3 DESC""")
show("Q7h cm-B-only committees, 2024: in the file at all, and their latest value", """
    SELECT s.cid IS NOT NULL AS in_file, right(s.seq, 1) AS latest, count(*) AS committees
    FROM q7 LEFT JOIN lob_seq AS s ON s.cid = q7.bcid
    WHERE cycle = 2024 AND rule LIKE 'b%' AND fcid IS NULL GROUP BY ALL ORDER BY ALL""")
show("Q7i file-only and cm-only committees, 2024, rule b (40)", """
    SELECT coalesce(fcid, bcid) AS cid, fcid IS NOT NULL AS in_file_rule, designation, type,
        s.seq, (SELECT name FROM cmte_2024 WHERE cid = coalesce(fcid, bcid)) AS name
    FROM q7 LEFT JOIN lob_seq AS s ON s.cid = coalesce(fcid, bcid)
    WHERE cycle = 2024 AND rule LIKE 'b%' AND (fcid IS NULL OR (bcid IS NULL AND in_cm))
    ORDER BY in_file_rule, cid LIMIT 40""")
show("Q7j the designation B committees that are also leadership PACs in leadership2024.csv", """
    SELECT count(*) AS committees FROM cmte_2024 WHERE designation = 'B'
        AND cid IN (SELECT cid FROM lead_2024)""") if lead(2024) else None
```

Output:

**Q7a rows per committee  (0 s)**

| rows_per_committee | committees | max_rows |
|---|---|---|
| 1 | 843 | 1 |
| 11-15 | 272 | 15 |
| 16+ | 82 | 26 |
| 2-5 | 851 | 5 |
| 6-10 | 726 | 10 |

**Q7b Is_Lobbyist by filing year  (0 s)**

| year | y_rows | blank_rows | committees |
|---|---|---|---|
| 2009 | 1,477 | 172 | 1,146 |
| 2010 | 517 | 185 | 496 |
| 2011 | 664 | 145 | 586 |
| 2012 | 1,022 | 132 | 962 |
| 2013 | 568 | 125 | 508 |
| 2014 | 562 | 100 | 507 |
| 2015 | 785 | 97 | 663 |
| 2016 | 629 | 83 | 519 |
| 2017 | 537 | 80 | 464 |
| 2018 | 698 | 98 | 592 |
| 2019 | 707 | 98 | 590 |
| 2020 | 572 | 65 | 491 |
| 2021 | 651 | 64 | 528 |
| 2022 | 650 | 52 | 548 |
| 2023 | 617 | 32 | 514 |
| 2024 | 654 | 47 | 528 |
| 2025 | 606 | 26 | 490 |
| 2026 | 654 | 15 | 520 |

**Q7c committees whose value changes over time, by pattern  (0 s)**

| pattern | committees |
|---|---|
| always Y | 2,213 |
| blank then Y | 444 |
| Y then blank | 59 |
| changes more than once | 58 |

**Q7d the same filing (Link_Image) on several rows  (0 s)**

| images_on_several_rows | their_rows |
|---|---|
| 0 |  |

**Q7e the file's committees in no cycle's committee table, 2010-2026  (0 s)**

| committees | rows |
|---|---|
| 14 | 24 |

**Q7f the decision line: each rule against designation B, per cycle (99% bar both ways)  (0 s)**

| cycle | rule | both | file_only_in_cm | file_only_not_in_cm | cm_b_only | file_in_b | b_in_file |
|---|---|---|---|---|---|---|---|
| 2010 | a: any Y filed by the cycle end | 1,068 | 82 | 0 | 25 | 92.87% | 97.71% |
| 2012 | a: any Y filed by the cycle end | 1,590 | 130 | 43 | 444 | 92.44% | 78.17% |
| 2014 | a: any Y filed by the cycle end | 1,679 | 106 | 109 | 406 | 94.06% | 80.53% |
| 2016 | a: any Y filed by the cycle end | 1,446 | 101 | 625 | 70 | 93.47% | 95.38% |
| 2018 | a: any Y filed by the cycle end | 1,307 | 105 | 867 | 74 | 92.56% | 94.64% |
| 2020 | a: any Y filed by the cycle end | 1,330 | 85 | 967 | 60 | 93.99% | 95.68% |
| 2022 | a: any Y filed by the cycle end | 1,389 | 75 | 1,048 | 60 | 94.88% | 95.86% |
| 2024 | a: any Y filed by the cycle end | 1,441 | 63 | 1,117 | 80 | 95.81% | 94.74% |
| 2026 | a: any Y filed by the cycle end | 1,502 | 67 | 1,205 | 102 | 95.73% | 93.64% |
| 2010 | b: latest filing by the cycle end is Y | 1,067 | 43 | 0 | 26 | 96.13% | 97.62% |
| 2012 | b: latest filing by the cycle end is Y | 1,589 | 92 | 42 | 445 | 94.53% | 78.12% |
| 2014 | b: latest filing by the cycle end is Y | 1,676 | 60 | 107 | 409 | 96.54% | 80.38% |
| 2016 | b: latest filing by the cycle end is Y | 1,444 | 51 | 621 | 72 | 96.59% | 95.25% |
| 2018 | b: latest filing by the cycle end is Y | 1,306 | 59 | 855 | 75 | 95.68% | 94.57% |
| 2020 | b: latest filing by the cycle end is Y | 1,330 | 35 | 952 | 60 | 97.44% | 95.68% |
| 2022 | b: latest filing by the cycle end is Y | 1,389 | 26 | 1,030 | 60 | 98.16% | 95.86% |
| 2024 | b: latest filing by the cycle end is Y | 1,441 | 18 | 1,095 | 80 | 98.77% | 94.74% |
| 2026 | b: latest filing by the cycle end is Y | 1,502 | 25 | 1,180 | 102 | 98.36% | 93.64% |

**Q7g file-only committees (in cm) by designation and type, 2024, rule b  (0 s)**

| designation | type | committees |
|---|---|---|
| U | Q | 14 |
| U | N | 3 |
| D | Q | 1 |

**Q7h cm-B-only committees, 2024: in the file at all, and their latest value  (0 s)**

| in_file | latest | committees |
|---|---|---|
| False |  | 80 |

**Q7i file-only and cm-only committees, 2024, rule b (40)  (0 s)**

| cid | in_file_rule | designation | type | seq | name |
|---|---|---|---|---|---|
| C00001198 | False | B | W |  | AMERICAN HOTEL AND LODGING ASSOCIATION POLITICAL ACTION COMMITTEE ('HOTELPAC') |
| C00130658 | False | B | V |  | CPAC ACTION PAC |
| C00176214 | False | B | Q |  | INTERNATIONAL LONGSHORE AND WAREHOUSE UNION -- POLITICAL ACTION FUND |
| C00327189 | False | B | W |  | VALUE IN ELECTING WOMEN POLITICAL ACTION COMMITTEE |
| C00410068 | False | B | W |  | FRATERNITY & SORORITY POLITICAL ACTION COMMITTEE |
| C00431114 | False | B | Q |  | KBR, INC. PAC |
| C00436022 | False | B | Q |  | MODERATE DEMOCRATS PAC |
| C00452276 | False | B | W |  | PODER PAC |
| C00483693 | False | B | O |  | SIERRA CLUB INDEPENDENT ACTION |
| C00483891 | False | B | W |  | ADVANCED ENERGY ACTION |
| C00484253 | False | B | O |  | UNITED FOOD AND COMMERCIAL WORKERS INTERNATIONAL UNION WORKING FAMILIES ADVOCACY PROJECT |
| C00488338 | False | B | O |  | ADPAC INDEPENDENT EXPENDITURES COMMITTEE |
| C00488486 | False | B | O |  | COMMUNICATIONS WORKERS OF AMERICA - WORKING VOICES |
| C00488742 | False | B | O |  | NATIONAL ASSOCIATION OF REALTORS CONGRESSIONAL FUND |
| C00489815 | False | B | O |  | NEA ADVOCACY FUND |
| C00490375 | False | B | O |  | NATIONAL NURSES UNITED FOR PATIENT PROTECTION |
| C00490847 | False | B | O |  | WORKING FOR WORKING AMERICANS - FEDERAL |
| C00499525 | False | B | O |  | KEEP CONSERVATIVES UNITED |
| C00509463 | False | B | O |  | PROTECTING OUR VOTE PAC |
| C00523589 | False | B | W |  | AMERICAN UNITY PAC INC |
| C00528208 | False | B | O |  | UTILITY WORKERS UNION OF AMERICA POLITICAL-LEGISLATIVE EDUCATION FUND |
| C00528448 | False | B | O |  | UAW EDUCATION FUND |
| C00528968 | False | B | V |  | CONSERVATIVE HISPANIC INITIATIVE PAC |
| C00532416 | False | B | O |  | FARM PAC |
| C00541433 | False | B | O |  | HUNTER ACTION FUND (HAF) |
| C00547349 | False | B | V |  | NEXTGEN CLIMATE ACTION COMMITTEE |
| C00556274 | False | B | O |  | USW WORKS |
| C00568444 | False | B | O |  | CENTER FORWARD COMMITTEE |
| C00577445 | False | B | V |  | DEFEND OUR NATION PAC |
| C00608836 | False | B | O |  | INDEPENDENT LEADERSHIP PAC |
| C00615344 | False | B | V |  | AMISH PAC |
| C00624817 | False | B | O |  | EARN INTERNATIONAL UNION OF OPERATING ENGINEERS |
| C00627372 | False | B | O |  | UNITE HERE PAC |
| C00632679 | False | B | O |  | CONSERVATIVE LOUISIANA |
| C00667824 | False | B | N |  | GLOBALSTAR INC POLITICAL ACTION COMMITTEE |
| C00674093 | False | B | W |  | BRADY PAC |
| C00688200 | False | B | O |  | HIGHER HEIGHTS POLITICAL FUND |
| C00691584 | False | B | V |  | CATALYST PAC |
| C00695254 | False | B | Q |  | BALLARD SPAHR LLP PAC |
| C00727719 | False | B | O |  | TRANSPORT WORKERS UNION VOICE |
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2024.csv | Last-Modified: Wed, 25 Nov 2026 10:10:59 GMT | bytes 120,104 | downloaded 2026-11-25T17:51:32+00:00
leadraw_2024: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0

**Q7j the designation B committees that are also leadership PACs in leadership2024.csv  (0 s)**

| committees |
|---|
| 0 |
EXIT 0 2026-11-25T18:37:34Z

## Q8: `lobbyist_bundle.csv`'s shape

Reports by cycle of their coverage end: 120 to 316 a cycle, 38 to 92 recipients, $8.6M to $63.3M
of period amounts (Q8a). Most are quarterly (1,375) and monthly (253); 167 cover six months (Q8b–c).
Recipients are campaigns (318 House, Senate and presidential committees), party committees (7,
$118.4M of period amounts) and joint fundraising committees (23, $109.5M); 27 leadership PACs
received bundles, $632,030 (Q8d). Five recipients are in no cycle's committee table, each one $0
report under a hoax-like name (Q8e). The 29 blank-coverage rows hold $56,500 in period amounts and
$529,124 semi-annual, most of it NRSC's $189,950 and Hensarling's $117,750 (Q8f). The semi-annual
amount sits on reports ending in June (393) and December (344), as Form 3L asks (Q8i).

```python
# Q8: lobbyist_bundle.csv's shape: rows and recipients by cycle, kinds of report, recipients.
bun()
allcmte()
show("Q8a rows, recipients and amounts by cycle (coverage end)", """
    SELECT cycle, count(*) AS rows, count(DISTINCT cid) AS recipients, sum(q) AS q_sum, sum(s) AS s_sum
    FROM bun GROUP BY 1 ORDER BY 1""")
show("Q8b covered-period length", """
    SELECT CASE WHEN days IS NULL THEN 'no dates' WHEN days <= 0 THEN '0 or less' WHEN days <= 35 THEN '1-35 (month)'
                WHEN days <= 75 THEN '36-75' WHEN days <= 100 THEN '76-100 (quarter)'
                WHEN days <= 165 THEN '101-165' WHEN days <= 190 THEN '166-190 (half-year)'
                ELSE '191+' END AS length, count(*) AS rows, sum(q) AS q_sum, sum(s) AS s_sum,
        count(*) FILTER (WHERE s > 0) AS s_above_0
    FROM bun GROUP BY 1 ORDER BY min(days) NULLS FIRST""")
show("Q8c Report_Type grouped by its words", """
    SELECT CASE WHEN Report_Type ILIKE '%MONTH%' THEN 'monthly'
                WHEN Report_Type ILIKE '%PRE%' OR Report_Type ILIKE '%POST%' OR Report_Type ILIKE '%GENERAL%'
                     OR Report_Type ILIKE '%PRIMARY%' OR Report_Type ILIKE '%RUN%' THEN 'pre- or post-election'
                WHEN Report_Type ILIKE '%QUARTER%' OR Report_Type ILIKE '%APRIL%' OR Report_Type ILIKE '%JULY%'
                     OR Report_Type ILIKE '%OCTOBER%' THEN 'quarterly'
                WHEN Report_Type ILIKE '%SEMI%' OR Report_Type ILIKE '%MID%' THEN 'semi-annual'
                WHEN Report_Type ILIKE '%YEAR%' THEN 'year-end'
                ELSE 'other' END AS kind,
        count(*) AS rows, string_agg(DISTINCT Report_Type, '; ') AS report_types, sum(q) AS q_sum, sum(s) AS s_sum
    FROM bun GROUP BY 1 ORDER BY 2 DESC""")
show("Q8d recipients by committee type and designation (the report's cycle's committee)", """
    SELECT coalesce(c.type, CASE WHEN b.cycle NOT IN (SELECT DISTINCT cycle FROM allcmte) THEN 'no build'
                                 ELSE 'absent' END) AS type,
        c.designation, count(DISTINCT b.cid) AS recipients, count(*) AS rows, sum(b.q) AS q_sum, sum(b.s) AS s_sum
    FROM bun AS b LEFT JOIN allcmte AS c ON c.cid = b.cid AND c.cycle = b.cycle
    GROUP BY ALL ORDER BY 3 DESC""")
show("Q8e recipients in no cycle's committee table, 2010-2026", """
    SELECT cid, any_value(Committee_Name) AS name, count(*) AS rows, list(DISTINCT cycle) AS cycles,
        sum(q) AS q_sum, sum(s) AS s_sum
    FROM bun WHERE cid NOT IN (SELECT cid FROM allcmte) GROUP BY 1 ORDER BY 3 DESC""")
show("Q8f rows with a blank coverage date", """
    SELECT rn, cid, Committee_Name, Report_Type, Receipt_Date, Coverage_Start_Date, Coverage_End_Date,
        q, s, Link_Image
    FROM bun WHERE cs IS NULL OR ce IS NULL ORDER BY rn""")
show("Q8g covered periods crossing a 31 December", """
    SELECT count(*) AS rows, sum(q) AS q_sum, sum(s) AS s_sum FROM bun WHERE year(cs) <> year(ce)""")
show("Q8h covered periods crossing a 30 June", """
    SELECT count(*) AS rows, sum(q) AS q_sum, sum(s) AS s_sum FROM bun
    WHERE year(cs) = year(ce) AND month(cs) <= 6 AND month(ce) >= 7""")
show("Q8i where the semi-annual amount sits: the covered period's end month", """
    SELECT month(ce) AS end_month, count(*) AS rows, count(*) FILTER (WHERE s > 0) AS s_above_0,
        sum(s) AS s_sum, count(*) FILTER (WHERE q > 0) AS q_above_0, sum(q) AS q_sum
    FROM bun GROUP BY 1 ORDER BY 1""")
```

Output:

**Q8a rows, recipients and amounts by cycle (coverage end)  (0 s)**

| cycle | rows | recipients | q_sum | s_sum |
|---|---|---|---|---|
| 2010 | 265 | 92 | 15,042,613 | 17,449,299 |
| 2012 | 239 | 65 | 25,423,423 | 27,852,750 |
| 2014 | 124 | 38 | 8,627,670 | 10,196,499 |
| 2016 | 162 | 45 | 63,349,426 | 41,366,738 |
| 2018 | 120 | 45 | 10,630,785 | 10,965,464 |
| 2020 | 200 | 62 | 52,726,659 | 41,838,060 |
| 2022 | 199 | 58 | 16,844,352 | 16,716,577 |
| 2024 | 316 | 84 | 59,812,626 | 63,220,351 |
| 2026 | 290 | 88 | 54,635,003 | 64,434,349 |
|  | 14 | 13 | 34,000 | 224,684 |

**Q8b covered-period length  (0 s)**

| length | rows | q_sum | s_sum | s_above_0 |
|---|---|---|---|---|
| no dates | 29 | 56,500 | 529,124 | 9 |
| 1-35 (month) | 418 | 81,331,622 | 119,802,556 | 119 |
| 36-75 | 272 | 12,634,669 | 26,228,126 | 103 |
| 76-100 (quarter) | 1,017 | 172,560,583 | 103,857,647 | 398 |
| 101-165 | 17 | 636,414 | 1,078,793 | 6 |
| 166-190 (half-year) | 167 | 38,814,781 | 41,818,389 | 133 |
| 191+ | 9 | 1,091,987 | 950,135 | 3 |

**Q8c Report_Type grouped by its words  (0 s)**

| kind | rows | report_types | q_sum | s_sum |
|---|---|---|---|---|
| quarterly | 1,375 | QUARTERLY MID-YEAR / SEMI-ANN; QUARTERLY YEAR END / SEMI-ANN; APRIL QUARTERLY; JULY QUARTERLY; QUARTERLY SEMI-ANNUAL (MY); QUARTERLY SEMI-ANNUAL (YE); JULY QUARTERLY / SEMI-ANNUAL; OCTOBER QUARTERLY | 210,270,836 | 188,594,698 |
| pre- or post-election | 257 | PRE-PRIMARY; POST-GENERAL; PRE-RUN-OFF; POST-RUN-OFF; POST-SPECIAL; PRE-SPECIAL; PRE-CONVENTION; PRE-GENERAL | 21,951,942 | 916,742 |
| monthly | 253 | AUGUST MONTHLY; FEBRUARY MONTHLY; OCTOBER MONTHLY; JUNE MONTHLY; APRIL MONTHLY; MONTHLY SEMI-ANNUAL (MY); NOVEMBER MONTHLY; JULY MONTHLY; MARCH MONTHLY; DECEMBER MONTHLY; MONTHLY SEMI-ANNUAL (YE); SEPTEMBER MONTHLY; MAY MONTHLY; MONTHLY YEAR END / SEMI-ANNUAL; JULY MONTHLY / SEMI-ANNUAL | 70,607,405 | 97,235,171 |
| year-end | 37 | YEAR-END | 2,179,447 | 5,394,884 |
| other | 5 |  | 142,650 | 109,500 |
| semi-annual | 2 | MID-YEAR REPORT | 1,974,276 | 2,013,776 |

**Q8d recipients by committee type and designation (the report's cycle's committee)  (0 s)**

| type | designation | recipients | rows | q_sum | s_sum |
|---|---|---|---|---|---|
| H | P | 190 | 683 | 27,974,666 | 25,187,484 |
| S | P | 114 | 662 | 33,593,132 | 34,314,097 |
| N | J | 23 | 80 | 109,472,814 | 76,493,974 |
| Q | D | 20 | 42 | 527,700 | 534,350 |
| absent |  | 18 | 19 | 34,000 | 224,684 |
| N | U | 14 | 20 | 5,000 | 2,500 |
| P | P | 14 | 46 | 15,705,794 | 17,037,918 |
| O | U | 8 | 14 | 0 | 6,600 |
| N | D | 7 | 17 | 104,330 | 148,259 |
| Y | U | 7 | 301 | 118,377,037 | 139,269,774 |
| N | B | 5 | 9 | 0 | 0 |
| S | J | 5 | 7 | 1,168,225 | 919,700 |
| V | U | 3 | 3 | 38,627 | 38,627 |
| H | A | 3 | 4 | 0 | 0 |
| X | U | 3 | 3 | 3,576 | 0 |
| Q | U | 2 | 2 | 0 | 0 |
| O | B | 2 | 8 | 0 | 0 |
| S | A | 1 | 4 | 121,607 | 86,753 |
| Q | B | 1 | 2 | 0 | 0 |
| U | U | 1 | 1 | 0 | 0 |
| W | U | 1 | 1 | 0 | 0 |
| X | P | 1 | 1 | 50 | 50 |

**Q8e recipients in no cycle's committee table, 2010-2026  (0 s)**

| cid | name | rows | cycles | q_sum | s_sum |
|---|---|---|---|---|---|
| C00746362 | VENA ALLIANCETRIPLANETORIUM RELIGIOUS PLANET JUPITER COUNTRY AND GOVERNMENT POLITICAL PARTY | 1 | [2020] | 0 | 0 |
| C00571638 | AMERICANS FOR HEALTH AND EDUCATION, PAC | 1 | [2018] | 0 | 0 |
| C00713883 | AMERICAN RELIGIOUS GOVERNMENT AND PRESIDENCY | 1 | [2020] | 0 | 0 |
| C00910612 | JIMMY T LE FOR PRESIDENT 2028 | 1 | [2026] | 0 | 0 |
| C00748178 | VENA ALLIANCE TRIPLANETORIUM RELIGIOUS GLOBAL COUNTRY GOVERNMENT POLITICAL PARTY | 1 | [2020] | 0 | 0 |

**Q8f rows with a blank coverage date  (0 s)**

| rn | cid | Committee_Name | Report_Type | Receipt_Date | Coverage_Start_Date | Coverage_End_Date | q | s | Link_Image |
|---|---|---|---|---|---|---|---|---|---|
| 189 | C00925529 | AXPAC | QUARTERLY SEMI-ANNUAL (YE) | 30-JAN-26 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_202601309795289379+0 |
| 567 | C00839324 | ONE AMERICAN PERCEPTION | MONTHLY SEMI-ANNUAL (MY) | 16-AUG-23 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_202308169596573290+0 |
| 694 | C00765909 | PULLIAM'S COMMITEE | QUARTERLY SEMI-ANNUAL (MY) | 09-AUG-22 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_202208099525169679+0 |
| 792 | C00764068 | TAKING MARSHFIELD BACK | MONTHLY SEMI-ANNUAL (MY) | 17-AUG-21 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_202108179466305998+0 |
| 797 | C00764068 | TAKING MARSHFIELD BACK | MONTHLY SEMI-ANNUAL (MY) | 29-JUL-21 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_202107299452153427+0 |
| 948 | C00701359 | CLEANOCEANSPAC | QUARTERLY SEMI-ANNUAL (YE) | 13-APR-20 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_202004139216664072+0 |
| 1,024 | C00674408 | AMERICAN-HAITIAN GENERATION IN ACTION | APRIL MONTHLY | 29-JAN-19 |  | 20-APR-18 | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201901300300258836+0 |
| 1,026 | C00674408 | AMERICAN-HAITIAN GENERATION IN ACTION | OCTOBER QUARTERLY | 29-JAN-19 |  | 15-OCT-18 | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201901300300258848+0 |
| 1,030 | C00679761 | HILDT4CONGRESS.ORG ELECTION COMMITTEE | YEAR-END | 27-DEC-18 |  | 27-DEC-18 | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201901290300257787+0 |
| 1,094 | C00582064 | TRADITIONAL MARRIAGE COALITION | YEAR-END | 01-FEB-18 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201802010300191432+0 |
| 1,106 | C00370213 | AMERICAN HEALTH QUALITY ASSOCIATION POLITICAL ACTION COMMITTEE (AHQA-PAC) | MONTHLY SEMI-ANNUAL (MY) | 12-SEP-17 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201709129074650502+0 |
| 1,112 | C00582064 | TRADITIONAL MARRIAGE COALITION | JULY QUARTERLY | 17-JUL-17 |  | 15-JUL-17 | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201707170300163132+0 |
| 1,132 | C00582064 | TRADITIONAL MARRIAGE COALITION | OCTOBER QUARTERLY | 02-MAR-17 |  | 24-FEB-17 | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201703020300143047+0 |
| 1,133 | C00582064 | TRADITIONAL MARRIAGE COALITION | APRIL QUARTERLY | 02-MAR-17 |  | 24-FEB-17 | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201703020300143057+0 |
| 1,134 | C00582064 | TRADITIONAL MARRIAGE COALITION | JULY QUARTERLY | 02-MAR-17 |  | 24-FEB-17 | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201703020300143052+0 |
| 1,135 | C00582064 | TRADITIONAL MARRIAGE COALITION | YEAR-END | 02-MAR-17 |  | 24-FEB-17 | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201703020300143042+0 |
| 1,173 | C00622738 | FELLOWSHIP UNITE POLITICAL ACTION COMMITTEE | PRE-GENERAL | 08-NOV-16 |  | 02-NOV-16 | 0 | 2,500 | http://docquery.fec.gov/cgi-bin/fecimg/?_201611080300118065+0 |
| 1,212 | C00504688 | OTERO FOR CONGRESS | QUARTERLY SEMI-ANNUAL (MY) | 15-JUL-16 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_201607159020666485+0 |
| 1,334 | C00548354 | MISSION: EQUALITY AND DEMOCRACY LLC | QUARTERLY SEMI-ANNUAL (MY) | 08-AUG-14 |  |  |  | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_14031283945+0 |
| 1,337 | C00000935 | DEMOCRATIC CONGRESSIONAL CAMPAIGN COMMITTEE | JULY MONTHLY / SEMI-ANNUAL | 18-JUL-14 |  |  | 34,000 | 34,000 | http://docquery.fec.gov/cgi-bin/fecimg/?_14941870981+0 |
| 1,379 | C00489195 | YINKA ABOSEDE ADESHINA | APRIL QUARTERLY | 06-MAR-14 |  | 31-MAR-14 |  | 45,540 | http://docquery.fec.gov/cgi-bin/fecimg/?_14031192326+0 |
| 1,383 | C00027466 | NATIONAL REPUBLICAN SENATORIAL COMMITTEE | QUARTERLY SEMI-ANNUAL (YE) | 31-JAN-14 |  |  | 0 | 189,950 | http://docquery.fec.gov/cgi-bin/fecimg/?_14020023839+0 |
| 1,453 | C00523423 | MY CAT XAVIER FOR A BETTER TOMORROW TOMORROW | YEAR-END | 22-JAN-13 |  |  | 0 | 0 | http://docquery.fec.gov/cgi-bin/fecimg/?_13031013656+0 |
| 1,598 | C00506725 | 72ND AREA WIDE DEMOCRATIC ALLIANCE  | QUARTERLY SEMI-ANNUAL (YE) | 17-JAN-12 |  |  |  | 734 | http://docquery.fec.gov/cgi-bin/fecimg/?_12030704026+0 |
| 1,642 | C00492231 | FRIENDS OF MIKE H | QUARTERLY MID-YEAR / SEMI-ANN | 15-JUL-11 |  | 30-JUN-11 | 0 | 84,200 | http://docquery.fec.gov/cgi-bin/fecimg/?_11020300066+0 |
| 1,714 | C00388793 | GROWTH AND PROSPERITY POLITICAL ACTION COMMITTEE | OCTOBER QUARTERLY | 15-OCT-10 |  | 30-SEP-10 | 22,500 |  | http://docquery.fec.gov/cgi-bin/fecimg/?_10931451678+0 |
| 1,750 | C00462135 | CHARLIE CRIST FOR US SENATE | QUARTERLY SEMI-ANNUAL (MY) | 15-JUL-10 |  | 30-JUN-10 | 0 | 34,450 | http://docquery.fec.gov/cgi-bin/fecimg/?_10020502170+0 |
| 1,813 | C00370650 | FRIENDS OF JEB HENSARLING | QUARTERLY SEMI-ANNUAL (YE) | 31-JAN-10 |  | 31-DEC-09 |  | 117,750 | http://docquery.fec.gov/cgi-bin/fecimg/?_10990244918+0 |
| 1,842 | C00385534 | LEGPAC | QUARTERLY SEMI-ANNUAL (YE) | 26-JAN-10 |  | 31-DEC-09 | 0 | 20,000 | http://docquery.fec.gov/cgi-bin/fecimg/?_10990144076+0 |

**Q8g covered periods crossing a 31 December  (0 s)**

| rows | q_sum | s_sum |
|---|---|---|
| 9 | 219,043 | 50 |

**Q8h covered periods crossing a 30 June  (0 s)**

| rows | q_sum | s_sum |
|---|---|---|
| 13 | 979,691 | 950,085 |

**Q8i where the semi-annual amount sits: the covered period's end month  (0 s)**

| end_month | rows | s_above_0 | s_sum | q_above_0 | q_sum |
|---|---|---|---|---|---|
| 1 | 25 | 0 | 0 | 22 | 13,805,205 |
| 2 | 41 | 0 | 0 | 29 | 14,002,786 |
| 3 | 259 | 11 | 868,156 | 192 | 55,687,930 |
| 4 | 43 | 0 | 0 | 27 | 7,211,226 |
| 5 | 36 | 2 | 68,250 | 29 | 1,810,992 |
| 6 | 487 | 393 | 179,108,460 | 325 | 65,014,105 |
| 7 | 41 | 0 | 0 | 25 | 4,962,852 |
| 8 | 29 | 2 | 46,525 | 18 | 3,425,125 |
| 9 | 359 | 8 | 384,772 | 289 | 86,997,252 |
| 10 | 97 | 4 | 487,740 | 55 | 10,490,650 |
| 11 | 86 | 4 | 314,227 | 55 | 7,615,779 |
| 12 | 412 | 344 | 112,761,956 | 193 | 36,068,653 |
|  | 14 | 3 | 224,684 | 1 | 34,000 |
EXIT 0 2026-11-25T18:37:38Z

## Q9: amendments in the bundling file

87 (committee, coverage start, coverage end) keys are on 194 rows. 60 differ in amounts and receipt
date (later amendments), 23 in receipt date alone, 3 are identical and 1 differs in amount on the
same day (Q9a). Keeping the latest receipt date, then the higher image number, keeps 1,822 rows
and supersedes 107 ($51.8M period, $32.4M semi-annual); 4 keys tie on receipt date and every row
has an image number (Q9b–c). Amendments come late: DCCC's June 2024 report was amended on
2026-10-23, and 211 kept reports were received after their cycle ended, 2 of them over a year
after (Q9g). A historical cycle's bronze copy is as old as its last extract, so a re-extract can
change its total.

Kept reports overlap in 90 pairs, 86 of them one inside the other (Q9e). They are not amendments:
a six-month `YEAR END / SEMI-ANN` report whose period amount equals its semi-annual figure, filed
beside the same half's quarterly and pre- and post-election reports (Trump Victory's second half
of 2020, DCCC's first half of 2017). They hold 9.16% of the file's period dollars, over the 1% bar,
so they went to the checkpoint. The default stands for amendments (Decision 7); Q10's second
reading handles the nesting (Decision 8).

```python
# Q9: amendments in lobbyist_bundle.csv, and the default rule (latest receipt date, then image).
bun()
con.execute("""
    CREATE TABLE q9 AS
    WITH t AS (
        SELECT b.*, CASE WHEN cs IS NULL OR ce IS NULL THEN rn END AS alone,
            max(rdt) OVER (PARTITION BY cid, cs, ce, CASE WHEN cs IS NULL OR ce IS NULL THEN rn END)
                AS max_rdt
        FROM bun AS b
    )
    SELECT t.*, count(*) OVER k AS key_rows,
        count(DISTINCT (q, s)) OVER k AS amounts, count(DISTINCT rdt) OVER k AS rdts,
        count(*) FILTER (WHERE rdt IS NOT DISTINCT FROM max_rdt) OVER k AS rows_on_latest_rdt
    FROM t
    WINDOW k AS (PARTITION BY cid, cs, ce, alone)""")
show("Q9a keys (committee, coverage start, coverage end) on more than one row", """
    SELECT CASE WHEN amounts = 1 AND rdts = 1 THEN 'identical amounts and receipt date'
                WHEN amounts = 1 THEN 'same amounts, receipt date differs'
                WHEN rdts = 1 THEN 'amounts differ, same receipt date'
                ELSE 'amounts and receipt date differ' END AS how,
        count(DISTINCT (cid, cs, ce)) AS keys, count(*) AS rows, sum(q) AS q_sum, sum(s) AS s_sum
    FROM q9 WHERE key_rows > 1 GROUP BY 1 ORDER BY 2 DESC""")
show("Q9b the default: kept and superseded", """
    SELECT kept, count(*) AS rows, sum(q) AS q_sum, sum(s) AS s_sum FROM bun GROUP BY 1 ORDER BY 1""")
show("Q9c ties: keys whose latest receipt date is on several rows (image number decides)", """
    SELECT count(DISTINCT (cid, cs, ce)) AS keys, count(*) AS rows,
        count(*) FILTER (WHERE img IS NULL) AS rows_without_image
    FROM q9 WHERE key_rows > 1 AND rows_on_latest_rdt > 1""")
show("Q9d every repeated key (largest first, 30)", """
    SELECT cid, Committee_Name, cs, ce, string_agg(Report_Type || ' ' || coalesce(rdt::VARCHAR, '-') || ' img '
        || coalesce(img::VARCHAR, '-') || ' q ' || coalesce(q::VARCHAR, '-') || ' s ' || coalesce(s::VARCHAR, '-')
        || CASE WHEN kept THEN ' KEPT' ELSE '' END, ' | ' ORDER BY rdt, img) AS rows
    FROM q9 WHERE key_rows > 1 GROUP BY ALL ORDER BY max(greatest(coalesce(q, 0), coalesce(s, 0))) DESC LIMIT 30""")
con.execute("""
    CREATE TABLE q9o AS
    SELECT a.cid, a.rn AS a_rn, b.rn AS b_rn, a.cs AS a_cs, a.ce AS a_ce, b.cs AS b_cs, b.ce AS b_ce,
        a.Report_Type AS a_type, b.Report_Type AS b_type, a.q AS a_q, b.q AS b_q, a.s AS a_s, b.s AS b_s,
        CASE WHEN a.cs >= b.cs AND a.ce <= b.ce OR b.cs >= a.cs AND b.ce <= a.ce THEN 'one inside the other'
             ELSE 'partial overlap' END AS kind,
        a.half = b.half AS same_half
    FROM bun AS a JOIN bun AS b ON a.cid = b.cid AND a.rn < b.rn AND a.kept AND b.kept
        AND a.cs <= b.ce AND b.cs <= a.ce""")
show("Q9e kept rows of one committee whose periods overlap (1% bar on the file's dollars)", """
    WITH r AS (SELECT DISTINCT kind, unnest([a_rn, b_rn]) AS rn FROM q9o)
    SELECT kind, (SELECT count(*) FROM q9o WHERE q9o.kind = r.kind) AS pairs, count(*) AS rows,
        sum(b.q) AS q_sum, sum(b.s) AS s_sum,
        sum(b.q) / (SELECT sum(q) FROM bun)::DOUBLE AS q_share_of_file,
        sum(b.s) / (SELECT sum(s) FROM bun)::DOUBLE AS s_share_of_file
    FROM r JOIN bun AS b USING (rn) GROUP BY 1 ORDER BY 1""")
show("Q9f those pairs (20, largest first)", """
    SELECT cid, kind, same_half, a_cs, a_ce, a_type, a_q, a_s, b_cs, b_ce, b_type, b_q, b_s FROM q9o
    ORDER BY greatest(coalesce(a_q, 0), coalesce(b_q, 0), coalesce(a_s, 0), coalesce(b_s, 0)) DESC LIMIT 20""")
show("Q9g reports received after their cycle's last day, by how late", """
    SELECT CASE WHEN rdt IS NULL THEN 'no receipt date' WHEN rdt <= make_date(cycle, 12, 31) THEN 'in the cycle'
                WHEN rdt <= make_date(cycle, 12, 31) + INTERVAL 90 DAY THEN 'up to 90 days late'
                WHEN rdt <= make_date(cycle + 1, 12, 31) THEN '91 days to a year'
                ELSE 'over a year' END AS received,
        kept, count(*) AS rows, sum(q) AS q_sum, sum(s) AS s_sum
    FROM bun WHERE ce IS NOT NULL GROUP BY ALL ORDER BY ALL""")
```

Output:

**Q9a keys (committee, coverage start, coverage end) on more than one row  (0 s)**

| how | keys | rows | q_sum | s_sum |
|---|---|---|---|---|
| amounts and receipt date differ | 60 | 130 | 91,841,553 | 64,218,944 |
| same amounts, receipt date differs | 23 | 56 | 1,178,274 | 676,968 |
| identical amounts and receipt date | 3 | 6 | 47,800 | 163,904 |
| amounts differ, same receipt date | 1 | 2 | 61,070 | 38,035 |

**Q9b the default: kept and superseded  (0 s)**

| kept | rows | q_sum | s_sum |
|---|---|---|---|
| False | 107 | 51,810,074 | 32,428,095 |
| True | 1,822 | 255,316,482 | 261,836,675 |

**Q9c ties: keys whose latest receipt date is on several rows (image number decides)  (0 s)**

| keys | rows | rows_without_image |
|---|---|---|
| 4 | 8 | 0 |

**Q9d every repeated key (largest first, 30)  (0 s)**

| cid | Committee_Name | cs | ce | rows |
|---|---|---|---|---|
| C00000935 | DCCC | 2026-06-01 | 2026-06-30 | JULY MONTHLY / SEMI-ANNUAL 2026-07-20 img 202607209890941282 q 225062.50 s 15719262.50 \| JULY MONTHLY / SEMI-ANNUAL 2026-10-23 img 202610239945196866 q 472275.50 s 16119375.50 KEPT |
| C00586537 | HILLARY VICTORY FUND | 2016-07-01 | 2016-09-30 | OCTOBER QUARTERLY 2016-10-15 img 201610159032761917 q 10601247.97 s 0.00 \| OCTOBER QUARTERLY 2016-10-27 img 201610279036941213 q 10660047.97 s 0.00 \| OCTOBER QUARTERLY 2017-01-31 img 201701319042360549 q 10769947.97 s 0.00 KEPT |
| C00000935 | DCCC | 2024-06-01 | 2024-06-30 | JULY MONTHLY / SEMI-ANNUAL 2024-07-19 img 202407199661302879 q 73500.00 s 6621807.50 \| JULY MONTHLY / SEMI-ANNUAL 2026-10-23 img 202610239945196723 q 156100.00 s 6701907.50 KEPT |
| C00000935 | DCCC | 2026-03-01 | 2026-03-31 | APRIL MONTHLY 2026-04-20 img 202604209863240268 q 3251400.00 s 0.00 \| APRIL MONTHLY 2026-07-20 img 202607209890940958 q 3271400.00 s 0.00 KEPT |
| C00575795 | HILLARY FOR AMERICA | 2016-04-01 | 2016-06-30 | JULY QUARTERLY / SEMI-ANNUAL 2016-07-15 img 201607159020642162 q 1190025.34 s 2896098.52 \| JULY QUARTERLY / SEMI-ANNUAL 2016-10-27 img 201610279036941147 q 1190025.34 s 2914998.52 KEPT |
| C00000935 | DCCC | 2024-03-01 | 2024-03-31 | APRIL MONTHLY 2024-04-19 img 202404199633502459 q 2710027.50 s 0.00 \| APRIL MONTHLY 2024-07-19 img 202407199661302469 q 2709777.50 s 0.00 KEPT |
| C00867937 | TRUMP 47 COMMITTEE, INC. | 2024-07-01 | 2024-09-30 | OCTOBER QUARTERLY 2024-10-15 img 202410159688956337 q 2546783.31 s 0.00 \| OCTOBER QUARTERLY 2025-01-31 img 202501319752736325 q 2598131.95 s 0.00 KEPT |
| C00586537 | HILLARY VICTORY FUND | 2016-10-01 | 2016-10-19 | PRE-GENERAL 2016-10-27 img 201610279036926257 q 2504964.48 s 0.00 \| PRE-GENERAL 2017-01-31 img 201701319042360646 q 2528864.48 s 0.00 KEPT |
| C00618389 | TRUMP VICTORY | 2019-10-01 | 2019-12-31 | QUARTERLY YEAR END / SEMI-ANN 2020-01-31 img 202001319185633560 q 1013292.61 s 1965326.26 \| QUARTERLY YEAR END / SEMI-ANN 2020-07-07 img 202007079244356481 q 866492.61 s 1458526.26 \| QUARTERLY YEAR END / SEMI-ANN 2020-07-17 img 202007179250397424 q 1512592.61 s 2104626.26 KEPT |
| C00000935 | DCCC | 2026-04-01 | 2026-04-30 | MAY MONTHLY 2026-05-19 img 202605199867016153 q 1861300.00 s 0.00 \| MAY MONTHLY 2026-08-20 img 202608209899718021 q 1949900.00 s 0.00 KEPT |
| C00000935 | DCCC | 2019-06-01 | 2019-06-30 | JULY MONTHLY / SEMI-ANNUAL 2019-07-19 img 201907199151512051 q 124362.50 s 1608462.50 \| JULY MONTHLY / SEMI-ANNUAL 2020-07-10 img 202007109244403644 q 128112.50 s 1739212.50 KEPT |
| C00575795 | HILLARY FOR AMERICA | 2016-01-01 | 2016-03-31 | APRIL QUARTERLY 2016-04-15 img 201604159012556514 q 1550185.00 s 0.00 \| APRIL QUARTERLY 2016-10-27 img 201610279036940114 q 1569085.00 s 0.00 KEPT |
| C00042366 | DSCC | 2020-01-01 | 2020-03-31 | APRIL QUARTERLY 2020-04-15 img 202004159216857085 q 960651.00 s 0.00 \| APRIL QUARTERLY 2020-07-15 img 202007159245090349 q 1293151.01 s 0.00 KEPT |
| C00618389 | TRUMP VICTORY | 2019-04-01 | 2019-06-30 | JULY QUARTERLY / SEMI-ANNUAL 2019-07-15 img 201907159150983654 q 111434.59 s 111434.59 \| JULY QUARTERLY / SEMI-ANNUAL 2019-07-19 img 201907199151532879 q 1036634.59 s 1036634.59 KEPT |
| C00618389 | TRUMP VICTORY | 2019-07-01 | 2019-09-30 | OCTOBER QUARTERLY 2019-10-15 img 201910159164575428 q 910000.00 s 0.00 \| OCTOBER QUARTERLY 2019-10-23 img 201910239165292591 q 952033.65 s 0.00 \| OCTOBER QUARTERLY 2020-07-07 img 202007079244356467 q 592033.65 s 0.00 KEPT |
| C00000935 | DCCC | 2025-07-01 | 2025-07-31 | AUGUST MONTHLY 2025-08-20 img 202508209789587513 q 792986.00 s 0.00 \| AUGUST MONTHLY 2026-01-29 img 202601299794406864 q 881586.00 s 0.00 KEPT |
| C00042366 | DEMOCRATIC SENATORIAL CAMPAIGN COMMITTEE | 2009-06-01 | 2009-06-30 | JULY MONTHLY / SEMI-ANNUAL 2009-07-20 img 29020282673 q 198950.00 s 731800.00 \| JULY MONTHLY / SEMI-ANNUAL 2009-12-04 img 29020444417 q 198950.00 s 787700.00 KEPT |
| C00000935 | DCCC | 2024-01-01 | 2024-01-31 | FEBRUARY MONTHLY 2024-02-16 img 202402169619788998 q 781480.00 s 0.00 \| FEBRUARY MONTHLY 2024-07-19 img 202407199661301560 q 786480.00 s 0.00 KEPT |
| C00000935 | DCCC | 2019-03-01 | 2019-03-31 | APRIL MONTHLY 2019-04-18 img 201904189149491883 q 659900.00 s 0.00 \| APRIL MONTHLY 2019-04-25 img 201904259149600801 q 727900.00 s 0.00 \| APRIL MONTHLY 2020-07-10 img 202007109244403584 q 712900.00 s 0.00 KEPT |
| C00000935 | DCCC | 2022-01-01 | 2022-01-31 | FEBRUARY MONTHLY 2022-02-18 img 202202189491786907 q 451400.00 s 0.00 \| FEBRUARY MONTHLY 2022-07-20 img 202207209522239007 q 668400.00 s 0.00 KEPT |
| C00867937 | TRUMP 47 COMMITTEE, INC. | 2024-10-01 | 2024-10-16 | PRE-GENERAL 2024-10-24 img 202410249713179299 q 519574.38 s 0.00 \| PRE-GENERAL 2025-01-31 img 202501319752736327 q 624574.38 s 0.00 KEPT |
| C00000935 | DCCC | 2022-02-01 | 2022-02-28 | MARCH MONTHLY 2022-03-14 img 202203149493775994 q 566650.00 s 0.00 \| MARCH MONTHLY 2022-07-20 img 202207209522239342 q 587650.00 s 0.00 KEPT |
| C00042366 | DEMOCRATIC SENATORIAL CAMPAIGN COMMITTEE | 2012-01-01 | 2012-01-31 | FEBRUARY MONTHLY 2012-02-17 img 12020172732 q 537250.00 s - \| FEBRUARY MONTHLY 2012-07-20 img 12020590001 q 559750.00 s - KEPT |
| C00042366 | DEMOCRATIC SENATORIAL CAMPAIGN COMMITTEE | 2014-02-01 | 2014-02-28 | MARCH MONTHLY 2014-03-20 img 14020170812 q 426150.00 s - \| MARCH MONTHLY 2014-07-17 img 14020562967 q 491999.00 s 0.00 KEPT |
| C00000935 | DCCC | 2019-02-01 | 2019-02-28 | MARCH MONTHLY 2019-03-20 img 201903209145882542 q 374500.00 s 0.00 \| MARCH MONTHLY 2020-07-10 img 202007109244402347 q 388000.00 s 0.00 KEPT |
| C00000935 | DCCC | 2020-02-01 | 2020-02-29 | MARCH MONTHLY 2020-03-20 img 202003209204021650 q 387100.00 s 0.00 \| MARCH MONTHLY 2020-07-20 img 202007209250421616 q 336100.00 s 0.00 KEPT |
| C00000935 | DCCC | 2020-01-01 | 2020-01-31 | FEBRUARY MONTHLY 2020-02-20 img 202002209186573173 q 159500.00 s 0.00 \| FEBRUARY MONTHLY 2020-07-20 img 202007209250421233 q 378800.00 s 0.00 KEPT |
| C00000935 | DCCC | 2022-03-01 | 2022-03-31 | APRIL MONTHLY 2022-04-19 img 202204199500049403 q 239500.00 s 0.00 \| APRIL MONTHLY 2022-07-20 img 202207209522241617 q 372000.00 s 0.00 KEPT |
| C00042366 | DEMOCRATIC SENATORIAL CAMPAIGN COMMITTEE | 2009-09-01 | 2009-09-30 | OCTOBER MONTHLY 2009-10-20 img 29020422431 q 152300.00 s - \| OCTOBER MONTHLY 2009-12-04 img 29020444424 q 226550.00 s - KEPT |
| C00042366 | DEMOCRATIC SENATORIAL CAMPAIGN COMMITTEE | 2009-04-01 | 2009-04-30 | MAY MONTHLY 2009-05-20 img 29020203563 q 209700.00 s 0.00 \| MAY MONTHLY 2009-07-20 img 29020282680 q 149300.00 s - \| MAY MONTHLY 2009-12-04 img 29020444413 q 134300.00 s - KEPT |

**Q9e kept rows of one committee whose periods overlap (1% bar on the file's dollars)  (0 s)**

| kind | pairs | rows | q_sum | s_sum | q_share_of_file | s_share_of_file |
|---|---|---|---|---|---|---|
| one inside the other | 86 | 150 | 28,138,453 | 15,003,797 | 9.16% | 5.10% |
| partial overlap | 4 | 8 | 321,639 | 306,889 | 0.10% | 0.10% |

**Q9f those pairs (20, largest first)  (0 s)**

| cid | kind | same_half | a_cs | a_ce | a_type | a_q | a_s | b_cs | b_ce | b_type | b_q | b_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C00618389 | one inside the other | True | 2020-07-01 | 2020-12-31 | QUARTERLY YEAR END / SEMI-ANN | 9,348,404 | 9,348,404 | 2020-10-01 | 2020-10-14 | PRE-GENERAL | 96,500 | 0 |
| C00618389 | one inside the other | True | 2020-07-01 | 2020-12-31 | QUARTERLY YEAR END / SEMI-ANN | 9,348,404 | 9,348,404 | 2020-10-15 | 2020-11-23 | POST-GENERAL | 2,304,200 | 0 |
| C00618389 | one inside the other | True | 2020-07-01 | 2020-12-31 | QUARTERLY YEAR END / SEMI-ANN | 9,348,404 | 9,348,404 | 2020-07-01 | 2020-09-30 | OCTOBER QUARTERLY | 6,947,704 | 0 |
| C00000935 | one inside the other | True | 2017-01-01 | 2017-06-30 | QUARTERLY MID-YEAR / SEMI-ANN | 748,100 | 748,100 | 2017-01-01 | 2017-03-31 | APRIL QUARTERLY | 696,600 | 0 |
| C00795211 | one inside the other | True | 2024-07-01 | 2024-12-31 | QUARTERLY YEAR END / SEMI-ANN | 569,685 | 569,685 | 2024-07-01 | 2024-09-30 | OCTOBER QUARTERLY | 224,276 | 0 |
| C00795211 | one inside the other | True | 2024-07-01 | 2024-12-31 | QUARTERLY YEAR END / SEMI-ANN | 569,685 | 569,685 | 2024-10-01 | 2024-10-16 | PRE-GENERAL | 197,918 | 0 |
| C00795211 | one inside the other | True | 2024-07-01 | 2024-12-31 | QUARTERLY YEAR END / SEMI-ANN | 569,685 | 569,685 | 2024-10-17 | 2024-11-25 | POST-GENERAL | 147,490 | 0 |
| C00741611 | one inside the other | True | 2020-07-01 | 2020-12-31 | QUARTERLY YEAR END / SEMI-ANN | 247,450 | 247,450 | 2020-10-15 | 2020-11-23 | POST-GENERAL | 26,866 | 0 |
| C00741611 | one inside the other | True | 2020-07-01 | 2020-12-31 | QUARTERLY YEAR END / SEMI-ANN | 247,450 | 247,450 | 2020-07-01 | 2020-09-30 | OCTOBER QUARTERLY | 168,246 | 0 |
| C00741611 | one inside the other | True | 2020-07-01 | 2020-12-31 | QUARTERLY YEAR END / SEMI-ANN | 247,450 | 247,450 | 2020-10-01 | 2020-10-14 | PRE-GENERAL | 27,330 | 0 |
| C00784959 | one inside the other | True | 2022-07-01 | 2022-12-31 | QUARTERLY YEAR END / SEMI-ANN | 216,330 | 216,330 | 2022-10-01 | 2022-10-19 | PRE-GENERAL | 22,452 | 0 |
| C00784959 | one inside the other | True | 2022-07-01 | 2022-12-31 | QUARTERLY YEAR END / SEMI-ANN | 216,330 | 216,330 | 2022-07-01 | 2022-09-30 | OCTOBER QUARTERLY | 168,928 | 0 |
| C00784959 | one inside the other | True | 2022-07-01 | 2022-12-31 | QUARTERLY YEAR END / SEMI-ANN | 216,330 | 216,330 | 2022-10-20 | 2022-11-28 | POST-GENERAL | 24,950 | 0 |
| C00326801 | one inside the other | True | 2012-07-01 | 2012-12-31 | QUARTERLY YEAR END / SEMI-ANN | 215,144 | 215,144 | 2012-07-01 | 2012-09-30 | OCTOBER QUARTERLY | 104,212 |  |
| C00003418 | one inside the other | True | 2011-07-01 | 2011-12-31 | QUARTERLY YEAR END / SEMI-ANN | 0 | 191,600 | 2011-10-01 | 2011-12-31 | QUARTERLY YEAR END / SEMI-ANN | 0 | 191,600 |
| C00499954 | one inside the other | True | 2012-01-01 | 2012-06-30 | QUARTERLY MID-YEAR / SEMI-ANN | 186,240 | 186,240 | 2012-01-01 | 2012-03-31 | APRIL QUARTERLY | 28,139 | 0 |
| C00499954 | one inside the other | True | 2012-01-01 | 2012-06-30 | QUARTERLY MID-YEAR / SEMI-ANN | 186,240 | 186,240 | 2012-04-19 | 2012-06-27 | PRE-RUN-OFF | 143,146 | 0 |
| C00499954 | partial overlap | False | 2012-06-28 | 2012-09-30 | OCTOBER QUARTERLY | 0 | 0 | 2012-01-01 | 2012-06-30 | QUARTERLY MID-YEAR / SEMI-ANN | 186,240 | 186,240 |
| C00696153 | one inside the other | True | 2020-07-01 | 2020-12-31 | QUARTERLY YEAR END / SEMI-ANN | 185,427 | 185,427 | 2020-10-01 | 2020-10-14 | PRE-GENERAL | 40,776 | 0 |
| C00696153 | one inside the other | True | 2020-07-01 | 2020-12-31 | QUARTERLY YEAR END / SEMI-ANN | 185,427 | 185,427 | 2020-07-01 | 2020-09-30 | OCTOBER QUARTERLY | 132,835 | 0 |

**Q9g reports received after their cycle's last day, by how late  (0 s)**

| received | kept | rows | q_sum | s_sum |
|---|---|---|---|---|
| 91 days to a year | True | 18 | 4,246,406 | 4,359,791 |
| in the cycle | False | 102 | 51,759,574 | 32,201,026 |
| in the cycle | True | 1,597 | 222,034,625 | 179,907,049 |
| over a year | True | 2 | 156,100 | 6,701,908 |
| up to 90 days late | False | 5 | 50,500 | 227,069 |
| up to 90 days late | True | 191 | 28,845,351 | 70,643,244 |
EXIT 0 2026-11-25T18:37:40Z

## Q10: the bundled total

Per cycle, under the spec's reading (all kept reports' period amounts against the half-year figure)
and the second (innermost reports only). The two differ most in 2020, $47.0M against $36.8M,
where Trump Victory's six-month report sits beside its quarters (Q10a). The asserted fact, that a
half's semi-annual figure is never below its periods' sum, fails in 55 halves ($13,582,066) when
every kept report is added, and in 8 ($267,586, the largest Rangel for Congress's second half of 2009) when only
the innermost are (Q10c–d). Where the semi-annual figure is higher (Q10e), a lobbyist crossed the
threshold over six months but in no shorter period: DCCC's first half of 2024, $6.70M against
$5.59M. 59 halves have only a semi-annual figure and 85 only period amounts (Q10b), which is why
the total takes the greater. **2024 under the adopted rule: $57,262,231 at 84 recipients**, the
figure NEU-2175's definition of done is within 1% of.

```python
# Q10: the bundled total: per committee and half-year, the half-year figure, the period amounts
# added, and the greater (spec §1.1); per cycle, all three. Beside them the second reading (Q9e):
# only the innermost kept reports' period amounts added.
bun_halves()
show("Q10a per cycle: the three totals and recipients, and the second reading", """
    SELECT cycle, count(DISTINCT cid) AS recipients, count(*) AS halves,
        sum(hf) AS half_year_figures, sum(ps) AS period_amounts, sum(g) AS greater_of,
        sum(ps_inner) AS period_amounts_inner, sum(g_inner) AS greater_of_inner,
        sum(outer_reports) AS reports_left_out
    FROM bh GROUP BY 1 ORDER BY 1""")
show("Q10b halves by which figures they have", """
    SELECT hf IS NOT NULL AS has_half_year_figure, coalesce(ps, 0) > 0 AS has_period_amounts,
        count(*) AS halves, sum(hf) AS hf_sum, sum(ps) AS ps_sum, sum(g) AS g_sum, sum(g_inner) AS g_inner_sum
    FROM bh GROUP BY ALL ORDER BY ALL""")
show("Q10c halves where the half-year figure is below the periods' sum (the asserted fact failing)", """
    SELECT 'all kept reports' AS reading, count(*) AS halves, sum(ps - hf) AS shortfall,
        count(*) FILTER (WHERE ps - hf > 1) AS by_over_1_dollar
    FROM bh WHERE hf < ps
    UNION ALL
    SELECT 'innermost reports', count(*), sum(ps_inner - hf), count(*) FILTER (WHERE ps_inner - hf > 1)
    FROM bh WHERE hf < ps_inner""")
show("Q10d halves where the half-year figure is below the innermost periods' sum (20, largest first)", """
    SELECT bh.cid, (SELECT any_value(Committee_Name) FROM bun WHERE bun.cid = bh.cid) AS name, bh.half,
        bh.hf, bh.ps, bh.ps_inner, bh.ps_inner - bh.hf AS shortfall, bh.reports
    FROM bh WHERE bh.hf < bh.ps_inner ORDER BY shortfall DESC LIMIT 20""")
show("Q10e halves where the half-year figure exceeds the innermost periods' sum (20, largest first)", """
    SELECT cid, half, hf, ps_inner, hf - coalesce(ps_inner, 0) AS excess, reports FROM bh
    WHERE hf > coalesce(ps_inner, 0) ORDER BY excess DESC LIMIT 20""")
show("Q10f 2024's 20 largest recipients", """
    SELECT bh.cid, (SELECT any_value(Committee_Name) FROM bun WHERE bun.cid = bh.cid) AS name,
        sum(hf) AS hf, sum(ps) AS ps, sum(g) AS greater_of, sum(ps_inner) AS ps_inner,
        sum(g_inner) AS greater_of_inner, count(*) AS halves
    FROM bh WHERE cycle = 2024 GROUP BY 1 ORDER BY greater_of_inner DESC LIMIT 20""")
```

Output:

**Q10a per cycle: the three totals and recipients, and the second reading  (0 s)**

| cycle | recipients | halves | half_year_figures | period_amounts | greater_of | period_amounts_inner | greater_of_inner | reports_left_out |
|---|---|---|---|---|---|---|---|---|
| 2010 | 92 | 158 | 15,870,959 | 13,847,720 | 17,258,622 | 13,260,312 | 16,737,764 | 11 |
| 2012 | 65 | 107 | 26,928,591 | 24,164,473 | 28,020,056 | 23,504,718 | 27,498,866 | 10 |
| 2014 | 38 | 65 | 10,052,699 | 8,201,520 | 10,173,486 | 8,070,125 | 10,100,286 | 6 |
| 2016 | 45 | 84 | 37,790,080 | 36,785,706 | 38,501,652 | 36,669,565 | 38,431,722 | 3 |
| 2018 | 45 | 68 | 10,815,427 | 10,412,143 | 11,853,012 | 9,605,161 | 11,110,339 | 2 |
| 2020 | 62 | 100 | 36,179,596 | 44,963,445 | 47,029,810 | 34,622,276 | 36,828,085 | 13 |
| 2022 | 58 | 98 | 16,716,577 | 15,347,302 | 17,168,495 | 14,809,524 | 16,770,812 | 8 |
| 2024 | 84 | 170 | 56,544,915 | 53,150,726 | 58,075,862 | 52,156,278 | 57,262,231 | 7 |
| 2026 | 88 | 166 | 48,715,087 | 48,409,448 | 53,135,574 | 48,141,602 | 52,879,635 | 4 |

**Q10b halves by which figures they have  (0 s)**

| has_half_year_figure | has_period_amounts | halves | hf_sum | ps_sum | g_sum | g_inner_sum |
|---|---|---|---|---|---|---|
| False | False | 220 |  | 0 | 0 | 0 |
| False | True | 85 |  | 8,020,573 | 8,020,573 | 7,738,224 |
| True | False | 59 | 4,724,576 | 0 | 4,724,576 | 4,724,576 |
| True | True | 652 | 254,889,353 | 247,261,910 | 268,471,419 | 255,156,940 |

**Q10c halves where the half-year figure is below the periods' sum (the asserted fact failing)  (0 s)**

| reading | halves | shortfall | by_over_1_dollar |
|---|---|---|---|
| all kept reports | 55 | 13,582,066 | 55 |
| innermost reports | 8 | 267,586 | 8 |

**Q10d halves where the half-year figure is below the innermost periods' sum (20, largest first)  (0 s)**

| cid | name | half | hf | ps | ps_inner | shortfall | reports |
|---|---|---|---|---|---|---|---|
| C00302422 | RANGEL FOR CONGRESS | 2009-2 | 63,900 | 188,789 | 188,789 | 124,889 | 2 |
| C00588772 | MAGGIE FOR NH | 2016-1 | 66,689 | 124,435 | 124,435 | 57,746 | 2 |
| C00463505 | ROBIN SMITH FOR TENNESSEE | 2010-1 | 75,735 | 107,685 | 107,685 | 31,950 | 2 |
| C00326801 | TAMMY BALDWIN FOR SENATE | 2024-1 | 43,959 | 73,688 | 73,688 | 29,729 | 2 |
| C00431171 | ROMNEY FOR PRESIDENT INC. | 2011-2 | 1,647,853 | 1,659,478 | 1,659,478 | 11,625 | 2 |
| C00331439 | UDALL FOR COLORADO | 2013-2 | 38,400 | 44,900 | 44,900 | 6,500 | 2 |
| C00458844 | MARCO RUBIO FOR PRESIDENT | 2015-2 | 1,036,622 | 1,041,734 | 1,041,734 | 5,112 | 2 |
| C00711549 | AMY MCGRATH FOR SENATE, INC. | 2019-2 | 110,504 | 110,540 | 110,540 | 36 | 2 |

**Q10e halves where the half-year figure exceeds the innermost periods' sum (20, largest first)  (0 s)**

| cid | half | hf | ps_inner | excess | reports |
|---|---|---|---|---|---|
| C00000935 | 2026-1 | 16,119,376 | 13,406,776 | 2,712,600 | 5 |
| C00518282 | 2012-2 | 11,955,240 | 10,545,795 | 1,409,446 | 4 |
| C00000935 | 2024-1 | 6,701,908 | 5,588,608 | 1,113,300 | 6 |
| C00867937 | 2024-1 | 6,670,774 | 5,606,174 | 1,064,600 | 1 |
| C00000935 | 2025-1 | 10,868,475 | 9,849,125 | 1,019,350 | 5 |
| C00000935 | 2017-2 | 592,571 | 0 | 592,571 | 1 |
| C00744946 | 2023-2 | 3,269,351 | 2,730,751 | 538,600 | 2 |
| C00586537 | 2016-2 | 14,771,033 | 14,252,483 | 518,549 | 4 |
| C00027466 | 2013-1 | 482,800 | 0 | 482,800 | 1 |
| C00010603 | 2020-2 | 878,478 | 457,934 | 420,544 | 4 |
| C00027466 | 2009-1 | 408,500 | 0 | 408,500 | 1 |
| C00042366 | 2009-1 | 787,700 | 399,750 | 387,950 | 3 |
| C00042366 | 2014-1 | 1,780,383 | 1,403,399 | 376,984 | 6 |
| C00027466 | 2010-2 | 623,600 | 274,900 | 348,700 | 2 |
| C00027466 | 2009-2 | 333,550 | 0 | 333,550 | 1 |
| C00042366 | 2020-2 | 1,199,848 | 870,850 | 328,998 | 4 |
| C00000935 | 2025-2 | 1,454,086 | 1,131,786 | 322,300 | 3 |
| C00042366 | 2013-1 | 1,224,230 | 919,400 | 304,830 | 6 |
| C00075820 | 2009-1 | 299,600 | 0 | 299,600 | 1 |
| C00042366 | 2012-1 | 1,535,918 | 1,239,726 | 296,192 | 6 |

**Q10f 2024's 20 largest recipients  (0 s)**

| cid | name | hf | ps | greater_of | ps_inner | greater_of_inner | halves |
|---|---|---|---|---|---|---|---|
| C00867937 | TRUMP 47 COMMITTEE, INC. | 10,293,939 | 9,185,798 | 10,293,939 | 9,185,798 | 10,293,939 | 2 |
| C00042366 | DEMOCRATIC SENATORIAL CAMPAIGN COMMITTEE | 9,841,143 | 9,382,059 | 9,841,143 | 9,382,059 | 9,841,143 | 4 |
| C00744946 | HARRIS VICTORY FUND | 9,699,650 | 9,110,863 | 9,699,650 | 9,110,863 | 9,699,650 | 3 |
| C00000935 | DEMOCRATIC CONGRESSIONAL CAMPAIGN COMMITTEE | 8,104,058 | 6,869,558 | 8,104,058 | 6,869,558 | 8,104,058 | 4 |
| C00842336 | BELL FOR MISSOURI | 3,167,971 | 3,166,329 | 3,167,971 | 3,166,329 | 3,167,971 | 2 |
| C00606939 | ROSEN FOR NEVADA | 1,829,265 | 1,829,265 | 1,829,265 | 1,829,265 | 1,829,265 | 4 |
| C00264564 | MENENDEZ FOR SENATE | 831,950 | 1,081,865 | 1,081,865 | 1,081,865 | 1,081,865 | 2 |
| C00431056 | BOB CASEY FOR SENATE INC | 950,589 | 912,876 | 950,589 | 912,876 | 950,589 | 4 |
| C00770941 | TRUMP SAVE AMERICA JOINT FUNDRAISING COMMITTEE | 903,350 | 903,350 | 903,350 | 903,350 | 903,350 | 1 |
| C00264697 | FRIENDS OF SHERROD BROWN | 874,246 | 831,728 | 874,246 | 831,728 | 874,246 | 4 |
| C00573949 | JOSH GOTTHEIMER FOR CONGRESS | 852,447 | 749,877 | 852,447 | 749,877 | 852,447 | 4 |
| C00795211 | DON DAVIS FOR NC | 846,075 | 1,397,064 | 1,415,760 | 827,379 | 846,075 | 4 |
| C00010603 | DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE | 719,394 | 331,402 | 719,394 | 331,402 | 719,394 | 4 |
| C00653816 | COMMITTEE TO ELECT JARED GOLDEN | 597,292 | 578,641 | 597,292 | 578,641 | 597,292 | 4 |
| C00413914 | GILLIBRAND FOR SENATE | 382,498 | 452,521 | 465,727 | 452,521 | 465,727 | 4 |
| C00703975 | BIDEN FOR PRESIDENT | 436,945 | 358,302 | 436,945 | 358,302 | 436,945 | 3 |
| C00541888 | KATHERINE CLARK FOR CONGRESS | 429,242 | 389,977 | 429,242 | 389,977 | 429,242 | 4 |
| C00832584 | JOANNA WEISS FOR CONGRESS | 394,849 | 388,489 | 394,849 | 388,489 | 394,849 | 1 |
| C00839597 | COLIN ALLRED FOR SENATE | 372,665 | 327,145 | 372,665 | 327,145 | 372,665 | 4 |
| C00343871 | SCHIFF FOR SENATE | 335,340 | 311,165 | 335,340 | 311,165 | 335,340 | 3 |
EXIT 0 2026-11-25T18:37:42Z

## Q11: bundled against counted money (2024)

Every 2024 recipient's bundled total is within its counted individual contributions (gold
`committee_cycle.total_individual`), as the milestone's contract assumes: $57.3M against $2.55B.
Ten recipients with no individual total bundled $0; of the other 74, 10 bundled 20% or more of their individual total (Q11a–b).

```python
# Q11: bundled against counted money (2024): each recipient's bundled total beside gold
# committee_cycle's individual and committee totals.
bun_halves()
out = work / "gold_cc_2024.csv"
with psycopg.connect(settings.database_url) as pg, out.open("w", newline="") as f:
    pg.read_only = True
    w = csv.writer(f)
    w.writerow(["cid", "total_individual", "total_from_committees", "total_from_organizations"])
    for row in pg.execute("SELECT committee_id, total_individual, total_from_committees,"
                          " total_from_organizations FROM gold.committee_cycle WHERE cycle = 2024"):
        w.writerow(row)
con.execute(f"""CREATE TABLE gcc AS SELECT cid, total_individual::DECIMAL(16, 2) AS total_individual,
    total_from_committees::DECIMAL(16, 2) AS total_from_committees,
    total_from_organizations::DECIMAL(16, 2) AS total_from_organizations
    FROM read_csv({literal(out)}, header = true, all_varchar = true)""")
con.execute("""
    CREATE TABLE q11 AS
    SELECT bh.cid, (SELECT any_value(Committee_Name) FROM bun WHERE bun.cid = bh.cid) AS name,
        sum(bh.g_inner) AS bundled, sum(bh.g) AS bundled_all_periods, any_value(g.total_individual) AS total_individual,
        any_value(g.total_from_committees) AS total_from_committees,
        any_value(g.total_from_organizations) AS total_from_organizations
    FROM bh LEFT JOIN gcc AS g USING (cid) WHERE bh.cycle = 2024 GROUP BY 1""")
show("Q11a 2024 recipients: bundled against total_individual", """
    SELECT CASE WHEN total_individual IS NULL THEN 'no gold row'
                WHEN bundled <= total_individual THEN 'bundled within individual total'
                ELSE 'bundled exceeds individual total' END AS how,
        count(*) AS recipients, sum(bundled) AS bundled, sum(total_individual) AS total_individual
    FROM q11 GROUP BY 1 ORDER BY 1""")
show("Q11b bundled as a share of total_individual, distribution", """
    SELECT CASE WHEN bundled / total_individual < 0.01 THEN 'under 1%' WHEN bundled / total_individual < 0.05 THEN '1-5%'
                WHEN bundled / total_individual < 0.2 THEN '5-20%' WHEN bundled / total_individual <= 1 THEN '20-100%'
                ELSE 'over 100%' END AS share, count(*) AS recipients
    FROM q11 WHERE total_individual > 0 GROUP BY 1 ORDER BY min(bundled / total_individual)""")
show("Q11c every recipient whose bundled total (innermost reading) exceeds its individual total", """
    SELECT cid, name, bundled, bundled_all_periods, total_individual, total_from_committees, total_from_organizations,
        bundled - total_individual AS excess
    FROM q11 WHERE total_individual IS NULL OR bundled > total_individual ORDER BY excess DESC NULLS FIRST""")
```

Output:

**Q11a 2024 recipients: bundled against total_individual  (0 s)**

| how | recipients | bundled | total_individual |
|---|---|---|---|
| bundled within individual total | 84 | 57,262,231 | 2,552,783,706 |

**Q11b bundled as a share of total_individual, distribution  (0 s)**

| share | recipients |
|---|---|
| under 1% | 21 |
| 1-5% | 31 |
| 5-20% | 12 |
| 20-100% | 10 |

**Q11c every recipient whose bundled total (innermost reading) exceeds its individual total  (0 s)**

| cid | name | bundled | bundled_all_periods | total_individual | total_from_committees | total_from_organizations | excess |
|---|---|---|---|---|---|---|---|
EXIT 0 2026-11-25T18:37:45Z

## Q12: every cycle's leadership file, 2010–2026

Every even cycle 2010–2026 has a file with 2024's header and one row per committee; 2008 and odd
years are 404s. Blank sponsors run 206 to 341 a cycle; rung 2 matches 82–94% of named sponsors to a candidate,
rising with the cycle, a few of them to several ids (Q12a).

By id against OpenFEC, rung 2 meets the 99% bar only in 2024 (Q12b: 92.77% in 2010 to 98.67% in
2026), because OpenFEC gives each PAC's sponsor under their current id (Q14 reads it by person).
The blanks OpenFEC names a sponsor for are 73–86% of each cycle's blanks. The flag's bar against
`D` is met in six cycles and missed in 2014, 2016 and 2026 by 4 to 11 committees (Q12c). Q12d
counts the list rows each rung would need as first tested (`residue`), before the checkpoint
changed what a list row is for; Q16 builds the list under the adopted rule.

```python
# Q12: every cycle's leadership<yyyy>.csv, 2010-2026: shape, the rule's rungs, OpenFEC's check,
# designation D, and the list rows each cycle needs. Odd years probed too.
for year in (2009, 2011, 2023, 2025, 2008):
    try:
        with urlopen(Request(f"{FEC}/data.fec.gov/leadership{year}.csv", method="HEAD",
                             headers={"User-Agent": USER_AGENT})) as r:
            print(f"leadership{year}.csv: {r.status}")
    except HTTPError as e:
        print(f"leadership{year}.csv: {e.code}")
rows = []
for c in CYCLES:
    if not lead(c):
        rows.append(f"SELECT {c} AS cycle, false AS header_as_2024")
        continue
    agree(c)
    cmte(c)
    for n in (1, 2):
        residue(c, n)
    rows.append(f"""
        SELECT {c} AS cycle, true AS header_as_2024,
            (SELECT count(*) FROM lead_{c}) AS rows,
            (SELECT count(*) - count(DISTINCT cid) FROM lead_{c}) AS rows_beyond_one_per_cmte,
            (SELECT count(*) FILTER (WHERE sponsor IS NULL) FROM lead_{c}) AS blank,
            (SELECT count(*) FILTER (WHERE r1_id IS NOT NULL) FROM m_{c}) AS r1_id,
            (SELECT count(*) FILTER (WHERE r2_id IS NOT NULL) FROM m_{c}) AS r2_id,
            (SELECT count(*) FILTER (WHERE r2 = 'several people') FROM m_{c}) AS r2_several,
            (SELECT count(*) FROM m_{c}) AS named,
            (SELECT count(*) FILTER (WHERE a1 IN ('agree', 'same person')) FROM a_{c}) AS r1_agree,
            (SELECT count(*) FILTER (WHERE a1 = 'disagree') FROM a_{c}) AS r1_disagree,
            (SELECT count(*) FILTER (WHERE a2 IN ('agree', 'same person')) FROM a_{c}) AS r2_agree,
            (SELECT count(*) FILTER (WHERE a2 = 'disagree') FROM a_{c}) AS r2_disagree,
            (SELECT count(*) FILTER (WHERE a2 IN ('OpenFEC none', 'OpenFEC lacks')) FROM a_{c}) AS unchecked,
            (SELECT count(*) FILTER (WHERE sponsor IS NULL AND len(o_ids) > 0) FROM a_{c}) AS blank_openfec_names,
            (SELECT count(*) FILTER (WHERE designation = 'D') FROM cmte_{c}) AS cm_d,
            (SELECT count(*) FROM lead_{c} JOIN cmte_{c} USING (cid) WHERE designation = 'D') AS file_and_d,
            (SELECT count(*) FROM lead_{c} WHERE cid NOT IN (SELECT cid FROM cmte_{c})) AS file_not_in_cm,
            (SELECT count(*) FROM res1_{c}) AS list_rows_r1, (SELECT count(*) FROM res2_{c}) AS list_rows_r2""")
con.execute("CREATE TABLE q12 AS " + " UNION ALL BY NAME ".join(rows))
for c in CYCLES:
    meta = work / f"leadership{c}.csv.meta"
    print(meta.read_text() if meta.exists() else f"{c}: no file")
show("Q12a shape and the rule's rungs per cycle", """
    SELECT cycle, header_as_2024, rows, rows_beyond_one_per_cmte, blank, named, r1_id, r2_id, r2_several,
        r2_id / named AS r2_rate
    FROM q12 ORDER BY cycle""")
show("Q12b agreement with OpenFEC per cycle (99% bar on each rung)", """
    SELECT cycle, r1_agree, r1_disagree, r1_agree / nullif(r1_agree + r1_disagree, 0) AS r1_agreement,
        r2_agree, r2_disagree, r2_agree / nullif(r2_agree + r2_disagree, 0) AS r2_agreement,
        unchecked, blank_openfec_names, blank_openfec_names / nullif(blank, 0) AS blank_share_named
    FROM q12 ORDER BY cycle""")
show("Q12c agreement with designation D per cycle (99% bar both ways)", """
    SELECT cycle, rows, cm_d, file_and_d, file_and_d / rows AS file_in_d, file_and_d / nullif(cm_d, 0) AS d_in_file,
        file_not_in_cm
    FROM q12 ORDER BY cycle""")
show("Q12d list rows per cycle under each rung", """
    SELECT cycle, list_rows_r1, list_rows_r2 FROM q12 ORDER BY cycle""")
```

Output:

builds {2010: '20261114T020123Z', 2012: '20261114T180514Z', 2014: '20261114T182542Z', 2016: '20261114T184036Z', 2018: '20261116T001733Z', 2020: '20261115T033259Z', 2022: '20261115T173437Z', 2024: '20261125T021311Z', 2026: '20261123T224142Z'} | cycles without a build: [] | duckdb v2.0.0 | Limits(memory_limit='32GB', max_temp_directory_size='60GB', threads=6) | commit {'SOURCE_COMMIT': ''}
leadership2009.csv: 404
leadership2011.csv: 404
leadership2023.csv: 404
leadership2025.csv: 404
leadership2008.csv: 404
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2010.csv | Last-Modified: Thu, 02 Jan 2025 10:13:34 GMT | bytes 61,357 | downloaded 2026-11-25T17:59:10+00:00
leadraw_2010: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2010: 440 committees (33 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2012.csv | Last-Modified: Thu, 02 Jan 2025 10:13:36 GMT | bytes 77,483 | downloaded 2026-11-25T17:59:31+00:00
leadraw_2012: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2012: 556 committees (48 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2014.csv | Last-Modified: Thu, 02 Jan 2025 10:13:38 GMT | bytes 80,944 | downloaded 2026-11-25T17:59:49+00:00
leadraw_2014: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2014: 598 committees (52 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2016.csv | Last-Modified: Thu, 02 Jan 2025 10:13:40 GMT | bytes 84,209 | downloaded 2026-11-25T18:00:11+00:00
leadraw_2016: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2016: 638 committees (57 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2018.csv | Last-Modified: Thu, 02 Jan 2025 10:13:42 GMT | bytes 97,197 | downloaded 2026-11-25T18:00:32+00:00
leadraw_2018: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2018: 689 committees (65 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2020.csv | Last-Modified: Thu, 02 Jan 2025 10:13:44 GMT | bytes 103,560 | downloaded 2026-11-25T18:00:54+00:00
leadraw_2020: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2020: 749 committees (65 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2022.csv | Last-Modified: Wed, 25 Nov 2026 10:10:57 GMT | bytes 109,905 | downloaded 2026-11-25T18:01:20+00:00
leadraw_2022: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2022: 798 committees (49 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2024.csv | Last-Modified: Wed, 25 Nov 2026 10:10:59 GMT | bytes 120,104 | downloaded 2026-11-25T17:51:32+00:00
leadraw_2024: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2024: 847 committees (32 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2026.csv | Last-Modified: Wed, 25 Nov 2026 10:11:01 GMT | bytes 133,894 | downloaded 2026-11-25T18:01:47+00:00
leadraw_2026: 8 columns: Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date, Total_Disbursement, Total_Receipt; records of another width: 0
OpenFEC 2026: 943 committees (1 of the file's fetched by id)
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2010.csv | Last-Modified: Thu, 02 Jan 2025 10:13:34 GMT | bytes 61,357 | downloaded 2026-11-25T17:59:10+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2012.csv | Last-Modified: Thu, 02 Jan 2025 10:13:36 GMT | bytes 77,483 | downloaded 2026-11-25T17:59:31+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2014.csv | Last-Modified: Thu, 02 Jan 2025 10:13:38 GMT | bytes 80,944 | downloaded 2026-11-25T17:59:49+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2016.csv | Last-Modified: Thu, 02 Jan 2025 10:13:40 GMT | bytes 84,209 | downloaded 2026-11-25T18:00:11+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2018.csv | Last-Modified: Thu, 02 Jan 2025 10:13:42 GMT | bytes 97,197 | downloaded 2026-11-25T18:00:32+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2020.csv | Last-Modified: Thu, 02 Jan 2025 10:13:44 GMT | bytes 103,560 | downloaded 2026-11-25T18:00:54+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2022.csv | Last-Modified: Wed, 25 Nov 2026 10:10:57 GMT | bytes 109,905 | downloaded 2026-11-25T18:01:20+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2024.csv | Last-Modified: Wed, 25 Nov 2026 10:10:59 GMT | bytes 120,104 | downloaded 2026-11-25T17:51:32+00:00
https://www.fec.gov/files/bulk-downloads/data.fec.gov/leadership2026.csv | Last-Modified: Wed, 25 Nov 2026 10:11:01 GMT | bytes 133,894 | downloaded 2026-11-25T18:01:47+00:00

**Q12a shape and the rule's rungs per cycle  (0 s)**

| cycle | header_as_2024 | rows | rows_beyond_one_per_cmte | blank | named | r1_id | r2_id | r2_several | r2_rate |
|---|---|---|---|---|---|---|---|---|---|
| 2010 | True | 422 | 0 | 206 | 216 | 113 | 180 | 5 | 83.33% |
| 2012 | True | 535 | 0 | 258 | 277 | 147 | 227 | 8 | 81.95% |
| 2014 | True | 559 | 0 | 274 | 285 | 156 | 241 | 6 | 84.56% |
| 2016 | True | 582 | 0 | 291 | 291 | 164 | 254 | 5 | 87.29% |
| 2018 | True | 673 | 0 | 323 | 350 | 208 | 313 | 5 | 89.43% |
| 2020 | True | 726 | 0 | 341 | 385 | 245 | 346 | 5 | 89.87% |
| 2022 | True | 764 | 0 | 302 | 462 | 328 | 419 | 12 | 90.69% |
| 2024 | True | 833 | 0 | 288 | 545 | 405 | 501 | 15 | 91.93% |
| 2026 | True | 933 | 0 | 290 | 643 | 500 | 603 | 11 | 93.78% |

**Q12b agreement with OpenFEC per cycle (99% bar on each rung)  (0 s)**

| cycle | r1_agree | r1_disagree | r1_agreement | r2_agree | r2_disagree | r2_agreement | unchecked | blank_openfec_names | blank_share_named |
|---|---|---|---|---|---|---|---|---|---|
| 2010 | 93 | 11 | 89.42% | 154 | 12 | 92.77% | 15 | 151 | 73.30% |
| 2012 | 120 | 13 | 90.23% | 198 | 11 | 94.74% | 21 | 191 | 74.03% |
| 2014 | 131 | 9 | 93.57% | 211 | 10 | 95.48% | 24 | 211 | 77.01% |
| 2016 | 138 | 10 | 93.24% | 225 | 9 | 96.15% | 23 | 220 | 75.60% |
| 2018 | 182 | 6 | 96.81% | 282 | 7 | 97.58% | 33 | 254 | 78.64% |
| 2020 | 221 | 6 | 97.36% | 318 | 5 | 98.45% | 33 | 276 | 80.94% |
| 2022 | 310 | 6 | 98.10% | 400 | 6 | 98.52% | 18 | 248 | 82.12% |
| 2024 | 391 | 6 | 98.49% | 489 | 4 | 99.19% | 9 | 242 | 84.03% |
| 2026 | 491 | 7 | 98.59% | 592 | 8 | 98.67% | 6 | 248 | 85.52% |

**Q12c agreement with designation D per cycle (99% bar both ways)  (0 s)**

| cycle | rows | cm_d | file_and_d | file_in_d | d_in_file | file_not_in_cm |
|---|---|---|---|---|---|---|
| 2010 | 422 | 423 | 422 | 100.00% | 99.76% | 0 |
| 2012 | 535 | 538 | 535 | 100.00% | 99.44% | 0 |
| 2014 | 559 | 563 | 555 | 99.28% | 98.58% | 0 |
| 2016 | 582 | 576 | 572 | 98.28% | 99.31% | 0 |
| 2018 | 673 | 678 | 673 | 100.00% | 99.26% | 0 |
| 2020 | 726 | 731 | 726 | 100.00% | 99.32% | 0 |
| 2022 | 764 | 771 | 764 | 100.00% | 99.09% | 0 |
| 2024 | 833 | 839 | 833 | 100.00% | 99.28% | 0 |
| 2026 | 933 | 940 | 929 | 99.57% | 98.83% | 4 |

**Q12d list rows per cycle under each rung  (0 s)**

| cycle | list_rows_r1 | list_rows_r2 |
|---|---|---|
| 2010 | 108 | 47 |
| 2012 | 136 | 58 |
| 2014 | 129 | 50 |
| 2016 | 129 | 43 |
| 2018 | 134 | 35 |
| 2020 | 128 | 32 |
| 2022 | 132 | 43 |
| 2024 | 142 | 45 |
| 2026 | 143 | 45 |
EXIT 0 2026-11-25T18:37:59Z

## Q13: what NEU-2179 checks

For NEU-2179. Each of 2024's ten largest leadership PACs with a sponsor in the file agrees with
OpenFEC by id (Q13a; Alamo PAC, Cornyn's, only by rung 2). The five largest recipients' bundled
totals under the adopted rule, with the kept reports and halves behind each (Q13b–d): Trump 47
Committee $10,293,939, DSCC $9,841,143, Harris Victory Fund $9,699,650, DCCC $8,104,058, Bell for
Missouri $3,167,971. None has a report left out by the innermost reading, so the two readings
agree on all five.

```python
# Q13: what NEU-2179 checks: 2024's ten largest leadership PACs with a matched sponsor, and five
# recipients' bundled totals with the kept reports behind each.
agree(2024)
rt(2024)
bun_halves()
show("Q13a 2024's ten leadership PACs with the largest receipts and a matched sponsor (rung 2)", """
    SELECT a.cid, a.name, r.receipts, a.sponsor, a.r1_id, a.r2_id, a.o_ids, a.a2
    FROM a_2024 AS a LEFT JOIN rt_2024 AS r ON r.committee_id = a.cid
    WHERE a.r2_id IS NOT NULL ORDER BY r.receipts DESC NULLS LAST LIMIT 10""")
con.execute("""
    CREATE TABLE five AS
    SELECT cid, sum(g_inner) AS bundled FROM bh WHERE cycle = 2024 GROUP BY 1 ORDER BY 2 DESC LIMIT 5""")
show("Q13b five recipients' bundled totals (2024's five largest)", """
    SELECT f.cid, (SELECT any_value(Committee_Name) FROM bun WHERE bun.cid = f.cid) AS name, f.bundled,
        (SELECT sum(hf) FROM bh WHERE bh.cid = f.cid AND cycle = 2024) AS hf,
        (SELECT sum(ps) FROM bh WHERE bh.cid = f.cid AND cycle = 2024) AS ps,
        (SELECT sum(ps_inner) FROM bh WHERE bh.cid = f.cid AND cycle = 2024) AS ps_inner,
        (SELECT sum(g) FROM bh WHERE bh.cid = f.cid AND cycle = 2024) AS greater_of_all_periods
    FROM five AS f ORDER BY bundled DESC""")
show("Q13c the kept reports behind them", """
    SELECT cid, half, cs, ce, Report_Type, rdt, img, q, s FROM bun
    WHERE kept AND cycle = 2024 AND cid IN (SELECT cid FROM five) ORDER BY cid, ce, rdt""")
show("Q13d their halves", """
    SELECT cid, half, hf, ps, g, ps_inner, g_inner, reports, outer_reports FROM bh WHERE cycle = 2024 AND cid IN (SELECT cid FROM five)
    ORDER BY cid, half""")
```

Output:

**Q13a 2024's ten leadership PACs with the largest receipts and a matched sponsor (rung 2)  (0 s)**

| cid | name | receipts | sponsor | r1_id | r2_id | o_ids | a2 |
|---|---|---|---|---|---|---|---|
| C00271338 | AMERIPAC: THE FUND FOR A GREATER AMERICA | 9,067,547 | HOYER, STENY | H2MD05155 | H2MD05155 | ['H2MD05155'] | agree |
| C00344234 | PAC TO THE FUTURE | 7,955,840 | PELOSI, NANCY | H8CA05035 | H8CA05035 | ['H8CA05035'] | agree |
| C00807412 | HELLFIRE PAC | 4,438,318 | HUNT, WESLEY | H0TX07170 | H0TX07170 | ['H0TX07170'] | agree |
| C00685552 | MEDICARE FOR ALL | 3,798,113 | JAYAPAL, PRAMILA | H6WA07458 | H6WA07458 | ['H6WA07458'] | agree |
| C00841148 | GREAT AMERICAN COMEBACK | 3,725,008 | DESANTIS, RON | P40013039 | P40013039 | ['P40013039'] | agree |
| C00617803 | JOBS, EDUCATION, & FAMILIES FIRST  JEFF PAC | 3,492,969 | JEFFRIES, HAKEEM | H2NY10092 | H2NY10092 | ['H2NY10092'] | agree |
| C00574970 | FAIR SHOT PAC | 3,214,307 | CLARK, KATHERINE | H4MA05084 | H4MA05084 | ['H4MA05084'] | agree |
| C00416131 | MIDWEST VALUES PAC | 2,649,578 | FRANKEN, AL | S8MN00438 | S8MN00438 | ['S8MN00438'] | agree |
| C00387464 | ALAMO PAC | 2,496,636 | CORNYN, JOHN |  | S2TX00106 | ['S2TX00106'] | agree |
| C00872804 | DEFEND FREEDOM, INC. | 2,425,025 | GABBARD, TULSI | H2HI02508 | H2HI02508 | ['H2HI02508'] | agree |

**Q13b five recipients' bundled totals (2024's five largest)  (0 s)**

| cid | name | bundled | hf | ps | ps_inner | greater_of_all_periods |
|---|---|---|---|---|---|---|
| C00867937 | TRUMP 47 COMMITTEE, INC. | 10,293,939 | 10,293,939 | 9,185,798 | 9,185,798 | 10,293,939 |
| C00042366 | DEMOCRATIC SENATORIAL CAMPAIGN COMMITTEE | 9,841,143 | 9,841,143 | 9,382,059 | 9,382,059 | 9,841,143 |
| C00744946 | BIDEN VICTORY FUND | 9,699,650 | 9,699,650 | 9,110,863 | 9,110,863 | 9,699,650 |
| C00000935 | DEMOCRATIC CONGRESSIONAL CAMPAIGN COMMITTEE | 8,104,058 | 8,104,058 | 6,869,558 | 6,869,558 | 8,104,058 |
| C00842336 | BELL FOR MISSOURI | 3,167,971 | 3,167,971 | 3,166,329 | 3,166,329 | 3,167,971 |

**Q13c the kept reports behind them  (0 s)**

| cid | half | cs | ce | Report_Type | rdt | img | q | s |
|---|---|---|---|---|---|---|---|---|
| C00000935 | 2023-1 | 2023-01-01 | 2023-01-31 | FEBRUARY MONTHLY | 2023-07-20 | 202307209583944202 | 205,050 | 0 |
| C00000935 | 2023-1 | 2023-02-01 | 2023-02-28 | MARCH MONTHLY | 2023-03-17 | 202303179579315861 | 42,000 | 0 |
| C00000935 | 2023-1 | 2023-03-01 | 2023-03-31 | APRIL MONTHLY | 2023-04-20 | 202304209581142010 | 35,000 | 0 |
| C00000935 | 2023-1 | 2023-04-01 | 2023-04-30 | MAY MONTHLY | 2023-05-17 | 202305179581532695 | 30,000 | 0 |
| C00000935 | 2023-1 | 2023-06-01 | 2023-06-30 | MONTHLY SEMI-ANNUAL (MY) | 2023-07-19 | 202307199583843530 | 0 | 358,000 |
| C00000935 | 2023-2 | 2023-07-01 | 2023-07-31 | AUGUST MONTHLY | 2024-01-31 | 202401319601160200 | 350,575 | 0 |
| C00000935 | 2023-2 | 2023-09-01 | 2023-09-30 | OCTOBER MONTHLY | 2024-01-31 | 202401319601163803 | 142,600 | 0 |
| C00000935 | 2023-2 | 2023-12-01 | 2023-12-31 | MONTHLY SEMI-ANNUAL (YE) | 2024-01-31 | 202401319601144663 | 0 | 510,375 |
| C00000935 | 2024-1 | 2024-01-01 | 2024-01-31 | FEBRUARY MONTHLY | 2024-07-19 | 202407199661301560 | 786,480 | 0 |
| C00000935 | 2024-1 | 2024-02-01 | 2024-02-29 | MARCH MONTHLY | 2024-03-20 | 202403209622534396 | 1,186,300 | 0 |
| C00000935 | 2024-1 | 2024-03-01 | 2024-03-31 | APRIL MONTHLY | 2024-07-19 | 202407199661302469 | 2,709,778 | 0 |
| C00000935 | 2024-1 | 2024-04-01 | 2024-04-30 | MAY MONTHLY | 2024-05-17 | 202405179646058555 | 363,450 | 0 |
| C00000935 | 2024-1 | 2024-05-01 | 2024-05-31 | JUNE MONTHLY | 2024-06-20 | 202406209649283864 | 386,500 | 0 |
| C00000935 | 2024-1 | 2024-06-01 | 2024-06-30 | JULY MONTHLY / SEMI-ANNUAL | 2026-10-23 | 202610239945196723 | 156,100 | 6,701,908 |
| C00000935 | 2024-2 | 2024-07-01 | 2024-07-31 | AUGUST MONTHLY | 2024-08-15 | 202408159666196097 | 282,600 | 0 |
| C00000935 | 2024-2 | 2024-09-01 | 2024-09-30 | OCTOBER MONTHLY | 2024-10-18 | 202410189699170508 | 167,400 | 0 |
| C00000935 | 2024-2 | 2024-10-01 | 2024-10-16 | PRE-GENERAL | 2024-10-23 | 202410239710132472 | 25,725 | 0 |
| C00000935 | 2024-2 | 2024-11-26 | 2024-12-31 | MONTHLY SEMI-ANNUAL (YE) | 2025-01-29 | 202501299748055336 | 0 | 533,775 |
| C00042366 | 2023-1 | 2023-01-01 | 2023-06-30 | QUARTERLY MID-YEAR / SEMI-ANN | 2023-07-31 | 202307319584181565 | 5,302,084 | 5,302,084 |
| C00042366 | 2023-2 | 2023-07-01 | 2023-12-31 | QUARTERLY YEAR END / SEMI-ANN | 2024-01-31 | 202401319600726048 | 320,398 | 320,398 |
| C00042366 | 2024-1 | 2024-01-01 | 2024-03-31 | APRIL QUARTERLY | 2024-04-15 | 202404159627949601 | 2,518,542 | 0 |
| C00042366 | 2024-1 | 2024-04-01 | 2024-06-30 | JULY QUARTERLY / SEMI-ANNUAL | 2024-07-15 | 202407159653377149 | 368,042 | 3,150,084 |
| C00042366 | 2024-2 | 2024-07-01 | 2024-09-30 | OCTOBER QUARTERLY | 2024-10-15 | 202410159685335795 | 872,992 | 0 |
| C00042366 | 2024-2 | 2024-11-26 | 2024-12-31 | QUARTERLY SEMI-ANNUAL (YE) | 2025-01-31 | 202501319748746803 | 0 | 1,068,576 |
| C00744946 | 2023-2 | 2023-07-01 | 2023-09-30 | OCTOBER QUARTERLY | 2023-10-15 | 202310159598405696 | 224,286 | 0 |
| C00744946 | 2023-2 | 2023-10-01 | 2023-12-31 | QUARTERLY YEAR END / SEMI-ANN | 2024-01-31 | 202401319619373289 | 2,506,465 | 3,269,351 |
| C00744946 | 2024-1 | 2024-04-01 | 2024-06-30 | JULY QUARTERLY / SEMI-ANNUAL | 2024-07-15 | 202407159660959396 | 1,062,704 | 1,103,761 |
| C00744946 | 2024-2 | 2024-07-01 | 2024-09-30 | OCTOBER QUARTERLY | 2024-10-15 | 202410159689243700 | 3,592,536 | 0 |
| C00744946 | 2024-2 | 2024-10-01 | 2024-10-16 | PRE-GENERAL | 2024-10-24 | 202410249713482723 | 1,164,420 | 0 |
| C00744946 | 2024-2 | 2024-10-17 | 2024-11-25 | POST-GENERAL | 2024-12-05 | 202412059731605977 | 560,452 | 0 |
| C00744946 | 2024-2 | 2024-11-26 | 2024-12-31 | QUARTERLY SEMI-ANNUAL (YE) | 2025-01-31 | 202501319753033210 | 0 | 5,326,539 |
| C00842336 | 2024-1 | 2024-01-01 | 2024-03-31 | APRIL QUARTERLY | 2025-04-15 | 202504159755516034 | 637,464 | 0 |
| C00842336 | 2024-1 | 2024-04-01 | 2024-06-30 | JULY QUARTERLY / SEMI-ANNUAL | 2025-04-15 | 202504159755516392 | 1,890,472 | 2,527,937 |
| C00842336 | 2024-2 | 2024-07-01 | 2024-09-30 | OCTOBER QUARTERLY | 2025-04-15 | 202504159755517858 | 638,392 | 0 |
| C00842336 | 2024-2 | 2024-10-01 | 2024-12-31 | QUARTERLY SEMI-ANNUAL (YE) | 2025-04-15 | 202504159755518115 | 0 | 640,034 |
| C00867937 | 2024-1 | 2024-04-01 | 2024-06-30 | JULY QUARTERLY / SEMI-ANNUAL | 2024-07-15 | 202407159660158200 | 5,606,174 | 6,670,774 |
| C00867937 | 2024-2 | 2024-07-01 | 2024-09-30 | OCTOBER QUARTERLY | 2025-01-31 | 202501319752736325 | 2,598,132 | 0 |
| C00867937 | 2024-2 | 2024-10-01 | 2024-10-16 | PRE-GENERAL | 2025-01-31 | 202501319752736327 | 624,574 | 0 |
| C00867937 | 2024-2 | 2024-10-17 | 2024-11-25 | POST-GENERAL | 2024-12-05 | 202412059731645283 | 356,918 | 0 |
| C00867937 | 2024-2 | 2024-11-26 | 2024-12-31 | QUARTERLY YEAR END / SEMI-ANN | 2025-01-31 | 202501319752736329 | 0 | 3,623,166 |

**Q13d their halves  (0 s)**

| cid | half | hf | ps | g | ps_inner | g_inner | reports | outer_reports |
|---|---|---|---|---|---|---|---|---|
| C00000935 | 2023-1 | 358,000 | 312,050 | 358,000 | 312,050 | 358,000 | 5 | 0 |
| C00000935 | 2023-2 | 510,375 | 493,175 | 510,375 | 493,175 | 510,375 | 3 | 0 |
| C00000935 | 2024-1 | 6,701,908 | 5,588,608 | 6,701,908 | 5,588,608 | 6,701,908 | 6 | 0 |
| C00000935 | 2024-2 | 533,775 | 475,725 | 533,775 | 475,725 | 533,775 | 4 | 0 |
| C00042366 | 2023-1 | 5,302,084 | 5,302,084 | 5,302,084 | 5,302,084 | 5,302,084 | 1 | 0 |
| C00042366 | 2023-2 | 320,398 | 320,398 | 320,398 | 320,398 | 320,398 | 1 | 0 |
| C00042366 | 2024-1 | 3,150,084 | 2,886,584 | 3,150,084 | 2,886,584 | 3,150,084 | 2 | 0 |
| C00042366 | 2024-2 | 1,068,576 | 872,992 | 1,068,576 | 872,992 | 1,068,576 | 2 | 0 |
| C00744946 | 2023-2 | 3,269,351 | 2,730,751 | 3,269,351 | 2,730,751 | 3,269,351 | 2 | 0 |
| C00744946 | 2024-1 | 1,103,761 | 1,062,704 | 1,103,761 | 1,062,704 | 1,103,761 | 1 | 0 |
| C00744946 | 2024-2 | 5,326,539 | 5,317,408 | 5,326,539 | 5,317,408 | 5,326,539 | 4 | 0 |
| C00842336 | 2024-1 | 2,527,937 | 2,527,937 | 2,527,937 | 2,527,937 | 2,527,937 | 2 | 0 |
| C00842336 | 2024-2 | 640,034 | 638,392 | 640,034 | 638,392 | 640,034 | 2 | 0 |
| C00867937 | 2024-1 | 6,670,774 | 5,606,174 | 6,670,774 | 5,606,174 | 6,670,774 | 1 | 0 |
| C00867937 | 2024-2 | 3,623,166 | 3,579,625 | 3,623,166 | 3,579,625 | 3,623,166 | 4 | 0 |
EXIT 0 2026-11-25T18:38:52Z

## Q14: the check, read by person

Run during the checkpoint, from Q12's cached OpenFEC answers. Each rung-2 match OpenFEC does not
confirm by id is classed by OpenFEC's sponsor name against the file's (last name and first given
name). Across all cycles, single-person matches are confirmed in 2,649 cases; in 49 OpenFEC names
the same person under another id, a later office's (Schiff's, Gallego's and Stevens's Senate ids on
their House-era PACs, Q14d); in 23 OpenFEC's name differs, and those are OpenFEC's own errors
(`H20R01240`, a letter O for a zero; Shelley Berkley's name on Ben Ray Luján's id) or one person's
older id (Ron Paul's House id beside his presidential one) (Q14c, Q14e). So a name matching one
person is right.

A name matching several ids is where the rule goes wrong (Q14b): taking the one standing in a race
picks Dan Sullivan of Massachusetts for the Alaska senator's PAC, Michael Simpson of South Carolina
for Idaho's, John Conyers III for John Conyers Jr.'s, and Antonio Delgado of California for New
York's. The checkpoint sent every such name to the list (Decision 3).

```python
# Q14: the check, read by person. OpenFEC gives each PAC's sponsors as they stand today, so a
# sponsor who has since run for another office may be listed under an id the cycle lacks (Brown's
# 2026 Senate id beside his 2024 one). Each rung-2 match that OpenFEC does not confirm by id is
# classed by OpenFEC's sponsor name: the file's own name (last and first given name), so the
# same name under another id; or another name.
allcand()
parts = []
for c in CYCLES:
    agree(c)
    parts.append(f"""
        SELECT {c} AS cycle, a.cid, a.sponsor, a.r2, a.r2_id, a.r2_ids, a.a2, a.o_ids, a.o_names,
            k.name AS rule_name, k.office AS rule_office, k.state AS rule_state, k.race_id AS rule_race,
            list_has_any(list_transform(string_split(coalesce(a.o_names, ''), '|'),
                lambda n: lastn(n) || '/' || firstn(n)), [lastn(a.sponsor) || '/' || firstn(a.sponsor)])
                AS openfec_same_name
        FROM a_{c} AS a LEFT JOIN cand_{c} AS k ON k.candidate_id = a.r2_id
        WHERE a.sponsor IS NOT NULL""")
con.execute("CREATE TABLE q14 AS " + " UNION ALL ".join(parts))
show("Q14a rung 2 against OpenFEC by person, per cycle", """
    SELECT cycle,
        count(*) FILTER (WHERE a2 = 'agree') AS agree_by_id,
        count(*) FILTER (WHERE a2 = 'same person' AND r2 = 'one') AS alias_id,
        count(*) FILTER (WHERE a2 = 'same person' AND r2 <> 'one') AS several_ids_other_picked,
        count(*) FILTER (WHERE a2 = 'disagree' AND openfec_same_name) AS same_name_other_id,
        count(*) FILTER (WHERE a2 = 'disagree' AND NOT openfec_same_name) AS other_name,
        count(*) FILTER (WHERE a2 IN ('OpenFEC none', 'OpenFEC lacks')) AS unchecked,
        count(*) FILTER (WHERE a2 = 'rule none') AS rule_none
    FROM q14 GROUP BY 1 ORDER BY 1""")
show("Q14b rung 2 picked one of several same-named ids and OpenFEC names another (every cycle)", """
    SELECT cycle, cid, sponsor, r2_id, rule_office || ' ' || rule_state AS picked, r2_ids, o_ids, o_names
    FROM q14 WHERE a2 = 'same person' AND r2 <> 'one' ORDER BY cycle, sponsor""")
show("Q14c rung 2 disagreements where OpenFEC's sponsor has another name (every cycle)", """
    SELECT cycle, cid, sponsor, r2_id, rule_name, rule_office || ' ' || rule_state AS picked, o_ids, o_names
    FROM q14 WHERE a2 = 'disagree' AND NOT openfec_same_name ORDER BY cycle, sponsor""")
show("Q14d rung 2 disagreements where OpenFEC names the same name under another id (30)", """
    SELECT q.cycle, q.cid, q.sponsor, q.r2_id, q.rule_office || ' ' || q.rule_state AS picked, q.o_ids,
        (SELECT list(DISTINCT ac.cycles[-1]) FROM allcand AS ac WHERE list_contains(q.o_ids, ac.candidate_id))
            AS openfec_id_last_cycle
    FROM q14 AS q WHERE a2 = 'disagree' AND openfec_same_name ORDER BY cycle DESC, sponsor LIMIT 30""")
show("Q14e rung 2 'one' class against OpenFEC, every cycle: is a single match ever wrong?", """
    SELECT r2, count(*) FILTER (WHERE a2 IN ('agree', 'same person')) AS confirmed,
        count(*) FILTER (WHERE a2 = 'disagree' AND openfec_same_name) AS same_name_other_id,
        count(*) FILTER (WHERE a2 = 'disagree' AND NOT openfec_same_name) AS other_name,
        count(*) FILTER (WHERE a2 IN ('OpenFEC none', 'OpenFEC lacks')) AS unchecked
    FROM q14 WHERE r2_id IS NOT NULL GROUP BY 1 ORDER BY 1""")
```

Output:

**Q14a rung 2 against OpenFEC by person, per cycle  (0 s)**

| cycle | agree_by_id | alias_id | several_ids_other_picked | same_name_other_id | other_name | unchecked | rule_none |
|---|---|---|---|---|---|---|---|
| 2010 | 152 | 0 | 2 | 10 | 2 | 15 | 35 |
| 2012 | 195 | 0 | 3 | 8 | 3 | 21 | 47 |
| 2014 | 208 | 0 | 3 | 8 | 2 | 24 | 40 |
| 2016 | 221 | 0 | 4 | 7 | 2 | 23 | 34 |
| 2018 | 275 | 0 | 7 | 5 | 2 | 33 | 28 |
| 2020 | 310 | 0 | 8 | 4 | 1 | 33 | 29 |
| 2022 | 394 | 0 | 6 | 4 | 2 | 18 | 38 |
| 2024 | 472 | 0 | 17 | 1 | 3 | 9 | 43 |
| 2026 | 573 | 0 | 19 | 2 | 6 | 6 | 37 |

**Q14b rung 2 picked one of several same-named ids and OpenFEC names another (every cycle)  (0 s)**

| cycle | cid | sponsor | r2_id | picked | r2_ids | o_ids | o_names |
|---|---|---|---|---|---|---|---|
| 2010 | C00450247 | BROWN, CORRINE | H2FL03056 | H FL | ['H2FL03056', 'S0FL00403'] | ['S0FL00403'] | BROWN, CORRINE |
| 2010 | C00477067 | GILLIBRAND, KIRSTEN | H6NY20167 | H NY | ['H6NY20167', 'S0NY00410'] | ['S0NY00410'] | GILLIBRAND, KIRSTEN |
| 2012 | C00481242 | AKIN, W TODD | H0MO02148 | H MO | ['H0MO02148', 'S2MO00429'] | ['S2MO00429'] | AKIN, W TODD |
| 2012 | C00489336 | CAPITO, SHELLEY | H0WV02138 | H WV | ['H0WV02138', 'S4WV00159'] | ['S4WV00159'] | CAPITO, SHELLEY MOORE |
| 2012 | C00377663 | HOEKSTRA, PETER | S2MI00193 | S MI | ['H2MI02066', 'S2MI00193'] | ['H2MI02066'] | HOEKSTRA, PETER |
| 2014 | C00448472 | BRALEY, BRUCE | H6IA01098 | H IA | ['H6IA01098', 'S4IA00087'] | ['S4IA00087'] | BRALEY, BRUCE L |
| 2014 | C00489336 | CAPITO, SHELLEY | H0WV02138 | H WV | ['H0WV02138', 'S4WV00159'] | ['S4WV00159'] | CAPITO, SHELLEY MOORE |
| 2014 | C00507574 | PETERS, GARY | H8MI09068 | H MI | ['H8MI09068', 'S4MI00355'] | ['S4MI00355'] | PETERS, GARY |
| 2016 | C00328468 | BOUSTANY, CHARLES | H4LA07029 | H LA | ['H4LA07029', 'S6LA00300'] | ['S6LA00300'] | BOUSTANY, CHARLES W JR DR |
| 2016 | C00388934 | GRAHAM, LINDSEY | P60007697 | P US | ['P60007697', 'S0SC00149'] | ['S0SC00149', 'S6SC04437'] | GRAHAM, DARLINE\|GRAHAM, LINDSEY O. |
| 2016 | C00500025 | RUBIO, MARCO | P60006723 | P US | ['P60006723', 'S0FL00338'] | ['S0FL00338'] | RUBIO, MARCO |
| 2016 | C00416743 | VAN HOLLEN, CHRIS | H2MD08126 | H MD | ['H2MD08126', 'S6MD03441'] | ['S6MD03441'] | VAN HOLLEN, CHRIS |
| 2018 | C00409276 | BLACKBURN, MARSHA | H2TN06030 | H TN | ['H2TN06030', 'S8TN00337'] | ['S8TN00337'] | BLACKBURN, MARSHA MRS. |
| 2018 | C00328468 | BOUSTANY, CHARLES | H4LA07029 | H LA | ['H4LA07029', 'S6LA00300'] | ['S6LA00300'] | BOUSTANY, CHARLES W JR DR |
| 2018 | C00691915 | CRAMER, KEVIN | H0ND01026 | H ND | ['H0ND01026', 'S8ND00120'] | ['S8ND00120'] | CRAMER, KEVIN MR. |
| 2018 | C00640029 | DELANEY, JOHN K. | H2MD06195 | H MD | ['H2MD06195', 'P00006213'] | ['P00006213'] | DELANEY, JOHN K. |
| 2018 | C00512855 | ROKITA, THEODORE | H0IN04170 | H IN | ['H0IN04170', 'S8IN00189'] | ['S8IN00189'] | ROKITA, THEODORE EDWARD |
| 2018 | C00654475 | ROSEN, JACKY | H6NV03139 | H NV | ['H6NV03139', 'S8NV00156'] | ['S8NV00156'] | ROSEN, JACKY |
| 2018 | C00571182 | SINEMA, KYRSTEN | H2AZ09019 | H AZ | ['H2AZ09019', 'S8AZ00197'] | ['S8AZ00197'] | SINEMA, KYRSTEN |
| 2020 | C00497131 | BOOKER, CORY | P00009795 | P US | ['P00009795', 'S4NJ00185'] | ['S4NJ00185'] | BOOKER, CORY A. |
| 2020 | C00745117 | DELGADO, ANTONIO | H0CA40138 | H CA | ['H0CA40138', 'H8NY19181'] | ['H8NY19181'] | DELGADO, ANTONIO |
| 2020 | C00477067 | GILLIBRAND, KIRSTEN | P00009290 | P US | ['P00009290', 'S0NY00410'] | ['S0NY00410'] | GILLIBRAND, KIRSTEN |
| 2020 | C00525600 | GILLIBRAND, KIRSTEN | P00009290 | P US | ['P00009290', 'S0NY00410'] | ['S0NY00410'] | GILLIBRAND, KIRSTEN |
| 2020 | C00629071 | HARRIS, KAMALA | P00009423 | P US | ['P00009423', 'S6CA00584'] | ['S6CA00584'] | HARRIS, KAMALA D |
| 2020 | C00687582 | HICKENLOOPER, JOHN | P00010520 | P US | ['P00010520', 'S0CO00575'] | ['S0CO00575'] | HICKENLOOPER, JOHN W. |
| 2020 | C00512855 | ROKITA, THEODORE | H0IN04170 | H IN | ['H0IN04170', 'S8IN00189'] | ['S8IN00189'] | ROKITA, THEODORE EDWARD |
| 2020 | C00569871 | RUIZ, RAUL | H0CA36177 | H CA | ['H0CA36177', 'H2CA36439'] | ['H2CA36439'] | RUIZ, RAUL DR. |
| 2022 | C00403675 | CONYERS, JOHN | H2MI13261 | H MI | ['H2MI13261', 'H6MI01028'] | ['H6MI01028'] | CONYERS, JOHN JR. |
| 2022 | C00685735 | HENG, ELIZABETH | H2CA22199 | H CA | ['H2CA22199', 'H8CA16065', 'S2CA01003'] | ['H8CA16065'] | HENG, ELIZABETH |
| 2022 | C00829879 | KENNEDY, RONDA | H0CA26145 | H CA | ['H0CA26145', 'S4NV00247'] | ['S4NV00247'] | KENNEDY, RONDA |
| 2022 | C00512855 | ROKITA, THEODORE | H0IN04170 | H IN | ['H0IN04170', 'S8IN00189'] | ['S8IN00189'] | ROKITA, THEODORE EDWARD |
| 2022 | C00571000 | SULLIVAN, DAN | H2MA09254 | H MA | ['H2MA09254', 'S4AK00214'] | ['S4AK00214'] | SULLIVAN, DAN |
| 2022 | C00615492 | WALKER, BRADLEY MARK | S2NC00307 | S NC | ['H4NC06052', 'S2NC00307'] | ['H4NC06052'] | WALKER, BRADLEY MARK MR. |
| 2024 | C00525717 | AMASH, JUSTIN | S4MI00694 | S MI | ['H0MI03126', 'S4MI00694'] | ['H0MI03126'] | AMASH, JUSTIN |
| 2024 | C00403675 | CONYERS, JOHN | H2MI13261 | H MI | ['H2MI13261', 'H6MI01028'] | ['H6MI01028'] | CONYERS, JOHN JR. |
| 2024 | C00880724 | DOWNING, TROY | H4MT02098 | H MT | ['H4MT02098', 'S8MT00218'] | ['S8MT00218'] | DOWNING, TROY |
| 2024 | C00853531 | FRATTO, MARIO | H4NY24115 | H NY | ['H2NY23152', 'H4NY24115'] | ['H2NY23152'] | FRATTO, MARIO |
| 2024 | C00892752 | GALLEGO, RUBEN | H4AZ07043 | H AZ | ['H4AZ07043', 'S4AZ00139'] | ['S4AZ00139'] | GALLEGO, RUBEN |
| 2024 | C00576975 | GALLEGO, RUBEN | H4AZ07043 | H AZ | ['H4AZ07043', 'S4AZ00139'] | ['S4AZ00139'] | GALLEGO, RUBEN |
| 2024 | C00481978 | GRAYSON, ALAN MARK | S2FL00581 | S FL | ['H6FL08213', 'S2FL00581', 'S6FL00376'] | ['H6FL08213'] | GRAYSON, ALAN MARK |
| 2024 | C00829879 | KENNEDY, RONDA | H0CA26145 | H CA | ['H0CA26145', 'S4NV00247'] | ['S4NV00247'] | KENNEDY, RONDA |
| 2024 | C00798405 | MASTERS, BLAKE | H4AZ08124 | H AZ | ['H4AZ08124', 'S2AZ00372'] | ['S2AZ00372'] | MASTERS, BLAKE |
| 2024 | C00773853 | MEIJER, PETER | S4MI00637 | S MI | ['H0MI03308', 'S4MI00637'] | ['H0MI03308'] | MEIJER, PETER MR. |
| 2024 | C00512855 | ROKITA, THEODORE | H0IN04170 | H IN | ['H0IN04170', 'S8IN00189'] | ['S8IN00189'] | ROKITA, THEODORE EDWARD |
| 2024 | C00406553 | SANDERS, BERNARD | P40019242 | P US | ['P40019242', 'P60007168', 'S4VT00033'] | ['S4VT00033'] | SANDERS, BERNARD |
| 2024 | C00422774 | SCHIFF, ADAM | H0CA27085 | H CA | ['H0CA27085', 'S4CA00555'] | ['S4CA00555'] | SCHIFF, ADAM |
| 2024 | C00827519 | SCOTT, TIMOTHY E. | P40012155 | P US | ['P40012155', 'S4SC00240'] | ['S4SC00240'] | SCOTT, TIMOTHY E. |
| 2024 | C00461996 | SIMPSON, MICHAEL K | H4SC06155 | H SC | ['H4SC06155', 'H8ID02064'] | ['H8ID02064'] | SIMPSON, MICHAEL |
| 2024 | C00780262 | SMILEY, TIFFANY | H4WA04179 | H WA | ['H4WA04179', 'S2WA00387'] | ['S2WA00387'] | SMILEY, TIFFANY |
| 2024 | C00571000 | SULLIVAN, DAN | H2MA09254 | H MA | ['H2MA09254', 'S4AK00214'] | ['S4AK00214'] | SULLIVAN, DAN |
| 2026 | C00525717 | AMASH, JUSTIN | S4MI00694 | S MI | ['H0MI03126', 'S4MI00694'] | ['H0MI03126'] | AMASH, JUSTIN |
| 2026 | C00403675 | CONYERS, JOHN | H2MI13261 | H MI | ['H2MI13261', 'H6MI01028'] | ['H6MI01028'] | CONYERS, JOHN JR. |
| 2026 | C00654186 | CURTIS, JOHN | S4UT00282 | S UT | ['H8UT03238', 'S4UT00282'] | ['H8UT03238'] | CURTIS, JOHN |
| 2026 | C00926113 | DEATON, JOHN | S6MA00304 | S MA | ['S4MA00358', 'S6MA00304'] | ['S4MA00358'] | DEATON, JOHN |
| 2026 | C00889543 | DESPAIN, MONIQUE | H6OR04260 | H OR | ['H4OR04125', 'H6OR04260'] | ['H4OR04125'] | DESPAIN, MONIQUE |
| 2026 | C00880724 | DOWNING, TROY | H4MT02098 | H MT | ['H4MT02098', 'S8MT00218'] | ['S8MT00218'] | DOWNING, TROY |
| 2026 | C00829879 | KENNEDY, RONDA | H6NV03238 | H NV | ['H6NV03238', 'H6NV04137', 'S4NV00247'] | ['S4NV00247'] | KENNEDY, RONDA |
| 2026 | C00761957 | KIM, ANDY | S4NJ00466 | S NJ | ['H8NJ03206', 'S4NJ00466'] | ['H8NJ03206'] | BUTLER, BENJAMIN BEN |
| 2026 | C00732925 | KISTNER, TYLER | H6MN02255 | H MN | ['H0MN02134', 'H6MN02255'] | ['H0MN02134'] | KISTNER, TYLER |
| 2026 | C00721225 | LURIA, ELAINE | H6VA02198 | H VA | ['H6VA02198', 'H8VA02111'] | ['H8VA02111'] | LURIA, ELAINE |
| 2026 | C00798405 | MASTERS, BLAKE | H4AZ08124 | H AZ | ['H4AZ08124', 'S2AZ00372'] | ['S2AZ00372'] | MASTERS, BLAKE |
| 2026 | C00773853 | MEIJER, PETER | S4MI00637 | S MI | ['H0MI03308', 'S4MI00637'] | ['H0MI03308'] | MEIJER, PETER MR. |
| 2026 | C00923268 | MURPHY, MORGAN W. W. | H6AL07190 | H AL | ['H6AL07190', 'S6AL00484'] | ['S6AL00484'] | MURPHY, MORGAN W. W. |
| 2026 | C00947739 | O'DONNELL, MARTY | H4NV03225 | H NV | ['H4NV03225', 'H6NV03204'] | ['H6NV03204'] | O'DONNELL, MARTY |
| 2026 | C00512855 | ROKITA, THEODORE | H0IN04170 | H IN | ['H0IN04170', 'S8IN00189'] | ['S8IN00189'] | ROKITA, THEODORE EDWARD |
| 2026 | C00495887 | SCOTT, TIMOTHY E. | S4SC00240 | S SC | ['P40012155', 'S4SC00240'] | ['P40012155'] | SCOTT, TIMOTHY E. |
| 2026 | C00433896 | SOLIS, HILDA | H6CA38139 | H CA | ['H0CA31087', 'H6CA38139'] | ['H0CA31087'] | SOLIS, HILDA |
| 2026 | C00746735 | STEVENS, HALEY | H8MI11254 | H MI | ['H8MI11254', 'S6MI00426'] | ['S6MI00426'] | STEVENS, HALEY |
| 2026 | C00615492 | WALKER, BRADLEY MARK | S2NC00307 | S NC | ['H4NC06052', 'S2NC00307'] | ['H4NC06052'] | WALKER, BRADLEY MARK MR. |

**Q14c rung 2 disagreements where OpenFEC's sponsor has another name (every cycle)  (0 s)**

| cycle | cid | sponsor | r2_id | rule_name | picked | o_ids | o_names |
|---|---|---|---|---|---|---|---|
| 2010 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2010 | C00234641 | PAUL, RON | P80000748 | PAUL, RON | P US | ['H6TX22101'] | PAUL, RONALD E. |
| 2012 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2012 | C00517235 | LUJAN, BEN RAY | H8NM03196 | LUJAN, BEN R MR. | H NM | ['S0NM00058'] | BERKLEY, SHELLEY |
| 2012 | C00234641 | PAUL, RON | P80000748 | PAUL, RON | P US | ['H6TX22101'] | PAUL, RONALD E. |
| 2014 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2014 | C00234641 | PAUL, RON | P80000748 | PAUL, RON | P US | ['H6TX22101'] | PAUL, RONALD E. |
| 2016 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2016 | C00234641 | PAUL, RON | P80000748 | PAUL, RON | P US | ['H6TX22101'] | PAUL, RONALD E. |
| 2018 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2018 | C00345702 | JOHNSON, SAMUEL | H8TX03107 | JOHNSON, SAMUEL H. | H TX | ['H2TX03118'] | JOHNSON, SAM MR. |
| 2020 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2022 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2022 | C00778167 | RUSS, DAVID | H2OR01240 | RUSS, DAVID HONORABLE | H OR | ['H20R01240'] |  |
| 2024 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2024 | C00832501 | RICKETTS, PETE | S6NE00129 | RICKETTS, PETE | S NE | ['S4NE00173'] |  |
| 2024 | C00838128 | STUTZMAN, MARLIN | H0IN03198 | STUTZMAN, MARLIN A | H IN | ['H4IN03174'] |  |
| 2026 | C00331694 | BROWN, SHERROD | S6OH00163 | BROWN, SHERROD | S OH | ['S6OH00379'] |  |
| 2026 | C00949495 | HEMPHILL, JAMES | H2OH11250 | HEMPHILL, JAMES TERRELLE | H OH | ['H20H11250'] |  |
| 2026 | C00856849 | MCGUIRE, JOHN | H0VA07133 | MCGUIRE, JOHN J. MR. III | H VA | ['H4VA05071'] |  |
| 2026 | C00888255 | ONDER, ROBERT | H4MO03221 | ONDER, ROBERT FOR JR. | H MO | ['H8MO09146'] | ONDER JR, ROBERT FRANK |
| 2026 | C00832501 | RICKETTS, PETE | S6NE00129 | RICKETTS, PETE | S NE | ['S4NE00173'] |  |
| 2026 | C00838128 | STUTZMAN, MARLIN | H0IN03198 | STUTZMAN, MARLIN A | H IN | ['H4IN03174'] |  |

**Q14d rung 2 disagreements where OpenFEC names the same name under another id (30)  (0 s)**

| cycle | cid | sponsor | r2_id | picked | o_ids | openfec_id_last_cycle |
|---|---|---|---|---|---|---|
| 2026 | C00832147 | SLOTKIN, ELISSA | S4MI00470 | S MI | ['H8MI08102'] | [2024] |
| 2026 | C00905836 | WILLIS, THOMAS EDWARD II | S6WV00162 | S WV | ['S8WV00176'] | [2018] |
| 2024 | C00746735 | STEVENS, HALEY | H8MI11254 | H MI | ['S6MI00426'] | [2026] |
| 2022 | C00576975 | GALLEGO, RUBEN | H4AZ07043 | H AZ | ['S4AZ00139'] | [2026] |
| 2022 | C00422774 | SCHIFF, ADAM | H0CA27085 | H CA | ['S4CA00555'] | [2026] |
| 2022 | C00495887 | SCOTT, TIMOTHY E. | S4SC00240 | S SC | ['P40012155'] | [2026] |
| 2022 | C00746735 | STEVENS, HALEY | H8MI11254 | H MI | ['S6MI00426'] | [2026] |
| 2020 | C00576975 | GALLEGO, RUBEN | H4AZ07043 | H AZ | ['S4AZ00139'] | [2026] |
| 2020 | C00422774 | SCHIFF, ADAM | H0CA27085 | H CA | ['S4CA00555'] | [2026] |
| 2020 | C00495887 | SCOTT, TIMOTHY E. | S4SC00240 | S SC | ['P40012155'] | [2026] |
| 2020 | C00746735 | STEVENS, HALEY | H8MI11254 | H MI | ['S6MI00426'] | [2026] |
| 2018 | C00450247 | BROWN, CORRINE | H2FL03056 | H FL | ['S0FL00403'] | [2010] |
| 2018 | C00576975 | GALLEGO, RUBEN | H4AZ07043 | H AZ | ['S4AZ00139'] | [2026] |
| 2018 | C00517235 | LUJAN, BEN RAY | H8NM03196 | H NM | ['S0NM00058'] | [2026] |
| 2018 | C00422774 | SCHIFF, ADAM | H0CA27085 | H CA | ['S4CA00555'] | [2026] |
| 2018 | C00495887 | SCOTT, TIMOTHY E. | S4SC00240 | S SC | ['P40012155'] | [2026] |
| 2016 | C00409276 | BLACKBURN, MARSHA | H2TN06030 | H TN | ['S8TN00337'] | [2026] |
| 2016 | C00450247 | BROWN, CORRINE | H2FL03056 | H FL | ['S0FL00403'] | [2010] |
| 2016 | C00576975 | GALLEGO, RUBEN | H4AZ07043 | H AZ | ['S4AZ00139'] | [2026] |
| 2016 | C00517235 | LUJAN, BEN RAY | H8NM03196 | H NM | ['S0NM00058'] | [2026] |
| 2016 | C00512855 | ROKITA, THEODORE | H0IN04170 | H IN | ['S8IN00189'] | [2026] |
| 2016 | C00422774 | SCHIFF, ADAM | H0CA27085 | H CA | ['S4CA00555'] | [2026] |
| 2016 | C00571182 | SINEMA, KYRSTEN | H2AZ09019 | H AZ | ['S8AZ00197'] | [2026] |
| 2014 | C00409276 | BLACKBURN, MARSHA | H2TN06030 | H TN | ['S8TN00337'] | [2026] |
| 2014 | C00328468 | BOUSTANY, CHARLES | H4LA07029 | H LA | ['S6LA00300'] | [2018] |
| 2014 | C00450247 | BROWN, CORRINE | H2FL03056 | H FL | ['S0FL00403'] | [2010] |
| 2014 | C00517235 | LUJAN, BEN RAY | H8NM03196 | H NM | ['S0NM00058'] | [2026] |
| 2014 | C00393603 | REHBERG, DENNIS | S6MT00097 | S MT | ['H0MT00033'] | [2024] |
| 2014 | C00512855 | ROKITA, THEODORE | H0IN04170 | H IN | ['S8IN00189'] | [2026] |
| 2014 | C00422774 | SCHIFF, ADAM | H0CA27085 | H CA | ['S4CA00555'] | [2026] |

**Q14e rung 2 'one' class against OpenFEC, every cycle: is a single match ever wrong?  (0 s)**

| r2 | confirmed | same_name_other_id | other_name | unchecked |
|---|---|---|---|---|
| one | 2,649 | 49 | 23 | 140 |
| one person, several ids | 220 | 0 | 0 | 3 |
EXIT 0 2026-11-25T18:38:10Z

## Q15: does `cm` name a blank sponsor?

Run during the checkpoint. Of 2024's 242 blank-sponsor PACs OpenFEC names a sponsor for, `cm`'s
connected organization is blank on 121 and mentions the sponsor's last name on 80, but as a joint
fundraising committee's name (`MCCONNELL FOR MAJORITY LEADER COMMITTEE` on Bluegrass,
`MCCARTHY VICTORY FUND` on MC PAC), not as a sponsor; Save America's is blank. No bulk field names
a blank sponsor.

```python
# Q15: does cm's CONNECTED_ORG_NM name a blank-sponsor PAC's sponsor? (2024)
agree(2024)
silver("committee", 2024)
show("Q15a blank-sponsor PACs: connected_org filled, and naming OpenFEC's sponsor (last name)", """
    SELECT nullif(trim(c.connected_org), '') IS NOT NULL AS connected_org_filled,
        coalesce(list_bool_or(list_transform(string_split(a.o_names, '|'),
            lambda n: contains(upper(c.connected_org), lastn(n)))), false) AS names_openfec_sponsor,
        count(*) AS pacs, sum(a.rcpt) AS file_receipts
    FROM a_2024 AS a JOIN silver_2024.committee AS c ON c.committee_id = a.cid
    WHERE a.sponsor IS NULL AND len(a.o_ids) > 0 GROUP BY ALL ORDER BY ALL""")
show("Q15b the largest 15 of them", """
    SELECT a.cid, a.name, a.rcpt, c.connected_org, a.o_names
    FROM a_2024 AS a JOIN silver_2024.committee AS c ON c.committee_id = a.cid
    WHERE a.sponsor IS NULL AND len(a.o_ids) > 0 ORDER BY a.rcpt DESC NULLS LAST LIMIT 15""")
```

Output:

**Q15a blank-sponsor PACs: connected_org filled, and naming OpenFEC's sponsor (last name)  (0 s)**

| connected_org_filled | names_openfec_sponsor | pacs | file_receipts |
|---|---|---|---|
| False | False | 121 | 131,336,402 |
| True | False | 41 | 18,330,657 |
| True | True | 80 | 49,150,092 |

**Q15b the largest 15 of them  (0 s)**

| cid | name | rcpt | connected_org | o_names |
|---|---|---|---|---|
| C00762591 | SAVE AMERICA | 99,719,703 |  | TRUMP, DONALD J. |
| C00828541 | NEVER SURRENDER, INC. | 20,981,683 | TRUMP BILIRAKIS VICTORY FUND | TRUMP, DONALD J. |
| C00536540 | JOBS, FREEDOM, AND SECURITY PAC | 3,479,994 |  | CRUZ, RAFAEL EDWARD  TED |
| C00409003 | HEARTLAND VALUES PAC | 3,376,658 | COMMONSENSE, CONSERVATIVE VALUES PAC | THUNE, JOHN R. |
| C00428052 | MAJORITY COMMITTEE PAC--MC PAC | 2,756,607 | MCCARTHY VICTORY FUND | MCCARTHY, KEVIN |
| C00563726 | MR. SOUTHERN MISSOURIAN IN THE HOUSE PAC | 2,588,921 |  | SMITH, JASON T |
| C00592089 | ELECTING MAJORITY MAKING EFFECTIVE REPUBLICANS PAC | 2,079,972 | EMMER VICTORY COMMITTEE | EMMER, THOMAS EARL JR. |
| C00467431 | THE EYE OF THE TIGER POLITICAL ACTION COMMITTEE | 2,063,973 |  | SCALISE, STEVE MR |
| C00571323 | TOGETHER HOLDING OUR MAJORITY PAC | 1,728,042 | NC RED | TILLIS, THOM R SEN |
| C00542027 | BIG SKY OPPORTUNITY PAC | 1,507,448 | MONTANA RED | DAINES, STEVE |
| C00296640 | REPUBLICAN MAJORITY FUND | 1,367,901 |  | COTTON, THOMAS |
| C00491654 | CITIZENS FOR PROSPERITY IN AMERICA TODAY PAC | 1,336,295 | PROPELLING AMERICA INTO TOMORROW | TOOMEY, PATRICK JOSEPH |
| C00719971 | SENATE EAGLE PAC | 1,312,902 | TEAM HAGERTY VICTORY | HAGERTY, BILL |
| C00844639 | DEMOCRATIC TURNOUT PROJECT PAC | 1,301,646 |  | KUSTER, ANN MCLANE |
| C00235655 | BLUEGRASS COMMITTEE | 1,296,929 | MCCONNELL FOR MAJORITY LEADER COMMITTEE | MCCONNELL, MITCH |
EXIT 0 2026-11-25T18:38:12Z

## Q16: `leadership_sponsors.csv`

The list under the checkpoint's rule, every cycle 2010–2026: 2,582 rows, 2,041 for blank sponsors,
255 for names matching no candidate and 286 for names matching several ids (Q16a–b). A case gets no
row when OpenFEC names nobody (532 blanks and 42 others), several people (6), or an id outside the
matched ones (Duncan Hunter's 2010 PAC, whose name matches the son's ids while OpenFEC names the
father; 4 in all) (Q16a, Q16c–d). The CSV it printed is committed as
`src/fundlens/fec/leadership_sponsors.csv`; it is not repeated here.

```python
# Q16: leadership_sponsors.csv under the checkpoint's rule (2026-11-25). Rung 2 takes the id of a
# name that matches one person; a name matching several ids takes none, and a file sponsor with
# no single-person match is linked only by a list row. A list row is written, from OpenFEC's
# sponsor_candidate_ids, for:
#   several - the file's name matches several ids: OpenFEC's id among them;
#   none    - the file's name matches no candidate of the cycle: OpenFEC's id;
#   blank   - the file names no sponsor: OpenFEC's sponsor and id.
# Each only when OpenFEC names exactly one person and fundlens holds a candidate under the id it
# takes. The id taken is, among OpenFEC's (and for 'several' among the matched ones too), the one
# standing in a race of the cycle, then a candidate of the cycle, then the lowest held id.
# A name matching one person never gets a row: by person, OpenFEC confirms those (Q14).
import sys
allcand()
parts = []
for c in CYCLES:
    agree(c)
    parts.append(f"""
        SELECT {c} AS cycle, a.cid, a.sponsor, a.r2, a.r2_ids, a.o_ids, a.o_names,
            CASE WHEN len(a.o_ids) = 0 THEN 0 ELSE len(list_distinct(list_transform(
                string_split(coalesce(a.o_names, ''), '|'),
                lambda n: lastn(n) || '/' || firstn(n)))) END AS people,
            CASE WHEN a.sponsor IS NULL THEN 'blank'
                 WHEN a.r2 IN ('one person, several ids', 'several people') THEN 'several'
                 WHEN a.r2 = 'none' THEN 'none' END AS why
        FROM a_{c} AS a""")
con.execute("CREATE TABLE q16c AS SELECT * FROM (" + " UNION ALL ".join(parts) + ") WHERE why IS NOT NULL")
con.execute("""
    CREATE TABLE q16 AS
    WITH cand_ids AS (
        SELECT q.cycle, q.cid, unnest(CASE WHEN q.why = 'several' THEN list_intersect(q.o_ids, q.r2_ids)
                                           ELSE q.o_ids END) AS id
        FROM q16c AS q WHERE q.people = 1
    ),
    ranked AS (
        SELECT ci.cycle, ci.cid, ci.id,
            row_number() OVER (PARTITION BY ci.cycle, ci.cid ORDER BY
                (SELECT bool_or(race_id IS NOT NULL) FROM (""" + " UNION ALL ".join(
                    f"SELECT {c} AS cycle, candidate_id, race_id FROM cand_{c}" for c in CYCLES) + """) AS k
                 WHERE k.cycle = ci.cycle AND k.candidate_id = ci.id) DESC NULLS LAST,
                ci.id IN (SELECT candidate_id FROM allcand) DESC, ci.id) AS o
        FROM cand_ids AS ci WHERE ci.id IN (SELECT candidate_id FROM allcand)
    )
    SELECT q.cycle, q.cid AS committee_id,
        coalesce(q.sponsor, split_part(q.o_names, '|', 1)) AS sponsor_name, r.id AS candidate_id,
        'https://www.fec.gov/data/committee/' || q.cid || '/ (OpenFEC sponsor_candidate_ids, read 2026-11-25)'
            AS source,
        q.why, q.people, q.o_ids, q.r2_ids
    FROM q16c AS q LEFT JOIN ranked AS r ON r.cycle = q.cycle AND r.cid = q.cid AND r.o = 1""")
show("Q16a the list by reason and cycle: rows written, and cases left without one", """
    SELECT cycle, why, count(*) FILTER (WHERE candidate_id IS NOT NULL) AS rows,
        count(*) FILTER (WHERE candidate_id IS NULL AND people = 0) AS openfec_names_none,
        count(*) FILTER (WHERE candidate_id IS NULL AND people > 1) AS openfec_names_several,
        count(*) FILTER (WHERE candidate_id IS NULL AND people = 1) AS id_not_held_or_not_matched
    FROM q16 GROUP BY ALL ORDER BY cycle, why""")
show("Q16b totals", """
    SELECT why, count(*) FILTER (WHERE candidate_id IS NOT NULL) AS rows, count(*) AS cases FROM q16
    GROUP BY ALL ORDER BY 1""")
show("Q16c cases with one person named by OpenFEC but no row (id not held, or not among the matched)", """
    SELECT cycle, committee_id, sponsor_name, why, o_ids, r2_ids FROM q16
    WHERE candidate_id IS NULL AND people = 1 ORDER BY cycle, committee_id""")
show("Q16d OpenFEC names several people", """
    SELECT cycle, committee_id, sponsor_name, why, o_ids FROM q16 WHERE people > 1 ORDER BY cycle, committee_id""")
print("\nBEGIN leadership_sponsors.csv")
w = csv.writer(sys.stdout, lineterminator="\n")
w.writerow(["cycle", "committee_id", "sponsor_name", "candidate_id", "source"])
for row in con.execute("SELECT cycle, committee_id, sponsor_name, candidate_id, source FROM q16"
                       " WHERE candidate_id IS NOT NULL ORDER BY cycle, committee_id").fetchall():
    w.writerow(row)
print("END leadership_sponsors.csv")
```

Output:

**Q16a the list by reason and cycle: rows written, and cases left without one  (0 s)**

| cycle | why | rows | openfec_names_none | openfec_names_several | id_not_held_or_not_matched |
|---|---|---|---|---|---|
| 2010 | blank | 151 | 55 | 0 | 0 |
| 2010 | none | 30 | 1 | 0 | 0 |
| 2010 | several | 16 | 0 | 0 | 1 |
| 2012 | blank | 191 | 67 | 0 | 0 |
| 2012 | none | 39 | 3 | 0 | 0 |
| 2012 | several | 19 | 1 | 0 | 2 |
| 2014 | blank | 211 | 63 | 0 | 0 |
| 2014 | none | 34 | 4 | 0 | 0 |
| 2014 | several | 20 | 1 | 0 | 0 |
| 2016 | blank | 220 | 71 | 0 | 0 |
| 2016 | none | 29 | 3 | 0 | 0 |
| 2016 | several | 18 | 0 | 1 | 0 |
| 2018 | blank | 254 | 69 | 0 | 0 |
| 2018 | none | 24 | 8 | 0 | 0 |
| 2018 | several | 20 | 1 | 0 | 0 |
| 2020 | blank | 276 | 65 | 0 | 0 |
| 2020 | none | 22 | 10 | 2 | 0 |
| 2020 | several | 31 | 1 | 0 | 0 |
| 2022 | blank | 248 | 54 | 0 | 0 |
| 2022 | none | 25 | 5 | 1 | 0 |
| 2022 | several | 41 | 0 | 0 | 0 |
| 2024 | blank | 242 | 46 | 0 | 0 |
| 2024 | none | 26 | 1 | 1 | 1 |
| 2024 | several | 56 | 0 | 0 | 0 |
| 2026 | blank | 248 | 42 | 0 | 0 |
| 2026 | none | 26 | 3 | 0 | 0 |
| 2026 | several | 65 | 0 | 1 | 0 |

**Q16b totals  (0 s)**

| why | rows | cases |
|---|---|---|
| blank | 2,041 | 2,573 |
| none | 255 | 298 |
| several | 286 | 295 |

**Q16c cases with one person named by OpenFEC but no row (id not held, or not among the matched)  (0 s)**

| cycle | committee_id | sponsor_name | why | o_ids | r2_ids |
|---|---|---|---|---|---|
| 2010 | C00377010 | HUNTER, DUNCAN D. | several | ['H2CA42023'] | ['H8CA52052', 'P80003395'] |
| 2012 | C00377010 | HUNTER, DUNCAN D. | several | ['H2CA42023'] | ['H8CA52052', 'P80003395'] |
| 2012 | C00495887 | SCOTT, TIMOTHY E. | several | ['P40012155'] | ['H0SC01279', 'S4SC00240'] |
| 2024 | C00856849 | MCGUIRE, JOHN | none | ['H4VA05071'] |  |

**Q16d OpenFEC names several people  (0 s)**

| cycle | committee_id | sponsor_name | why | o_ids |
|---|---|---|---|---|
| 2016 | C00388934 | GRAHAM, LINDSEY | several | ['S0SC00149', 'S6SC04437'] |
| 2020 | C00745273 | DEMINGS, VAL | none | ['H2FL08063', 'S2FL00631'] |
| 2020 | C00764761 | LETLOW, JULIA | none | ['H0LA05120', 'H2LA05126', 'S6LA00664'] |
| 2022 | C00388934 | GRAHAM, DARLINE | none | ['S0SC00149', 'S6SC04437'] |
| 2024 | C00388934 | GRAHAM, DARLINE | none | ['S0SC00149', 'S6SC04437'] |
| 2026 | C00764761 | LETLOW, JULIA | several | ['H0LA05120', 'H2LA05126', 'S6LA00664'] |

(The CSV printed here is `src/fundlens/fec/leadership_sponsors.csv`, 2,582 rows, omitted.)
EXIT 0 2026-11-25T18:38:19Z

## Decisions

The spec pinned a 99% bar on each decision; one met is stated, one missed went to the checkpoint
held on 2026-11-25, whose answers project spec §7 records with their rejected alternatives.

1. **Leadership PAC flag: designation `D`, or a row in the cycle's leadership file** (checkpoint).
   The bar is met in 2010, 2012, 2018, 2020, 2022 and 2024 and missed in 2014, 2016 and 2026 by 4
   to 11 committees (Q12c). Either source alone loses committees the other names; `D` alone keeps a
   flag for 1980–2008.
2. **The file's money figures are not held** (bar met). `Total_Receipt`, `Total_Disbursement`,
   `Cash_on_Hand` and `Coverage_End_Date` equal `reported_total`'s within $1 for 99.5% or more of
   the 814 committees both hold (Q3).
3. **The sponsor: rung 2, one person only; the list for the rest** (checkpoint). A name matching
   one candidate of the cycle, through `alias_of`, links to that id. A name matching several ids,
   or none, links only through `leadership_sponsors.csv`. The bar by id is met in 2024 alone
   (99.19%) because OpenFEC gives current ids (Q12b, Q14d); by person, single-person matches agree
   across 2010–2026: 2,649 confirmed, 49 under a later id, 23 OpenFEC's errors or older ids (Q14a, Q14e).
   The rule links, per cycle 2010–2026, 168, 213, 226, 240, 297, 319, 390, 460 and 548 named
   sponsors: 77.8%, 76.9%, 79.3%, 82.5%, 84.9%, 82.9%, 84.4%, 84.4% and 85.2%. These are Q12a's rung-2
   ids less the names matching one person under several ids (Q16a's several-id cases less Q12a's
   several people); 2024's equals Q4d and the sum, 2,861, Q14e's single-person matches.
4. **Blank sponsors are filled from the list** (checkpoint; the spec pinned the reverse). OpenFEC
   names a sponsor for 73–86% of each cycle's blanks, the largest leadership PACs among them (Q5f,
   Q12b).
5. **`leadership_sponsors.csv`** (Q16): a row for a blank sponsor, a name matching no candidate, or a
   name matching several ids, when OpenFEC names one person and fundlens holds a candidate under
   the id taken. Its `source` cites the committee's FEC page. 2,582 rows.
6. **Lobbyist/registrant PAC flag: `lobbyist.csv`, rule b** (checkpoint). A committee is one in a
   cycle when its latest Form 1 filed on or before the cycle's last day has the box ticked. No rule
   meets the bar against `B` (Q7f). 2010–; no flag before.
7. **Amendments in the bundling file: the default** (stated; Q9's overlap bar went to the
   checkpoint with the total). Among a committee's rows with the same coverage start and end, the
   latest `Receipt_Date`, then the higher image number in `Link_Image`, is kept. A row with a blank
   coverage date is kept alone.
8. **The bundled total: the greater of the half-year figure and the innermost period amounts**
   (checkpoint). Per committee and half-year: the semi-annual amount on the kept report with the
   latest coverage end in the half that carries one above $0; against it the period amounts of the
   kept reports whose covered period holds no other kept report of the committee. A cycle's total
   adds its four halves (Q10).
9. **Edge rows** (checkpoint): a report with no coverage end is kept with amount 0 and its cycle by
   `Receipt_Date` (14 rows); one with an end and no start counts in its end's half, as Q10 counts it
   (15 rows); a report whose recipient is no committee of its cycle is dropped (Q8e–f).
10. **Cycles.** No cycle 2010–2026 needs a rule of its own: every leadership file's header equals
    2024's, and no file has a committee on two rows (Q12a). 2008 and odd years have no leadership
    file. The two undated files hold 2009–2026, so 2010 is the first cycle of every M4 table.

## For NEU-2174 to NEU-2180

- **NEU-2174** catalogues all three files: `leadership` per cycle, 2010–2026, 8 columns
  (`Committee_Id, Committee_Name, Link_Image, Sponsor_Name, Cash_on_Hand, Coverage_End_Date,
  Total_Disbursement, Total_Receipt`); `lobbyist` undated, 5 columns (`Link_Image, Committee_Name,
  Committee_Id, Date_Filed, Is_Lobbyist`); `lobbyist_bundle` undated, 11 columns (Q1). Dates are
  `DD-MON-YY` in all three; every cell casts (Q1a, Q1d, Q1f). Fixture rows worth having: a blank
  sponsor, a name with a title (`GARAMENDI, CONGRESSMAN JOHN`), a committee whose `Is_Lobbyist`
  changes, a bundling amendment (DCCC's June 2024 report, received 2024-07-19 and 2026-10-23), a
  six-month report beside its quarters, a blank coverage date.
- **NEU-2175** builds silver `leadership_pac`, `lobbyist_pac` and `bundling_report` (spec §7.3–7.5)
  and reads `leadership_sponsors.csv`. 2024's figures to be within 1% of: 833 leadership PACs, 460
  linked by the rule and 324 by list rows (Q4d, Q16); the lobbyist flag's 1,459 committees in `cm`
  under rule b (Q7f: 1,441 also `B`, 18 not); bundled total $57,262,231 at 84 recipients (Q10a).
- **NEU-2176 to NEU-2178** build gold, the API and pages on `committee_cycle`'s per-cycle fields
  (spec §7.7). No bundler and no donor is named anywhere: the file has none.
- **NEU-2179** checks Q13: the ten leadership PACs and sponsors, and the five recipients' totals.
- **NEU-2180**'s backfill needs nothing more: the list covers every cycle 2010–2026.
