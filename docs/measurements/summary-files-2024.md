# FEC's 2024 summary files against each other and against fundlens gold

Measured for [NEU-2140](https://linear.app/neuroticsasquatch/issue/NEU-2140) (milestone M1 Reported
totals; spec [`NEU-2140-summary-files-measurement.md`](../specs/NEU-2140-summary-files-measurement.md)).
FEC publishes its own cycle-to-date figures for every candidate and committee in five overlapping
files. This document measures which file holds what, how a candidate's figures relate to its
committees', what `TTL_INDIV_CONTRIB` means, and how far fundlens's itemized totals sit from FEC's
reported itemized figure for every 2024 committee. It repeats what it can for 2004. It fixes the
decisions NEU-2141 writes into spec §4. Nothing under `sql/`, `src/` or `frontend/` changed, and no
silver, gold or marker was written.

| What | Value |
| --- | --- |
| Run | 2026-11-05 23:14 – 2026-11-06 00:16 UTC, over SSH on `music-box-dancer`. The blocks below are the final run, 23:37–23:41 UTC, except Q3, Q5, Q6 and Q7, re-run 00:10–00:13 UTC after review added Q3n, Q5n, Q6d3, Q7f and Q7g. The re-runs fetched the five 2024 files again, with the same `Last-Modified` |
| Code | `main` at `d82c07076f0de2cd3bb5bd7ecc4c8d58d4bb712c` (the `pipeline` container's `service.version`) |
| Container | `pipeline-lvch8zyndujjzkz16ksys8im-20261105T223851` |
| DuckDB | 2.0.0; `Limits(memory_limit='28GB', max_temp_directory_size='60GB', threads=6)`; `connect`'s build-side optimizer off (NEU-2076) |
| Live gold | build `20261105T205814Z`, published 2026-11-05 22:09:56 UTC; 2024 source dates `cm`, `cn`, `ccl`, `indiv`, `oth`, `pas2` all 2026-10-31. Silver read is the same build's |
| `weball24.zip` | `https://www.fec.gov/files/bulk-downloads/2024/weball24.zip`, `Last-Modified: Thu, 05 Nov 2026 06:39:59 GMT`, downloaded 2026-11-05T23:14:50Z |
| `webl24.zip` | `…/2024/webl24.zip`, `Last-Modified: Thu, 05 Nov 2026 06:39:51 GMT`, downloaded 23:14:52Z |
| `webk24.zip` | `…/2024/webk24.zip`, `Last-Modified: Thu, 05 Nov 2026 06:40:07 GMT`, downloaded 23:14:53Z |
| `committee_summary_2024.csv` | `…/2024/committee_summary_2024.csv`, `Last-Modified: Thu, 05 Nov 2026 10:14:16 GMT`, downloaded 23:14:57Z |
| `candidate_summary_2024.csv` | `…/2024/candidate_summary_2024.csv`, `Last-Modified: Thu, 05 Nov 2026 10:13:59 GMT`, downloaded 23:14:59Z |
| `weball04.zip`, `webl04.zip`, `webk04.zip` | `…/2004/<file>`, each `Last-Modified: Thu, 31 Aug 2017 18:23:38 GMT`, downloaded 23:36:57–23:37:00Z |
| Header sources | FEC publishes no header file for `weball`, `webl` or `webk`: `data_dictionaries/<file>_header_file.csv` is a 404 for each (2026-11-05). The columns are the file descriptions' ([all candidates](https://www.fec.gov/campaign-finance-data/all-candidates-file-description/), [current campaigns](https://www.fec.gov/campaign-finance-data/current-campaigns-house-and-senate-file-description/), [PAC and party summary](https://www.fec.gov/campaign-finance-data/pac-and-party-summary-file-description/)), read 2026-11-05, and match spec §2's table. The two CSVs carry their own header row |
| 2004 bronze | `bronze/cycle=2004/{cm,cn,ccl,indiv,pas2,oth}/2026-11-05.zip`, written by `fundlens extract --cycle 2004 --file <f>` for each file, kept for the M4 backfill (NEU-2060). No `silver/…/cycle=2004` object and no `markers/cycle=2004/` key exist (checked after the run) |

None of the summary files is catalogued or in bronze. They lived in the work directory for the run
only.

## Headline

- **Candidate figures from 2008 on are the sum of the committees fundlens credits to the
  candidate**, taken from `committee_summary`. That sum equals `candidate_summary.Total_Receipt`
  within 1% for 2,235 of 2,255 candidates with a credited committee (99.11%; 99.95% of those with
  any receipts), above the 95% bar. The 20 that differ are 10 campaigns turned PACs that fundlens
  credits through `cn.CAND_PCC` ($523.3M, $495.9M of it Trump's NEVER SURRENDER), 6 empty
  `candidate_summary` rows ($12,193), and 4 with no money on either side (`candidate_summary` $0,
  the committee's summary figures blank). Before 2008 the source is `weball`. `webl` is `weball`'s rows,
  identical on every measure, in 2024 and in 2004 (Q1, Q3, Q8).
- **`committee_summary` wins for committees from 2008 on.** Where `webk` and it both have a figure,
  they agree within $1 on receipts, disbursements and cash on hand for 9,830 of 9,833 committees.
  `webk` adds only figures that `committee_summary` leaves blank for Form 5 (type I) and Form 7
  (type C) filers. `committee_summary` repeats a committee once per linked candidate (65 committees,
  136 rows) and must be deduplicated (Q1, Q2).
- **`TTL_INDIV_CONTRIB` and `webk`'s `INDV_CONTRIB` include unitemized money.** `TTL_INDIV_CONTRIB`
  equals FEC's itemized-plus-unitemized figure, not the itemized one, for 2,049 candidates; the reverse
  holds for 8. `INDV_CONTRIB` does the same for 5,389 committees against 21 (Q4).
- **Coverage should use measure B** (individual plus organization money). It is within 1% of FEC's
  itemized figure at 5,114 committees against A's 4,440, and at super PACs 802 against 386. Dollar
  weighted, super PAC B is 99.65% and A 60.19%. The median committee's B is 99.91% of FEC's itemized
  figure (Q5).
- **725 committees exceed FEC's itemized figure by more than 1%**, by $1.94B on B. Six diagnostics
  explain 548 of them; 58 have no FEC itemized figure to exceed. 119 remain unexplained ($34.4M).
  The causes are filed as NEU-2192 to NEU-2197. Hybrid PACs' non-contribution account (type 10) is
  $1.70B of the excess, and party special accounts $84.2M (Q6).
- **The three named gaps.** Senate Leadership Fund's $34.6M excess and MAGA Inc.'s $5.1M are
  organization money each filer put on line 15, other receipts, not line 11(a)(i). Fairshake's $43.4M
  shortfall comes from $69.4M of LLC gifts (a16z, USV, Paradigm, others) that it itemized only as
  memo attributions to the partners, which silver drops (NEU-2198) (Q7).
- Two more fundlens bugs surfaced on the way: WinRed's `total_individual` is −$48.2M because
  conduit refunds of earmarks are counted (NEU-2199, Q5l), and the 15C self-funding miss (NEU-2194).

## How to re-run

On the VM, in `tmux`. Save the setup script below as `setup.py`, each block as `qN.py` (Q6's two
parts as `q6core.py` and `q6.py`), and this runner as `run.sh`. Then run the blocks in order:

```bash
# VM, in tmux. Container names change on every deploy (first-run.md).
cat > run.sh <<'SH'
#!/bin/sh
# Usage: run.sh qN [extra.py ...]: setup.py, the extras and qN.py into the pipeline container, output to qN.out.
P=$(docker ps --format "{{.Names}}" | grep "^pipeline-lvch8zyndujjzkz16ksys8im" | head -1)
q=$1; shift
cat setup.py "$@" $q.py | docker exec -i "$P" python - 2>&1 | grep -v "^{" > $q.out
echo "EXIT $? $(date -u +%FT%TZ)" >> $q.out
SH
chmod +x run.sh
./run.sh q0 && ./run.sh q1 && ./run.sh q2 && ./run.sh q3 && ./run.sh q4 && ./run.sh q5
./run.sh q6 q6core.py && ./run.sh q7 q6core.py
# Q8 needs 2004's bronze. --file writes no `extracted` marker; the plain command would.
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
for f in cm cn ccl indiv pas2 oth; do docker exec "$(fl pipeline)" fundlens extract --cycle 2004 --file $f; done
./run.sh q8
docker exec "$(fl pipeline)" rm -rf /data/fundlens/scratch/measure-summary-files-2024
```

Run one block at a time, never beside a pipeline step, and do not merge to `main` while they run:
a deploy restarts `pipeline`. The first block unpacks 2024's `indiv`, `cm` and (Q7) `oth` into
`/data/fundlens/scratch/measure-summary-files-2024`, and later blocks reuse them. The run peaked at
about 15 GB there. This run deleted the directory after its last block, at 00:16 UTC.

`fundlens extract` deletes every cycle's local bronze cache except the current cycle's (2026).
R2 is untouched, and 2024's zips download again the next time a step needs them.

Every table's title carries the seconds its query took. Amounts are as filed, cast
`DECIMAL(16, 2)` inside each query, so a malformed cell would fail the query rather than read as
NULL. None did.

### Setup

The views `weball`, `webl`, `webk`, `committee_summary` and `candidate_summary` are the files as
filed, every column VARCHAR. `silver.<table>` are the live build's partitions as gold reads them
(`_require_inputs`, `_register_silver`), plus `silver.candidate_committee_link`. `gold_cc` is live
`gold.committee_cycle` for 2024, read with a read-only connection.

The setup differs from the spec's §4.1 in four ways:

- `cs`, one row per committee: `committee_summary` repeats a committee once per linked candidate
  (Q1b).
- `credited`, `04_contribution.sql`'s `linked` rule. It lists the handed-off committee under both
  candidates, as spec §1.1 asks.
- `compare()`, the per-measure equality table every cross-file query uses.
- (After Q5) `cov` and `over`, the coverage table and the over-1% list. A negative FEC figure counts
  by its size, so a committee $1 above −$1,698 is not over.

```python
import datetime as dt
import time
import zipfile
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg

from fundlens import paths
from fundlens.fec.extract import USER_AGENT
from fundlens.fec.files import CATALOGUE
from fundlens.load.gold import _register_silver, _require_inputs
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import (
    Limits, _register_handoffs, connect, literal, register_bulk, unzip_bulk,
)

settings = get_settings()
store = R2.from_settings(settings)
scratch = paths.scratch_dir(settings.data_dir)
work = scratch / "measure-summary-files-2024"
work.mkdir(parents=True, exist_ok=True)
con = connect(Limits.from_settings(settings), scratch)


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
        print("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")


# The live build's silver tables, as gold reads them (views silver.<table>), and its
# committee_cycle rows, read-only.
with psycopg.connect(settings.database_url) as pg:
    pg.read_only = True
    BUILD = pg.execute("SELECT cycles -> '2024' ->> 'build_id' FROM gold.meta").fetchone()[0]
    gold_csv = work / "gold_committee_cycle.csv"
    with gold_csv.open("wb") as out, pg.cursor().copy(
        "COPY (SELECT committee_id, total_individual, self_funding, total_from_organizations"
        " FROM gold.committee_cycle WHERE cycle = 2024) TO STDOUT WITH (FORMAT csv, HEADER)"
    ) as copy:
        for block in copy:
            out.write(block)
print("build", BUILD)
_register_silver(con, _require_inputs(store, 2024, BUILD, data_dir=settings.data_dir))
# candidate_committee_link is not a gold input: its partition is registered by hand.
link_prefix = paths.silver_partition("candidate_committee_link", 2024, BUILD)
for key in store.list_keys(link_prefix + "/"):
    local = paths.local_path(settings.data_dir, key)
    if not local.exists():
        store.download_to(key, local)
link = paths.local_path(settings.data_dir, link_prefix)
con.execute(
    "CREATE VIEW silver.candidate_committee_link AS SELECT * FROM"
    f" read_parquet({literal(link / '**' / '*.parquet')}, hive_partitioning = false)"
)
con.execute(f"CREATE TABLE gold_cc AS SELECT * FROM read_csv({literal(gold_csv)}, header = true)")
_register_handoffs(con, 2024)


def bulk(name: str, cycle: int = 2024) -> None:
    """The view `name` over `cycle`'s newest bronze `name`, unpacked into work/<cycle> on first
    use and reused after. Another cycle's view is in the schema `c<cycle>`: `c2004.indiv`."""
    file = CATALOGUE[name]
    where = work / str(cycle)
    where.mkdir(parents=True, exist_ok=True)
    text, done = where / f"{name}.txt", where / f"{name}.done"
    if not done.exists():
        text = unzip_bulk(store, cycle, file, data_dir=settings.data_dir, work=where)
        done.touch()
    if cycle != 2024:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS c{cycle}; USE c{cycle}")
    register_bulk(con, file, text)
    con.execute("USE memory.main")


def fetch(path: str) -> Path:
    """One FEC file into `work`, its Last-Modified printed; skipped when already there."""
    target = work / Path(path).name
    if not target.exists():
        url = f"{settings.fec_bulk_url.rstrip('/')}/{path}"
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT})) as response:
            target.write_bytes(response.read())
            print(url, "| Last-Modified:", response.headers.get("Last-Modified"),
                  "| downloaded", dt.datetime.now(dt.UTC).isoformat(timespec="seconds"))
    return target


def view_zip(name: str, path: Path, header: list[str]) -> None:
    """A pipe-delimited, headerless summary zip as a VARCHAR view named `name`."""
    with zipfile.ZipFile(path) as archive:
        (member,) = archive.namelist()
        text = work / f"{name}.txt"
        if not text.exists():
            text.write_bytes(archive.read(member))
    columns = "{" + ", ".join(f"'{h}': 'VARCHAR'" for h in header) + "}"
    con.execute(
        f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv({literal(text)}, delim = '|',"
        f" quote = '', escape = '', header = false, auto_detect = false, columns = {columns})"
    )


def view_csv(name: str, path: Path) -> None:
    """A header-row CSV summary file as a view named `name`, every column VARCHAR."""
    con.execute(
        f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv({literal(path)}, header = true,"
        " all_varchar = true)"
    )


# FEC publishes no header file for weball, webl or webk (data_dictionaries/<f>_header_file.csv
# is a 404 for each, 2026-11-05): the columns are each file description's, in order.
# webl's layout is weball's (https://www.fec.gov/campaign-finance-data/all-candidates-file-description/,
# .../current-campaigns-house-and-senate-file-description/).
WEBALL = ["CAND_ID", "CAND_NAME", "CAND_ICI", "PTY_CD", "CAND_PTY_AFFILIATION", "TTL_RECEIPTS",
          "TRANS_FROM_AUTH", "TTL_DISB", "TRANS_TO_AUTH", "COH_BOP", "COH_COP", "CAND_CONTRIB",
          "CAND_LOANS", "OTHER_LOANS", "CAND_LOAN_REPAY", "OTHER_LOAN_REPAY", "DEBTS_OWED_BY",
          "TTL_INDIV_CONTRIB", "CAND_OFFICE_ST", "CAND_OFFICE_DISTRICT", "SPEC_ELECTION",
          "PRIM_ELECTION", "RUN_ELECTION", "GEN_ELECTION", "GEN_ELECTION_PRECENT",
          "OTHER_POL_CMTE_CONTRIB", "POL_PTY_CONTRIB", "CVG_END_DT", "INDIV_REFUNDS",
          "CMTE_REFUNDS"]
# https://www.fec.gov/campaign-finance-data/pac-and-party-summary-file-description/
WEBK = ["CMTE_ID", "CMTE_NM", "CMTE_TP", "CMTE_DSGN", "CMTE_FILING_FREQ", "TTL_RECEIPTS",
        "TRANS_FROM_AFF", "INDV_CONTRIB", "OTHER_POL_CMTE_CONTRIB", "CAND_CONTRIB", "CAND_LOANS",
        "TTL_LOANS_RECEIVED", "TTL_DISB", "TRANF_TO_AFF", "INDV_REFUNDS", "OTHER_POL_CMTE_REFUNDS",
        "CAND_LOAN_REPAY", "LOAN_REPAY", "COH_BOP", "COH_COP", "DEBTS_OWED_BY",
        "NONFED_TRANS_RECEIVED", "CONTRIB_TO_OTHER_CMTE", "IND_EXP", "PTY_COORD_EXP",
        "NONFED_SHARE_EXP", "CVG_END_DT"]
view_zip("weball", fetch("2024/weball24.zip"), WEBALL)
view_zip("webl", fetch("2024/webl24.zip"), WEBALL)
view_zip("webk", fetch("2024/webk24.zip"), WEBK)
view_csv("committee_summary", fetch("2024/committee_summary_2024.csv"))
view_csv("candidate_summary", fetch("2024/candidate_summary_2024.csv"))

con.execute("""
-- An amount as filed: blank is NULL, anything else must cast. Dates: the zips and
-- candidate_summary write MM/DD/YYYY, committee_summary YYYYMMDD.
CREATE MACRO amt(x) AS CAST(nullif(trim(x), '') AS DECIMAL(16, 2));
CREATE MACRO mdy(x) AS CAST(strptime(nullif(trim(x), ''), '%m/%d/%Y') AS DATE);
CREATE MACRO ymd(x) AS CAST(strptime(nullif(trim(x), ''), '%Y%m%d') AS DATE);

-- The committees fundlens credits to each candidate: 04_contribution.sql's `linked` rule over the
-- build's silver link and candidate tables (P or A, or the committee CAND_PCC names; principal
-- first, then the lower candidate_id). A handed-off committee (fec/handoffs.csv) is listed under
-- both its candidates, `handoff` true: a cycle-to-date summary row cannot be split at the date.
CREATE TABLE credited AS
SELECT link.committee_id, link.candidate_id, false AS handoff
FROM silver.candidate_committee_link AS link
LEFT JOIN silver.candidate AS candidate USING (candidate_id)
WHERE (link.designation IN ('P', 'A') OR link.committee_id = candidate.principal_committee_id)
    AND link.committee_id NOT IN (SELECT committee_id FROM handoff)
QUALIFY row_number() OVER (
    PARTITION BY link.committee_id
    ORDER BY (link.designation = 'P' OR link.committee_id = candidate.principal_committee_id) DESC,
        link.candidate_id
) = 1
UNION ALL
SELECT committee_id, from_candidate_id, true FROM handoff
UNION ALL
SELECT committee_id, to_candidate_id, true FROM handoff;
""")

con.execute("""
-- committee_summary repeats a committee once per candidate it is linked to, every other column
-- the same (Q1b): `cs` is one row per committee, CAND_ID dropped.
CREATE VIEW cs AS
SELECT * EXCLUDE (CAND_ID, Link_Image) FROM committee_summary
QUALIFY row_number() OVER (PARTITION BY CMTE_ID ORDER BY CAND_ID) = 1;
""")


def compare(title: str, joined: str, measures: list[str], a: str = "a", b: str = "b") -> None:
    """Per measure, over `joined` (columns <a>_<m> and <b>_<m>, NULL where a side has no value):
    rows with both sides, equal within $1, within 1% beyond that, beyond 1%, and the differences."""
    parts = []
    for m in measures:
        d = f"({a}_{m} - {b}_{m})"
        parts.append(f"""
        SELECT '{m}' AS measure, count(*) FILTER (WHERE {d} IS NOT NULL) AS both_sides,
            count(*) FILTER (WHERE abs({d}) <= 1) AS within_1_dollar,
            count(*) FILTER (WHERE abs({d}) > 1
                AND abs({d}) <= 0.01 * greatest(abs({a}_{m}), abs({b}_{m}))) AS within_1_pct,
            count(*) FILTER (WHERE abs({d}) > 1
                AND abs({d}) > 0.01 * greatest(abs({a}_{m}), abs({b}_{m}))) AS beyond_1_pct,
            count(*) FILTER (WHERE abs({d}) <= 1) / count(*) FILTER (WHERE {d} IS NOT NULL)::DOUBLE
                AS share_within_1_dollar,
            sum({a}_{m}) AS sum_{a}, sum({b}_{m}) AS sum_{b}, sum(abs({d})) AS sum_abs_diff,
            max(abs({d})) AS max_abs_diff
        FROM ({joined})""")
    show(title, " UNION ALL ".join(parts))

con.execute("""
-- Coverage per committee (Q5): fundlens's measure A (total_individual) and B (A plus
-- total_from_organizations), live gold, net of refunds; FEC's committee_summary figures as filed.
CREATE MACRO grp(t) AS CASE WHEN t IN ('H', 'S', 'P') THEN 'candidate' WHEN t IN ('O', 'U') THEN 'super PAC'
    WHEN t IN ('V', 'W') THEN 'hybrid PAC' WHEN t IN ('X', 'Y', 'Z') THEN 'party' WHEN t IN ('N', 'Q') THEN 'PAC'
    ELSE 'other' END;
CREATE TABLE cov AS
SELECT g.committee_id, c.CMTE_NM AS name, c.CMTE_TP AS type, grp(c.CMTE_TP) AS grp,
    CAST(g.total_individual AS DECIMAL(16, 2)) AS a,
    CAST(g.total_individual + g.total_from_organizations AS DECIMAL(16, 2)) AS b,
    CAST(g.total_from_organizations AS DECIMAL(16, 2)) AS orgs,
    amt(c.INDV_ITEM_CONTB) AS item, amt(c.INDV_UNITEM_CONTB) AS unitem, amt(c.INDV_CONTB) AS total,
    amt(c.INDV_REF) AS refunds, ymd(c.CVG_END_DT) AS cvg_end
FROM gold_cc AS g JOIN cs AS c ON c.CMTE_ID = g.committee_id;
-- Over 1%: fundlens above FEC's itemized figure by more than 1% of it, on A or B (FEC's figure 0
-- or blank counts as 0, so any fundlens dollar over it is over; a negative one by its size).
CREATE VIEW over AS
SELECT *, b - coalesce(item, 0) AS excess_b, a - coalesce(item, 0) AS excess_a,
    (a - coalesce(item, 0)) / nullif(item, 0) AS excess_a_pct, (b - coalesce(item, 0)) / nullif(item, 0) AS excess_b_pct
FROM cov
WHERE a - coalesce(item, 0) > 0.01 * abs(coalesce(item, 0)) OR b - coalesce(item, 0) > 0.01 * abs(coalesce(item, 0));
""")
```

### Q0: the run's provenance

```python
import os
import duckdb
with psycopg.connect(settings.database_url) as pg:
    pg.read_only = True
    print("gold.meta:", pg.execute("SELECT build_id, published_at, cycles FROM gold.meta").fetchone())
print("OTEL_RESOURCE_ATTRIBUTES:", os.environ.get("OTEL_RESOURCE_ATTRIBUTES"))
print("duckdb", duckdb.__version__, Limits.from_settings(settings))
print("silver build", BUILD)
```

```text
build 20261105T205814Z
gold.meta: ('20261105T205814Z', datetime.datetime(2026, 11, 5, 22, 9, 56, 185730, tzinfo=zoneinfo.ZoneInfo(key='Etc/UTC')), {'2024': {'build_id': '20261105T205814Z', 'source_dates': {'cm': '2026-10-31', 'cn': '2026-10-31', 'ccl': '2026-10-31', 'oth': '2026-10-31', 'pas2': '2026-10-31', 'indiv': '2026-10-31'}}})
OTEL_RESOURCE_ATTRIBUTES: service.name=fundlens-pipeline,deployment.environment=production,service.version=d82c07076f0de2cd3bb5bd7ecc4c8d58d4bb712c
duckdb 2.0.0 Limits(memory_limit='28GB', max_temp_directory_size='60GB', threads=6)
silver build 20261105T205814Z
```

## Q1: grain, keys and overlap (2024)

```python
show("Q1a: rows and keys per file", """
SELECT 'weball' AS file, count(*) AS rows, count(DISTINCT CAND_ID) AS keys, NULL AS election_years,
    min(mdy(CVG_END_DT)) AS cvg_end_min, median(mdy(CVG_END_DT)) AS cvg_end_median,
    max(mdy(CVG_END_DT)) AS cvg_end_max,
    count(*) FILTER (WHERE mdy(CVG_END_DT) <= DATE '2024-12-31') AS cvg_end_by_2024_12_31
FROM weball
UNION ALL
SELECT 'webl', count(*), count(DISTINCT CAND_ID), NULL, min(mdy(CVG_END_DT)),
    median(mdy(CVG_END_DT)), max(mdy(CVG_END_DT)),
    count(*) FILTER (WHERE mdy(CVG_END_DT) <= DATE '2024-12-31')
FROM webl
UNION ALL
SELECT 'webk', count(*), count(DISTINCT CMTE_ID), NULL, min(mdy(CVG_END_DT)),
    median(mdy(CVG_END_DT)), max(mdy(CVG_END_DT)),
    count(*) FILTER (WHERE mdy(CVG_END_DT) <= DATE '2024-12-31')
FROM webk
UNION ALL
SELECT 'committee_summary', count(*), count(DISTINCT CMTE_ID),
    string_agg(DISTINCT FEC_ELECTION_YR, ', ' ORDER BY FEC_ELECTION_YR), min(ymd(CVG_END_DT)),
    median(ymd(CVG_END_DT)), max(ymd(CVG_END_DT)),
    count(*) FILTER (WHERE ymd(CVG_END_DT) <= DATE '2024-12-31')
FROM committee_summary
UNION ALL
SELECT 'candidate_summary', count(*), count(DISTINCT Cand_Id), NULL, min(mdy(Coverage_End_Date)),
    median(mdy(Coverage_End_Date)), max(mdy(Coverage_End_Date)),
    count(*) FILTER (WHERE mdy(Coverage_End_Date) <= DATE '2024-12-31')
FROM candidate_summary
""")

show("Q1b: duplicate keys", """
SELECT 'weball' AS file, CAND_ID AS key, count(*) AS rows FROM weball GROUP BY ALL HAVING count(*) > 1
UNION ALL SELECT 'webl', CAND_ID, count(*) FROM webl GROUP BY ALL HAVING count(*) > 1
UNION ALL SELECT 'webk', CMTE_ID, count(*) FROM webk GROUP BY ALL HAVING count(*) > 1
UNION ALL SELECT 'committee_summary', CMTE_ID, count(*) FROM committee_summary GROUP BY ALL HAVING count(*) > 1
UNION ALL SELECT 'candidate_summary', Cand_Id, count(*) FROM candidate_summary GROUP BY ALL HAVING count(*) > 1
ORDER BY 1, 2
""")

show("Q1c: committee_summary rows by FEC_ELECTION_YR and CMTE_TP group", """
SELECT FEC_ELECTION_YR,
    CASE WHEN CMTE_TP IN ('H', 'S', 'P') THEN CMTE_TP WHEN CMTE_TP IN ('O', 'U') THEN 'O/U super PAC'
        WHEN CMTE_TP IN ('X', 'Y', 'Z') THEN 'X/Y/Z party' WHEN CMTE_TP IN ('N', 'Q') THEN 'N/Q PAC'
        ELSE coalesce(CMTE_TP, '(blank)') END AS type, count(*) AS rows,
    sum(amt(TTL_RECEIPTS)) AS ttl_receipts
FROM committee_summary GROUP BY ALL ORDER BY ALL
""")

show("Q1d: candidates in weball vs candidate_summary", """
SELECT 'weball only' AS side, left(w.CAND_ID, 1) AS office, count(*) AS candidates,
    sum(amt(w.TTL_RECEIPTS)) AS ttl_receipts
FROM weball AS w ANTI JOIN candidate_summary AS c ON c.Cand_Id = w.CAND_ID GROUP BY ALL
UNION ALL
SELECT 'candidate_summary only', left(c.Cand_Id, 1), count(*), sum(amt(c.Total_Receipt))
FROM candidate_summary AS c ANTI JOIN weball AS w ON w.CAND_ID = c.Cand_Id GROUP BY ALL
UNION ALL
SELECT 'both', left(w.CAND_ID, 1), count(*), sum(amt(w.TTL_RECEIPTS))
FROM weball AS w SEMI JOIN candidate_summary AS c ON c.Cand_Id = w.CAND_ID GROUP BY ALL
ORDER BY 1, 2
""")

show("Q1e: webl vs weball", """
WITH l AS (SELECT * FROM webl), w AS (SELECT * FROM weball)
SELECT 'webl only' AS side, count(*) AS candidates, sum(amt(l.TTL_RECEIPTS)) AS ttl_receipts
FROM l ANTI JOIN w ON w.CAND_ID = l.CAND_ID
UNION ALL
SELECT 'weball only', count(*), sum(amt(w.TTL_RECEIPTS)) FROM w ANTI JOIN l ON l.CAND_ID = w.CAND_ID
UNION ALL
SELECT 'both, every measure equal', count(*), sum(amt(w.TTL_RECEIPTS))
FROM w JOIN l USING (CAND_ID)
WHERE (w.TTL_RECEIPTS, w.TTL_DISB, w.COH_BOP, w.COH_COP, w.DEBTS_OWED_BY, w.TTL_INDIV_CONTRIB,
       w.OTHER_POL_CMTE_CONTRIB, w.POL_PTY_CONTRIB, w.CAND_CONTRIB, w.CAND_LOANS, w.TRANS_FROM_AUTH,
       w.TRANS_TO_AUTH, w.CVG_END_DT)
    IS NOT DISTINCT FROM
      (l.TTL_RECEIPTS, l.TTL_DISB, l.COH_BOP, l.COH_COP, l.DEBTS_OWED_BY, l.TTL_INDIV_CONTRIB,
       l.OTHER_POL_CMTE_CONTRIB, l.POL_PTY_CONTRIB, l.CAND_CONTRIB, l.CAND_LOANS, l.TRANS_FROM_AUTH,
       l.TRANS_TO_AUTH, l.CVG_END_DT)
UNION ALL
SELECT 'both, some measure differs', count(*), sum(amt(w.TTL_RECEIPTS))
FROM w JOIN l USING (CAND_ID)
WHERE (w.TTL_RECEIPTS, w.TTL_DISB, w.COH_BOP, w.COH_COP, w.DEBTS_OWED_BY, w.TTL_INDIV_CONTRIB,
       w.OTHER_POL_CMTE_CONTRIB, w.POL_PTY_CONTRIB, w.CAND_CONTRIB, w.CAND_LOANS, w.TRANS_FROM_AUTH,
       w.TRANS_TO_AUTH, w.CVG_END_DT)
    IS DISTINCT FROM
      (l.TTL_RECEIPTS, l.TTL_DISB, l.COH_BOP, l.COH_COP, l.DEBTS_OWED_BY, l.TTL_INDIV_CONTRIB,
       l.OTHER_POL_CMTE_CONTRIB, l.POL_PTY_CONTRIB, l.CAND_CONTRIB, l.CAND_LOANS, l.TRANS_FROM_AUTH,
       l.TRANS_TO_AUTH, l.CVG_END_DT)
""")

show("Q1e2: webl and weball by office", """
SELECT left(CAND_ID, 1) AS office, (SELECT count(*) FROM webl AS l WHERE left(l.CAND_ID, 1) = left(w.CAND_ID, 1)) AS webl_rows,
    count(*) AS weball_rows
FROM weball AS w GROUP BY ALL ORDER BY 1
""")

show("Q1e3: committee_summary's repeated rows: committees, rows, distinct rows less CAND_ID", """
WITH d AS (
    SELECT * EXCLUDE (CAND_ID, Link_Image) FROM committee_summary
    WHERE CMTE_ID IN (SELECT CMTE_ID FROM committee_summary GROUP BY ALL HAVING count(*) > 1)
)
SELECT count(DISTINCT CMTE_ID) AS committees, count(*) AS rows,
    (SELECT count(*) FROM (SELECT DISTINCT * FROM d)) AS distinct_rows_less_cand_id
FROM d
""")

show("Q1e4: candidates in weball or candidate_summary, by silver candidate election year", """
SELECT CASE WHEN c.election_year IS NULL THEN 'not in cn' WHEN c.election_year < 2023 THEN 'before 2023'
        WHEN c.election_year > 2024 THEN 'after 2024' ELSE c.election_year::VARCHAR END AS cn_election_year,
    count(*) FILTER (WHERE w.CAND_ID IS NOT NULL) AS in_weball,
    sum(amt(w.TTL_RECEIPTS)) AS weball_receipts,
    count(*) FILTER (WHERE s.Cand_Id IS NOT NULL) AS in_candidate_summary,
    sum(amt(s.Total_Receipt)) AS candidate_summary_receipts,
    count(*) FILTER (WHERE w.CAND_ID IS NOT NULL AND s.Cand_Id IS NOT NULL) AS in_both
FROM weball AS w
FULL JOIN candidate_summary AS s ON s.Cand_Id = w.CAND_ID
LEFT JOIN silver.candidate AS c ON c.candidate_id = coalesce(w.CAND_ID, s.Cand_Id)
GROUP BY ALL ORDER BY 1
""")

show("Q1f: weball candidates by credited committees in committee_summary", """
WITH n AS (
    SELECT w.CAND_ID, amt(w.TTL_RECEIPTS) AS receipts,
        count(DISTINCT cr.committee_id) AS credited,
        count(DISTINCT cs.CMTE_ID) AS credited_in_summary
    FROM weball AS w
    LEFT JOIN credited AS cr ON cr.candidate_id = w.CAND_ID
    LEFT JOIN committee_summary AS cs ON cs.CMTE_ID = cr.committee_id
    GROUP BY ALL
),
pa AS (
    SELECT DISTINCT candidate_id FROM silver.candidate_committee_link WHERE designation IN ('P', 'A')
)
SELECT
    CASE WHEN credited_in_summary > 0 THEN 'credited committee in committee_summary'
        WHEN credited > 0 THEN 'credited committee(s), none in committee_summary'
        WHEN CAND_ID IN (SELECT candidate_id FROM pa) THEN 'no credited committee, a P/A link (an alias?)'
        WHEN CAND_ID IN (SELECT candidate_id FROM silver.candidate) THEN 'in cn, no P/A committee'
        ELSE 'not in cn' END AS status,
    count(*) AS candidates, sum(receipts) AS weball_ttl_receipts,
    count(*) FILTER (WHERE receipts <> 0) AS with_receipts
FROM n GROUP BY ALL ORDER BY 2 DESC
""")

show("Q1g: committee_summary committees credited to a candidate not in weball", """
SELECT left(cr.candidate_id, 1) AS office, count(*) AS committees,
    sum(amt(cs.TTL_RECEIPTS)) AS ttl_receipts,
    string_agg(cs.CMTE_ID || ' ' || cr.candidate_id, ', ' ORDER BY amt(cs.TTL_RECEIPTS) DESC)
        FILTER (WHERE amt(cs.TTL_RECEIPTS) >= 100000) AS largest
FROM committee_summary AS cs
JOIN credited AS cr ON cr.committee_id = cs.CMTE_ID
ANTI JOIN weball AS w ON w.CAND_ID = cr.candidate_id
GROUP BY ALL ORDER BY 1
""")

show("Q1h: webk vs committee_summary, by CMTE_TP", """
SELECT 'webk only' AS side, k.CMTE_TP, count(*) AS committees, sum(amt(k.TTL_RECEIPTS)) AS ttl_receipts
FROM webk AS k ANTI JOIN committee_summary AS cs ON cs.CMTE_ID = k.CMTE_ID GROUP BY ALL
UNION ALL
SELECT 'committee_summary only', cs.CMTE_TP, count(*), sum(amt(cs.TTL_RECEIPTS))
FROM committee_summary AS cs ANTI JOIN webk AS k ON k.CMTE_ID = cs.CMTE_ID GROUP BY ALL
UNION ALL
SELECT 'both', k.CMTE_TP, count(*), sum(amt(k.TTL_RECEIPTS))
FROM webk AS k SEMI JOIN committee_summary AS cs ON cs.CMTE_ID = k.CMTE_ID GROUP BY ALL
ORDER BY 1, 2
""")

show("Q1i: committee_summary vs silver committee (cm), by CMTE_TP", """
SELECT 'committee_summary only' AS side, cs.CMTE_TP AS type, count(*) AS committees,
    sum(amt(cs.TTL_RECEIPTS)) AS ttl_receipts
FROM committee_summary AS cs ANTI JOIN silver.committee AS c ON c.committee_id = cs.CMTE_ID GROUP BY ALL
UNION ALL
SELECT 'silver committee only', c.type, count(*), NULL
FROM silver.committee AS c ANTI JOIN committee_summary AS cs ON cs.CMTE_ID = c.committee_id GROUP BY ALL
UNION ALL
SELECT 'both', cs.CMTE_TP, count(*), sum(amt(cs.TTL_RECEIPTS))
FROM committee_summary AS cs SEMI JOIN silver.committee AS c ON c.committee_id = cs.CMTE_ID GROUP BY ALL
ORDER BY 1, 2
""")

show("Q1j: committee counts NEU-2143 checks against", """
SELECT (SELECT count(*) FROM committee_summary) AS committee_summary_rows,
    (SELECT count(DISTINCT CMTE_ID) FROM committee_summary) AS committee_summary_committees,
    (SELECT count(*) FROM silver.committee) AS silver_committees,
    (SELECT count(*) FROM committee_summary AS cs SEMI JOIN silver.committee AS c
        ON c.committee_id = cs.CMTE_ID) AS in_both,
    (SELECT count(*) FROM gold_cc) AS gold_committee_cycle_rows
""")
```

**Q1a: rows and keys per file  (0 s)**

| file | rows | keys | election_years | cvg_end_min | cvg_end_median | cvg_end_max | cvg_end_by_2024_12_31 |
|---|---|---|---|---|---|---|---|
| weball | 3,857 | 3,857 |  | 2023-01-01 | 2024-12-31 00:00:00 | 2025-01-31 | 3,854 |
| webl | 2,378 | 2,378 |  | 2023-01-26 | 2024-12-31 00:00:00 | 2025-01-31 | 2,375 |
| webk | 12,379 | 12,379 |  | 2023-01-01 | 2024-12-31 00:00:00 | 2025-06-30 | 10,119 |
| committee_summary | 14,066 | 13,995 | 2024 | 2023-01-01 | 2024-12-31 00:00:00 | 2025-06-30 | 14,056 |
| candidate_summary | 5,302 | 5,302 |  | 2023-02-10 | 2024-12-31 00:00:00 | 2025-01-31 | 2,317 |

**Q1b: duplicate keys  (0 s)**

| file | key | rows |
|---|---|---|
| committee_summary | C00343871 | 2 |
| committee_summary | C00447474 | 2 |
| committee_summary | C00548289 | 2 |
| committee_summary | C00558627 | 2 |
| committee_summary | C00577999 | 2 |
| committee_summary | C00647339 | 2 |
| committee_summary | C00648220 | 2 |
| committee_summary | C00653196 | 2 |
| committee_summary | C00680728 | 2 |
| committee_summary | C00703975 | 2 |
| committee_summary | C00720573 | 2 |
| committee_summary | C00721787 | 2 |
| committee_summary | C00726117 | 2 |
| committee_summary | C00727164 | 2 |
| committee_summary | C00749226 | 2 |
| committee_summary | C00769463 | 2 |
| committee_summary | C00778423 | 2 |
| committee_summary | C00794362 | 3 |
| committee_summary | C00805473 | 2 |
| committee_summary | C00815563 | 2 |
| committee_summary | C00819672 | 2 |
| committee_summary | C00821306 | 2 |
| committee_summary | C00823435 | 2 |
| committee_summary | C00826354 | 2 |
| committee_summary | C00829523 | 2 |
| committee_summary | C00830661 | 3 |
| committee_summary | C00837377 | 3 |
| committee_summary | C00837567 | 2 |
| committee_summary | C00839332 | 2 |
| committee_summary | C00842336 | 2 |
| committee_summary | C00844654 | 2 |
| committee_summary | C00844993 | 2 |
| committee_summary | C00845560 | 2 |
| committee_summary | C00845750 | 2 |
| committee_summary | C00846048 | 2 |
| committee_summary | C00846402 | 4 |
| committee_summary | C00846451 | 2 |
| committee_summary | C00847384 | 2 |
| committee_summary | C00847939 | 2 |
| committee_summary | C00848838 | 2 |
| committee_summary | C00849984 | 2 |
| committee_summary | C00850354 | 2 |
| committee_summary | C00850636 | 2 |
| committee_summary | C00851006 | 2 |
| committee_summary | C00853317 | 3 |
| committee_summary | C00855676 | 2 |
| committee_summary | C00858209 | 2 |
| committee_summary | C00858811 | 2 |
| committee_summary | C00865170 | 2 |
| committee_summary | C00866293 | 2 |
| committee_summary | C00866988 | 2 |
| committee_summary | C00869974 | 2 |
| committee_summary | C00870139 | 2 |
| committee_summary | C00870451 | 2 |
| committee_summary | C00870600 | 2 |
| committee_summary | C00872952 | 2 |
| committee_summary | C00875286 | 2 |
| committee_summary | C00876490 | 2 |
| committee_summary | C00878454 | 2 |
| committee_summary | C00881177 | 2 |
| committee_summary | C00881458 | 2 |
| committee_summary | C00881599 | 2 |
| committee_summary | C00882662 | 2 |
| committee_summary | C00888511 | 2 |
| committee_summary | C00889030 | 2 |

**Q1c: committee_summary rows by FEC_ELECTION_YR and CMTE_TP group  (0 s)**

| FEC_ELECTION_YR | type | rows | ttl_receipts |
|---|---|---|---|
| 2024 | (blank) | 1 | 2,000 |
| 2024 | C | 68 |  |
| 2024 | H | 3,234 | 2,133,492,366 |
| 2024 | I | 208 |  |
| 2024 | N/Q PAC | 6,367 | 6,018,782,401 |
| 2024 | O/U super PAC | 2,082 | 5,110,306,354 |
| 2024 | P | 176 | 2,659,147,257 |
| 2024 | S | 669 | 1,921,113,692 |
| 2024 | V | 644 | 7,097,691,808 |
| 2024 | W | 137 | 991,390,804 |
| 2024 | X/Y/Z party | 480 | 3,713,277,518 |

**Q1d: candidates in weball vs candidate_summary  (0 s)**

| side | office | candidates | ttl_receipts |
|---|---|---|---|
| both | H | 1,911 | 2,085,707,878 |
| both | P | 136 | 2,681,688,716 |
| both | S | 273 | 1,508,521,039 |
| candidate_summary only | H | 1,167 | 0 |
| candidate_summary only | P | 1,466 | 0 |
| candidate_summary only | S | 349 | 0 |
| weball only | H | 1,162 | 318,040,583 |
| weball only | P | 39 | 36,446,076 |
| weball only | S | 336 | 215,691,261 |

**Q1e: webl vs weball  (0 s)**

| side | candidates | ttl_receipts |
|---|---|---|
| webl only | 0 |  |
| weball only | 1,479 | 342,977,715 |
| both, every measure equal | 2,378 | 6,503,117,839 |
| both, some measure differs | 0 |  |

**Q1e2: webl and weball by office  (0 s)**

| office | webl_rows | weball_rows |
|---|---|---|
| H | 1,926 | 3,073 |
| P | 175 | 175 |
| S | 277 | 609 |

**Q1e3: committee_summary's repeated rows: committees, rows, distinct rows less CAND_ID  (1 s)**

| committees | rows | distinct_rows_less_cand_id |
|---|---|---|
| 65 | 136 | 65 |

**Q1e4: candidates in weball or candidate_summary, by silver candidate election year  (0 s)**

| cn_election_year | in_weball | weball_receipts | in_candidate_summary | candidate_summary_receipts | in_both |
|---|---|---|---|---|---|
| 2023 | 22 | 4,541,224 | 107 | 4,541,224 | 22 |
| 2024 | 2,315 | 6,461,830,035 | 5,195 | 6,271,376,410 | 2,298 |
| after 2024 | 120 | 206,284,794 | 0 |  | 0 |
| before 2023 | 1,393 | 137,708,996 | 0 |  | 0 |
| not in cn | 7 | 35,730,504 | 0 |  | 0 |

**Q1f: weball candidates by credited committees in committee_summary  (0 s)**

| status | candidates | weball_ttl_receipts | with_receipts |
|---|---|---|---|
| credited committee in committee_summary | 3,661 | 6,400,992,004 | 2,726 |
| in cn, no P/A committee | 106 | 351,319,033 | 77 |
| no credited committee, a P/A link (an alias?) | 80 | 53,691,995 | 63 |
| credited committee(s), none in committee_summary | 10 | 40,092,522 | 4 |

**Q1g: committee_summary committees credited to a candidate not in weball  (0 s)**

| office | committees | ttl_receipts | largest |
|---|---|---|---|
| H | 71 | 13,633,522 | C00651042 H8AZ01104, C00610212 H6WI08155, C00607556 H6WY00159, C00476820 H0OH06189, C00401034 H4NY27076, C00768101 H2GA14044, C00590489 H2FL08063, C00691790 H0CA04167, C00620443 H6FL07140, C00178418 H2VA09010, C00393348 H4TX24094, C00656686 H8NJ07223, C00573378 H4CO04090 |
| P | 8 | 1,670,594 | C00573519 P60005915, C00581876 P60003670 |
| S | 25 | 25,205,556 | C00771972 S2MO00528, C00784959 S2WI00441, C00711549 S0KY00339, C00640623 S0AL00156, C00461046 S4PA00121, C00304758 S0MO00183 |

**Q1h: webk vs committee_summary, by CMTE_TP  (1 s)**

| side | CMTE_TP | committees | ttl_receipts |
|---|---|---|---|
| both | C | 68 | 0 |
| both | H | 76 | 16,281,203 |
| both | I | 207 | 23,101,598 |
| both | N | 3,094 | 4,161,548,218 |
| both | O | 2,063 | 5,100,366,933 |
| both | P | 1 | 224 |
| both | Q | 3,273 | 1,857,221,822 |
| both | S | 69 | 9,768,699 |
| both | U | 19 | 10,112,022 |
| both | V | 644 | 7,097,691,808 |
| both | W | 137 | 991,390,804 |
| both | X | 241 | 296,609,996 |
| both | Y | 239 | 3,416,645,502 |
| committee_summary only | H | 3,158 | 2,117,211,163 |
| committee_summary only | I | 1 |  |
| committee_summary only | P | 175 | 2,659,147,033 |
| committee_summary only | S | 600 | 1,911,344,993 |
| committee_summary only |  | 1 | 2,000 |
| webk only | C | 42 |  |
| webk only | E | 122 |  |
| webk only | H | 17 |  |
| webk only | I | 649 | 268,710,400 |
| webk only | N | 557 | 0 |
| webk only | O | 473 |  |
| webk only | P | 10 |  |
| webk only | Q | 33 |  |
| webk only | S | 6 |  |
| webk only | U | 52 |  |
| webk only | V | 113 |  |
| webk only | W | 5 |  |
| webk only | X | 167 | 0 |
| webk only | Y | 2 |  |

**Q1i: committee_summary vs silver committee (cm), by CMTE_TP  (1 s)**

| side | type | committees | ttl_receipts |
|---|---|---|---|
| both | C | 68 |  |
| both | H | 3,234 | 2,133,492,366 |
| both | I | 207 |  |
| both | N | 3,094 | 4,161,560,579 |
| both | O | 2,063 | 5,100,194,333 |
| both | P | 176 | 2,659,147,257 |
| both | Q | 3,273 | 1,857,221,822 |
| both | S | 669 | 1,921,113,692 |
| both | U | 19 | 10,112,022 |
| both | V | 644 | 7,097,691,808 |
| both | W | 137 | 991,390,804 |
| both | X | 241 | 296,632,016 |
| both | Y | 239 | 3,416,645,502 |
| both |  | 1 | 2,000 |
| committee_summary only | I | 1 |  |
| silver committee only | C | 42 |  |
| silver committee only | E | 121 |  |
| silver committee only | H | 2,589 |  |
| silver committee only | I | 646 |  |
| silver committee only | N | 468 |  |
| silver committee only | O | 444 |  |
| silver committee only | P | 1,692 |  |
| silver committee only | Q | 33 |  |
| silver committee only | S | 604 |  |
| silver committee only | U | 49 |  |
| silver committee only | V | 111 |  |
| silver committee only | W | 5 |  |
| silver committee only | X | 132 |  |
| silver committee only | Y | 2 |  |
| silver committee only |  | 5 |  |

**Q1j: committee counts NEU-2143 checks against  (1 s)**

| committee_summary_rows | committee_summary_committees | silver_committees | in_both | gold_committee_cycle_rows |
|---|---|---|---|---|
| 14,066 | 13,995 | 20,937 | 14,065 | 20,937 |

**Reading.**

- **`committee_summary`'s grain is committee × linked candidate**, not committee. 65 committees
  appear more than once, 136 rows in all, and the rows differ only in `CAND_ID`. Harris for
  President (C00703975) is under both Biden and Harris. Schiff for Senate is under his House and
  Senate ids. Summing it unduplicated would count those committees twice, so every query below
  reads `cs`. The file carries one `FEC_ELECTION_YR`, 2024, so there are no special-election rows
  from 2023.
- **`webl` is a subset of `weball`'s rows.** All 2,378 of its candidates are in `weball` with every
  measure identical. It holds presidential candidates too (175), despite its name. `weball` adds
  1,479 House and Senate candidates whose committees were active in 2023–24 but who are not 2024
  candidates.
- **`weball` and `candidate_summary` hold different populations.** `weball` lists every candidate
  id with an active committee in the 2024 cycle. 1,393 are candidates of an earlier cycle,
  120 of a later one, 7 are not in `cn`, and 17 are 2024 candidates without a `candidate_summary`
  row. Those 1,537 rows carry $570.2M of receipts.
  `candidate_summary` lists every candidate standing in 2024, including 2,982 with no money.
  2,320 candidates are in both.
- 3,661 `weball` candidates have a credited committee in `committee_summary`. 106 are in `cn` with
  no P or A committee ($351.3M). 80 have a P/A link but no credited committee, because the committee
  is credited to another of their ids or they are aliases ($53.7M; Q3m). 10 have credited committees
  that `committee_summary` lacks ($40.1M).
- **`webk` against `committee_summary`.** 10,131 committees are in both. The 2,248 only in `webk`
  carry no receipts or disbursements, except one Form 5 record: C90022021, "THE COMMITTEE OF 99 FOR
  GAMBERT, JASON", $268.7M of receipts with a 2023-03-31 coverage end, plainly a bad filing. Of the
  3,935 only in `committee_summary`, 3,933 are candidate committees (H, S, P), which `webk` does not
  cover. The other two are one type-I row and one untyped row, both without figures.
- **The committee count for NEU-2143: 13,995 committees** (14,066 rows) in `committee_summary_2024`.
  13,994 of them are silver committees. The one that is not is type I with no figures. 6,943 silver
  committees have no summary row, and none holds fundlens money (Q5b).

## Q2: `webk` against `committee_summary` (PACs and parties), and `webl` against the credited committees

```python
WEBK_PAIRS = {  # measure: (webk column, committee_summary column)
    "receipts": ("TTL_RECEIPTS", "TTL_RECEIPTS"), "disbursements": ("TTL_DISB", "TTL_DISB"),
    "coh_start": ("COH_BOP", "COH_BOP"), "coh_end": ("COH_COP", "COH_COP"),
    "debts_owed_by": ("DEBTS_OWED_BY", "DEBTS_OWED_BY_CMTE"), "indiv_total": ("INDV_CONTRIB", "INDV_CONTB"),
    "other_committees": ("OTHER_POL_CMTE_CONTRIB", "OTH_CMTE_CONTB"),
    "transfers_in": ("TRANS_FROM_AFF", "TRANF_FROM_OTHER_AUTH_CMTE"), "indiv_refunds": ("INDV_REFUNDS", "INDV_REF"),
}
cols = ", ".join(f"amt(k.{w}) AS k_{m}, amt(c.{s}) AS c_{m}" for m, (w, s) in WEBK_PAIRS.items())
con.execute(f"""
CREATE TABLE webk_cs AS
SELECT k.CMTE_ID, k.CMTE_NM, k.CMTE_TP, mdy(k.CVG_END_DT) AS k_cvg_end, ymd(c.CVG_END_DT) AS c_cvg_end, {cols}
FROM webk AS k JOIN cs AS c USING (CMTE_ID)
""")
compare("Q2a: webk vs committee_summary, committees in both", "SELECT * FROM webk_cs", list(WEBK_PAIRS), "k", "c")

show("Q2b: webk vs committee_summary: coverage end dates", """
SELECT count(*) AS committees, count(*) FILTER (WHERE k_cvg_end IS NOT DISTINCT FROM c_cvg_end) AS same_cvg_end,
    count(*) FILTER (WHERE k_cvg_end < c_cvg_end) AS webk_earlier, count(*) FILTER (WHERE k_cvg_end > c_cvg_end) AS webk_later,
    count(*) FILTER (WHERE k_cvg_end IS NULL OR c_cvg_end IS NULL) AS a_side_blank
FROM webk_cs
""")

show("Q2c: webk vs committee_summary: the 20 largest receipts differences", """
SELECT CMTE_ID, CMTE_NM, CMTE_TP, k_receipts, c_receipts, k_receipts - c_receipts AS diff,
    k_coh_end - c_coh_end AS coh_end_diff, k_cvg_end, c_cvg_end
FROM webk_cs WHERE abs(k_receipts - c_receipts) > 1 OR (k_receipts IS NULL) <> (c_receipts IS NULL)
ORDER BY abs(coalesce(k_receipts, 0) - coalesce(c_receipts, 0)) DESC LIMIT 20
""")

show("Q2d: webk committees by whether committee_summary holds them and whether they carry money", """
SELECT k.CMTE_TP, CMTE_ID IN (SELECT CMTE_ID FROM cs) AS in_committee_summary,
    coalesce(amt(k.TTL_RECEIPTS), 0) <> 0 OR coalesce(amt(k.TTL_DISB), 0) <> 0
        OR coalesce(amt(k.COH_COP), 0) <> 0 AS has_money,
    count(*) AS committees, sum(amt(k.TTL_RECEIPTS)) AS ttl_receipts, sum(amt(k.TTL_DISB)) AS ttl_disb
FROM webk AS k GROUP BY ALL ORDER BY 2, 1, 3
""")

show("Q2e: webk committees with money that committee_summary lacks: the 15 largest", """
SELECT k.CMTE_ID, k.CMTE_NM, k.CMTE_TP, k.CMTE_DSGN, amt(k.TTL_RECEIPTS) AS ttl_receipts, amt(k.TTL_DISB) AS ttl_disb,
    amt(k.IND_EXP) AS ind_exp, k.CVG_END_DT
FROM webk AS k ANTI JOIN cs ON cs.CMTE_ID = k.CMTE_ID
WHERE coalesce(amt(k.TTL_RECEIPTS), 0) <> 0 OR coalesce(amt(k.TTL_DISB), 0) <> 0
ORDER BY abs(coalesce(amt(k.TTL_RECEIPTS), 0)) + abs(coalesce(amt(k.TTL_DISB), 0)) DESC LIMIT 15
""")

show("Q2f: the precedence rule (spec §1.1) applied", """
SELECT (SELECT count(*) FROM webk) AS webk_committees,
    (SELECT count(*) FROM webk_cs) AS in_committee_summary,
    (SELECT count(*) FROM webk_cs) / (SELECT count(*) FROM webk)::DOUBLE AS share_held,
    (SELECT count(*) FROM webk WHERE coalesce(amt(TTL_RECEIPTS), 0) <> 0 OR coalesce(amt(TTL_DISB), 0) <> 0) AS webk_with_money,
    (SELECT count(*) FROM webk_cs WHERE coalesce(k_receipts, 0) <> 0 OR coalesce(k_disbursements, 0) <> 0) AS with_money_held,
    (SELECT count(*) FROM webk_cs WHERE abs(coalesce(k_receipts, 0) - coalesce(c_receipts, 0)) <= 1
        AND abs(coalesce(k_disbursements, 0) - coalesce(c_disbursements, 0)) <= 1
        AND abs(coalesce(k_coh_end, 0) - coalesce(c_coh_end, 0)) <= 1) / (SELECT count(*) FROM webk_cs)::DOUBLE
        AS share_shared_agreeing_on_3
""")

show("Q2f2: shared committees agreeing within $1 on receipts, disbursements and cash on hand, by CMTE_TP", """
SELECT CMTE_TP, count(*) AS shared,
    count(*) FILTER (WHERE k_receipts IS NOT DISTINCT FROM c_receipts AND k_disbursements IS NOT DISTINCT FROM c_disbursements
        AND k_coh_end IS NOT DISTINCT FROM c_coh_end) AS identical_incl_blanks,
    count(*) FILTER (WHERE abs(k_receipts - c_receipts) <= 1 AND abs(k_disbursements - c_disbursements) <= 1
        AND abs(k_coh_end - c_coh_end) <= 1) AS agree_both_filled,
    count(*) FILTER (WHERE c_receipts IS NULL AND k_receipts IS NOT NULL) AS cs_receipts_blank_webk_filled,
    count(*) FILTER (WHERE c_disbursements IS NULL AND k_disbursements IS NOT NULL) AS cs_disb_blank_webk_filled,
    count(*) FILTER (WHERE abs(k_receipts - c_receipts) > 1 OR abs(k_disbursements - c_disbursements) > 1
        OR abs(k_coh_end - c_coh_end) > 1) AS disagree_both_filled
FROM webk_cs GROUP BY ALL ORDER BY 1
""")

show("Q2f3: shared committees disagreeing with both sides filled", """
SELECT CMTE_ID, CMTE_NM, CMTE_TP, k_receipts - c_receipts AS receipts_diff, k_disbursements - c_disbursements AS disb_diff,
    k_coh_end - c_coh_end AS coh_end_diff, k_indiv_total - c_indiv_total AS indiv_diff, k_cvg_end, c_cvg_end
FROM webk_cs WHERE abs(k_receipts - c_receipts) > 1 OR abs(k_disbursements - c_disbursements) > 1
    OR abs(k_coh_end - c_coh_end) > 1 OR abs(k_coh_start - c_coh_start) > 1
ORDER BY CMTE_ID
""")

# webl vs the sum of credited committees in committee_summary, House and Senate candidates.
L_PAIRS = {"receipts": ("TTL_RECEIPTS", "TTL_RECEIPTS"), "disbursements": ("TTL_DISB", "TTL_DISB"),
           "coh_end": ("COH_COP", "COH_COP"), "indiv_total": ("TTL_INDIV_CONTRIB", "INDV_CONTB"),
           "transfers_in": ("TRANS_FROM_AUTH", "TRANF_FROM_OTHER_AUTH_CMTE"),
           "transfers_out": ("TRANS_TO_AUTH", "TRANF_TO_OTHER_AUTH_CMTE")}
lcols = ", ".join(f"any_value(amt(l.{w})) AS l_{m}, sum(amt(c.{s})) AS c_{m}" for m, (w, s) in L_PAIRS.items())
con.execute(f"""
CREATE TABLE webl_sum AS
SELECT l.CAND_ID, any_value(l.CAND_NAME) AS name, count(c.CMTE_ID) AS committees, {lcols}
FROM webl AS l
JOIN credited AS cr ON cr.candidate_id = l.CAND_ID
JOIN cs AS c ON c.CMTE_ID = cr.committee_id
WHERE left(l.CAND_ID, 1) IN ('H', 'S')
GROUP BY ALL
""")
compare("Q2g: webl vs the sum of credited committees in committee_summary (H and S, one or more credited)",
        "SELECT * FROM webl_sum", list(L_PAIRS), "l", "c")
show("Q2h: webl receipts vs the credited sum, by committees summed; and whether transfers explain the gap", """
SELECT least(committees, 3) AS committees_summed, count(*) AS candidates,
    count(*) FILTER (WHERE abs(l_receipts - c_receipts) <= 1) AS equal,
    count(*) FILTER (WHERE abs(l_receipts - c_receipts) > 1
        AND abs(l_receipts - (c_receipts - c_transfers_in)) <= 1) AS equal_less_transfers_in,
    count(*) FILTER (WHERE abs(l_receipts - c_receipts) > 1
        AND abs(l_receipts - (c_receipts - c_transfers_in)) > 1) AS neither,
    sum(l_receipts - c_receipts) AS sum_diff, sum(c_transfers_in) AS sum_transfers_in
FROM webl_sum GROUP BY ALL ORDER BY 1
""")
```

**Q2a: webk vs committee_summary, committees in both  (0 s)**

| measure | both_sides | within_1_dollar | within_1_pct | beyond_1_pct | share_within_1_dollar | sum_k | sum_c | sum_abs_diff | max_abs_diff |
|---|---|---|---|---|---|---|---|---|---|
| receipts | 9,845 | 9,843 | 0 | 2 | 99.98% | 22,980,738,826 | 22,957,499,009 | 172,600 | 150,500 |
| disbursements | 9,845 | 9,844 | 0 | 1 | 99.99% | 22,753,187,841 | 22,625,291,863 | 7,159 | 7,159 |
| coh_start | 9,843 | 9,839 | 0 | 4 | 99.96% | 1,477,592,457 | 1,477,799,757 | 87,953 | 47,295 |
| coh_end | 9,833 | 9,832 | 0 | 1 | 99.99% | 1,786,956,257 | 1,787,056,123 | 3,555 | 3,555 |
| debts_owed_by | 9,715 | 9,715 | 0 | 0 | 100.00% | 160,818,250 | 160,818,250 | 0 | 0 |
| indiv_total | 9,836 | 9,770 | 2 | 64 | 99.33% | 15,903,376,211 | 15,902,902,624 | 451,404 | 68,924 |
| other_committees | 9,817 | 9,817 | 0 | 0 | 100.00% | 1,136,684,617 | 1,136,684,617 | 0 | 0 |
| transfers_in | 9,823 | 9,823 | 0 | 0 | 100.00% | 2,430,513,425 | 2,430,513,425 | 0 | 0 |
| indiv_refunds | 9,820 | 9,820 | 0 | 0 | 100.00% | 234,533,179 | 234,533,179 | 0 | 0 |

**Q2b: webk vs committee_summary: coverage end dates  (0 s)**

| committees | same_cvg_end | webk_earlier | webk_later | a_side_blank |
|---|---|---|---|---|
| 10,131 | 10,119 | 0 | 3 | 9 |

**Q2c: webk vs committee_summary: the 20 largest receipts differences  (0 s)**

| CMTE_ID | CMTE_NM | CMTE_TP | k_receipts | c_receipts | diff | coh_end_diff | k_cvg_end | c_cvg_end |
|---|---|---|---|---|---|---|---|---|
| C90018904 | THE CONSERVATIVE CAUCUS DBA AMERICANS FOR CONSTITUTIONAL LIBERTY | I | 10,017,175 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90016627 | WORKER POWER | I | 2,000,000 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90018300 | MID-ATLANTIC LABORERS POLITICAL EDUCATION FUND | I | 1,556,880 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90016106 | AFL-CIO COMMITTEE ON POLITICAL EDUCATION TREASURY FUND | I | 1,546,158 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90019472 | MONTANA RURAL VOTERS (WORC) | I | 1,469,483 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90022476 | STAND UP FOR OHIO (OHIO ORGANIZING CAMPAIGN) | I | 725,000 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90016510 | PLANNED PARENTHOOD ADVOCATES OF WISCONSIN POLITICAL FUND | I | 562,539 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90022229 | BRIGHTER FUTURE ALLIANCE | I | 514,092 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90021692 | 350 WISCONSIN ACTION | I | 361,700 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90016023 | 32BJ UNITED AMERICAN DREAM FUND | I | 337,500 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90022872 | IN UNION USA ACTION | I | 300,995 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90017906 | MI FAMILIA VOTA | I | 300,000 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90017492 | INDIVISIBLE PROJECT INC. | I | 276,960 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90019357 | FOOD AND WATER ACTION | I | 275,195 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90017898 | PROTECT OUR WINTERS ACTION FUND | I | 267,755 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90019902 | NCAAT IN ACTION | I | 266,000 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90018177 | THE WILDERNESS SOCIETY ACTION FUND | I | 250,000 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90011891 | AMERICAN MAJORITY ACTION INC. | I | 200,000 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90022252 | 60 PLUS, ANUZIS | I | 192,379 |  |  |  | 2024-12-31 | 2024-12-31 |
| C90022997 | PAC FOR GEORGIA'S YOUTH | I | 153,999 |  |  |  | 2024-12-31 | 2024-12-31 |

**Q2d: webk committees by whether committee_summary holds them and whether they carry money  (0 s)**

| CMTE_TP | in_committee_summary | has_money | committees | ttl_receipts | ttl_disb |
|---|---|---|---|---|---|
| C | False | False | 42 |  |  |
| E | False | False | 122 |  |  |
| H | False | False | 17 |  |  |
| I | False | False | 648 |  |  |
| I | False | True | 1 | 268,710,400 | 0 |
| N | False | False | 557 | 0 | 0 |
| O | False | False | 473 |  |  |
| P | False | False | 10 |  |  |
| Q | False | False | 33 |  |  |
| S | False | False | 6 |  |  |
| U | False | False | 52 |  |  |
| V | False | False | 113 |  |  |
| W | False | False | 5 |  |  |
| X | False | False | 167 | 0 | 0 |
| Y | False | False | 2 |  |  |
| C | True | False | 2 | 0 | 0 |
| C | True | True | 66 | 0 | 40,533,537 |
| H | True | False | 11 | 0 | 0 |
| H | True | True | 65 | 16,281,203 | 18,508,191 |
| I | True | False | 9 | 0 | 0 |
| I | True | True | 198 | 23,101,598 | 87,393,993 |
| N | True | False | 318 | 0 | 0 |
| N | True | True | 2,776 | 4,161,548,218 | 4,086,885,896 |
| O | True | False | 336 | 0 | 0 |
| O | True | True | 1,727 | 5,100,366,933 | 5,013,884,932 |
| P | True | True | 1 | 224 | 222 |
| Q | True | False | 22 | 0 | 0 |
| Q | True | True | 3,251 | 1,857,221,822 | 1,841,083,092 |
| S | True | False | 2 | 0 | 0 |
| S | True | True | 67 | 9,768,699 | 10,764,655 |
| U | True | False | 5 | 0 | 0 |
| U | True | True | 14 | 10,112,022 | 10,030,463 |
| V | True | False | 91 | 0 | 0 |
| V | True | True | 553 | 7,097,691,808 | 7,009,393,252 |
| W | True | False | 4 | 0 | 0 |
| W | True | True | 133 | 991,390,804 | 981,590,644 |
| X | True | False | 21 | 0 | 0 |
| X | True | True | 220 | 296,609,996 | 274,997,072 |
| Y | True | False | 1 | 0 | 0 |
| Y | True | True | 238 | 3,416,645,502 | 3,378,121,893 |

**Q2e: webk committees with money that committee_summary lacks: the 15 largest  (0 s)**

| CMTE_ID | CMTE_NM | CMTE_TP | CMTE_DSGN | ttl_receipts | ttl_disb | ind_exp | CVG_END_DT |
|---|---|---|---|---|---|---|---|
| C90022021 | THE COMMITTEE OF 99 FOR GAMBERT, JASON | I | U | 268,710,400 | 0 | 0 | 03/31/2023 |

**Q2f: the precedence rule (spec §1.1) applied  (0 s)**

| webk_committees | in_committee_summary | share_held | webk_with_money | with_money_held | share_shared_agreeing_on_3 |
|---|---|---|---|---|---|
| 12,379 | 10,131 | 81.84% | 8,917 | 8,916 | 97.33% |

**Q2f2: shared committees agreeing within $1 on receipts, disbursements and cash on hand, by CMTE_TP  (0 s)**

| CMTE_TP | shared | identical_incl_blanks | agree_both_filled | cs_receipts_blank_webk_filled | cs_disb_blank_webk_filled | disagree_both_filled |
|---|---|---|---|---|---|---|
| C | 68 | 0 | 0 | 68 | 68 | 0 |
| H | 76 | 76 | 76 | 0 | 0 | 0 |
| I | 207 | 3 | 0 | 204 | 204 | 0 |
| N | 3,094 | 3,082 | 3,082 | 3 | 3 | 0 |
| O | 2,063 | 2,055 | 2,055 | 2 | 2 | 3 |
| P | 1 | 1 | 1 | 0 | 0 | 0 |
| Q | 3,273 | 3,270 | 3,270 | 0 | 0 | 0 |
| S | 69 | 69 | 69 | 0 | 0 | 0 |
| U | 19 | 18 | 18 | 0 | 0 | 0 |
| V | 644 | 644 | 644 | 0 | 0 | 0 |
| W | 137 | 137 | 137 | 0 | 0 | 0 |
| X | 241 | 239 | 239 | 0 | 0 | 0 |
| Y | 239 | 239 | 239 | 0 | 0 | 0 |

**Q2f3: shared committees disagreeing with both sides filled  (0 s)**

| CMTE_ID | CMTE_NM | CMTE_TP | receipts_diff | disb_diff | coh_end_diff | indiv_diff | k_cvg_end | c_cvg_end |
|---|---|---|---|---|---|---|---|---|
| C00114314 | NATIONAL ASSOCIATION OF LETTER CARRIERS OF UNITED STATES OF AMERICA BRANCH 9 P.A.L. | Q | 0 | 0 | 0 | 7,910 | 2024-12-31 | 2024-12-31 |
| C00215590 | AMERICAN SYSTEMS CORPORATION POLITICAL ACTION COMMITTEE (ASC-PAC) | N | 0 | 0 | 0 | 0 | 2024-12-31 | 2024-12-31 |
| C00299867 | UNITED STEELWORKERS LOCAL 420-A PAC  | Q | 0 | 0 | 0 | 16,958 | 2024-12-31 | 2024-12-31 |
| C00719021 | YAY NAY PAC | N | 0 | 0 | 0 | 0 | 2024-12-31 | 2024-12-31 |
| C00833814 | NEW ORDER PAC (NOPAC) | O | 0 | 0 | 3,555 | 0 | 2023-12-31 | 2023-12-31 |
| C00858670 | FIGHTING 4 ONE AMERICA PAC | O | 150,500 | 0 | 0 | 0 | 2023-12-31 | 2023-12-31 |
| C00877670 | CAAG PAC | O | 22,100 | 7,159 | 0 | 0 | 2024-12-31 | 2024-12-31 |

**Q2g: webl vs the sum of credited committees in committee_summary (H and S, one or more credited)  (0 s)**

| measure | both_sides | within_1_dollar | within_1_pct | beyond_1_pct | share_within_1_dollar | sum_l | sum_c | sum_abs_diff | max_abs_diff |
|---|---|---|---|---|---|---|---|---|---|
| receipts | 2,118 | 2,118 | 0 | 0 | 100.00% | 3,514,586,857 | 3,514,586,857 | 0 | 0 |
| disbursements | 2,118 | 2,118 | 0 | 0 | 100.00% | 3,399,735,489 | 3,399,735,489 | 0 | 0 |
| coh_end | 2,118 | 2,116 | 0 | 2 | 99.91% | 564,802,422 | 564,830,676 | 28,254 | 23,254 |
| indiv_total | 2,109 | 2,100 | 2 | 7 | 99.57% | 2,283,155,435 | 2,283,131,522 | 23,559 | 8,500 |
| transfers_in | 2,106 | 2,106 | 0 | 0 | 100.00% | 337,177,231 | 337,177,231 | 0 | 0 |
| transfers_out | 2,107 | 2,107 | 0 | 0 | 100.00% | 29,916,012 | 29,916,012 | 0 | 0 |

**Q2h: webl receipts vs the credited sum, by committees summed; and whether transfers explain the gap  (0 s)**

| committees_summed | candidates | equal | equal_less_transfers_in | neither | sum_diff | sum_transfers_in |
|---|---|---|---|---|---|---|
| 1 | 2,029 | 2,026 | 0 | 0 | 0 | 265,082,116 |
| 2 | 81 | 81 | 0 | 0 | 0 | 55,480,496 |
| 3 | 11 | 11 | 0 | 0 | 0 | 16,614,619 |

**Reading.**

- Where both files carry a figure they are the same data. Receipts agree within $1 for 9,843 of
  9,845 committees, debts, contributions from other committees, transfers and refunds for every one,
  and coverage end dates for 10,119 of 10,131. Three committees disagree on receipts, disbursements or ending cash with both sides filled
  (Q2f3), all super PACs, two of them with a 2023-12-31 coverage end. Q2f3's other four differ only
  on individual money or starting cash.
- **The spec's precedence bar fails as written and holds on substance.** `committee_summary` holds
  81.84% of `webk`'s committees, against a bar of 99%. But the `webk`-only rows are empty: it holds
  8,916 of the 8,917 `webk` committees with any receipts or disbursements, and the one it lacks is
  the bad Form 5 record. On receipts, disbursements and cash on hand, 97.33% of shared committees
  agree when a blank is read as 0, under the 99% bar. The rest are all blanks in
  `committee_summary` where `webk` has a figure: 204 Form 5 filers (type I) and 68 Form 7 filers
  (type C, communication costs). With both sides filled, 9,830 of 9,833 agree (99.97%). So
  `committee_summary` wins, and `webk` fills a measure that `committee_summary` leaves blank.
- **`webl` (and so `weball`) equals the sum of the credited committees exactly.** All 2,118 House
  and Senate candidates with a credited committee match on receipts, disbursements and transfers.
  So FEC does not net transfers between authorized committees out of the candidate figure, despite
  the file note. The candidates with 2 and 3 committees summed (81 and 11) match too (Q2h).

## Q3: candidate figures, `weball` against `candidate_summary` against the credited committees

`c_` is the sum over the committees fundlens credits (`credited`) that `cs` holds. `f_` is the sum
over the rows `committee_summary` itself links to the candidate as P or A: FEC's own roll-up. It was
added to explain the differences.

```python
# Measure: (weball, candidate_summary, committee_summary).
CAND_MEASURES = {
    "receipts": ("TTL_RECEIPTS", "Total_Receipt", "TTL_RECEIPTS"),
    "disbursements": ("TTL_DISB", "Total_Disbursement", "TTL_DISB"),
    "coh_end": ("COH_COP", "Cash_On_Hand_COP", "COH_COP"),
    "debts_owed_by": ("DEBTS_OWED_BY", "Debt_Owed_By_Committee", "DEBTS_OWED_BY_CMTE"),
    "indiv_total": ("TTL_INDIV_CONTRIB", "Individual_Contribution", "INDV_CONTB"),
    "other_committees": ("OTHER_POL_CMTE_CONTRIB", "Other_Committee_Contribution", "OTH_CMTE_CONTB"),
    "party_committees": ("POL_PTY_CONTRIB", "Party_Committee_Contribution", "PTY_CMTE_CONTB"),
    "candidate_own": ("CAND_CONTRIB", "Cand_Contribution", "CAND_CNTB"),
    "candidate_loans": ("CAND_LOANS", "Cand_Loan", "CAND_LOAN"),
    "transfers_in": ("TRANS_FROM_AUTH", "Transfer_From_Other_Auth_Committee", "TRANF_FROM_OTHER_AUTH_CMTE"),
    "transfers_out": ("TRANS_TO_AUTH", "Transfer_To_Other_Auth_Committee", "TRANF_TO_OTHER_AUTH_CMTE"),
}
w_cols = ", ".join(f"amt(w.{w}) AS w_{m}" for m, (w, _, _) in CAND_MEASURES.items())
s_cols = ", ".join(f"amt(s.{c}) AS s_{m}" for m, (_, c, _) in CAND_MEASURES.items())
c_sums = ", ".join(f"sum(amt(c.{k})) AS c_{m}" for m, (_, _, k) in CAND_MEASURES.items())
f_sums = ", ".join(f"sum(amt(c.{k})) AS f_{m}" for m, (_, _, k) in CAND_MEASURES.items())
con.execute(f"""
-- Per candidate in weball or candidate_summary: weball's figures (w_), candidate_summary's (s_),
-- the sum over the committees fundlens credits to the candidate that committee_summary holds (c_),
-- and the sum over the committees committee_summary itself links to the candidate as P or A (f_).
CREATE TABLE cand3 AS
WITH c AS (
    SELECT cr.candidate_id, count(*) AS credited_in_cs,
        string_agg(cr.committee_id || CASE WHEN cr.handoff THEN ' (handoff)' ELSE '' END, ', '
            ORDER BY cr.committee_id) AS credited_committees,
        {c_sums}
    FROM credited AS cr JOIN cs AS c ON c.CMTE_ID = cr.committee_id GROUP BY ALL
),
cn AS (SELECT candidate_id, count(*) AS credited FROM credited GROUP BY ALL),
-- Credited committees committee_summary does not designate P or A: a campaign turned PAC that
-- fundlens credits through cn.CAND_PCC (04_contribution.sql's exception).
np AS (
    SELECT cr.candidate_id, sum(amt(c.TTL_RECEIPTS)) AS non_pa_receipts,
        string_agg(c.CMTE_ID || ' ' || c.CMTE_TP || '/' || c.CMTE_DSGN || ' ' || c.CMTE_NM, '; ') AS non_pa_committees
    FROM credited AS cr JOIN cs AS c ON c.CMTE_ID = cr.committee_id
    WHERE c.CMTE_DSGN NOT IN ('P', 'A') GROUP BY ALL
),
f AS (
    SELECT c.CAND_ID AS candidate_id, count(*) AS fec_linked_pa,
        string_agg(c.CMTE_ID, ', ' ORDER BY c.CMTE_ID) AS fec_linked_committees, {f_sums}
    FROM committee_summary AS c WHERE c.CMTE_DSGN IN ('P', 'A') GROUP BY ALL
)
SELECT coalesce(w.CAND_ID, s.Cand_Id) AS candidate_id, coalesce(w.CAND_NAME, s.Cand_Name) AS name,
    left(coalesce(w.CAND_ID, s.Cand_Id), 1) AS office, w.CAND_ICI AS ici,
    w.CAND_ID IS NOT NULL AS in_weball, s.Cand_Id IS NOT NULL AS in_candidate_summary,
    coalesce(cn.credited, 0) AS credited, coalesce(c.credited_in_cs, 0) AS credited_in_cs,
    c.credited_committees, coalesce(f.fec_linked_pa, 0) AS fec_linked_pa, f.fec_linked_committees,
    sc.alias_of, sc.candidate_id IS NOT NULL AS in_cn, np.non_pa_receipts, np.non_pa_committees,
    {w_cols}, {s_cols}, c.* EXCLUDE (candidate_id, credited_in_cs, credited_committees),
    f.* EXCLUDE (candidate_id, fec_linked_pa, fec_linked_committees)
FROM weball AS w
FULL JOIN candidate_summary AS s ON s.Cand_Id = w.CAND_ID
LEFT JOIN c ON c.candidate_id = coalesce(w.CAND_ID, s.Cand_Id)
LEFT JOIN cn ON cn.candidate_id = coalesce(w.CAND_ID, s.Cand_Id)
LEFT JOIN f ON f.candidate_id = coalesce(w.CAND_ID, s.Cand_Id)
LEFT JOIN np ON np.candidate_id = coalesce(w.CAND_ID, s.Cand_Id)
LEFT JOIN silver.candidate AS sc ON sc.candidate_id = coalesce(w.CAND_ID, s.Cand_Id)
""")
M = list(CAND_MEASURES)
compare("Q3a: weball vs candidate_summary, candidates in both", "SELECT * FROM cand3 WHERE in_weball AND in_candidate_summary", M, "w", "s")
compare("Q3b: weball vs the sum of credited committees, weball candidates with one or more credited in committee_summary",
        "SELECT * FROM cand3 WHERE in_weball AND credited_in_cs > 0", M, "w", "c")
compare("Q3c: candidate_summary vs the sum of credited committees, candidate_summary candidates with one or more credited",
        "SELECT * FROM cand3 WHERE in_candidate_summary AND credited_in_cs > 0", M, "s", "c")
compare("Q3d: candidate_summary vs the sum of committee_summary's own P/A rows for the candidate",
        "SELECT * FROM cand3 WHERE in_candidate_summary AND fec_linked_pa > 0", M, "s", "f")

show("Q3e: receipts, candidate_summary vs credited sum, by office and committees credited", """
SELECT office, least(credited_in_cs, 2) AS credited_in_cs, count(*) AS candidates,
    count(*) FILTER (WHERE abs(s_receipts - c_receipts) <= 1) AS within_1_dollar,
    count(*) FILTER (WHERE abs(s_receipts - c_receipts) > 1 AND abs(s_receipts - c_receipts) <= 0.01 * abs(s_receipts)) AS within_1_pct,
    count(*) FILTER (WHERE abs(coalesce(s_receipts, 0) - coalesce(c_receipts, 0)) > greatest(1, 0.01 * abs(coalesce(s_receipts, 0)))) AS beyond,
    sum(s_receipts) AS candidate_summary, sum(c_receipts) AS credited_sum, sum(w_receipts) AS weball
FROM cand3 WHERE in_candidate_summary GROUP BY ALL ORDER BY ALL
""")

show("Q3f: receipts, weball vs credited sum, by office and committees credited", """
SELECT office, least(credited_in_cs, 2) AS credited_in_cs, count(*) AS candidates,
    count(*) FILTER (WHERE abs(w_receipts - c_receipts) <= 1) AS within_1_dollar,
    count(*) FILTER (WHERE abs(coalesce(w_receipts, 0) - coalesce(c_receipts, 0)) > greatest(1, 0.01 * abs(coalesce(w_receipts, 0)))) AS beyond_1_pct,
    sum(w_receipts) AS weball, sum(c_receipts) AS credited_sum
FROM cand3 WHERE in_weball GROUP BY ALL ORDER BY ALL
""")

show("Q3g: the decision rule (spec §1.1): candidate_summary candidates with one or more credited committee", """
SELECT count(*) AS candidates,
    count(*) FILTER (WHERE abs(s_receipts - c_receipts) <= greatest(1, 0.01 * abs(s_receipts))) AS within_1_pct,
    count(*) FILTER (WHERE abs(s_receipts - c_receipts) <= greatest(1, 0.01 * abs(s_receipts))) / count(*)::DOUBLE AS match_rate,
    count(*) FILTER (WHERE abs(s_receipts - c_receipts) <= greatest(1, 0.01 * abs(s_receipts))
        AND coalesce(s_receipts, 0) <> 0) AS within_1_pct_nonzero,
    count(*) FILTER (WHERE coalesce(s_receipts, 0) <> 0) AS nonzero,
    count(*) FILTER (WHERE abs(s_receipts - c_receipts) <= greatest(1, 0.01 * abs(s_receipts))
        AND coalesce(s_receipts, 0) <> 0) / count(*) FILTER (WHERE coalesce(s_receipts, 0) <> 0)::DOUBLE AS match_rate_nonzero
FROM cand3 WHERE in_candidate_summary AND credited_in_cs > 0
""")

show("Q3h: every mismatch under the rule, with what the queries show", """
WITH m AS (
    SELECT *, s_receipts - c_receipts AS diff FROM cand3
    WHERE in_candidate_summary AND credited_in_cs > 0
        AND NOT coalesce(abs(s_receipts - c_receipts) <= greatest(1, 0.01 * abs(s_receipts)), false)
)
SELECT candidate_id, name, s_receipts, c_receipts, f_receipts, diff,
    credited_committees, fec_linked_committees, non_pa_committees,
    CASE WHEN credited_committees LIKE '%(handoff)%' THEN 'handoff'
        WHEN abs(diff + non_pa_receipts) <= 1 THEN 'credits a committee FEC no longer designates P/A (CAND_PCC)'
        WHEN s_receipts = 0 AND abs(f_receipts - c_receipts) <= 1 THEN 'candidate_summary row empty; committee_summary links the committee'
        WHEN abs(s_receipts - f_receipts) <= 1 THEN 'FEC links other committees'
        WHEN abs(s_receipts - (c_receipts - c_transfers_in)) <= 1 THEN 'transfers between authorized committees'
        WHEN alias_of IS NOT NULL THEN 'alias'
        WHEN s_receipts IS NULL THEN 'candidate_summary receipts blank'
        WHEN c_receipts IS NULL THEN 'credited committees'' receipts blank'
        ELSE 'other' END AS reading
FROM m ORDER BY abs(diff) DESC NULLS LAST
""")

show("Q3h2: candidate_summary vs committee_summary's own P/A rows: the mismatches", """
SELECT candidate_id, name, s_receipts, f_receipts, s_receipts - f_receipts AS diff, fec_linked_committees
FROM cand3 WHERE in_candidate_summary AND fec_linked_pa > 0 AND abs(s_receipts - f_receipts) > 1
ORDER BY abs(s_receipts - f_receipts) DESC
""")

show("Q3h3: weball rows repeating another weball row's figures (one committee under two candidate ids)", """
WITH f AS (SELECT CAND_ID, TTL_RECEIPTS, TTL_DISB, COH_COP FROM weball WHERE coalesce(amt(TTL_RECEIPTS), 0) <> 0),
dup AS (
    SELECT * FROM f WHERE (TTL_RECEIPTS, TTL_DISB, COH_COP) IN (
        SELECT (TTL_RECEIPTS, TTL_DISB, COH_COP) FROM f GROUP BY ALL HAVING count(*) > 1)
)
SELECT count(*) AS rows, count(DISTINCT (TTL_RECEIPTS, TTL_DISB, COH_COP)) AS distinct_figures,
    sum(amt(TTL_RECEIPTS)) AS receipts_in_those_rows,
    count(*) FILTER (WHERE CAND_ID IN (SELECT Cand_Id FROM candidate_summary)) AS of_which_in_candidate_summary
FROM dup
""")

pick = """
WITH ranked AS (
    SELECT *, row_number() OVER (PARTITION BY office, ici ORDER BY w_receipts DESC NULLS LAST) AS r_hs,
        row_number() OVER (PARTITION BY office ORDER BY w_receipts DESC NULLS LAST) AS r_office,
        row_number() OVER (PARTITION BY office, fec_linked_pa >= 2 ORDER BY w_receipts DESC NULLS LAST) AS r_multi
    FROM cand3 WHERE in_weball
)
SELECT *, CASE WHEN office IN ('H', 'S') AND ici IN ('I', 'C', 'O') AND r_hs <= 2 THEN office || ' ' || ici
    WHEN office = 'P' AND r_office <= 4 THEN 'P' ELSE 'H 2+ P/A' END AS picked_as
FROM ranked
WHERE (office IN ('H', 'S') AND ici IN ('I', 'C', 'O') AND r_hs <= 2) OR (office = 'P' AND r_office <= 4)
    OR (office = 'H' AND fec_linked_pa >= 2 AND r_multi <= 4)
"""
con.execute(f"CREATE TABLE pick20 AS {pick}")
show("Q3i: the 20 candidates: receipts, disbursements, cash on hand, debts, individual (weball w / candidate_summary s / credited sum c)", """
SELECT picked_as, candidate_id, name, credited_committees, w_receipts, s_receipts, c_receipts, w_disbursements, s_disbursements, c_disbursements,
    w_coh_end, s_coh_end, c_coh_end, w_debts_owed_by, s_debts_owed_by, c_debts_owed_by, w_indiv_total, s_indiv_total, c_indiv_total
FROM pick20 ORDER BY picked_as, w_receipts DESC
""")
show("Q3j: the 20 candidates: the other measures", """
SELECT picked_as, candidate_id, w_other_committees, s_other_committees, c_other_committees, w_party_committees, s_party_committees, c_party_committees,
    w_candidate_own, s_candidate_own, c_candidate_own, w_candidate_loans, s_candidate_loans, c_candidate_loans,
    w_transfers_in, s_transfers_in, c_transfers_in, w_transfers_out, s_transfers_out, c_transfers_out
FROM pick20 ORDER BY picked_as, w_receipts DESC
""")
show("Q3k: Biden, Harris and C00703975", """
SELECT candidate_id, name, credited_committees, fec_linked_committees, w_receipts, s_receipts, c_receipts, f_receipts,
    w_indiv_total, s_indiv_total, c_indiv_total, s_coh_end, c_coh_end
FROM cand3 WHERE candidate_id IN ('P80000722', 'P00009423')
""")
show("Q3l: Trump P80001571 and C00828541", """
SELECT candidate_id, name, credited_committees, fec_linked_committees, w_receipts, s_receipts, c_receipts, f_receipts
FROM cand3 WHERE candidate_id = 'P80001571'
""")
show("Q3m: candidate_summary candidates with receipts but no credited committee in committee_summary, by why", """
WITH z AS (
    SELECT c.*, (SELECT string_agg(DISTINCT cr.candidate_id, ', ') FROM committee_summary AS k JOIN credited AS cr ON cr.committee_id = k.CMTE_ID
        WHERE k.CAND_ID = c.candidate_id AND k.CMTE_DSGN IN ('P', 'A')) AS credited_to
    FROM cand3 AS c WHERE in_candidate_summary AND credited_in_cs = 0 AND coalesce(s_receipts, 0) <> 0
)
SELECT CASE WHEN alias_of IS NOT NULL THEN 'an alias (NEU-2127)' WHEN credited_to IS NOT NULL THEN 'its committee is credited to another candidate id'
        WHEN NOT in_cn THEN 'not in cn' ELSE 'other' END AS why,
    count(*) AS candidates, sum(s_receipts) AS candidate_summary_receipts,
    string_agg(candidate_id || ' ' || name || coalesce(' -> ' || coalesce(alias_of, credited_to), ''), '; ' ORDER BY s_receipts DESC) FILTER (WHERE s_receipts >= 1000000) AS largest
FROM z GROUP BY ALL ORDER BY 3 DESC
""")

# fundlens's itemized credit for the two, live gold, read-only.
with psycopg.connect(settings.database_url) as pg:
    pg.read_only = True
    rows = pg.execute(
        "SELECT candidate_id, total_individual, self_funding FROM gold.candidate_cycle"
        " WHERE cycle = 2024 AND candidate_id IN ('P80000722', 'P00009423') ORDER BY 1"
    ).fetchall()
print("\n**Q3n: Biden and Harris in live gold.candidate_cycle (candidate_id, total_individual, self_funding)**\n")
for row in rows:
    print(f"- {row[0]}: {row[1]:,.0f}, {row[2]:,.0f}")
```

**Q3a: weball vs candidate_summary, candidates in both  (0 s)**

| measure | both_sides | within_1_dollar | within_1_pct | beyond_1_pct | share_within_1_dollar | sum_w | sum_s | sum_abs_diff | max_abs_diff |
|---|---|---|---|---|---|---|---|---|---|
| receipts | 2,320 | 2,320 | 0 | 0 | 100.00% | 6,275,917,633 | 6,275,917,633 | 0 | 0 |
| disbursements | 2,320 | 2,320 | 0 | 0 | 100.00% | 6,162,133,085 | 6,162,133,085 | 0 | 0 |
| coh_end | 2,317 | 2,314 | 0 | 3 | 99.87% | 579,462,683 | 579,511,037 | 48,354 | 23,254 |
| debts_owed_by | 2,305 | 2,302 | 0 | 3 | 99.87% | 449,552,620 | 449,586,675 | 34,055 | 29,000 |
| indiv_total | 2,320 | 2,305 | 2 | 13 | 99.35% | 3,736,616,455 | 3,736,560,499 | 55,956 | 31,196 |
| other_committees | 2,320 | 2,320 | 0 | 0 | 100.00% | 491,773,010 | 491,773,010 | 0 | 0 |
| party_committees | 2,320 | 2,320 | 0 | 0 | 100.00% | 6,970,207 | 6,970,207 | 0 | 0 |
| candidate_own | 2,320 | 2,320 | 0 | 0 | 100.00% | 55,595,629 | 55,595,629 | 0 | 0 |
| candidate_loans | 2,320 | 2,320 | 0 | 0 | 100.00% | 445,334,012 | 445,334,012 | 0 | 0 |
| transfers_in | 2,320 | 2,320 | 0 | 0 | 100.00% | 1,421,758,847 | 1,421,758,847 | 0 | 0 |
| transfers_out | 2,320 | 2,320 | 0 | 0 | 100.00% | 24,278,952 | 24,278,952 | 0 | 0 |

**Q3b: weball vs the sum of credited committees, weball candidates with one or more credited in committee_summary  (0 s)**

| measure | both_sides | within_1_dollar | within_1_pct | beyond_1_pct | share_within_1_dollar | sum_w | sum_c | sum_abs_diff | max_abs_diff |
|---|---|---|---|---|---|---|---|---|---|
| receipts | 3,655 | 3,652 | 0 | 3 | 99.92% | 6,400,992,004 | 6,896,849,999 | 495,874,823 | 495,853,270 |
| disbursements | 3,655 | 3,652 | 0 | 3 | 99.92% | 6,278,051,254 | 6,749,632,301 | 471,586,780 | 471,501,652 |
| coh_end | 3,657 | 3,650 | 0 | 7 | 99.81% | 874,823,589 | 902,269,067 | 27,456,885 | 27,372,521 |
| debts_owed_by | 3,638 | 3,633 | 0 | 5 | 99.86% | 602,865,406 | 614,201,303 | 11,345,498 | 11,306,643 |
| indiv_total | 3,637 | 3,623 | 2 | 12 | 99.62% | 3,819,882,909 | 3,888,388,755 | 68,633,484 | 68,570,090 |
| other_committees | 3,633 | 3,632 | 0 | 1 | 99.97% | 509,961,348 | 510,302,464 | 341,116 | 341,116 |
| party_committees | 3,633 | 3,632 | 0 | 1 | 99.97% | 6,901,765 | 6,904,765 | 3,000 | 3,000 |
| candidate_own | 3,641 | 3,641 | 0 | 0 | 100.00% | 59,495,468 | 59,495,468 | 0 | 0 |
| candidate_loans | 3,634 | 3,634 | 0 | 0 | 100.00% | 424,221,685 | 424,221,685 | 0 | 0 |
| transfers_in | 3,633 | 3,631 | 0 | 2 | 99.94% | 1,436,414,571 | 1,823,031,451 | 386,616,880 | 386,611,815 |
| transfers_out | 3,633 | 3,633 | 0 | 0 | 100.00% | 35,318,657 | 35,318,657 | 0 | 0 |

**Q3c: candidate_summary vs the sum of credited committees, candidate_summary candidates with one or more credited  (0 s)**

| measure | both_sides | within_1_dollar | within_1_pct | beyond_1_pct | share_within_1_dollar | sum_s | sum_c | sum_abs_diff | max_abs_diff |
|---|---|---|---|---|---|---|---|---|---|
| receipts | 2,251 | 2,235 | 0 | 16 | 99.29% | 6,166,882,468 | 6,690,197,711 | 523,315,243 | 495,853,270 |
| disbursements | 2,251 | 2,236 | 0 | 15 | 99.33% | 6,039,189,030 | 6,540,590,210 | 501,401,180 | 471,501,652 |
| coh_end | 2,251 | 2,238 | 0 | 13 | 99.42% | 569,673,853 | 601,178,643 | 31,504,810 | 27,372,521 |
| debts_owed_by | 2,237 | 2,233 | 0 | 4 | 99.82% | 423,970,048 | 435,330,453 | 11,360,406 | 11,306,643 |
| indiv_total | 2,235 | 2,224 | 0 | 11 | 99.51% | 3,668,429,246 | 3,761,520,490 | 93,091,244 | 68,570,090 |
| other_committees | 2,230 | 2,224 | 0 | 6 | 99.73% | 485,294,201 | 487,269,965 | 1,975,763 | 590,292 |
| party_committees | 2,230 | 2,228 | 0 | 2 | 99.91% | 6,892,372 | 6,903,246 | 10,874 | 7,874 |
| candidate_own | 2,236 | 2,233 | 0 | 3 | 99.87% | 54,938,285 | 54,940,595 | 2,311 | 2,081 |
| candidate_loans | 2,230 | 2,228 | 0 | 2 | 99.91% | 418,940,881 | 418,962,880 | 21,999 | 20,000 |
| transfers_in | 2,229 | 2,225 | 0 | 4 | 99.82% | 1,415,909,069 | 1,802,939,233 | 387,030,164 | 386,611,815 |
| transfers_out | 2,231 | 2,229 | 0 | 2 | 99.91% | 23,997,539 | 25,302,475 | 1,304,936 | 873,721 |

**Q3d: candidate_summary vs the sum of committee_summary's own P/A rows for the candidate  (0 s)**

| measure | both_sides | within_1_dollar | within_1_pct | beyond_1_pct | share_within_1_dollar | sum_s | sum_f | sum_abs_diff | max_abs_diff |
|---|---|---|---|---|---|---|---|---|---|
| receipts | 2,321 | 2,315 | 0 | 6 | 99.74% | 6,275,917,633 | 6,275,929,826 | 12,193 | 5,300 |
| disbursements | 2,321 | 2,316 | 0 | 5 | 99.78% | 6,162,133,085 | 6,162,152,877 | 19,792 | 10,081 |
| coh_end | 2,321 | 2,317 | 0 | 4 | 99.83% | 579,506,803 | 579,509,596 | 2,812 | 2,000 |
| debts_owed_by | 2,307 | 2,306 | 0 | 1 | 99.96% | 449,569,381 | 449,571,380 | 1,999 | 1,999 |
| indiv_total | 2,305 | 2,302 | 0 | 3 | 99.87% | 3,736,560,499 | 3,736,567,459 | 6,960 | 5,300 |
| other_committees | 2,300 | 2,300 | 0 | 0 | 100.00% | 491,773,010 | 491,773,010 | 0 | 0 |
| party_committees | 2,300 | 2,300 | 0 | 0 | 100.00% | 6,970,207 | 6,970,207 | 0 | 0 |
| candidate_own | 2,307 | 2,304 | 0 | 3 | 99.87% | 55,595,629 | 55,597,940 | 2,311 | 2,081 |
| candidate_loans | 2,301 | 2,300 | 0 | 1 | 99.96% | 445,334,012 | 445,336,011 | 1,999 | 1,999 |
| transfers_in | 2,299 | 2,299 | 0 | 0 | 100.00% | 1,421,758,847 | 1,421,758,847 | 0 | 0 |
| transfers_out | 2,301 | 2,301 | 0 | 0 | 100.00% | 24,278,952 | 24,278,952 | 0 | 0 |

**Q3e: receipts, candidate_summary vs credited sum, by office and committees credited  (0 s)**

| office | credited_in_cs | candidates | within_1_dollar | within_1_pct | beyond | candidate_summary | credited_sum | weball |
|---|---|---|---|---|---|---|---|---|
| H | 0 | 1,208 | 0 | 0 | 48 | 41,243,112 |  | 41,243,112 |
| H | 1 | 1,794 | 1,781 | 0 | 10 | 1,842,979,448 | 1,847,251,428 | 1,842,979,448 |
| H | 2 | 76 | 76 | 0 | 0 | 201,485,318 | 201,485,318 | 201,485,318 |
| P | 0 | 1,468 | 0 | 0 | 5 | 23,358,446 |  | 23,358,446 |
| P | 1 | 130 | 126 | 0 | 3 | 1,479,510,736 | 1,479,515,308 | 1,479,510,736 |
| P | 2 | 4 | 3 | 0 | 1 | 1,178,819,534 | 1,674,672,805 | 1,178,819,534 |
| S | 0 | 371 | 0 | 0 | 22 | 44,433,608 |  | 44,433,608 |
| S | 1 | 236 | 234 | 0 | 2 | 1,132,163,869 | 1,155,349,290 | 1,132,163,869 |
| S | 2 | 15 | 15 | 0 | 0 | 331,923,562 | 331,923,562 | 331,923,562 |

**Q3f: receipts, weball vs credited sum, by office and committees credited  (0 s)**

| office | credited_in_cs | candidates | within_1_dollar | beyond_1_pct | weball | credited_sum |
|---|---|---|---|---|---|---|
| H | 0 | 126 | 0 | 99 | 336,880,145 |  |
| H | 1 | 2,833 | 2,828 | 1 | 1,863,538,343 | 1,863,529,929 |
| H | 2 | 114 | 113 | 1 | 203,329,973 | 203,343,113 |
| P | 0 | 16 | 0 | 10 | 59,052,626 |  |
| P | 1 | 153 | 152 | 0 | 1,479,876,368 | 1,479,876,368 |
| P | 2 | 6 | 5 | 1 | 1,179,205,798 | 1,675,059,069 |
| S | 0 | 54 | 0 | 35 | 49,170,780 |  |
| S | 1 | 540 | 539 | 0 | 1,343,117,959 | 1,343,117,959 |
| S | 2 | 15 | 15 | 0 | 331,923,562 | 331,923,562 |

**Q3g: the decision rule (spec §1.1): candidate_summary candidates with one or more credited committee  (0 s)**

| candidates | within_1_pct | match_rate | within_1_pct_nonzero | nonzero | match_rate_nonzero |
|---|---|---|---|---|---|
| 2,255 | 2,235 | 99.11% | 2,142 | 2,143 | 99.95% |

**Q3h: every mismatch under the rule, with what the queries show  (0 s)**

| candidate_id | name | s_receipts | c_receipts | f_receipts | diff | credited_committees | fec_linked_committees | non_pa_committees | reading |
|---|---|---|---|---|---|---|---|---|---|
| P80001571 | TRUMP, DONALD J. | 29,134 | 495,882,404 | 29,134 | -495,853,270 | C00828541, C00867275 | C00867275 | C00828541 N/D NEVER SURRENDER, INC. | credits a committee FEC no longer designates P/A (CAND_PCC) |
| S2MO00528 | KUNCE, LUCAS | 0 | 23,184,061 |  | -23,184,061 | C00771972 |  | C00771972 V/U HEARTLAND PATRIOTS | credits a committee FEC no longer designates P/A (CAND_PCC) |
| H6WI08155 | GALLAGHER, MICHAEL JOHN | 0 | 2,121,829 |  | -2,121,829 | C00610212 |  | C00610212 Q/U WAGING PEACE | credits a committee FEC no longer designates P/A (CAND_PCC) |
| H0OH06189 | JOHNSON, BILL | 0 | 850,408 |  | -850,408 | C00476820 |  | C00476820 H/U OHIO BELIEF PAC | credits a committee FEC no longer designates P/A (CAND_PCC) |
| H4NY27076 | HIGGINS, BRIAN | 0 | 633,277 |  | -633,277 | C00401034 |  | C00401034 N/U BUILDING FOUNDATIONS & LANDMARK OPPORTUNITIES PAC (BFLO PAC) | credits a committee FEC no longer designates P/A (CAND_PCC) |
| H2GA14044 | FLOWERS, MARCUS | 0 | 475,234 |  | -475,234 | C00768101 |  | C00768101 N/D MISSION DEMOCRACY PAC | credits a committee FEC no longer designates P/A (CAND_PCC) |
| H4CO04090 | BUCK, KENNETH R | 0 | 162,213 |  | -162,213 | C00573378 |  | C00573378 H/U BUCK PAC | credits a committee FEC no longer designates P/A (CAND_PCC) |
| H0TX20124 | MCQUEEN, ELDON DAN | 0 | 20,000 |  | -20,000 | C00715896 |  | C00715896 S/U MCQUEEN FOR CONGRESS | credits a committee FEC no longer designates P/A (CAND_PCC) |
| H4AZ01319 | MARTIN, MICHELLE | 0 | 5,300 | 5,300 | -5,300 | C00874313 | C00874313 |  | candidate_summary row empty; committee_summary links the committee |
| P40019192 | OLSCAMP, DAVID MICHAEL | 0 | 4,080 | 4,080 | -4,080 | C00870097 | C00870097 |  | candidate_summary row empty; committee_summary links the committee |
| H8OH16124 | GONZALEZ, ANTHONY E | 0 | 2,305 |  | -2,305 | C00654079 |  | C00654079 Q/U AEG PAC | credits a committee FEC no longer designates P/A (CAND_PCC) |
| S4FL00819 | EVERIDGE, BEN | 0 | 1,360 | 1,360 | -1,360 | C00877175 | C00877175 |  | candidate_summary row empty; committee_summary links the committee |
| H4IN05302 | SHILLINGS, LAURI | 0 | 1,114 | 1,114 | -1,114 | C00881409 | C00881409 |  | candidate_summary row empty; committee_summary links the committee |
| P40008716 | MARCELLINI, MARK ROBERT | 0 | 452 |  | -452 | C00822791 |  | C00822791 X/U PEOPLE''S LIFE NATIONAL COMMITTEE; THE | credits a committee FEC no longer designates P/A (CAND_PCC) |
| H4NJ07164 | LEGUIA, LANA | 0 | 300 | 300 | -300 | C00879254 | C00879254 |  | candidate_summary row empty; committee_summary links the committee |
| P40019705 | ASTRONAUT, DOCTOR FN PO2 | 0 | 39 | 39 | -39 | C00874594 | C00874594 |  | candidate_summary row empty; committee_summary links the committee |
| H4DC00118 | WATTS, HELCHIC KOTON | 0 |  |  |  | C00884866 | C00884866 |  | credited committees' receipts blank |
| H4NY10163 | BRISCOE, PAUL J. | 0 |  |  |  | C00885335 | C00885335 |  | credited committees' receipts blank |
| H4OH03113 | YOUNG, MICHAEL | 0 |  |  |  | C00874065 | C00874065 |  | credited committees' receipts blank |
| P40011512 | GREATHOUSE, CHRISTINA | 0 |  |  |  | C00835843 | C00835843 |  | credited committees' receipts blank |

**Q3h2: candidate_summary vs committee_summary's own P/A rows: the mismatches  (0 s)**

| candidate_id | name | s_receipts | f_receipts | diff | fec_linked_committees |
|---|---|---|---|---|---|
| H4AZ01319 | MARTIN, MICHELLE | 0 | 5,300 | -5,300 | C00874313 |
| P40019192 | OLSCAMP, DAVID MICHAEL | 0 | 4,080 | -4,080 | C00870097 |
| S4FL00819 | EVERIDGE, BEN | 0 | 1,360 | -1,360 | C00877175 |
| H4IN05302 | SHILLINGS, LAURI | 0 | 1,114 | -1,114 | C00881409 |
| H4NJ07164 | LEGUIA, LANA | 0 | 300 | -300 | C00879254 |
| P40019705 | ASTRONAUT, DOCTOR FN PO2 | 0 | 39 | -39 | C00874594 |

**Q3h3: weball rows repeating another weball row's figures (one committee under two candidate ids)  (0 s)**

| rows | distinct_figures | receipts_in_those_rows | of_which_in_candidate_summary |
|---|---|---|---|
| 248 | 116 | 789,449,206 | 140 |

**Q3i: the 20 candidates: receipts, disbursements, cash on hand, debts, individual (weball w / candidate_summary s / credited sum c)  (0 s)**

| picked_as | candidate_id | name | credited_committees | w_receipts | s_receipts | c_receipts | w_disbursements | s_disbursements | c_disbursements | w_coh_end | s_coh_end | c_coh_end | w_debts_owed_by | s_debts_owed_by | c_debts_owed_by | w_indiv_total | s_indiv_total | c_indiv_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H 2+ P/A | H4MT01041 | ZINKE, RYAN K | C00778159, C00798454 | 10,117,221 | 10,117,221 | 10,117,221 | 9,546,738 | 9,546,738 | 9,546,738 | 680,531 | 680,531 | 680,531 | 0 | 0 | 0 | 7,952,759 | 7,952,759 | 7,952,759 |
| H 2+ P/A | H2MI10150 | JAMES, JOHN | C00798694, C00803502 | 9,546,139 | 9,546,139 | 9,546,139 | 9,606,964 | 9,606,964 | 9,606,964 | 734,681 | 734,681 | 734,681 | 4,000 | 4,000 | 4,000 | 4,647,146 | 4,647,146 | 4,647,146 |
| H 2+ P/A | H2AZ01354 | CRANE, ELI | C00775007, C00784934 | 8,559,239 | 8,559,239 | 8,559,239 | 8,308,125 | 8,308,125 | 8,308,125 | 317,370 | 317,370 | 317,370 | 202,776 | 202,776 | 202,776 | 8,412,660 | 8,412,660 | 8,412,660 |
| H 2+ P/A | H2NY17162 | LAWLER, MICHAEL VINCENT | C00815415, C00818955 | 8,387,802 | 8,387,802 | 8,387,802 | 8,256,895 | 8,256,895 | 8,256,895 | 169,369 | 169,369 | 169,369 | 0 | 0 | 0 | 3,863,417 | 3,863,417 | 3,863,417 |
| H C | H2CA42205 | ROLLINS, WILL | C00792507 | 12,603,462 | 12,603,462 | 12,603,462 | 12,610,995 | 12,610,995 | 12,610,995 | 37,399 | 37,399 | 37,399 | 0 | 0 | 0 | 9,887,069 | 9,887,069 | 9,887,069 |
| H C | H8NM01224 | HEINRICH, MARTIN |  | 10,731,410 |  |  | 11,549,995 |  |  | 319,551 |  |  | 0 |  |  | 8,100,493 |  |  |
| H I | H4AZ07043 | GALLEGO, RUBEN |  | 64,657,200 |  |  | 65,722,622 |  |  | 211,153 |  |  | 0 |  |  | 59,385,707 |  |  |
| H I | H6MD08549 | TRONE, DAVID |  | 63,833,137 |  |  | 64,032,402 |  |  | 3,841 |  |  | 73,680,994 |  |  | 853,812 |  |  |
| H O | H4VA07234 | VINDMAN, YEVGENY 'EUGENE' | C00856955 | 18,096,190 | 18,096,190 | 18,096,190 | 17,961,256 | 17,961,256 | 17,961,256 | 134,934 | 134,934 | 134,934 | 0 | 0 | 0 | 17,428,791 | 17,428,791 | 17,428,791 |
| H O | H2CO03351 | FRISCH, ADAM | C00805275 | 17,188,573 | 17,188,573 | 17,188,573 | 17,314,502 | 17,314,502 | 17,314,502 | 239,381 | 239,381 | 239,381 | 0 | 0 | 0 | 16,853,163 | 16,853,163 | 16,853,163 |
| P | P00009423 | HARRIS, KAMALA | C00694455, C00703975 (handoff) | 1,175,189,365 | 1,175,189,365 | 1,175,189,365 | 1,175,284,547 | 1,175,284,547 | 1,175,284,547 | 1,762,057 | 1,762,057 | 1,762,057 | 934,180 | 934,180 | 934,180 | 613,557,357 | 613,557,357 | 613,557,357 |
| P | P80000722 | BIDEN, JOSEPH R JR | C00703975 (handoff) | 1,175,189,365 | 1,175,189,365 | 1,175,189,365 | 1,175,214,806 | 1,175,214,806 | 1,175,214,806 | 1,762,057 | 1,762,057 | 1,762,057 | 934,180 | 934,180 | 934,180 | 613,557,357 | 613,557,357 | 613,557,357 |
| P | P40011793 | KENNEDY, ROBERT, F. JR., SHANAHAN, NICOLE | C00836916 | 67,278,247 | 67,278,247 | 67,278,247 | 66,539,069 | 66,539,069 | 66,539,069 | 739,178 | 739,178 | 739,178 | 1,924,501 | 1,924,501 | 1,924,501 | 66,442,924 | 66,442,924 | 66,442,924 |
| P | P40011082 | RAMASWAMY, VIVEK | C00833913 | 66,197,196 | 66,197,196 | 66,197,196 | 66,197,196 | 66,197,196 | 66,197,196 | 0 | 0 | 0 | 0 | 0 | 0 | 11,206,974 | 11,206,974 | 11,206,974 |
| S C | S4TX00722 | ALLRED, COLIN | C00839597 | 94,674,183 | 94,674,183 | 94,674,183 | 94,530,048 | 94,530,048 | 94,530,048 | 144,135 | 144,135 | 144,135 | 0 | 0 | 0 | 85,341,900 | 85,341,900 | 85,341,900 |
| S C | S4FL00611 | MUCARSEL-POWELL, DEBBIE | C00848648 | 36,616,416 | 36,616,416 | 36,616,416 | 36,641,694 | 36,641,694 | 36,641,694 | -25,277 | -25,277 | -25,277 | 56,774 | 56,774 | 56,774 | 34,482,940 | 34,482,940 | 34,482,940 |
| S I | S6OH00163 | BROWN, SHERROD | C00264697 | 96,530,241 | 96,530,241 | 96,530,241 | 99,564,642 | 99,564,642 | 99,564,642 | 394,230 | 394,230 | 394,230 | 0 | 0 | 0 | 79,877,201 | 79,877,201 | 79,877,201 |
| S I | S6MT00162 | TESTER, R. JON | C00412304, C00887521 | 93,570,123 | 93,570,123 | 93,570,123 | 95,689,258 | 95,689,258 | 95,689,258 | 765,624 | 765,624 | 765,624 | 0 | 0 | 0 | 81,104,097 | 81,104,097 | 81,104,097 |
| S O | S4AZ00139 | GALLEGO, RUBEN | C00558627 | 64,657,200 | 64,657,200 | 64,657,200 | 65,722,622 | 65,722,622 | 65,722,622 | 211,153 | 211,153 | 211,153 | 0 | 0 | 0 | 59,385,707 | 59,385,707 | 59,385,707 |
| S O | S4MD00319 | TRONE, DAVID | C00653196 | 63,833,137 | 63,833,137 | 63,833,137 | 64,032,402 | 64,032,402 | 64,032,402 | 3,841 | 3,841 | 3,841 | 73,680,994 | 73,680,994 | 73,680,994 | 853,812 | 853,812 | 853,812 |

**Q3j: the 20 candidates: the other measures  (0 s)**

| picked_as | candidate_id | w_other_committees | s_other_committees | c_other_committees | w_party_committees | s_party_committees | c_party_committees | w_candidate_own | s_candidate_own | c_candidate_own | w_candidate_loans | s_candidate_loans | c_candidate_loans | w_transfers_in | s_transfers_in | c_transfers_in | w_transfers_out | s_transfers_out | c_transfers_out |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H 2+ P/A | H4MT01041 | 1,290,718 | 1,290,718 | 1,290,718 | 249 | 249 | 249 | 0 | 0 | 0 | 0 | 0 | 0 | 838,449 | 838,449 | 838,449 | 517 | 517 | 517 |
| H 2+ P/A | H2MI10150 | 1,323,180 | 1,323,180 | 1,323,180 | 5,000 | 5,000 | 5,000 | 0 | 0 | 0 | 0 | 0 | 0 | 3,547,674 | 3,547,674 | 3,547,674 | 11,653 | 11,653 | 11,653 |
| H 2+ P/A | H2AZ01354 | 114,700 | 114,700 | 114,700 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,781 | 4,781 | 4,781 | 2,354 | 2,354 | 2,354 |
| H 2+ P/A | H2NY17162 | 2,326,003 | 2,326,003 | 2,326,003 | 24,652 | 24,652 | 24,652 | 0 | 0 | 0 | 0 | 0 | 0 | 2,046,708 | 2,046,708 | 2,046,708 | 0 | 0 | 0 |
| H C | H2CA42205 | 825,703 | 825,703 | 825,703 | 10,291 | 10,291 | 10,291 | 0 | 0 | 0 | 0 | 0 | 0 | 1,678,795 | 1,678,795 | 1,678,795 | 0 | 0 | 0 |
| H C | H8NM01224 | 2,004,501 |  |  | 57,800 |  |  | 0 |  |  | 0 |  |  | 469,098 |  |  | 0 |  |  |
| H I | H4AZ07043 | 1,784,685 |  |  | 75,650 |  |  | 0 |  |  | 0 |  |  | 2,910,010 |  |  | 0 |  |  |
| H I | H6MD08549 | 5,000 |  |  | 0 |  |  | 0 |  |  | 62,877,800 |  |  | 0 |  |  | 0 |  |  |
| H O | H4VA07234 | 394,193 | 394,193 | 394,193 | 5,000 | 5,000 | 5,000 | 0 | 0 | 0 | 0 | 0 | 0 | 190,780 | 190,780 | 190,780 | 0 | 0 | 0 |
| H O | H2CO03351 | 240,125 | 240,125 | 240,125 | 14,500 | 14,500 | 14,500 | 0 | 0 | 0 | 0 | 0 | 0 | 56,823 | 56,823 | 56,823 | 0 | 0 | 0 |
| P | P00009423 | 152,322 | 152,322 | 152,322 | 2,090 | 2,090 | 2,090 | 0 | 0 | 0 | 0 | 0 | 0 | 533,714,770 | 533,714,770 | 533,714,770 | 67,904 | 67,904 | 67,904 |
| P | P80000722 | 152,322 | 152,322 | 152,322 | 2,090 | 2,090 | 2,090 | 0 | 0 | 0 | 0 | 0 | 0 | 533,714,770 | 533,714,770 | 533,714,770 | 19,400 | 19,400 | 19,400 |
| P | P40011793 | 13,200 | 13,200 | 13,200 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 563,480 | 563,480 | 563,480 | 0 | 0 | 0 |
| P | P40011082 | 13,750 | 13,750 | 13,750 | 0 | 0 | 0 | 25,875,270 | 25,875,270 | 25,875,270 | 28,880,000 | 28,880,000 | 28,880,000 | 0 | 0 | 0 | 0 | 0 | 0 |
| S C | S4TX00722 | 964,090 | 964,090 | 964,090 | 62,300 | 62,300 | 62,300 | 0 | 0 | 0 | 0 | 0 | 0 | 7,498,842 | 7,498,842 | 7,498,842 | 404,231 | 404,231 | 404,231 |
| S C | S4FL00611 | 806,010 | 806,010 | 806,010 | 58,050 | 58,050 | 58,050 | 0 | 0 | 0 | 0 | 0 | 0 | 1,097,747 | 1,097,747 | 1,097,747 | 0 | 0 | 0 |
| S I | S6OH00163 | 3,085,597 | 3,085,597 | 3,085,597 | 57,800 | 57,800 | 57,800 | 0 | 0 | 0 | 0 | 0 | 0 | 11,884,749 | 11,884,749 | 11,884,749 | 0 | 0 | 0 |
| S I | S6MT00162 | 3,077,010 | 3,077,010 | 3,077,010 | 61,171 | 61,171 | 61,171 | 0 | 0 | 0 | 0 | 0 | 0 | 9,079,778 | 9,079,778 | 9,079,778 | 3,744,699 | 3,744,699 | 3,744,699 |
| S O | S4AZ00139 | 1,784,685 | 1,784,685 | 1,784,685 | 75,650 | 75,650 | 75,650 | 0 | 0 | 0 | 0 | 0 | 0 | 2,910,010 | 2,910,010 | 2,910,010 | 0 | 0 | 0 |
| S O | S4MD00319 | 5,000 | 5,000 | 5,000 | 0 | 0 | 0 | 0 | 0 | 0 | 62,877,800 | 62,877,800 | 62,877,800 | 0 | 0 | 0 | 0 | 0 | 0 |

**Q3k: Biden, Harris and C00703975  (0 s)**

| candidate_id | name | credited_committees | fec_linked_committees | w_receipts | s_receipts | c_receipts | f_receipts | w_indiv_total | s_indiv_total | c_indiv_total | s_coh_end | c_coh_end |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P00009423 | HARRIS, KAMALA | C00694455, C00703975 (handoff) | C00694455, C00703975 | 1,175,189,365 | 1,175,189,365 | 1,175,189,365 | 1,175,189,365 | 613,557,357 | 613,557,357 | 613,557,357 | 1,762,057 | 1,762,057 |
| P80000722 | BIDEN, JOSEPH R JR | C00703975 (handoff) | C00703975 | 1,175,189,365 | 1,175,189,365 | 1,175,189,365 | 1,175,189,365 | 613,557,357 | 613,557,357 | 613,557,357 | 1,762,057 | 1,762,057 |

**Q3l: Trump P80001571 and C00828541  (0 s)**

| candidate_id | name | credited_committees | fec_linked_committees | w_receipts | s_receipts | c_receipts | f_receipts |
|---|---|---|---|---|---|---|---|
| P80001571 | TRUMP, DONALD J. | C00828541, C00867275 | C00867275 | 29,134 | 29,134 | 495,882,404 | 29,134 |

**Q3m: candidate_summary candidates with receipts but no credited committee in committee_summary, by why  (0 s)**

| why | candidates | candidate_summary_receipts | largest |
|---|---|---|---|
| its committee is credited to another candidate id | 42 | 62,607,071 | P40012155 SCOTT, TIMOTHY E. -> S4SC00240; H8NJ03206 KIM, ANDY -> S4NJ00466; H8UT03238 CURTIS, JOHN -> S4UT00282; S4MO00250 BELL, WESLEY -> H4MO01134; P40019937 FISHBACK, BRIAN C MR. -> H4NH02399; S4FL00553 GROSS, KEITH -> H4FL01247; H4AZ01202 CHERNY, ANDREI -> H2AZ09043; H2NC14019 NICKEL, WILEY -> S6NC00340; H4NY03184 SAPRAICONE, MICHAEL -> S4NY00404; S4UT00225 BIRD, ROD JR. -> H4UT03302; S4FL00587 EHR, PHILLIP -> H4FL28042; S8MT00234 ROSENDALE, MATT MR. -> H4MT00050; H4WV01058 EVANS, JONATHAN DERRICK -> S6WV00147 |
| an alias (NEU-2127) | 32 | 46,200,132 | S4WI00256 HOVDE, ERIC -> S2WI00268; H4WI03169 COOKE, REBECCA -> H2WI03130; H4WI01197 BARCA, PETER -> H4WI01056; H4MN05113 AL-AQIDI, DALIA -> H0MN05251 |
| other | 1 | 227,963 |  |

**Q3n: Biden and Harris in live gold.candidate_cycle (candidate_id, total_individual, self_funding)**

- P00009423: 307,377,035, 0
- P80000722: 73,961,689, 0

**Reading.**

- **`weball` and `candidate_summary` are the same figures** for every candidate in both: receipts,
  disbursements, transfers, loans and other committees agree for all 2,320. Cash, debts and
  individual money differ for at most 15. **`candidate_summary` is the sum of `committee_summary`'s
  own P/A rows for the candidate** for 2,315 of 2,321. The 6 that differ are `candidate_summary`
  rows of $0 whose committee has a few dollars (Q3h2).
- **The decision rule passes.** The credited sum is within 1% of `Total_Receipt` for 2,235 of 2,255
  candidates (99.11%). Among candidates with any receipts it is 2,142 of 2,143 (99.95%). Every
  mismatch is in Q3h, with its reason:
  - 10 candidates are credited a committee that `committee_summary` no longer designates P or A, by
    `cn.CAND_PCC` (04_contribution.sql's exception): $523.3M. Trump's NEVER SURRENDER (C00828541)
    is $495.9M. The others are Kunce's Heartland Patriots ($23.2M), Gallagher's Waging Peace
    ($2.1M), Bill Johnson's Ohio Belief PAC, Higgins's BFLO PAC, Flowers's Mission Democracy PAC,
    Buck PAC, McQueen for Congress, AEG PAC and People's Life National Committee. These are the
    campaigns turned PACs that the CAND_PCC rule exists for. FEC's roll-up credits them to no
    candidate.
  - 6 have a `candidate_summary` row of $0 although `committee_summary` links their committee:
    $12,193.
  - 4 have a `candidate_summary` row of $0 and a credited committee whose summary figures are
    blank. They count as mismatches only because a blank is not $0.
- **What summing changes.** For handed-off and CAND_PCC committees, summing shows the candidate the
  committees fundlens credits rather than FEC's attribution. It also keeps a committee under one
  candidate id. `candidate_summary` reports 42 candidates' committees under a second id as well
  ($62.6M, e.g. Tim Scott's presidential id with his Senate committee), and 32 aliases ($46.2M,
  e.g. Hovde's old id; Q3m). In `weball`, 248 rows repeat another row's figures ($789.4M), one
  committee under two ids (Q3h3). FEC's candidate files are not additive across candidates. The
  credited sum is, because `credited` gives each committee one candidate.
- **The handoff (C00703975).** Its one cycle-to-date row is under Biden and under Harris in all three
  sources: $1,175,189,365 of receipts and $613,557,357 of individual money for each (Q3k). FEC
  reports the whole committee under both. fundlens's itemized credit splits it at 2024-07-21. If
  NEU-2141 credits the row to both, race and candidate totals count it twice, as FEC's do. If it
  credits only Harris, Biden's reported figures are $0 beside $73,961,689 of itemized individual
  money in live gold (Harris: $307,377,035; Q3n). Apportioning by
  date cannot be done from a cycle-to-date row. NEU-2141 decides.
- The 20 candidates (Q3i, Q3j) agree on every measure across all three sources. The only exceptions
  are the House ids of Gallego, Trone and Heinrich, who ran for the Senate: `weball` lists their
  Senate committee's money under the House id too, and fundlens credits it to the Senate id.

## Q4: does `TTL_INDIV_CONTRIB` include unitemized money?

```python
con.execute("""
CREATE TABLE ind AS
SELECT w.CAND_ID, amt(w.TTL_INDIV_CONTRIB) AS ttl_indiv, amt(s.Individual_Contribution) AS s_total,
    amt(s.Individual_Itemized_Contribution) AS s_item, amt(s.Individual_Unitemized_Contribution) AS s_unitem,
    c.c_total, c.c_item
FROM weball AS w
LEFT JOIN candidate_summary AS s ON s.Cand_Id = w.CAND_ID
LEFT JOIN (
    SELECT cr.candidate_id, sum(amt(c.INDV_CONTB)) AS c_total, sum(amt(c.INDV_ITEM_CONTB)) AS c_item
    FROM credited AS cr JOIN cs AS c ON c.CMTE_ID = cr.committee_id GROUP BY ALL
) AS c ON c.candidate_id = w.CAND_ID
""")
show("Q4a: weball TTL_INDIV_CONTRIB against candidate_summary's individual figures and the credited committees'", """
SELECT 'candidate_summary' AS against, count(*) FILTER (WHERE s_total IS NOT NULL) AS candidates,
    count(*) FILTER (WHERE s_unitem <> 0) AS with_unitemized,
    count(*) FILTER (WHERE abs(ttl_indiv - s_total) <= 1) AS equals_total,
    count(*) FILTER (WHERE abs(ttl_indiv - s_item) <= 1) AS equals_itemized,
    count(*) FILTER (WHERE abs(ttl_indiv - s_total) <= 1 AND abs(ttl_indiv - s_item) > 1) AS equals_total_not_itemized,
    count(*) FILTER (WHERE abs(ttl_indiv - s_item) <= 1 AND abs(ttl_indiv - s_total) > 1) AS equals_itemized_not_total,
    count(*) FILTER (WHERE abs(ttl_indiv - s_total) > 1 AND abs(ttl_indiv - s_item) > 1) AS equals_neither
FROM ind
UNION ALL
SELECT 'credited committees (INDV_CONTB, INDV_ITEM_CONTB)', count(*) FILTER (WHERE c_total IS NOT NULL),
    count(*) FILTER (WHERE c_total - c_item <> 0),
    count(*) FILTER (WHERE abs(ttl_indiv - c_total) <= 1), count(*) FILTER (WHERE abs(ttl_indiv - c_item) <= 1),
    count(*) FILTER (WHERE abs(ttl_indiv - c_total) <= 1 AND abs(ttl_indiv - c_item) > 1),
    count(*) FILTER (WHERE abs(ttl_indiv - c_item) <= 1 AND abs(ttl_indiv - c_total) > 1),
    count(*) FILTER (WHERE abs(ttl_indiv - c_total) > 1 AND abs(ttl_indiv - c_item) > 1)
FROM ind
""")
show("Q4b: weball candidates where TTL_INDIV_CONTRIB equals neither candidate_summary figure", """
SELECT CAND_ID, ttl_indiv, s_total, s_item, s_unitem, ttl_indiv - s_total AS diff_from_total FROM ind
WHERE abs(ttl_indiv - s_total) > 1 AND abs(ttl_indiv - s_item) > 1 ORDER BY abs(ttl_indiv - s_total) DESC
""")
show("Q4c: committee_summary: INDV_CONTB = INDV_ITEM_CONTB + INDV_UNITEM_CONTB?", """
SELECT count(*) AS committees, count(*) FILTER (WHERE INDV_CONTB IS NULL OR trim(INDV_CONTB) = '') AS blank_total,
    count(*) FILTER (WHERE abs(amt(INDV_CONTB) - coalesce(amt(INDV_ITEM_CONTB), 0) - coalesce(amt(INDV_UNITEM_CONTB), 0)) <= 0.01) AS identity_holds,
    count(*) FILTER (WHERE abs(amt(INDV_CONTB) - coalesce(amt(INDV_ITEM_CONTB), 0) - coalesce(amt(INDV_UNITEM_CONTB), 0)) > 0.01) AS identity_fails,
    count(*) FILTER (WHERE amt(INDV_CONTB) IS NOT NULL AND (INDV_ITEM_CONTB IS NULL OR INDV_UNITEM_CONTB IS NULL)) AS a_part_blank,
    sum(amt(INDV_CONTB)) AS indv_contb, sum(amt(INDV_ITEM_CONTB)) AS indv_item_contb, sum(amt(INDV_UNITEM_CONTB)) AS indv_unitem_contb
FROM cs
""")
show("Q4d: committee_summary rows where the identity fails", """
SELECT CMTE_ID, CMTE_NM, CMTE_TP, INDV_CONTB, INDV_ITEM_CONTB, INDV_UNITEM_CONTB,
    amt(INDV_CONTB) - coalesce(amt(INDV_ITEM_CONTB), 0) - coalesce(amt(INDV_UNITEM_CONTB), 0) AS gap
FROM cs WHERE abs(amt(INDV_CONTB) - coalesce(amt(INDV_ITEM_CONTB), 0) - coalesce(amt(INDV_UNITEM_CONTB), 0)) > 0.01
ORDER BY abs(gap) DESC LIMIT 20
""")
show("Q4e: webk INDV_CONTRIB against committee_summary's INDV_CONTB and INDV_ITEM_CONTB", """
SELECT count(*) AS committees, count(*) FILTER (WHERE amt(c.INDV_UNITEM_CONTB) <> 0) AS with_unitemized,
    count(*) FILTER (WHERE abs(amt(k.INDV_CONTRIB) - amt(c.INDV_CONTB)) <= 1) AS equals_total,
    count(*) FILTER (WHERE abs(amt(k.INDV_CONTRIB) - amt(c.INDV_ITEM_CONTB)) <= 1) AS equals_itemized,
    count(*) FILTER (WHERE abs(amt(k.INDV_CONTRIB) - amt(c.INDV_CONTB)) <= 1 AND abs(amt(k.INDV_CONTRIB) - amt(c.INDV_ITEM_CONTB)) > 1) AS equals_total_not_itemized,
    count(*) FILTER (WHERE abs(amt(k.INDV_CONTRIB) - amt(c.INDV_ITEM_CONTB)) <= 1 AND abs(amt(k.INDV_CONTRIB) - amt(c.INDV_CONTB)) > 1) AS equals_itemized_not_total,
    count(*) FILTER (WHERE abs(amt(k.INDV_CONTRIB) - amt(c.INDV_CONTB)) > 1 AND abs(amt(k.INDV_CONTRIB) - amt(c.INDV_ITEM_CONTB)) > 1) AS equals_neither
FROM webk AS k JOIN cs AS c USING (CMTE_ID) WHERE k.INDV_CONTRIB IS NOT NULL AND c.INDV_CONTB IS NOT NULL
""")
show("Q4f: webk committees where INDV_CONTRIB equals neither", """
SELECT k.CMTE_ID, k.CMTE_NM, k.CMTE_TP, amt(k.INDV_CONTRIB) AS webk_indv, amt(c.INDV_CONTB) AS cs_total,
    amt(c.INDV_ITEM_CONTB) AS cs_item, amt(c.INDV_UNITEM_CONTB) AS cs_unitem, amt(c.INDV_REF) AS cs_ref,
    amt(k.INDV_CONTRIB) - amt(c.INDV_CONTB) AS diff
FROM webk AS k JOIN cs AS c USING (CMTE_ID)
WHERE abs(amt(k.INDV_CONTRIB) - amt(c.INDV_CONTB)) > 1 AND abs(amt(k.INDV_CONTRIB) - amt(c.INDV_ITEM_CONTB)) > 1
ORDER BY abs(diff) DESC LIMIT 25
""")
```

**Q4a: weball TTL_INDIV_CONTRIB against candidate_summary's individual figures and the credited committees'  (0 s)**

| against | candidates | with_unitemized | equals_total | equals_itemized | equals_total_not_itemized | equals_itemized_not_total | equals_neither |
|---|---|---|---|---|---|---|---|
| candidate_summary | 2,320 | 2,059 | 2,305 | 264 | 2,049 | 8 | 7 |
| credited committees (INDV_CONTB, INDV_ITEM_CONTB) | 3,637 | 2,224 | 3,623 | 1,432 | 2,201 | 7 | 7 |

**Q4b: weball candidates where TTL_INDIV_CONTRIB equals neither candidate_summary figure  (0 s)**

| CAND_ID | ttl_indiv | s_total | s_item | s_unitem | diff_from_total |
|---|---|---|---|---|---|
| P40006983 | 32,148 | 952 | 14,795 | 17,353 | 31,196 |
| H4CA32129 | 3,722 | 277 | 3,674 | 48 | 3,445 |
| H4IN08306 | 7,676 | 5,205 | 5,496 | 2,180 | 2,471 |
| P40005928 | 626 | 0 | 0 | 626 | 626 |
| P20003174 | 120 | 0 | 50 | 70 | 120 |
| S4UT00324 | 6,876 | 6,856 | 6,620 | 256 | 20 |
| H4IN03190 | 5,102 | 5,093 | 5,010 | 93 | 10 |

**Q4c: committee_summary: INDV_CONTB = INDV_ITEM_CONTB + INDV_UNITEM_CONTB?  (0 s)**

| committees | blank_total | identity_holds | identity_fails | a_part_blank | indv_contb | indv_item_contb | indv_unitem_contb |
|---|---|---|---|---|---|---|---|
| 13,995 | 322 | 13,507 | 166 | 20 | 19,118,115,813 | 15,590,924,166 | 3,338,729,590 |

**Q4d: committee_summary rows where the identity fails  (0 s)**

| CMTE_ID | CMTE_NM | CMTE_TP | INDV_CONTB | INDV_ITEM_CONTB | INDV_UNITEM_CONTB | gap |
|---|---|---|---|---|---|---|
| C00838862 | DEVELOPMENT NOW FOR CHICAGO | X | 99294038.81 |  | 627 | 99,293,412 |
| C00834978 | 170 FREEDOM MILWAUKEE 2024 HOST COMMITTEE INC | X | 90390559.74 |  | 109.5 | 90,390,450 |
| C00249581 | AMERICAN ASSOCIATION OF BIOANALYSTS POLITICAL ACTION COMMITTEE (AAB*PAC) | Q | 699 | 699033 | 0 | -698,334 |
| C00164236 | REPUBLICAN PARTY 2ND CONG DISTRICT WI | X | 0 | 54028.01 | 14895.69 | -68,924 |
| C00844555 | NASSAU COUNTY PBA FEDERAL PAC | N | 1000 | 0 | 51000 | -50,000 |
| C00832238 | DEMOCRACY THROUGH VOTING | O | 45545.12 | 85172.62 | 0 | -39,628 |
| C00805697 | JASMINE SHERMAN FOR PRESIDENT | P | 952.24 | 14795 | 17353 | -31,196 |
| C00389601 | ASSOCIATION OF MARYLAND PILOTS PAC | Q | 20543 | 0 | 0 | 20,543 |
| C00207969 | NATIONAL CUSTOMS BROKERS & FORWARDERS ASSOCIATION PAC | Q | 17130 | 14350 | 23065 | -20,285 |
| C00656546 | AMERICAN ASSOCIATION OF COSMETOLOGY SCHOOLS POLITICAL ACTION COMMITTEE (AACS PAC) | N | 0 | 19450 | 0 | -19,450 |
| C00833988 | GEORGIA FREEDOM FUND | N | 0 | 18550 | 400 | -18,950 |
| C00141242 | AGRI-MARK INC POLITICAL ACTION COMMITTEE | Q | 0 | 18589.8 | 0 | -18,590 |
| C00299867 | UNITED STEELWORKERS LOCAL 420-A PAC  | Q | 2165.57 | 0 | 19123.07 | -16,958 |
| C00549162 | KPH HEALTHCARE SERVICES, INC. POLITICAL ACTION COMMITTEE | N | 13600 | 27775 | 1925 | -16,100 |
| C00417394 | INTL ASSOC OF HEAT/FROST INSULATORS/ASBESTOS WKRS LOC NO 1 PAC (IAH | Q | 15252.62 | 0 | 29962.65 | -14,710 |
| C00188078 | 7TH DISTRICT REPUBLICAN PARTY OF WISCONSIN | Y | 2276.46 | 40 | 15220.46 | -12,984 |
| C00169441 | DICKIE, MCCAMEY & CHILCOTE, PC POLITICAL ACTION COMMITTEE | Q | 10950 | 0 | 0 | 10,950 |
| C00297853 | UNITED CATCHER BOATS PAC | Q | 7781.18 | 0 | 18541.18 | -10,760 |
| C00852228 | CONSTANCE JOHNSON FOR PRESIDENT OF THE UNITED STATES OF AMERICA | P | 10201 |  |  | 10,201 |
| C00843573 | FRIENDS OF JORDAN HESS | H | 0 | 9742 | 0 | -9,742 |

**Q4e: webk INDV_CONTRIB against committee_summary's INDV_CONTB and INDV_ITEM_CONTB  (0 s)**

| committees | with_unitemized | equals_total | equals_itemized | equals_total_not_itemized | equals_itemized_not_total | equals_neither |
|---|---|---|---|---|---|---|
| 9,836 | 5,488 | 9,770 | 4,394 | 5,389 | 21 | 45 |

**Q4f: webk committees where INDV_CONTRIB equals neither  (0 s)**

| CMTE_ID | CMTE_NM | CMTE_TP | webk_indv | cs_total | cs_item | cs_unitem | cs_ref | diff |
|---|---|---|---|---|---|---|---|---|
| C00164236 | REPUBLICAN PARTY 2ND CONG DISTRICT WI | X | 68,924 | 0 | 54,028 | 14,896 | 0 | 68,924 |
| C00844555 | NASSAU COUNTY PBA FEDERAL PAC | N | 51,000 | 1,000 | 0 | 51,000 | 0 | 50,000 |
| C00207969 | NATIONAL CUSTOMS BROKERS & FORWARDERS ASSOCIATION PAC | Q | 37,415 | 17,130 | 14,350 | 23,065 | 0 | 20,285 |
| C00833988 | GEORGIA FREEDOM FUND | N | 18,950 | 0 | 18,550 | 400 | 0 | 18,950 |
| C00299867 | UNITED STEELWORKERS LOCAL 420-A PAC  | Q | 19,123 | 2,166 | 0 | 19,123 | 0 | 16,958 |
| C00549162 | KPH HEALTHCARE SERVICES, INC. POLITICAL ACTION COMMITTEE | N | 29,700 | 13,600 | 27,775 | 1,925 | 0 | 16,100 |
| C00417394 | INTL ASSOC OF HEAT/FROST INSULATORS/ASBESTOS WKRS LOC NO 1 PAC (IAH | Q | 29,963 | 15,253 | 0 | 29,963 | 0 | 14,710 |
| C00188078 | 7TH DISTRICT REPUBLICAN PARTY OF WISCONSIN | Y | 15,402 | 2,276 | 40 | 15,220 | 0 | 13,126 |
| C00297853 | UNITED CATCHER BOATS PAC | Q | 18,541 | 7,781 | 0 | 18,541 | 0 | 10,760 |
| C00803155 | COBALT ADVOCATES FEDERAL POLITICAL ACTION | N | 11,220 | 1,536 | 10,536 | 685 | 0 | 9,685 |
| C00156935 | AMERICAN INTELLECTUAL PROPERTY LAW ASSOCIATION (AIPLA) PAC | Q | 32,750 | 23,650 | 20,600 | 12,150 | 0 | 9,100 |
| C00114314 | NATIONAL ASSOCIATION OF LETTER CARRIERS OF UNITED STATES OF AMERICA BRANCH 9 P.A.L. | Q | 16,137 | 8,227 | 0 | 16,137 | 0 | 7,910 |
| C00371625 | NATIONAL AIR CARRIER ASSOCIATION POLITICAL ACTION COMMITTEE | N | 12,040 | 4,420 | 8,040 | 4,000 | 0 | 7,620 |
| C00402768 | MOTORCYCLE PAC OF MINNESOTA | N | 24,802 | 17,211 | 0 | 24,802 | 0 | 7,591 |
| C00455352 | CHICO DEMOCRATS | Y | 41,370 | 36,220 | 16,695 | 24,625 | 0 | 5,150 |
| C00363069 | MARYLAND & VIRGINIA MILK PRODUCERS COOPERATIVE ASSOCIATION INC POLITICAL ACTION COMMITTEE | Q | 18,711 | 13,637 | 16,717 | 1,994 | 0 | 5,074 |
| C00451088 | PLUMBERS LOCAL 98 POLITICAL ACTION COMMITTEE | Q | 4,705 | 628 | 0 | 4,705 | 0 | 4,076 |
| C00536722 | SHASTA COUNTY DEMOCRATIC WOMENS CLUB AND FRIENDS | N | 6,194 | 2,231 | 0 | 6,194 | 0 | 3,963 |
| C00428706 | NORTHEAST TENNESSEE DEMOCRAT RESOURCE CENTER | N | 15,524 | 12,083 | 9,051 | 6,842 | 0 | 3,441 |
| C00407965 | FISHING VESSEL OWNERS ASSOCIATION HALIBUT AND SABLEFISH SUSTAINABLE FISH PAC | Q | 7,400 | 4,100 | 0 | 7,400 | 0 | 3,300 |
| C00392373 | RIETH-RILEY CONSTRUCTION CO INC FEDERAL POLITICAL ACTION COMMITTEE | N | 4,210 | 1,050 | 100 | 4,110 | 0 | 3,160 |
| C00337964 | K-VA-T FOOD STORES INC FOODPAC | Q | 14,728 | 11,580 | 11,470 | 3,258 | 0 | 3,148 |
| C00118828 | BOILERMAKERS LOCAL 85 FEDERAL POLITICAL ACTION COMMITTEE | Q | 19,923 | 16,865 | 0 | 19,923 | 0 | 3,058 |
| C00022756 | DARIGOLD POLITICAL ACTION COMMITTEE FKA NORTH PACIFIC DAIRY | Q | 34,640 | 32,191 | 30,075 | 4,566 | 0 | 2,450 |
| C00331876 | ORGANIZATION OF STAFF ANALYSTS PAC | Q | 4,206 | 2,064 | 527 | 3,679 | 0 | 2,142 |

**Reading. Yes.** `TTL_INDIV_CONTRIB` equals `candidate_summary.Individual_Contribution` (itemized
plus unitemized) for 2,305 of 2,320 candidates. It equals the itemized figure alone and not the
total for only 8. The candidates where both are equal have no unitemized money. Against the credited
committees it is 2,201 against 7.

`webk.INDV_CONTRIB` is likewise the total: 5,389 committees against 21. Where it equals neither
(45 committees), it is usually itemized plus unitemized and `committee_summary.INDV_CONTB` is the
filer's own total line, which does not add up.

That identity, `INDV_CONTB = INDV_ITEM_CONTB + INDV_UNITEM_CONTB`, holds for 13,507 committees and
fails for 166. Two of the failures are convention host committees (Form 4), whose
`INDV_ITEM_CONTB` is blank. The rest are filers' arithmetic. `reported_total` should store the
three figures as filed and not derive one from the others.

## Q5: coverage today

```python
show("Q5a: committees compared", """
SELECT (SELECT count(*) FROM gold_cc) AS gold_committees, (SELECT count(*) FROM cov) AS with_summary_row,
    (SELECT count(*) FROM cov WHERE item IS NULL) AS summary_itemized_blank,
    (SELECT count(*) FROM cov WHERE item > 0) AS summary_itemized_positive,
    (SELECT sum(item) FROM cov) AS fec_itemized, (SELECT sum(a) FROM cov) AS fundlens_a,
    (SELECT sum(b) FROM cov) AS fundlens_b, (SELECT sum(refunds) FROM cov) AS fec_indv_refunds
""")
show("Q5b: gold committees with no summary row, and summary rows with no gold row", """
SELECT 'gold, no committee_summary row' AS side, grp(c.type) AS grp, count(*) AS committees,
    count(*) FILTER (WHERE g.total_individual <> 0 OR g.total_from_organizations <> 0) AS with_fundlens_money,
    sum(g.total_individual) AS fundlens_a, sum(g.total_individual + g.total_from_organizations) AS fundlens_b, NULL AS fec_itemized
FROM gold_cc AS g JOIN silver.committee AS c USING (committee_id) ANTI JOIN cs ON cs.CMTE_ID = g.committee_id GROUP BY ALL
UNION ALL
SELECT 'committee_summary, no gold row', grp(cs.CMTE_TP), count(*), NULL, NULL, NULL, sum(amt(cs.INDV_ITEM_CONTB))
FROM cs ANTI JOIN gold_cc AS g ON g.committee_id = cs.CMTE_ID GROUP BY ALL
ORDER BY 1, 2
""")
show("Q5c: B / FEC itemized by decile and committee group (committees with FEC itemized > 0)", """
SELECT grp, count(*) AS committees,
    quantile_cont(b / item, 0.1) AS p10, quantile_cont(b / item, 0.25) AS p25, quantile_cont(b / item, 0.5) AS median,
    quantile_cont(b / item, 0.75) AS p75, quantile_cont(b / item, 0.9) AS p90,
    sum(b) / sum(item) AS dollar_weighted
FROM cov WHERE item > 0 GROUP BY ROLLUP (grp) ORDER BY grp NULLS LAST
""")
show("Q5d: A / FEC itemized by decile and committee group (committees with FEC itemized > 0)", """
SELECT grp, count(*) AS committees,
    quantile_cont(a / item, 0.1) AS p10, quantile_cont(a / item, 0.25) AS p25, quantile_cont(a / item, 0.5) AS median,
    quantile_cont(a / item, 0.75) AS p75, quantile_cont(a / item, 0.9) AS p90,
    sum(a) / sum(item) AS dollar_weighted
FROM cov WHERE item > 0 GROUP BY ROLLUP (grp) ORDER BY grp NULLS LAST
""")
show("Q5e: deciles of B / itemized over every committee with FEC itemized > 0", """
SELECT unnest([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]) AS q,
    unnest(quantile_cont(b / item, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])) AS b_ratio,
    unnest(quantile_cont(a / item, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])) AS a_ratio
FROM cov WHERE item > 0
""")
show("Q5f: committees by band of B / itemized (and A / itemized), with FEC's dollars", """
WITH banded AS (
    SELECT *, CASE WHEN coalesce(item, 0) = 0 THEN CASE WHEN b > 0 THEN 'FEC 0, fundlens > 0' ELSE 'both 0' END
        WHEN b < 0.99 * item THEN '< 0.99' WHEN b <= 1.01 * item THEN '0.99-1.01' ELSE '> 1.01' END AS band_b,
        CASE WHEN coalesce(item, 0) = 0 THEN CASE WHEN a > 0 THEN 'FEC 0, fundlens > 0' ELSE 'both 0' END
        WHEN a < 0.99 * item THEN '< 0.99' WHEN a <= 1.01 * item THEN '0.99-1.01' ELSE '> 1.01' END AS band_a
    FROM cov
)
SELECT 'B' AS measure, band_b AS band, count(*) AS committees, sum(item) AS fec_itemized, sum(b) AS fundlens
FROM banded GROUP BY ALL
UNION ALL
SELECT 'A', band_a, count(*), sum(item), sum(a) FROM banded GROUP BY ALL
ORDER BY 1, 2
""")
show("Q5g: B and A against FEC itemized, by committee group", """
SELECT grp, count(*) AS committees, sum(item) AS fec_itemized, sum(unitem) AS fec_unitemized, sum(a) AS fundlens_a, sum(orgs) AS organizations, sum(b) AS fundlens_b,
    sum(a) / sum(item) AS a_over_itemized, sum(b) / sum(item) AS b_over_itemized,
    count(*) FILTER (WHERE item > 0 AND abs(a - item) <= 0.01 * item) AS a_within_1_pct,
    count(*) FILTER (WHERE item > 0 AND abs(b - item) <= 0.01 * item) AS b_within_1_pct,
    count(*) FILTER (WHERE a - coalesce(item, 0) > 0.01 * abs(coalesce(item, 0))) AS a_over_1_pct,
    count(*) FILTER (WHERE b - coalesce(item, 0) > 0.01 * abs(coalesce(item, 0))) AS b_over_1_pct,
    sum(greatest(item - b, 0)) AS fec_not_reached_b
FROM cov GROUP BY ROLLUP (grp) ORDER BY grp NULLS LAST
""")
show("Q5h: dollars FEC reports that fundlens (B) does not reach, by CMTE_TP", """
SELECT type, count(*) FILTER (WHERE item > b) AS committees_short, sum(greatest(item - b, 0)) AS fec_not_reached,
    sum(greatest(b - coalesce(item, 0), 0)) AS fundlens_over
FROM cov GROUP BY ALL ORDER BY 2 DESC
""")
show("Q5i: the over-1% list: count and dollars", """
SELECT count(*) AS committees, count(*) FILTER (WHERE excess_a > 0.01 * abs(coalesce(item, 0))) AS over_on_a,
    count(*) FILTER (WHERE excess_b > 0.01 * abs(coalesce(item, 0))) AS over_on_b,
    count(*) FILTER (WHERE coalesce(item, 0) = 0) AS fec_itemized_0_or_blank,
    sum(greatest(excess_a, 0)) AS excess_a_dollars, sum(greatest(excess_b, 0)) AS excess_b_dollars
FROM over
""")
show("Q5j: the over-1% list by group and size of excess (B)", """
SELECT grp, CASE WHEN excess_b < 1000 THEN '< $1k' WHEN excess_b < 10000 THEN '$1k-10k' WHEN excess_b < 100000 THEN '$10k-100k'
    WHEN excess_b < 1000000 THEN '$100k-1M' ELSE '>= $1M' END AS excess_b_size, count(*) AS committees, sum(excess_b) AS excess_b
FROM over GROUP BY ALL ORDER BY 1, min(excess_b)
""")

show("Q5k: B against FEC itemized alone and against itemized plus OTHER_RECEIPTS (line 15), committees within 1%", """
SELECT cov.grp, count(*) FILTER (WHERE item > 0) AS committees,
    count(*) FILTER (WHERE item > 0 AND abs(b - item) <= 0.01 * item) AS b_within_1_pct_of_itemized,
    count(*) FILTER (WHERE item > 0 AND abs(a - item) <= 0.01 * item) AS a_within_1_pct_of_itemized,
    count(*) FILTER (WHERE item > 0 AND abs(b - (item + coalesce(amt(c.OTHER_RECEIPTS), 0))) <= 0.01 * (item + coalesce(amt(c.OTHER_RECEIPTS), 0)))
        AS b_within_1_pct_of_itemized_plus_line_15,
    count(*) FILTER (WHERE item > 0 AND b > 1.01 * item) AS b_over,
    count(*) FILTER (WHERE item > 0 AND b > 1.01 * item AND b <= 1.01 * (item + coalesce(amt(c.OTHER_RECEIPTS), 0))) AS b_over_but_within_line_15
FROM cov JOIN cs AS c ON c.CMTE_ID = cov.committee_id GROUP BY ROLLUP (cov.grp) ORDER BY cov.grp NULLS LAST
""")
show("Q5l: the conduits (fec/conduits.csv) against FEC itemized: FEC counts the earmarks they pass on, fundlens counts them at the recipient (ADR-0004)", """
SELECT cov.committee_id, cov.name, cov.type, cov.item AS fec_itemized, cov.a, cov.b, cov.item - cov.b AS fec_not_reached
FROM cov WHERE committee_id IN (SELECT committee_id FROM silver.committee WHERE is_conduit) ORDER BY cov.item DESC NULLS LAST
""")
show("Q5m: FEC itemized dollars fundlens (B) does not reach: conduits and the rest", """
SELECT committee_id IN (SELECT committee_id FROM silver.committee WHERE is_conduit) AS conduit, count(*) FILTER (WHERE item > b) AS committees_short,
    sum(greatest(item - b, 0)) AS fec_not_reached
FROM cov GROUP BY ALL ORDER BY 1
""")

show("Q5n: A and B against FEC's individual total (INDV_CONTB, itemized and unitemized), by committee group", """
SELECT grp, count(*) FILTER (WHERE total > 0) AS committees, sum(total) AS fec_total, sum(a) / sum(total) AS a_over_total,
    sum(b) / sum(total) AS b_over_total, quantile_cont(a / total, 0.5) AS a_median, quantile_cont(b / total, 0.5) AS b_median
FROM cov WHERE total > 0 GROUP BY ROLLUP (grp) ORDER BY grp NULLS LAST
""")
```

**Q5a: committees compared  (0 s)**

| gold_committees | with_summary_row | summary_itemized_blank | summary_itemized_positive | fec_itemized | fundlens_a | fundlens_b | fec_indv_refunds |
|---|---|---|---|---|---|---|---|
| 20,937 | 13,994 | 322 | 8,714 | 15,590,924,166 | 9,432,495,555 | 11,686,802,299 | 319,304,106 |

**Q5b: gold committees with no summary row, and summary rows with no gold row  (0 s)**

| side | grp | committees | with_fundlens_money | fundlens_a | fundlens_b | fec_itemized |
|---|---|---|---|---|---|---|
| committee_summary, no gold row | other | 1 |  |  |  |  |
| gold, no committee_summary row | PAC | 501 | 0 | 0.00% | 0.00% |  |
| gold, no committee_summary row | candidate | 4,885 | 0 | 0.00% | 0.00% |  |
| gold, no committee_summary row | hybrid PAC | 116 | 0 | 0.00% | 0.00% |  |
| gold, no committee_summary row | other | 814 | 0 | 0.00% | 0.00% |  |
| gold, no committee_summary row | party | 134 | 0 | 0.00% | 0.00% |  |
| gold, no committee_summary row | super PAC | 493 | 0 | 0.00% | 0.00% |  |

**Q5c: B / FEC itemized by decile and committee group (committees with FEC itemized > 0)  (0 s)**

| grp | committees | p10 | p25 | median | p75 | p90 | dollar_weighted |
|---|---|---|---|---|---|---|---|
| PAC | 4,573 | 88.87% | 98.51% | 99.95% | 100.00% | 100.00% | 94.97% |
| candidate | 2,296 | 67.79% | 91.18% | 97.80% | 99.99% | 100.00% | 96.17% |
| hybrid PAC | 431 | 88.83% | 99.97% | 118.13% | 528.90% | 3491.27% | 27.19% |
| party | 359 | 76.17% | 94.38% | 99.13% | 100.00% | 100.00% | 108.18% |
| super PAC | 1,055 | 91.94% | 99.96% | 100.00% | 100.00% | 100.00% | 98.37% |
|  | 8,714 | 82.80% | 96.85% | 99.91% | 100.00% | 100.00% | 72.29% |

**Q5d: A / FEC itemized by decile and committee group (committees with FEC itemized > 0)  (0 s)**

| grp | committees | p10 | p25 | median | p75 | p90 | dollar_weighted |
|---|---|---|---|---|---|---|---|
| PAC | 4,573 | 82.70% | 97.63% | 99.90% | 100.00% | 100.00% | 94.47% |
| candidate | 2,296 | 65.37% | 89.91% | 97.24% | 99.98% | 100.00% | 95.82% |
| hybrid PAC | 431 | 80.59% | 99.28% | 100.00% | 306.99% | 1542.11% | 15.60% |
| party | 359 | 70.69% | 92.70% | 98.60% | 100.00% | 100.00% | 106.24% |
| super PAC | 1,055 | 0.00% | 12.63% | 84.68% | 100.00% | 100.00% | 60.14% |
|  | 8,714 | 56.28% | 92.69% | 99.56% | 100.00% | 100.00% | 59.13% |

**Q5e: deciles of B / itemized over every committee with FEC itemized > 0  (0 s)**

| q | b_ratio | a_ratio |
|---|---|---|
| 0 | 82.80% | 56.28% |
| 0 | 94.95% | 87.88% |
| 0 | 98.07% | 95.38% |
| 0 | 99.44% | 98.19% |
| 0 | 99.91% | 99.56% |
| 1 | 100.00% | 99.95% |
| 1 | 100.00% | 100.00% |
| 1 | 100.00% | 100.00% |
| 1 | 100.00% | 100.00% |

**Q5f: committees by band of B / itemized (and A / itemized), with FEC's dollars  (0 s)**

| measure | band | committees | fec_itemized | fundlens |
|---|---|---|---|---|
| A | 0.99-1.01 | 4,440 | 1,842,861,104 | 1,837,141,817 |
| A | < 0.99 | 3,913 | 13,092,658,727 | 5,926,976,716 |
| A | > 1.01 | 370 | 655,404,335 | 1,454,003,399 |
| A | FEC 0, fundlens > 0 | 141 | 0 | 218,735,766 |
| A | both 0 | 5,130 | 0 | -4,362,143 |
| B | 0.99-1.01 | 5,114 | 3,394,974,747 | 3,389,314,634 |
| B | < 0.99 | 3,131 | 10,687,695,385 | 4,850,600,008 |
| B | > 1.01 | 478 | 1,508,254,035 | 3,031,066,060 |
| B | FEC 0, fundlens > 0 | 244 | 0 | 420,383,326 |
| B | both 0 | 5,027 | 0 | -4,561,729 |

**Q5g: B and A against FEC itemized, by committee group  (0 s)**

| grp | committees | fec_itemized | fec_unitemized | fundlens_a | organizations | fundlens_b | a_over_itemized | b_over_itemized | a_within_1_pct | b_within_1_pct | a_over_1_pct | b_over_1_pct | fec_not_reached_b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PAC | 6,367 | 3,548,788,852 | 1,421,357,922 | 3,351,038,135 | 17,845,506 | 3,368,883,641 | 94.43% | 94.93% | 3,052 | 3,229 | 60 | 67 | 183,542,982 |
| candidate | 4,008 | 2,199,130,165 | 1,039,078,996 | 2,107,564,605 | 7,828,016 | 2,115,392,621 | 95.84% | 96.19% | 728 | 812 | 117 | 119 | 116,758,761 |
| hybrid PAC | 781 | 5,570,360,342 | 266,106,582 | 1,073,361,553 | 772,375,565 | 1,845,737,118 | 19.27% | 33.13% | 121 | 102 | 253 | 343 | 5,405,625,135 |
| other | 276 |  |  | 4,250,143 | 7,679,311 | 11,929,454 |  |  | 0 | 0 | 34 | 52 | 0 |
| party | 480 | 695,375,132 | 495,733,315 | 743,001,484 | 36,948,890 | 779,950,374 | 106.85% | 112.16% | 153 | 169 | 15 | 20 | 7,621,882 |
| super PAC | 2,082 | 3,577,269,676 | 116,452,776 | 2,153,279,635 | 1,411,629,456 | 3,564,909,091 | 60.19% | 99.65% | 386 | 802 | 32 | 121 | 134,888,711 |
|  | 13,994 | 15,590,924,166 | 3,338,729,590 | 9,432,495,555 | 2,254,306,744 | 11,686,802,299 | 60.50% | 74.96% | 4,440 | 5,114 | 511 | 722 | 5,848,437,471 |

**Q5h: dollars FEC reports that fundlens (B) does not reach, by CMTE_TP  (0 s)**

| type | committees_short | fec_not_reached | fundlens_over |
|---|---|---|---|
| Q | 1,901 | 98,931,033 | 2,620,580 |
| H | 1,536 | 44,677,045 | 5,143,751 |
| N | 999 | 84,611,949 | 1,017,191 |
| O | 432 | 134,788,711 | 122,447,126 |
| S | 308 | 42,015,351 | 1,592,414 |
| Y | 176 | 6,987,327 | 64,434,471 |
| V | 96 | 5,403,841,682 | 1,115,883,498 |
| X | 87 | 634,555 | 27,762,653 |
| P | 54 | 30,066,365 | 26,285,052 |
| W | 23 | 1,783,453 | 565,118,413 |
| U | 2 | 100,000 | 81,000 |
|  | 0 | 0 | 0 |
| C | 0 | 0 | 0 |
| I | 0 | 0 | 11,929,454 |

**Q5i: the over-1% list: count and dollars  (0 s)**

| committees | over_on_a | over_on_b | fec_itemized_0_or_blank | excess_a_dollars | excess_b_dollars |
|---|---|---|---|---|---|
| 725 | 511 | 722 | 244 | 1,017,385,092 | 1,943,196,031 |

**Q5j: the over-1% list by group and size of excess (B)  (0 s)**

| grp | excess_b_size | committees | excess_b |
|---|---|---|---|
| PAC | < $1k | 14 | 5,786 |
| PAC | $1k-10k | 29 | 112,018 |
| PAC | $10k-100k | 20 | 482,583 |
| PAC | $100k-1M | 4 | 875,388 |
| PAC | >= $1M | 1 | 2,110,085 |
| candidate | < $1k | 34 | 8,200 |
| candidate | $1k-10k | 44 | 162,231 |
| candidate | $10k-100k | 27 | 765,556 |
| candidate | $100k-1M | 12 | 3,751,608 |
| candidate | >= $1M | 3 | 28,293,184 |
| hybrid PAC | < $1k | 10 | 2,788 |
| hybrid PAC | $1k-10k | 40 | 163,708 |
| hybrid PAC | $10k-100k | 92 | 3,933,007 |
| hybrid PAC | $100k-1M | 125 | 40,117,965 |
| hybrid PAC | >= $1M | 77 | 1,636,758,230 |
| other | < $1k | 8 | 5,013 |
| other | $1k-10k | 12 | 36,685 |
| other | $10k-100k | 17 | 738,396 |
| other | $100k-1M | 11 | 3,364,170 |
| other | >= $1M | 4 | 7,785,190 |
| party | < $1k | 1 | 360 |
| party | $10k-100k | 6 | 352,857 |
| party | $100k-1M | 7 | 2,994,139 |
| party | >= $1M | 6 | 88,842,623 |
| super PAC | < $1k | 13 | 4,789 |
| super PAC | $1k-10k | 21 | 74,753 |
| super PAC | $10k-100k | 31 | 1,179,451 |
| super PAC | $100k-1M | 36 | 13,496,244 |
| super PAC | >= $1M | 20 | 106,774,182 |

**Q5k: B against FEC itemized alone and against itemized plus OTHER_RECEIPTS (line 15), committees within 1%  (0 s)**

| grp | committees | b_within_1_pct_of_itemized | a_within_1_pct_of_itemized | b_within_1_pct_of_itemized_plus_line_15 | b_over | b_over_but_within_line_15 |
|---|---|---|---|---|---|---|
| PAC | 4,573 | 3,229 | 3,052 | 2,943 | 62 | 9 |
| candidate | 2,296 | 812 | 728 | 730 | 76 | 6 |
| hybrid PAC | 431 | 102 | 121 | 142 | 246 | 246 |
| other | 0 | 0 | 0 | 0 | 0 | 0 |
| party | 359 | 169 | 153 | 140 | 18 | 11 |
| super PAC | 1,055 | 802 | 386 | 782 | 74 | 41 |
|  | 8,714 | 5,114 | 4,440 | 4,737 | 476 | 313 |

**Q5l: the conduits (fec/conduits.csv) against FEC itemized: FEC counts the earmarks they pass on, fundlens counts them at the recipient (ADR-0004)  (0 s)**

| committee_id | name | type | fec_itemized | a | b | fec_not_reached |
|---|---|---|---|---|---|---|
| C00401224 | ACTBLUE | V | 3,758,627,951 | 26,611,402 | 26,612,661 | 3,732,015,290 |
| C00694323 | WINRED | V | 1,614,739,959 | -48,199,349 | -48,199,349 | 1,662,939,308 |

**Q5m: FEC itemized dollars fundlens (B) does not reach: conduits and the rest  (0 s)**

| conduit | committees_short | fec_not_reached |
|---|---|---|
| False | 5,612 | 453,482,873 |
| True | 2 | 5,394,954,598 |

**Q5n: A and B against FEC's individual total (INDV_CONTB, itemized and unitemized), by committee group  (0 s)**

| grp | committees | fec_total | a_over_total | b_over_total | a_median | b_median |
|---|---|---|---|---|---|---|
| PAC | 4,846 | 4,969,117,743 | 67.47% | 67.82% | 87.01% | 88.49% |
| candidate | 2,451 | 3,238,287,705 | 65.07% | 65.31% | 72.99% | 73.37% |
| hybrid PAC | 499 | 5,836,466,488 | 16.19% | 27.40% | 86.72% | 97.52% |
| party | 390 | 1,380,702,926 | 53.81% | 56.49% | 57.23% | 58.55% |
| super PAC | 1,174 | 3,693,686,129 | 58.25% | 95.31% | 42.81% | 99.57% |
|  | 9,360 | 19,118,260,990 | 48.64% | 59.55% | 79.06% | 84.04% |

**Reading.**

- **B is the figure `coverage` should use.** Form 3X line 11(a)(i) counts every giver who is not a
  political committee, organizations included. B is within 1% of FEC's itemized figure at 5,114
  committees and A at 4,440. At super PACs it is 802 against 386, and dollar weighted 99.65% against
  60.19%. A under-counts every super PAC by its organization money. B is within 1% at more
  PACs (3,229 against 3,052), candidate committees (812 against 728) and parties (169 against 153).
  Across all committees the median B is 99.91% of FEC's itemized figure, the 25th percentile
  96.85% (Q5c).
- **Where B runs over, and why** (Q6 has the detail):
  - Hybrid PACs: only 102 of 431 are within 1%, because the non-contribution account's type-10
    money is in B (NEU-2192).
  - Some super PACs put organization money on line 15, other receipts. Of the 74 super PACs over 1%,
    41 are within 1% of itemized plus `OTHER_RECEIPTS` (Q5k).
  - Parties: special accounts (NEU-2193).

  Comparing B against itemized plus line 15 instead does not help overall. It matches fewer
  committees (4,737 against 5,114), because line 15 also holds interest, dividends and refunds.
- **Conduits.** ActBlue's and WinRed's `INDV_ITEM_CONTB` ($3.76B and $1.61B) include the earmarks
  they pass on, which fundlens counts at the recipient (ADR-0004). They are $5.39B of the $5.85B of
  FEC itemized dollars that fundlens does not reach (Q5m). Coverage at a conduit is meaningless and
  should be shown as such. WinRed's B is **−$48.2M**: conduit refunds of earmarked gifts are
  counted (NEU-2199).
- Leaving the conduits aside, fundlens falls short of FEC's itemized figure by $453.5M at 5,612
  committees. The largest shares are PACs ($183.5M, types Q and N) and super PACs ($134.9M, of which
  Fairshake is $43.4M, Q7). Against FEC's individual *total* (itemized and unitemized), B is 59.55%
  dollar weighted and its median 84.04% (Q5n). Unitemized money is what the itemized files cannot
  reach.

## Q6: why fundlens exceeds FEC

Each counted row of an over-1% committee gets the first diagnostic that holds, so no dollar is
counted twice. D8 is per committee and comes last. The spec's list changed in these ways:

- **D1 (refunds) explains none of an excess.** Silver subtracts refunds, which lowers fundlens's
  figure against FEC's gross one. It is reported but not counted toward an explanation.
- **D4 skips cm types I, C and E.** Those are organizations and people that file Forms 5, 7 and 9,
  not political committees. ONE NATION, AFL-CIO and Koch Industries are among them. FEC does not put
  their gifts on the committee lines 11(b)/(c): they go on 11(a)(i) or, as at SLF, on line 15. A
  first pass without the exclusion called their gifts committee money.
- **D5 is memo lines only.** The spec also counts 15E/15I/15T rows, but FEC puts those on line
  11(a)(i) at the recipient, so they explain no excess. A surviving conduit-side row would be a 24I
  or an "EARMARKED FOR" 15, and D3 catches the 24I.
- **D7 matches by transaction type 15C or by name**, not by `contributor_key`. A contributor key
  includes ZIP code, employer and occupation, so the candidate's own gift under a different
  employer would be missed. The name test is 04_contribution.sql's own.
- **D8 is new**: organization money the filer put on line 15. It is the excess the row diagnostics
  leave, up to the committee's organization receipts and its `OTHER_RECEIPTS`. **It is fitted, not
  measured**: it reads the summary, not the rows, so it explains whatever the other diagnostics
  leave, up to those two caps. A D8 "explained" verdict means the excess fits organization money on
  line 15, not that the rows were traced there. NEU-2197's line-number check on Schedule A is how to
  confirm it.
- **"No FEC figure"** is the verdict for committees whose `INDV_ITEM_CONTB` is blank: 52 Form 5
  filers (type I), 2 Form 4 host committees (X) and 4 candidate committees (H, S; Q6d3). There is
  no figure to exceed, so they are not a fundlens excess. The 44 of them with no diagnosed cause
  ($6.5M, nearly all type-I money) are outside NEU-2197.
- Q2's 272 shared committees blank on one side (I and C types, Q2f2) are counted by type, not
  listed. Q3 breaks the match down by office and committee count for receipts only, the decision's
  measure; `compare()` gives every measure overall. Q5's deciles are by committee group, with
  dollars by `CMTE_TP` in Q5h.

The `fec_line` CASE is the transaction type → Form 3X line mapping NEU-2141 can lift.

```python
bulk("indiv")
bulk("cm")
con.execute("""
-- The FEC line each counted row's transaction type goes on (Form 3/3X), as FEC files it; `cmte_type`
-- is the recipient's CMTE_TP, since type 10 is a hybrid PAC's non-contribution account (V, W)
-- and a contribution on line 11(a)(i) anywhere else.
CREATE MACRO fec_line(tt, cmte_type) AS CASE
    WHEN tt IN ('15', '15E', '15I', '15T', '11', '11J', '15Z') THEN '11(a)(i)'
    WHEN tt IN ('10', '10J') THEN CASE WHEN cmte_type IN ('V', 'W') THEN 'non-contribution account' ELSE '11(a)(i)' END
    WHEN tt = '15C' THEN '11(d) candidate'
    WHEN tt IN ('16C', '16F', '16G', '16H', '16J', '16K', '16L', '16R') THEN '13 loans'
    WHEN tt IN ('18G', '18J', '18K', '18L') THEN '12 transfers'
    WHEN tt = '18U' THEN '11(c) unregistered committee'
    WHEN tt = '18H' THEN '15 other receipts'
    WHEN tt IN ('19', '19J') THEN 'electioneering'
    WHEN regexp_matches(tt, '^3[012][A-Z]?$') THEN 'party account ' || left(tt, 2)
    WHEN regexp_matches(tt, '^[24][0-9]Y$') OR tt = '22Z' THEN '20 refunds'
    WHEN tt = '24I' THEN 'earmark, conduit side (24I)'
    ELSE 'other: ' || coalesce(tt, '(blank)') END;

CREATE MACRO name_key(n) AS regexp_replace(upper(n), '[^A-Z0-9]', '', 'g');
CREATE MACRO last_first(n) AS
    regexp_replace(upper(split_part(n, ',', 1)), '[^A-Z0-9]', '', 'g') || '|' ||
    regexp_replace(upper(split_part(trim(split_part(n, ',', 2)), ' ', 1)), '[^A-Z0-9]', '', 'g');

-- Every committee over 1% (view `over`), with the excess it is explained against: B's, or A's
-- where only A is over.
CREATE TABLE ol AS
SELECT *, excess_b > 0.01 * abs(coalesce(item, 0)) AS on_b,
    CASE WHEN excess_b > 0.01 * abs(coalesce(item, 0)) THEN excess_b ELSE excess_a END AS excess
FROM over;

-- Every counted row of those committees: contribution (its own money aside) and, where B is the
-- measure, organization_receipt.
CREATE TABLE ro AS
SELECT 'contribution' AS src, c.recipient_committee_id AS committee_id, c.source_record_id, c.contributor_key AS key,
    c.contributor_name AS name, c.amount, c.date, c.transaction_type AS tt, c.file_num, c.candidate_id, ol.type AS cmte_type
FROM silver.contribution AS c JOIN ol ON ol.committee_id = c.recipient_committee_id
WHERE NOT c.is_self_funding
UNION ALL
SELECT 'organization', o.recipient_committee_id, o.source_record_id, o.organization_key, o.organization_name,
    o.amount, o.date, o.transaction_type, o.file_num, NULL, ol.type
FROM silver.organization_receipt AS o JOIN ol ON ol.committee_id = o.recipient_committee_id
WHERE ol.on_b;

-- Their indiv rows as filed (for D1 and D5), read once with the few keys on the right.
CREATE TABLE filed AS
SELECT indiv.SUB_ID, indiv.TRANSACTION_AMT, indiv.MEMO_CD
FROM indiv JOIN (SELECT DISTINCT source_record_id FROM ro) AS k ON k.source_record_id = indiv.SUB_ID;

-- Political committees by name: cm's types I, C and E are persons and organizations filing
-- Form 5, 7 or 9 (independent expenditures, communication costs, electioneering), not committees,
-- and FEC puts their gifts on line 11(a)(i).
CREATE TABLE cm_named AS
SELECT name_key(CMTE_NM) AS name_key, min(CMTE_ID) AS committee_id FROM cm
WHERE CMTE_TP NOT IN ('I', 'C', 'E') GROUP BY ALL HAVING count(*) = 1;

-- Each row's diagnostic, the first that holds, so no dollar is counted twice:
-- D7 the candidate's own money not flagged self-funding (a 15C, or a gift under the recipient's
-- candidate's last and first name); D3 a transaction type FEC puts on a line other than 11(a)(i);
-- D4 a giver naming exactly one cm political committee; D5 a memo line silver kept; D6 dated after the
-- summary row's coverage end; D2 a duplicate beyond the first of its (committee, giver key,
-- amount, date) group. D1, refunds, is reported apart: silver subtracts them, so they lower
-- fundlens's figure and explain none of an excess.
CREATE TABLE rd AS
WITH dup AS (
    SELECT source_record_id, src,
        row_number() OVER (PARTITION BY committee_id, src, key, amount, date ORDER BY source_record_id) > 1 AS is_dup,
        count(DISTINCT file_num) OVER (PARTITION BY committee_id, src, key, amount, date) > 1 AS files_differ
    FROM ro
)
SELECT ro.*, fec_line(ro.tt, ro.cmte_type) AS line, f.TRANSACTION_AMT AS filed_amount, f.MEMO_CD,
    CASE
        WHEN ro.src = 'contribution' AND (ro.tt = '15C' OR last_first(ro.name) = last_first(cand.name)) THEN 'D7 own money'
        WHEN fec_line(ro.tt, ro.cmte_type) NOT IN ('11(a)(i)', '20 refunds') THEN 'D3 ' || fec_line(ro.tt, ro.cmte_type)
        WHEN cmn.committee_id IS NOT NULL AND cmn.committee_id <> ro.committee_id THEN 'D4 names a committee'
        WHEN f.MEMO_CD = 'X' THEN 'D5 memo line'
        WHEN ro.date > ol.cvg_end THEN 'D6 after coverage end'
        WHEN dup.is_dup THEN CASE WHEN dup.files_differ THEN 'D2 duplicate, files differ' ELSE 'D2 duplicate, same file' END
        WHEN fec_line(ro.tt, ro.cmte_type) = '20 refunds' THEN 'D1 refund'
    END AS diag
FROM ro
JOIN ol USING (committee_id)
LEFT JOIN dup ON dup.source_record_id = ro.source_record_id AND dup.src = ro.src
LEFT JOIN filed AS f ON f.SUB_ID = ro.source_record_id
LEFT JOIN silver.candidate AS cand ON cand.candidate_id = ro.candidate_id
LEFT JOIN cm_named AS cmn ON cmn.name_key = name_key(ro.name);

CREATE TABLE diag AS
SELECT ol.committee_id, ol.name, ol.type, ol.item, ol.a, ol.b, ol.on_b, ol.excess,
    ol.excess / nullif(ol.item, 0) AS excess_pct, ol.cvg_end,
    coalesce(sum(rd.amount) FILTER (WHERE rd.diag LIKE 'D1%'), 0) AS d1_refunds,
    coalesce(sum(rd.amount) FILTER (WHERE rd.tt IN (SELECT DISTINCT tt FROM rd WHERE regexp_matches(tt, '^[24][0-9]Y$'))
        AND rd.filed_amount > 0), 0) AS d1_filed_positive,
    coalesce(sum(rd.amount) FILTER (WHERE rd.diag LIKE 'D2%'), 0) AS d2_duplicates,
    coalesce(sum(rd.amount) FILTER (WHERE rd.diag LIKE 'D3%'), 0) AS d3_other_line,
    coalesce(sum(rd.amount) FILTER (WHERE rd.diag LIKE 'D4%'), 0) AS d4_names_committee,
    coalesce(sum(rd.amount) FILTER (WHERE rd.diag LIKE 'D5%'), 0) AS d5_memo,
    coalesce(sum(rd.amount) FILTER (WHERE rd.diag LIKE 'D6%'), 0) AS d6_after_cvg_end,
    coalesce(sum(rd.amount) FILTER (WHERE rd.diag LIKE 'D7%'), 0) AS d7_own_money,
    string_agg(DISTINCT rd.diag, ', ') FILTER (WHERE rd.diag LIKE 'D3%') AS d3_lines
FROM ol LEFT JOIN rd USING (committee_id)
GROUP BY ALL;

-- D8, per committee rather than per row: organization money the filer put on line 15, other
-- receipts, not 11(a)(i). The excess the row diagnostics leave, up to the committee's
-- organization receipts and its summary's OTHER_RECEIPTS, whichever is less (measure B only).
CREATE TABLE verdict AS
WITH d AS (
    SELECT diag.*, ol.orgs, amt(c.OTHER_RECEIPTS) AS other_receipts,
        CASE WHEN diag.on_b THEN greatest(least(
            diag.excess - (d2_duplicates + d3_other_line + d4_names_committee + d5_memo + d6_after_cvg_end + d7_own_money),
            ol.orgs, coalesce(amt(c.OTHER_RECEIPTS), 0)), 0) ELSE 0 END AS d8_orgs_on_line_15
    FROM diag JOIN ol USING (committee_id) LEFT JOIN cs AS c ON c.CMTE_ID = diag.committee_id
)
SELECT *, excess - (d2_duplicates + d3_other_line + d4_names_committee + d5_memo + d6_after_cvg_end + d7_own_money
        + d8_orgs_on_line_15) AS unexplained_dollars,
    CASE WHEN item IS NULL THEN 'no FEC figure'
        WHEN excess - (d2_duplicates + d3_other_line + d4_names_committee + d5_memo + d6_after_cvg_end + d7_own_money
            + d8_orgs_on_line_15) <= greatest(0.01 * abs(item), 1) THEN 'explained' ELSE 'unexplained' END AS verdict,
    CASE greatest(d2_duplicates, d3_other_line, d4_names_committee, d5_memo, d6_after_cvg_end, d7_own_money, d8_orgs_on_line_15)
        WHEN 0 THEN 'none'
        WHEN d3_other_line THEN 'D3 other line'
        WHEN d8_orgs_on_line_15 THEN 'D8 organizations on line 15'
        WHEN d7_own_money THEN 'D7 own money'
        WHEN d6_after_cvg_end THEN 'D6 after coverage end'
        WHEN d2_duplicates THEN 'D2 duplicates'
        WHEN d4_names_committee THEN 'D4 names a committee'
        WHEN d5_memo THEN 'D5 memo line' END AS primary_cause
FROM d;
""")
```

```python
show("Q6a: diagnostics over every over-1% committee, dollars by diagnostic and line", """
SELECT coalesce(diag, '(none: an 11(a)(i) row)') AS diagnostic, count(*) AS rows, sum(amount) AS dollars,
    count(DISTINCT committee_id) AS committees
FROM rd GROUP BY ALL ORDER BY abs(sum(amount)) DESC
""")
show("Q6b: D1 refunds: rows filed positive that silver made negative", """
SELECT count(*) FILTER (WHERE filed_amount > 0) AS filed_positive, sum(filed_amount) FILTER (WHERE filed_amount > 0) AS filed_positive_dollars,
    count(*) FILTER (WHERE filed_amount < 0) AS filed_negative, sum(amount) AS silver_dollars
FROM rd WHERE line = '20 refunds'
""")
show("Q6c: D2 duplicates by whether file numbers differ", """
SELECT diag, cmte_type, count(*) AS rows, sum(amount) AS dollars, count(DISTINCT committee_id) AS committees FROM rd WHERE diag LIKE 'D2%' GROUP BY ALL ORDER BY 1, 4 DESC
""")
show("Q6c2: D3 by line and committee", """
SELECT diag, committee_id, any_value(o.name) AS name, any_value(o.type) AS type, count(*) AS rows, sum(amount) AS dollars
FROM rd JOIN ol AS o USING (committee_id) WHERE diag LIKE 'D3%' AND diag <> 'D3 non-contribution account'
GROUP BY ALL ORDER BY 1, 6 DESC
""")
show("Q6c3: D7 by transaction type, entity type, and whether the name matches the candidate's", """
SELECT rd.tt, rd.entity_type, last_first(rd.name) = last_first(cand.name) AS name_matches, count(*) AS rows, sum(rd.amount) AS dollars,
    count(DISTINCT rd.committee_id) AS committees
FROM (SELECT ro.*, c.entity_type FROM rd AS ro JOIN silver.contribution AS c
    ON c.source_record_id = ro.source_record_id AND ro.src = 'contribution' WHERE ro.diag LIKE 'D7%') AS rd
LEFT JOIN silver.candidate AS cand ON cand.candidate_id = rd.candidate_id
GROUP BY ALL ORDER BY 5 DESC
""")
show("Q6c4: D7, the largest committees", """
SELECT rd.committee_id, any_value(o.name) AS name, any_value(cand.name) AS candidate, string_agg(DISTINCT rd.name, '; ') AS givers,
    count(*) AS rows, sum(rd.amount) AS dollars
FROM rd JOIN ol AS o USING (committee_id) LEFT JOIN silver.candidate AS cand ON cand.candidate_id = rd.candidate_id
WHERE rd.diag LIKE 'D7%' GROUP BY ALL ORDER BY dollars DESC LIMIT 10
""")
show("Q6c5: D4, the largest givers", """
SELECT rd.name, n.committee_id AS names_committee, c.CMTE_TP, rd.src, count(*) AS rows, sum(rd.amount) AS dollars, count(DISTINCT rd.committee_id) AS recipients
FROM rd JOIN cm_named AS n ON n.name_key = name_key(rd.name) JOIN cm AS c ON c.CMTE_ID = n.committee_id
WHERE rd.diag LIKE 'D4%' GROUP BY ALL ORDER BY dollars DESC LIMIT 15
""")
show("Q6d: verdicts and primary causes", """
SELECT primary_cause, verdict, count(*) AS committees, sum(excess) AS excess, sum(unexplained_dollars) AS unexplained_dollars
FROM verdict GROUP BY ALL ORDER BY 1, 2
""")
show("Q6d2: dollars per diagnostic over every over-1% committee", """
SELECT sum(excess) AS total_excess, sum(d1_refunds) AS d1, sum(d2_duplicates) AS d2, sum(d3_other_line) AS d3, sum(d4_names_committee) AS d4,
    sum(d5_memo) AS d5, sum(d6_after_cvg_end) AS d6, sum(d7_own_money) AS d7, sum(d8_orgs_on_line_15) AS d8,
    sum(greatest(unexplained_dollars, 0)) FILTER (WHERE verdict = 'unexplained') AS unexplained,
    count(*) FILTER (WHERE d2_duplicates > 0) AS c2, count(*) FILTER (WHERE d3_other_line > 0) AS c3, count(*) FILTER (WHERE d4_names_committee > 0) AS c4,
    count(*) FILTER (WHERE d6_after_cvg_end > 0) AS c6, count(*) FILTER (WHERE d7_own_money > 0) AS c7, count(*) FILTER (WHERE d8_orgs_on_line_15 > 0) AS c8
FROM verdict
""")
show("Q6d3: D6 by whether the summary row's coverage ends before 2024-12-31; and the no-FEC-figure committees by type", """
SELECT 'coverage ends before 2024-12-31' AS what, count(*) AS committees, sum(excess) AS excess, sum(d6_after_cvg_end) AS d6
FROM verdict WHERE cvg_end < DATE '2024-12-31'
UNION ALL
SELECT 'coverage ends 2024-12-31 or later', count(*), sum(excess), sum(d6_after_cvg_end) FROM verdict WHERE cvg_end >= DATE '2024-12-31'
UNION ALL
SELECT 'no FEC figure, type ' || coalesce(type, '(blank)'), count(*), sum(excess), sum(d6_after_cvg_end)
FROM verdict WHERE verdict = 'no FEC figure' GROUP BY type
""")
show("Q6e: every over-1% committee, by excess", """
SELECT committee_id, name, type, item AS fec_itemized, a, b, CASE WHEN on_b THEN 'B' ELSE 'A' END AS measure, excess, excess_pct,
    d1_refunds, d2_duplicates, d3_other_line, d4_names_committee, d5_memo, d6_after_cvg_end, d7_own_money, d8_orgs_on_line_15, unexplained_dollars,
    primary_cause, verdict
FROM verdict ORDER BY excess DESC
""")
```

**Q6a: diagnostics over every over-1% committee, dollars by diagnostic and line  (0 s)**

| diagnostic | rows | dollars | committees |
|---|---|---|---|
| D3 non-contribution account | 653,370 | 1,696,885,797 | 344 |
| (none: an 11(a)(i) row) | 6,782,283 | 1,588,309,394 | 574 |
| D3 party account 32 | 3,215 | 40,737,660 | 6 |
| D3 party account 31 | 7,051 | 38,628,860 | 6 |
| D7 own money | 742 | 32,740,218 | 94 |
| D4 names a committee | 73 | 27,639,632 | 28 |
| D3 11(c) unregistered committee | 84 | 22,224,103 | 1 |
| D1 refund | 62,617 | -20,129,599 | 199 |
| D2 duplicate, same file | 805,063 | 14,998,710 | 216 |
| D3 party account 30 | 314 | 4,797,308 | 2 |
| D2 duplicate, files differ | 45,282 | 4,137,018 | 24 |
| D3 12 transfers | 2 | 500,000 | 1 |
| D3 11(d) candidate | 7 | 50,877 | 4 |
| D3 earmark, conduit side (24I) | 40 | 17,936 | 2 |
| D6 after coverage end | 2 | 3,000 | 1 |

**Q6b: D1 refunds: rows filed positive that silver made negative  (0 s)**

| filed_positive | filed_positive_dollars | filed_negative | silver_dollars |
|---|---|---|---|
| 133,160 | 23,098,662 | 317 | -22,865,330 |

**Q6c: D2 duplicates by whether file numbers differ  (0 s)**

| diag | cmte_type | rows | dollars | committees |
|---|---|---|---|---|
| D2 duplicate, files differ | V | 44,843 | 4,046,797 | 4 |
| D2 duplicate, files differ | Q | 254 | 35,017 | 7 |
| D2 duplicate, files differ | H | 22 | 28,700 | 3 |
| D2 duplicate, files differ | N | 71 | 21,842 | 7 |
| D2 duplicate, files differ | O | 5 | 2,236 | 1 |
| D2 duplicate, files differ | I | 54 | 2,205 | 1 |
| D2 duplicate, files differ | S | 33 | 221 | 1 |
| D2 duplicate, same file | Y | 610,679 | 6,922,934 | 17 |
| D2 duplicate, same file | W | 84,473 | 2,102,918 | 49 |
| D2 duplicate, same file | O | 1,870 | 1,557,261 | 21 |
| D2 duplicate, same file | H | 6,190 | 1,276,013 | 26 |
| D2 duplicate, same file | N | 45,424 | 897,132 | 14 |
| D2 duplicate, same file | P | 14,432 | 848,887 | 3 |
| D2 duplicate, same file | V | 33,896 | 727,150 | 60 |
| D2 duplicate, same file | Q | 4,028 | 313,046 | 19 |
| D2 duplicate, same file | S | 3,941 | 307,776 | 5 |
| D2 duplicate, same file | X | 5 | 32,600 | 1 |
| D2 duplicate, same file | I | 125 | 12,993 | 1 |

**Q6c2: D3 by line and committee  (0 s)**

| diag | committee_id | name | type | rows | dollars |
|---|---|---|---|---|---|
| D3 11(c) unregistered committee | C00834978 | 170 FREEDOM MILWAUKEE 2024 HOST COMMITTEE INC | X | 84 | 22,224,103 |
| D3 11(d) candidate | C00852699 | RIC HOLDEN FOR MONTANA | H | 2 | 27,069 |
| D3 11(d) candidate | C00868521 | SCHAEFER FOR US SENATE NV2024 | S | 1 | 15,128 |
| D3 11(d) candidate | C00847319 | CLATTERBUCK FOR CONGRESS | H | 2 | 8,600 |
| D3 11(d) candidate | C00875492 | SHAUN GREENE FOR CONGRESS | H | 2 | 80 |
| D3 12 transfers | C00580068 | PROGRESSIVE TURNOUT PROJECT | W | 2 | 500,000 |
| D3 earmark, conduit side (24I) | C00842104 | FIGHT LIKE HELL PAC | W | 39 | 16,936 |
| D3 earmark, conduit side (24I) | C00859066 | THE SCHOOL BOARD PROJECT | V | 1 | 1,000 |
| D3 party account 30 | C00003418 | REPUBLICAN NATIONAL COMMITTEE | Y | 306 | 4,399,708 |
| D3 party account 30 | C00010603 | DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE | Y | 8 | 397,600 |
| D3 party account 31 | C00000935 | DCCC | Y | 2,703 | 13,592,490 |
| D3 party account 31 | C00003418 | REPUBLICAN NATIONAL COMMITTEE | Y | 1,131 | 11,650,680 |
| D3 party account 31 | C00042366 | DSCC | Y | 77 | 6,138,550 |
| D3 party account 31 | C00027466 | NRSC | Y | 53 | 3,280,479 |
| D3 party account 31 | C00075820 | NRCC | Y | 3,027 | 2,579,876 |
| D3 party account 31 | C00010603 | DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE | Y | 60 | 1,386,785 |
| D3 party account 32 | C00042366 | DSCC | Y | 698 | 15,072,241 |
| D3 party account 32 | C00027466 | NRSC | Y | 1,789 | 8,770,869 |
| D3 party account 32 | C00003418 | REPUBLICAN NATIONAL COMMITTEE | Y | 174 | 7,196,965 |
| D3 party account 32 | C00000935 | DCCC | Y | 132 | 6,310,938 |
| D3 party account 32 | C00010603 | DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE | Y | 149 | 2,091,028 |
| D3 party account 32 | C00075820 | NRCC | Y | 273 | 1,295,619 |

**Q6c3: D7 by transaction type, entity type, and whether the name matches the candidate's  (2 s)**

| tt | entity_type | name_matches | rows | dollars | committees |
|---|---|---|---|---|---|
| 15C | IND | True | 286 | 26,853,597 | 23 |
| 15C | CAN | False | 300 | 4,640,442 | 50 |
| 15C | CAN |  | 93 | 1,164,319 | 8 |
| 15 | IND | True | 39 | 42,102 | 11 |
| 15C | IND | False | 14 | 27,123 | 6 |
| 15E | CAN | True | 2 | 5,500 | 2 |
| 15C |  |  | 4 | 3,621 | 1 |
| 10 | IND | True | 1 | 2,012 | 1 |
| 15C | CAN | True | 3 | 1,502 | 3 |

**Q6c4: D7, the largest committees  (0 s)**

| committee_id | name | candidate | givers | rows | dollars |
|---|---|---|---|---|---|
| C00833913 | VIVEK 2024 | RAMASWAMY, VIVEK | RAMASWAMY, VIVEK | 43 | 25,875,255 |
| C00666859 | MARYOTT FOR CONGRESS | MARYOTT, BRIAN L MR | MARYOTT - PERSONAL FUNDS, BRIAN | 16 | 1,425,296 |
| C00875740 | JERRY TORRES FOR CONGRESS | TORRES, JERRY | TORRESS, JERRY | 5 | 1,114,222 |
| C00676965 | RICK SCOTT FOR FLORIDA | SCOTT, RICK SEN | SCOTT, RICK SEN; SCOTT, RICK; SCOTT, RICK SENATOR | 26 | 640,527 |
| C00843029 | COURAGEOUS LEADERS |  | REESE, LEXI | 7 | 534,215 |
| C00850420 | CISNEROS FOR CONGRESS |  | CISNEROS, GIL | 2 | 506,600 |
| C00840108 | GUNDERSON FOR CONGRESS | GUNDERSON, MATT | GUNDERSON - PERSONAL FUNDS, MATTHEW | 1 | 500,000 |
| C00539890 | FEINSTEIN FOR SENATE 2024 | FEINSTEIN, DIANNE | FEINSTEIN, SENATOR DIANNE | 2 | 500,000 |
| C00704981 | MICHELLE STEEL FOR CONGRESS | STEEL, MICHELLE | STEEL - PERSONAL FUNDS, MICHELLE | 1 | 260,000 |
| C00868596 | WEST VIRGINIANS TO ELECT DON | BLANKENSHIP, DON | BLANKENSHIP, DON | 27 | 175,299 |

**Q6c5: D4, the largest givers  (0 s)**

| name | names_committee | CMTE_TP | src | rows | dollars | recipients |
|---|---|---|---|---|---|---|
| BRIGHT FUTURE FUND | C00816629 | O | organization | 8 | 12,270,000 | 3 |
| RESTORATION PAC | C00571588 | O | organization | 6 | 9,000,000 | 1 |
| STRATEGIC VICTORY FUND IE PAC | C00741769 | O | organization | 1 | 2,462,000 | 1 |
| AMERICA VOTES ACTION FUND | C00492520 | O | organization | 1 | 2,000,000 | 1 |
| PEOPLE POWER PENNSYLVANIA | C00882381 | O | organization | 1 | 800,000 | 1 |
| BATTLEGROUND CALIFORNIA | C00872549 | O | organization | 4 | 275,000 | 1 |
| BATTLEGROUND NEW YORK | C00859355 | O | organization | 2 | 135,135 | 1 |
| WINRED | C00694323 | V | organization | 16 | 118,888 | 1 |
| VIRGINIA PLUS PAC | C00697755 | O | organization | 3 | 100,000 | 1 |
| MOVEMENT VOTER PAC | C00728360 | V | organization | 2 | 100,000 | 2 |
| PEOPLE'S ACTION POWER | C00738237 | V | organization | 1 | 90,000 | 1 |
| EDF ACTION VOTES | C00707844 | O | organization | 1 | 75,000 | 1 |
| BATTLEGROUNDCALIFORNIA | C00872549 | O | organization | 1 | 58,920 | 1 |
| COMMUNICATIONS WORKERS OF AMERICA WORKING VOICES | C00488486 | O | organization | 1 | 50,000 | 1 |
| THE SENTINEL ACTION FUND | C00811166 | O | organization | 1 | 35,000 | 1 |

**Q6d: verdicts and primary causes  (0 s)**

| primary_cause | verdict | committees | excess | unexplained_dollars |
|---|---|---|---|---|
| D2 duplicates | explained | 40 | 2,111,929 | -2,353,135 |
| D2 duplicates | no FEC figure | 2 | 2,922,774 | 2,907,576 |
| D2 duplicates | unexplained | 28 | 20,360,602 | 20,022,037 |
| D3 other line | explained | 351 | 1,743,152,278 | -51,874,388 |
| D3 other line | no FEC figure | 2 | 27,608,231 | 3,310,806 |
| D3 other line | unexplained | 1 | 34,450 | 13,750 |
| D4 names a committee | explained | 10 | 18,651,494 | -7,092,947 |
| D4 names a committee | no FEC figure | 7 | 2,653,055 | 249,000 |
| D7 own money | explained | 86 | 32,134,285 | -1,315,890 |
| D7 own money | no FEC figure | 3 | 1,768 | 0 |
| D7 own money | unexplained | 2 | 34,652 | 21,185 |
| D8 organizations on line 15 | explained | 61 | 68,378,344 | 28,120 |
| D8 organizations on line 15 | unexplained | 21 | 14,032,301 | 9,729,011 |
| none | no FEC figure | 44 | 6,472,625 | 6,472,625 |
| none | unexplained | 67 | 4,651,852 | 4,663,599 |

**Q6d2: dollars per diagnostic over every over-1% committee  (0 s)**

| total_excess | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | unexplained | c2 | c3 | c4 | c6 | c7 | c8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1,943,200,639 | -20,129,599 | 19,135,728 | 1,803,842,541 | 27,639,632 | 0 | 3,000 | 32,740,218 | 75,058,172 | 34,449,581 | 211 | 355 | 26 | 1 | 94 | 90 |

**Q6d3: D6 by whether the summary row's coverage ends before 2024-12-31; and the no-FEC-figure committees by type  (0 s)**

| what | committees | excess | d6 |
|---|---|---|---|
| coverage ends before 2024-12-31 | 128 | 52,101,346 | 0 |
| coverage ends 2024-12-31 or later | 597 | 1,891,099,293 | 3,000 |
| no FEC figure, type H | 2 | 1,578 | 0 |
| no FEC figure, type I | 52 | 11,929,454 | 0 |
| no FEC figure, type S | 2 | 15,318 | 0 |
| no FEC figure, type X | 2 | 27,712,103 | 0 |

**Q6e: every over-1% committee, by excess  (0 s)**

| committee_id | name | type | fec_itemized | a | b | measure | excess | excess_pct | d1_refunds | d2_duplicates | d3_other_line | d4_names_committee | d5_memo | d6_after_cvg_end | d7_own_money | d8_orgs_on_line_15 | unexplained_dollars | primary_cause | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C00669259 | FF PAC | V | 6,250 | 178,269,529 | 481,464,962 | B | 481,458,712 | 7703339.39% | -135,041 | 0 | 481,593,753 | 0 | 0 | 0 | 0 | 0 | -135,041 | D3 other line | explained |
| C00504530 | CONGRESSIONAL LEADERSHIP FUND | W | 10,100 | 140,949,685 | 237,249,777 | B | 237,239,677 | 2348907.69% | -5,000 | 0 | 237,244,677 | 0 | 0 | 0 | 0 | 0 | -5,000 | D3 other line | explained |
| C00687103 | AMERICANS FOR PROSPERITY ACTION, INC. (AFP ACTION) DBA CVA ACTION AND DBA LIBRE ACTION | V | 0 | 73,419,037 | 176,034,463 | B | 176,034,463 |  | -65,300 | 0 | 176,099,763 | 0 | 0 | 0 | 0 | 0 | -65,300 | D3 other line | explained |
| C00495028 | HMP | W | 7,720,883 | 106,417,533 | 180,062,872 | B | 172,341,989 | 2232.15% | -992,147 | 309,633 | 173,304,812 | 0 | 0 | 0 | 0 | 0 | -1,272,456 | D3 other line | explained |
| C00492140 | AB PAC | V | 76,458 | 39,564,465 | 82,996,131 | B | 82,919,673 | 108451.27% | -41,321 | 5,782 | 82,963,667 | 0 | 0 | 0 | 0 | 0 | -49,776 | D3 other line | explained |
| C00828061 | SFA FUND, INC | V | 0 | 72,877,800 | 79,188,800 | B | 79,188,800 |  | -560,000 | 0 | 79,748,800 | 0 | 0 | 0 | 0 | 0 | -560,000 | D3 other line | explained |
| C00821439 | AMERICAN VALUES 2024 | V | 66,550 | 45,421,269 | 51,049,776 | B | 50,983,226 | 76608.90% | -10,010 | 0 | 51,028,236 | 0 | 0 | 0 | 0 | 0 | -45,010 | D3 other line | explained |
| C00728360 | MOVEMENT VOTER PAC | V | 4,094,186 | 49,921,268 | 50,532,331 | B | 46,438,145 | 1134.25% | -48,945 | -1,450 | 46,492,741 | 0 | 0 | 0 | 0 | 0 | -53,146 | D3 other line | explained |
| C00571703 | SENATE LEADERSHIP FUND | O | 220,730,171 | 176,050,171 | 255,310,171 | B | 34,580,000 | 15.67% | 0 | 500 | 0 | 0 | 0 | 0 | 0 | 34,579,500 | 0 | D8 organizations on line 15 | explained |
| C00834978 | 170 FREEDOM MILWAUKEE 2024 HOST COMMITTEE INC | X |  | 4,140,000 | 27,593,103 | B | 27,593,103 |  | 0 | 0 | 22,224,103 | 0 | 0 | 0 | 0 | 2,058,194 | 3,310,806 | D3 other line | no FEC figure |
| C00833913 | VIVEK 2024 | P | 5,889,065 | 31,642,731 | 31,642,731 | B | 25,753,666 | 437.31% | -111,856 | 46,510 | 0 | 0 | 0 | 0 | 25,875,255 | 0 | -168,099 | D7 own money | explained |
| C00892471 | MAGA INC. | V | 0 | 21,850,000 | 22,850,000 | B | 22,850,000 |  | 0 | 0 | 22,850,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00003418 | REPUBLICAN NATIONAL COMMITTEE | Y | 87,269,680 | 108,104,023 | 108,235,795 | B | 20,966,115 | 24.02% | -364,424 | 1,560,033 | 23,247,353 | 0 | 0 | 0 | 0 | 0 | -3,841,271 | D3 other line | explained |
| C00779595 | RSLC PAC | O | 0 | 0 | 19,293,000 | B | 19,293,000 |  | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | 19,143,000 | D2 duplicates | unexplained |
| C00000935 | DCCC | Y | 105,517,956 | 120,618,725 | 124,444,150 | B | 18,926,194 | 17.94% | -534,553 | 915,683 | 19,903,428 | 0 | 0 | 0 | 0 | 0 | -1,892,917 | D3 other line | explained |
| C00677773 | UNITE AMERICA PAC INC. | W | 250,698 | 21,465,176 | 17,429,445 | B | 17,178,747 | 6852.37% | -4,136,731 | 0 | 21,315,500 | 0 | 0 | 0 | 0 | 0 | -4,136,753 | D3 other line | explained |
| C00559740 | GOPAC ELECTION FUND | W | 68,000 | 150,500 | 16,656,170 | B | 16,588,170 | 24394.37% | 0 | 0 | 16,588,170 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00725820 | THE LINCOLN PROJECT | V | 0 | 15,244,981 | 15,659,095 | B | 15,659,095 |  | -467,436 | -3,213 | 16,129,744 | 0 | 0 | 0 | 0 | 0 | -467,436 | D3 other line | explained |
| C00042366 | DSCC | Y | 110,889,568 | 120,669,687 | 123,223,402 | B | 12,333,834 | 11.12% | -2,241,135 | 1,219,768 | 21,210,791 | 0 | 0 | 0 | 0 | 0 | -10,096,725 | D3 other line | explained |
| C00418897 | VOTEVETS | W | 3,562,224 | 14,064,952 | 15,867,764 | B | 12,305,540 | 345.45% | -108,029 | 55,153 | 12,421,161 | 0 | 0 | 0 | 0 | 0 | -170,774 | D3 other line | explained |
| C00636027 | TECH FOR CAMPAIGNS | V | 1,000 | 9,740,522 | 11,748,052 | B | 11,747,052 | 1174705.20% | -5,076 | 0 | 11,752,128 | 0 | 0 | 0 | 0 | 0 | -5,076 | D3 other line | explained |
| C00744920 | CFFE PAC | W | 85,750 | 220,223 | 11,676,107 | B | 11,590,357 | 13516.45% | -1,509 | 0 | 11,591,884 | 0 | 0 | 0 | 0 | 0 | -1,527 | D3 other line | explained |
| C00606962 | WORKING FAMILIES PARTY PAC | W | 578,699 | 7,849,850 | 11,631,415 | B | 11,052,716 | 1909.92% | 0 | 12,770 | 11,053,251 | 0 | 0 | 0 | 0 | 0 | -13,305 | D3 other line | explained |
| C00840546 | TRUST IN THE MISSION PAC | V | 0 | 9,432,899 | 10,562,899 | B | 10,562,899 |  | -25,000 | 0 | 10,587,899 | 0 | 0 | 0 | 0 | 0 | -25,000 | D3 other line | explained |
| C00731133 | MAKE LIBERTY WIN | V | 16,850 | 1,347,131 | 9,510,143 | B | 9,493,293 | 56340.02% | 0 | 0 | 9,493,293 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00530766 | WOMEN SPEAK OUT PAC | O | 338,960 | 338,959 | 9,353,874 | B | 9,014,914 | 2659.58% | 0 | 0 | 0 | 9,000,000 | 0 | 0 | 0 | 14,914 | 0 | D4 names a committee | explained |
| C00786830 | WELCOMEPAC | W | 389,795 | 7,199,166 | 9,061,803 | B | 8,672,008 | 2224.76% | -5,990 | 157,200 | 8,712,237 | 0 | 0 | 0 | 0 | 0 | -197,429 | D3 other line | explained |
| C00027466 | NRSC | Y | 101,098,477 | 107,395,776 | 108,634,576 | B | 7,536,099 | 7.45% | -2,297,297 | 1,196,507 | 12,051,348 | 12,500 | 0 | 0 | 0 | 0 | -5,724,256 | D3 other line | explained |
| C00547349 | NEXTGEN CLIMATE ACTION COMMITTEE | V | 310,050 | 1,315,830 | 7,211,778 | B | 6,901,728 | 2226.00% | 0 | 0 | 7,206,778 | 0 | 0 | 0 | 0 | 0 | -305,050 | D3 other line | explained |
| C00836353 | NEWSOM FOR CALIFORNIA GOVERNOR 2022 | V | 6,878,564 | 10,076,516 | 13,486,516 | B | 6,607,952 | 96.07% | 0 | 3,990,437 | 6,608,928 | 0 | 0 | 0 | 0 | 0 | -3,991,413 | D3 other line | explained |
| C00678839 | INDIVISIBLE ACTION | W | 61,230 | 3,239,168 | 6,284,403 | B | 6,223,173 | 10163.65% | -13,378 | 340 | 6,236,993 | 0 | 0 | 0 | 0 | 0 | -14,160 | D3 other line | explained |
| C00710848 | DMFI PAC | W | 410,698 | 5,120,197 | 6,415,814 | B | 6,005,116 | 1462.17% | -1,000 | 550 | 6,006,117 | 0 | 0 | 0 | 0 | 0 | -1,551 | D3 other line | explained |
| C00540443 | GIFFORDS PAC | W | 992,970 | 3,695,856 | 6,929,928 | B | 5,936,958 | 597.90% | -28,368 | -415 | 5,967,323 | 0 | 0 | 0 | 0 | 0 | -29,950 | D3 other line | explained |
| C00580068 | PROGRESSIVE TURNOUT PROJECT | W | 14,064,034 | 14,693,787 | 19,618,676 | B | 5,554,642 | 39.50% | -475,578 | 737,758 | 6,387,540 | 0 | 0 | 0 | 0 | 0 | -1,570,656 | D3 other line | explained |
| C00825851 | MAKE AMERICA GREAT AGAIN INC. | O | 383,797,150 | 305,954,164 | 388,899,300 | B | 5,102,150 | 1.33% | -300,000 | 108,400 | 0 | 0 | 0 | 0 | 0 | 4,993,750 | 0 | D8 organizations on line 15 | explained |
| C00627372 | UNITE HERE PAC | O | 0 | 0 | 5,000,000 | B | 5,000,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,782,500 | 3,217,500 | D8 organizations on line 15 | unexplained |
| C00698936 | WFW ACTION FUND, INC. | V | 18,750 | 3,606,750 | 5,006,750 | B | 4,988,000 | 26602.67% | 0 | 0 | 4,988,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00754051 | WORKERS VOTE | O | 1,754,906 | 1,754,905 | 6,545,484 | B | 4,790,578 | 272.98% | 0 | 6,000 | 0 | 0 | 0 | 0 | 0 | 4,784,578 | 0 | D8 organizations on line 15 | explained |
| C00685719 | DLGA PAC | V | 169,646 | 405,918 | 4,948,918 | B | 4,779,272 | 2817.21% | -5,560 | 100 | 4,883,821 | 0 | 0 | 0 | 0 | 0 | -104,648 | D3 other line | explained |
| C00873513 | THE JUSTICE PROJECT | V | 30,325 | 30,250 | 4,617,770 | B | 4,587,445 | 15127.60% | 0 | 0 | 4,587,520 | 0 | 0 | 0 | 0 | 0 | -75 | D3 other line | explained |
| C00633248 | 314 ACTION FUND | W | 2,637,463 | 5,560,278 | 7,185,372 | B | 4,547,909 | 172.44% | -135,304 | 25,925 | 4,688,221 | 0 | 0 | 0 | 0 | 0 | -166,237 | D3 other line | explained |
| C00844282 | PIVOTPAC | O | 455,060 | 96,234 | 4,949,734 | B | 4,494,674 | 987.71% | 0 | 35,000 | 0 | 4,330,000 | 0 | 0 | 0 | 129,674 | 0 | D4 names a committee | explained |
| C00789966 | FORWARD PARTY | W | 374,762 | 4,439,350 | 4,527,183 | B | 4,152,421 | 1108.02% | -878 | 733 | 4,172,887 | 0 | 0 | 0 | 0 | 0 | -21,199 | D3 other line | explained |
| C00686832 | WAY TO LEAD PAC | W | 192,512 | 2,677,111 | 4,152,111 | B | 3,959,599 | 2056.81% | 0 | 5,000 | 3,957,250 | 0 | 0 | 0 | 0 | 0 | -2,651 | D3 other line | explained |
| C00890053 | FUTURE PENNSYLVANIA PAC | O | 0 | 0 | 3,731,486 | B | 3,731,486 |  | 0 | 0 | 0 | 3,262,000 | 0 | 0 | 0 | 469,486 | 0 | D4 names a committee | explained |
| C00887182 | PLANNED PARENTHOOD VOTES NORTH CAROLINA | O | 0 | 0 | 3,678,228 | B | 3,678,228 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3,678,228 | 0 | D8 organizations on line 15 | explained |
| C00632133 | SWING LEFT | W | 4,331,100 | 7,914,385 | 7,983,243 | B | 3,652,143 | 84.32% | -9,573 | 624,608 | 5,055,065 | 0 | 0 | 0 | 0 | 0 | -2,027,530 | D3 other line | explained |
| C00764209 | LEADERSHIP IN ACTION | V | 71,711 | 327,261 | 3,678,011 | B | 3,606,300 | 5028.92% | -100,750 | 200 | 3,707,550 | 0 | 0 | 0 | 0 | 0 | -101,450 | D3 other line | explained |
| C00756940 | TEXAS ORGANIZING PROJECT POLITICAL ACTION COMMITTEE | V | 0 | 2,037,254 | 3,602,293 | B | 3,602,293 |  | 0 | 0 | 3,602,293 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00654053 | THE PAC FOR AMERICA'S FUTURE | V | 7,506,405 | 7,549,624 | 11,054,513 | B | 3,548,108 | 47.27% | -30,800 | 56,291 | 3,580,389 | 0 | 0 | 0 | 0 | 0 | -88,572 | D3 other line | explained |
| C00806893 | JANE FONDA CLIMATE PAC | W | 1,046,566 | 3,931,257 | 4,584,136 | B | 3,537,570 | 338.02% | -35,165 | 5,227 | 3,587,116 | 0 | 0 | 0 | 0 | 0 | -54,773 | D3 other line | explained |
| C00495861 | PRIORITIES USA ACTION | V | 57,150 | 1,258,490 | 3,586,974 | B | 3,529,824 | 6176.42% | 0 | 0 | 3,529,824 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00785790 | PROTECTING AMERICANS PROJECT ACTION FUND | V | 49,570 | 2,657,570 | 3,238,570 | B | 3,189,000 | 6433.33% | 0 | 0 | 3,189,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00808311 | RSLC VICTORY FUND | V | 0 | 3,134,587 | 3,135,587 | B | 3,135,587 |  | 0 | 0 | 3,135,587 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00764860 | THE 1776 PROJECT PAC | V | 76,708 | 2,872,691 | 3,121,451 | B | 3,044,743 | 3969.28% | -87,064 | -9,168 | 3,141,035 | 0 | 0 | 0 | 0 | 0 | -87,124 | D3 other line | explained |
| C00876391 | THE IMPACT FUND | V | 71,670 | 2,585,285 | 3,094,602 | B | 3,022,932 | 4217.85% | 0 | 0 | 3,022,932 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90018904 | THE CONSERVATIVE CAUCUS DBA AMERICANS FOR CONSTITUTIONAL LIBERTY | I |  | 2,908,450 | 2,919,950 | B | 2,919,950 |  | 0 | 12,993 | 0 | 0 | 0 | 0 | 0 | 0 | 2,906,957 | D2 duplicates | no FEC figure |
| C00812495 | STATE DEMOCRACY DEFENDERS PAC | V | 56,850 | 2,773,150 | 2,789,859 | B | 2,733,009 | 4807.40% | -25,000 | 0 | 2,758,009 | 0 | 0 | 0 | 0 | 0 | -25,000 | D3 other line | explained |
| C00731042 | POWERED BY PEOPLE | V | 1,641,745 | 1,785,194 | 4,330,848 | B | 2,689,103 | 163.80% | -19,805 | 12,901 | 2,713,634 | 0 | 0 | 0 | 0 | 0 | -37,432 | D3 other line | explained |
| C00822932 | PROGRESSIVE ERA PAC | O | 0 | 2,678,800 | 2,678,800 | B | 2,678,800 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,678,800 | none | unexplained |
| C00542431 | JOHN BOLTON PAC | W | 672,567 | 3,342,755 | 3,342,755 | B | 2,670,188 | 397.01% | 0 | 96 | 2,670,200 | 0 | 0 | 0 | 0 | 0 | -108 | D3 other line | explained |
| C00814152 | TURNING POINT PAC INC. | W | 730,107 | 2,163,155 | 3,398,155 | B | 2,668,048 | 365.43% | 0 | 4,558 | 2,673,100 | 0 | 0 | 0 | 0 | 0 | -9,610 | D3 other line | explained |
| C00542217 | TEXANS FOR A CONSERVATIVE MAJORITY | V | 0 | 1,060,000 | 2,585,000 | B | 2,585,000 |  | 0 | 0 | 2,585,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00741355 | MAJORITY PAC | W | 17,000 | 2,580,127 | 2,580,127 | B | 2,563,127 | 15077.22% | 0 | 0 | 2,563,127 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00760124 | NATIONAL VICTORY ACTION FUND | W | 270,777 | 270,779 | 2,664,542 | B | 2,393,765 | 884.04% | 0 | 15,196 | 2,394,798 | 0 | 0 | 0 | 0 | 0 | -16,229 | D3 other line | explained |
| C00842104 | FIGHT LIKE HELL PAC | W | 3,467,617 | 5,656,496 | 5,790,988 | B | 2,323,371 | 67.00% | -11,562 | 15,230 | 2,438,759 | 0 | 0 | 0 | 0 | 0 | -130,618 | D3 other line | explained |
| C00754069 | PAF | V | 1,997,738 | 4,239,262 | 4,239,262 | B | 2,241,524 | 112.20% | -14,409 | 67,810 | 2,261,649 | 0 | 0 | 0 | 0 | 0 | -87,935 | D3 other line | explained |
| C00748228 | MARCH ON PAC | W | 48,341 | 2,170,545 | 2,215,457 | B | 2,167,116 | 4483.01% | -22,605 | -1,273 | 2,193,059 | 0 | 0 | 0 | 0 | 0 | -24,670 | D3 other line | explained |
| C00450098 | WOMENCOUNT PAC | V | 145,816 | 565,265 | 2,297,765 | B | 2,151,949 | 1475.80% | -2,500 | 1,245 | 2,189,850 | -35,000 | 0 | 0 | 0 | 0 | -4,146 | D3 other line | explained |
| C00808998 | DEMOCRACYFIRST PAC | Q | 25,295 | 1,927,884 | 2,135,380 | B | 2,110,085 | 8341.91% | -2,105 | -75 | 0 | 0 | 0 | 0 | 0 | 207,496 | 1,902,664 | D8 organizations on line 15 | unexplained |
| C00887968 | EVANGELICALS FOR AMERICA PAC | V | 34,128 | 180,128 | 2,140,128 | B | 2,106,000 | 6170.89% | 0 | 0 | 2,106,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00824342 | WAY BACK PAC | V | 46,250 | 758,950 | 2,144,200 | B | 2,097,950 | 4536.11% | 0 | 0 | 2,097,950 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00872879 | STAND UP PAC | V | 37,858 | 1,947,142 | 2,127,142 | B | 2,089,284 | 5518.74% | -2,005 | 262 | 2,091,300 | 0 | 0 | 0 | 0 | 0 | -2,278 | D3 other line | explained |
| C00620971 | FOR OUR FUTURE | O | 2,147,548 | 0 | 4,228,896 | B | 2,081,348 | 96.92% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 38,791 | 2,042,557 | D8 organizations on line 15 | unexplained |
| C90016627 | WORKER POWER | I |  | 0 | 2,000,000 | B | 2,000,000 |  | 0 | 0 | 0 | 2,000,000 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | no FEC figure |
| C00890715 | DID THEY VOTE | O | 0 | 0 | 2,000,000 | B | 2,000,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,000,000 | 0 | D8 organizations on line 15 | explained |
| C00843110 | LEADERS WE DESERVE | V | 2,773,201 | 4,495,551 | 4,705,024 | B | 1,931,823 | 69.66% | -66,105 | 22,131 | 2,138,028 | 0 | 0 | 0 | 0 | 0 | -228,336 | D3 other line | explained |
| C00809483 | EIGHTEEN FIFTY-FOUR FUND | O | 650,000 | 500,000 | 2,550,000 | B | 1,900,000 | 292.31% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,900,000 | 0 | D8 organizations on line 15 | explained |
| C00889931 | BADGER VALUES | O | 0 | 0 | 1,850,000 | B | 1,850,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,850,000 | 0 | D8 organizations on line 15 | explained |
| C00773846 | OPEN DEMOCRACY PAC | V | 111,050 | 692,150 | 1,928,027 | B | 1,816,977 | 1636.18% | 0 | 0 | 1,817,127 | 0 | 0 | 0 | 0 | 0 | -150 | D3 other line | explained |
| C00693515 | FAIR FIGHT | V | 1,186,967 | 4,371,091 | 2,959,058 | B | 1,772,091 | 149.30% | -2,280,735 | -1,456 | 4,057,519 | 0 | 0 | 0 | 0 | 0 | -2,283,972 | D3 other line | explained |
| C00589507 | AAPI VICTORY FUND, INC. | W | 53,242 | 1,217,346 | 1,770,676 | B | 1,717,434 | 3225.73% | -1,000 | 0 | 1,718,435 | 0 | 0 | 0 | 0 | 0 | -1,001 | D3 other line | explained |
| C00838805 | COMMON SENSE | V | 60,520 | 728,453 | 1,769,063 | B | 1,708,543 | 2823.12% | -45,000 | 1,921 | 1,754,667 | 0 | 0 | 0 | 0 | 0 | -48,045 | D3 other line | explained |
| C00719872 | BLACK CHURCH PAC | V | 29,382 | 674,140 | 1,724,140 | B | 1,694,758 | 5768.01% | -10,242 | 25 | 1,705,000 | 0 | 0 | 0 | 0 | 0 | -10,267 | D3 other line | explained |
| C00428557 | COLOROFCHANGE PAC | V | 0 | 128,265 | 1,609,155 | B | 1,609,155 |  | -11,196 | 0 | 1,620,351 | 0 | 0 | 0 | 0 | 0 | -11,196 | D3 other line | explained |
| C00752576 | OUR VOICE OUR VOTE ARIZONA PAC | V | 492,762 | 598,778 | 2,050,278 | B | 1,557,516 | 316.08% | -77,898 | 13,792 | 1,703,750 | 0 | 0 | 0 | 0 | 0 | -160,026 | D3 other line | explained |
| C90016106 | AFL-CIO COMMITTEE ON POLITICAL EDUCATION TREASURY FUND | I |  | 0 | 1,546,157 | B | 1,546,157 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,546,157 | none | no FEC figure |
| C00651109 | STATE GOVERNMENT CITIZENS' CAMPAIGN | V | 359,624 | 1,862,321 | 1,894,399 | B | 1,534,775 | 426.77% | -2,250 | 500 | 1,537,025 | 0 | 0 | 0 | 0 | 0 | -2,750 | D3 other line | explained |
| C00010603 | DNC SERVICES CORP / DEMOCRATIC NATIONAL COMMITTEE | Y | 102,425,946 | 103,537,525 | 103,913,225 | B | 1,487,279 | 1.45% | -596,430 | 700,058 | 3,875,413 | 250 | 0 | 0 | 0 | 0 | -3,088,442 | D3 other line | explained |
| C00666859 | MARYOTT FOR CONGRESS | H | 150 | 1,425,446 | 1,425,446 | B | 1,425,296 | 950197.33% | 0 | 0 | 0 | 0 | 0 | 0 | 1,425,296 | 0 | 0 | D7 own money | explained |
| C00682211 | COMMON POWER | W | 988,607 | 2,164,938 | 2,370,945 | B | 1,382,338 | 139.83% | -8,591 | 4,200 | 1,397,941 | 0 | 0 | 0 | 0 | 0 | -19,803 | D3 other line | explained |
| C00804856 | REPUBLICAN ACCOUNTABILITY PAC | O | 39,216,320 | 33,575,341 | 40,562,085 | B | 1,345,765 | 3.43% | -1,685 | 300 | 0 | 0 | 0 | 0 | 0 | 1,345,465 | 0 | D8 organizations on line 15 | explained |
| C00630665 | JUSTICE DEMOCRATS PAC | W | 1,790,482 | 2,533,961 | 3,126,201 | B | 1,335,719 | 74.60% | -37,895 | 2,875 | 1,536,320 | 75 | 0 | 0 | 0 | 0 | -203,551 | D3 other line | explained |
| C90019472 | MONTANA RURAL VOTERS (WORC) | I |  | 28,083 | 1,319,083 | B | 1,319,083 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,319,083 | none | no FEC figure |
| C00853713 | WON'T PAC DOWN | V | 0 | 1,325,100 | 1,300,100 | B | 1,300,100 |  | -125,000 | 0 | 1,425,100 | 0 | 0 | 0 | 0 | 0 | -125,000 | D3 other line | explained |
| C00562777 | LATINO VICTORY FUND | W | 210,557 | 947,936 | 1,472,703 | B | 1,262,146 | 599.43% | -5,500 | 0 | 1,267,647 | 0 | 0 | 0 | 0 | 0 | -5,501 | D3 other line | explained |
| C00684969 | JDCA PAC | V | 637,932 | 1,891,741 | 1,891,741 | B | 1,253,809 | 196.54% | -526 | 59,150 | 1,664,525 | 0 | 0 | 0 | 0 | 0 | -469,866 | D3 other line | explained |
| C00843714 | FIGHT LIKE A FLYNN | V | 2,000 | 226,141 | 1,231,733 | B | 1,229,733 | 61486.65% | -320 | 0 | 1,230,053 | 0 | 0 | 0 | 0 | 0 | -320 | D3 other line | explained |
| C00877191 | COMMON SENSE NEW YORK | V | 49,500 | 249,800 | 1,249,800 | B | 1,200,300 | 2424.85% | 0 | 0 | 1,200,300 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00885491 | DEMOCRACY DEFENDERS PAC | V | 14,525 | 1,201,910 | 1,201,910 | B | 1,187,385 | 8174.77% | 0 | 0 | 1,187,435 | 0 | 0 | 0 | 0 | 0 | -50 | D3 other line | explained |
| C00887414 | BLACK LEADERSHIP FEDERAL PAC | O | 25,000 | 25,000 | 1,155,000 | B | 1,130,000 | 4520.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,130,000 | 0 | D8 organizations on line 15 | explained |
| C00648808 | VETERANS FOR RESPONSIBLE LEADERSHIP | V | 0 | 693,367 | 1,114,450 | B | 1,114,450 |  | 0 | 0 | 1,114,450 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00875740 | JERRY TORRES FOR CONGRESS | H | 0 | 1,114,222 | 1,114,222 | B | 1,114,222 |  | 0 | 0 | 0 | 0 | 0 | 0 | 1,114,222 | 0 | 0 | D7 own money | explained |
| C00718510 | OCCUPY DEMOCRATS ELECTION FUND | W | 223,003 | 1,329,021 | 1,329,021 | B | 1,106,018 | 495.97% | -272,941 | -528 | 1,386,679 | 0 | 0 | 0 | 0 | 0 | -280,133 | D3 other line | explained |
| C00631549 | FORWARD MAJORITY ACTION | O | 35,405,188 | 12,058,533 | 36,485,425 | B | 1,080,237 | 3.05% | -807 | 1,525 | 0 | 7,865,000 | 0 | 0 | 0 | 0 | -6,786,288 | D4 names a committee | explained |
| C00738237 | PEOPLE'S ACTION POWER | V | 30,500 | 508,735 | 1,092,305 | B | 1,061,805 | 3481.33% | 0 | 0 | 1,061,805 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00762666 | DEMOCRATIC MAJORITY ACTION (DMA PAC) | W | 239,754 | 1,290,436 | 1,290,436 | B | 1,050,682 | 438.23% | -5,578 | 1,095 | 1,056,402 | 0 | 0 | 0 | 0 | 0 | -6,815 | D3 other line | explained |
| C00742205 | SURJ PAC | W | 163,289 | 1,097,249 | 1,197,249 | B | 1,033,960 | 633.21% | 0 | 0 | 1,040,000 | 0 | 0 | 0 | 0 | 0 | -6,040 | D3 other line | explained |
| C00866780 | PA UNITED FEDERAL ACTION COMMITTEE | O | 0 | 0 | 1,023,000 | B | 1,023,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,023,000 | 0 | D8 organizations on line 15 | explained |
| C00860148 | WEST MICHIGAN FOR CHANGE | O | 0 | 0 | 1,000,000 | B | 1,000,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,000,000 | 0 | D8 organizations on line 15 | explained |
| C00868562 | AND JUSTICE FOR ALL PAC | O | 0 | 0 | 1,000,000 | B | 1,000,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,000,000 | 0 | D8 organizations on line 15 | explained |
| C00790089 | THE MODERATE PAC, INC. | V | 44,560 | 1,000,903 | 1,000,903 | B | 956,343 | 2146.19% | 0 | 0 | 956,343 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00564690 | CAPA21- FEDERAL | W | 91,358 | 1,036,981 | 1,043,981 | B | 952,623 | 1042.74% | 0 | 0 | 952,623 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00853770 | A STRONG INNOVATION ECONOMY REQUIRES STRONG IP PROTECTION | O | 0 | 0 | 950,000 | B | 950,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 950,000 | 0 | D8 organizations on line 15 | explained |
| C00041269 | GEORGIA FEDERAL ELECTIONS COMMITTEE | Y | 2,681,478 | 2,765,413 | 3,619,067 | B | 937,589 | 34.97% | -64,980 | 42,078 | 0 | 0 | 0 | 0 | 0 | 531,563 | 363,948 | D8 organizations on line 15 | unexplained |
| C00075820 | NRCC | Y | 44,264,299 | 43,225,107 | 45,191,146 | B | 926,847 | 2.09% | -606,481 | 960,453 | 3,875,495 | 0 | 0 | 0 | 0 | 0 | -3,909,101 | D3 other line | explained |
| C00829598 | COMMUNITY SOLAR ACTION FUND | V | 39,537 | 40,523 | 955,861 | B | 916,324 | 2317.63% | 0 | 0 | 916,338 | 0 | 0 | 0 | 0 | 0 | -14 | D3 other line | explained |
| C00847327 | GIULIANI DEFENSE | V | 250 | 735,999 | 859,910 | B | 859,660 | 343864.00% | 0 | 0 | 859,910 | 0 | 0 | 0 | 0 | 0 | -250 | D3 other line | explained |
| C00761072 | ONE APIA PAC | O | 0 | 0 | 850,000 | B | 850,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 850,000 | 0 | D8 organizations on line 15 | explained |
| C00514125 | THE AMERICAN FOUNDATIONS COMMITTEE | O | 1,747,500 | 2,247,500 | 2,587,500 | B | 840,000 | 48.07% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 340,000 | 500,000 | D8 organizations on line 15 | unexplained |
| C00835496 | RESOLUTE REPUBLIC | V | 0 | 0 | 833,951 | B | 833,951 |  | -19,294 | 0 | 853,245 | 0 | 0 | 0 | 0 | 0 | -19,294 | D3 other line | explained |
| C00735183 | CLIMATE CABINET PAC | V | 179,668 | 936,141 | 1,013,379 | B | 833,711 | 464.03% | -1,800 | 1,000 | 835,513 | 0 | 0 | 0 | 0 | 0 | -2,802 | D3 other line | explained |
| C00843482 | LOCAL ACCOUNTABILITY PAC | V | 100 | 10,100 | 827,176 | B | 827,076 | 827076.00% | 0 | 0 | 827,076 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00882233 | DEMOCRATIC YOUTH WAVE | V | 15,300 | 823,751 | 823,751 | B | 808,451 | 5283.99% | -45,301 | -118 | 854,870 | 0 | 0 | 0 | 0 | 0 | -46,301 | D3 other line | explained |
| C00693531 | FUTURE LEADERS FUND | V | 500 | 793,424 | 794,297 | B | 793,797 | 158759.40% | 0 | 0 | 793,797 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00608380 | DLCC PAC | V | 1,537,708 | 2,314,088 | 2,314,088 | B | 776,380 | 50.49% | -29,869 | 21,458 | 940,700 | 0 | 0 | 0 | 0 | 0 | -185,778 | D3 other line | explained |
| C00796946 | TEXANS FOR RESPONSIBLE GOVERNMENT PAC | V | 0 | 0 | 750,000 | B | 750,000 |  | 0 | 0 | 750,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00865964 | PA CONGRESSIONAL CONSERVATIVES FUND | O | 295,000 | 1,040,000 | 1,040,000 | B | 745,000 | 252.54% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 745,000 | none | unexplained |
| C00693382 | DEMOCRACY PAC | O | 70,002,500 | 2,500 | 70,740,507 | B | 738,007 | 1.05% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 738,007 | 0 | D8 organizations on line 15 | explained |
| C00568444 | CENTER FORWARD COMMITTEE | O | 250,000 | 0 | 982,000 | B | 732,000 | 292.80% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 732,000 | 0 | D8 organizations on line 15 | explained |
| C90022476 | STAND UP FOR OHIO (OHIO ORGANIZING CAMPAIGN) | I |  | 0 | 725,000 | B | 725,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 725,000 | none | no FEC figure |
| C00804633 | RIGHT ARIZONA | V | 0 | 109,583 | 714,590 | B | 714,590 |  | 0 | 0 | 714,590 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00822700 | FIGHT FOR OUR RIGHTS PAC | V | 0 | 702,250 | 702,250 | B | 702,250 |  | -2,900 | 0 | 705,150 | 0 | 0 | 0 | 0 | 0 | -2,900 | D3 other line | explained |
| C00817122 | GOA VICTORY FUND | O | 645,720 | 45,621 | 1,345,621 | B | 699,901 | 108.39% | 0 | 545 | 0 | 0 | 0 | 0 | 0 | 4,000 | 695,356 | D8 organizations on line 15 | unexplained |
| C00855379 | AMERICA'S PROMISE | O | 0 | 463,473 | 653,168 | B | 653,168 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 189,695 | 463,473 | D8 organizations on line 15 | unexplained |
| C00878025 | MOMSRISING PAC | V | 0 | 0 | 636,949 | B | 636,949 |  | 0 | 0 | 636,949 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00692137 | VOTE MAMA | W | 302,061 | 318,907 | 919,407 | B | 617,346 | 204.38% | -25 | 8,575 | 678,615 | 0 | 0 | 0 | 0 | 0 | -69,844 | D3 other line | explained |
| C00807321 | PROJECT DEMOCRACY | V | 37,517 | 255,766 | 633,966 | B | 596,449 | 1589.83% | 0 | 0 | 611,450 | 0 | 0 | 0 | 0 | 0 | -15,001 | D3 other line | explained |
| C00756056 | PROTECT THE VOTE | O | 7,682 | 599,732 | 599,732 | B | 592,050 | 7706.98% | 0 | 39,091 | 0 | 0 | 0 | 0 | 0 | 0 | 552,959 | D2 duplicates | unexplained |
| C00640664 | GREAT AMERICA COMMITTEE | W | 14,612 | 130,916 | 605,916 | B | 591,304 | 4046.70% | -1,024 | 50 | 592,328 | 0 | 0 | 0 | 0 | 0 | -1,074 | D3 other line | explained |
| C00757419 | SD PAC | W | 1,150,179 | 1,734,964 | 1,734,964 | B | 584,785 | 50.84% | -44,105 | 69,691 | 652,945 | 0 | 0 | 0 | 0 | 0 | -137,851 | D3 other line | explained |
| C00716423 | THE NEXT 50 PAC | W | 336,832 | 760,830 | 911,464 | B | 574,632 | 170.60% | 0 | 1,000 | 574,634 | 0 | 0 | 0 | 0 | 0 | -1,002 | D3 other line | explained |
| C00453704 | EMGAGE FEDERAL POLITICAL ACTION COMMITTEE | V | 13,485 | 252,420 | 570,420 | B | 556,935 | 4130.03% | 0 | 0 | 556,935 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00838177 | CE4A ACTION | V | 89,331 | 73,011 | 646,136 | B | 556,805 | 623.31% | 0 | 0 | 567,000 | 7,625 | 0 | 0 | 0 | 0 | -17,820 | D3 other line | explained |
| C00885913 | GENBLUE PAC | V | 19,775 | 476,576 | 576,576 | B | 556,801 | 2815.68% | 0 | 0 | 556,801 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00490730 | RGA RIGHT DIRECTION PAC | O | 0 | 0 | 540,372 | B | 540,372 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 540,372 | 0 | D8 organizations on line 15 | explained |
| C00834424 | MARIANNE WILLIAMSON FOR PRESIDENT | P | 2,273,142 | 2,797,460 | 2,796,710 | B | 523,568 | 23.03% | -248,092 | 797,370 | 0 | 0 | 0 | 0 | 0 | 0 | -273,802 | D2 duplicates | explained |
| C00851204 | FORWARD PARTY - RESTRICTED | V | 0 | 522,000 | 522,000 | B | 522,000 |  | 0 | 0 | 522,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90022229 | BRIGHTER FUTURE ALLIANCE | I |  | 514,090 | 514,090 | B | 514,090 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 514,090 | none | no FEC figure |
| C00676965 | RICK SCOTT FOR FLORIDA | S | 3,327,273 | 3,833,424 | 3,840,024 | B | 512,751 | 15.41% | -104,916 | 37,783 | 0 | 0 | 0 | 0 | 640,527 | 0 | -165,559 | D7 own money | explained |
| C00539890 | FEINSTEIN FOR SENATE 2024 | S | 1,095 | 501,095 | 501,095 | B | 500,000 | 45662.10% | 0 | 0 | 0 | 0 | 0 | 0 | 500,000 | 0 | 0 | D7 own money | explained |
| C00490375 | NATIONAL NURSES UNITED FOR PATIENT PROTECTION | O | 0 | 0 | 500,000 | B | 500,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 500,000 | 0 | D8 organizations on line 15 | explained |
| C00743682 | STRAIGHT TALK POLITICS PAC | V | 0 | 0 | 499,614 | B | 499,614 |  | 0 | 0 | 499,614 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00738039 | MIJENTE PAC | W | 10,698 | 271,640 | 510,013 | B | 499,315 | 4667.37% | -1,156 | 0 | 473,971 | 0 | 0 | 0 | 0 | 25,344 | 0 | D3 other line | explained |
| C00840108 | GUNDERSON FOR CONGRESS | H | 1,019,554 | 1,516,234 | 1,516,234 | B | 496,680 | 48.72% | -3,315 | 96,029 | 0 | 0 | 0 | 0 | 500,000 | 0 | -99,349 | D7 own money | explained |
| C00850420 | CISNEROS FOR CONGRESS | H | 488,202 | 972,989 | 984,589 | B | 496,388 | 101.68% | -10,210 | 6,210 | 0 | 0 | 0 | 0 | 506,600 | 0 | -16,422 | D7 own money | explained |
| C00167015 | DEMOCRATIC PARTY OF ILLINOIS | Y | 776,707 | 760,742 | 1,253,824 | B | 477,117 | 61.43% | -11,950 | 715 | 0 | 16,076 | 0 | 0 | 0 | 397,267 | 63,060 | D8 organizations on line 15 | unexplained |
| C00824912 | UNITE PAC | V | 272,363 | 269,263 | 748,207 | B | 475,844 | 174.71% | -85,500 | 2,750 | 589,444 | 0 | 0 | 0 | 0 | 0 | -116,350 | D3 other line | explained |
| C00887992 | BATTLE BORN PROGRESS - FEDERAL | V | 0 | 0 | 475,000 | B | 475,000 |  | 0 | 0 | 475,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00785899 | EQUALITY PROJECT PAC | W | 130,482 | 572,055 | 604,555 | B | 474,073 | 363.32% | 0 | 125 | 479,073 | 0 | 0 | 0 | 0 | 0 | -5,125 | D3 other line | explained |
| C00528455 | INTERNATIONAL ALLIANCE OF THEATRICAL STAGE EMPLOYEES FEDERAL SPEECH PAC | O | 0 | 0 | 473,700 | B | 473,700 |  | 0 | 15,000 | 0 | 0 | 0 | 0 | 0 | 458,700 | 0 | D8 organizations on line 15 | explained |
| C00785311 | FUTURE DEMOCRATS PAC | W | 7,220 | 426,573 | 476,573 | B | 469,353 | 6500.73% | -1,907 | -2,608 | 474,486 | 0 | 0 | 0 | 0 | 0 | -2,525 | D3 other line | explained |
| C00822536 | HEALTHCARE FOR ACTION PAC | W | 156,420 | 623,800 | 623,800 | B | 467,380 | 298.80% | 0 | 0 | 467,500 | 0 | 0 | 0 | 0 | 0 | -120 | D3 other line | explained |
| C00811786 | DEMOCRACY DEFENSE FUND | V | 155,429 | 619,392 | 619,392 | B | 463,963 | 298.50% | -12,697 | 245 | 478,239 | 0 | 0 | 0 | 0 | 0 | -14,521 | D3 other line | explained |
| C00630129 | DEMOCRACY LEGACY | O | 5,260 | 78,648 | 454,609 | B | 449,349 | 8542.76% | -3,150 | 0 | 0 | 0 | 0 | 0 | 0 | 375,961 | 73,388 | D8 organizations on line 15 | unexplained |
| C00678995 | BE A HERO PAC | W | 1,673 | 42,238 | 442,336 | B | 440,663 | 26339.69% | 0 | 0 | 441,136 | 0 | 0 | 0 | 0 | 0 | -473 | D3 other line | explained |
| C00871475 | FOR LOVE OF COUNTRY, INC. | V | 32,450 | 442,450 | 457,450 | B | 425,000 | 1309.71% | 0 | 0 | 425,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00620021 | COMMON DEFENSE ACTION FUND | V | 27,972 | 251,095 | 452,504 | B | 424,532 | 1517.70% | -4,750 | 0 | 448,404 | 0 | 0 | 0 | 0 | 0 | -23,872 | D3 other line | explained |
| C00559906 | AMERICAS PAC | O | 280,000 | 280,000 | 696,000 | B | 416,000 | 148.57% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 416,000 | 0 | D8 organizations on line 15 | explained |
| C00843029 | COURAGEOUS LEADERS | N | 1,403,300 | 1,817,614 | 1,817,614 | B | 414,314 | 29.52% | -79,800 | 397,019 | 0 | 0 | 0 | 0 | 534,215 | 0 | -516,920 | D7 own money | explained |
| C00519413 | L PAC | W | 265,958 | 601,540 | 656,540 | B | 390,582 | 146.86% | 0 | 2,250 | 390,582 | 0 | 0 | 0 | 0 | 0 | -2,250 | D3 other line | explained |
| C00877233 | AMERICAN CONSERVATION COALITION PAC (ACC PAC) | V | 30,000 | 225,000 | 415,000 | B | 385,000 | 1283.33% | 0 | 0 | 390,000 | 0 | 0 | 0 | 0 | 0 | -5,000 | D3 other line | explained |
| C00816876 | OUTRIDER PAC | V | 0 | 385,000 | 385,000 | B | 385,000 |  | 0 | 0 | 385,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00672576 | BLACK ECONOMIC ALLIANCE PAC | W | 113,500 | 488,530 | 488,530 | B | 375,030 | 330.42% | 0 | 2,500 | 380,030 | 0 | 0 | 0 | 0 | 0 | -7,500 | D3 other line | explained |
| C00795534 | PURPLE GOOD GOVERNMENT PAC (PURPLE PAC; PGGPAC; PPAC) | V | 20,000 | 375,000 | 375,000 | B | 355,000 | 1775.00% | 0 | 0 | 355,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00855098 | GUARANTEE PAC | V | 15,000 | 367,500 | 367,500 | B | 352,500 | 2350.00% | 0 | 0 | 352,500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00858233 | FIGHTING FOR AMERICA'S FUTURE | O | 5,000 | 5,000 | 355,000 | B | 350,000 | 7000.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 350,000 | 0 | D8 organizations on line 15 | explained |
| C00867028 | FIND OUT PAC | V | 76,704 | 393,905 | 424,405 | B | 347,701 | 453.31% | -330 | 0 | 348,788 | 0 | 0 | 0 | 0 | 0 | -1,087 | D3 other line | explained |
| C00885137 | SPEAK UP PAC | V | 126,353 | 123,746 | 473,746 | B | 347,393 | 274.94% | -1,000 | 1,033 | 351,935 | 0 | 0 | 0 | 0 | 0 | -5,575 | D3 other line | explained |
| C90016023 | 32BJ UNITED AMERICAN DREAM FUND | I |  | 0 | 337,500 | B | 337,500 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 337,500 | none | no FEC figure |
| C00864785 | IN THIS TOGETHER PAC | V | 760,640 | 829,310 | 1,090,529 | B | 329,889 | 43.37% | -6,500 | 1,600 | 338,816 | 0 | 0 | 0 | 0 | 0 | -10,527 | D3 other line | explained |
| C00764274 | SECURE PROGRESS | W | 526,991 | 849,257 | 849,257 | B | 322,266 | 61.15% | -9,200 | 3,697 | 331,473 | 0 | 0 | 0 | 0 | 0 | -12,904 | D3 other line | explained |
| C00825737 | SIEMBRA PAC | V | 0 | 71,311 | 305,886 | B | 305,886 |  | -75,708 | 0 | 381,594 | 0 | 0 | 0 | 0 | 0 | -75,708 | D3 other line | explained |
| C00824656 | UNITED TOMORROW | O | 74,850 | 74,850 | 376,350 | B | 301,500 | 402.81% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 301,500 | 0 | D8 organizations on line 15 | explained |
| C90022872 | IN UNION USA ACTION | I |  | 0 | 300,995 | B | 300,995 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 300,995 | none | no FEC figure |
| C00866731 | GROWTH DEMOCRATS | V | 29,772 | 330,266 | 330,266 | B | 300,494 | 1009.30% | 0 | 164 | 300,500 | 0 | 0 | 0 | 0 | 0 | -170 | D3 other line | explained |
| C00893362 | FORWARD PAC INC. | V | 5,000 | 305,000 | 305,000 | B | 300,000 | 6000.00% | 0 | 0 | 300,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00875039 | HIGH PLAINS PAC | O | 1,085,000 | 735,000 | 1,385,000 | B | 300,000 | 27.65% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 300,000 | 0 | D8 organizations on line 15 | explained |
| C00863472 | EDW ACTION FUND | V | 0 | 25,500 | 290,500 | B | 290,500 |  | 0 | 0 | 290,500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00543504 | GROUNDWORK PROJECT PAC | W | 6,455 | 293,898 | 293,898 | B | 287,443 | 4453.03% | -30 | -20 | 287,493 | 0 | 0 | 0 | 0 | 0 | -30 | D3 other line | explained |
| C00488387 | TRI-STATE MAXED-OUT WOMEN | W | 780,942 | 1,063,121 | 1,063,121 | B | 282,179 | 36.13% | -15,100 | -2,100 | 302,280 | 0 | 0 | 0 | 0 | 0 | -18,001 | D3 other line | explained |
| C00884130 | ROAD2RIGHTS | O | 0 | 281,162 | 281,162 | B | 281,162 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 281,162 | none | unexplained |
| C00025254 | MINNESOTA DEMOCRATIC-FARMER-LABOR PARTY | Y | 2,945,906 | 2,996,511 | 3,226,582 | B | 280,676 | 9.53% | -18,525 | 8,460 | 0 | 17,500 | 0 | 0 | 0 | 230,071 | 24,645 | D8 organizations on line 15 | explained |
| C00711549 | HONOR BOUND PAC | W | 15,651 | 255,651 | 296,061 | B | 280,410 | 1791.64% | 0 | 0 | 280,410 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00853838 | SURVIVOR POLITICAL ACTION COMMITTEE (DBA SURVIVOR PAC) | V | 0 | 0 | 279,407 | B | 279,407 |  | 0 | 0 | 279,407 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90017492 | INDIVISIBLE PROJECT INC. | I |  | 275,486 | 276,486 | B | 276,486 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 276,486 | none | no FEC figure |
| C90019357 | FOOD AND WATER ACTION | I |  | 0 | 275,135 | B | 275,135 |  | 0 | 0 | 0 | 135,135 | 0 | 0 | 0 | 0 | 140,000 | D4 names a committee | no FEC figure |
| C00853887 | ENERGIZED FOR CHANGE FEDERAL PAC | V | 943,141 | 874,307 | 1,216,062 | B | 272,921 | 28.94% | -68,247 | 46,314 | 341,755 | 0 | 0 | 0 | 3,300 | 0 | -118,448 | D3 other line | explained |
| C00891879 | INDEPENDENT VETERANS OF AMERICA PAC | V | 0 | 0 | 266,500 | B | 266,500 |  | 0 | 0 | 266,500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880070 | ARAB AMERICANS FOR A BETTER AMERICA | V | 13,000 | 21,000 | 277,750 | B | 264,750 | 2036.54% | 0 | 0 | 264,750 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00844530 | ROLLING SEA ACTION FUND | V | 146,963 | 165,554 | 411,190 | B | 264,227 | 179.79% | -758 | 1,735 | 277,136 | 0 | 0 | 0 | 0 | 0 | -14,644 | D3 other line | explained |
| C90017898 | PROTECT OUR WINTERS ACTION FUND | I |  | 140,466 | 261,966 | B | 261,966 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 261,966 | none | no FEC figure |
| C00853010 | THE FIRST ASK | V | 5,150 | 263,483 | 265,733 | B | 260,583 | 5059.86% | -28,388 | 0 | 288,971 | 0 | 0 | 0 | 0 | 0 | -28,388 | D3 other line | explained |
| C00831651 | LEADERSHIP AMERICA NEEDS | W | 706,421 | 819,515 | 964,565 | B | 258,144 | 36.54% | -2,850 | 2,400 | 449,150 | 0 | 0 | 0 | 0 | 0 | -193,406 | D3 other line | explained |
| C00890657 | OLD LINE PAC | O | 0 | 0 | 250,000 | B | 250,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 250,000 | 0 | D8 organizations on line 15 | explained |
| C90018177 | THE WILDERNESS SOCIETY ACTION FUND | I |  | 0 | 250,000 | B | 250,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 250,000 | none | no FEC figure |
| C00772079 | DIGITAL LEADERSHIP FUND | O | 0 | 0 | 250,000 | B | 250,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 250,000 | 0 | D8 organizations on line 15 | explained |
| C00746628 | FUTURE PROGRESS | O | 0 | 0 | 250,000 | B | 250,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 250,000 | 0 | D8 organizations on line 15 | explained |
| C00667196 | UNITE AMERICA REFORM FUND | O | 1,967,500 | 1,967,500 | 2,217,500 | B | 250,000 | 12.71% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 250,000 | 0 | D8 organizations on line 15 | explained |
| C00885426 | CARDS AGAINST HUMANITY PAC | O | 102,072 | 2,065 | 352,065 | B | 249,993 | 244.92% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 249,993 | none | unexplained |
| C00850750 | CONTEST EVERY RACE PAC | V | 0 | 0 | 249,450 | B | 249,450 |  | -10,690 | 0 | 260,480 | -340 | 0 | 0 | 0 | 0 | -10,690 | D3 other line | explained |
| C00773820 | ENGEL FOR ARIZONA | H | 5,202,576 | 5,447,500 | 5,451,800 | B | 249,224 | 4.79% | -66,126 | 618,852 | 0 | 0 | 0 | 0 | 0 | 0 | -369,628 | D2 duplicates | explained |
| C00872317 | DRAG PAC | V | 28,843 | 267,622 | 275,202 | B | 246,359 | 854.14% | -1,221 | 0 | 247,580 | 0 | 0 | 0 | 0 | 0 | -1,221 | D3 other line | explained |
| C00674697 | SUNRISE PAC | W | 24,096 | 98,040 | 268,433 | B | 244,338 | 1014.04% | 0 | 0 | 244,338 | 0 | 0 | 0 | 0 | 0 | -0 | D3 other line | explained |
| C00821348 | PROGRESSIVE VICTORY PAC | V | 137,210 | 394,826 | 380,194 | B | 242,984 | 177.09% | -105,823 | 2,324 | 350,276 | 0 | 0 | 0 | 0 | 0 | -109,616 | D3 other line | explained |
| C00690867 | LEFT OF CENTER PAC | V | 0 | 205,214 | 236,214 | B | 236,214 |  | 0 | 0 | 236,214 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00674093 | BRADY PAC | W | 419,636 | 514,492 | 655,611 | B | 235,975 | 56.23% | -13,863 | 15,849 | 307,819 | 0 | 0 | 0 | 0 | 0 | -87,693 | D3 other line | explained |
| C00856815 | LATINOS FOR AMERICA | V | 0 | 235,000 | 235,000 | B | 235,000 |  | -200,000 | 0 | 435,000 | 0 | 0 | 0 | 0 | 0 | -200,000 | D3 other line | explained |
| C00847673 | STOP THESE OPPRESSIVE PEOPLE: TYRANTS RACISTS UNQUALIFIEDS MISOGYNISTS PROPAGANDISTS (STOP TRUMP) | V | 3,943,923 | 4,165,670 | 4,165,670 | B | 221,747 | 5.62% | -119,284 | 222,251 | 422,029 | 0 | 0 | 0 | 0 | 0 | -422,533 | D3 other line | explained |
| C00843938 | UNITED FOR AMERICA INC | V | 0 | 172,487 | 216,987 | B | 216,987 |  | -77 | 0 | 217,064 | 0 | 0 | 0 | 0 | 0 | -77 | D3 other line | explained |
| C00660795 | DAN CRENSHAW FOR CONGRESS | H | 1,540,266 | 1,742,414 | 1,753,164 | B | 212,898 | 13.82% | -8,020 | 262,351 | 0 | 0 | 0 | 0 | 0 | 0 | -49,453 | D2 duplicates | explained |
| C00523589 | AMERICAN UNITY PAC INC | W | 32,300 | 239,300 | 239,300 | B | 207,000 | 640.87% | 0 | 0 | 207,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00704981 | MICHELLE STEEL FOR CONGRESS | H | 2,899,942 | 3,079,976 | 3,103,576 | B | 203,634 | 7.02% | -47,864 | 123,428 | 0 | 0 | 0 | 0 | 260,000 | 0 | -179,794 | D7 own money | explained |
| C00476978 | LGBTQ VICTORY FUND FEDERAL PAC | W | 166,007 | 247,367 | 364,615 | B | 198,608 | 119.64% | 0 | 100 | 198,985 | 0 | 0 | 0 | 0 | 0 | -477 | D3 other line | explained |
| C00816124 | PATRIOT FREEDOM PAC INC | V | 436,750 | 559,250 | 633,284 | B | 196,534 | 45.00% | 0 | 0 | 196,534 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00839894 | TURN LEFT PAC | V | 29,984 | 221,916 | 225,327 | B | 195,343 | 651.49% | -44,995 | 140 | 240,573 | 3,411 | 0 | 0 | 0 | 0 | -48,781 | D3 other line | explained |
| C00546119 | SELECT MEDICAL CORPORATION PAC | Q | 609,519 | 795,006 | 795,006 | B | 185,487 | 30.43% | 0 | 186,659 | 0 | 0 | 0 | 0 | 0 | 0 | -1,172 | D2 duplicates | explained |
| C00884361 | THE AMERICAN DREAM PAC | V | 42,700 | 223,864 | 223,864 | B | 181,164 | 424.27% | 0 | 0 | 181,164 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00867762 | PAPERBACK PAC, INC. | O | 1,000 | 1,000 | 180,809 | B | 179,809 | 17980.90% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 179,809 | 0 | D8 organizations on line 15 | explained |
| C00473918 | WOMEN VOTE | O | 14,592,865 | 11,062,850 | 14,769,817 | B | 176,952 | 1.21% | -1,000 | 1,005,500 | 0 | 0 | 0 | 0 | 0 | 0 | -828,548 | D2 duplicates | explained |
| C00571091 | LEADERS IN EDUCATION | W | 10,625 | 110,625 | 186,625 | B | 176,000 | 1656.47% | 0 | 0 | 176,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00868596 | WEST VIRGINIANS TO ELECT DON | S | 0 | 175,299 | 175,299 | B | 175,299 |  | 0 | 0 | 0 | 0 | 0 | 0 | 175,299 | 0 | 0 | D7 own money | explained |
| C00516500 | POWERPACPLUS | W | 0 | 25,000 | 175,000 | B | 175,000 |  | 0 | 0 | 175,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00866640 | RESOLUTE COURAGE PAC | W | 17,500 | 142,500 | 192,500 | B | 175,000 | 1000.00% | 0 | 0 | 175,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00746107 | PROGRESSNOW AZ - FEDERAL | O | 258,030 | 251,500 | 433,029 | B | 174,999 | 67.82% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 174,999 | 0 | D8 organizations on line 15 | explained |
| C00883017 | JOIN THE UNION | V | 39,675 | 214,597 | 210,689 | B | 171,014 | 431.04% | -41,729 | -50 | 212,943 | 0 | 0 | 0 | 0 | 0 | -41,879 | D3 other line | explained |
| C00401786 | FREEDOM'S DEFENSE FUND | V | 311,806 | 480,768 | 480,768 | B | 168,962 | 54.19% | -4,925 | 2,125 | 171,491 | 0 | 0 | 0 | 0 | 0 | -4,654 | D3 other line | explained |
| C00794404 | CRIMSON GOES BLUE, INC. | V | 240,171 | 409,107 | 409,107 | B | 168,936 | 70.34% | -60,515 | 0 | 230,000 | 0 | 0 | 0 | 0 | 0 | -61,064 | D3 other line | explained |
| C00746073 | DEMOCRACY DEFENSE ACTION | V | 16,708 | 185,114 | 185,114 | B | 168,406 | 1007.94% | -500 | 175 | 169,871 | 0 | 0 | 0 | 0 | 0 | -1,640 | D3 other line | explained |
| C00829952 | HOPE IN ACTION PAC | V | 0 | 10,000 | 165,000 | B | 165,000 |  | 0 | 0 | 165,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00410068 | FRATERNITY & SORORITY POLITICAL ACTION COMMITTEE | W | 671,883 | 768,628 | 834,843 | B | 162,960 | 24.25% | -4,975 | 0 | 168,131 | 0 | 0 | 0 | 0 | 0 | -5,171 | D3 other line | explained |
| C00815928 | READY TO WIN | V | 284,972 | 446,082 | 446,182 | B | 161,210 | 56.57% | -90 | 200 | 161,308 | 0 | 0 | 0 | 0 | 0 | -298 | D3 other line | explained |
| C00010363 | CONSERVATIVE LEADERSHIP POLITICAL ACTION COMMITTEE | W | 118,900 | 275,300 | 276,800 | B | 157,900 | 132.80% | 0 | 0 | 157,900 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00836403 | TEAM EMMER | N | 3,007,632 | 3,164,232 | 3,164,232 | B | 156,600 | 5.21% | 0 | 431,904 | 0 | 0 | 0 | 0 | 0 | 0 | -275,304 | D2 duplicates | explained |
| C00774463 | DEMOCRATS SERVE | V | 8,450 | 74,050 | 164,155 | B | 155,705 | 1842.66% | 0 | 0 | 155,655 | 0 | 0 | 0 | 0 | 50 | 0 | D3 other line | explained |
| C90022997 | PAC FOR GEORGIA'S YOUTH | I |  | 0 | 153,998 | B | 153,998 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 153,998 | none | no FEC figure |
| C00881169 | GEORGIA PROGRESS INCUBATOR | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880955 | TEXAS MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881086 | NEVADA POLITICAL INNOVATIONS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881185 | MICHIGAN PROGRESS INCUBATOR | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00570721 | LONG ISLAND LAW ENFORCEMENT FOUNDATION | O | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 150,000 | 0 | D8 organizations on line 15 | explained |
| C00880856 | ARIZONA MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00849075 | MOVEMENT LABS PAC | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881151 | ARIZONA PROGRESS INCUBATOR | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880948 | WISCONSIN MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00874404 | AMERICAN DEMOCRACY LAB | O | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 150,000 | 0 | D8 organizations on line 15 | explained |
| C00877977 | RAPID RECRUIT PAC | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880898 | MICHIGAN MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00875625 | WIN FOR DEMOCRACY PAC | O | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | explained |
| C00880930 | PENNSYLVANIA MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880922 | NORTH CAROLINA MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881110 | PENNSYLVANIA POLITICAL INNOVATIONS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881219 | PENNSYLVANIA PROGRESS INCUBATOR | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881136 | TEXAS POLITICAL INNOVATIONS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880914 | NEVADA MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880963 | FLORIDA MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880872 | GEORGIA MOVEMENT LABS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881193 | NEVADA PROGRESS INCUBATOR | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881094 | NORTH CAROLINA POLITICAL INNOVATIONS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881128 | WISCONSIN POLITICAL INNOVATIONS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00877993 | POLITICAL INNOVATIONS PAC | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00488494 | NEW PROSPERITY FOUNDATION; THE | O | 0 | 150,000 | 150,000 | B | 150,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 150,000 | none | unexplained |
| C00877985 | TEXTING SOLUTIONS PAC | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880971 | ARIZONA POLITICAL INNOVATIONS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880997 | MICHIGAN POLITICAL INNOVATIONS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881201 | NORTH CAROLINA PROGRESS INCUBATOR | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00881144 | FLORIDA POLITICAL INNOVATIONS | V | 0 | 0 | 150,000 | B | 150,000 |  | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00758003 | RURAL GROUNDGAME 3X | V | 4,275 | 63,665 | 149,252 | B | 144,977 | 3391.27% | 0 | 200 | 145,152 | 0 | 0 | 0 | 0 | 0 | -375 | D3 other line | explained |
| C00826115 | ADVANCE RIGHT SUPER PAC | O | 0 | 30,000 | 144,900 | B | 144,900 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 114,900 | 30,000 | D8 organizations on line 15 | unexplained |
| C00581876 | KASICH FOR AMERICA, INC. | W | 244,090 | 352,940 | 387,013 | B | 142,923 | 58.55% | -15,000 | 100 | 167,923 | 0 | 0 | 0 | 0 | 0 | -25,100 | D3 other line | explained |
| C00099267 | TEXAS DEMOCRATIC PARTY | Y | 1,021,498 | 1,116,898 | 1,164,218 | B | 142,720 | 13.97% | -9,229 | 6,705 | 0 | 0 | 0 | 0 | 0 | 47,320 | 88,695 | D8 organizations on line 15 | unexplained |
| C00640300 | ACTIVATE AMERICA | O | 1,287,409 | 1,222,341 | 1,429,791 | B | 142,382 | 11.06% | -8,763 | 175,424 | 0 | 0 | 0 | 0 | 0 | 0 | -33,042 | D2 duplicates | explained |
| C00800060 | POLARIS NATIONAL SECURITY PAC, INC. | W | 14,800 | 114,800 | 156,800 | B | 142,000 | 959.46% | 0 | 999 | 142,000 | 0 | 0 | 0 | 0 | 0 | -999 | D3 other line | explained |
| C00788463 | HARBICK FOR US SENATE | S | 0 | 140,412 | 140,412 | B | 140,412 |  | 0 | 0 | 0 | 0 | 0 | 0 | 140,412 | 0 | 0 | D7 own money | explained |
| C00803593 | BUILDING AMERICA'S ECONOMY | V | 13,000 | 13,000 | 153,000 | B | 140,000 | 1076.92% | 0 | 0 | 140,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00878918 | WOMEN'S HEALTH PAC | V | 60,850 | 192,650 | 200,650 | B | 139,800 | 229.75% | 0 | 0 | 139,800 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00845131 | COALITION FOR FANTASY SPORTS PAC | V | 2,100 | 2,100 | 137,450 | B | 135,350 | 6445.24% | 0 | 0 | 135,350 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00865121 | COUNTER COALITION | V | 0 | 133,956 | 135,258 | B | 135,258 |  | 0 | 0 | 135,258 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90021155 | NATIONAL WOMEN''S LAW CENTER ACTION FUND | I |  | 110,000 | 135,000 | B | 135,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 135,000 | none | no FEC figure |
| C90021692 | 350 WISCONSIN ACTION | I |  | 29,000 | 134,000 | B | 134,000 |  | 0 | 0 | 0 | 25,000 | 0 | 0 | 0 | 0 | 109,000 | D4 names a committee | no FEC figure |
| C00670216 | YOUTH PROGRESSIVE ACTION CATALYST | W | 182,281 | 311,053 | 315,752 | B | 133,471 | 73.22% | -500 | 1,825 | 133,971 | 0 | 0 | 0 | 0 | 0 | -2,325 | D3 other line | explained |
| C00879866 | WHISTLEBLOWER PAC | V | 0 | 0 | 130,000 | B | 130,000 |  | 0 | 0 | 130,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00843656 | HEROES FOR DEMOCRACY | V | 0 | 110,184 | 128,184 | B | 128,184 |  | -638 | -35 | 128,857 | 0 | 0 | 0 | 0 | 0 | -638 | D3 other line | explained |
| C00880518 | BITCOIN VOTER PAC | V | 0 | 0 | 125,000 | B | 125,000 |  | 0 | 0 | 125,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00866590 | BILL CAMPBELL COMMITTEE | H | 0 | 120,718 | 120,718 | B | 120,718 |  | -3,282 | 0 | 0 | 0 | 0 | 0 | 124,000 | 0 | -3,282 | D7 own money | explained |
| C00797241 | LAFAZAN FOR CONGRESS | H | 551,688 | 672,224 | 671,724 | B | 120,036 | 21.76% | -22,209 | 5,550 | 0 | 0 | 0 | 0 | 166,000 | 0 | -51,514 | D7 own money | explained |
| C00838862 | DEVELOPMENT NOW FOR CHICAGO | X |  | 119,000 | 119,000 | B | 119,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 119,000 | none | no FEC figure |
| C00776526 | TIM SCOTT VICTORY FUND | N | 2,492,048 | 2,611,035 | 2,611,035 | B | 118,987 | 4.77% | 0 | 6,050 | 0 | 0 | 0 | 0 | 0 | 0 | 112,937 | D2 duplicates | unexplained |
| C00758011 | VOTAR ES PODER PAC | O | 0 | 0 | 115,000 | B | 115,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 115,000 | 0 | D8 organizations on line 15 | explained |
| C00599050 | NEW HORIZONS USA POLITICAL ACTION COMMITTEE | V | 0 | 0 | 112,500 | B | 112,500 |  | 0 | 0 | 112,500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00010439 | IDAHO STATE DEMOCRATIC PARTY | Y | 1,298,557 | 1,341,568 | 1,408,748 | B | 110,191 | 8.49% | -15,825 | 30,593 | 0 | 0 | 0 | 0 | 0 | 46,464 | 33,134 | D8 organizations on line 15 | unexplained |
| C00835017 | DEMOCRACY PROTECTION PROJECT | V | 27,000 | 135,000 | 134,000 | B | 107,000 | 396.30% | -1,000 | 0 | 108,000 | 0 | 0 | 0 | 0 | 0 | -1,000 | D3 other line | explained |
| C00874032 | LEAD LOCALLY PAC | O | 91,900 | 41,900 | 191,900 | B | 100,000 | 108.81% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 100,000 | 0 | D8 organizations on line 15 | explained |
| C00762658 | KEEP AMERICA AMERICA ACTION FUND | O | 235,000 | 0 | 335,000 | B | 100,000 | 42.55% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 99,970 | D8 organizations on line 15 | unexplained |
| C00837336 | STAY ENGAGED | V | 0 | 100,000 | 100,000 | B | 100,000 |  | 0 | 0 | 100,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00571398 | BLAKPAC | O | 0 | 100,000 | 100,000 | B | 100,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 100,000 | none | unexplained |
| C00812792 | EVERY STATE | V | 109,368 | 207,457 | 207,457 | B | 98,089 | 89.69% | 0 | 7,229 | 99,394 | 0 | 0 | 0 | 0 | 0 | -8,534 | D3 other line | explained |
| C00005561 | DEMOCRATIC EXECUTIVE COMMITTEE OF FLORIDA | Y | 2,585,922 | 2,494,331 | 2,681,729 | B | 95,807 | 3.70% | -83,373 | 11,911 | 0 | 0 | 0 | 0 | 0 | 83,896 | 0 | D8 organizations on line 15 | explained |
| C00793083 | FRONTLINE PATRIOTS | W | 7,050 | 82,050 | 102,050 | B | 95,000 | 1347.52% | 0 | 0 | 95,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00699785 | MISES PAC | V | 108,329 | 200,607 | 201,035 | B | 92,706 | 85.58% | 0 | 900 | 93,698 | 0 | 0 | 0 | 0 | 0 | -1,892 | D3 other line | explained |
| C00754192 | ORANGE COUNTY PAC | O | 571,675 | 21,675 | 664,000 | B | 92,325 | 16.15% | 0 | 0 | 0 | 275,000 | 0 | 0 | 0 | 0 | -182,675 | D4 names a committee | explained |
| C00632554 | REAL JUSTICE PAC | V | 58,360 | 149,606 | 149,606 | B | 91,246 | 156.35% | 0 | 84 | 91,246 | 0 | 0 | 0 | 0 | 0 | -84 | D3 other line | explained |
| C00140590 | CALIFORNIA REPUBLICAN PARTY FEDERAL ACCT. | Y | 4,078,507 | 3,918,559 | 4,169,408 | B | 90,901 | 2.23% | -3,370 | 189,500 | 0 | 118,888 | 0 | 0 | 0 | 0 | -217,487 | D2 duplicates | explained |
| C90021643 | PA STANDS UP POWER | I |  | 0 | 90,000 | B | 90,000 |  | 0 | 0 | 0 | 90,000 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | no FEC figure |
| C00878165 | ANIMAL PROTECTION PAC | V | 44,961 | 133,706 | 133,706 | B | 88,745 | 197.38% | -1,250 | 133 | 90,000 | 0 | 0 | 0 | 0 | 0 | -1,388 | D3 other line | explained |
| C00760686 | BLACK LIVES MATTER PAC | V | 0 | 88,646 | 88,646 | B | 88,646 |  | 0 | 0 | 88,646 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00527226 | WE VOTE - NOSOTROS VOTAMOS - PPAMM COMMITTEE | O | 365,749 | 413,579 | 454,330 | B | 88,581 | 24.22% | -1,250 | 7,725 | 0 | 0 | 0 | 0 | 0 | 40,751 | 40,105 | D8 organizations on line 15 | unexplained |
| C00838219 | GOLDEN STATE WATCHDOG PAC | V | 13,261 | 13,260 | 100,760 | B | 87,499 | 659.84% | 0 | 0 | 87,500 | 0 | 0 | 0 | 0 | 0 | -1 | D3 other line | explained |
| C00848937 | BAN ASSAULT WEAPONS NOW PAC | V | 114,426 | 113,529 | 201,262 | B | 86,836 | 75.89% | -525 | 55,376 | 87,733 | 0 | 0 | 0 | 0 | 0 | -56,273 | D3 other line | explained |
| C00667055 | DEMSVOTE | V | 0 | 86,181 | 86,181 | B | 86,181 |  | 0 | 0 | 86,181 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90022740 | MARCH FOR OUR LIVES ACTION FUND | I |  | 9,991 | 84,991 | B | 84,991 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 84,991 | none | no FEC figure |
| C00776609 | SOUTHERN PROGRESS | V | 8,610 | 93,125 | 93,125 | B | 84,515 | 981.62% | -1,012 | 0 | 85,661 | 0 | 0 | 0 | 0 | 0 | -1,146 | D3 other line | explained |
| C00809020 | AMERICAN DREAM FEDERAL ACTION | V | 0 | 0 | 84,031 | B | 84,031 |  | 0 | 0 | 84,031 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90022104 | NH PEACE ACTION | I |  | 7,500 | 82,500 | B | 82,500 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 82,500 | none | no FEC figure |
| C00879973 | DEMOCRACY 2025 | O | 1,050,000 | 882,000 | 1,132,000 | B | 82,000 | 7.81% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 82,000 | none | unexplained |
| C00735738 | KNOCK FOR DEMOCRACY, INC. | W | 224,909 | 316,327 | 306,277 | B | 81,368 | 36.18% | -42,029 | 650 | 124,000 | 0 | 0 | 0 | 0 | 0 | -43,282 | D3 other line | explained |
| C00834309 | VOTE 4 US AMERICA | U | 0 | 81,000 | 81,000 | B | 81,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 81,000 | 0 | 0 | D7 own money | explained |
| C00866418 | IMPACT 65 | O | 0 | 10,000 | 80,000 | B | 80,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 70,000 | 10,000 | D8 organizations on line 15 | unexplained |
| C00833103 | VOTERS OF TOMORROW PAC | V | 221,409 | 242,338 | 299,942 | B | 78,533 | 35.47% | -3,500 | 1,431 | 82,921 | 0 | 0 | 0 | 0 | 0 | -5,819 | D3 other line | explained |
| C00838367 | WOMENLEAD | V | 8,616 | 86,655 | 86,655 | B | 78,039 | 905.70% | 0 | 0 | 78,200 | 0 | 0 | 0 | 0 | 0 | -161 | D3 other line | explained |
| C00532465 | ROUNDS FOR SENATE | S | 319,746 | 393,161 | 395,661 | B | 75,915 | 23.74% | -925 | 86,842 | 0 | 0 | 0 | 0 | 0 | 0 | -10,927 | D2 duplicates | explained |
| C00608489 | GREAT AMERICA PAC | W | 36,985 | 78,010 | 112,610 | B | 75,625 | 204.47% | -375 | 0 | 76,000 | 0 | 0 | 0 | 0 | 0 | -375 | D3 other line | explained |
| C00671628 | STRONGND PAC | V | 5,000 | 75,000 | 80,000 | B | 75,000 | 1500.00% | 0 | 0 | 75,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90023185 | BLUE SKY WAUKESHA | I |  | 0 | 75,000 | B | 75,000 |  | 0 | 0 | 0 | 75,000 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | no FEC figure |
| C00388181 | CONNELL FOLEY PAC A NEW JERSEY NON-PROFIT CORPORATION | N | 48,000 | 122,885 | 122,885 | B | 74,885 | 156.01% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 74,885 | none | unexplained |
| C00877134 | TOUR TO SAVE DEMOCRACY CO. | V | 0 | 57,862 | 72,662 | B | 72,662 |  | -9,985 | 0 | 82,647 | 0 | 0 | 0 | 0 | 0 | -9,985 | D3 other line | explained |
| C00729574 | AMERICANS4HINDUS PAC (MULTI-CANDIDATE) | W | 288,440 | 335,687 | 359,037 | B | 70,597 | 24.48% | -5,150 | 275 | 83,033 | 0 | 0 | 0 | 0 | 0 | -12,711 | D3 other line | explained |
| C00745869 | TOM STEYER PAC | V | 0 | 70,000 | 70,000 | B | 70,000 |  | 0 | 0 | 70,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00706689 | 80-20 ASIAN AMERICAN EMPOWERMENT PAC | V | 106,250 | 174,250 | 174,250 | B | 68,000 | 64.00% | 0 | 0 | 68,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00765768 | HER BOLD MOVE ACTION | V | 70,109 | 135,175 | 136,175 | B | 66,066 | 94.23% | -1,750 | 750 | 69,025 | 0 | 0 | 0 | 0 | 0 | -3,709 | D3 other line | explained |
| C00785774 | KRIMSON POLITICAL ACTION COUNCIL LLC | W | 43,437 | 43,437 | 109,437 | B | 66,000 | 151.94% | 0 | 0 | 66,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880302 | REPRO RISING VIRGINIA PAC | V | 18,050 | 83,050 | 84,050 | B | 66,000 | 365.65% | 0 | 0 | 66,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00687483 | NATIONAL DEMOCRATIC COUNTY OFFICIALS - NDCO | V | 0 | 0 | 65,000 | B | 65,000 |  | 0 | 0 | 65,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00760132 | NYIC POLITICAL ACTION FUND | O | 0 | 0 | 65,000 | B | 65,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 65,000 | 0 | D8 organizations on line 15 | explained |
| C00169441 | DICKIE, MCCAMEY & CHILCOTE, PC POLITICAL ACTION COMMITTEE | Q | 0 | 63,225 | 63,225 | B | 63,225 |  | 0 | 7,650 | 0 | 0 | 0 | 0 | 0 | 0 | 55,575 | D2 duplicates | unexplained |
| C00874214 | CARL MARK COESTER | H | 11,135 | 74,017 | 74,017 | B | 62,882 | 564.72% | 0 | 0 | 0 | 0 | 0 | 0 | 63,132 | 0 | -250 | D7 own money | explained |
| C00603084 | NDTC | V | 2,665,836 | 2,587,328 | 2,726,379 | B | 60,543 | 2.27% | 0 | 145,788 | 297,536 | 0 | 0 | 0 | 0 | 0 | -382,781 | D3 other line | explained |
| C00130658 | CPAC ACTION PAC | V | 1,473,204 | 1,533,350 | 1,533,350 | B | 60,146 | 4.08% | 0 | 10,796 | 60,150 | 0 | 0 | 0 | 0 | 0 | -10,800 | D3 other line | explained |
| C90021577 | DOLORES HUERTA ACTION FUND | I |  | 0 | 58,920 | B | 58,920 |  | 0 | 0 | 0 | 58,920 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | no FEC figure |
| C00712109 | GRASSROOTS LAW PAC | V | 9,993 | 67,848 | 67,848 | B | 57,855 | 578.97% | -100 | 0 | 57,969 | 0 | 0 | 0 | 0 | 0 | -114 | D3 other line | explained |
| C00190934 | OKLAHOMA DEMOCRATIC PARTY | Y | 445,212 | 322,453 | 502,453 | B | 57,241 | 12.86% | -1,369 | 21,509 | 0 | 0 | 0 | 0 | 0 | 35,732 | 0 | D8 organizations on line 15 | explained |
| C00708255 | OUR STATES MATTER PAC | V | 0 | 30,650 | 55,650 | B | 55,650 |  | 0 | 0 | 55,650 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00880815 | GREATER GEORGIA ACTION | O | 0 | 0 | 55,249 | B | 55,249 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55,249 | 0 | D8 organizations on line 15 | explained |
| C00740126 | UNITEDEMOCRATS PAC | W | 141,049 | 194,591 | 194,591 | B | 53,542 | 37.96% | -6,416 | 3,043 | 67,802 | 0 | 0 | 0 | 0 | 0 | -17,303 | D3 other line | explained |
| C00327189 | VALUE IN ELECTING WOMEN POLITICAL ACTION COMMITTEE | W | 132,900 | 131,400 | 186,400 | B | 53,500 | 40.26% | 0 | 0 | 58,500 | 0 | 0 | 0 | 0 | 0 | -5,000 | D3 other line | explained |
| C00890939 | SECURE PROGRESS | V | 19,760 | 73,175 | 73,175 | B | 53,415 | 270.32% | -500 | 0 | 53,915 | 0 | 0 | 0 | 0 | 0 | -500 | D3 other line | explained |
| C00839407 | GET OUT THE VOTE PAC | W | 530,043 | 581,135 | 581,135 | B | 51,092 | 9.64% | -27,487 | 5,645 | 79,443 | 0 | 0 | 0 | 0 | 0 | -33,996 | D3 other line | explained |
| C00888131 | DALLAS COUNTY DEMOCRATIC PARTY (FEDERAL) | X | 284,342 | 334,643 | 334,643 | B | 50,301 | 17.69% | 0 | 32,600 | 0 | 0 | 0 | 0 | 0 | 0 | 17,701 | D2 duplicates | unexplained |
| C00872341 | MAKE AMERICA JUST AGAIN | V | 0 | 35,000 | 50,032 | B | 50,032 |  | 0 | 0 | 50,032 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00839126 | MARVIN ABNEY FOR CONGRESS | H | 49,800 | 99,800 | 99,800 | B | 50,000 | 100.40% | 0 | 24,400 | 0 | 0 | 0 | 0 | 0 | 0 | 25,600 | D2 duplicates | unexplained |
| C00852483 | EISEN FOR NY | S | 5,300 | 55,300 | 55,300 | B | 50,000 | 943.40% | 0 | 0 | 0 | 0 | 0 | 0 | 50,000 | 0 | 0 | D7 own money | explained |
| C00820712 | BROKER ACTION COALITION PAC (BACPAC) | V | 6,750 | 6,750 | 56,750 | B | 50,000 | 740.74% | 0 | 0 | 50,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00875450 | CENTER FORWARD INITIATIVE INC | O | 302,000 | 0 | 352,000 | B | 50,000 | 16.56% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 50,000 | 0 | D8 organizations on line 15 | explained |
| C00760116 | THE 9 | O | 14,547 | 14,546 | 64,546 | B | 49,999 | 343.71% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 49,999 | 0 | D8 organizations on line 15 | explained |
| C00754754 | RURALVOTE.ORG | O | 214,321 | 124,271 | 264,317 | B | 49,996 | 23.33% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 29 | 49,967 | D8 organizations on line 15 | unexplained |
| C00452276 | PODER PAC | W | 61,250 | 73,450 | 108,850 | B | 47,600 | 77.71% | 0 | 0 | 52,600 | 0 | 0 | 0 | 0 | 0 | -5,000 | D3 other line | explained |
| C00635664 | WOMEN FOR AMERICAN VALUES AND ETHICS POLITICAL ACTION COMMITTEE (A/K/A WAVE PAC) | W | 239,910 | 287,122 | 287,372 | B | 47,462 | 19.78% | -500 | 0 | 47,985 | 0 | 0 | 0 | 0 | 0 | -523 | D3 other line | explained |
| C00630830 | PA PAC AKA PATRIOT ACTION | V | 4,000 | 49,000 | 51,000 | B | 47,000 | 1175.00% | 0 | 0 | 47,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00852152 | JENNIFER ADAMS FOR CONGRESS | H | 90,913 | 137,908 | 137,908 | B | 46,995 | 51.69% | 0 | 0 | 0 | 0 | 0 | 0 | 46,995 | 0 | 0 | D7 own money | explained |
| C00704593 | BLUE BATTLEGROUND PROJECT | V | 17,612 | 16,351 | 64,351 | B | 46,739 | 265.38% | -1,250 | 175 | 48,000 | 0 | 0 | 0 | 0 | 0 | -1,436 | D3 other line | explained |
| C00846139 | MONTANA VALUES FOR AMERICA, INC. | O | 0 | 0 | 46,000 | B | 46,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 46,000 | 0 | D8 organizations on line 15 | explained |
| C90020454 | FREEDOM ACTION NOW INC. | I |  | 0 | 45,435 | B | 45,435 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 45,435 | none | no FEC figure |
| C00885749 | CONSENSUS DEMOCRATS PAC | V | 5,000 | 50,000 | 50,000 | B | 45,000 | 900.00% | 0 | 0 | 45,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00688739 | DITCH FUND | V | 125,756 | 125,588 | 170,115 | B | 44,359 | 35.27% | -165 | 2,885 | 44,527 | 0 | 0 | 0 | 0 | 0 | -3,053 | D3 other line | explained |
| C00847319 | CLATTERBUCK FOR CONGRESS | H | 1,095 | 36,669 | 45,269 | B | 44,174 | 4033.25% | 0 | 0 | 8,600 | 0 | 0 | 0 | 36,169 | 0 | -595 | D7 own money | explained |
| C00299396 | ITALIAN AMERICAN DEMOCRATIC LEADERSHIP COUNCIL | W | 109,850 | 114,850 | 153,410 | B | 43,560 | 39.65% | -5,000 | 500 | 48,560 | 0 | 0 | 0 | 0 | 0 | -5,500 | D3 other line | explained |
| C00851790 | DEREK TRAN FOR CONGRESS | H | 3,636,550 | 3,676,360 | 3,679,960 | B | 43,410 | 1.19% | -61,053 | 26,970 | 0 | 0 | 0 | 0 | 0 | 3,600 | 12,840 | D2 duplicates | explained |
| C90012956 | PATRIOT MAJORITY USA | I |  | 42,500 | 42,500 | B | 42,500 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 42,500 | none | no FEC figure |
| C00888552 | DEFEND THE BLUE DOT PAC | O | 10,250 | 10,250 | 50,250 | B | 40,000 | 390.24% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 40,000 | 0 | D8 organizations on line 15 | explained |
| C90023193 | LIBERTY FIRST USA | I |  | 40,000 | 40,000 | B | 40,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 40,000 | none | no FEC figure |
| C90023052 | POWER ACTION FUND | I |  | 0 | 40,000 | B | 40,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 40,000 | none | no FEC figure |
| C00523217 | MASSACHUSETTS BLUE PAC OF BLUE CROSS BLUE SHIELD OF MASSACHUSETTS | N | 38,262 | 76,862 | 76,862 | B | 38,600 | 100.89% | 0 | 10,381 | 0 | 0 | 0 | 3,000 | 0 | 0 | 25,219 | D2 duplicates | unexplained |
| C00563254 | DEMOCRATIC JEWISH OUTREACH PA | V | 146,537 | 184,699 | 184,699 | B | 38,162 | 26.04% | -500 | 0 | 42,262 | 0 | 0 | 0 | 0 | 0 | -4,100 | D3 other line | explained |
| C00824607 | TOMORROW'S JOBS | V | 17,300 | 32,300 | 53,900 | B | 36,600 | 211.56% | 0 | 0 | 36,600 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00858126 | EDUCATED WE STAND | V | 122,388 | 158,908 | 158,908 | B | 36,520 | 29.84% | -13,000 | 272 | 50,552 | 0 | 0 | 0 | 0 | 0 | -14,304 | D3 other line | explained |
| C00756734 | CHOOSE DEMOCRACY | V | 250 | 30,500 | 35,500 | B | 35,250 | 14100.00% | 0 | 0 | 35,500 | 0 | 0 | 0 | 0 | 0 | -250 | D3 other line | explained |
| C00154625 | KAPTUR FOR CONGRESS | H | 2,318,109 | 2,345,954 | 2,353,254 | B | 35,145 | 1.52% | -13,085 | 98,526 | 0 | 0 | 0 | 0 | 0 | 0 | -63,381 | D2 duplicates | explained |
| C00887067 | MS FUTURE PAC | V | 0 | 0 | 35,000 | B | 35,000 |  | 0 | 0 | 35,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00839233 | DRAFT TUCKER PAC | V | 0 | 35,000 | 35,000 | B | 35,000 |  | 0 | 0 | 35,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00878520 | MOMS FOR SAFE NEIGHBORHOODS, INC. | O | 0 | 0 | 35,000 | B | 35,000 |  | 0 | 0 | 0 | 35,000 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | explained |
| C00839977 | HISPANIC LEADERSHIP PAC | V | 10,261 | 22,900 | 44,900 | B | 34,639 | 337.59% | 0 | 0 | 44,640 | 0 | 0 | 0 | 0 | 0 | -10,001 | D3 other line | explained |
| C00771097 | STACKEDPAC | V | 240 | 34,690 | 34,690 | B | 34,450 | 14354.17% | 0 | 0 | 20,700 | 0 | 0 | 0 | 0 | 0 | 13,750 | D3 other line | unexplained |
| C00348540 | 1199 SEIU UNITED HEALTHCARE WORKERS EAST FEDERAL POLITICAL ACTION FUND | Q | 111,984 | 149,882 | 145,978 | B | 33,994 | 30.36% | -10,671 | 49,253 | 0 | 0 | 0 | 0 | 0 | 0 | -15,259 | D2 duplicates | explained |
| C00167346 | TENNESSEE DEMOCRATIC PARTY | Y | 787,512 | 817,236 | 821,236 | B | 33,724 | 4.28% | -4,192 | 1,675 | 0 | 0 | 0 | 0 | 0 | 4,000 | 28,049 | D8 organizations on line 15 | unexplained |
| C00839878 | ZANE 4 SENATE COMMITTEE | S | 0 | 33,480 | 33,480 | B | 33,480 |  | 0 | 0 | 0 | 0 | 0 | 0 | 33,480 | 0 | 0 | D7 own money | explained |
| C00827063 | BEHEARD PAC | V | 17,500 | 49,575 | 49,575 | B | 32,075 | 183.29% | -2,000 | 0 | 34,075 | 0 | 0 | 0 | 0 | 0 | -2,000 | D3 other line | explained |
| C00827998 | AMERICANS FOR PROSPARODY | V | 0 | 32,020 | 32,020 | B | 32,020 |  | -167,980 | 0 | 200,000 | 0 | 0 | 0 | 0 | 0 | -167,980 | D3 other line | explained |
| C90022799 | ALL IN ACTION FUND | I |  | 0 | 31,248 | B | 31,248 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 31,248 | none | no FEC figure |
| C00844381 | JOE SIGNORELLO FOR CONGRESS | H | 69,654 | 97,378 | 100,897 | B | 31,243 | 44.86% | 0 | 250 | 0 | 0 | 0 | 0 | 31,244 | 0 | -251 | D7 own money | explained |
| C00770495 | PROTECT OHIO VALUES PAC (POV PAC) | V | 0 | 31,000 | 31,000 | B | 31,000 |  | 0 | 0 | 31,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00739557 | ASIAN AMERICAN ADVOCACY FUND PAC | O | 66,431 | 59,275 | 97,431 | B | 31,000 | 46.66% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 31,000 | 0 | D8 organizations on line 15 | explained |
| C00833632 | CARMEN GOERS FOR CONGRESS | H | 116,422 | 147,101 | 147,101 | B | 30,680 | 26.35% | -521 | 2,868 | 0 | 0 | 0 | 0 | 31,207 | 0 | -3,396 | D7 own money | explained |
| C00839308 | PROTECT THE HOUSE CALIFORNIA 2024 | N | 2,015,915 | 2,046,389 | 2,046,389 | B | 30,474 | 1.51% | 0 | 8,500 | 0 | 0 | 0 | 0 | 0 | 0 | 21,974 | D2 duplicates | unexplained |
| C90011156 | WORKING AMERICA | I |  | 30,000 | 30,000 | B | 30,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 30,000 | none | no FEC figure |
| C00859066 | THE SCHOOL BOARD PROJECT | V | 27,850 | 57,850 | 57,850 | B | 30,000 | 107.72% | 0 | 0 | 31,000 | 0 | 0 | 0 | 0 | 0 | -1,000 | D3 other line | explained |
| C00703082 | ARTISTS UNITED FOR CHANGE | O | 679,612 | 59,612 | 709,612 | B | 30,000 | 4.41% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 30,000 | none | unexplained |
| C00836056 | R.E.D PAC | O | 1,546,664 | 0 | 1,576,431 | B | 29,767 | 1.92% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 29,767 | 0 | D8 organizations on line 15 | explained |
| C00813436 | PUBLIC WISE PAC | V | 20,000 | 25,000 | 49,102 | B | 29,102 | 145.51% | 0 | 0 | 29,102 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00852699 | RIC HOLDEN FOR MONTANA | H | 9,927 | 11,940 | 39,009 | B | 29,082 | 292.96% | 0 | 300 | 27,069 | 0 | 0 | 0 | 5,000 | 0 | -3,287 | D3 other line | explained |
| C00866707 | CONSERVATIVE PAC | V | 26,901 | 55,901 | 55,901 | B | 29,000 | 107.80% | 0 | 0 | 30,000 | 0 | 0 | 0 | 0 | 0 | -1,000 | D3 other line | explained |
| C00851774 | AMERICAN DREAM DEFENDERS PAC | V | 0 | 0 | 28,755 | B | 28,755 |  | 0 | 0 | 28,755 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00885012 | BAD ASS WOMEN COMMUNITY | V | 531 | 27,033 | 29,033 | B | 28,502 | 5367.09% | 0 | 0 | 29,033 | 0 | 0 | 0 | 0 | 0 | -531 | D3 other line | explained |
| C00607374 | ELBERT GUILLORY'S AMERICA | W | 475,454 | 497,662 | 503,750 | B | 28,296 | 5.95% | -3,457 | 2,074 | 31,788 | 0 | 0 | 0 | 0 | 0 | -5,566 | D3 other line | explained |
| C00656686 | DISTRICTS FOR DEMOCRACY | V | 94,296 | 115,731 | 122,231 | B | 27,935 | 29.62% | -2,815 | 150 | 30,750 | 0 | 0 | 0 | 0 | 0 | -2,965 | D3 other line | explained |
| C90018045 | UNITED WE DREAM ACTION | I |  | 27,890 | 27,890 | B | 27,890 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 27,890 | none | no FEC figure |
| C00406124 | HANSON PROFESSIONAL SERVICES INC PAC | Q | 14,200 | 41,200 | 41,200 | B | 27,000 | 190.14% | 0 | 14,250 | 0 | 0 | 0 | 0 | 0 | 0 | 12,750 | D2 duplicates | unexplained |
| C00878264 | CONSERVATIVE FUTURE FUND | O | 1,588,000 | 85,000 | 1,614,342 | B | 26,342 | 1.66% | 0 | 0 | 0 | 26,342 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | explained |
| C00804179 | COINBASE, INC. INNOVATION PAC (COINBASE INNOVATION PAC) | Q | 161,413 | 187,451 | 187,451 | B | 26,038 | 16.13% | 0 | 26,217 | 0 | 0 | 0 | 0 | 0 | 0 | -179 | D2 duplicates | explained |
| C00685693 | CASA IN ACTION PAC | O | 2,491,926 | 66,191 | 2,517,942 | B | 26,016 | 1.04% | 0 | 0 | 0 | 150,000 | 0 | 0 | 0 | 0 | -123,984 | D4 names a committee | explained |
| C00874354 | UNITY LAB PAC | V | 0 | 25,977 | 25,977 | B | 25,977 |  | 0 | 0 | 25,977 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00427435 | MAVERICK PAC USA | W | 104,267 | 121,099 | 129,599 | B | 25,332 | 24.30% | 0 | 0 | 25,433 | 0 | 0 | 0 | 0 | 0 | -101 | D3 other line | explained |
| C00889196 | SAVE CENTRAL NEW YORK PAC | O | 63,500 | 63,500 | 88,500 | B | 25,000 | 39.37% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25,000 | 0 | D8 organizations on line 15 | explained |
| C00873679 | TOGETHER FOR PROGRESS 2024 | O | 382,686 | 382,686 | 407,686 | B | 25,000 | 6.53% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25,000 | none | unexplained |
| C00216614 | DEMOCRATIC PARTY COMMITTEE ABROAD | Y | 1,075,168 | 1,100,050 | 1,100,050 | B | 24,882 | 2.31% | -11,160 | 57,166 | 0 | 0 | 0 | 0 | 0 | 0 | -32,284 | D2 duplicates | explained |
| C00846378 | MATT SHOEMAKER FOR CONGRESS | H | 9,950 | 34,718 | 34,718 | B | 24,768 | 248.92% | 0 | 525 | 0 | 0 | 0 | 0 | 24,768 | 0 | -525 | D7 own money | explained |
| C00836395 | ACTIONS SPEAK LOUDER THAN TWEETS PAC | V | 0 | 24,000 | 24,000 | B | 24,000 |  | 0 | 0 | 24,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00814483 | ELEVATING AMERICA | V | 0 | 0 | 23,896 | B | 23,896 |  | 0 | 0 | 23,896 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00408435 | SOCIETY OF INTERVENTIONAL RADIOLOGY POLITICAL ACTION COMMITTEE | Q | 82,955 | 106,330 | 106,330 | B | 23,375 | 28.18% | -1,000 | 24,375 | 0 | 0 | 0 | 0 | 0 | 0 | -1,000 | D2 duplicates | explained |
| C00472894 | ELECTING WOMEN DENVER | W | 264,438 | 287,386 | 287,386 | B | 22,948 | 8.68% | -2,000 | 2,000 | 25,000 | 0 | 0 | 0 | 0 | 0 | -4,052 | D3 other line | explained |
| C00784496 | LEAGUE FOR SPORTSMEN, LAW ENFORCEMENT AND DEFENSE (AKA THE LEAGUE) | W | 43,786 | 32,787 | 66,287 | B | 22,501 | 51.39% | -10,999 | 0 | 33,500 | 0 | 0 | 0 | 0 | 0 | -10,999 | D3 other line | explained |
| C00832238 | DEMOCRACY THROUGH VOTING | O | 85,173 | 107,134 | 107,134 | B | 21,961 | 25.78% | 0 | 9,101 | 0 | 0 | 0 | 0 | 0 | 0 | 12,860 | D2 duplicates | unexplained |
| C00840025 | SENSIBLE AMERICANS | V | 159,533 | 181,152 | 181,152 | B | 21,619 | 13.55% | -10,750 | 0 | 191,902 | 0 | 0 | 0 | 0 | 0 | -170,283 | D3 other line | explained |
| C00716720 | HICKENLOOPER FOR COLORADO | S | 720,094 | 739,733 | 741,333 | B | 21,239 | 2.95% | 18,909 | 108,497 | 0 | 0 | 0 | 0 | 0 | 0 | -87,258 | D2 duplicates | explained |
| C90022393 | FAITH VOTERS FOR GOOD | I |  | 21,112 | 21,112 | B | 21,112 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 21,112 | none | no FEC figure |
| C00768101 | MISSION DEMOCRACY PAC | N | 29,545 | 50,590 | 50,590 | B | 21,045 | 71.23% | -37,512 | 525 | 0 | 0 | 0 | 0 | 2,012 | 0 | 18,508 | D7 own money | unexplained |
| C00856492 | AMERICANS UNITED FOR LIBERTY AND TRUTH | V | 0 | 0 | 21,000 | B | 21,000 |  | 0 | 0 | 21,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00758078 | ASIAN AMERICAN FORWARD | W | 80,098 | 89,447 | 100,947 | B | 20,849 | 26.03% | 0 | 2,250 | 20,850 | 0 | 0 | 0 | 0 | 0 | -2,251 | D3 other line | explained |
| C00718197 | #WALKAWAY CAMPAIGN PAC | V | 3,171 | 23,920 | 23,920 | B | 20,749 | 654.34% | 0 | 0 | 22,770 | 0 | 0 | 0 | 0 | 0 | -2,021 | D3 other line | explained |
| C00823468 | AMERICA UPHELD | V | 39,000 | 44,500 | 59,500 | B | 20,500 | 52.56% | 0 | 0 | 20,500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00837849 | 1859 PAC | V | 25,000 | 45,500 | 45,500 | B | 20,500 | 82.00% | 0 | 0 | 25,500 | 0 | 0 | 0 | 0 | 0 | -5,000 | D3 other line | explained |
| C00799528 | PROTECT OUR KIDS PAC | V | 7,562 | 7,561 | 28,061 | B | 20,499 | 271.06% | 0 | 0 | 20,500 | 0 | 0 | 0 | 0 | 0 | -1 | D3 other line | explained |
| C00892257 | ONE COMMUNITY PAC | V | 5,000 | 25,000 | 25,000 | B | 20,000 | 400.00% | 0 | 0 | 20,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90022237 | BLUE HORIZON | I |  | 20,000 | 20,000 | B | 20,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20,000 | none | no FEC figure |
| C90022245 | REPRODUCTIVE FREEDOM FOR ALL | I |  | 0 | 20,000 | B | 20,000 |  | 0 | 0 | 0 | 20,000 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | no FEC figure |
| C00864280 | PEAY FOR CONGRESS | H | 197,800 | 217,636 | 217,636 | B | 19,836 | 10.03% | 0 | 4,100 | 0 | 0 | 0 | 0 | 21,336 | 0 | -5,600 | D7 own money | explained |
| C00801910 | FOOD AND WATER ACTION PAC | O | 1,000 | 19,000 | 20,697 | B | 19,697 | 1969.70% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,697 | 18,000 | D8 organizations on line 15 | unexplained |
| C00829549 | TEAMSTERS LOCAL 79 PAC FOR BETTER GOVERNMENT | N | 0 | 18,950 | 18,950 | B | 18,950 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 18,950 | none | unexplained |
| C00756841 | NEW DEAL AMERICA PAC | V | 0 | 17,921 | 17,921 | B | 17,921 |  | 0 | 0 | 17,921 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00834960 | LOYD FOR CONGRESS | H | 63,451 | 81,104 | 81,104 | B | 17,653 | 27.82% | 0 | 0 | 0 | 0 | 0 | 0 | 17,671 | 0 | -18 | D7 own money | explained |
| C00830224 | KENTUCKIANS FOR BALANCE | O | 36,000 | 13,500 | 53,500 | B | 17,500 | 48.61% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 17,500 | 0 | D8 organizations on line 15 | explained |
| C00804732 | CRYPTO INNOVATION | O | 0 | 0 | 16,102 | B | 16,102 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16,102 | 0 | D8 organizations on line 15 | explained |
| C00873539 | GEN Z TAKE OVER | V | 5,900 | 21,900 | 21,900 | B | 16,000 | 271.19% | 0 | 0 | 16,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00867291 | ARIZONANS FOR A SECURE AMERICA | O | 25,000 | 15,000 | 41,000 | B | 16,000 | 64.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16,000 | none | unexplained |
| C00301358 | BLUE CROSS AND BLUE SHIELD OF KANSAS CITY FEDERAL PAC | Q | 23,500 | 39,350 | 39,350 | B | 15,850 | 67.45% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15,850 | none | unexplained |
| C00866822 | MONTANA''S ELECTRIC COOPERATIVES PAC | N | 60,873 | 76,617 | 76,617 | B | 15,744 | 25.86% | 0 | 18,183 | 0 | 0 | 0 | 0 | 0 | 0 | -2,439 | D2 duplicates | explained |
| C00886721 | BEIGE RAINBOW PAC | V | 3,300 | 0 | 19,000 | B | 15,700 | 475.76% | 0 | 0 | 19,000 | 0 | 0 | 0 | 0 | 0 | -3,300 | D3 other line | explained |
| C00859868 | WES HOLDEN FOR CONGRESS | H | 21,388 | 37,072 | 37,072 | B | 15,684 | 73.33% | 0 | 0 | 0 | 0 | 0 | 0 | 15,685 | 0 | -1 | D7 own money | explained |
| C00298000 | MADISON PROJECT INC. | W | 473,740 | 472,740 | 489,345 | B | 15,605 | 3.29% | -1,000 | 4,017 | 16,605 | 0 | 0 | 0 | 0 | 0 | -5,017 | D3 other line | explained |
| C00668517 | BLACK AMERICANS MAKING AMERICA FIRST | O | 129,275 | 128,898 | 144,725 | B | 15,450 | 11.95% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15,450 | 0 | D8 organizations on line 15 | explained |
| C00877688 | CARLTON 4 US SENATE  | S | 6,620 | 21,917 | 21,917 | B | 15,297 | 231.08% | 0 | 0 | 0 | 0 | 0 | 0 | 18,303 | 0 | -3,006 | D7 own money | explained |
| C00868521 | SCHAEFER FOR US SENATE NV2024 | S |  | 0 | 15,128 | B | 15,128 |  | 0 | 0 | 15,128 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | no FEC figure |
| C00851303 | PATRICK BOHAN POLITICAL CAMPAIGN | H | 0 | 15,072 | 15,072 | B | 15,072 |  | 0 | 0 | 0 | 0 | 0 | 0 | 15,072 | 0 | 0 | D7 own money | explained |
| C00884155 | RIGHTLY PAC | V | 0 | 0 | 15,000 | B | 15,000 |  | 0 | 0 | 15,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00886192 | SOUTHERN STATES CONSERVATIVE FUND | V | 0 | 15,000 | 15,000 | B | 15,000 |  | 0 | 0 | 15,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00845578 | TOGETHER FUND | V | 0 | 15,000 | 15,000 | B | 15,000 |  | 0 | 0 | 15,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00748475 | CONSERVATIVE OUTSIDER PAC INC | O | 9,400 | 9,400 | 24,175 | B | 14,775 | 157.18% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14,775 | 0 | D8 organizations on line 15 | explained |
| C90022252 | 60 PLUS, ANUZIS | I |  | 14,550 | 14,550 | B | 14,550 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14,550 | none | no FEC figure |
| C00750901 | SIGMAPAC1914 | V | 13,428 | 12,924 | 27,924 | B | 14,496 | 107.95% | -500 | 0 | 15,000 | 0 | 0 | 0 | 0 | 0 | -504 | D3 other line | explained |
| C90022617 | CALIFORNIA CONFERENCE OF CARPENTERS | I |  | 0 | 14,250 | B | 14,250 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14,250 | none | no FEC figure |
| C00687491 | PLANNED PARENTHOOD ADVOCACY PROJECT LOS ANGELES COUNTY ACTION FUND | O | 880,370 | 883,845 | 894,145 | B | 13,775 | 1.56% | -500 | 0 | 0 | 0 | 0 | 0 | 0 | 10,300 | 3,475 | D8 organizations on line 15 | explained |
| C00775601 | PRESSURE PAC | V | 950 | 14,650 | 14,650 | B | 13,700 | 1442.11% | -6,828 | 0 | 20,603 | 0 | 0 | 0 | 0 | 0 | -6,903 | D3 other line | explained |
| C00875963 | NEW GEN 47 | V | 0 | 12,660 | 13,660 | B | 13,660 |  | 0 | 0 | 13,660 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00879197 | HEITHOLD FOR CONGRESS | H | 4,660 | 18,022 | 18,267 | B | 13,607 | 292.01% | 0 | 0 | 0 | 0 | 0 | 0 | 10,930 | 0 | 2,677 | D7 own money | unexplained |
| C00835025 | VICE MAYOR DAYSOG FOR US CONGRESS | H | 2,657 | 16,161 | 16,161 | B | 13,504 | 508.14% | 0 | 0 | 0 | 0 | 0 | 0 | 14,503 | 0 | -999 | D7 own money | explained |
| C00785733 | MARK MEUSER FOR U.S. SENATE | S | 0 | 13,400 | 13,400 | B | 13,400 |  | 0 | 0 | 0 | 0 | 0 | 0 | 13,400 | 0 | 0 | D7 own money | explained |
| C00765982 | STAND FOR AMERICA PAC | Q | 1,277,754 | 1,290,908 | 1,290,908 | B | 13,154 | 1.03% | -1,000 | -10,947 | 0 | 0 | 0 | 0 | 0 | 0 | 24,101 | none | unexplained |
| C00820225 | DOCTORS FOR FERTILITY PAC | W | 71,703 | 72,803 | 84,803 | B | 13,100 | 18.27% | 0 | 0 | 13,100 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00849364 | ADVANCE PAC | V | 0 | 0 | 13,096 | B | 13,096 |  | 0 | 0 | 13,096 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00823559 | POWER ON PAC | V | 500 | 500 | 13,500 | B | 13,000 | 2600.00% | 0 | 0 | 13,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00626861 | WFP IE COMMITTEE | O | 7,291 | 7,286 | 20,286 | B | 12,995 | 178.22% | 0 | 1,011 | 0 | 0 | 0 | 0 | 0 | 11,984 | 0 | D8 organizations on line 15 | explained |
| C00780965 | MEET IN THE MIDDLE FOR AMERICA | O | 0 | 12,922 | 12,922 | B | 12,922 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12,922 | none | unexplained |
| C00833657 | FRIENDS OF NIKKI SNYDER | H | 139,688 | 152,439 | 152,439 | B | 12,751 | 9.13% | -25,451 | 14,200 | 0 | 0 | 0 | 0 | 38,202 | 0 | -39,651 | D7 own money | explained |
| C00456335 | PHYSICIANS MUTUAL INSURANCE COMPANY PAC | Q | 20,450 | 33,000 | 33,000 | B | 12,550 | 61.37% | 0 | 12,550 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | D2 duplicates | explained |
| C00790964 | MANUEL CASANOVA FOR CONGRESS 2022 | H | 0 | 12,500 | 12,500 | B | 12,500 |  | 0 | 0 | 0 | 0 | 0 | 0 | 12,500 | 0 | 0 | D7 own money | explained |
| C00874966 | US CHRISTIAN CITIZENS PAC | Q | 1,000 | 1,000 | 13,500 | B | 12,500 | 1250.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12,500 | 0 | D8 organizations on line 15 | explained |
| C00763375 | AMERICAN LEBANESE POLICY INSTITUTE PAC - ALPI PAC | N | 5,500 | 5,500 | 18,000 | B | 12,500 | 227.27% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12,500 | 0 | D8 organizations on line 15 | explained |
| C00767079 | BETTER OHIO PAC | V | 21,826 | 23,569 | 34,266 | B | 12,440 | 56.99% | -5,315 | 0 | 17,765 | 0 | 0 | 0 | 0 | 0 | -5,325 | D3 other line | explained |
| C00389601 | ASSOCIATION OF MARYLAND PILOTS PAC | Q | 0 | 11,976 | 11,976 | B | 11,976 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11,976 | none | unexplained |
| C00875609 | CAVALRY PAC | V | 13,870 | 23,366 | 25,366 | B | 11,496 | 82.88% | 0 | 227 | 12,000 | 0 | 0 | 0 | 0 | 0 | -731 | D3 other line | explained |
| C00837609 | COSTELLO FOR SENATE | S | 19,692 | 31,175 | 31,175 | B | 11,483 | 58.31% | 0 | 0 | 0 | 0 | 0 | 0 | 11,683 | 0 | -200 | D7 own money | explained |
| C00822726 | ADOPT A DEMOCRAT | V | 0 | 11,000 | 11,000 | B | 11,000 |  | 0 | 0 | 11,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00844688 | GARCIA FOR WA | S | 565,668 | 576,297 | 576,297 | B | 10,629 | 1.88% | -5,300 | 71,575 | 0 | 0 | 0 | 0 | 21,035 | 0 | -81,981 | D2 duplicates | explained |
| C00717553 | FEMS FOR DEMS PAC | N | 32,897 | 43,477 | 43,477 | B | 10,580 | 32.16% | 0 | 1,225 | 0 | 0 | 0 | 0 | 0 | 0 | 9,355 | D2 duplicates | unexplained |
| C00877845 | GRAYPAC | V | 216,149 | 226,353 | 226,353 | B | 10,204 | 4.72% | -200 | 200 | 10,500 | 0 | 0 | 0 | 0 | 0 | -496 | D3 other line | explained |
| C00322362 | RHODE ISLAND BROTHERHOOD OF CORRECTIONAL OFFICERS | Q | 0 | 10,142 | 10,142 | B | 10,142 |  | -558 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10,142 | none | unexplained |
| C00783332 | DISABLED VETERANS PAC | V | 1,200 | 11,235 | 11,235 | B | 10,035 | 836.25% | 0 | 0 | 10,035 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00585687 | ELECTING WOMEN BAY AREA PAC | W | 413,555 | 412,555 | 423,555 | B | 10,000 | 2.42% | -10,000 | 0 | 20,000 | 0 | 0 | 0 | 0 | 0 | -10,000 | D3 other line | explained |
| C00822288 | NEW COALITION PAC | O | 2,355 | 12,355 | 12,355 | B | 10,000 | 424.63% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10,000 | none | unexplained |
| C00877928 | FRISCH VICTORY FUND | N | 131,800 | 141,800 | 141,800 | B | 10,000 | 7.59% | -10,000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10,000 | none | unexplained |
| C00844787 | GOOD PARTY PAC | V | 12,656 | 22,655 | 22,655 | B | 9,999 | 79.01% | 0 | 0 | 10,000 | 0 | 0 | 0 | 0 | 0 | -1 | D3 other line | explained |
| C00870980 | FRIENDS OF NCR | V | 52,560 | 62,355 | 62,355 | B | 9,795 | 18.64% | -195 | 0 | 10,000 | 0 | 0 | 0 | 0 | 0 | -205 | D3 other line | explained |
| C00880849 | VIRGINIANS AGAINST SEXUAL ASSAULT PAC | O | 2,500 | 12,000 | 12,000 | B | 9,500 | 380.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9,500 | none | unexplained |
| C00830422 | VOTE GREG WHEELER | H | 141,897 | 151,138 | 151,138 | B | 9,241 | 6.51% | -17,525 | 6,600 | 0 | 0 | 0 | 0 | 33,479 | 0 | -30,838 | D7 own money | explained |
| C00879601 | TEXANS FIGHTING CORRUPTION FEDERAL PAC | V | 3,160 | 11,826 | 11,826 | B | 8,666 | 274.24% | -20 | 0 | 8,686 | 0 | 0 | 0 | 0 | 0 | -20 | D3 other line | explained |
| C00851881 | VOTEDOWN PAC | V | 10,858 | 15,576 | 19,483 | B | 8,625 | 79.44% | 0 | 0 | 8,626 | 0 | 0 | 0 | 0 | 0 | -1 | D3 other line | explained |
| C00827824 | TURNOUT 2022 | O | 9,000 | 9,000 | 17,000 | B | 8,000 | 88.89% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8,000 | none | unexplained |
| C00889188 | COMMON SENSE MARYLAND | O | 183,540 | 189,240 | 191,480 | B | 7,940 | 4.33% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7,940 | none | unexplained |
| C00841395 | PERIDOT OPERATIONS INC- DR. ULOMA S. KAMA EKPETE-H4RI01315. | H | 7,325 | 14,650 | 14,650 | B | 7,325 | 100.00% | 0 | 0 | 0 | 0 | 0 | 0 | 14,650 | 0 | -7,325 | D7 own money | explained |
| C00811307 | TEAM MONICA VICTORY | N | 620,402 | 627,697 | 627,697 | B | 7,295 | 1.18% | 0 | 21,141 | 0 | 0 | 0 | 0 | 0 | 0 | -13,846 | D2 duplicates | explained |
| C00741041 | END THE OCCUPATION | Q | 21,420 | 28,195 | 28,695 | B | 7,275 | 33.96% | -1,000 | 0 | 0 | 0 | 0 | 0 | 0 | 500 | 6,775 | D8 organizations on line 15 | unexplained |
| C00248948 | PEOPLE HELPING PEOPLE | Q | 40,000 | 47,080 | 47,080 | B | 7,080 | 17.70% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7,080 | none | unexplained |
| C00778548 | COMPLETE PARACHUTE SOLUTIONS INC POLITICAL ACTION COMMITTEE 'CPS PAC' | N | 12,294 | 19,080 | 19,080 | B | 6,786 | 55.20% | 0 | 1,560 | 0 | 0 | 0 | 0 | 0 | 0 | 5,226 | D2 duplicates | unexplained |
| C00001214 | TEXAS MEDICAL ASSOCIATION POLITICAL ACTION COMMITTEE | Q | 60,250 | 66,945 | 66,945 | B | 6,695 | 11.11% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6,695 | none | unexplained |
| C00199703 | GLAXOSMITHKLINE LLC PAC (GSK PAC) | Q | 308,647 | 315,308 | 315,308 | B | 6,661 | 2.16% | 0 | 8,267 | 0 | 0 | 0 | 0 | 0 | 0 | -1,606 | D2 duplicates | explained |
| C00117911 | NORTH DAKOTA BANKERS ASSOCIATION POLITICAL ACTION COMMITTEE | Q | 18,170 | 24,780 | 24,780 | B | 6,610 | 36.38% | 0 | 6,590 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | D2 duplicates | explained |
| C00887034 | RACHEL FIORI PRESIDENTIAL CANDIDATE | P | 11,068 | 17,674 | 17,674 | B | 6,606 | 59.69% | 0 | 5,007 | 0 | 0 | 0 | 0 | 0 | 0 | 1,600 | D2 duplicates | unexplained |
| C00762161 | RETIRE HIM | V | 0 | 6,476 | 6,476 | B | 6,476 |  | 0 | 0 | 6,476 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00875369 | TOGETHER! | V | 5,000 | 10,000 | 11,439 | B | 6,439 | 128.78% | 0 | 0 | 6,439 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00862862 | JUST PAC | V | 48,746 | 52,171 | 55,171 | B | 6,425 | 13.18% | 0 | 0 | 7,041 | 0 | 0 | 0 | 0 | 0 | -616 | D3 other line | explained |
| C00770511 | TZEDEK PAC | W | 3,000 | 3,000 | 9,394 | B | 6,394 | 213.13% | 0 | 0 | 6,394 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00780619 | BRADY DUKE FOR CONGRESS | H | 0 | 6,369 | 6,369 | B | 6,369 |  | 6,369 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6,369 | none | unexplained |
| C00736348 | PEOPLE FOR CHARLES HUGHES | H | 0 | 6,293 | 6,293 | B | 6,293 |  | 0 | 0 | 0 | 0 | 0 | 0 | 6,293 | 0 | 0 | D7 own money | explained |
| C00891440 | NORTHERN CALIFORNIA CARPENTERS REGIONAL COUNCIL POWER PAC | O | 204,830 | 0 | 211,117 | B | 6,287 | 3.07% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6,287 | 0 | D8 organizations on line 15 | explained |
| C00573519 | THINK BIG AMERICA PAC | Q | 255,260 | 261,515 | 261,515 | B | 6,255 | 2.45% | 0 | 11,593 | 0 | 0 | 0 | 0 | 0 | 0 | -5,338 | D2 duplicates | explained |
| C00831974 | THE REAL TEXAS PAC | V | 111,784 | 117,869 | 117,869 | B | 6,085 | 5.44% | -5,149 | 3,657 | 28,256 | 0 | 0 | 0 | 0 | 0 | -25,828 | D3 other line | explained |
| C00784983 | TAMIE WILSON FOR US | H | 534,569 | 538,136 | 540,636 | B | 6,067 | 1.13% | -2,500 | 6,574 | 0 | 0 | 0 | 0 | 0 | 0 | -507 | D2 duplicates | explained |
| C00846162 | NINETY3 PAC | V | 333,186 | 306,635 | 339,226 | B | 6,040 | 1.81% | -34,650 | 17,000 | 44,591 | 0 | 0 | 0 | 0 | 0 | -55,551 | D3 other line | explained |
| C00215699 | CHRISTOPHER SHAYS FOR CONGRESS COMMITTEE | H | 0 | 5,951 | 5,951 | B | 5,951 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5,951 | none | unexplained |
| C00494997 | DOWNTOWN FOR DEMOCRACY | O | 275 | 1,901 | 6,176 | B | 5,901 | 2145.82% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,275 | 1,626 | D8 organizations on line 15 | unexplained |
| C00853200 | SHIRLEY FOR NEW JERSEY | H | 33,717 | 39,597 | 39,597 | B | 5,880 | 17.44% | 0 | 50 | 0 | 0 | 0 | 0 | 0 | 0 | 5,830 | D2 duplicates | unexplained |
| C00867150 | COMMITTEE TO ELECT MICHAEL KRIPCHAK | H | 53,582 | 59,331 | 59,331 | B | 5,749 | 10.73% | 0 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 | 4,749 | D2 duplicates | unexplained |
| C00803197 | SUMMIT COUNTY PROGRESSIVE DEMOCRATS FEDERAL PAC | N | 14,535 | 20,250 | 20,250 | B | 5,715 | 39.32% | 0 | 4,750 | 0 | 0 | 0 | 0 | 0 | 0 | 965 | D2 duplicates | unexplained |
| C00734491 | MOWERS FOR CONGRESS | H | 0 | 5,700 | 5,700 | B | 5,700 |  | 5,700 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5,700 | none | unexplained |
| C00874321 | STAMPER FOR CONGRESS | H | 1,200 | 6,770 | 6,770 | B | 5,570 | 464.17% | 0 | 0 | 0 | 0 | 0 | 0 | 5,570 | 0 | 0 | D7 own money | explained |
| C00836007 | THEIR FUTURE PAC | V | 102,547 | 107,546 | 108,046 | B | 5,499 | 5.36% | 0 | 0 | 5,500 | 0 | 0 | 0 | 0 | 0 | -1 | D3 other line | explained |
| C00712398 | FRIENDS OF MELANIE DARRIGO | H | 0 | 5,450 | 5,450 | B | 5,450 |  | 0 | 0 | 0 | 0 | 0 | 0 | 5,450 | 0 | 0 | D7 own money | explained |
| C90022146 | SEATTLE DSA | I |  | 5,400 | 5,400 | B | 5,400 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5,400 | none | no FEC figure |
| C00847210 | THE GREAT AMERICAN PAC | N | 8,622 | 14,005 | 14,005 | B | 5,383 | 62.44% | -1,000 | 6,676 | 0 | 0 | 0 | 0 | 0 | 0 | -1,293 | D2 duplicates | explained |
| C00864777 | KELLY IN CONGRESS 2024 | H | 39,423 | 44,749 | 44,749 | B | 5,326 | 13.51% | 0 | 0 | 0 | 0 | 0 | 0 | 5,326 | 0 | -0 | D7 own money | explained |
| C90020041 | EQUALITY FLORIDA ACTION INC. | I |  | 5,212 | 5,212 | B | 5,212 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5,212 | none | no FEC figure |
| C90018078 | NEW JERSEY CITIZEN ACTION | I |  | 0 | 5,000 | B | 5,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5,000 | none | no FEC figure |
| C00753327 | MORE PERFECT UNION PAC | W | 23,250 | 28,250 | 28,250 | B | 5,000 | 21.51% | -5,000 | 0 | 10,000 | 0 | 0 | 0 | 0 | 0 | -5,000 | D3 other line | explained |
| C00508200 | 1911 UNITED | O | 0 | -2,500 | 4,750 | B | 4,750 |  | -2,500 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,750 | none | unexplained |
| C00860486 | STOLL FOR CONGRESS | H | 0 | 4,745 | 4,745 | B | 4,745 |  | 0 | 0 | 0 | 0 | 0 | 0 | 4,745 | 0 | 0 | D7 own money | explained |
| C00548719 | MCKINNEY TEA PARTY | N | 14,846 | 13,646 | 19,501 | B | 4,655 | 31.36% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,655 | none | unexplained |
| C00833053 | SIGNORELLO FOR SENATE | S | 54,800 | 59,450 | 59,450 | B | 4,650 | 8.49% | -300 | 3,300 | 0 | 0 | 0 | 0 | 6,150 | 0 | -4,800 | D7 own money | explained |
| C00777276 | PATRIOTTAKES | V | 0 | 4,514 | 4,514 | B | 4,514 |  | 0 | 0 | 4,514 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00818591 | GRASSROOTS AMERICA PAC | V | 50,000 | 50,000 | 54,506 | B | 4,506 | 9.01% | 0 | 0 | 4,506 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00870170 | LEHIGH VALLEY FOR ALL PAC | N | 9,280 | 12,780 | 13,780 | B | 4,500 | 48.49% | 0 | 3,500 | 0 | 0 | 0 | 0 | 0 | 0 | 1,000 | D2 duplicates | unexplained |
| C00766220 | MORE BLUE | W | 98,181 | 102,681 | 102,681 | B | 4,500 | 4.58% | 0 | 2,100 | 4,500 | 0 | 0 | 0 | 0 | 0 | -2,100 | D3 other line | explained |
| C00858811 | PHIL HEIMLICH FOR CONGRESS | H | 51,803 | 56,287 | 56,287 | B | 4,484 | 8.66% | 0 | 5 | 0 | 0 | 0 | 0 | 4,500 | 0 | -21 | D7 own money | explained |
| C00856435 | THE FUTURE - TODAY & TOMORROW | O | 25,917 | 20,395 | 30,395 | B | 4,478 | 17.28% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,478 | none | unexplained |
| C00887042 | WORKERS EN ACCION PAC | O | 61,500 | 61,500 | 65,966 | B | 4,466 | 7.26% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,466 | 0 | D8 organizations on line 15 | explained |
| C00710871 | CHRIS BELL FOR SENATE | S | 0 | 4,150 | 4,150 | B | 4,150 |  | -10,400 | 0 | 0 | 0 | 0 | 0 | 14,550 | 0 | -10,400 | D7 own money | explained |
| C00763359 | DIRT ROAD DEMOCRATS PAC | V | 143,151 | 147,298 | 147,298 | B | 4,147 | 2.90% | -200 | 1,940 | 5,000 | 0 | 0 | 0 | 0 | 0 | -2,793 | D3 other line | explained |
| C00676247 | SUBURBAN VIRGINIA REPUBLICAN COALITION (SUV GOP) | V | 64,563 | 63,295 | 68,645 | B | 4,082 | 6.32% | -1,250 | 1,000 | 5,350 | 0 | 0 | 0 | 0 | 0 | -2,268 | D3 other line | explained |
| C00762419 | TURNOUT DEMOCRATS | V | 0 | 4,030 | 4,030 | B | 4,030 |  | 0 | 0 | 4,030 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00872754 | CHERYL RILEY FOR CONGRESS | H | 2,163 | 6,179 | 6,179 | B | 4,016 | 185.65% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,016 | none | unexplained |
| C00865170 | TOM FOR OHIO | H | 0 | 4,000 | 4,000 | B | 4,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 4,000 | 0 | 0 | D7 own money | explained |
| C00656850 | ELECTING WOMEN NEW MEXICO | V | 28,000 | 32,000 | 32,000 | B | 4,000 | 14.29% | 0 | 0 | 4,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00793000 | EXPAND LIBERTY PAC | V | 250 | 250 | 4,208 | B | 3,958 | 1583.20% | 0 | 0 | 3,958 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00662148 | BIKERS FOR AMERICA | V | 200 | 200 | 4,143 | B | 3,943 | 1971.50% | 0 | 0 | 3,943 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00784074 | BEN SAMUELS FOR CONGRESS | H | 0 | 3,936 | 3,936 | B | 3,936 |  | 1,036 | 2,900 | 0 | 0 | 0 | 0 | 0 | 0 | 1,036 | D2 duplicates | unexplained |
| C00388157 | AMERICAN COMPOSITES MANUFACTURERS ASSOCIATION POLITICAL ACTION COMMITTEE | Q | 5,250 | 8,996 | 8,996 | B | 3,746 | 71.34% | 0 | 1,808 | 0 | 0 | 0 | 0 | 0 | 0 | 1,938 | D2 duplicates | unexplained |
| C00836866 | VOTERS DESERVE BETTER | O | 33,891 | 33,499 | 37,597 | B | 3,706 | 10.93% | 0 | 2,031 | 0 | 0 | 0 | 0 | 0 | 0 | 1,675 | D2 duplicates | unexplained |
| C00859140 | COMMITTEE TO ELECT MISSI HESKETH FOR CONGRESS | H | 7,335 | 7,935 | 11,035 | B | 3,700 | 50.44% | -50 | 1,650 | 0 | 0 | 0 | 0 | 0 | 0 | 2,050 | D2 duplicates | unexplained |
| C00873414 | COMMITTEE FOR AMERICAN RESILIENCE PAC | O | 3,118 | 5,817 | 6,817 | B | 3,699 | 118.66% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3,699 | none | unexplained |
| C00711358 | JOSE CASTILLO FOR CONGRESS | H | 6,089 | 9,607 | 9,607 | B | 3,518 | 57.78% | 0 | 0 | 0 | 0 | 0 | 0 | 3,707 | 0 | -189 | D7 own money | explained |
| C00635391 | RED TO BLUE CA | W | 15,710 | 19,218 | 13,718 | A | 3,508 | 22.33% | 0 | 0 | 3,512 | 0 | 0 | 0 | 0 | 0 | -4 | D3 other line | explained |
| C00866632 | FRIENDS OF MICHAEL BROWN FOR CONGRESS | H | 29,350 | 32,850 | 32,850 | B | 3,500 | 11.93% | 0 | 500 | 0 | 0 | 0 | 0 | 3,500 | 0 | -500 | D7 own money | explained |
| C90022609 | DRIFTLESS DADS | I |  | 3,447 | 3,447 | B | 3,447 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3,447 | none | no FEC figure |
| C90022435 | COBALT ADVOCATES  | I |  | 0 | 3,305 | B | 3,305 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3,305 | none | no FEC figure |
| C00794016 | WILD FOR PA VICTORY FUND | N | 282,200 | 285,500 | 285,500 | B | 3,300 | 1.17% | 0 | 3,300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | D2 duplicates | explained |
| C00786566 | NICOLE LOPEZ FOR CONGRESS | H | 3,250 | 6,531 | 6,531 | B | 3,281 | 100.95% | 0 | 0 | 0 | 0 | 0 | 0 | 3,281 | 0 | 0 | D7 own money | explained |
| C00843292 | PUBLIUS PAC | V | 8,479 | 11,714 | 11,714 | B | 3,235 | 38.15% | 0 | 0 | 5,000 | 0 | 0 | 0 | 0 | 0 | -1,765 | D3 other line | explained |
| C00859900 | BOB KING FOR TEXAS-21 | H | 54,284 | 57,512 | 57,512 | B | 3,228 | 5.95% | 0 | 0 | 0 | 0 | 0 | 0 | 3,229 | 0 | -1 | D7 own money | explained |
| C00854737 | ALLIES OF THOMAS E DAVIS FOR CONGRESS | H | 3,616 | 6,801 | 6,801 | B | 3,185 | 88.08% | 0 | 0 | 0 | 0 | 0 | 0 | 4,472 | 0 | -1,287 | D7 own money | explained |
| C00799502 | DAUGHTERS DEFEND DEMOCRACY | V | 0 | 3,125 | 3,125 | B | 3,125 |  | 0 | 0 | 3,125 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00172858 | NEBRASKA CREDIT UNION LEAGUE POLITICAL ACTION COMMITTEE--(NCULPAC) | Q | 23,536 | 26,619 | 26,619 | B | 3,083 | 13.10% | 0 | 2,701 | 0 | 0 | 0 | 0 | 0 | 0 | 382 | D2 duplicates | unexplained |
| C00625145 | CRES PAC | W | 11,500 | 11,500 | 14,500 | B | 3,000 | 26.09% | 0 | 0 | 3,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00848416 | PENNSYLVANIA LEADERSHIP ALLIANCE | V | 31,250 | 31,250 | 34,250 | B | 3,000 | 9.60% | 0 | 2,500 | 3,000 | 0 | 0 | 0 | 0 | 0 | -2,500 | D3 other line | explained |
| C00781252 | KARA HAHN FOR CONGRESS | H | 0 | 2,900 | 2,900 | B | 2,900 |  | 2,900 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,900 | none | unexplained |
| C00646364 | LOCAL MAJORITY | V | 0 | 2,900 | 2,900 | B | 2,900 |  | 0 | 0 | 2,900 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C90023136 | ROSE MARY HUTCHINSON | I |  | 2,824 | 2,824 | B | 2,824 |  | 0 | 2,205 | 0 | 0 | 0 | 0 | 0 | 0 | 619 | D2 duplicates | no FEC figure |
| C00724237 | SHARICE DAVIDS VICTORY FUND 2024 | N | 140,751 | 93,247 | 143,564 | B | 2,813 | 2.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,813 | none | unexplained |
| C90022666 | YEAGER, THOMAS FREDERICK | I |  | 410 | 2,778 | B | 2,778 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,778 | none | no FEC figure |
| C00336131 | INTELLECTUAL PROPERTY OWNERS ASSOCIATION POLITICAL ACTION FUND | N | 4,250 | 7,000 | 7,000 | B | 2,750 | 64.71% | 0 | 500 | 0 | 0 | 0 | 0 | 0 | 0 | 2,250 | D2 duplicates | unexplained |
| C00432815 | LOCAL 399 INTERNATIONAL UNION OF OPERATING ENGINEERS FEDERAL PAC (LOCAL 399 IUOE FED PAC) | N | 38,329 | 41,045 | 41,045 | B | 2,716 | 7.09% | 0 | 2,010 | 0 | 0 | 0 | 0 | 0 | 0 | 706 | D2 duplicates | unexplained |
| C00800227 | DC STATEHOOD PAC | V | 28,900 | 31,543 | 31,543 | B | 2,643 | 9.15% | 0 | 25 | 3,145 | 0 | 0 | 0 | 0 | 0 | -527 | D3 other line | explained |
| C90023003 | HERR, STEVEN | I |  | 2,514 | 2,514 | B | 2,514 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,514 | none | no FEC figure |
| C00762062 | MENTAL HEALTH PAC | V | 67,253 | 68,253 | 69,753 | B | 2,500 | 3.72% | 0 | 0 | 2,500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00872994 | DR. MIKE KATZ FOR UNITED STATES SENATE | S | 0 | 2,500 | 2,500 | B | 2,500 |  | 0 | 0 | 0 | 0 | 0 | 0 | 2,500 | 0 | 0 | D7 own money | explained |
| C00350884 | RESOLUTE FOREST PRODUCTS INC. POLITICAL ACTION COMMITTEE AKA DOMTAR PAC | Q | 92,658 | 95,133 | 95,133 | B | 2,475 | 2.67% | 3,000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,475 | none | unexplained |
| C00839191 | ALL IN TO WIN VIRGINIA | V | 0 | 2,406 | 2,406 | B | 2,406 |  | 0 | 0 | 2,406 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00610956 | MEMORIALHEALTHPAC | Q | 132,363 | 134,761 | 134,761 | B | 2,398 | 1.81% | -2,500 | 830 | 0 | 0 | 0 | 0 | 0 | 0 | 1,568 | D2 duplicates | unexplained |
| C00834622 | MOTHERS FOR DEMOCRACY ACTION PAC | V | 18,650 | 17,650 | 20,950 | B | 2,300 | 12.33% | -1,000 | 0 | 3,300 | 0 | 0 | 0 | 0 | 0 | -1,000 | D3 other line | explained |
| C00648246 | SPECIALIZED MEDICINE AND RESPONSIBLE TREATMENT PAC | V | 169 | 384 | 2,384 | B | 2,215 | 1312.57% | 0 | 0 | 2,192 | 0 | 0 | 0 | 0 | 23 | 0 | D3 other line | explained |
| C00874776 | DR PETER W SHERRILL FOR US CONGRESS  | H | 1,100 | 3,300 | 3,300 | B | 2,200 | 200.00% | 0 | 0 | 0 | 0 | 0 | 0 | 2,300 | 0 | -100 | D7 own money | explained |
| C00869040 | BLUEVOTE.ORG | O | 2,000 | 4,100 | 4,100 | B | 2,100 | 105.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,100 | none | unexplained |
| C00833459 | FREEMAN FOR CONGRESS | H | 9,742 | 11,784 | 11,784 | B | 2,042 | 20.96% | 0 | 0 | 0 | 0 | 0 | 0 | 2,690 | 0 | -648 | D7 own money | explained |
| C00871228 | NATIONAL POLITICAL INDEPENDENCE CONVENTION, INC. | O | 0 | 2,022 | 2,022 | B | 2,022 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,022 | none | unexplained |
| C00767541 | DEMOCRATIC CLUB AT CEDAR CREST | N | 985 | 3,000 | 3,000 | B | 2,015 | 204.57% | 0 | 1,250 | 0 | 0 | 0 | 0 | 0 | 0 | 765 | D2 duplicates | unexplained |
| C00784512 | COALITION FOR A BETTER FUTURE | V | 2,500 | 2,500 | 4,500 | B | 2,000 | 80.00% | 0 | 0 | 2,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00765198 | LEADING PEOPLE FORWARD PAC | Q | 52,500 | 54,500 | 54,500 | B | 2,000 | 3.81% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,000 | none | unexplained |
| C00850214 | EDWIN STICKLE FOR CONGRESS | H | 0 | 2,000 | 2,000 | B | 2,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 2,000 | 0 | 0 | D7 own money | explained |
| C00758102 | MOVE AHEAD USA | O | 240 | 2,240 | 2,240 | B | 2,000 | 832.87% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2,000 | none | unexplained |
| C00517235 | TURQUOISE PAC | Q | 137,616 | 50,415 | 139,615 | B | 1,999 | 1.45% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,999 | none | unexplained |
| C00415745 | HACKETT FOR SENATE | S | 0 | 1,998 | 1,998 | B | 1,998 |  | 0 | 0 | 0 | 0 | 0 | 0 | 1,998 | 0 | 0 | D7 own money | explained |
| C00890624 | NGBPAC | V | 1,250 | 1,250 | 3,188 | B | 1,938 | 155.04% | 0 | 0 | 1,938 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00864439 | JOSHUA JAMES FOR TENNESSEE | H | 2,800 | 3,690 | 4,690 | B | 1,890 | 67.50% | 0 | 0 | 0 | 0 | 0 | 0 | 1,890 | 0 | 0 | D7 own money | explained |
| C00838243 | TIM SANCHEZ FOR CONGRESS | H | 78,825 | 80,680 | 80,680 | B | 1,855 | 2.35% | 0 | 500 | 0 | 0 | 0 | 0 | 2,280 | 0 | -925 | D7 own money | explained |
| C90014580 | 350.ORG ACTION FUND | I |  | 1,850 | 1,850 | B | 1,850 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,850 | none | no FEC figure |
| C00825471 | MAGAZINER VICTORY FUND | N | 500 | 2,250 | 2,250 | B | 1,750 | 350.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,750 | none | unexplained |
| C00650655 | MICHAEL KOTICK FOR CONGRESS | H | 0 | 1,750 | 1,750 | B | 1,750 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,750 | none | unexplained |
| C90022682 | SISTERHOOD 2024 | I |  | 1,673 | 1,673 | B | 1,673 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,673 | none | no FEC figure |
| C00852491 | TOM HERMAN FOR CONGRESS | H | 3,400 | 5,042 | 5,042 | B | 1,642 | 48.29% | 0 | 0 | 0 | 0 | 0 | 0 | 1,642 | 0 | 0 | D7 own money | explained |
| C00814855 | GROUND GAME PAC | V | 900 | 2,500 | 2,500 | B | 1,600 | 177.78% | 0 | 0 | 1,600 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00842401 | ADVANCE THE ELECTORATE PAC | V | 22,761 | 23,761 | 24,269 | B | 1,508 | 6.63% | 0 | 300 | 1,508 | 0 | 0 | 0 | 0 | 0 | -300 | D3 other line | explained |
| C00684175 | STAUBER VICTORY FUND | N | 121,800 | 121,800 | 123,300 | B | 1,500 | 1.23% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,500 | none | unexplained |
| C00866772 | ILLINOIS MUSLIM POLITICAL ACTION COMMITTEE | V | 28,025 | 28,025 | 29,525 | B | 1,500 | 5.35% | 0 | 0 | 1,500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00807263 | MARGARITA MARIA CARRANZA 4 CONGRESS | H | 0 | 1,500 | 1,500 | B | 1,500 |  | 0 | 0 | 0 | 0 | 0 | 0 | 1,500 | 0 | 0 | D7 own money | explained |
| C90022708 | FARNAM, JAMES B. | I |  | 1,500 | 1,500 | B | 1,500 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,500 | none | no FEC figure |
| C00887612 | GOD SUPER PAC | O | 4,171 | 0 | 5,671 | B | 1,500 | 35.95% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,500 | none | unexplained |
| C00876508 | ROGERS FOR US HOUSE OF REPRESNTATIVES #1 | H |  | 1,478 | 1,478 | B | 1,478 |  | 0 | 0 | 0 | 0 | 0 | 0 | 1,478 | 0 | 0 | D7 own money | no FEC figure |
| C00487827 | BLUE AMERICA PAC INDEPENDENT EXPENDITURE COMMITTEE | O | 2,521 | 2,020 | 3,999 | B | 1,478 | 58.63% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,478 | 0 | D8 organizations on line 15 | explained |
| C00855403 | ALL ACTION PAC | V | 7,650 | 7,650 | 9,037 | B | 1,387 | 18.13% | 0 | 0 | 1,387 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00551382 | VOTECLIMATE.US PAC | O | 2,179 | 3,522 | 3,522 | B | 1,343 | 61.60% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,343 | none | unexplained |
| C00714881 | ADVANCED CAMPAIGN STRATEGIES PAC | V | 0 | 0 | 1,328 | B | 1,328 |  | 0 | 0 | 1,328 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00813006 | BETTER ACCESS TO CHIROPRACTIC PAC (CHIROPRACTIC FUTURE, LLC) | O | 37,980 | 979 | 39,303 | B | 1,323 | 3.48% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,323 | 0 | D8 organizations on line 15 | explained |
| C00873828 | THE 2024 VICTORY COMMITTEE | N | 83,742 | 85,030 | 85,030 | B | 1,288 | 1.54% | 0 | 500 | 0 | 0 | 0 | 0 | 0 | 0 | 788 | D2 duplicates | explained |
| C00852871 | ALAN GARZA FOR CONGRESS | H | 3,414 | 4,690 | 4,690 | B | 1,276 | 37.36% | 0 | 0 | 0 | 0 | 0 | 0 | 1,282 | 0 | -6 | D7 own money | explained |
| C00542902 | AMERICARISINGPAC.ORG | O | -1,810 | -550 | -550 | B | 1,260 | -69.61% | 0 | -300 | 0 | 0 | 0 | 0 | 0 | 0 | 1,560 | none | unexplained |
| C00806323 | DE LA CRUZ FOR CONGRESS | H | -2,250 | -1,000 | -1,000 | B | 1,250 | -55.56% | 0 | -500 | 0 | 0 | 0 | 0 | 0 | 0 | 1,750 | none | unexplained |
| C90022377 | WESTERN MONTANA DEMOCRATIC SOCIALISTS OF AMERICA | I |  | 1,182 | 1,182 | B | 1,182 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,182 | none | no FEC figure |
| C00117614 | FARMERS MUTUAL HAIL INS CO OF IOWA POLITICAL ACTION COMMITTEE (FMH PAC) | Q | 22,288 | 23,422 | 23,422 | B | 1,134 | 5.09% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,134 | none | unexplained |
| C00413401 | HAWAIIAN TELCOM COMMUNICATIONS INC FEDPAC | Q | 2,190 | 3,280 | 3,280 | B | 1,090 | 49.79% | 0 | 1,160 | 0 | 0 | 0 | 0 | 0 | 0 | -70 | D2 duplicates | explained |
| C00184382 | MODERN WOODMEN OF AMERICA POLITICAL ACTION COMMITTEE | Q | 2,050 | 3,100 | 3,100 | B | 1,050 | 51.22% | 0 | 1,550 | 0 | 0 | 0 | 0 | 0 | 0 | -500 | D2 duplicates | explained |
| C00848242 | ANDERSON FOR CONGRESS 2024 | H | 3,300 | 4,330 | 4,330 | B | 1,030 | 31.21% | 0 | 0 | 0 | 0 | 0 | 0 | 1,030 | 0 | 0 | D7 own money | explained |
| C00862896 | HART FOR CONGRESS | H | 13,860 | 14,860 | 14,860 | B | 1,000 | 7.22% | 0 | 0 | 0 | 0 | 0 | 0 | 1,000 | 0 | 0 | D7 own money | explained |
| C00856807 | TEXAS DEMOCRATIC ALLIANCE POLITICAL ACTION COMMITTEE | V | 37,000 | 37,000 | 38,000 | B | 1,000 | 2.70% | 0 | 0 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00843318 | SCOTT FOR UTAH | H | 1,300 | 2,300 | -1,549 | A | 1,000 | 76.92% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,000 | none | unexplained |
| C00745182 | IRANIAN AMERICANS FOR PEACE | O | 2,500 | 0 | 3,500 | B | 1,000 | 40.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,000 | none | unexplained |
| C00866137 | JOHN HENRY NEWMAN FOR CONGRESS | H | 750 | 1,750 | 1,750 | B | 1,000 | 133.33% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,000 | none | unexplained |
| C00865071 | SARAH FOR NJ | H | 13,300 | 14,300 | 14,300 | B | 1,000 | 7.52% | 0 | 0 | 0 | 0 | 0 | 0 | 1,000 | 0 | 0 | D7 own money | explained |
| C00821934 | MAGA.COM, INC | O | 0 | 0 | 1,000 | B | 1,000 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,000 | 0 | D8 organizations on line 15 | explained |
| C00804971 | RIGHT APPEAL PAC | V | 500 | 500 | 1,500 | B | 1,000 | 200.00% | 0 | 0 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00794669 | GEORGE WASHINGTON INITIATIVE ACTION FUND | O | 9,150 | 1,650 | 10,150 | B | 1,000 | 10.93% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1,000 | none | unexplained |
| C00876839 | DEVIN DAVIS FOR CONGRESS | H | 81,036 | 82,033 | 82,033 | B | 998 | 1.23% | 0 | 25 | 0 | 0 | 0 | 0 | 1,000 | 0 | -28 | D7 own money | explained |
| C00871517 | THE MOM VOTE PAC | V | 16,800 | 17,762 | 17,762 | B | 962 | 5.73% | -15,038 | 0 | 16,000 | 0 | 0 | 0 | 0 | 0 | -15,038 | D3 other line | explained |
| C00157958 | MISSOURI RIGHT TO LIFE FEDERAL POLITICAL ACTION COMMITTEE | Q | 1,745 | 2,675 | 2,675 | B | 930 | 53.32% | 0 | 932 | 0 | 0 | 0 | 0 | 0 | 0 | -2 | D2 duplicates | explained |
| C90023169 | GREG JERGESON | I |  | 912 | 912 | B | 912 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 912 | none | no FEC figure |
| C00626119 | COMMITTEE FOR WORKING FAMILIES, SPONSORED BY LABOR ORGANIZATIONS | O | 0 | 0 | 906 | B | 906 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 906 | 0 | D8 organizations on line 15 | explained |
| C00890889 | CONGRESS MAJORITY PAC | O | 83,315 | 84,215 | 84,215 | B | 900 | 1.08% | 0 | 1,200 | 0 | 0 | 0 | 0 | 0 | 0 | -300 | D2 duplicates | explained |
| C00872952 | DOUG BELL FOR PRESIDENT | P | 996 | 1,869 | 1,869 | B | 873 | 87.65% | 0 | 0 | 0 | 0 | 0 | 0 | 1,369 | 0 | -496 | D7 own money | explained |
| C00845172 | JAMES BUFORD FOR CONGRESS | H | 9,250 | 10,100 | 10,100 | B | 850 | 9.19% | 0 | 850 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | D2 duplicates | explained |
| C00857185 | WE COMPETE PAC | V | 750 | 0 | 1,600 | B | 850 | 113.33% | 0 | 0 | 850 | 750 | 0 | 0 | 0 | 0 | -750 | D3 other line | explained |
| C90019662 | NILC IMMIGRANT JUSTICE FUND | I |  | 783 | 783 | B | 783 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 783 | none | no FEC figure |
| C00103861 | SOUTH CAROLINA BANKERS POLITICAL ACTION COMMITTE | Q | 69,230 | 70,010 | 69,910 | A | 780 | 1.13% | 0 | 500 | 0 | 0 | 0 | 0 | 0 | 0 | 280 | D2 duplicates | explained |
| C00140772 | JOHN H HAAKE BRANCH 343 NATIONAL ASSOCIATION OF LETTER CARRIERS POLITICAL ACTION FUND | Q | 4,900 | 5,675 | 5,675 | B | 775 | 15.82% | 0 | 650 | 0 | 0 | 0 | 0 | 0 | 0 | 125 | D2 duplicates | unexplained |
| C00888487 | BLACK MEN VOTING | O | 0 | 259 | 759 | B | 759 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 743 | D8 organizations on line 15 | unexplained |
| C90018771 | FORFACT, LLC | I |  | 759 | 759 | B | 759 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 759 | none | no FEC figure |
| C00429241 | FRIENDS OF CMU | Q | 4,500 | 5,250 | 5,250 | B | 750 | 16.67% | 0 | 750 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | D2 duplicates | explained |
| C90010620 | VOTEVETS.ORG ACTION FUND | I |  | 750 | 750 | B | 750 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 750 | none | no FEC figure |
| C00846717 | DAVE BAKER FOR CONGRESS | H | 1,200 | 1,900 | 1,900 | B | 700 | 58.33% | 0 | 0 | 0 | 0 | 0 | 0 | 700 | 0 | 0 | D7 own money | explained |
| C00844050 | KEOUGH FOR SENATE | S | 20,053 | 20,752 | 20,752 | B | 699 | 3.49% | 0 | 0 | 0 | 0 | 0 | 0 | 700 | 0 | -1 | D7 own money | explained |
| C90023110 | JANICE NORLIN | I |  | 697 | 697 | B | 697 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 697 | none | no FEC figure |
| C00672634 | HERBERT LEE MD FOR CONGRESS | H | 0 | 601 | 601 | B | 601 |  | -2,699 | 0 | 0 | 0 | 0 | 0 | 3,300 | 0 | -2,699 | D7 own money | explained |
| C00850990 | LUDWIG VICTORY COMMITTEE | N | 1,250 | 1,850 | 1,850 | B | 600 | 48.00% | 0 | 0 | 0 | 0 | 0 | 0 | 600 | 0 | 0 | D7 own money | explained |
| C00652958 | MALEK FOR CONGRESS | H | 0 | 600 | 600 | B | 600 |  | 0 | 0 | 0 | 0 | 0 | 0 | 600 | 0 | 0 | D7 own money | explained |
| C90019027 | METRO DC DEMOCRATIC SOCIALISTS OF AMERICA | I |  | 593 | 593 | B | 593 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 593 | none | no FEC figure |
| C00834457 | FRIENDS OF BEN | H | 24,540 | 25,115 | 25,115 | B | 575 | 2.34% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 575 | none | unexplained |
| C00875179 | REPUBLICAN ASSEMBLY INDIANA SOUTHWEST (RAINS) | O | 5,608 | 5,608 | 6,152 | B | 544 | 9.70% | 0 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 | -456 | D2 duplicates | explained |
| C00525899 | CONCERNED AMERICAN VOTERS | V | 0 | 0 | 516 | B | 516 |  | 0 | 0 | 516 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00856252 | PROJECT LIBERAL PAC | V | 28,318 | 28,305 | 28,822 | B | 504 | 1.78% | 0 | 358 | 517 | 0 | 0 | 0 | 0 | 0 | -371 | D3 other line | explained |
| C00769752 | BOOT TEXAS REPUBLICANS | V | 0 | 500 | 500 | B | 500 |  | 0 | 0 | 500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00730820 | WESTON FOR UTAH | S | 0 | 500 | 500 | B | 500 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 500 | none | unexplained |
| C00874438 | FRIENDS OF BRIAN SCHKEEPER | H | 10,650 | 11,150 | 11,150 | B | 500 | 4.69% | 0 | 0 | 0 | 0 | 0 | 0 | 500 | 0 | 0 | D7 own money | explained |
| C00483891 | ADVANCED ENERGY ACTION | W | 14,500 | 14,500 | 15,000 | B | 500 | 3.45% | 0 | 0 | 500 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00756304 | MARVIN LUCAS SUPERPAC | O | 10,565 | 11,065 | 11,065 | B | 500 | 4.73% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 500 | none | unexplained |
| C00099754 | BAKEPAC - THE POLITICAL ACTION COMMITTEE OF THE INDEPENDENT BAKERS ASSOCIATION | Q | 0 | 0 | 500 | B | 500 |  | 0 | 0 | 0 | 500 | 0 | 0 | 0 | 0 | 0 | D4 names a committee | explained |
| C00487298 | RIVER HORSE PAC | V | 6,104 | 6,603 | 6,603 | B | 499 | 8.17% | 0 | 0 | 500 | 0 | 0 | 0 | 0 | 0 | -1 | D3 other line | explained |
| C00799312 | LISA BARTLETT FOR CONGRESS | H | 1,500 | 1,950 | 1,950 | B | 450 | 30.00% | 0 | 0 | 0 | 0 | 0 | 0 | 450 | 0 | 0 | D7 own money | explained |
| C00684332 | LIUNA MINNESOTA & NORTH DAKOTA/LABORERS' DISTRICT COUNCIL OF MINNESOTA & NORTH DAKOTA | O | 0 | 0 | 438 | B | 438 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 438 | 0 | D8 organizations on line 15 | explained |
| C00582072 | SAVING OUR LAKES AND OPEN SPACES IN RANCHO MURIETA POLITICAL ACTION COMMITTEE | O | 510 | 200 | 920 | B | 410 | 80.39% | 0 | 410 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | D2 duplicates | explained |
| C00832303 | JUSTIN LASTER FOR CONGRESS | H | 0 | 405 | 405 | B | 405 |  | 0 | 0 | 0 | 0 | 0 | 0 | 405 | 0 | 0 | D7 own money | explained |
| C00740068 | JENNY GARCIA SHARON FOR CONGRESS | H | 0 | 375 | 375 | B | 375 |  | 0 | 0 | 0 | 0 | 0 | 0 | 375 | 0 | 0 | D7 own money | explained |
| C00455725 | MARIPOSA COUNTY REPUBLICAN CENTRAL COMMITTEE (FEDERAL) | Y | 2,800 | 3,160 | 3,160 | B | 360 | 12.86% | 0 | 120 | 0 | 0 | 0 | 0 | 0 | 0 | 240 | D2 duplicates | unexplained |
| C00849356 | TIM PETERSON FOR CONGRESS | H | 2,500 | 2,836 | 2,836 | B | 336 | 13.44% | 0 | 0 | 0 | 0 | 0 | 0 | 336 | 0 | 0 | D7 own money | explained |
| C00682963 | DE LA TORRE FOR PRESIDENT | P | 0 | 302 | 302 | B | 302 |  | 0 | 0 | 0 | 0 | 0 | 0 | 302 | 0 | 0 | D7 own money | explained |
| C00353037 | NATIONAL FEDERATION OF DEMOCRATIC WOMEN PAC | N | 10,930 | 11,230 | 11,230 | B | 300 | 2.74% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 300 | none | unexplained |
| C00320143 | HAWAII OPTOMETRIC POLITICAL ACTION COMMITTEE | Q | 3,699 | 3,999 | 3,999 | B | 300 | 8.11% | 0 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | D2 duplicates | explained |
| C90023243 | KATHRYN A HOGG | I |  | 300 | 300 | B | 300 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 300 | none | no FEC figure |
| C00859157 | NIKET FOR US CONGRESS | H | 0 | 277 | 277 | B | 277 |  | 0 | 0 | 0 | 0 | 0 | 0 | 277 | 0 | 0 | D7 own money | explained |
| C00858753 | ELECT PAM GENANT | H | 23,165 | 23,429 | 23,429 | B | 264 | 1.14% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 264 | none | unexplained |
| C00843193 | COMMITTEE TO ELECT GUY WARNER | H | 0 | 250 | 250 | B | 250 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 250 | none | unexplained |
| C00128975 | CMHA BLOCK & PAVER PAC CONCRETE MASONRY AND HARDSCAPES VALLEY DRIVE | Q | 14,400 | 14,650 | 14,650 | B | 250 | 1.74% | 0 | 250 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | D2 duplicates | explained |
| C00003061 | NORTH DAKOTA MEDICAL ASSOCIATION POLITICAL ACTION COMMITTEE | Q | 10,400 | 10,650 | 10,650 | B | 250 | 2.40% | 0 | 250 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | D2 duplicates | explained |
| C00377754 | FLORIDA MUNICIPAL ELECTRIC ASSOCIATION INC PAC FMEA PAC | Q | 5,150 | 5,400 | 5,400 | B | 250 | 4.85% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 250 | none | unexplained |
| C00846808 | J.EMILIO MARTINEZ FOR CONGRESS 2024 | H | 250 | 500 | 500 | B | 250 | 100.00% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 250 | none | unexplained |
| C00725671 | RESOLVE TO WIN FUND | V | 202 | 452 | 452 | B | 250 | 123.32% | 0 | 0 | 250 | 0 | 0 | 0 | 0 | 0 | -0 | D3 other line | explained |
| C00830778 | JACK LOMBARDI FOR US CONGRESS | H | 0 | 222 | 222 | B | 222 |  | 0 | 0 | 0 | 0 | 0 | 0 | 222 | 0 | 0 | D7 own money | explained |
| C90022336 | BOZEMAN DEMOCRATIC SOCALISTS OF AMERICAN | I |  | 219 | 219 | B | 219 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 219 | none | no FEC figure |
| C00638817 | MAIN VOTERS | V | 0 | 0 | 200 | B | 200 |  | 0 | 0 | 200 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00629048 | RAY J WRITZ FOR US SENATE | S |  | 190 | 190 | B | 190 |  | 0 | 0 | 0 | 0 | 0 | 0 | 190 | 0 | 0 | D7 own money | no FEC figure |
| C00372722 | JAMES HART FOR CONGRESS | H | 0 | 179 | 179 | B | 179 |  | 0 | 0 | 0 | 0 | 0 | 0 | 179 | 0 | 0 | D7 own money | explained |
| C00672204 | MS VOTERS INFORMATION PROVIDERS PAC | N | 800 | 450 | 950 | B | 150 | 18.75% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 150 | none | unexplained |
| C00851683 | CROWL FOR CONGRESS | H | 5,538 | 5,638 | 5,638 | B | 100 | 1.81% | 0 | 0 | 0 | 0 | 0 | 0 | 100 | 0 | 0 | D7 own money | explained |
| C00866897 | ELEVATE AMERICA PAC | O | 0 | 100 | 100 | B | 100 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 100 | none | unexplained |
| C00840611 | SCOTT FOR MICHIGAN | S | 1,000 | 1,100 | 1,100 | B | 100 | 10.00% | 0 | 0 | 0 | 0 | 0 | 0 | 100 | 0 | 0 | D7 own money | explained |
| C00831057 | SHERIDAN FOR CONGRESS 2024 | H | 4,000 | 4,100 | 4,100 | B | 100 | 2.50% | 0 | 0 | 0 | 0 | 0 | 0 | 100 | 0 | 0 | D7 own money | explained |
| C00868786 | GROVES FOR CONGRESS | H |  | 100 | 100 | B | 100 |  | 0 | 0 | 0 | 0 | 0 | 0 | 100 | 0 | 0 | D7 own money | no FEC figure |
| C00846238 | UPLIFT OUR FUTURE | O | 0 | 0 | 100 | B | 100 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 100 | none | unexplained |
| C00858258 | FRIENDS OF DAN MOILANEN | H | 7,832 | 7,913 | 7,913 | B | 81 | 1.03% | 0 | 0 | 0 | 0 | 0 | 0 | 275 | 0 | -194 | D7 own money | explained |
| C00875492 | SHAUN GREENE FOR CONGRESS | H | 0 | 0 | 80 | B | 80 |  | 0 | 0 | 80 | 0 | 0 | 0 | 0 | 0 | 0 | D3 other line | explained |
| C00871350 | MICHIGAN ACTION FEDERAL SUPER PAC | O | 0 | 0 | 50 | B | 50 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 50 | none | unexplained |
| C00839712 | THE VALLEY FORGE PROJECT | O | 0 | 50 | 50 | B | 50 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 50 | none | unexplained |
| C00880005 | RAYMOND PETERSEN FOR US SENATE CAMPAIGN COMMITTEE | S | 0 | 47 | 47 | B | 47 |  | 0 | 0 | 0 | 0 | 0 | 0 | 47 | 0 | 0 | D7 own money | explained |
| C00508556 | CENTRIST INDEPENDENT VOTER POLITICAL ACTION COMMITTEE | O | 1,127 | 1,158 | 1,158 | B | 31 | 2.76% | 0 | 34 | 0 | 0 | 0 | 0 | 0 | 0 | -3 | D2 duplicates | explained |
| C00437079 | WESTCHESTER-PLAYA DEMOCRATIC CLUB | Q | 1,658 | 1,685 | 1,685 | B | 27 | 1.63% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 27 | none | unexplained |
| C00129627 | PIPEFITTERS LOCAL 636 POLITICAL ACTION COMMITTEE | Q | 170 | 194 | 194 | B | 24 | 13.87% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | none | unexplained |
| C00818468 | MIKE TROUT FOR CONGRESS CAMPAIGN COMMITTEE | H | 0 | 22 | 22 | B | 22 |  | 0 | 0 | 0 | 0 | 0 | 0 | 22 | 0 | 0 | D7 own money | explained |
| C00501924 | BARBARA MALLORY CARAWAY FOR CONGRESS | H | 198 | 216 | 216 | B | 18 | 9.09% | 0 | 0 | 0 | 0 | 0 | 0 | 18 | 0 | 0 | D7 own money | explained |
| C00776039 | FRANK CRAFT FOR CONGRESS | H | 0 | 4 | 4 | B | 4 |  | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | D7 own money | explained |
| C00784132 | ELECT DR. TIMOTHY BILASH M.D. FOR CONGRESS | H | 0 | 2 | 2 | B | 2 |  | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | D7 own money | explained |
| C00623355 | NATIONAL TREASURY EMPLOYEES UNION ADVOCACY COMMITTEE | O | 0 | 0 | 1 | B | 1 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | D8 organizations on line 15 | explained |

**Reading.**

- **The excess is $1,943.2M** over 725 committees. Of it, D3 (a type FEC puts on another line)
  explains $1,803.8M at 355 committees: $1,696.9M is hybrid PACs' non-contribution account (type 10
  at V/W), and $84.2M is the national parties' convention, headquarters and recount/legal accounts
  (30, 31, 32). The rest: D8 organizations on line 15 $75.1M (90 committees); D7 candidates' own
  money not flagged self-funding $32.7M (94); D4 committees typed ORG $27.6M (26); D2 repeated rows
  $19.1M (211, $4.1M of it across differing filings); D6 rows dated after the coverage end $3,000
  (1). D5 is $0: silver kept no memo line.
- **Verdicts:** 548 explained, 58 with no FEC figure, **119 unexplained, $34,449,580 left over.**
  The largest unexplained remainder is RSLC PAC's $19.1M from the Republican State Leadership
  Committee, a 527 that FEC's summary shows on no receipt line.
- **Distinct causes and their tickets** (all Bug, in P-NEU-105, related to NEU-2140):

  | Cause | Committees | Dollars | Ticket |
  | --- | --- | --- | --- |
  | D3: hybrid PACs' non-contribution account (type 10 at V/W) | 344 | $1,696,885,797 | [NEU-2192](https://linear.app/neuroticsasquatch/issue/NEU-2192) |
  | D3: party special accounts (30/31/32 and variants), 18U, 18G, 24I | 6 parties + 4 | $106,905,867 ($84,163,828 party accounts, $22,224,103 18U at a host committee) | [NEU-2193](https://linear.app/neuroticsasquatch/issue/NEU-2193) |
  | D7 (and D3 11(d)): candidates' own money (15C) typed IND or under a variant name | 94 | $32,791,095 | [NEU-2194](https://linear.app/neuroticsasquatch/issue/NEU-2194) |
  | D4: ORG-typed gifts from registered political committees | 26 | $27,639,632 | [NEU-2195](https://linear.app/neuroticsasquatch/issue/NEU-2195) |
  | D2: repeated rows, across filings and within one | 211 | $19,135,728 | [NEU-2196](https://linear.app/neuroticsasquatch/issue/NEU-2196) |
  | Unexplained remainder | 119 | $34,449,580 | [NEU-2197](https://linear.app/neuroticsasquatch/issue/NEU-2197) |
  | D8: organization money on line 15 | 90 | $75,058,172 | none: the filer's line choice, not a fundlens bug; NEU-2141's coverage note |
  | D6: dated after the summary's coverage end | 1 | $3,000 | none: FEC's roll-up lag |
  | D1: refunds | 199 | −$20,129,599 | none: lowers fundlens, explains no excess |

## Q7: the three named gaps

```python
bulk("oth")
THREE = "('C00835959', 'C00825851', 'C00571703')"
show("Q7a: Fairshake, MAGA Inc. and Senate Leadership Fund: Q5's figures and the summary's receipt lines", f"""
SELECT cov.committee_id, cov.name, cov.item AS fec_itemized, cov.unitem AS fec_unitemized, cov.a, cov.orgs, cov.b,
    cov.b - cov.item AS b_less_itemized, amt(c.OTHER_RECEIPTS) AS fec_other_receipts, amt(c.OTH_CMTE_CONTB) AS fec_other_committees,
    amt(c.TTL_RECEIPTS) AS fec_ttl_receipts, cov.cvg_end
FROM cov JOIN cs AS c ON c.CMTE_ID = cov.committee_id WHERE cov.committee_id IN {THREE} ORDER BY 1
""")
show("Q7b: Q6's diagnostics for those over 1%", f"""
SELECT committee_id, name, excess, d1_refunds, d2_duplicates, d3_other_line, d4_names_committee, d5_memo, d6_after_cvg_end,
    d7_own_money, d8_orgs_on_line_15, unexplained_dollars, primary_cause, verdict
FROM verdict WHERE committee_id IN {THREE}
""")
con.execute(f"""
-- Every indiv row of the three, with where silver put it or why it dropped it.
CREATE TABLE three AS
SELECT i.CMTE_ID, i.SUB_ID, i.TRANSACTION_TP, nullif(trim(i.ENTITY_TP), '') AS entity, i.MEMO_CD, i.TRANSACTION_AMT,
    CAST(try_strptime(i.TRANSACTION_DT, '%m%d%Y') AS DATE) AS date, i.NAME,
    CASE WHEN i.SUB_ID IN (SELECT source_record_id FROM silver.contribution WHERE recipient_committee_id IN {THREE}) THEN 'contribution'
        WHEN i.SUB_ID IN (SELECT source_record_id FROM silver.organization_receipt WHERE recipient_committee_id IN {THREE}) THEN 'organization_receipt'
        WHEN i.SUB_ID IN (SELECT source_record_id FROM silver.committee_transfer WHERE to_committee_id IN {THREE}) THEN 'committee_transfer'
        WHEN i.MEMO_CD = 'X' THEN 'dropped: memo line'
        WHEN i.TRANSACTION_TP = '24T' THEN 'dropped: 24T'
        WHEN trim(i.ENTITY_TP) IN ('PAC', 'COM', 'CCM', 'PTY') THEN 'dropped: committee giver, no single cm match'
        ELSE 'dropped: other' END AS outcome
FROM indiv AS i WHERE i.CMTE_ID IN {THREE}
""")
show("Q7c: their indiv rows by where silver put them, as filed", """
SELECT CMTE_ID, outcome, entity, TRANSACTION_TP, count(*) AS rows, sum(TRANSACTION_AMT) AS filed_dollars
FROM three GROUP BY ALL ORDER BY 1, 2, 6 DESC
""")
show("Q7d: their indiv rows dated after the summary's coverage end, or with no date", """
SELECT t.CMTE_ID, count(*) FILTER (WHERE t.date > ymd(c.CVG_END_DT)) AS after_cvg_end, sum(t.TRANSACTION_AMT) FILTER (WHERE t.date > ymd(c.CVG_END_DT)) AS dollars_after,
    count(*) FILTER (WHERE t.date IS NULL) AS no_date, min(t.date) AS first, max(t.date) AS last
FROM three AS t JOIN cs AS c ON c.CMTE_ID = t.CMTE_ID GROUP BY ALL ORDER BY 1
""")
show("Q7e: Senate Leadership Fund and MAGA Inc.: organization receipts by giver", """
SELECT o.recipient_committee_id, o.organization_name, count(*) AS rows, sum(o.amount) AS dollars, string_agg(DISTINCT o.transaction_type, ', ') AS types
FROM silver.organization_receipt AS o WHERE o.recipient_committee_id IN ('C00571703', 'C00825851')
GROUP BY ALL ORDER BY 1, 4 DESC
""")

show("Q7f: Fairshake's memo lines and organization rows in indiv, as filed", """
SELECT TRANSACTION_TP, ENTITY_TP, MEMO_CD, NAME, EMPLOYER, TRANSACTION_AMT, TRANSACTION_DT, IMAGE_NUM FROM indiv
WHERE CMTE_ID = 'C00835959' AND (MEMO_CD = 'X' OR ENTITY_TP = 'ORG') ORDER BY ENTITY_TP, TRANSACTION_AMT DESC
""")
show("Q7g: AH Capital Management (a16z) anywhere in indiv, and Fairshake's receipts in oth", """
SELECT 'indiv' AS file, CMTE_ID, TRANSACTION_TP, ENTITY_TP, MEMO_CD, NAME, TRANSACTION_AMT, TRANSACTION_DT FROM indiv
WHERE NAME LIKE '%AH CAPITAL%' OR NAME LIKE 'ANDREESSEN HOROWITZ%'
UNION ALL
SELECT 'oth', CMTE_ID, TRANSACTION_TP, ENTITY_TP, MEMO_CD, NAME, TRANSACTION_AMT, TRANSACTION_DT FROM oth
WHERE CMTE_ID = 'C00835959' AND left(TRANSACTION_TP, 1) IN ('1', '3')
ORDER BY 1, 7 DESC
""")
```

**Q7a: Fairshake, MAGA Inc. and Senate Leadership Fund: Q5's figures and the summary's receipt lines  (0 s)**

| committee_id | name | fec_itemized | fec_unitemized | a | orgs | b | b_less_itemized | fec_other_receipts | fec_other_committees | fec_ttl_receipts | cvg_end |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C00571703 | SENATE LEADERSHIP FUND | 220,730,171 | 8,213 | 176,050,171 | 79,260,000 | 255,310,171 | 34,580,000 | 66,432,747 | 8,934,548 | 298,859,707 | 2024-12-31 |
| C00825851 | MAKE AMERICA GREAT AGAIN INC. | 383,797,150 | 246 | 305,954,164 | 82,945,136 | 388,899,300 | 5,102,150 | 8,421,780 | 14,759,411 | 410,509,931 | 2024-12-31 |
| C00835959 | FAIRSHAKE | 217,419,084 | 4,796 | 7,326,650 | 166,692,432 | 174,019,082 | -43,400,002 | 41,660,410 | 0 | 260,070,709 | 2024-12-31 |

**Q7b: Q6's diagnostics for those over 1%  (0 s)**

| committee_id | name | excess | d1_refunds | d2_duplicates | d3_other_line | d4_names_committee | d5_memo | d6_after_cvg_end | d7_own_money | d8_orgs_on_line_15 | unexplained_dollars | primary_cause | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C00825851 | MAKE AMERICA GREAT AGAIN INC. | 5,102,150 | -300,000 | 108,400 | 0 | 0 | 0 | 0 | 0 | 4,993,750 | 0 | D8 organizations on line 15 | explained |
| C00571703 | SENATE LEADERSHIP FUND | 34,580,000 | 0 | 500 | 0 | 0 | 0 | 0 | 0 | 34,579,500 | 0 | D8 organizations on line 15 | explained |

**Q7c: their indiv rows by where silver put them, as filed  (0 s)**

| CMTE_ID | outcome | entity | TRANSACTION_TP | rows | filed_dollars |
|---|---|---|---|---|---|
| C00571703 | committee_transfer | PAC | 10 | 17 | 8,684,545 |
| C00571703 | contribution | IND | 10 | 356 | 176,050,171 |
| C00571703 | dropped: committee giver, no single cm match | PAC | 10 | 2 | 250,000 |
| C00571703 | dropped: memo line | IND | 10 | 5 | 1,000,000 |
| C00571703 | organization_receipt | ORG | 10 | 89 | 79,260,000 |
| C00825851 | committee_transfer | PAC | 10 | 2 | 10,422,000 |
| C00825851 | committee_transfer | COM | 10 | 2 | 1,300,000 |
| C00825851 | contribution | IND | 10 | 305 | 306,054,164 |
| C00825851 | contribution | IND | 22Y | 1 | 100,000 |
| C00825851 | dropped: committee giver, no single cm match | PAC | 20Y | 4 | 12,250,000 |
| C00825851 | dropped: committee giver, no single cm match | COM | 20Y | 1 | 5,000,000 |
| C00825851 | dropped: committee giver, no single cm match | PAC | 10 | 3 | 100,000 |
| C00825851 | dropped: memo line | IND | 10 | 22 | 13,039,809 |
| C00825851 | dropped: memo line | ORG | 10 | 1 | 5,070,414 |
| C00825851 | organization_receipt | ORG | 10 | 62 | 83,145,136 |
| C00825851 | organization_receipt | ORG | 20Y | 1 | 200,000 |
| C00835959 | contribution | IND | 10 | 37 | 7,326,650 |
| C00835959 | dropped: memo line | IND | 10 | 18 | 69,447,540 |
| C00835959 | organization_receipt | ORG | 10 | 19 | 166,692,432 |

**Q7d: their indiv rows dated after the summary's coverage end, or with no date  (0 s)**

| CMTE_ID | after_cvg_end | dollars_after | no_date | first | last |
|---|---|---|---|---|---|
| C00571703 | 0 |  | 0 | 2023-01-03 | 2024-12-27 |
| C00825851 | 0 |  | 0 | 2023-02-02 | 2024-12-16 |
| C00835959 | 0 |  | 0 | 2023-07-01 | 2024-12-24 |

**Q7e: Senate Leadership Fund and MAGA Inc.: organization receipts by giver  (0 s)**

| recipient_committee_id | organization_name | rows | dollars | types |
|---|---|---|---|---|
| C00571703 | ONE NATION | 5 | 35,580,000 | 10 |
| C00571703 | CHEVRON CORPORATION | 4 | 4,500,000 | 10 |
| C00571703 | OCCIDENTAL PETROLEUM CORP | 2 | 4,000,000 | 10 |
| C00571703 | ALTRIA CLIENT SERVICES LLC | 7 | 3,875,000 | 10 |
| C00571703 | AMERICAN PETROLEUM INSTITUTE | 4 | 3,500,000 | 10 |
| C00571703 | HILLWOOD DEVELOPMENT COMPANY LLC | 3 | 3,000,000 | 10 |
| C00571703 | RAI SERVICES COMPANY | 4 | 3,000,000 | 10 |
| C00571703 | MELALEUCA INC. | 2 | 2,100,000 | 10 |
| C00571703 | VALERO SERVICES INC. | 7 | 2,000,000 | 10 |
| C00571703 | DEVON ENERGY PRODUCTION COMPANY | 2 | 2,000,000 | 10 |
| C00571703 | CONOCOPHILLIPS ANS MARKETING CO. | 1 | 1,500,000 | 10 |
| C00571703 | KOCH INDUSTRIES INC | 6 | 1,500,000 | 10 |
| C00571703 | THE ANSCHUTZ CORPORATION | 2 | 1,000,000 | 10 |
| C00571703 | CONOCOPHILLIPS ANS MARKETING COMPANY | 1 | 1,000,000 | 10 |
| C00571703 | SMARTWASH SOLUTIONS LLC | 2 | 1,000,000 | 10 |
| C00571703 | OTA HOLDINGS INC. | 1 | 1,000,000 | 10 |
| C00571703 | NATIONAL ASSOCIATION OF REALTORS | 1 | 1,000,000 | 10 |
| C00571703 | U.S. CHAMBER OF COMMERCE | 1 | 1,000,000 | 10 |
| C00571703 | KOCH INC. | 4 | 1,000,000 | 10 |
| C00571703 | CONTINENTAL RESOURCES | 1 | 900,000 | 10 |
| C00571703 | GULF UNITED INVESTMENTS CORP | 1 | 500,000 | 10 |
| C00571703 | AH CAPITAL MANAGEMENT LLC | 1 | 500,000 | 10 |
| C00571703 | COINBASE INC. | 1 | 500,000 | 10 |
| C00571703 | ARDLEIGH IMPACT CORP | 1 | 400,000 | 10 |
| C00571703 | GEO ACQUISTION II INC. | 4 | 400,000 | 10 |
| C00571703 | OVINTIV USA INC. | 2 | 350,000 | 10 |
| C00571703 | EQT CORPORATION | 2 | 300,000 | 10 |
| C00571703 | TAYLOR FRESH FOODS INC. | 1 | 250,000 | 10 |
| C00571703 | PAYWARD INC | 1 | 250,000 | 10 |
| C00571703 | AIBFF INC. | 1 | 200,000 | 10 |
| C00571703 | C.V. STARR & COMPANY INC. | 1 | 150,000 | 10 |
| C00571703 | AMERICAN FUEL AND PETROCHEMICAL MANUFACTURERS | 1 | 150,000 | 10 |
| C00571703 | CUSTOM MANAGEMENT SERVICES | 1 | 100,000 | 10 |
| C00571703 | DOORDASH INC. | 1 | 100,000 | 10 |
| C00571703 | MARATHON OIL COMPANY | 1 | 100,000 | 10 |
| C00571703 | CALPORTLAND COMPANY | 1 | 100,000 | 10 |
| C00571703 | ERGON INC. | 1 | 100,000 | 10 |
| C00571703 | GEO ACQUISTION II | 1 | 100,000 | 10 |
| C00571703 | PROBITY INTERNATIONAL CORPORATION | 1 | 60,000 | 10 |
| C00571703 | GUARANTEE TRUST LIFE | 1 | 50,000 | 10 |
| C00571703 | SORRENTO WEST PROPERTIES INC. | 1 | 50,000 | 10 |
| C00571703 | JUUL LABS INC. | 1 | 50,000 | 10 |
| C00571703 | WHI INC. | 1 | 25,000 | 10 |
| C00571703 | AMERICAN CONSOLIDATED NATURAL RESOURCES INC. | 1 | 20,000 | 10 |
| C00825851 | SECURING AMERICAN GREATNESS | 1 | 52,558,283 | 10 |
| C00825851 | RAI SERVICES COMPANY | 4 | 10,000,000 | 10 |
| C00825851 | CAPITAL INSTITUTIONAL SERVICES INC | 2 | 8,066,879 | 10 |
| C00825851 | CONTINENTAL RESOURCES INC | 2 | 2,000,000 | 10 |
| C00825851 | REPUBLICAN JEWISH COALITION | 4 | 1,493,500 | 10 |
| C00825851 | GEO ACQUISITION II INC | 3 | 1,000,000 | 10 |
| C00825851 | NXUM GROUP LLC | 1 | 1,000,000 | 10 |
| C00825851 | FLORIDA CRYSTALS CORPORATION | 1 | 1,000,000 | 10 |
| C00825851 | LRF JR, LLC | 1 | 1,000,000 | 10 |
| C00825851 | CONSERVATIVE AGENDA FOR AMERICA | 1 | 950,000 | 10 |
| C00825851 | CHURCHILL BUSINESS CONSULTANTS INC. | 3 | 750,000 | 10 |
| C00825851 | HAWTHORNE HYDROPONICS LLC | 1 | 500,000 | 10 |
| C00825851 | PEPPER HILL SNF OPERATIONS  LLC | 1 | 250,000 | 10 |
| C00825851 | O M S INVESTMENTS INC | 1 | 250,000 | 10 |
| C00825851 | SWISS FARMS PRODUCTS INC | 1 | 250,000 | 10 |
| C00825851 | PROFESSIONAL ENTERPRISES OF HATTERAS ISLAND, INC. | 5 | 250,000 | 10 |
| C00825851 | HILTON, INC. | 1 | 200,000 | 10 |
| C00825851 | SAC HOLDINGS, CORP | 1 | 200,000 | 10 |
| C00825851 | GRAFICO PRINTING | 1 | 105,000 | 10 |
| C00825851 | CHARLOTTE PIPE AND FOUNDRY | 1 | 100,000 | 10 |
| C00825851 | OUTBUILD LLC | 1 | 100,000 | 10 |
| C00825851 | 1A AUTO INC | 1 | 100,000 | 10 |
| C00825851 | DYNALAB TEST SYSTEM INC | 1 | 100,000 | 10 |
| C00825851 | CDR ENTERPRISES INC | 1 | 100,000 | 10 |
| C00825851 | BULLINGTON CONSTRUCTION INC. | 1 | 100,000 | 10 |
| C00825851 | VIERGE GROUP LLC | 1 | 100,000 | 10 |
| C00825851 | SUNSHINE GASOLINE DISTRIBUTORS, INC | 1 | 76,800 | 10 |
| C00825851 | SURF OR SOUND REALTY | 1 | 50,000 | 10 |
| C00825851 | SMYRNA READY MIX CONCRETE LLC | 1 | 50,000 | 10 |
| C00825851 | CAPITAL SALES COMPANY INC | 1 | 45,000 | 10 |
| C00825851 | MARD ENERGY SOLUTIONS LLC | 1 | 38,400 | 10 |
| C00825851 | CROELL INC | 1 | 27,000 | 10 |
| C00825851 | GENESIS LIFE LLC | 1 | 25,000 | 10 |
| C00825851 | NATURES BEST INC. | 1 | 25,000 | 10 |
| C00825851 | PROGRESSIVE MERCHANTS INC. | 1 | 25,000 | 10 |
| C00825851 | SANCTUARY LOUISIANA LLC | 1 | 25,000 | 10 |
| C00825851 | OLD NATIONAL BANCORP | 1 | 20,000 | 10 |
| C00825851 | MONTANA COAL COUNCIL | 1 | 5,000 | 10 |
| C00825851 | THE POLICYHOLDER PROTECTION GROUP | 1 | 3,274 | 10 |
| C00825851 | 3047 INVESTMENT CORPORATION | 1 | 1,000 | 10 |
| C00825851 | MACA CONSTRUCTION CORPORATION | 1 | 1,000 | 10 |
| C00825851 | 3-H DEVELOPMENT OF MIAMI, INC. | 1 | 1,000 | 10 |
| C00825851 | CFLP PROPERTY MANAGERS, INC | 1 | 1,000 | 10 |
| C00825851 | APEX MAINTENANCE, INC | 1 | 1,000 | 10 |
| C00825851 | FENIX CONTRACTORS, INC | 1 | 1,000 | 10 |
| C00825851 | SUNBEAM SOLUTIONS LLC | 2 | 0 | 10, 20Y |

**Q7f: Fairshake's memo lines and organization rows in indiv, as filed  (9 s)**

| TRANSACTION_TP | ENTITY_TP | MEMO_CD | NAME | EMPLOYER | TRANSACTION_AMT | TRANSACTION_DT | IMAGE_NUM |
|---|---|---|---|---|---|---|---|
| 10 | IND | X | ANDREESSEN, MARC | AH CAPITAL MANAGEMENT | 12,500,000 | 05302024 | 202406209652010581 |
| 10 | IND | X | HOROWITZ, BEN | AH CAPITAL MANAGEMENT | 12,500,000 | 05302024 | 202406209652010581 |
| 10 | IND | X | HOROWITZ, BEN | AH CAPITAL MANAGEMENT | 11,500,000 | 11062024 | 202412059731456863 |
| 10 | IND | X | ANDREESSEN, MARC | AH CAPITAL MANAGEMENT | 11,500,000 | 11062024 | 202412059731456863 |
| 10 | IND | X | ANDREESSEN, MARC | AH CAPITAL MANAGEMENT | 7,000,000 | 12132023 | 202401319618984577 |
| 10 | IND | X | HOROWITZ, BEN | AH CAPITAL MANAGEMENT | 7,000,000 | 12132023 | 202401319618984577 |
| 10 | IND | X | ANDREESSEN, MARC | AH CAPITAL MANAGEMENT | 2,500,000 | 10232023 | 202401319618984576 |
| 10 | IND | X | HOROWITZ, BEN | AH CAPITAL MANAGEMENT | 2,500,000 | 10232023 | 202401319618984576 |
| 10 | IND | X | WILSON, FRED | UNION SQUARE VENTURES | 1,047,540 | 12192023 | 202401319618984587 |
| 10 | IND | X | HUANG, MATT | PARADIGM OPERATIONS LP | 250,000 | 12122023 | 202401319618984585 |
| 10 | IND | X | GARG, AVICHAL | ELECTRIC CAPITAL PARTNERS | 250,000 | 01262024 | 202402209619869830 |
| 10 | IND | X | SPENCER, CURTIS | ELECTRIC CAPITAL PARTNERS | 250,000 | 01262024 | 202402209619869830 |
| 10 | IND | X | EHRSAM, FRED | PARADIGM OPERATIONS LP | 250,000 | 12122023 | 202401319618984585 |
| 10 | IND | X | SAMANI, PYAHM | MULTICOIN CAPITAL | 100,000 | 12152023 | 202401319618984584 |
| 10 | IND | X | WILSON, DONALD | CUMBERLAND DRW | 100,000 | 12142023 | 202401319618984580 |
| 10 | IND | X | JAIN, TUSHAR | MULTICOIN CAPITAL | 100,000 | 12152023 | 202401319618984583 |
| 10 | IND | X | STEPHENS, BART | BLOCKCHAIN CAPITAL. LLC | 50,000 | 01222024 | 202402209619869829 |
| 10 | IND | X | STEPHENS, BRADFORD | BLOCKCHAIN CAPITAL. LLC | 50,000 | 01222024 | 202402209619869829 |
| 10 | ORG |  | COINBASE COMMERCE (EXCHANGE) |  | 25,000,000 | 06032024 | 202407209661447526 |
| 10 | ORG |  | RIPPLE LABS INC. |  | 25,000,000 | 05152024 | 202406209652010583 |
| 10 | ORG |  | COINBASE |  | 24,999,995 | 05302024 | 202406209652010582 |
| 10 | ORG |  | COINBASE |  | 23,000,000 | 12202024 | 202501319752374587 |
| 10 | ORG |  | RIPPLE LABS INC |  | 20,000,000 | 12152023 | 202401319618984586 |
| 10 | ORG |  | COINBASE |  | 15,500,000 | 12202023 | 202401319618984580 |
| 10 | ORG |  | JUMP CRYPTO |  | 10,000,000 | 05242024 | 202406209652010583 |
| 10 | ORG |  | JUMP CRYPTO |  | 10,000,000 | 12242024 | 202501319752374587 |
| 10 | ORG |  | JUMP CRYPTO |  | 5,000,000 | 12132023 | 202401319618984582 |
| 10 | ORG |  | COINBASE |  | 5,000,000 | 11032023 | 202401319618984579 |
| 10 | ORG |  | CIRCLE INTERNET FINANCIAL |  | 1,000,000 | 12192023 | 202401319618984579 |
| 10 | ORG |  | CONSENSYS SOFTWARE INC. |  | 800,000 | 09062024 | 202410209699280003 |
| 10 | ORG |  | PAYWARD, INC. |  | 750,000 | 01122024 | 202402209619869831 |
| 10 | ORG |  | PAYWARD, INC. |  | 250,000 | 03152024 | 202404209633594595 |
| 10 | ORG |  | LIGHTSPARK GROUP |  | 200,000 | 12132023 | 202401319618984582 |
| 10 | ORG |  | ARK INVEST |  | 156,915 | 12122023 | 202401319618984578 |
| 10 | ORG |  | ACTION FACTORY, INC. |  | 25,000 | 07312024 | 202408209666661492 |
| 10 | ORG |  | UNOFFICIAL LLC |  | 10,000 | 12262023 | 202401319618984586 |
| 10 | ORG |  | ARK INVEST |  | 522 | 12122023 | 202401319618984578 |

**Q7g: AH Capital Management (a16z) anywhere in indiv, and Fairshake's receipts in oth  (12 s)**

| file | CMTE_ID | TRANSACTION_TP | ENTITY_TP | MEMO_CD | NAME | TRANSACTION_AMT | TRANSACTION_DT |
|---|---|---|---|---|---|---|---|
| indiv | C00484642 | 10 | ORG |  | AH CAPITAL MANAGEMENT LLC | 500,000 | 09202024 |
| indiv | C00484642 | 10 | ORG |  | AH CAPITAL MANAGEMENT LLC | 500,000 | 06202024 |
| indiv | C00571703 | 10 | ORG |  | AH CAPITAL MANAGEMENT LLC | 500,000 | 10012024 |
| indiv | C00484642 | 10 | ORG |  | AH CAPITAL MANAGEMENT LLC | 250,000 | 03072024 |
| indiv | C00504530 | 10 | ORG |  | ANDREESSEN HOROWITZ CAPITAL MANAGEMENT | 250,000 | 03142024 |
| indiv | C00495028 | 10 | ORG |  | AH CAPITAL MANAGEMENT | 250,000 | 09242024 |
| indiv | C00504530 | 10 | ORG |  | ANDREESSEN HOROWITZ CAPITAL MANAGEMENT | 250,000 | 06202024 |
| indiv | C00495028 | 10 | ORG |  | ANDREESSEN HOROWITZ CAPITAL MANAGEMENT LLC | 250,000 | 12192023 |
| indiv | C00504530 | 10 | ORG |  | ANDREESSEN HOROWITZ CAPITAL MANAGEMENT | 250,000 | 09242024 |

**Senate Leadership Fund (C00571703): $34.6M over FEC.** fundlens counts $176.1M from
individuals and $79.3M from organizations, all type 10. FEC reports $220.7M itemized and $66.4M of
other receipts. The excess is organization money SLF reported on line 15 rather than 11(a)(i) (D8
explains all but $500). ONE NATION's $35.6M is the largest of it. Nothing in fundlens is wrong.

**MAGA Inc. (C00825851): $5.1M over FEC.** FEC reports $383.8M itemized and $8.4M of other
receipts. fundlens's B is $388.9M. D8 explains $4.99M as organization money on line 15. D2 adds
$108,400 of repeated rows, and refunds net −$300,000. Silver also dropped $18.1M of memo lines and
$17.25M of refunds to committees it cannot name (20Y from PAC/COM givers). Neither changes the
excess.

**Fairshake (C00835959): $43.4M under FEC.** fundlens counts 37 gifts from individuals ($7.3M)
and 19 organization receipts ($166.7M), against FEC's $217.4M itemized. The money missing is 18
memo lines ($69.4M; Q7c, Q7f). Fairshake reported a16z's gifts (AH Capital Management, $67.0M across four
dates) and those of Union Square Ventures, Paradigm, Electric Capital, Multicoin, Blockchain Capital
and Cumberland DRW only as attributions to the partners: Horowitz and Andreessen $12.5M each, and so
on. No parent LLC row exists in `indiv` (AH Capital's nine
`indiv` rows all go to other committees) or among Fairshake's `oth` receipts (Q7g). Silver drops memo lines, so fundlens never sees
the money (NEU-2198). Rows dated after the coverage end are none, and its unitemized money is
$4,796. The remaining $26.0M difference between $69.4M and $43.4M is consistent with part of its
organization money sitting on line 15 ($41.7M of other receipts).

## Q8: 2004, with `weball`, `webl` and `webk` only

The fundlens side is the spec's §2 proxy: counted `indiv` rows, refunds as −abs, 15C apart. It has
no classifier, conduit rule or self-funding name match. It is compared with FEC's individual
*total*, since nothing before 2008 splits itemized from unitemized.

```python
for name in ("indiv", "cm", "cn", "ccl"):
    bulk(name, 2004)
view_zip("weball04", fetch("2004/weball04.zip"), WEBALL)
view_zip("webl04", fetch("2004/webl04.zip"), WEBALL)
view_zip("webk04", fetch("2004/webk04.zip"), WEBK)

show("Q8a: rows and keys per 2004 file", """
SELECT 'weball04' AS file, count(*) AS rows, count(DISTINCT CAND_ID) AS keys, min(mdy(CVG_END_DT)) AS cvg_end_min,
    median(mdy(CVG_END_DT))::DATE AS cvg_end_median, max(mdy(CVG_END_DT)) AS cvg_end_max,
    count(*) FILTER (WHERE mdy(CVG_END_DT) <= DATE '2004-12-31') AS cvg_end_by_2004_12_31, sum(amt(TTL_RECEIPTS)) AS ttl_receipts
FROM weball04
UNION ALL
SELECT 'webl04', count(*), count(DISTINCT CAND_ID), min(mdy(CVG_END_DT)), median(mdy(CVG_END_DT))::DATE, max(mdy(CVG_END_DT)),
    count(*) FILTER (WHERE mdy(CVG_END_DT) <= DATE '2004-12-31'), sum(amt(TTL_RECEIPTS))
FROM webl04
UNION ALL
SELECT 'webk04', count(*), count(DISTINCT CMTE_ID), min(mdy(CVG_END_DT)), median(mdy(CVG_END_DT))::DATE, max(mdy(CVG_END_DT)),
    count(*) FILTER (WHERE mdy(CVG_END_DT) <= DATE '2004-12-31'), sum(amt(TTL_RECEIPTS))
FROM webk04
""")
show("Q8b: webl04 vs weball04, by office", """
SELECT left(coalesce(w.CAND_ID, l.CAND_ID), 1) AS office,
    count(*) FILTER (WHERE l.CAND_ID IS NULL) AS weball_only, count(*) FILTER (WHERE w.CAND_ID IS NULL) AS webl_only,
    count(*) FILTER (WHERE w.CAND_ID IS NOT NULL AND l.CAND_ID IS NOT NULL
        AND (w.TTL_RECEIPTS, w.TTL_DISB, w.COH_BOP, w.COH_COP, w.DEBTS_OWED_BY, w.TTL_INDIV_CONTRIB, w.OTHER_POL_CMTE_CONTRIB,
             w.POL_PTY_CONTRIB, w.CAND_CONTRIB, w.CAND_LOANS, w.TRANS_FROM_AUTH, w.TRANS_TO_AUTH, w.CVG_END_DT)
        IS NOT DISTINCT FROM
            (l.TTL_RECEIPTS, l.TTL_DISB, l.COH_BOP, l.COH_COP, l.DEBTS_OWED_BY, l.TTL_INDIV_CONTRIB, l.OTHER_POL_CMTE_CONTRIB,
             l.POL_PTY_CONTRIB, l.CAND_CONTRIB, l.CAND_LOANS, l.TRANS_FROM_AUTH, l.TRANS_TO_AUTH, l.CVG_END_DT)) AS both_equal,
    count(*) FILTER (WHERE w.CAND_ID IS NOT NULL AND l.CAND_ID IS NOT NULL
        AND (w.TTL_RECEIPTS, w.TTL_DISB, w.COH_BOP, w.COH_COP, w.DEBTS_OWED_BY, w.TTL_INDIV_CONTRIB, w.OTHER_POL_CMTE_CONTRIB,
             w.POL_PTY_CONTRIB, w.CAND_CONTRIB, w.CAND_LOANS, w.TRANS_FROM_AUTH, w.TRANS_TO_AUTH, w.CVG_END_DT)
        IS DISTINCT FROM
            (l.TTL_RECEIPTS, l.TTL_DISB, l.COH_BOP, l.COH_COP, l.DEBTS_OWED_BY, l.TTL_INDIV_CONTRIB, l.OTHER_POL_CMTE_CONTRIB,
             l.POL_PTY_CONTRIB, l.CAND_CONTRIB, l.CAND_LOANS, l.TRANS_FROM_AUTH, l.TRANS_TO_AUTH, l.CVG_END_DT)) AS both_differ
FROM weball04 AS w FULL JOIN webl04 AS l USING (CAND_ID) GROUP BY ALL ORDER BY 1
""")
show("Q8c: webk04 committees against 2004 cm, by CMTE_TP group", """
SELECT grp(k.CMTE_TP) AS grp, count(*) AS committees, count(*) FILTER (WHERE k.CMTE_ID IN (SELECT CMTE_ID FROM c2004.cm)) AS in_cm,
    sum(amt(k.TTL_RECEIPTS)) AS ttl_receipts, sum(amt(k.INDV_CONTRIB)) AS indv_contrib
FROM webk04 AS k GROUP BY ALL ORDER BY 1
""")
con.execute("""
-- The 2004 proxy for total_individual (spec §2): counted indiv rows, refunds as -abs, 15C apart. No
-- classifier, no conduit rule, no name match.
CREATE TABLE proxy04 AS
SELECT CMTE_ID,
    sum(CASE WHEN regexp_matches(TRANSACTION_TP, '^[24][0-9]Y$') THEN -abs(TRANSACTION_AMT) ELSE TRANSACTION_AMT END)
        FILTER (WHERE TRANSACTION_TP IS DISTINCT FROM '15C') AS proxy,
    coalesce(sum(TRANSACTION_AMT) FILTER (WHERE TRANSACTION_TP = '15C'), 0) AS own, count(*) AS rows
FROM c2004.indiv
WHERE MEMO_CD IS DISTINCT FROM 'X' AND TRANSACTION_TP IS DISTINCT FROM '24T'
    AND coalesce(nullif(trim(ENTITY_TP), ''), 'IND') IN ('IND', 'CAN')
GROUP BY ALL;
CREATE TABLE k04 AS
SELECT k.CMTE_ID, k.CMTE_TP, grp(k.CMTE_TP) AS grp, amt(k.INDV_CONTRIB) AS reported, coalesce(p.proxy, 0) AS proxy
FROM webk04 AS k LEFT JOIN proxy04 AS p USING (CMTE_ID);
""")
show("Q8d: 2004 coverage per committee in webk04: proxy / INDV_CONTRIB (itemized and unitemized), committees with INDV_CONTRIB > 0", """
SELECT grp, count(*) AS committees, quantile_cont(proxy / reported, 0.1) AS p10, quantile_cont(proxy / reported, 0.25) AS p25,
    quantile_cont(proxy / reported, 0.5) AS median, quantile_cont(proxy / reported, 0.75) AS p75, quantile_cont(proxy / reported, 0.9) AS p90,
    sum(proxy) / sum(reported) AS dollar_weighted,
    count(*) FILTER (WHERE proxy > 1.01 * reported) AS over_1_pct, sum(proxy - reported) FILTER (WHERE proxy > 1.01 * reported) AS over_dollars,
    sum(reported) AS reported, sum(proxy) AS proxy
FROM k04 WHERE reported > 0 GROUP BY ROLLUP (grp) ORDER BY grp NULLS LAST
""")
show("Q8e: 2004 committees in webk04 with no INDV_CONTRIB but proxy dollars", """
SELECT grp, count(*) AS committees, sum(proxy) AS proxy FROM k04 WHERE coalesce(reported, 0) <= 0 AND proxy > 0 GROUP BY ALL ORDER BY 1
""")
con.execute("""
-- A 2004 candidate's committees: ccl's P and A links, and cn's CAND_PCC.
CREATE TABLE cc04 AS
SELECT DISTINCT CAND_ID, CMTE_ID FROM (
    SELECT CAND_ID, CMTE_ID FROM c2004.ccl WHERE CMTE_DSGN IN ('P', 'A')
    UNION ALL
    SELECT CAND_ID, CAND_PCC FROM c2004.cn WHERE nullif(trim(CAND_PCC), '') IS NOT NULL
);
CREATE TABLE w04 AS
SELECT w.CAND_ID, left(w.CAND_ID, 1) AS office, amt(w.TTL_INDIV_CONTRIB) AS reported,
    count(cc.CMTE_ID) AS committees, coalesce(sum(p.proxy), 0) AS proxy
FROM weball04 AS w LEFT JOIN cc04 AS cc USING (CAND_ID) LEFT JOIN proxy04 AS p ON p.CMTE_ID = cc.CMTE_ID
GROUP BY ALL;
""")
show("Q8f: 2004 coverage per candidate in weball04: proxy over P/A committees / TTL_INDIV_CONTRIB, candidates with TTL_INDIV_CONTRIB > 0", """
SELECT office, count(*) AS candidates, count(*) FILTER (WHERE committees = 0) AS no_committee,
    quantile_cont(proxy / reported, 0.1) AS p10, quantile_cont(proxy / reported, 0.25) AS p25, quantile_cont(proxy / reported, 0.5) AS median,
    quantile_cont(proxy / reported, 0.75) AS p75, quantile_cont(proxy / reported, 0.9) AS p90, sum(proxy) / sum(reported) AS dollar_weighted,
    count(*) FILTER (WHERE proxy > 1.01 * reported) AS over_1_pct, sum(reported) AS reported, sum(proxy) AS proxy
FROM w04 WHERE reported > 0 GROUP BY ROLLUP (office) ORDER BY office NULLS LAST
""")
show("Q8g: 2004 candidates whose proxy exceeds TTL_INDIV_CONTRIB by more than 1%: the 15 largest", """
SELECT w.CAND_ID, b.CAND_NAME, w.committees, w.reported, w.proxy, w.proxy - w.reported AS excess
FROM w04 AS w JOIN weball04 AS b USING (CAND_ID) WHERE w.proxy > 1.01 * w.reported AND w.reported > 0
ORDER BY excess DESC LIMIT 15
""")
parts = []
for view, cols in (("weball04", WEBALL), ("webk04", WEBK)):
    for col in cols:
        if col in ("CAND_ID", "CMTE_ID", "CAND_NAME", "CMTE_NM"):
            continue
        parts.append(f"SELECT '{view}' AS file, '{col}' AS column_name, count(*) AS rows, "
                     f"count(*) FILTER (WHERE nullif(trim({col}), '') IS NOT NULL) AS filled, "
                     f"count(*) FILTER (WHERE nullif(trim({col}), '') IS NOT NULL AND trim({col}) NOT IN ('0', '0.00', '0.0')) AS nonzero FROM {view}")
show("Q8h: which 2004 columns carry values", " UNION ALL ".join(parts))
```

**Q8a: rows and keys per 2004 file  (0 s)**

| file | rows | keys | cvg_end_min | cvg_end_median | cvg_end_max | cvg_end_by_2004_12_31 | ttl_receipts |
|---|---|---|---|---|---|---|---|
| weball04 | 2,468 | 2,468 | 2003-01-01 | 2004-12-31 | 2005-03-31 | 2,455 | 2,244,696,474 |
| webl04 | 1,578 | 1,578 | 2003-01-31 | 2004-12-31 | 2005-03-31 | 1,566 | 2,148,422,053 |
| webk04 | 6,082 | 6,082 | 2003-01-01 | 2004-12-31 | 2005-12-31 | 5,514 | 3,199,709,147 |

**Q8b: webl04 vs weball04, by office  (0 s)**

| office | weball_only | webl_only | both_equal | both_differ |
|---|---|---|---|---|
| H | 695 | 0 | 1,273 | 0 |
| P | 0 | 0 | 104 | 0 |
| S | 195 | 0 | 201 | 0 |

**Q8c: webk04 committees against 2004 cm, by CMTE_TP group  (0 s)**

| grp | committees | in_cm | ttl_receipts | indv_contrib |
|---|---|---|---|---|
| PAC | 4,922 | 4,922 | 1,293,762,864 | 934,108,300 |
| candidate | 54 | 54 | 5,698,038 | 2,350,727 |
| other | 378 | 378 | 3,507,825 | 722,250 |
| party | 628 | 628 | 1,895,589,731 | 1,372,961,814 |
| super PAC | 100 | 100 | 1,150,688 | 948,496 |

**Q8d: 2004 coverage per committee in webk04: proxy / INDV_CONTRIB (itemized and unitemized), committees with INDV_CONTRIB > 0  (0 s)**

| grp | committees | p10 | p25 | median | p75 | p90 | dollar_weighted | over_1_pct | over_dollars | reported | proxy |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PAC | 3,844 | 0.00% | 3.00% | 36.35% | 85.77% | 99.47% | 36.11% | 52 | 588,785 | 934,108,300 | 337,317,465 |
| candidate | 34 | 1.35% | 66.76% | 95.23% | 99.85% | 100.00% | 99.22% | 2 | 119,479 | 2,350,727 | 2,332,457 |
| other | 4 | 35.42% | 51.20% | 74.40% | 90.53% | 93.59% | 90.77% | 0 |  | 722,250 | 655,551 |
| party | 433 | 0.00% | 3.85% | 33.53% | 70.13% | 96.69% | 44.11% | 9 | 99,780 | 1,372,961,814 | 605,664,559 |
| super PAC | 47 | 0.00% | 0.00% | 25.75% | 72.27% | 92.34% | 41.37% | 1 | 205 | 948,496 | 392,359 |
|  | 4,362 | 0.00% | 3.13% | 36.17% | 84.84% | 99.37% | 40.95% | 64 | 808,249 | 2,311,091,587 | 946,362,391 |

**Q8e: 2004 committees in webk04 with no INDV_CONTRIB but proxy dollars  (0 s)**

| grp | committees | proxy |
|---|---|---|
| PAC | 13 | 35,880,057 |
| other | 10 | 1,713,362 |
| party | 1 | 1,625 |
| super PAC | 1 | 1,359 |

**Q8f: 2004 coverage per candidate in weball04: proxy over P/A committees / TTL_INDIV_CONTRIB, candidates with TTL_INDIV_CONTRIB > 0  (0 s)**

| office | candidates | no_committee | p10 | p25 | median | p75 | p90 | dollar_weighted | over_1_pct | reported | proxy |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H | 1,357 | 0 | 4.18% | 47.30% | 71.66% | 85.16% | 93.33% | 76.16% | 31 | 405,391,840 | 308,728,923 |
| P | 37 | 0 | 0.00% | 0.00% | 45.58% | 68.21% | 86.50% | 64.55% | 0 | 641,055,039 | 413,828,093 |
| S | 273 | 0 | 0.00% | 38.45% | 67.51% | 86.13% | 96.01% | 70.95% | 12 | 391,585,566 | 277,829,991 |
|  | 1,667 | 0 | 0.00% | 45.16% | 70.42% | 85.16% | 93.63% | 69.57% | 43 | 1,438,032,445 | 1,000,387,007 |

**Q8g: 2004 candidates whose proxy exceeds TTL_INDIV_CONTRIB by more than 1%: the 15 largest  (0 s)**

| CAND_ID | CAND_NAME | committees | reported | proxy | excess |
|---|---|---|---|---|---|
| S4CO00163 | SALAZAR, KEN | 1 | 7,838,762 | 8,405,498 | 566,736 |
| S6OR00110 | WYDEN, RONALD LEE | 1 | 2,624,758 | 3,136,742 | 511,984 |
| H4OH02032 | PORTMAN, ROBERT J | 1 | 1,478,284 | 1,687,552 | 209,268 |
| H6PA12030 | MURTHA, JOHN P MR. | 1 | 1,547,392 | 1,713,535 | 166,143 |
| H4NC10062 | LYONS, SANFORD DAVID | 1 | 295,760 | 452,204 | 156,444 |
| H0SC01071 | BROWN, HENRY E JR. | 1 | 288,086 | 422,184 | 134,098 |
| H2IL05092 | EMANUEL, RAHM | 1 | 1,149,636 | 1,271,205 | 121,569 |
| H4WI04159 | FLYNN, MATTHEW J | 1 | 568,739 | 689,872 | 121,133 |
| S2NH00025 | GREGG, JUDD A | 1 | 1,171,484 | 1,284,981 | 113,497 |
| H4OR01089 | AMERI, GOLI YAZDI | 1 | 1,887,861 | 1,978,950 | 91,089 |
| S4IL00198 | WASHINGTON, JOYCE W | 1 | 291,769 | 374,006 | 82,237 |
| S2TN00058 | ALEXANDER, LAMAR | 2 | 1,426,616 | 1,495,175 | 68,559 |
| S4LA00040 | JOHN, CHRIS | 1 | 2,515,293 | 2,572,102 | 56,809 |
| H8LA04134 | MCCRERY, JAMES OTIS III | 1 | 508,799 | 549,603 | 40,804 |
| H2IN09084 | SODREL, MICHAEL E | 2 | 666,101 | 704,939 | 38,838 |

**Q8h: which 2004 columns carry values  (0 s)**

| file | column_name | rows | filled | nonzero |
|---|---|---|---|---|
| weball04 | CAND_ICI | 2,468 | 2,468 | 2,468 |
| weball04 | PTY_CD | 2,468 | 2,468 | 2,468 |
| weball04 | CAND_PTY_AFFILIATION | 2,468 | 2,468 | 2,468 |
| weball04 | TTL_RECEIPTS | 2,468 | 2,468 | 1,997 |
| weball04 | TRANS_FROM_AUTH | 2,468 | 2,468 | 182 |
| weball04 | TTL_DISB | 2,468 | 2,468 | 2,134 |
| weball04 | TRANS_TO_AUTH | 2,468 | 2,468 | 227 |
| weball04 | COH_BOP | 2,468 | 2,468 | 1,428 |
| weball04 | COH_COP | 2,468 | 2,468 | 1,696 |
| weball04 | CAND_CONTRIB | 2,468 | 2,468 | 662 |
| weball04 | CAND_LOANS | 2,468 | 2,468 | 609 |
| weball04 | OTHER_LOANS | 2,468 | 2,468 | 82 |
| weball04 | CAND_LOAN_REPAY | 2,468 | 2,468 | 507 |
| weball04 | OTHER_LOAN_REPAY | 2,468 | 2,468 | 80 |
| weball04 | DEBTS_OWED_BY | 2,468 | 2,468 | 1,018 |
| weball04 | TTL_INDIV_CONTRIB | 2,468 | 2,468 | 1,668 |
| weball04 | CAND_OFFICE_ST | 2,468 | 2,468 | 2,468 |
| weball04 | CAND_OFFICE_DISTRICT | 2,468 | 2,468 | 2,468 |
| weball04 | SPEC_ELECTION | 2,468 | 0 | 0 |
| weball04 | PRIM_ELECTION | 2,468 | 65 | 65 |
| weball04 | RUN_ELECTION | 2,468 | 5 | 5 |
| weball04 | GEN_ELECTION | 2,468 | 851 | 851 |
| weball04 | GEN_ELECTION_PRECENT | 2,468 | 851 | 821 |
| weball04 | OTHER_POL_CMTE_CONTRIB | 2,468 | 2,468 | 1,147 |
| weball04 | POL_PTY_CONTRIB | 2,468 | 2,468 | 691 |
| weball04 | CVG_END_DT | 2,468 | 2,468 | 2,468 |
| weball04 | INDIV_REFUNDS | 2,468 | 2,468 | 809 |
| weball04 | CMTE_REFUNDS | 2,468 | 2,468 | 459 |
| webk04 | CMTE_TP | 6,082 | 6,082 | 6,082 |
| webk04 | CMTE_DSGN | 6,082 | 6,081 | 6,081 |
| webk04 | CMTE_FILING_FREQ | 6,082 | 6,082 | 6,082 |
| webk04 | TTL_RECEIPTS | 6,082 | 5,539 | 4,658 |
| webk04 | TRANS_FROM_AFF | 6,082 | 5,539 | 474 |
| webk04 | INDV_CONTRIB | 6,082 | 5,539 | 4,362 |
| webk04 | OTHER_POL_CMTE_CONTRIB | 6,082 | 5,539 | 1,064 |
| webk04 | CAND_CONTRIB | 6,082 | 5,539 | 0 |
| webk04 | CAND_LOANS | 6,082 | 5,539 | 1 |
| webk04 | TTL_LOANS_RECEIVED | 6,082 | 5,539 | 2 |
| webk04 | TTL_DISB | 6,082 | 5,539 | 5,021 |
| webk04 | TRANF_TO_AFF | 6,082 | 5,539 | 846 |
| webk04 | INDV_REFUNDS | 6,082 | 5,539 | 835 |
| webk04 | OTHER_POL_CMTE_REFUNDS | 6,082 | 5,539 | 150 |
| webk04 | CAND_LOAN_REPAY | 6,082 | 5,539 | 1 |
| webk04 | LOAN_REPAY | 6,082 | 5,539 | 58 |
| webk04 | COH_BOP | 6,082 | 5,539 | 4,060 |
| webk04 | COH_COP | 6,082 | 5,539 | 4,486 |
| webk04 | DEBTS_OWED_BY | 6,082 | 5,539 | 286 |
| webk04 | NONFED_TRANS_RECEIVED | 6,082 | 5,539 | 247 |
| webk04 | CONTRIB_TO_OTHER_CMTE | 6,082 | 5,539 | 3,627 |
| webk04 | IND_EXP | 6,082 | 5,539 | 343 |
| webk04 | PTY_COORD_EXP | 6,082 | 5,539 | 63 |
| webk04 | NONFED_SHARE_EXP | 6,082 | 5,539 | 388 |
| webk04 | CVG_END_DT | 6,082 | 5,539 | 5,539 |

**Reading.**

- `webl04` is again a subset of `weball04` (1,578 of 2,468 candidates), identical on every measure.
- 2004 coverage cannot be read as a fraction of the itemized figure, only of the total. Candidates'
  itemized proxy is 69.57% of `TTL_INDIV_CONTRIB` dollar weighted (median 70.42%). PACs' is 36.11%,
  because payroll-deduction PACs raise mostly unitemized. 43 candidates and 64 committees have a
  proxy above the total by more than 1%. Those are proxy effects (no conduit rule, no self-funding
  match) or filers' arithmetic, too small to chase ($0.8M for the committees).
- **What a pre-2008 page can show** (Q8h):
  - Candidates (`weball`): receipts, disbursements, transfers to and from authorized committees, cash
    at the start and end, the candidate's contributions and loans, other loans and repayments, debts
    owed by, total individual money, other-committee and party money, refunds, and coverage end.
  - Committees (`webk`): the same at committee grain. It has no party-committee line, and its
    candidate contribution and loan lines are all but empty, as expected for PACs.
  - Neither file has an itemized/unitemized split, debts owed to, or a coverage start. `COH_BOP` is
    filled for every `weball04` row, so a candidate's starting cash is available.
  - House and Senate candidate committees have no committee-grain row before 2008 (`webk04` holds
    only 54 candidate committees).

## Decisions

1. **Candidate figures' source.** 2008 and later: the sum, over the committees fundlens credits to
   the candidate (04_contribution.sql's `linked` rule), of their deduplicated `committee_summary`
   rows. The match rate against `candidate_summary` is 99.11% (99.95% with any receipts). Every
   mismatch is a CAND_PCC campaign turned PAC, an empty `candidate_summary` row, or a $0 against a
   blank (Q3h). Before 2008:
   `weball`. `webl` never adds a figure, being `weball`'s rows (2024 and 2004).
2. **Precedence per cycle range and grain.**

   | Cycles | Committee grain | Candidate grain |
   | --- | --- | --- |
   | 2008– | `committee_summary`, one row per committee; `webk` only for a measure `committee_summary` leaves blank (Form 5 and Form 7 filers). Q2: 9,830 of 9,833 shared committees agree with both filled | Sum of credited committees from `committee_summary` (decision 1); `weball`/`candidate_summary` only as checks |
   | 1996–2006 | `webk` (PACs, parties, and the few candidate committees it holds) | `weball` |
   | 1980–1994 | none: no committee-grain file | `weball` |

   This amends the milestone contract. `webl` drops out, because it holds `weball`'s rows.
   `committee_summary` must be deduplicated on `CMTE_ID`, because it repeats a committee per linked
   candidate. And `webk` is a per-measure fallback rather than a lower tier that loses to it.
3. **`TTL_INDIV_CONTRIB` (`weball`/`webl`) and `INDV_CONTRIB` (`webk`) hold itemized plus
   unitemized individual money** (2,049 against 8 candidates; 5,389 against 21 committees). Only
   `committee_summary` and `candidate_summary` split it. Before 2008 no file does.
4. **`coverage` uses measure B** (`total_individual + total_from_organizations`) against
   `INDV_ITEM_CONTB`: 5,114 committees within 1% against A's 4,440, and super PACs 802 against 386
   (Q5g). Three caveats for NEU-2141's definition:
   - Coverage is not defined for conduits, whose FEC figure includes earmarks fundlens credits
     elsewhere.
   - It is not defined where `INDV_ITEM_CONTB` is blank (Form 4 and Form 5 filers).
   - It can exceed 100% where the filer put organization money on line 15 (90 committees, $75.1M
     by D8's fit). NEU-2141 decides how to show a figure above 100%. Comparing against itemized
     plus line 15 instead matches fewer committees (Q5k).
5. **Over-1% causes and tickets**: NEU-2192 (hybrid non-contribution account), NEU-2193 (party
   accounts and other off-11(a)(i) types), NEU-2194 (15C self-funding), NEU-2195 (ORG-typed
   committee gifts), NEU-2196 (repeated rows), NEU-2197 (the 119 unexplained committees). Found on
   the way: NEU-2198 (memo-only LLC attributions, under-count) and NEU-2199 (conduit refunds of
   earmarks).
6. **For NEU-2142: do not catalogue `candidate_summary` or `webl`.** `candidate_summary` is the sum
   of `committee_summary`'s own P/A rows (2,315 of 2,321). Decision 1 does not read it, and it adds
   no column a candidate page needs that `committee_summary` lacks. `webl` repeats `weball`.
   Catalogue `weball` (1980–), `webk` (1996–) and `committee_summary` (2008–).

## For NEU-2141, NEU-2142 and NEU-2143

- **NEU-2141 (spec §4, glossary).**
  - Decisions 1–4.
  - `reported_total`'s NULL rules by cycle range: before 2008 there is no itemized/unitemized split,
    no debts owed to and no coverage start at either grain. Before 1996 there are no committee-grain
    figures. Before 2008 there are none for House and Senate campaign committees.
  - The handoff question (C00703975's one row under Biden and Harris, Q3k).
  - A related question: whether a CAND_PCC-credited committee that FEC no longer designates P or A
    adds its whole cycle-to-date row to the candidate. That row includes what it raised as a PAC
    after converting (Trump $495.9M, Kunce $23.2M).
  - Q6's `fec_line` CASE, for any rule on which lines `total_individual` counts.
  - The coverage caveats in decision 4.
- **NEU-2142 (catalogue and extract).**
  - Catalogue `weball` (1980–), `webk` (1996–) and `committee_summary` (2008–). Skip `webl` and
    `candidate_summary`.
  - The zips are pipe-delimited with no header row, and FEC publishes no header file for them
    (404). Vendor the column lists from the file descriptions above.
  - `committee_summary` is a CSV with a header row, dates as `YYYYMMDD`, and a leading `Link_Image`
    column. `candidate_summary` dates are `MM/DD/YYYY`.
  - FEC rebuilds the 2024 files nightly (`Last-Modified` 2026-11-05 06:39–10:14 UTC). 2004's are
    static since 2017-08-31.
- **NEU-2143 (silver `reported_total`).** The definition-of-done count is **13,995 committees**
  for 2024 (14,066 rows before deduplication on `CMTE_ID`). 13,994 of them match a silver committee.
  Deduplicate on `CMTE_ID`. Its rows differ only in `CAND_ID`, which the checks should assert. Take
  `webk` for I- and C-type figures that `committee_summary` leaves blank.
