# FEC's 2024 `oppexp`: sub-items, amendments, overlap, categories and payees

Measured for [NEU-2149](https://linear.app/neuroticsasquatch/issue/NEU-2149) (milestone M2 Spending;
spec [`NEU-2149-oppexp-measurement.md`](../specs/NEU-2149-oppexp-measurement.md)). FEC's operating
expenditures file holds what committees paid out to run themselves. This document measures how it
files a sub-itemized payment, whether it carries superseded or repeated rows, whether any row is
already in the receipt files, how often FEC's `CATEGORY` is filled, and how payee names group under
the organization normalizer. It does this for 2024, with one structural profile of every cycle
2004–2026. It fixes the counting rules NEU-2150 writes into spec §5 and labels the 200 purposes
NEU-2153 tests against (`tests/fixtures/spending/purpose_labels_2024.csv`). Nothing under `sql/`,
`src/` or `frontend/` changed, and no bronze, silver, gold or marker was written.

| What | Value |
| --- | --- |
| Run | 2026-11-21 01:14–02:04 UTC, over SSH on `music-box-dancer`. The blocks below are the final run, 01:49:12–01:56:15 UTC, every block in order (`all.sh`). Four were re-run after review, on the same work directory and files: Q3 at 01:56:36 (Q3n added), and Q5, Q10 and Q11 at 02:03–02:04 (the fourth raw filing, the conduit predicate, Q10c2, every rule's deciles) |
| Code | `main` at `89635a535738dcbf5f9b6420be006a8be0d943fd` (the `pipeline` image's tag) |
| Container | `pipeline-lvch8zyndujjzkz16ksys8im-20261121T005308` |
| DuckDB | 2.0.0; `Limits(memory_limit='32GB', max_temp_directory_size='60GB', threads=6)`; `connect`'s build-side optimizer off (NEU-2076) |
| Live build | `20261120T212246Z` (`gold.meta.cycles → 2024`). Its 2024 source dates: `cm`, `cn`, `ccl` 2026-11-15; `indiv`, `oth`, `pas2` 2026-11-16; `weball`, `webk`, `committee_summary` 2026-11-19. The 2024 `cm`, `indiv`, `oth` and `pas2` read here are that build's bronze, and `silver.*` are its partitions |
| Header file | `https://www.fec.gov/files/bulk-downloads/data_dictionaries/oppexp_header_file.csv`, `Last-Modified: Wed, 10 Jan 2018 18:30:12 GMT`, downloaded 2026-11-21T01:14:23Z. It names the 25 columns spec §3 lists, unchanged |
| `oppexp24.zip` | `https://www.fec.gov/files/bulk-downloads/2024/oppexp24.zip`, 64,105,756 bytes, `Last-Modified: Sun, 15 Nov 2026 19:38:31 GMT`, downloaded 2026-11-21T01:14:45Z. Every 2024 block reads the text unpacked from that download. Q2 deletes each zip after profiling it, so Q3 fetched the zip again (01:52, the same 64,105,756 bytes), and `view_oppexp` kept the text it had |
| Other cycles | `…/<cycle>/oppexp<yy>.zip` for 2004–2022 and 2026, each fetched, profiled and deleted by Q2. Sizes and `Last-Modified` are in Q2a's fetch lines. 2024's is the row above |
| Raw filings | `https://docquery.fec.gov/dcdev/posted/<FILE_NUM>.fec` for three filings (Q5) |

None of the `oppexp` zips is catalogued or in bronze. They lived in the work directory for the run
only. The work directory `/data/fundlens/scratch/measure-oppexp-2024` was deleted at 02:07:09 UTC.

## Headline

- **A sub-itemized payment counts at its parent.** 80,249 parents carry 670,054 children. A parent
  is *fully itemized* when its children add up to it within $1.00. Fully itemized parents hold
  $250.5M of the $524.2M parents carry: **47.78%, under §1.1's 50% bar, so the rule is parent
  always** (R2). The parent counts, whatever its memo code. A child of a parent in the file never
  counts. The card issuer stays the payee of $192.9M of card bills, and no child reaches a payee
  page: $503.0M of children, $250.5M of them under fully itemized parents. R2 differs from FEC's own rule (non-memo rows, R1) by $194,596 in all (Q3).
  The bar is close and is not met only in 2024 and 2016: it is met in the other ten cycles, from
  51.09% to 84.68% (Q2c). At a 1% tolerance 2024 would pass at 68.00% (Q3k).
- **No paper filing in any cycle.** Every 2024 row is electronic (`FILE_NUM` above 0, `TRAN_ID`
  filled), and no cycle 2004–2026 has more than 4 rows without a `TRAN_ID` (Q1c, Q4c).
- **Repeated rows: 2,943 ($3.24M) on 11 filings**, each transaction twice, which v1's rule drops.
  The four largest filings' raw `.fec` files hold each `TRAN_ID` once (Q5).
- **Amendments: the receipt side's superseded filings, alone.** `indiv`'s `superseded_filing` set
  holds 47 filings with $15.12M of R2 spending. A payment-side rule would add 23 filings ($124,469).
  10 of them ($105,184) are "superseded" by a different report, and the 13 that are the same
  report hold $19,286 (Q6).
- **No overlap.** No `oppexp` row shares a `SUB_ID`, or a filing, `TRAN_ID` and amount, with `pas2`,
  `oth` or `indiv`, and none is a silver `committee_transfer` or `independent_expenditure` row.
  Nothing is dropped (Q7).
- **Sign: amounts as filed.** Negative rows net $-191.5M. Super PACs hold $-124.5M of it, $-109.1M on
  rows naming Schedule E or an IE: money already reported as operating expenditure, moved. Counting them as filed nets each move to
  nothing (Q10).
- **Counted, under the adopted rules (R4):** 1,550,230 rows, $9,594,311,329 at committees with a
  reported figure, and $9,715,514,602 in all, against FEC's reported $9.917B. The median committee
  is at 98.76% of its reported figure, and 63 are more than 1% above it, by $1.09M (Q11).
- **`CATEGORY` is filled on 28.94% of counted rows and 16.20% of counted dollars**, and code 001
  is a catch-all. Where it is filled on a labelled purpose, the label agrees with code 001 on 3.57%
  of its dollars, against 85–99% for 004, 005, 002 and 102 (Q8).
- **The category list grows from 11 to 15.** `mail` (7.39% of the labelled set's dollars),
  `field` (2.62%), `polling_research` (2.62%) and `credit_card` (2.38%) pass the 2% bar. The 200
  purposes hold 76.75% of counted dollars (Q8).
- **The top 100 payee keys hold 52.37% of counted dollars**, and the top 1,000 hold 80.26%. No
  wrong merge was seen in the top 100. Three firms are split across keys (`AX MEDIA`/`AXMEDIA`,
  `TEAM DIRECT`/`TEAMDIRECT`, MissionWired under three keys) (Q9).
- **The table fits.** Built as NEU-2152 would build it, `operating_expenditure` holds 887.4 MiB in
  DuckDB. The 2024 transform's 26.48 GiB peak becomes about 27.35 GiB, under the 32 GB
  (29.80 GiB) limit. On the earlier build that peaked at 28.97 GiB it would not fit (Q1).

## How to re-run

On the VM, in `tmux`. Save the setup script below as `setup.py`, each block under its name, and
`tests/fixtures/spending/purpose_labels_2024.csv` beside them. Then run `all.sh`. It runs `run.sh`
on each block in order and stops at the first that fails. It copies the labelled set into the work
directory before Q8b. The final run's `all.sh` did neither: its `run.sh` reported `grep`'s status, and
the CSV was already in the work directory, copied at 01:40. Every block's `EXIT 0` line was checked
by hand, and the two scripts were fixed after review.

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
# The final run: every block in order, each into its own qN.out. The labelled set
# (tests/fixtures/spending/purpose_labels_2024.csv, saved beside these files) goes into the work
# directory before q8b reads it.
cd ~/measure-oppexp-2024
P=$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)
date -u +"START %FT%TZ" > all.log
./run.sh q1 && ./run.sh q1mem_a && ./run.sh q1mem_b && ./run.sh q2 \
 && ./run.sh q3 load.py fam.py && ./run.sh q4 load.py && ./run.sh q5 load.py \
 && ./run.sh q6 load.py && ./run.sh q7 load.py && ./run.sh q8 load.py counted.py \
 && docker exec -i "$P" sh -c "cat > /data/fundlens/scratch/measure-oppexp-2024/purpose_labels_2024.csv" \
    < purpose_labels_2024.csv \
 && ./run.sh q8b load.py counted.py && ./run.sh q9 load.py counted.py payee.py \
 && ./run.sh q10 load.py counted.py payee.py && ./run.sh q11 load.py counted.py
date -u +"END %FT%TZ" >> all.log
# Afterwards:
docker exec "$(docker ps --format '{{.Names}}' | grep '^pipeline-lvch8zyndujjzkz16ksys8im' | head -1)" \
  rm -rf /data/fundlens/scratch/measure-oppexp-2024
```

Run one block at a time, never beside a pipeline step, and do not merge to `main` while they run:
a deploy restarts `pipeline`. The first block unpacks `oppexp24.zip` and 2024's `cm`, and Q6 and Q7
unpack 2024's `indiv`, `pas2` and `oth`, into `/data/fundlens/scratch/measure-oppexp-2024`. Later
blocks reuse them. Q3, Q6 and Q2 leave Parquet files there (`r2`, `fam`, `superseded_b`,
`superseded_c`, `profile`) that later blocks read. The whole run takes about 7 minutes.

Every table's title carries the seconds its query took. Amounts are cast with `TRY_CAST` inside
each query, so a cell that fails is counted, not a read error. None failed (Q1a).

### Setup

`oppexp` (and `raw` for another cycle) is the zip's text member as `copy_as_utf8` rewrites it: every
column VARCHAR, FEC's 25 header names and `extra_1` for the 26th field the trailing `|` makes.
`typed()` adds §2's derived columns. DuckDB's names are case-blind, so they cannot reuse the raw
names: `amt`, `dt`, `sid` (`SUB_ID`), `fnum` (`FILE_NUM`), `memo`, `tran`, `back` and `purp`
(§2's purpose). It also adds the filer group from 2024's `cm` and `is_repeat`, v1's repeated-row
rule. `ox` is the typed rows less repeats, which is what NEU-2152 will read once the file is
catalogued. `silver.<table>` are the live build's 2024 partitions.

The setup differs from spec §4.1 in four ways:

- `bulk()` registers a file only when a block asks for it, so a block that does not read `indiv`
  never unpacks it.
- `silver()` downloads one table's partition, not every gold input `_require_inputs` would.
- `typed()` spells `_drop_fec_repeats` inline. The function takes a catalogued `BulkFile`, which
  `oppexp` is not yet.
- A row whose `BACK_REF_TRAN_ID` names its own `TRAN_ID` (4 rows in 2024) is read as no child.

The rules are named as the spec's §2 names them, with one change. The spec's R2 is §1.1's
children-where-they-add-up rule, and its R3 and R4 build on it. Q3 rejects that rule, so here it is
**R2c**. **R2** is the rule Q3 adopts (parent always), and R3 and R4 build on R2, so that
"counted" in Q8 to Q11 is the adopted rule, as the spec's §2 asks. Q3 and Q11 report R2c beside
R2.

```python
import datetime as dt
import resource
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
from fundlens.resolve import normalize
from fundlens.settings import get_settings
from fundlens.transform.runner import Limits, connect, copy_as_utf8, fetch_bulk, literal, register_bulk

settings = get_settings()
store = R2.from_settings(settings)
scratch = paths.scratch_dir(settings.data_dir)
work = scratch / "measure-oppexp-2024"
work.mkdir(parents=True, exist_ok=True)
con = connect(Limits.from_settings(settings), scratch)
normalize.register(con)  # organization_key, as silver calls it


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


def fetch(path: str) -> Path:
    """One FEC file into `work`, its URL, Last-Modified, size and download time printed;
    skipped when already there."""
    target = work / Path(path).name
    if not target.exists():
        url = f"{settings.fec_bulk_url.rstrip('/')}/{path}"
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT})) as response:
            target.write_bytes(response.read())
            print(url, "| Last-Modified:", response.headers.get("Last-Modified"),
                  "| bytes", f"{target.stat().st_size:,}",
                  "| downloaded", dt.datetime.now(dt.UTC).isoformat(timespec="seconds"))
    return target


# FEC's header file for oppexp, fetched again (spec §3).
HEADER = fetch("data_dictionaries/oppexp_header_file.csv").read_text().strip().split(",")


def view_oppexp(name: str, zip_path: Path) -> int:
    """The view `name` over the zip's text member, rewritten by `copy_as_utf8` (the transform's
    own repair): FEC's header plus `extra_<n>` for each field beyond it. The fields per line."""
    text = work / f"{name}.txt"
    if not text.exists():
        with zipfile.ZipFile(zip_path) as archive, text.open("wb") as out:
            (member,) = archive.namelist()
            with archive.open(member) as src:
                copy_as_utf8(src, out)
    fields = con.execute(
        f"SELECT max(len(string_split(line, '|'))) FROM read_csv({literal(text)}, delim = '\\x01',"
        " quote = '', escape = '', header = false, auto_detect = false,"
        " columns = {'line': 'VARCHAR'})"
    ).fetchone()[0]
    names = HEADER + [f"extra_{n}" for n in range(1, fields - len(HEADER) + 1)]
    columns = ", ".join(f"'{h}': 'VARCHAR'" for h in names)
    con.execute(
        f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv({literal(text)}, delim = '|',"
        f" quote = '', escape = '', header = false, auto_detect = false, null_padding = true,"
        f" columns = {{{columns}}})"
    )
    return fields


def bulk(name: str) -> None:
    """2024's bronze `name` as the transform sees it: `<name>` with repeated rows dropped,
    `<name>_published` with them kept (pas2, oth, indiv)."""
    file = CATALOGUE[name]
    text, done = work / f"{name}.txt", work / f"{name}.done"
    if not done.exists():
        text = fetch_bulk(store, 2024, file, data_dir=settings.data_dir, work=work)
        done.touch()
    register_bulk(con, file, text)


# The live build's silver tables this measurement reads, as views silver.<table>.
with psycopg.connect(settings.database_url) as pg:
    pg.read_only = True
    BUILD = pg.execute("SELECT cycles -> '2024' ->> 'build_id' FROM gold.meta").fetchone()[0]
con.execute("CREATE SCHEMA silver")


def silver(table: str) -> None:
    """The live build's 2024 partition of `table` as the view silver.<table>."""
    prefix = paths.silver_partition(table, 2024, BUILD)
    for key in store.list_keys(prefix + "/"):
        local = paths.local_path(settings.data_dir, key)
        if not local.exists():
            store.download_to(key, local)
    local = paths.local_path(settings.data_dir, prefix)
    con.execute(f"CREATE VIEW silver.{table} AS SELECT * FROM read_parquet("
                f"{literal(local / '**' / '*.parquet')}, hive_partitioning = false)")


def peak() -> None:
    """This process's peak resident memory, at exit of a memory block."""
    print(f"\npeak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20:.2f} GiB")


print("build", BUILD, "| duckdb", con.execute("SELECT version()").fetchone()[0],
      "|", Limits.from_settings(settings))


SUB_ID_TYPE = CATALOGUE["indiv"].columns["SUB_ID"]
PARSED = "coalesce(try_strptime(TRANSACTION_DT, '%m/%d/%Y'), try_strptime(TRANSACTION_DT, '%m%d%Y'))"


def typed(name: str, source: str) -> None:
    """The table `name`: `source`'s rows as published, with §2's typed and derived columns beside
    the raw ones, each committee's filer group from 2024's `cm` (the view `cm`, registered
    first), and `is_repeat`: v1's repeated-row rule (`_drop_fec_repeats`, NEU-2401) spelled for
    this file. A row repeats when it is not the first, by SUB_ID, of the rows of an electronic
    filing that share its TRAN_ID and every other column. The view `ox` is `name` less them."""
    raw = [r[0] for r in con.execute(f"DESCRIBE {source}").fetchall()]
    same = ", ".join(f'o."{c}"' for c in raw if c != "SUB_ID")
    con.execute(f"""
        CREATE OR REPLACE TABLE {name} AS
        SELECT o.*,
            TRY_CAST(o.TRANSACTION_AMT AS DECIMAL(14, 2)) AS amt,
            CAST({PARSED} AS DATE) AS dt,
            TRY_CAST(o.SUB_ID AS {SUB_ID_TYPE}) AS sid,
            TRY_CAST(o.FILE_NUM AS BIGINT) AS fnum,
            o.MEMO_CD IS NOT DISTINCT FROM 'X' AS memo,
            nullif(trim(o.TRAN_ID), '') AS tran,
            -- A row naming itself is no child (2024: 4 rows).
            nullif(nullif(trim(o.BACK_REF_TRAN_ID), ''), nullif(trim(o.TRAN_ID), '')) AS back,
            nullif(regexp_replace(upper(trim(o.PURPOSE)), '\\s+', ' ', 'g'), '') AS purp,
            CASE
                WHEN cm.CMTE_TP IN ('H', 'S', 'P') THEN 'candidate'
                WHEN cm.CMTE_TP IN ('X', 'Y') THEN 'party'
                WHEN cm.CMTE_TP IN ('O', 'U') THEN 'super PAC'
                WHEN cm.CMTE_ID IS NOT NULL THEN 'other'
                ELSE 'not in cm'
            END AS filer,
            coalesce(TRY_CAST(o.FILE_NUM AS BIGINT) > 0 AND nullif(trim(o.TRAN_ID), '') IS NOT NULL
                AND TRY_CAST(o.SUB_ID AS {SUB_ID_TYPE})
                    > min(TRY_CAST(o.SUB_ID AS {SUB_ID_TYPE})) OVER (PARTITION BY {same}), false)
                AS is_repeat
        FROM {source} AS o
        LEFT JOIN (SELECT DISTINCT CMTE_ID, CMTE_TP FROM cm) AS cm ON cm.CMTE_ID = o.CMTE_ID
    """)
    con.execute(f"CREATE OR REPLACE VIEW ox AS SELECT * FROM {name} WHERE NOT is_repeat")


bulk("cm")
```

`load.py`, the 2024 file as `oxp` and `ox`, read by every block after Q1:

```python
view_oppexp("oppexp", fetch("2024/oppexp24.zip"))
typed("oxp", "oppexp")
```

## Q1: size, shape and memory (2024)

```python
z = fetch("2024/oppexp24.zip")
view_oppexp("oppexp", z)
# Lines copy_as_utf8 had to re-decode: the member's lines that are not UTF-8 as filed.
with zipfile.ZipFile(z) as archive, archive.open("oppexp.txt") as src:
    bad = nul = 0
    for line in src:
        nul += b"\x00" in line
        try:
            line.decode("utf-8")
        except UnicodeDecodeError:
            bad += 1
print(f"lines not UTF-8 as filed: {bad:,}; lines holding a NUL: {nul:,}")
typed("oxp", "oppexp")

show("Q1a. Rows, cells that fail a cast, keys", """
SELECT count(*) AS rows,
    count(*) FILTER (WHERE amt IS NULL AND TRANSACTION_AMT IS NOT NULL) AS amount_fails,
    count(*) FILTER (WHERE TRANSACTION_AMT IS NULL) AS amount_blank,
    count(*) FILTER (WHERE dt IS NULL AND TRANSACTION_DT IS NOT NULL) AS date_fails,
    count(*) FILTER (WHERE TRANSACTION_DT IS NULL) AS date_blank,
    count(*) FILTER (WHERE try_strptime(TRANSACTION_DT, '%m/%d/%Y') IS NOT NULL) AS date_mm_dd_yyyy,
    count(*) FILTER (WHERE sid IS NULL) AS sub_id_fails,
    count(DISTINCT sid) AS distinct_sub_id,
    count(*) FILTER (WHERE fnum IS NULL AND FILE_NUM IS NOT NULL) AS file_num_fails,
    count(*) FILTER (WHERE extra_1 IS NOT NULL) AS extra_1_filled,
    min(dt) AS earliest, max(dt) AS latest
FROM oxp""")

show("Q1b. Dollars: every row, and R1 (non-memo rows)", """
SELECT sum(amt) AS dollars_all, sum(amt) FILTER (WHERE NOT memo) AS dollars_r1,
    count(*) FILTER (WHERE memo) AS memo_rows, sum(amt) FILTER (WHERE memo) AS memo_dollars,
    count(*) FILTER (WHERE amt < 0) AS negative_rows, sum(amt) FILTER (WHERE amt < 0) AS negative_dollars
FROM oxp""")

show("Q1c. Electronic and paper: FILE_NUM against TRAN_ID", """
SELECT CASE WHEN fnum > 0 THEN 'FILE_NUM > 0' WHEN fnum IS NULL THEN 'FILE_NUM blank'
            ELSE 'FILE_NUM <= 0' END AS filing,
    tran IS NOT NULL AS has_tran_id, count(*) AS rows, sum(amt) AS dollars,
    count(*) FILTER (WHERE back IS NOT NULL) AS with_back_ref
FROM oxp GROUP BY ALL ORDER BY ALL""")

show("Q1d. Form, schedule and line", """
SELECT FORM_TP_CD AS form, SCHED_TP_CD AS sched, LINE_NUM AS line, count(*) AS rows,
    sum(amt) AS dollars, avg(memo::INT)::DOUBLE AS memo_rows_share,
    (sum(amt) FILTER (WHERE memo) / nullif(sum(amt), 0))::DOUBLE AS memo_dollars_share
FROM oxp GROUP BY ALL ORDER BY dollars DESC""")

show("Q1e. ENTITY_TP", """
SELECT ENTITY_TP, count(*) AS rows, sum(amt) AS dollars FROM oxp GROUP BY ALL ORDER BY rows DESC""")
show("Q1f. AMNDT_IND", """
SELECT AMNDT_IND, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT fnum) AS filings
FROM oxp GROUP BY ALL ORDER BY rows DESC""")
show("Q1g. RPT_YR", """
SELECT RPT_YR, count(*) AS rows, sum(amt) AS dollars FROM oxp GROUP BY ALL ORDER BY ALL""")
show("Q1h. Filer group", """
SELECT filer, count(DISTINCT CMTE_ID) AS committees, count(*) AS rows, sum(amt) AS dollars,
    sum(amt) FILTER (WHERE NOT memo) AS dollars_r1
FROM oxp GROUP BY ALL ORDER BY dollars DESC""")

# Parquet size: the typed rows, as the transform writes a silver part.
out = work / "ox.parquet"
con.execute(f"COPY (SELECT * EXCLUDE (extra_1, is_repeat) FROM ox) TO {literal(out)}"
            " (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 999424)")
print(f"\nParquet: {out.stat().st_size:,} bytes; zip {z.stat().st_size:,}; text "
      f"{(work / 'oppexp.txt').stat().st_size:,}")
out.unlink()
```

```text
lines not UTF-8 as filed: 0; lines holding a NUL: 0
```

**Q1a. Rows, cells that fail a cast, keys  (0 s)**

| rows | amount_fails | amount_blank | date_fails | date_blank | date_mm_dd_yyyy | sub_id_fails | distinct_sub_id | file_num_fails | extra_1_filled | earliest | latest |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2,249,911 | 0 | 0 | 0 | 0 | 2,249,911 | 0 | 2,249,911 | 0 | 0 | 2001-01-01 | 2042-09-20 |

**Q1b. Dollars: every row, and R1 (non-memo rows)  (0 s)**

| dollars_all | dollars_r1 | memo_rows | memo_dollars | negative_rows | negative_dollars |
|---|---|---|---|---|---|
| 10,260,926,985 | 9,733,435,945 | 696,235 | 527,491,040 | 22,581 | -221,619,156 |

**Q1c. Electronic and paper: FILE_NUM against TRAN_ID  (0 s)**

| filing | has_tran_id | rows | dollars | with_back_ref |
|---|---|---|---|---|
| FILE_NUM > 0 | True | 2,249,911 | 10,260,926,985 | 677,759 |

**Q1d. Form, schedule and line  (0 s)**

| form | sched | line | rows | dollars | memo_rows_share | memo_dollars_share |
|---|---|---|---|---|---|---|
| F3X | SB | 21B | 904,688 | 4,601,073,127 | 27.76% | 4.47% |
| F3 | SB | 17 | 1,141,106 | 3,526,403,263 | 27.92% | 6.38% |
| F3P | SB | 23 | 204,070 | 2,133,391,638 | 62.00% | 4.54% |
| F3X | SB | 21 | 47 | 58,958 | 0.00% |  |

**Q1e. ENTITY_TP  (0 s)**

| ENTITY_TP | rows | dollars |
|---|---|---|
| ORG | 1,846,221 | 9,212,267,643 |
| IND | 351,518 | 715,380,649 |
| PAC | 24,778 | 30,318,684 |
| CAN | 11,542 | 23,357,611 |
| COM | 5,091 | 22,100,174 |
| PTY | 4,934 | 87,672,506 |
| CCM | 3,328 | 168,477,718 |
|  | 2,499 | 1,352,001 |

**Q1f. AMNDT_IND  (0 s)**

| AMNDT_IND | rows | dollars | filings |
|---|---|---|---|
| N | 1,411,353 | 5,859,933,769 | 45,832 |
| A | 828,815 | 4,370,671,643 | 9,924 |
| T | 9,743 | 30,321,573 | 1,540 |

**Q1g. RPT_YR  (0 s)**

| RPT_YR | rows | dollars |
|---|---|---|
| 2023 | 825,949 | 2,312,347,215 |
| 2024 | 1,423,962 | 7,948,579,770 |

**Q1h. Filer group  (0 s)**

| filer | committees | rows | dollars | dollars_r1 |
|---|---|---|---|---|
| candidate | 3,093 | 1,287,574 | 4,987,564,395 | 4,685,238,455 |
| other | 4,073 | 517,820 | 2,757,389,761 | 2,609,785,888 |
| party | 357 | 333,253 | 1,507,938,601 | 1,450,449,036 |
| super PAC | 1,309 | 111,246 | 886,318,440 | 866,732,257 |
| not in cm | 3 | 18 | 121,715,789 | 121,230,310 |

```text
Parquet: 109,452,863 bytes; zip 64,105,756; text 429,582,743
```

All 2,249,911 lines have 26 fields: FEC's 25 and an empty one after a trailing `|` (the assertion
in spec §3, confirmed). The zip holds one member, `oppexp.txt`. No line needed re-decoding and none
holds a NUL. Every amount, date, `SUB_ID` and `FILE_NUM` casts, `SUB_ID` is unique, and every date
is `MM/DD/YYYY`. Dates run from 2001 to 2042: filers' typos, kept as filed.

The file holds three lines and nothing else: Form 3 line 17, Form 3P line 23 and Form 3X line
21(b), plus 47 rows ($58,958) on a Form 3X line written `21`. FEC's description also names
21(a)(i) and 21(a)(ii), the shared federal and nonfederal operating expenditures of party and PAC
filers. The 2024 file has no row on either, and no Schedule H4 row, so a shared payment's
federal share is not in it. Q11's party gap is this.

### Memory

Each block runs in a fresh process.

```python
# Q1 memory (a): one full-scan aggregate over the file, in a fresh process.
view_oppexp("oppexp", fetch("2024/oppexp24.zip"))
show("Q1j. A full-scan aggregate", """SELECT count(*) AS rows, sum(TRY_CAST(TRANSACTION_AMT AS DECIMAL(14, 2))) AS dollars,
    count(DISTINCT CMTE_ID) AS committees, count(DISTINCT NAME) AS names FROM oppexp""")
peak()
```

**Q1j. A full-scan aggregate  (0 s)**

| rows | dollars | committees | names |
|---|---|---|---|
| 2,249,911 | 10,260,926,985 | 8,835 | 148,431 |

```text
peak RSS 0.53 GiB
```

```python
# Q1 memory (b): the table NEU-2152 builds, in a fresh process: the typed rows with repeats
# dropped, organization_key once per distinct name joined back, and the child-to-parent join.
start = time.monotonic()
view_oppexp("oppexp", fetch("2024/oppexp24.zip"))
typed("oxp", "oppexp")
con.execute("""CREATE TABLE payee_name AS SELECT NAME, organization_key(NAME) AS payee_key FROM (SELECT DISTINCT NAME FROM ox)""")
con.execute("""CREATE TABLE parent AS SELECT CMTE_ID, fnum, back AS tran FROM ox WHERE back IS NOT NULL GROUP BY ALL""")
con.execute("""
CREATE TABLE operating_expenditure AS
SELECT o.* EXCLUDE (extra_1, is_repeat, filer), n.payee_key,
    CASE WHEN pp.tran IS NOT NULL THEN false WHEN p.tran IS NOT NULL THEN true ELSE NOT o.memo END AS counted
FROM ox AS o
LEFT JOIN payee_name AS n ON n.NAME IS NOT DISTINCT FROM o.NAME
LEFT JOIN parent AS p ON p.CMTE_ID = o.CMTE_ID AND p.fnum = o.fnum AND p.tran = o.tran
LEFT JOIN parent AS pp ON pp.CMTE_ID = o.CMTE_ID AND pp.fnum = o.fnum AND pp.tran = o.back""")
con.execute("DROP TABLE payee_name; DROP TABLE parent; DROP VIEW ox; DROP TABLE oxp")
print(f"built in {time.monotonic() - start:.0f} s")
show("Q1k. The table, and the database after it", """
SELECT (SELECT count(*) FROM operating_expenditure) AS rows,
    (SELECT estimated_size FROM duckdb_tables() WHERE table_name = 'operating_expenditure') AS estimated_rows,
    (SELECT memory_usage FROM pragma_database_size() WHERE database_name = 'memory') AS database_memory,
    (SELECT sum(memory_usage_bytes) FROM duckdb_memory()) AS duckdb_memory_bytes""")
show("Q1l. DuckDB's memory by tag", "SELECT tag, memory_usage_bytes, temporary_storage_bytes FROM duckdb_memory() WHERE memory_usage_bytes > 0 ORDER BY 2 DESC")
peak()
```

```text
built in 6 s
```

**Q1k. The table, and the database after it  (0 s)**

| rows | estimated_rows | database_memory | duckdb_memory_bytes |
|---|---|---|---|
| 2,246,968 | 2,246,968 | 887.4 MiB | 930,543,360 |

**Q1l. DuckDB's memory by tag  (0 s)**

| tag | memory_usage_bytes | temporary_storage_bytes |
|---|---|---|
| IN_MEMORY_TABLE | 929,494,784 | 0 |

```text
peak RSS 1.97 GiB
```

The table NEU-2152 builds (typed columns, `payee_key`, `counted`) holds 887.4 MiB in DuckDB
memory (930,543,360 bytes, 0.87 GiB, by `duckdb_memory()`), and the process peaked at 1.97 GiB. The transform holds every silver table in memory until
it is written. So, beside the 2024 transform's 26.48 GiB peak (`docs/capacity.md`, build
`20261116T005426Z`, at "write contribution"), the table adds about 0.87 GiB: about 27.35 GiB
against the 32 GB (29.80 GiB) limit. The earlier transform-only build `20261115T182139Z` peaked at
28.97 GiB, and 0.87 GiB more would have crossed the limit. This is the budget NEU-2152 is held to.

## Q2: every cycle's profile (2004–2026)

```python
# Every cycle's oppexp, fetched, profiled and deleted, one at a time.
con.execute("""CREATE TABLE profile (cycle INT, zip_bytes BIGINT, text_bytes BIGINT, rows BIGINT, fields VARCHAR,
    dollars DECIMAL(18, 2), r1_dollars DECIMAL(18, 2), memo_rows DOUBLE, memo_dollars DOUBLE,
    paper_rows DOUBLE, paper_dollars DOUBLE, back_ref_rows DOUBLE, linked_children DOUBLE,
    full_parent_dollars DOUBLE, category_rows DOUBLE, category_dollars DOUBLE, entity_rows DOUBLE,
    entity_dollars DOUBLE, purpose_rows DOUBLE, purpose_dollars DOUBLE, forms VARCHAR, earliest DATE, latest DATE,
    undated BIGINT, repeats BIGINT, paper_n BIGINT, not_electronic_n BIGINT)""")
for cycle in range(2004, 2027, 2):
    yy = f"{cycle % 100:02d}"
    z = fetch(f"{cycle}/oppexp{yy}.zip")
    view_oppexp("raw", z)
    text = work / "raw.txt"
    fields = con.execute(f"""SELECT string_agg(f || ': ' || n, ', ' ORDER BY f) FROM (
        SELECT len(string_split(line, '|')) AS f, count(*) AS n
        FROM read_csv({literal(text)}, delim = '\\x01', quote = '', escape = '', header = false,
                      auto_detect = false, columns = {{'line': 'VARCHAR'}}) GROUP BY 1)""").fetchone()[0]
    typed("cyc", "raw")
    con.execute("""CREATE OR REPLACE TABLE kid AS
        SELECT CMTE_ID, fnum, back AS tran, sum(amt) AS kid_amt, count(*) AS kids
        FROM ox WHERE back IS NOT NULL GROUP BY ALL""")
    con.execute(f"""INSERT INTO profile
    WITH par AS (SELECT p.amt, abs(k.kid_amt - p.amt) <= 1.00 AS ok, k.kids FROM ox AS p
                 JOIN kid AS k ON k.CMTE_ID = p.CMTE_ID AND k.fnum = p.fnum AND k.tran = p.tran)
    SELECT {cycle}, {z.stat().st_size}, {text.stat().st_size}, count(*), '{fields}', sum(amt),
        sum(amt) FILTER (WHERE NOT memo), avg(memo::INT), sum(amt) FILTER (WHERE memo) / sum(amt),
        avg((tran IS NULL)::INT), sum(amt) FILTER (WHERE tran IS NULL) / sum(amt),
        avg((back IS NOT NULL)::INT), (SELECT sum(kids) FROM par) / nullif(count(*) FILTER (WHERE back IS NOT NULL), 0),
        (SELECT sum(amt) FILTER (WHERE ok) / sum(amt) FROM par),
        avg((nullif(trim(CATEGORY), '') IS NOT NULL)::INT),
        sum(amt) FILTER (WHERE nullif(trim(CATEGORY), '') IS NOT NULL) / sum(amt),
        avg((nullif(trim(ENTITY_TP), '') IS NOT NULL)::INT),
        sum(amt) FILTER (WHERE nullif(trim(ENTITY_TP), '') IS NOT NULL) / sum(amt),
        avg((purp IS NOT NULL)::INT), sum(amt) FILTER (WHERE purp IS NOT NULL) / sum(amt),
        (SELECT string_agg(k || ' ' || share || '%', ', ' ORDER BY n DESC) FROM (
            SELECT k, n, round(100.0 * n / sum(n) OVER (), 1) AS share
            FROM (SELECT FORM_TP_CD || ' ' || SCHED_TP_CD || ' ' || LINE_NUM AS k, count(*) AS n FROM ox GROUP BY 1)
            QUALIFY row_number() OVER (ORDER BY n DESC) <= 6)),
        min(dt), max(dt), count(*) FILTER (WHERE dt IS NULL),
        (SELECT count(*) FROM cyc WHERE is_repeat), count(*) FILTER (WHERE tran IS NULL),
        count(*) FILTER (WHERE coalesce(fnum, 0) <= 0)
    FROM ox""")
    con.execute("DROP VIEW ox; DROP TABLE cyc; DROP VIEW raw")
    z.unlink()
    text.unlink()
P = "SELECT cycle, "
show("Q2a. Size and shape", P + "zip_bytes, text_bytes, rows, fields, repeats, earliest, latest, undated FROM profile ORDER BY cycle")
show("Q2b. Dollars, memo rows and paper rows", P + """dollars, r1_dollars, memo_rows, memo_dollars,
    paper_n AS rows_without_tran_id, not_electronic_n AS rows_file_num_0_or_blank, paper_dollars FROM profile ORDER BY cycle""")
show("Q2c. Sub-itemization", P + "back_ref_rows, linked_children, full_parent_dollars FROM profile ORDER BY cycle")
show("Q2d. Fill rates of CATEGORY, ENTITY_TP and PURPOSE (rows, dollars)", P + """category_rows, category_dollars,
    entity_rows, entity_dollars, purpose_rows, purpose_dollars FROM profile ORDER BY cycle""")
show("Q2e. Form, schedule and line mix (six commonest, share of rows)", P + "forms FROM profile ORDER BY cycle")
con.execute(f"COPY profile TO {literal(work / 'profile.parquet')} (FORMAT parquet)")
```

```text
https://www.fec.gov/files/bulk-downloads/2004/oppexp04.zip | Last-Modified: Thu, 31 Aug 2017 18:23:31 GMT | bytes 25,734,364 | downloaded 2026-11-21T01:49:50+00:00
https://www.fec.gov/files/bulk-downloads/2006/oppexp06.zip | Last-Modified: Thu, 31 Aug 2017 18:23:48 GMT | bytes 30,217,068 | downloaded 2026-11-21T01:49:58+00:00
https://www.fec.gov/files/bulk-downloads/2008/oppexp08.zip | Last-Modified: Thu, 31 Aug 2017 18:24:16 GMT | bytes 43,785,331 | downloaded 2026-11-21T01:50:07+00:00
https://www.fec.gov/files/bulk-downloads/2010/oppexp10.zip | Last-Modified: Wed, 20 Sep 2017 19:42:31 GMT | bytes 37,478,492 | downloaded 2026-11-21T01:50:17+00:00
https://www.fec.gov/files/bulk-downloads/2012/oppexp12.zip | Last-Modified: Wed, 20 Sep 2017 19:43:53 GMT | bytes 45,382,905 | downloaded 2026-11-21T01:50:26+00:00
https://www.fec.gov/files/bulk-downloads/2014/oppexp14.zip | Last-Modified: Sun, 30 Dec 2018 16:48:29 GMT | bytes 38,894,605 | downloaded 2026-11-21T01:50:36+00:00
https://www.fec.gov/files/bulk-downloads/2016/oppexp16.zip | Last-Modified: Sun, 16 Oct 2022 15:14:21 GMT | bytes 51,856,704 | downloaded 2026-11-21T01:50:47+00:00
https://www.fec.gov/files/bulk-downloads/2018/oppexp18.zip | Last-Modified: Sun, 01 Jan 2023 16:49:45 GMT | bytes 52,731,735 | downloaded 2026-11-21T01:51:00+00:00
https://www.fec.gov/files/bulk-downloads/2020/oppexp20.zip | Last-Modified: Sun, 29 Dec 2024 22:10:14 GMT | bytes 64,556,004 | downloaded 2026-11-21T01:51:11+00:00
https://www.fec.gov/files/bulk-downloads/2022/oppexp22.zip | Last-Modified: Sun, 15 Nov 2026 17:44:01 GMT | bytes 56,164,549 | downloaded 2026-11-21T01:51:27+00:00
https://www.fec.gov/files/bulk-downloads/2026/oppexp26.zip | Last-Modified: Sun, 15 Nov 2026 17:12:25 GMT | bytes 50,362,004 | downloaded 2026-11-21T01:51:51+00:00
```

**Q2a. Size and shape  (0 s)**

| cycle | zip_bytes | text_bytes | rows | fields | repeats | earliest | latest | undated |
|---|---|---|---|---|---|---|---|---|
| 2,004 | 25,734,364 | 168,173,606 | 953,645 | 26: 954706 | 1,061 | 1998-07-03 | 2020-12-30 | 222 |
| 2,006 | 30,217,068 | 196,090,957 | 1,104,456 | 26: 1104753 | 297 | 1995-10-21 | 2009-10-29 | 525 |
| 2,008 | 43,785,331 | 289,573,859 | 1,637,960 | 26: 1639878 | 1,918 | 1900-01-01 | 2027-09-09 | 381 |
| 2,010 | 37,478,492 | 242,359,398 | 1,338,036 | 26: 1339329 | 1,293 | 1930-10-29 | 2091-07-29 | 493 |
| 2,012 | 45,382,905 | 299,958,848 | 1,654,328 | 26: 1656089 | 1,761 | 1899-12-30 | 9201-12-02 | 297 |
| 2,014 | 38,894,605 | 249,571,328 | 1,351,066 | 26: 1351071 | 5 | 1925-04-02 | 2714-03-01 | 55 |
| 2,016 | 51,856,704 | 329,929,014 | 1,743,435 | 26: 1744187 | 752 | 1201-04-02 | 9201-11-01 | 152 |
| 2,018 | 52,731,735 | 343,941,837 | 1,799,908 | 26: 1800080 | 172 | 1930-02-18 | 9201-10-02 | 252 |
| 2,020 | 64,556,004 | 436,137,842 | 2,309,716 | 26: 2310524 | 808 | 1919-06-19 | 2029-12-11 | 15 |
| 2,022 | 56,164,549 | 376,665,034 | 1,944,035 | 26: 1962279 | 18,244 | 1931-09-01 | 2033-07-30 | 0 |
| 2,024 | 64,105,756 | 429,582,743 | 2,246,968 | 26: 2249911 | 2,943 | 2001-01-01 | 2042-09-20 | 0 |
| 2,026 | 50,362,004 | 343,933,588 | 1,790,165 | 26: 1790165 | 0 | 1960-05-01 | 2056-04-17 | 0 |

**Q2b. Dollars, memo rows and paper rows  (0 s)**

| cycle | dollars | r1_dollars | memo_rows | memo_dollars | rows_without_tran_id | rows_file_num_0_or_blank | paper_dollars |
|---|---|---|---|---|---|---|---|
| 2,004 | 2,861,046,327 | 2,253,896,775 | 16.28% | 21.22% | 0 | 0 |  |
| 2,006 | 2,241,148,576 | 2,112,593,441 | 20.08% | 5.74% | 0 | 462 |  |
| 2,008 | 4,155,611,215 | 3,876,201,602 | 29.03% | 6.72% | 0 | 0 |  |
| 2,010 | 2,834,403,321 | 2,677,040,313 | 21.76% | 5.55% | 0 | 0 |  |
| 2,012 | 4,659,469,326 | 4,421,733,135 | 25.70% | 5.10% | 0 | 0 |  |
| 2,014 | 2,838,491,474 | 2,636,026,727 | 25.71% | 7.13% | 4 | 0 | 0.00% |
| 2,016 | 5,238,038,133 | 4,875,822,875 | 32.43% | 6.92% | 0 | 0 |  |
| 2,018 | 4,583,985,466 | 4,278,244,156 | 27.70% | 6.67% | 0 | 0 |  |
| 2,020 | 12,393,887,121 | 11,617,640,862 | 34.01% | 6.26% | 0 | 0 |  |
| 2,022 | 6,889,420,974 | 6,523,144,655 | 23.37% | 5.32% | 0 | 0 |  |
| 2,024 | 10,257,688,169 | 9,730,497,943 | 30.97% | 5.14% | 0 | 0 |  |
| 2,026 | 6,272,203,109 | 5,784,650,969 | 25.69% | 7.77% | 0 | 0 |  |

**Q2c. Sub-itemization  (0 s)**

| cycle | back_ref_rows | linked_children | full_parent_dollars |
|---|---|---|---|
| 2,004 | 8.81% | 94.11% | 79.71% |
| 2,006 | 7.12% | 92.37% | 69.01% |
| 2,008 | 19.80% | 97.10% | 84.68% |
| 2,010 | 11.33% | 94.74% | 65.83% |
| 2,012 | 15.04% | 95.63% | 73.29% |
| 2,014 | 13.90% | 95.73% | 64.87% |
| 2,016 | 22.62% | 97.76% | 47.73% |
| 2,018 | 22.00% | 96.14% | 57.78% |
| 2,020 | 29.89% | 98.18% | 58.55% |
| 2,022 | 22.21% | 98.46% | 51.09% |
| 2,024 | 30.14% | 98.92% | 47.78% |
| 2,026 | 25.27% | 98.39% | 57.40% |

**Q2d. Fill rates of CATEGORY, ENTITY_TP and PURPOSE (rows, dollars)  (0 s)**

| cycle | category_rows | category_dollars | entity_rows | entity_dollars | purpose_rows | purpose_dollars |
|---|---|---|---|---|---|---|
| 2,004 | 25.81% | 13.16% | 95.27% | 97.37% | 98.61% | 82.55% |
| 2,006 | 24.32% | 18.84% | 84.88% | 73.58% | 99.50% | 99.37% |
| 2,008 | 25.06% | 18.33% | 89.36% | 87.93% | 99.66% | 99.80% |
| 2,010 | 30.16% | 26.02% | 83.00% | 70.51% | 99.46% | 99.78% |
| 2,012 | 29.38% | 20.98% | 86.30% | 82.38% | 99.64% | 99.89% |
| 2,014 | 31.89% | 27.00% | 82.92% | 73.93% | 99.65% | 99.89% |
| 2,016 | 24.64% | 16.81% | 86.64% | 84.89% | 99.67% | 99.83% |
| 2,018 | 28.32% | 23.40% | 90.67% | 90.38% | 99.52% | 99.84% |
| 2,020 | 22.07% | 15.10% | 99.80% | 99.98% | 99.56% | 99.94% |
| 2,022 | 30.18% | 23.56% | 99.87% | 99.98% | 99.60% | 99.91% |
| 2,024 | 26.81% | 16.25% | 99.89% | 99.99% | 99.67% | 99.93% |
| 2,026 | 29.56% | 30.62% | 99.98% | 100.00% | 99.57% | 99.89% |

**Q2e. Form, schedule and line mix (six commonest, share of rows)  (0 s)**

| cycle | forms |
|---|---|
| 2,004 | F3 SB 17 46.2%, F3X SB 21B 33.1%, F3P SB 23 20.7% |
| 2,006 | F3 SB 17 64.3%, F3X SB 21B 34.7%, F3P SB 23 1.0%, F3X SB 21 0.0% |
| 2,008 | F3 SB 17 46.9%, F3X SB 21B 26.9%, F3P SB 23 26.2%, F3X SB 21 0.0% |
| 2,010 | F3 SB 17 68.1%, F3X SB 21B 31.1%, F3P SB 23 0.9%, F3X SB 21 0.0% |
| 2,012 | F3 SB 17 55.1%, F3X SB 21B 30.7%, F3P SB 23 14.2%, F3X SB 21 0.0% |
| 2,014 | F3 SB 17 63.3%, F3X SB 21B 36.2%, F3P SB 23 0.5%, F3X SB 21 0.0% |
| 2,016 | F3 SB 17 48.5%, F3X SB 21B 34.0%, F3P SB 23 17.5%, F3X SB 21 0.0%, F3X SB 21C 0.0% |
| 2,018 | F3 SB 17 61.6%, F3X SB 21B 37.3%, F3P SB 23 1.1% |
| 2,020 | F3 SB 17 45.1%, F3X SB 21B 32.0%, F3P SB 23 22.9%, F3X SB 21 0.0% |
| 2,022 | F3 SB 17 60.0%, F3X SB 21B 39.7%, F3P SB 23 0.3%, F3X SB 21 0.0% |
| 2,024 | F3 SB 17 50.7%, F3X SB 21B 40.2%, F3P SB 23 9.0%, F3X SB 21 0.0% |
| 2,026 | F3 SB 17 57.1%, F3X SB 21B 42.7%, F3P SB 23 0.2%, F3X SB 21 0.0% |

Read across, three things change:

- **Sub-itemization.** Children are 7–30% of rows. Their parents are in the file for 92–99% of
  them. Fully itemized parents hold 47.73% (2016) to 84.68% (2008) of parent dollars: the bar
  is met in every cycle but 2016 and 2024. Parent always is right where the bar fails and loses
  payee detail where it passes. NEU-2150 should decide whether the rule is one rule for every
  cycle (as adopted here, from 2024) or the bar applied per cycle.
- **Memo dollars in 2004** are 21.22% of the file, against 5–8% in every later cycle.
  2004's parents are fully itemized for 79.71% of their dollars, so its memo children mostly
  restate their parents, as later cycles' do.
- **`ENTITY_TP`** is filled on 70.5–90.4% of dollars from 2006 to 2018 (97.37% in 2004) and on
  99.98% or more from 2020.
  A payee-is-a-person rule that reads it (Q9) holds from 2020 only. `PURPOSE` is filled on 99%
  or more of rows in every cycle, and on 82.55% of 2004's dollars.

There are no paper rows to treat differently: no cycle has more than 4 rows without a
`TRAN_ID` (Q4c). Every cycle has the trailing `|` and only lines 17, 21(b) and 23 (and a handful of
`21`, `21C`). Repeated rows appear in every cycle but 2026, 18,244 of them in 2022. Out-of-range
dates appear in every cycle (years 1201 to 9201).

## Q3: sub-itemization (2024)

`fam.py` is one row per parent with its children's sum, and one row per row of `ox` with its role
and three rules. R1 is FEC's (non-memo rows). R2c is §1.1's children-where-they-add-up rule. R2 is
parent always.

```python
# A parent's kind (§2): `card` when the payee or the purpose names a card or its issuer,
# `reimbursement` when the payee is a person or the purpose names a reimbursement.
CARD = (r"\b(AMERICAN EXPRESS|AMEX|CAPITAL ONE|CHASE|CITI ?CARDS?|CITIBANK|BANK OF AMERICA|"
        r"BARCLAY ?CARD|BARCLAYS|DISCOVER|MASTER ?CARD|VISA|CREDIT CARD|CARD ?MEMBER|"
        r"CARD SERVICES|ELAN|U\.? ?S\.? BANK|WELLS FARGO|FIRST NATIONAL BANK|BREX|RAMP|DIVVY)\b")
con.execute(f"""
CREATE TABLE fam AS
WITH kid AS (
    SELECT CMTE_ID, fnum, back AS tran, count(*) AS kids, sum(amt) AS kid_amt,
        count(*) FILTER (WHERE memo) AS memo_kids, coalesce(sum(amt) FILTER (WHERE memo), 0) AS memo_kid_amt
    FROM ox WHERE back IS NOT NULL GROUP BY ALL
)
SELECT p.sid, p.CMTE_ID, p.fnum, p.tran, p.amt, p.memo, p.NAME, p.purp, p.ENTITY_TP, p.filer,
    p.back AS parent_back, k.kids, k.kid_amt, k.memo_kids, k.memo_kid_amt,
    abs(k.kid_amt - p.amt) <= 1.00 AS is_full,
    CASE
        WHEN (coalesce(p.ENTITY_TP, '') <> 'IND' AND regexp_matches(upper(p.NAME), '{CARD}'))
            OR regexp_matches(coalesce(p.purp, ''), '\\bCREDIT CARD\\b') THEN 'card'
        WHEN p.ENTITY_TP = 'IND' OR regexp_matches(coalesce(p.purp, ''), 'REIMB') THEN 'reimbursement'
        ELSE 'other'
    END AS kind
FROM ox AS p
JOIN kid AS k ON k.CMTE_ID = p.CMTE_ID AND k.fnum = p.fnum AND k.tran = p.tran
""")
# Each row's role, and the three counting rules Q3 compares (§2). R1: non-memo rows, FEC's own.
# R2c, §1.1's rule: a fully itemized parent gives way to its children, whatever their memo code; a
# child counts when its parent is fully itemized; any other parent counts. R2, parent always: a
# parent counts, whatever its memo code, and a child of a parent in the file never does. Under both,
# a child whose parent is not in the file, and every other row, counts when it is not a memo row. A
# row that is both a child and a parent (a chain) is read as a child first.
# Q3's decision adopts R2 (the bar is not met), so "counted" from Q6 on is R2 with Q6's and Q7's
# exclusions.
con.execute("""
CREATE TABLE r2 AS
SELECT o.sid, o.amt, o.memo,
    CASE
        WHEN f.sid IS NOT NULL AND pf.sid IS NOT NULL THEN 'chain'
        WHEN f.sid IS NOT NULL THEN CASE WHEN f.is_full THEN 'full parent' ELSE 'partial parent' END
        WHEN pf.sid IS NOT NULL THEN CASE WHEN pf.is_full THEN 'child of full' ELSE 'child of partial' END
        WHEN o.back IS NOT NULL THEN 'orphan child'
        ELSE 'plain'
    END AS role,
    pf.sid AS parent_sid,
    NOT o.memo AS r1,
    CASE
        WHEN pf.sid IS NOT NULL THEN false
        WHEN f.sid IS NOT NULL THEN true
        ELSE NOT o.memo
    END AS r2,
    CASE
        WHEN f.is_full THEN false
        WHEN pf.sid IS NOT NULL THEN pf.is_full
        WHEN f.sid IS NOT NULL THEN true
        ELSE NOT o.memo
    END AS r2c
FROM ox AS o
LEFT JOIN fam AS f ON f.sid = o.sid
LEFT JOIN fam AS pf ON pf.CMTE_ID = o.CMTE_ID AND pf.fnum = o.fnum AND pf.tran = o.back
""")
```

```python
show("Q3a. Rows by role, under R1, R2c and R2", """
SELECT role, count(*) AS rows, sum(amt) AS dollars, avg(memo::INT)::DOUBLE AS memo_rows,
    sum(amt) FILTER (WHERE r1) AS r1_dollars, sum(amt) FILTER (WHERE r2c) AS r2c_dollars,
    sum(amt) FILTER (WHERE r2) AS r2_dollars
FROM r2 GROUP BY ALL ORDER BY dollars DESC""")
show("Q3b. Parents by kind and filer group", """
SELECT kind, filer, count(*) AS parents, sum(amt) AS dollars, avg(memo::INT)::DOUBLE AS memo_parents,
    sum(kids) AS children, avg(is_full::INT)::DOUBLE AS full_by_parents,
    (sum(amt) FILTER (WHERE is_full) / sum(amt))::DOUBLE AS full_by_dollars
FROM fam GROUP BY ROLLUP (kind, filer) ORDER BY kind NULLS LAST, dollars DESC""")
show("Q3c. The 25 parent payees with the most dollars, by kind", """
SELECT kind, upper(NAME) AS payee, count(*) AS parents, sum(amt) AS dollars,
    avg(is_full::INT)::DOUBLE AS full_by_parents
FROM fam GROUP BY ALL ORDER BY dollars DESC LIMIT 25""")
show("Q3d. Parent memo code against child memo code", """
SELECT f.memo AS parent_memo, c.memo AS child_memo, count(DISTINCT f.sid) AS parents,
    sum(f.amt) FILTER (WHERE c.first) AS parent_dollars, count(*) AS children, sum(c.amt) AS child_dollars,
    (sum(f.amt) FILTER (WHERE c.first AND f.is_full) / sum(f.amt) FILTER (WHERE c.first))::DOUBLE AS full_by_dollars
FROM (SELECT r2.parent_sid, r2.memo, r2.amt,
             row_number() OVER (PARTITION BY r2.parent_sid, r2.memo ORDER BY r2.sid) = 1 AS first
      FROM r2 WHERE parent_sid IS NOT NULL) AS c
JOIN fam AS f ON f.sid = c.parent_sid
GROUP BY ALL ORDER BY ALL""")
show("Q3e. Neither a memo row: the parents with the most dollars (R1 counts both sides)", """
SELECT f.CMTE_ID, f.filer, f.kind, f.NAME, f.purp, f.amt, f.kids, f.kid_amt, f.is_full, f.memo_kids
FROM fam AS f WHERE NOT f.memo AND f.memo_kids < f.kids ORDER BY f.amt DESC LIMIT 15""")
show("Q3f. Chains (a child that is a parent)", """
SELECT r2.role, count(*) AS rows, sum(r2.amt) AS dollars, sum(r2.amt) FILTER (WHERE r2.r2c) AS r2c_dollars, sum(r2.amt) FILTER (WHERE r2.r2) AS r2_dollars,
    count(*) FILTER (WHERE f.parent_back IS NOT NULL AND
        EXISTS (SELECT 1 FROM fam AS g WHERE g.CMTE_ID = f.CMTE_ID AND g.fnum = f.fnum AND g.tran = f.parent_back
                AND g.parent_back IS NOT NULL)) AS deeper_than_two
FROM r2 JOIN fam AS f ON f.sid = r2.sid WHERE r2.role = 'chain' GROUP BY ALL""")
show("Q3g. Children ÷ parent, for every parent", """
SELECT CASE
        WHEN is_full THEN '1. within $1 (fully itemized)'
        WHEN amt = 0 THEN '7. parent $0'
        WHEN kid_amt / amt < 0 THEN '6. opposite sign'
        WHEN kid_amt / amt < 0.5 THEN '2. under 50%'
        WHEN kid_amt / amt < 0.99 THEN '3. 50% to 99%'
        WHEN kid_amt / amt <= 1.01 THEN '4. 99% to 101%, not within $1'
        ELSE '5. over 101%'
    END AS children_over_parent,
    count(*) AS parents, sum(amt) AS parent_dollars, sum(kid_amt) AS child_dollars
FROM fam GROUP BY ALL ORDER BY ALL""")
show("Q3h. Under 50%: how many children, and their memo codes", """
SELECT CASE WHEN kids = 1 THEN '1' WHEN kids <= 5 THEN '2-5' ELSE '6+' END AS children,
    memo_kids = kids AS all_memo, count(*) AS parents, sum(amt) AS parent_dollars, sum(kid_amt) AS child_dollars
FROM fam WHERE NOT is_full AND amt <> 0 AND kid_amt / amt BETWEEN 0 AND 0.5 GROUP BY ALL ORDER BY ALL""")

# The 100 parents (Q3 of the spec): in card and reimbursement, the 25 largest and 25 by
# hash(SUB_ID), each with its children, ten largest first.
con.execute("""
CREATE TEMP TABLE pick AS
SELECT * FROM (
    SELECT f.*, 'largest' AS pick, row_number() OVER (PARTITION BY kind ORDER BY amt DESC, sid) AS n
    FROM fam AS f WHERE kind IN ('card', 'reimbursement')) WHERE n <= 25
UNION ALL
SELECT * FROM (
    SELECT f.*, 'hash' AS pick, row_number() OVER (PARTITION BY kind ORDER BY hash(sid), sid) AS n
    FROM fam AS f WHERE kind IN ('card', 'reimbursement')
        AND sid NOT IN (SELECT sid FROM (SELECT sid, row_number() OVER (PARTITION BY kind ORDER BY amt DESC, sid) AS m
                                          FROM fam WHERE kind IN ('card', 'reimbursement')) WHERE m <= 25)) WHERE n <= 25
""")
show("Q3i. The 100 parents, with their children", """
SELECT p.kind, p.pick, p.n, p.CMTE_ID, p.NAME AS parent, p.purp, p.amt, p.memo, p.kids, p.kid_amt, p.is_full,
    string_agg(concat(c.NAME, ' ', c.amt, CASE WHEN c.memo THEN ' X' ELSE '' END), '; '
               ORDER BY c.amt DESC) FILTER (WHERE c.k <= 10) AS largest_children
FROM pick AS p
JOIN (SELECT o.*, r2.parent_sid, row_number() OVER (PARTITION BY r2.parent_sid ORDER BY o.amt DESC, o.sid) AS k
      FROM ox AS o JOIN r2 USING (sid) WHERE r2.parent_sid IN (SELECT sid FROM pick)) AS c ON c.parent_sid = p.sid
GROUP BY ALL ORDER BY p.kind, p.pick DESC, p.n""")

show("Q3j. The decision: §1.1's bar, and the dollars on each side", """
SELECT sum(amt) AS parent_dollars, sum(amt) FILTER (WHERE is_full) AS full_parent_dollars,
    (sum(amt) FILTER (WHERE is_full) / sum(amt))::DOUBLE AS full_share,
    sum(kid_amt) FILTER (WHERE is_full) AS counted_at_children,
    sum(amt) FILTER (WHERE NOT is_full) AS counted_at_parents,
    sum(amt) FILTER (WHERE NOT is_full AND kind = 'card') AS card_dollars_kept_by_issuer,
    sum(kid_amt) FILTER (WHERE NOT is_full) AS child_dollars_reaching_no_payee
FROM fam""")
show("Q3k. The bar at other tolerances (not adopted: §1.1 pins $1.00)", """
SELECT tolerance, (sum(amt) FILTER (WHERE ok) / sum(amt))::DOUBLE AS share_of_parent_dollars,
    count(*) FILTER (WHERE ok) AS parents
FROM (SELECT '$1.00' AS tolerance, amt, abs(kid_amt - amt) <= 1.00 AS ok FROM fam
      UNION ALL SELECT '1% of the parent', amt, abs(kid_amt - amt) <= abs(amt) * 0.01 FROM fam
      UNION ALL SELECT '5% of the parent', amt, abs(kid_amt - amt) <= abs(amt) * 0.05 FROM fam)
GROUP BY ALL ORDER BY share_of_parent_dollars""")
show("Q3l. R1, R2c and R2, every row", """
SELECT sum(amt) FILTER (WHERE r1) AS r1, sum(amt) FILTER (WHERE r2c) AS r2c, sum(amt) FILTER (WHERE r2) AS r2,
    sum(amt) FILTER (WHERE r1 AND NOT r2) AS r1_not_r2, sum(amt) FILTER (WHERE r2 AND NOT r1) AS r2_not_r1,
    count(*) FILTER (WHERE r1) AS r1_rows, count(*) FILTER (WHERE r2) AS r2_rows
FROM r2""")
show("Q3m. Where R2 and R1 part", """
SELECT role, memo, r1, r2, count(*) AS rows, sum(amt) AS dollars FROM r2
WHERE r1 <> r2 GROUP BY ALL ORDER BY dollars DESC""")
show("Q3n. Orphan children: is their parent on another filing of the committee? (spec §3)", """
WITH o AS (SELECT x.CMTE_ID, x.back FROM ox AS x JOIN r2 USING (sid) WHERE r2.role = 'orphan child'),
t AS (SELECT DISTINCT CMTE_ID, tran FROM ox)
SELECT t.tran IS NOT NULL AS a_payment_elsewhere_has_that_tran_id, count(*) AS orphans
FROM o LEFT JOIN t ON t.CMTE_ID = o.CMTE_ID AND t.tran = o.back GROUP BY ALL""")
con.execute(f"COPY r2 TO {literal(work / 'r2.parquet')} (FORMAT parquet)")
con.execute(f"COPY fam TO {literal(work / 'fam.parquet')} (FORMAT parquet)")
```

**Q3a. Rows by role, under R1, R2c and R2  (0 s)**

| role | rows | dollars | memo_rows | r1_dollars | r2c_dollars | r2_dollars |
|---|---|---|---|---|---|---|
| plain | 1,489,389 | 9,210,299,565 | 1.71% | 9,186,808,950 | 9,186,808,950 | 9,186,808,950 |
| partial parent | 24,526 | 273,720,413 | 0.07% | 273,572,711 | 273,720,413 | 273,720,413 |
| child of partial | 427,309 | 252,540,826 | 99.98% | 17,676 |  |  |
| child of full | 242,737 | 250,477,979 | 100.00% | 8,773 | 250,477,979 |  |
| full parent | 55,715 | 250,477,610 | 0.02% | 250,460,880 |  | 250,477,610 |
| orphan child | 7,284 | 20,160,970 | 4.27% | 19,625,238 | 19,625,238 | 19,625,238 |
| chain | 8 | 10,804 | 87.50% | 3,714 | 599 |  |

**Q3b. Parents by kind and filer group  (0 s)**

| kind | filer | parents | dollars | memo_parents | children | full_by_parents | full_by_dollars |
|---|---|---|---|---|---|---|---|
| card |  | 26,994 | 268,934,976 | 0.02% | 469,334 | 53.32% | 28.27% |
| card | candidate | 13,645 | 132,965,456 | 0.01% | 263,258 | 32.85% | 14.76% |
| card | other | 6,864 | 81,707,733 | 0.04% | 107,362 | 58.65% | 46.84% |
| card | party | 5,952 | 49,686,398 | 0.00% | 90,742 | 94.10% | 31.72% |
| card | super PAC | 533 | 4,575,388 | 0.00% | 7,972 | 53.28% | 51.98% |
| other |  | 17,590 | 206,768,255 | 0.16% | 97,208 | 86.14% | 71.25% |
| other | candidate | 13,802 | 136,756,510 | 0.08% | 72,426 | 88.65% | 84.32% |
| other | other | 2,287 | 52,641,137 | 0.04% | 12,965 | 84.35% | 35.40% |
| other | party | 1,180 | 8,864,332 | 0.00% | 9,822 | 60.76% | 65.16% |
| other | super PAC | 321 | 8,506,277 | 4.98% | 1,995 | 84.42% | 89.32% |
| reimbursement |  | 35,665 | 48,505,596 | 0.01% | 103,512 | 73.39% | 55.93% |
| reimbursement | candidate | 18,349 | 26,958,470 | 0.02% | 55,935 | 64.31% | 48.41% |
| reimbursement | other | 7,186 | 16,422,143 | 0.01% | 29,337 | 70.89% | 66.91% |
| reimbursement | party | 9,307 | 3,574,518 | 0.00% | 16,135 | 93.89% | 67.84% |
| reimbursement | super PAC | 823 | 1,550,465 | 0.00% | 2,105 | 65.98% | 43.12% |
|  |  | 80,249 | 524,208,828 | 0.05% | 670,054 | 69.43% | 47.78% |

**Q3c. The 25 parent payees with the most dollars, by kind  (0 s)**

| kind | payee | parents | dollars | full_by_parents |
|---|---|---|---|---|
| card | AMERICAN EXPRESS | 10,236 | 184,158,562 | 48.54% |
| other | GUSTO | 6,120 | 70,407,785 | 97.68% |
| other | MOVEON.ORG CIVIC ACTION | 28 | 30,969,526 | 0.00% |
| other | PAYROLL DATA PROCESSING | 1,698 | 21,362,440 | 98.41% |
| other | PAYCHEX | 940 | 13,062,712 | 94.57% |
| card | RAMP BUSINESS CORPORATION | 34 | 12,786,908 | 2.94% |
| card | AMERICAN EXPRESS CREDIT CARD | 45 | 6,722,249 | 46.67% |
| card | BANK OF AMERICA | 4,325 | 5,268,183 | 95.35% |
| other | ADP | 704 | 5,039,575 | 95.31% |
| other | JUSTWORKS, INC. AND AFFILIATES | 58 | 4,680,821 | 91.38% |
| card | CHASE CARD SERVICES | 849 | 4,201,466 | 37.34% |
| other | QTI HUMAN RESOURCES | 94 | 4,009,812 | 77.66% |
| card | FIRST BANKCARD | 754 | 3,830,932 | 69.23% |
| other | PRIMEPAY LLC | 64 | 3,788,599 | 89.06% |
| other | ADP, INC. | 215 | 3,370,645 | 97.67% |
| other | ADP INC. | 44 | 3,095,342 | 100.00% |
| other | PAYROLL DATA PROCESSING INC. | 120 | 2,743,128 | 100.00% |
| card | FIRST NATIONAL BANK OF OMAHA | 245 | 2,729,790 | 24.08% |
| card | CARDMEMBER SERVICE | 341 | 2,440,966 | 36.36% |
| other | WINRED TECHNICAL SERVICES, LLC | 199 | 2,380,768 | 82.41% |
| other | PAYCHEX, INC. | 186 | 2,307,923 | 93.55% |
| reimbursement | ROLLA GROUP, LLC | 417 | 2,210,953 | 88.01% |
| card | CAPITAL ONE | 406 | 2,073,019 | 33.25% |
| other | CONCUR TECHNOLOGIES INC | 218 | 2,051,016 | 19.27% |
| other | JOHNSON, PERRY | 7 | 1,918,518 | 100.00% |

**Q3d. Parent memo code against child memo code  (0 s)**

| parent_memo | child_memo | parents | parent_dollars | children | child_dollars | full_by_dollars |
|---|---|---|---|---|---|---|
| False | False | 53 | 1,781,155 | 89 | 17,568 | 0.25% |
| False | True | 80,208 | 523,989,222 | 669,668 | 502,826,375 | 47.80% |
| True | False | 10 | 9,777 | 10 | 12,596 | 81.95% |
| True | True | 27 | 161,744 | 287 | 173,070 | 8.79% |

**Q3e. Neither a memo row: the parents with the most dollars (R1 counts both sides)  (0 s)**

| CMTE_ID | filer | kind | NAME | purp | amt | kids | kid_amt | is_full | memo_kids |
|---|---|---|---|---|---|---|---|---|---|
| C00703975 | candidate | card | RAMP BUSINESS CORPORATION | CREDIT CARD PAYMENT | 1,179,002 | 1,102 | 1,215,145 | False | 1,101 |
| C00027466 | party | card | AMERICAN EXPRESS CREDIT CARD | CREDIT CARD PAYMENT | 242,166 | 71 | 170,976 | False | 70 |
| C00839597 | candidate | card | AMERICAN EXPRESS | CREDIT CARD PAYMENT - SEE BELOW IF ITEMIZED | 55,466 | 40 | 59,390 | False | 39 |
| C00573519 | other | other | TMA DIRECT INC | DIGITAL/FINANCE CONSULTING | 47,497 | 1 | -47,497 | False | 0 |
| C00856237 | candidate | card | AMERICAN EXPRESS | CREDIT CARD PAYMENT - SEE BELOW IF ITEMIZED | 39,994 | 26 | 42,735 | False | 25 |
| C00854778 | candidate | card | DIVVY | CREDIT CARD PAYMENT | 31,323 | 66 | 30,423 | False | 64 |
| C00653196 | candidate | card | CAPITAL ONE | CREDIT CARD PAYMENT - SEE BELOW | 26,214 | 48 | 24,437 | False | 47 |
| C00854778 | candidate | card | DIVVY | CREDIT CARD PAYMENT | 17,571 | 60 | 16,601 | False | 56 |
| C00458976 | candidate | card | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 15,843 | 18 | 15,671 | False | 17 |
| C00697334 | candidate | other | PEX CARD | PRE-LOADED DEBIT CARDS FOR CAMPAIGN STAFF, SEE ATTACHED ITEMIZATION. | 15,001 | 29 | 15,239 | False | 28 |
| C00653196 | candidate | card | PNC BANK | CREDIT CARD PAYMENT - SEE BELOW | 14,079 | 18 | 17,763 | False | 17 |
| C00795823 | candidate | card | BANKCARD CENTER | CREDIT CARD PAYMENT - BELOW IF ITEMIZED | 11,321 | 37 | 10,830 | False | 36 |
| C00308676 | candidate | card | BANK OF AMERICA | CREDIT CARD PAYMENT | 9,826 | 115 | 9,447 | False | 114 |
| C00580068 | other | card | AMERICAN EXPRESS | CREDIT CARD EXPENDITURES - SEE DETAIL BELOW | 9,721 | 46 | 14,641 | False | 45 |
| C00580068 | other | card | AMERICAN EXPRESS | CREDIT CARD EXPENDITURES - SEE DETAIL BELOW | 7,041 | 57 | 6,281 | False | 56 |

**Q3f. Chains (a child that is a parent)  (0 s)**

| role | rows | dollars | r2c_dollars | r2_dollars | deeper_than_two |
|---|---|---|---|---|---|
| chain | 8 | 10,804 | 599 |  | 2 |

**Q3g. Children ÷ parent, for every parent  (0 s)**

| children_over_parent | parents | parent_dollars | child_dollars |
|---|---|---|---|
| 1. within $1 (fully itemized) | 55,720 | 250,483,113 | 250,483,072 |
| 2. under 50% | 2,705 | 9,270,746 | 2,599,209 |
| 3. 50% to 99% | 18,914 | 151,940,092 | 135,374,707 |
| 4. 99% to 101%, not within $1 | 2,330 | 105,982,364 | 105,667,116 |
| 5. over 101% | 542 | 6,423,403 | 8,959,284 |
| 6. opposite sign | 30 | 109,110 | -53,525 |
| 7. parent $0 | 8 | 0 | -254 |

**Q3h. Under 50%: how many children, and their memo codes  (0 s)**

| children | all_memo | parents | parent_dollars | child_dollars |
|---|---|---|---|---|
| 1 | False | 1 | 438 | 85 |
| 1 | True | 1,465 | 1,424,702 | 248,416 |
| 2-5 | True | 990 | 2,214,759 | 526,076 |
| 6+ | True | 255 | 5,634,788 | 1,826,603 |

**Q3i. The 100 parents, with their children  (0 s)**

| kind | pick | n | CMTE_ID | parent | purp | amt | memo | kids | kid_amt | is_full | largest_children |
|---|---|---|---|---|---|---|---|---|---|---|---|
| card | largest | 1 | C00703975 | RAMP BUSINESS CORPORATION | CREDIT CARD PAYMENT | 1,423,109 | False | 775 | 1,419,209 | False | THE GRANDVIEW AT LAS VEGAS 145600.00 X; INTERCONTINENTAL HOTEL GROUP 67970.46 X; HYATT REGENCY GREEN BAY 65609.01 X; SHERATON 47054.26 X; BELLAGIO 42847.90 X; HILTON HOTELS 28770.00 X; PLUGGED IN COLLEC 28500.98 X; WASHINGTON CROSSING INN 26499.90 X; ALL PRO COLOR 26160.51 X; ALL PRO COLOR 24380.00 X |
| card | largest | 2 | C00703975 | RAMP BUSINESS CORPORATION | CREDIT CARD PAYMENT | 1,372,287 | False | 712 | 1,374,469 | False | MARRIOTT 378000.00 X; DEKALBCSD 77811.14 X; PHILADELPHIA TRIBUNE COMPANY 43336.80 X; W HOTELS 40298.00 X; SUMMIT PRINTING 38019.66 X; THE ATLANTA VOICE 30000.00 X; COBO CENTER 26000.00 X; GO VIP WORLDWIDE 25817.81 X; ENTERCOM 24984.90 X; PARTY OF 5 EVENT 19737.18 X |
| card | largest | 3 | C00703975 | RAMP BUSINESS CORPORATION | CREDIT CARD PAYMENT | 1,251,523 | False | 956 | 1,243,557 | False | INTERCONTINENTAL HOTEL GROUP 40000.00 X; CHARTERUP 37400.00 X; EMERY 34991.05 X; AUTOGRAPH COLLECTION HOTELS 34000.00 X; OMNI HOTELS 31388.83 X; HILTON HOTELS 30437.79 X; NOMAD LAS VEGAS 29552.50 X; HILTON HOTELS 27976.00 X; SHERATON 27819.94 X; KEEN WATER SPRINGS 27000.00 X |
| card | largest | 4 | C00703975 | RAMP BUSINESS CORPORATION | CREDIT CARD PAYMENT | 1,179,002 | False | 1,102 | 1,215,145 | False | RENAISSANCE HOTELS 256309.40 X; FOUR SEASONS 55410.93 X; AT&T 47000.00 X; AT&T 42565.61 X; THE WESTIN 40439.97 X; DEKALBCSD 33693.64 X; THE WESTIN 32786.04 X; ZOOM 23953.40 X; ALOFT 23156.40 X; HYATT 21194.40 X |
| card | largest | 5 | C00703975 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 1,030,831 | False | 3,732 | 1,029,921 | False | JW MARRIOTT ESSEX HOUSE 68806.00 X; DELAWARE LIMO 12500.00 X; CANOPY BY HILTON 11400.35 X; DELAWARE LIMO 9179.00 X; DELAWARE LIMO 8214.73 X; EGENCIA 7673.04 X; CANOPY BY HILTON 6344.78 X; DELAWARE LIMO 6007.50 X; EGENCIA 4278.94 X; AVIS RENT A CAR 4058.80 X |
| card | largest | 6 | C00703975 | RAMP BUSINESS CORPORATION | CREDIT CARD PAYMENT | 1,018,593 | False | 543 | 1,008,747 | False | AT&T 99000.00 X; AT&T 92678.02 X; AT&T 92678.01 X; HILTON HOTELS 76605.30 X; BOYNE HLD GROUP SALES 75000.00 X; AT&T 68888.94 X; CITY OF MESA 41519.70 X; SHERATON 24549.48 X; HOTEL FORTY FIVE 19747.00 X; ZOOM 16094.00 X |
| card | largest | 7 | C00828541 | AMERICAN EXPRESS | CREDIT CARD PAYMENT: SEE ITEMIZATIONS IF REQUIRED | 995,074 | False | 2,041 | 995,038 | False | HYATT 46306.00 X; HILTON 39266.10 X; MARRIOTT INTERNATIONAL 30760.65 X; MARRIOTT INTERNATIONAL 29094.89 X; TRUMP HOTEL COLLECTION 22505.52 X; WARWICK HOTEL RITTENHOUSE 20106.52 X; MARRIOTT INTERNATIONAL 11217.00 X; MARRIOTT INTERNATIONAL 10822.30 X; MARRIOTT INTERNATIONAL 10436.52 X; WARWICK HOTEL RITTENHOUSE 9215.00 X |
| card | largest | 8 | C00753558 | AMERICAN EXPRESS | CREDIT CARD PAYMENT - SEE BELOW IF ITEMIZED | 945,454 | False | 5 | 945,454 | True | LAS VEGAS GRAND PRIX INC. 736545.70 X; WALDORF ASTORIA - LAS VEGAS 108300.56 X; AMERICAN EXPRESS 64000.00 X; TICKETMASTER 35850.60 X; THE HAY-ADAMS 757.52 X |
| card | largest | 9 | C00703975 | RAMP BUSINESS CORPORATION | CREDIT CARD PAYMENT | 925,332 | False | 534 | 916,167 | False | CALOOSA SOUND CONVENTION CENTER & AMPHITHEATER 113388.81 X; TUCSON 80100.00 X; DELAWARE RIVER WATERFRONT 79424.00 X; HBCU LIVING LEGENDS GALA 50000.00 X; WALDORF ASTORIA 30317.91 X; DELAWARE RIVER WATERFRONT 30000.00 X; MARKET HALL 24410.00 X; FAIRMONT HOTELS 20730.81 X; FAIRMONT HOTELS 20730.81 X; UNITED CENTER 19699.11 X |
| card | largest | 10 | C00773911 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 917,731 | False | 2,695 | 917,441 | False | INTERCON BARCLAY HOTEL 40947.07 X; HILTON GDN INN SCTSD 17695.71 X; GRAHAMS HOTEL SYSTEMS INC 17652.33 X; WESTIN BOOK CADILLAC 17129.50 X; FAIRMONT CENTURY PLAZA 15976.57 X; MARRIOTT RALEIGH 15904.23 X; THE EDGEWATER HOTEL - LOD 15478.97 X; DELAWARE LIMO 14588.00 X; SHERATON GREAT VALLEY 9114.21 X; WESTIN BOOK CADILLAC 6870.11 X |
| card | largest | 11 | C00773911 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 903,811 | False | 1,024 | 907,934 | False | OMNI WILLIAM PENN HOTEL 181161.89 X; FOUR SEASONS HOTEL HOUSTON 95864.56 X; FAIRMONT SCOTTS LODGING 55841.63 X; FOUR SEASONS HOTEL 30373.72 X; ENTERPRISE RENT A CAR 30142.26 X; SHERATON PHILADELPHIA UNIVERSITY CITY 23845.92 X; FOUR SEASONS RESORT SCOTTSDALE 22792.60 X; INTERCONTINENTIAL MIAMI 18351.53 X; HAMPTON INN & STE MADISON 18283.00 X; THE WESTIN BOOK CADILLAC 17633.35 X |
| card | largest | 12 | C00703975 | RAMP BUSINESS CORPORATION | CREDIT CARD PAYMENT | 853,270 | False | 297 | 858,707 | False | OMNI CHICAGO 197971.62 X; OMNI CHICAGO 174016.15 X; OMNI CHICAGO 120000.00 X; UNITED CENTER 51927.80 X; UNITED CENTER 42274.72 X; HUGHES TRANSPORTATION 37240.00 X; 3BUCKS ARENA 34263.65 X; SOFITEL 17675.70 X; CHICAGO VAN RENTALS 15993.28 X; INTERNATIONAL MINUTE PRESS 14542.44 X |
| card | largest | 13 | C00562983 | AMERICAN EXPRESS | CREDIT CARD PAYMENT, SEE BELOW | 845,130 | False | 2 | 845,130 | True | TATANGO INC. 485130.20 X; FACEBOOK ADVERTISING USA 360000.00 X |
| card | largest | 14 | C00003418 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 821,834 | False | 156 | 821,808 | False | MARRIOTT HOTELS 659848.52 X; UBER 31296.55 X; EZCATER 25214.91 X; OMNI HOTELS & RESORTS 19473.14 X; AMERICAN AIRLINES 17535.15 X; GOOGLE 7280.66 X; GRABIEN 6365.14 X; DELTA AIRLINES 6192.46 X; UNITED AIRLINES 5669.32 X; 10K HILL SOUTH 4625.59 X |
| card | largest | 15 | C00703975 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 798,005 | False | 2,728 | 797,800 | False | THE DRAKE HOTEL 121298.80 X; PARK HYATT CHICAGO 94298.13 X; SHERATON DENVER DOWNTOWN 10867.16 X; SOFITEL 7631.58 X; LUFTHANSA 5285.40 X; EGENCIA 3175.40 X; DELAWARE LIMO 2838.00 X; AMERICAN AIRLINES 2789.36 X; DELTA AIRLINES 2650.93 X; AMERICAN AIRLINES 2621.96 X |
| card | largest | 16 | C00867937 | AMERICAN EXPRESS | CREDIT CARD PAYMENT: SEE ITEMIZATIONS IF REQUIRED | 770,786 | False | 75 | 770,733 | False | GAYLORD ROCKIES RESORT & CONVENTION CENTER 158816.86 X; GAYLORD ROCKIES RESORT & CONVENTION CENTER 84696.00 X; FOUR POINTS BY SHERATON 42081.65 X; THE BROWN PALACE HOTEL 36970.57 X; GEORGIA STATE UNIVERSITY 36913.53 X; CROWN COMPLEX 28230.75 X; MIDLAND COUNTRY CLUB 26184.48 X; PICKERING EVENTS LLC 24514.00 X; HILTON 24401.89 X; SHERATON GREENSBORO 24000.00 X |
| card | largest | 17 | C00703975 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 752,940 | False | 2,192 | 752,331 | False | AIRBNB 11050.07 X; AIRBNB 10022.59 X; AIRBNB 6735.43 X; AIRBNB 5675.09 X; AIRBNB 5488.49 X; AIRBNB 5327.85 X; AIRBNB 5298.56 X; AIRBNB 4840.44 X; AIRBNB 4684.59 X; AIRBNB 4503.66 X |
| card | largest | 18 | C00828541 | AMERICAN EXPRESS | CREDIT CARD PAYMENT: SEE ITEMIZATIONS IF REQUIRED | 747,122 | False | 2,129 | 747,122 | True | TRUMP INTERNATIONAL HOTEL LAS VEGAS 42285.07 X; HILTON 5941.00 X; ENTERPRISE RENT A CAR 5644.41 X; ENTERPRISE RENT A CAR 5211.01 X; HILTON 4459.99 X; BILLBOARD EXPRESS 2729.50 X; INTERCONTINENTAL HOTELS GROUP 2384.51 X; INTERCONTINENTAL HOTELS GROUP 2384.51 X; INTERCONTINENTAL HOTELS GROUP 2384.51 X; INTERCONTINENTAL HOTELS GROUP 2384.51 X |
| card | largest | 19 | C00744946 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 738,242 | False | 844 | 738,073 | False | UNITED CENTER SUITES 165364.92 X; HALL ARTS HOTEL 59086.96 X; COCO'S 58512.68 X; LIMELIGHT CATERING 45325.11 X; UNITED CENTER SUITES 36060.39 X; RESIDENCE INN WILMINGTON DOWNTOWN 34611.63 X; REVEL DECOR 30186.21 X; MANHATTA 21298.39 X; THE WATERGATE HOTEL 20925.00 X; BITE CATERING COUTURE, LLC 14979.00 X |
| card | largest | 20 | C00562983 | AMERICAN EXPRESS | CREDIT CARD PAYMENT, SEE BELOW | 734,756 | False | 2 | 734,756 | True | FACEBOOK ADVERTISING USA 483521.78 X; TATANGO INC. 251233.78 X |
| card | largest | 21 | C00703975 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 715,564 | False | 3,504 | 714,447 | False | AMAZON WEB SERVICES 4882.61 X; EGENCIA 3128.45 X; EGENCIA 2810.28 X; JETBLUE 2694.76 X; EGENCIA 2557.59 X; JETBLUE 2451.16 X; EGENCIA 2078.79 X; EGENCIA 2050.69 X; AMERICAN AIRLINES 2020.48 X; EGENCIA 1975.80 X |
| card | largest | 22 | C00773911 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 714,295 | False | 1,864 | 714,173 | False | W LOS ANGELES 39096.84 X; FAIRMONT CENTURY PLAZA 37628.91 X; H-LOTTE NEW YORK PALACE 24800.40 X; RENAISSANCE PHOENIX DT 15903.06 X; HAMPTON INN GREENSBORO AI 9677.91 X; OMNI WILLIAM PENN 7251.00 X; ENTERPRISE RENT A CAR 6109.12 X; MARRIOTT 337W8 TROY 5729.10 X; HOLIDAY INN EXPRESS PHILADELPHIA 4815.17 X; FOUR POINTS KALAMAZOO 3626.04 X |
| card | largest | 23 | C00703975 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 708,371 | False | 2,565 | 706,879 | False | DELAWARE LIMO 10708.00 X; AIRBNB 8514.66 X; DELAWARE LIMO 6934.98 X; AMERICAN AIRLINES 5908.51 X; AIRBNB 5903.25 X; AIRBNB 4973.93 X; DELAWARE LIMO 4696.50 X; AIRBNB 4683.19 X; AIRBNB 4330.75 X; AIRBNB 3931.11 X |
| card | largest | 24 | C00703975 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 708,371 | False | 2,190 | 668,853 | False | DELAWARE LIMO 9986.56 X; DELAWARE LIMO 9864.35 X; BELLAGIO 7587.22 X; DELAWARE LIMO 6979.04 X; DELAWARE LIMO 5317.11 X; EGENCIA 4645.86 X; EGENCIA 4589.40 X; OMNI CHARLOTTE 4200.00 X; JETBLUE AIRWAYS 3547.03 X; JETBLUE AIRWAYS 3547.03 X |
| card | largest | 25 | C00703975 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 708,371 | False | 2,177 | 707,576 | False | AIRBNB 30589.23 X; AIRBNB 29376.88 X; AIRBNB 18116.97 X; 6 COLUMBUS 17516.13 X; AIRBNB 15970.43 X; AIRBNB 15805.95 X; AIRBNB 15044.01 X; AIRBNB 11796.85 X; AIRBNB 11223.27 X; AIRBNB 10272.53 X |
| card | hash | 1 | C00344648 | CITI CARDS | SEE MEMO | 2,111 | False | 7 | 1,949 | False | CAPITAL JEWISH MUSEUM 1500.00 X; AT&T 156.82 X; WASHINGTON POST 156.76 X; SIRIUS XM 46.73 X; WALL STREET JOURNAL 41.33 X; APPLE 25.94 X; NEW YORK TIMES 21.20 X |
| card | hash | 2 | C00857615 | WINRED TECHNICAL SERVICES, LLC | CREDIT CARD FEES | 140,190 | False | 16 | 140,190 | True | HICKORY DATA LLC 55595.30 X; RED WING STRATEGIES 18096.97 X; TMA DIRECT 15013.94 X; OPINION STRATEGIES 9926.63 X; NORTH COUNTRY STRATEGIES 8374.23 X; BETTER MOUSETRAP DIGITAL 6846.11 X; WINRED TECHNICAL SERVICES, LLC 6582.25 X; OLYMPIC MEDIA 6236.63 X; EDEE INC 4232.67 X; ROC DIGITAL 3958.36 X |
| card | hash | 3 | C00477745 | ARVEST BANK CREDIT CARD | SEE SUBVENDORS | 588 | False | 1 | 301 | False | VA ABC 301.00 X |
| card | hash | 4 | C00310532 | CAPITAL ONE | CREDIT CARD PAYMENT | 4,148 | False | 8 | 2,849 | False | POTBELLY 1028.88 X; AT&T 666.39 X; CAPITOL HILL CLUB 599.46 X; FASTSIGNS 223.64 X; 360 WEB SECURITY SITELOCK 105.54 X; HOSTMONSTER 103.97 X; CAPITAL ONE 96.93 X; MICROSOFT 24.18 X |
| card | hash | 5 | C00539825 | TRUIST BANKCARD CENTER | CREDIT CARD PAYMENT | 1,205 | False | 10 | 1,205 | True | CONSTANT CONTACT 322.56 X; AT&T 286.55 X; UBER 142.64 X; US SENATE STATIONERY 104.00 X; DELTA 98.89 X; DELTA 98.89 X; ON THE MOVE SELF STORAGE 92.00 X; UBER 28.41 X; CONSTANT CONTACT 21.40 X; CONSTANT CONTACT 9.98 X |
| card | hash | 6 | C00842104 | CARDMEMBER SERVICES | CREDIT CARD PAYMENT | 3,746 | False | 8 | 3,746 | True | DELTA AIRLINES 1158.00 X; DELTA AIRLINES 749.00 X; DELTA AIRLINES 435.00 X; DELTA AIRLINES 398.10 X; AMERICAN AIRLINES 317.10 X; AMERICAN AIRLINES 270.10 X; ALASKA AIRLINES INC 229.10 X; DELTA AIRLINES 190.00 X |
| card | hash | 7 | C00367862 | AMERICAN EXPRESS* | CATERING, EMAIL SERVICE | 1,437 | False | 4 | 1,437 | True | CAPITOL HILL CLUB 1117.09 X; CAPITOL HILL CLUB 215.15 X; CONSTANT CONTACT 81.00 X; GOOGLE BUSINESS SERVICE 24.00 X |
| card | hash | 8 | C00431353 | CARDMEMBER SERVICE | CREDIT CARD PAYMENT - SEE BELOW IF ITEMIZED | 18,981 | False | 206 | 16,619 | False | GOOGLE 1529.41 X; HERTZ CAR RENTAL 1088.00 X; DELTA AIRLINES 793.96 X; KOWALSKI'S MARKET 763.17 X; DELTA AIRLINES 653.96 X; COMCAST 622.25 X; UNITED AIRLINES 619.37 X; DELTA AIRLINES 600.48 X; SOUTHWEST AIRLINES 586.98 X; DELTA AIRLINES 532.98 X |
| card | hash | 9 | C00000935 | BANK OF AMERICA | TRAVEL | 805 | False | 4 | 805 | True | AMERICAN AIRLINES 536.20 X; AMERICAN AIRLINES 251.21 X; EGENCIA FEE 9.00 X; EGENCIA FEE 9.00 X |
| card | hash | 10 | C00000935 | BANK OF AMERICA | TRAVEL | 337 | False | 1 | 337 | True | AMTRAK 337.00 X |
| card | hash | 11 | C00701672 | CARD SERVICES | CREDIT CARD PAYMENT | 10,229 | False | 17 | 9,850 | False | THE BEN AUTOGRAPH COLLECTION 3517.97 X; DC BUS CHARTER 2047.50 X; AMERICAN AIRLINES 785.64 X; TRUMP NATIONAL GOLF CLUB JUPITER 509.33 X; PROPER GRIT 500.00 X; ELISABETTAS RISORANTE 464.68 X; TRUMP INTERNATIONAL GOLF CLUB WEST PALM BEACH 417.30 X; COSTCO 286.15 X; MARYLAND JOCKEY CLUB 275.00 X; DOROTHY MCDANIELS FLOWER MARKET 210.05 X |
| card | hash | 12 | C00000935 | BANK OF AMERICA | TRAVEL | 404 | False | 2 | 404 | True | AMERICAN AIRLINES 394.68 X; EGENCIA FEE 9.00 X |
| card | hash | 13 | C00000935 | BANK OF AMERICA | GENERIC CMTE. SUBSCRIPTIONS | 698 | False | 3 | 698 | True | HAPPYFOX 474.00 X; GOOGLE CLOUD 111.87 X; GOOGLE CLOUD 111.64 X |
| card | hash | 14 | C00000935 | BANK OF AMERICA | GENERIC CMTE. SUBSCRIPTIONS | 630 | False | 5 | 630 | True | DROPBOX 265.00 X; DROPBOX 265.00 X; WALL STREET JOURNAL 41.33 X; COOK POLITICAL REPORT 37.10 X; NY TIMES 21.20 X |
| card | hash | 15 | C00556365 | BB&T | CREDIT CARD PAYMENT- SEE MEMOS | 567 | False | 2 | 567 | True | CAPITOL HILL CLUB 451.67 X; VERIZON WIRELESS 115.19 X |
| card | hash | 16 | C00573758 | CAPITAL ONE | CREDIT CARD PAYMENT | 4,111 | False | 6 | 3,274 | False | LEXISNEXIS 1823.20 X; AMERICAN SELF STORAGE 639.00 X; GOOGLE 381.60 X; CONSTANT CONTACT 315.00 X; INTUIT QUICKBOOKS 85.00 X; ZOOM.US 29.98 X |
| card | hash | 17 | C00516724 | BB&T CREDIT CARD | CREDIT CARD PAYMENT-SEE MEMOS | 818 | False | 2 | 731 | False | AMERICAN AIRLINES 411.60 X; ENTERPRISE RENT A CAR 319.62 X |
| card | hash | 18 | C00193433 | AMERICAN EXPRESS | TRAVEL/ACCOMMODATION /MEALS | 142 | False | 1 | 142 | True | UNITED ELEC TICKETNG 142.14 X |
| card | hash | 19 | C00789834 | CHASE CARD SERVICES | CREDIT CARD PAYMENT - SEE MEMOS | 1,652 | False | 3 | 1,652 | True | THE RITZ-CARLTON HOTEL COMPANY LLC 1014.00 X; W HOTELS WORLDWIDE - STARWOOD HOTELS & RESORTS 421.55 X; AMERICAN AIRLINES 216.90 X |
| card | hash | 20 | C00823500 | CARD SERVICES CENTER | CREDIT CARD PAYMENT | 2,956 | False | 7 | 2,860 | False | ROCKET CITY TAVERN 1178.27 X; DELTA 549.95 X; CAPITOL HILL CLUB 494.09 X; AMERICAN AIRLINES 418.96 X; CAPITOL HILL CLUB 140.16 X; CAPITOL HILL CLUB 44.00 X; AMERICAN AIRLINES 35.00 X |
| card | hash | 21 | C00213512 | AMERICAN EXPRESS | CREDIT CARD PAYMENT - SEE BELOW | 82,917 | False | 49 | 80,364 | False | UNITED AIRLINES 20405.39 X; BRITISH AIRPORTS AUTHORITY 9746.87 X; THE RITZ CARLTON 9572.93 X; FOUR SEASONS HOTEL 8593.65 X; MARRIOTT INTERNATIONAL, INC. 5898.87 X; HYATT HOTELS REGENCY 5005.69 X; PEERLY 3915.74 X; CHABE LIMITED 3590.22 X; UBER TECHNOLOGIES, INC. 3565.82 X; AMERICAN AIRLINES 2829.07 X |
| card | hash | 22 | C00373001 | AADVANTAGE CARD SERVICES | SEE MEMO | 8,395 | False | 15 | 7,431 | False | WRIGHT-PATTERSON CLUB 3389.75 X; AMERICAN AIRLINES 787.47 X; CAPITOL HILL CLUB 752.98 X; YOUNG CHOW 380.70 X; ENGINEERS CLUB OF DAYTON 355.60 X; OSAKA JAPANESE STEAKHOUSE 344.23 X; UBER TECHNOLOGIES INC. 306.51 X; OAKWOOD CLUB 291.61 X; HYATT REGENCY 229.44 X; DOROTHY LANE MARKET 189.72 X |
| card | hash | 23 | C00313247 | AMERICAN EXPRESS | CREDIT CARD PAYMENT | 10,392 | False | 20 | 9,483 | False | TASTE GOURMET 4750.90 X; TRATTORIA ALBERTO 1002.89 X; AMERICAN AIRLINES 879.95 X; DANIEL GEORGE RESTAURANT 768.22 X; CHARLIE PALMER STEAK 400.00 X; EMBASSY SUITES 356.27 X; DELTA AIR LINES 299.97 X; THE WAVERLY LOCAL 238.32 X; HELEN 227.77 X; PUBLIX 109.51 X |
| card | hash | 24 | C00837484 | AMERICAN EXPRESS | SEE MEMO | 22,056 | False | 30 | 22,056 | True | CLEVELAND WRAP 5175.00 X; I DJ NOW 2699.56 X; PRINT MUSE 2481.84 X; HOLIDAY INN EXPRESS 2291.82 X; FAIRFIELD INN & SUITES 1498.47 X; BEST WESTERN PLUS 1355.92 X; MICROTEL INN 754.01 X; B&H PHOTO VIDEO 636.94 X; ARMORY SMOKEHOUSE 542.23 X; J. CREW FACTORY 453.25 X |
| card | hash | 25 | C00833608 | US BANK | CREDIT CARD PAYMENT (SEE BELOW IF ITEMIZED) | 5,411 | False | 21 | 4,876 | False | MANGO HAUS RESTAURANT 1322.50 X; HOTEL AMARANO 748.70 X; MARRIOTT HOTELS 551.68 X; MARRIOTT HOTELS 414.68 X; MARRIOTT HOTELS 408.82 X; NOVO BRAZIL BREWING 377.87 X; MARRIOTT HOTELS 324.44 X; COMCAST 227.46 X; MARRIOTT HOTELS 192.80 X; SINGH TAXI AND LIMO 84.00 X |
| reimbursement | largest | 1 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL / INSURANCE / SOFTWARE / WEB SERVICE / SUBSCRIPTION | 338,466 | False | 9 | 338,268 | False | CITATION MANAGEMENT 182066.57 X; CITATION MANAGEMENT 83561.85 X; EPIC INSURANCE MIDWEST 33525.00 X; INDY JET MANAGEMENT 14484.10 X; INDY JET SERVICES LLC 10158.97 X; INDY JET SERVICES LLC 6715.10 X; GOGO BUSINESS AVIATION LLC 3876.51 X; AIRCRAFT PERFORMANCE GROUP LLC 3693.00 X; AIRCRAFT PERFORMANCE GROUP LLC 187.00 X |
| reimbursement | largest | 2 | C00661264 | CTC FOR PROGRESS | REIMBURSEMENT OF OPERATIONAL EXPENSES | 232,553 | False | 25 | 220,478 | False | COMMUNITY LABOR ADMINISTRATIVE SERVICES 45126.36 X; COMMUNITY LABOR ADMINISTRATIVE SERVICES 42750.62 X; COMMUNITY LABOR ADMINISTRATIVE SERVICES 37339.03 X; COMMUNITY LABOR ADMINISTRATIVE SERVICES 30120.08 X; HERTZ 10511.35 X; CAMPUS COPY CENTER 4934.45 X; A CHILDS DREAM TOO, INC. 4500.00 X; MACHO'S DELISH MIX 3588.39 X; PARTY ON EVENT RENTAL 3560.00 X; A CHILDS DREAM TOO, INC. 3300.00 X |
| reimbursement | largest | 3 | C00837567 | GROSS, KEITH | REIMBURSEMENT (SEE BELOW) | 180,967 | False | 126 | 177,938 | False | MAMMOTH STRATEGY GROUP 92988.00 X; MAMMOTH STRATEGY GROUP 7950.00 X; MIGHTY GRAPHICS 5813.13 X; WIN AMERICA 5558.44 X; PROGRESSIVE INSURANCE 3897.00 X; MURPHY RV 3893.14 X; PROGRESSIVE INSURANCE 3097.00 X; TRAIL MAPPER INC 3000.00 X; TRAIL MAPPER INC 3000.00 X; PRESS HALL 2766.07 X |
| reimbursement | largest | 4 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL / FOOD / BEVERAGE | 170,888 | False | 2 | 170,888 | True | CITATION MANAGEMENT 156399.58 X; INDY JET MANAGEMENT 14488.68 X |
| reimbursement | largest | 5 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL | 167,598 | False | 1 | 167,598 | True | CITATION MANAGEMENT 167597.50 X |
| reimbursement | largest | 6 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL | 157,712 | False | 1 | 157,712 | True | CITATION MANAGEMENT 157712.50 X |
| reimbursement | largest | 7 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL | 151,006 | False | 1 | 151,006 | True | CITATION MANAGEMENT 151006.25 X |
| reimbursement | largest | 8 | C00002840 | INTERNATIONAL UNION, UAW | REIMBURSEMENT FOR VCAP EXPENSES PAID FROM INTERNATIONAL ACCOUNT IN ERROR | 128,610 | False | 3 | 128,610 | True | ESTWO PROMOTIONS INC 113713.41 X; ESTWO PROMOTIONS INC 11964.45 X; IN STOCK MARKETING SERVICES, LLC 2932.50 X |
| reimbursement | largest | 9 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL | 112,484 | False | 3 | 112,484 | True | INDY JET MANAGEMENT 110400.00 X; AMERICAN AIRLINES 1606.00 X; DELTA AIRLINES 478.20 X |
| reimbursement | largest | 10 | C00802488 | O'ROURKE, JOHN (JR) RYAN | SEE MEMO ITEMS | 107,841 | False | 87 | 106,197 | False | WHEELS UP 29190.82 X; WHEELS UP 22281.75 X; ONE AIR JET 17549.44 X; WHEELS UP 16035.36 X; WESTFIELDS MARRIOTT 9526.21 X; WHEELS UP 5838.16 X; WHEELS UP 5838.16 X; WHEELS UP 5838.16 X; WHEELS UP 5838.16 X; WHEELS UP 5838.16 X |
| reimbursement | largest | 11 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL | 86,400 | False | 1 | 86,400 | True | DORADO AIRCRAFT LEASING 86400.00 X |
| reimbursement | largest | 12 | C00616268 | THE KAM CO. | FUNDRAISING REIMBURSEMENTS -- SEE MEMO ITEMS | 83,898 | False | 9 | 83,134 | False | BROADMOOR HOTEL 79485.07 X; NATIONAL RENTAL CAR 1321.61 X; COURTYARD BY MARRIOTT 789.04 X; JOTFORM INC. 468.00 X; SOUTHWEST AIRLINES 411.96 X; OFFICE DEPOT 348.38 X; COCOA DOLCE CHOCOLATES 203.13 X; AMAZON 72.50 X; USPS 34.60 X |
| reimbursement | largest | 13 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL | 82,156 | False | 1 | 82,156 | True | CITATION MANAGEMENT 82156.25 X |
| reimbursement | largest | 14 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL | 81,854 | False | 1 | 81,854 | True | V LEASING 81853.75 X |
| reimbursement | largest | 15 | C00744946 | HUNT-SCOTT, SHANNON | CATERING, FOOD & BEVERAGES | 79,304 | False | 3 | 79,304 | True | HENSLEY EVENT RESOURCES 41557.12 X; HANDHELD CATERING 33927.59 X; BRIGHT PARTY RENTALS 3819.10 X |
| reimbursement | largest | 16 | C00852343 | MOORE, NICK | TRAVEL/EVENT/OFFICE SUPPLIES EXPENSE REIMBURSEMENT: SEE ITEMIZATIONS IF REQUIRED | 76,989 | False | 119 | 76,008 | False | VOLANTI SCOTTSDALE HANGAR EVENTS 17309.45 X; VOLANTI SCOTTSDALE HANGAR EVENTS 10052.27 X; AIRPARK PROPERTY 7500.00 X; BW CREATIVE AGENCY 4120.00 X; PRETTY POWDER ROOMS 3634.39 X; VRBO 1800.25 X; BOB'S BARRICADES 1498.68 X; RED ROCK CASINO RESORT AND SPA 1458.85 X; RED ROCK CASINO RESORT AND SPA 1298.37 X; THE BLS COMPANY 1188.51 X |
| reimbursement | largest | 17 | C00855551 | PALMER, JASON | CANDIDATE EXPENSE REIMBURSEMENT | 75,335 | False | 8 | 75,335 | True | PALMER, JASON 40917.34 X; PALMER, JASON 16041.17 X; PALMER, JASON 9414.62 X; PALMER, JASON 4023.25 X; PALMER, JASON 2546.60 X; PALMER, JASON 1246.95 X; PALMER, JASON 1116.58 X; PALMER, JASON 28.57 X |
| reimbursement | largest | 18 | C00438713 | KAINE FOR VIRGINIA | REIMBURSEMENT FOR INCORRECTLY PAID EXPENSE | 75,054 | False | 1 | 75,054 | True | ASSEMBLE THE AGENCY, LLC 75054.00 X |
| reimbursement | largest | 19 | C00856120 | MOORE, NICK | EXPENSE REIMBURSEMENT: SEE ITEMIZATIONS IF REQUIRED | 71,527 | False | 147 | 70,138 | False | TRUMP NATIONAL GOLF CLUB BEDMINSTER 11819.78 X; CAMPAIGN NUCLEUS LLC 3936.00 X; TRUMP NATIONAL GOLF CLUB BEDMINSTER 2836.74 X; HERTZ CAR RENTAL 2703.02 X; CARPENTER, CARSON 1750.00 X; CARPENTER, CARSON 1750.00 X; HILTON 1674.40 X; HILTON 1674.40 X; COSTCO 1628.97 X; CAMPAIGN NUCLEUS LLC 1280.00 X |
| reimbursement | largest | 20 | C00744946 | ANDERSON, LISA | FUNDRAISING EVENT PRODUCTION & SITE RENTALS | 71,240 | False | 5 | 71,240 | True | HARRYS GOOD TIMES 37090.28 X; CORT PARTY RENTAL 20807.10 X; LIGHTSMITHS, LLC 11658.71 X; FLEURISH 893.83 X; LIGHTSMITHS, LLC 789.75 X |
| reimbursement | largest | 21 | C00744946 | GILL, TIMOTHY | FUNDRAISING EVENT PRODUCTION & EQUIPMENT RENTAL | 69,340 | False | 4 | 69,340 | True | FASTLANE PRODUCTIONS 20399.67 X; JAY'S VALET 17187.50 X; EPICUREAN CATERING, LLC 16958.36 X; EVENT RENTS 14794.41 X |
| reimbursement | largest | 22 | C00833913 | RAMASWAMY, VIVEK | IN-KIND OFFSET: TRAVEL | 68,688 | False | 1 | 68,688 | True | CITATION MANAGEMENT 68687.50 X |
| reimbursement | largest | 23 | C00607838 | THE ELEVATED GROUP LLC | EXPENSE REIMBURSEMENT: SEE BELOW | 68,599 | False | 2 | 68,599 | True | SEA ISLAND CATERING 38940.16 X; SEA ISLAND RESORT 29658.44 X |
| reimbursement | largest | 24 | C00571182 | FULKERSON KENNEDY & COMPANY, LLC | EVENT & CATERING REIMBURSEMENT | 65,149 | False | 2 | 65,149 | True | FULKERSON KENNEDY & COMPANY, LLC 51593.57 X; FULKERSON KENNEDY & COMPANY, LLC 13555.39 X |
| reimbursement | largest | 25 | C00833590 | FRAHS, JESSICA | GENERIC CMTE. EVENTS/MEETINGS | 61,700 | False | 12 | 61,700 | True | THE WESTIN SEATTLE 41164.67 X; NW STAGE, EVENT PRODUCTION 8793.34 X; NW STAGE, EVENT PRODUCTION 8793.33 X; NW STAGE, EVENT PRODUCTION 1425.00 X; THE WESTIN SEATTLE 600.13 X; CACTUS MADISON PARK 396.18 X; BOUAVONH KEOPANYA 172.72 X; OFFICE DEPOT 161.89 X; OFFICE DEPOT 93.92 X; CACTUS MADISON PARK 66.54 X |
| reimbursement | hash | 1 | C00773911 | ROSHAN, NILA | CAMPAIGN EVENT SUPPLIES REIMBURSEMENT | 27 | False | 1 | 27 | True | CVS 27.18 X |
| reimbursement | hash | 2 | C00839944 | KOTA, SHIVA | PRINT DOOR HANGERS | 529 | False | 1 | 529 | True | ARTA PRINT & PROMOTIONS 529.39 X |
| reimbursement | hash | 3 | C00552539 | LIRTZMAN-SIVKIN, JESSE | REIMBURSEMENT - SEE BELOW | 581 | False | 1 | 581 | True | CAPITAL ONE ARENA 581.46 X |
| reimbursement | hash | 4 | C00763649 | ANGERHOLZER BROZ CONSULTING LLC | REIMBURSABLE EXPENSES | 358 | False | 11 | 358 | True | FEDEX 105.13 X; INTUIT 66.78 X; FEDEX 48.79 X; FEDEX 32.38 X; UBER 29.95 X; BLUEJACKET BREWERY 25.00 X; UBER 17.95 X; UBER 15.95 X; FEDEX 9.20 X; UBER 4.03 X |
| reimbursement | hash | 5 | C00326801 | SCHNEIDER, CATHERINE GREER | TRAVEL - MILEAGE, MEALS | 572 | False | 4 | 572 | True | CAFE ZUPAS 225.67 X; SCHNEIDER, CATHERINE GREER 188.50 X; PANERA BREAD 135.67 X; CAFE ZUPAS 22.15 X |
| reimbursement | hash | 6 | C00259481 | THURBER, SAMANTHA | REIMBURSEMENT - SEE MEMO ENTRIES (IF ITEMIZED) | 466 | False | 14 | 466 | True | UBER 90.25 X; UBER 87.16 X; ASADERO DOUBLE TREE PARADISE VALLEY RESORT 60.05 X; ASADERO DOUBLE TREE PARADISE VALLEY RESORT 54.39 X; WAYMO 46.98 X; DELTA AIRLINES INC. 35.00 X; ASADERO DOUBLE TREE PARADISE VALLEY RESORT 23.58 X; STARBUCKS - CORPORATE 18.24 X; LYFT 11.65 X; HILTON HOTELS - CORPORATE 10.06 X |
| reimbursement | hash | 7 | C00614214 | ROSSWAY, RITA | SEE MEMO ENTRY | 66 | False | 1 | 66 | True | GORDON FOOD SERVICE STORE 66.25 X |
| reimbursement | hash | 8 | C00539601 | KAUFFMAN, KIMBERLY | REIMBURSEMENT - CATERING | 1,436 | False | 1 | 1,436 | True | BISTRO CACAO 1436.00 X |
| reimbursement | hash | 9 | C00633982 | ROUDA, HARLEY | TRAVEL, MEALS, OFFICE SUPPLIES, SOFTWARE SUBSCRIPTION REIMBURSEMENT - SEE BELOW IF ITEMIZED | 541 | False | 2 | 74 | False | AMERICAN AIRLINES 49.95 X; GOOGLE 24.00 X |
| reimbursement | hash | 10 | C00008227 | DEMMING, JEANETTE | PARTY REIMBURSEMENTS: SEE MEMO ITEMS | 310 | False | 1 | 122 | False | DEMMING, JEANETTE 121.94 X |
| reimbursement | hash | 11 | C00828541 | KERR, JAMES | TRAVEL REIMBURSEMENT: SEE ITEMIZATION(S) IF REQUIRED | 2,002 | False | 5 | 2,002 | True | KERR, JAMES 1875.00 X; GET GO 38.33 X; LYFT 32.99 X; WALMART 28.58 X; UBER 26.92 X |
| reimbursement | hash | 12 | C00654723 | ARBIE, JOSEPH | EXPENSE REIMBURSEMENT | 225 | False | 1 | 225 | True | UBER 224.52 X |
| reimbursement | hash | 13 | C00834424 | MICHAELS, LORIE | REIMB. - SHIPPING, FACILITY RENTAL, PRINTING | 4,192 | False | 2 | 4,101 | False | GLOO FACTORY INK 3900.98 X; GALLIVANT GLOBAL EATERY 200.00 X |
| reimbursement | hash | 14 | C00832816 | COMER, MARY B | FUNDRAISING CONSULTING, EVENT ENTERNTAINMENT, TABLECLOTHS, DECORATIONS, FOOD/BEVERAGE, PHONE SERVICE | 11,209 | False | 3 | 2,054 | False | OUTLAW BLUE GRASS BAND 1200.00 X; DEWEY'S BAKERY 636.76 X; WALMART 216.95 X |
| reimbursement | hash | 15 | C00766519 | TUNNELL, KEZIA | REIMBURSEMENT | 2,311 | False | 1 | 2,311 | True | FEDEX OFFICE 2311.15 X |
| reimbursement | hash | 16 | C00833913 | AARON, STEPHEN | TRAVEL / FOOD / BEVERAGE | 3,936 | False | 8 | 3,895 | False | AMERICAN AIRLINES 1373.69 X; DELTA AIRLINES 1126.20 X; UBER 377.35 X; MARRIOTT 317.10 X; SOUTHWEST AIRLINES 294.98 X; WESTIN 222.08 X; THE TRADE MILWAUKEE 144.84 X; LYFT 38.49 X |
| reimbursement | hash | 17 | C00399071 | NATHANS, ELI | REIMBURSE: COFFEE AND SNACKS AT MONTHLY GENERAL MEMBERSHIP MEETINGS | 130 | False | 1 | 116 | False | BUSCH'S 116.29 X |
| reimbursement | hash | 18 | C00000935 | GREEN, LIBERTIE | TELEPHONES | 50 | False | 1 | 50 | True | T-MOBILE 50.00 X |
| reimbursement | hash | 19 | C00000935 | ERICSON, ELIZABETH | TELEPHONES | 75 | False | 1 | 75 | True | CRICKET WIRELESS 75.00 X |
| reimbursement | hash | 20 | C00000935 | SISTO, SARAH | TRAVEL | 72 | False | 1 | 72 | True | WASHINGTON METROPOLITAN AREA 72.00 X |
| reimbursement | hash | 21 | C00431056 | LEISURE, ERIC | MILEAGE & TRAVEL REIMBURSEMENT - SEE BELOW IF ITEMIZED | 419 | False | 2 | 14 | False | DUNKIN BRANDS GROUP INC. 7.93 X; WAWA 5.98 X |
| reimbursement | hash | 22 | C00550970 | ROLLA GROUP, LLC | REIMBURSEMENT (VENDORS THAT AGGREGATE OVER $200 LISTED BELOW) | 9,312 | False | 5 | 9,312 | True | LA CONCHA RENAISSANCE 5000.00 X; NEW YORK MARRIOTT MARQUIS 2834.67 X; DELTA AIR LINES 659.48 X; JETBLUE AIRWAYS 622.70 X; NEW YORK MARRIOTT MARQUIS 195.00 X |
| reimbursement | hash | 23 | C00376939 | KIDWELL, GREY | TRAVEL REIMBURSEMENT | 467 | False | 4 | 399 | False | UBER TECHNOLOGIES 199.71 X; UBER TECHNOLOGIES 127.10 X; UBER TECHNOLOGIES 61.40 X; UBER TECHNOLOGIES 10.91 X |
| reimbursement | hash | 24 | C00703975 | SHAH, AISHA | TRAVEL | 103 | False | 1 | 103 | True | UBER 103.26 X |
| reimbursement | hash | 25 | C00042366 | WILLIAMS, JANUARY | TRAVEL EXPENSES | 157 | False | 3 | 157 | True | AMTRAK 91.00 X; UNION STATION PARKING 50.00 X; UBER TECHNOLOGIES, INC., JANIE 15.98 X |

**Q3j. The decision: §1.1's bar, and the dollars on each side  (0 s)**

| parent_dollars | full_parent_dollars | full_share | counted_at_children | counted_at_parents | card_dollars_kept_by_issuer | child_dollars_reaching_no_payee |
|---|---|---|---|---|---|---|
| 524,208,828 | 250,483,113 | 47.78% | 250,483,072 | 273,725,715 | 192,903,671 | 252,546,537 |

**Q3k. The bar at other tolerances (not adopted: §1.1 pins $1.00)  (0 s)**

| tolerance | share_of_parent_dollars | parents |
|---|---|---|
| $1.00 | 47.78% | 55,720 |
| 1% of the parent | 68.00% | 58,033 |
| 5% of the parent | 82.51% | 64,052 |

**Q3l. R1, R2c and R2, every row  (0 s)**

| r1 | r2c | r2 | r1_not_r2 | r2_not_r1 | r1_rows | r2_rows |
|---|---|---|---|---|---|---|
| 9,730,497,943 | 9,730,633,180 | 9,730,632,212 | 30,164 | 164,432 | 1,551,168 | 1,551,099 |

**Q3m. Where R2 and R1 part  (0 s)**

| role | memo | r1 | r2 | rows | dollars |
|---|---|---|---|---|---|
| partial parent | True | False | True | 17 | 147,702 |
| child of partial | False | True | False | 86 | 17,676 |
| full parent | True | False | True | 13 | 16,730 |
| child of full | False | True | False | 12 | 8,773 |
| chain | False | True | False | 1 | 3,714 |

**Q3n. Orphan children: is their parent on another filing of the committee? (spec §3)  (0 s)**

| a_payment_elsewhere_has_that_tran_id | orphans |
|---|---|
| False | 7,284 |

The structure is what FEC's description says: a parent is an ordinary row (99.95% are not memo
rows) and its children are memo lines (99.99%), on the same filing. The 2×2 (Q3d) puts 89
children ($17,568) under 53 non-memo parents. Both sides are not memo rows, so R1 counts them
twice. Most are card bills whose last charge was filed without its memo code. 30 parents
($164,432) are memo rows themselves (Q3m). Chains are 8 rows ($10,804), two deeper than two levels. The rule reads a
chain's middle row as a child, so under R2 none of it counts. Spec §3's assertion that a sub-item's
parent is on its filing holds: no orphan child names a payment's `TRAN_ID` on another filing of its
committee (Q3n), and 5,552 of the 7,284 orphans name a receipt instead (Q7c).

Card bills are the parents that do not add up: 28.27% of card parents' dollars are fully itemized,
against 71.25% of other parents' (payroll processors, 97–98%) and 55.93% of reimbursements'. A card
statement's charges seldom equal the bill to the cent: 2,330 parents ($106.0M) are within 1% but
not within $1. At a 1% tolerance the share would be 68.00% (Q3k). §1.1 pins $1.00, so Q3k decides
nothing.

**Decision (§1.1's bar applied):** fully itemized parents hold $250,483,113 of $524,208,828, which
is 47.78%, under 50%. **The rule is parent always.** A parent counts, whatever its memo code. A
child of a parent in the file never counts. A child whose parent is not in the file, and every
other row, counts when it is not a memo row. Dollars on each side: $273,725,715 counted at parents
that are not fully itemized, and $250,483,113 counted at fully itemized parents, which R2c would
have counted at their children ($250,483,072). Card issuers keep $192,903,671 of card bills that are
not fully itemized. $252,546,537 of children's dollars reach no payee because their parent is not
fully itemized, and under R2 the $250.48M of fully itemized children reach none either. R2 counts
$9,730,632,212 of 2024, against R1's $9,730,497,943 (Q3l).

The contract's "`MEMO_CD = 'X'` rows are not counted" needs one exception under R2: a parent filed
as a memo row counts (30 rows, $164,432, Q3m). That is the only place R2 and R1 part by more than
$20,000.

## Q4: paper filings (2024)

```python
show("Q4a. Paper rows in 2024 (no TRAN_ID), by filer group and form", """
SELECT filer, FORM_TP_CD, count(*) AS rows, sum(amt) AS dollars FROM ox WHERE tran IS NULL GROUP BY ALL""")
show("Q4b. Paper rows in 2024: any row a sub-item could be on, by MEMO_TEXT pattern", """
SELECT count(*) FILTER (WHERE tran IS NULL AND memo) AS paper_memo_rows,
    count(*) FILTER (WHERE tran IS NULL AND back IS NOT NULL) AS paper_rows_with_back_ref,
    count(*) FILTER (WHERE coalesce(fnum, 0) <= 0) AS rows_with_no_file_num FROM ox""")
show("Q4c. Every cycle: rows with no TRAN_ID, and rows with FILE_NUM 0 or blank (from Q2)", f"""
SELECT cycle, rows, paper_n AS rows_without_tran_id, not_electronic_n AS rows_file_num_0_or_blank
FROM read_parquet({literal(work / 'profile.parquet')}) ORDER BY cycle""")
```

**Q4a. Paper rows in 2024 (no TRAN_ID), by filer group and form  (0 s)**

| filer | FORM_TP_CD | rows | dollars |
|---|---|---|---|

**Q4b. Paper rows in 2024: any row a sub-item could be on, by MEMO_TEXT pattern  (0 s)**

| paper_memo_rows | paper_rows_with_back_ref | rows_with_no_file_num |
|---|---|---|
| 0 | 0 | 0 |

**Q4c. Every cycle: rows with no TRAN_ID, and rows with FILE_NUM 0 or blank (from Q2)  (0 s)**

| cycle | rows | rows_without_tran_id | rows_file_num_0_or_blank |
|---|---|---|---|
| 2,004 | 953,645 | 0 | 0 |
| 2,006 | 1,104,456 | 0 | 462 |
| 2,008 | 1,637,960 | 0 | 0 |
| 2,010 | 1,338,036 | 0 | 0 |
| 2,012 | 1,654,328 | 0 | 0 |
| 2,014 | 1,351,066 | 4 | 0 |
| 2,016 | 1,743,435 | 0 | 0 |
| 2,018 | 1,799,908 | 0 | 0 |
| 2,020 | 2,309,716 | 0 | 0 |
| 2,022 | 1,944,035 | 0 | 0 |
| 2,024 | 2,246,968 | 0 | 0 |
| 2,026 | 1,790,165 | 0 | 0 |

The 2024 file has no paper row. No cycle has more than 4 rows without a `TRAN_ID` (2014's four),
and only 2006 has rows with `FILE_NUM` 0 or blank: 462, each with a `TRAN_ID` (Q4c). FEC's description
says paper filers are in the file from October 2005, and Senate campaigns filed on paper until
2019. Their operating expenditures are not in it. **Rule:** a row without a `TRAN_ID` counts when it
is not a memo row, and its sub-items are never promoted. It is stated for completeness. No cycle
gives it more than 4 rows to apply to.

## Q5: repeated rows (2024)

```python
show("Q5a. Repeated rows: what register_bulk's rule drops", """
SELECT count(*) FILTER (WHERE is_repeat) AS repeat_rows, sum(amt) FILTER (WHERE is_repeat) AS repeat_dollars,
    sum(amt) FILTER (WHERE is_repeat AND NOT memo) AS repeat_dollars_r1,
    count(DISTINCT (CMTE_ID, fnum)) FILTER (WHERE is_repeat) AS filings,
    count(DISTINCT CMTE_ID) FILTER (WHERE is_repeat) AS committees
FROM oxp""")
show("Q5b. The ten filings with the most repeated dollars", """
WITH f AS (
    SELECT CMTE_ID, fnum, any_value(filer) AS filer, count(*) AS rows, sum(amt) AS dollars,
        count(*) FILTER (WHERE is_repeat) AS repeat_rows, sum(amt) FILTER (WHERE is_repeat) AS repeat_dollars
    FROM oxp GROUP BY ALL)
SELECT f.*, c.CMTE_NM FROM f LEFT JOIN (SELECT DISTINCT CMTE_ID, CMTE_NM FROM cm) AS c USING (CMTE_ID)
WHERE repeat_rows > 0 ORDER BY repeat_dollars DESC LIMIT 10""")
show("Q5c. Copies per repeated transaction", """
WITH t AS (SELECT CMTE_ID, fnum, tran, count(*) AS copies FROM oxp
           WHERE (CMTE_ID, fnum, tran) IN (SELECT (CMTE_ID, fnum, tran) FROM oxp WHERE is_repeat)
           GROUP BY ALL)
SELECT copies, count(*) AS transactions FROM t GROUP BY ALL ORDER BY ALL""")
show("Q5d. TRAN_IDs on more than one row of a filing whose rows differ (all read)", """
SELECT count(*) AS tran_ids, sum(n) AS rows, sum(d) AS dollars FROM (
    SELECT CMTE_ID, fnum, tran, count(*) AS n, sum(amt) AS d FROM ox
    WHERE tran IS NOT NULL GROUP BY ALL HAVING count(*) > 1)""")
# The raw filings of the four largest (Q5b), as NEU-2401 checked indiv's: rows filed on oppexp's lines.
for file_num in (1764677, 1764419, 1765783, 1764264):
    url = f"https://docquery.fec.gov/dcdev/posted/{file_num}.fec"
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT})) as response:
        lines = response.read().decode("latin-1").split("\n")  # splitlines would cut at \x1c
    sb = [line for line in lines if line.startswith(("SB17\x1c", "SB21B\x1c", "SB23\x1c"))]
    ids = {line.split("\x1c")[2] for line in sb}  # form, filer id, TRAN_ID, ...
    print(f"{url}: {len(sb):,} rows on lines 17, 21B and 23, {len(ids):,} distinct TRAN_IDs; oppexp holds",
          con.execute(f"SELECT count(*), count(*) FILTER (WHERE NOT is_repeat) FROM oxp WHERE fnum = {file_num}").fetchone())
```

**Q5a. Repeated rows: what register_bulk's rule drops  (0 s)**

| repeat_rows | repeat_dollars | repeat_dollars_r1 | filings | committees |
|---|---|---|---|---|
| 2,943 | 3,238,816 | 2,938,001 | 11 | 8 |

**Q5b. The ten filings with the most repeated dollars  (0 s)**

| CMTE_ID | fnum | filer | rows | dollars | repeat_rows | repeat_dollars | CMTE_NM |
|---|---|---|---|---|---|---|---|
| C00834424 | 1,764,677 | candidate | 1,936 | 2,298,295 | 968 | 1,149,147 | MARIANNE WILLIAMSON FOR PRESIDENT |
| C00660795 | 1,764,419 | candidate | 910 | 1,274,471 | 455 | 637,235 | DAN CRENSHAW FOR CONGRESS |
| C00834424 | 1,765,783 | candidate | 884 | 1,267,359 | 442 | 633,679 | MARIANNE WILLIAMSON FOR PRESIDENT |
| C00640300 | 1,764,264 | super PAC | 1,046 | 578,417 | 523 | 289,208 | ACTIVATE AMERICA |
| C00773820 | 1,780,265 | candidate | 290 | 478,542 | 145 | 239,271 | ENGEL FOR ARIZONA |
| C00532465 | 1,753,309 | candidate | 186 | 171,452 | 93 | 85,726 | ROUNDS FOR SENATE |
| C00532465 | 1,753,352 | candidate | 204 | 135,171 | 102 | 67,585 | ROUNDS FOR SENATE |
| C00532465 | 1,753,303 | candidate | 166 | 119,682 | 83 | 59,841 | ROUNDS FOR SENATE |
| C00216614 | 1,810,736 | party | 256 | 97,028 | 128 | 48,514 | DEMOCRATIC PARTY COMMITTEE ABROAD |
| C00348540 | 1,777,595 | other | 2 | 34,216 | 1 | 17,108 | 1199 SEIU UNITED HEALTHCARE WORKERS EAST FEDERAL POLITICAL ACTION FUND |

**Q5c. Copies per repeated transaction  (0 s)**

| copies | transactions |
|---|---|
| 2 | 2,943 |

**Q5d. TRAN_IDs on more than one row of a filing whose rows differ (all read)  (0 s)**

| tran_ids | rows | dollars |
|---|---|---|
| 0 |  |  |
```text
https://docquery.fec.gov/dcdev/posted/1764677.fec: 968 rows on lines 17, 21B and 23, 968 distinct TRAN_IDs; oppexp holds (1936, 968)
https://docquery.fec.gov/dcdev/posted/1764419.fec: 455 rows on lines 17, 21B and 23, 455 distinct TRAN_IDs; oppexp holds (910, 455)
https://docquery.fec.gov/dcdev/posted/1765783.fec: 445 rows on lines 17, 21B and 23, 445 distinct TRAN_IDs; oppexp holds (884, 442)
https://docquery.fec.gov/dcdev/posted/1764264.fec: 523 rows on lines 17, 21B and 23, 523 distinct TRAN_IDs; oppexp holds (1046, 523)
```

Every repeated transaction is on exactly two rows, the same in every column but `SUB_ID`, and
whole filings are doubled: Marianne Williamson's filings 1764677 and 1765783 (the filings `indiv`
also doubles, NEU-2401), Dan Crenshaw's 1764419 and Activate America's 1764264, the four largest.
Each raw filing holds each `TRAN_ID` once. 1765783's raw file has 445 rows on these lines to
`oppexp`'s 442 distinct, so three of its rows are not in the file at all, so **v1's rule is right for this file**: a repeated payment row is one payment, as a
repeated gift row is one gift. No `TRAN_ID` has two rows that differ (Q5d). `register_bulk` will drop
the 2,943 rows ($3,238,816) once NEU-2151 catalogues the file, since `oppexp` has all four
`TRANSACTION_KEY` columns.

## Q6: amendments (2024)

```python
r2_parquet = literal(work / "r2.parquet")
con.execute(f"CREATE TABLE r2 AS SELECT * FROM read_parquet({r2_parquet})")

show("Q6a. TRAN_IDs at one committee under more than one FILE_NUM", """
WITH t AS (
    SELECT CMTE_ID, tran, count(DISTINCT fnum) AS filings, count(*) AS rows, sum(amt) AS dollars,
        count(DISTINCT (upper(NAME), amt, dt)) = 1 AS same_payee_amount_date
    FROM ox WHERE tran IS NOT NULL GROUP BY ALL HAVING count(DISTINCT fnum) > 1)
SELECT same_payee_amount_date, count(*) AS tran_ids, sum(rows) AS rows, sum(dollars) AS dollars,
    count(DISTINCT CMTE_ID) AS committees
FROM t GROUP BY ALL ORDER BY ALL""")
show("Q6a2. Of those agreeing: is a later-numbered filing an amendment (AMNDT_IND 'A')?", """
WITH t AS (
    SELECT CMTE_ID, tran FROM ox WHERE tran IS NOT NULL GROUP BY ALL
    HAVING count(DISTINCT fnum) > 1 AND count(DISTINCT (upper(NAME), amt, dt)) = 1),
r AS (SELECT o.CMTE_ID, o.tran, o.fnum, o.AMNDT_IND, o.RPT_TP, o.amt,
             o.fnum = max(o.fnum) OVER (PARTITION BY o.CMTE_ID, o.tran) AS latest
      FROM ox AS o JOIN t USING (CMTE_ID, tran))
SELECT latest, AMNDT_IND, count(*) AS rows, sum(amt) AS dollars FROM r GROUP BY ALL ORDER BY ALL""")

# (b) v1's rule applied to payments (spec §4.2 Q6): a payment is the hash of committee, name key,
# ZIP5, amount, date and purpose on a dated non-memo electronic row; a filing is superseded when a
# later-numbered amendment at the same committee repeats at least half of its payments.
con.execute("""
CREATE TEMP TABLE filed_payment AS
SELECT CMTE_ID, fnum AS FILE_NUM, AMNDT_IND,
    hash(CMTE_ID, regexp_replace(upper(coalesce(NAME, '')), '[^A-Z0-9]', '', 'g'), left(ZIP_CODE, 5),
         amt, dt, purp) AS gift
FROM ox WHERE NOT memo AND dt IS NOT NULL AND fnum > 0""")
con.execute("""
CREATE TEMP TABLE repeated_payment AS
SELECT gift FROM filed_payment GROUP BY gift HAVING min(FILE_NUM) <> max(FILE_NUM)""")
con.execute("""
CREATE TEMP TABLE filing_payment AS
SELECT f.CMTE_ID, f.FILE_NUM, bool_or(f.AMNDT_IND = 'A') AS is_amendment, r.gift, count(*) AS rows
FROM filed_payment AS f LEFT JOIN repeated_payment AS r ON r.gift = f.gift
GROUP BY f.CMTE_ID, f.FILE_NUM, r.gift""")
con.execute("""
CREATE TABLE superseded_pair AS
WITH filing AS (
    SELECT CMTE_ID, FILE_NUM, bool_or(is_amendment) AS is_amendment, sum(rows) AS rows
    FROM filing_payment GROUP BY CMTE_ID, FILE_NUM)
SELECT earlier.FILE_NUM, later.FILE_NUM AS by_file_num
FROM filing_payment AS earlier
JOIN filing_payment AS later
    ON later.CMTE_ID = earlier.CMTE_ID AND later.gift = earlier.gift AND later.FILE_NUM > earlier.FILE_NUM
JOIN filing AS amendment ON amendment.FILE_NUM = later.FILE_NUM AND amendment.is_amendment
JOIN filing AS original ON original.FILE_NUM = earlier.FILE_NUM
GROUP BY earlier.FILE_NUM, later.FILE_NUM, original.rows
HAVING sum(earlier.rows) * 2 >= original.rows""")
con.execute("CREATE TABLE superseded_b AS SELECT DISTINCT FILE_NUM FROM superseded_pair")

# (c) The receipt side's set: 04_contribution.sql's three statements, read from the container's
# own copy at this SHA and run on 2024's `indiv` (repeated rows dropped, as silver reads it).
bulk("indiv")
sql = (settings.sql_dir / "silver" / "04_contribution.sql").read_text()
start = sql.index("CREATE TEMP VIEW filed_gift AS")
end = sql.index("HAVING sum(earlier.rows) * 2 >= original.rows;") + len("HAVING sum(earlier.rows) * 2 >= original.rows;")
print("\n```sql\n" + sql[start:end] + "\n```")
for statement in sql[start:end].split(";"):
    if statement.strip():
        con.execute(statement)
con.execute("CREATE TABLE superseded_c AS SELECT DISTINCT FILE_NUM FROM superseded_filing")

show("Q6b-d. Filings superseded by each set, and the oppexp rows on them", """
WITH s AS (
    SELECT coalesce(b.FILE_NUM, c.FILE_NUM) AS FILE_NUM,
        CASE WHEN b.FILE_NUM IS NOT NULL AND c.FILE_NUM IS NOT NULL THEN 'both'
             WHEN b.FILE_NUM IS NOT NULL THEN 'only (b) payments' ELSE 'only (c) receipts' END AS sets
    FROM superseded_b AS b FULL JOIN superseded_c AS c ON c.FILE_NUM = b.FILE_NUM),
o AS (SELECT o.fnum, o.amt, r2.r2 FROM ox AS o JOIN r2 USING (sid))
SELECT s.sets, count(DISTINCT s.FILE_NUM) AS filings, count(DISTINCT o.fnum) AS with_oppexp_rows,
    count(o.fnum) AS rows, sum(o.amt) AS dollars, sum(o.amt) FILTER (WHERE o.r2) AS r2_dollars
FROM s LEFT JOIN o ON o.fnum = s.FILE_NUM GROUP BY ALL ORDER BY ALL""")
show("Q6e. Filings only (b) finds: their receipts in indiv, and the amendment that repeats them (by R2 dollars)", """
WITH only_b AS (SELECT FILE_NUM FROM superseded_b EXCEPT SELECT FILE_NUM FROM superseded_c),
report AS (SELECT fnum, any_value(CMTE_ID) AS CMTE_ID, any_value(RPT_YR) AS yr, any_value(RPT_TP) AS rpt_tp,
                  any_value(AMNDT_IND) AS amndt, count(*) AS rows, sum(ox.amt) FILTER (WHERE r2.r2) AS r2_dollars
           FROM ox JOIN r2 USING (sid) GROUP BY fnum),
gifts AS (SELECT FILE_NUM, count(*) AS indiv_rows FROM indiv WHERE FILE_NUM IN (SELECT FILE_NUM FROM only_b) GROUP BY ALL)
SELECT e.CMTE_ID, e.fnum, e.yr || ' ' || e.rpt_tp || ' ' || e.amndt AS report, e.rows, e.r2_dollars,
    coalesce(gifts.indiv_rows, 0) AS indiv_rows,
    string_agg(DISTINCT l.fnum || ' (' || l.yr || ' ' || l.rpt_tp || ' ' || l.amndt || ')', ', ') AS superseded_by,
    bool_and(l.yr = e.yr AND l.rpt_tp = e.rpt_tp) AS same_report, any_value(c.CMTE_NM) AS committee
FROM only_b JOIN report AS e ON e.fnum = only_b.FILE_NUM
JOIN superseded_pair AS p ON p.FILE_NUM = e.fnum JOIN report AS l ON l.fnum = p.by_file_num
LEFT JOIN gifts ON gifts.FILE_NUM = e.fnum
LEFT JOIN (SELECT DISTINCT CMTE_ID, CMTE_NM FROM cm) AS c ON c.CMTE_ID = e.CMTE_ID
GROUP BY ALL ORDER BY e.r2_dollars DESC""")
show("Q6e2. Filings (b) finds, by whether the superseding amendment is the same report", """
WITH report AS (SELECT fnum, any_value(RPT_YR) AS yr, any_value(RPT_TP) AS rpt_tp, sum(ox.amt) FILTER (WHERE r2.r2) AS d
                FROM ox JOIN r2 USING (sid) GROUP BY fnum),
f AS (SELECT p.FILE_NUM, bool_or(l.yr = e.yr AND l.rpt_tp = e.rpt_tp) AS same_report, any_value(e.d) AS d,
             p.FILE_NUM IN (SELECT FILE_NUM FROM superseded_c) AS in_c
      FROM superseded_pair AS p JOIN report AS e ON e.fnum = p.FILE_NUM JOIN report AS l ON l.fnum = p.by_file_num
      GROUP BY p.FILE_NUM)
SELECT in_c, same_report, count(*) AS filings, sum(d) AS r2_dollars FROM f GROUP BY ALL ORDER BY ALL""")
show("Q6f. Filings only (c) finds: their spending, and why (b) does not (15 by R2 dollars)", """
WITH only_c AS (SELECT FILE_NUM FROM superseded_c EXCEPT SELECT FILE_NUM FROM superseded_b),
sp AS (SELECT o.CMTE_ID, o.fnum, any_value(o.RPT_TP) AS rpt_tp, any_value(o.AMNDT_IND) AS amndt,
              count(*) AS rows, sum(o.amt) FILTER (WHERE r2.r2) AS r2_dollars
       FROM ox AS o JOIN r2 USING (sid) WHERE o.fnum IN (SELECT FILE_NUM FROM only_c) GROUP BY ALL),
rep AS (SELECT FILE_NUM, sum(rows) FILTER (WHERE gift IS NOT NULL) AS repeated, sum(rows) AS payments
        FROM filing_payment WHERE FILE_NUM IN (SELECT FILE_NUM FROM only_c) GROUP BY ALL)
SELECT sp.*, rep.payments, rep.repeated, c.CMTE_NM
FROM sp LEFT JOIN rep ON rep.FILE_NUM = sp.fnum
LEFT JOIN (SELECT DISTINCT CMTE_ID, CMTE_NM FROM cm) AS c USING (CMTE_ID)
ORDER BY r2_dollars DESC LIMIT 15""")
con.execute(f"COPY superseded_b TO {literal(work / 'superseded_b.parquet')} (FORMAT parquet)")
con.execute(f"COPY superseded_c TO {literal(work / 'superseded_c.parquet')} (FORMAT parquet)")
```

**Q6a. TRAN_IDs at one committee under more than one FILE_NUM  (1 s)**

| same_payee_amount_date | tran_ids | rows | dollars | committees |
|---|---|---|---|---|
| False | 16,032 | 65,644 | 374,774,481 | 456 |
| True | 1,013 | 2,046 | 29,388,790 | 34 |

**Q6a2. Of those agreeing: is a later-numbered filing an amendment (AMNDT_IND 'A')?  (1 s)**

| latest | AMNDT_IND | rows | dollars |
|---|---|---|---|
| False | A | 168 | 4,443,075 |
| False | N | 856 | 10,248,283 |
| False | T | 9 | 14,076 |
| True | A | 890 | 14,584,856 |
| True | N | 121 | 97,549 |
| True | T | 2 | 950 |

```sql
CREATE TEMP VIEW filed_gift AS
SELECT
    CMTE_ID,
    FILE_NUM,
    AMNDT_IND,
    CASE
        WHEN try_strptime(TRANSACTION_DT, '%m%d%Y') IS NOT NULL THEN hash(
            CMTE_ID,
            regexp_replace(upper(coalesce(NAME, '')), '[^A-Z0-9]', '', 'g'),
            left(ZIP_CODE, 5),
            upper(EMPLOYER),
            upper(OCCUPATION),
            TRANSACTION_AMT,
            TRANSACTION_DT
        )
    END AS gift
FROM indiv
WHERE MEMO_CD IS DISTINCT FROM 'X' AND TRANSACTION_TP IS DISTINCT FROM '24T' AND FILE_NUM > 0;

CREATE TEMP TABLE repeated_gift AS
SELECT gift
FROM filed_gift
WHERE gift IS NOT NULL
GROUP BY gift
HAVING min(FILE_NUM) <> max(FILE_NUM);

-- One row per filing and repeated gift on it, and one per filing for its other rows (gift NULL).
CREATE TEMP TABLE filing_gift AS
SELECT
    filed_gift.CMTE_ID,
    filed_gift.FILE_NUM,
    bool_or(filed_gift.AMNDT_IND = 'A') AS is_amendment,
    repeated_gift.gift,
    count(*) AS rows
FROM filed_gift
LEFT JOIN repeated_gift ON repeated_gift.gift = filed_gift.gift
GROUP BY filed_gift.CMTE_ID, filed_gift.FILE_NUM, repeated_gift.gift;

CREATE TEMP TABLE superseded_filing AS
WITH filing AS (
    SELECT CMTE_ID, FILE_NUM, bool_or(is_amendment) AS is_amendment, sum(rows) AS rows
    FROM filing_gift
    GROUP BY CMTE_ID, FILE_NUM
)
SELECT DISTINCT earlier.FILE_NUM
FROM filing_gift AS earlier
JOIN filing_gift AS later
    ON later.CMTE_ID = earlier.CMTE_ID
    AND later.gift = earlier.gift
    AND later.FILE_NUM > earlier.FILE_NUM
JOIN filing AS amendment ON amendment.FILE_NUM = later.FILE_NUM AND amendment.is_amendment
JOIN filing AS original ON original.FILE_NUM = earlier.FILE_NUM
GROUP BY earlier.FILE_NUM, later.FILE_NUM, original.rows
HAVING sum(earlier.rows) * 2 >= original.rows;
```

**Q6b-d. Filings superseded by each set, and the oppexp rows on them  (0 s)**

| sets | filings | with_oppexp_rows | rows | dollars | r2_dollars |
|---|---|---|---|---|---|
| both | 20 | 20 | 590 | 7,751,324 | 7,732,069 |
| only (b) payments | 23 | 23 | 113 | 126,162 | 124,469 |
| only (c) receipts | 27 | 6 | 322 | 7,385,541 | 7,385,541 |

**Q6e. Filings only (b) finds: their receipts in indiv, and the amendment that repeats them (by R2 dollars)  (9 s)**

| CMTE_ID | fnum | report | rows | r2_dollars | indiv_rows | superseded_by | same_report | committee |
|---|---|---|---|---|---|---|---|---|
| C00696153 | 1,763,631 | 2024 30S N | 24 | 30,108 | 0 | 1774633 (2024 Q1 A) | False | JAIME HARRISON FOR US SENATE |
| C00833053 | 1,730,298 | 2023 Q3 N | 3 | 29,597 | 0 | 1735054 (2023 TER A) | False | SIGNORELLO FOR SENATE |
| C00620443 | 1,692,479 | 2023 Q1 N | 19 | 15,573 | 0 | 1696328 (2023 TER A) | False | CENTER AISLE PAC |
| C00818815 | 1,710,368 | 2023 Q2 N | 2 | 11,402 | 0 | 1717874 (2023 TER A) | False | FREEDOM PRINCIPLE MO MISSOURI FIRST PAC |
| C00746909 | 1,720,189 | 2023 TER T | 6 | 8,237 | 0 | 1720305 (2023 TER A) | True | DELIVER DEMOCRACY |
| C00741611 | 1,777,526 | 2024 Q1 N | 4 | 5,135 | 0 | 1778084 (2024 M4 A) | False | BIG SKY VALUES |
| C00874321 | 1,790,074 | 2024 12P N | 5 | 4,881 | 0 | 1822205 (2024 Q2 A) | False | STAMPER FOR CONGRESS |
| C00799288 | 1,871,624 | 2024 TER T | 1 | 4,876 | 0 | 1872298 (2024 YE A) | False | RETIRE OR LOSE |
| C00717553 | 1,724,017 | 2023 MY A | 21 | 3,336 | 42 | 1779904 (2023 MY A) | True | FEMS FOR DEMS PAC |
| C00784843 | 1,725,544 | 2023 Q3 N | 5 | 3,171 | 0 | 1725547 (2023 TER A) | False | CICELY DAVIS FOR CONGRESS |
| C00848937 | 1,773,325 | 2024 Q1 N | 2 | 1,958 | 76 | 1872580 (2024 Q1 A) | True | BAN ASSAULT WEAPONS NOW PAC |
| C00771949 | 1,806,084 | 2024 TER A | 2 | 1,612 | 0 | 1808447 (2024 TER A) | True | SABATINI FOR CONGRESS |
| C00523217 | 2,011,993 | 2023 YE A | 1 | 1,108 | 25 | 2015028 (2023 YE A) | True | MASSACHUSETTS BLUE PAC OF BLUE CROSS BLUE SHIELD OF MASSACHUSETTS |
| C00692715 | 1,772,652 | 2024 Q1 N | 2 | 1,075 | 0 | 1780940 (2024 Q1 A) | True | HELP ELECT REPUBLICANS NOW |
| C00745182 | 1,788,626 | 2024 TER T | 1 | 962 | 0 | 1792372 (2024 TER A) | True | IRANIAN AMERICANS FOR PEACE |
| C00868174 | 1,769,064 | 2024 Q1 N | 1 | 421 | 4 | 1820257 (2024 Q1 A) | True | JKLC VICTORY FUND |
| C00602698 | 1,702,446 | 2023 Q1 N | 3 | 400 | 0 | 1724463 (2023 MY A) | False | AMERICAN WOOD COUNCIL POLITICAL ACTION COMMITTEE (WOOD-PAC) |
| C00478362 | 1,878,746 | 2024 Q3 A | 2 | 339 | 0 | 1879216 (2024 Q3 A) | True | HEALTH EDUCATION AND LEARNING POLITICAL ACTION COMMITTEE (HEALPAC)-FEDERAL |
| C00377168 | 1,815,310 | 2024 Q2 A | 3 | 162 | 2 | 1877047 (2024 Q2 A) | True | FEMINIST MAJORITY PAC |
| C00803197 | 1,876,208 | 2024 Q3 A | 2 | 69 | 0 | 1877150 (2024 Q3 A) | True | SUMMIT COUNTY PROGRESSIVE DEMOCRATS FEDERAL PAC |
| C00696948 | 1,838,777 | 2024 12G N | 2 | 39 | 0 | 1849167 (2024 M11 A) | False | BERNIE 2020 |
| C00812305 | 1,795,217 | 2024 Q1 A | 1 | 6 | 0 | 1795501 (2024 Q1 A) | True | JERICO MATIAS CRUZ FOR US CONGRESS |
| C00849752 | 1,749,678 | 2023 TER T | 1 | 1 | 0 | 1753956 (2023 TER A) | True | REPRESENTATION MATTERS: VITAL VOICES IN THE HOUSE |

**Q6e2. Filings (b) finds, by whether the superseding amendment is the same report  (0 s)**

| in_c | same_report | filings | r2_dollars |
|---|---|---|---|
| False | False | 10 | 105,184 |
| False | True | 13 | 19,286 |
| True | False | 7 | 1,215,814 |
| True | True | 13 | 6,516,255 |

**Q6f. Filings only (c) finds: their spending, and why (b) does not (15 by R2 dollars)  (0 s)**

| CMTE_ID | fnum | rpt_tp | amndt | rows | r2_dollars | payments | repeated | CMTE_NM |
|---|---|---|---|---|---|---|---|---|
| C00833160 | 1,731,634 | Q3 | N | 292 | 7,144,194 | 292 | 86 | PERRY JOHNSON FOR PRESIDENT INC. |
| C00833160 | 1,753,530 | YE | N | 18 | 227,917 | 18 | 8 | PERRY JOHNSON FOR PRESIDENT INC. |
| C00848937 | 1,857,589 | 30G | N | 6 | 12,645 | 6 | 1 | BAN ASSAULT WEAPONS NOW PAC |
| C00847210 | 1,762,257 | YE | A | 2 | 295 | 2 |  | THE GREAT AMERICAN PAC |
| C00847210 | 1,762,154 | Q3 | A | 2 | 245 | 2 |  | THE GREAT AMERICAN PAC |
| C00847210 | 1,789,986 | Q3 | A | 2 | 245 | 2 |  | THE GREAT AMERICAN PAC |

(a) 17,045 `TRAN_ID`s recur under more than one `FILE_NUM` at one committee. 16,032 of them differ
in payee, amount or date: a filer's ids restarting each report, not an amendment. The 1,013 that
agree are mostly an original and its amendment, with the later filing an `A` for 890 of the 1,013
rows on the latest filing (Q6a2).

(b)–(d) The two sets: the receipt side's (`indiv`'s `superseded_filing`, the three statements above,
copied from the container's `04_contribution.sql` at this SHA) finds 47 filings, 26 of which carry
`oppexp` rows: $7,732,069 (both sets) and $7,385,541 (only the receipt side's) of R2 spending,
$15,117,610 in all. Most of that is Perry Johnson for President's Q3 and YE 2023 filings
($7.37M). The payment rule finds 43 filings, 23 of them alone. Those 23 hold $124,469 (Q6e).
Their receipts are not in `indiv` (18 of 23 have no `indiv` row), which is why the receipt side
misses them. But 10 of them, $105,184, are "superseded" by a later amendment of a *different* report
(a Q3 by a termination report, a 30S by a Q1): payments repeated across two reports, not an
amendment. The other 13 ($19,286) are the same report amended.

**Decision: the receipt side's set alone.** A filing superseded for receipts is superseded for
spending, so a superseded filing's `oppexp` rows are not counted: $15,117,610 of R2, R3 =
$9,715,514,602. Spec §4.2 lets (b) add a filing "only if the document shows filings with spending
and too few gifts for (c) to see". Q6e does show them: 13 same-report amendments (8 of them with no
`indiv` row), $19,286. That condition lets (b) in. It does not require it. The payment rule as
written would also bring the 10 wrong pairs ($105,184, 84.5% of its dollars), and a same-report
variant is a fourth rule the spec does not list, for $19,286 (0.0002% of counted spending). Not
adopted here. NEU-2150 may add it. Q11 cannot decide this: FEC's own figure counts a superseded
filing too (NEU-2196).

## Q7: overlap with `pas2`, `oth` and `indiv` (2024)

```python
con.execute(f"CREATE TABLE r2 AS SELECT * FROM read_parquet({literal(work / 'r2.parquet')})")
con.execute("""CREATE TABLE ids AS
    SELECT o.sid, o.CMTE_ID, o.fnum, o.tran, o.back, o.amt, o.FORM_TP_CD || ' ' || o.LINE_NUM AS line, r2.r2
    FROM ox AS o JOIN r2 USING (sid)""")
for name in ("indiv", "pas2", "oth"):
    bulk(name)
# By SUB_ID, against each file as published (repeats kept); oppexp is the small, right side.
con.execute("CREATE TABLE by_sub_id (file VARCHAR, sid UBIGINT, tp VARCHAR, other_cmte VARCHAR, other_amt DECIMAL(14, 2))")
for name in ("indiv", "pas2", "oth"):
    con.execute(f"""INSERT INTO by_sub_id
        SELECT '{name}', ids.sid, i.TRANSACTION_TP, i.CMTE_ID, i.TRANSACTION_AMT
        FROM {name}_published AS i JOIN ids ON ids.sid = i.SUB_ID""")
show("Q7a. oppexp rows whose SUB_ID is in pas2, oth or indiv", """
SELECT b.file, i.line, b.tp, count(*) AS rows, sum(i.amt) AS dollars, sum(i.amt) FILTER (WHERE i.r2) AS r2_dollars,
    count(*) FILTER (WHERE b.other_cmte = i.CMTE_ID AND b.other_amt = i.amt) AS same_committee_and_amount
FROM by_sub_id AS b JOIN ids AS i USING (sid) GROUP BY ALL ORDER BY dollars DESC""")
# By filing and TRAN_ID with the same amount, for rows SUB_ID did not match.
con.execute("CREATE TABLE by_tran (file VARCHAR, sid UBIGINT, tp VARCHAR)")
for name in ("indiv", "pas2", "oth"):
    con.execute(f"""INSERT INTO by_tran
        SELECT '{name}', k.sid, i.TRANSACTION_TP
        FROM {name}_published AS i
        JOIN (SELECT * FROM ids WHERE sid NOT IN (SELECT sid FROM by_sub_id)) AS k
            ON k.CMTE_ID = i.CMTE_ID AND k.fnum = i.FILE_NUM AND k.tran = i.TRAN_ID AND k.amt = i.TRANSACTION_AMT""")
show("Q7b. oppexp rows sharing committee, filing, TRAN_ID and amount with a row of pas2, oth or indiv", """
SELECT b.file, i.line, b.tp, count(*) AS rows, sum(i.amt) AS dollars, sum(i.amt) FILTER (WHERE i.r2) AS r2_dollars
FROM by_tran AS b JOIN ids AS i USING (sid) GROUP BY ALL ORDER BY dollars DESC""")
# The in-kind pairs Q3 found: a child whose BACK_REF_TRAN_ID is a receipt's TRAN_ID on its filing.
con.execute("CREATE TABLE in_kind (file VARCHAR, sid UBIGINT, tp VARCHAR, same_amount BOOLEAN)")
for name in ("indiv", "pas2", "oth"):
    con.execute(f"""INSERT INTO in_kind
        SELECT '{name}', k.sid, i.TRANSACTION_TP, k.amt = i.TRANSACTION_AMT
        FROM {name}_published AS i
        JOIN (SELECT ids.* FROM ids JOIN r2 USING (sid) WHERE r2.role = 'orphan child') AS k
            ON k.CMTE_ID = i.CMTE_ID AND k.fnum = i.FILE_NUM AND k.back = i.TRAN_ID""")
show("Q7c. Orphan children whose BACK_REF_TRAN_ID is a receipt on their filing", """
SELECT b.file, b.tp, b.same_amount, count(*) AS rows, sum(i.amt) AS dollars, sum(i.amt) FILTER (WHERE i.r2) AS r2_dollars
FROM in_kind AS b JOIN ids AS i USING (sid) GROUP BY ALL ORDER BY dollars DESC""")
show("Q7c2. Orphan children: matched to a receipt or not", """
SELECT sid IN (SELECT sid FROM in_kind) AS receipt_found, count(*) AS rows, sum(amt) AS dollars,
    sum(amt) FILTER (WHERE r2) AS r2_dollars
FROM ids JOIN r2 USING (sid, amt, r2) WHERE r2.role = 'orphan child' GROUP BY ALL""")
silver("committee_transfer")
silver("independent_expenditure")
show("Q7d. oppexp rows whose SUB_ID is a silver source_record_id", """
SELECT 'committee_transfer' AS silver_table, count(*) AS rows, sum(i.amt) AS dollars
FROM silver.committee_transfer AS t JOIN ids AS i ON i.sid = t.source_record_id
UNION ALL
SELECT 'independent_expenditure', count(*), sum(i.amt)
FROM silver.independent_expenditure AS t JOIN ids AS i ON i.sid = t.source_record_id""")
con.execute(f"""COPY (SELECT sid, 'sub_id ' || file AS why FROM by_sub_id UNION ALL SELECT sid, 'tran ' || file FROM by_tran)
    TO {literal(work / 'overlap.parquet')} (FORMAT parquet)""")
```

**Q7a. oppexp rows whose SUB_ID is in pas2, oth or indiv  (0 s)**

| file | line | tp | rows | dollars | r2_dollars | same_committee_and_amount |
|---|---|---|---|---|---|---|

**Q7b. oppexp rows sharing committee, filing, TRAN_ID and amount with a row of pas2, oth or indiv  (0 s)**

| file | line | tp | rows | dollars | r2_dollars |
|---|---|---|---|---|---|

**Q7c. Orphan children whose BACK_REF_TRAN_ID is a receipt on their filing  (0 s)**

| file | tp | same_amount | rows | dollars | r2_dollars |
|---|---|---|---|---|---|
| indiv | 15 | True | 1,593 | 8,713,962 | 8,504,080 |
| indiv | 10 | False | 333 | 2,636,610 | 2,577,796 |
| indiv | 10 | True | 182 | 1,947,446 | 1,947,446 |
| indiv | 15 | False | 1,261 | 1,382,052 | 1,277,942 |
| oth | 15Z | False | 627 | 1,016,454 | 1,016,454 |
| oth | 18G | True | 4 | 891,211 | 891,211 |
| indiv | 15C | True | 291 | 789,935 | 765,935 |
| oth | 15Z | True | 253 | 365,043 | 365,043 |
| oth | 18K | False | 85 | 360,999 | 360,999 |
| indiv | 15C | False | 722 | 330,319 | 330,319 |
| oth | 18G | False | 43 | 178,107 | 178,107 |
| indiv | 15E | True | 26 | 59,045 | 59,045 |
| oth | 24K | False | 9 | 53,728 |  |
| oth | 18K | True | 34 | 43,790 | 43,790 |
| indiv | 15E | False | 31 | 33,657 | 33,657 |
| oth | 24Z | False | 24 | 13,038 | 2,941 |
| oth | 18J | True | 1 | 9,540 |  |
| oth | 15J | False | 10 | 3,565 | 413 |
| oth | 22Z | False | 4 | 1,730 | 1,730 |
| pas2 | 24Z | False | 7 | 1,302 |  |
| oth | 41 | False | 2 | 1,000 |  |
| pas2 | 24K | False | 2 | 957 |  |
| oth | 16C | False | 1 | 927 | 927 |
| indiv | 22Y | True | 1 | 450 |  |
| indiv | 22Y | False | 12 | 439 |  |
| oth | 24Z | True | 2 | 282 |  |
| oth | 15J | True | 1 | 49 |  |

**Q7c2. Orphan children: matched to a receipt or not  (0 s)**

| receipt_found | rows | dollars | r2_dollars |
|---|---|---|---|
| False | 1,732 | 1,327,593 | 1,267,403 |
| True | 5,552 | 18,833,378 | 18,357,835 |

**Q7d. oppexp rows whose SUB_ID is a silver source_record_id  (0 s)**

| silver_table | rows | dollars |
|---|---|---|
| committee_transfer | 0 |  |
| independent_expenditure | 0 |  |

**No row overlaps.** No `oppexp` `SUB_ID` is in any of the three files as published (spec §3's
assertion that one transaction shares a `SUB_ID` across files: untested, since no transaction is in
both `oppexp` and a receipt file, so there is nothing to compare; no `SUB_ID` is shared). No row shares committee, filing, `TRAN_ID` and amount with one. None is a silver
`committee_transfer` or `independent_expenditure` row. The contributions a committee makes (Form 3X
line 23, Form 3 line 18) are not on the lines `oppexp` holds.

What does pair across files is Q3's orphan children: 5,552 of the 7,284 ($18,833,378) name by
`BACK_REF_TRAN_ID` a receipt on their own filing, mostly `indiv` 15 and 10 and `oth` 15Z and 18G.
They are the outlay side of an in-kind contribution, filed as FEC requires: the gift on Schedule A
and its use on Schedule B. Silver counts the gift as a contribution and this row as its use. That
is two different facts, as FEC's own totals count them, so it is not an overlap. Their payee is the
gift's contributor (Planned Parenthood Action Fund, the artists who gave artworks), not a business
the committee paid, which matters to payee pages (Decisions 6).

**Decision:** the overlap rule is *none needed*: $0 dropped, every counted row kept. R4 = R3.

## Q8: `CATEGORY` and purposes (2024)

Counted rows from here on are `cx.counted`: R2, less the receipt side's superseded filings (R3,
which is R4).

```python
# "Counted" from here on (§2): R2, Q3's adopted rule, less rows on a filing Q6's adopted set (the
# receipt side's, (c)) supersedes; Q7 found no overlap row to drop. The view `cx` is `ox` with
# each row's R1, R2, R3 and `counted` (R4, which is R3).
con.execute(f"CREATE TABLE r2 AS SELECT * FROM read_parquet({literal(work / 'r2.parquet')})")
con.execute(f"CREATE TABLE superseded_c AS SELECT * FROM read_parquet({literal(work / 'superseded_c.parquet')})")
con.execute("""CREATE VIEW cx AS
    SELECT o.*, r2.role, r2.r1, r2.r2c, r2.r2, r2.r2 AND o.fnum NOT IN (SELECT FILE_NUM FROM superseded_c) AS r3,
        r2.r2 AND o.fnum NOT IN (SELECT FILE_NUM FROM superseded_c) AS counted
    FROM ox AS o JOIN r2 USING (sid)""")
# FEC's CATEGORY as a code: one written without its leading zeros ('1', '01') is the code it pads to.
con.execute("""CREATE MACRO fec_code(c) AS CASE
    WHEN regexp_matches(trim(c), '^[0-9]{1,3}$') AND TRY_CAST(trim(c) AS INT) BETWEEN 1 AND 12
        THEN lpad(CAST(TRY_CAST(trim(c) AS INT) AS VARCHAR), 3, '0')
    ELSE nullif(trim(c), '') END""")
```

```python
show("Q8a. CATEGORY fill rate: overall, and by filer group", """
SELECT coalesce(filer, 'all') AS filer, count(*) FILTER (WHERE counted) AS counted_rows,
    (count(*) FILTER (WHERE counted AND nullif(trim(CATEGORY), '') IS NOT NULL) / count(*) FILTER (WHERE counted))::DOUBLE AS filled_by_rows,
    (sum(amt) FILTER (WHERE counted AND nullif(trim(CATEGORY), '') IS NOT NULL) / sum(amt) FILTER (WHERE counted))::DOUBLE AS filled_by_dollars
FROM cx GROUP BY ROLLUP (filer) ORDER BY filer NULLS FIRST""")
show("Q8b. CATEGORY fill rate by form and by report year", """
SELECT 'form' AS by, FORM_TP_CD AS value,
    (count(*) FILTER (WHERE counted AND nullif(trim(CATEGORY), '') IS NOT NULL) / count(*) FILTER (WHERE counted))::DOUBLE AS filled_by_rows,
    (sum(amt) FILTER (WHERE counted AND nullif(trim(CATEGORY), '') IS NOT NULL) / sum(amt) FILTER (WHERE counted))::DOUBLE AS filled_by_dollars
FROM cx GROUP BY ALL
UNION ALL
SELECT 'year', RPT_YR,
    (count(*) FILTER (WHERE counted AND nullif(trim(CATEGORY), '') IS NOT NULL) / count(*) FILTER (WHERE counted))::DOUBLE,
    (sum(amt) FILTER (WHERE counted AND nullif(trim(CATEGORY), '') IS NOT NULL) / sum(amt) FILTER (WHERE counted))::DOUBLE
FROM cx GROUP BY ALL ORDER BY 1, 2""")
show("Q8c. Every CATEGORY code as filed, counted rows", """
SELECT CATEGORY, string_agg(DISTINCT trim(CATEGORY_DESC), ' / ') AS category_desc, count(*) AS rows, sum(amt) AS dollars
FROM cx WHERE counted GROUP BY ALL ORDER BY CATEGORY NULLS LAST""")
show("Q8d. Purposes: distinct, blank, and the share of counted dollars the top N hold", """
WITH p AS (SELECT purp, sum(amt) AS d FROM cx WHERE counted GROUP BY ALL),
r AS (SELECT d, row_number() OVER (ORDER BY d DESC) AS n FROM p WHERE purp IS NOT NULL),
t AS (SELECT sum(d) AS total FROM p)
SELECT (SELECT count(*) FROM p WHERE purp IS NOT NULL) AS distinct_purposes,
    ((SELECT d FROM p WHERE purp IS NULL) / total)::DOUBLE AS blank_share,
    (sum(d) FILTER (WHERE n <= 50) / total)::DOUBLE AS top_50, (sum(d) FILTER (WHERE n <= 100) / total)::DOUBLE AS top_100,
    (sum(d) FILTER (WHERE n <= 200) / total)::DOUBLE AS top_200, (sum(d) FILTER (WHERE n <= 500) / total)::DOUBLE AS top_500,
    (sum(d) FILTER (WHERE n <= 1000) / total)::DOUBLE AS top_1000
FROM r, t GROUP BY total""")
con.execute("""CREATE TABLE top_purpose AS
WITH code AS (
    SELECT purp, trim(CATEGORY) AS code, count(*) AS n FROM cx
    WHERE counted AND nullif(trim(CATEGORY), '') IS NOT NULL GROUP BY ALL)
SELECT p.purp AS purpose, p.rows, p.dollars, p.dollars_category_blank,
    (SELECT code FROM code WHERE code.purp = p.purp ORDER BY n DESC, code LIMIT 1) AS fec_category
FROM (SELECT purp, count(*) AS rows, sum(amt) AS dollars,
             coalesce(sum(amt) FILTER (WHERE nullif(trim(CATEGORY), '') IS NULL), 0) AS dollars_category_blank
      FROM cx WHERE counted AND purp IS NOT NULL GROUP BY ALL ORDER BY dollars DESC LIMIT 200) AS p
ORDER BY p.dollars DESC""")
show("Q8e. The top 200 purposes by counted dollars, with each one's largest payee", """
WITH payee AS (
    SELECT purp, upper(NAME) AS payee, sum(amt) AS d,
        row_number() OVER (PARTITION BY purp ORDER BY sum(amt) DESC, upper(NAME)) AS k
    FROM cx WHERE counted AND purp IN (SELECT purpose FROM top_purpose) GROUP BY purp, upper(NAME))
SELECT row_number() OVER (ORDER BY t.dollars DESC) AS n, t.*, p.payee AS largest_payee,
    (p.d / t.dollars)::DOUBLE AS its_share
FROM top_purpose AS t JOIN payee AS p ON p.purp = t.purpose AND p.k = 1 ORDER BY t.dollars DESC""")
con.execute(f"COPY top_purpose TO {literal(work / 'top_purpose.csv')} (FORMAT csv, HEADER)")
```

**Q8a. CATEGORY fill rate: overall, and by filer group  (0 s)**

| filer | counted_rows | filled_by_rows | filled_by_dollars |
|---|---|---|---|
| all | 1,550,230 | 28.94% | 16.20% |
| candidate | 876,141 | 30.85% | 17.99% |
| not in cm | 5 | 80.00% | 100.00% |
| other | 364,863 | 27.11% | 11.18% |
| party | 213,729 | 21.47% | 8.90% |
| super PAC | 95,492 | 35.09% | 22.18% |

**Q8b. CATEGORY fill rate by form and by report year  (0 s)**

| by | value | filled_by_rows | filled_by_dollars |
|---|---|---|---|
| form | F3 | 31.66% | 23.32% |
| form | F3P | 15.09% | 9.66% |
| form | F3X | 27.14% | 13.90% |
| year | 2023 | 29.11% | 19.81% |
| year | 2024 | 28.83% | 15.19% |

**Q8c. Every CATEGORY code as filed, counted rows  (0 s)**

| CATEGORY | category_desc | rows | dollars |
|---|---|---|---|
| 001 | Administrative/Salary/Overhead Expenses | 321,708 | 860,509,348 |
| 002 | Travel Expenses | 22,624 | 23,095,503 |
| 003 | Solicitation and Fundraising Expenses | 60,969 | 221,865,197 |
| 004 | Advertising Expenses | 18,776 | 256,161,505 |
| 005 | Polling Expenses | 1,523 | 26,260,087 |
| 006 | Campaign Materials | 6,125 | 16,552,232 |
| 007 | Campaign Event Expenses | 5,581 | 10,702,729 |
| 008 | Transfers | 98 | 1,829,720 |
| 009 | Loan Repayments | 57 | 1,499,229 |
| 01 |  | 1 | 6,000 |
| 010 | Refunds of Contributions | 108 | 142,455 |
| 011 | Political Contributions | 1,648 | 4,203,109 |
| 012 | Donations | 540 | 1,987,993 |
| 02 |  | 1 | 45 |
| 1 |  | 26 | 221,994 |
| 101 |  | 7,142 | 129,547,719 |
| 102 |  | 157 | 6,721,936 |
| 103 |  | 75 | 1,391,913 |
| 104 |  | 837 | 4,774,914 |
| 105 |  | 34 | 388,617 |
| 106 |  | 13 | 164,233 |
| 107 |  | 513 | 3,393,298 |
| 2 |  | 4 | 5,083 |
| 212 |  | 1 | 26 |
| 216 |  | 13 | 2,908 |
| 21B |  | 6 | 770 |
| 3 |  | 13 | 326,184 |
| 4 |  | 8 | 1,793,093 |
| 5 |  | 1 | 68,632 |
| 6 |  | 1 | 250 |
| 7 |  | 8 | 144,690 |
|  |  | 1,101,619 | 8,141,753,187 |

**Q8d. Purposes: distinct, blank, and the share of counted dollars the top N hold  (0 s)**

| distinct_purposes | blank_share | top_50 | top_100 | top_200 | top_500 | top_1000 |
|---|---|---|---|---|---|---|
| 68,541 | 0.07% | 54.95% | 66.41% | 76.75% | 86.54% | 91.85% |

**Q8e. The top 200 purposes by counted dollars, with each one's largest payee  (0 s)**

| n | purpose | rows | dollars | dollars_category_blank | fec_category | largest_payee | its_share |
|---|---|---|---|---|---|---|---|
| 1 | MEDIA BUY | 1,764 | 527,394,741 | 478,576,592 | 004 | BULLY PULPIT INTERACTIVE LLC | 16.85% |
| 2 | MEDIA BUY & PRODUCTION | 198 | 526,677,344 | 525,237,387 | 004 | MEDIA BUYING & ANALYTICS LLC | 59.25% |
| 3 | PLACED MEDIA | 224 | 327,820,385 | 327,820,385 |  | STRATEGIC MEDIA SERVICES, INC. | 81.98% |
| 4 | PAYROLL | 80,458 | 296,479,811 | 237,549,261 | 001 | GUSTO | 15.09% |
| 5 | ONLINE FUNDRAISING | 353 | 204,565,034 | 204,524,026 | 001 | META PLATFORMS, INC. | 49.22% |
| 6 | MEDIA | 1,192 | 200,392,690 | 189,974,408 | 004 | AX MEDIA LLC | 16.46% |
| 7 | MEDIA ADVERTISING | 548 | 187,929,009 | 184,800,414 | 004 | AL MEDIA | 28.37% |
| 8 | FUNDRAISING CONSULTING | 20,846 | 187,916,662 | 117,678,216 | 003 | TARGETED VICTORY | 7.33% |
| 9 | DIGITAL ADVERTISING | 5,644 | 144,159,321 | 131,764,029 | 004 | MIDDLE SEAT | 12.16% |
| 10 | DIRECT MAIL | 5,088 | 129,388,605 | 105,291,151 | 001 | MISSIONWIRED | 32.93% |
| 11 | OPERATING EXPENDITURE | 4 | 119,980,345 | 0 | 001 | JIM A NORRIS FOR THE UNITED STATES PRESIDENT | 100.00% |
| 12 | ADVERTISING | 6,506 | 117,033,006 | 80,341,895 | 004 | TECHNICOLOR | 5.86% |
| 13 | CREDIT CARD PAYMENT | 6,050 | 113,635,192 | 101,873,733 | 001 | AMERICAN EXPRESS | 68.90% |
| 14 | PAYROLL TAXES | 21,796 | 112,842,698 | 101,447,100 | 001 | GUSTO | 34.54% |
| 15 | POSTAGE | 19,436 | 109,874,945 | 99,493,374 | 001 | TEAM DIRECT LLC | 14.12% |
| 16 | LEGAL CONSULTING | 4,344 | 108,910,411 | 105,359,292 | 001 | ROBERT & ROBERT, PLLC | 11.08% |
| 17 | DIGITAL CONSULTING | 7,893 | 101,008,527 | 78,061,468 | 001 | TARGETED VICTORY | 14.42% |
| 18 | PAID MEDIA | 265 | 94,726,876 | 94,722,046 | 004 | SCREEN STRATEGIES MEDIA | 44.46% |
| 19 | CANVASSING | 2,198 | 93,768,281 | 90,441,736 | 001 | PATRIOT GRASSROOTS | 27.80% |
| 20 | SALARY | 35,862 | 84,028,305 | 46,092,971 | 001 | WALLACE-JONES, REGINA | 0.75% |
| 21 | LEGAL SERVICES | 7,142 | 76,378,032 | 70,109,432 | 001 | WILMER CUTLER PICKERING HALE AND DORR LLP | 15.41% |
| 22 | MEDIA PLACEMENT | 833 | 74,663,345 | 18,173,996 | 001 | VENTURA MEDIA PARTNERS | 20.51% |
| 23 | TELEVISION ADVERTISING | 334 | 69,604,533 | 53,594,922 | 004 | SCREEN STRATEGIES MEDIA | 15.22% |
| 24 | MEDIA PRODUCTION | 2,650 | 68,410,745 | 64,272,733 | 001 | ASSEMBLY HOUSE LLC | 15.54% |
| 25 | TRAVEL | 51,290 | 66,769,327 | 60,174,195 | 002 | DNC TRAVEL ESCROW | 46.87% |
| 26 | TV ADVERTISING | 325 | 65,929,229 | 64,085,430 | 004 | SCREEN STRATEGIES MEDIA | 20.01% |
| 27 | POLLING | 1,800 | 61,576,293 | 50,347,270 | 005 | DNC SERVICES CORP./DEM. NAT'L COMMITTEE | 12.41% |
| 28 | TEXT MESSAGING | 1,385 | 57,083,220 | 53,236,974 | 004 | SCALE TO WIN | 38.35% |
| 29 | SERVICE FEE | 8,704 | 56,626,595 | 55,746,368 | 003 | ACTBLUE TECHNICAL SERVICES | 77.97% |
| 30 | DIGITAL FUNDRAISING & ONLINE ADVERTISING | 20 | 55,752,885 | 55,752,885 |  | LAUNCHPAD STRATEGIES, LLC | 57.07% |
| 31 | LIST ACQUISITION | 1,945 | 55,129,409 | 47,703,157 | 003 | MISSIONWIRED | 16.82% |
| 32 | FUNDRAISING FEES | 19,041 | 54,098,205 | 53,874,155 | 003 | FRONTLINE STRATEGIES LLC | 11.45% |
| 33 | IN-KIND CONTRIBUTION | 458 | 53,280,654 | 53,274,520 | 001 | UNITED STATES OF AMERICA INC | 97.61% |
| 34 | PRINTING | 11,878 | 50,388,080 | 42,364,577 | 001 | THE LUKENS COMPANY | 13.61% |
| 35 | DIRECT MAIL PRINTING & POSTAGE | 405 | 50,074,992 | 49,777,629 | 003 | RED BEACON STRATEGIES, LLC | 91.91% |
| 36 | POLITICAL STRATEGY CONSULTING | 5,584 | 49,338,397 | 44,002,657 | 001 | JACKSON PARKER AGENCY LLC | 2.89% |
| 37 | MERCHANT FEES | 44,608 | 48,437,942 | 44,580,325 | 001 | WINRED TECHNICAL SERVICES LLC | 53.29% |
| 38 | DIRECT MAIL SERVICES | 3,996 | 47,370,306 | 42,370,382 | 001 | RWT PRODUCTION, LLC | 12.15% |
| 39 | TV & CABLE MEDIA BUY | 42 | 46,901,324 | 46,901,324 |  | GRASSROOTS MEDIA | 100.00% |
| 40 | COMPLIANCE CONSULTING | 16,119 | 45,635,331 | 32,956,970 | 001 | RED CURVE SOLUTIONS | 17.60% |
| 41 | LIST RENTAL | 6,393 | 44,107,724 | 41,183,415 | 003 | FRONTLINE STRATEGIES LLC | 11.38% |
| 42 | TEXT MESSAGE OUTREACH | 117 | 43,033,975 | 43,033,975 |  | ACTION NETWORK | 50.35% |
| 43 | DIRECT MAIL PRODUCTION | 2,417 | 42,714,908 | 36,027,016 | 001 | TEAMDIRECT LLC | 8.88% |
| 44 | DIGITAL FUNDRAISING | 1,582 | 40,613,944 | 37,736,111 | 003 | TARGETED VICTORY LLC | 34.09% |
| 45 | MERCHANDISE FOR ONLINE STORE SALES | 270 | 40,437,931 | 40,437,931 |  | BUMPERACTIVE | 74.22% |
| 46 | FUNDRAISING CONSULTING SERVICES | 4,751 | 39,918,989 | 36,018,345 | 003 | MOTHERSHIP STRATEGIES | 19.08% |
| 47 | AUDIO VISUAL SERVICES, EVENT STAGING EXPENSE, & TRAVEL EXPENSES | 86 | 38,468,057 | 38,468,057 |  | EVENT STRATEGIES, INC. | 100.00% |
| 48 | MEDIA BUY GENERIC | 175 | 36,782,215 | 36,782,215 |  | GRASSROOTS MEDIA | 28.42% |
| 49 | SOFTWARE | 22,799 | 36,682,979 | 30,305,524 | 001 | NGP VAN, INC. | 13.00% |
| 50 | CREDIT CARD PROCESSING FEE | 58,053 | 33,568,770 | 30,953,686 | 001 | ACTBLUE TECHNICAL SERVICES | 79.88% |
| 51 | DIGITAL MEDIA BUY | 149 | 32,999,099 | 32,496,393 | 004 | GAMBIT STRATEGIES | 71.76% |
| 52 | CAMPAIGN CONSULTING | 4,831 | 32,892,343 | 18,440,225 | 001 | ACCELEVATE 2020 LLC | 24.43% |
| 53 | CREDIT CARD PROCESSING FEES | 57,088 | 31,109,104 | 26,456,955 | 001 | ACTBLUE TECHNICAL SERVICES | 60.12% |
| 54 | TAXES | 2,818 | 30,976,858 | 28,774,189 | 001 | INTERNAL REVENUE SERVICE | 59.55% |
| 55 | PAYROLL ESCROW TRANSFER AND PREPAID EXPENSES | 29 | 30,972,917 | 30,972,917 |  | MOVEON.ORG CIVIC ACTION | 100.00% |
| 56 | INSURANCE | 3,583 | 30,213,448 | 29,215,008 | 001 | ARTHUR J GALLAGHER | 13.99% |
| 57 | RESEARCH | 1,824 | 28,747,853 | 26,322,155 | 001 | THE MAJORITY INSTITUTE LLC | 18.31% |
| 58 | ONLINE ADVERTISING | 1,081 | 27,582,496 | 26,337,989 | 004 | WAVELENGTH STRATEGY LLC | 20.68% |
| 59 | COMMUNICATIONS CONSULTING | 3,471 | 27,557,885 | 22,165,903 | 001 | TARGETED VICTORY | 6.43% |
| 60 | CANVASSING/FIELD OPERATIONS | 32 | 27,003,351 | 27,003,351 |  | BLITZ CANVASSING | 53.97% |
| 61 | FINANCE CONSULTING | 2,811 | 26,888,730 | 20,813,836 | 003 | SOCKO STRATEGIES LLC | 5.86% |
| 62 | DEPOSIT - TV/MEDIA PLACEMENT | 5 | 26,683,779 | 26,683,779 |  | MAIN STREET MEDIA GROUP | 88.68% |
| 63 | TRAVEL: AIR | 284 | 26,165,802 | 26,165,802 |  | AIR PARTNER LLC | 48.42% |
| 64 | DATA SERVICES | 659 | 26,011,490 | 15,878,178 | 001 | PACTION DATA INC. | 37.22% |
| 65 | SMS ADVERTISING | 154 | 25,688,002 | 25,688,002 |  | DIRECTSND, LLC | 44.60% |
| 66 | 24,999,995 USDC RECEIVED, NOT LIQUIDATED | 1 | 24,999,995 | 0 | 001 | COINBASE | 100.00% |
| 67 | SURVEY RESEARCH | 538 | 24,221,865 | 20,427,370 | 005 | WPA INTELLIGENCE | 33.96% |
| 68 | MEDIA BUY AND PRODUCTION | 47 | 23,213,052 | 23,213,052 |  | MEDIA BUYING & ANALYTICS LLC | 53.65% |
| 69 | CAMPAIGN EVENT PRODUCTION | 293 | 23,139,054 | 23,139,054 |  | MARYLAND EVENT SERVICES | 24.87% |
| 70 | IN-KIND 236.20702457 BITCOINS NOT LIQUIDATED | 1 | 23,000,000 | 0 | 001 | COINBASE | 100.00% |
| 71 | HEADQUARTERS ACCOUNT - TRANSFER FOR HEADQUARTERS EXPENSES | 13 | 22,311,706 | 22,311,706 |  | DNC SERVICES CORP./DEM. NAT'L COMMITTEE | 100.00% |
| 72 | TELEMARKETING | 1,275 | 21,707,584 | 20,886,084 | 001 | FLS CONNECT LLC | 25.92% |
| 73 | MAIL PRODUCTION SERVICES | 307 | 21,604,178 | 21,604,178 |  | TEAM DIRECT LLC | 40.67% |
| 74 | CREDIT CARD PAYMENT - SEE BELOW IF ITEMIZED | 1,733 | 21,509,085 | 20,814,626 | 001 | AMERICAN EXPRESS | 69.39% |
| 75 | COMPLIANCE SERVICES | 9,372 | 21,442,141 | 20,390,139 | 001 | MBA CONSULTING GROUP | 24.93% |
| 76 | DATA SERVICE | 417 | 21,411,389 | 21,411,389 |  | NGP VAN, INC. | 28.05% |
| 77 | DIGITAL ADS | 1,077 | 21,312,675 | 12,191,647 | 004 | AISLE 518 STRATEGIES, LLC | 19.14% |
| 78 | GENERIC CMTE. MEDIA BUYS | 195 | 20,982,718 | 20,982,718 |  | LEFT HOOK COMMUNICATIONS LLC | 21.96% |
| 79 | RENT | 6,206 | 20,650,965 | 17,546,470 | 001 | 1800 M STREET REIT, LP | 14.58% |
| 80 | POLLING/FOCUS GROUPS | 222 | 20,272,963 | 20,272,963 |  | HART RESEARCH ASSOCIATES | 13.85% |
| 81 | VOTER REGISTRATION CONSULTING | 94 | 20,136,039 | 20,134,307 | 001 | THE OUTREACH TEAM, LLC | 56.36% |
| 82 | PAYROLL - SEE BELOW IF ITEMIZED | 1,403 | 19,649,007 | 19,649,007 |  | PAYROLL DATA PROCESSING | 75.16% |
| 83 | FUNDRAISING CONSULTANT | 1,339 | 18,756,382 | 16,239,927 | 003 | MOTHERSHIP STRATEGIES | 61.01% |
| 84 | STRATEGIC CONSULTING | 3,041 | 18,722,603 | 13,853,695 | 001 | THOMAS PARTNERS | 4.76% |
| 85 | VIDEO PRODUCTION SERVICES | 213 | 18,019,774 | 17,838,350 | 004 | THEMATIC CAMPAIGNS | 83.22% |
| 86 | SPOKESPERSON CONSULTANT | 18 | 18,000,000 | 18,000,000 |  | BAUER, BRIAN | 5.56% |
| 87 | DIGITAL SERVICES | 1,000 | 17,931,963 | 17,285,334 | 001 | MISSION WIRED | 39.17% |
| 88 | AD BUY | 304 | 17,758,237 | 16,168,635 | 101 | M2 PLACEMENT | 32.80% |
| 89 | TEXTING SERVICES | 1,634 | 17,750,705 | 17,492,886 | 001 | MESSAGE DIGITAL | 24.28% |
| 90 | AUDIO VISUAL SERVICES | 374 | 17,745,612 | 17,734,691 | 001 | CREATIVE SOUND AND LIGHTING | 36.41% |
| 91 | CREDIT CARD FEES | 29,532 | 17,731,266 | 10,064,581 | 001 | ACTBLUE TECHNICAL SERVICES | 47.28% |
| 92 | RESEARCH CONSULTING | 1,203 | 17,634,277 | 16,881,223 | 001 | HAYSTACKID LLC | 11.26% |
| 93 | SALARY & OVERHEAD EXPENSES | 42 | 17,315,530 | 17,315,530 |  | DNC SERVICES CORP./DEM. NAT'L COMMITTEE | 75.31% |
| 94 | MEDIA CONSULTING / MEDIA PRODUCTION / MEDIA PLACEMENT | 16 | 16,919,009 | 16,919,009 |  | ONMESSAGE INC. | 100.00% |
| 95 | FUNDRAISING SERVICES | 2,802 | 16,761,108 | 14,978,672 | 003 | SAPPHIRE STRATEGIES | 19.74% |
| 96 | TRAVEL; AIRFARE | 84 | 16,310,101 | 16,310,101 |  | PRIVATE JET SERVICES GROUP, LLC | 48.94% |
| 97 | DATA PROCESSING SERVICES | 333 | 15,910,151 | 15,872,209 | 003 | RED CURVE SOLUTIONS | 89.81% |
| 98 | FIELD ORGANIZING | 27 | 15,908,135 | 15,849,755 | 007 | SHAWMUT SERVICES LLC | 99.63% |
| 99 | TELEVISION AD BUY | 12 | 15,622,151 | 15,622,151 |  | SCREEN STRATEGIES MEDIA | 91.23% |
| 100 | IN-KIND - 15,500,000 US DOLLAR COIN (USDC) | 1 | 15,500,000 | 15,500,000 |  | COINBASE | 100.00% |
| 101 | MEDIA CONSULTING | 1,131 | 15,493,128 | 12,411,955 | 001 | FIDI MEDIA LLC | 11.74% |
| 102 | DIGITAL CONSULTING SERVICES | 1,385 | 15,412,206 | 14,774,180 | 003 | AMPLIFY, LLC | 18.11% |
| 103 | SALARIES | 5,214 | 15,160,615 | 15,159,415 | 001 | MACKLER, JESSICA | 2.57% |
| 104 | TEXT MESSAGING SERVICES | 1,384 | 15,067,433 | 15,017,488 | 001 | MOTHERSHIP STRATEGIES | 28.85% |
| 105 | DIGITAL ORGANIZING | 128 | 14,840,435 | 14,840,435 |  | MOTHERSHIP STRATEGIES | 56.20% |
| 106 | CREDIT CARD PAYMENT: SEE ITEMIZATIONS IF REQUIRED | 273 | 14,632,219 | 14,632,219 |  | AMERICAN EXPRESS | 98.02% |
| 107 | DIGITAL MEDIA | 223 | 14,547,000 | 14,160,863 | 004 | GPS IMPACT | 56.32% |
| 108 | DIGITAL ACQUISITION | 295 | 14,425,778 | 14,425,759 | 006 | MIDDLE SEAT | 44.38% |
| 109 | ADVANCE PAYMENT FOR FUTURE INDEPENDENT EXPENDITURES | 81 | 14,329,117 | 14,329,117 |  | PENNSYLVANIA SEIU COPE | 18.09% |
| 110 | STRATEGY CONSULTING | 1,869 | 14,186,360 | 9,387,308 | 001 | HWY 99 LLC | 6.42% |
| 111 | DIGITAL FUNDRAISING SERVICES | 353 | 14,181,262 | 13,320,646 | 003 | AISLE 518 STRATEGIES | 64.61% |
| 112 | MEDIA PLACEMENT AND PRODUCTION | 82 | 13,963,704 | 452,516 | 004 | GEN2 SOLUTIONS, LLC | 96.61% |
| 113 | MERCHANDISE FEES | 667 | 13,858,159 | 13,857,855 | 003 | WINRED TECHNICAL SERVICES LLC | 83.25% |
| 114 | DIRECT MAIL POSTAGE | 948 | 13,783,048 | 10,961,388 | 003 | RWT PRODUCTION, LLC | 20.37% |
| 115 | PAYROLL - SEE MEMO ITEMS | 1,737 | 13,514,204 | 13,018,810 | 001 | GUSTO | 94.95% |
| 116 | PAYROLL SVC/TAXES/INSURANCE | 56 | 13,066,839 | 13,066,839 |  | INSPERITY | 100.00% |
| 117 | POLLING EXPENSE | 198 | 13,063,897 | 12,811,133 | 001 | FABRIZIO, LEE & ASSOCIATES, LLC | 66.74% |
| 118 | GENERIC CMTE. POSTAGE/DELIVERY | 273 | 12,981,924 | 0 | 001 | RWT PRODUCTION, LLC | 92.99% |
| 119 | EVENT PRODUCTION & SITE RENTALS | 114 | 12,841,195 | 12,841,195 |  | WEYMOUTH WATSON, LLC | 23.97% |
| 120 | POLLING SERVICES / CONSULTING | 41 | 12,814,158 | 12,814,158 |  | FABRIZIO LEE & ASSOCIATES LLC | 48.25% |
| 121 | POSTAGE & SHIPPING | 466 | 12,808,460 | 12,805,441 | 001 | MISSIONWIRED | 84.61% |
| 122 | ADVERTISING - TV | 79 | 12,751,608 | 11,262,164 | 102 | AL MEDIA | 29.08% |
| 123 | CONVENTION ACCOUNT - TRANSFER | 6 | 12,554,717 | 12,554,717 |  | 2024 DEMOCRATIC NATIONAL CONVENTION COMMITTEE | 100.00% |
| 124 | DIGITAL CONSULTING, ONLINE ADVERTISING & LIST RENTAL | 9 | 12,442,036 | 12,442,036 |  | CAMPAIGN INBOX | 85.67% |
| 125 | DIGITAL FUNDRAISING CONSULTING / SMS MESSAGES / LIST RENTAL / WEB SERVICES | 13 | 12,399,926 | 12,399,926 |  | TARGETED VICTORY LLC | 100.00% |
| 126 | PAYROLL: EMPLOYEE WITHHOLDING | 68 | 12,253,709 | 0 | 001 | UKG INC. | 57.26% |
| 127 | LEGAL FEES | 2,413 | 12,113,481 | 8,937,827 | 001 | ELIAS LAW GROUP | 7.51% |
| 128 | DIRECT MARKETING SERVICES | 365 | 12,042,875 | 12,042,875 |  | TATANGO INC. | 28.81% |
| 129 | FUNDRAISING EVENT PRODUCTION & SITE RENTALS | 156 | 11,916,656 | 11,916,656 |  | EDEN T PRODUCTIONS LLC | 13.28% |
| 130 | RELATIONAL ORGANIZING | 18 | 11,663,199 | 11,663,199 |  | RALLY BY RELENTLESS | 99.96% |
| 131 | DIGITAL BUY | 42 | 11,662,711 | 11,395,211 | 004 | GAMBIT STRATEGIES, LLC | 93.46% |
| 132 | CONTRIBUTION | 585 | 11,461,718 | 7,616,994 | 011 | AB PAC | 36.64% |
| 133 | PRINTING & COPYING | 1,503 | 11,431,434 | 11,431,434 |  | GARNER PRINTING | 14.41% |
| 134 | VENUE RENTAL AND CATERING | 150 | 11,412,070 | 11,388,379 | 007 | WALDORF ASTORIA MONARCH BEACH RESORT & CLUB | 11.64% |
| 135 | PERSONNEL/BENEFITS | 24 | 11,243,555 | 11,243,555 |  | AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE | 100.00% |
| 136 | PRINTING/POSTAGE | 489 | 11,221,224 | 10,538,275 | 001 | THE RICHARD NORMAN COMPANY | 49.97% |
| 137 | EVENT PRODUCTION/AUDIO VISUAL SERVICES | 128 | 11,175,187 | 11,175,187 |  | WIZARD STUDIOS NORTH, INC | 80.29% |
| 138 | GENERIC CMTE. SUBSCRIPTIONS | 532 | 10,832,319 | 10,832,319 |  | TATANGO, INC. | 47.13% |
| 139 | CREDIT CARD - SEE BELOW IF ITEMIZED | 206 | 10,723,215 | 10,723,215 |  | AMERICAN EXPRESS | 99.47% |
| 140 | EVENT PRODUCTION | 640 | 10,553,705 | 10,320,534 | 001 | MAJIC PRODUCTIONS | 18.95% |
| 141 | STRATEGIC CONSULTING SERVICES | 1,519 | 10,544,677 | 10,211,144 | 001 | HICKMAN ANALYTICS, INC. | 9.01% |
| 142 | PAYROLL/TAXES/RETIREMENT | 50 | 10,446,395 | 10,446,395 |  | INSPERITY | 100.00% |
| 143 | CANVASSING SERVICES | 200 | 10,396,274 | 10,059,559 | 003 | OTG STRATEGIES | 58.09% |
| 144 | SOFTWARE SUBSCRIPTION | 4,355 | 10,357,850 | 4,703,522 | 001 | SCALE TO WIN | 50.26% |
| 145 | TEXTING | 1,084 | 10,331,183 | 8,677,412 | 001 | SWITCHBOARD | 41.71% |
| 146 | PAID MEDIA BUY - TV | 53 | 10,170,065 | 5,572,178 | 004 | BLUEWEST MEDIA | 45.21% |
| 147 | MEDIA ADVERTISEMENT | 55 | 10,169,846 | 7,896,189 | 004 | AMERICAN MEDIA & ADVOCACY GROUP | 67.24% |
| 148 | DIGITAL FUNDRAISING FEES | 2,497 | 10,017,351 | 9,979,714 | 003 | TMA DIRECT | 18.41% |
| 149 | GENERIC CMTE. POLLING | 660 | 10,003,274 | 0 | 005 | GBAO | 15.81% |
| 150 | CATERING | 6,806 | 9,995,506 | 8,327,644 | 003 | CAPITOL HILL CLUB | 2.04% |
| 151 | VOTER CANVASSING | 31 | 9,993,958 | 9,993,958 |  | OTG STRATEGIES | 43.28% |
| 152 | SECURITY SERVICES | 1,429 | 9,920,843 | 9,680,953 | 001 | PROSEGUR GLOBAL RISK SERVICES LLC | 41.26% |
| 153 | ALLOCABLE EXPENSES FROM NRCC ACCT | 22 | 9,672,630 | 9,672,630 |  | NRCC | 100.00% |
| 154 | GENERIC STRATEGIC/ POLITICAL CONSULTANT | 509 | 9,574,705 | 9,574,705 |  | AMPLIFY MEDIA LLC | 20.71% |
| 155 | ADVANCE LOGISTICS SERVICES | 5,283 | 9,391,888 | 9,391,888 |  | PAISLEY, KELLY | 0.64% |
| 156 | DIGITAL FUNDRAISING CONSULTING | 3,456 | 9,305,564 | 4,072,401 | 003 | TARGETED VICTORY | 35.19% |
| 157 | WEB HOSTING | 1,313 | 9,014,847 | 8,938,764 | 001 | SALESFORCE.COM INC | 73.91% |
| 158 | BENEFITS-MEDICAL/DENTAL | 488 | 8,992,352 | 8,992,352 |  | CAREFIRST BLUECROSS BLUESHIELD | 92.47% |
| 159 | CREDIT CARD PAYMENT - SEE BELOW | 970 | 8,964,303 | 8,631,320 | 001 | AMERICAN EXPRESS | 62.71% |
| 160 | DIRECT MAIL COSTS | 503 | 8,958,231 | 4,148 | 003 | MDI IMAGING & MAIL | 17.36% |
| 161 | EVENT PRODUCTION & AUDIO VISUAL SERVICES | 44 | 8,896,191 | 8,896,191 |  | KIRSHNER EVENTS INC | 50.58% |
| 162 | MANAGEMENT CONSULTING | 1,068 | 8,856,861 | 6,924,376 | 001 | JACKSON CONSULTING GROUP LLC | 4.19% |
| 163 | SEE MEMO ITEMS | 1,786 | 8,675,032 | 1,237,088 | 001 | AMERICAN EXPRESS | 30.04% |
| 164 | TV & RADIO AD BUY | 19 | 8,631,905 | 8,631,905 |  | CANAL PARTNERS MEDIA | 100.00% |
| 165 | GENERAL CAMPAIGN CONSULTING | 1,572 | 8,577,024 | 5,164,718 | 001 | ASCENSION LLC | 4.87% |
| 166 | COMPUTER EQUIPMENT | 616 | 8,228,256 | 8,199,232 | 001 | MAC BUSINESS SOLUTIONS | 61.14% |
| 167 | JFC FUNDRAISING ADVERTISING | 35 | 8,224,768 | 8,224,768 |  | GEN2 SOLUTIONS LLC | 67.54% |
| 168 | HEALTH INSURANCE | 1,663 | 7,944,422 | 7,461,241 | 001 | HIGHMARK HEALTH CARE | 32.96% |
| 169 | REIMBURSEMENT FOR FUNDRAISING EXPENSES | 27 | 7,890,343 | 7,746,887 | 003 | DONALD J. TRUMP FOR PRESIDENT 2024, INC. | 98.18% |
| 170 | LODGING | 5,591 | 7,757,661 | 6,632,076 | 002 | HYATT REGENCY MCCORMICK PLACE CHICAGO | 7.72% |
| 171 | CREDIT CARD PAYMENT, SEE BELOW | 372 | 7,754,967 | 7,729,681 | 001 | AMERICAN EXPRESS | 81.28% |
| 172 | ACCOUNTING SERVICES | 3,767 | 7,574,247 | 5,313,006 | 001 | PCMS, LLC | 8.52% |
| 173 | VIDEO PRODUCTION | 577 | 7,558,343 | 5,082,255 | 004 | SIEGEL STRATEGIES, LLC | 16.44% |
| 174 | DIRECT MAIL PRINTING | 266 | 7,553,723 | 6,985,718 | 003 | TEAMDIRECT | 36.01% |
| 175 | DIRECT MARKETING | 620 | 7,540,217 | 6,615,886 | 003 | TATANGO INC. | 14.80% |
| 176 | VOTER MAIL | 50 | 7,500,681 | 7,317,765 | 004 | GDA WINS | 70.03% |
| 177 | PRE-PAYMENT FOR IES DISSEMINATING IN OCTOBER | 19 | 7,463,272 | 7,463,272 |  | DIVVY | 33.77% |
| 178 | CREDIT CARD MERCHANT FEE | 7,576 | 7,435,646 | 7,279,110 | 001 | WINRED TECHNICAL SERVICES LLC | 63.17% |
| 179 | SEE MEMO | 1,559 | 7,257,586 | 3,474,035 | 001 | ADP | 26.26% |
| 180 | RESEARCH SERVICES | 505 | 7,223,178 | 6,573,741 | 001 | FRAMESHIFT LLC | 9.88% |
| 181 | GENERIC CMTE. PRINTING | 310 | 7,161,869 | 7,161,869 |  | RWT PRODUCTION, LLC | 98.63% |
| 182 | SITE RENTAL | 874 | 7,149,685 | 7,125,270 | 001 | DYNAMO STADIUM, LLC | 9.35% |
| 183 | DISGORGEMENT | 5 | 7,037,952 | 7,033,900 | 001 | U.S. MARSHALS SERVICE | 85.25% |
| 184 | BANK FEES | 24,249 | 7,037,712 | 6,251,418 | 001 | WINRED TECHNICAL SERVICES LLC | 32.64% |
| 185 | PROCESSING FEE | 7,983 | 7,027,330 | 6,508,486 | 001 | WIN RED | 72.49% |
| 186 | DIGITAL FUNDRAISING CONSULTING & ONLINE ADVERTISING | 2 | 6,928,458 | 6,928,458 |  | LAUNCHPAD STRATEGIES, LLC | 100.00% |
| 187 | TAXES - PAYROLL | 104 | 6,911,976 | 6,887,497 | 001 | PAYLOCITY | 99.58% |
| 188 | TRANSFER TO STATE ACCOUNT FOR NON-FEDERAL EXPENSES | 17 | 6,750,000 | 6,750,000 |  | NJ STATE LABORERS' PAC | 100.00% |
| 189 | PAID PHONE CALLS | 19 | 6,738,360 | 6,738,360 |  | WILDFIRE CONTACT LLC | 54.08% |
| 190 | CREDIT CARD MERCHANT FEES | 3,622 | 6,728,400 | 6,726,481 | 001 | WINRED TECHNICAL SERVICES LLC | 85.33% |
| 191 | CREDIT CARD PROCESSING | 8,674 | 6,525,470 | 6,011,672 | 001 | ACTBLUE TECHNICAL SERVICES | 47.30% |
| 192 | EVENT EXPENSE: FACILITY RENTAL | 189 | 6,457,631 | 6,457,081 | 001 | MSG ARENA LLC | 10.06% |
| 193 | DIRECT MAIL EXPENSE | 1,072 | 6,427,305 | 5,289,157 | 001 | FULFILLMENT SOLUTIONS INC. | 19.03% |
| 194 | NONFEDERAL CONTRIBUTION FROM CONTRIBUTION ACCOUNT | 80 | 6,402,821 | 6,402,821 |  | PENNSYLVANIA HOUSE DEMOCRATIC CAMPAIGN COMMITTEE | 26.11% |
| 195 | EMAIL SERVICES | 2,323 | 6,398,436 | 6,328,428 | 001 | DYSPATCHIT EMAIL AND TEXT SERVICES | 40.31% |
| 196 | FUNDRAISING, PAYMENT, TECHNICAL & COMPLIANCE SVCS | 309 | 6,386,661 | 0 | 003 | PATRON PLUS, INC | 19.18% |
| 197 | GENERIC CMTE. EVENTS/MEETINGS | 785 | 6,373,696 | 6,373,696 |  | BANK OF AMERICA | 10.17% |
| 198 | ARTWORK | 151 | 6,301,900 | 6,300,350 | 001 | LEIGH, SIMONE | 5.55% |
| 199 | WIRE SERVICES/ ON LINE SVCS. | 265 | 6,247,788 | 0 | 001 | SWITCHBOARD PUBLIC BENEFIT CORP. | 36.65% |
| 200 | FUNDRAISING AD BUY | 27 | 6,247,013 | 6,247,013 |  | M2 PLACEMENT | 97.28% |

FEC codes 101–107 are presidential filers' codes, which carry no `CATEGORY_DESC` in the file. Their
meanings are FEC's [list of disbursement category codes](https://www.fec.gov/campaign-finance-data/disbursement-category-code-descriptions)
(read 2026-11-21): 101 non-allocable, 102 media, 103 mass mailings and campaign materials, 104
overhead of state offices, 105 special telephone programs, 106 public opinion polls, 107
fundraising. 001–012 are everyone else's. A handful of rows write a code without its leading zeros
(`1`, `01`) or a line number (`21B`). 101's $129.5M is one row's $119,980,010 (Q8h), Jim A Norris
for the United States President's `OPERATING EXPENDITURE` to itself, a filer not in `cm`.

The top 200 purposes hold 76.75% of counted dollars: a 200-row test set stands for three quarters of
the money and none of the long tail. 68,541 distinct purposes share the rest.

### Definitions and tie-breaks

Written before any row was labelled, and applied to the purpose as §2 normalizes it. A purpose is
labelled by what it says. Its largest payee (Q8e) is read only when the words leave the category
open, and the reason then names it.

| Slug | Holds | FEC codes |
| --- | --- | --- |
| `media` | Paid advertising in broadcast, cable, satellite, radio, print and out of home, its production (video, audio) and its placement; an ad or "media" buy whose medium is unnamed | 004, 102 |
| `digital` | Online advertising (search, social, display, digital video), text and email messaging, websites and hosting, digital organizing and digital consulting, and campaign data and voter-file services | — |
| `fundraising` | The cost of raising money: fundraising consultants and their commissions, digital and online fundraising, donor list rental and acquisition, telemarketing, merchandise sold to supporters, a fundraising event's costs where the purpose names fundraising | 003, 107 |
| `payroll` | Pay to staff and its costs: salary, payroll, payroll taxes and withholding, benefits and health insurance, payroll processors and employer organizations | — |
| `consulting` | General, political, strategic, management and communications consulting whose purpose names no other category | — |
| `travel` | Air and ground travel, lodging, mileage, meals while travelling | 002 |
| `events` | Putting on an event: venue and site rental, production and staging, audio-visual, catering, advance and logistics | 007 |
| `administrative` | Running an office: rent, utilities, software, computer equipment, supplies, insurance other than staff's, taxes other than payroll's, security, subscriptions | 001, 104 |
| `legal_compliance` | Legal services and fees, compliance consulting and services, accounting and FEC reporting | — |
| `transfers_fees` | Money passed on: transfers to another committee or account, contributions, donations, refunds, loan repayments, disgorgement; and fees charged per payment processed: merchant, card-processing, conduit and bank fees | 008–012 |
| `other` | Anything else, and a purpose that names nothing bought (`SEE MEMO`, `OPERATING EXPENDITURE`) | 101 |

Tie-breaks, numbered as the CSV's `reason` column cites them:

- **T1.** Advertising whose channel is unnamed (`ADVERTISING`, `AD BUY`) is `media`. Only advertising named digital, online, SMS or social is `digital`.
- **T2.** When a purpose names both what the money was for and the channel it went through, the activity wins: `DIGITAL FUNDRAISING`, `FUNDRAISING AD BUY` and `JFC FUNDRAISING ADVERTISING` are `fundraising`.
- **T3.** "*X* consulting", "*X* consultant" and "*X* services" go to *X*'s category when *X* names one: `FUNDRAISING CONSULTING` is `fundraising`, `MEDIA CONSULTING` is `media`, `LEGAL CONSULTING` is `legal_compliance`.
- **T4.** A fee charged per payment processed is `transfers_fees`: merchant, processing, card and bank fees, and a `SERVICE FEE` or other fee whose largest payee is a conduit (ActBlue, WinRed) or a processor. A fee whose largest payees are fundraising firms is `fundraising`.
- **T5.** A purpose that lists two or more categories takes the first named: `SALARY & OVERHEAD EXPENSES` is `payroll`, `AUDIO VISUAL SERVICES, EVENT STAGING EXPENSE, & TRAVEL EXPENSES` is `events`.
- **T6.** Mail and printing (direct mail, postage, printing, mail production, lettershop) have no home among the 11. FEC's 004 is broadcast, print and cable *advertising*, and FEC puts mass mailings in 006, campaign materials. In the first pass they are `other`, group `mail`.
- **T7.** Polling, survey and focus-group research, and research unqualified (opposition and policy research), are `other`, group `polling_research`, in the first pass.
- **T8.** Voter contact in person and by phone (canvassing, field organizing, relational organizing, voter registration, paid calls to voters) is `other`, group `field`, in the first pass. `events` holds putting on an event, not knocking on doors, although FEC's 007 description names phone banks and get-out-the-vote.
- **T9.** A card bill (`CREDIT CARD PAYMENT`, `… - SEE BELOW IF ITEMIZED`) says nothing of what was bought. It is `other`, group `credit_card`, in the first pass. Q3's adopted rule counts the bill, not its charges, so these are counted dollars.
- **T10.** An independent expenditure paid ahead (`ADVANCE PAYMENT FOR FUTURE INDEPENDENT EXPENDITURES`) whose medium is unnamed is `media`.
- **T11.** In-kind outlays (Q3's orphan children, Q7c) and in-kind crypto received but not sold are `other`, group `in_kind`.

The bar (§1.1): after the first pass, each `other` group holding 2% or more of the labelled set's
dollars becomes a category, and its rows are relabelled with its slug. The CSV is labelled in the
final list.

### The labels

`labels.py` holds the first-pass label of each purpose, with its `other` group, and writes the CSV.
Each label is one of the categories above, or `other` with a group, and each judgement call carries
its reason:

```python
"""Pass-1 labels of the 200 purposes against the milestone's 11 categories (definitions and
tie-breaks in the document's Q8). A purpose the 11 cannot hold is `other` with the group it
belongs to; a group at 2% or more of the labelled set's dollars becomes a category (pass 2)."""
import csv, sys

C, J = "clear", "judgement"
# purpose: (pass-1 category, group when other, confidence, reason)
L = {}
def lab(cat, conf, reason, *purposes, group=None):
    for p in purposes:
        assert p not in L, p
        L[p] = (cat, group, conf, reason)

lab("media", C, "", "MEDIA BUY", "MEDIA BUY & PRODUCTION", "PLACED MEDIA", "MEDIA", "MEDIA ADVERTISING",
    "PAID MEDIA", "MEDIA PLACEMENT", "TELEVISION ADVERTISING", "MEDIA PRODUCTION", "TV ADVERTISING",
    "TV & CABLE MEDIA BUY", "MEDIA BUY GENERIC", "DEPOSIT - TV/MEDIA PLACEMENT", "MEDIA BUY AND PRODUCTION",
    "GENERIC CMTE. MEDIA BUYS", "VIDEO PRODUCTION SERVICES", "AD BUY",
    "MEDIA CONSULTING / MEDIA PRODUCTION / MEDIA PLACEMENT", "TELEVISION AD BUY", "MEDIA PLACEMENT AND PRODUCTION",
    "ADVERTISING - TV", "PAID MEDIA BUY - TV", "MEDIA ADVERTISEMENT", "TV & RADIO AD BUY", "VIDEO PRODUCTION")
lab("media", C, "", "MEDIA CONSULTING")  # T3
lab("media", J, "T1: the channel is unnamed; advertising not named digital is media", "ADVERTISING")
lab("media", J, "T10: an independent expenditure paid ahead, medium unnamed, is media",
    "ADVANCE PAYMENT FOR FUTURE INDEPENDENT EXPENDITURES", "PRE-PAYMENT FOR IES DISSEMINATING IN OCTOBER")

lab("digital", C, "", "DIGITAL ADVERTISING", "DIGITAL CONSULTING", "TEXT MESSAGING", "DIGITAL MEDIA BUY",
    "ONLINE ADVERTISING", "SMS ADVERTISING", "DATA SERVICES", "DATA SERVICE", "DIGITAL ADS", "DIGITAL SERVICES",
    "TEXTING SERVICES", "TEXT MESSAGING SERVICES", "DIGITAL MEDIA", "DIGITAL BUY", "TEXTING", "WEB HOSTING",
    "EMAIL SERVICES", "TEXT MESSAGE OUTREACH", "DIGITAL CONSULTING SERVICES")
lab("digital", C, "", "DIGITAL CONSULTING, ONLINE ADVERTISING & LIST RENTAL")  # T5: first named
lab("digital", J, "T5: digital is named before organizing; field takes in-person organizing", "DIGITAL ORGANIZING")
lab("digital", J, "the purpose names no channel; its largest payee (Tatango, 29%) is a text-messaging platform",
    "DIRECT MARKETING SERVICES")
lab("digital", J, "the purpose names no channel; its largest payee (Tatango, 15%) is a text-messaging platform",
    "DIRECT MARKETING")
lab("digital", J, "the purpose names wire and online services; its largest payee (Switchboard, 37%) is a texting platform",
    "WIRE SERVICES/ ON LINE SVCS.")

lab("fundraising", C, "", "FUNDRAISING CONSULTING", "ONLINE FUNDRAISING", "LIST ACQUISITION", "LIST RENTAL",
    "DIGITAL FUNDRAISING", "FUNDRAISING CONSULTING SERVICES", "FUNDRAISING CONSULTANT", "FUNDRAISING SERVICES",
    "DIGITAL FUNDRAISING SERVICES", "DIGITAL FUNDRAISING CONSULTING", "REIMBURSEMENT FOR FUNDRAISING EXPENSES",
    "FUNDRAISING AD BUY", "JFC FUNDRAISING ADVERTISING", "DIGITAL FUNDRAISING & ONLINE ADVERTISING",
    "DIGITAL FUNDRAISING CONSULTING & ONLINE ADVERTISING",
    "DIGITAL FUNDRAISING CONSULTING / SMS MESSAGES / LIST RENTAL / WEB SERVICES",
    "FUNDRAISING, PAYMENT, TECHNICAL & COMPLIANCE SVCS")
lab("fundraising", J, "T2: fundraising named with an event's costs is fundraising",
    "FUNDRAISING EVENT PRODUCTION & SITE RENTALS")
lab("fundraising", J, "a campaign's finance consultant raises its money", "FINANCE CONSULTING")
lab("fundraising", J, "T4: the largest payees are fundraising consultants, not a conduit or processor",
    "FUNDRAISING FEES", "DIGITAL FUNDRAISING FEES")
lab("fundraising", J, "telemarketing names calls for money; its largest payee does fundraising and voter calls",
    "TELEMARKETING")
lab("fundraising", J, "merchandise sold to supporters raises money", "MERCHANDISE FOR ONLINE STORE SALES")
lab("fundraising", J, "acquisition names donor acquisition; T2 the activity wins over the channel", "DIGITAL ACQUISITION")

lab("payroll", C, "", "PAYROLL", "PAYROLL TAXES", "SALARY", "PAYROLL - SEE BELOW IF ITEMIZED", "SALARIES",
    "PAYROLL - SEE MEMO ITEMS", "PAYROLL SVC/TAXES/INSURANCE", "PAYROLL: EMPLOYEE WITHHOLDING",
    "PERSONNEL/BENEFITS", "PAYROLL/TAXES/RETIREMENT", "BENEFITS-MEDICAL/DENTAL", "HEALTH INSURANCE", "TAXES - PAYROLL")
lab("payroll", J, "T5: salary is named before overhead", "SALARY & OVERHEAD EXPENSES")
lab("payroll", J, "T5: payroll is named first", "PAYROLL ESCROW TRANSFER AND PREPAID EXPENSES")

lab("consulting", C, "", "POLITICAL STRATEGY CONSULTING", "CAMPAIGN CONSULTING", "COMMUNICATIONS CONSULTING",
    "STRATEGIC CONSULTING", "SPOKESPERSON CONSULTANT", "STRATEGY CONSULTING", "STRATEGIC CONSULTING SERVICES",
    "GENERIC STRATEGIC/ POLITICAL CONSULTANT", "MANAGEMENT CONSULTING", "GENERAL CAMPAIGN CONSULTING")

lab("travel", C, "", "TRAVEL", "TRAVEL: AIR", "TRAVEL; AIRFARE", "LODGING")

lab("events", C, "", "CAMPAIGN EVENT PRODUCTION", "AUDIO VISUAL SERVICES", "EVENT PRODUCTION & SITE RENTALS",
    "VENUE RENTAL AND CATERING", "EVENT PRODUCTION/AUDIO VISUAL SERVICES", "EVENT PRODUCTION",
    "EVENT PRODUCTION & AUDIO VISUAL SERVICES", "GENERIC CMTE. EVENTS/MEETINGS", "EVENT EXPENSE: FACILITY RENTAL",
    "ADVANCE LOGISTICS SERVICES", "CATERING")
lab("events", C, "", "AUDIO VISUAL SERVICES, EVENT STAGING EXPENSE, & TRAVEL EXPENSES")  # T5
lab("events", J, "a site is rented for an event far more often than for an office; largest payee a stadium", "SITE RENTAL")

lab("administrative", C, "", "SOFTWARE", "INSURANCE", "RENT", "COMPUTER EQUIPMENT", "SECURITY SERVICES")
lab("administrative", J, "taxes not named payroll; its largest payee is the IRS, which payroll taxes also reach", "TAXES")
lab("administrative", J, "software is administrative; its largest payee (Scale to Win) is a texting tool",
    "SOFTWARE SUBSCRIPTION")
lab("administrative", J, "subscriptions are administrative; its largest payee (Tatango, 47%) is a texting platform",
    "GENERIC CMTE. SUBSCRIPTIONS")

lab("legal_compliance", C, "", "LEGAL CONSULTING", "LEGAL SERVICES", "COMPLIANCE CONSULTING", "COMPLIANCE SERVICES",
    "LEGAL FEES", "ACCOUNTING SERVICES")
lab("legal_compliance", J, "its largest payee (Red Curve Solutions, 90%) is a compliance firm processing contributions",
    "DATA PROCESSING SERVICES")

lab("transfers_fees", C, "", "MERCHANT FEES", "CREDIT CARD PROCESSING FEE", "CREDIT CARD PROCESSING FEES",
    "CREDIT CARD FEES", "CREDIT CARD MERCHANT FEE", "CREDIT CARD MERCHANT FEES", "CREDIT CARD PROCESSING",
    "PROCESSING FEE", "BANK FEES", "HEADQUARTERS ACCOUNT - TRANSFER FOR HEADQUARTERS EXPENSES",
    "CONVENTION ACCOUNT - TRANSFER", "CONTRIBUTION", "TRANSFER TO STATE ACCOUNT FOR NON-FEDERAL EXPENSES",
    "NONFEDERAL CONTRIBUTION FROM CONTRIBUTION ACCOUNT")
lab("transfers_fees", J, "T4: the largest payee (ActBlue, 78%) is a conduit; its fee is per contribution", "SERVICE FEE")
lab("transfers_fees", J, "T4: the largest payee (WinRed, 83%) is a conduit; its fee is per sale processed", "MERCHANDISE FEES")
lab("transfers_fees", J, "money passed between a party's accounts", "ALLOCABLE EXPENSES FROM NRCC ACCT")
lab("transfers_fees", J, "money given up to the Treasury, as a refund is", "DISGORGEMENT")

lab("other", C, "", "CREDIT CARD PAYMENT", "CREDIT CARD PAYMENT - SEE BELOW IF ITEMIZED",
    "CREDIT CARD PAYMENT: SEE ITEMIZATIONS IF REQUIRED", "CREDIT CARD - SEE BELOW IF ITEMIZED",
    "CREDIT CARD PAYMENT - SEE BELOW", "CREDIT CARD PAYMENT, SEE BELOW", group="credit_card")
lab("other", C, "", "DIRECT MAIL", "POSTAGE", "PRINTING", "DIRECT MAIL PRINTING & POSTAGE", "DIRECT MAIL SERVICES",
    "DIRECT MAIL PRODUCTION", "MAIL PRODUCTION SERVICES", "DIRECT MAIL POSTAGE", "GENERIC CMTE. POSTAGE/DELIVERY",
    "POSTAGE & SHIPPING", "PRINTING/POSTAGE", "DIRECT MAIL COSTS", "DIRECT MAIL PRINTING", "VOTER MAIL",
    "GENERIC CMTE. PRINTING", "DIRECT MAIL EXPENSE", group="mail")
lab("other", J, "printing is mail's (T6); copying could be an office's", "PRINTING & COPYING", group="mail")
lab("other", C, "", "POLLING", "SURVEY RESEARCH", "POLLING/FOCUS GROUPS", "POLLING EXPENSE",
    "POLLING SERVICES / CONSULTING", "GENERIC CMTE. POLLING", group="polling_research")
lab("other", J, "research unqualified is opposition or policy research (T7)", "RESEARCH", "RESEARCH SERVICES",
    group="polling_research")
lab("other", J, "T3: research consulting is research's; its largest payee (HaystackID) is an e-discovery firm",
    "RESEARCH CONSULTING", group="polling_research")
lab("other", C, "", "CANVASSING", "CANVASSING/FIELD OPERATIONS", "FIELD ORGANIZING", "CANVASSING SERVICES",
    "VOTER CANVASSING", "RELATIONAL ORGANIZING", group="field")
lab("other", J, "T3: voter registration consulting is field's", "VOTER REGISTRATION CONSULTING", group="field")
lab("other", J, "calls to voters are field's (T8); paid calls could be fundraising's", "PAID PHONE CALLS", group="field")
lab("other", C, "", "IN-KIND CONTRIBUTION", "24,999,995 USDC RECEIVED, NOT LIQUIDATED",
    "IN-KIND 236.20702457 BITCOINS NOT LIQUIDATED", "IN-KIND - 15,500,000 US DOLLAR COIN (USDC)", group="in_kind")
lab("other", J, "artworks given in kind (Q3's orphan children, '* IN-KIND RECEIVED')", "ARTWORK", group="in_kind")
lab("other", J, "names nothing bought; the rows are a filer's whole spending in four lines", "OPERATING EXPENDITURE",
    group="unnamed")
lab("other", J, "names nothing bought; the items are memo lines", "SEE MEMO ITEMS", "SEE MEMO", group="unnamed")

rows = list(csv.DictReader(open(sys.argv[1])))
missing = [r["purpose"] for r in rows if r["purpose"] not in L]
extra = set(L) - {r["purpose"] for r in rows}
assert not missing and not extra, (missing, extra)
total = sum(float(r["dollars"]) for r in rows)
groups = {}
for r in rows:
    cat, group, *_ = L[r["purpose"]]
    key = group if cat == "other" else cat
    groups[key] = groups.get(key, 0) + float(r["dollars"])
print("pass 1, labelled set", f"{total:,.0f}")
for k, v in sorted(groups.items(), key=lambda kv: -kv[1]):
    print(f"| {k} | {v:,.0f} | {v / total:.2%} |")
promoted = {g for g, v in groups.items() if g not in {"media", "digital", "fundraising", "payroll", "consulting",
            "travel", "events", "administrative", "legal_compliance", "transfers_fees"} and v / total >= 0.02}
print("promoted", sorted(promoted))
with open(sys.argv[2], "w", newline="") as out:
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["purpose", "rows", "dollars", "dollars_category_blank", "fec_category", "spending_category",
                "confidence", "reason"])
    for r in rows:
        cat, group, conf, reason = L[r["purpose"]]
        final = group if cat == "other" and group in promoted else cat
        w.writerow([r["purpose"], r["rows"], r["dollars"], r["dollars_category_blank"], r["fec_category"],
                    final, conf, reason])
```

Its first pass, over the labelled set's $7,456,498,116:

| Pass-1 category or `other` group | Dollars | Share |
| --- | --- | --- |
| media | 2,583,995,150 | 34.65% |
| fundraising | 914,578,367 | 12.27% |
| digital | 671,520,029 | 9.01% |
| payroll | 660,822,336 | 8.86% |
| mail | 551,243,911 | 7.39% |
| transfers_fees | 312,277,937 | 4.19% |
| legal_compliance | 287,963,796 | 3.86% |
| consulting | 198,250,854 | 2.66% |
| field | 195,607,598 | 2.62% |
| polling_research | 195,557,759 | 2.62% |
| credit_card | 177,218,981 | 2.38% |
| events | 173,599,476 | 2.33% |
| administrative | 157,863,519 | 2.12% |
| unnamed | 135,912,962 | 1.82% |
| in_kind | 123,082,549 | 1.65% |
| travel | 117,002,891 | 1.57% |

`mail`, `field`, `polling_research` and `credit_card` pass the bar and become categories. `in_kind`
(1.65%) and `unnamed` (1.82%, of which $119,980,010 is the one Norris row) stay `other`. 35 of the
200 labels are judgement calls. The four join the list with these definitions:

| Slug | Holds | FEC codes |
| --- | --- | --- |
| `mail` | Direct mail and printed material: its design, printing, postage and lettershop, whether it persuades voters or asks them for money | 006, 103 |
| `field` | Voter contact in person and by phone: canvassing, field and relational organizing, voter registration, paid calls to voters | 105 |
| `polling_research` | Polling, surveys and focus groups, and opposition and policy research | 005, 106 |
| `credit_card` | A card bill, counted as the bill: what it bought is itemized, if at all, only in memo lines Decision 1 does not count | — |

`credit_card` is a judgement call. It passes the bar as a coherent group, since every purpose in it
names a card payment. But it says where the money went (the card issuer), not what it bought, and
it exists only because Decision 1 counts the bill. NEU-2150 may fold it into `other` instead. The
CSV keeps it, so NEU-2153 can test either way.

```python
# The labelled set (tests/fixtures/spending/purpose_labels_2024.csv, copied into work).
con.execute(f"""CREATE TABLE label AS SELECT * FROM read_csv({literal(work / 'purpose_labels_2024.csv')},
    header = true, all_varchar = true)""")
# FEC's code to the final list, each code by FEC's description; a code written without its leading
# zeros ('1', '01') is read as the code it pads to, and any other ('21B', '212') maps to nothing.
con.execute("""CREATE TABLE code_map AS SELECT * FROM (VALUES
    ('001', 'administrative'), ('002', 'travel'), ('003', 'fundraising'), ('004', 'media'),
    ('005', 'polling_research'), ('006', 'mail'), ('007', 'events'), ('008', 'transfers_fees'),
    ('009', 'transfers_fees'), ('010', 'transfers_fees'), ('011', 'transfers_fees'), ('012', 'transfers_fees'),
    ('101', 'other'), ('102', 'media'), ('103', 'mail'), ('104', 'administrative'), ('105', 'field'),
    ('106', 'polling_research'), ('107', 'fundraising')) AS t(code, category)""")
show("Q8f. Dollars per category in the labelled set (final list)", """
SELECT spending_category, count(*) AS purposes, sum(dollars::DECIMAL(16, 2)) AS dollars,
    (sum(dollars::DECIMAL(16, 2)) / (SELECT sum(dollars::DECIMAL(16, 2)) FROM label))::DOUBLE AS share,
    count(*) FILTER (WHERE confidence = 'judgement') AS judgement_calls
FROM label GROUP BY ALL ORDER BY dollars DESC""")
show("Q8g. Label against FEC's code, counted rows of the labelled purposes with CATEGORY filled", """
SELECT fec_code(x.CATEGORY) AS code, m.category AS code_category,
    sum(x.amt) AS dollars, sum(x.amt) FILTER (WHERE l.spending_category = m.category) AS agreeing,
    (sum(x.amt) FILTER (WHERE l.spending_category = m.category) / sum(x.amt))::DOUBLE AS agree_share,
    arg_max(l.spending_category, x.amt) FILTER (WHERE l.spending_category IS DISTINCT FROM m.category) AS commonest_other_label
FROM cx AS x JOIN label AS l ON l.purpose = x.purp
LEFT JOIN code_map AS m ON m.code = fec_code(x.CATEGORY)
WHERE x.counted AND nullif(trim(x.CATEGORY), '') IS NOT NULL
GROUP BY ALL ORDER BY dollars DESC""")
show("Q8h. Label against FEC's code: the labels code 001 and 101 rows carry", """
SELECT fec_code(x.CATEGORY) AS code, l.spending_category, sum(x.amt) AS dollars, count(*) AS rows
FROM cx AS x JOIN label AS l ON l.purpose = x.purp
WHERE x.counted AND fec_code(x.CATEGORY) IN ('001', '101')
GROUP BY ALL ORDER BY code, dollars DESC""")
show("Q8i. Every counted dollar by its code's category, where CATEGORY is filled", """
SELECT coalesce(m.category, 'unmapped: ' || fec_code(x.CATEGORY)) AS category, sum(x.amt) AS dollars, count(*) AS rows
FROM cx AS x LEFT JOIN code_map AS m ON m.code = fec_code(x.CATEGORY)
WHERE x.counted AND nullif(trim(x.CATEGORY), '') IS NOT NULL GROUP BY ALL ORDER BY dollars DESC""")
```

**Q8f. Dollars per category in the labelled set (final list)  (0 s)**

| spending_category | purposes | dollars | share | judgement_calls |
|---|---|---|---|---|
| media | 29 | 2,583,995,150 | 34.65% | 3 |
| fundraising | 24 | 914,578,367 | 12.27% | 7 |
| digital | 24 | 671,520,029 | 9.01% | 4 |
| payroll | 15 | 660,822,336 | 8.86% | 2 |
| mail | 17 | 551,243,911 | 7.39% | 1 |
| transfers_fees | 18 | 312,277,937 | 4.19% | 4 |
| legal_compliance | 7 | 287,963,796 | 3.86% | 1 |
| other | 8 | 258,995,512 | 3.47% | 4 |
| consulting | 10 | 198,250,854 | 2.66% | 0 |
| field | 8 | 195,607,598 | 2.62% | 2 |
| polling_research | 9 | 195,557,759 | 2.62% | 3 |
| credit_card | 6 | 177,218,981 | 2.38% | 0 |
| events | 13 | 173,599,476 | 2.33% | 1 |
| administrative | 8 | 157,863,519 | 2.12% | 3 |
| travel | 4 | 117,002,891 | 1.57% | 0 |

**Q8g. Label against FEC's code, counted rows of the labelled purposes with CATEGORY filled  (0 s)**

| code | code_category | dollars | agreeing | agree_share | commonest_other_label |
|---|---|---|---|---|---|
| 001 | administrative | 511,096,243 | 18,269,743 | 3.57% | other |
| 004 | media | 162,324,768 | 137,949,736 | 84.98% | digital |
| 101 | other | 121,923,171 | 119,980,010 | 98.41% | legal_compliance |
| 003 | fundraising | 107,598,706 | 69,489,419 | 64.58% | mail |
| 005 | polling_research | 20,622,232 | 20,514,917 | 99.48% | fundraising |
| 002 | travel | 6,703,824 | 5,975,525 | 89.14% | other |
| 102 | media | 3,514,849 | 3,418,882 | 97.27% | fundraising |
| 107 | fundraising | 2,412,748 | 400,089 | 16.58% | field |
| 006 | mail | 2,203,754 | 1,651,776 | 74.95% | fundraising |
| 011 | transfers_fees | 1,832,220 | 1,755,492 | 95.81% | credit_card |
| 104 | administrative | 1,484,941 | 101,311 | 6.82% | consulting |
| 007 | events | 760,900 | 393,741 | 51.75% | digital |
| 106 | polling_research | 91,825 | 91,825 | 100.00% |  |
| 012 | transfers_fees | 27,553 | 23,015 | 83.53% | media |
| 105 | field | 5,509 |  |  | digital |
| 009 | transfers_fees | 3,221 |  |  | credit_card |
| 010 | transfers_fees | 3,023 | 3,023 | 100.00% |  |
| 103 | mail | 1,395 |  |  | digital |
| 216 |  | 270 |  |  | transfers_fees |
| 21B |  | 158 |  |  | transfers_fees |

**Q8h. Label against FEC's code: the labels code 001 and 101 rows carry  (0 s)**

| code | spending_category | dollars | rows |
|---|---|---|---|
| 001 | payroll | 121,113,387 | 36,237 |
| 001 | media | 65,843,288 | 2,079 |
| 001 | other | 58,551,802 | 2,330 |
| 001 | digital | 48,809,314 | 4,108 |
| 001 | mail | 48,612,690 | 8,971 |
| 001 | fundraising | 40,964,899 | 4,769 |
| 001 | consulting | 36,957,030 | 6,520 |
| 001 | legal_compliance | 28,148,144 | 10,370 |
| 001 | transfers_fees | 20,226,696 | 55,487 |
| 001 | administrative | 18,269,743 | 7,204 |
| 001 | credit_card | 11,948,619 | 2,120 |
| 001 | polling_research | 8,296,259 | 888 |
| 001 | travel | 1,564,610 | 4,079 |
| 001 | field | 1,363,741 | 507 |
| 001 | events | 426,023 | 312 |
| 101 | other | 119,980,010 | 1 |
| 101 | legal_compliance | 551,146 | 73 |
| 101 | consulting | 350,518 | 87 |
| 101 | credit_card | 274,046 | 27 |
| 101 | media | 234,685 | 228 |
| 101 | payroll | 153,026 | 15 |
| 101 | events | 76,506 | 4 |
| 101 | administrative | 74,226 | 34 |
| 101 | digital | 72,570 | 25 |
| 101 | fundraising | 52,908 | 18 |
| 101 | travel | 47,890 | 107 |
| 101 | mail | 33,065 | 202 |
| 101 | polling_research | 8,500 | 1 |
| 101 | field | 8,250 | 1 |
| 101 | transfers_fees | 5,825 | 56 |

**Q8i. Every counted dollar by its code's category, where CATEGORY is filled  (0 s)**

| category | dollars | rows |
|---|---|---|
| administrative | 865,512,257 | 322,572 |
| media | 264,676,535 | 18,941 |
| fundraising | 225,584,678 | 61,495 |
| other | 129,547,719 | 7,142 |
| polling_research | 26,492,952 | 1,537 |
| travel | 23,100,631 | 22,629 |
| mail | 17,944,396 | 6,201 |
| events | 10,847,419 | 5,589 |
| transfers_fees | 9,662,507 | 2,451 |
| field | 388,617 | 34 |
| unmapped: 216 | 2,908 | 13 |
| unmapped: 21B | 770 | 6 |
| unmapped: 212 | 26 | 1 |

Where FEC's code is filled on a labelled purpose, the label agrees with code 004 (media) on 84.98%
of its dollars, 005 (polling) on 99.48%, 002 (travel) on 89.14% and 102 (presidential media) on
97.27%. It agrees with **001 on 3.57%**. Filers write 001, "administrative/salary/overhead", on
payroll ($121.1M), media ($65.8M), digital, mail, fundraising, consulting and legal work alike
(Q8h). 003 agrees on 64.58% (mail and digital fundraising sit under it), and 107 and 104 barely at
all. So the contract's "FEC's `CATEGORY` when filled" holds for 002, 004, 005, 011, 102 and 106,
and reading 001 as `administrative` would misfile most of its dollars.

## Q9: payees (2024)

```python
# organization_key once per distinct name, joined back (the shape NEU-2152 builds).
con.execute("""CREATE TABLE payee_name AS
    SELECT NAME, organization_key(NAME) AS payee_key, normalize_employer(NAME) IS NULL AS fell_back
    FROM (SELECT DISTINCT NAME FROM ox)""")
con.execute("""CREATE VIEW px AS SELECT x.*, n.payee_key, n.fell_back
    FROM cx AS x LEFT JOIN payee_name AS n ON n.NAME IS NOT DISTINCT FROM x.NAME""")
```

```python
show("Q9a. Payee keys over counted rows", """
WITH k AS (SELECT payee_key, sum(amt) AS d, count(DISTINCT NAME) AS spellings FROM px WHERE counted GROUP BY ALL),
r AS (SELECT *, row_number() OVER (ORDER BY d DESC) AS n FROM k WHERE payee_key IS NOT NULL)
SELECT count(*) AS keys, (SELECT count(DISTINCT NAME) FROM px WHERE counted) AS raw_names,
    avg(spellings) AS spellings_per_key, max(spellings) AS most_spellings,
    count(*) FILTER (WHERE spellings > 1) AS keys_with_2_or_more,
    (sum(d) FILTER (WHERE n <= 100) / (SELECT sum(amt) FROM px WHERE counted))::DOUBLE AS top_100_share,
    (sum(d) FILTER (WHERE n <= 1000) / (SELECT sum(amt) FROM px WHERE counted))::DOUBLE AS top_1000_share,
    (SELECT sum(amt) FROM px WHERE counted AND payee_key IS NULL) AS no_key_dollars
FROM r""")
show("Q9b. The top 100 payee keys by counted dollars, with up to ten spellings each", """
WITH s AS (SELECT payee_key, NAME, sum(amt) AS d FROM px WHERE counted GROUP BY payee_key, NAME),
top AS (SELECT payee_key, sum(amt) AS dollars, count(*) AS rows, count(DISTINCT CMTE_ID) AS committees,
               count(DISTINCT STATE) AS states, count(DISTINCT NAME) AS spellings
        FROM px WHERE counted AND payee_key IS NOT NULL GROUP BY payee_key ORDER BY dollars DESC LIMIT 100)
SELECT row_number() OVER (ORDER BY top.dollars DESC) AS n, top.*,
    (SELECT string_agg(NAME, '; ' ORDER BY d DESC) FROM (SELECT NAME, d FROM s WHERE s.payee_key = top.payee_key
        ORDER BY d DESC LIMIT 10)) AS largest_spellings
FROM top ORDER BY dollars DESC""")
show("Q9c. Names normalize_employer reads as no employer (the cleaned-name fallback), and blank names, counted rows", """
SELECT NAME IS NULL AS blank_name, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT NAME) AS names
FROM px WHERE counted AND fell_back GROUP BY ALL ORDER BY ALL""")
show("Q9e. Keys that name no payee (stoplist candidates), counted rows", """
SELECT payee_key, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT CMTE_ID) AS committees
FROM px WHERE counted AND regexp_matches(coalesce(payee_key, ''),
    '^(.*\\bVARIOUS\\b.*|UNITEMIZED.*|.*\\bSEE (BELOW|MEMO|ATTACHED|SCHEDULE)\\b.*|MEMO( .*)?|CASH|PETTY CASH|CASH WITHDRAWA?L|ATM|ATM WITHDRAWA?L|NONE|N ?A|PAYROLL|STAFF|EMPLOYEES?|VENDORS?|MULTIPLE( VENDORS?)?|CREDIT CARD|UNKNOWN|TBD|BANK|NOT ITEMIZED)$')
GROUP BY ALL ORDER BY dollars DESC LIMIT 30""")
show("Q9f. Payees that are people: counted rows by ENTITY_TP", """
SELECT ENTITY_TP, count(*) AS rows, sum(amt) AS dollars, count(DISTINCT payee_key) AS keys
FROM px WHERE counted GROUP BY ALL ORDER BY dollars DESC""")
show("Q9g. IND keys spanning more than one state (a floor on people merged under one key)", """
WITH k AS (SELECT payee_key, count(DISTINCT STATE) AS states, sum(amt) AS d
           FROM px WHERE counted AND ENTITY_TP = 'IND' GROUP BY ALL)
SELECT count(*) AS ind_keys, count(*) FILTER (WHERE states > 1) AS over_one_state,
    sum(d) FILTER (WHERE states > 1) AS their_dollars, max(states) AS most_states,
    arg_max(payee_key, states) AS key_with_most_states
FROM k""")
```

**Q9a. Payee keys over counted rows  (0 s)**

| keys | raw_names | spellings_per_key | most_spellings | keys_with_2_or_more | top_100_share | top_1000_share | no_key_dollars |
|---|---|---|---|---|---|---|---|
| 98,975 | 105,313 | 106.40% | 15 | 4,395 | 52.37% | 80.26% | 34,042 |

**Q9b. The top 100 payee keys by counted dollars, with up to ten spellings each  (1 s)**

| n | payee_key | dollars | rows | committees | states | spellings | largest_spellings |
|---|---|---|---|---|---|---|---|
| 1 | MEDIA BUYING ANALYTICS | 333,818,262 | 62 | 2 | 1 | 1 | MEDIA BUYING & ANALYTICS LLC |
| 2 | STRATEGIC MEDIA SERVICES | 287,206,938 | 150 | 24 | 1 | 4 | STRATEGIC MEDIA SERVICES, INC.; STRATEGIC MEDIA SERVICES INC.; STRATEGIC MEDIA SERVICES; STRATEGIC MEDIA SERVICES INC |
| 3 | AMERICAN EXPRESS | 195,178,900 | 13,039 | 632 | 12 | 5 | AMERICAN EXPRESS; AMERICAN EXPRESS*; AMERICAN EXPRESS CO; AMERICAN EXPRESS COMPANY; AMERICAN EXPRESS CORP |
| 4 | GAMBIT STRATEGIES | 176,096,372 | 276 | 14 | 2 | 3 | GAMBIT STRATEGIES LLC; GAMBIT STRATEGIES; GAMBIT STRATEGIES, LLC |
| 5 | SCREEN STRATEGIES MEDIA | 142,665,313 | 385 | 32 | 1 | 3 | SCREEN STRATEGIES MEDIA; SCREEN STRATEGIES MEDIA, LLC; SCREEN STRATEGIES MEDIA LLC |
| 6 | GRASSROOTS MEDIA | 135,292,306 | 197 | 9 | 1 | 3 | GRASSROOTS MEDIA; GRASSROOTS MEDIA LLC; GRASSROOTS MEDIA, LLC |
| 7 | ACTBLUE TECHNICAL SERVICES | 125,663,546 | 90,806 | 1,462 | 7 | 8 | ACTBLUE TECHNICAL SERVICES; ACTBLUE TECHNICAL SERVICES, INC.; ACTBLUE TECHNICAL SERVICES INC; ACTBLUE TECHNICAL SERVICES LLC; ACTBLUE TECHNICAL SERVICES, INC; ACTBLUE TECHNICAL SERVICES INC.; ACTBLUE, TECHNICAL SERVICES;  ACTBLUE TECHNICAL SERVICES |
| 8 | TARGETED VICTORY | 123,331,228 | 1,745 | 126 | 1 | 3 | TARGETED VICTORY; TARGETED VICTORY LLC; TARGETED VICTORY, LLC |
| 9 | DUPONT CIRCLE STRATEGIES | 122,572,809 | 115 | 2 | 1 | 1 | DUPONT CIRCLE STRATEGIES LLC |
| 10 | JIM A NORRIS FOR THE UNITED STATES PRESIDENT | 121,230,010 | 4 | 1 | 1 | 1 | JIM A NORRIS FOR THE UNITED STATES PRESIDENT |
| 11 | BULLY PULPIT INTERACTIVE | 114,738,023 | 107 | 5 | 1 | 3 | BULLY PULPIT INTERACTIVE LLC; BULLY PULPIT INTERACTIVE; BULLY PULPIT INTERACTIVE, LLC |
| 12 | GUSTO | 113,091,764 | 18,902 | 286 | 6 | 6 | GUSTO; GUSTO INC.; GUSTO INC; GUSTO, INC.; GUSTO LLC; GUSTO, LLC |
| 13 | META | 106,970,861 | 9,726 | 361 | 7 | 14 | META PLATFORMS, INC.; FACEBOOK; META PLATFORMS INC; META; FACEBOOK, INC.; META PLATFORMS; META, INC.; META PLATFORMS INC.; META PLATFORMS, INC; FACEBOOK INC. |
| 14 | WINRED TECHNICAL SERVICES | 97,186,075 | 54,100 | 720 | 5 | 5 | WINRED TECHNICAL SERVICES LLC; WINRED TECHNICAL SERVICES, LLC; WINRED TECHNICAL SERVICES; WINRED TECHNICAL SERVICES INC; WINRED TECHNICAL SERVICES INC. |
| 15 | AL MEDIA | 93,347,128 | 383 | 21 | 2 | 3 | AL MEDIA; AL MEDIA, LLC; AL MEDIA LLC |
| 16 | GOOGLE | 87,998,226 | 11,327 | 673 | 7 | 8 | GOOGLE LLC; GOOGLE; GOOGLE, INC.; GOOGLE INC.; GOOGLE INC; GOOGLE, INC; GOOGLE.; GOOGLE, LLC |
| 17 | ONMESSAGE | 85,361,173 | 1,207 | 54 | 2 | 5 | ONMESSAGE INC; ONMESSAGE INC.; ONMESSAGE, INC.; ONMESSAGE, INC; ONMESSAGE |
| 18 | MOTHERSHIP STRATEGIES | 83,118,845 | 1,821 | 45 | 1 | 2 | MOTHERSHIP STRATEGIES; MOTHERSHIP STRATEGIES, LLC |
| 19 | LAUNCHPAD STRATEGIES | 79,588,078 | 615 | 6 | 1 | 2 | LAUNCHPAD STRATEGIES, LLC; LAUNCHPAD STRATEGIES LLC |
| 20 | MISSIONWIRED | 72,027,073 | 683 | 19 | 1 | 1 | MISSIONWIRED |
| 21 | FLEXPOINT MEDIA | 70,802,018 | 253 | 28 | 2 | 4 | FLEXPOINT MEDIA INC.; FLEXPOINT MEDIA INC; FLEXPOINT MEDIA, INC.; FLEXPOINT MEDIA |
| 22 | CANAL PARTNERS MEDIA | 68,357,560 | 200 | 21 | 3 | 3 | CANAL PARTNERS MEDIA; CANAL PARTNERS MEDIA LLC; CANAL PARTNERS MEDIA, LLC |
| 23 | COINBASE | 63,516,265 | 16 | 7 | 2 | 3 | COINBASE; COINBASE INC; COINBASE, INC. |
| 24 | RWT PRODUCTION | 60,027,535 | 1,565 | 79 | 1 | 4 | RWT PRODUCTION, LLC; RWT PRODUCTION LLC; RWT PRODUCTION; RWT PRODUCTION, LLC. |
| 25 | GMMB | 57,268,950 | 258 | 25 | 2 | 4 | GMMB; GMMB INC.; GMMB INC; GMMB, INC. |
| 26 | GEN2 SOLUTIONS | 57,056,291 | 338 | 29 | 1 | 3 | GEN2 SOLUTIONS LLC; GEN2 SOLUTIONS, LLC; GEN2 SOLUTIONS |
| 27 | BUYING TIME | 54,029,633 | 242 | 25 | 2 | 3 | BUYING TIME LLC; BUYING TIME, LLC; BUYING TIME |
| 28 | UNITED STATES OF AMERICA | 52,008,951 | 7 | 1 | 1 | 1 | UNITED STATES OF AMERICA INC |
| 29 | SKDKNICKERBOCKER | 51,394,682 | 233 | 21 | 2 | 3 | SKDKNICKERBOCKER LLC; SKDKNICKERBOCKER; SKDKNICKERBOCKER, LLC |
| 30 | RED BEACON STRATEGIES | 51,275,409 | 379 | 30 | 1 | 3 | RED BEACON STRATEGIES, LLC; RED BEACON STRATEGIES; RED BEACON STRATEGIES LLC |
| 31 | AISLE 518 STRATEGIES | 49,897,176 | 867 | 24 | 3 | 3 | AISLE 518 STRATEGIES LLC; AISLE 518 STRATEGIES, LLC; AISLE 518 STRATEGIES |
| 32 | STRATEGIC MEDIA PLACEMENT | 48,972,653 | 323 | 49 | 1 | 5 | STRATEGIC MEDIA PLACEMENT INC; STRATEGIC MEDIA PLACEMENT; STRATEGIC MEDIA PLACEMENT INC.; STRATEGIC MEDIA PLACEMENT, INC.; STRATEGIC MEDIA PLACEMENT, INC |
| 33 | EVENT STRATEGIES | 47,814,851 | 192 | 10 | 1 | 4 | EVENT STRATEGIES, INC.; EVENT STRATEGIES; EVENT STRATEGIES INC; EVENT STRATEGIES, INC |
| 34 | SCALE TO WIN | 46,288,901 | 1,162 | 201 | 5 | 3 | SCALE TO WIN; SCALE TO WIN, LLC; SCALE TO WIN LLC |
| 35 | DNC SERVICES CORP DEM NATL COMMITTEE | 45,444,863 | 153 | 9 | 1 | 1 | DNC SERVICES CORP./DEM. NAT'L COMMITTEE |
| 36 | AX MEDIA | 44,091,636 | 89 | 15 | 2 | 2 | AX MEDIA LLC; AX MEDIA |
| 37 | CONEXION | 38,587,713 | 69 | 4 | 1 | 2 | CONEXION INC; CONEXION INC. |
| 38 | THEMATIC CAMPAIGNS | 38,086,357 | 162 | 13 | 1 | 3 | THEMATIC CAMPAIGNS; THEMATIC CAMPAIGNS LLC; THEMATIC CAMPAIGNS, LLC |
| 39 | PAYROLL DATA PROCESSING | 37,377,571 | 5,901 | 90 | 1 | 4 | PAYROLL DATA PROCESSING; PAYROLL DATA PROCESSING INC.; PAYROLL DATA PROCESSING, INC.; PAYROLL DATA PROCESSING INC |
| 40 | TAG | 36,778,767 | 1,330 | 79 | 1 | 4 | TAG LLC; TAG, LLC; TAG  LLC; TAG |
| 41 | AUTHENTIC CAMPAIGNS | 36,339,123 | 836 | 43 | 3 | 5 | AUTHENTIC CAMPAIGNS, INC.; AUTHENTIC CAMPAIGNS; AUTHENTIC CAMPAIGNS INC.; AUTHENTIC CAMPAIGNS, INC; AUTHENTIC CAMPAIGNS INC |
| 42 | RED CURVE SOLUTIONS | 36,130,023 | 1,700 | 118 | 1 | 3 | RED CURVE SOLUTIONS; RED CURVE SOLUTIONS, LLC; RED CURVE SOLUTIONS LLC |
| 43 | AMERICAN MEDIA ADVOCACY GROUP | 34,926,849 | 161 | 14 | 2 | 2 | AMERICAN MEDIA & ADVOCACY GROUP; AMERICAN MEDIA & ADVOCACY GROUP LLC |
| 44 | MIDDLE SEAT | 34,768,131 | 784 | 32 | 2 | 1 | MIDDLE SEAT |
| 45 | NGP VAN | 34,480,759 | 11,558 | 1,177 | 6 | 12 | NGP VAN, INC.; NGP VAN; NGP VAN INC.; NGP VAN INC; NGP VAN, INC; NGP-VAN; NGP-VAN INC.; NGP VAN , INC.; NGP/VAN; NGP VAN. INC. |
| 46 | PAYCHEX | 34,227,912 | 9,278 | 175 | 26 | 5 | PAYCHEX; PAYCHEX, INC.; PAYCHEX, INC; PAYCHEX INC.; PAYCHEX INC |
| 47 | ADP | 33,169,717 | 8,857 | 135 | 22 | 7 | ADP, INC.; ADP; ADP INC.; ADP INC; ADP, INC; ADP, LLC; ADP INCORPORATED |
| 48 | LEFT HOOK | 32,869,817 | 203 | 17 | 1 | 2 | LEFT HOOK; LEFT HOOK LLC |
| 49 | BUMPERACTIVE | 31,548,063 | 1,056 | 69 | 1 | 1 | BUMPERACTIVE |
| 50 | WAVELENGTH STRATEGY | 31,532,421 | 219 | 21 | 2 | 5 | WAVELENGTH STRATEGY LLC; WAVELENGTH STRATEGY INC.; WAVELENGTH STRATEGY, LLC; WAVELENGTH STRATEGY INC; WAVELENGTH STRATEGY |
| 51 | DNC TRAVEL ESCROW | 31,294,206 | 605 | 8 | 1 | 1 | DNC TRAVEL ESCROW |
| 52 | MOVEONORG CIVIC ACTION | 31,008,085 | 30 | 1 | 2 | 1 | MOVEON.ORG CIVIC ACTION |
| 53 | INSPERITY | 30,533,721 | 720 | 18 | 3 | 1 | INSPERITY |
| 54 | TRUXTON CREATIVE | 30,505,936 | 40 | 2 | 1 | 2 | TRUXTON CREATIVE LLC; TRUXTON CREATIVE, LLC |
| 55 | GPS IMPACT | 29,484,870 | 519 | 37 | 1 | 1 | GPS IMPACT |
| 56 | OTG STRATEGIES | 29,442,370 | 98 | 7 | 2 | 2 | OTG STRATEGIES LLC; OTG STRATEGIES |
| 57 | TEAM DIRECT | 27,935,812 | 208 | 9 | 1 | 2 | TEAM DIRECT LLC; TEAM DIRECT |
| 58 | MESSAGE DIGITAL | 26,838,923 | 359 | 29 | 1 | 3 | MESSAGE DIGITAL; MESSAGE DIGITAL LLC; MESSAGE DIGITAL, LLC |
| 59 | PATRIOT GRASSROOTS | 26,801,815 | 25 | 7 | 2 | 3 | PATRIOT GRASSROOTS; PATRIOT GRASSROOTS LLC; PATRIOT GRASSROOTS, LLC |
| 60 | SHAWMUT SERVICES | 26,671,186 | 47 | 6 | 1 | 2 | SHAWMUT SERVICES LLC; SHAWMUT SERVICES |
| 61 | FULFILLMENT SOLUTIONS | 25,259,583 | 2,999 | 93 | 2 | 5 | FULFILLMENT SOLUTIONS INC.; FULFILLMENT SOLUTIONS INC; FULFILLMENT SOLUTIONS; FULFILLMENT SOLUTIONS, INC.; FULFILLMENT SOLUTIONS, INC |
| 62 | ACE SPECIALTIES | 22,885,549 | 913 | 44 | 2 | 3 | ACE SPECIALTIES, LLC; ACE SPECIALTIES LLC; ACE SPECIALTIES |
| 63 | ANNE LEWIS STRATEGIES | 22,834,693 | 492 | 28 | 4 | 3 | ANNE LEWIS STRATEGIES; ANNE LEWIS STRATEGIES LLC; ANNE LEWIS STRATEGIES, LLC |
| 64 | ACTION NETWORK | 22,728,800 | 585 | 52 | 6 | 1 | ACTION NETWORK |
| 65 | DIRECTSND | 22,595,983 | 170 | 11 | 1 | 2 | DIRECTSND, LLC; DIRECTSND LLC |
| 66 | MEETING STREET SERVICES | 22,503,538 | 191 | 4 | 1 | 1 | MEETING STREET SERVICES LLC |
| 67 | INTERNAL REVENUE SERVICE | 22,350,334 | 1,669 | 267 | 17 | 1 | INTERNAL REVENUE SERVICE |
| 68 | PUSH DIGITAL | 22,143,466 | 615 | 46 | 1 | 3 | PUSH DIGITAL LLC; PUSH DIGITAL, LLC; PUSH DIGITAL |
| 69 | SMART MEDIA GROUP | 21,697,604 | 183 | 21 | 2 | 3 | SMART MEDIA GROUP LLC; SMART MEDIA GROUP, LLC; SMART MEDIA GROUP |
| 70 | SAPPHIRE STRATEGIES | 21,040,008 | 755 | 29 | 3 | 3 | SAPPHIRE STRATEGIES; SAPPHIRE STRATEGIES LLC; SAPPHIRE STRATEGIES, LLC. |
| 71 | PAYLOCITY | 21,036,826 | 1,574 | 6 | 1 | 2 | PAYLOCITY; PAYLOCITY CORPORATION |
| 72 | PACTION DATA | 21,013,561 | 166 | 26 | 2 | 5 | PACTION DATA INC.; PACTION DATA, INC.; PACTION DATA INC; PACTION DATA, INC; PACTION DATA |
| 73 | ULTIPRO | 20,349,180 | 176 | 2 | 1 | 1 | ULTIPRO |
| 74 | TEAMDIRECT | 20,030,740 | 118 | 2 | 1 | 2 | TEAMDIRECT; TEAMDIRECT LLC |
| 75 | M2 PLACEMENT | 18,977,211 | 102 | 10 | 2 | 2 | M2 PLACEMENT; M2 PLACEMENT LLC |
| 76 | STRATEGIC ADVANCE SERVICES | 18,900,259 | 268 | 26 | 2 | 3 | STRATEGIC ADVANCE SERVICES; STRATEGIC ADVANCE SERVICES LLC; STRATEGIC ADVANCE SERVICES, LLC |
| 77 | AXMEDIA | 18,873,547 | 103 | 13 | 1 | 2 | AXMEDIA; AXMEDIA LLC |
| 78 | ANNE LEWIS STRATEGIES LLC DBA MISSIONWIRED | 18,741,217 | 83 | 2 | 1 | 1 | ANNE LEWIS STRATEGIES, LLC DBA MISSIONWIRED |
| 79 | BARREL PLACEMENTS | 18,629,595 | 149 | 15 | 1 | 1 | BARREL PLACEMENTS |
| 80 | TECHNICOLOR POLITICAL | 18,421,949 | 142 | 18 | 2 | 3 | TECHNICOLOR POLITICAL; TECHNICOLOR POLITICAL LLC; TECHNICOLOR POLITICAL, LLC |
| 81 | CAMPAIGN INBOX | 18,049,588 | 788 | 24 | 3 | 3 | CAMPAIGN INBOX; CAMPAIGN INBOX, LLC; CAMPAIGN INBOX LLC |
| 82 | RISING TIDE INTERACTIVE | 17,625,311 | 180 | 17 | 1 | 2 | RISING TIDE INTERACTIVE; RISING TIDE INTERACTIVE, LLC |
| 83 | SWITCHBOARD PUBLIC BENEFIT | 17,497,230 | 1,591 | 185 | 5 | 5 | SWITCHBOARD PUBLIC BENEFIT CORP.; SWITCHBOARD PUBLIC BENEFIT CORP; SWITCHBOARD PUBLIC BENEFIT CORPORATION; SWITCHBOARD PUBLIC BENEFIT; SWITCHBOARD PUBLIC BENEFIT COMPANY |
| 84 | GRASSROOTS ANALYTICS | 17,277,958 | 1,599 | 196 | 4 | 7 | GRASSROOTS ANALYTICS; GRASSROOTS ANALYTICS, LLC; GRASSROOTS ANALYTICS, INC.; GRASSROOTS ANALYTICS INC; GRASSROOTS ANALYTICS LLC; GRASSROOTS ANALYTICS INC.; GRASSROOTS ANALYTICS, INC |
| 85 | NEXUS DIRECT | 17,072,396 | 50 | 1 | 1 | 1 | NEXUS DIRECT |
| 86 | UKG | 17,064,262 | 292 | 3 | 2 | 3 | UKG INC.; UKG INC; UKG |
| 87 | AIR PARTNER | 16,723,720 | 28 | 4 | 2 | 2 | AIR PARTNER LLC; AIR PARTNER |
| 88 | THE LUKENS | 16,186,148 | 484 | 41 | 2 | 3 | THE LUKENS COMPANY; THE LUKENS COMPANY INC; THE LUKENS CO |
| 89 | CONVERT DIGITAL | 16,130,968 | 482 | 29 | 2 | 3 | CONVERT DIGITAL LLC; CONVERT DIGITAL; CONVERT DIGITAL, LLC |
| 90 | FABRIZIO LEE ASSOCIATES | 15,962,050 | 87 | 14 | 1 | 5 | FABRIZIO, LEE & ASSOCIATES, LLC; FABRIZIO LEE & ASSOCIATES LLC; FABRIZIO LEE & ASSOCIATES; FABRIZIO  LEE & ASSOCIATES LLC; FABRIZIO LEE & ASSOCIATES, LLC |
| 91 | TMA DIRECT | 15,893,403 | 2,706 | 84 | 2 | 7 | TMA DIRECT; TMA DIRECT, INC.; TMA DIRECT INC; TMA DIRECT INC.; TMA DIRECT LLC; TMA DIRECT, INC; TMA DIRECT, LLC |
| 92 | ASSEMBLY HOUSE | 15,851,549 | 149 | 5 | 2 | 2 | ASSEMBLY HOUSE LLC; ASSEMBLY HOUSE |
| 93 | HARRIS FOR PRESIDENT | 15,767,951 | 14 | 7 | 1 | 1 | HARRIS FOR PRESIDENT |
| 94 | FRONTLINE STRATEGIES | 15,663,965 | 1,828 | 70 | 7 | 4 | FRONTLINE STRATEGIES LLC; FRONTLINE STRATEGIES  LLC; FRONTLINE STRATEGIES; FRONTLINE STRATEGIES, LLC |
| 95 | VENTURA MEDIA PARTNERS | 15,375,989 | 13 | 1 | 1 | 1 | VENTURA MEDIA PARTNERS |
| 96 | LIFTOFF CAMPAIGNS | 15,070,487 | 484 | 37 | 2 | 3 | LIFTOFF CAMPAIGNS; LIFTOFF CAMPAIGNS LLC; LIFTOFF CAMPAIGNS, LLC |
| 97 | BLITZ CANVASSING | 14,773,191 | 33 | 4 | 1 | 2 | BLITZ CANVASSING; BLITZ CANVASSING LLC |
| 98 | CMDI | 14,756,677 | 6,561 | 351 | 1 | 2 | CMDI; CMDI INC |
| 99 | DONALD J TRUMP FOR PRESIDENT 2024 | 14,411,699 | 42 | 2 | 1 | 1 | DONALD J. TRUMP FOR PRESIDENT 2024, INC. |
| 100 | TATANGO | 14,169,772 | 2,087 | 65 | 1 | 5 | TATANGO, INC.; TATANGO INC.; TATANGO; TATANGO, INC; TATANGO INC |

**Q9c. Names normalize_employer reads as no employer (the cleaned-name fallback), and blank names, counted rows  (0 s)**

| blank_name | rows | dollars | names |
|---|---|---|---|
| True | 91 | 34,042 | 0 |

**Q9e. Keys that name no payee (stoplist candidates), counted rows  (0 s)**

| payee_key | rows | dollars | committees |
|---|---|---|---|
| UNITEMIZED UNITEMIZED | 38 | 103,578 | 7 |
| UNITEMIZED PREVIOUS PERIOD | 1 | 56,467 | 1 |
| PAYROLL | 94 | 53,311 | 1 |
| PETTY CASH | 85 | 39,487 | 19 |
| UNITEMIZED RECIEPTS UNITEMIZED RECIEPTS | 1 | 5,000 | 1 |
| UNITEMIZED INDIVIDUALS VARIOUS INDIVIDUALS | 1 | 2,687 | 1 |
| VARIOUS PRESSURES | 1 | 2,572 | 1 |
| UNITEMIZED | 2 | 2,553 | 2 |
| UNITEMIZED TOTAL | 1 | 1,218 | 1 |
| CASH WITHDRAWAL | 8 | 808 | 2 |
| ATM WITHDRAWL | 2 | 504 | 1 |
| GENERAL CAMPAIGN COSTS INCURRED VARIOUS VENDORS | 1 | 400 | 1 |
| UNITEMIZED CASH | 1 | 300 | 1 |
| CASH | 4 | 180 | 1 |
| ATM | 1 | 104 | 1 |
| UNITEMIZED DISBURSEMENTS | 1 | 52 | 1 |

**Q9f. Payees that are people: counted rows by ENTITY_TP  (0 s)**

| ENTITY_TP | rows | dollars | keys |
|---|---|---|---|
| ORG | 1,222,973 | 8,840,320,536 | 57,682 |
| IND | 277,547 | 547,257,955 | 37,072 |
| CCM | 3,081 | 167,230,883 | 757 |
| PTY | 4,491 | 90,382,505 | 527 |
| PAC | 23,958 | 28,661,602 | 860 |
| CAN | 10,914 | 20,789,686 | 1,127 |
| COM | 4,832 | 19,533,379 | 1,267 |
|  | 2,434 | 1,338,057 | 924 |

**Q9g. IND keys spanning more than one state (a floor on people merged under one key)  (0 s)**

| ind_keys | over_one_state | their_dollars | most_states | key_with_most_states |
|---|---|---|---|---|
| 37,072 | 1,380 | 67,330,632 | 5 | JOHNSON ROBERT |

Payee keys barely merge: 105,313 raw names become 98,975 keys, and 4,395 keys have two spellings or
more (`META` has 14, Facebook's among them by alias). Every named payee has a key from
`normalize_employer` itself. The cleaned-name fallback is taken only by the 91 rows ($34,042) with
no name at all, which have no key.

Read by eye, the top 100 hold **no wrong merge**: no key holds two payees. They hold **three split
payees**: `AX MEDIA` (36) and `AXMEDIA` (77); `TEAM DIRECT` (57) and `TEAMDIRECT` (74); and
`MISSIONWIRED` (20), `ANNE LEWIS STRATEGIES` (63) and `ANNE LEWIS STRATEGIES LLC DBA MISSIONWIRED`
(78), one firm. Four of the 100 are committees (DNC Services, MoveOn.org Civic Action, Harris for
President, Donald J. Trump for President 2024), and two are one payer's each:
`JIM A NORRIS FOR THE UNITED STATES PRESIDENT` ($121.2M in four rows paid to itself, by a filer
`cm` does not hold) and `UNITED STATES OF AMERICA` ($52.0M, seven `IN-KIND CONTRIBUTION` rows on
two filings of the super PAC C00879510). `AMERICAN EXPRESS` (3, $195.2M) is a card
issuer, the payee that names nobody under parent always.

**Stoplist candidates** (Q9e) are small: `UNITEMIZED …` keys, `PAYROLL`, `PETTY CASH`, `CASH`,
`ATM` and `CASH WITHDRAWAL`, about $270,000 together. No key reads `VARIOUS` or `SEE MEMO` with
real money.

**People:** 277,547 counted rows ($547.3M) are `IND`, under 37,072 keys. 1,380 `IND` keys span
more than one state, holding $67.3M: a floor on how many people one key merges, since one person
can be paid in two states too. Whether a person gets a payee page is NEU-2150's.

## Q10: conduit fees and refunds (2024)

```python
show("Q10a. The conduits as payees (fec/conduits.csv: ActBlue C00401224, WinRed C00694323)", """
SELECT CASE WHEN regexp_matches(payee_key, 'ACT ?BLUE') THEN 'ActBlue' WHEN regexp_matches(payee_key, 'WIN ?RED') THEN 'WinRed' END AS conduit,
    count(*) AS rows, sum(amt) AS dollars, sum(amt) FILTER (WHERE counted) AS counted_dollars,
    avg(memo::INT)::DOUBLE AS memo_rows, count(DISTINCT CMTE_ID) FILTER (WHERE counted) AS committees_paying,
    count(DISTINCT payee_key) AS keys, count(*) FILTER (WHERE role LIKE '%parent%') AS parent_rows,
    count(*) FILTER (WHERE role LIKE 'child%') AS child_rows
FROM px WHERE regexp_matches(coalesce(payee_key, ''), 'ACT ?BLUE|WIN ?RED') GROUP BY ALL""")
show("Q10b. Their counted rows by purpose (top 15) and CATEGORY", """
SELECT CASE WHEN regexp_matches(payee_key, 'ACT ?BLUE') THEN 'ActBlue' WHEN regexp_matches(payee_key, 'WIN ?RED') THEN 'WinRed' END AS conduit, purp,
    count(*) AS rows, sum(amt) AS dollars, mode(fec_code(CATEGORY)) AS commonest_code
FROM px WHERE counted AND regexp_matches(coalesce(payee_key, ''), 'ACT ?BLUE|WIN ?RED')
GROUP BY ALL ORDER BY dollars DESC LIMIT 15""")
show("Q10c. Negative amounts by form and line, counted rows", """
SELECT FORM_TP_CD, LINE_NUM, count(*) AS rows, sum(amt) AS dollars FROM cx WHERE counted AND amt < 0
GROUP BY ALL ORDER BY dollars""")
show("Q10c2. Negative amounts by filer group, and those whose purpose names Schedule E or an IE", """
SELECT filer, count(*) AS rows, sum(amt) AS dollars,
    sum(amt) FILTER (WHERE regexp_matches(coalesce(purp, ''), 'SCHEDULE E|SCH\\. E|SCHED\\. E|\\bIES?\\b|INDEPENDENT EXPENDITURE|LINE 24')) AS naming_schedule_e
FROM cx WHERE counted AND amt < 0 GROUP BY ALL ORDER BY dollars""")
show("Q10d. Negative amounts: the top 30 purposes", """
SELECT purp, count(*) AS rows, sum(amt) AS dollars FROM cx WHERE counted AND amt < 0
GROUP BY ALL ORDER BY dollars LIMIT 30""")
show("Q10e. Positive rows whose purpose names a refund, void or reissue: by form and line", """
SELECT FORM_TP_CD, LINE_NUM, count(*) AS rows, sum(amt) AS dollars FROM cx
WHERE counted AND amt > 0 AND regexp_matches(coalesce(purp, ''), '\\b(REFUND|VOID|VOIDED|REISSUE|REISSUED|REVERSAL|OFFSET|RETURNED)\\b')
GROUP BY ALL ORDER BY dollars DESC""")
show("Q10f. Those positive rows: the top 30 purposes", """
SELECT purp, count(*) AS rows, sum(amt) AS dollars FROM cx
WHERE counted AND amt > 0 AND regexp_matches(coalesce(purp, ''), '\\b(REFUND|VOID|VOIDED|REISSUE|REISSUED|REVERSAL|OFFSET|RETURNED)\\b')
GROUP BY ALL ORDER BY dollars DESC LIMIT 30""")
show("Q10g. The sign rule's stakes, counted rows", """
SELECT sum(amt) AS as_filed, sum(abs(amt)) AS every_amount_positive,
    sum(amt) FILTER (WHERE amt > 0) AS negatives_dropped,
    sum(amt) - 2 * sum(amt) FILTER (WHERE amt > 0 AND regexp_matches(coalesce(purp, ''), '\\b(REFUND|VOID|VOIDED|REISSUE|REISSUED|REVERSAL|OFFSET|RETURNED)\\b'))
        AS refund_named_positives_negated
FROM cx WHERE counted""")
```

**Q10a. The conduits as payees (fec/conduits.csv: ActBlue C00401224, WinRed C00694323)  (0 s)**

| conduit | rows | dollars | counted_dollars | memo_rows | committees_paying | keys | parent_rows | child_rows |
|---|---|---|---|---|---|---|---|---|
| WinRed | 78,912 | 117,159,024 | 115,830,177 | 3.37% | 1,075 | 25 | 3,020 | 2,621 |
| ActBlue | 111,095 | 136,084,617 | 136,048,065 | 0.25% | 1,916 | 33 | 0 | 63 |

**Q10b. Their counted rows by purpose (top 15) and CATEGORY  (0 s)**

| conduit | purp | rows | dollars | commonest_code |
|---|---|---|---|---|
| ActBlue | SERVICE FEE | 5,932 | 44,482,332 | 003 |
| WinRed | MERCHANT FEES | 16,252 | 33,493,466 | 001 |
| ActBlue | CREDIT CARD PROCESSING FEE | 31,402 | 27,799,715 | 003 |
| ActBlue | CREDIT CARD PROCESSING FEES | 22,951 | 20,050,333 | 001 |
| WinRed | MERCHANDISE FEES | 574 | 13,848,043 | 003 |
| ActBlue | MERCHANT FEES | 14,845 | 11,271,926 | 001 |
| ActBlue | CREDIT CARD FEES | 9,240 | 8,804,326 | 003 |
| WinRed | CREDIT CARD MERCHANT FEES | 1,131 | 5,821,122 |  |
| WinRed | CREDIT CARD FEES | 6,896 | 5,634,784 | 001 |
| WinRed | CREDIT CARD MERCHANT FEE | 2,295 | 5,561,027 | 001 |
| WinRed | ONLINE FUNDRAISING/CREDIT CARD MERCHANT FEES | 195 | 5,383,481 |  |
| WinRed | PROCESSING FEE | 2,143 | 5,344,017 | 001 |
| ActBlue | CREDIT CARD PROCESSING | 2,424 | 5,104,261 | 001 |
| WinRed | CREDIT CARD PROCESSING FEES | 10,731 | 4,790,070 | 001 |
| ActBlue | PROCESSING FEE FOR POLITICAL CONTRIBUTIONS | 128 | 4,026,009 | 001 |

**Q10c. Negative amounts by form and line, counted rows  (0 s)**

| FORM_TP_CD | LINE_NUM | rows | dollars |
|---|---|---|---|
| F3X | 21B | 5,902 | -187,971,975 |
| F3 | 17 | 2,922 | -2,965,324 |
| F3P | 23 | 167 | -592,947 |

**Q10c2. Negative amounts by filer group, and those whose purpose names Schedule E or an IE  (0 s)**

| filer | rows | dollars | naming_schedule_e |
|---|---|---|---|
| super PAC | 2,293 | -124,546,997 | -109,089,818 |
| party | 1,263 | -48,339,614 |  |
| other | 2,367 | -15,200,860 | -10,741,823 |
| candidate | 3,068 | -3,442,776 |  |

**Q10d. Negative amounts: the top 30 purposes  (0 s)**

| purp | rows | dollars |
|---|---|---|
| SEE SCHEDULE E | 6 | -28,430,202 |
| SEE SCHEDULE E, MEDIA BUY | 17 | -18,760,271 |
| ALLOCABLE EXPENSES TO LEGAL ACCT | 22 | -9,830,779 |
| RECAPTURE OF LEGAL FUNDS | 6 | -8,213,191 |
| INTERNAL LEGAL PROCEEDINGS EXPENDITURES TRANSFER | 22 | -7,674,823 |
| INTERNAL HQ ALLOCABLE EXPENDITURES TRANSFER | 16 | -6,394,295 |
| SEE SCHEDULE E, DIGITAL MEDIA BUY | 12 | -6,129,273 |
| CANVASSING SERVICES (DISBURSEMENT REPORTED IN PRIOR MONTH FOR FEDERAL IE; SEE SCHEDULE E) | 23 | -6,039,207 |
| BILLBOARD ADVERTISING BUY (IE PAID 9/20/2024; SEE LINE 24) | 1 | -5,800,000 |
| REVERSAL OF PRE-PAYMENT FOR IES DISSEMINATING IN OCTOBER | 15 | -4,694,353 |
| TRSFR TO LINE 24 (SEE MEMO TEXT FOR DETAILED EXPLANATION) | 26 | -4,504,437 |
| DATA SERVICES SUBSCRIPTION | 24 | -3,600,000 |
| ALLOCABLE EXPENSES TO HQ ACCT | 7 | -3,577,146 |
| RECAPTURE OF HEADQUARTERS FUNDS | 1 | -2,873,996 |
| RVERSAL FOR PRE-PAYMENT FOR IES DISSEMINATING IN OCTOBER | 1 | -2,520,620 |
| MOVING FROM AN OPERATING EXPENSE TO AN INDEPENDENT EXPENDITURE - SEE LINE 24 | 1 | -2,306,119 |
| RELATIONAL ORGANIZING (IE PAID 11/13/24, SEE SCHEDULE E) | 1 | -2,255,056 |
| SMS MESSAGING (IE PAID 10/15/2024 SEE SCH. E) | 1 | -2,000,000 |
| DRAWDOWN OF ADVANCE PAYMENT | 17 | -2,000,000 |
| PLACED MEDIA: TV (IE PAID 10/15/24, SEE SCHEDULE E) | 3 | -1,907,000 |
| SOFTWARE | 22 | -1,614,266 |
| TV AD BUY | 4 | -1,522,156 |
| DRAW DOWN AGAINST ADVANCE PAYMENT FOR DIGITAL ADS, SEE SCHED. E | 22 | -1,504,709 |
| SEE SCHEDULE E; DIGITAL MEDIA BUY | 2 | -1,394,737 |
| CANVASSING, SEE SCHEDULE E | 10 | -1,308,382 |
| DIGITAL ADVERTISING, SEE SCHEDULE E | 7 | -1,307,949 |
| OFFSETTING ADJUSTMENT: VENDOR CREDIT: PLACED TV [SB21B:6920] | 1 | -1,260,794 |
| DIGITAL AD BUY | 7 | -1,255,500 |
| MAILER POSTAGE AND PRODUCTION (IE DISSEMINATED 10/23; SEE SCHEDULE E) | 1 | -1,243,814 |
| MEDIA BUY, SEE SCHEDULE E | 9 | -1,187,249 |

**Q10e. Positive rows whose purpose names a refund, void or reissue: by form and line  (0 s)**

| FORM_TP_CD | LINE_NUM | rows | dollars |
|---|---|---|---|
| F3X | 21B | 387 | 2,643,839 |
| F3P | 23 | 80 | 1,995,706 |
| F3 | 17 | 619 | 1,181,808 |

**Q10f. Those positive rows: the top 30 purposes  (0 s)**

| purp | rows | dollars |
|---|---|---|
| IN-KIND OFFSET: TRAVEL | 34 | 1,282,067 |
| DIGITAL PRODUCTION AND ADVERTISING. SEE OFFSET PRO-CHOICE WOMEN 9.24.24 | 1 | 450,000 |
| RETURN OF OFFSET OVERPAYMENT FOR MAY YTD 2024 PERSONNEL & OPERATING COSTS | 1 | 387,595 |
| IN-KIND OFFSET: TRAVEL / INSURANCE / SOFTWARE / WEB SERVICE / SUBSCRIPTION | 1 | 338,466 |
| INKIND: OFFSET | 17 | 306,280 |
| RETURN OF DUPLICATE TAX REFUND - COVID-19 RELIEF FOR SOCIAL SECURITY | 1 | 244,746 |
| POSTAGE REFUND | 9 | 231,008 |
| IN-KIND OFFSET: TRAVEL / FOOD / BEVERAGE | 3 | 201,654 |
| OFFSET FOR IN-KIND EVENTS | 20 | 173,554 |
| REISSUE FUNDRAISING CONSULTING FROM 7/25/2023 | 1 | 143,000 |
| CONTRIBUTION REFUND | 103 | 127,577 |
| CANDIDATE LOAN REVERSAL TO CHASE VIA WIRE TRANSFER FROM COAST- WRONG ACCOUNT | 1 | 100,000 |
| REFUND | 48 | 86,340 |
| REFUND OF TRAVEL DEPOSITS | 3 | 71,633 |
| OFFSET FOR INKIND RECEIPT OF STAFF TIME - SEE SCHEDULE A | 2 | 67,414 |
| IN KIND OFFSET: FOOD / BEVERAGE | 13 | 54,695 |
| FUNDRAISING EVENT FOR TURNING POINT ACTION IN FLORIDA - ACH WAS RETURNED AND HAD TO BE PAID AGAIN | 1 | 50,000 |
| IN-KIND OFFSET: CATERING SERVICES / FOOD / BEVERAGE | 6 | 48,919 |
| OFFSET FOR IN-KIND EVENT CATERING/SVCS | 8 | 48,316 |
| CANDIDATE IN-KIND OFFSET: TRAVEL | 13 | 42,234 |
| REFUND OF GENERAL 2024 CONTRIBUTION | 16 | 38,984 |
| REFUND OF CONTRIBUTION | 17 | 37,636 |
| REISSUE VOIDED PAYMENT; ORIGINAL DATE 1/2/24 | 1 | 37,158 |
| OFFSET FOR IN-KIND SERVICES RENDERED | 2 | 33,500 |
| REFUND CANDIDATE CONTRIBUTION | 1 | 30,291 |
| IN-KIND OFFSET: SURVEY / SURVEY RESEARCH | 1 | 30,000 |
| REFUND FOR DOUBLE CHARGE | 1 | 28,000 |
| CONTRIBUTION- REFUND PENDING | 1 | 25,000 |
| REISSUE OF CHECK PREVIOUSLY REPORTED | 1 | 21,352 |
| IN-KIND OFFSET - FOOD/BEVERAGE | 6 | 20,428 |

**Q10g. The sign rule's stakes, counted rows  (0 s)**

| as_filed | every_amount_positive | negatives_dropped | refund_named_positives_negated |
|---|---|---|---|
| 9,715,514,602 | 10,098,575,096 | 9,907,044,849 | 9,703,871,896 |

ActBlue is paid $136.0M and WinRed $115.8M of counted spending. Nearly all of it is fees per
contribution processed (`SERVICE FEE`, `MERCHANT FEES`, `CREDIT CARD PROCESSING FEE(S)`), so it is
`transfers_fees`. WinRed's `MERCHANDISE FEES` ($13.8M) is its fee on merchandise sales. WinRed is
also a parent (3,020 parent rows: committees' WinRed bills itemizing the payees behind them under
`MEMO: SUBVENDOR OF-WINRED TECHNICAL SERVICES`).

Negative amounts net $-191.5M of counted spending, almost all on Form 3X line 21(b). Super PACs
hold $-124.5M of it, $-109.1M on rows whose purpose names Schedule E or an IE, and parties
$-48.3M (Q10c2). The largest are super PACs moving a payment already reported as an operating expenditure to Schedule E (`SEE
SCHEDULE E`, `… (IE PAID 10/15/24, SEE SCHEDULE E)`), parties moving costs between accounts
(`ALLOCABLE EXPENSES TO LEGAL ACCT`, `RECAPTURE OF LEGAL FUNDS`), and drawdowns of advance
payments. Positive rows naming a refund, void or reissue are $5.8M, most of them filed as in-kind offsets.

**The sign rule: amounts are summed as filed.** A negative row cancels its positive. A super PAC's
media buy reclassified as an independent expenditure then nets to nothing here and counts once,
in `independent_expenditure`. Counting every amount positive would add $383.1M, and dropping the
negatives $191.5M, most of it money counted again as an IE. Negating positive refund-named rows
too would move $11.6M (each moves twice its amount), mostly rows filed as in-kind offsets, which
are real spending. The contract's "refunds and
offsets net out" is this rule.

## Q11: against FEC's reported operating expenditures (2024)

```python
silver("reported_total")
with psycopg.connect(settings.database_url) as pg:
    pg.read_only = True
    print("\nlive gold 2024:", pg.execute("SELECT cycles -> '2024' FROM gold.meta").fetchone()[0])
con.execute("""
CREATE TABLE per AS
WITH s AS (
    SELECT CMTE_ID, LINE_NUM IN ('17', '21B', '23') AS named,
        sum(amt) FILTER (WHERE r1) AS r1, sum(amt) FILTER (WHERE r2c) AS r2c, sum(amt) FILTER (WHERE r2) AS r2,
        sum(amt) FILTER (WHERE r3) AS r3, sum(amt) FILTER (WHERE counted) AS r4
    FROM cx GROUP BY ALL),
-- Every rule twice: over every line, and over the lines FEC names (17, 21B, 23).
l AS (
    SELECT CMTE_ID, 'all lines' AS lines, sum(r1) AS r1, sum(r2c) AS r2c, sum(r2) AS r2, sum(r3) AS r3, sum(r4) AS r4
    FROM s GROUP BY ALL
    UNION ALL
    SELECT CMTE_ID, 'named lines', sum(r1), sum(r2c), sum(r2), sum(r3), sum(r4) FROM s WHERE named GROUP BY ALL),
cmf AS (SELECT DISTINCT CMTE_ID, CASE
        WHEN CMTE_TP IN ('H', 'S', 'P') THEN 'candidate' WHEN CMTE_TP IN ('X', 'Y') THEN 'party'
        WHEN CMTE_TP IN ('O', 'U') THEN 'super PAC' ELSE 'other' END AS filer FROM cm),
keys AS (SELECT committee_id, lines FROM silver.reported_total, (VALUES ('all lines'), ('named lines')) AS v(lines)
         UNION SELECT CMTE_ID, lines FROM l)
SELECT k.committee_id, k.lines, coalesce(cmf.filer, 'not in cm') AS filer, rt.operating_expenditures AS reported,
    k.committee_id IN (SELECT CMTE_ID FROM s) AS has_rows,
    coalesce(l.r1, 0) AS r1, coalesce(l.r2c, 0) AS r2c, coalesce(l.r2, 0) AS r2, coalesce(l.r3, 0) AS r3,
    coalesce(l.r4, 0) AS r4
FROM keys AS k
LEFT JOIN l ON l.CMTE_ID = k.committee_id AND l.lines = k.lines
LEFT JOIN silver.reported_total AS rt ON rt.committee_id = k.committee_id
LEFT JOIN cmf ON cmf.CMTE_ID = k.committee_id""")
con.execute("""CREATE TABLE per_rule AS
    SELECT committee_id, lines, filer, reported, has_rows, rule, counted
    FROM per UNPIVOT (counted FOR rule IN (r1, r2c, r2, r3, r4))""")
DECILES = ", ".join(f"round(quantile_cont(counted / reported, {d / 10}), 4) AS p{d}0" for d in range(1, 10))
show("Q11a. Committees with a reported figure above $0: counted ÷ reported by decile, per rule and lines", f"""
SELECT rule, lines, count(*) AS committees, sum(reported) AS reported, sum(counted) AS counted, {DECILES},
    count(*) FILTER (WHERE counted > reported * 1.01) AS over_1pct,
    sum(counted - reported) FILTER (WHERE counted > reported * 1.01) AS dollars_over
FROM per_rule WHERE reported > 0 GROUP BY ALL ORDER BY rule, lines""")
show("Q11b. By filer group, per rule (every line)", """
SELECT rule, filer, count(*) AS committees, sum(reported) AS reported, sum(counted) AS counted,
    (sum(counted) / sum(reported))::DOUBLE AS dollar_weighted,
    round(quantile_cont(counted / reported, 0.1), 4) AS p10, round(quantile_cont(counted / reported, 0.5), 4) AS median,
    round(quantile_cont(counted / reported, 0.9), 4) AS p90,
    count(*) FILTER (WHERE counted > reported * 1.01) AS over_1pct,
    sum(counted - reported) FILTER (WHERE counted > reported * 1.01) AS dollars_over
FROM per_rule WHERE reported > 0 AND lines = 'all lines' GROUP BY ALL ORDER BY rule, reported DESC""")
show("Q11c. Reported $0 or blank beside counted money, and a reported figure with no oppexp row, per rule", """
SELECT rule,
    count(*) FILTER (WHERE coalesce(reported, 0) = 0 AND counted <> 0) AS reported_0_or_blank_with_counted,
    sum(counted) FILTER (WHERE coalesce(reported, 0) = 0 AND counted <> 0) AS their_counted,
    count(*) FILTER (WHERE reported IS NULL AND counted <> 0) AS of_which_blank,
    count(*) FILTER (WHERE reported > 0 AND NOT has_rows) AS reported_no_rows,
    sum(reported) FILTER (WHERE reported > 0 AND NOT has_rows) AS their_reported
FROM per_rule WHERE lines = 'all lines' GROUP BY rule ORDER BY rule""")
show("Q11d. The 20 largest excesses under R4, with their form, schedule and line mix (undiagnosed)", """
WITH over AS (SELECT * FROM per_rule WHERE rule = 'r4' AND lines = 'all lines' AND reported IS NOT NULL
                  AND counted > reported * 1.01
              ORDER BY counted - reported DESC LIMIT 20),
mix AS (SELECT CMTE_ID, string_agg(line || ' ' || format('{:,.0f}', d), '; ' ORDER BY d DESC) AS lines
        FROM (SELECT CMTE_ID, FORM_TP_CD || ' ' || SCHED_TP_CD || ' ' || LINE_NUM AS line, sum(amt) AS d
              FROM cx WHERE counted AND CMTE_ID IN (SELECT committee_id FROM over) GROUP BY ALL) GROUP BY CMTE_ID)
SELECT o.committee_id, c.CMTE_NM, o.filer, o.reported, o.counted, o.counted - o.reported AS excess, mix.lines
FROM over AS o LEFT JOIN mix ON mix.CMTE_ID = o.committee_id
LEFT JOIN (SELECT DISTINCT CMTE_ID, CMTE_NM FROM cm) AS c ON c.CMTE_ID = o.committee_id
ORDER BY excess DESC""")
show("Q11e. Committees not in reported_total with counted money, by filer group (R4)", """
SELECT filer, count(*) AS committees, sum(counted) AS counted FROM per_rule
WHERE rule = 'r4' AND lines = 'all lines' AND reported IS NULL AND counted <> 0 GROUP BY ALL ORDER BY counted DESC""")
```

```text
live gold 2024: {'build_id': '20261120T212246Z', 'source_dates': {'cm': '2026-11-15', 'cn': '2026-11-15', 'ccl': '2026-11-15', 'oth': '2026-11-16', 'pas2': '2026-11-16', 'webk': '2026-11-19', 'indiv': '2026-11-16', 'weball': '2026-11-19', 'committee_summary': '2026-11-19'}}
```

**Q11a. Committees with a reported figure above $0: counted ÷ reported by decile, per rule and lines  (0 s)**

| rule | lines | committees | reported | counted | p10 | p20 | p30 | p40 | p50 | p60 | p70 | p80 | p90 | over_1pct | dollars_over |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r1 | all lines | 9,909 | 9,916,558,902 | 9,609,294,671 | 0.00% | 75.01% | 92.26% | 97.06% | 98.77% | 99.48% | 99.80% | 99.96% | 100.00% | 61 | 899,332 |
| r1 | named lines | 9,909 | 9,916,558,902 | 9,609,235,749 | 0.00% | 75.00% | 92.25% | 97.06% | 98.77% | 99.48% | 99.80% | 99.96% | 100.00% | 59 | 899,083 |
| r2 | all lines | 9,909 | 9,916,558,902 | 9,609,428,939 | 0.00% | 75.01% | 92.26% | 97.06% | 98.77% | 99.48% | 99.80% | 99.96% | 100.00% | 63 | 1,095,370 |
| r2 | named lines | 9,909 | 9,916,558,902 | 9,609,370,018 | 0.00% | 75.00% | 92.25% | 97.06% | 98.77% | 99.48% | 99.80% | 99.96% | 100.00% | 61 | 1,095,122 |
| r2c | all lines | 9,909 | 9,916,558,902 | 9,609,429,907 | 0.00% | 75.01% | 92.26% | 97.06% | 98.77% | 99.48% | 99.80% | 99.96% | 100.00% | 63 | 1,095,370 |
| r2c | named lines | 9,909 | 9,916,558,902 | 9,609,370,985 | 0.00% | 75.00% | 92.25% | 97.06% | 98.77% | 99.48% | 99.80% | 99.96% | 100.00% | 61 | 1,095,122 |
| r3 | all lines | 9,909 | 9,916,558,902 | 9,594,311,329 | 0.00% | 74.99% | 92.23% | 97.05% | 98.76% | 99.48% | 99.80% | 99.96% | 100.00% | 63 | 1,086,185 |
| r3 | named lines | 9,909 | 9,916,558,902 | 9,594,252,407 | 0.00% | 74.93% | 92.18% | 97.05% | 98.75% | 99.48% | 99.80% | 99.96% | 100.00% | 61 | 1,085,937 |
| r4 | all lines | 9,909 | 9,916,558,902 | 9,594,311,329 | 0.00% | 74.99% | 92.23% | 97.05% | 98.76% | 99.48% | 99.80% | 99.96% | 100.00% | 63 | 1,086,185 |
| r4 | named lines | 9,909 | 9,916,558,902 | 9,594,252,407 | 0.00% | 74.93% | 92.18% | 97.05% | 98.75% | 99.48% | 99.80% | 99.96% | 100.00% | 61 | 1,085,937 |

**Q11b. By filer group, per rule (every line)  (0 s)**

| rule | filer | committees | reported | counted | dollar_weighted | p10 | median | p90 | over_1pct | dollars_over |
|---|---|---|---|---|---|---|---|---|---|---|
| r1 | candidate | 3,296 | 4,693,988,895 | 4,682,632,238 | 99.76% | 67.74% | 99.21% | 100.00% | 27 | 552,300 |
| r1 | other | 4,728 | 2,624,086,568 | 2,609,785,907 | 99.46% | 0.00% | 98.15% | 100.00% | 25 | 61,864 |
| r1 | party | 402 | 1,730,269,348 | 1,450,405,811 | 83.83% | 0.00% | 50.51% | 99.50% | 2 | 3,833 |
| r1 | super PAC | 1,483 | 868,214,091 | 866,470,714 | 99.80% | 0.00% | 99.49% | 100.00% | 7 | 281,334 |
| r2 | candidate | 3,296 | 4,693,988,895 | 4,682,597,823 | 99.76% | 67.74% | 99.21% | 100.00% | 27 | 552,300 |
| r2 | other | 4,728 | 2,624,086,568 | 2,609,804,436 | 99.46% | 0.00% | 98.15% | 100.00% | 26 | 109,035 |
| r2 | party | 402 | 1,730,269,348 | 1,450,406,639 | 83.83% | 0.00% | 50.51% | 99.50% | 2 | 3,833 |
| r2 | super PAC | 1,483 | 868,214,091 | 866,620,041 | 99.82% | 0.00% | 99.49% | 100.00% | 8 | 430,203 |
| r2c | candidate | 3,296 | 4,693,988,895 | 4,682,598,805 | 99.76% | 67.74% | 99.21% | 100.00% | 27 | 552,300 |
| r2c | other | 4,728 | 2,624,086,568 | 2,609,804,429 | 99.46% | 0.00% | 98.15% | 100.00% | 26 | 109,035 |
| r2c | party | 402 | 1,730,269,348 | 1,450,406,636 | 83.83% | 0.00% | 50.51% | 99.50% | 2 | 3,833 |
| r2c | super PAC | 1,483 | 868,214,091 | 866,620,038 | 99.82% | 0.00% | 99.49% | 100.00% | 8 | 430,203 |
| r3 | candidate | 3,296 | 4,693,988,895 | 4,667,594,328 | 99.44% | 66.78% | 99.20% | 100.00% | 27 | 543,139 |
| r3 | other | 4,728 | 2,624,086,568 | 2,609,690,321 | 99.45% | 0.00% | 98.14% | 100.00% | 26 | 109,011 |
| r3 | party | 402 | 1,730,269,348 | 1,450,406,639 | 83.83% | 0.00% | 50.51% | 99.50% | 2 | 3,833 |
| r3 | super PAC | 1,483 | 868,214,091 | 866,620,041 | 99.82% | 0.00% | 99.49% | 100.00% | 8 | 430,203 |
| r4 | candidate | 3,296 | 4,693,988,895 | 4,667,594,328 | 99.44% | 66.78% | 99.20% | 100.00% | 27 | 543,139 |
| r4 | other | 4,728 | 2,624,086,568 | 2,609,690,321 | 99.45% | 0.00% | 98.14% | 100.00% | 26 | 109,011 |
| r4 | party | 402 | 1,730,269,348 | 1,450,406,639 | 83.83% | 0.00% | 50.51% | 99.50% | 2 | 3,833 |
| r4 | super PAC | 1,483 | 868,214,091 | 866,620,041 | 99.82% | 0.00% | 99.49% | 100.00% | 8 | 430,203 |

**Q11c. Reported $0 or blank beside counted money, and a reported figure with no oppexp row, per rule  (0 s)**

| rule | reported_0_or_blank_with_counted | their_counted | of_which_blank | reported_no_rows | their_reported |
|---|---|---|---|---|---|
| r1 | 16 | 121,275,276 | 4 | 1,114 | 4,041,384 |
| r2 | 16 | 121,275,276 | 4 | 1,114 | 4,041,384 |
| r2c | 16 | 121,275,276 | 4 | 1,114 | 4,041,384 |
| r3 | 16 | 121,275,276 | 4 | 1,114 | 4,041,384 |
| r4 | 16 | 121,275,276 | 4 | 1,114 | 4,041,384 |

**Q11d. The 20 largest excesses under R4, with their form, schedule and line mix (undiagnosed)  (0 s)**

| committee_id | CMTE_NM | filer | reported | counted | excess | lines |
|---|---|---|---|---|---|---|
| C00853473 | JONATHAN NEZ FOR CONGRESS | candidate | 5,052,383 | 5,359,336 | 306,953 | F3 SB 17 5,359,336 |
| C00494021 | CATHOLICVOTE.ORG CANDIDATE FUND | super PAC | 122,191 | 321,708 | 199,517 | F3X SB 21B 321,708 |
| C00720029 | EVERYDAY PEOPLE | super PAC | 897,481 | 1,046,350 | 148,869 | F3X SB 21B 1,046,350 |
| C00845164 | TEKESHA MARTINEZ FOR CONGRESS | candidate | 546,710 | 594,763 | 48,053 | F3 SB 17 594,763 |
| C00573519 | THINK BIG AMERICA PAC | other | 933,913 | 981,083 | 47,170 | F3X SB 21B 981,083 |
| C00487470 | CLUB FOR GROWTH ACTION | super PAC | 3,479,656 | 3,526,605 | 46,948 | F3X SB 21B 3,526,605 |
| C00847483 | SHAWN FOR GEORGIA | candidate | 3,481,277 | 3,522,848 | 41,571 | F3 SB 17 3,522,848 |
| C00522730 | CITIZENS FOR JOE MILLER | candidate | 17,435 | 54,390 | 36,955 | F3 SB 17 54,390 |
| C00868596 | WEST VIRGINIANS TO ELECT DON | candidate | 145,097 | 175,389 | 30,291 | F3 SB 17 175,389 |
| C00858381 | INDEPENDENTS MOVING THE NEEDLE | super PAC | 382,556 | 407,002 | 24,446 | F3X SB 21B 407,002 |
| C00839878 | ZANE 4 SENATE COMMITTEE | candidate | 16,822 | 33,631 | 16,809 | F3 SB 17 33,631 |
| C00832956 | COMMITTEE TO ELECT MICHAEL LYNCH | candidate | 18,406 | 31,774 | 13,368 | F3 SB 17 31,774 |
| C00156554 | INTERNATIONAL ASSOCIATION OF BRIDGE STRUCTURAL & ORNAMENTAL IRON WORKERS LOCAL NO 67 PAC | other | 499 | 12,978 | 12,479 | F3X SB 21B 12,978 |
| C00832287 | CHARLES IN CHARGE | candidate | 540 | 11,148 | 10,608 | F3 SB 17 10,668; F3P SB 23 480 |
| C00287904 | SHEILA JACKSON LEE FOR CONGRESS | candidate | 856,718 | 866,399 | 9,681 | F3 SB 17 866,399 |
| C00852699 | RIC HOLDEN FOR MONTANA | candidate | 50,604 | 59,905 | 9,301 | F3 SB 17 59,905 |
| C00207969 | NATIONAL CUSTOMS BROKERS & FORWARDERS ASSOCIATION PAC | other | 0 | 7,500 | 7,500 | F3X SB 21B 7,500 |
| C00738815 | TAKEACTION MN FEDERAL FUND | super PAC | 6,428 | 12,473 | 6,045 | F3X SB 21B 12,473 |
| C00874321 | STAMPER FOR CONGRESS | candidate | 30,077 | 36,049 | 5,971 | F3 SB 17 36,049 |
| C00185652 | NORTH CAROLINA PEANUT GROWERS ASSOCIATION PAC FKA VIRGINIA-CAROLINA'S PEANUT PAC | other | 1,787 | 7,721 | 5,934 | F3X SB 21B 7,721 |

**Q11e. Committees not in reported_total with counted money, by filer group (R4)  (0 s)**

| filer | committees | counted |
|---|---|---|
| not in cm | 2 | 121,230,310 |
| other | 1 | 11,616 |
| super PAC | 1 | 1,516 |

The rules barely differ against FEC's figure. Under each, over every line or the lines FEC names, the
median committee sits at 98.75–98.77% of its reported figure, every decile moves by 0.08 points at
most, and 59–63 committees are more than 1% above it, by $0.90M–$1.10M. Each rule's filer split
(Q11b) is R4's to within $0.2M. R2 against
R1 adds two committees and $196,038 over, the memo-row parents. The superseded filings take
$15.1M off without changing the over count. Restricting to the lines FEC names drops 47 rows.

Itemized spending sits below the reported figure by design: payments of $200 or less in a year
are unitemized. 1,114 committees report operating expenditures ($4.0M) and have no `oppexp` row
(Q11c). Parties
are at 83.83% dollar-weighted, against 99.4–99.8% for every other group: the file has no line
21(a) (Q1). The 20 largest excesses (Q11d) are undiagnosed, as §1.1 asks, and no Bug ticket was
filed from them. The 16 committees with a reported $0 or blank beside counted money hold
$121.3M, $121.2M of it the Norris filer that `cm` does not hold (Q11c). The `oppexp` zip (`Last-Modified`
2026-11-15) is four days older than the build's `committee_summary` (2026-11-19).

## Decisions

1. **Sub-itemization: parent always** (Q3). A parent counts, whatever its memo code. A child of a
   parent in the file never counts. Every other row counts when it is not a memo row. §1.1's bar is
   not met in 2024 (47.78%), though it is met in ten of the twelve cycles (Q2c). The contract's
   "`MEMO_CD = 'X'` rows are not counted" gains one exception: a parent filed as a memo row
   ($164,432 in 2024). NEU-2150 writes it.
2. **Amendments: the receipt side's superseded filings, alone** (Q6). A filing in `indiv`'s
   `superseded_filing` set is not counted in spending either: 47 filings, $15,117,610 of 2024. The
   payment-side rule's extra $124,469 is not adopted.
3. **Overlap: none needed** (Q7). No `oppexp` row is in `pas2`, `oth` or `indiv`. In-kind outlays
   ($18.8M of orphan children naming a receipt) are kept as spending.
4. **Sign: as filed** (Q10). Negative rows subtract, and nothing is negated or dropped for its
   purpose.
5. **Categories: 15** (Q8). `media`, `digital`, `fundraising`, `payroll`, `consulting`, `travel`,
   `events`, `administrative`, `legal_compliance`, `transfers_fees`, `other`, plus `mail`,
   `field`, `polling_research` and `credit_card`, each defined in Q8's table and T6–T9. FEC's code
   map:

   | Code | FEC's meaning | Category |
   | --- | --- | --- |
   | 001 | Administrative/salary/overhead | `administrative` |
   | 002 | Travel | `travel` |
   | 003 | Solicitation and fundraising | `fundraising` |
   | 004 | Advertising | `media` |
   | 005 | Polling | `polling_research` |
   | 006 | Campaign materials | `mail` |
   | 007 | Campaign event expenses | `events` |
   | 008 | Transfers | `transfers_fees` |
   | 009 | Loan repayments | `transfers_fees` |
   | 010 | Refunds of contributions | `transfers_fees` |
   | 011 | Political contributions | `transfers_fees` |
   | 012 | Donations | `transfers_fees` |
   | 101 | Non-allocable (presidential) | `other` |
   | 102 | Media (presidential) | `media` |
   | 103 | Mass mailings and campaign materials (presidential) | `mail` |
   | 104 | Overhead of state offices (presidential) | `administrative` |
   | 105 | Special telephone programs (presidential) | `field` |
   | 106 | Public opinion polls (presidential) | `polling_research` |
   | 107 | Fundraising (presidential) | `fundraising` |

   A code written without its leading zeros reads as the code it pads to. Any other code maps to
   nothing. **For NEU-2150:** "FEC's `CATEGORY` when filled" misfiles 001's dollars (3.57% agree,
   Q8g), and 101, 104 and 107's. A contract that trusts only the codes that agree (002, 004, 005,
   011, 102, 106) and reads the purpose otherwise would follow the measurement. That is NEU-2150's
   call, not this document's.
6. **Payee keys** (Q9). No wrong merge in the top 100. Three split firms. Stoplist candidates:
   `UNITEMIZED …`, `PAYROLL`, `PETTY CASH`, `CASH`, `ATM`, `CASH WITHDRAWAL` (about $270,000). Card
   issuers (American Express $195.2M) name no real payee under Decision 1. An in-kind outlay's payee
   is its contributor. People: 37,072 `IND` keys, $547.3M, with 1,380 keys in more than one state.
7. **Memory** (Q1). `operating_expenditure` holds about 0.87 GiB for 2024, which puts the transform's
   peak at about 27.35 GiB under the 29.80 GiB limit. NEU-2152 should write the table and drop it
   before `contribution`'s write, the transform's peak, if it can, since the earlier 28.97 GiB build
   would not have fit.
8. **Cycles where a 2024 rule does not apply as written** (Q2). The counting rules (Decisions 1–4)
   apply in every cycle: no cycle has paper rows, and every cycle has the same lines and the same
   parent–child links. Two do not:
   - **The person rule** (a payee is a person when `ENTITY_TP` is `IND`, Q9) cannot apply as written
     in **2006, 2008, 2010, 2012, 2014, 2016 and 2018**, where `ENTITY_TP` is blank on 9.6–29.5% of
     dollars. It holds in 2004 (2.6% blank) and from 2020.
   - **The sub-itemization bar** is met in every cycle but **2016 and 2024**. Parent always is
     adopted for every cycle from 2024's result. A per-cycle bar would count children in the other
     ten.

   For NEU-2150 and NEU-2180's backfill.

## For NEU-2150, NEU-2151, NEU-2152, NEU-2153 and NEU-2160

- **NEU-2150** (spec §5, glossary, ADR 0012): Decisions 1–6. The memo-parent exception to the
  contract. Whether to keep one sub-itemization rule for every cycle (Decision 8). The 15
  categories with their definitions and the code map. Whether 001 is trusted (Decision 5). In-kind
  outlays' and card issuers' payee pages, and people as payees.
- **NEU-2151** (catalogue and extract): 26 fields per line, the 26th always empty after a
  trailing `|`, in every cycle. One member, `oppexp.txt`, in every zip checked. No cell fails a cast
  in 2024, and dates are `MM/DD/YYYY`. Out-of-range dates (years 1201 to 9201) are in every cycle.
  Fixture rows worth having: a card bill and its memo children, the same not adding up, a doubled
  filing's two copies, an orphan in-kind child (`* IN-KIND RECEIVED`), a negative `SEE SCHEDULE E`
  row, a self-referencing `BACK_REF_TRAN_ID`, a code written `1`.
- **NEU-2152** (silver `operating_expenditure`): counted under Decisions 1–4, 2024 has 1,550,230
  rows and $9,715,514,602. Its definition of done is within 1% of these. The memory budget is
  Decision 7. Its `no_contribution` check finds no row (Q7).
- **NEU-2153** (the classifier): the test set is `tests/fixtures/spending/purpose_labels_2024.csv`,
  200 purposes, 76.75% of counted dollars, 35 judgement calls with reasons. Q8g gives where FEC's
  codes disagree with the labels: 001 on 96% of its dollars, 003 on 35%, 004 on 15% (mostly
  `digital`).
- **NEU-2160** (production run): Q11's figures. Counted $9,594,311,329 against reported
  $9,916,558,902 at 9,909 committees, a median of 98.76%, 63 committees over by $1.09M, parties at
  83.83%.
