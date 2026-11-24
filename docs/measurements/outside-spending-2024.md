# FEC's 2024 outside spending: `pas2` against the 24/48-hour file, non-committee spenders, electioneering communications, communication costs, amendments

Measured for [NEU-2162](https://linear.app/neuroticsasquatch/issue/NEU-2162) (milestone M3 All outside
spending; spec [`NEU-2162-outside-spending-measurement.md`](../specs/NEU-2162-outside-spending-measurement.md)).
Four sources describe outside spending and they overlap. `pas2` holds committees' independent
expenditures (24A against, 24E for), party coordinated expenditures (24C) and communication costs
(24F, 24N). The **24/48-hour file** (`independent_expenditure_<yyyy>.csv`) holds the same
spenders' 24- and 48-hour reports. `ElectioneeringComm_<yyyy>.csv` and `CommunicationCosts_<yyyy>.csv`
hold electioneering communications and communication costs. This document measures how they
overlap on 2024, takes one live reading of 2026 for timeliness, and profiles every cycle 2010–2026.
It fixes the source and dedup rule NEU-2163 writes into spec §6 for each kind. Nothing under
`sql/`, `src/` or `frontend/` changed, and no bronze, silver, gold or marker was written.

| What | Value |
| --- | --- |
| Run | 2026-11-24, over SSH on `music-box-dancer`. The blocks were written and tried 02:09–02:35 UTC. The blocks below are the final run, 02:36:08–02:38:58 UTC, every block in order (`all.sh`), but Q3, Q5, Q7, Q8 and Q11. Review found that `pas2` drops the cents the other files carry and that the ladder compared them exactly. Those five blocks were re-run at 15:16:10–15:17:02 UTC with amounts compared with the cents dropped; `setup.py` below is the fixed one (a first fix at 15:05, rounding, was itself wrong and is superseded). The re-runs read the three 2024 CSVs from copies downloaded at 02:07 UTC, of the same sizes and `Last-Modified` as the 02:09–02:10 downloads, since FEC had published newer ones by then |
| Code | `main` at `54fe259e1834c70a2fc2cd4db56dbd7efb563e06` (the `pipeline` image's tag) |
| Container | `pipeline-lvch8zyndujjzkz16ksys8im-20261124T001550` |
| DuckDB | 2.0.0; `Limits(memory_limit='32GB', max_temp_directory_size='60GB', threads=6)`; `connect`'s build-side optimizer off (NEU-2076) |
| Live builds | 2024: `20261124T002500Z`; 2026: `20261123T224142Z` (`gold.meta.cycles`). Every 2024 and 2026 source date of both builds is 2026-11-23, but 2024's `oppexp` (2026-11-22). The `cm`, `cn` and `pas2` read here are those builds' bronze, and `silver_<cycle>.*` their partitions. The other cycles' `cm` and `pas2` are their live builds' bronze (Q12) |
| 2024 CSVs | `https://www.fec.gov/files/bulk-downloads/2024/<name>_2024.csv`, each answering 302 to an S3 address. `independent_expenditure_2024.csv`: 19,534,174 bytes, `Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT`, downloaded 02:09:55 UTC. `ElectioneeringComm_2024.csv`: 18,370 bytes, `10:12:16 GMT`, 02:10:51 UTC. `CommunicationCosts_2024.csv`: 237,322 bytes, `10:12:07 GMT`, 02:10:53 UTC. The final run's blocks read those downloads; the re-runs read copies downloaded at 02:07 UTC (see Run) |
| 2026 files (Q7) | As Q7 below read them: `pas226.zip`, 9,568,089 bytes, `Last-Modified: Sun, 22 Nov 2026 17:01:09 GMT`, downloaded 15:16:34 UTC; `independent_expenditure_2026.csv`, 13,733,832 bytes, `Last-Modified: Tue, 24 Nov 2026 10:13:31 GMT`, downloaded 15:16:38 UTC. The final run's Q7 had read the same `pas226.zip` (02:17:19 UTC) and the 23 November CSV (13,733,351 bytes); its figures differ from these by under $8,000. Neither is catalogued or in bronze |
| Other cycles (Q12) | The three CSVs of each cycle 2010–2022 and 2026, each fetched, profiled and deleted by Q12, 02:37–02:38 UTC. Every one was last modified on 2026-11-23 between 10:11:58 and 10:13:33 GMT; sizes are in Q12a |
| Form 9 filings (Q9) | `https://api.open.fec.gov/v1/filings/?form_type=F9&cycle=<cycle>&committee_id=…` with `DEMO_KEY`, fetched on the VM host by `f9.sh` at 02:28:37 UTC (2024: 63 filings of the 25 sponsors, one request) and 02:28:40 UTC (2010: 188 filings of 4 sponsors, two requests). Raw filings: `https://docquery.fec.gov/dcdev/posted/<FILE_NUM>.fec` for 1816711, 1849492 (2024) and 32 filings of 2010, listed in Q9p |

None of these files is catalogued or in bronze. They lived in the work directory for the run only.
The work directory `/data/fundlens/scratch/measure-outside-spending-2024` was deleted at
14:59:23 UTC, made again for the re-runs, and deleted at 15:05:50 and, finally, at 15:17:02 UTC.

## Headline

- **Independent expenditures: `pas2` is the source; the 24/48-hour file should add by spender (NEU-2163 decides).**
  `pas2` counts 73,841 rows, $4,422,382,849, from 1,115 spenders, 153 of them Form 5 filers
  (`cm` type `I`, $84,903,413). It holds no 24- or 48-hour report and nothing twice (Q4). The
  24/48-hour file's rows for spenders that `pas2` holds are the same spending: per spender, its
  totals exceed `pas2`'s by $40,549,211 in all, 0.92% (Q5r). Row by row it nearly matches. Filers
  renumber their transactions and revise their estimates, and the two files code Biden's and
  Harris's ids differently, so rows worth 1.62% of counted dollars stay unmatched. That is just over
  §1.1's 1% bar, which is set on rows (Q5p), so the add rule goes to NEU-2163 with this evidence.
- **The 24/48-hour file holds $43.9B of hoax filings.** Sixteen rows of $100M or more hold $44.9B
  of the file's $49.7B (Q1j). Seven spenders `cm` lacks ($33.9B) and seven committees with no reported figures ($9.98B)
  filed web-form lines (`tran_id` `WFT…`) naming a presidential or Senate candidate:
  `THE COURT OF DIVINE JUSTICE` $9,978,412,568, `THE COMMITTEE OF 300`, `Republican Emo Girl`.
  None reports an independent expenditure anywhere. Added by spender without a screen, they would
  be 99.99% of what the file adds. With Q6's screen (the spender reports independent expenditures
  in `reported_total`, and the file holds no more than ten times that figure) the rule adds
  **$1,001,297 from 14 spenders**, 13 of them Form 5 filers. Without the screen, but with web-form
  ids aside, it adds $4,835,248 (Q6).
- **Non-committee spenders are Form 5 filers, and they are in `pas2`.** `cm` lacks only 8
  spenders. Seven are hoaxes and one is a $64,107 Form 5 line (Q2b). Form 5 filers are `cm` type
  `I` and in `pas2` like committees. 142 of the 199 match their reported figure within 1%, and 57
  fall short by $2,494,431 in all, mostly money only the 24/48-hour file carries (Q2f–g).
- **24/48-hour amendments: the filing chain, against §1.1's bar.** Amendments carrying under
  half of their original's transaction ids hold 1.63% of the dollars on amended filings. That is
  over the 1% bar, which would adopt the per-transaction rule (Q3h). But `tran_id` is not a key
  across filings: Senate Leadership Fund numbers a line `SE.1` on every new report, so the
  per-transaction rule would drop $439,518,994 of distinct expenditures (Q3j, Q3l). Of the rows only
  the chain drops (1,140, $29.7M), 706 are in `pas2` by amount under another `tran_id`: the
  amendment renumbered them (Q3n). The chain rule keeps 61,426 rows ($48.34B, or $4,401,751,869
  with web-form ids aside) and drops 12,023 ($1,340,305,331).
- **Timeliness: met on 2026.** On 2026, the latest-amendment 24/48-hour rows dated after their
  spender's last periodic report hold $1,287,474,092, and only 0.46% of it is already in `pas2`.
  That is under §1.1's 1% bar (Q7e). So the rule that adds them until a periodic report covers
  them adds $1,281,571,904 on 2026 today. On 2024, where every report is in, it adds $28,732.
- **Communication costs: `pas2` is the source.** Every row of the CSV is a `pas2` 24F/24N row
  under the same `SUB_ID`, filer, filing, `TRAN_ID` and candidate, in every cycle 2010–2026. The
  amounts differ by under $1, because `pas2` drops the cents the CSV writes (Q8, Q12g). `pas2`
  holds 20 rows ($59,480) the CSV leaves out, all without a candidate. 2024: 799 rows,
  $7,157,987, already silver's `communication_cost`.
- **Electioneering communications: every row counts, but copies.** 2024's file holds 69 rows,
  59 disbursements, $9,480,874 in candidate shares, from 25 sponsors, all `C3` (`cm` type `E`). 24
  rows ($2,179,759) name no candidate. Each row's share times its candidate count is its amount to the
  cent. The file has no filing number. Both of 2024's repeat groups are one restatement by an
  amendment ($33,750). Of 2010's 20 largest, 13 are separate Form 9 reports and 4 are one report
  filed twice (Q9p). The file key would drop $3.1M of 2010's $71.7M, most of it real, so no in-file
  amendment rule is safe. Two one-candidate disbursements sit on two rows each ($38,500), and a
  disbursement's rows beyond its candidate count are dropped. 2024: 67 rows, $9,442,374.
- **Party coordinated expenditures:** silver's 812 rows, $89,161,724, of which $88,084,906
  reaches a race. 45 committees match their reported figure within 1%. Three non-party filers file
  24C ($89,537) (Q10).
- **No overlap across kinds** but two electioneering rows ($1,451) that a sponsor's affiliate also
  filed as independent expenditures (Q11).
- **No Bug ticket.** No live figure is wrong: `pas2` counts no expenditure twice (Q4), and
  nothing measured here is in a live total yet.

## How to re-run

On the VM, in `tmux`. Save the setup script below as `setup.py`, each block under its name, and
`run.sh`, `f9.sh` and `all.sh` beside them. Then run `all.sh`. It runs `run.sh` on each block in
order and stops at the first that fails. `q9prep` writes the sponsors whose Form 9 filings `f9.sh`
fetches on the host. The container's address had spent `DEMO_KEY`'s ten requests by then; the
host's had not. A list already in the work directory is kept, so a re-run asks for none.

```bash
#!/bin/sh
# Usage: run.sh qN [extra.py ...]: setup.py, the extras and qN.py into the pipeline container, output
# to qN.out. Exits with Python's status, so all.sh stops at a failing block.
P=$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)
q=$1; shift
cat setup.py "$@" $q.py | docker exec -i "$P" python - > $q.raw 2>&1
status=$?
grep -v "^{" $q.raw > $q.out; rm -f $q.raw
echo "EXIT $status $(date -u +%FT%TZ)" >> $q.out
exit $status
```

```bash
#!/bin/sh
# Usage: f9.sh <cycle>: every Form 9 of the sponsors q9prep wrote for <cycle>, from OpenFEC, into the
# work directory as f9-<cycle>.json (a JSON list of OpenFEC's filing records), all pages.
P=$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)
W=/data/fundlens/scratch/measure-outside-spending-2024
c=$1
# A list already in the work directory is kept: DEMO_KEY allows 10 requests a day per address.
if docker exec "$P" test -s $W/f9-$c.json; then echo "$c: kept $W/f9-$c.json"; exit 0; fi
ids=$(docker exec "$P" cat $W/f9-sponsors-$c.txt)
q=""; for i in $ids; do q="$q&committee_id=$i"; done
page=1; echo "[]" > f9-$c.json
while :; do
  curl -sS -A "fundlens (+https://fundlens.org)" -D f9-$c.headers -o f9-$c.page.json \
    "https://api.open.fec.gov/v1/filings/?form_type=F9&cycle=$c&per_page=100&page=$page&sort=receipt_date&api_key=DEMO_KEY$q"
  grep -i "^HTTP/\|ratelimit-remaining" f9-$c.headers
  jq -s '.[0] + .[1].results' f9-$c.json f9-$c.page.json > f9-$c.tmp && mv f9-$c.tmp f9-$c.json
  pages=$(jq '.pagination.pages' f9-$c.page.json)
  [ "$page" -ge "$pages" ] && break
  page=$((page + 1))
done
echo "$c: $(jq length f9-$c.json) filings, $(date -u +%FT%TZ)"
docker exec -i "$P" sh -c "cat > $W/f9-$c.json" < f9-$c.json
rm -f f9-$c.page.json f9-$c.headers
```

```bash
#!/bin/sh
# The final run: every block in order, each into its own qN.out. q9prep writes the sponsors whose
# Form 9s f9.sh fetches on the host before q9 reads them; q6 writes added_2024.parquet for q13.
cd ~/measure-outside-spending-2024
date -u +"START %FT%TZ" > all.log
./run.sh q1 && ./run.sh q2 && ./run.sh q3 && ./run.sh q4 && ./run.sh q5 && ./run.sh q6 \
 && ./run.sh q7 && ./run.sh q8 && ./run.sh q9prep && ./f9.sh 2024 && ./f9.sh 2010 && ./run.sh q9 \
 && ./run.sh q10 && ./run.sh q11 && ./run.sh q12 && ./run.sh q13
echo "status $?" >> all.log
date -u +"END %FT%TZ" >> all.log
# Afterwards:
# docker exec "$(docker ps --format '{{.Names}}' | grep '^pipeline-lvch8zyndujjzkz16ksys8im' | head -1)" \
#   rm -rf /data/fundlens/scratch/measure-outside-spending-2024
```

Run one block at a time, never beside a pipeline step, and do not merge to `main` while they run:
a deploy restarts `pipeline`. The blocks fetch FEC's files into
`/data/fundlens/scratch/measure-outside-spending-2024` once and reuse them. Q5 and Q6 leave
`lm_2024.parquet`, `pmatch_2024.parquet` and `added_2024.parquet` there, and Q13 reads the last.
Q12 deletes each cycle's CSVs after profiling it, but 2024's. The whole run takes about 3 minutes.

Every table's title carries the seconds its query took. Amounts and dates are cast with `TRY_CAST`
and `try_strptime` inside each query, so a cell that fails is counted, not a read error.

### Setup

The setup is `oppexp-2024.md`'s, with the helpers §4.1 names and these additions:

- `h24(cycle)` is the 24/48-hour file typed: `spe`, `cand`, `amt`, `edt` (`exp_date`), `ddt`
  (`dissem_dt`), `rdt` (`receipt_dat`), `fnum`, `pfnum`, `tran`, the spender group `grp`, and
  both amendment rules' flags: `superseded` (the chain) and `latest_tran` (per transaction).
  `adopt_h24_rule` makes `l_<cycle>` the rows a rule keeps; every block after Q3 uses the chain.
- `counted_pas2(cycle)` is the live build's silver `independent_expenditure` (`kind = 'ie'`)
  joined to bronze `pas2` by `SUB_ID`, for the columns silver does not keep (`TRAN_ID`,
  `FILE_NUM`, `RPT_TP`, the payee). For 2026 (Q7) it spells silver's filter over the fresh
  `pas226.zip` instead. `cand` is the file's own id through `alias_of`, before the handoff and
  any correction (spec §2). `credited` and `race_id` are silver's.
- `ladder(cycle)` is Q5's ladder. It adds **rung 4** to §2's three: same spender, amount and date,
  the candidate not compared. Q5 shows why: the 24/48-hour file codes Biden's id on spending that
  `pas2` codes Harris's. Rung 4 is reported apart. Rungs 2–4 compare amounts with the cents
  dropped, because `pas2` drops them (Q4h, Q8l).
- `ec_table` and `cc_table` are the electioneering and communication-costs files typed, each with
  the sponsor's or filer's group and `cm` type.
- `view_csv` reads each CSV in `register_bulk`'s CSV dialect, so a blank `""` reads as NULL as it will
  once catalogued.

```python
import csv
import datetime as dt
import os
import shutil
import time
import zipfile
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg

from fundlens import paths
from fundlens.fec.extract import USER_AGENT
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import (
    Limits, connect, copy_as_utf8, copy_bulk, fetch_bulk, literal, register_bulk,
)

settings = get_settings()
store = R2.from_settings(settings)
scratch = paths.scratch_dir(settings.data_dir)
work = scratch / "measure-outside-spending-2024"
work.mkdir(parents=True, exist_ok=True)
con = connect(Limits.from_settings(settings), scratch)
FEC = "https://www.fec.gov/files/bulk-downloads"


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
            f"{v:,.0f}" if isinstance(v, (int, Decimal)) and not isinstance(v, bool)
            else f"{v:.2%}" if isinstance(v, float) else "" if v is None else str(v)
            for v in row
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


def fec_csv(stem: str, cycle: int) -> Path:
    """FEC's `<stem>_<cycle>.csv` (the 24/48-hour, electioneering or communication-costs file)."""
    return fetch(f"{FEC}/{cycle}/{stem}_{cycle}.csv")


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


def bulk(name: str, cycle: int, *, fresh: bool = False) -> None:
    """The cycle's bronze `name` as the transform sees it, as tables `<name>_<cycle>` (pas2: repeated
    rows dropped) and `<name>_published_<cycle>` (pas2: as published). `fresh` reads the zip from
    FEC now instead of bronze (2026's pas2, Q7)."""
    file = CATALOGUE[name]
    if con.execute(f"SELECT count(*) FROM duckdb_tables() WHERE table_name = '{name}_{cycle}'").fetchone()[0]:
        return
    here = work / f"bulk-{cycle}"
    here.mkdir(exist_ok=True)
    if fresh:
        z = fetch(f"{FEC}/{cycle}/{name}{cycle % 100:02d}.zip")
        text = here / f"{name}.txt"
        with zipfile.ZipFile(z) as archive, text.open("w+b") as out:
            copy_bulk(archive, file, out, cycle=cycle, source=str(z))
    else:
        text = fetch_bulk(store, cycle, file, data_dir=settings.data_dir, work=here)
    register_bulk(con, file, text)
    if con.execute(f"SELECT count(*) FROM duckdb_views() WHERE view_name = '{name}_published'").fetchone()[0]:
        con.execute(f"CREATE TABLE {name}_published_{cycle} AS SELECT * FROM {name}_published")
        con.execute(f"CREATE TABLE {name}_{cycle} AS SELECT * FROM {name}")
        con.execute(f"DROP VIEW {name}; DROP VIEW {name}_published; DROP TABLE {name}_repeat")
    else:
        con.execute(f"CREATE TABLE {name}_{cycle} AS SELECT * FROM {name}")
        con.execute(f"DROP VIEW {name}")
    shutil.rmtree(here)


with psycopg.connect(settings.database_url) as pg:
    pg.read_only = True
    META = pg.execute("SELECT cycles FROM gold.meta").fetchone()[0]


def silver(table: str, cycle: int) -> None:
    """The live build's partition of `table` for `cycle` as the view silver_<cycle>.<table>."""
    build = META[str(cycle)]["build_id"]
    con.execute(f"CREATE SCHEMA IF NOT EXISTS silver_{cycle}")
    prefix = paths.silver_partition(table, cycle, build)
    for key in store.list_keys(prefix + "/"):
        local = paths.local_path(settings.data_dir, key)
        if not local.exists():
            store.download_to(key, local)
    local = paths.local_path(settings.data_dir, prefix)
    con.execute(f"CREATE OR REPLACE VIEW silver_{cycle}.{table} AS SELECT * FROM read_parquet("
                f"{literal(local / '**' / '*.parquet')}, hive_partitioning = false)")


def groups(cycle: int) -> None:
    """The table `grp_<cycle>`: each id in the cycle's `cm` with its spender group (§2)."""
    bulk("cm", cycle)
    con.execute(f"""
        CREATE OR REPLACE TABLE grp_{cycle} AS
        SELECT CMTE_ID AS id, any_value(CMTE_TP) AS cmte_tp, any_value(CMTE_NM) AS cmte_nm,
            CASE WHEN any_value(CMTE_TP) = 'I' THEN 'type I' ELSE 'committee' END AS grp
        FROM cm_{cycle} GROUP BY 1""")


def grp(id_sql: str, cycle: int) -> str:
    """SQL for the spender group of `id_sql` (absent when `cm` lacks it)."""
    return f"coalesce((SELECT g.grp FROM grp_{cycle} AS g WHERE g.id = {id_sql}), 'absent')"


DMY = "CAST(try_strptime({c}, '%d-%b-%y') AS DATE)"


def h24(cycle: int) -> None:
    """The table `h_<cycle>`: the cycle's 24/48-hour file, typed, with spender group, `rn` a row
    number in file order, and `superseded` (the filing chain, Q3) and `latest_tran` (the
    per-transaction rule) beside each row. `l_<cycle>` is the latest-amendment rows."""
    groups(cycle)
    view_csv(f"h24raw_{cycle}", fec_csv("independent_expenditure", cycle))
    con.execute(f"""
        CREATE OR REPLACE TABLE h_{cycle} AS
        WITH t AS (
            SELECT row_number() OVER () AS rn, r.*,
                trim(spe_id) AS spe, nullif(trim(cand_id), '') AS cand,
                TRY_CAST(exp_amo AS DECIMAL(14, 2)) AS amt, TRY_CAST(agg_amo AS DECIMAL(14, 2)) AS agg,
                {DMY.format(c='exp_date')} AS edt, {DMY.format(c='dissem_dt')} AS ddt,
                {DMY.format(c='receipt_dat')} AS rdt,
                TRY_CAST(file_num AS BIGINT) AS fnum, TRY_CAST(prev_file_num AS BIGINT) AS pfnum,
                nullif(trim(tran_id), '') AS tran
            FROM h24raw_{cycle} AS r
        )
        SELECT t.*, coalesce(g.grp, 'absent') AS grp,
            t.fnum IN (SELECT pfnum FROM t WHERE pfnum IS NOT NULL) AS superseded,
            t.fnum = max(t.fnum) OVER (PARTITION BY t.spe, t.tran) AS latest_tran
        FROM t LEFT JOIN grp_{cycle} AS g ON g.id = t.spe""")


def adopt_h24_rule(cycle: int, rule: str) -> None:
    """`l_<cycle>`: the latest-amendment rows under `rule` ('chain' or 'tran')."""
    keep = "NOT superseded" if rule == "chain" else "coalesce(latest_tran, true)"
    con.execute(f"CREATE OR REPLACE VIEW l_{cycle} AS SELECT * FROM h_{cycle} WHERE {keep}")


def counted_pas2(cycle: int, *, from_silver: bool = True) -> None:
    """`p_<cycle>`: counted `pas2` independent expenditures with their bronze columns. From the
    live build's silver (`kind = 'ie'`, every rule applied) when `from_silver`; else spelled from
    the fresh `pas2_<cycle>` as silver spells it (24A/24E, no memo line, filer in `cm`).
    `pm_<cycle>`: the memo lines (24A/24E, MEMO_CD X). `cand` is the file's id through
    `alias_of`; `credited` is silver's candidate (handoff and corrections applied)."""
    groups(cycle)
    bulk("pas2", cycle)
    bulk("cn", cycle)
    silver("candidate", cycle)
    base = f"""
        SELECT b.SUB_ID AS sid, trim(b.CMTE_ID) AS spe, nullif(trim(b.TRAN_ID), '') AS tran,
            b.FILE_NUM AS fnum, b.RPT_TP AS rpt_tp, b.AMNDT_IND AS amndt_ind,
            b.TRANSACTION_TP AS tp, b.TRANSACTION_AMT AS amt,
            CAST(try_strptime(b.TRANSACTION_DT, '%m%d%Y') AS DATE) AS dt,
            nullif(trim(b.CAND_ID), '') AS raw_cand, b.IMAGE_NUM AS image_num, b.NAME AS payee,
            CASE WHEN b.TRANSACTION_TP = '24A' THEN 'O' ELSE 'S' END AS sup_opp,
            b.MEMO_CD AS memo_cd"""
    if from_silver:
        silver("independent_expenditure", cycle)
        con.execute(f"""
            CREATE OR REPLACE TABLE p_{cycle} AS
            {base}, s.candidate_id AS credited, s.race_id
            FROM silver_{cycle}.independent_expenditure AS s
            JOIN pas2_{cycle} AS b ON b.SUB_ID = s.source_record_id
            WHERE s.kind = 'ie'""")
    else:
        con.execute(f"""
            CREATE OR REPLACE TABLE p_{cycle} AS
            {base}, NULL::VARCHAR AS credited, NULL::VARCHAR AS race_id
            FROM pas2_{cycle} AS b
            WHERE b.TRANSACTION_TP IN ('24A', '24E') AND coalesce(b.MEMO_CD, '') <> 'X'
                AND b.CMTE_ID IN (SELECT id FROM grp_{cycle})""")
    con.execute(f"""
        CREATE OR REPLACE TABLE pm_{cycle} AS {base}
        FROM pas2_{cycle} AS b WHERE b.TRANSACTION_TP IN ('24A', '24E') AND b.MEMO_CD = 'X'""")
    for t in (f"p_{cycle}", f"pm_{cycle}"):
        con.execute(f"""
            CREATE OR REPLACE TABLE {t} AS
            SELECT p.*, coalesce(c.alias_of, p.raw_cand) AS cand, coalesce(g.grp, 'absent') AS grp
            FROM {t} AS p
            LEFT JOIN (SELECT candidate_id, any_value(alias_of) AS alias_of
                       FROM silver_{cycle}.candidate GROUP BY 1) AS c ON c.candidate_id = p.raw_cand
            LEFT JOIN grp_{cycle} AS g ON g.id = p.spe""")
    con.execute(f"""
        CREATE OR REPLACE TABLE l_{cycle}_a AS
        SELECT l.*, coalesce(c.alias_of, l.cand) AS acand
        FROM l_{cycle} AS l
        LEFT JOIN (SELECT candidate_id, any_value(alias_of) AS alias_of
                   FROM silver_{cycle}.candidate GROUP BY 1) AS c ON c.candidate_id = l.cand""")


def ladder(cycle: int, tag: str = "") -> None:
    """Q5's ladder of `l_<cycle>_a` against `p_<cycle>`, as tables, all for `cycle`:
    `m1<tag>` (spender, tran) keys matched with each side's sums; `lm<tag>` each 24/48-hour row's
    rung ('1', '2e', '2d', '3', '4e', '4d', 'memo' or NULL); `pmatch<tag>` each pas2 row's rung or NULL."""
    L, P, PM = f"l_{cycle}_a", f"p_{cycle}", f"pm_{cycle}"
    con.execute(f"""
        CREATE OR REPLACE TABLE m1{tag} AS
        WITH l AS (SELECT spe, tran, count(*) AS l_rows, sum(amt) AS l_amt,
                        string_agg(DISTINCT acand, ',' ORDER BY acand) AS l_cand,
                        string_agg(DISTINCT sup_opp, ',' ORDER BY sup_opp) AS l_so,
                        min(edt) AS l_edt, min(ddt) AS l_ddt, any_value(grp) AS grp
                   FROM {L} WHERE tran IS NOT NULL GROUP BY 1, 2),
             p AS (SELECT spe, tran, count(*) AS p_rows, sum(amt) AS p_amt,
                        string_agg(DISTINCT cand, ',' ORDER BY cand) AS p_cand,
                        string_agg(DISTINCT sup_opp, ',' ORDER BY sup_opp) AS p_so,
                        min(dt) AS p_dt
                   FROM {P} WHERE tran IS NOT NULL GROUP BY 1, 2)
        SELECT * FROM l JOIN p USING (spe, tran)""")
    # Rows left after rung 1.
    con.execute(f"""
        CREATE OR REPLACE TABLE lr{tag} AS SELECT l.* FROM {L} AS l
        WHERE NOT EXISTS (SELECT 1 FROM m1{tag} AS m WHERE m.spe = l.spe AND m.tran = l.tran)""")
    con.execute(f"""
        CREATE OR REPLACE TABLE pr{tag} AS SELECT p.* FROM {P} AS p
        WHERE NOT EXISTS (SELECT 1 FROM m1{tag} AS m WHERE m.spe = p.spe AND m.tran = p.tran)""")

    def pair(rung: str, l_date: str, key: str, window: int | None) -> None:
        # One to one within the key, in date then rn / SUB_ID order.
        lk = ", ".join(f"l.{k}" for k in key.split(", "))
        cond = " AND ".join(f"l.{k} IS NOT DISTINCT FROM p.{k}" for k in key.split(", "))
        if window is None:
            lkey, pkey = f"{key}, {l_date}", f"{key}, dt"
            dcond = f"l.{l_date} = p.dt"
        else:
            lkey, pkey = key, key
            dcond = f"abs(date_diff('day', l.{l_date}, p.dt)) <= {window}"
        con.execute(f"""
            CREATE OR REPLACE TABLE pair{tag}_{rung} AS
            WITH l AS (SELECT rn, {lk.replace('l.', '')}, {l_date},
                           row_number() OVER (PARTITION BY {lkey} ORDER BY {l_date}, fnum, rn) AS o
                       FROM lr{tag} WHERE {l_date} IS NOT NULL
                           AND rn NOT IN (SELECT rn FROM pairs{tag})),
                 p AS (SELECT sid, {key}, dt,
                           row_number() OVER (PARTITION BY {pkey} ORDER BY dt, sid) AS o
                       FROM pr{tag} WHERE dt IS NOT NULL
                           AND sid NOT IN (SELECT sid FROM pairs{tag}))
            SELECT l.rn, p.sid, '{rung}' AS rung FROM l JOIN p ON {cond} AND l.o = p.o AND {dcond}""")
        con.execute(f"INSERT INTO pairs{tag} SELECT * FROM pair{tag}_{rung}")
        con.execute(f"DROP TABLE pair{tag}_{rung}")

    con.execute(f"CREATE OR REPLACE TABLE pairs{tag} (rn BIGINT, sid UBIGINT, rung VARCHAR)")
    # Rungs 2 and 3 match on the alias-resolved candidate, under pas2's column name. Amounts
    # match in whole dollars (`wamt`): pas2 drops the cents the 24/48-hour file writes (Q4h-i, Q8l).
    con.execute(f"""CREATE OR REPLACE TABLE lr{tag} AS SELECT * EXCLUDE (cand), acand AS cand,
        trunc(amt) AS wamt FROM lr{tag}""")
    con.execute(f"CREATE OR REPLACE TABLE pr{tag} AS SELECT *, trunc(amt) AS wamt FROM pr{tag}")
    pair("2e", "edt", "spe, cand, wamt", None)
    pair("2d", "ddt", "spe, cand, wamt", None)
    con.execute(f"CREATE OR REPLACE TABLE lr{tag} AS SELECT *, coalesce(edt, ddt) AS anydt FROM lr{tag}")
    pair("3", "anydt", "spe, cand, wamt", 7)
    # Rung 4 (not in the spec's ladder; Q5 shows why): same spender, amount and date, the
    # candidate not compared. The 24/48-hour file codes Biden's id where pas2 codes Harris's.
    pair("4e", "edt", "spe, wamt", None)
    pair("4d", "ddt", "spe, wamt", None)
    con.execute(f"""
        CREATE OR REPLACE TABLE lm{tag} AS
        SELECT l.rn,
            CASE WHEN m.tran IS NOT NULL THEN '1' ELSE pr.rung END AS rung0
        FROM {L} AS l
        LEFT JOIN m1{tag} AS m ON m.spe = l.spe AND m.tran = l.tran
        LEFT JOIN pairs{tag} AS pr ON pr.rn = l.rn""")
    con.execute(f"""
        CREATE OR REPLACE TABLE lm{tag} AS
        SELECT lm.rn, coalesce(lm.rung0, CASE WHEN EXISTS (
                SELECT 1 FROM {PM} AS pm WHERE pm.spe = l.spe AND (pm.tran = l.tran
                    OR (pm.cand IS NOT DISTINCT FROM l.acand AND pm.amt = trunc(l.amt))))
            THEN 'memo' END) AS rung
        FROM lm{tag} AS lm JOIN {L} AS l USING (rn)""")
    con.execute(f"""
        CREATE OR REPLACE TABLE pmatch{tag} AS
        SELECT p.sid, CASE WHEN m.tran IS NOT NULL THEN '1' ELSE pr.rung END AS rung
        FROM {P} AS p
        LEFT JOIN m1{tag} AS m ON m.spe = p.spe AND m.tran = p.tran
        LEFT JOIN pairs{tag} AS pr ON pr.sid = p.sid""")


def ec_table(cycle: int) -> None:
    """`ec_<cycle>`: the electioneering file, typed; `rn` its row number in file order."""
    groups(cycle)
    view_csv(f"ecraw_{cycle}", fec_csv("ElectioneeringComm", cycle))
    con.execute(f"""
        CREATE OR REPLACE TABLE ec_{cycle} AS
        SELECT row_number() OVER () AS rn, e.*,
            nullif(trim(CANDIDATE_ID), '') AS cand, trim(COMMITTEE_ID) AS spon,
            TRY_CAST(REPORTED_DISBURSEMENT_AMOUNT AS DECIMAL(14, 2)) AS amt,
            TRY_CAST(CALCULATED_CANDIDATE_SHARE AS DECIMAL(14, 2)) AS share,
            TRY_CAST(NUMBER_OF_CANDIDATES AS INTEGER) AS ncand,
            {DMY.format(c='DISBURSEMENT_DATE')} AS ddt, {DMY.format(c='COMMUNICATION_DATE')} AS cdt,
            {DMY.format(c='PUBLIC_DISBURSEMENT_DATE')} AS pdt,
            coalesce(g.grp, 'absent') AS grp, g.cmte_tp
        FROM ecraw_{cycle} AS e LEFT JOIN grp_{cycle} AS g ON g.id = trim(e.COMMITTEE_ID)""")


def cc_table(cycle: int) -> None:
    """`cc_<cycle>`: the communication-costs file, typed."""
    groups(cycle)
    view_csv(f"ccraw_{cycle}", fec_csv("CommunicationCosts", cycle))
    con.execute(f"""
        CREATE OR REPLACE TABLE cc_{cycle} AS
        SELECT c.*, TRY_CAST(TRANSACTION_AMT AS DECIMAL(14, 2)) AS amt,
            CAST(try_strptime(TRANSACTION_DT, '%Y%m%d') AS DATE) AS dt,
            TRY_CAST(SUB_ID AS UBIGINT) AS sid, TRY_CAST(FILE_NUM AS BIGINT) AS fnum,
            nullif(trim(TRAN_ID), '') AS tran, trim(CMTE_ID) AS filer,
            coalesce(g.grp, 'absent') AS grp, g.cmte_tp
        FROM ccraw_{cycle} AS c LEFT JOIN grp_{cycle} AS g ON g.id = trim(c.CMTE_ID)""")


print("2024 build", META["2024"]["build_id"], META["2024"]["source_dates"].get("pas2"),
      "| 2026 build", META["2026"]["build_id"], META["2026"]["source_dates"].get("pas2"),
      "| duckdb", con.execute("SELECT version()").fetchone()[0], "|", Limits.from_settings(settings))
```

## Q1: shape of the three CSVs (2024)

```python
import re

# Q1: the three 2024 CSVs as served.
FIELD = r'"(?:[^"]|"")*"'
QUOTED = re.compile(rf"^{FIELD}(?:,{FIELD})*$")
files = {
    "h24raw_2024": fec_csv("independent_expenditure", 2024),
    "ec_2024": fec_csv("ElectioneeringComm", 2024),
    "cc_2024": fec_csv("CommunicationCosts", 2024),
}
for name, path in files.items():
    data = path.read_bytes()
    lines = data.split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    with path.open(newline="", encoding="utf-8") as f:
        records = sum(1 for _ in csv.reader(f))
    try:
        data.decode("utf-8")
        utf8 = "yes"
    except UnicodeDecodeError:
        utf8 = "no"
    print(f"{path.name}: bytes {len(data):,}; physical lines {len(lines):,}; CSV records {records:,}"
          f" (embedded newlines: {len(lines) - records:,}); BOM {data.startswith(b'\xef\xbb\xbf')};"
          f" CRLF lines {sum(l.endswith(b'\r') for l in lines):,}; ends with LF {data.endswith(b'\n')};"
          f" UTF-8 as served {utf8}; lines not fully double-quoted"
          f" {sum(not QUOTED.match(l.decode('utf-8', 'replace').rstrip('\r')) for l in lines):,}")

h24(2024)

show("Q1a. The 24/48-hour file: rows, casts, keys", """
SELECT count(*) AS rows, sum(amt) AS dollars,
    count(*) FILTER (WHERE amt IS NULL AND exp_amo IS NOT NULL) AS amount_fails,
    count(*) FILTER (WHERE exp_amo IS NULL) AS amount_blank,
    count(*) FILTER (WHERE agg IS NULL AND agg_amo IS NOT NULL) AS agg_fails,
    count(*) FILTER (WHERE edt IS NULL AND exp_date IS NOT NULL) AS exp_date_fails,
    count(*) FILTER (WHERE exp_date IS NULL) AS exp_date_blank,
    count(*) FILTER (WHERE ddt IS NULL AND dissem_dt IS NOT NULL) AS dissem_fails,
    count(*) FILTER (WHERE dissem_dt IS NULL) AS dissem_blank,
    count(*) FILTER (WHERE exp_date IS NULL AND dissem_dt IS NULL) AS both_blank,
    count(*) FILTER (WHERE rdt IS NULL) AS receipt_fails_or_blank,
    count(*) FILTER (WHERE fnum IS NULL) AS file_num_fails_or_blank,
    count(*) FILTER (WHERE tran IS NULL) AS tran_id_blank,
    count(*) FILTER (WHERE spe_nam <> trim(spe_nam)) AS spender_name_untrimmed,
    count(*) FILTER (WHERE spe_id <> trim(spe_id)) AS spender_id_untrimmed,
    count(*) - count(DISTINCT (spe, fnum, tran)) AS rows_beyond_unique_key,
    min(edt) AS exp_earliest, max(edt) AS exp_latest, min(ddt) AS dissem_earliest, max(ddt) AS dissem_latest
FROM h_2024""")

show("Q1b. The 24/48-hour key (spe_id, file_num, tran_id): groups on more than one row", """
SELECT n AS rows_per_key, count(*) AS keys, sum(n) AS rows, sum(d) AS dollars, sum(same::INT) AS identical_but_rn
FROM (SELECT spe, fnum, tran, count(*) AS n, sum(amt) AS d,
          count(DISTINCT (cand_id, exp_amo, exp_date, sup_opp, pur, pay, image_num, dissem_dt)) = 1 AS same
      FROM h_2024 GROUP BY ALL HAVING count(*) > 1)
GROUP BY ALL ORDER BY ALL""")

for col in ("amndt_ind", "sup_opp", "ele_type", "can_office", "fec_election_yr"):
    show(f"Q1c. 24/48-hour `{col}`", f"""
    SELECT {col}, count(*) AS rows, sum(amt) AS dollars FROM h_2024 GROUP BY ALL ORDER BY rows DESC""")

show("Q1d. 24/48-hour: exp_amo against agg_amo", """
SELECT CASE WHEN agg IS NULL THEN 'agg blank' WHEN agg = amt THEN 'agg = amount'
            WHEN agg > amt THEN 'agg > amount' ELSE 'agg < amount' END AS relation,
    count(*) AS rows, sum(amt) AS dollars
FROM h_2024 GROUP BY ALL ORDER BY rows DESC""")

show("Q1e. 24/48-hour: amounts by sign", """
SELECT sign(amt) AS sign, count(*) AS rows, sum(amt) AS dollars FROM h_2024 GROUP BY ALL ORDER BY ALL""")

ec_table(2024)
show("Q1f. Electioneering: rows, casts, keys", """
SELECT count(*) AS rows, sum(share) AS share_dollars,
    count(*) FILTER (WHERE amt IS NULL) AS amount_fails_or_blank,
    count(*) FILTER (WHERE share IS NULL) AS share_fails_or_blank,
    count(*) FILTER (WHERE ncand IS NULL) AS ncand_fails_or_blank,
    count(*) FILTER (WHERE ddt IS NULL) AS disb_date_fails_or_blank,
    count(*) FILTER (WHERE cdt IS NULL) AS comm_date_fails_or_blank,
    count(*) FILTER (WHERE pdt IS NULL) AS public_date_fails_or_blank,
    count(*) FILTER (WHERE cand IS NULL) AS candidate_blank,
    count(DISTINCT SB_IMAGE_NUM) AS image_nums,
    count(*) - (SELECT count(*) FROM (SELECT DISTINCT * EXCLUDE (rn) FROM ec_2024)) AS fully_identical_extra_rows,
    min(ddt) AS earliest, max(ddt) AS latest
FROM ec_2024""")
show("Q1g. Electioneering NUMBER_OF_CANDIDATES", """
SELECT ncand, count(*) AS rows, sum(share) AS share_dollars FROM ec_2024 GROUP BY ALL ORDER BY ALL""")

cc_table(2024)
show("Q1h. Communication costs: rows, casts, keys", """
SELECT count(*) AS rows, sum(amt) AS dollars,
    count(*) FILTER (WHERE amt IS NULL) AS amount_fails_or_blank,
    count(*) FILTER (WHERE dt IS NULL AND TRANSACTION_DT IS NOT NULL) AS date_fails,
    count(*) FILTER (WHERE TRANSACTION_DT IS NULL) AS date_blank,
    count(*) FILTER (WHERE sid IS NULL) AS sub_id_fails, count(DISTINCT sid) AS distinct_sub_id,
    count(*) FILTER (WHERE fnum IS NULL) AS file_num_fails_or_blank,
    count(*) FILTER (WHERE nullif(trim(CAND_ID), '') IS NULL) AS candidate_blank,
    min(dt) AS earliest, max(dt) AS latest
FROM cc_2024""")
for col in ("TRANSACTION_TP", "SUPPORT_OPPOSE_IND", "COMMUNICATION_TP", "COMMUNICATION_CLASS",
            "FORM_TP_CD", "SCHED_TP_CD", "RPT_YR", "CAND_OFFICE"):
    show(f"Q1i. Communication costs `{col}`", f"""
    SELECT {col}, count(*) AS rows, sum(amt) AS dollars FROM cc_2024 GROUP BY ALL ORDER BY rows DESC""")

show("Q1j. 24/48-hour: the 20 largest rows", """
SELECT spe, spe_nam, grp, cand, sup_opp, amt, agg, exp_date, dissem_dt, fnum, amndt_ind, tran, superseded, pur
FROM h_2024 ORDER BY amt DESC LIMIT 20""")
show("Q1k. 24/48-hour: rows by amount band", """
SELECT CASE WHEN amt >= 1e8 THEN '>= $100M' WHEN amt >= 1e7 THEN '$10M-100M' WHEN amt >= 1e6 THEN '$1M-10M'
            ELSE '< $1M' END AS band, count(*) AS rows, sum(amt) AS dollars
FROM h_2024 GROUP BY ALL ORDER BY dollars DESC""")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:10:51+00:00
https://www.fec.gov/files/bulk-downloads/2024/CommunicationCosts_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:07 GMT | bytes 237,322 | downloaded 2026-11-24T02:10:53+00:00
independent_expenditure_2024.csv: bytes 19,534,174; physical lines 73,450; CSV records 73,450 (embedded newlines: 0); BOM False; CRLF lines 0; ends with LF True; UTF-8 as served yes; lines not fully double-quoted 1
ElectioneeringComm_2024.csv: bytes 18,370; physical lines 70; CSV records 70 (embedded newlines: 0); BOM False; CRLF lines 0; ends with LF True; UTF-8 as served yes; lines not fully double-quoted 1
CommunicationCosts_2024.csv: bytes 237,322; physical lines 780; CSV records 780 (embedded newlines: 0); BOM False; CRLF lines 0; ends with LF True; UTF-8 as served yes; lines not fully double-quoted 1
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
```

**Q1a. The 24/48-hour file: rows, casts, keys  (0 s)**

| rows | dollars | amount_fails | amount_blank | agg_fails | exp_date_fails | exp_date_blank | dissem_fails | dissem_blank | both_blank | receipt_fails_or_blank | file_num_fails_or_blank | tran_id_blank | spender_name_untrimmed | spender_id_untrimmed | rows_beyond_unique_key | exp_earliest | exp_latest | dissem_earliest | dissem_latest |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 73,449 | 49,679,404,427 | 0 | 0 | 0 | 0 | 25,780 | 0 | 14,141 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2023-01-02 | 2024-12-30 | 2004-10-17 | 2042-11-01 |

**Q1b. The 24/48-hour key (spe_id, file_num, tran_id): groups on more than one row  (0 s)**

| rows_per_key | keys | rows | dollars | identical_but_rn |
|---|---|---|---|---|

**Q1c. 24/48-hour `amndt_ind`  (0 s)**

| amndt_ind | rows | dollars |
|---|---|---|
| N | 60,573 | 49,363,452,382 |
| A1 | 10,043 | 298,707,294 |
| A2 | 2,756 | 14,048,046 |
| A3 | 65 | 2,755,239 |
| A4 | 12 | 441,467 |

**Q1c. 24/48-hour `sup_opp`  (0 s)**

| sup_opp | rows | dollars |
|---|---|---|
| S | 54,969 | 46,940,819,964 |
| O | 18,363 | 2,733,428,534 |
|  | 117 | 5,155,929 |

**Q1c. 24/48-hour `ele_type`  (0 s)**

| ele_type | rows | dollars |
|---|---|---|
| G | 53,821 | 5,565,582,146 |
| P | 18,636 | 44,067,186,347 |
| O | 350 | 15,722,324 |
| S | 261 | 13,547,758 |
| R | 217 | 5,407,508 |
| C | 164 | 11,958,345 |

**Q1c. 24/48-hour `can_office`  (0 s)**

| can_office | rows | dollars |
|---|---|---|
| H | 30,900 | 1,393,753,040 |
| P | 25,513 | 40,520,563,121 |
| S | 17,020 | 7,764,809,407 |
|  | 16 | 278,859 |

**Q1c. 24/48-hour `fec_election_yr`  (0 s)**

| fec_election_yr | rows | dollars |
|---|---|---|
| 2024 | 73,449 | 49,679,404,427 |

**Q1d. 24/48-hour: exp_amo against agg_amo  (0 s)**

| relation | rows | dollars |
|---|---|---|
| agg > amount | 68,945 | 5,520,920,688 |
| agg = amount | 3,909 | 246,980,372 |
| agg < amount | 435 | 43,906,459,411 |
| agg blank | 160 | 5,043,956 |

**Q1e. 24/48-hour: amounts by sign  (0 s)**

| sign | rows | dollars |
|---|---|---|
| -1 | 21 | -1,257,602 |
| 0 | 25 | 0 |
| 1 | 73,403 | 49,680,662,029 |

```text
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:10:51+00:00
ecraw_2024: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
```

**Q1f. Electioneering: rows, casts, keys  (0 s)**

| rows | share_dollars | amount_fails_or_blank | share_fails_or_blank | ncand_fails_or_blank | disb_date_fails_or_blank | comm_date_fails_or_blank | public_date_fails_or_blank | candidate_blank | image_nums | fully_identical_extra_rows | earliest | latest |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 69 | 9,480,874 | 0 | 0 | 0 | 0 | 0 | 2 | 24 | 40 | 2 | 2024-01-10 | 2024-10-31 |

**Q1g. Electioneering NUMBER_OF_CANDIDATES  (0 s)**

| ncand | rows | share_dollars |
|---|---|---|
| 1 | 51 | 9,150,804 |
| 2 | 18 | 330,070 |

```text
https://www.fec.gov/files/bulk-downloads/2024/CommunicationCosts_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:07 GMT | bytes 237,322 | downloaded 2026-11-24T02:10:53+00:00
ccraw_2024: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
```

**Q1h. Communication costs: rows, casts, keys  (0 s)**

| rows | dollars | amount_fails_or_blank | date_fails | date_blank | sub_id_fails | distinct_sub_id | file_num_fails_or_blank | candidate_blank | earliest | latest |
|---|---|---|---|---|---|---|---|---|---|---|
| 779 | 7,098,726 | 0 | 0 | 0 | 0 | 779 | 0 | 0 | 2023-03-31 | 2024-12-31 |

**Q1i. Communication costs `TRANSACTION_TP`  (0 s)**

| TRANSACTION_TP | rows | dollars |
|---|---|---|
| 24F | 693 | 7,043,880 |
| 24N | 86 | 54,846 |

**Q1i. Communication costs `SUPPORT_OPPOSE_IND`  (0 s)**

| SUPPORT_OPPOSE_IND | rows | dollars |
|---|---|---|
| S | 687 | 7,037,654 |
| O | 86 | 54,846 |
| 24F | 6 | 6,226 |

**Q1i. Communication costs `COMMUNICATION_TP`  (0 s)**

| COMMUNICATION_TP | rows | dollars |
|---|---|---|
| DM | 535 | 6,186,067 |
| O | 238 | 906,433 |
| M | 5 | 5,524 |
| L | 1 | 703 |

**Q1i. Communication costs `COMMUNICATION_CLASS`  (0 s)**

| COMMUNICATION_CLASS | rows | dollars |
|---|---|---|
| M | 770 | 7,045,775 |
| E | 9 | 52,951 |

**Q1i. Communication costs `FORM_TP_CD`  (0 s)**

| FORM_TP_CD | rows | dollars |
|---|---|---|
| F7 | 779 | 7,098,726 |

**Q1i. Communication costs `SCHED_TP_CD`  (0 s)**

| SCHED_TP_CD | rows | dollars |
|---|---|---|
| F76 | 779 | 7,098,726 |

**Q1i. Communication costs `RPT_YR`  (0 s)**

| RPT_YR | rows | dollars |
|---|---|---|
| 2024 | 773 | 7,092,500 |
| 2023 | 6 | 6,226 |

**Q1i. Communication costs `CAND_OFFICE`  (0 s)**

| CAND_OFFICE | rows | dollars |
|---|---|---|
| H | 573 | 3,275,528 |
| S | 154 | 3,021,530 |
| P | 52 | 801,669 |

**Q1j. 24/48-hour: the 20 largest rows  (0 s)**

| spe | spe_nam | grp | cand | sup_opp | amt | agg | exp_date | dissem_dt | fnum | amndt_ind | tran | superseded | pur |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C00875427 | THE COURT OF DIVINE JUSTICE | committee | P40007304 | S | 9,978,412,568 | 2,888,374,799 | 20-APR-24 | 20-APR-24 | 1,778,759 | N | WFT20243201436-1 | False | Political Contribution |
| C00874586 | THE COMMITTEE OF 300 | absent | P40019226 | S | 9,778,412,568 | 257,875,349 |  | 31-MAR-24 | 1,766,664 | N | WFT20242312317-1 | False | Political Contribution |
| C00785352 | THE COMMITTEE OF 300 | absent | P40019226 | S | 9,000,000,000 | 592,018 | 25-MAR-24 | 27-MAR-24 | 1,766,323 | N | WFT2024227513-1 | False | DEPOSIT FOR WINNING IN ELECTION |
| C00874586 | THE COMMITTEE OF 300 | absent | P40007304 | S | 7,959,594,848 | 2,458,043,468 | 14-JUL-24 | 14-JUL-24 | 1,798,067 | N | WFT20246141728-1 | False | FOR WIN THIS ELECTION |
| C00873521 | Republican Emo Girl | absent | S4OK00398 | S | 6,347,882,325 | 2,024 | 17-MAR-24 | 17-MAR-24 | 1,763,978 | N | WFT20242171533-1 | False | Senate campaign. |
| C00874909 | The Masonic Illuminati Eye | absent | P40007304 | S | 579,874,829 | 257,192,836 | 05-APR-24 | 02-APR-24 | 1,767,013 | N | WFT2024321734-1 | False | Political Contribution |
| C00843094 | Gus Associates | absent | H4NM02098 | S | 255,000,000 | 2,024 | 15-JUN-23 | 15-JUN-23 | 1,707,511 | N | WFT202351617-1 | False | funding for waltuh white's campaign |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017507 | True | Voter outreach |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017510 | True | Voter outreach |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017515 | True | Voter outreach |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017513 | True | Voter outreach |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017514 | True | Voter outreach |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017508 | True | Voter outreach |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017509 | True | Voter outreach |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017511 | True | Voter outreach |
| C90019357 | Food & Water Action | type I | P00009423 | S | 114,056,874 | 1,026,537,161 | 05-NOV-24 |  | 1,848,231 | N | 500017512 | True | Voter outreach |
| C00825851 | MAKE AMERICA GREAT AGAIN INC. | committee | P80000722 | O | 30,033,271 | 284,977,349 | 25-OCT-24 | 30-OCT-24 | 1,845,199 | N | SE.8507 | False | PLACED MEDIA: TV |
| C00825851 | MAKE AMERICA GREAT AGAIN INC. | committee | P80000722 | O | 24,083,279 | 239,142,615 | 18-OCT-24 | 23-OCT-24 | 1,841,262 | N | SE.8450 | False | PLACED MEDIA: TV |
| C00825851 | MAKE AMERICA GREAT AGAIN INC. | committee | P80000722 | O | 21,798,392 | 208,627,135 | 11-OCT-24 | 16-OCT-24 | 1,830,216 | N | SE.8335 | False | PLACED MEDIA: TV |
| C00825851 | MAKE AMERICA GREAT AGAIN INC. | committee | P80000722 | O | 21,147,261 | 123,938,948 | 23-AUG-24 | 28-AUG-24 | 1,813,195 | N | SE.8029 | False | PLACED MEDIA: TV |

**Q1k. 24/48-hour: rows by amount band  (0 s)**

| band | rows | dollars |
|---|---|---|
| >= $100M | 16 | 44,925,689,004 |
| < $1M | 72,517 | 2,350,601,534 |
| $1M-10M | 890 | 1,993,063,303 |
| $10M-100M | 26 | 410,050,586 |

All three files are UTF-8 with LF line ends and no BOM. They have no embedded newlines and no
record of another width. Every data field is double-quoted, and the header row is not (the one
"line not fully double-quoted" in each). The headers are as spec §3 lists them, the 24/48-hour
file's in lower case. Every amount and date casts. The date formats are `DD-MON-YY` in the
24/48-hour and electioneering files and `YYYYMMDD` in the communication-costs file.

**The 24/48-hour file.** 73,449 rows, and (`spe_id`, `file_num`, `tran_id`) is unique. 25,780
rows have no `exp_date` and 14,141 no `dissem_dt`, but none lacks both. Its dissemination dates
run from 2004 to 2042, filers' typos. Sixteen rows of $100M or more hold $44.9B of its $49.7B
(Q1j–k): seven web-form hoaxes (Q2b) and nine copies of a $114M Form 5 line, which an amendment
supersedes (Q3). `agg_amo` is the year-to-date aggregate; it is below `exp_amo` only on 435 rows,
the hoaxes among them.

**The electioneering file.** 69 rows, 25 sponsors, 40 image numbers. Two rows are copies in every
column. They are two-candidate disbursements with no candidate id, one row per candidate (Q9i).

**The communication-costs file.** 779 rows, `SUB_ID` unique, every row a Form 7 line 6 (`F76`).
Six 2023 rows ($6,226) carry `24F` in `SUPPORT_OPPOSE_IND`, and `PURPOSE` is never filled.

## Q2: who the spenders are (2024)

```python
# Q2: who the spenders are (2024).
h24(2024)
adopt_h24_rule(2024, "chain")
counted_pas2(2024)
silver("reported_total", 2024)

show("Q2a. 24/48-hour spenders by group and id prefix (every row; and rows on no superseded filing)", """
SELECT grp, left(spe, 2) AS prefix, count(DISTINCT spe) AS spenders, count(*) AS rows, sum(amt) AS dollars,
    count(*) FILTER (WHERE NOT superseded) AS rows_unsuperseded,
    sum(amt) FILTER (WHERE NOT superseded) AS dollars_unsuperseded
FROM h_2024 GROUP BY ALL ORDER BY grp, prefix""")

show("Q2b. Every `absent` spender in the 24/48-hour file", """
SELECT spe, any_value(trim(spe_nam)) AS name, count(*) AS rows, sum(amt) AS dollars,
    sum(amt) FILTER (WHERE NOT superseded) AS dollars_unsuperseded,
    string_agg(DISTINCT left(tran, 3), ',') AS tran_prefixes, min(rdt) AS first_received,
    (SELECT count(*) FROM p_2024 AS p WHERE p.spe = h.spe) AS pas2_rows
FROM h_2024 AS h WHERE grp = 'absent' GROUP BY 1 ORDER BY dollars DESC""")

show("Q2c. 24/48-hour transaction ids beginning WFT (FEC's web-form filings) by group", """
SELECT grp, tran LIKE 'WFT%' AS web_form, count(DISTINCT spe) AS spenders, count(*) AS rows, sum(amt) AS dollars,
    sum(amt) FILTER (WHERE NOT superseded) AS dollars_unsuperseded
FROM h_2024 GROUP BY ALL ORDER BY ALL""")

show("Q2d. Counted `pas2` independent expenditures by spender group and id prefix", """
SELECT grp, left(spe, 2) AS prefix, count(DISTINCT spe) AS spenders, count(*) AS rows, sum(amt) AS dollars
FROM p_2024 GROUP BY ALL ORDER BY grp, prefix""")

show("Q2e. Spenders in both files, by group (24/48-hour rows on no superseded filing)", """
WITH h AS (SELECT spe, any_value(grp) AS grp, count(*) AS h_rows, sum(amt) AS h_dollars
           FROM l_2024 GROUP BY 1),
     p AS (SELECT spe, any_value(grp) AS grp, count(*) AS p_rows, sum(amt) AS p_dollars FROM p_2024 GROUP BY 1)
SELECT coalesce(h.grp, p.grp) AS grp,
    CASE WHEN h.spe IS NULL THEN 'only in pas2' WHEN p.spe IS NULL THEN 'only in 24/48-hour' ELSE 'in both' END AS where_,
    count(*) AS spenders, sum(h_rows) AS h_rows, sum(h_dollars) AS h_dollars, sum(p_rows) AS p_rows, sum(p_dollars) AS p_dollars
FROM h FULL JOIN p USING (spe) GROUP BY ALL ORDER BY ALL""")

show("Q2f. `type I` filers: counted pas2 dollars against reported_total.independent_expenditures", """
WITH f AS (
    SELECT g.id, g.cmte_nm, coalesce(p.d, 0) AS pas2, r.independent_expenditures AS reported
    FROM grp_2024 AS g
    LEFT JOIN (SELECT spe, sum(amt) AS d FROM p_2024 GROUP BY 1) AS p ON p.spe = g.id
    LEFT JOIN silver_2024.reported_total AS r ON r.committee_id = g.id
    WHERE g.grp = 'type I' AND (p.d IS NOT NULL OR coalesce(r.independent_expenditures, 0) <> 0))
SELECT CASE WHEN reported IS NULL THEN 'no reported figure' WHEN reported = 0 THEN 'reported 0'
            WHEN abs(pas2 - reported) <= 0.01 * abs(reported) THEN 'within 1%'
            WHEN pas2 > reported THEN 'pas2 more than 1% above' ELSE 'pas2 more than 1% below' END AS band,
    count(*) AS filers, sum(pas2) AS pas2_dollars, sum(reported) AS reported_dollars
FROM f GROUP BY ALL ORDER BY filers DESC""")

show("Q2g. `type I` filers more than 1% apart (or with no reported figure), by the gap", """
WITH f AS (
    SELECT g.id, g.cmte_nm, coalesce(p.d, 0) AS pas2, r.independent_expenditures AS reported,
        (SELECT sum(amt) FROM l_2024 AS l WHERE l.spe = g.id) AS h24_unsuperseded
    FROM grp_2024 AS g
    LEFT JOIN (SELECT spe, sum(amt) AS d FROM p_2024 GROUP BY 1) AS p ON p.spe = g.id
    LEFT JOIN silver_2024.reported_total AS r ON r.committee_id = g.id
    WHERE g.grp = 'type I' AND (p.d IS NOT NULL OR coalesce(r.independent_expenditures, 0) <> 0))
SELECT id, cmte_nm, pas2, reported, pas2 - coalesce(reported, 0) AS gap, h24_unsuperseded
FROM f WHERE reported IS NULL OR abs(pas2 - reported) > 0.01 * abs(reported)
ORDER BY abs(pas2 - coalesce(reported, 0)) DESC LIMIT 40""")

show("Q2h. Ratio pas2 ÷ reported, deciles, `type I` filers with a reported figure above 0", """
WITH f AS (
    SELECT coalesce(p.d, 0) / r.independent_expenditures AS ratio
    FROM grp_2024 AS g
    LEFT JOIN (SELECT spe, sum(amt) AS d FROM p_2024 GROUP BY 1) AS p ON p.spe = g.id
    JOIN silver_2024.reported_total AS r ON r.committee_id = g.id
    WHERE g.grp = 'type I' AND r.independent_expenditures > 0)
SELECT count(*) AS filers,
    round(quantile_cont(ratio, 0.1), 4) AS p10, round(quantile_cont(ratio, 0.25), 4) AS p25,
    round(median(ratio), 4) AS median, round(quantile_cont(ratio, 0.75), 4) AS p75,
    round(quantile_cont(ratio, 0.9), 4) AS p90
FROM f""")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
```

**Q2a. 24/48-hour spenders by group and id prefix (every row; and rows on no superseded filing)  (0 s)**

| grp | prefix | spenders | rows | dollars | rows_unsuperseded | dollars_unsuperseded |
|---|---|---|---|---|---|---|
| absent | C0 | 7 | 8 | 33,921,014,570 | 8 | 33,921,014,570 |
| absent | C9 | 1 | 1 | 64,107 | 1 | 64,107 |
| committee | C0 | 833 | 59,637 | 14,636,173,595 | 51,822 | 14,331,231,639 |
| committee | C9 | 1 | 23 | 882,400 | 17 | 582,102 |
| type I | C9 | 159 | 13,780 | 1,121,269,756 | 9,578 | 86,206,678 |

**Q2b. Every `absent` spender in the 24/48-hour file  (0 s)**

| spe | name | rows | dollars | dollars_unsuperseded | tran_prefixes | first_received | pas2_rows |
|---|---|---|---|---|---|---|---|
| C00874586 | THE COMMITTEE OF 300 | 2 | 17,738,007,416 | 17,738,007,416 | WFT | 2024-03-31 | 0 |
| C00785352 | THE COMMITTEE OF 300 | 1 | 9,000,000,000 | 9,000,000,000 | WFT | 2024-03-26 | 0 |
| C00873521 | Republican Emo Girl | 1 | 6,347,882,325 | 6,347,882,325 | WFT | 2024-03-17 | 0 |
| C00874909 | The Masonic Illuminati Eye | 1 | 579,874,829 | 579,874,829 | WFT | 2024-04-02 | 0 |
| C00843094 | Gus Associates | 1 | 255,000,000 | 255,000,000 | WFT | 2023-06-16 | 0 |
| C00734400 | CYRUS SAJNA FOR CONGRESS COMMITTEE | 1 | 250,000 | 250,000 | WFT | 2023-10-21 | 0 |
| C90022054 | Casey Family Farms | 1 | 64,107 | 64,107 | F57 | 2023-08-10 | 0 |
| C00830596 | THE AMERICAN POLITICAL PARTY | 1 | 0 | 0 | WFT | 2023-01-02 | 0 |

**Q2c. 24/48-hour transaction ids beginning WFT (FEC's web-form filings) by group  (0 s)**

| grp | web_form | spenders | rows | dollars | dollars_unsuperseded |
|---|---|---|---|---|---|
| absent | False | 1 | 1 | 64,107 | 64,107 |
| absent | True | 7 | 8 | 33,921,014,570 | 33,921,014,570 |
| committee | False | 772 | 57,963 | 4,606,095,583 | 4,315,991,981 |
| committee | True | 85 | 1,697 | 10,030,960,412 | 10,015,821,760 |
| type I | False | 158 | 13,766 | 1,120,758,858 | 85,695,781 |
| type I | True | 2 | 14 | 510,897 | 510,897 |

**Q2d. Counted `pas2` independent expenditures by spender group and id prefix  (0 s)**

| grp | prefix | spenders | rows | dollars |
|---|---|---|---|---|
| committee | C0 | 961 | 58,420 | 4,336,897,334 |
| committee | C9 | 1 | 17 | 582,102 |
| type I | C9 | 153 | 15,404 | 84,903,413 |

**Q2e. Spenders in both files, by group (24/48-hour rows on no superseded filing)  (0 s)**

| grp | where_ | spenders | h_rows | h_dollars | p_rows | p_dollars |
|---|---|---|---|---|---|---|
| absent | only in 24/48-hour | 8 | 9 | 33,921,078,677 |  |  |
| committee | in both | 799 | 51,633 | 4,348,534,355 | 56,050 | 4,334,343,620 |
| committee | only in 24/48-hour | 35 | 206 | 9,983,279,387 |  |  |
| committee | only in pas2 | 163 |  |  | 2,387 | 3,135,816 |
| type I | in both | 135 | 9,430 | 84,118,124 | 10,789 | 84,418,730 |
| type I | only in 24/48-hour | 24 | 148 | 2,088,554 |  |  |
| type I | only in pas2 | 18 |  |  | 4,615 | 484,683 |

**Q2f. `type I` filers: counted pas2 dollars against reported_total.independent_expenditures  (0 s)**

| band | filers | pas2_dollars | reported_dollars |
|---|---|---|---|
| within 1% | 142 | 73,231,868 | 73,239,356 |
| pas2 more than 1% below | 57 | 11,671,545 | 14,165,976 |

**Q2g. `type I` filers more than 1% apart (or with no reported figure), by the gap  (0 s)**

| id | cmte_nm | pas2 | reported | gap | h24_unsuperseded |
|---|---|---|---|---|---|
| C90016023 | 32BJ UNITED AMERICAN DREAM FUND | 45,259 | 677,463 | -632,204 | 609,475 |
| C90016510 | PLANNED PARENTHOOD ADVOCATES OF WISCONSIN POLITICAL FUND | 125,580 | 706,738 | -581,158 | 706,738 |
| C90022781 | EARTHJUSTICE ACTION | 0 | 293,577 | -293,577 | 293,577 |
| C90020447 | FLIC VOTES INC. | 0 | 209,322 | -209,322 | 207,175 |
| C90011156 | WORKING AMERICA | 11,041,759 | 11,188,075 | -146,316 | 11,016,168 |
| C90020058 | RED WINE AND BLUE | 0 | 134,695 | -134,695 | 134,695 |
| C90022567 | SOMOS THE FUTURE | 0 | 90,020 | -90,020 | 90,020 |
| C90020454 | FREEDOM ACTION NOW INC. | 0 | 84,696 | -84,696 | 84,468 |
| C90022997 | PAC FOR GEORGIA'S YOUTH | 0 | 76,999 | -76,999 | 76,999 |
| C90021643 | PA STANDS UP POWER | 3,049 | 27,156 | -24,107 | 32,837 |
| C90013517 | PAGE COMMUNICATIONS L.L.C. | 0 | 17,665 | -17,665 |  |
| C90022393 | FAITH VOTERS FOR GOOD | 144,814 | 160,226 | -15,412 | 271,344 |
| C90022146 | SEATTLE DSA | 0 | 15,363 | -15,363 | 7,833 |
| C90022732 | PRO CHOICE MISSOURI DBA ABORTION ACTION MISSOURI | 0 | 12,090 | -12,090 |  |
| C90021841 | FINANCIAL SERVICES STAKEHOLDER ACTION NFP, D.B.A. PRIVATE EQUITY STAKEHOLDER ACTION | 0 | 11,479 | -11,479 | 11,479 |
| C90018516 | CALIFORNIA PROFESSIONAL FIREFIGHTERS | 0 | 10,674 | -10,674 |  |
| C90014515 | CALIFORNIA FEDERATION OF TEACHERS COPE | 0 | 10,167 | -10,167 |  |
| C90022161 | TOGETHERSF ACTION | 0 | 10,024 | -10,024 |  |
| C90022690 | PUBLIC CITIZEN INC | 0 | 9,455 | -9,455 |  |
| C90020363 | NAKASEC ACTION FUND | 133,482 | 141,195 | -7,713 | 141,227 |
| C90022948 | U.S. VETERANS FOR UKRAINE INC. | 0 | 7,120 | -7,120 | 2,070 |
| C90022724 | ETHEL A EDWARDS | 0 | 6,949 | -6,949 |  |
| C90018391 | THE FAMILY FOUNDATION ACTION | 0 | 6,900 | -6,900 | 33,892 |
| C90022740 | MARCH FOR OUR LIVES ACTION FUND | 81,234 | 87,853 | -6,619 | 80,554 |
| C90021692 | 350 WISCONSIN ACTION | 9,879 | 15,099 | -5,220 | 1,134 |
| C90022989 | LABORERS BUILDING A BETTER NEW YORK | 15,000 | 20,000 | -5,000 | 20,000 |
| C90018235 | KEYSTONE PROGRESS | 0 | 5,000 | -5,000 |  |
| C90018078 | NEW JERSEY CITIZEN ACTION | 0 | 4,757 | -4,757 |  |
| C90023250 | MAXWELL 4 AMERICA  | 0 | 4,542 | -4,542 |  |
| C90022625 | ONE TALAHASSEE | 0 | 4,334 | -4,334 |  |
| C90023060 | JOINT COUNCIL OF TEAMSTERS NO. 28 | 0 | 4,078 | -4,078 |  |
| C90022823 | THOMAS THORESEN FOR CONCERNED WI HUNTERS AND ANGLERS | 0 | 4,045 | -4,045 |  |
| C90019027 | METRO DC DEMOCRATIC SOCIALISTS OF AMERICA | 0 | 3,549 | -3,549 |  |
| C90022435 | COBALT ADVOCATES  | 0 | 3,305 | -3,305 |  |
| C90023094 | INTERNATIONAL BROTHERHOOD OF 42 JOINT COUNCIL | 0 | 3,021 | -3,021 | 3,021 |
| C90023136 | ROSE MARY HUTCHINSON | 0 | 2,825 | -2,825 |  |
| C90023003 | HERR, STEVEN | 0 | 2,614 | -2,614 | 2,614 |
| C90022195 | RHODE ISLAND DEMOCRATIC SOCIALISTS OF AMERICA | 0 | 2,203 | -2,203 |  |
| C90021577 | DOLORES HUERTA ACTION FUND | 61,818 | 63,722 | -1,904 |  |
| C90023128 | THE CONCERNED CITIZENS OF THE SHORELINE | 0 | 1,838 | -1,838 |  |

**Q2h. Ratio pas2 ÷ reported, deciles, `type I` filers with a reported figure above 0  (0 s)**

| filers | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|
| 199 | 0.00% | 70.21% | 99.99% | 100.00% | 100.00% |

`cm` lacks 8 of the 24/48-hour file's 1,001 spenders. Seven filed web-form lines,
$33,921,014,570 in all, and none is in `pas2`. The eighth, Casey Family Farms, filed a $64,107 Form 5
line. **No `absent` spender is in `pas2`, and only one is real.** The non-committee spenders that
matter are `type I`: 159 in the 24/48-hour file, 153 in `pas2` with $84,903,413 (Q2d). So `pas2`
is the record of Form 5 filers as it is of committees. Its rows for a filer match the filer's
`reported_total.independent_expenditures` within 1% for 142 of 199 filers, and the median filer is
at 99.99%. The 57 that fall short are $2,494,431 below in all. For most of them the 24/48-hour file
holds what `pas2` lacks: Earthjustice Action's $293,577, FLIC Votes' $209,322 (Q2g).

Web-form ids are not hoaxes by themselves. 85 committees and two Form 5 filers used FEC's web form
for real lines (Q2c). Q6's screen tells them apart by the spender's own reported figure.

## Q3: amendments in the 24/48-hour file (2024)

```python
# Q3: amendments in the 24/48-hour file (2024).
h24(2024)

show("Q3a. amndt_ind against prev_file_num", """
SELECT amndt_ind, pfnum IS NOT NULL AS has_prev_file_num, count(DISTINCT fnum) AS filings,
    count(*) AS rows, sum(amt) AS dollars
FROM h_2024 GROUP BY ALL ORDER BY ALL""")

con.execute("""
CREATE TABLE filing AS
SELECT fnum, any_value(spe) AS spe, count(DISTINCT spe) AS spenders, any_value(pfnum) AS pfnum,
    count(DISTINCT pfnum) AS pfnums, any_value(amndt_ind) AS amndt_ind, count(*) AS rows, sum(amt) AS dollars,
    list(DISTINCT tran) AS trans, any_value(superseded) AS superseded, min(rdt) AS received
FROM h_2024 GROUP BY 1""")

show("Q3b. Filings: superseded (named by another's prev_file_num) and how", """
SELECT superseded, amndt_ind LIKE 'A%' AS is_amendment, count(*) AS filings, sum(rows) AS rows, sum(dollars) AS dollars,
    count(*) FILTER (WHERE spenders > 1) AS multi_spender, count(*) FILTER (WHERE pfnums > 1) AS multi_prev
FROM filing GROUP BY ALL ORDER BY ALL""")

show("Q3c. prev_file_num targets: in the file or not, the amendment's spender against the original's", """
SELECT o.fnum IS NOT NULL AS original_in_file, o.spe IS NOT DISTINCT FROM a.spe AS same_spender,
    count(*) AS amendments, sum(a.dollars) AS amendment_dollars
FROM filing AS a LEFT JOIN filing AS o ON o.fnum = a.pfnum
WHERE a.pfnum IS NOT NULL GROUP BY ALL ORDER BY ALL""")

show("Q3d. Filings named by more than one amendment (siblings, which the chain rule keeps both of)", """
WITH named AS (SELECT pfnum, count(*) AS amendments FROM filing WHERE pfnum IS NOT NULL GROUP BY 1)
SELECT amendments AS named_by, count(*) AS originals,
    sum((SELECT sum(dollars) FROM filing AS f WHERE f.pfnum = named.pfnum AND NOT f.superseded)) AS unsuperseded_sibling_dollars
FROM named GROUP BY 1 ORDER BY 1""")

show("Q3e. Chain depth (amendments above an original still in the file)", """
WITH RECURSIVE chain(fnum, root, depth) AS (
    SELECT fnum, fnum, 0 FROM filing WHERE pfnum IS NULL OR pfnum NOT IN (SELECT fnum FROM filing)
    UNION ALL
    SELECT f.fnum, c.root, c.depth + 1 FROM filing AS f JOIN chain AS c ON f.pfnum = c.fnum
)
SELECT depth, count(*) AS filings, count(DISTINCT root) AS chains,
    sum((SELECT dollars FROM filing AS f WHERE f.fnum = chain.fnum)) AS dollars
FROM chain GROUP BY 1 ORDER BY 1""")

show("Q3f. (spe_id, tran_id) on more than one filing: do amount, candidate and date agree?", """
WITH k AS (SELECT spe, tran, count(DISTINCT fnum) AS filings, count(*) AS rows, sum(amt) AS dollars,
               count(DISTINCT amt) = 1 AS amt_same, count(DISTINCT coalesce(cand, '')) = 1 AS cand_same,
               count(DISTINCT coalesce(edt, ddt)) <= 1 AS date_same,
               max(amt) FILTER (WHERE latest_tran) AS latest_amt
           FROM h_2024 GROUP BY 1, 2 HAVING count(DISTINCT fnum) > 1)
SELECT amt_same, cand_same, date_same, count(*) AS transactions, sum(rows) AS rows, sum(dollars) AS dollars_all_rows,
    sum(latest_amt) AS dollars_latest_row
FROM k GROUP BY ALL ORDER BY transactions DESC""")

show("Q3g. Each amendment's share of its original's transaction ids it carries", """
WITH s AS (
    SELECT a.fnum, a.dollars, o.dollars AS original_dollars,
        len(list_intersect(a.trans, o.trans))::DOUBLE / len(o.trans) AS carried
    FROM filing AS a JOIN filing AS o ON o.fnum = a.pfnum)
SELECT CASE WHEN carried = 1 THEN 'all' WHEN carried >= 0.5 THEN 'half or more' WHEN carried > 0 THEN 'under half'
            ELSE 'none' END AS carried, count(*) AS amendments, sum(dollars) AS amendment_dollars,
    sum(original_dollars) AS original_dollars
FROM s GROUP BY ALL ORDER BY amendments DESC""")

show("Q3h. The partial-amendment bar: dollars on amendments carrying under half of their original's ids", """
WITH s AS (
    SELECT a.dollars, o.dollars AS original_dollars,
        len(list_intersect(a.trans, o.trans))::DOUBLE / len(o.trans) AS carried
    FROM filing AS a JOIN filing AS o ON o.fnum = a.pfnum)
SELECT sum(dollars) FILTER (WHERE carried < 0.5) AS under_half_dollars,
    sum(original_dollars) AS dollars_on_amended_filings, sum(dollars) AS dollars_on_amendments,
    (sum(dollars) FILTER (WHERE carried < 0.5) / sum(original_dollars))::DOUBLE AS share_of_amended,
    (sum(dollars) FILTER (WHERE carried < 0.5) / sum(dollars))::DOUBLE AS share_of_amendments
FROM s""")

show("Q3i. Rows and dollars each rule keeps and drops", """
SELECT 'filing chain' AS rule, count(*) FILTER (WHERE NOT superseded) AS rows_kept,
    sum(amt) FILTER (WHERE NOT superseded) AS dollars_kept,
    count(*) FILTER (WHERE superseded) AS rows_dropped, sum(amt) FILTER (WHERE superseded) AS dollars_dropped
FROM h_2024
UNION ALL
SELECT 'per transaction', count(*) FILTER (WHERE latest_tran), sum(amt) FILTER (WHERE latest_tran),
    count(*) FILTER (WHERE NOT latest_tran), sum(amt) FILTER (WHERE NOT latest_tran)
FROM h_2024
UNION ALL
SELECT 'chain, less WFT web-form rows', count(*) FILTER (WHERE NOT superseded AND tran NOT LIKE 'WFT%'),
    sum(amt) FILTER (WHERE NOT superseded AND tran NOT LIKE 'WFT%'), NULL, NULL
FROM h_2024""")

show("Q3j. Where the two rules disagree", """
SELECT CASE WHEN superseded AND latest_tran THEN 'chain drops, per-transaction keeps'
            ELSE 'chain keeps, per-transaction drops' END AS disagreement,
    count(*) AS rows, sum(amt) AS dollars, count(DISTINCT fnum) AS filings, count(DISTINCT spe) AS spenders
FROM h_2024 WHERE superseded = latest_tran GROUP BY 1 ORDER BY 1""")

show("Q3k. 20 rows the chain drops and the per-transaction rule keeps (an amendment left them out), largest first", """
SELECT spe, trim(spe_nam) AS spender, grp, fnum, amndt_ind, tran, cand, sup_opp, amt, exp_date, dissem_dt,
    (SELECT string_agg(f.fnum::VARCHAR, ',') FROM filing AS f WHERE f.pfnum = h.fnum) AS superseded_by
FROM h_2024 AS h WHERE superseded AND latest_tran ORDER BY amt DESC LIMIT 20""")

show("Q3l. 20 rows the chain keeps and the per-transaction rule drops, largest first", """
SELECT spe, trim(spe_nam) AS spender, grp, fnum, pfnum, amndt_ind, tran, cand, sup_opp, amt, exp_date,
    (SELECT max(fnum) FROM h_2024 AS x WHERE x.spe = h.spe AND x.tran = h.tran) AS latest_file_num
FROM h_2024 AS h WHERE NOT superseded AND NOT latest_tran ORDER BY amt DESC LIMIT 20""")

show("Q3m. The kept rows' key (spe_id, tran_id) under the chain: repeats left", """
SELECT count(*) AS keys, sum(n) AS rows, sum(d) AS dollars
FROM (SELECT spe, tran, count(*) AS n, sum(amt) AS d FROM h_2024 WHERE NOT superseded GROUP BY 1, 2 HAVING count(*) > 1)""")

# A third rule, from what Q3j shows: a row on a superseded filing is dropped only when a later
# filing of its chain carries its tran_id ("chain, per transaction"). Tested against pas2.
adopt_h24_rule(2024, "chain")  # counted_pas2 aliases its candidates too
counted_pas2(2024)
con.execute("""
CREATE TABLE chainf AS
WITH RECURSIVE chain(fnum, root, depth) AS (
    SELECT fnum, fnum, 0 FROM filing WHERE pfnum IS NULL OR pfnum NOT IN (SELECT fnum FROM filing)
    UNION ALL
    SELECT f.fnum, c.root, c.depth + 1 FROM filing AS f JOIN chain AS c ON f.pfnum = c.fnum)
SELECT * FROM chain""")
con.execute("""
CREATE TABLE hx AS
SELECT h.*, c.root, c.depth,
    h.superseded AND EXISTS (SELECT 1 FROM h_2024 AS y JOIN chainf AS cy ON cy.fnum = y.fnum
        WHERE cy.root = c.root AND cy.depth > c.depth AND y.spe = h.spe AND y.tran = h.tran) AS restated
FROM h_2024 AS h JOIN chainf AS c USING (fnum)""")
show("Q3n. Rows on superseded filings: restated by a later filing of their chain, or not; and found in pas2", """
SELECT superseded, restated, count(*) AS rows, sum(amt) AS dollars,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS p WHERE p.spe = hx.spe AND p.tran = hx.tran)) AS rows_in_pas2_by_tran,
    sum(amt) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS p WHERE p.spe = hx.spe AND p.tran = hx.tran)) AS dollars_in_pas2_by_tran,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS p WHERE p.spe = hx.spe AND p.amt = trunc(hx.amt)
        AND p.raw_cand IS NOT DISTINCT FROM hx.cand)) AS rows_in_pas2_by_amount
FROM hx WHERE superseded GROUP BY ALL ORDER BY ALL""")
show("Q3o. Superseded and not restated, by how much of the original its amendment carries", """
WITH s AS (SELECT a.pfnum AS fnum, len(list_intersect(a.trans, o.trans))::DOUBLE / len(o.trans) AS carried
           FROM filing AS a JOIN filing AS o ON o.fnum = a.pfnum)
SELECT CASE WHEN carried = 1 THEN 'all' WHEN carried >= 0.5 THEN 'half or more' WHEN carried > 0 THEN 'under half'
            ELSE 'none' END AS amendment_carries, count(*) AS rows, sum(amt) AS dollars,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS p WHERE p.spe = hx.spe AND p.tran = hx.tran)) AS rows_in_pas2_by_tran,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS p WHERE p.spe = hx.spe AND p.amt = trunc(hx.amt)
        AND p.raw_cand IS NOT DISTINCT FROM hx.cand)) AS rows_in_pas2_by_amount
FROM hx JOIN s USING (fnum) WHERE superseded AND NOT restated GROUP BY ALL ORDER BY rows DESC""")
show("Q3p. 20 superseded rows no later filing of their chain restates, largest first, with their amendment", """
SELECT hx.spe, trim(hx.spe_nam) AS spender, hx.fnum, hx.tran, hx.cand, hx.amt, hx.exp_date, hx.dissem_dt,
    (SELECT string_agg(f.fnum || ' (' || f.rows || ' rows, $' || f.dollars || ')', '; ') FROM filing AS f WHERE f.pfnum = hx.fnum) AS amended_by,
    EXISTS (SELECT 1 FROM p_2024 AS p WHERE p.spe = hx.spe AND p.tran = hx.tran) AS in_pas2_by_tran
FROM hx WHERE superseded AND NOT restated ORDER BY amt DESC LIMIT 20""")
show("Q3q. Rows and dollars the three rules keep", """
SELECT count(*) FILTER (WHERE NOT superseded) AS chain_rows, sum(amt) FILTER (WHERE NOT superseded) AS chain_dollars,
    count(*) FILTER (WHERE NOT restated) AS chain_per_tran_rows, sum(amt) FILTER (WHERE NOT restated) AS chain_per_tran_dollars,
    count(*) FILTER (WHERE latest_tran) AS per_tran_rows, sum(amt) FILTER (WHERE latest_tran) AS per_tran_dollars,
    sum(amt) FILTER (WHERE NOT restated AND tran NOT LIKE 'WFT%') AS chain_per_tran_less_wft_dollars
FROM hx""")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:07:00+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
```

**Q3a. amndt_ind against prev_file_num  (0 s)**

| amndt_ind | has_prev_file_num | filings | rows | dollars |
|---|---|---|---|---|
| A1 | False | 2 | 9 | 19,831 |
| A1 | True | 946 | 10,034 | 298,687,463 |
| A2 | True | 227 | 2,756 | 14,048,046 |
| A3 | True | 11 | 65 | 2,755,239 |
| A4 | True | 2 | 12 | 441,467 |
| N | False | 10,649 | 60,573 | 49,363,452,382 |

**Q3b. Filings: superseded (named by another's prev_file_num) and how  (0 s)**

| superseded | is_amendment | filings | rows | dollars | multi_spender | multi_prev |
|---|---|---|---|---|---|---|
| False | False | 9,720 | 51,320 | 48,038,530,115 | 0 | 0 |
| False | True | 949 | 10,106 | 300,568,981 | 0 | 0 |
| True | False | 929 | 9,253 | 1,324,922,267 | 0 | 0 |
| True | True | 239 | 2,770 | 15,383,065 | 0 | 0 |

**Q3c. prev_file_num targets: in the file or not, the amendment's spender against the original's  (0 s)**

| original_in_file | same_spender | amendments | amendment_dollars |
|---|---|---|---|
| False | False | 17 | 2,539,495 |
| True | True | 1,169 | 313,392,719 |

**Q3d. Filings named by more than one amendment (siblings, which the chain rule keeps both of)  (0 s)**

| named_by | originals | unsuperseded_sibling_dollars |
|---|---|---|
| 1 | 1,184 | 300,542,666 |
| 2 | 1 | 26,315 |

**Q3e. Chain depth (amendments above an original still in the file)  (0 s)**

| depth | filings | chains | dollars |
|---|---|---|---|
| 0 | 10,668 | 10,668 | 49,366,011,708 |
| 1 | 936 | 935 | 298,138,779 |
| 2 | 221 | 221 | 12,500,080 |
| 3 | 10 | 10 | 2,312,393 |
| 4 | 2 | 2 | 441,467 |

**Q3f. (spe_id, tran_id) on more than one filing: do amount, candidate and date agree?  (0 s)**

| amt_same | cand_same | date_same | transactions | rows | dollars_all_rows | dollars_latest_row |
|---|---|---|---|---|---|---|
| True | True | True | 7,994 | 18,061 | 421,491,771 | 207,714,109 |
| False | True | True | 386 | 846 | 1,109,574,694 | 39,358,348 |
| False | True | False | 240 | 1,298 | 59,642,467 | 10,497,550 |
| False | False | False | 230 | 2,385 | 417,827,987 | 14,438,163 |
| True | True | False | 120 | 255 | 12,467,797 | 5,876,431 |
| True | False | True | 36 | 75 | 14,382,588 | 7,182,885 |
| True | False | False | 6 | 13 | 30,890 | 12,680 |
| False | False | True | 4 | 8 | 227,374 | 38,974 |

**Q3g. Each amendment's share of its original's transaction ids it carries  (0 s)**

| carried | amendments | amendment_dollars | original_dollars |
|---|---|---|---|
| all | 1,007 | 220,756,391 | 1,238,782,327 |
| none | 78 | 19,218,640 | 19,510,205 |
| half or more | 70 | 70,732,149 | 75,909,779 |
| under half | 14 | 2,685,540 | 6,129,335 |

**Q3h. The partial-amendment bar: dollars on amendments carrying under half of their original's ids  (0 s)**

| under_half_dollars | dollars_on_amended_filings | dollars_on_amendments | share_of_amended | share_of_amendments |
|---|---|---|---|---|
| 21,904,180 | 1,340,331,646 | 313,392,719 | 1.63% | 6.99% |

**Q3i. Rows and dollars each rule keeps and drops  (0 s)**

| rule | rows_kept | dollars_kept | rows_dropped | dollars_dropped |
|---|---|---|---|---|
| filing chain | 61,426 | 48,339,099,096 | 12,023 | 1,340,305,331 |
| per transaction | 59,524 | 47,928,877,999 | 13,925 | 1,750,526,429 |
| chain, less WFT web-form rows | 60,225 | 4,401,751,869 |  |  |

**Q3j. Where the two rules disagree  (0 s)**

| disagreement | rows | dollars | filings | spenders |
|---|---|---|---|---|
| chain drops, per-transaction keeps | 1,106 | 29,297,896 | 155 | 81 |
| chain keeps, per-transaction drops | 3,008 | 439,518,994 | 937 | 103 |

**Q3k. 20 rows the chain drops and the per-transaction rule keeps (an amendment left them out), largest first  (0 s)**

| spe | spender | grp | fnum | amndt_ind | tran | cand | sup_opp | amt | exp_date | dissem_dt | superseded_by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C00492140 | AB PAC | committee | 1,791,815 | N | 501175161 | P80001571 | O | 1,126,284 | 21-MAY-24 | 18-JUN-24 | 1837626 |
| C00492140 | AB PAC | committee | 1,791,815 | N | 501175160 | P80001571 | O | 1,113,166 | 21-MAY-24 | 18-JUN-24 | 1837626 |
| C00492140 | AB PAC | committee | 1,791,815 | N | 501175163 | P80001571 | O | 870,680 | 21-MAY-24 | 18-JUN-24 | 1837626 |
| C00492140 | AB PAC | committee | 1,791,815 | N | 501175162 | P80001571 | O | 833,912 | 21-MAY-24 | 18-JUN-24 | 1837626 |
| C00495028 | HMP | committee | 1,831,031 | N | 500541638 | H2NY04277 | O | 748,736 |  | 15-OCT-24 | 1843366 |
| C00492140 | AB PAC | committee | 1,785,902 | N | 501169142 | P80001571 | O | 724,928 | 14-MAY-24 | 21-MAY-24 | 1812296 |
| C00492140 | AB PAC | committee | 1,791,815 | N | 501175165 | P80001571 | O | 680,870 | 21-MAY-24 | 18-JUN-24 | 1837626 |
| C00492140 | AB PAC | committee | 1,791,815 | N | 501175164 | P80001571 | O | 673,529 | 21-MAY-24 | 18-JUN-24 | 1837626 |
| C00832691 | STANDING STRONG PAC | committee | 1,755,206 | N | WFT20241111516-1 | S4CA00803 | O | 666,928 |  | 09-FEB-24 | 1756067 |
| C00492140 | AB PAC | committee | 1,788,851 | N | 501173123 | P80001571 | O | 650,000 |  | 11-JUN-24 | 1837586 |
| C00492140 | AB PAC | committee | 1,791,815 | N | 501174986 | P80001571 | O | 600,964 | 14-JUN-24 | 18-JUN-24 | 1837626 |
| C00869321 | VICTORY PAC | committee | 1,765,756 | N | SE.4113 | H4AZ03117 | S | 566,469 |  | 18-MAR-24 | 1774881 |
| C00492140 | AB PAC | committee | 1,785,902 | N | 501169144 | P80001571 | O | 557,572 | 14-MAY-24 | 21-MAY-24 | 1812296 |
| C00492140 | AB PAC | committee | 1,788,851 | N | 501173121 | P80001571 | O | 550,000 |  | 11-JUN-24 | 1837586 |
| C00486845 | LCV Victory Fund | committee | 1,823,258 | N | 500459305 | S4MI00470 | S | 467,500 |  | 09-OCT-24 | 1861924 |
| C00486845 | LCV Victory Fund | committee | 1,823,258 | N | 500459314 | P00009423 | S | 467,500 |  | 09-OCT-24 | 1861924 |
| C00753277 | Black Voters Matter Action PAC | committee | 1,843,192 | N | E1213D1199C914456899 | P00009423 | S | 460,000 |  | 25-OCT-24 | 1890200 |
| C00492140 | AB PAC | committee | 1,785,902 | N | 501169143 | P80001571 | O | 451,002 | 14-MAY-24 | 21-MAY-24 | 1812296 |
| C00492140 | AB PAC | committee | 1,791,815 | N | 501174987 | P80001571 | O | 437,558 | 14-JUN-24 | 18-JUN-24 | 1837626 |
| C00486845 | LCV Victory Fund | committee | 1,823,258 | N | 500459300 | H4CA27111 | S | 400,000 |  | 09-OCT-24 | 1861924 |

**Q3l. 20 rows the chain keeps and the per-transaction rule drops, largest first  (0 s)**

| spe | spender | grp | fnum | pfnum | amndt_ind | tran | cand | sup_opp | amt | exp_date | latest_file_num |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C00571703 | Senate Leadership Fund | committee | 1,821,585 |  | N | SE.1 | S6OH00163 | O | 6,668,132 | 03-OCT-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,844,328 |  | N | SE.1 | S4MI00470 | O | 6,483,736 | 23-OCT-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,819,518 |  | N | SE.1 | S6OH00163 | O | 6,406,833 | 25-SEP-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,818,476 |  | N | SE.1 | S6OH00163 | O | 5,583,890 | 18-SEP-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,835,385 |  | N | SE.1 | S6OH00163 | O | 5,302,424 | 18-OCT-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,827,684 |  | N | SE.2 | S6OH00163 | O | 5,053,931 | 09-OCT-24 | 1,844,750 |
| C00487363 | American Crossroads | committee | 1,821,441 |  | N | SE.1 | S6OH00163 | O | 4,887,741 | 03-OCT-24 | 1,846,209 |
| C00571703 | Senate Leadership Fund | committee | 1,813,789 |  | N | SE.1 | S6OH00163 | O | 4,869,452 | 28-AUG-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,835,373 |  | N | SE.1 | S4MI00470 | O | 4,773,701 | 17-OCT-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,816,073 |  | N | SE.1 | S6OH00163 | O | 4,614,032 | 11-SEP-24 | 1,845,585 |
| C00487363 | American Crossroads | committee | 1,819,413 |  | N | SE.1 | S6OH00163 | O | 4,406,545 | 26-SEP-24 | 1,846,209 |
| C00571703 | Senate Leadership Fund | committee | 1,814,760 |  | N | SE.1 | S6OH00163 | O | 4,316,118 | 04-SEP-24 | 1,845,585 |
| C00487363 | American Crossroads | committee | 1,827,502 |  | N | SE.1 | S6OH00163 | O | 4,196,053 | 10-OCT-24 | 1,846,209 |
| C00571703 | Senate Leadership Fund | committee | 1,818,479 |  | N | SE.1 | S6PA00217 | O | 4,063,130 | 18-SEP-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,844,391 |  | N | SE.1 | S2WI00219 | O | 4,019,891 | 24-OCT-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,844,750 |  | N | SE.1 | S6PA00217 | O | 3,973,838 | 24-OCT-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,816,074 |  | N | SE.1 | S6PA00217 | O | 3,934,603 | 11-SEP-24 | 1,845,585 |
| C00571703 | Senate Leadership Fund | committee | 1,837,565 |  | N | SE.1 | S6PA00217 | O | 3,895,471 | 18-OCT-24 | 1,845,585 |
| C00487363 | American Crossroads | committee | 1,816,070 |  | N | SE.1 | S6OH00163 | O | 3,894,827 | 11-SEP-24 | 1,846,209 |
| C00571703 | Senate Leadership Fund | committee | 1,813,790 |  | N | SE.1 | S6PA00217 | O | 3,889,503 | 28-AUG-24 | 1,845,585 |

**Q3m. The kept rows' key (spe_id, tran_id) under the chain: repeats left  (0 s)**

| keys | rows | dollars |
|---|---|---|
| 545 | 3,545 | 464,528,465 |

**Q3n. Rows on superseded filings: restated by a later filing of their chain, or not; and found in pas2  (0 s)**

| superseded | restated | rows | dollars | rows_in_pas2_by_tran | dollars_in_pas2_by_tran | rows_in_pas2_by_amount |
|---|---|---|---|---|---|---|
| True | False | 1,140 | 29,711,780 | 118 | 5,690,116 | 706 |
| True | True | 10,883 | 1,310,593,552 | 7,358 | 1,233,794,506 | 8,421 |

**Q3o. Superseded and not restated, by how much of the original its amendment carries  (0 s)**

| amendment_carries | rows | dollars | rows_in_pas2_by_tran | rows_in_pas2_by_amount |
|---|---|---|---|---|
| none | 434 | 19,180,958 | 1 | 107 |
| under half | 404 | 4,077,659 | 81 | 346 |
| half or more | 302 | 6,453,162 | 36 | 253 |

**Q3p. 20 superseded rows no later filing of their chain restates, largest first, with their amendment  (0 s)**

| spe | spender | fnum | tran | cand | amt | exp_date | dissem_dt | amended_by | in_pas2_by_tran |
|---|---|---|---|---|---|---|---|---|---|
| C00492140 | AB PAC | 1,791,815 | 501175161 | P80001571 | 1,126,284 | 21-MAY-24 | 18-JUN-24 | 1837626 (18 rows, $7179006.42) | False |
| C00492140 | AB PAC | 1,791,815 | 501175160 | P80001571 | 1,113,166 | 21-MAY-24 | 18-JUN-24 | 1837626 (18 rows, $7179006.42) | False |
| C00492140 | AB PAC | 1,791,815 | 501175163 | P80001571 | 870,680 | 21-MAY-24 | 18-JUN-24 | 1837626 (18 rows, $7179006.42) | False |
| C00492140 | AB PAC | 1,791,815 | 501175162 | P80001571 | 833,912 | 21-MAY-24 | 18-JUN-24 | 1837626 (18 rows, $7179006.42) | False |
| C00495028 | HMP | 1,831,031 | 500541638 | H2NY04277 | 748,736 |  | 15-OCT-24 | 1843366 (166 rows, $34128536.35) | False |
| C00492140 | AB PAC | 1,785,902 | 501169142 | P80001571 | 724,928 | 14-MAY-24 | 21-MAY-24 | 1812296 (3 rows, $1733502.00) | False |
| C00492140 | AB PAC | 1,791,815 | 501175165 | P80001571 | 680,870 | 21-MAY-24 | 18-JUN-24 | 1837626 (18 rows, $7179006.42) | False |
| C00492140 | AB PAC | 1,791,815 | 501175164 | P80001571 | 673,529 | 21-MAY-24 | 18-JUN-24 | 1837626 (18 rows, $7179006.42) | False |
| C00832691 | STANDING STRONG PAC | 1,755,206 | WFT20241111516-1 | S4CA00803 | 666,928 |  | 09-FEB-24 | 1756067 (3 rows, $721928.00) | False |
| C00492140 | AB PAC | 1,788,851 | 501173123 | P80001571 | 650,000 |  | 11-JUN-24 | 1837586 (9 rows, $1945742.93) | False |
| C00492140 | AB PAC | 1,791,815 | 501174986 | P80001571 | 600,964 | 14-JUN-24 | 18-JUN-24 | 1837626 (18 rows, $7179006.42) | False |
| C00869321 | VICTORY PAC | 1,765,756 | SE.4113 | H4AZ03117 | 566,469 |  | 18-MAR-24 | 1774881 (3 rows, $509629.85) | False |
| C00492140 | AB PAC | 1,785,902 | 501169144 | P80001571 | 557,572 | 14-MAY-24 | 21-MAY-24 | 1812296 (3 rows, $1733502.00) | False |
| C00492140 | AB PAC | 1,788,851 | 501173121 | P80001571 | 550,000 |  | 11-JUN-24 | 1837586 (9 rows, $1945742.93) | False |
| C00486845 | LCV Victory Fund | 1,823,258 | 500459314 | P00009423 | 467,500 |  | 09-OCT-24 | 1861924 (5 rows, $179957.59) | True |
| C00486845 | LCV Victory Fund | 1,823,258 | 500459305 | S4MI00470 | 467,500 |  | 09-OCT-24 | 1861924 (5 rows, $179957.59) | True |
| C00753277 | Black Voters Matter Action PAC | 1,843,192 | E1213D1199C914456899 | P00009423 | 460,000 |  | 25-OCT-24 | 1890200 (3 rows, $539939.28) | False |
| C00492140 | AB PAC | 1,785,902 | 501169143 | P80001571 | 451,002 | 14-MAY-24 | 21-MAY-24 | 1812296 (3 rows, $1733502.00) | False |
| C00492140 | AB PAC | 1,791,815 | 501174987 | P80001571 | 437,558 | 14-JUN-24 | 18-JUN-24 | 1837626 (18 rows, $7179006.42) | False |
| C00486845 | LCV Victory Fund | 1,823,258 | 500459300 | H4CA27111 | 400,000 |  | 09-OCT-24 | 1861924 (5 rows, $179957.59) | True |

**Q3q. Rows and dollars the three rules keep  (0 s)**

| chain_rows | chain_dollars | chain_per_tran_rows | chain_per_tran_dollars | per_tran_rows | per_tran_dollars | chain_per_tran_less_wft_dollars |
|---|---|---|---|---|---|---|
| 61,426 | 48,339,099,096 | 62,566 | 48,368,810,876 | 59,524 | 47,928,877,999 | 4,430,384,607 |

**`prev_file_num` names the filing an amendment replaces** (§3's assertion, confirmed): 1,169 of
1,186 amendments name a filing of the same spender in the file, and 17 ($2,539,495) name one the
file lacks. Two `A1` filings (9 rows, $19,831) name none. Chains run up to four amendments deep, and
one original is named by two amendments ($26,315 kept twice by the chain).

**An amendment does not always restate its whole report** (corrected). 1,007 of 1,169 carry every
transaction id of their original. 92 carry none or under half, holding $21,904,180: 1.63% of the
$1,340,331,646 on amended filings, over §1.1's 1% bar (Q3h).

**The bar's fallback rule is broken in this file.** The per-transaction rule keeps the row on the
highest `file_num` per spender and `tran_id`. That assumes a `tran_id` names one transaction across
a spender's filings, and it does not. Senate Leadership Fund and American Crossroads number the
first line of every new 24-hour report `SE.1` (Q3l), so the rule drops 3,008 rows, $439,518,994, on
original filings that nothing amends (Q3j).

**What the chain alone drops was renumbered, not lost.** Rows on a superseded filing that no later
filing of the chain restates under the same `tran_id` are 1,140, $29,711,780. 118 of them
($5,690,116) are in `pas2` by `tran_id`. 706 are in `pas2` by spender, candidate and amount, with
the cents dropped, under another `tran_id` (Q3n). The amendment restated them under new numbers,
as AB PAC's filing 1791815 is restated by 1837626 (Q3p). A third rule ("chain, per transaction":
drop a superseded row only when a later filing of its chain carries its `tran_id`) would keep the
old row beside the amendment's renumbered one.

**Decision line:** §1.1's partial-amendment bar is crossed (1.63% > 1%), so the spec would adopt
the per-transaction rule. This document does not adopt it: it drops $439.5M of distinct
expenditures, 15 times what it is meant to save. **Recommended: the filing chain**, every row on a
filing another's `prev_file_num` names dropped. It keeps 61,426 rows ($48,339,099,096; $4,401,751,869 with
web-form ids aside) and drops 12,023 ($1,340,305,331). Departing from a pinned §1.1 rule is NEU-2163's to decide, on this evidence.

## Q4: `pas2`'s own independent expenditures (2024)

```python
# Q4: pas2's own independent expenditures (2024).
h24(2024)
adopt_h24_rule(2024, "chain")
counted_pas2(2024)

show("Q4a. Counted rows by RPT_TP and spender group", """
SELECT rpt_tp, grp, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT fnum) AS filings, count(DISTINCT spe) AS spenders
FROM p_2024 GROUP BY ALL ORDER BY dollars DESC""")
show("Q4b. Counted rows by AMNDT_IND and spender group", """
SELECT amndt_ind, grp, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT fnum) AS filings
FROM p_2024 GROUP BY ALL ORDER BY ALL""")
show("Q4c. (CMTE_ID, TRAN_ID) on more than one FILE_NUM among counted rows, by the RPT_TPs involved", """
WITH k AS (SELECT spe, tran, count(DISTINCT fnum) AS filings, count(*) AS rows, sum(amt) AS dollars,
               string_agg(DISTINCT rpt_tp, ',' ORDER BY rpt_tp) AS rpt_tps,
               count(DISTINCT amt) = 1 AS same_amount, count(DISTINCT coalesce(raw_cand, '')) = 1 AS same_candidate,
               count(DISTINCT dt) <= 1 AS same_date
           FROM p_2024 WHERE tran IS NOT NULL GROUP BY 1, 2 HAVING count(DISTINCT fnum) > 1)
SELECT rpt_tps, same_amount AND same_candidate AND same_date AS all_alike, count(*) AS transactions, sum(rows) AS rows,
    sum(dollars) AS dollars
FROM k GROUP BY ALL ORDER BY dollars DESC""")
show("Q4d. The same, spender by spender: the 20 with most dollars where amount, candidate and date all agree", """
WITH k AS (SELECT spe, tran, count(DISTINCT fnum) AS filings, count(*) AS rows, sum(amt) AS dollars,
               max(amt) AS one, string_agg(DISTINCT rpt_tp, ',' ORDER BY rpt_tp) AS rpt_tps,
               count(DISTINCT amt) = 1 AND count(DISTINCT coalesce(raw_cand, '')) = 1 AND count(DISTINCT dt) <= 1 AS alike
           FROM p_2024 WHERE tran IS NOT NULL GROUP BY 1, 2 HAVING count(DISTINCT fnum) > 1)
SELECT spe, (SELECT cmte_nm FROM grp_2024 WHERE id = spe) AS name, rpt_tps, count(*) AS transactions,
    sum(rows) AS rows, sum(dollars) AS dollars, sum(dollars - one) AS dollars_beyond_one_row
FROM k WHERE alike GROUP BY ALL ORDER BY dollars_beyond_one_row DESC LIMIT 20""")
show("Q4e. Counted rows on a 24- or 48-hour report (RPT_TP 24 or 48), and whether the same spender has a periodic row of equal amount, candidate and date", """
SELECT p.rpt_tp, p.grp, count(*) AS rows, sum(p.amt) AS dollars,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS q WHERE q.spe = p.spe AND q.rpt_tp NOT IN ('24', '48')
        AND q.amt = p.amt AND q.raw_cand IS NOT DISTINCT FROM p.raw_cand AND q.dt IS NOT DISTINCT FROM p.dt)) AS rows_also_periodic,
    sum(p.amt) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS q WHERE q.spe = p.spe AND q.rpt_tp NOT IN ('24', '48')
        AND q.amt = p.amt AND q.raw_cand IS NOT DISTINCT FROM p.raw_cand AND q.dt IS NOT DISTINCT FROM p.dt)) AS dollars_also_periodic
FROM p_2024 AS p WHERE p.rpt_tp IN ('24', '48') GROUP BY ALL ORDER BY ALL""")
show("Q4f. Counted rows whose FILE_NUM is a 24/48-hour filing (in the 24/48-hour file's file_num)", """
SELECT grp, (fnum IN (SELECT fnum FROM h_2024)) AS on_a_24_48_hour_filing, count(*) AS rows, sum(amt) AS dollars
FROM p_2024 GROUP BY ALL ORDER BY ALL""")
show("Q4g. Counted rows whose filing a later pas2 filing of the same spender supersedes (pas2 FILE_NUM named by the 24/48-hour file's prev_file_num)", """
SELECT grp, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT fnum) AS filings
FROM p_2024 WHERE fnum IN (SELECT pfnum FROM h_2024 WHERE pfnum IS NOT NULL) GROUP BY ALL""")
show("Q4h. Counted pas2 amounts in whole dollars (Q5's 'within $1' and Q8's cents)", """
SELECT amt = round(amt) AS whole_dollars, count(*) AS rows, sum(amt) AS dollars FROM p_2024 GROUP BY ALL""")
show("Q4i. The 24/48-hour file's amounts in whole dollars", """
SELECT amt = round(amt) AS whole_dollars, count(*) AS rows, sum(amt) AS dollars FROM l_2024 GROUP BY ALL""")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
```

**Q4a. Counted rows by RPT_TP and spender group  (0 s)**

| rpt_tp | grp | rows | dollars | filings | spenders |
|---|---|---|---|---|---|
| 30G | committee | 14,664 | 1,171,017,674 | 538 | 537 |
| 12G | committee | 8,268 | 1,001,356,406 | 408 | 408 |
| Q3 | committee | 6,415 | 550,483,406 | 307 | 305 |
| M10 | committee | 4,537 | 456,093,908 | 138 | 126 |
| M9 | committee | 2,332 | 285,749,039 | 116 | 106 |
| YE | committee | 5,395 | 221,260,731 | 176 | 161 |
| M8 | committee | 2,041 | 127,491,224 | 95 | 88 |
| M6 | committee | 1,415 | 72,734,945 | 78 | 72 |
| Q2 | committee | 1,669 | 72,054,498 | 179 | 179 |
| M3 | committee | 1,415 | 71,862,666 | 79 | 73 |
| M2 | committee | 1,168 | 64,587,901 | 65 | 59 |
| 12P | committee | 1,466 | 54,240,674 | 102 | 91 |
| YE | type I | 9,726 | 51,383,056 | 118 | 117 |
| MY | committee | 2,211 | 44,639,250 | 66 | 66 |
| M7 | committee | 1,392 | 41,071,275 | 89 | 80 |
| Q1 | committee | 1,228 | 39,819,999 | 136 | 136 |
| M5 | committee | 1,204 | 30,484,124 | 66 | 61 |
| Q3 | type I | 4,604 | 25,305,865 | 73 | 71 |
| TER | committee | 262 | 13,040,541 | 44 | 43 |
| M4 | committee | 939 | 11,161,907 | 63 | 57 |
| Q2 | type I | 685 | 4,652,927 | 37 | 34 |
| Q1 | type I | 389 | 3,561,565 | 22 | 21 |
| 12R | committee | 63 | 2,921,426 | 5 | 5 |
| 12S | committee | 56 | 2,910,929 | 6 | 6 |
| M12 | committee | 93 | 1,450,905 | 9 | 9 |
| M11 | committee | 109 | 800,594 | 9 | 9 |
| 30S | committee | 95 | 245,414 | 6 | 6 |

**Q4b. Counted rows by AMNDT_IND and spender group  (0 s)**

| amndt_ind | grp | rows | dollars | filings |
|---|---|---|---|---|
| A | committee | 24,763 | 1,666,316,269 | 881 |
| A | type I | 5,362 | 27,310,549 | 44 |
| N | committee | 33,452 | 2,658,810,868 | 1,858 |
| N | type I | 10,042 | 57,592,864 | 206 |
| T | committee | 222 | 12,352,299 | 41 |

**Q4c. (CMTE_ID, TRAN_ID) on more than one FILE_NUM among counted rows, by the RPT_TPs involved  (0 s)**

| rpt_tps | all_alike | transactions | rows | dollars |
|---|---|---|---|---|
| 12G,30G,Q3 | False | 21 | 63 | 26,864,536 |
| Q2,Q3 | False | 21 | 44 | 21,181,676 |
| M2,YE | False | 16 | 32 | 12,599,440 |
| 30G,Q2,Q3 | False | 6 | 18 | 9,487,859 |
| Q3,YE | False | 178 | 356 | 9,355,581 |
| 12G,12P,30G,Q2,Q3,YE | False | 5 | 30 | 9,055,427 |
| 30G,Q3 | False | 5 | 10 | 8,612,435 |
| 12G,12P,30G,Q1 | False | 3 | 12 | 5,913,658 |
| 12P,12R,Q1,Q2,Q3 | False | 4 | 28 | 4,139,378 |
| 12G,Q3 | False | 18 | 36 | 4,128,721 |
| 12P,Q1,Q2 | False | 8 | 24 | 3,771,615 |
| 12P,30G,Q2,Q3,YE | False | 1 | 5 | 3,318,662 |
| 12G,30G,M10 | False | 68 | 204 | 3,166,055 |
| 12P,12R,Q2,Q3 | False | 11 | 57 | 2,778,638 |
| 12P,12R,Q2 | False | 8 | 25 | 2,501,190 |
| M2,MY,YE | False | 22 | 66 | 1,818,471 |
| 12P,30G,Q3,YE | False | 1 | 4 | 1,690,330 |
| 12G,30G,M10,M7,M8,M9 | False | 16 | 96 | 954,748 |
| 12G,30G | False | 11 | 22 | 935,549 |
| Q2,Q3,YE | False | 7 | 22 | 767,036 |
| 12G,30G,M10,M6,M7,M8,M9,Q1 | False | 3 | 24 | 680,787 |
| 12G,30G,M10,M6,M7,M8,M9 | False | 2 | 14 | 568,762 |
| 12P,30G | False | 1 | 2 | 556,000 |
| 30G,Q1 | False | 1 | 2 | 543,866 |
| MY,YE | False | 13 | 26 | 461,832 |
| 30G,M10,M9 | False | 4 | 12 | 456,851 |
| 30G,M10 | False | 12 | 24 | 404,039 |
| 12G,M6 | False | 4 | 8 | 307,775 |
| 12P,30G,Q1 | False | 1 | 3 | 265,272 |
| 12G,30G,M6,M8,Q1 | False | 2 | 10 | 210,897 |
| MY,Q3 | False | 1 | 2 | 200,000 |
| 12G,30G,M10,M9 | False | 4 | 16 | 197,268 |
| Q1,Q3,YE | False | 28 | 84 | 157,989 |
| 12R,Q2 | False | 8 | 16 | 154,799 |
| 12G,30G,M10,M6,M8,Q1 | False | 1 | 6 | 124,009 |
| Q1,Q2,Q3,YE | False | 2 | 8 | 91,478 |
| 12G,M10 | False | 10 | 20 | 84,404 |
| 12P,Q2 | False | 2 | 4 | 73,604 |
| Q1,Q2 | False | 3 | 6 | 72,641 |
| 12G,30G,M10,M8,M9 | False | 2 | 10 | 71,325 |
| M10,M9 | False | 1 | 2 | 70,285 |
| 30G,M10,M6,M7,M8,M9 | False | 1 | 6 | 55,459 |
| 30G,YE | False | 5 | 10 | 38,379 |
| 12G,YE | False | 2 | 4 | 27,540 |
| 30G,M10,M7,M8,M9 | False | 3 | 15 | 20,502 |
| M3,YE | False | 2 | 4 | 18,645 |
| M10,M7,M8,M9 | False | 2 | 8 | 13,359 |
| 12G,M10,M8,M9 | False | 1 | 4 | 6,424 |
| Q2,YE | False | 2 | 4 | 3,270 |
| M10,M8,M9 | False | 1 | 3 | 2,195 |
| 30G,M10,M8,M9 | False | 1 | 4 | 1,208 |
| M7,M8 | False | 1 | 2 | 350 |
| M10,M5 | False | 1 | 2 | 0 |

**Q4d. The same, spender by spender: the 20 with most dollars where amount, candidate and date all agree  (0 s)**

| spe | name | rpt_tps | transactions | rows | dollars | dollars_beyond_one_row |
|---|---|---|---|---|---|---|

**Q4e. Counted rows on a 24- or 48-hour report (RPT_TP 24 or 48), and whether the same spender has a periodic row of equal amount, candidate and date  (0 s)**

| rpt_tp | grp | rows | dollars | rows_also_periodic | dollars_also_periodic |
|---|---|---|---|---|---|

**Q4f. Counted rows whose FILE_NUM is a 24/48-hour filing (in the 24/48-hour file's file_num)  (0 s)**

| grp | on_a_24_48_hour_filing | rows | dollars |
|---|---|---|---|
| committee | False | 58,437 | 4,337,479,436 |
| type I | False | 15,404 | 84,903,413 |

**Q4g. Counted rows whose filing a later pas2 filing of the same spender supersedes (pas2 FILE_NUM named by the 24/48-hour file's prev_file_num)  (0 s)**

| grp | rows | dollars | filings |
|---|---|---|---|

**Q4h. Counted pas2 amounts in whole dollars (Q5's 'within $1' and Q8's cents)  (0 s)**

| whole_dollars | rows | dollars |
|---|---|---|
| True | 73,841 | 4,422,382,849 |

**Q4i. The 24/48-hour file's amounts in whole dollars  (0 s)**

| whole_dollars | rows | dollars |
|---|---|---|
| False | 38,308 | 2,102,695,766 |
| True | 23,118 | 46,236,403,330 |

**`pas2` holds an independent expenditure once, from the periodic report** (§3's assertion,
confirmed). No counted row is on a 24- or 48-hour report (`RPT_TP` `24` or `48`, Q4a, Q4e), and none
is on a filing in the 24/48-hour file (Q4f). A (`CMTE_ID`, `TRAN_ID`) on more than one filing never
agrees on amount, candidate and date (Q4c–d): the same renumbering as Q3, not one expenditure counted twice. So
v1's totals count nothing twice, and no Bug ticket is filed.

`pas2` writes whole dollars: every counted amount is an integer (Q4h). The 24/48-hour file and the
communication-costs CSV carry cents. That is why rung 1 matches 18,505 keys "within $1" (Q5c) and Q8's
amounts differ.

## Q5: the ladder (2024)

```python
# Q5: the ladder (2024), latest-amendment 24/48-hour rows against counted pas2 rows.
h24(2024)
adopt_h24_rule(2024, "chain")
counted_pas2(2024)
ladder(2024)
con.execute(f"COPY (SELECT * FROM lm) TO {literal(work / 'lm_2024.parquet')} (FORMAT parquet)")
con.execute(f"COPY (SELECT * FROM pmatch) TO {literal(work / 'pmatch_2024.parquet')} (FORMAT parquet)")
con.execute("CREATE VIEW lj AS SELECT l.*, lm.rung FROM l_2024_a AS l JOIN lm USING (rn)")
con.execute("CREATE VIEW pj AS SELECT p.*, m.rung FROM p_2024 AS p JOIN pmatch AS m USING (sid)")

show("Q5a. Per rung and spender group: 24/48-hour rows and dollars", """
SELECT coalesce(rung, 'unmatched') AS rung, grp, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT spe) AS spenders
FROM lj GROUP BY ALL ORDER BY ALL""")
show("Q5b. Per rung and spender group: counted pas2 rows and dollars", """
SELECT coalesce(rung, 'unmatched') AS rung, grp, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT spe) AS spenders
FROM pj GROUP BY ALL ORDER BY ALL""")
show("Q5c. Rung 1 at its grain (spender, tran_id): amounts, candidate, side and date", """
SELECT CASE WHEN l_amt = p_amt THEN 'equal' WHEN abs(l_amt - p_amt) <= 1 THEN 'within $1'
            WHEN p_amt > l_amt THEN 'pas2 higher' ELSE 'pas2 lower' END AS amount,
    l_cand IS NOT DISTINCT FROM p_cand AS same_candidate, l_so IS NOT DISTINCT FROM p_so AS same_side,
    count(*) AS keys, sum(l_amt) AS h24_dollars, sum(p_amt) AS pas2_dollars, sum(p_amt - l_amt) AS net_pas2_minus_h24
FROM m1 GROUP BY ALL ORDER BY keys DESC""")
show("Q5d. Rung 1: pas2 ÷ 24/48-hour where they differ, deciles", """
SELECT count(*) AS keys, round(quantile_cont(p_amt / l_amt, 0.1), 4) AS p10, round(quantile_cont(p_amt / l_amt, 0.25), 4) AS p25,
    round(median(p_amt / l_amt), 4) AS median, round(quantile_cont(p_amt / l_amt, 0.75), 4) AS p75,
    round(quantile_cont(p_amt / l_amt, 0.9), 4) AS p90, sum(p_amt - l_amt) AS net
FROM m1 WHERE l_amt <> p_amt AND l_amt <> 0""")
show("Q5e. Rung 1: dates", """
SELECT CASE WHEN l_edt = p_dt THEN 'exp_date equal' WHEN l_ddt = p_dt THEN 'dissem_dt equal'
            WHEN l_edt IS NULL AND l_ddt IS NULL THEN 'no 24/48-hour date' ELSE 'neither' END AS date,
    count(*) AS keys, sum(p_amt) AS pas2_dollars
FROM m1 GROUP BY ALL ORDER BY keys DESC""")
show("Q5f. Rung 1: candidates that differ after aliases, the 20 largest", """
SELECT spe, tran, l_cand, p_cand, l_amt, p_amt, l_so, p_so FROM m1
WHERE l_cand IS DISTINCT FROM p_cand ORDER BY p_amt DESC LIMIT 20""")
show("Q5g. Rung 1: sup_opp against pas2's side", """
SELECT l_so AS h24_sup_opp, p_so AS pas2_side, count(*) AS keys, sum(p_amt) AS pas2_dollars FROM m1 GROUP BY ALL ORDER BY keys DESC""")

show("Q5h. Only in 24/48-hour: by spender group and web-form transaction id", """
SELECT grp, tran LIKE 'WFT%' AS web_form, spe IN (SELECT spe FROM p_2024) AS spender_in_pas2,
    count(*) AS rows, sum(amt) AS dollars, count(DISTINCT spe) AS spenders
FROM lj WHERE rung IS NULL GROUP BY ALL ORDER BY ALL""")
show("Q5i. Only in 24/48-hour: by month of exp_date (else dissem_dt)", """
SELECT strftime(coalesce(edt, ddt), '%Y-%m') AS month, count(*) AS rows, sum(amt) AS dollars,
    sum(amt) FILTER (WHERE tran NOT LIKE 'WFT%') AS dollars_not_web_form
FROM lj WHERE rung IS NULL GROUP BY ALL ORDER BY ALL""")
show("Q5j. Only in 24/48-hour: the 20 largest spenders", """
SELECT spe, any_value(trim(spe_nam)) AS name, grp, count(*) AS rows, sum(amt) AS dollars,
    bool_or(tran LIKE 'WFT%') AS any_web_form, spe IN (SELECT spe FROM p_2024) AS in_pas2,
    (SELECT sum(amt) FROM p_2024 AS p WHERE p.spe = lj.spe) AS pas2_dollars
FROM lj WHERE rung IS NULL GROUP BY spe, grp ORDER BY dollars DESC LIMIT 20""")
show("Q5k. Only in 24/48-hour: 10 largest rows and 10 by hash order", """
(SELECT 'largest' AS pick, spe, trim(spe_nam) AS name, grp, fnum, tran, cand, sup_opp, amt, exp_date, dissem_dt, left(pur, 40) AS purpose
 FROM lj WHERE rung IS NULL ORDER BY amt DESC LIMIT 10)
UNION ALL
(SELECT 'hash', spe, trim(spe_nam), grp, fnum, tran, cand, sup_opp, amt, exp_date, dissem_dt, left(pur, 40)
 FROM lj WHERE rung IS NULL ORDER BY hash(rn) LIMIT 10)""")

show("Q5l. Only in pas2: by spender group and RPT_TP", """
SELECT grp, rpt_tp, spe IN (SELECT spe FROM l_2024) AS spender_in_24_48_hour, count(*) AS rows, sum(amt) AS dollars
FROM pj WHERE rung IS NULL GROUP BY ALL ORDER BY dollars DESC""")
show("Q5m. Only in pas2: by month", """
SELECT strftime(dt, '%Y-%m') AS month, count(*) AS rows, sum(amt) AS dollars FROM pj WHERE rung IS NULL GROUP BY ALL ORDER BY ALL""")
show("Q5n. Only in pas2: the 20 largest spenders", """
SELECT spe, (SELECT cmte_nm FROM grp_2024 WHERE id = spe) AS name, grp, count(*) AS rows, sum(amt) AS dollars,
    spe IN (SELECT spe FROM l_2024) AS in_24_48_hour
FROM pj WHERE rung IS NULL GROUP BY spe, grp ORDER BY dollars DESC LIMIT 20""")
show("Q5o. Only in pas2: 10 largest rows and 10 by hash order", """
(SELECT 'largest' AS pick, spe, grp, rpt_tp, fnum, tran, raw_cand, sup_opp, amt, dt, left(payee, 30) AS payee
 FROM pj WHERE rung IS NULL ORDER BY amt DESC LIMIT 10)
UNION ALL
(SELECT 'hash', spe, grp, rpt_tp, fnum, tran, raw_cand, sup_opp, amt, dt, left(payee, 30)
 FROM pj WHERE rung IS NULL ORDER BY hash(sid) LIMIT 10)""")

show("Q5p. The decision: unmatched 24/48-hour rows at spenders with a counted pas2 row, against counted IE dollars", """
SELECT sum(amt) FILTER (WHERE rung IS NULL AND spe IN (SELECT spe FROM p_2024)) AS unmatched_at_pas2_spenders,
    count(*) FILTER (WHERE rung IS NULL AND spe IN (SELECT spe FROM p_2024)) AS rows,
    (SELECT sum(amt) FROM p_2024) AS counted_ie_dollars,
    (sum(amt) FILTER (WHERE rung IS NULL AND spe IN (SELECT spe FROM p_2024)) / (SELECT sum(amt) FROM p_2024))::DOUBLE AS share,
    sum(amt) FILTER (WHERE rung IS NULL AND spe IN (SELECT spe FROM p_2024) AND tran NOT LIKE 'WFT%') AS less_web_form,
    (sum(amt) FILTER (WHERE rung IS NULL AND spe IN (SELECT spe FROM p_2024) AND tran NOT LIKE 'WFT%')
        / (SELECT sum(amt) FROM p_2024))::DOUBLE AS share_less_web_form,
    (sum(amt) FILTER (WHERE (rung IS NULL OR rung LIKE '4%') AND spe IN (SELECT spe FROM p_2024))
        / (SELECT sum(amt) FROM p_2024))::DOUBLE AS share_without_rung_4
FROM lj""")
show("Q5q. What each grain would add: by spender (spenders with no counted pas2 row) and by row (every unmatched row)", """
SELECT 'by spender' AS grain, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT spe) AS spenders,
    sum(amt) FILTER (WHERE tran NOT LIKE 'WFT%') AS dollars_less_web_form
FROM lj WHERE spe NOT IN (SELECT spe FROM p_2024)
UNION ALL
SELECT 'by row', count(*), sum(amt), count(DISTINCT spe), sum(amt) FILTER (WHERE tran NOT LIKE 'WFT%')
FROM lj WHERE rung IS NULL""")

show("Q5r. Spenders in both files: each one's latest-amendment 24/48-hour total against its counted pas2 total", """
WITH h AS (SELECT spe, any_value(grp) AS grp, sum(amt) AS h FROM l_2024 WHERE tran NOT LIKE 'WFT%' GROUP BY 1),
     p AS (SELECT spe, sum(amt) AS p FROM p_2024 GROUP BY 1)
SELECT grp, CASE WHEN abs(h - p) <= 0.01 * abs(p) THEN 'within 1%' WHEN abs(h - p) <= 0.05 * abs(p) THEN '1-5%'
                 WHEN h > p THEN '24/48-hour more than 5% above' ELSE '24/48-hour more than 5% below' END AS band,
    count(*) AS spenders, sum(h) AS h24_dollars, sum(p) AS pas2_dollars,
    sum(greatest(h - p, 0)) AS h24_excess_dollars
FROM h JOIN p USING (spe) GROUP BY ALL ORDER BY ALL""")
show("Q5s. Spenders in both: the 20 with the largest 24/48-hour excess over pas2", """
WITH h AS (SELECT spe, any_value(trim(spe_nam)) AS name, any_value(grp) AS grp, sum(amt) AS h,
               max(rdt) AS last_received FROM l_2024 WHERE tran NOT LIKE 'WFT%' GROUP BY 1),
     p AS (SELECT spe, sum(amt) AS p, max(dt) AS last_pas2 FROM p_2024 GROUP BY 1)
SELECT spe, name, grp, h AS h24_dollars, p AS pas2_dollars, h - p AS excess, last_received, last_pas2
FROM h JOIN p USING (spe) WHERE h > p ORDER BY h - p DESC LIMIT 20""")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:07:00+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
```

**Q5a. Per rung and spender group: 24/48-hour rows and dollars  (0 s)**

| rung | grp | rows | dollars | spenders |
|---|---|---|---|---|
| 1 | committee | 34,882 | 2,887,746,315 | 344 |
| 1 | type I | 5,890 | 43,838,445 | 75 |
| 2d | committee | 183 | 34,228,105 | 40 |
| 2e | committee | 6,944 | 958,214,673 | 386 |
| 2e | type I | 2,633 | 22,831,128 | 58 |
| 3 | committee | 361 | 23,964,685 | 81 |
| 3 | type I | 13 | 70,165 | 4 |
| 4d | committee | 41 | 530,083 | 17 |
| 4e | committee | 1,825 | 338,021,479 | 145 |
| 4e | type I | 603 | 13,542,974 | 25 |
| memo | committee | 4,355 | 39,044,429 | 142 |
| unmatched | absent | 9 | 33,921,078,677 | 8 |
| unmatched | committee | 3,248 | 10,050,063,972 | 252 |
| unmatched | type I | 439 | 5,923,966 | 54 |

**Q5b. Per rung and spender group: counted pas2 rows and dollars  (0 s)**

| rung | grp | rows | dollars | spenders |
|---|---|---|---|---|
| 1 | committee | 33,776 | 2,780,613,226 | 344 |
| 1 | type I | 5,390 | 37,888,890 | 75 |
| 2d | committee | 183 | 34,228,055 | 40 |
| 2e | committee | 6,944 | 958,212,911 | 386 |
| 2e | type I | 2,633 | 22,830,270 | 58 |
| 3 | committee | 361 | 23,964,595 | 81 |
| 3 | type I | 13 | 70,160 | 4 |
| 4d | committee | 41 | 530,078 | 17 |
| 4e | committee | 1,825 | 338,020,972 | 145 |
| 4e | type I | 603 | 13,542,876 | 25 |
| unmatched | committee | 15,307 | 201,909,599 | 538 |
| unmatched | type I | 6,765 | 10,571,217 | 92 |

**Q5c. Rung 1 at its grain (spender, tran_id): amounts, candidate, side and date  (0 s)**

| amount | same_candidate | same_side | keys | h24_dollars | pas2_dollars | net_pas2_minus_h24 |
|---|---|---|---|---|---|---|
| within $1 | True | True | 14,706 | 741,943,514 | 741,936,224 | -7,290 |
| equal | True | True | 9,854 | 1,029,510,223 | 1,029,510,223 | 0 |
| pas2 lower | True | True | 4,230 | 302,565,045 | 181,039,187 | -121,525,858 |
| within $1 | False | True | 3,767 | 304,349,326 | 304,347,405 | -1,921 |
| pas2 higher | True | True | 2,709 | 80,688,245 | 112,164,934 | 31,476,689 |
| equal | False | True | 2,657 | 264,350,013 | 264,350,013 | 0 |
| pas2 lower | False | True | 445 | 91,095,954 | 64,847,450 | -26,248,504 |
| pas2 higher | False | True | 163 | 92,601,405 | 108,492,286 | 15,890,881 |
| pas2 lower | False | False | 41 | 22,689,730 | 4,960,523 | -17,729,207 |
| pas2 higher | False | False | 33 | 1,536,160 | 6,598,738 | 5,062,578 |
| within $1 | True | False | 32 | 8,287 | 8,274 | -13 |
| equal | True | False | 17 | 21,235 | 21,235 | 0 |
| equal | False | False | 2 | 225,624 | 225,624 | 0 |

**Q5d. Rung 1: pas2 ÷ 24/48-hour where they differ, deciles  (0 s)**

| keys | p10 | p25 | median | p75 | p90 | net |
|---|---|---|---|---|---|---|
| 26,126 | 67.46% | 99.05% | 99.98% | 100.00% | 105.05% | -113,082,645 |

**Q5e. Rung 1: dates  (0 s)**

| date | keys | pas2_dollars |
|---|---|---|
| exp_date equal | 22,048 | 1,384,779,425 |
| neither | 14,453 | 746,602,831 |
| dissem_dt equal | 2,155 | 687,119,860 |

**Q5f. Rung 1: candidates that differ after aliases, the 20 largest  (0 s)**

| spe | tran | l_cand | p_cand | l_amt | p_amt | l_so | p_so |
|---|---|---|---|---|---|---|---|
| C00669259 | 500193530 | P00009423 | P80000722 | 18,986,237 | 18,226,830 | S | S |
| C00669259 | 500193567 | P00009423 | P80000722 | 14,244,859 | 16,185,334 | S | S |
| C00669259 | 500195264 | P00009423 | P80000722 | 13,387,272 | 13,387,272 | S | S |
| C00669259 | 500195265 | P00009423 | P80000722 | 11,143,662 | 12,209,566 | S | S |
| C00669259 | 500183634 | P00009423 | P80000722 | 9,955,000 | 10,592,977 | S | S |
| C00669259 | 500195236 | P00009423 | P80000722 | 11,629,887 | 10,064,792 | S | S |
| C00669259 | 500193566 | P00009423 | P80000722 | 9,435,250 | 9,435,250 | S | S |
| C00669259 | 500193533 | P00009423 | P80000722 | 9,368,238 | 9,377,243 | S | S |
| C00669259 | 500195238 | P00009423 | P80000722 | 8,670,504 | 8,747,706 | S | S |
| C00669259 | 500193537 | P00009423 | P80000722 | 7,761,704 | 7,795,849 | S | S |
| C00669259 | 500195230 | P00009423 | P80000722 | 2,266,393 | 6,948,233 | S | S |
| C00669259 | 500195231 | P00009423 | P80000722 | 6,027,878 | 6,805,478 | S | S |
| C00834077 | SE24.120 |  | P40013039 | 6,736,839 | 6,736,839 | S | S |
| C00669259 | 500195221 | P00009423 | P80000722 | 10,895,951 | 6,711,863 | S | S |
| C00669259 | 500195232 | P00009423 | P80000722 | 5,901,514 | 5,901,657 | S | S |
| C00879510 | SE24.1101 |  | P00009423 | 4,526,887 | 4,526,887 | O | O |
| C00879510 | SE24.1100 |  | P80001571 | 4,526,887 | 4,526,887 | S | S |
| C00669259 | 500193541 | P00009423 | P80000722 | 3,107,644 | 3,117,364 | S | S |
| C00834077 | SE24.28 |  | P40013039 | 2,947,500 | 2,947,500 | S | S |
| C00669259 | 500193542 | P00009423 | P80000722 | 2,907,015 | 2,859,122 | S | S |

**Q5g. Rung 1: sup_opp against pas2's side  (0 s)**

| h24_sup_opp | pas2_side | keys | pas2_dollars |
|---|---|---|---|
| S | S | 28,819 | 1,409,920,291 |
| O | O | 9,675 | 1,367,751,382 |
|  | S | 48 | 11,509 |
| O,S | O,S | 37 | 29,016,049 |
| O,S | S | 31 | 2,437,027 |
| S | O,S | 17 | 2,566,197 |
| O,S | O | 10 | 3,890,160 |
| S | O | 7 | 646,359 |
| O | S | 6 | 39,768 |
| O | O,S | 6 | 2,223,374 |

**Q5h. Only in 24/48-hour: by spender group and web-form transaction id  (0 s)**

| grp | web_form | spender_in_pas2 | rows | dollars | spenders |
|---|---|---|---|---|---|
| absent | False | False | 1 | 64,107 | 1 |
| absent | True | False | 8 | 33,921,014,570 | 7 |
| committee | False | False | 75 | 2,355,035 | 14 |
| committee | False | True | 2,804 | 60,544,294 | 194 |
| committee | True | False | 65 | 9,980,093,578 | 16 |
| committee | True | True | 304 | 7,071,066 | 31 |
| type I | False | False | 144 | 1,585,332 | 23 |
| type I | False | True | 281 | 3,827,737 | 30 |
| type I | True | False | 4 | 503,222 | 1 |
| type I | True | True | 10 | 7,675 | 1 |

**Q5i. Only in 24/48-hour: by month of exp_date (else dissem_dt)  (0 s)**

| month | rows | dollars | dollars_not_web_form |
|---|---|---|---|
| 2022-05 | 3 | 34,873 |  |
| 2022-06 | 2 | 29,766 |  |
| 2022-07 | 42 | 37,537 | 37,537 |
| 2022-08 | 6 | 5,362 | 5,362 |
| 2022-09 | 7 | 1,225,000 | 1,225,000 |
| 2022-10 | 107 | 908,247 | 908,038 |
| 2022-11 | 67 | 513,860 | 513,797 |
| 2022-12 | 1 | 39,856 | 39,856 |
| 2023-01 | 8 | 1,096,133 | 1,096,133 |
| 2023-02 | 5 | 124,292 | 124,292 |
| 2023-03 | 10 | 1,299 | 1,299 |
| 2023-04 | 4 | 2,632 | 2,632 |
| 2023-05 | 2 | 19,823 | 19,823 |
| 2023-06 | 5 | 255,117,000 | 117,000 |
| 2023-07 | 7 | 1,134,500 | 1,134,500 |
| 2023-08 | 13 | 210,640 | 186,640 |
| 2023-09 | 34 | 2,025,941 | 1,045,049 |
| 2023-10 | 6 | 645,128 | 395,128 |
| 2023-11 | 1 | 17,000 | 17,000 |
| 2023-12 | 15 | 246,934 | 172,991 |
| 2024-01 | 15 | 801,467 | 129,046 |
| 2024-02 | 155 | 1,182,448 | 1,017,499 |
| 2024-03 | 100 | 25,126,864,897 | 361,253 |
| 2024-04 | 15 | 10,558,433,354 | 127,087 |
| 2024-05 | 72 | 1,044,455 | 936,866 |
| 2024-06 | 76 | 1,301,845 | 1,261,334 |
| 2024-07 | 133 | 7,962,664,317 | 2,381,174 |
| 2024-08 | 191 | 1,249,843 | 1,138,970 |
| 2024-09 | 585 | 27,870,523 | 26,965,914 |
| 2024-10 | 1,671 | 30,243,002 | 25,448,449 |
| 2024-11 | 334 | 1,899,614 | 1,541,557 |
| 2024-12 | 4 | 75,025 | 25,279 |

**Q5j. Only in 24/48-hour: the 20 largest spenders  (0 s)**

| spe | name | grp | rows | dollars | any_web_form | in_pas2 | pas2_dollars |
|---|---|---|---|---|---|---|---|
| C00874586 | THE COMMITTEE OF 300 | absent | 2 | 17,738,007,416 | True | False |  |
| C00875427 | THE COURT OF DIVINE JUSTICE | committee | 1 | 9,978,412,568 | True | False |  |
| C00785352 | THE COMMITTEE OF 300 | absent | 1 | 9,000,000,000 | True | False |  |
| C00873521 | Republican Emo Girl | absent | 1 | 6,347,882,325 | True | False |  |
| C00874909 | The Masonic Illuminati Eye | absent | 1 | 579,874,829 | True | False |  |
| C00843094 | Gus Associates | absent | 1 | 255,000,000 | True | False |  |
| C00075820 | NRCC | committee | 183 | 14,093,661 | False | True | 36,483,042 |
| C00886614 | YOUR COMMUNITY PAC | committee | 12 | 7,927,805 | False | True | 19,033,234 |
| C00834630 | BUCKEYE VALUES PAC | committee | 3 | 3,750,000 | False | True | 15,829,044 |
| C00544387 | American Principles Project PAC | committee | 18 | 3,592,800 | False | True | 7,933,278 |
| C00693838 | MORE JOBS, LESS GOVERNMENT | committee | 9 | 2,468,334 | False | True | 19,943,488 |
| C00890335 | STRATEGIC MAJORITY PAC | committee | 5 | 2,190,932 | False | True | 4,556,977 |
| C00747998 | Care in Action PAC | committee | 2 | 2,052,000 | False | True | 4,501,845 |
| C00815928 | READY FOR RON | committee | 3 | 2,035,000 | False | True | 1,680,549 |
| C00620971 | For Our Future | committee | 79 | 1,529,283 | False | True | 11,308,269 |
| C00763409 | ORGANIZING EMPOWERMENT PAC | committee | 23 | 1,442,605 | False | True | 1,422,483 |
| C00556860 | Planned Parenthood Affiliates of California VOTES PAC | committee | 64 | 1,288,894 | False | True | 2,095,290 |
| C00770149 | Shield PAC | committee | 7 | 1,225,000 | False | False |  |
| C00606962 | WORKING FAMILIES PARTY PAC | committee | 28 | 1,200,748 | True | True | 8,050,966 |
| C00761072 | ONE APIA PAC | committee | 30 | 1,158,673 | True | True | 1,158,664 |

**Q5k. Only in 24/48-hour: 10 largest rows and 10 by hash order  (0 s)**

| pick | spe | name | grp | fnum | tran | cand | sup_opp | amt | exp_date | dissem_dt | purpose |
|---|---|---|---|---|---|---|---|---|---|---|---|
| largest | C00875427 | THE COURT OF DIVINE JUSTICE | committee | 1,778,759 | WFT20243201436-1 | P40007304 | S | 9,978,412,568 | 20-APR-24 | 20-APR-24 | Political Contribution |
| largest | C00874586 | THE COMMITTEE OF 300 | absent | 1,766,664 | WFT20242312317-1 | P40019226 | S | 9,778,412,568 |  | 31-MAR-24 | Political Contribution |
| largest | C00785352 | THE COMMITTEE OF 300 | absent | 1,766,323 | WFT2024227513-1 | P40019226 | S | 9,000,000,000 | 25-MAR-24 | 27-MAR-24 | DEPOSIT FOR WINNING IN ELECTION |
| largest | C00874586 | THE COMMITTEE OF 300 | absent | 1,798,067 | WFT20246141728-1 | P40007304 | S | 7,959,594,848 | 14-JUL-24 | 14-JUL-24 | FOR WIN THIS ELECTION |
| largest | C00873521 | Republican Emo Girl | absent | 1,763,978 | WFT20242171533-1 | S4OK00398 | S | 6,347,882,325 | 17-MAR-24 | 17-MAR-24 | Senate campaign. |
| largest | C00874909 | The Masonic Illuminati Eye | absent | 1,767,013 | WFT2024321734-1 | P40007304 | S | 579,874,829 | 05-APR-24 | 02-APR-24 | Political Contribution |
| largest | C00843094 | Gus Associates | absent | 1,707,511 | WFT202351617-1 | H4NM02098 | S | 255,000,000 | 15-JUN-23 | 15-JUN-23 | funding for waltuh white's campaign |
| largest | C00886614 | YOUR COMMUNITY PAC | committee | 1,822,026 | SE.4179 | P00009423 | S | 5,800,000 | 20-SEP-24 | 07-OCT-24 | Billboard Advertising Buy (Estimate) |
| largest | C00544387 | American Principles Project PAC | committee | 1,821,610 | SE.8666 | P80001571 | S | 2,111,900 |  | 06-OCT-24 | Digital advertising placement (estimate) |
| largest | C00834630 | BUCKEYE VALUES PAC | committee | 1,832,586 | SE.1 | P00009423 | O | 2,000,000 | 15-OCT-24 | 18-OCT-24 | SMS MESSAGING |
| hash | C00853523 | Vote Planned Parenthood Northern California, a Project of Planned Parenthood Northern California (CA) Action Fund | committee | 1,841,455 | PDT.E.14 |  | S | 500 | 23-OCT-24 | 23-OCT-24 | Phonebanking (estimate) |
| hash | C00690776 | MICHIGAN LIBERATION ACTION FUND | committee | 1,694,877 | SE.4581 | H8MI08102 | S | 2,532 |  | 29-OCT-22 | Payroll Share |
| hash | C00890053 | FUTURE PENNSYLVANIA PAC | committee | 1,862,265 | WFT20249221321-1 |  | O | 5,816 | 21-OCT-24 | 21-OCT-24 | Field Staff payroll |
| hash | C00868026 | America's First Freedoms, Inc. | committee | 1,754,982 | SE.4165 | H4IN08249 | S | 3,250 |  | 07-FEB-24 | Radio |
| hash | C00821728 | INLAND EMPIRE UNITED FEDERAL ACTION FUND | committee | 1,833,983 | PDT.E.131 |  | S | 3,075 | 19-OCT-24 | 19-OCT-24 | PHONE CALLS & CANVASSING (ESTIMATE) |
| hash | C00738815 | TAKEACTION MN FEDERAL FUND | committee | 1,841,258 | SE.6070 | S2WI00219 | S | 6 |  | 21-OCT-24 | Mileage Reimbursement |
| hash | C90022781 | Earthjustice Action | type I | 1,839,761 | F57.000006 |  | S | 535 | 24-OCT-24 |  | staff time |
| hash | C90016510 | PLANNED PARENTHOOD ADVOCATES OF WISCONSIN POLITICAL FUND | type I | 1,842,315 | F57.4342 |  | S | 5,000 | 26-OCT-24 |  | Phone banking 10/26-11/5 |
| hash | C00738815 | TAKEACTION MN FEDERAL FUND | committee | 1,831,853 | SE.5704 | P00009423 | S | 112 |  | 16-OCT-24 | Wages |
| hash | C00867861 | TAKE BACK YOUR LIBERTY | committee | 1,806,327 | SE.4231 | S4MI00694 | S | 13,073 | 17-JUN-24 | 25-JUL-24 | Postage |

**Q5l. Only in pas2: by spender group and RPT_TP  (0 s)**

| grp | rpt_tp | spender_in_24_48_hour | rows | dollars |
|---|---|---|---|---|
| committee | Q3 | True | 1,307 | 46,967,514 |
| committee | 30G | True | 3,331 | 45,948,725 |
| committee | 12G | True | 1,342 | 30,994,274 |
| committee | YE | True | 1,563 | 27,308,948 |
| committee | Q2 | True | 512 | 14,518,430 |
| type I | YE | True | 1,408 | 7,165,633 |
| committee | 12P | True | 133 | 5,966,852 |
| committee | TER | True | 92 | 5,259,152 |
| committee | M2 | True | 302 | 4,013,008 |
| committee | M10 | True | 589 | 3,754,846 |
| committee | Q1 | True | 371 | 3,003,320 |
| committee | M8 | True | 421 | 2,455,514 |
| type I | Q3 | True | 444 | 2,316,911 |
| committee | MY | True | 537 | 2,199,106 |
| committee | M9 | True | 383 | 1,420,768 |
| committee | M7 | True | 496 | 1,352,646 |
| committee | 12R | True | 23 | 1,171,578 |
| committee | TER | False | 15 | 1,038,060 |
| committee | M3 | True | 378 | 1,024,276 |
| committee | M6 | True | 411 | 687,539 |
| committee | 30G | False | 416 | 636,114 |
| type I | Q3 | False | 723 | 400,148 |
| type I | Q2 | True | 233 | 378,846 |
| committee | Q3 | False | 623 | 361,174 |
| committee | 12G | False | 384 | 361,002 |
| committee | M4 | True | 343 | 360,848 |
| committee | MY | False | 87 | 318,863 |
| committee | M5 | True | 246 | 237,844 |
| type I | Q1 | True | 65 | 225,144 |
| committee | YE | False | 123 | 221,137 |
| type I | YE | False | 3,858 | 74,659 |
| committee | M12 | True | 19 | 60,936 |
| committee | Q2 | False | 129 | 52,758 |
| committee | Q1 | False | 199 | 51,457 |
| committee | 30S | True | 82 | 32,612 |
| committee | M11 | True | 37 | 25,041 |
| committee | 12P | False | 224 | 19,391 |
| committee | M9 | False | 34 | 15,427 |
| committee | M10 | False | 42 | 14,195 |
| committee | M7 | False | 31 | 12,032 |
| committee | 12S | True | 2 | 10,006 |
| type I | Q1 | False | 31 | 9,272 |
| committee | M5 | False | 6 | 7,724 |
| committee | M6 | False | 10 | 5,418 |
| committee | M8 | False | 29 | 5,413 |
| committee | M12 | False | 1 | 5,000 |
| committee | M3 | False | 15 | 4,877 |
| committee | M2 | False | 7 | 4,478 |
| committee | M4 | False | 12 | 1,296 |
| type I | Q2 | False | 3 | 604 |

**Q5m. Only in pas2: by month  (0 s)**

| month | rows | dollars |
|---|---|---|
| 2023-01 | 265 | 1,488,581 |
| 2023-02 | 237 | 1,166,591 |
| 2023-03 | 144 | 201,142 |
| 2023-04 | 85 | 450,266 |
| 2023-05 | 174 | 514,634 |
| 2023-06 | 246 | 1,225,472 |
| 2023-07 | 129 | 6,195,821 |
| 2023-08 | 150 | 3,340,482 |
| 2023-09 | 246 | 4,774,440 |
| 2023-10 | 158 | 2,802,684 |
| 2023-11 | 145 | 1,944,538 |
| 2023-12 | 272 | 6,505,131 |
| 2024-01 | 433 | 3,813,479 |
| 2024-02 | 629 | 1,595,362 |
| 2024-03 | 512 | 2,798,737 |
| 2024-04 | 464 | 3,744,190 |
| 2024-05 | 661 | 10,512,257 |
| 2024-06 | 808 | 7,713,000 |
| 2024-07 | 832 | 11,689,971 |
| 2024-08 | 994 | 18,502,108 |
| 2024-09 | 2,661 | 27,390,767 |
| 2024-10 | 6,558 | 53,517,576 |
| 2024-11 | 3,965 | 18,425,431 |
| 2024-12 | 682 | 5,543,993 |
|  | 622 | 16,624,163 |

**Q5n. Only in pas2: the 20 largest spenders  (0 s)**

| spe | name | grp | rows | dollars | in_24_48_hour |
|---|---|---|---|---|---|
| C00849489 | KEYSTONE RENEWAL PAC | committee | 74 | 47,354,455 | True |
| C00870030 | MARYLAND'S FUTURE | committee | 29 | 10,794,639 | True |
| C00804856 | REPUBLICAN ACCOUNTABILITY PAC | committee | 812 | 8,638,683 | True |
| C00486845 | LCV VICTORY FUND | committee | 226 | 8,212,113 | True |
| C00886614 | YOUR COMMUNITY PAC | committee | 32 | 8,056,872 | True |
| C00834630 | BUCKEYE VALUES PAC | committee | 18 | 7,415,386 | True |
| C00053553 | NATIONAL RIFLE ASSOCIATION OF AMERICA POLITICAL VICTORY FUND | committee | 341 | 6,877,560 | True |
| C00841593 | TELL IT LIKE IT IS PAC | committee | 142 | 6,332,527 | True |
| C00833749 | AMERICAN EXCEPTIONALISM PAC | committee | 161 | 6,285,291 | True |
| C00857011 | FIGHT RIGHT INC | committee | 18 | 5,867,058 | True |
| C00801803 | SOS AMERICA PAC | committee | 37 | 5,154,368 | True |
| C00620971 | FOR OUR FUTURE | committee | 523 | 4,673,266 | True |
| C00606962 | WORKING FAMILIES PARTY PAC | committee | 145 | 4,215,040 | True |
| C00828061 | SFA FUND, INC | committee | 5 | 4,053,141 | True |
| C00855064 | CONSERVATIVE VALUES FOR UTAH | committee | 30 | 3,815,910 | True |
| C00769232 | JEFFERSON RISING | committee | 53 | 3,660,247 | True |
| C00864926 | AMERICA LEADS ACTION INC. | committee | 85 | 3,549,464 | True |
| C00544387 | AMERICAN PRINCIPLES PROJECT PAC | committee | 19 | 3,498,847 | True |
| C90022278 | NEWLIN, DAN | type I | 184 | 2,915,537 | True |
| C00890335 | STRATEGIC MAJORITY PAC | committee | 5 | 2,190,932 | True |

**Q5o. Only in pas2: 10 largest rows and 10 by hash order  (0 s)**

| pick | spe | grp | rpt_tp | fnum | tran | raw_cand | sup_opp | amt | dt | payee |
|---|---|---|---|---|---|---|---|---|---|---|
| largest | C00886614 | committee | 12G | 1,841,038 | SE.4177 | P00009423 | S | 5,800,000 |  | TARGETED PLATFORM MEDIA, LLC |
| largest | C00849489 | committee | Q3 | 1,826,107 | SE.27 | S6PA00217 | O | 3,245,625 | 2024-09-03 | DEL CIELO MEDIA LLC |
| largest | C00870030 | committee | 12G | 1,841,231 | SE.13 | S4MD00327 | O | 3,167,698 | 2024-10-09 | MAIN STREET MEDIA GROUP |
| largest | C00870030 | committee | Q3 | 1,827,942 | SE.16 | S4MD00327 | O | 3,037,741 | 2024-09-25 | MAIN STREET MEDIA GROUP |
| largest | C00849489 | committee | Q3 | 1,826,107 | SE.31 | S6PA00217 | O | 3,000,000 | 2024-09-11 | DEL CIELO MEDIA LLC |
| largest | C00849489 | committee | Q3 | 1,826,107 | SE.24 | S6PA00217 | O | 2,918,662 | 2024-08-26 | DEL CIELO MEDIA LLC |
| largest | C00849489 | committee | Q3 | 1,826,107 | SE.35 | S6PA00217 | O | 2,800,716 | 2024-09-18 | DEL CIELO MEDIA LLC |
| largest | C00849489 | committee | Q2 | 1,806,357 | SE.7 | S2PA00661 | S | 2,747,485 | 2024-05-07 | DEL CIELO MEDIA LLC |
| largest | C00849489 | committee | Q2 | 1,806,357 | SE.17 | S2PA00661 | S | 2,551,475 | 2024-05-29 | DEL CIELO MEDIA LLC |
| largest | C00849489 | committee | Q3 | 1,826,107 | SE.10 | S6PA00217 | O | 2,328,664 | 2024-07-26 | DEL CIELO MEDIA LLC |
| hash | C00432260 | committee | YE | 1,756,295 | SE.11475 | H2TX00064 | S | 590 | 2023-12-01 | THE MAIL HAUS |
| hash | C00802389 | committee | YE | 1,752,717 | 500430937 | H8NC13067 | S | 32 | 2023-11-15 | NEW BLUE INTERACTIVE |
| hash | C90021577 | type I | Q3 | 1,949,359 | F57-5886 | P00009423 | S | 8 | 2024-09-28 | RODGERS, SEAN M. |
| hash | C90011891 | type I | YE | 1,900,837 | F57.11930 | P80001571 | S | 150 | 2024-10-10 | TAYLOR, LATASHA |
| hash | C90021577 | type I | YE | 1,949,368 | F57-6538 | S4CA00555 | S | 0 | 2024-10-11 | DOLORES HUERTA ACTION FUND |
| hash | C90021577 | type I | YE | 1,949,368 | F57-27970 | H2CA21233 | S | 20 | 2024-10-11 | DOLORES HUERTA ACTION FUND |
| hash | C00891275 | committee | 30G | 1,858,577 | SE.4119 | S4AZ00139 | S | 7,368 |  | PROGRESSIVE IMPACT, LLC |
| hash | C90023037 | type I | YE | 1,874,773 | F57.000013 | H6NV04020 | S | 918 | 2024-11-02 | POPULATION CONNECTION ACTION F |
| hash | C90021577 | type I | YE | 1,949,368 | F57-14542 | H2CA13115 | S | 19 | 2024-11-06 | LIPOW, SYDNEY |
| hash | C90021577 | type I | YE | 1,949,368 | F57-14702 | H2CA13115 | S | 3 | 2024-11-08 | DOLORES HUERTA ACTION FUND |

**Q5p. The decision: unmatched 24/48-hour rows at spenders with a counted pas2 row, against counted IE dollars  (0 s)**

| unmatched_at_pas2_spenders | rows | counted_ie_dollars | share | less_web_form | share_less_web_form | share_without_rung_4 |
|---|---|---|---|---|---|---|
| 71,450,772 | 3,399 | 4,422,382,849 | 1.62% | 64,372,031 | 1.46% | 9.58% |

**Q5q. What each grain would add: by spender (spenders with no counted pas2 row) and by row (every unmatched row)  (0 s)**

| grain | rows | dollars | spenders | dollars_less_web_form |
|---|---|---|---|---|
| by spender | 363 | 43,906,446,618 | 67 | 4,835,248 |
| by row | 3,696 | 43,977,066,615 | 314 | 68,376,504 |

**Q5r. Spenders in both files: each one's latest-amendment 24/48-hour total against its counted pas2 total  (0 s)**

| grp | band | spenders | h24_dollars | pas2_dollars | h24_excess_dollars |
|---|---|---|---|---|---|
| committee | 1-5% | 68 | 889,278,984 | 897,679,944 | 2,064,548 |
| committee | 24/48-hour more than 5% above | 79 | 161,894,862 | 126,021,163 | 35,873,699 |
| committee | 24/48-hour more than 5% below | 111 | 84,285,357 | 110,901,273 | 0 |
| committee | within 1% | 495 | 3,177,346,970 | 3,177,548,822 | 747,228 |
| type I | 1-5% | 15 | 18,328,720 | 18,547,005 | 138,136 |
| type I | 24/48-hour more than 5% above | 14 | 2,877,863 | 1,160,722 | 1,717,141 |
| type I | 24/48-hour more than 5% below | 29 | 4,252,723 | 6,028,048 | 0 |
| type I | within 1% | 77 | 58,651,143 | 58,682,955 | 8,459 |

**Q5s. Spenders in both: the 20 with the largest 24/48-hour excess over pas2  (0 s)**

| spe | name | grp | h24_dollars | pas2_dollars | excess | last_received | last_pas2 |
|---|---|---|---|---|---|---|---|
| C00075820 | NRCC | committee | 50,576,807 | 36,483,042 | 14,093,765 | 2024-11-01 | 2024-10-30 |
| C00620971 | For Our Future | committee | 14,418,862 | 11,308,269 | 3,110,593 | 2024-11-04 | 2024-12-19 |
| C00869073 | Power to the Polls Federal Fund | committee | 5,032,050 | 2,220,889 | 2,811,161 | 2025-06-27 | 2024-11-05 |
| C00815928 | READY FOR RON | committee | 4,345,000 | 1,680,549 | 2,664,451 | 2024-01-03 | 2023-12-31 |
| C00004036 | SEIU COPE (Service Employees International Union Committee On Political Education) | committee | 9,443,913 | 6,882,856 | 2,561,057 | 2024-11-04 | 2024-11-03 |
| C00693838 | MORE JOBS, LESS GOVERNMENT | committee | 21,031,610 | 19,943,488 | 1,088,122 | 2024-11-04 | 2024-11-03 |
| C00747998 | Care in Action PAC | committee | 5,512,682 | 4,501,845 | 1,010,837 | 2024-12-24 | 2024-12-23 |
| C00707844 | EDF Action Votes | committee | 11,739,177 | 10,871,378 | 867,799 | 2024-11-01 | 2024-10-31 |
| C90016510 | PLANNED PARENTHOOD ADVOCATES OF WISCONSIN POLITICAL FUND | type I | 706,738 | 125,580 | 581,158 | 2024-11-01 | 2024-09-20 |
| C00858779 | We Deserve Better, Inc. | committee | 3,483,035 | 2,905,007 | 578,028 | 2024-02-20 | 2024-02-15 |
| C90016023 | 32BJ UNITED AMERICAN DREAM FUND | type I | 609,475 | 45,259 | 564,216 | 2024-10-31 | 2024-06-04 |
| C00804856 | Republican Accountability PAC | committee | 37,292,740 | 36,750,334 | 542,406 | 2024-11-05 | 2024-12-30 |
| C00804823 | Mainstream Democrats PAC | committee | 3,080,592 | 2,573,060 | 507,532 | 2024-10-25 | 2024-10-29 |
| C00689745 | MAKE THE ROAD ACTION INDEPENDENT EXPENDITURE COMMITTEE | committee | 945,767 | 440,771 | 504,996 | 2024-10-28 | 2024-10-31 |
| C00821439 | American Values 2024 | committee | 11,930,135 | 11,461,194 | 468,941 | 2024-11-04 | 2024-11-20 |
| C00753277 | Black Voters Matter Action PAC | committee | 4,063,370 | 3,623,631 | 439,739 | 2025-04-24 | 2025-10-25 |
| C00869321 | Victory PAC | committee | 968,231 | 543,912 | 424,319 | 2024-07-29 | 2024-08-01 |
| C00865923 | BUILDING A STRONG AMERICA | committee | 419,272 | 0 | 419,272 | 2024-05-07 |  |
| C00756940 | Texas Organizing Project PAC | committee | 694,260 | 283,045 | 411,215 | 2024-10-30 | 2024-10-29 |
| C00684969 | JDCA PAC | committee | 1,415,302 | 1,060,570 | 354,732 | 2024-11-03 | 2024-11-05 |

**The 24/48-hour file's `tran_id` is `pas2`'s** (§3's assertion, confirmed for most): rung 1 matches
40,772 rows, $2,931,584,760 of the file's $4.40B without web-form ids. Within it the
amounts agree within $1 on 31,035 of 38,656 keys. Where they differ, `pas2` is $113M lower net:
the estimates fell (Q5c–d). Candidates differ after aliases on 7,108 keys. The largest are Future
Forward USA Action's lines (`C00669259`), coded Harris in the 24/48-hour file and Biden in `pas2`,
which the handoff credits to Harris (Q5f). The side disagrees on 125 keys, 0.3%.

**Where it is not, the same spending is renumbered.** MAKE AMERICA GREAT AGAIN INC.'s `SE.8507`
($30,033,271 against Biden, 2024-10-25) is `pas2`'s `SE.8485` ($30,033,271 against Harris, the same
day). Rungs 2 and 3 miss it on the candidate, and rung 4 finds it. Rungs 2–4 compare amounts with the cents dropped, as `pas2` drops them (Q8l): MAGA's `SE.8029`
($21,147,261 as these tables round its cents) is `pas2`'s `SE.8022` ($21,147,260), and no longer appears among the residuals. After rung 4,
$71,450,772 of 24/48-hour rows at spenders in `pas2` stays unmatched, and `pas2` keeps
$212,480,816 of its own unmatched. Both peak in September and October 2024 (Q5i, Q5m). Spender by spender they balance (Q5r). For 572 of
888 spenders the two totals are within 1%. Where the 24/48-hour file is higher, it is higher by
$40,549,211 in all, 0.92% of counted dollars, led by the NRCC ($14.1M, its last 24-hour lines
after its last `pas2` row).

**The memo bucket:** 4,355 rows ($39,044,429) match only a `pas2` memo line. They are counted as their own bucket, never as "only in 24/48-hour".

**Decision line:** unmatched 24/48-hour rows at spenders in `pas2` hold $71,450,772, **1.62%** of
counted independent expenditure dollars (1.46% with web-form ids aside; 9.58% with §2's three rungs
alone, without rung 4). That is over §1.1's 1%
bar, so the by-spender rule is **not adopted here**: NEU-2163 decides. The rows are the same
spending under other ids, other amounts and the other presidential candidate's id, not money
`pas2` lacks: per spender the file exceeds `pas2` by 0.92%. By spender the rule would add
$43,906,446,618 (67 spenders), $4,835,248 with web-form ids aside. By row it would add
$43,977,066,615, and $68,376,504 with web-form ids aside, most of it spending `pas2` holds under other
ids or amounts.
**Recommended to NEU-2163: by spender, with Q6's screen.**

## Q6: what the by-spender rule adds (2024)

```python
# Q6: what the by-spender rule adds (2024): every latest-amendment 24/48-hour row of a spender with
# no counted pas2 independent expenditure in the cycle.
h24(2024)
adopt_h24_rule(2024, "chain")
counted_pas2(2024)
silver("reported_total", 2024)
con.execute("""
CREATE TABLE added AS
SELECT l.*, r.independent_expenditures AS reported_ie, r.committee_id IS NOT NULL AS has_reported_total,
    c.candidate_id IS NOT NULL AS candidate_of_cycle, c.race_id,
    l.acand IN (SELECT trim(CAND_ID) FROM cn_2024) AS in_cn
FROM l_2024_a AS l
LEFT JOIN silver_2024.reported_total AS r ON r.committee_id = l.spe
LEFT JOIN (SELECT candidate_id, any_value(race_id) AS race_id FROM silver_2024.candidate GROUP BY 1) AS c
    ON c.candidate_id = l.acand
WHERE l.spe NOT IN (SELECT spe FROM p_2024)""")

show("Q6a. Added: spenders, rows and dollars by group, web-form id and whether the spender files a reported total", """
SELECT grp, tran LIKE 'WFT%' AS web_form, has_reported_total, coalesce(reported_ie, 0) > 0 AS reports_ie,
    count(DISTINCT spe) AS spenders, count(*) AS rows, sum(amt) AS dollars
FROM added GROUP BY ALL ORDER BY ALL""")
show("Q6b. Every added spender, by dollars, with its reported independent expenditures", """
SELECT spe, any_value(trim(spe_nam)) AS name, grp, count(*) AS rows, sum(amt) AS dollars,
    any_value(reported_ie) AS reported_ie, bool_or(tran LIKE 'WFT%') AS web_form,
    string_agg(DISTINCT sup_opp, ',') AS sides, min(rdt) AS first_received
FROM added GROUP BY spe, grp ORDER BY dollars DESC""")
show("Q6c. A screen: added rows whose spender's 24/48-hour total exceeds its reported independent expenditures more than tenfold, or that files none", """
WITH s AS (SELECT spe, sum(amt) AS d, any_value(reported_ie) AS rep FROM added GROUP BY 1)
SELECT CASE WHEN rep IS NULL OR rep <= 0 THEN 'no reported IE'
            WHEN d > 10 * rep THEN 'over 10x reported' ELSE 'within 10x reported' END AS screen,
    count(*) AS spenders, sum(d) AS dollars, sum(rep) AS reported
FROM s GROUP BY ALL ORDER BY ALL""")
show("Q6d. Added rows under the screen (spender reports IE and is within 10x): by group and side", """
WITH s AS (SELECT spe FROM added GROUP BY 1 HAVING any_value(reported_ie) > 0 AND sum(amt) <= 10 * any_value(reported_ie))
SELECT grp, sup_opp, count(DISTINCT spe) AS spenders, count(*) AS rows, sum(amt) AS dollars
FROM added WHERE spe IN (SELECT spe FROM s) GROUP BY ALL ORDER BY ALL""")
show("Q6e. Added rows' candidates (alias-resolved)", """
SELECT CASE WHEN acand IS NULL THEN 'blank' WHEN NOT in_cn THEN 'not in cn' WHEN NOT candidate_of_cycle THEN 'not a candidate of the cycle'
            WHEN race_id IS NULL THEN 'candidate, no race' ELSE 'candidate with a race' END AS candidate,
    acand IS DISTINCT FROM cand AS alias_resolved, count(*) AS rows, sum(amt) AS dollars,
    sum(amt) FILTER (WHERE spe IN (SELECT spe FROM added GROUP BY 1
        HAVING any_value(reported_ie) > 0 AND sum(amt) <= 10 * any_value(reported_ie))) AS dollars_under_screen
FROM added GROUP BY ALL ORDER BY ALL""")
show("Q6f. Added: the 20 largest spenders under the screen", """
WITH s AS (SELECT spe FROM added GROUP BY 1 HAVING any_value(reported_ie) > 0 AND sum(amt) <= 10 * any_value(reported_ie))
SELECT spe, any_value(trim(spe_nam)) AS name, grp, count(*) AS rows, sum(amt) AS dollars, any_value(reported_ie) AS reported_ie,
    sum(amt) FILTER (WHERE race_id IS NOT NULL) AS dollars_reaching_a_race
FROM added WHERE spe IN (SELECT spe FROM s) GROUP BY spe, grp ORDER BY dollars DESC LIMIT 20""")
con.execute(f"COPY (SELECT * FROM added) TO {literal(work / 'added_2024.parquet')} (FORMAT parquet)")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
```

**Q6a. Added: spenders, rows and dollars by group, web-form id and whether the spender files a reported total  (0 s)**

| grp | web_form | has_reported_total | reports_ie | spenders | rows | dollars |
|---|---|---|---|---|---|---|
| absent | False | False | False | 1 | 1 | 64,107 |
| absent | True | False | False | 7 | 8 | 33,921,014,570 |
| committee | False | True | False | 19 | 141 | 3,185,809 |
| committee | True | False | False | 7 | 31 | 9,979,516,811 |
| committee | True | True | False | 8 | 31 | 526,766 |
| committee | True | True | True | 1 | 3 | 50,000 |
| type I | False | False | False | 8 | 21 | 476,796 |
| type I | False | True | False | 2 | 26 | 157,238 |
| type I | False | True | True | 13 | 97 | 951,297 |
| type I | True | False | False | 1 | 4 | 503,222 |

**Q6b. Every added spender, by dollars, with its reported independent expenditures  (0 s)**

| spe | name | grp | rows | dollars | reported_ie | web_form | sides | first_received |
|---|---|---|---|---|---|---|---|---|
| C00874586 | THE COMMITTEE OF 300 | absent | 2 | 17,738,007,416 |  | True | S | 2024-03-31 |
| C00875427 | THE COURT OF DIVINE JUSTICE | committee | 1 | 9,978,412,568 |  | True | S | 2024-04-20 |
| C00785352 | THE COMMITTEE OF 300 | absent | 1 | 9,000,000,000 |  | True | S | 2024-03-26 |
| C00873521 | Republican Emo Girl | absent | 1 | 6,347,882,325 |  | True | S | 2024-03-17 |
| C00874909 | The Masonic Illuminati Eye | absent | 1 | 579,874,829 |  | True | S | 2024-04-02 |
| C00843094 | Gus Associates | absent | 1 | 255,000,000 |  | True | S | 2023-06-16 |
| C00770149 | Shield PAC | committee | 7 | 1,225,000 | 0 | False | S | 2023-03-22 |
| C00850719 | UnitedTech Governance Coalition for National Politics and Legislation | committee | 1 | 950,000 |  | True | S | 2023-09-15 |
| C90018730 | BIG SKY 55+ | type I | 4 | 503,222 |  | True | S | 2024-09-16 |
| C00787432 | ALL FOR OUR COUNTRY | committee | 8 | 427,769 | 0 | False | O,S | 2023-01-06 |
| C00504522 | HUDSON FOR CONGRESS | committee | 2 | 413,923 |  | True | S | 2024-09-11 |
| C00891077 | Let's Get It Done PAC | committee | 11 | 355,235 | 0 | False | O | 2024-10-24 |
| C90022898 | Independent Veterans of America | type I | 2 | 322,601 |  | False | S | 2024-10-23 |
| C00836916 | Team Kennedy | committee | 34 | 305,101 |  | False | S | 2024-10-18 |
| C00890665 | MI PODER PAC | committee | 6 | 305,000 | 0 | False | S | 2024-10-29 |
| C90022781 | Earthjustice Action | type I | 18 | 293,577 | 293,577 | False | S,O | 2024-10-17 |
| C00734400 | CYRUS SAJNA FOR CONGRESS COMMITTEE | absent | 1 | 250,000 |  | True | S | 2023-10-21 |
| C90020447 | FLIC VOTES INC | type I | 8 | 207,175 | 209,322 | False | O,S | 2024-10-08 |
| C90020058 | RED WINE AND BLUE | type I | 5 | 134,695 | 134,695 | False | S | 2024-10-23 |
| C00162339 | OHIO REPUBLICAN PARTY STATE CENTRAL & EXECUTIVE COMMITTEE | committee | 2 | 130,012 | 0 | False | S | 2024-11-04 |
| C90022591 | IMPACT CT INC. | type I | 13 | 123,149 | 0 | False | S | 2024-10-10 |
| C00540229 | Constitutional Rights PAC | committee | 2 | 110,000 | 0 | False | O | 2024-10-17 |
| C00750778 | LANDSLIDE | committee | 7 | 98,604 |  | True | O | 2024-12-24 |
| C90022567 | Somos the Future | type I | 5 | 90,020 | 90,020 | False | S | 2024-10-09 |
| C90020454 | Freedom Action Now Inc. | type I | 5 | 84,468 | 84,696 | False | O | 2024-10-29 |
| C90022997 | PAC for Georgia's Youth | type I | 2 | 76,999 | 76,999 | False | S,O | 2024-11-01 |
| C00455923 | FEDUP POLITICAL ACTION COMMITTEE AKA FEDUP PAC | committee | 28 | 75,361 | 0 | False | S | 2024-04-25 |
| C00428557 | ColorOfChange PAC | committee | 15 | 66,800 | 0 | False | S | 2024-10-18 |
| C00807958 | PATRIOTS PAC LLC | committee | 5 | 64,639 | 0 | True | S | 2023-10-23 |
| C90022054 | Casey Family Farms | absent | 1 | 64,107 |  | False | S | 2023-08-10 |
| C00001636 | SMART TD PAC | committee | 6 | 63,500 | 0 | False | S | 2024-10-04 |
| C00849034 | BUILDING A STRONG RHODE ISLAND | committee | 6 | 54,892 |  | True | S | 2023-08-30 |
| C90023268 | VoterBridge | type I | 1 | 51,424 |  | False | S | 2025-03-11 |
| C00892117 | BEYONDROE.COM POLITICAL FUND | committee | 3 | 50,000 | 59,792 | True | O | 2024-11-01 |
| C90021619 | Ruralorganizing.org Inc. | type I | 1 | 39,095 |  | False | S | 2024-10-18 |
| C90021668 | Black Ohio Leaders for Democracy | type I | 12 | 37,491 |  | False | S | 2024-11-03 |
| C90022104 | NH PEACE ACTION | type I | 13 | 34,090 | 0 | False | O | 2024-01-30 |
| C90018391 | The Family Foundation Action | type I | 7 | 33,892 | 6,900 | False | S,O | 2024-10-23 |
| C00885954 | COCONUT BRAT PAC | committee | 2 | 30,000 | 0 | False | S | 2024-11-04 |
| C00891382 | MOTHERING JUSTICE PAC | committee | 3 | 28,380 | 0 | False | S | 2024-11-01 |
| C00893198 | CONSERVATIVE FIGHTER PAC | committee | 2 | 25,279 | 0 | False | S | 2025-01-02 |
| C00563254 | DEMOCRATIC JEWISH OUTREACH PA | committee | 4 | 23,040 | 0 | True | S | 2024-10-09 |
| C00332841 | INDEPENDENT BANKERS ASSOCIATION OF TEXAS FEDERAL PAC (IBAT FEDPAC) | committee | 12 | 13,000 | 0 | True | S | 2024-10-24 |
| C90022070 | Freshwater | type I | 1 | 12,000 |  | False | O | 2023-08-23 |
| C90021841 | Financial Services Stakeholder Action NFP d.b.a. Private Equity Stakeholder Action | type I | 6 | 11,479 | 11,479 | False | S | 2024-10-28 |
| C00499988 | Cotton for Senate | committee | 2 | 10,000 |  | False | S,O | 2024-06-04 |
| C00792028 | WAKE UP NEW YORK | committee | 1 | 10,000 | 0 | False | S | 2024-10-31 |
| C00332296 | Susan B. Anthony List. Inc. Candidate Fund (DBA Susan B. Anthony Pro-Life America Candidate Fund) | committee | 2 | 10,000 | 0 | False | O,S | 2024-08-29 |
| C90016577 | MAKE THE ROAD ACTION INC. | type I | 1 | 10,000 |  | False | S | 2024-05-29 |
| C00890707 | TUBMAN DOUGLASS PAC | committee | 2 | 7,895 | 0 | True | O,S | 2024-11-01 |
| C90022146 | Seattle DSA | type I | 3 | 7,833 | 15,363 | False | O | 2024-03-06 |
| C00858852 | NRRC | committee | 6 | 4,675 | 0 | False | O | 2024-10-28 |
| C00863761 | TERRY L. CRANDALL FOR CONGRESS | committee | 2 | 3,765 |  | True | S | 2024-01-19 |
| C00018929 | North Dakota Republican Party | committee | 3 | 3,689 | 0 | False | S | 2024-10-25 |
| C90018771 | FORFACT LLC | type I | 35 | 3,454 | 759 | False | O,S | 2024-10-30 |
| C90023094 | International Brotherhood of 42 Joint Council | type I | 1 | 3,021 | 3,021 | False | S | 2024-12-10 |
| C90023003 | Herr | type I | 1 | 2,614 | 2,614 | False | S | 2024-11-01 |
| C90020124 | Free the Ballot! Incarcerated Voter Family Network | type I | 2 | 2,250 |  | False | S | 2024-10-25 |
| C90022948 | U.S. Veterans for Ukraine Inc. | type I | 1 | 2,070 | 7,120 | False | O | 2024-10-29 |
| C90022153 | American Muslim Advancement Council | type I | 1 | 1,935 |  | False | S | 2024-03-20 |
| C00890640 | COUNTERPOINT USA | committee | 3 | 504 | 0 | True | O | 2024-12-23 |
| C00878033 | COUNTRY COMMUNITY HONOR | committee | 14 | 498 |  | True | S | 2024-06-27 |
| C00881896 | NATHAN E BILLIPS | committee | 1 | 250 |  | True | O | 2024-08-16 |
| C00481200 | National Association For Gun Rights Inc PAC | committee | 1 | 8 | 0 | False | S | 2024-03-19 |
| C00880138 | TYLER LEE SCAFIDI''S PRESIDENTIAL POLITICAL ACTION COMMITTEE (PAC) FOR EQUITABLE AMERICAN LAW, ORDER, AND JUSTICE | committee | 1 | 1 |  | True | S | 2024-06-02 |
| C00830596 | THE AMERICAN POLITICAL PARTY | absent | 1 | 0 |  | True | S | 2023-01-02 |
| C00884098 | JEANNICA LANE | committee | 1 | 0 |  | True | S | 2024-07-30 |

**Q6c. A screen: added rows whose spender's 24/48-hour total exceeds its reported independent expenditures more than tenfold, or that files none  (0 s)**

| screen | spenders | dollars | reported |
|---|---|---|---|
| no reported IE | 53 | 43,905,445,320 | 0 |
| within 10x reported | 14 | 1,001,297 | 996,357 |

**Q6d. Added rows under the screen (spender reports IE and is within 10x): by group and side  (0 s)**

| grp | sup_opp | spenders | rows | dollars |
|---|---|---|---|---|
| committee | O | 1 | 3 | 50,000 |
| type I | O | 8 | 43 | 336,095 |
| type I | S | 10 | 53 | 615,118 |
| type I |  | 1 | 1 | 85 |

**Q6e. Added rows' candidates (alias-resolved)  (0 s)**

| candidate | alias_resolved | rows | dollars | dollars_under_screen |
|---|---|---|---|---|
| blank | False | 125 | 1,626,941 | 750,073 |
| candidate with a race | False | 226 | 18,523,259,904 | 251,224 |
| candidate, no race | False | 10 | 25,126,559,765 |  |
| not in cn | False | 2 | 255,000,008 |  |

**Q6f. Added: the 20 largest spenders under the screen  (0 s)**

| spe | name | grp | rows | dollars | reported_ie | dollars_reaching_a_race |
|---|---|---|---|---|---|---|
| C90022781 | Earthjustice Action | type I | 18 | 293,577 | 293,577 |  |
| C90020447 | FLIC VOTES INC | type I | 8 | 207,175 | 209,322 |  |
| C90020058 | RED WINE AND BLUE | type I | 5 | 134,695 | 134,695 | 96,841 |
| C90022567 | Somos the Future | type I | 5 | 90,020 | 90,020 | 90,020 |
| C90020454 | Freedom Action Now Inc. | type I | 5 | 84,468 | 84,696 |  |
| C90022997 | PAC for Georgia's Youth | type I | 2 | 76,999 | 76,999 |  |
| C00892117 | BEYONDROE.COM POLITICAL FUND | committee | 3 | 50,000 | 59,792 |  |
| C90018391 | The Family Foundation Action | type I | 7 | 33,892 | 6,900 | 33,892 |
| C90021841 | Financial Services Stakeholder Action NFP d.b.a. Private Equity Stakeholder Action | type I | 6 | 11,479 | 11,479 | 11,479 |
| C90022146 | Seattle DSA | type I | 3 | 7,833 | 15,363 | 7,833 |
| C90018771 | FORFACT LLC | type I | 35 | 3,454 | 759 | 3,454 |
| C90023094 | International Brotherhood of 42 Joint Council | type I | 1 | 3,021 | 3,021 | 3,021 |
| C90023003 | Herr | type I | 1 | 2,614 | 2,614 | 2,614 |
| C90022948 | U.S. Veterans for Ukraine Inc. | type I | 1 | 2,070 | 7,120 | 2,070 |

Unscreened, the by-spender rule adds the hoaxes: $43,906,446,618, of which $43,905,445,320 is
from 53 spenders that report no independent expenditure at all (Q6c). The screen keeps a spender
that reports independent expenditures in `reported_total` and whose 24/48-hour total is within ten times that figure. The screen and its tenfold threshold are this
document's, not §1.1's, and were set after seeing the hoaxes. The gap they open is wide: no kept
spender holds more than five times its reported figure (The Family Foundation Action, 4.9), and every dropped one reports none (Q6b–c).
It adds **14 spenders, 100 rows, $1,001,297** against $996,357 they report. 13 are Form 5
filers: Earthjustice Action $293,577, FLIC Votes $207,175, Red Wine and Blue $134,695. $251,224
of it reaches a race and $750,073 names no candidate (Q6e). Real spenders the screen loses are
those reporting no independent expenditure: Shield PAC ($1,225,000, dated 2023), Team Kennedy
($305,101), 19 committees with $3,185,809 in all. That is the cost of the screen, and
NEU-2163 weighs it.

**The figure NEU-2165's definition of done is within 1% of: $1,001,297** (screened), with
$4,835,248 (unscreened, web-form ids aside) if NEU-2163 drops the screen.

## Q7: timeliness

```python
# Q7: timeliness. 2026 live: its 24/48-hour file and pas226.zip fetched from FEC in the same
# minute; 2024 by date, from the same files as Q1-Q6.
bulk("pas2", 2026, fresh=True)
h24(2026)
for cycle in (2026, 2024):
    if cycle == 2024:
        h24(2024)
    adopt_h24_rule(cycle, "chain")
    counted_pas2(cycle, from_silver=(cycle == 2024))
    silver("reported_total", cycle)
    ladder(cycle, tag=f"_{cycle}")

show("Q7a. 2026 pas2 as fetched: the latest transaction date among 24A/24E rows, by RPT_TP", """
SELECT RPT_TP, count(*) AS rows, sum(TRANSACTION_AMT) AS dollars,
    max(CAST(try_strptime(TRANSACTION_DT, '%m%d%Y') AS DATE)) AS latest
FROM pas2_2026 WHERE TRANSACTION_TP IN ('24A', '24E') GROUP BY 1 ORDER BY latest DESC NULLS LAST""")

for cycle in (2026, 2024):
    t = f"_{cycle}"
    con.execute(f"""
    CREATE OR REPLACE TABLE lt{t} AS
    SELECT l.*, lm.rung, r.period_end, r.committee_id IS NOT NULL AS has_reported_total,
        coalesce(l.edt, l.ddt) AS on_date,
        CASE WHEN r.period_end IS NULL THEN 'no period_end'
             WHEN coalesce(l.edt, l.ddt) IS NULL THEN 'undated'
             WHEN coalesce(l.edt, l.ddt) > r.period_end THEN 'after period_end' ELSE 'on or before' END AS timing
    FROM l_{cycle}_a AS l JOIN lm{t} AS lm USING (rn)
    LEFT JOIN silver_{cycle}.reported_total AS r ON r.committee_id = l.spe""")
    show(f"Q7b. {cycle}: spenders' reported_total.period_end (spenders in the 24/48-hour file)", f"""
    SELECT period_end, count(DISTINCT spe) AS spenders, count(*) AS rows, sum(amt) AS dollars
    FROM lt{t} GROUP BY 1 ORDER BY dollars DESC LIMIT 12""")
    show(f"Q7c. {cycle}: latest-amendment 24/48-hour rows against their spender's period_end, and the ladder", f"""
    SELECT timing, grp, count(*) AS rows, sum(amt) AS dollars,
        count(*) FILTER (WHERE rung IS NOT NULL AND rung <> 'memo') AS rows_matched,
        sum(amt) FILTER (WHERE rung IS NOT NULL AND rung <> 'memo') AS dollars_matched,
        (sum(amt) FILTER (WHERE rung IS NOT NULL AND rung <> 'memo') / nullif(sum(amt), 0))::DOUBLE AS matched_share
    FROM lt{t} GROUP BY ALL ORDER BY ALL""")
    show(f"Q7d. {cycle}: rows after period_end by week of their date", f"""
    SELECT date_trunc('week', on_date)::DATE AS week, count(*) AS rows, sum(amt) AS dollars,
        sum(amt) FILTER (WHERE rung IS NOT NULL AND rung <> 'memo') AS dollars_matched
    FROM lt{t} WHERE timing = 'after period_end' GROUP BY 1 ORDER BY 1 DESC LIMIT 16""")
    show(f"Q7e. {cycle}: the decision: rows after period_end, and how much of them pas2 already holds", f"""
    SELECT count(*) AS rows, sum(amt) AS dollars,
        sum(amt) FILTER (WHERE rung IS NOT NULL AND rung <> 'memo') AS dollars_already_in_pas2,
        (sum(amt) FILTER (WHERE rung IS NOT NULL AND rung <> 'memo') / sum(amt))::DOUBLE AS share_already_in_pas2,
        sum(amt) FILTER (WHERE rung IS NULL OR rung = 'memo') AS dollars_rule_would_add,
        count(DISTINCT spe) AS spenders
    FROM lt{t} WHERE timing = 'after period_end'""")
    show(f"Q7f. {cycle}: rows after period_end, the 15 largest spenders", f"""
    SELECT spe, any_value(trim(spe_nam)) AS name, grp, any_value(period_end) AS period_end, count(*) AS rows,
        sum(amt) AS dollars, sum(amt) FILTER (WHERE rung IS NOT NULL AND rung <> 'memo') AS matched,
        max(on_date) AS latest
    FROM lt{t} WHERE timing = 'after period_end' GROUP BY spe, grp ORDER BY dollars DESC LIMIT 15""")
print("\nsource dates:", {c: META[str(c)]["source_dates"] for c in (2024, 2026)})
```

```text
https://www.fec.gov/files/bulk-downloads/2026/pas226.zip | Last-Modified: Sun, 22 Nov 2026 17:01:09 GMT | bytes 9,568,089 | downloaded 2026-11-24T15:16:34+00:00
https://www.fec.gov/files/bulk-downloads/2026/independent_expenditure_2026.csv | Last-Modified: Tue, 24 Nov 2026 10:13:31 GMT | bytes 13,733,832 | downloaded 2026-11-24T15:16:38+00:00
h24raw_2026: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:07:00+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
```

**Q7a. 2026 pas2 as fetched: the latest transaction date among 24A/24E rows, by RPT_TP  (0 s)**

| RPT_TP | rows | dollars | latest |
|---|---|---|---|
| M12 | 303 | 1,069,479 | 2026-11-21 |
| 12G | 1,592 | 105,320,620 | 2026-10-14 |
| Q3 | 9,554 | 667,518,991 | 2026-10-01 |
| M10 | 3,225 | 364,886,266 | 2026-09-30 |
| TER | 191 | 12,725,400 | 2026-09-21 |
| M9 | 1,438 | 54,075,630 | 2026-08-31 |
| M7 | 1,506 | 84,030,103 | 2026-08-21 |
| 30R | 8 | 324,999 | 2026-08-18 |
| 30S | 182 | 9,417,467 | 2026-08-14 |
| 12P | 1,279 | 97,380,252 | 2026-08-12 |
| 12R | 79 | 12,420,901 | 2026-08-04 |
| M8 | 1,457 | 93,686,940 | 2026-07-31 |
| 12S | 132 | 4,858,803 | 2026-07-29 |
| Q2 | 2,753 | 120,772,701 | 2026-07-01 |
| M6 | 1,625 | 93,799,851 | 2026-06-03 |
| M5 | 1,104 | 34,702,651 | 2026-04-30 |
| M4 | 842 | 28,119,633 | 2026-03-31 |
| Q1 | 1,352 | 85,335,477 | 2026-03-31 |
| M3 | 1,083 | 48,233,944 | 2026-03-06 |
| M2 | 552 | 6,912,773 | 2026-02-02 |
| YE | 796 | 31,835,699 | 2025-12-31 |
| M11 | 170 | 194,742 | 2025-10-30 |
| MY | 794 | 6,359,713 | 2025-06-30 |

**Q7b. 2026: spenders' reported_total.period_end (spenders in the 24/48-hour file)  (0 s)**

| period_end | spenders | rows | dollars |
|---|---|---|---|
|  | 70 | 2,131 | 38,537,975,668 |
| 2026-10-14 | 623 | 37,577 | 3,782,516,368 |
| 2026-09-30 | 177 | 6,017 | 155,086,663 |
| 2026-10-05 | 1 | 83 | 35,406,730 |
| 2026-09-10 | 1 | 43 | 17,344,929 |
| 2026-10-15 | 6 | 183 | 15,773,814 |
| 2026-07-06 | 3 | 72 | 11,144,088 |
| 2026-07-15 | 1 | 73 | 7,484,113 |
| 2026-05-11 | 1 | 22 | 4,886,822 |
| 2026-11-22 | 2 | 50 | 4,427,061 |
| 2026-06-30 | 15 | 98 | 4,168,210 |
| 2026-08-04 | 1 | 16 | 3,943,595 |

**Q7c. 2026: latest-amendment 24/48-hour rows against their spender's period_end, and the ladder  (0 s)**

| timing | grp | rows | dollars | rows_matched | dollars_matched | matched_share |
|---|---|---|---|---|---|---|
| after period_end | committee | 13,563 | 1,276,098,036 | 25 | 4,688,582 | 0.37% |
| after period_end | type I | 2,869 | 11,376,056 | 77 | 1,213,607 | 10.67% |
| no period_end | absent | 34 | 38,524,001,200 | 0 |  |  |
| no period_end | committee | 819 | 9,437,587 | 0 |  |  |
| no period_end | type I | 1,278 | 4,536,881 | 0 |  |  |
| on or before | committee | 26,536 | 2,761,585,059 | 17,897 | 1,893,621,726 | 68.57% |
| on or before | type I | 1,952 | 14,389,202 | 1,749 | 12,470,958 | 86.67% |

**Q7d. 2026: rows after period_end by week of their date  (0 s)**

| week | rows | dollars | dollars_matched |
|---|---|---|---|
| 2028-09-25 | 1 | 32,070 |  |
| 2026-11-23 | 3 | 7,786 | 200 |
| 2026-11-16 | 11 | 5,674 | 385 |
| 2026-11-09 | 51 | 603,083 |  |
| 2026-11-02 | 631 | 5,157,750 | 228,682 |
| 2026-10-26 | 6,208 | 543,989,069 | 914,435 |
| 2026-10-19 | 6,247 | 625,164,333 | 1,986,188 |
| 2026-10-12 | 2,798 | 109,709,125 | 2,550,706 |
| 2026-10-05 | 362 | 2,310,167 | 217,378 |
| 2026-09-28 | 119 | 489,036 | 4,215 |
| 2026-06-29 | 1 | 6,000 |  |

**Q7e. 2026: the decision: rows after period_end, and how much of them pas2 already holds  (0 s)**

| rows | dollars | dollars_already_in_pas2 | share_already_in_pas2 | dollars_rule_would_add | spenders |
|---|---|---|---|---|---|
| 16,432 | 1,287,474,092 | 5,902,189 | 0.46% | 1,281,571,904 | 512 |

**Q7f. 2026: rows after period_end, the 15 largest spenders  (0 s)**

| spe | name | grp | period_end | rows | dollars | matched | latest |
|---|---|---|---|---|---|---|---|
| C00495028 | HMP | committee | 2026-10-14 | 645 | 157,119,155 |  | 2026-10-31 |
| C00865444 | WinSenate | committee | 2026-10-14 | 184 | 114,759,273 |  | 2026-11-01 |
| C00571703 | SLF PAC | committee | 2026-10-14 | 336 | 102,137,317 |  | 2026-11-03 |
| C00960435 | NO GOING BACK PAC INC. | committee | 2026-10-14 | 591 | 85,586,609 |  | 2026-11-02 |
| C00504530 | CLF | committee | 2026-10-14 | 287 | 85,010,718 |  | 2026-10-30 |
| C00960443 | SAFETY & AFFORDABILITY PAC INC. | committee | 2026-10-14 | 70 | 46,992,687 |  | 2026-10-30 |
| C00961276 | Lower Costs Now | committee | 2026-10-14 | 159 | 44,450,590 |  | 2026-11-01 |
| C00879510 | America PAC | committee | 2026-10-14 | 469 | 35,382,148 |  | 2026-11-02 |
| C00960211 | TEXAS PAC | committee | 2026-10-14 | 10 | 33,538,779 |  | 2026-10-26 |
| C00915595 | Government That Works PAC | committee | 2026-10-14 | 147 | 26,974,874 |  | 2026-11-01 |
| C00688655 | EVERYTOWN FOR GUN SAFETY VICTORY FUND (EVERYTOWN VICTORY FUND) | committee | 2026-10-14 | 104 | 26,569,179 |  | 2026-10-30 |
| C00744920 | CFFE PAC | committee | 2026-10-14 | 243 | 22,766,693 |  | 2026-11-01 |
| C00486845 | LCV Victory Fund | committee | 2026-10-14 | 162 | 21,523,488 |  | 2026-10-30 |
| C00853861 | GLCF, INC. | committee | 2026-10-14 | 11 | 18,431,450 |  | 2026-11-02 |
| C00687103 | Americans for Prosperity Action, Inc. (AFP Action) DBA CVA Action and DBA LIBRE Action | committee | 2026-10-14 | 404 | 17,540,974 |  | 2026-10-30 |

**Q7b. 2024: spenders' reported_total.period_end (spenders in the 24/48-hour file)  (0 s)**

| period_end | spenders | rows | dollars |
|---|---|---|---|
|  | 24 | 65 | 43,901,575,507 |
| 2024-12-31 | 846 | 59,494 | 4,314,155,563 |
| 2024-11-08 | 1 | 122 | 33,816,255 |
| 2024-01-24 | 1 | 94 | 14,978,801 |
| 2024-10-24 | 2 | 33 | 10,573,082 |
| 2024-12-05 | 4 | 110 | 9,798,366 |
| 2024-12-27 | 1 | 191 | 6,554,191 |
| 2024-09-30 | 17 | 183 | 5,385,201 |
| 2024-03-31 | 9 | 223 | 4,271,268 |
| 2024-08-20 | 3 | 75 | 3,911,827 |
| 2024-03-20 | 1 | 19 | 3,325,728 |
| 2024-09-27 | 1 | 12 | 3,245,817 |

**Q7c. 2024: latest-amendment 24/48-hour rows against their spender's period_end, and the ladder  (0 s)**

| timing | grp | rows | dollars | rows_matched | dollars_matched | matched_share |
|---|---|---|---|---|---|---|
| after period_end | committee | 2 | 25,279 | 0 |  |  |
| after period_end | type I | 35 | 3,454 | 0 |  |  |
| no period_end | absent | 9 | 33,921,078,677 | 0 |  |  |
| no period_end | committee | 31 | 9,979,516,811 | 0 |  |  |
| no period_end | type I | 25 | 980,019 | 0 |  |  |
| on or before | committee | 51,806 | 4,352,271,651 | 44,236 | 4,242,705,340 | 97.48% |
| on or before | type I | 9,518 | 85,223,206 | 9,139 | 80,282,712 | 94.20% |

**Q7d. 2024: rows after period_end by week of their date  (0 s)**

| week | rows | dollars | dollars_matched |
|---|---|---|---|
| 2024-12-30 | 2 | 25,279 |  |
| 2024-10-28 | 24 | 2,428 |  |
| 2024-10-21 | 5 | 284 |  |
| 2024-10-14 | 2 | 213 |  |
| 2024-10-07 | 2 | 300 |  |
| 2024-09-30 | 2 | 229 |  |

**Q7e. 2024: the decision: rows after period_end, and how much of them pas2 already holds  (0 s)**

| rows | dollars | dollars_already_in_pas2 | share_already_in_pas2 | dollars_rule_would_add | spenders |
|---|---|---|---|---|---|
| 37 | 28,732 |  |  | 28,732 | 2 |

**Q7f. 2024: rows after period_end, the 15 largest spenders  (0 s)**

| spe | name | grp | period_end | rows | dollars | matched | latest |
|---|---|---|---|---|---|---|---|
| C00893198 | CONSERVATIVE FIGHTER PAC | committee | 2024-11-25 | 2 | 25,279 |  | 2024-12-30 |
| C90018771 | FORFACT LLC | type I | 2024-09-30 | 35 | 3,454 |  | 2024-11-03 |

```text
source dates: {2024: {'cm': '2026-11-23', 'cn': '2026-11-23', 'ccl': '2026-11-23', 'oth': '2026-11-23', 'pas2': '2026-11-23', 'webk': '2026-11-23', 'indiv': '2026-11-23', 'oppexp': '2026-11-22', 'weball': '2026-11-23', 'committee_summary': '2026-11-23'}, 2026: {'cm': '2026-11-23', 'cn': '2026-11-23', 'ccl': '2026-11-23', 'oth': '2026-11-23', 'pas2': '2026-11-23', 'webk': '2026-11-23', 'indiv': '2026-11-23', 'oppexp': '2026-11-23', 'weball': '2026-11-23', 'committee_summary': '2026-11-23'}}
```

**2026, live.** `pas226.zip` was last modified on 22 November. Its latest 24A/24E rows are a
monthly filer's (`M12`, to 2026-11-21) and the pre-general report's run to 2026-10-14 (Q7a). 623
spenders' `reported_total.period_end` is 2026-10-14, which confirms §3's pre-general close. The
3 December post-general deadline is not in any file read here, so it is neither confirmed nor
corrected. Q7 ran on 24 November, before it either way. Rows dated
after their spender's `period_end` hold $1,287,474,092 from 512 spenders, nearly all from the
last three weeks of October (Q7d). `pas2` already holds 0.46% of them by the ladder, against 69%
and 87% of the rows dated on or before it (Q7c).

**Decision line:** 0.46% is under §1.1's 1% timeliness bar, so **a timeliness rule is stated**.
A spender's latest-amendment 24/48-hour rows dated after its `reported_total.period_end` are added
until a periodic report covers them. On 2026 today it adds **$1,281,571,904**. A spender with no
`period_end` falls to Q6's rule, which screens out 2026's own hoaxes ($38,524,001,200 from five
spenders `cm` lacks). On 2024 the rule adds $28,732 from two spenders, as expected with every
report filed. Both builds read `committee_summary` and `pas2` of the same day (2026-11-23).

## Q8: communication costs (2024)

```python
# Q8: communication costs (2024): the CSV against pas2's 24F/24N rows.
cc_table(2024)
bulk("pas2", 2024)
silver("independent_expenditure", 2024)
silver("reported_total", 2024)
con.execute("""
CREATE TABLE pc AS
SELECT b.SUB_ID AS sid, trim(b.CMTE_ID) AS filer, b.FILE_NUM AS fnum, nullif(trim(b.TRAN_ID), '') AS tran,
    b.TRANSACTION_TP AS tp, b.TRANSACTION_AMT AS amt, b.MEMO_CD AS memo_cd, nullif(trim(b.CAND_ID), '') AS cand,
    b.SUB_ID IN (SELECT source_record_id FROM silver_2024.independent_expenditure WHERE kind = 'communication_cost') AS in_silver
FROM pas2_published_2024 AS b WHERE b.TRANSACTION_TP IN ('24F', '24N')""")

show("Q8a. pas2's 24F/24N rows: memo lines, repeats, silver", """
SELECT tp, memo_cd, in_silver, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT filer) AS filers
FROM pc GROUP BY ALL ORDER BY ALL""")
show("Q8b. The CSV against pas2_published 24F/24N by SUB_ID", """
SELECT CASE WHEN p.sid IS NULL THEN 'only in the CSV' WHEN c.sid IS NULL THEN 'only in pas2'
            WHEN c.amt = p.amt THEN 'in both, amounts equal' ELSE 'in both, amounts differ' END AS bucket,
    count(*) AS rows, sum(c.amt) AS csv_dollars, sum(p.amt) AS pas2_dollars
FROM cc_2024 AS c FULL JOIN pc AS p ON p.sid = c.sid GROUP BY ALL ORDER BY ALL""")
show("Q8c. In both: the other columns", """
SELECT c.TRANSACTION_TP = p.tp AS same_tp, c.filer = p.filer AS same_filer, c.fnum = p.fnum AS same_file_num,
    c.tran IS NOT DISTINCT FROM p.tran AS same_tran_id, nullif(trim(c.CAND_ID), '') IS NOT DISTINCT FROM p.cand AS same_candidate,
    count(*) AS rows, sum(c.amt) AS dollars
FROM cc_2024 AS c JOIN pc AS p ON p.sid = c.sid GROUP BY ALL ORDER BY ALL""")
show("Q8d. What SUB_ID left, matched by (CMTE_ID, FILE_NUM, TRAN_ID)", """
WITH c AS (SELECT * FROM cc_2024 WHERE sid NOT IN (SELECT sid FROM pc)),
     p AS (SELECT * FROM pc WHERE sid NOT IN (SELECT sid FROM cc_2024))
SELECT CASE WHEN p.sid IS NULL THEN 'only in the CSV' WHEN c.sid IS NULL THEN 'only in pas2' ELSE 'matched' END AS bucket,
    count(*) AS rows, sum(c.amt) AS csv_dollars, sum(p.amt) AS pas2_dollars
FROM c FULL JOIN p ON p.filer = c.filer AND p.fnum = c.fnum AND p.tran = c.tran GROUP BY ALL ORDER BY ALL""")
show("Q8e. Rows in one source only, listed", """
SELECT 'only in the CSV' AS side, c.filer, c.CMTE_NM AS name, c.fnum, c.tran, c.sid::VARCHAR AS sid, c.TRANSACTION_TP AS tp, c.amt, c.dt::VARCHAR AS dt
FROM cc_2024 AS c WHERE c.sid NOT IN (SELECT sid FROM pc)
UNION ALL
SELECT 'only in pas2', p.filer, (SELECT cmte_nm FROM grp_2024 WHERE id = p.filer), p.fnum, p.tran, p.sid::VARCHAR, p.tp, p.amt, p.memo_cd
FROM pc AS p WHERE p.sid NOT IN (SELECT sid FROM cc_2024)
ORDER BY side, amt DESC""")
show("Q8f. Filers by group and cm type", """
SELECT grp, cmte_tp, left(filer, 2) AS prefix, count(DISTINCT filer) AS filers, count(*) AS rows, sum(amt) AS dollars
FROM cc_2024 GROUP BY ALL ORDER BY ALL""")
show("Q8g. SUPPORT_OPPOSE_IND against TRANSACTION_TP", """
SELECT TRANSACTION_TP, SUPPORT_OPPOSE_IND, count(*) AS rows, sum(amt) AS dollars FROM cc_2024 GROUP BY ALL ORDER BY ALL""")
show("Q8h. COMMUNICATION_TP and COMMUNICATION_CLASS", """
SELECT COMMUNICATION_TP, COMMUNICATION_CLASS, count(*) AS rows, sum(amt) AS dollars FROM cc_2024 GROUP BY ALL ORDER BY dollars DESC""")
show("Q8i. PURPOSE filled", """
SELECT PURPOSE IS NOT NULL AS purpose_filled, count(*) AS rows, sum(amt) AS dollars FROM cc_2024 GROUP BY ALL""")
show("Q8j. The 20 largest filers, with silver's counted communication cost", """
SELECT filer, any_value(CMTE_NM) AS name, count(*) AS rows, sum(amt) AS csv_dollars,
    (SELECT sum(amount) FROM silver_2024.independent_expenditure AS s WHERE s.committee_id = cc.filer AND s.kind = 'communication_cost') AS silver_dollars
FROM cc_2024 AS cc GROUP BY 1 ORDER BY csv_dollars DESC LIMIT 20""")
show("Q8k. Silver's communication_cost rows against the CSV", """
SELECT s.source_record_id IN (SELECT sid FROM cc_2024) AS in_csv, count(*) AS rows, sum(amount) AS dollars,
    count(*) FILTER (WHERE candidate_id IS NULL) AS no_candidate
FROM silver_2024.independent_expenditure AS s WHERE kind = 'communication_cost' GROUP BY ALL""")
show("Q8l. In both with amounts that differ: is pas2 the CSV amount rounded, or with its cents dropped?", """
SELECT CASE WHEN abs(c.amt - p.amt) < 1 THEN 'under $1' ELSE '$1 or more' END AS difference,
    c.amt = round(c.amt) AS csv_whole_dollars, p.amt = round(p.amt) AS pas2_whole_dollars,
    round(c.amt) = p.amt AS pas2_is_csv_rounded, trunc(c.amt) = p.amt AS pas2_is_csv_truncated, count(*) AS rows, sum(c.amt) AS csv_dollars, sum(p.amt) AS pas2_dollars,
    max(abs(c.amt - p.amt)) AS largest_gap
FROM cc_2024 AS c JOIN pc AS p ON p.sid = c.sid WHERE c.amt <> p.amt GROUP BY ALL ORDER BY ALL""")
show("Q8m. The CSV's TRANSACTION_AMT as served: with a decimal point or not", """
SELECT TRANSACTION_AMT LIKE '%.%' AS has_decimal_point, count(*) AS rows FROM cc_2024 GROUP BY ALL""")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/CommunicationCosts_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:07 GMT | bytes 237,322 | downloaded 2026-11-24T02:07:00+00:00
ccraw_2024: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
```

**Q8a. pas2's 24F/24N rows: memo lines, repeats, silver  (0 s)**

| tp | memo_cd | in_silver | rows | dollars | filers |
|---|---|---|---|---|---|
| 24F |  | True | 708 | 7,101,055 | 9 |
| 24N |  | True | 91 | 56,932 | 3 |

**Q8b. The CSV against pas2_published 24F/24N by SUB_ID  (0 s)**

| bucket | rows | csv_dollars | pas2_dollars |
|---|---|---|---|
| in both, amounts differ | 437 | 5,040,964 | 5,040,745 |
| in both, amounts equal | 342 | 2,057,762 | 2,057,762 |
| only in pas2 | 20 |  | 59,480 |

**Q8c. In both: the other columns  (0 s)**

| same_tp | same_filer | same_file_num | same_tran_id | same_candidate | rows | dollars |
|---|---|---|---|---|---|---|
| True | True | True | True | True | 779 | 7,098,726 |

**Q8d. What SUB_ID left, matched by (CMTE_ID, FILE_NUM, TRAN_ID)  (0 s)**

| bucket | rows | csv_dollars | pas2_dollars |
|---|---|---|---|
| only in pas2 | 20 |  | 59,480 |

**Q8e. Rows in one source only, listed  (0 s)**

| side | filer | name | fnum | tran | sid | tp | amt | dt |
|---|---|---|---|---|---|---|---|---|
| only in pas2 | C70002563 | NATIONAL ASSOCIATION OF REALTORS | 1,798,486 | E67E19A5CC5B24BECBA3 | 4072920241979962008 | 24F | 14,944 |  |
| only in pas2 | C70002563 | NATIONAL ASSOCIATION OF REALTORS | 1,826,542 | E534778377DFA4BA2B4F | 4111920241070315039 | 24F | 8,583 |  |
| only in pas2 | C70002563 | NATIONAL ASSOCIATION OF REALTORS | 1,868,572 | EA274BE689A794526BA5 | 4013120251139357112 | 24F | 7,787 |  |
| only in pas2 | C70002563 | NATIONAL ASSOCIATION OF REALTORS | 1,798,486 | E70CB3E388C3F4E26B6B | 4072920241979962019 | 24F | 7,100 |  |
| only in pas2 | C70001979 | INTERNATIONAL BROTHERHOOD OF TEAMSTERS | -1,104,451 |  | 1091820230265311352 | 24F | 6,715 |  |
| only in pas2 | C70006358 | ENVIRONMENTAL DEFENSE ACTION FUND | 1,840,525 | F76.4249 | 4120920241075170021 | 24F | 2,292 |  |
| only in pas2 | C70002472 | AMERICAN FEDERATION OF TEACHERS, AFL-CIO | 1,873,964 | F76.4487 | 4020520251142543063 | 24N | 2,116 |  |
| only in pas2 | C70006358 | ENVIRONMENTAL DEFENSE ACTION FUND | 1,828,672 | F76.4223 | 4103020241011356013 | 24F | 2,037 |  |
| only in pas2 | C70002563 | NATIONAL ASSOCIATION OF REALTORS | 1,798,486 | E6802D49030D940AAAC8 | 4072920241979962007 | 24F | 1,800 |  |
| only in pas2 | C70006358 | ENVIRONMENTAL DEFENSE ACTION FUND | 1,840,525 | F76.4248 | 4120920241075170013 | 24F | 1,783 |  |
| only in pas2 | C70006358 | ENVIRONMENTAL DEFENSE ACTION FUND | 1,828,672 | F76.4222 | 4103020241011356007 | 24F | 1,650 |  |
| only in pas2 | C70006358 | ENVIRONMENTAL DEFENSE ACTION FUND | 1,840,525 | F76.4281 | 4120920241075170014 | 24F | 623 |  |
| only in pas2 | C70002563 | NATIONAL ASSOCIATION OF REALTORS | 1,826,542 | E0C070F2D9BD74790853 | 4111920241070315028 | 24F | 600 |  |
| only in pas2 | C70002563 | NATIONAL ASSOCIATION OF REALTORS | 1,868,572 | EAD6346AB001045F6B42 | 4013120251139357141 | 24F | 600 |  |
| only in pas2 | C70002563 | NATIONAL ASSOCIATION OF REALTORS | 1,798,486 | EEECAB71E956349B9A0B | 4072920241979962021 | 24F | 600 |  |
| only in pas2 | C70002472 | AMERICAN FEDERATION OF TEACHERS, AFL-CIO | 1,873,964 | F76.4448 | 4020520251142543066 | 24F | 250 |  |
| only in pas2 | C70004874 | AFSCME COUNCIL 13 | 1,822,192 | F76.4135 | 4101020242069365010 | 24N | 0 |  |
| only in pas2 | C70004874 | AFSCME COUNCIL 13 | 1,835,015 | F76.4128 | 4112120241071690022 | 24N | 0 |  |
| only in pas2 | C70004874 | AFSCME COUNCIL 13 | 1,861,731 | F76.4134 | 4012320251133620011 | 24N | 0 |  |
| only in pas2 | C70004874 | AFSCME COUNCIL 13 | 1,796,076 | F76.4135 | 4071220241972799010 | 24N | 0 |  |

**Q8f. Filers by group and cm type  (0 s)**

| grp | cmte_tp | prefix | filers | rows | dollars |
|---|---|---|---|---|---|
| committee | C | C7 | 9 | 779 | 7,098,726 |

**Q8g. SUPPORT_OPPOSE_IND against TRANSACTION_TP  (0 s)**

| TRANSACTION_TP | SUPPORT_OPPOSE_IND | rows | dollars |
|---|---|---|---|
| 24F | 24F | 6 | 6,226 |
| 24F | S | 687 | 7,037,654 |
| 24N | O | 86 | 54,846 |

**Q8h. COMMUNICATION_TP and COMMUNICATION_CLASS  (0 s)**

| COMMUNICATION_TP | COMMUNICATION_CLASS | rows | dollars |
|---|---|---|---|
| DM | M | 534 | 6,134,353 |
| O | M | 230 | 905,196 |
| DM | E | 1 | 51,715 |
| M | M | 5 | 5,524 |
| O | E | 8 | 1,236 |
| L | M | 1 | 703 |

**Q8i. PURPOSE filled  (0 s)**

| purpose_filled | rows | dollars |
|---|---|---|
| False | 779 | 7,098,726 |

**Q8j. The 20 largest filers, with silver's counted communication cost  (0 s)**

| filer | name | rows | csv_dollars | silver_dollars |
|---|---|---|---|---|
| C70002563 | NATIONAL ASSOCIATION OF REALTORS | 448 | 4,081,900 | 4,123,808 |
| C70002472 | AMERICAN FEDERATION OF TEACHERS, AFL-CIO | 107 | 1,961,062 | 1,963,378 |
| C70003124 | SERVICE EMPLOYEES INTERNATIONAL UNION | 25 | 461,130 | 461,117 |
| C70004874 | AFSCME COUNCIL 13 | 72 | 304,989 | 304,987 |
| C70004676 | SUSAN B ANTHONY LIST INC DBA SUSAN B ANTHONY PRO-LIFE AMERICA | 68 | 159,464 | 159,433 |
| C70006358 | ENVIRONMENTAL DEFENSE ACTION FUND | 51 | 123,144 | 131,516 |
| C70004569 | HUMAN RIGHTS CAMPAIGN | 5 | 5,524 | 5,521 |
| C70006176 | UFCW LOCAL 1776KS | 2 | 810 | 810 |
| C70001979 | INTERNATIONAL BROTHERHOOD OF TEAMSTERS | 1 | 703 | 7,417 |

**Q8k. Silver's communication_cost rows against the CSV  (0 s)**

| in_csv | rows | dollars | no_candidate |
|---|---|---|---|
| True | 779 | 7,098,507 | 0 |
| False | 20 | 59,480 | 20 |

**Q8l. In both with amounts that differ: is pas2 the CSV amount rounded, or with its cents dropped?  (0 s)**

| difference | csv_whole_dollars | pas2_whole_dollars | pas2_is_csv_rounded | pas2_is_csv_truncated | rows | csv_dollars | pas2_dollars | largest_gap |
|---|---|---|---|---|---|---|---|---|
| under $1 | False | True | False | True | 234 | 2,370,442 | 2,370,272 | 1 |
| under $1 | False | True | True | True | 203 | 2,670,522 | 2,670,473 | 0 |

**Q8m. The CSV's TRANSACTION_AMT as served: with a decimal point or not  (0 s)**

| has_decimal_point | rows |
|---|---|
| False | 342 |
| True | 437 |

**`SUB_ID` is the same for one communication cost in `pas2` and the CSV** (§3's assertion,
confirmed): all 779 CSV rows are `pas2` 24F/24N rows under their `SUB_ID`, with the same
transaction type, filer, filing, `TRAN_ID` and candidate (Q8c). 342 amounts are equal. 437 differ
by under $1: the CSV has cents and `pas2` drops them: every one is the CSV's amount truncated (Q8l–m). `pas2` holds 20 rows the CSV lacks,
$59,480, all without a candidate. One is a Teamsters paper filing (`FILE_NUM` −1104451), and four
are AFSCME $0 lines. No 24F/24N line is a memo line. The filers are 9 `C7` committees (`cm` type
`C`). `COMMUNICATION_TP` is direct mail (`DM`) for $6.19M, and `COMMUNICATION_CLASS` is `M` for
$7.05M. No file read here carries Form 7's reported total, so each filer's sum is unchecked.

**Decision line:** the CSV's rows and dollars are 100% `pas2` rows by `SUB_ID` with amounts equal
once the CSV's cents are dropped, in 2024 and in every cycle 2010–2026 (Q12g). That meets §1.1's 99% bar, with
"equal" read as equal to the dollar, because `pas2` drops cents. That reading is this document's, and
NEU-2163 confirms it. **The source is `pas2`**: silver's
`communication_cost` rows, 799 rows, **$7,157,987** in 2024. The CSV supplies
`COMMUNICATION_TP`, `COMMUNICATION_CLASS` and the cents by `SUB_ID`. NEU-2167's definition of done
is within 1% of $7,157,987.

## Q9: electioneering communications (2024)

```python
# Q9 prep: the sponsors whose Form 9s Q9 reads, written to the work directory for f9.sh, which
# fetches them from OpenFEC on the VM host (the container's address had spent DEMO_KEY's quota).
REPEAT = "spon, PAYEE_NAME, DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, CANDIDATE_ID"
counts = {}
for cycle in range(2010, 2027, 2):
    ec_table(cycle)
    counts[cycle] = con.execute(f"""SELECT count(*) FROM (SELECT 1 FROM ec_{cycle} GROUP BY {REPEAT}
        HAVING count(DISTINCT SB_IMAGE_NUM) > 1)""").fetchone()[0]
print("repeat groups by cycle:", counts)
most = max((c for c in counts if c != 2024), key=lambda c: counts[c])
lists = {
    2024: [r[0] for r in con.execute("SELECT DISTINCT spon FROM ec_2024 ORDER BY 1").fetchall()],
    most: [r[0] for r in con.execute(f"""SELECT DISTINCT spon FROM (SELECT spon, sum(share) AS d FROM ec_{most}
        GROUP BY {REPEAT} HAVING count(DISTINCT SB_IMAGE_NUM) > 1 ORDER BY d DESC LIMIT 20) ORDER BY 1""").fetchall()],
}
for cycle, ids in lists.items():
    (work / f"f9-sponsors-{cycle}.txt").write_text(" ".join(ids))
    print(cycle, len(ids), " ".join(ids))
```

```text
https://www.fec.gov/files/bulk-downloads/2010/ElectioneeringComm_2010.csv | Last-Modified: Mon, 23 Nov 2026 10:12:09 GMT | bytes 160,783 | downloaded 2026-11-24T02:37:14+00:00
ecraw_2010: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2012/ElectioneeringComm_2012.csv | Last-Modified: Mon, 23 Nov 2026 10:12:10 GMT | bytes 75,779 | downloaded 2026-11-24T02:37:15+00:00
ecraw_2012: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2014/ElectioneeringComm_2014.csv | Last-Modified: Mon, 23 Nov 2026 10:12:11 GMT | bytes 10,506 | downloaded 2026-11-24T02:37:16+00:00
ecraw_2014: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2016/ElectioneeringComm_2016.csv | Last-Modified: Mon, 23 Nov 2026 10:12:12 GMT | bytes 27,703 | downloaded 2026-11-24T02:37:18+00:00
ecraw_2016: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2018/ElectioneeringComm_2018.csv | Last-Modified: Mon, 23 Nov 2026 10:12:13 GMT | bytes 51,662 | downloaded 2026-11-24T02:37:19+00:00
ecraw_2018: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2020/ElectioneeringComm_2020.csv | Last-Modified: Mon, 23 Nov 2026 10:12:14 GMT | bytes 71,074 | downloaded 2026-11-24T02:37:20+00:00
ecraw_2020: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2022/ElectioneeringComm_2022.csv | Last-Modified: Mon, 23 Nov 2026 10:12:15 GMT | bytes 11,977 | downloaded 2026-11-24T02:37:21+00:00
ecraw_2022: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:10:51+00:00
ecraw_2024: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2026/ElectioneeringComm_2026.csv | Last-Modified: Mon, 23 Nov 2026 10:12:17 GMT | bytes 13,079 | downloaded 2026-11-24T02:37:23+00:00
ecraw_2026: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
repeat groups by cycle: {2010: 20, 2012: 12, 2014: 1, 2016: 3, 2018: 1, 2020: 5, 2022: 0, 2024: 2, 2026: 3}
2024 25 C30001978 C30002430 C30002851 C30002885 C30003354 C30003362 C30003370 C30003388 C30003396 C30003404 C30003412 C30003420 C30003438 C30003446 C30003453 C30003461 C30003479 C30003487 C30003495 C30003503 C30003511 C30003529 C30003537 C30003552 C30003560
2010 4 C30000814 C30001101 C30001564 C30001648
```

```python
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlencode

# Q9: electioneering communications (2024), with each sponsor's Form 9 filings from OpenFEC.
ec_table(2024)
bulk("cn", 2024)
silver("candidate", 2024)
DISB = "spon, SB_IMAGE_NUM, PAYEE_NAME, DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT"
REPEAT = "spon, PAYEE_NAME, DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, CANDIDATE_ID"

show("Q9a. Rows, disbursements, dollars, sponsors", f"""
SELECT count(*) AS rows, count(DISTINCT ({DISB})) AS disbursements, sum(share) AS share_dollars,
    (SELECT sum(amt) FROM (SELECT DISTINCT {DISB}, amt FROM ec_2024)) AS disbursement_dollars,
    count(DISTINCT spon) AS sponsors FROM ec_2024""")
show("Q9b. Sponsors by group, cm type and id prefix", """
SELECT grp, cmte_tp, left(spon, 2) AS prefix, count(DISTINCT spon) AS sponsors, count(*) AS rows, sum(share) AS share_dollars
FROM ec_2024 GROUP BY ALL ORDER BY ALL""")
show("Q9c. Every sponsor", """
SELECT spon, any_value(COMMITTEE_NAME) AS name, grp, count(*) AS rows, sum(share) AS share_dollars,
    count(*) FILTER (WHERE cand IS NULL) AS blank_candidate_rows, count(DISTINCT SB_IMAGE_NUM) AS images
FROM ec_2024 GROUP BY spon, grp ORDER BY share_dollars DESC""")
show("Q9d. Blank CANDIDATE_ID: by sponsor and description", """
SELECT spon, any_value(COMMITTEE_NAME) AS name, DISBURSEMENT_DESCRIPTION, count(*) AS rows, sum(share) AS share_dollars,
    min(ddt) AS first, max(ddt) AS last
FROM ec_2024 WHERE cand IS NULL GROUP BY ALL ORDER BY share_dollars DESC""")
show("Q9e. Named candidates: in cn, a candidate of the cycle, with a race", """
SELECT e.cand, any_value(e.CANDIDATE_NAME) AS name, any_value(e.CANDIDATE_OFFICE) AS office, any_value(e.CANDIDATE_STATE) AS state,
    e.cand IN (SELECT trim(CAND_ID) FROM cn_2024) AS in_cn, any_value(c.candidate_id) IS NOT NULL AS candidate_of_cycle,
    any_value(c.race_id) AS race_id, count(*) AS rows, sum(e.share) AS share_dollars
FROM ec_2024 AS e LEFT JOIN silver_2024.candidate AS c ON c.candidate_id = coalesce(
    (SELECT alias_of FROM silver_2024.candidate AS a WHERE a.candidate_id = e.cand), e.cand)
WHERE e.cand IS NOT NULL GROUP BY e.cand ORDER BY share_dollars DESC""")
show("Q9f. The split: share × NUMBER_OF_CANDIDATES against the amount, and rows per disbursement", f"""
WITH d AS (SELECT {DISB}, any_value(ncand) AS ncand, count(*) AS n, sum(share) AS shares, any_value(amt) AS amt,
               bool_and(abs(share * ncand - amt) <= 0.01) AS split_ok
           FROM ec_2024 GROUP BY ALL)
SELECT ncand, n AS rows_per_disbursement, split_ok, abs(shares - amt) <= 0.01 * ncand AS shares_sum_to_amount,
    count(*) AS disbursements, sum(amt) AS dollars
FROM d GROUP BY ALL ORDER BY ALL""")
show("Q9g. Multi-candidate share", """
SELECT ncand > 1 AS multi_candidate, count(*) AS rows, sum(share) AS share_dollars,
    (sum(share) / (SELECT sum(share) FROM ec_2024))::DOUBLE AS share_of_dollars FROM ec_2024 GROUP BY ALL""")
con.execute(f"""
CREATE TABLE rg AS
SELECT {REPEAT}, count(*) AS rows, count(DISTINCT SB_IMAGE_NUM) AS images, list(SB_IMAGE_NUM ORDER BY SB_IMAGE_NUM) AS image_nums,
    sum(share) AS share_dollars
FROM ec_2024 GROUP BY ALL HAVING count(DISTINCT SB_IMAGE_NUM) > 1""")
show("Q9h. Repeat groups (§2): count, rows, dollars", """
SELECT count(*) AS groups, sum(rows) AS rows, sum(share_dollars) AS share_dollars FROM rg""")
show("Q9i. Fully identical rows (every column, the image number too)", """
SELECT trim(COMMITTEE_ID) AS spon, SB_IMAGE_NUM, PAYEE_NAME, DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, CANDIDATE_ID,
    NUMBER_OF_CANDIDATES, count(*) AS copies
FROM ecraw_2024 GROUP BY ALL HAVING count(*) > 1""")
# Each 2024 sponsor's Form 9 filings, from OpenFEC (docquery's forms listing answers 403). Cached in
# work so a re-run makes no new request.
API = "https://api.open.fec.gov/v1/filings/"


def form9s(sponsors: list[str], cycle: int) -> list[dict]:
    """Every Form 9 of `sponsors` in `cycle`, in as few requests as OpenFEC allows: one query
    names every sponsor (DEMO_KEY allows 30 requests an hour)."""
    cache = work / f"f9-{cycle}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    out, page = [], 1
    while True:
        q = urlencode([("committee_id", s) for s in sponsors] + [
            ("form_type", "F9"), ("cycle", cycle), ("per_page", 100), ("page", page),
            ("api_key", "DEMO_KEY"), ("sort", "receipt_date")])
        for attempt in range(6):
            try:
                with urlopen(Request(f"{API}?{q}", headers={"User-Agent": USER_AGENT})) as r:
                    body = json.load(r)
                break
            except HTTPError as e:  # DEMO_KEY allows 10 requests a window: wait it out
                if e.code != 429 or attempt == 5:
                    raise
                time.sleep(65)
        out += body["results"]
        if page >= body["pagination"]["pages"]:
            break
        page += 1
    cache.write_text(json.dumps(out))
    print(f"OpenFEC: {page} request(s), {len(out)} filings, {dt.datetime.now(dt.UTC).isoformat(timespec='seconds')}")
    return out


def load_form9s(cycle: int, sponsors: list[str]) -> None:
    rows = []
    for f in form9s(sponsors, cycle):
        rows.append((f["committee_id"], f["file_number"], f["amendment_indicator"], f.get("is_amended"), f.get("most_recent"),
                     f.get("most_recent_file_number"), json.dumps(f.get("amendment_chain") or []),
                     f.get("beginning_image_number"), f.get("ending_image_number"), f.get("receipt_date"),
                     f.get("means_filed"), f.get("document_description")))
    con.execute(f"""CREATE OR REPLACE TABLE f9_{cycle} (spon VARCHAR, file_num BIGINT, amndt VARCHAR, is_amended BOOLEAN,
        most_recent BOOLEAN, most_recent_file_num BIGINT, chain VARCHAR, begin_image VARCHAR, end_image VARCHAR,
        received VARCHAR, means VARCHAR, description VARCHAR)""")
    con.executemany(f"INSERT INTO f9_{cycle} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    print(f"Form 9 filings read for {cycle}: {len(rows)} from {len(sponsors)} sponsors, {API}?committee_id=<id>&form_type=F9&cycle={cycle}")


def ec_filings(cycle: int) -> None:
    """`ecf_<cycle>`: each electioneering row with the Form 9 whose image range holds its SB_IMAGE_NUM."""
    con.execute(f"""
    CREATE OR REPLACE TABLE ecf_{cycle} AS
    SELECT e.*, f.file_num, f.amndt, f.is_amended, f.most_recent, f.most_recent_file_num, f.chain, f.means
    FROM ec_{cycle} AS e LEFT JOIN f9_{cycle} AS f
        ON f.spon = e.spon AND TRY_CAST(e.SB_IMAGE_NUM AS HUGEINT) BETWEEN TRY_CAST(f.begin_image AS HUGEINT)
            AND TRY_CAST(f.end_image AS HUGEINT)""")


sponsors = [r[0] for r in con.execute("SELECT DISTINCT spon FROM ec_2024 ORDER BY 1").fetchall()]
load_form9s(2024, sponsors)
ec_filings(2024)
show("Q9j. 2024 Form 9 filings by sponsor: amendment indicator, superseded or not", """
SELECT spon, amndt, is_amended, most_recent, count(*) AS filings FROM f9_2024 GROUP BY ALL ORDER BY ALL""")
show("Q9k. Electioneering rows by the Form 9 they are on: found, amended, most recent", """
SELECT file_num IS NOT NULL AS filing_found, amndt, is_amended, most_recent, count(*) AS rows, sum(share) AS share_dollars,
    count(DISTINCT file_num) AS filings
FROM ecf_2024 GROUP BY ALL ORDER BY ALL""")


def read_groups(cycle: int, title: str, limit: int = 1000) -> None:
    show(title, f"""
    WITH r AS (SELECT {REPEAT}, sum(share) AS share_dollars, count(*) AS rows FROM ec_{cycle}
               GROUP BY ALL HAVING count(DISTINCT SB_IMAGE_NUM) > 1 ORDER BY share_dollars DESC LIMIT {limit}),
    g AS (
        SELECT r.spon, r.PAYEE_NAME, r.DISBURSEMENT_DATE, r.REPORTED_DISBURSEMENT_AMOUNT AS amount, r.CANDIDATE_ID,
            r.rows, r.share_dollars,
            list(DISTINCT e.file_num ORDER BY e.file_num) AS filings, list(DISTINCT e.amndt ORDER BY e.amndt) AS amndts,
            list(DISTINCT e.most_recent_file_num ORDER BY e.most_recent_file_num) AS latest_of_each,
            count(DISTINCT e.file_num) AS n_filings, count(e.file_num) AS rows_on_a_found_filing
        FROM r JOIN ecf_{cycle} AS e USING (spon, PAYEE_NAME, DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT)
        WHERE e.CANDIDATE_ID IS NOT DISTINCT FROM r.CANDIDATE_ID GROUP BY ALL)
    SELECT *, CASE WHEN rows_on_a_found_filing < rows THEN 'a row on no filing OpenFEC lists'
                   WHEN n_filings = 1 THEN 'two lines on one filing'
                   WHEN len(latest_of_each) = 1 THEN 'restatement: one amendment chain'
                   ELSE 'separate filings, not one chain' END AS reading
    FROM g ORDER BY share_dollars DESC""")


read_groups(2024, "Q9l. Every 2024 repeat group, its rows' filings, and what they are")
show("Q9m. 2024 rows on a superseded Form 9 (not the most recent of its chain), whatever their key", """
SELECT most_recent, count(*) AS rows, sum(share) AS share_dollars, count(DISTINCT file_num) AS filings,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM ecf_2024 AS y WHERE y.file_num = x.most_recent_file_num
        AND y.PAYEE_NAME = x.PAYEE_NAME AND y.REPORTED_DISBURSEMENT_AMOUNT = x.REPORTED_DISBURSEMENT_AMOUNT
        AND y.CANDIDATE_ID IS NOT DISTINCT FROM x.CANDIDATE_ID)) AS rows_restated_on_the_latest
FROM ecf_2024 AS x WHERE file_num IS NOT NULL GROUP BY ALL""")

# §1.1's fallback: 2024 holds fewer than 5 repeat groups, so the profiled cycle with the most is
# read too, its 20 largest groups against their Form 9s.
counts = {}
for cycle in range(2010, 2027, 2):
    if cycle != 2024:
        ec_table(cycle)
    counts[cycle] = con.execute(f"""SELECT count(*) FROM (SELECT 1 FROM ec_{cycle} GROUP BY {REPEAT}
        HAVING count(DISTINCT SB_IMAGE_NUM) > 1)""").fetchone()[0]
print("\nrepeat groups by cycle:", counts)
most = max(counts, key=lambda c: counts[c])
top = [r[0] for r in con.execute(f"""SELECT DISTINCT spon FROM (SELECT spon, sum(share) AS d FROM ec_{most}
    GROUP BY {REPEAT} HAVING count(DISTINCT SB_IMAGE_NUM) > 1 ORDER BY d DESC LIMIT 20)""").fetchall()]
load_form9s(most, top)
ec_filings(most)
read_groups(most, f"Q9n. {most}, the cycle with the most repeat groups: its 20 largest against their Form 9s", 20)
show(f"Q9o. {most}: those sponsors' rows by whether their Form 9 is the most recent of its chain", f"""
SELECT most_recent, count(*) AS rows, sum(share) AS share_dollars, count(DISTINCT file_num) AS filings
FROM ecf_{most} WHERE spon IN (SELECT spon FROM f9_{most}) GROUP BY ALL""")


def raw_filing(file_num: int) -> list[list[str]]:
    """The electronic filing's lines (split on LF only: str.splitlines would split on 0x1C too),
    fields split on FEC's 0x1C, or on ',' in a format before 6."""
    path = fetch(f"https://docquery.fec.gov/dcdev/posted/{file_num}.fec", f"{file_num}.fec")
    text = path.read_bytes().decode("latin-1")
    lines = [line.rstrip("\r") for line in text.split("\n") if line.strip()]
    if "\x1c" in text:
        return [line.split("\x1c") for line in lines]
    return [next(csv.reader([line])) for line in lines]


def original_of(lines: list[list[str]], file_num: int) -> int:
    """The filing an amendment restates, from its HDR's report id (FEC-<original>); else itself."""
    hdr = next(l for l in lines if l[0].upper() == "HDR")
    rid = next((f for f in hdr if f.upper().startswith("FEC-")), "")
    return int(rid[4:]) if rid[4:].isdigit() else file_num


def read_raw(cycle: int, limit: int) -> None:
    groups = con.execute(f"""
        WITH r AS (SELECT {REPEAT}, sum(share) AS d FROM ec_{cycle} GROUP BY ALL
                   HAVING count(DISTINCT SB_IMAGE_NUM) > 1 ORDER BY d DESC LIMIT {limit})
        SELECT r.spon, r.PAYEE_NAME, r.DISBURSEMENT_DATE, r.REPORTED_DISBURSEMENT_AMOUNT, r.CANDIDATE_ID, r.d,
            list(DISTINCT e.file_num ORDER BY e.file_num) AS filings
        FROM r JOIN ecf_{cycle} AS e USING (spon, PAYEE_NAME, DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT)
        WHERE e.CANDIDATE_ID IS NOT DISTINCT FROM r.CANDIDATE_ID GROUP BY ALL ORDER BY r.d DESC""").fetchall()
    print(f"\n**Q9p. {cycle}: each repeat group read against its raw filings**\n")
    print("| sponsor | payee | date | amount | candidate | filings | form, original (HDR) and F93 lines to the payee | reading |")
    print("|---|---|---|---|---|---|---|---|")
    for spon, payee, date, amount, cand, d, filings in groups:
        notes, originals, f93, covers = [], set(), [], []
        for fnum in filings:
            if fnum is None or fnum <= 0:
                notes.append(f"{fnum}: paper, not read")
                originals.add(fnum)
                continue
            lines = raw_filing(fnum)
            cover = next(l for l in lines if l[0].upper().startswith("F9") and l[0].upper()[:3] not in ("F91", "F92", "F93", "F94"))
            orig = original_of(lines, fnum)
            originals.add(orig)
            key = re.sub(r"[^A-Z0-9]", "", payee.upper())[:10]
            to_payee = [l for l in lines if l[0].upper().startswith("F93")
                        and key in re.sub(r"[^A-Z0-9]", "", " ".join(l).upper())]
            covers.append(tuple(f.upper() for f in cover[16:21]))
            f93.append(len(to_payee))
            notes.append(f"{fnum}: {cover[0]}, of {orig}, cover {' '.join(f for f in cover[16:20] if f)} '{cover[20][:28]}'; F93 " + "; ".join(
                f"{l[17] if len(l) > 17 else ''} {l[19] if len(l) > 19 else ''} {l[20] if len(l) > 20 else ''}".strip()
                for l in to_payee))
        if any(f is None or f <= 0 for f in filings):
            reading = "not read (paper)"
        elif len(filings) == 1:
            reading = "two F93 lines on one filing" if f93 and f93[0] > 1 else "one F93 line, two rows"
        elif len(originals) == 1:
            reading = "restatement (one report and its amendment)"
        elif len(set(covers)) == 1:
            reading = "the same report filed again as new (same cover dates and title, case aside)"
        else:
            reading = "two reports with different covers"
        print(f"| {spon} | {payee} | {date} | {amount} | {cand or ''} | {len(filings)} | {' / '.join(notes)} | {reading} |")


read_raw(2024, 1000)
read_raw(most, 20)

show("Q9q. Two candidate dedup rules on the file alone, by cycle: a repeat group (§2) whose rows also agree on COMMUNICATION_DATE and PUBLIC_DISBURSEMENT_DATE keeps only its highest SB_IMAGE_NUM", " UNION ALL ".join(f"""
SELECT '{c}' AS cycle, count(*) AS rows, sum(share) AS dollars,
    count(*) FILTER (WHERE dup) AS rows_dropped_by_extended_key, sum(share) FILTER (WHERE dup) AS dollars_dropped_by_extended_key,
    count(*) FILTER (WHERE rep) AS rows_dropped_by_file_key, sum(share) FILTER (WHERE rep) AS dollars_dropped_by_file_key
FROM (SELECT share,
        SB_IMAGE_NUM < max(SB_IMAGE_NUM) OVER (PARTITION BY {REPEAT}) AS rep,
        SB_IMAGE_NUM < max(SB_IMAGE_NUM) OVER (PARTITION BY {REPEAT}, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE) AS dup
      FROM ec_{c})""" for c in range(2010, 2027, 2)))
```

```text
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:10:51+00:00
ecraw_2024: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
```

**Q9a. Rows, disbursements, dollars, sponsors  (0 s)**

| rows | disbursements | share_dollars | disbursement_dollars | sponsors |
|---|---|---|---|---|
| 69 | 59 | 9,480,874 | 9,454,306 | 25 |

**Q9b. Sponsors by group, cm type and id prefix  (0 s)**

| grp | cmte_tp | prefix | sponsors | rows | share_dollars |
|---|---|---|---|---|---|
| committee | E | C3 | 25 | 69 | 9,480,874 |

**Q9c. Every sponsor  (0 s)**

| spon | name | grp | rows | share_dollars | blank_candidate_rows | images |
|---|---|---|---|---|---|---|
| C30003412 | PUT NEW HAMPSHIRE FIRST | committee | 4 | 2,856,060 | 0 | 3 |
| C30003404 | SOMOS VOTANTES | committee | 1 | 1,291,930 | 0 | 1 |
| C30002430 | AMERICAN CHEMISTRY COUNCIL INC | committee | 4 | 893,876 | 4 | 4 |
| C30003487 | NO ON 33 CALIFORNIANS FOR RESPONSIBLE HOUSING (FPPC ID# 1421884) | committee | 2 | 810,435 | 0 | 1 |
| C30003370 | BUILDING AMERICA'S FUTURE | committee | 6 | 724,185 | 0 | 2 |
| C30003479 | EVAN LOW FOR ASSEMBLY 2024 | committee | 9 | 590,070 | 0 | 5 |
| C30003446 | WISCONSIN PRINCIPLES INC. | committee | 2 | 454,500 | 2 | 1 |
| C30003560 | VOTE YES FOR A STRONG SOUTH DAKOTA | committee | 2 | 260,482 | 0 | 1 |
| C30003511 | ASSOCIATION OF EQUIPMENT MANUFACTURERS (AEM) | committee | 6 | 205,832 | 0 | 3 |
| C30003529 | KEYSTONE PROSPERITY PAC | committee | 2 | 193,785 | 2 | 1 |
| C30003495 | FAIR FUTURE NC | committee | 2 | 173,000 | 0 | 2 |
| C30002851 | AMERICAN BANKERS ASSOCIATION | committee | 2 | 161,392 | 2 | 2 |
| C30002885 | AMERICAN CIVIL LIBERTIES UNION INC. | committee | 4 | 145,121 | 0 | 1 |
| C30003537 | SAFER NORTH CAROLINA | committee | 2 | 127,272 | 2 | 1 |
| C30003438 | PROTECTING AMERICA INITIATIVE | committee | 2 | 114,500 | 2 | 1 |
| C30003420 | AMERICANS FOR CONSUMER PROTECTION | committee | 2 | 86,466 | 2 | 1 |
| C30003503 | COLORADANS FOR RESPONSIBLE ENERGY DEVELOPMENT | committee | 2 | 80,000 | 2 | 1 |
| C30003461 | ISSUE ONE ACTION | committee | 4 | 67,500 | 0 | 2 |
| C30003453 | FAIR ELECTION FUND | committee | 4 | 66,517 | 4 | 1 |
| C30001978 | PATRIOTIC VETERANS, INC | committee | 1 | 63,000 | 0 | 1 |
| C30003552 | AMERICANS FOR PHARMA REFORM INC. | committee | 1 | 42,000 | 0 | 1 |
| C30003362 | PROTECT U.S. FAMILIES | committee | 1 | 32,000 | 0 | 1 |
| C30003388 | AMERICAN RESOLVE PAC INC. | committee | 1 | 29,500 | 0 | 1 |
| C30003354 | FLORIDA ASSOCIATION OF NURSE ANESTHETISTS DBA FLORIDA ASSOCIATION OF NURSE ANESTHESIOLOGY (FANA) | committee | 1 | 10,000 | 0 | 1 |
| C30003396 | STRAIGHT AHEAD ORGANIZATION | committee | 2 | 1,451 | 2 | 1 |

**Q9d. Blank CANDIDATE_ID: by sponsor and description  (0 s)**

| spon | name | DISBURSEMENT_DESCRIPTION | rows | share_dollars | first | last |
|---|---|---|---|---|---|---|
| C30003446 | WISCONSIN PRINCIPLES INC. | ADVERTISING PLACEMENT - TRUTH BROADCAST TELEVISION AD | 1 | 450,500 | 2024-09-12 | 2024-09-12 |
| C30002430 | AMERICAN CHEMISTRY COUNCIL INC | INTERNET BROADCAST AND CABLE TV ADS: MOST EFFECTIVE | 1 | 323,147 | 2024-05-28 | 2024-05-28 |
| C30002430 | AMERICAN CHEMISTRY COUNCIL INC | INTERNET BROADCAST AND CABLE TV ADS: CHAMPION | 1 | 230,000 | 2024-02-28 | 2024-02-28 |
| C30003529 | KEYSTONE PROSPERITY PAC | TV ADVERTISING - MEDIA PLACEMENT ANARCHY | 1 | 187,785 | 2024-10-09 | 2024-10-09 |
| C30002430 | AMERICAN CHEMISTRY COUNCIL INC | INTERNET BROADCAST AND CABLE TV PUBLICATION OF REP. LEE ADVERTISEMENT. | 1 | 177,953 | 2024-08-06 | 2024-08-06 |
| C30002430 | AMERICAN CHEMISTRY COUNCIL INC | INTERNET BROADCAST AND CABLE TV ADS BARRASSO | 1 | 162,776 | 2024-08-06 | 2024-08-06 |
| C30003537 | SAFER NORTH CAROLINA | TELEVISION ADVERTISING - MEDIA PLACEMENT INCREDIBLE | 1 | 122,772 | 2024-10-09 | 2024-10-09 |
| C30003438 | PROTECTING AMERICA INITIATIVE | TV MEDIA PLACEMENT - OPENED THE DOOR | 1 | 102,000 | 2024-09-06 | 2024-09-06 |
| C30002851 | AMERICAN BANKERS ASSOCIATION | COMMUNITY INVESTMENTS ELECTIONEERING COMMUNICATION - TV | 1 | 99,929 | 2024-10-09 | 2024-10-09 |
| C30003420 | AMERICANS FOR CONSUMER PROTECTION | TV MEDIA PLACEMENT - OUT OF TOUCH | 1 | 66,116 | 2024-09-09 | 2024-09-09 |
| C30002851 | AMERICAN BANKERS ASSOCIATION | FREEDOM ELECTIONEERING COMMUNICATION - RADIO | 1 | 61,463 | 2024-02-21 | 2024-02-21 |
| C30003453 | FAIR ELECTION FUND | TV MEDIA PLACEMENT - PROTECTED | 2 | 52,819 | 2024-09-12 | 2024-09-12 |
| C30003503 | COLORADANS FOR RESPONSIBLE ENERGY DEVELOPMENT | DIGITAL 30 SECONDS VP HARRIS SUPPORTS FRACKING | 1 | 40,000 | 2024-10-08 | 2024-10-08 |
| C30003503 | COLORADANS FOR RESPONSIBLE ENERGY DEVELOPMENT | DIGITAL 15 SECONDS VP HARRIS SUPPORTS FRACKING | 1 | 40,000 | 2024-10-08 | 2024-10-08 |
| C30003420 | AMERICANS FOR CONSUMER PROTECTION | TV MEDIA PRODUCTION - OUT OF TOUCH | 1 | 20,350 | 2024-09-10 | 2024-09-10 |
| C30003453 | FAIR ELECTION FUND | TV MEDIA PRODUCTION - PROTECTED | 2 | 13,698 | 2024-09-13 | 2024-09-13 |
| C30003438 | PROTECTING AMERICA INITIATIVE | TV MEDIA PRODUCTION - OPENED THE DOOR | 1 | 12,500 | 2024-09-06 | 2024-09-06 |
| C30003529 | KEYSTONE PROSPERITY PAC | ADVERTISING - PRODUCTION ANARCHY | 1 | 6,000 | 2024-10-16 | 2024-10-16 |
| C30003537 | SAFER NORTH CAROLINA | ADVERTISING - PRODUCTION INCREDIBLE | 1 | 4,500 | 2024-10-18 | 2024-10-18 |
| C30003446 | WISCONSIN PRINCIPLES INC. | ADVERTISING PRODUCTION - TRUTH BROADCAST TELEVISION AD | 1 | 4,000 | 2024-09-12 | 2024-09-12 |
| C30003396 | STRAIGHT AHEAD ORGANIZATION | PHONE BANKING | 1 | 1,360 | 2024-04-12 | 2024-04-12 |
| C30003396 | STRAIGHT AHEAD ORGANIZATION | SOCIAL MEDIA POSTS | 1 | 91 | 2024-04-11 | 2024-04-11 |

**Q9e. Named candidates: in cn, a candidate of the cycle, with a race  (0 s)**

| cand | name | office | state | in_cn | candidate_of_cycle | race_id | rows | share_dollars |
|---|---|---|---|---|---|---|---|---|
| P80001571 | TRUMP, DONALD J. | P | US | True | True | 2024-P-US-00 | 12 | 3,381,602 |
| P00009423 | HARRIS, KAMALA | P | US | True | True | 2024-P-US-00 | 3 | 2,102,365 |
| P80000722 | BIDEN, JOSEPH R JR | P | US | True | True | 2024-P-US-00 | 6 | 777,245 |
| H4CA16239 | LOW, EVAN | H | CA | True | True | 2024-H-CA-16 | 9 | 590,070 |
| H8IA02043 | MILLER-MEEKS, MARIANNETTE JANE | H | IA | True | True | 2024-H-IA-01 | 3 | 104,298 |
| H6NE02125 | BACON, DONALD J | H | NE | True | True | 2024-H-NE-02 | 3 | 101,534 |
| S4OH00200 | LAROSE, FRANK | S | OH | True | True | 2024-S-OH-00 | 1 | 63,000 |
| S2WI00219 | BALDWIN, TAMMY | S | WI | True | True | 2024-S-WI-00 | 1 | 42,000 |
| H6LA04138 | JOHNSON, JAMES MICHAEL | H | LA | True | True | 2024-H-LA-04 | 2 | 33,750 |
| H0LA01087 | SCALISE, STEVE MR | H | LA | True | True | 2024-H-LA-01 | 2 | 33,750 |
| P60012143 |  |  |  | False | False |  | 1 | 32,000 |
| S4OH00192 | MORENO, BERNIE | S | OH | True | True | 2024-S-OH-00 | 1 | 29,500 |
| P40013039 | DESANTIS, RON | P | US | True | True | 2024-P-US-00 | 1 | 10,000 |

**Q9f. The split: share × NUMBER_OF_CANDIDATES against the amount, and rows per disbursement  (0 s)**

| ncand | rows_per_disbursement | split_ok | shares_sum_to_amount | disbursements | dollars |
|---|---|---|---|---|---|
| 1 | 1 | True | True | 47 | 9,073,804 |
| 1 | 2 | True | False | 2 | 38,500 |
| 2 | 1 | True | False | 2 | 23,864 |
| 2 | 2 | True | True | 8 | 318,138 |

**Q9g. Multi-candidate share  (0 s)**

| multi_candidate | rows | share_dollars | share_of_dollars |
|---|---|---|---|
| True | 18 | 330,070 | 3.48% |
| False | 51 | 9,150,804 | 96.52% |

**Q9h. Repeat groups (§2): count, rows, dollars  (0 s)**

| groups | rows | share_dollars |
|---|---|---|
| 2 | 4 | 67,500 |

**Q9i. Fully identical rows (every column, the image number too)  (0 s)**

| spon | SB_IMAGE_NUM | PAYEE_NAME | DISBURSEMENT_DATE | REPORTED_DISBURSEMENT_AMOUNT | CANDIDATE_ID | NUMBER_OF_CANDIDATES | copies |
|---|---|---|---|---|---|---|---|
| C30003453 | 202409169675480474 | M2 PLACEMENT LLC | 12-SEP-24 | 52819 |  | 2 | 2 |
| C30003453 | 202409169675480474 | HIGHTIDE MEDIA | 13-SEP-24 | 13698 |  | 2 | 2 |
| C30003479 | 202410019684773225 | IMPACT POLITICS LLC | 25-SEP-24 | 5000 | H4CA16239 | 1 | 2 |

```text
Form 9 filings read for 2024: 63 from 25 sponsors, https://api.open.fec.gov/v1/filings/?committee_id=<id>&form_type=F9&cycle=2024
```

**Q9j. 2024 Form 9 filings by sponsor: amendment indicator, superseded or not  (0 s)**

| spon | amndt | is_amended | most_recent | filings |
|---|---|---|---|---|
| C30001978 | A |  | True | 1 |
| C30001978 | N | False | False | 1 |
| C30001978 | N | False | True | 1 |
| C30002430 | A | False | True | 2 |
| C30002430 | A | True | False | 2 |
| C30002430 | A | True | True | 1 |
| C30002430 | N | False | True | 2 |
| C30002430 | N | True | False | 2 |
| C30002851 | A | False | True | 1 |
| C30002851 | N | False | False | 1 |
| C30002851 | N | False | True | 1 |
| C30002851 | N | True | False | 1 |
| C30002885 | N | False | True | 1 |
| C30003354 | A | False | True | 1 |
| C30003354 | N | True | False | 1 |
| C30003362 | N | False | False | 1 |
| C30003362 | N | False | True | 1 |
| C30003370 | A | False | True | 2 |
| C30003370 | N | True | False | 2 |
| C30003388 | N | False | True | 1 |
| C30003396 | N | False | True | 1 |
| C30003404 | A | False | True | 1 |
| C30003404 | N | True | False | 1 |
| C30003412 | N | False | True | 3 |
| C30003420 | N | False | True | 1 |
| C30003438 | N | False | True | 1 |
| C30003446 | A | False | True | 1 |
| C30003446 | N | True | False | 1 |
| C30003453 | N | False | True | 2 |
| C30003461 | A | False | True | 1 |
| C30003461 | A | True | False | 1 |
| C30003461 | N | False | False | 1 |
| C30003461 | N | True | True | 1 |
| C30003479 | N | False | True | 3 |
| C30003487 | N | False | True | 1 |
| C30003495 | A | False | True | 1 |
| C30003495 | N | False | True | 1 |
| C30003495 | N | True | False | 1 |
| C30003503 | N | False | True | 1 |
| C30003511 | A | False | True | 3 |
| C30003511 | N | True | False | 3 |
| C30003529 | N | False | True | 1 |
| C30003537 | N | False | True | 3 |
| C30003552 | N | False | True | 1 |
| C30003560 | A | False | True | 1 |
| C30003560 | N | True | False | 1 |

**Q9k. Electioneering rows by the Form 9 they are on: found, amended, most recent  (0 s)**

| filing_found | amndt | is_amended | most_recent | rows | share_dollars | filings |
|---|---|---|---|---|---|---|
| True | A | False | True | 22 | 3,448,421 | 13 |
| True | A | True | False | 2 | 33,750 | 1 |
| True | N | False | True | 43 | 5,964,953 | 23 |
| True | N | True | True | 2 | 33,750 | 1 |

**Q9l. Every 2024 repeat group, its rows' filings, and what they are  (0 s)**

| spon | PAYEE_NAME | DISBURSEMENT_DATE | amount | CANDIDATE_ID | rows | share_dollars | filings | amndts | latest_of_each | n_filings | rows_on_a_found_filing | reading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C30003461 | GMMB INC. | 13-SEP-24 | 33750 | H6LA04138 | 2 | 33,750 | [1816711, 1849492] | ['A', 'N'] | [1816711, 1860200] | 2 | 2 | separate filings, not one chain |
| C30003461 | GMMB INC. | 13-SEP-24 | 33750 | H0LA01087 | 2 | 33,750 | [1816711, 1849492] | ['A', 'N'] | [1816711, 1860200] | 2 | 2 | separate filings, not one chain |

**Q9m. 2024 rows on a superseded Form 9 (not the most recent of its chain), whatever their key  (0 s)**

| most_recent | rows | share_dollars | filings | rows_restated_on_the_latest |
|---|---|---|---|---|
| False | 2 | 33,750 | 1 | 0 |
| True | 67 | 9,447,124 | 37 | 67 |

```text
https://www.fec.gov/files/bulk-downloads/2010/ElectioneeringComm_2010.csv | Last-Modified: Mon, 23 Nov 2026 10:12:09 GMT | bytes 160,783 | downloaded 2026-11-24T02:37:14+00:00
ecraw_2010: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2012/ElectioneeringComm_2012.csv | Last-Modified: Mon, 23 Nov 2026 10:12:10 GMT | bytes 75,779 | downloaded 2026-11-24T02:37:15+00:00
ecraw_2012: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2014/ElectioneeringComm_2014.csv | Last-Modified: Mon, 23 Nov 2026 10:12:11 GMT | bytes 10,506 | downloaded 2026-11-24T02:37:16+00:00
ecraw_2014: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2016/ElectioneeringComm_2016.csv | Last-Modified: Mon, 23 Nov 2026 10:12:12 GMT | bytes 27,703 | downloaded 2026-11-24T02:37:18+00:00
ecraw_2016: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2018/ElectioneeringComm_2018.csv | Last-Modified: Mon, 23 Nov 2026 10:12:13 GMT | bytes 51,662 | downloaded 2026-11-24T02:37:19+00:00
ecraw_2018: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2020/ElectioneeringComm_2020.csv | Last-Modified: Mon, 23 Nov 2026 10:12:14 GMT | bytes 71,074 | downloaded 2026-11-24T02:37:20+00:00
ecraw_2020: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2022/ElectioneeringComm_2022.csv | Last-Modified: Mon, 23 Nov 2026 10:12:15 GMT | bytes 11,977 | downloaded 2026-11-24T02:37:21+00:00
ecraw_2022: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2026/ElectioneeringComm_2026.csv | Last-Modified: Mon, 23 Nov 2026 10:12:17 GMT | bytes 13,079 | downloaded 2026-11-24T02:37:23+00:00
ecraw_2026: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
```

```text
repeat groups by cycle: {2010: 20, 2012: 12, 2014: 1, 2016: 3, 2018: 1, 2020: 5, 2022: 0, 2024: 2, 2026: 3}
Form 9 filings read for 2010: 188 from 4 sponsors, https://api.open.fec.gov/v1/filings/?committee_id=<id>&form_type=F9&cycle=2010
```

**Q9n. 2010, the cycle with the most repeat groups: its 20 largest against their Form 9s  (0 s)**

| spon | PAYEE_NAME | DISBURSEMENT_DATE | amount | CANDIDATE_ID | rows | share_dollars | filings | amndts | latest_of_each | n_filings | rows_on_a_found_filing | reading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C30001648 | WF OF R MEDIA | 12-OCT-10 | 725000 | H6CO07023 | 2 | 1,450,000 | [502785, 510432] | ['N'] | [502785, 510432] | 2 | 2 | separate filings, not one chain |
| C30001648 | WF OF R MEDIA | 12-OCT-10 | 505000 | H6OH06095 | 2 | 1,010,000 | [502227, 510439] | ['N'] | [502227, 510439] | 2 | 2 | separate filings, not one chain |
| C30001648 | WF OF R MEDIA | 12-OCT-10 | 435000 | H0PA12132 | 2 | 870,000 | [502233, 510272] | ['N'] | [502233, 510272] | 2 | 2 | separate filings, not one chain |
| C30001648 | WF OF R MEDIA | 12-OCT-10 | 275000 | H8NM01224 | 2 | 550,000 | [502791, 510230] | ['N'] | [502791, 510230] | 2 | 2 | separate filings, not one chain |
| C30001648 | WF OF R MEDIA | 12-OCT-10 | 231000 | H2SD00092 | 2 | 462,000 | [502278, 510384] | ['A', 'N'] | [502278, 510384] | 2 | 2 | separate filings, not one chain |
| C30001648 | WF OF R MEDIA | 12-OCT-10 | 225000 | H0WV01106 | 2 | 450,000 | [507117, 510397] | ['A', 'N'] | [507117, 510397] | 2 | 2 | separate filings, not one chain |
| C30001648 | WF OF R MEDIA | 12-OCT-10 | 130000 | H6WI08122 | 2 | 260,000 | [502778, 510243] | ['N'] | [502778, 510243] | 2 | 2 | separate filings, not one chain |
| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 04-OCT-10 | 111574 | H0AR04038 | 2 | 223,148 | [496996, 497081] | ['N'] | [496996, 497081] | 2 | 2 | separate filings, not one chain |
| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 04-OCT-10 | 97570 | H8AL02130 | 2 | 195,140 | [496995, 497078] | ['N'] | [496995, 497078] | 2 | 2 | separate filings, not one chain |
| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 04-OCT-10 | 70617 | H8ID01090 | 2 | 141,234 | [496994, 497080] | ['N'] | [496994, 497080] | 2 | 2 | separate filings, not one chain |
| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 04-OCT-10 | 68604 | H8MS01061 | 2 | 137,208 | [496997, 497083] | ['N'] | [496997, 497083] | 2 | 2 | separate filings, not one chain |
| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 15-OCT-10 | 49921 | H8MD01086 | 2 | 99,842 | [504911, 504913] | ['N'] | [504911, 504913] | 2 | 2 | separate filings, not one chain |
| C30001101 | MCCARTHY MARCUS HENNINGS | 07-SEP-10 | 10756.5 | S2CA00286 | 4 | 43,026 | [492058, 492064, 492067, 492071] | ['N'] | [492058, 492064, 492067, 492071] | 4 | 4 | separate filings, not one chain |
| C30001564 | CHUN & YONAMINE ADVERTISING | 30-APR-10 | 10471.2 | H0HI01157 | 6 | 41,885 | [470285, 754321] | ['N'] | [470285, 754321] | 2 | 6 | separate filings, not one chain |
| C30001564 | CHUN & YONAMINE ADVERTISING | 30-APR-10 | 10471.2 | H2HI02128 | 6 | 41,885 | [470285, 754321] | ['N'] | [470285, 754321] | 2 | 6 | separate filings, not one chain |
| C30001564 | CHUN & YONAMINE ADVERTISING | 10-MAY-10 | 7853.4 | H0HI01157 | 6 | 31,414 | [467813, 754635] | ['N'] | [467813, 754635] | 2 | 6 | separate filings, not one chain |
| C30001564 | CHUN & YONAMINE ADVERTISING | 10-MAY-10 | 7853.4 | H2HI02128 | 6 | 31,414 | [467813, 754635] | ['N'] | [467813, 754635] | 2 | 6 | separate filings, not one chain |
| C30000814 | CSG INC | 19-FEB-09 | 14375 | H0IL05302 | 2 | 28,750 | [-32070, None] | ['N'] | [-32070, None] | 1 | 1 | a row on no filing OpenFEC lists |
| C30001564 | CHUN & YONAMINE ADVERTISING | 30-APR-10 | 8368 | H0HI01157 | 4 | 20,920 | [-303745] | ['N'] | [-303745] | 1 | 4 | two lines on one filing |
| C30001564 | CHUN & YONAMINE ADVERTISING | 30-APR-10 | 8368 | H2HI02128 | 4 | 20,920 | [-303745] | ['N'] | [-303745] | 1 | 4 | two lines on one filing |

**Q9o. 2010: those sponsors' rows by whether their Form 9 is the most recent of its chain  (0 s)**

| most_recent | rows | share_dollars | filings |
|---|---|---|---|
| True | 202 | 45,809,001 | 158 |

**Q9p. 2024: each repeat group read against its raw filings**

| sponsor | payee | date | amount | candidate | filings | form, original (HDR) and F93 lines to the payee | reading |
|---|---|---|---|---|---|---|---|

```text
https://docquery.fec.gov/dcdev/posted/1816711.fec | Last-Modified: Thu, 19 Sep 2024 19:08:57 GMT | bytes 729 | downloaded 2026-11-24T02:29:23+00:00
https://docquery.fec.gov/dcdev/posted/1849492.fec | Last-Modified: Fri, 22 Nov 2024 16:41:45 GMT | bytes 532 | downloaded 2026-11-24T02:29:24+00:00
```

| C30003461 | GMMB INC. | 13-SEP-24 | 33750 | H0LA01087 | 2 | 1816711: F9N, of 1816711, cover 20240917 20240927 ''; F93 G2024 20240913 33750.00 / 1849492: F9A, of 1816711, cover 20240919 20240917 20240927 '20240917'; F93 P2024 20240913 33750.00 | restatement (one report and its amendment) |

```text
https://docquery.fec.gov/dcdev/posted/1816711.fec | Last-Modified: Thu, 19 Sep 2024 19:08:57 GMT | bytes 729 | downloaded 2026-11-24T02:29:23+00:00
https://docquery.fec.gov/dcdev/posted/1849492.fec | Last-Modified: Fri, 22 Nov 2024 16:41:45 GMT | bytes 532 | downloaded 2026-11-24T02:29:24+00:00
```

| C30003461 | GMMB INC. | 13-SEP-24 | 33750 | H6LA04138 | 2 | 1816711: F9N, of 1816711, cover 20240917 20240927 ''; F93 G2024 20240913 33750.00 / 1849492: F9A, of 1816711, cover 20240919 20240917 20240927 '20240917'; F93 P2024 20240913 33750.00 | restatement (one report and its amendment) |

**Q9p. 2010: each repeat group read against its raw filings**

| sponsor | payee | date | amount | candidate | filings | form, original (HDR) and F93 lines to the payee | reading |
|---|---|---|---|---|---|---|---|

```text
https://docquery.fec.gov/dcdev/posted/502785.fec | Last-Modified: Sat, 06 Apr 2024 01:34:50 GMT | bytes 713 | downloaded 2026-11-24T02:29:33+00:00
https://docquery.fec.gov/dcdev/posted/510432.fec | Last-Modified: Sat, 06 Apr 2024 05:50:45 GMT | bytes 703 | downloaded 2026-11-24T02:29:37+00:00
```

| C30001648 | WF OF R MEDIA | 12-OCT-10 | 725000 | H6CO07023 | 2 | 502785: F9N, of 502785, cover 20101012 20101013 20101013 'hiding'; F93 G2010 20101012 725000.00 / 510432: F9N, of 510432, cover 20101012 20101022 20101022 'skype'; F93 G2010 20101012 725000.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/502227.fec | Last-Modified: Sat, 06 Apr 2024 20:39:53 GMT | bytes 720 | downloaded 2026-11-24T02:29:31+00:00
https://docquery.fec.gov/dcdev/posted/510439.fec | Last-Modified: Sat, 06 Apr 2024 05:50:50 GMT | bytes 719 | downloaded 2026-11-24T02:29:37+00:00
```

| C30001648 | WF OF R MEDIA | 12-OCT-10 | 505000 | H6OH06095 | 2 | 502227: F9N, of 502227, cover 20101012 20101014 20101014 'READ THIS'; F93 G2010 20101012 505000.00 / 510439: F9N, of 510439, cover 20101012 20101022 20101022 'ridiculous'; F93 G2010 20101012 505000.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/502233.fec | Last-Modified: Sat, 06 Apr 2024 20:39:48 GMT | bytes 710 | downloaded 2026-11-24T02:29:32+00:00
https://docquery.fec.gov/dcdev/posted/510272.fec | Last-Modified: Sat, 06 Apr 2024 05:48:33 GMT | bytes 705 | downloaded 2026-11-24T02:29:36+00:00
```

| C30001648 | WF OF R MEDIA | 12-OCT-10 | 435000 | H0PA12132 | 2 | 502233: F9N, of 502233, cover 20101012 20101014 20101014 'REPEAL'; F93 G2010 20101012 435000.00 / 510272: F9N, of 510272, cover 20101012 20101022 20101022 'TAXES'; F93 G2010 20101012 435000.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/502791.fec | Last-Modified: Sat, 06 Apr 2024 01:34:54 GMT | bytes 718 | downloaded 2026-11-24T02:29:33+00:00
https://docquery.fec.gov/dcdev/posted/510230.fec | Last-Modified: Sat, 06 Apr 2024 05:48:00 GMT | bytes 712 | downloaded 2026-11-24T02:29:35+00:00
```

| C30001648 | WF OF R MEDIA | 12-OCT-10 | 275000 | H8NM01224 | 2 | 502791: F9N, of 502791, cover 20101012 20101013 20101013 'wallpaper'; F93 G2010 20101012 275000.00 / 510230: F9N, of 510230, cover 20101012 20101021 20101021 'NAKED'; F93 G2010 20101012 275000.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/502278.fec | Last-Modified: Sat, 06 Apr 2024 20:40:55 GMT | bytes 723 | downloaded 2026-11-24T02:29:32+00:00
https://docquery.fec.gov/dcdev/posted/510384.fec | Last-Modified: Sat, 06 Apr 2024 05:49:49 GMT | bytes 720 | downloaded 2026-11-24T02:29:36+00:00
```

| C30001648 | WF OF R MEDIA | 12-OCT-10 | 231000 | H2SD00092 | 2 | 502278: F9A, of 502272, cover 20101012 20101014 20101014 ''; F93 G2010 20101012 231000.00 / 510384: F9N, of 510384, cover 20101012 20101022 20101022 'wasted'; F93 G2010 20101012 231000.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/507117.fec | Last-Modified: Sat, 06 Apr 2024 04:14:00 GMT | bytes 710 | downloaded 2026-11-24T02:29:34+00:00
https://docquery.fec.gov/dcdev/posted/510397.fec | Last-Modified: Sat, 06 Apr 2024 05:50:08 GMT | bytes 708 | downloaded 2026-11-24T02:29:36+00:00
```

| C30001648 | WF OF R MEDIA | 12-OCT-10 | 225000 | H0WV01106 | 2 | 507117: F9A, of 502202, cover 20101012 20101014 20101014 'order'; F93 G2010 20101012 225000.00 / 510397: F9N, of 510397, cover 20101012 20101022 20101022 'FIRST'; F93 G2010 20101012 225000.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/502778.fec | Last-Modified: Sat, 06 Apr 2024 01:34:43 GMT | bytes 716 | downloaded 2026-11-24T02:29:33+00:00
https://docquery.fec.gov/dcdev/posted/510243.fec | Last-Modified: Sat, 06 Apr 2024 05:48:10 GMT | bytes 706 | downloaded 2026-11-24T02:29:35+00:00
```

| C30001648 | WF OF R MEDIA | 12-OCT-10 | 130000 | H6WI08122 | 2 | 502778: F9N, of 502778, cover 20101012 20101013 20101013 'wallpaper'; F93 G2010 20101012 130000.00 / 510243: F9N, of 510243, cover 20101012 20101021 20101021 'NAKED'; F93 G2010 20101012 130000.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/496996.fec | Last-Modified: Sat, 06 Apr 2024 17:17:29 GMT | bytes 808 | downloaded 2026-11-24T02:29:29+00:00
https://docquery.fec.gov/dcdev/posted/497081.fec | Last-Modified: Sat, 06 Apr 2024 17:18:44 GMT | bytes 806 | downloaded 2026-11-24T02:29:31+00:00
```

| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 04-OCT-10 | 111574 | H0AR04038 | 2 | 496996: F9N, of 496996, cover 20101004 20101007 20101007 'Working'; F93 G2010 20101004 111574.00 / 497081: F9N, of 497081, cover 20101004 20101007 20101007 'Trust'; F93 G2010 20101004 111574.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/496995.fec | Last-Modified: Sat, 06 Apr 2024 17:17:28 GMT | bytes 810 | downloaded 2026-11-24T02:29:29+00:00
https://docquery.fec.gov/dcdev/posted/497078.fec | Last-Modified: Sat, 06 Apr 2024 17:18:42 GMT | bytes 807 | downloaded 2026-11-24T02:29:30+00:00
```

| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 04-OCT-10 | 97570 | H8AL02130 | 2 | 496995: F9N, of 496995, cover 20101004 20101007 20101007 'Working'; F93 G2010 20101004 97570.00 / 497078: F9N, of 497078, cover 20101004 20101007 20101007 'Trust'; F93 G2010 20101004 97570.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/496994.fec | Last-Modified: Sat, 06 Apr 2024 17:17:27 GMT | bytes 809 | downloaded 2026-11-24T02:29:28+00:00
https://docquery.fec.gov/dcdev/posted/497080.fec | Last-Modified: Sat, 06 Apr 2024 17:18:44 GMT | bytes 807 | downloaded 2026-11-24T02:29:30+00:00
```

| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 04-OCT-10 | 70617 | H8ID01090 | 2 | 496994: F9N, of 496994, cover 20101004 20101007 20101007 'Working'; F93 G2010 20101004 70617.00 / 497080: F9N, of 497080, cover 20101004 20101007 20101007 'Trust'; F93 G2010 20101004 70617.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/496997.fec | Last-Modified: Sat, 06 Apr 2024 17:17:43 GMT | bytes 812 | downloaded 2026-11-24T02:29:29+00:00
https://docquery.fec.gov/dcdev/posted/497083.fec | Last-Modified: Sat, 06 Apr 2024 17:18:46 GMT | bytes 810 | downloaded 2026-11-24T02:29:31+00:00
```

| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 04-OCT-10 | 68604 | H8MS01061 | 2 | 496997: F9N, of 496997, cover 20101004 20101007 20101007 'Working'; F93 G2010 20101004 68604.00 / 497083: F9N, of 497083, cover 20101004 20101007 20101007 'Trust'; F93 G2010 20101004 68604.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/504911.fec | Last-Modified: Sat, 06 Apr 2024 03:03:09 GMT | bytes 812 | downloaded 2026-11-24T02:29:34+00:00
https://docquery.fec.gov/dcdev/posted/504913.fec | Last-Modified: Sat, 06 Apr 2024 03:03:12 GMT | bytes 807 | downloaded 2026-11-24T02:29:34+00:00
```

| C30001101 | ISSUE AND IMAGE ADVOCACY AND ADVERTISING | 15-OCT-10 | 49921 | H8MD01086 | 2 | 504911: F9N, of 504911, cover 20101015 20101019 20101019 ''Working''; F93 G2010 20101015 49921.00 / 504913: F9N, of 504913, cover 20101015 20101019 20101019 'Trust'; F93 G2010 20101015 49921.00 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/492058.fec | Last-Modified: Sat, 06 Apr 2024 14:19:34 GMT | bytes 1,106 | downloaded 2026-11-24T02:29:26+00:00
https://docquery.fec.gov/dcdev/posted/492064.fec | Last-Modified: Sat, 06 Apr 2024 14:19:47 GMT | bytes 1,094 | downloaded 2026-11-24T02:29:26+00:00
https://docquery.fec.gov/dcdev/posted/492067.fec | Last-Modified: Sat, 06 Apr 2024 14:20:21 GMT | bytes 1,117 | downloaded 2026-11-24T02:29:27+00:00
https://docquery.fec.gov/dcdev/posted/492071.fec | Last-Modified: Sat, 06 Apr 2024 14:20:05 GMT | bytes 1,106 | downloaded 2026-11-24T02:29:28+00:00
```

| C30001101 | MCCARTHY MARCUS HENNINGS | 07-SEP-10 | 10756.5 | S2CA00286 | 4 | 492058: F9N, of 492058, cover 20100831 20100908 20100908 ''Can't Work' TV Ad - Sacrame'; F93 G2010 20100907 10756.50 / 492064: F9N, of 492064, cover 20100831 20100908 20100908 ''Can't Work' TV Ad - San Die'; F93 G2010 20100907 10756.50 / 492067: F9N, of 492067, cover 20100831 20100908 20100908 ''Can't Work' TV Ad - Fresno/'; F93 G2010 20100907 10756.50 / 492071: F9N, of 492071, cover 20100831 20100908 20100908 ''Can't Work' TV Ad - Bakersf'; F93 G2010 20100907 10756.50 | two reports with different covers |

```text
https://docquery.fec.gov/dcdev/posted/470285.fec | Last-Modified: Sat, 06 Apr 2024 04:03:28 GMT | bytes 1,739 | downloaded 2026-11-24T02:29:26+00:00
https://docquery.fec.gov/dcdev/posted/754321.fec | Last-Modified: Sat, 06 Apr 2024 07:42:55 GMT | bytes 1,844 | downloaded 2026-11-24T02:29:37+00:00
```

| C30001564 | CHUN & YONAMINE ADVERTISING | 30-APR-10 | 10471.2 | H2HI02128 | 2 | 470285: F9N, of 470285, cover 20100430 20100509 20100501 'radio ads'; F93 O2010 20100430 10471.20; O2010 20100430 10471.20; O2010 20100430 10471.20; O2010 20100430 10471.20 / 754321: F9N, of 754321, cover 20100430 20100509 20100501 'RADIO ADS'; F93 O2010 20100430 10471.20; O2010 20100430 10471.20; O2010 20100430 10471.20; O2010 20100430 10471.20 | the same report filed again as new (same cover dates and title, case aside) |

```text
https://docquery.fec.gov/dcdev/posted/470285.fec | Last-Modified: Sat, 06 Apr 2024 04:03:28 GMT | bytes 1,739 | downloaded 2026-11-24T02:29:26+00:00
https://docquery.fec.gov/dcdev/posted/754321.fec | Last-Modified: Sat, 06 Apr 2024 07:42:55 GMT | bytes 1,844 | downloaded 2026-11-24T02:29:37+00:00
```

| C30001564 | CHUN & YONAMINE ADVERTISING | 30-APR-10 | 10471.2 | H0HI01157 | 2 | 470285: F9N, of 470285, cover 20100430 20100509 20100501 'radio ads'; F93 O2010 20100430 10471.20; O2010 20100430 10471.20; O2010 20100430 10471.20; O2010 20100430 10471.20 / 754321: F9N, of 754321, cover 20100430 20100509 20100501 'RADIO ADS'; F93 O2010 20100430 10471.20; O2010 20100430 10471.20; O2010 20100430 10471.20; O2010 20100430 10471.20 | the same report filed again as new (same cover dates and title, case aside) |

```text
https://docquery.fec.gov/dcdev/posted/467813.fec | Last-Modified: Sat, 06 Apr 2024 03:14:48 GMT | bytes 1,590 | downloaded 2026-11-24T02:29:25+00:00
https://docquery.fec.gov/dcdev/posted/754635.fec | Last-Modified: Sat, 06 Apr 2024 07:53:21 GMT | bytes 1,670 | downloaded 2026-11-24T02:29:38+00:00
```

| C30001564 | CHUN & YONAMINE ADVERTISING | 10-MAY-10 | 7853.4 | H2HI02128 | 2 | 467813: F9N, of 467813, cover 20100510 20100518 20100510 'radio ads'; F93 O2010 20100510 7853.40; O2010 20100510 7853.40; O2010 20100510 7853.40; O2010 20100510 7853.40 / 754635: F9N, of 754635, cover 20100510 20100518 20100510 'RADIO ADS'; F93 O2010 20100510 7853.40; O2010 20100510 7853.40; O2010 20100510 7853.40; O2010 20100510 7853.40 | the same report filed again as new (same cover dates and title, case aside) |

```text
https://docquery.fec.gov/dcdev/posted/467813.fec | Last-Modified: Sat, 06 Apr 2024 03:14:48 GMT | bytes 1,590 | downloaded 2026-11-24T02:29:25+00:00
https://docquery.fec.gov/dcdev/posted/754635.fec | Last-Modified: Sat, 06 Apr 2024 07:53:21 GMT | bytes 1,670 | downloaded 2026-11-24T02:29:38+00:00
```

| C30001564 | CHUN & YONAMINE ADVERTISING | 10-MAY-10 | 7853.4 | H0HI01157 | 2 | 467813: F9N, of 467813, cover 20100510 20100518 20100510 'radio ads'; F93 O2010 20100510 7853.40; O2010 20100510 7853.40; O2010 20100510 7853.40; O2010 20100510 7853.40 / 754635: F9N, of 754635, cover 20100510 20100518 20100510 'RADIO ADS'; F93 O2010 20100510 7853.40; O2010 20100510 7853.40; O2010 20100510 7853.40; O2010 20100510 7853.40 | the same report filed again as new (same cover dates and title, case aside) |
| C30000814 | CSG INC | 19-FEB-09 | 14375 | H0IL05302 | 2 | -32070: paper, not read / None: paper, not read | not read (paper) |
| C30001564 | CHUN & YONAMINE ADVERTISING | 30-APR-10 | 8368 | H0HI01157 | 1 | -303745: paper, not read | not read (paper) |
| C30001564 | CHUN & YONAMINE ADVERTISING | 30-APR-10 | 8368 | H2HI02128 | 1 | -303745: paper, not read | not read (paper) |

**Q9q. Two candidate dedup rules on the file alone, by cycle: a repeat group (§2) whose rows also agree on COMMUNICATION_DATE and PUBLIC_DISBURSEMENT_DATE keeps only its highest SB_IMAGE_NUM  (0 s)**

| cycle | rows | dollars | rows_dropped_by_extended_key | dollars_dropped_by_extended_key | rows_dropped_by_file_key | dollars_dropped_by_file_key |
|---|---|---|---|---|---|---|
| 2010 | 654 | 71,692,553 | 33 | 561,423 | 41 | 3,101,798 |
| 2012 | 288 | 15,392,078 | 57 | 187,950 | 60 | 188,638 |
| 2014 | 40 | 7,545,119 | 1 | 206,835 | 1 | 206,835 |
| 2016 | 97 | 9,785,808 | 2 | 40,750 | 3 | 65,750 |
| 2018 | 212 | 14,713,765 | 0 |  | 1 | 5,635 |
| 2020 | 273 | 25,948,848 | 16 | 147,143 | 16 | 147,143 |
| 2022 | 45 | 4,599,212 | 0 |  | 0 |  |
| 2024 | 69 | 9,480,874 | 0 |  | 2 | 33,750 |
| 2026 | 48 | 5,966,538 | 5 | 524,000 | 5 | 524,000 |

**Who and what.** 25 sponsors, all `C3` and `cm` type `E`, none a committee of another kind, 69
rows, 59 disbursements. Disbursements total $9,454,306 and candidate shares $9,480,874 (Q9a). Two
one-candidate disbursements sit on two rows each, on one image number: the Association of
Equipment Manufacturers' $33,500 for Bacon and Evan Low for Assembly's $5,000 for Low. Their shares
count $38,500 twice. Two two-candidate disbursements have one row each, $11,932 short (Q9f, Q9i).
These copies were not checked against their filings. 24
rows ($2,179,759) name no candidate. They are issue ads by trade groups and nonprofits (the
American Chemistry Council's four, $893,876; Wisconsin Principles' $450,500). The 45 named rows
are all candidates of the cycle with a race, but `P60012143` ($32,000), which `cn` lacks (Q9e).

**The split is exact.** Every row's `CALCULATED_CANDIDATE_SHARE × NUMBER_OF_CANDIDATES` equals
its amount to the cent. A two-candidate disbursement has two rows in 8 of 10 cases; in the other two
it has one row (Q9f). Multi-candidate rows are 3.48% of dollars (Q9g).

**Amendments.** The file has no filing number and no amendment indicator (§1, confirmed). An
image number falls inside one Form 9's image range on OpenFEC for every 2024 row (Q9k). Two rows,
$33,750, are on a Form 9 that a later one supersedes (Q9m). 2024's two repeat groups are those two
rows and their restatement (Q9l): Issue One Action's $33,750 to GMMB on 2024-09-13, split between
`H6LA04138` and `H0LA01087`. Its raw filings say so: `1849492` is an `F9A` whose header names
`FEC-1816711`, changing the election code from `G2024` to `P2024` (Q9p). OpenFEC's own chain
missed it.

**Fewer than 5 repeat groups, so 2010 too** (§1.1's fallback). 2010 has the most, 20, and its 20
largest were read against their Form 9s. 13 are **two different reports**: the same payee, date and
amount on two Form 9s with different covers and titles. `C30001648`'s payments to `WF OF R MEDIA` on
12-OCT-10 each sit on two reports for two different ads (`hiding` and `skype`). Four are **one report filed
again as new** (`C30001564`, `CHUN & YONAMINE`, the same cover and title filed again as 754321 and
754635). Three are paper filings and could not be read.

**§3's docquery listing is corrected:** `https://docquery.fec.gov/cgi-bin/forms/C30002851/` answered
`403 Forbidden` on 2026-11-24 at about 02:20 UTC, to `curl` from the VM with the project's user agent
and with a browser's.
The filing list came from OpenFEC's `/v1/filings/` and the lines from `dcdev/posted/<FILE_NUM>.fec`,
which answer.

**Decision line.** The Form 9s support one rule: a row restated by an amendment of the same report,
or by the same report filed again, is one payment. A repeat across two reports is two. The file
cannot apply it alone, because it carries no filing number or cover. The §2 file key (keep the highest image
number of a repeat group) drops 2024's restatement exactly ($33,750) but 2010's separate reports
too: $3,101,798 of $71,692,553, of which the 20 largest groups read are mostly real (Q9q). The file key
widened by communication and distribution dates misses 2024's restatement, since the amendment
changed those dates. **Every row counts but a disbursement's copies:** rows of one disbursement
(sponsor, image number, payee, date and amount) beyond its `NUMBER_OF_CANDIDATES` are dropped.
2024 then keeps 67 rows, **$9,442,374**, and drops 2 ($38,500, Q9f's arithmetic). It still
overcounts the amended restatement by $33,750 (0.36%), and 2010 by its refiled pairs (about
$73,000). $9,442,374 is the figure NEU-2166's definition of done is within 1% of. It is $9,480,874
if NEU-2163 counts every row, and $9,408,624 with the file key as well. Blank-candidate rows count
toward the sponsor's total and no candidate's.

## Q10: party coordinated expenditures (2024)

```python
# Q10: party coordinated expenditures (2024), silver's kind 'coordinated'.
groups(2024)
bulk("pas2", 2024)
silver("independent_expenditure", 2024)
silver("reported_total", 2024)
silver("candidate", 2024)
con.execute("""
CREATE TABLE co AS SELECT s.*, g.cmte_tp, g.cmte_nm, b.MEMO_CD, b.RPT_TP FROM silver_2024.independent_expenditure AS s
JOIN pas2_2024 AS b ON b.SUB_ID = s.source_record_id
LEFT JOIN grp_2024 AS g ON g.id = s.committee_id WHERE s.kind = 'coordinated'""")
show("Q10a. Coordinated expenditures: rows and dollars, by filer cm type", """
SELECT cmte_tp, count(DISTINCT committee_id) AS filers, count(*) AS rows, sum(amount) AS dollars,
    count(*) FILTER (WHERE candidate_id IS NULL) AS no_candidate_rows, sum(amount) FILTER (WHERE candidate_id IS NULL) AS no_candidate_dollars
FROM co GROUP BY ALL ORDER BY dollars DESC""")
show("Q10b. 24C memo lines silver drops, and 24C rows by MEMO_CD in pas2", """
SELECT MEMO_CD, count(*) AS rows, sum(TRANSACTION_AMT) AS dollars FROM pas2_2024 WHERE TRANSACTION_TP = '24C' GROUP BY ALL ORDER BY ALL""")
show("Q10c. The 20 largest party committees", """
SELECT committee_id, any_value(cmte_nm) AS name, any_value(cmte_tp) AS cm_type, count(*) AS rows, sum(amount) AS dollars,
    (SELECT party_coordinated FROM silver_2024.reported_total AS r WHERE r.committee_id = co.committee_id) AS reported
FROM co GROUP BY 1 ORDER BY dollars DESC LIMIT 20""")
show("Q10d. The 20 largest candidates", """
SELECT co.candidate_id, any_value(c.name) AS name, any_value(co.race_id) AS race, count(*) AS rows, sum(amount) AS dollars,
    count(DISTINCT committee_id) AS committees
FROM co LEFT JOIN (SELECT candidate_id, any_value(name) AS name FROM silver_2024.candidate GROUP BY 1) AS c USING (candidate_id)
GROUP BY 1 ORDER BY dollars DESC LIMIT 20""")
show("Q10e. 24C from a filer that is not a party committee (cm type not X or Y)", """
SELECT committee_id, any_value(cmte_nm) AS name, any_value(cmte_tp) AS cm_type, count(*) AS rows, sum(amount) AS dollars
FROM co WHERE cmte_tp NOT IN ('X', 'Y') OR cmte_tp IS NULL GROUP BY 1 ORDER BY dollars DESC""")
show("Q10f. Each committee's sum against reported_total.party_coordinated", """
WITH f AS (SELECT r.committee_id, coalesce(c.d, 0) AS pas2, r.party_coordinated AS reported
           FROM silver_2024.reported_total AS r LEFT JOIN (SELECT committee_id, sum(amount) AS d FROM co GROUP BY 1) AS c USING (committee_id)
           WHERE c.d IS NOT NULL OR coalesce(r.party_coordinated, 0) <> 0)
SELECT CASE WHEN reported IS NULL THEN 'no reported figure' WHEN abs(pas2 - reported) <= 0.01 * abs(reported) THEN 'within 1%'
            WHEN pas2 > reported THEN 'pas2 more than 1% above' ELSE 'pas2 more than 1% below' END AS band,
    count(*) AS committees, sum(pas2) AS pas2_dollars, sum(reported) AS reported_dollars
FROM f GROUP BY ALL ORDER BY committees DESC""")
show("Q10g. Committees more than 1% apart, by the gap", """
WITH f AS (SELECT r.committee_id, g.cmte_nm, coalesce(c.d, 0) AS pas2, r.party_coordinated AS reported
           FROM silver_2024.reported_total AS r LEFT JOIN (SELECT committee_id, sum(amount) AS d FROM co GROUP BY 1) AS c USING (committee_id)
           LEFT JOIN grp_2024 AS g ON g.id = r.committee_id
           WHERE c.d IS NOT NULL OR coalesce(r.party_coordinated, 0) <> 0)
SELECT *, pas2 - coalesce(reported, 0) AS gap FROM f
WHERE reported IS NULL OR abs(pas2 - reported) > 0.01 * abs(reported) ORDER BY abs(pas2 - coalesce(reported, 0)) DESC LIMIT 20""")
show("Q10h. The figure: counted coordinated expenditures, and those reaching a candidate of the cycle", """
SELECT count(*) AS rows, sum(amount) AS dollars, sum(amount) FILTER (WHERE candidate_id IS NOT NULL) AS to_a_candidate,
    sum(amount) FILTER (WHERE race_id IS NOT NULL) AS to_a_race FROM co""")
```


**Q10a. Coordinated expenditures: rows and dollars, by filer cm type  (0 s)**

| cmte_tp | filers | rows | dollars | no_candidate_rows | no_candidate_dollars |
|---|---|---|---|---|---|
| Y | 43 | 806 | 89,062,707 | 12 | 127,332 |
| H | 1 | 2 | 85,250 | 0 |  |
| X | 1 | 2 | 9,480 | 0 |  |
| Q | 1 | 1 | 3,000 | 0 |  |
| N | 1 | 1 | 1,287 | 0 |  |

**Q10b. 24C memo lines silver drops, and 24C rows by MEMO_CD in pas2  (0 s)**

| MEMO_CD | rows | dollars |
|---|---|---|
| X | 282 | 1,414,204 |
|  | 812 | 89,161,724 |

**Q10c. The 20 largest party committees  (0 s)**

| committee_id | name | cm_type | rows | dollars | reported |
|---|---|---|---|---|---|
| C00003418 | REPUBLICAN NATIONAL COMMITTEE | Y | 7 | 29,255,723 | 29,255,724 |
| C00042366 | DSCC | Y | 35 | 18,385,083 | 18,385,086 |
| C00010603 | DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE | Y | 132 | 13,860,122 | 13,860,160 |
| C00027466 | NRSC | Y | 40 | 13,174,028 | 13,174,035 |
| C00000935 | DCCC | Y | 81 | 5,357,091 | 5,357,093 |
| C00255695 | LIBERTARIAN NATIONAL COMMITTEE, INC. | Y | 290 | 3,543,622 | 3,543,694 |
| C00075820 | NRCC | Y | 37 | 2,966,686 | 2,966,688 |
| C00143230 | NEW YORK STATE DEMOCRATIC COMMITTEE | Y | 46 | 556,207 | 556,214 |
| C00008664 | MISSOURI REPUBLICAN STATE COMMITTEE-FEDERAL | Y | 5 | 348,313 | 348,315 |
| C00141812 | DEMOCRATIC STATE CENTRAL COMMITTEE OF MARYLAND | Y | 7 | 196,549 | 196,551 |
| C00136457 | NEW HAMPSHIRE REPUBLICAN STATE COMMITTEE | Y | 2 | 160,000 | 160,000 |
| C00099259 | REPUBLICAN PARTY OF FLORIDA | Y | 2 | 118,000 | 118,000 |
| C00044842 | REPUBLICAN FEDERAL COMMITTEE OF PENNSYLVANIA | Y | 1 | 109,400 | 109,400 |
| C00140590 | CALIFORNIA REPUBLICAN PARTY FEDERAL ACCT. | Y | 1 | 100,000 | 100,000 |
| C00104471 | NEW JERSEY DEMOCRATIC STATE COMMITTEE | Y | 7 | 96,100 | 96,100 |
| C00772335 | JEFF BUONGIORNO FOR CONGRESS | H | 2 | 85,250 |  |
| C00033134 | COLORADO REPUBLICAN COMMITTEE | Y | 5 | 80,556 | 80,557 |
| C00007658 | DEMOCRATIC PARTY OF SOUTH CAROLINA | Y | 10 | 73,078 | 73,081 |
| C00155952 | DEMOCRATIC PARTY OF VIRGINIA | Y | 22 | 69,963 | 69,968 |
| C00136200 | RHODE ISLAND DEMOCRATIC STATE COMMITTEE | Y | 6 | 58,917 | 58,917 |

**Q10d. The 20 largest candidates  (0 s)**

| candidate_id | name | race | rows | dollars | committees |
|---|---|---|---|---|---|
| P80001571 | TRUMP, DONALD J. | 2024-P-US-00 | 7 | 29,255,723 | 1 |
| P80000722 | BIDEN, JOSEPH R JR | 2024-P-US-00 | 78 | 8,514,149 | 1 |
| S4TX00722 | ALLRED, COLIN | 2024-S-TX-00 | 6 | 5,600,000 | 1 |
| P00009423 | HARRIS, KAMALA | 2024-P-US-00 | 52 | 5,285,094 | 1 |
| P40011793 | KENNEDY, ROBERT, F. JR., SHANAHAN, NICOLE | 2024-P-US-00 | 289 | 3,542,403 | 1 |
| S2TX00312 | CRUZ, RAFAEL EDWARD  TED | 2024-S-TX-00 | 3 | 2,835,501 | 1 |
| S6PA00217 | CASEY, ROBERT P. JR. | 2024-S-PA-00 | 6 | 2,550,018 | 1 |
| S2PA00661 | MCCORMICK, DAVE | 2024-S-PA-00 | 5 | 2,458,625 | 1 |
| S6OH00163 | BROWN, SHERROD | 2024-S-OH-00 | 2 | 2,276,000 | 1 |
| S4MI00470 | SLOTKIN, ELISSA | 2024-S-MI-00 | 1 | 1,959,000 | 1 |
| S4OH00192 | MORENO, BERNIE | 2024-S-OH-00 | 2 | 1,928,697 | 1 |
| S4MI00595 | ROGERS, MICHAEL J | 2024-S-MI-00 | 7 | 1,589,974 | 1 |
| S4AZ00139 | GALLEGO, RUBEN | 2024-S-AZ-00 | 1 | 1,427,520 | 1 |
| S4MD00327 | ALSOBROOKS, ANGELA | 2024-S-MD-00 | 5 | 1,171,450 | 2 |
| S4MD00483 | HOGAN, LARRY | 2024-S-MD-00 | 15 | 1,170,997 | 1 |
| S2WI00219 | BALDWIN, TAMMY | 2024-S-WI-00 | 2 | 1,139,501 | 2 |
| S2WI00268 | HOVDE, ERIC D | 2024-S-WI-00 | 1 | 1,098,871 | 1 |
| S4FL00611 | MUCARSEL-POWELL, DEBBIE | 2024-S-FL-00 | 1 | 1,000,000 | 1 |
| S4AZ00220 | LAKE, KARI | 2024-S-AZ-00 | 2 | 604,125 | 1 |
| S2NV00308 | BROWN, SAM | 2024-S-NV-00 | 1 | 522,500 | 1 |

**Q10e. 24C from a filer that is not a party committee (cm type not X or Y)  (0 s)**

| committee_id | name | cm_type | rows | dollars |
|---|---|---|---|---|
| C00772335 | JEFF BUONGIORNO FOR CONGRESS | H | 2 | 85,250 |
| C00434076 | OPERATING ENGINEERS LOCAL 478 POLITICAL ACTION COMMITTEE (OE478PAC) | Q | 1 | 3,000 |
| C00410167 | CITY OF ALAMEDA DEMOCRATIC CLUB FEDERAL PAC | N | 1 | 1,287 |

**Q10f. Each committee's sum against reported_total.party_coordinated  (0 s)**

| band | committees | pas2_dollars | reported_dollars |
|---|---|---|---|
| within 1% | 45 | 89,073,474 | 89,073,644 |
| pas2 more than 1% below | 4 | 3,000 | 20,650 |
| no reported figure | 1 | 85,250 |  |

**Q10g. Committees more than 1% apart, by the gap  (0 s)**

| committee_id | cmte_nm | pas2 | reported | gap |
|---|---|---|---|---|
| C00772335 | JEFF BUONGIORNO FOR CONGRESS | 85,250 |  | 85,250 |
| C00625137 | CITZENS FOR AMERICAN ENERGY FEDERAL PAC | 0 | 7,500 | -7,500 |
| C00446294 | JCM PROPERTIES LP PAC | 0 | 5,000 | -5,000 |
| C00434076 | OPERATING ENGINEERS LOCAL 478 POLITICAL ACTION COMMITTEE (OE478PAC) | 3,000 | 8,000 | -5,000 |
| C00671313 | TUOLUMNE COUNTY DEMOCRATIC CENTRAL COMMITTEE | 0 | 150 | -150 |

**Q10h. The figure: counted coordinated expenditures, and those reaching a candidate of the cycle  (0 s)**

| rows | dollars | to_a_candidate | to_a_race |
|---|---|---|---|
| 812 | 89,161,724 | 89,034,392 | 88,084,906 |

Silver's coordinated rows are 812, $89,161,724, from 47 filers, 43 of them state and national party
committees (`cm` type `Y`). The 282 memo lines silver drops hold $1,414,204 (Q10b). Each party
committee matches its `reported_total.party_coordinated` to the dollar or within 1%. The four
more than 1% below report $20,650 and file $3,000. Three filers are not party committees: Jeff
Buongiorno for Congress files $85,250 of 24C (`cm` type `H`, no reported figure), an Operating
Engineers PAC $3,000, and a Democratic club $1,287 (Q10e). They are filer errors and small.
$89,034,392 names a candidate and $88,084,906 reaches a race of the cycle (Q10h).

**The figure NEU-2167's definition of done is within 1% of: $89,161,724.**

## Q11: across kinds (2024)

```python
# Q11: across kinds (2024): is one payment in two kinds?
h24(2024)
adopt_h24_rule(2024, "chain")
counted_pas2(2024)
ec_table(2024)
cc_table(2024)
silver("independent_expenditure", 2024)
con.execute("""
CREATE TABLE kinds AS
SELECT DISTINCT spe AS id, 'ie (pas2)' AS kind FROM p_2024
UNION ALL SELECT DISTINCT spe, 'ie (24/48-hour only)' FROM l_2024 WHERE spe NOT IN (SELECT spe FROM p_2024)
UNION ALL SELECT DISTINCT spon, 'electioneering' FROM ec_2024
UNION ALL SELECT DISTINCT filer, 'communication cost' FROM cc_2024
UNION ALL SELECT DISTINCT committee_id, 'coordinated' FROM silver_2024.independent_expenditure WHERE kind = 'coordinated'""")
show("Q11a. Spender ids in more than one kind", """
SELECT kinds, count(*) AS ids, string_agg(id, ', ' ORDER BY id) FILTER (WHERE true) AS example_ids
FROM (SELECT id, string_agg(kind, ' + ' ORDER BY kind) AS kinds FROM kinds GROUP BY 1 HAVING count(*) > 1)
GROUP BY 1 ORDER BY ids DESC""")
show("Q11b. Electioneering rows against 24/48-hour rows: same payee (first 12 letters), date and amount", """
SELECT count(*) AS ec_rows, sum(e.share) AS ec_dollars,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM l_2024 AS l WHERE l.amt = e.amt
        AND left(regexp_replace(upper(l.pay), '[^A-Z0-9]', '', 'g'), 12) = left(regexp_replace(upper(e.PAYEE_NAME), '[^A-Z0-9]', '', 'g'), 12)
        AND (l.edt = e.ddt OR l.ddt = e.ddt OR l.ddt = e.pdt))) AS matched_24_48_hour,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS p WHERE p.amt = trunc(e.amt)
        AND left(regexp_replace(upper(p.payee), '[^A-Z0-9]', '', 'g'), 12) = left(regexp_replace(upper(e.PAYEE_NAME), '[^A-Z0-9]', '', 'g'), 12)
        AND p.dt = e.ddt)) AS matched_pas2,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM l_2024 AS l WHERE l.amt = e.amt AND (l.edt = e.ddt OR l.ddt = e.ddt))) AS same_amount_and_date_any_payee
FROM ec_2024 AS e""")
show("Q11c. Electioneering sponsors in the 24/48-hour file or pas2 as spenders", """
SELECT spon, any_value(COMMITTEE_NAME) AS name, sum(share) AS ec_dollars,
    (SELECT sum(amt) FROM l_2024 WHERE spe = spon) AS h24_dollars, (SELECT sum(amt) FROM p_2024 WHERE spe = spon) AS pas2_dollars
FROM ec_2024 GROUP BY 1 HAVING spon IN (SELECT spe FROM l_2024) OR spon IN (SELECT spe FROM p_2024)""")
show("Q11d. Communication-cost rows against 24/48-hour rows: same filer, candidate and amount", """
SELECT count(*) AS cc_rows, sum(c.amt) AS cc_dollars,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM l_2024 AS l WHERE l.spe = c.filer AND l.amt = c.amt)) AS matched_by_filer,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM l_2024 AS l WHERE l.amt = c.amt AND l.cand = trim(c.CAND_ID)
        AND (l.edt = c.dt OR l.ddt = c.dt))) AS matched_by_candidate_amount_date_any_spender
FROM cc_2024 AS c""")
show("Q11e. Coordinated against independent expenditures: same committee, candidate, amount and date", """
SELECT count(*) AS coordinated_rows, sum(s.amount) AS dollars,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM p_2024 AS p WHERE p.spe = s.committee_id AND p.credited IS NOT DISTINCT FROM s.candidate_id
        AND p.amt = s.amount AND p.dt IS NOT DISTINCT FROM s.date)) AS also_an_ie
FROM silver_2024.independent_expenditure AS s WHERE s.kind = 'coordinated'""")
show("Q11f. The electioneering rows that match a pas2 independent expenditure by payee, date and amount", """
SELECT e.spon, e.COMMITTEE_NAME, e.PAYEE_NAME, e.ddt, e.amt, e.cand, p.spe, p.payee, p.dt, p.amt AS pas2_amt, p.raw_cand
FROM ec_2024 AS e JOIN p_2024 AS p ON p.amt = trunc(e.amt) AND p.dt = e.ddt
    AND left(regexp_replace(upper(p.payee), '[^A-Z0-9]', '', 'g'), 12) = left(regexp_replace(upper(e.PAYEE_NAME), '[^A-Z0-9]', '', 'g'), 12)""")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:07:00+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:07:00+00:00
ecraw_2024: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/CommunicationCosts_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:07 GMT | bytes 237,322 | downloaded 2026-11-24T02:07:00+00:00
ccraw_2024: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
```

**Q11a. Spender ids in more than one kind  (0 s)**

| kinds | ids | example_ids |
|---|---|---|
| coordinated + ie (pas2) | 13 | C00000935, C00006486, C00023838, C00027466, C00042366, C00071365, C00075820, C00082925, C00089243, C00099259, C00141812, C00350991, C00410167 |

**Q11b. Electioneering rows against 24/48-hour rows: same payee (first 12 letters), date and amount  (0 s)**

| ec_rows | ec_dollars | matched_24_48_hour | matched_pas2 | same_amount_and_date_any_payee |
|---|---|---|---|---|
| 69 | 9,480,874 | 0 | 2 | 9 |

**Q11c. Electioneering sponsors in the 24/48-hour file or pas2 as spenders  (0 s)**

| spon | name | ec_dollars | h24_dollars | pas2_dollars |
|---|---|---|---|---|

**Q11d. Communication-cost rows against 24/48-hour rows: same filer, candidate and amount  (0 s)**

| cc_rows | cc_dollars | matched_by_filer | matched_by_candidate_amount_date_any_spender |
|---|---|---|---|
| 779 | 7,098,726 | 0 | 1 |

**Q11e. Coordinated against independent expenditures: same committee, candidate, amount and date  (0 s)**

| coordinated_rows | dollars | also_an_ie |
|---|---|---|
| 812 | 89,161,724 | 0 |

**Q11f. The electioneering rows that match a pas2 independent expenditure by payee, date and amount  (0 s)**

| spon | COMMITTEE_NAME | PAYEE_NAME | ddt | amt | cand | spe | payee | dt | pas2_amt | raw_cand |
|---|---|---|---|---|---|---|---|---|---|---|
| C30003396 | STRAIGHT AHEAD ORGANIZATION | GUSTO | 2024-04-12 | 1,360 |  | C90022914 | GUSTO | 2024-04-12 | 1,360 | H2PA18200 |
| C30003396 | STRAIGHT AHEAD ORGANIZATION | GUSTO | 2024-04-11 | 91 |  | C90022914 | GUSTO | 2024-04-11 | 91 | H2PA18200 |

Thirteen spender ids are in two kinds: twelve party committees that both coordinate with their
candidate and spend independently, and a Democratic club (`C00410167`, `cm` type `N`). No coordinated row equals an independent expenditure of the
same committee, candidate, amount and date (Q11e). No electioneering sponsor files independent
expenditures under its own id (Q11c). Two electioneering rows of Straight Ahead Organization
(`C30003396`, $1,451 of payroll to Gusto) are also independent expenditures of its affiliate
`C90022914` (Q11f). No communication cost matches a 24/48-hour row by filer (Q11d).

**Decision line:** no cross-kind rule is needed. The one overlap is $1,451.

## Q12: every cycle's profile (2010–2026)

```python
# Q12: every cycle's profile, 2010-2026: its three CSVs fetched, profiled and deleted, with its
# bronze cm and pas2. One table per measure, a cycle per row.
REPEAT = "spon, PAYEE_NAME, DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, CANDIDATE_ID"
H24_HEADER = view_csv("hdr_h24", fec_csv("independent_expenditure", 2024))
EC_HEADER = view_csv("hdr_ec", fec_csv("ElectioneeringComm", 2024))
CC_HEADER = view_csv("hdr_cc", fec_csv("CommunicationCosts", 2024))
results: dict[str, list] = {}


def keep(table: str, cycle: int, sql: str) -> None:
    rel = con.sql(sql)
    cols = ["cycle"] + rel.columns
    results.setdefault(table, [cols])
    for row in rel.fetchall():
        results[table].append([str(cycle)] + list(row))


for cycle in range(2010, 2027, 2):
    paths_ = {stem: fec_csv(stem, cycle) for stem in ("independent_expenditure", "ElectioneeringComm", "CommunicationCosts")}
    meta = {stem: (p.with_name(p.name + ".meta").read_text().split(" | ")) for stem, p in paths_.items()}
    h24(cycle)
    adopt_h24_rule(cycle, "chain")
    ec_table(cycle)
    cc_table(cycle)
    bulk("pas2", cycle)
    headers = {
        "independent_expenditure": con.execute(f"DESCRIBE h24raw_{cycle}").fetchall(),
        "ElectioneeringComm": con.execute(f"DESCRIBE ecraw_{cycle}").fetchall(),
        "CommunicationCosts": con.execute(f"DESCRIBE ccraw_{cycle}").fetchall(),
    }
    same = {s: [c[0] for c in h] == want for (s, h), want in zip(headers.items(), (H24_HEADER, EC_HEADER, CC_HEADER))}
    for stem in paths_:
        results.setdefault("files", [["cycle", "file", "bytes", "Last-Modified", "header as 2024's"]])
        results["files"].append([str(cycle), stem, meta[stem][2].replace("bytes ", ""), meta[stem][1].replace("Last-Modified: ", ""), same[stem]])
    keep("rows", cycle, f"""SELECT
        (SELECT count(*) FROM h_{cycle}) AS h24_rows, (SELECT sum(amt) FROM h_{cycle}) AS h24_dollars,
        (SELECT sum(amt) FROM h_{cycle} WHERE NOT superseded AND coalesce(tran, '') NOT LIKE 'WFT%') AS h24_kept_less_web_form,
        (SELECT count(*) FROM ec_{cycle}) AS ec_rows, (SELECT sum(share) FROM ec_{cycle}) AS ec_dollars,
        (SELECT count(*) FROM cc_{cycle}) AS cc_rows, (SELECT sum(amt) FROM cc_{cycle}) AS cc_dollars,
        (SELECT count(*) FILTER (WHERE edt IS NULL AND exp_date IS NOT NULL) + count(*) FILTER (WHERE amt IS NULL)
         FROM h_{cycle}) AS h24_cast_fails""")
    keep("spenders", cycle, f"""SELECT
        count(DISTINCT spe) FILTER (WHERE grp = 'committee') AS committee, count(DISTINCT spe) FILTER (WHERE grp = 'type I') AS type_i,
        count(DISTINCT spe) FILTER (WHERE grp = 'absent') AS absent,
        sum(amt) FILTER (WHERE grp = 'committee') AS committee_dollars, sum(amt) FILTER (WHERE grp = 'type I') AS type_i_dollars,
        sum(amt) FILTER (WHERE grp = 'absent') AS absent_dollars,
        sum(amt) FILTER (WHERE coalesce(tran, '') LIKE 'WFT%') AS web_form_dollars
    FROM l_{cycle}""")
    keep("amendments", cycle, f"""SELECT
        count(*) FILTER (WHERE amndt_ind = 'N') AS n_rows, count(*) FILTER (WHERE amndt_ind LIKE 'A%') AS a_rows,
        count(*) FILTER (WHERE amndt_ind NOT IN ('N') AND amndt_ind NOT LIKE 'A%' OR amndt_ind IS NULL) AS other_rows,
        count(*) FILTER (WHERE pfnum IS NOT NULL) AS with_prev_file_num,
        sum(amt) FILTER (WHERE NOT superseded) AS chain_kept, sum(amt) FILTER (WHERE superseded) AS chain_dropped,
        sum(amt) FILTER (WHERE latest_tran) AS per_tran_kept
    FROM h_{cycle}""")
    # Rung 1 against raw pas2's counted rows (24A/24E, no memo line, filer in cm), no silver.
    keep("rung1", cycle, f"""
    WITH p AS (SELECT trim(CMTE_ID) AS spe, nullif(trim(TRAN_ID), '') AS tran, sum(TRANSACTION_AMT) AS d
               FROM pas2_{cycle} WHERE TRANSACTION_TP IN ('24A', '24E') AND coalesce(MEMO_CD, '') <> 'X'
                   AND CMTE_ID IN (SELECT id FROM grp_{cycle}) GROUP BY 1, 2),
         l AS (SELECT spe, tran, sum(amt) AS d FROM l_{cycle} WHERE coalesce(tran, '') NOT LIKE 'WFT%' GROUP BY 1, 2)
    SELECT (SELECT sum(d) FROM p) AS pas2_ie_dollars, (SELECT sum(d) FROM l) AS h24_dollars_less_web_form,
        (SELECT sum(l.d) FROM l JOIN p USING (spe, tran)) AS h24_rung1_dollars,
        ((SELECT sum(l.d) FROM l JOIN p USING (spe, tran)) / (SELECT sum(d) FROM l))::DOUBLE AS h24_rung1_share,
        ((SELECT sum(p.d) FROM p JOIN l USING (spe, tran)) / (SELECT sum(d) FROM p))::DOUBLE AS pas2_rung1_share,
        (SELECT sum(l.d) FROM l WHERE spe NOT IN (SELECT spe FROM p)) AS h24_at_spenders_not_in_pas2""")
    keep("electioneering", cycle, f"""SELECT count(DISTINCT spon) AS sponsors,
        count(*) FILTER (WHERE grp <> 'committee') AS rows_non_committee_sponsor,
        count(*) FILTER (WHERE cand IS NULL) AS blank_candidate_rows, sum(share) FILTER (WHERE cand IS NULL) AS blank_candidate_dollars,
        (sum(share) FILTER (WHERE ncand > 1) / sum(share))::DOUBLE AS multi_candidate_share,
        (SELECT count(*) FROM (SELECT 1 FROM ec_{cycle} GROUP BY {REPEAT} HAVING count(DISTINCT SB_IMAGE_NUM) > 1)) AS repeat_groups,
        count(*) FILTER (WHERE abs(share * ncand - amt) > 0.01) AS split_off_by_a_cent
    FROM ec_{cycle}""")
    keep("comm_costs", cycle, f"""
    WITH p AS (SELECT SUB_ID AS sid, TRANSACTION_AMT AS amt FROM pas2_published_{cycle} WHERE TRANSACTION_TP IN ('24F', '24N'))
    SELECT count(*) FILTER (WHERE p.sid IS NOT NULL AND c.sid IS NOT NULL AND abs(c.amt - p.amt) < 1) AS both_amount_within_1,
        count(*) FILTER (WHERE p.sid IS NOT NULL AND c.sid IS NOT NULL AND abs(c.amt - p.amt) >= 1) AS both_amount_differs,
        count(*) FILTER (WHERE p.sid IS NULL) AS only_csv, count(*) FILTER (WHERE c.sid IS NULL) AS only_pas2,
        sum(c.amt) FILTER (WHERE p.sid IS NULL) AS only_csv_dollars, sum(p.amt) FILTER (WHERE c.sid IS NULL) AS only_pas2_dollars,
        (sum(c.amt) FILTER (WHERE p.sid IS NOT NULL AND abs(c.amt - p.amt) < 1) / sum(c.amt))::DOUBLE AS csv_dollars_in_pas2
    FROM cc_{cycle} AS c FULL JOIN p ON p.sid = c.sid""")
    keep("pas2_kinds", cycle, f"""SELECT
        count(*) FILTER (WHERE TRANSACTION_TP = '24C' AND coalesce(MEMO_CD, '') <> 'X') AS coordinated_rows,
        sum(TRANSACTION_AMT) FILTER (WHERE TRANSACTION_TP = '24C' AND coalesce(MEMO_CD, '') <> 'X') AS coordinated_dollars,
        count(*) FILTER (WHERE TRANSACTION_TP IN ('24F', '24N') AND coalesce(MEMO_CD, '') <> 'X') AS comm_cost_rows,
        sum(TRANSACTION_AMT) FILTER (WHERE TRANSACTION_TP IN ('24F', '24N') AND coalesce(MEMO_CD, '') <> 'X') AS comm_cost_dollars,
        count(*) FILTER (WHERE TRANSACTION_TP IN ('24A', '24E') AND coalesce(MEMO_CD, '') <> 'X') AS ie_rows,
        sum(TRANSACTION_AMT) FILTER (WHERE TRANSACTION_TP IN ('24A', '24E') AND coalesce(MEMO_CD, '') <> 'X') AS ie_dollars
    FROM pas2_{cycle}""")
    # Delete the cycle's files and tables (2024's CSVs stay for the later blocks).
    if cycle != 2024:
        for p in paths_.values():
            p.unlink()
            p.with_name(p.name + ".meta").unlink()
        for f in work.glob(f"*raw_{cycle}.utf8.csv"):
            f.unlink()
    for t in con.execute(f"SELECT table_name FROM duckdb_tables() WHERE table_name LIKE '%\\_{cycle}%' ESCAPE '\\'").fetchall():
        con.execute(f"DROP TABLE {t[0]}")
    print(f"profiled {cycle}", dt.datetime.now(dt.UTC).isoformat(timespec="seconds"))


def fmt(v: object) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, Decimal)):
        return f"{v:,.0f}"
    if isinstance(v, float):
        return f"{v:.2%}"
    return "" if v is None else str(v)


titles = {
    "files": "Q12a. Files: bytes, Last-Modified, header equal to 2024's",
    "rows": "Q12b. Rows and dollars per file (24/48-hour kept: latest-amendment by the chain, web-form ids aside)",
    "spenders": "Q12c. 24/48-hour spenders by group (latest-amendment rows)",
    "amendments": "Q12d. 24/48-hour amendments: amndt_ind mix, and the chain rule's kept and dropped dollars",
    "rung1": "Q12e. Rung 1 against raw pas2's 24A/24E (spender, tran_id), web-form ids aside",
    "electioneering": "Q12f. Electioneering: sponsors, blank candidates, multi-candidate share, repeat groups",
    "comm_costs": "Q12g. Communication costs: the CSV against pas2's 24F/24N by SUB_ID (Q8's buckets, amounts within $1)",
    "pas2_kinds": "Q12h. pas2's own rows by kind (memo lines aside)",
}
for key, title in titles.items():
    rows = results[key]
    print(f"\n**{title}**\n")
    print("| " + " | ".join(rows[0]) + " |")
    print("|" + "---|" * len(rows[0]))
    for row in rows[1:]:
        print("| " + " | ".join(fmt(v) for v in row) + " |")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
hdr_h24: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:10:51+00:00
hdr_ec: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/CommunicationCosts_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:07 GMT | bytes 237,322 | downloaded 2026-11-24T02:10:53+00:00
hdr_cc: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2010/independent_expenditure_2010.csv | Last-Modified: Mon, 23 Nov 2026 10:13:15 GMT | bytes 11,437,199 | downloaded 2026-11-24T02:37:46+00:00
https://www.fec.gov/files/bulk-downloads/2010/ElectioneeringComm_2010.csv | Last-Modified: Mon, 23 Nov 2026 10:12:09 GMT | bytes 160,783 | downloaded 2026-11-24T02:37:14+00:00
https://www.fec.gov/files/bulk-downloads/2010/CommunicationCosts_2010.csv | Last-Modified: Mon, 23 Nov 2026 10:11:58 GMT | bytes 1,819,157 | downloaded 2026-11-24T02:37:48+00:00
https://www.fec.gov/files/bulk-downloads/2010/independent_expenditure_2010.csv | Last-Modified: Mon, 23 Nov 2026 10:13:15 GMT | bytes 11,437,199 | downloaded 2026-11-24T02:37:46+00:00
h24raw_2010: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2010/ElectioneeringComm_2010.csv | Last-Modified: Mon, 23 Nov 2026 10:12:09 GMT | bytes 160,783 | downloaded 2026-11-24T02:37:14+00:00
ecraw_2010: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2010/CommunicationCosts_2010.csv | Last-Modified: Mon, 23 Nov 2026 10:11:58 GMT | bytes 1,819,157 | downloaded 2026-11-24T02:37:48+00:00
ccraw_2010: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2010 2026-11-24T02:37:50+00:00
https://www.fec.gov/files/bulk-downloads/2012/independent_expenditure_2012.csv | Last-Modified: Mon, 23 Nov 2026 10:13:17 GMT | bytes 26,951,945 | downloaded 2026-11-24T02:37:55+00:00
https://www.fec.gov/files/bulk-downloads/2012/ElectioneeringComm_2012.csv | Last-Modified: Mon, 23 Nov 2026 10:12:10 GMT | bytes 75,779 | downloaded 2026-11-24T02:37:15+00:00
https://www.fec.gov/files/bulk-downloads/2012/CommunicationCosts_2012.csv | Last-Modified: Mon, 23 Nov 2026 10:11:59 GMT | bytes 1,718,667 | downloaded 2026-11-24T02:37:57+00:00
https://www.fec.gov/files/bulk-downloads/2012/independent_expenditure_2012.csv | Last-Modified: Mon, 23 Nov 2026 10:13:17 GMT | bytes 26,951,945 | downloaded 2026-11-24T02:37:55+00:00
h24raw_2012: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2012/ElectioneeringComm_2012.csv | Last-Modified: Mon, 23 Nov 2026 10:12:10 GMT | bytes 75,779 | downloaded 2026-11-24T02:37:15+00:00
ecraw_2012: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2012/CommunicationCosts_2012.csv | Last-Modified: Mon, 23 Nov 2026 10:11:59 GMT | bytes 1,718,667 | downloaded 2026-11-24T02:37:57+00:00
ccraw_2012: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2012 2026-11-24T02:38:00+00:00
https://www.fec.gov/files/bulk-downloads/2014/independent_expenditure_2014.csv | Last-Modified: Mon, 23 Nov 2026 10:13:20 GMT | bytes 16,656,127 | downloaded 2026-11-24T02:38:04+00:00
https://www.fec.gov/files/bulk-downloads/2014/ElectioneeringComm_2014.csv | Last-Modified: Mon, 23 Nov 2026 10:12:11 GMT | bytes 10,506 | downloaded 2026-11-24T02:37:16+00:00
https://www.fec.gov/files/bulk-downloads/2014/CommunicationCosts_2014.csv | Last-Modified: Mon, 23 Nov 2026 10:12:01 GMT | bytes 1,136,509 | downloaded 2026-11-24T02:38:05+00:00
https://www.fec.gov/files/bulk-downloads/2014/independent_expenditure_2014.csv | Last-Modified: Mon, 23 Nov 2026 10:13:20 GMT | bytes 16,656,127 | downloaded 2026-11-24T02:38:04+00:00
h24raw_2014: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2014/ElectioneeringComm_2014.csv | Last-Modified: Mon, 23 Nov 2026 10:12:11 GMT | bytes 10,506 | downloaded 2026-11-24T02:37:16+00:00
ecraw_2014: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2014/CommunicationCosts_2014.csv | Last-Modified: Mon, 23 Nov 2026 10:12:01 GMT | bytes 1,136,509 | downloaded 2026-11-24T02:38:05+00:00
ccraw_2014: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2014 2026-11-24T02:38:07+00:00
https://www.fec.gov/files/bulk-downloads/2016/independent_expenditure_2016.csv | Last-Modified: Mon, 23 Nov 2026 10:13:22 GMT | bytes 42,350,280 | downloaded 2026-11-24T02:38:14+00:00
https://www.fec.gov/files/bulk-downloads/2016/ElectioneeringComm_2016.csv | Last-Modified: Mon, 23 Nov 2026 10:12:12 GMT | bytes 27,703 | downloaded 2026-11-24T02:37:18+00:00
https://www.fec.gov/files/bulk-downloads/2016/CommunicationCosts_2016.csv | Last-Modified: Mon, 23 Nov 2026 10:12:02 GMT | bytes 761,139 | downloaded 2026-11-24T02:38:15+00:00
https://www.fec.gov/files/bulk-downloads/2016/independent_expenditure_2016.csv | Last-Modified: Mon, 23 Nov 2026 10:13:22 GMT | bytes 42,350,280 | downloaded 2026-11-24T02:38:14+00:00
h24raw_2016: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2016/ElectioneeringComm_2016.csv | Last-Modified: Mon, 23 Nov 2026 10:12:12 GMT | bytes 27,703 | downloaded 2026-11-24T02:37:18+00:00
ecraw_2016: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2016/CommunicationCosts_2016.csv | Last-Modified: Mon, 23 Nov 2026 10:12:02 GMT | bytes 761,139 | downloaded 2026-11-24T02:38:15+00:00
ccraw_2016: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2016 2026-11-24T02:38:19+00:00
https://www.fec.gov/files/bulk-downloads/2018/independent_expenditure_2018.csv | Last-Modified: Mon, 23 Nov 2026 10:13:24 GMT | bytes 11,772,520 | downloaded 2026-11-24T02:38:22+00:00
https://www.fec.gov/files/bulk-downloads/2018/ElectioneeringComm_2018.csv | Last-Modified: Mon, 23 Nov 2026 10:12:13 GMT | bytes 51,662 | downloaded 2026-11-24T02:37:19+00:00
https://www.fec.gov/files/bulk-downloads/2018/CommunicationCosts_2018.csv | Last-Modified: Mon, 23 Nov 2026 10:12:03 GMT | bytes 411,037 | downloaded 2026-11-24T02:38:24+00:00
https://www.fec.gov/files/bulk-downloads/2018/independent_expenditure_2018.csv | Last-Modified: Mon, 23 Nov 2026 10:13:24 GMT | bytes 11,772,520 | downloaded 2026-11-24T02:38:22+00:00
h24raw_2018: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2018/ElectioneeringComm_2018.csv | Last-Modified: Mon, 23 Nov 2026 10:12:13 GMT | bytes 51,662 | downloaded 2026-11-24T02:37:19+00:00
ecraw_2018: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2018/CommunicationCosts_2018.csv | Last-Modified: Mon, 23 Nov 2026 10:12:03 GMT | bytes 411,037 | downloaded 2026-11-24T02:38:24+00:00
ccraw_2018: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2018 2026-11-24T02:38:26+00:00
https://www.fec.gov/files/bulk-downloads/2020/independent_expenditure_2020.csv | Last-Modified: Mon, 23 Nov 2026 10:13:26 GMT | bytes 21,357,680 | downloaded 2026-11-24T02:38:30+00:00
https://www.fec.gov/files/bulk-downloads/2020/ElectioneeringComm_2020.csv | Last-Modified: Mon, 23 Nov 2026 10:12:14 GMT | bytes 71,074 | downloaded 2026-11-24T02:37:20+00:00
https://www.fec.gov/files/bulk-downloads/2020/CommunicationCosts_2020.csv | Last-Modified: Mon, 23 Nov 2026 10:12:05 GMT | bytes 308,464 | downloaded 2026-11-24T02:38:31+00:00
https://www.fec.gov/files/bulk-downloads/2020/independent_expenditure_2020.csv | Last-Modified: Mon, 23 Nov 2026 10:13:26 GMT | bytes 21,357,680 | downloaded 2026-11-24T02:38:30+00:00
h24raw_2020: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2020/ElectioneeringComm_2020.csv | Last-Modified: Mon, 23 Nov 2026 10:12:14 GMT | bytes 71,074 | downloaded 2026-11-24T02:37:20+00:00
ecraw_2020: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2020/CommunicationCosts_2020.csv | Last-Modified: Mon, 23 Nov 2026 10:12:05 GMT | bytes 308,464 | downloaded 2026-11-24T02:38:31+00:00
ccraw_2020: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2020 2026-11-24T02:38:35+00:00
https://www.fec.gov/files/bulk-downloads/2022/independent_expenditure_2022.csv | Last-Modified: Mon, 23 Nov 2026 10:13:28 GMT | bytes 16,646,736 | downloaded 2026-11-24T02:38:39+00:00
https://www.fec.gov/files/bulk-downloads/2022/ElectioneeringComm_2022.csv | Last-Modified: Mon, 23 Nov 2026 10:12:15 GMT | bytes 11,977 | downloaded 2026-11-24T02:37:21+00:00
https://www.fec.gov/files/bulk-downloads/2022/CommunicationCosts_2022.csv | Last-Modified: Mon, 23 Nov 2026 10:12:06 GMT | bytes 1,280,869 | downloaded 2026-11-24T02:38:40+00:00
https://www.fec.gov/files/bulk-downloads/2022/independent_expenditure_2022.csv | Last-Modified: Mon, 23 Nov 2026 10:13:28 GMT | bytes 16,646,736 | downloaded 2026-11-24T02:38:39+00:00
h24raw_2022: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2022/ElectioneeringComm_2022.csv | Last-Modified: Mon, 23 Nov 2026 10:12:15 GMT | bytes 11,977 | downloaded 2026-11-24T02:37:21+00:00
ecraw_2022: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2022/CommunicationCosts_2022.csv | Last-Modified: Mon, 23 Nov 2026 10:12:06 GMT | bytes 1,280,869 | downloaded 2026-11-24T02:38:40+00:00
ccraw_2022: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2022 2026-11-24T02:38:44+00:00
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:10:51+00:00
https://www.fec.gov/files/bulk-downloads/2024/CommunicationCosts_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:07 GMT | bytes 237,322 | downloaded 2026-11-24T02:10:53+00:00
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:10:51+00:00
ecraw_2024: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/CommunicationCosts_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:07 GMT | bytes 237,322 | downloaded 2026-11-24T02:10:53+00:00
ccraw_2024: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2024 2026-11-24T02:38:47+00:00
https://www.fec.gov/files/bulk-downloads/2026/independent_expenditure_2026.csv | Last-Modified: Mon, 23 Nov 2026 10:13:33 GMT | bytes 13,733,351 | downloaded 2026-11-24T02:36:58+00:00
https://www.fec.gov/files/bulk-downloads/2026/ElectioneeringComm_2026.csv | Last-Modified: Mon, 23 Nov 2026 10:12:17 GMT | bytes 13,079 | downloaded 2026-11-24T02:37:23+00:00
https://www.fec.gov/files/bulk-downloads/2026/CommunicationCosts_2026.csv | Last-Modified: Mon, 23 Nov 2026 10:12:08 GMT | bytes 48,982 | downloaded 2026-11-24T02:38:48+00:00
https://www.fec.gov/files/bulk-downloads/2026/independent_expenditure_2026.csv | Last-Modified: Mon, 23 Nov 2026 10:13:33 GMT | bytes 13,733,351 | downloaded 2026-11-24T02:36:58+00:00
h24raw_2026: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2026/ElectioneeringComm_2026.csv | Last-Modified: Mon, 23 Nov 2026 10:12:17 GMT | bytes 13,079 | downloaded 2026-11-24T02:37:23+00:00
ecraw_2026: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2026/CommunicationCosts_2026.csv | Last-Modified: Mon, 23 Nov 2026 10:12:08 GMT | bytes 48,982 | downloaded 2026-11-24T02:38:48+00:00
ccraw_2026: 25 columns: CMTE_ID, CMTE_NM, CAND_ID, CAND_NAME, CAND_OFFICE, CAND_STATE, CAND_OFFICE_DISTRICT, CAND_PTY_AFFILIATION, TRANSACTION_DT, TRANSACTION_AMT, TRANSACTION_TP, COMMUNICATION_TP, COMMUNICATION_CLASS, SUPPORT_OPPOSE_IND, IMAGE_NUM, LINE_NUM, FORM_TP_CD, SCHED_TP_CD, TRAN_ID, SUB_ID, FILE_NUM, RPT_YR, CAND_STATE_DESCRIPTION, CAND_PTY_AFFILIATION_DESCRIPTION, PURPOSE; records of another width: 0
profiled 2026 2026-11-24T02:38:49+00:00
```

**Q12a. Files: bytes, Last-Modified, header equal to 2024's**

| cycle | file | bytes | Last-Modified | header as 2024's |
|---|---|---|---|---|
| 2010 | independent_expenditure | 11,437,199 | Mon, 23 Nov 2026 10:13:15 GMT | yes |
| 2010 | ElectioneeringComm | 160,783 | Mon, 23 Nov 2026 10:12:09 GMT | yes |
| 2010 | CommunicationCosts | 1,819,157 | Mon, 23 Nov 2026 10:11:58 GMT | yes |
| 2012 | independent_expenditure | 26,951,945 | Mon, 23 Nov 2026 10:13:17 GMT | yes |
| 2012 | ElectioneeringComm | 75,779 | Mon, 23 Nov 2026 10:12:10 GMT | yes |
| 2012 | CommunicationCosts | 1,718,667 | Mon, 23 Nov 2026 10:11:59 GMT | yes |
| 2014 | independent_expenditure | 16,656,127 | Mon, 23 Nov 2026 10:13:20 GMT | yes |
| 2014 | ElectioneeringComm | 10,506 | Mon, 23 Nov 2026 10:12:11 GMT | yes |
| 2014 | CommunicationCosts | 1,136,509 | Mon, 23 Nov 2026 10:12:01 GMT | yes |
| 2016 | independent_expenditure | 42,350,280 | Mon, 23 Nov 2026 10:13:22 GMT | yes |
| 2016 | ElectioneeringComm | 27,703 | Mon, 23 Nov 2026 10:12:12 GMT | yes |
| 2016 | CommunicationCosts | 761,139 | Mon, 23 Nov 2026 10:12:02 GMT | yes |
| 2018 | independent_expenditure | 11,772,520 | Mon, 23 Nov 2026 10:13:24 GMT | yes |
| 2018 | ElectioneeringComm | 51,662 | Mon, 23 Nov 2026 10:12:13 GMT | yes |
| 2018 | CommunicationCosts | 411,037 | Mon, 23 Nov 2026 10:12:03 GMT | yes |
| 2020 | independent_expenditure | 21,357,680 | Mon, 23 Nov 2026 10:13:26 GMT | yes |
| 2020 | ElectioneeringComm | 71,074 | Mon, 23 Nov 2026 10:12:14 GMT | yes |
| 2020 | CommunicationCosts | 308,464 | Mon, 23 Nov 2026 10:12:05 GMT | yes |
| 2022 | independent_expenditure | 16,646,736 | Mon, 23 Nov 2026 10:13:28 GMT | yes |
| 2022 | ElectioneeringComm | 11,977 | Mon, 23 Nov 2026 10:12:15 GMT | yes |
| 2022 | CommunicationCosts | 1,280,869 | Mon, 23 Nov 2026 10:12:06 GMT | yes |
| 2024 | independent_expenditure | 19,534,174 | Mon, 23 Nov 2026 10:13:30 GMT | yes |
| 2024 | ElectioneeringComm | 18,370 | Mon, 23 Nov 2026 10:12:16 GMT | yes |
| 2024 | CommunicationCosts | 237,322 | Mon, 23 Nov 2026 10:12:07 GMT | yes |
| 2026 | independent_expenditure | 13,733,351 | Mon, 23 Nov 2026 10:13:33 GMT | yes |
| 2026 | ElectioneeringComm | 13,079 | Mon, 23 Nov 2026 10:12:17 GMT | yes |
| 2026 | CommunicationCosts | 48,982 | Mon, 23 Nov 2026 10:12:08 GMT | yes |

**Q12b. Rows and dollars per file (24/48-hour kept: latest-amendment by the chain, web-form ids aside)**

| cycle | h24_rows | h24_dollars | h24_kept_less_web_form | ec_rows | ec_dollars | cc_rows | cc_dollars | h24_cast_fails |
|---|---|---|---|---|---|---|---|---|
| 2010 | 48,328 | 392,402,654 | 385,033,130 | 654 | 71,692,553 | 5,947 | 25,075,936 | 0 |
| 2012 | 113,386 | 1,470,963,320 | 1,113,966,463 | 288 | 15,392,078 | 5,791 | 25,867,394 | 0 |
| 2014 | 68,234 | 827,758,177 | 672,509,131 | 40 | 7,545,119 | 3,961 | 9,137,001 | 0 |
| 2016 | 171,405 | 1,936,239,656 | 1,523,000,783 | 97 | 9,785,808 | 2,382 | 17,878,692 | 12 |
| 2018 | 45,039 | 1,395,449,941 | 1,265,233,671 | 212 | 14,713,765 | 1,344 | 4,357,183 | 1 |
| 2020 | 80,766 | 6,239,345,034 | 3,249,584,067 | 273 | 25,948,848 | 1,018 | 5,674,722 | 0 |
| 2022 | 61,779 | 46,938,881,729 | 2,227,298,095 | 45 | 4,599,212 | 4,416 | 11,799,495 | 0 |
| 2024 | 73,449 | 49,679,404,427 | 4,401,751,869 | 69 | 9,480,874 | 779 | 7,098,726 | 0 |
| 2026 | 51,401 | 42,833,503,954 | 4,023,647,820 | 48 | 5,966,538 | 165 | 1,505,169 | 0 |

**Q12c. 24/48-hour spenders by group (latest-amendment rows)**

| cycle | committee | type_i | absent | committee_dollars | type_i_dollars | absent_dollars | web_form_dollars |
|---|---|---|---|---|---|---|---|
| 2010 | 175 | 117 | 2 | 304,193,453 | 80,825,097 | 14,580 |  |
| 2012 | 359 | 187 | 1 | 965,529,462 | 303,655,370 | 65,500 | 155,283,869 |
| 2014 | 313 | 109 | 1 | 622,603,300 | 154,336,597 | 8,061 | 104,438,827 |
| 2016 | 457 | 182 | 3 | 1,480,203,132 | 196,547,046 | 132,713 | 153,882,108 |
| 2018 | 475 | 179 | 0 | 1,181,905,010 | 118,537,557 |  | 35,208,896 |
| 2020 | 773 | 208 | 3 | 3,185,591,993 | 107,299,458 | 1,735,041,910 | 1,778,349,294 |
| 2022 | 748 | 139 | 3 | 2,229,953,504 | 31,031,024 | 31,354,620,063 | 31,388,306,497 |
| 2024 | 834 | 159 | 8 | 14,331,813,741 | 86,206,678 | 33,921,078,677 | 43,937,347,227 |
| 2026 | 842 | 114 | 5 | 4,047,113,096 | 30,302,140 | 38,524,001,200 | 38,577,768,616 |

**Q12d. 24/48-hour amendments: amndt_ind mix, and the chain rule's kept and dropped dollars**

| cycle | n_rows | a_rows | other_rows | with_prev_file_num | chain_kept | chain_dropped | per_tran_kept |
|---|---|---|---|---|---|---|---|
| 2010 | 36,421 | 11,907 | 0 | 11,895 | 385,033,130 | 7,369,524 | 251,503,291 |
| 2012 | 100,153 | 13,233 | 0 | 13,233 | 1,269,250,332 | 201,712,988 | 972,998,228 |
| 2014 | 64,783 | 3,451 | 0 | 3,451 | 776,947,958 | 50,810,220 | 683,325,891 |
| 2016 | 159,186 | 12,219 | 0 | 12,137 | 1,676,882,891 | 259,356,765 | 1,397,330,290 |
| 2018 | 37,478 | 7,561 | 0 | 7,433 | 1,300,442,567 | 95,007,374 | 1,040,885,184 |
| 2020 | 68,429 | 12,337 | 0 | 12,327 | 5,027,933,361 | 1,211,411,672 | 4,467,681,537 |
| 2022 | 55,357 | 6,422 | 0 | 6,393 | 33,615,604,592 | 13,323,277,137 | 33,104,976,968 |
| 2024 | 60,573 | 12,876 | 0 | 12,867 | 48,339,099,096 | 1,340,305,331 | 47,928,877,999 |
| 2026 | 46,351 | 5,050 | 0 | 5,050 | 42,601,416,436 | 232,087,518 | 41,217,480,115 |

**Q12e. Rung 1 against raw pas2's 24A/24E (spender, tran_id), web-form ids aside**

| cycle | pas2_ie_dollars | h24_dollars_less_web_form | h24_rung1_dollars | h24_rung1_share | pas2_rung1_share | h24_at_spenders_not_in_pas2 |
|---|---|---|---|---|---|---|
| 2010 | 386,156,713 | 385,033,130 | 201,355,539 | 52.30% | 43.04% | 13,084,099 |
| 2012 | 1,232,936,482 | 1,113,966,463 | 653,952,271 | 58.70% | 33.78% | 4,879,676 |
| 2014 | 726,416,758 | 672,509,131 | 468,148,668 | 69.61% | 55.16% | 7,256,596 |
| 2016 | 1,561,920,011 | 1,523,000,783 | 869,195,018 | 57.07% | 47.88% | 24,721,452 |
| 2018 | 1,299,456,047 | 1,265,233,671 | 914,988,542 | 72.32% | 53.99% | 3,138,214 |
| 2020 | 3,252,530,502 | 3,249,584,067 | 1,785,993,700 | 54.96% | 50.03% | 2,147,898 |
| 2022 | 2,237,737,365 | 2,227,298,095 | 1,151,382,313 | 51.69% | 50.19% | 1,375,395 |
| 2024 | 4,422,382,849 | 4,401,751,869 | 2,931,584,761 | 66.60% | 63.73% | 4,835,248 |
| 2026 | 1,933,630,447 | 4,023,647,820 | 1,228,603,328 | 30.53% | 61.94% | 168,402,549 |

**Q12f. Electioneering: sponsors, blank candidates, multi-candidate share, repeat groups**

| cycle | sponsors | rows_non_committee_sponsor | blank_candidate_rows | blank_candidate_dollars | multi_candidate_share | repeat_groups | split_off_by_a_cent |
|---|---|---|---|---|---|---|---|
| 2010 | 51 | 0 | 0 |  | 5.12% | 20 | 28 |
| 2012 | 30 | 0 | 0 |  | 28.11% | 12 | 16 |
| 2014 | 12 | 0 | 0 |  | 13.46% | 1 | 0 |
| 2016 | 24 | 0 | 34 | 7,334,858 | 8.61% | 3 | 0 |
| 2018 | 24 | 0 | 98 | 5,497,004 | 5.66% | 1 | 10 |
| 2020 | 34 | 0 | 94 | 2,513,866 | 9.86% | 5 | 0 |
| 2022 | 10 | 0 | 11 | 1,444,034 | 9.31% | 0 | 0 |
| 2024 | 25 | 0 | 24 | 2,179,759 | 3.48% | 2 | 0 |
| 2026 | 8 | 0 | 16 | 925,154 | 0.62% | 3 | 0 |

**Q12g. Communication costs: the CSV against pas2's 24F/24N by SUB_ID (Q8's buckets, amounts within $1)**

| cycle | both_amount_within_1 | both_amount_differs | only_csv | only_pas2 | only_csv_dollars | only_pas2_dollars | csv_dollars_in_pas2 |
|---|---|---|---|---|---|---|---|
| 2010 | 5,947 | 0 | 0 | 3 |  | 363 | 100.00% |
| 2012 | 5,791 | 0 | 0 | 6 |  | 5,815 | 100.00% |
| 2014 | 3,961 | 0 | 0 | 53 |  | 32,087 | 100.00% |
| 2016 | 2,382 | 0 | 0 | 19 |  | 97,318 | 100.00% |
| 2018 | 1,344 | 0 | 0 | 10 |  | 6,938 | 100.00% |
| 2020 | 1,018 | 0 | 0 | 4 |  | 2,290 | 100.00% |
| 2022 | 4,415 | 0 | 0 | 112 |  | 448,303 | 100.00% |
| 2024 | 779 | 0 | 0 | 20 |  | 59,480 | 100.00% |
| 2026 | 165 | 0 | 0 | 6 |  | 3,808 | 100.00% |

**Q12h. pas2's own rows by kind (memo lines aside)**

| cycle | coordinated_rows | coordinated_dollars | comm_cost_rows | comm_cost_dollars | ie_rows | ie_dollars |
|---|---|---|---|---|---|---|
| 2010 | 3,982 | 52,233,795 | 5,950 | 25,074,105 | 43,524 | 386,156,713 |
| 2012 | 1,959 | 72,575,053 | 5,797 | 25,870,778 | 114,776 | 1,232,936,482 |
| 2014 | 2,236 | 25,094,842 | 4,014 | 9,167,880 | 69,728 | 726,416,758 |
| 2016 | 1,586 | 80,182,155 | 2,400 | 17,974,421 | 234,546 | 1,561,920,011 |
| 2018 | 1,260 | 39,092,197 | 1,354 | 4,363,583 | 55,536 | 1,299,456,047 |
| 2020 | 1,246 | 87,045,042 | 1,022 | 5,676,617 | 80,653 | 3,252,530,502 |
| 2022 | 705 | 42,327,712 | 4,528 | 12,245,899 | 72,054 | 2,237,737,365 |
| 2024 | 812 | 89,161,724 | 799 | 7,157,987 | 73,841 | 4,422,382,849 |
| 2026 | 2,708 | 351,217,482 | 171 | 1,508,953 | 28,935 | 1,933,630,447 |

Every header equals 2024's in every cycle (Q12a), and only 2016 and 2018 have cells that fail a
cast (12 and 1, Q12b). Every communication-costs row is a `pas2` row in every cycle, but one 2022 row that
none of Q12g's buckets holds, and `pas2` has a few rows the CSV lacks (Q12g). The rules hold with these differences:

- **Hoaxes begin in 2020.** `absent` spenders hold $1.74B in 2020, $31.4B in 2022, $33.9B in
  2024 and $38.5B in 2026 (Q12c). Before 2020 they are under $133,000 a cycle. Q6's screen is
  needed from 2020 on.
- **The chain rule drops more in 2022** ($13.3B, hoaxes amended by hoaxes) **and 2020** ($1.21B).
  The per-transaction rule keeps less than the chain in every cycle, by $93.6M (2014) to $1.38B
  (2026) (Q12d). Q3's finding is not 2024's alone.
- **Rung 1 alone matches half to two thirds of the 24/48-hour file in every cycle** (52%–72%; 2026
  31%, its periodic reports not yet in). The 24/48-hour rows at spenders absent from `pas2`, before
  any screen, run from $1.4M (2022) to $24.7M (2016). 2026 holds $168.4M, which is Q7's timeliness
  (Q12e).
- **Electioneering:** blank-candidate rows begin in 2016. 2010 and 2012 have 28 and 16 rows whose
  split is off by over a cent, and 2018 has 10. Repeat groups peak in 2010 (20) and 2012 (12) (Q12f).
  Every 2024 rule applies there, with the split taken as filed.
- **2026's coordinated expenditures are four times 2024's** ($351,217,482, Q12h), with the cycle not
  over.

**No cycle breaks a 2024 rule as written.** The hoaxes of 2020 on are the one change, and Q6's
screen covers it. NEU-2180's backfill should expect the per-transaction rule to fail in every cycle.

## Q13: five Senate races (2024)

```python
# Q13: five 2024 Senate races, per candidate, every kind.
h24(2024)
adopt_h24_rule(2024, "chain")
counted_pas2(2024)
ec_table(2024)
silver("independent_expenditure", 2024)
silver("reported_total", 2024)
added = work / "added_2024.parquet"
con.execute(f"CREATE TABLE added AS SELECT * FROM read_parquet({literal(added)})")
with psycopg.connect(settings.database_url) as pg:
    pg.read_only = True
    races = pg.execute("""SELECT race_id, ie_support + ie_oppose AS ie, ie_support, ie_oppose FROM gold.race
        WHERE cycle = 2024 AND office = 'S' AND NOT is_special ORDER BY ie_support + ie_oppose DESC LIMIT 12""").fetchall()
    rc = pg.execute("""SELECT rc.race_id, rc.candidate_id, rc.name, rc.party, rc.ie_support, rc.ie_oppose
        FROM gold.race_candidate AS rc JOIN gold.race AS r USING (race_id)
        WHERE r.cycle = 2024 AND r.office = 'S' AND NOT r.is_special""").fetchall()
con.execute("CREATE TABLE ranking (race_id VARCHAR, ie DECIMAL(16,2), ie_support DECIMAL(16,2), ie_oppose DECIMAL(16,2))")
con.executemany("INSERT INTO ranking VALUES (?, ?, ?, ?)", races)
con.execute("CREATE TABLE rc (race_id VARCHAR, candidate_id VARCHAR, name VARCHAR, party VARCHAR, ie_support DECIMAL(16,2), ie_oppose DECIMAL(16,2))")
con.executemany("INSERT INTO rc VALUES (?, ?, ?, ?, ?, ?)", rc)
# The screened added rows (Q6): spender reports IE, and its 24/48-hour total is within 10x of it.
con.execute("""CREATE VIEW added_ok AS SELECT * FROM added WHERE spe IN (SELECT spe FROM added GROUP BY 1
    HAVING any_value(reported_ie) > 0 AND sum(amt) <= 10 * any_value(reported_ie))""")
# Electioneering shares through the alias, with Q9's rule (no row dropped in 2024's file but the
# restated pair on the superseded Form 9, which names House candidates).
con.execute("""CREATE VIEW ecs AS SELECT e.*, coalesce(c.alias_of, e.cand) AS candidate_id, c2.race_id
    FROM ec_2024 AS e LEFT JOIN (SELECT candidate_id, any_value(alias_of) AS alias_of FROM silver_2024.candidate GROUP BY 1) AS c
        ON c.candidate_id = e.cand
    LEFT JOIN (SELECT candidate_id, any_value(race_id) AS race_id FROM silver_2024.candidate GROUP BY 1) AS c2
        ON c2.candidate_id = coalesce(c.alias_of, e.cand)""")
show("Q13a. The ranking: 2024 regular Senate races by live gold ie_support + ie_oppose, and which kinds each holds", """
SELECT row_number() OVER (ORDER BY r.ie DESC) AS rank, r.race_id, r.ie, r.ie_support, r.ie_oppose,
    (SELECT count(*) FROM ecs WHERE ecs.race_id = r.race_id) AS ec_rows,
    (SELECT count(*) FROM silver_2024.independent_expenditure AS s WHERE s.race_id = r.race_id AND s.kind = 'communication_cost') AS cc_rows,
    (SELECT count(*) FROM silver_2024.independent_expenditure AS s WHERE s.race_id = r.race_id AND s.kind = 'coordinated') AS coordinated_rows,
    (SELECT count(DISTINCT p.spe) FROM p_2024 AS p WHERE p.race_id = r.race_id AND p.grp <> 'committee') AS non_committee_spenders_pas2,
    (SELECT count(DISTINCT a.spe) FROM added_ok AS a WHERE a.race_id = r.race_id) AS added_spenders
FROM ranking AS r ORDER BY rank""")
FIVE = [r[0] for r in con.execute("SELECT race_id FROM ranking ORDER BY ie DESC LIMIT 5").fetchall()]
five = ", ".join(f"'{r}'" for r in FIVE)
print("\nThe five:", FIVE, "- between them every kind and a non-committee spender (Q13a), so none is swapped.")
show("Q13b. Per candidate, every kind: live gold IE, what the 24/48-hour rule adds (screened, Q6), electioneering shares, communication costs and coordinated expenditures", f"""
WITH s AS (SELECT candidate_id, kind, support_oppose, sum(amount) AS d FROM silver_2024.independent_expenditure
           WHERE race_id IN ({five}) GROUP BY ALL),
     a AS (SELECT acand AS candidate_id, sup_opp, sum(amt) AS d FROM added_ok WHERE race_id IN ({five}) GROUP BY ALL),
     e AS (SELECT candidate_id, sum(share) AS d FROM ecs WHERE race_id IN ({five}) GROUP BY ALL)
SELECT rc.race_id, rc.candidate_id, rc.name, rc.party, rc.ie_support AS gold_ie_for, rc.ie_oppose AS gold_ie_against,
    coalesce((SELECT d FROM a WHERE a.candidate_id = rc.candidate_id AND sup_opp = 'S'), 0) AS added_for,
    coalesce((SELECT d FROM a WHERE a.candidate_id = rc.candidate_id AND sup_opp = 'O'), 0) AS added_against,
    coalesce((SELECT d FROM e WHERE e.candidate_id = rc.candidate_id), 0) AS electioneering,
    coalesce((SELECT d FROM s WHERE s.candidate_id = rc.candidate_id AND kind = 'communication_cost' AND support_oppose = 'S'), 0) AS comm_cost_for,
    coalesce((SELECT d FROM s WHERE s.candidate_id = rc.candidate_id AND kind = 'communication_cost' AND support_oppose = 'O'), 0) AS comm_cost_against,
    coalesce((SELECT d FROM s WHERE s.candidate_id = rc.candidate_id AND kind = 'coordinated'), 0) AS coordinated,
    coalesce((SELECT d FROM s WHERE s.candidate_id = rc.candidate_id AND kind = 'ie' AND support_oppose = 'S'), 0) AS silver_ie_for,
    coalesce((SELECT d FROM s WHERE s.candidate_id = rc.candidate_id AND kind = 'ie' AND support_oppose = 'O'), 0) AS silver_ie_against
FROM rc WHERE rc.race_id IN ({five})
    AND (rc.ie_support + rc.ie_oppose > 0 OR rc.candidate_id IN (SELECT candidate_id FROM s UNION SELECT candidate_id FROM e UNION SELECT candidate_id FROM a))
ORDER BY rc.race_id, rc.ie_support + rc.ie_oppose DESC""")
show("Q13c. Per race, every kind", f"""
SELECT r.race_id, r.ie_support AS gold_ie_for, r.ie_oppose AS gold_ie_against,
    (SELECT sum(amt) FROM added_ok WHERE race_id = r.race_id) AS added,
    (SELECT sum(share) FROM ecs WHERE race_id = r.race_id) AS electioneering,
    (SELECT sum(amount) FROM silver_2024.independent_expenditure WHERE race_id = r.race_id AND kind = 'communication_cost') AS comm_costs,
    (SELECT sum(amount) FROM silver_2024.independent_expenditure WHERE race_id = r.race_id AND kind = 'coordinated') AS coordinated
FROM ranking AS r WHERE r.race_id IN ({five}) ORDER BY r.ie DESC""")
show("Q13d. Each race's non-committee spenders (type I or absent): in pas2, and added from the 24/48-hour file", f"""
SELECT race_id, spe, name, source, rows, dollars FROM (
    SELECT p.race_id, p.spe, (SELECT cmte_nm FROM grp_2024 WHERE id = p.spe) AS name, 'pas2' AS source,
        count(*) AS rows, sum(p.amt) AS dollars
    FROM p_2024 AS p WHERE p.race_id IN ({five}) AND p.grp <> 'committee' GROUP BY ALL
    UNION ALL
    SELECT a.race_id, a.spe, any_value(trim(a.spe_nam)), '24/48-hour (added)', count(*), sum(a.amt)
    FROM added_ok AS a WHERE a.race_id IN ({five}) GROUP BY a.race_id, a.spe)
ORDER BY race_id, dollars DESC""")
show("Q13e. Each race's electioneering sponsors", f"""
SELECT race_id, spon, any_value(COMMITTEE_NAME) AS name, candidate_id, count(*) AS rows, sum(share) AS dollars
FROM ecs WHERE race_id IN ({five}) GROUP BY race_id, spon, candidate_id ORDER BY race_id, dollars DESC""")
```

```text
https://www.fec.gov/files/bulk-downloads/2024/independent_expenditure_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:13:30 GMT | bytes 19,534,174 | downloaded 2026-11-24T02:09:55+00:00
h24raw_2024: 23 columns: cand_id, cand_name, spe_id, spe_nam, ele_type, can_office_state, can_office_dis, can_office, cand_pty_aff, exp_amo, exp_date, agg_amo, sup_opp, pur, pay, file_num, amndt_ind, tran_id, image_num, receipt_dat, fec_election_yr, prev_file_num, dissem_dt; records of another width: 0
https://www.fec.gov/files/bulk-downloads/2024/ElectioneeringComm_2024.csv | Last-Modified: Mon, 23 Nov 2026 10:12:16 GMT | bytes 18,370 | downloaded 2026-11-24T02:10:51+00:00
ecraw_2024: 19 columns: CANDIDATE_ID, CANDIDATE_NAME, CANDIDATE_OFFICE, CANDIDATE_STATE, CANDIDATE_DISTRICT, COMMITTEE_ID, COMMITTEE_NAME, SB_IMAGE_NUM, PAYEE_NAME, PAYEE_STREET, PAYEE_CITY, PAYEE_STATE, DISBURSEMENT_DESCRIPTION, DISBURSEMENT_DATE, COMMUNICATION_DATE, PUBLIC_DISBURSEMENT_DATE, REPORTED_DISBURSEMENT_AMOUNT, NUMBER_OF_CANDIDATES, CALCULATED_CANDIDATE_SHARE; records of another width: 0
```

**Q13a. The ranking: 2024 regular Senate races by live gold ie_support + ie_oppose, and which kinds each holds  (0 s)**

| rank | race_id | ie | ie_support | ie_oppose | ec_rows | cc_rows | coordinated_rows | non_committee_spenders_pas2 | added_spenders |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2024-S-OH-00 | 307,506,874 | 99,581,722 | 207,925,152 | 2 | 21 | 4 | 12 | 2 |
| 2 | 2024-S-PA-00 | 231,748,357 | 48,905,307 | 182,843,050 | 0 | 27 | 11 | 11 | 0 |
| 3 | 2024-S-MT-00 | 162,141,537 | 35,153,092 | 126,988,445 | 0 | 17 | 12 | 9 | 0 |
| 4 | 2024-S-MI-00 | 141,793,114 | 48,717,439 | 93,075,675 | 0 | 4 | 8 | 8 | 0 |
| 5 | 2024-S-WI-00 | 119,883,599 | 18,497,971 | 101,385,628 | 1 | 18 | 3 | 13 | 0 |
| 6 | 2024-S-NV-00 | 97,997,136 | 23,222,232 | 74,774,904 | 0 | 16 | 2 | 10 | 0 |
| 7 | 2024-S-AZ-00 | 77,822,085 | 26,475,245 | 51,346,840 | 0 | 12 | 3 | 13 | 0 |
| 8 | 2024-S-TX-00 | 55,361,524 | 20,202,681 | 35,158,843 | 0 | 6 | 9 | 3 | 0 |
| 9 | 2024-S-MD-00 | 51,586,637 | 6,149,891 | 45,436,746 | 0 | 4 | 20 | 10 | 0 |
| 10 | 2024-S-NE-00 | 29,200,174 | 13,576,336 | 15,623,838 | 0 | 2 | 2 | 1 | 0 |
| 11 | 2024-S-CA-00 | 21,694,116 | 2,428,483 | 19,265,633 | 0 | 0 | 0 | 2 | 0 |
| 12 | 2024-S-UT-00 | 12,505,326 | 10,512,139 | 1,993,187 | 0 | 2 | 1 | 2 | 0 |

```text
The five: ['2024-S-OH-00', '2024-S-PA-00', '2024-S-MT-00', '2024-S-MI-00', '2024-S-WI-00'] - between them every kind and a non-committee spender (Q13a), so none is swapped.
```

**Q13b. Per candidate, every kind: live gold IE, what the 24/48-hour rule adds (screened, Q6), electioneering shares, communication costs and coordinated expenditures  (0 s)**

| race_id | candidate_id | name | party | gold_ie_for | gold_ie_against | added_for | added_against | electioneering | comm_cost_for | comm_cost_against | coordinated | silver_ie_for | silver_ie_against |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-S-MI-00 | S4MI00470 | SLOTKIN, ELISSA | DEM | 23,942,099 | 53,991,590 | 0 | 0 | 0 | 5,210 | 0 | 1,959,000 | 23,942,099 | 53,991,590 |
| 2024-S-MI-00 | S4MI00595 | ROGERS, MICHAEL J | REP | 24,273,884 | 39,084,085 | 0 | 0 | 0 | 0 | 7,918 | 1,589,974 | 24,273,884 | 39,084,085 |
| 2024-S-MI-00 | S4MI00694 | AMASH, JUSTIN | REP | 473,608 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 473,608 | 0 |
| 2024-S-MI-00 | S4MI00553 | HARPER, FRANK EUGENE HILL | DEM | 27,848 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 27,848 | 0 |
| 2024-S-MT-00 | S4MT00183 | SHEEHY, TIM | REP | 18,563,194 | 63,515,395 | 0 | 0 | 0 | 36,268 | 0 | 219,972 | 18,563,194 | 63,515,395 |
| 2024-S-MT-00 | S6MT00162 | TESTER, R. JON | DEM | 16,589,898 | 63,314,407 | 0 | 0 | 0 | 50,144 | 38 | 246,304 | 16,589,898 | 63,314,407 |
| 2024-S-MT-00 | S8MT00234 | ROSENDALE, MATT MR. | REP | 0 | 114,297 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 114,297 |
| 2024-S-MT-00 | S4MT00225 | BARB, ROBERT | GRE | 0 | 44,346 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 44,346 |
| 2024-S-OH-00 | S4OH00192 | MORENO, BERNIE | REP | 68,907,148 | 85,641,445 | 0 | 0 | 29,500 | 36,268 | 1,145 | 1,928,697 | 68,907,148 | 85,641,445 |
| 2024-S-OH-00 | S6OH00163 | BROWN, SHERROD | DEM | 24,295,843 | 115,071,732 | 108,320 | 0 | 0 | 151,189 | 16 | 2,276,000 | 24,295,843 | 115,071,732 |
| 2024-S-OH-00 | S4OH00200 | LAROSE, FRANK | REP | 3,248,966 | 4,033,491 | 0 | 0 | 63,000 | 0 | 0 | 0 | 3,248,966 | 4,033,491 |
| 2024-S-OH-00 | S2OH00477 | DOLAN, MATT | REP | 3,129,765 | 3,178,484 | 0 | 0 | 0 | 0 | 0 | 0 | 3,129,765 | 3,178,484 |
| 2024-S-PA-00 | S6PA00217 | CASEY, ROBERT P. JR. | DEM | 19,668,493 | 104,734,969 | 0 | 0 | 0 | 342,203 | 54 | 2,550,018 | 19,668,493 | 104,734,969 |
| 2024-S-PA-00 | S2PA00661 | MCCORMICK, DAVE | REP | 29,236,814 | 78,108,081 | 0 | 0 | 0 | 0 | 5,320 | 2,458,625 | 29,236,814 | 78,108,081 |
| 2024-S-WI-00 | S2WI00268 | HOVDE, ERIC D | REP | 10,105,634 | 50,324,227 | 0 | 0 | 0 | 0 | 1,139 | 1,098,871 | 10,105,634 | 50,324,227 |
| 2024-S-WI-00 | S2WI00219 | BALDWIN, TAMMY | DEM | 8,392,337 | 51,061,401 | 0 | 0 | 42,000 | 53,715 | 0 | 1,139,501 | 8,392,337 | 51,061,401 |

**Q13c. Per race, every kind  (0 s)**

| race_id | gold_ie_for | gold_ie_against | added | electioneering | comm_costs | coordinated |
|---|---|---|---|---|---|---|
| 2024-S-OH-00 | 99,581,722 | 207,925,152 | 108,320 | 92,500 | 188,618 | 4,204,697 |
| 2024-S-PA-00 | 48,905,307 | 182,843,050 |  |  | 347,577 | 5,008,643 |
| 2024-S-MT-00 | 35,153,092 | 126,988,445 |  |  | 86,450 | 466,276 |
| 2024-S-MI-00 | 48,717,439 | 93,075,675 |  |  | 13,128 | 3,548,974 |
| 2024-S-WI-00 | 18,497,971 | 101,385,628 |  | 42,000 | 54,854 | 2,238,372 |

**Q13d. Each race's non-committee spenders (type I or absent): in pas2, and added from the 24/48-hour file  (0 s)**

| race_id | spe | name | source | rows | dollars |
|---|---|---|---|---|---|
| 2024-S-MI-00 | C90011156 | WORKING AMERICA | pas2 | 23 | 360,397 |
| 2024-S-MI-00 | C90019589 | ALLIANCE FOR YOUTH ACTION | pas2 | 1 | 195,301 |
| 2024-S-MI-00 | C90022443 | MI PODER | pas2 | 5 | 112,497 |
| 2024-S-MI-00 | C90022872 | IN UNION USA ACTION | pas2 | 2 | 73,712 |
| 2024-S-MI-00 | C90021155 | NATIONAL WOMEN''S LAW CENTER ACTION FUND | pas2 | 8 | 44,114 |
| 2024-S-MI-00 | C90021890 | RISE INC | pas2 | 95 | 8,840 |
| 2024-S-MI-00 | C90018367 | MOMSRISING TOGETHER | pas2 | 2 | 8,294 |
| 2024-S-MI-00 | C90022674 | EMGAGE ACTION INC. | pas2 | 1 | 348 |
| 2024-S-MT-00 | C90019472 | MONTANA RURAL VOTERS (WORC) | pas2 | 71 | 1,417,193 |
| 2024-S-MT-00 | C90022542 | CLIMATE EMERGENCY ADVOCATES | pas2 | 22 | 391,855 |
| 2024-S-MT-00 | C90016437 | NATIONAL ASSOCIATION OF HOME BUILDERS | pas2 | 1 | 350,000 |
| 2024-S-MT-00 | C90009994 | NATIONAL WILDLIFE FEDERATION ACTION FUND | pas2 | 2 | 299,985 |
| 2024-S-MT-00 | C90011156 | WORKING AMERICA | pas2 | 10 | 36,504 |
| 2024-S-MT-00 | C90017898 | PROTECT OUR WINTERS ACTION FUND | pas2 | 344 | 19,784 |
| 2024-S-MT-00 | C90018904 | THE CONSERVATIVE CAUCUS DBA AMERICANS FOR CONSTITUTIONAL LIBERTY | pas2 | 11 | 4,064 |
| 2024-S-MT-00 | C90017492 | INDIVISIBLE PROJECT INC. | pas2 | 2 | 547 |
| 2024-S-MT-00 | C90018367 | MOMSRISING TOGETHER | pas2 | 1 | 384 |
| 2024-S-OH-00 | C90011156 | WORKING AMERICA | pas2 | 16 | 472,560 |
| 2024-S-OH-00 | C90022476 | STAND UP FOR OHIO (OHIO ORGANIZING CAMPAIGN) | pas2 | 5 | 263,349 |
| 2024-S-OH-00 | C90022534 | OHIOANS UNITED FOR PUBLIC EDUCATION | pas2 | 2 | 134,764 |
| 2024-S-OH-00 | C90021726 | OHIO CITIZEN ACTION | pas2 | 11 | 102,839 |
| 2024-S-OH-00 | C90020058 | RED WINE AND BLUE | 24/48-hour (added) | 3 | 96,841 |
| 2024-S-OH-00 | C90022526 | AMERICANS FOR CONSUMER PROTECTION | pas2 | 3 | 89,560 |
| 2024-S-OH-00 | C90011172 | AFSCME WORKING FAMILIES FUND | pas2 | 1 | 60,000 |
| 2024-S-OH-00 | C90022542 | CLIMATE EMERGENCY ADVOCATES | pas2 | 14 | 49,832 |
| 2024-S-OH-00 | C90022351 | IBEW PAC EDUCATIONAL FUND | pas2 | 4 | 15,481 |
| 2024-S-OH-00 | C90021841 | Financial Services Stakeholder Action NFP d.b.a. Private Equity Stakeholder Action | 24/48-hour (added) | 6 | 11,479 |
| 2024-S-OH-00 | C90018904 | THE CONSERVATIVE CAUCUS DBA AMERICANS FOR CONSTITUTIONAL LIBERTY | pas2 | 11 | 4,064 |
| 2024-S-OH-00 | C90017492 | INDIVISIBLE PROJECT INC. | pas2 | 5 | 1,221 |
| 2024-S-OH-00 | C90022666 | YEAGER, THOMAS FREDERICK | pas2 | 1 | 1,111 |
| 2024-S-OH-00 | C90018367 | MOMSRISING TOGETHER | pas2 | 1 | 384 |
| 2024-S-PA-00 | C90011156 | WORKING AMERICA | pas2 | 33 | 286,742 |
| 2024-S-PA-00 | C90022542 | CLIMATE EMERGENCY ADVOCATES | pas2 | 15 | 97,679 |
| 2024-S-PA-00 | C90020363 | NAKASEC ACTION FUND | pas2 | 41 | 65,541 |
| 2024-S-PA-00 | C90022757 | WORKING FOR AMERICA POLICY INC. | pas2 | 1 | 33,253 |
| 2024-S-PA-00 | C90018367 | MOMSRISING TOGETHER | pas2 | 4 | 16,201 |
| 2024-S-PA-00 | C90021890 | RISE INC | pas2 | 84 | 13,507 |
| 2024-S-PA-00 | C90022906 | ACTION TOGETHER NEPA INC. | pas2 | 5 | 4,258 |
| 2024-S-PA-00 | C90020116 | CHESAPEAKE CLIMATE ACTION NETWORK ACTION FUND | pas2 | 9 | 2,972 |
| 2024-S-PA-00 | C90017492 | INDIVISIBLE PROJECT INC. | pas2 | 3 | 2,631 |
| 2024-S-PA-00 | C90023037 | POPULATION CONNECTION ACTION FUND | pas2 | 5 | 2,369 |
| 2024-S-PA-00 | C90022559 | 1199 SEIU NEW YORK STATE POLITICAL ACTION FUND | pas2 | 5 | 1,742 |
| 2024-S-WI-00 | C90011156 | WORKING AMERICA | pas2 | 31 | 369,641 |
| 2024-S-WI-00 | C90022542 | CLIMATE EMERGENCY ADVOCATES | pas2 | 15 | 91,478 |
| 2024-S-WI-00 | C90020181 | LEADERS IGNITING TRANSFORMATION | pas2 | 2 | 85,185 |
| 2024-S-WI-00 | C90022872 | IN UNION USA ACTION | pas2 | 2 | 76,784 |
| 2024-S-WI-00 | C90016510 | PLANNED PARENTHOOD ADVOCATES OF WISCONSIN POLITICAL FUND | pas2 | 12 | 62,790 |
| 2024-S-WI-00 | C90022450 | WISCONSIN PRINCIPLES INC. | pas2 | 1 | 50,000 |
| 2024-S-WI-00 | C90021155 | NATIONAL WOMEN''S LAW CENTER ACTION FUND | pas2 | 8 | 25,450 |
| 2024-S-WI-00 | C90019589 | ALLIANCE FOR YOUTH ACTION | pas2 | 1 | 20,000 |
| 2024-S-WI-00 | C90011826 | VOCES DE LA FRONTERA ACTION | pas2 | 4 | 16,867 |
| 2024-S-WI-00 | C90023185 | BLUE SKY WAUKESHA | pas2 | 1 | 7,038 |
| 2024-S-WI-00 | C90021890 | RISE INC | pas2 | 85 | 6,710 |
| 2024-S-WI-00 | C90021692 | 350 WISCONSIN ACTION | pas2 | 14 | 2,502 |
| 2024-S-WI-00 | C90018367 | MOMSRISING TOGETHER | pas2 | 2 | 984 |

**Q13e. Each race's electioneering sponsors  (0 s)**

| race_id | spon | name | CANDIDATE_ID | rows | dollars |
|---|---|---|---|---|---|
| 2024-S-OH-00 | C30001978 | PATRIOTIC VETERANS, INC | S4OH00200 | 1 | 63,000 |
| 2024-S-OH-00 | C30003388 | AMERICAN RESOLVE PAC INC. | S4OH00192 | 1 | 29,500 |
| 2024-S-WI-00 | C30003552 | AMERICANS FOR PHARMA REFORM INC. | S2WI00219 | 1 | 42,000 |

**The pick:** the five 2024 regular Senate races with the most independent expenditures in live
gold are Ohio, Pennsylvania, Montana, Michigan and Wisconsin. Between them they hold every kind.
Ohio and Wisconsin have electioneering communications, every one has communication costs and
coordinated expenditures, and each has Form 5 spenders. Ohio also has two spenders the 24/48-hour
file adds. **No race is swapped** (Q13a).

Silver's counted independent expenditures equal live gold's for every candidate (Q13b). These are
the figures NEU-2171 compares gold against once M3's silver is built, under this document's rules:
gold's IE for and against, plus "added" (Q6's screened rule), electioneering shares (every row),
communication costs for and against (`pas2`), and coordinated expenditures.

## Decisions

Each states its source, its rule and its dollars, and what it asks of NEU-2163.

1. **Non-committee spenders are Form 5 filers (`cm` type `I`), and their spending is in `pas2`.**
   153 of them hold $84,903,413 of 2024's counted independent expenditures. The "absent from `cm`"
   half is a single real spender ($64,107) and seven hoaxes ($33.9B). The 24/48-hour file adds
   what 57 Form 5 filers' `pas2` rows lack ($2.49M short of their reported figures). NEU-2163
   writes "non-committee spender" as a Form 5 filer and amends the milestone's "spenders not in
   `cm`" contract, whose group is near-empty.
2. **24/48-hour amendments: the filing chain, recommended.** Every row on a filing another row's
   `prev_file_num` names is dropped. 2024: keeps 61,426 rows, $48,339,099,096 ($4,401,751,869
   with web-form ids aside), drops 12,023, $1,340,305,331. §1.1's partial-amendment bar is crossed
   (1.63%), but its fallback, per transaction, drops $439.5M of distinct expenditures because
   `tran_id` repeats across a spender's filings. The departure from §1.1 is NEU-2163's to decide.
3. **The match and the add rule.** The ladder with rung 4 matches by spender, `tran_id`, then
   candidate, date and amount, then candidate-blind. Row matching fails §1.1's 1% bar (1.62%),
   and per-spender totals agree within 0.92%. **Recommended: add by spender**, a spender with no
   counted `pas2` independent expenditure in the cycle contributing all its latest-amendment rows,
   **with the screen**: it reports independent expenditures in `reported_total`, and its rows hold
   no more than ten times that figure. 2024: **$1,001,297** from 14 spenders. Without the screen:
   $43,906,446,618, all but $4.8M of it hoaxes. By row: $43,977,066,615, $68,376,504 with web-form ids aside.
   NEU-2163 decides, as §1.1 asks when the bar is not met.
4. **Timeliness: in.** A spender's latest-amendment 24/48-hour rows dated after its
   `reported_total.period_end` are added until a periodic report covers them. On 2026, `pas2`
   already holds 0.46% of them (bar: 1%). The rule adds $1,281,571,904 on 2026 today and $28,732
   on 2024. This confirms the contract's "pre-period-report timeliness" condition.
5. **Communication costs: `pas2`**, silver's `communication_cost` rows (24F for, 24N against, memo
   lines dropped). The CSV supplies communication type and class, and cents, by `SUB_ID`. 2024:
   799 rows, $7,157,987. The CSV adds no row in any cycle 2010–2026 and drops 20 ($59,480, no
   candidate).
6. **Electioneering: the CSV, every row counted but a disbursement's copies.** A row's candidate
   is `CANDIDATE_ID` through `alias_of`, and its amount is `CALCULATED_CANDIDATE_SHARE`, which
   splits exactly. Rows of one disbursement beyond its `NUMBER_OF_CANDIDATES` are dropped. A
   blank-candidate row counts toward its sponsor and no candidate. 2024: 67 rows, $9,442,374; drops
   2 ($38,500). The Form 9s show amendment restatements ($33,750 in 2024) that the file cannot tell
   from separate reports, which the file key would drop in 2010 ($3.1M), so no amendment rule.
   NEU-2163 amends the milestone's "duplicates after amendment" contract to this.
7. **Party coordinated expenditures: `pas2`**, silver's `coordinated` rows (24C, memo lines
   dropped), credited to the candidate. 2024: 812 rows, $89,161,724. The contract stands. Three
   non-party filers' 24C ($89,537) count as filed.
8. **Cross-kind overlap: none needing a rule.** $1,451 in 2024.
9. **Cycles:** every 2024 rule applies 2010–2026 as written. Web-form hoaxes from 2020 on need
   decision 3's screen in every cycle, and their size (over $30B a cycle since 2022) is why.

## For NEU-2163 to NEU-2171

- **NEU-2163** (spec §6, glossary): the nine decisions above. In `CONTEXT.md`: a
  **non-committee spender** is a Form 5 filer (`cm` type `I`). The **24/48-hour file** keeps
  superseded filings, which the chain drops. A web-form hoax is the reason for decision 3's screen.
  To decide, each against a pinned §1.1 rule or beyond one: the amendment fallback (Q3, the chain
  recommended instead); the add rule, whose bar Q5 misses (1.62%); Q6's screen and its tenfold
  threshold, which are this document's; rung 4 (the bar is 9.58% without it); and Q8's reading of
  "equal amounts" as equal with the cents dropped.
- **NEU-2164** (catalogue and extract): the headers as served are Q1's, every cycle's equal to
  2024's (Q12a). The 24/48-hour file's are lower case. Each URL answers 302 to S3. Dates are
  `DD-MON-YY` (24/48-hour, electioneering) and `YYYYMMDD` (communication costs). In the
  `register_bulk` dialect, a header row is unquoted and every data field quoted. Cells that fail a cast: none in 2024, 12 in
  2016, 1 in 2018. Fixture rows worth having: a hoax web-form line (`WFT20243201436-1`), an
  `A1` with no `prev_file_num`, the `SE.1` reuse (Senate Leadership Fund's 1821585 and 1844328), a
  two-candidate electioneering row with no candidate, a `24F` in `SUPPORT_OPPOSE_IND`.
- **NEU-2165** (24/48-hour rows into `independent_expenditure`): within 1% of **$1,001,297** (Q6,
  screened), or of $4,835,248 without the screen. On 2026, timeliness adds $1,281,571,904 (Q7).
- **NEU-2166** (`electioneering_communication`): within 1% of **$9,442,374**, 67 rows (Q9). That
  becomes $9,480,874 if every row counts, and $9,408,624 under the file key as well.
- **NEU-2167** (communication costs and coordinated): within 1% of **$7,157,987** (799 rows) and
  **$89,161,724** (812 rows).
- **NEU-2171** (production run): Q13b and Q13c, per candidate and race.
