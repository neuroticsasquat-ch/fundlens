# Organization money in 2024 `indiv` and `oth`, and a blank-entity-type organization classifier

Measured for [NEU-2129](https://linear.app/neuroticsasquatch/issue/NEU-2129) (milestone M3.5
Organization money; spec [`NEU-2129-organization-money-measurement.md`](../specs/NEU-2129-organization-money-measurement.md)).
It counts the money fundlens drops today because its giver is neither an individual nor a committee,
and it fixes two rules for the tickets after it: what happens to PAC/COM/CCM/PTY rows with no
committee ID, and which name pattern calls a blank-entity-type giver an organization. Nothing under
`sql/`, `src/` or `frontend/` changed, and no silver, gold or marker was written.

| What | Value |
| --- | --- |
| Run | 2026-11-05, 00:30–01:10 UTC, by hand over SSH on `music-box-dancer` |
| Code | `main` at `71f5c7767bba97c25f2e0023429b293c161fbfdd` (the `pipeline` container's `service.version`) |
| Container | `pipeline-lvch8zyndujjzkz16ksys8im-20261105T001507` |
| DuckDB | 2.0.0; `Limits(memory_limit='28GB', max_temp_directory_size='60GB', threads=6)`; `connect`'s build-side optimizer off (NEU-2076) |
| 2024 `indiv`, `oth`, `cm` | `bronze/cycle=2024/<file>/2026-10-31.zip`: FEC files downloaded 2026-10-31, the live build's (`20261103T175128Z`) |
| 1998, 2000 `indiv` | `bronze/cycle=1998/indiv/2026-11-05.zip` (26.5 MB), `bronze/cycle=2000/indiv/2026-11-05.zip` (45.8 MB): downloaded 2026-11-05 by `fundlens extract --cycle <c> --file indiv`, kept in bronze for the M4 backfill (NEU-2060) |
| `webk24.zip` | FEC's 2024 PAC summary, `Last-Modified: Wed, 04 Nov 2026 06:40:31 GMT`, downloaded 2026-11-05T01:02:14Z (the run shown in Q7) into the work dir only: not catalogued, not in bronze |
| Live gold | `gold.committee_cycle`, build `20261103T175128Z`, read 2026-11-05 |

## Headline

- **Organizations gave $2.26 billion in 2024 that fundlens does not count.** 18,233 counted `indiv`
  rows carry entity type ORG. $1.42B of it went to super PACs and $815M to other committees that are neither a
  candidate's nor a party's; candidates got $9.3M. Organization receipts in `oth` whose giver is no committee are small beside it:
  $24.0M of ORG with a blank or non-committee giver ID, $23.1M of it gifts rather than loans or
  15J lines (Q2).
- **PAC/COM/CCM/PTY rows with no committee ID hold another $788.4M**, $778.5M of it in `indiv`.
  80.6% of those dollars name exactly one `cm` committee, short of the 95% bar, so by the rule this
  ticket was given they are **dropped** (Q3). Q7 shows they are real committee money that FEC
  counts. NEU-2130 should look at the note under [Decisions](#decisions).
- **`indiv` and `oth` barely overlap on organizations**: 2 of 1,080 `oth` organization receipts
  ($133,900) mirror an `indiv` row, and none shares a `SUB_ID` (Q4).
- **The classifier is V8**: a name with no comma, or ending in a strict legal suffix, or holding
  one of 16 organization words in a comma-separated segment of two tokens or more. On filled-type
  2024 rows it scores 99.66% precision and 97.99% recall by rows. It calls 2.6% of the blank rows
  in 1998 and in 2000 organizations: $166.7M and $389.0M (Q5, Q6).
- **Five super PACs show the gap.** Fairshake reported $260.1M of receipts. fundlens counts $7.3M,
  and ORG-typed `indiv` rows hold $166.7M of the difference (Q7).

## How to re-run

On the VM, in `tmux`, with the `fl` helper from [`docs/runbooks/first-run.md`](../runbooks/first-run.md).
Save the setup script as `setup.py`, each block below as `qN.py`, and the classifier definitions as
`classifier.py`, then run each block after the setup:

```bash
# VM, in tmux. Container names change on every deploy (first-run.md).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
cat setup.py q1.py | docker exec -i "$(fl pipeline)" python - 2>&1 | grep -v '^{' | tee q1.out
cat setup.py classifier.py q5b.py | docker exec -i "$(fl pipeline)" python - 2>&1 | grep -v '^{' | tee q5b.out
```

Run them one at a time: they share the container's DuckDB limits, and none may run beside a
pipeline step. Do not merge to `main` while they run, because a deploy restarts `pipeline`. The
first block unpacks the 2024 files into `/data/fundlens/scratch/measure-organization-money-2024`,
and later blocks reuse them. The run peaked at 19 GB there. Delete the directory at the end. This run did, on 2026-11-05 after
its last block:

```bash
# VM
docker exec "$(fl pipeline)" rm -rf /data/fundlens/scratch/measure-organization-money-2024
```

Every table's title carries the seconds its query took. Dollars are `sum(TRANSACTION_AMT)` as
filed (net) unless a column says gross (`sum(abs(...))`). The refund sign rule (NEU-2073) is
silver's, not this measurement's.

### Setup

The views `indiv`, `oth` and `cm` are the transform's own (`unzip_bulk`, `register_bulk`,
`connect`), with the vendored column names and catalogue types. `bulk()` differs from the spec's
§4.1 in one way: another cycle's view goes in a schema of its own (`c1998.indiv`), because
`register_bulk` always creates a view named after the file. `counted`, `receipt` and `recipient` are
the spec's §2 definitions. `receipt`'s giver status adds one bucket the spec does not name:
**blank, names a JFC**, a blank `OTHER_ID` whose `NAME` is a designation-J committee's.
`05_committee_transfer.sql` already counts those rows as transfers (NEU-2124).

```python
import time
from decimal import Decimal

from fundlens import paths
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import Limits, connect, register_bulk, unzip_bulk

settings = get_settings()
store = R2.from_settings(settings)
scratch = paths.scratch_dir(settings.data_dir)
work = scratch / "measure-organization-money-2024"
con = connect(Limits.from_settings(settings), scratch)


def bulk(name: str, cycle: int = 2024) -> None:
    """The view `name` over `cycle`'s newest bronze `name`, unpacked into work/<cycle> on first use
    and reused after. Another cycle's view is in the schema `c<cycle>`: `c1998.indiv`."""
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


def show(title: str, sql: str) -> None:
    """Run `sql` and print its result as a Markdown table, with the seconds it took."""
    start = time.monotonic()
    rel = con.sql(sql)
    rows = rel.fetchall()
    print(f"\n#### {title}  ({time.monotonic() - start:.0f} s)\n")
    print("| " + " | ".join(rel.columns) + " |")
    print("|" + "---|" * len(rel.columns))
    for row in rows:
        cells = (
            f"{v:,.0f}" if isinstance(v, (int, Decimal)) and not isinstance(v, bool)
            else f"{v:.2%}" if isinstance(v, float) else "" if v is None else str(v)
            for v in row
        )
        print("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")


for name in ("indiv", "oth", "cm"):
    bulk(name)

# The groupings every query shares (spec §2).
con.execute("""
CREATE VIEW recipient AS
SELECT CMTE_ID, CMTE_NM, CMTE_TP, CMTE_DSGN,
    CASE WHEN CMTE_TP IN ('O', 'U') THEN 'super PAC' WHEN CMTE_TP IN ('X', 'Y') THEN 'party'
        WHEN CMTE_TP IN ('H', 'S', 'P') THEN 'candidate' ELSE 'other' END AS recipient_group
FROM cm;

-- A counted `indiv` row: 04_contribution.sql's memo and 24T filters, nothing else.
CREATE VIEW counted AS
SELECT indiv.*,
    coalesce(nullif(trim(indiv.ENTITY_TP), ''), '<blank>') AS entity_type,
    coalesce(recipient.recipient_group, 'not in cm') AS recipient_group,
    regexp_matches(indiv.TRANSACTION_TP, '^[24][0-9]Y$') AS is_refund
FROM indiv
LEFT JOIN recipient USING (CMTE_ID)
WHERE indiv.MEMO_CD IS DISTINCT FROM 'X' AND indiv.TRANSACTION_TP IS DISTINCT FROM '24T';

-- Each designation-J committee by name key; a key two share names neither (05_committee_transfer.sql).
CREATE VIEW jfc_named AS
SELECT regexp_replace(upper(CMTE_NM), '[^A-Z0-9]', '', 'g') AS name_key
FROM cm WHERE CMTE_DSGN = 'J' GROUP BY name_key HAVING count(*) = 1;

-- An `oth` receipt (05_committee_transfer.sql), with its giver's status.
CREATE VIEW receipt AS
SELECT oth.*,
    coalesce(nullif(trim(oth.ENTITY_TP), ''), '<blank>') AS entity_type,
    CASE
        WHEN trim(oth.OTHER_ID) LIKE 'C%' AND giver.CMTE_ID IS NOT NULL THEN 'committee'
        WHEN trim(oth.OTHER_ID) LIKE 'C%' THEN 'unknown id'
        WHEN coalesce(trim(oth.OTHER_ID), '') <> '' THEN 'non-committee id'
        WHEN jfc_named.name_key IS NOT NULL THEN 'blank, names a JFC'
        ELSE 'blank'
    END AS giver_status,
    coalesce(recipient.recipient_group, 'not in cm') AS recipient_group
FROM oth
LEFT JOIN cm AS giver ON giver.CMTE_ID = trim(oth.OTHER_ID)
LEFT JOIN jfc_named
    ON coalesce(trim(oth.OTHER_ID), '') = ''
    AND jfc_named.name_key = regexp_replace(upper(oth.NAME), '[^A-Z0-9]', '', 'g')
LEFT JOIN recipient ON recipient.CMTE_ID = oth.CMTE_ID
WHERE left(oth.TRANSACTION_TP, 1) IN ('1', '3') AND oth.MEMO_CD IS DISTINCT FROM 'X';
""")
```

```python
# q0.py: what is in bronze, and the files' sizes.
for c in (1998, 2000, 2024):
    for f in ("indiv", "oth", "cm"):
        print(c, f, sorted(store.list_keys(paths.bronze_dir(c, f))))
print(Limits.from_settings(settings))
show("cm: rows and distinct ids", "SELECT count(*) AS rows, count(DISTINCT CMTE_ID) AS ids FROM cm")
show("indiv and oth: rows", "SELECT 'indiv' AS file, count(*) AS rows FROM indiv UNION ALL SELECT 'oth', count(*) FROM oth")
```

1998 indiv ['bronze/cycle=1998/indiv/2026-11-05.zip']
1998 oth []
1998 cm []
2000 indiv ['bronze/cycle=2000/indiv/2026-11-05.zip']
2000 oth []
2000 cm []
2024 indiv ['bronze/cycle=2024/indiv/2026-10-31.zip']
2024 oth ['bronze/cycle=2024/oth/2026-10-31.zip']
2024 cm ['bronze/cycle=2024/cm/2026-10-31.zip']
Limits(memory_limit='28GB', max_temp_directory_size='60GB', threads=6)

**cm: rows and distinct ids  (0 s)**

| rows | ids |
|---|---|
| 20,937 | 20,937 |

**indiv and oth: rows  (9 s)**

| file | rows |
|---|---|
| indiv | 58,210,165 |
| oth | 18,667,129 |

`cm` has one row per committee ID, so joining it never multiplies rows.

## Q1: `indiv` by entity type and recipient group

How much counted `indiv` money (no memo line, no 24T) each entity type gives, and to which kind of
committee. 04_contribution.sql keeps IND, CAN and blank today. A gift to a committee missing from
`cm` shows as `not in cm`.

```python
show("Q1a: counted indiv rows by entity type and recipient group", """
SELECT entity_type, coalesce(recipient_group, '(all)') AS recipient_group,
    count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars,
    count(*) FILTER (WHERE is_refund) AS refund_rows,
    coalesce(sum(TRANSACTION_AMT) FILTER (WHERE is_refund), 0) AS refund_dollars,
    count(DISTINCT CMTE_ID) AS committees
FROM counted
GROUP BY GROUPING SETS ((entity_type, recipient_group), (entity_type))
ORDER BY entity_type, recipient_group NULLS LAST
""")
show("Q1b: ORG/PAC/COM/CCM/PTY counted indiv rows by transaction type", """
SELECT entity_type, TRANSACTION_TP, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars
FROM counted
WHERE entity_type IN ('ORG', 'PAC', 'COM', 'CCM', 'PTY')
GROUP BY ALL
ORDER BY entity_type, net_dollars DESC
""")
from fundlens.transform.runner import _register_conduits

_register_conduits(con)
show("Q1c: counted indiv rows that are a conduit's side of an earmark, which 04_contribution.sql drops", """
SELECT entity_type, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars
FROM counted
WHERE CMTE_ID IN (SELECT committee_id FROM conduit)
    AND regexp_matches(coalesce(MEMO_TEXT, ''), 'EARMARKED FOR .*\\(C[0-9]{8}\\)')
GROUP BY ALL ORDER BY entity_type
""")
```


**Q1a: counted indiv rows by entity type and recipient group  (12 s)**

| entity_type | recipient_group | rows | net_dollars | refund_rows | refund_dollars | committees |
|---|---|---|---|---|---|---|
| `<blank>` | (all) | 343 | 332,584 | 17 | 8,819 | 62 |
| `<blank>` | candidate | 38 | 80,717 | 12 | 5,509 | 12 |
| `<blank>` | other | 216 | 189,619 | 2 | 1,100 | 39 |
| `<blank>` | party | 8 | 2,050 | 0 | 0 | 3 |
| `<blank>` | super PAC | 81 | 60,198 | 3 | 2,210 | 8 |
| CAN | (all) | 9,101 | 67,213,319 | 86 | 229,597 | 1,019 |
| CAN | candidate | 8,037 | 40,336,430 | 65 | 210,891 | 931 |
| CAN | not in cm | 7 | 25,800,000 | 0 | 0 | 1 |
| CAN | other | 242 | 685,879 | 14 | 16,252 | 43 |
| CAN | party | 811 | 306,480 | 7 | 2,454 | 41 |
| CAN | super PAC | 4 | 84,530 | 0 | 0 | 3 |
| CCM | (all) | 259 | 19,015,290 | 4 | 150,200 | 90 |
| CCM | candidate | 108 | 3,782,363 | 0 | 0 | 30 |
| CCM | not in cm | 9 | 9,830,000 | 0 | 0 | 1 |
| CCM | other | 73 | 2,784,078 | 1 | 200 | 23 |
| CCM | party | 20 | 158,953 | 0 | 0 | 10 |
| CCM | super PAC | 49 | 2,459,896 | 3 | 150,000 | 26 |
| COM | (all) | 1,229 | 173,107,418 | 23 | 5,758,025 | 334 |
| COM | candidate | 66 | 103,420 | 4 | 11,700 | 35 |
| COM | other | 387 | 22,558,793 | 10 | 152,800 | 87 |
| COM | party | 21 | 84,100 | 4 | 3,250 | 14 |
| COM | super PAC | 755 | 150,361,105 | 5 | 5,590,275 | 198 |
| IND | (all) | 51,110,941 | 9,818,080,223 | 1,448,669 | 174,516,117 | 8,623 |
| IND | candidate | 14,160,932 | 2,238,368,507 | 115,429 | 56,537,356 | 2,340 |
| IND | other | 30,056,770 | 4,642,370,408 | 1,199,974 | 97,254,726 | 5,028 |
| IND | party | 6,341,743 | 765,303,972 | 116,279 | 11,297,993 | 357 |
| IND | super PAC | 551,496 | 2,172,037,336 | 16,987 | 9,426,042 | 898 |
| ORG | (all) | 18,233 | 2,257,182,796 | 1,194 | 12,696,581 | 2,303 |
| ORG | candidate | 4,975 | 9,332,261 | 626 | 629,148 | 704 |
| ORG | other | 5,933 | 815,158,663 | 476 | 8,787,506 | 828 |
| ORG | party | 1,057 | 14,982,513 | 45 | 225,063 | 114 |
| ORG | super PAC | 6,268 | 1,417,709,359 | 47 | 3,054,864 | 657 |
| PAC | (all) | 2,701 | 606,517,908 | 16 | 12,926,411 | 526 |
| PAC | candidate | 108 | 226,344 | 3 | -7,000 | 49 |
| PAC | other | 1,127 | 223,647,672 | 1 | 275,000 | 151 |
| PAC | party | 43 | 7,224,271 | 0 | 0 | 12 |
| PAC | super PAC | 1,423 | 375,419,621 | 12 | 12,658,411 | 314 |
| PTY | (all) | 31 | 467,291 | 4 | 58,200 | 20 |
| PTY | candidate | 4 | 6,500 | 2 | 5,200 | 4 |
| PTY | other | 11 | 268,083 | 2 | 53,000 | 7 |
| PTY | party | 5 | 13,544 | 0 | 0 | 2 |
| PTY | super PAC | 11 | 179,164 | 0 | 0 | 7 |

**Q1b: ORG/PAC/COM/CCM/PTY counted indiv rows by transaction type  (9 s)**

| entity_type | TRANSACTION_TP | rows | net_dollars |
|---|---|---|---|
| CCM | 15C | 87 | 13,573,375 |
| CCM | 10 | 132 | 5,189,393 |
| CCM | 20Y | 3 | 150,000 |
| CCM | 32 | 2 | 59,284 |
| CCM | 15 | 18 | 31,288 |
| CCM | 15E | 15 | 9,250 |
| CCM | 11 | 1 | 2,500 |
| CCM | 22Y | 1 | 200 |
| COM | 10 | 1,109 | 167,156,824 |
| COM | 20Y | 15 | 5,743,075 |
| COM | 11 | 40 | 119,900 |
| COM | 15 | 32 | 42,003 |
| COM | 32 | 1 | 15,000 |
| COM | 22Y | 8 | 14,950 |
| COM | 15E | 23 | 13,669 |
| COM | 31 | 1 | 1,997 |
| ORG | 10 | 9,500 | 2,197,653,000 |
| ORG | 15 | 3,773 | 29,927,068 |
| ORG | 11 | 3,429 | 13,946,007 |
| ORG | 20Y | 285 | 8,758,055 |
| ORG | 22Y | 810 | 3,853,205 |
| ORG | 31T | 20 | 940,700 |
| ORG | 32T | 15 | 807,700 |
| ORG | 15E | 281 | 522,074 |
| ORG | 31 | 7 | 285,173 |
| ORG | 32 | 9 | 202,424 |
| ORG | 31E | 1 | 123,900 |
| ORG | 21Y | 99 | 85,321 |
| ORG | 30T | 1 | 75,900 |
| ORG | 30 | 1 | 2,189 |
| ORG | 15C | 2 | 80 |
| PAC | 10 | 2,550 | 586,199,236 |
| PAC | 20Y | 13 | 12,933,411 |
| PAC | 24I | 8 | 6,925,000 |
| PAC | 15E | 61 | 118,787 |
| PAC | 11 | 48 | 117,200 |
| PAC | 32 | 3 | 100,000 |
| PAC | 30 | 1 | 45,000 |
| PAC | 31 | 5 | 44,600 |
| PAC | 32E | 1 | 25,000 |
| PAC | 15 | 8 | 16,674 |
| PAC | 22Y | 3 | -7,000 |
| PTY | 10 | 22 | 404,247 |
| PTY | 20Y | 2 | 53,000 |
| PTY | 22Y | 2 | 5,200 |
| PTY | 15 | 3 | 3,700 |
| PTY | 11 | 1 | 1,000 |
| PTY | 15E | 1 | 144 |

**Q1c: counted indiv rows that are a conduit's side of an earmark, which 04_contribution.sql drops  (11 s)**

| entity_type | rows | net_dollars |
|---|---|---|
| IND | 106,102 | 7,299,752 |

No organization row is a conduit's side of an earmark (Q1c): all 106,102 such rows are IND, so
04_contribution.sql's earmark rule removes nothing from organizations in 2024.

**Reading.** ORG is the money: 18,233 rows, $2,257,182,796 net, 63% to super PACs and 36% to other committees (neither candidates' nor parties'). PAC ($606.5M) and COM ($173.1M) rows are mostly committees giving to super PACs, reported on
the recipient's Schedule A without the giver's ID (Q3). In 2024 the blank entity type is almost
empty: 343 rows, $332,584. The blank bucket is a pre-2002 problem, not a live-cycle one (Q6). ORG
money is almost all type 10, a gift to a super PAC or a non-contribution account ($2.20B). Type 15,
an ordinary contribution, holds $29.9M of it.

## Q2: `oth` receipts whose giver is not a committee

`oth` receipts (type 1x or 3x, no memo line) by giver status, entity type and transaction type.
`committee` is shown for scale. `blank, names a JFC` is already a transfer. **`unknown id` is
already counted too:** 05_committee_transfer.sql takes any `C`-prefixed `OTHER_ID` as the giver,
in `cm` or not. So `organization_receipt` takes only `non-committee id` and `blank`.

```python
show("Q2a: oth receipts by giver status and entity type", """
SELECT giver_status, entity_type, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars,
    count(*) FILTER (WHERE recipient_group = 'not in cm') AS rows_to_committee_not_in_cm
FROM receipt
GROUP BY ALL
ORDER BY giver_status, net_dollars DESC
""")
show("Q2b: oth receipts whose giver is not a committee, by entity type and transaction type", """
SELECT giver_status, entity_type, TRANSACTION_TP, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars
FROM receipt
WHERE giver_status IN ('unknown id', 'non-committee id', 'blank')
GROUP BY ALL
ORDER BY giver_status, entity_type, net_dollars DESC
""")
show("Q2c: oth receipts whose giver is not a committee, by recipient group", """
SELECT entity_type, recipient_group, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars
FROM receipt
WHERE giver_status IN ('unknown id', 'non-committee id', 'blank')
GROUP BY ALL
ORDER BY entity_type, net_dollars DESC
""")
```


**Q2a: oth receipts by giver status and entity type  (3 s)**

| giver_status | entity_type | rows | net_dollars | rows_to_committee_not_in_cm |
|---|---|---|---|---|
| blank | IND | 843 | 26,374,182 | 0 |
| blank | ORG | 175 | 23,880,067 | 0 |
| blank | CAN | 54 | 21,395,750 | 0 |
| blank | COM | 10 | 8,326,327 | 0 |
| blank | PTY | 5 | 1,479,589 | 0 |
| blank | PAC | 5 | 90,000 | 0 |
| blank | CCM | 7 | 48,003 | 0 |
| blank | `<blank>` | 1 | 9,609 | 0 |
| blank, names a JFC | COM | 27 | 37,279,600 | 0 |
| blank, names a JFC | ORG | 4 | 183,545 | 0 |
| blank, names a JFC | CCM | 1 | 11,506 | 0 |
| committee | COM | 15,652 | 1,937,814,471 | 0 |
| committee | PAC | 58,974 | 957,989,345 | 0 |
| committee | PTY | 6,312 | 713,982,521 | 0 |
| committee | ORG | 752 | 392,588,137 | 0 |
| committee | CCM | 5,575 | 212,788,538 | 0 |
| committee | `<blank>` | 38 | 134,758 | 0 |
| committee | IND | 29 | 104,821 | 0 |
| committee | CAN | 4 | 27,150 | 0 |
| non-committee id | CAN | 3,569 | 353,165,305 | 0 |
| non-committee id | IND | 163 | 21,039,511 | 0 |
| non-committee id | CCM | 213 | 5,023,452 | 2 |
| non-committee id | ORG | 4 | 109,000 | 0 |
| non-committee id | PTY | 1 | 7,000 | 0 |
| non-committee id | COM | 1 | 100 | 0 |
| unknown id | COM | 204 | 13,520,946 | 0 |
| unknown id | PTY | 85 | 3,131,005 | 0 |
| unknown id | PAC | 275 | 2,116,174 | 0 |
| unknown id | CCM | 86 | 1,722,434 | 0 |
| unknown id | ORG | 9 | 771,855 | 0 |
| unknown id | `<blank>` | 27 | 51,402 | 0 |
| unknown id | CAN | 2 | 1,000 | 0 |
| unknown id | IND | 1 | -454 | 0 |

**Q2b: oth receipts whose giver is not a committee, by entity type and transaction type  (3 s)**

| giver_status | entity_type | TRANSACTION_TP | rows | net_dollars |
|---|---|---|---|---|
| blank | `<blank>` | 15J | 1 | 9,609 |
| blank | CAN | 16C | 47 | 21,201,250 |
| blank | CAN | 16G | 7 | 194,500 |
| blank | CCM | 16G | 3 | 29,803 |
| blank | CCM | 18K | 1 | 12,500 |
| blank | CCM | 11J | 1 | 5,000 |
| blank | CCM | 15J | 2 | 700 |
| blank | COM | 32J | 1 | 8,308,404 |
| blank | COM | 18K | 4 | 7,170 |
| blank | COM | 18G | 2 | 5,503 |
| blank | COM | 11J | 3 | 5,250 |
| blank | IND | 16C | 7 | 23,750,000 |
| blank | IND | 16G | 102 | 1,723,323 |
| blank | IND | 15J | 687 | 647,673 |
| blank | IND | 32G | 10 | 186,071 |
| blank | IND | 31J | 9 | 35,731 |
| blank | IND | 32K | 5 | 31,816 |
| blank | IND | 32J | 11 | 2,878 |
| blank | IND | 10J | 9 | 1,290 |
| blank | IND | 31K | 1 | 300 |
| blank | IND | 11J | 1 | 100 |
| blank | IND | 31G | 1 | -5,000 |
| blank | ORG | 18U | 84 | 22,224,103 |
| blank | ORG | 16F | 3 | 512,581 |
| blank | ORG | 18G | 3 | 502,000 |
| blank | ORG | 16G | 6 | 273,500 |
| blank | ORG | 31K | 1 | 123,900 |
| blank | ORG | 32J | 2 | 117,400 |
| blank | ORG | 11J | 10 | 76,500 |
| blank | ORG | 10J | 3 | 30,000 |
| blank | ORG | 15J | 63 | 20,083 |
| blank | PAC | 10J | 1 | 70,000 |
| blank | PAC | 18K | 4 | 20,000 |
| blank | PTY | 32G | 2 | 1,389,560 |
| blank | PTY | 32K | 1 | 45,000 |
| blank | PTY | 31K | 1 | 45,000 |
| blank | PTY | 11J | 1 | 29 |
| non-committee id | CAN | 16C | 3,569 | 353,165,305 |
| non-committee id | CCM | 16C | 213 | 5,023,452 |
| non-committee id | COM | 16C | 1 | 100 |
| non-committee id | IND | 16C | 163 | 21,039,511 |
| non-committee id | ORG | 16C | 4 | 109,000 |
| non-committee id | PTY | 16C | 1 | 7,000 |
| unknown id | `<blank>` | 18G | 5 | 49,511 |
| unknown id | `<blank>` | 18K | 22 | 1,891 |
| unknown id | CAN | 18K | 2 | 1,000 |
| unknown id | CCM | 18G | 29 | 981,663 |
| unknown id | CCM | 18K | 56 | 737,674 |
| unknown id | CCM | 15Z | 1 | 3,097 |
| unknown id | COM | 18G | 109 | 10,124,883 |
| unknown id | COM | 31G | 13 | 1,460,653 |
| unknown id | COM | 32G | 12 | 1,212,407 |
| unknown id | COM | 18K | 60 | 364,633 |
| unknown id | COM | 18J | 3 | 159,032 |
| unknown id | COM | 32K | 3 | 118,184 |
| unknown id | COM | 31K | 3 | 48,259 |
| unknown id | COM | 32F | 1 | 32,895 |
| unknown id | IND | 18G | 1 | -454 |
| unknown id | ORG | 18G | 7 | 731,255 |
| unknown id | ORG | 31K | 1 | 35,000 |
| unknown id | ORG | 18K | 1 | 5,600 |
| unknown id | PAC | 18G | 107 | 1,344,995 |
| unknown id | PAC | 18K | 162 | 540,403 |
| unknown id | PAC | 18J | 1 | 95,000 |
| unknown id | PAC | 31K | 2 | 90,000 |
| unknown id | PAC | 32K | 1 | 45,000 |
| unknown id | PAC | 15Z | 2 | 776 |
| unknown id | PTY | 18G | 56 | 3,033,669 |
| unknown id | PTY | 18K | 14 | 90,640 |
| unknown id | PTY | 15Z | 14 | 6,277 |
| unknown id | PTY | 18J | 1 | 419 |

**Q2c: oth receipts whose giver is not a committee, by recipient group  (3 s)**

| entity_type | recipient_group | rows | net_dollars |
|---|---|---|---|
| `<blank>` | other | 6 | 59,120 |
| `<blank>` | party | 22 | 1,891 |
| CAN | candidate | 3,618 | 374,434,055 |
| CAN | other | 6 | 127,500 |
| CAN | party | 1 | 500 |
| CCM | candidate | 230 | 4,636,481 |
| CCM | not in cm | 2 | 1,200,000 |
| CCM | party | 65 | 929,361 |
| CCM | other | 9 | 28,047 |
| COM | party | 127 | 16,161,433 |
| COM | candidate | 47 | 5,530,818 |
| COM | other | 41 | 155,122 |
| IND | candidate | 481 | 46,500,505 |
| IND | other | 231 | 732,907 |
| IND | party | 289 | 120,327 |
| IND | super PAC | 6 | 59,500 |
| ORG | party | 160 | 23,328,840 |
| ORG | candidate | 20 | 720,042 |
| ORG | other | 8 | 712,040 |
| PAC | party | 44 | 889,689 |
| PAC | other | 177 | 637,492 |
| PAC | candidate | 58 | 608,993 |
| PAC | super PAC | 1 | 70,000 |
| PTY | party | 66 | 4,489,467 |
| PTY | other | 5 | 92,348 |
| PTY | candidate | 20 | 35,779 |

**Reading.** Outside the committees, `oth` holds little organization money. ORG with a blank
`OTHER_ID` comes to 175 rows and $23.9M, $22.2M of it 18U (a contribution from an unregistered
committee), received mostly by parties (Q2c). The `non-committee id` rows are almost all 16C, loans
from candidates ($353.2M under CAN), where `OTHER_ID` is a candidate ID. They are loans, not gifts,
and stay out, as do the other loan types (16F from a bank, 16G from a person). 15J lines that are not memo lines are scarce: 63 ORG rows, $20,083.

## Q3: PAC/COM/CCM/PTY rows without a committee ID

Counted `indiv` rows and Q2's `blank` receipts with entity type PAC, COM, CCM or PTY and a blank
`OTHER_ID`, split by whether their name key (uppercased, letters and digits only, as both silver files
compare names) names one, several or no `cm` committee. Then the 95% bar. Then the same entity
types where `indiv` does carry a `cm` committee ID, and whether `oth` holds the same gift (Q3d).
Then, for the `indiv` rows naming one committee, whether `oth` holds the gift from that committee
(Q3e). Q3c's `entity_type` is `any_value`: a name filed under two types shows one.

```python
con.execute("""
-- How many `cm` committees each name key names.
CREATE TABLE cm_named AS
SELECT regexp_replace(upper(CMTE_NM), '[^A-Z0-9]', '', 'g') AS name_key, count(*) AS committees,
    min(CMTE_ID) AS committee_id
FROM cm GROUP BY name_key;

-- PAC/COM/CCM/PTY rows with no committee id: a blank OTHER_ID (spec §4.2 Q3).
CREATE TABLE no_id AS
SELECT 'indiv' AS file, entity_type, SUB_ID, CMTE_ID, NAME, TRANSACTION_AMT, TRANSACTION_DT
FROM counted
WHERE entity_type IN ('PAC', 'COM', 'CCM', 'PTY') AND coalesce(trim(OTHER_ID), '') = ''
UNION ALL
SELECT 'oth', entity_type, SUB_ID, CMTE_ID, NAME, TRANSACTION_AMT, TRANSACTION_DT
FROM receipt
WHERE entity_type IN ('PAC', 'COM', 'CCM', 'PTY') AND giver_status = 'blank';
""")
show("Q3a: PAC/COM/CCM/PTY rows with no committee id, by how many cm committees the name names", """
SELECT file, entity_type,
    CASE coalesce(cm_named.committees, 0) WHEN 0 THEN 'none' WHEN 1 THEN 'one' ELSE 'several' END AS names,
    count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars
FROM no_id
LEFT JOIN cm_named ON cm_named.name_key = regexp_replace(upper(no_id.NAME), '[^A-Z0-9]', '', 'g')
GROUP BY GROUPING SETS ((file, entity_type, names), (names))
ORDER BY file NULLS LAST, entity_type, names
""")
show("Q3b: the 95% bar, indiv and oth together", """
SELECT
    sum(TRANSACTION_AMT) AS net_dollars,
    sum(TRANSACTION_AMT) FILTER (WHERE cm_named.committees = 1) AS names_one,
    sum(TRANSACTION_AMT) FILTER (WHERE coalesce(cm_named.committees, 0) <> 1) AS names_several_or_none,
    sum(TRANSACTION_AMT) FILTER (WHERE cm_named.committees = 1) / sum(TRANSACTION_AMT) AS share_net,
    sum(abs(TRANSACTION_AMT)) FILTER (WHERE cm_named.committees = 1) / sum(abs(TRANSACTION_AMT)) AS share_gross,
    count(*) FILTER (WHERE cm_named.committees = 1) / count(*) AS share_rows
FROM no_id
LEFT JOIN cm_named ON cm_named.name_key = regexp_replace(upper(no_id.NAME), '[^A-Z0-9]', '', 'g')
""")
show("Q3c: the largest names with no committee id that name no single cm committee", """
SELECT NAME, any_value(entity_type) AS entity_type, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars
FROM no_id
LEFT JOIN cm_named ON cm_named.name_key = regexp_replace(upper(no_id.NAME), '[^A-Z0-9]', '', 'g')
WHERE coalesce(cm_named.committees, 0) <> 1
GROUP BY NAME ORDER BY net_dollars DESC LIMIT 20
""")
con.execute("""
-- PAC/COM/CCM/PTY counted indiv rows whose OTHER_ID is a committee in cm.
CREATE TABLE with_id AS
SELECT counted.SUB_ID, counted.CMTE_ID, trim(counted.OTHER_ID) AS other_id,
    counted.TRANSACTION_AMT, counted.TRANSACTION_DT
FROM counted
JOIN cm ON cm.CMTE_ID = trim(counted.OTHER_ID)
WHERE counted.entity_type IN ('PAC', 'COM', 'CCM', 'PTY');

-- The oth receipts that share a SUB_ID with one, and those mirroring one under another SUB_ID
-- (same recipient, giver, amount and date).
CREATE TABLE with_id_same AS
SELECT DISTINCT with_id.SUB_ID FROM receipt JOIN with_id USING (SUB_ID);

CREATE TABLE with_id_mirrored AS
SELECT DISTINCT with_id.SUB_ID
FROM receipt
JOIN with_id
    ON receipt.CMTE_ID = with_id.CMTE_ID
    AND trim(receipt.OTHER_ID) = with_id.other_id
    AND receipt.TRANSACTION_AMT = with_id.TRANSACTION_AMT
    AND receipt.TRANSACTION_DT = with_id.TRANSACTION_DT
WHERE receipt.SUB_ID <> with_id.SUB_ID;
""")
show("Q3d: PAC/COM/CCM/PTY counted indiv rows whose OTHER_ID is a cm committee, and their oth twin", """
SELECT
    CASE WHEN s.SUB_ID IS NOT NULL THEN 'same SUB_ID in oth' WHEN m.SUB_ID IS NOT NULL
        THEN 'mirrored in oth' ELSE 'not in oth' END AS in_oth,
    count(*) AS rows, sum(with_id.TRANSACTION_AMT) AS net_dollars
FROM with_id
LEFT JOIN with_id_same AS s USING (SUB_ID)
LEFT JOIN with_id_mirrored AS m USING (SUB_ID)
GROUP BY ALL ORDER BY in_oth
""")
show("Q3e: no-id rows naming one cm committee, and whether oth already holds the gift from that committee", """
WITH named AS (
    SELECT no_id.*, cm_named.committee_id AS named_committee
    FROM no_id
    JOIN cm_named ON cm_named.name_key = regexp_replace(upper(no_id.NAME), '[^A-Z0-9]', '', 'g')
    WHERE cm_named.committees = 1 AND no_id.file = 'indiv'
),
twin AS (
    SELECT DISTINCT named.SUB_ID
    FROM receipt
    JOIN named
        ON receipt.CMTE_ID = named.CMTE_ID
        AND trim(receipt.OTHER_ID) = named.named_committee
        AND receipt.TRANSACTION_AMT = named.TRANSACTION_AMT
        AND receipt.TRANSACTION_DT = named.TRANSACTION_DT
)
SELECT CASE WHEN twin.SUB_ID IS NOT NULL THEN 'twin in oth' ELSE 'not in oth' END AS in_oth,
    count(*) AS rows, sum(named.TRANSACTION_AMT) AS net_dollars
FROM named LEFT JOIN twin USING (SUB_ID)
GROUP BY ALL ORDER BY in_oth
""")
```


**Q3a: PAC/COM/CCM/PTY rows with no committee id, by how many cm committees the name names  (0 s)**

| file | entity_type | names | rows | net_dollars |
|---|---|---|---|---|
| indiv | CCM | none | 43 | 310,739 |
| indiv | CCM | one | 113 | 5,116,926 |
| indiv | CCM | several | 1 | 5,000 |
| indiv | COM | none | 712 | 53,205,593 |
| indiv | COM | one | 484 | 114,017,881 |
| indiv | COM | several | 10 | 5,870,275 |
| indiv | PAC | none | 661 | 69,257,820 |
| indiv | PAC | one | 1,939 | 516,079,117 |
| indiv | PAC | several | 32 | 14,137,184 |
| indiv | PTY | none | 20 | 303,995 |
| indiv | PTY | one | 10 | 163,152 |
| oth | CCM | none | 3 | 5,700 |
| oth | CCM | one | 4 | 42,303 |
| oth | COM | none | 10 | 8,326,327 |
| oth | PAC | none | 2 | 10,000 |
| oth | PAC | one | 3 | 80,000 |
| oth | PTY | none | 3 | 1,389,589 |
| oth | PTY | one | 2 | 90,000 |
|  |  | none | 1,454 | 132,809,763 |
|  |  | one | 2,555 | 635,589,379 |
|  |  | several | 43 | 20,012,459 |

**Q3b: the 95% bar, indiv and oth together  (0 s)**

| net_dollars | names_one | names_several_or_none | share_net | share_gross | share_rows |
|---|---|---|---|---|---|
| 788,411,601 | 635,589,379 | 152,822,222 | 80.62% | 80.60% | 63.06% |

**Q3c: the largest names with no committee id that name no single cm committee  (0 s)**

| NAME | entity_type | rows | net_dollars |
|---|---|---|---|
| SAVE AMERICA | COM | 5 | 17,250,000 |
| REPUBLICAN GOVERNORS ASSOCIATION | COM | 11 | 12,200,000 |
| TRUMP 47 COMMITTEE | COM | 1 | 8,308,404 |
| WORKING FOR WORKING AMERICANS | PAC | 7 | 7,810,000 |
| HOUSE MAJORITY PAC | PAC | 20 | 5,098,582 |
| VOTE NURSES VALUES PAC | COM | 3 | 5,020,000 |
| SEIU COPE | COM | 9 | 3,915,170 |
| SENATE MAJORITY PAC | PAC | 5 | 3,850,000 |
| SEIU COPE (SERVICES EMPLOYEES INTERNATIONAL UNION COMMITTEE ON POLITICAL EDUCATION) | PAC | 2 | 3,500,000 |
| AMERICA VOTES | COM | 7 | 3,175,000 |
| STRATEGIC VICTORY FUND | COM | 7 | 3,042,200 |
| AMERICAN BRIDGE PAC | PAC | 3 | 2,750,000 |
| UA UNION PLUMBERS & PIPEFITTERS VOTE! PAC | PAC | 5 | 2,495,000 |
| DEMOCRATIC LEGISLATIVE CAMPAIGN COMMITTEE | COM | 21 | 2,352,000 |
| SERVICE EMPLOYEES INTERNATIONAL UNION COPE | PAC | 4 | 2,250,000 |
| UAW V CAP | PAC | 2 | 2,025,000 |
| ADVOCACY ACTION FUND, INC. | COM | 1 | 2,000,000 |
| SIXTEEN THIRTY FUND | COM | 2 | 1,900,000 |
| ENGINEERS POLITICAL EDUCATION COMMITTEE | PAC | 8 | 1,725,000 |
| OHIO EDUCATION ASSOCIATION EDUCATORS PCE | COM | 6 | 1,669,329 |

**Q3d: PAC/COM/CCM/PTY counted indiv rows whose OTHER_ID is a cm committee, and their oth twin  (0 s)**

| in_oth | rows | net_dollars |
|---|---|---|
| not in oth | 107 | 7,065,850 |

**Q3e: no-id rows naming one cm committee, and whether oth already holds the gift from that committee  (3 s)**

| in_oth | rows | net_dollars |
|---|---|---|
| not in oth | 2,541 | 635,307,076 |
| twin in oth | 5 | 70,000 |

**Reading.** $788,411,601 in 4,052 rows, $778,467,682 of it in `indiv`. A unique name match covers
$635.6M (80.62% net, 80.60% gross, 63.06% of rows). The rest name no committee, because the
reported name differs from FEC's (`SAVE AMERICA`, `HOUSE MAJORITY PAC`, `SEIU COPE`), or name a
state committee or an unregistered one (`REPUBLICAN GOVERNORS ASSOCIATION`, a 527). The 107 rows
($7.07M) that do carry a `cm` committee ID have no twin in `oth`, by `SUB_ID` or by mirror, so
`committee_transfer` does not hold them either. Of the `indiv` rows naming one committee, 5
($70,000) have a twin in `oth` from that committee; the other 2,541 ($635,307,076) do not (Q3e).

## Q4: `indiv` and `oth` overlap

Q2's organization receipts (non-committee giver, entity type ORG/PAC/COM/CCM/PTY; this set also
counts `unknown id`, which Q2 shows is already a transfer): whether `indiv` holds the same gift
under the same `SUB_ID`, or as a mirror (same recipient, name key, amount and date) under another.

```python
con.execute("""
-- Organization receipts in oth: a giver that is no committee, an organization entity type.
CREATE TABLE org_receipt AS
SELECT SUB_ID, CMTE_ID, entity_type, TRANSACTION_AMT, TRANSACTION_DT,
    regexp_replace(upper(NAME), '[^A-Z0-9]', '', 'g') AS name_key
FROM receipt
WHERE giver_status IN ('unknown id', 'non-committee id', 'blank')
    AND entity_type IN ('ORG', 'PAC', 'COM', 'CCM', 'PTY');

-- The ones sharing a SUB_ID with an indiv row, and whether that row is counted.
CREATE TABLE by_sub_id AS
SELECT org_receipt.SUB_ID,
    bool_or(indiv.MEMO_CD IS DISTINCT FROM 'X' AND indiv.TRANSACTION_TP IS DISTINCT FROM '24T') AS counted
FROM indiv JOIN org_receipt USING (SUB_ID)
GROUP BY org_receipt.SUB_ID;

-- The ones mirrored by an indiv row under another SUB_ID: same recipient, name key, amount, date.
CREATE TABLE by_mirror AS
SELECT org_receipt.SUB_ID,
    bool_or(indiv.MEMO_CD IS DISTINCT FROM 'X' AND indiv.TRANSACTION_TP IS DISTINCT FROM '24T') AS counted
FROM indiv
JOIN org_receipt
    ON indiv.CMTE_ID = org_receipt.CMTE_ID
    AND indiv.TRANSACTION_AMT = org_receipt.TRANSACTION_AMT
    AND indiv.TRANSACTION_DT = org_receipt.TRANSACTION_DT
    AND indiv.SUB_ID <> org_receipt.SUB_ID
WHERE regexp_replace(upper(indiv.NAME), '[^A-Z0-9]', '', 'g') = org_receipt.name_key
GROUP BY org_receipt.SUB_ID;
""")
show("Q4: oth organization receipts also in indiv", """
SELECT entity_type,
    CASE WHEN s.SUB_ID IS NOT NULL THEN 'same SUB_ID' WHEN m.SUB_ID IS NOT NULL THEN 'mirrored'
        ELSE 'neither' END AS in_indiv,
    coalesce(s.counted, m.counted) AS indiv_row_counted,
    count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars
FROM org_receipt
LEFT JOIN by_sub_id AS s USING (SUB_ID)
LEFT JOIN by_mirror AS m USING (SUB_ID)
GROUP BY GROUPING SETS ((entity_type, in_indiv, indiv_row_counted), (in_indiv, indiv_row_counted))
ORDER BY entity_type NULLS LAST, in_indiv, indiv_row_counted
""")
```


**Q4: oth organization receipts also in indiv  (0 s)**

| entity_type | in_indiv | indiv_row_counted | rows | net_dollars |
|---|---|---|---|---|
| CCM | neither |  | 306 | 6,793,889 |
| COM | neither |  | 215 | 21,847,373 |
| ORG | mirrored | True | 2 | 133,900 |
| ORG | neither |  | 186 | 24,627,022 |
| PAC | neither |  | 280 | 2,206,174 |
| PTY | neither |  | 91 | 4,617,594 |
|  | mirrored | True | 2 | 133,900 |
|  | neither |  | 1,078 | 60,092,052 |

**Reading.** No `SUB_ID` is shared. 2 rows ($133,900, both ORG) are mirrored by a counted `indiv`
row. The rest, 1,078 rows and $60.1M, appear only in `oth`.

## Q5: the classifier

Each distinct counted 2024 `indiv` name with its entity type, rows and dollars, written once to
Parquet (`q5a.py`). Then each variant is scored on the names with a filled entity type
(`classifier.py`, `q5b.py`). **Positives** are ORG, PAC, COM, CCM and PTY, and **negatives** IND
and CAN. The ORG-only scores drop PAC/COM/CCM/PTY from the population. Precision and recall are
by rows and by gross dollars.

```python
# Every counted 2024 indiv name with its entity type: rows, net and gross dollars. Q5b and Q6 read it.
start = time.monotonic()
con.execute(f"""
COPY (
    SELECT NAME, entity_type, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars,
        sum(abs(TRANSACTION_AMT)) AS gross_dollars
    FROM counted
    GROUP BY ALL
) TO '{work / "names_2024.parquet"}'
""")
print(f"names_2024.parquet written ({time.monotonic() - start:.0f} s)")
show("Q5a: distinct names by entity type", f"""
SELECT entity_type, count(*) AS names, sum(rows) AS rows, sum(gross_dollars) AS gross_dollars
FROM '{work / "names_2024.parquet"}' GROUP BY ALL ORDER BY rows DESC
""")
```

names_2024.parquet written (13 s)

**Q5a: distinct names by entity type  (0 s)**

| entity_type | names | rows | gross_dollars |
|---|---|---|---|
| IND | 3,539,736 | 51,110,941 | 9,972,341,089 |
| ORG | 6,903 | 18,233 | 2,261,185,934 |
| CAN | 1,338 | 9,101 | 67,468,957 |
| PAC | 1,027 | 2,701 | 606,558,908 |
| COM | 669 | 1,229 | 173,247,768 |
| `<blank>` | 60 | 343 | 332,584 |
| CCM | 115 | 259 | 35,820,820 |
| PTY | 26 | 31 | 467,291 |

The variants. V1–V3 are the spec's. V4–V9 and NC were added after V1–V3's false positives were
read (Q5d below), and every variant tried is kept.

| Variant | Suffix as last token | Words | Segment rule | No comma counts |
| --- | --- | --- | --- | --- |
| V1 | `SUFFIXES` | none | | |
| V2 | `SUFFIXES` | `WORDS` | | |
| V3 | `SUFFIXES` | `WORDS + WIDER` | | |
| V4 | `STRICT` | none | | |
| V5 | `STRICT` | `WORDS` | yes | |
| V6 | `STRICT` | `WORDS + WIDER` | yes | |
| NC | none | none | | yes |
| V7 | `STRICT` | none | | yes |
| V8 | `STRICT` | `SURE` | yes | yes |
| V9 | `STRICT` | `WORDS` | yes | yes |

```python
# The classifier variants (spec §4.2 Q5). A name is tokenized by uppercasing it, deleting periods and
# apostrophes ('L.L.C.' is 'LLC', "O'BRIEN" 'OBRIEN') and splitting on every other run of
# non-alphanumerics. A variant calls a name an organization when its last token is one of the
# variant's suffixes, or a token is one of its words. Under the segment rule a word counts only in
# a comma-separated segment of two tokens or more: 'BANK, LISSY' and 'WOOTEN, COUNCIL' are a
# surname and a first name standing alone, 'TRIBAL COUNCIL, PRAIRIE ISLAND' is not.
def tokens(sql: str) -> str:
    return f"trim(regexp_replace(regexp_replace(upper({sql}), '[.'']', '', 'g'), '[^A-Z0-9]+', ' ', 'g'))"


TOKENS = tokens("NAME")
SUFFIXES = ["INC", "LLC", "CORP", "CO", "LTD", "LLP", "LP", "PC", "PLLC", "INCORPORATED",
            "CORPORATION", "LIMITED", "COMPANY"]
# V1's suffixes without the four that end people's names in 2024 (Q5d V1): 'COX, JOHN T. MR. III
# PC', 'PERRETT, LP', a CO or COMPANY after an employer that leaked into NAME.
STRICT = [s for s in SUFFIXES if s not in ("CO", "PC", "LP", "COMPANY")]
WORDS = ["UNION", "ASSOCIATION", "ASSN", "ASSOC", "COMMITTEE", "FUND", "PAC", "TRIBE", "NATION",
         "COUNCIL", "FEDERATION", "PARTNERS", "GROUP", "BANK"]
WIDER = ["TRUST", "FOUNDATION", "INSTITUTE", "SOCIETY", "LEAGUE", "ALLIANCE", "COALITION",
         "ENTERPRISES", "HOLDINGS", "INDUSTRIES", "INTERNATIONAL", "INTL", "PARTNERSHIP", "CHURCH",
         "SCHOOL", "UNIVERSITY", "HOSPITAL", "CLUB"]

# The words whose row precision under the segment rule is 98% or more on 2024 with 20 false-positive
# rows or fewer (Q5e), chosen after it: V8 is fitted to the data it is scored on.
SURE = ["UNION", "INTERNATIONAL", "INTL", "LEAGUE", "FEDERATION", "PARTNERSHIP", "PARTNERS",
        "INSTITUTE", "INDUSTRIES", "SOCIETY", "HOSPITAL", "SCHOOL", "ASSN", "FUND", "COALITION",
        "ENTERPRISES"]

# Variant: suffixes, words, whether words follow the segment rule, whether a name with no comma
# counts too.
VARIANTS: dict[str, tuple[list[str], list[str], bool, bool]] = {
    "V1": (SUFFIXES, [], False, False),
    "V2": (SUFFIXES, WORDS, False, False),
    "V3": (SUFFIXES, WORDS + WIDER, False, False),
    "V4": (STRICT, [], False, False),
    "V5": (STRICT, WORDS, True, False),
    "V6": (STRICT, WORDS + WIDER, True, False),
    "NC": ([], [], False, True),
    "V7": (STRICT, [], False, True),
    "V8": (STRICT, SURE, True, True),
    "V9": (STRICT, WORDS, True, True),
}


def regexes(variant: str) -> list[str]:
    """The variant's regular expressions: the last-token suffix one, then the word one."""
    suffixes, words, _, _ = VARIANTS[variant]
    out = [f"(^| )({'|'.join(suffixes)})$"] if suffixes else []
    if words:
        out.append(f"(^| )({'|'.join(words)})( |$)")
    return out


def flag(variant: str) -> str:
    """SQL true when the name (`NAME`, tokenized as `tokens`) matches the variant."""
    suffixes, words, segment, no_comma = VARIANTS[variant]
    parts = []
    if suffixes:
        parts.append(f"regexp_matches(tokens, '{regexes(variant)[0]}')")
    if words and segment:
        seg = tokens("s")
        parts.append(
            f"list_bool_or(list_transform(string_split(NAME, ','), lambda s: "
            f"regexp_matches({seg}, '{regexes(variant)[-1]}') AND contains({seg}, ' ')))"
        )
    elif words:
        parts.append(f"regexp_matches(tokens, '{regexes(variant)[-1]}')")
    if no_comma:
        parts.append("NOT contains(NAME, ',')")
    return "coalesce(" + " OR ".join(parts) + ", false)"


def matched(variant: str) -> str:
    """SQL list of the suffixes and words in `tokens` that can make the variant match."""
    suffixes, words, _, no_comma = VARIANTS[variant]
    s = "[" + ", ".join(f"'{w}'" for w in suffixes) + "]::VARCHAR[]"
    w = "[" + ", ".join(f"'{w}'" for w in words) + "]::VARCHAR[]"
    return (f"list_distinct(list_filter(string_split(tokens, ' '), lambda t: list_contains({w}, t))"
            f" || CASE WHEN list_contains({s}, string_split(tokens, ' ')[-1])"
            f" THEN [string_split(tokens, ' ')[-1]] ELSE [] END"
            f"{" || CASE WHEN NOT contains(NAME, ',') THEN ['(no comma)'] ELSE [] END" if no_comma else ''})")
```

```python
names = work / "names_2024.parquet"
con.execute(f"""
-- Each filed-type name, positive (organization) or negative (person), tokenized, with each variant's call.
CREATE TABLE scored AS
SELECT *, {", ".join(f"{flag(v)} AS {v}" for v in VARIANTS)}
FROM (
    SELECT NAME, entity_type, rows, gross_dollars, {TOKENS} AS tokens
    FROM '{names}'
    WHERE entity_type IN ('ORG', 'PAC', 'COM', 'CCM', 'PTY', 'IND', 'CAN')
)
""")
POSITIVES = {"ORG/PAC/COM/CCM/PTY": "('ORG', 'PAC', 'COM', 'CCM', 'PTY')", "ORG only": "('ORG')"}
parts = []
for v in VARIANTS:
    for label, positive in POSITIVES.items():
        parts.append(f"""
SELECT '{v}' AS variant, '{label}' AS positives,
    tp / (tp + fp) AS precision_rows, tp / (tp + fn) AS recall_rows,
    tp_d / (tp_d + fp_d) AS precision_dollars, tp_d / (tp_d + fn_d) AS recall_dollars,
    tp::BIGINT AS tp_rows, fp::BIGINT AS fp_rows, fn::BIGINT AS fn_rows, tn::BIGINT AS tn_rows,
    tp_d::DECIMAL(16, 2) AS tp_dollars, fp_d::DECIMAL(16, 2) AS fp_dollars, fn_d::DECIMAL(16, 2) AS fn_dollars
FROM (
    SELECT
        sum(rows) FILTER (WHERE pos AND {v})::DOUBLE AS tp,
        sum(rows) FILTER (WHERE NOT pos AND {v})::DOUBLE AS fp,
        sum(rows) FILTER (WHERE pos AND NOT {v})::DOUBLE AS fn,
        sum(rows) FILTER (WHERE NOT pos AND NOT {v})::DOUBLE AS tn,
        sum(gross_dollars) FILTER (WHERE pos AND {v})::DOUBLE AS tp_d,
        sum(gross_dollars) FILTER (WHERE NOT pos AND {v})::DOUBLE AS fp_d,
        sum(gross_dollars) FILTER (WHERE pos AND NOT {v})::DOUBLE AS fn_d
    FROM (
        SELECT *, entity_type IN {positive} AS pos FROM scored
        WHERE entity_type IN {positive} OR entity_type IN ('IND', 'CAN')
    )
)""")
show("Q5b: classifier variants, rows and gross dollars (precision, recall)", " UNION ALL ".join(parts))
for v in VARIANTS:
    show(f"Q5c {v}: false positives, the 30 IND/CAN names with the most dollars", f"""
SELECT NAME, sum(rows) AS rows, sum(gross_dollars) AS gross_dollars
FROM scored WHERE entity_type IN ('IND', 'CAN') AND {v}
GROUP BY NAME ORDER BY gross_dollars DESC LIMIT 30""")
    show(f"Q5c {v}: false positives, 30 IND/CAN names drawn at random (by hash)", f"""
SELECT NAME, sum(rows) AS rows, sum(gross_dollars) AS gross_dollars
FROM scored WHERE entity_type IN ('IND', 'CAN') AND {v}
GROUP BY NAME ORDER BY hash(NAME) LIMIT 30""")
    show(f"Q5c {v}: false negatives, the 30 ORG names with the most dollars it misses", f"""
SELECT NAME, sum(rows) AS rows, sum(gross_dollars) AS gross_dollars
FROM scored WHERE entity_type = 'ORG' AND NOT {v}
GROUP BY NAME ORDER BY gross_dollars DESC LIMIT 30""")
    show(f"Q5d {v}: the suffixes and words behind its false positives", f"""
SELECT word, count(*) AS names, sum(rows) AS rows, sum(gross_dollars) AS gross_dollars
FROM (SELECT unnest({matched(v)}) AS word, rows, gross_dollars
      FROM scored WHERE entity_type IN ('IND', 'CAN') AND {v})
GROUP BY word ORDER BY rows DESC""")
# Each suffix and word on its own, against ORG/PAC/COM/CCM/PTY (tp) and IND/CAN (fp), by rows:
# a word anywhere, and a word under the segment rule. A suffix only as the last token.
words_sql = "[" + ", ".join(f"'{w}'" for w in WORDS + WIDER) + "]"
suffixes_sql = "[" + ", ".join(f"'{w}'" for w in SUFFIXES) + "]"
seg = tokens("s")
show("Q5e: each suffix and word alone, rows", f"""
WITH named AS (
    SELECT *, entity_type IN ('ORG', 'PAC', 'COM', 'CCM', 'PTY') AS pos,
        string_split(tokens, ' ') AS toks,
        list_transform(string_split(NAME, ','), lambda s: {seg}) AS segs
    FROM scored
),
hit AS (
    SELECT word, 'suffix (last token)' AS how, pos, rows FROM named, unnest({suffixes_sql}) AS t(word)
    WHERE toks[-1] = word
    UNION ALL
    SELECT word, 'word anywhere', pos, rows FROM named, unnest({words_sql}) AS t(word)
    WHERE list_contains(toks, word)
    UNION ALL
    SELECT word, 'word, segment rule', pos, rows FROM named, unnest({words_sql}) AS t(word)
    WHERE list_bool_or(list_transform(segs, lambda g: list_contains(string_split(g, ' '), word) AND contains(g, ' ')))
)
SELECT word, how, sum(rows) FILTER (WHERE pos) AS tp_rows, sum(rows) FILTER (WHERE NOT pos) AS fp_rows,
    sum(rows) FILTER (WHERE pos)::DOUBLE / sum(rows) AS precision_rows
FROM hit GROUP BY ALL ORDER BY how, tp_rows DESC NULLS LAST
""")
```


**Q5b: classifier variants, rows and gross dollars (precision, recall)  (1 s)**

| variant | positives | precision_rows | recall_rows | precision_dollars | recall_dollars | tp_rows | fp_rows | fn_rows | tn_rows | tp_dollars | fp_dollars | fn_dollars |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | ORG/PAC/COM/CCM/PTY | 95.93% | 23.33% | 99.99% | 18.89% | 5,239 | 222 | 17,214 | 51,119,820 | 581,222,896 | 71,829 | 2,496,057,825 |
| V1 | ORG only | 95.81% | 27.83% | 99.99% | 22.49% | 5,074 | 222 | 13,159 | 51,119,820 | 508,588,628 | 71,829 | 1,752,597,306 |
| V2 | ORG/PAC/COM/CCM/PTY | 69.94% | 51.72% | 96.87% | 49.62% | 11,612 | 4,990 | 10,841 | 51,115,052 | 1,526,959,269 | 49,347,943 | 1,550,321,452 |
| V2 | ORG only | 64.35% | 49.40% | 95.18% | 43.08% | 9,008 | 4,990 | 9,225 | 51,115,052 | 974,161,832 | 49,347,943 | 1,287,024,102 |
| V3 | ORG/PAC/COM/CCM/PTY | 47.37% | 55.36% | 97.12% | 55.71% | 12,429 | 13,807 | 10,024 | 51,106,235 | 1,714,307,317 | 50,923,579 | 1,362,973,404 |
| V3 | ORG only | 41.32% | 53.32% | 95.63% | 49.23% | 9,722 | 13,807 | 8,511 | 51,106,235 | 1,113,238,546 | 50,923,579 | 1,147,947,388 |
| V4 | ORG/PAC/COM/CCM/PTY | 99.31% | 21.69% | 100.00% | 17.50% | 4,869 | 34 | 17,584 | 51,120,008 | 538,633,956 | 14,676 | 2,538,646,765 |
| V4 | ORG only | 99.28% | 25.82% | 100.00% | 20.61% | 4,707 | 34 | 13,526 | 51,120,008 | 466,081,942 | 14,676 | 1,795,103,992 |
| V5 | ORG/PAC/COM/CCM/PTY | 96.44% | 50.14% | 96.84% | 48.29% | 11,257 | 415 | 11,196 | 51,119,627 | 1,486,058,229 | 48,457,415 | 1,591,222,492 |
| V5 | ORG only | 95.43% | 47.49% | 95.06% | 41.28% | 8,658 | 415 | 9,575 | 51,119,627 | 933,383,046 | 48,457,415 | 1,327,802,888 |
| V6 | ORG/PAC/COM/CCM/PTY | 93.50% | 53.83% | 97.14% | 54.42% | 12,086 | 840 | 10,367 | 51,119,202 | 1,674,655,277 | 49,300,292 | 1,402,625,444 |
| V6 | ORG only | 91.78% | 51.47% | 95.61% | 47.48% | 9,384 | 840 | 8,849 | 51,119,202 | 1,073,708,760 | 49,300,292 | 1,187,477,174 |
| NC | ORG/PAC/COM/CCM/PTY | 99.91% | 90.96% | 100.00% | 95.61% | 20,423 | 18 | 2,030 | 51,120,024 | 2,942,260,096 | 1,947 | 135,020,625 |
| NC | ORG only | 99.89% | 89.88% | 100.00% | 95.27% | 16,388 | 18 | 1,845 | 51,120,024 | 2,154,300,020 | 1,947 | 106,885,914 |
| V7 | ORG/PAC/COM/CCM/PTY | 99.76% | 97.72% | 100.00% | 99.58% | 21,941 | 52 | 512 | 51,119,990 | 3,064,431,056 | 16,623 | 12,849,665 |
| V7 | ORG only | 99.71% | 97.69% | 100.00% | 99.61% | 17,812 | 52 | 421 | 51,119,990 | 2,252,412,117 | 16,623 | 8,773,817 |
| V8 | ORG/PAC/COM/CCM/PTY | 99.66% | 97.99% | 99.10% | 99.84% | 22,002 | 76 | 451 | 51,119,966 | 3,072,306,917 | 27,976,546 | 4,973,804 |
| V8 | ORG only | 99.58% | 97.82% | 98.78% | 99.86% | 17,836 | 76 | 397 | 51,119,966 | 2,257,971,286 | 27,976,546 | 3,214,648 |
| V9 | ORG/PAC/COM/CCM/PTY | 98.07% | 98.20% | 98.45% | 99.90% | 22,049 | 433 | 404 | 51,119,609 | 3,074,126,865 | 48,459,362 | 3,153,856 |
| V9 | ORG only | 97.63% | 97.91% | 97.90% | 99.89% | 17,852 | 433 | 381 | 51,119,609 | 2,258,656,434 | 48,459,362 | 2,529,500 |


**Reading.** The spec's word list fails on people. Surnames and first names like BANK, NATION,
TRIBE, COUNCIL, PAC and UNION stand alone between commas (`BANK, LISSY`, `WOOTEN, COUNCIL`), and
four suffixes end people's names (`COX, JOHN T. MR. III PC`, `PERRETT, LP`). No spec variant
reaches 99% row precision: V1 is the best at 95.93%. Dropping CO, PC, LP and COMPANY (V4) and
counting a word only in a segment of two tokens or more (V5) fixes much of it. The decisive signal
is the comma, though. FEC writes people as `LAST, FIRST`: 18 of 51.1M IND/CAN rows have no comma
(` UPDIKE`, `LOFTUS`), while 91% of organization rows have none. NC alone scores 99.91% precision
and 90.96% recall by rows.

Many "false positives" are organizations that FEC typed IND: `NEA ADVOCACY FUND, ASSOCIATION`
($27.8M, the whole dollar-precision gap of V8), `NATION, CHEROKEE`, `PAC, COMMON GROUND`. So the
precision figures understate every variant a little.

**Pick: V8**, the highest row recall (97.99%) at ≥ 99% row precision (99.66%). V8's word list
(`SURE`) was chosen from Q5e on the same rows it is scored on, so its edge over V7 (99.76% / 97.72%,
no word list) is partly fitted. The two differ by 0–3 rows in 1998 and 2000 (Q6).

<details>
<summary>Q5c/Q5d for every variant: 30 false positives by dollars, 30 at random (ordered by
<code>hash(NAME)</code>), 30 false negatives by dollars, and the words behind the false positives</summary>

**Q5c V1: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| PERRETT, LP | 21 | 14,335 |
| COX, JOHN T. MR. III PC | 1 | 11,600 |
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |
| RITCHIE, STEPHEN L P.C. | 2 | 3,000 |
| FPHIS, INC | 1 | 2,500 |
| P.A.C., HANGER INC | 1 | 2,500 |
| MAXWELL FROST FOR CONGRESS, MAXWELL FROST FOR CO | 1 | 2,500 |
| STEDT, MARGARET EVELYN C.S.A., LP | 21 | 2,325 |
| KAO, EDWARD P.C | 3 | 2,250 |
| MODESITT, PC | 3 | 2,100 |
| FALLON, BRIAN L.P. | 3 | 1,500 |
| HILDEBRAND, HENRIETTA P.C. | 2 | 1,500 |
| REITER, MITCHELL F DR MD PC | 3 | 1,420 |
| KANDERS AND CO, KANDERS AND CO | 3 | 1,350 |
| FRANTZ, CO | 11 | 1,175 |
| COX, AMANDA CO | 18 | 1,057 |
| NEVETRAL, CYNTHIA COMPANY | 17 | 1,033 |
| BROTHERS, STONE LP | 1 | 1,000 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| PAC, NRDC ACTION FUND INC | 1 | 1,000 |
| N/A - CORPORATION, VICA CAPITAL LLC | 1 | 1,000 |
| CPA, SULLIVAN & COMPANY | 1 | 860 |
| GUILHERME, EDWARD PC | 33 | 796 |
| BICKLER, JASON LIMITED | 1 | 750 |
| GILBERT, PC | 4 | 625 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| MOUNT, SAMUEL CO | 3 | 549 |
| EA, LP | 2 | 520 |
| NEWKIRK, CASSANDRA F MD,PC | 2 | 500 |
| LATHROP, NANNY-CO | 2 | 500 |

**Q5c V1: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| PENDERGRASS, LP | 1 | 318 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| STEDT, MARGARET EVELYN C.S.A., LP | 21 | 2,325 |
| HILDEBRAND, HENRIETTA P.C. | 2 | 1,500 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| ECONOMOS, JAMES P MR. DDS PC | 1 | 250 |
| NEVETRAL, CYNTHIA COMPANY | 17 | 1,033 |
| RITCHIE, STEPHEN L P.C. | 2 | 3,000 |
| SMITH, PATRICIA J LLC | 2 | 16 |
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |
| GILBERT, PC | 4 | 625 |
| REITER, MITCHELL F DR MD PC | 3 | 1,420 |
| BICKLER, JASON LIMITED | 1 | 750 |
| STORMER, PC | 1 | 500 |
| COX, AMANDA CO | 18 | 1,057 |
| KLINGEMIER, AARON F LLC | 1 | 85 |
| FPHIS, INC | 1 | 2,500 |
| COOPER, STEPHANIE R PC | 1 | 100 |
| OLIVA, CHRISTIAN LLC | 3 | 73 |
| KAO, EDWARD P.C | 3 | 2,250 |
| RODGERS, RICHARD P.C. | 1 | 27 |
| LEVINE, JEFFREY J. LLC | 1 | 121 |
| PAC, NRDC ACTION FUND INC | 1 | 1,000 |
| LARSON, BEV LLC | 1 | 300 |
| FALLON, BRIAN L.P. | 3 | 1,500 |
| SO, CHRISTINE CO | 1 | 100 |
| LATHROP, NANNY-CO | 2 | 500 |
| JOHNSON, THOMAS L.P. | 1 | 400 |
| COX, JOHN T. MR. III PC | 1 | 11,600 |
| MOUNT, SAMUEL CO | 3 | 549 |

**Q5c V1: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| FUTURE FORWARD USA ACTION | 22 | 266,470,349 |
| MAJORITY FORWARD | 58 | 127,230,000 |
| EMPOWER PARENTS PAC | 1 | 82,500,000 |
| COINBASE | 9 | 71,519,995 |
| SECURING AMERICAN GREATNESS | 2 | 67,558,283 |
| FUND FOR POLICY REFORM | 1 | 60,000,000 |
| HOUSE MAJORITY FORWARD | 21 | 47,088,047 |
| STAND TOGETHER CHAMBER OF COMMERCE | 4 | 44,800,000 |
| AMERICAN ACTION NETWORK | 17 | 43,040,000 |
| ONE NATION | 5 | 35,580,000 |
| AB FOUNDATION | 35 | 35,230,666 |
| UNITED BROTHERHOOD OF CARPENTERS AND JOINERS | 22 | 32,773,042 |
| AMERICA VOTES | 49 | 32,142,000 |
| BUILDING AMERICA'S FUTURE | 11 | 28,470,000 |
| JUMP CRYPTO | 3 | 25,000,000 |
| COINBASE COMMERCE (EXCHANGE) | 1 | 25,000,000 |
| AMERICAN PROSPERITY ALLIANCE | 18 | 22,549,000 |
| ELON MUSK REVOCABLE TRUST | 1 | 20,500,000 |
| REPUBLICAN STATE LEADERSHIP COMMITTEE | 38 | 19,568,000 |
| SIXTEEN THIRTY FUND | 45 | 18,719,131 |
| EVIDENCE FOR IMPACT | 6 | 16,810,000 |
| COMMUNICATIONS WORKERS OF AMERICA | 86 | 16,631,382 |
| ENVIRONMENTAL DEFENSE ACTION FUND | 29 | 15,074,500 |
| BRIGHT FUTURE FUND | 10 | 14,610,000 |
| RAPID RESIST ACTION | 33 | 12,860,000 |
| INTERNATIONAL UNION OF OPERATING ENGINEERS | 25 | 11,395,887 |
| AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE | 1 | 11,000,000 |
| IBEW PAC EDUCATIONAL FUND | 27 | 10,851,000 |
| STRATEGIC VICTORY FUND | 6 | 10,487,459 |
| CLIMATE POWER | 11 | 10,415,419 |

**Q5d V1: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| PC | 19 | 66 | 25,790 |
| CO | 11 | 52 | 8,322 |
| LP | 9 | 52 | 21,148 |
| LLC | 18 | 30 | 7,926 |
| COMPANY | 2 | 18 | 1,893 |
| INC | 3 | 3 | 6,000 |
| LIMITED | 1 | 1 | 750 |

**Q5c V2: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| NEA ADVOCACY FUND, ASSOCIATION | 7 | 27,837,048 |
| NATIONAL ASSOCIATION OF REALTO, . | 29 | 20,054,012 |
| PARTNERS LIMITED, RLM FAMILY | 1 | 100,000 |
| BANK, LISSY | 18 | 69,300 |
| TRIBAL COUNCIL, PRAIRIE ISLAND | 2 | 53,300 |
| GROUP, INC., PICERNE | 1 | 50,000 |
| NATION, CHEROKEE | 9 | 29,800 |
| NATION, CHICKASAW | 8 | 29,200 |
| WOOTEN, COUNCIL | 636 | 25,019 |
| NATION, MARK | 1 | 25,000 |
| PAC, ASTA | 7 | 23,000 |
| PAC, RMSP | 23 | 23,000 |
| BANK, PENNY | 9 | 19,250 |
| PAC, RAJA | 10 | 17,007 |
| NATION, THE CHICKASAW | 7 | 16,200 |
| NATION, TOHONO O'ODHAM | 5 | 15,000 |
| PERRETT, LP | 21 | 14,335 |
| TRIBE, MARK | 2 | 14,250 |
| NATION, OSAGE | 4 | 14,100 |
| ONCOLOGY PAC, FRIENDS OF COMMUNITY | 4 | 12,000 |
| COX, JOHN T. MR. III PC | 1 | 11,600 |
| PAC, SNC | 7 | 10,500 |
| PAC, TURQUOISE | 1 | 10,000 |
| NATION, THE CHEROKEE | 2 | 10,000 |
| TRIBE, OTOE-MISSOURIA | 2 | 10,000 |
| COUNCIL, MARTHA LAURIN | 2 | 10,000 |
| LA, TUNICA-BILOXI TRIBE | 3 | 10,000 |
| US PAC, US VENTURE | 2 | 10,000 |
| PAC (HOEVEN), DAKOTA | 1 | 10,000 |
| OF FLORIDA, SEMINOLE TRIBE | 3 | 9,900 |

**Q5c V2: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| BANK, BATIA | 2 | 106 |
| COUNCIL, TONY | 1 | 2,100 |
| TRIBE, LAURENCE | 17 | 1,150 |
| UNION, DAVID | 2 | 72 |
| BANK, CHARLOTTE A. | 10 | 165 |
| PENDERGRASS, LP | 1 | 318 |
| PAC, CITY | 5 | 7,750 |
| COMMITTEE, OTTAVIANI | 1 | 1,000 |
| SMITH, COUNCIL | 2 | 200 |
| FUTURE, COMMITTEE FOR A DEMO | 1 | 1,000 |
| NATION, LINDA A | 1 | 171 |
| FUND, MICHAEL B | 5 | 130 |
| INDIAN TRIBE, SAGINAW-CHIPPEWA | 1 | 1,000 |
| CONFEDERATED TRIBES & BANDS, OF THE YAKAMA NATION | 1 | 3,300 |
| PARTNERS, INC., DE RITO | 1 | 2,500 |
| BANK, PATRICIA | 5 | 132 |
| CAMPAIGN-FUND, STEVEMEYERSON-JODIRE | 1 | 250 |
| PAC, COMMON GROUND | 1 | 2,500 |
| NATION, GARY | 3 | 1,500 |
| VON BANK, HEATHER | 11 | 275 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| COUNCIL, DONNA T | 15 | 4,257 |
| PARTNERS, KANSAS | 1 | 400 |
| BANK, LISSY | 18 | 69,300 |
| NATION, GALEN DR. | 15 | 821 |
| BANK, AMY | 1 | 4,450 |
| GOVERNMENT FUND, MARCHANT GOOD | 3 | 4,500 |
| PAC, MICHAEL | 2 | 69 |
| INDIAN NATION, SAMISH TYEE | 1 | 1,000 |
| BANK, MARINA | 1 | 1,000 |

**Q5c V2: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| FUTURE FORWARD USA ACTION | 22 | 266,470,349 |
| MAJORITY FORWARD | 58 | 127,230,000 |
| COINBASE | 9 | 71,519,995 |
| SECURING AMERICAN GREATNESS | 2 | 67,558,283 |
| HOUSE MAJORITY FORWARD | 21 | 47,088,047 |
| STAND TOGETHER CHAMBER OF COMMERCE | 4 | 44,800,000 |
| AMERICAN ACTION NETWORK | 17 | 43,040,000 |
| AB FOUNDATION | 35 | 35,230,666 |
| UNITED BROTHERHOOD OF CARPENTERS AND JOINERS | 22 | 32,773,042 |
| AMERICA VOTES | 49 | 32,142,000 |
| BUILDING AMERICA'S FUTURE | 11 | 28,470,000 |
| JUMP CRYPTO | 3 | 25,000,000 |
| COINBASE COMMERCE (EXCHANGE) | 1 | 25,000,000 |
| AMERICAN PROSPERITY ALLIANCE | 18 | 22,549,000 |
| ELON MUSK REVOCABLE TRUST | 1 | 20,500,000 |
| EVIDENCE FOR IMPACT | 6 | 16,810,000 |
| COMMUNICATIONS WORKERS OF AMERICA | 86 | 16,631,382 |
| RAPID RESIST ACTION | 33 | 12,860,000 |
| CLIMATE POWER | 11 | 10,415,419 |
| PIVOTAL VENTURES | 9 | 7,950,000 |
| AMERICAN PETROLEUM INSTITUTE | 7 | 6,500,000 |
| BUILDING AMERIC'AS FUTURE | 3 | 6,350,000 |
| BRICK BY BRICK FOUNDATION | 3 | 5,750,000 |
| REPUBLICAN JEWISH COALITION | 10 | 5,743,500 |
| NEXTGEN CLIMATE ACTION | 4 | 5,200,000 |
| FAIR DEMOCRACY | 25 | 5,165,742 |
| UNITE HERE | 5 | 5,025,148 |
| DEFENDING DEMOCRACY TOGETHER (DDT) | 2 | 5,000,000 |
| CENTER FOR VOTER INFORMATION | 1 | 4,900,000 |
| GRATON RANCHERIA | 2 | 4,400,000 |

**Q5d V2: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| COUNCIL | 77 | 3,003 | 159,611 |
| BANK | 99 | 633 | 186,973 |
| NATION | 107 | 516 | 310,814 |
| PAC | 78 | 185 | 284,572 |
| TRIBE | 66 | 128 | 246,060 |
| UNION | 11 | 125 | 4,804 |
| PC | 19 | 66 | 25,790 |
| GROUP | 25 | 61 | 63,097 |
| FUND | 24 | 59 | 27,852,713 |
| CO | 11 | 52 | 8,322 |
| LP | 9 | 52 | 21,148 |
| ASSOCIATION | 4 | 38 | 47,894,060 |
| LLC | 18 | 30 | 7,926 |
| COMMITTEE | 20 | 22 | 16,558 |
| COMPANY | 2 | 18 | 1,893 |
| ASSOC | 4 | 8 | 1,800 |
| INC | 3 | 3 | 6,000 |
| PARTNERS | 3 | 3 | 102,900 |
| LIMITED | 1 | 1 | 750 |

**Q5c V3: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| NEA ADVOCACY FUND, ASSOCIATION | 7 | 27,837,048 |
| NATIONAL ASSOCIATION OF REALTO, . | 29 | 20,054,012 |
| BRIGHTER FUTURE ALLIANCE, - ORGANIZATION | 16 | 514,090 |
| LEVY-CHURCH, JEANNE | 2 | 105,000 |
| ENTERPRISES, BRETLINGER | 1 | 100,000 |
| PARTNERS LIMITED, RLM FAMILY | 1 | 100,000 |
| BANK, LISSY | 18 | 69,300 |
| TRIBAL COUNCIL, PRAIRIE ISLAND | 2 | 53,300 |
| GROUP, INC., PICERNE | 1 | 50,000 |
| FAMILY TRUST, NERIN | 1 | 36,500 |
| NATION, CHEROKEE | 9 | 29,800 |
| NATION, CHICKASAW | 8 | 29,200 |
| WOOTEN, COUNCIL | 636 | 25,019 |
| NATION, MARK | 1 | 25,000 |
| TRUST, BERYL SNYDER | 1 | 25,000 |
| STIEFEL TRUST, BARBARA A | 1 | 25,000 |
| PAC, RMSP | 23 | 23,000 |
| PAC, ASTA | 7 | 23,000 |
| HOLDINGS INC., OURREA | 1 | 22,000 |
| FOUNDATION, R.C. | 4 | 20,000 |
| BANK, PENNY | 9 | 19,250 |
| CHURCH, CHARLES | 47 | 18,360 |
| PAC, RAJA | 10 | 17,007 |
| NATION, THE CHICKASAW | 7 | 16,200 |
| CHURCH, CHARLES R. | 22 | 15,250 |
| NATION, TOHONO O'ODHAM | 5 | 15,000 |
| LEVY-CHURCH, KENNETH | 23 | 14,874 |
| PERRETT, LP | 21 | 14,335 |
| TRIBE, MARK | 2 | 14,250 |
| NATION, OSAGE | 4 | 14,100 |

**Q5c V3: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| BANK, BATIA | 2 | 106 |
| CHURCH, ROBERT E. | 11 | 670 |
| CHURCH, NED | 1 | 2,000 |
| CHURCH, MARLENE | 13 | 650 |
| CHURCH, GORDON | 2,542 | 13,888 |
| TRUST, MURRAY FAMILY | 1 | 1,000 |
| COUNCIL, TONY | 1 | 2,100 |
| TRIBE, LAURENCE | 17 | 1,150 |
| UNION, DAVID | 2 | 72 |
| STIEFEL TRUST, BARBARA A | 1 | 25,000 |
| CHURCH, JAY | 2 | 297 |
| BANK, CHARLOTTE A. | 10 | 165 |
| PENDERGRASS, LP | 1 | 318 |
| PAC, CITY | 5 | 7,750 |
| CHURCH, GEORGE | 2 | 1,000 |
| CHURCH, ELIZABETH G. MS. | 17 | 1,475 |
| COMMITTEE, OTTAVIANI | 1 | 1,000 |
| CHURCH, ALISON | 4 | 200 |
| CLUB, DEM | 2 | 490 |
| CHURCH, HOLLIS MARGARET | 5 | 702 |
| SMITH, COUNCIL | 2 | 200 |
| FUTURE, COMMITTEE FOR A DEMO | 1 | 1,000 |
| NATION, LINDA A | 1 | 171 |
| FUND, MICHAEL B | 5 | 130 |
| INDIAN TRIBE, SAGINAW-CHIPPEWA | 1 | 1,000 |
| CHURCH, MARY C. MS. | 100 | 118 |
| CONFEDERATED TRIBES & BANDS, OF THE YAKAMA NATION | 1 | 3,300 |
| CHURCH, JOHN SR | 27 | 1,801 |
| PARTNERS, INC., DE RITO | 1 | 2,500 |
| BANK, PATRICIA | 5 | 132 |

**Q5c V3: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| FUTURE FORWARD USA ACTION | 22 | 266,470,349 |
| MAJORITY FORWARD | 58 | 127,230,000 |
| COINBASE | 9 | 71,519,995 |
| SECURING AMERICAN GREATNESS | 2 | 67,558,283 |
| HOUSE MAJORITY FORWARD | 21 | 47,088,047 |
| STAND TOGETHER CHAMBER OF COMMERCE | 4 | 44,800,000 |
| AMERICAN ACTION NETWORK | 17 | 43,040,000 |
| UNITED BROTHERHOOD OF CARPENTERS AND JOINERS | 22 | 32,773,042 |
| AMERICA VOTES | 49 | 32,142,000 |
| BUILDING AMERICA'S FUTURE | 11 | 28,470,000 |
| COINBASE COMMERCE (EXCHANGE) | 1 | 25,000,000 |
| JUMP CRYPTO | 3 | 25,000,000 |
| EVIDENCE FOR IMPACT | 6 | 16,810,000 |
| COMMUNICATIONS WORKERS OF AMERICA | 86 | 16,631,382 |
| RAPID RESIST ACTION | 33 | 12,860,000 |
| CLIMATE POWER | 11 | 10,415,419 |
| PIVOTAL VENTURES | 9 | 7,950,000 |
| BUILDING AMERIC'AS FUTURE | 3 | 6,350,000 |
| NEXTGEN CLIMATE ACTION | 4 | 5,200,000 |
| FAIR DEMOCRACY | 25 | 5,165,742 |
| UNITE HERE | 5 | 5,025,148 |
| DEFENDING DEMOCRACY TOGETHER (DDT) | 2 | 5,000,000 |
| CENTER FOR VOTER INFORMATION | 1 | 4,900,000 |
| GRATON RANCHERIA | 2 | 4,400,000 |
| CHAMBER OF COMMERCE OF THE USA | 4 | 4,394,000 |
| DEMOCRACY MATTERS | 4 | 4,250,000 |
| SAN PABLO LYTTON CASINO | 22 | 4,210,736 |
| OUR AMERICAN FUTURE ACTION | 10 | 4,150,000 |
| NO ON 2 | 2 | 4,000,000 |
| NORTH CAROLINA FAMILIES FIRST | 4 | 3,950,000 |

**Q5d V3: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| CHURCH | 466 | 8,044 | 634,304 |
| COUNCIL | 77 | 3,003 | 159,611 |
| BANK | 99 | 633 | 186,973 |
| NATION | 107 | 516 | 310,814 |
| TRUST | 71 | 393 | 190,009 |
| PAC | 78 | 185 | 284,572 |
| LEAGUE | 21 | 137 | 20,069 |
| TRIBE | 66 | 128 | 246,060 |
| UNION | 11 | 125 | 4,804 |
| ALLIANCE | 7 | 93 | 525,753 |
| PC | 19 | 66 | 25,790 |
| GROUP | 25 | 61 | 63,097 |
| FUND | 24 | 59 | 27,852,713 |
| LP | 9 | 52 | 21,148 |
| CLUB | 11 | 52 | 13,072 |
| CO | 11 | 52 | 8,322 |
| ASSOCIATION | 4 | 38 | 47,894,060 |
| LLC | 18 | 30 | 7,926 |
| HOLDINGS | 7 | 23 | 34,000 |
| SCHOOL | 9 | 22 | 6,954 |
| COMMITTEE | 20 | 22 | 16,558 |
| COMPANY | 2 | 18 | 1,893 |
| ENTERPRISES | 8 | 15 | 104,661 |
| COALITION | 3 | 14 | 2,774 |
| FOUNDATION | 8 | 12 | 33,218 |
| ASSOC | 4 | 8 | 1,800 |
| HOSPITAL | 4 | 5 | 444 |
| PARTNERSHIP | 1 | 5 | 378 |
| PARTNERS | 3 | 3 | 102,900 |
| INC | 3 | 3 | 6,000 |
| UNIVERSITY | 2 | 2 | 1,500 |
| LIMITED | 1 | 1 | 750 |
| INTERNATIONAL | 1 | 1 | 10,000 |
| INDUSTRIES | 1 | 1 | 500 |

**Q5c V4: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |
| P.A.C., HANGER INC | 1 | 2,500 |
| FPHIS, INC | 1 | 2,500 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| N/A - CORPORATION, VICA CAPITAL LLC | 1 | 1,000 |
| PAC, NRDC ACTION FUND INC | 1 | 1,000 |
| BICKLER, JASON LIMITED | 1 | 750 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| MEDEIROS, LORI LLC | 1 | 315 |
| PEARCE, IVA E LLC | 4 | 301 |
| LARSON, BEV LLC | 1 | 300 |
| HUDSON-PARKER, LLC | 2 | 300 |
| REINHOLDT, AMY S LLC | 2 | 170 |
| PAQUETTE, LYNDA (LAMP LLC) | 5 | 125 |
| MURACCO, CHRISTINA MARIE LLC | 1 | 122 |
| LEVINE, JEFFREY J. LLC | 1 | 121 |
| KLINGEMIER, AARON F LLC | 1 | 85 |
| OLIVA, CHRISTIAN LLC | 3 | 73 |
| LLC, VELAY LLC | 1 | 47 |
| WARREN, BC ARMORY, LLC | 1 | 20 |
| MCMAHAN, ELIZABETH LLC | 1 | 18 |
| SMITH, PATRICIA J LLC | 2 | 16 |

**Q5c V4: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| LARSON, BEV MS. LLC | 1 | 1,000 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| SMITH, PATRICIA J LLC | 2 | 16 |
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |
| BICKLER, JASON LIMITED | 1 | 750 |
| KLINGEMIER, AARON F LLC | 1 | 85 |
| FPHIS, INC | 1 | 2,500 |
| OLIVA, CHRISTIAN LLC | 3 | 73 |
| LEVINE, JEFFREY J. LLC | 1 | 121 |
| PAC, NRDC ACTION FUND INC | 1 | 1,000 |
| LARSON, BEV LLC | 1 | 300 |
| LLC, VELAY LLC | 1 | 47 |
| MCMAHAN, ELIZABETH LLC | 1 | 18 |
| PAQUETTE, LYNDA (LAMP LLC) | 5 | 125 |
| MEDEIROS, LORI LLC | 1 | 315 |
| WARREN, BC ARMORY, LLC | 1 | 20 |
| N/A - CORPORATION, VICA CAPITAL LLC | 1 | 1,000 |
| MURACCO, CHRISTINA MARIE LLC | 1 | 122 |
| REINHOLDT, AMY S LLC | 2 | 170 |
| HUDSON-PARKER, LLC | 2 | 300 |
| PEARCE, IVA E LLC | 4 | 301 |
| P.A.C., HANGER INC | 1 | 2,500 |

**Q5c V4: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| FUTURE FORWARD USA ACTION | 22 | 266,470,349 |
| MAJORITY FORWARD | 58 | 127,230,000 |
| EMPOWER PARENTS PAC | 1 | 82,500,000 |
| COINBASE | 9 | 71,519,995 |
| SECURING AMERICAN GREATNESS | 2 | 67,558,283 |
| FUND FOR POLICY REFORM | 1 | 60,000,000 |
| HOUSE MAJORITY FORWARD | 21 | 47,088,047 |
| STAND TOGETHER CHAMBER OF COMMERCE | 4 | 44,800,000 |
| AMERICAN ACTION NETWORK | 17 | 43,040,000 |
| ONE NATION | 5 | 35,580,000 |
| AB FOUNDATION | 35 | 35,230,666 |
| UNITED BROTHERHOOD OF CARPENTERS AND JOINERS | 22 | 32,773,042 |
| AMERICA VOTES | 49 | 32,142,000 |
| BUILDING AMERICA'S FUTURE | 11 | 28,470,000 |
| JUMP CRYPTO | 3 | 25,000,000 |
| COINBASE COMMERCE (EXCHANGE) | 1 | 25,000,000 |
| AMERICAN PROSPERITY ALLIANCE | 18 | 22,549,000 |
| RAI SERVICES COMPANY | 32 | 22,445,000 |
| ELON MUSK REVOCABLE TRUST | 1 | 20,500,000 |
| REPUBLICAN STATE LEADERSHIP COMMITTEE | 38 | 19,568,000 |
| SIXTEEN THIRTY FUND | 45 | 18,719,131 |
| EVIDENCE FOR IMPACT | 6 | 16,810,000 |
| COMMUNICATIONS WORKERS OF AMERICA | 86 | 16,631,382 |
| ENVIRONMENTAL DEFENSE ACTION FUND | 29 | 15,074,500 |
| BRIGHT FUTURE FUND | 10 | 14,610,000 |
| RAPID RESIST ACTION | 33 | 12,860,000 |
| INTERNATIONAL UNION OF OPERATING ENGINEERS | 25 | 11,395,887 |
| AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE | 1 | 11,000,000 |
| IBEW PAC EDUCATIONAL FUND | 27 | 10,851,000 |
| STRATEGIC VICTORY FUND | 6 | 10,487,459 |

**Q5d V4: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| LLC | 18 | 30 | 7,926 |
| INC | 3 | 3 | 6,000 |
| LIMITED | 1 | 1 | 750 |

**Q5c V5: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| NEA ADVOCACY FUND, ASSOCIATION | 7 | 27,837,048 |
| NATIONAL ASSOCIATION OF REALTO, . | 29 | 20,054,012 |
| PARTNERS LIMITED, RLM FAMILY | 1 | 100,000 |
| TRIBAL COUNCIL, PRAIRIE ISLAND | 2 | 53,300 |
| ONCOLOGY PAC, FRIENDS OF COMMUNITY | 4 | 12,000 |
| US PAC, US VENTURE | 2 | 10,000 |
| LA, TUNICA-BILOXI TRIBE | 3 | 10,000 |
| PAC (HOEVEN), DAKOTA | 1 | 10,000 |
| OF FLORIDA, SEMINOLE TRIBE | 3 | 9,900 |
| TRIBAL NATION, MASHANTUCKET PEQUOT | 3 | 9,900 |
| KUMEYAAY NATION, SYCUAN BAND OF THE | 4 | 8,300 |
| INDIAN NATION, CATAWBA | 3 | 8,100 |
| ONEIDA NATION, . | 7 | 8,000 |
| TRIBE OF INDIANS, PUYALLUP | 4 | 7,600 |
| CHIPPEWA TRIBE OF ND, TURTLE MOUNTAIN BAND | 3 | 7,500 |
| OF LA, TUNICA-BILOXI TRIBE | 2 | 7,500 |
| OF OKLAHOMA, CHOCTAW NATION | 3 | 7,150 |
| TRIBAL SUPPORT, MIAMI TRIBE | 2 | 6,600 |
| THE CHICKASAW NATION, . | 2 | 6,600 |
| SAN PABLO LYTTON, CASINO TRIBE | 2 | 6,600 |
| OF INDIANS, PUYALLUP TRIBE | 2 | 6,600 |
| INDIANS OF WISCONSIN, ONEIDA TRIBE OF | 2 | 6,600 |
| TRIBE OF FLORIDA, SEMINOLE | 2 | 6,600 |
| INDIAN NATION, ONEIDA | 2 | 6,600 |
| CHOCTAW NATION OF OKLAHOMA, . | 3 | 6,125 |
| INDIAN TRIBE, COWLITZ | 2 | 6,000 |
| WOMEN PAC, TRI-STATE MAXED-OUT | 2 | 6,000 |
| ACTION PAC, DEMOCRATIC MAJORITY | 1 | 5,000 |
| THAYER (SUSTAINABILITY GROUP /, MILLICENT S. | 1 | 5,000 |
| KUSKO PAC, YUKON | 1 | 5,000 |

**Q5c V5: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| FUTURE, COMMITTEE FOR A DEMO | 1 | 1,000 |
| INDIAN TRIBE, SAGINAW-CHIPPEWA | 1 | 1,000 |
| CONFEDERATED TRIBES & BANDS, OF THE YAKAMA NATION | 1 | 3,300 |
| CAMPAIGN-FUND, STEVEMEYERSON-JODIRE | 1 | 250 |
| VON BANK, HEATHER | 11 | 275 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| GOVERNMENT FUND, MARCHANT GOOD | 3 | 4,500 |
| INDIAN NATION, SAMISH TYEE | 1 | 1,000 |
| HPUL PROJECT OPERATIONS, .HABEMATOLEL TRIBE. | 1 | 3,300 |
| KALISPEL, TRIBE OF INDIANS | 1 | 1,000 |
| COUNCIL-HURST, MARCIA | 10 | 223 |
| MUSCOGEE, CREEK NATION | 2 | 2,000 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| ABDULLAHI CAMPAIGN COMMITTEE, MUNIRA | 1 | 3,300 |
| HANSEN, CORNHUSKER BANK | 2 | 600 |
| NISQUALLY, INDIAN TRIBE | 1 | 1,000 |
| GUZZARDI, COMMITTEE TO ELECT W | 1 | 500 |
| OF LOUISIANA, TUNICA-BILOXI TRIBE | 1 | 2,700 |
| AMERICAN WOMEN PAC, NATIONAL COALITION O | 1 | 1,000 |
| TRIBAL COUNCIL, TULE RIVER | 1 | 3,300 |
| MUSCOGEE CREEK NATION, . | 5 | 4,500 |
| POLYAK BROWN & ASSOC., BARBARA LANDAU | 5 | 1,250 |
| WOOTEN, COUNCIL JR | 39 | 1,942 |
| SMITH, PATRICIA J LLC | 2 | 16 |
| DEFEND THE DREAM PAC, CLAIRE M. DR. | 1 | 100 |
| TRIBAL COUNCIL, PRAIRIE ISLAND | 2 | 53,300 |
| INDIAN TRIBE, COWLITZ | 2 | 6,000 |
| NYDIA VELAZQUEZ, COMMITTEE TO RE-ELEC | 1 | 2,000 |
| MASHANTUCKET, PEQUOT TRIBE | 1 | 2,000 |
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |

**Q5c V5: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| FUTURE FORWARD USA ACTION | 22 | 266,470,349 |
| MAJORITY FORWARD | 58 | 127,230,000 |
| COINBASE | 9 | 71,519,995 |
| SECURING AMERICAN GREATNESS | 2 | 67,558,283 |
| HOUSE MAJORITY FORWARD | 21 | 47,088,047 |
| STAND TOGETHER CHAMBER OF COMMERCE | 4 | 44,800,000 |
| AMERICAN ACTION NETWORK | 17 | 43,040,000 |
| AB FOUNDATION | 35 | 35,230,666 |
| UNITED BROTHERHOOD OF CARPENTERS AND JOINERS | 22 | 32,773,042 |
| AMERICA VOTES | 49 | 32,142,000 |
| BUILDING AMERICA'S FUTURE | 11 | 28,470,000 |
| COINBASE COMMERCE (EXCHANGE) | 1 | 25,000,000 |
| JUMP CRYPTO | 3 | 25,000,000 |
| AMERICAN PROSPERITY ALLIANCE | 18 | 22,549,000 |
| RAI SERVICES COMPANY | 32 | 22,445,000 |
| ELON MUSK REVOCABLE TRUST | 1 | 20,500,000 |
| EVIDENCE FOR IMPACT | 6 | 16,810,000 |
| COMMUNICATIONS WORKERS OF AMERICA | 86 | 16,631,382 |
| RAPID RESIST ACTION | 33 | 12,860,000 |
| CLIMATE POWER | 11 | 10,415,419 |
| PIVOTAL VENTURES | 9 | 7,950,000 |
| AMERICAN PETROLEUM INSTITUTE | 7 | 6,500,000 |
| BUILDING AMERIC'AS FUTURE | 3 | 6,350,000 |
| BRICK BY BRICK FOUNDATION | 3 | 5,750,000 |
| REPUBLICAN JEWISH COALITION | 10 | 5,743,500 |
| NEXTGEN CLIMATE ACTION | 4 | 5,200,000 |
| FAIR DEMOCRACY | 25 | 5,165,742 |
| UNITE HERE | 5 | 5,025,148 |
| DEFENDING DEMOCRACY TOGETHER (DDT) | 2 | 5,000,000 |
| CENTER FOR VOTER INFORMATION | 1 | 4,900,000 |

**Q5d V5: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| NATION | 31 | 74 | 111,035 |
| TRIBE | 42 | 66 | 151,700 |
| COUNCIL | 9 | 58 | 62,830 |
| PAC | 38 | 51 | 94,323 |
| ASSOCIATION | 2 | 36 | 47,891,060 |
| BANK | 8 | 35 | 5,873 |
| LLC | 18 | 30 | 7,926 |
| GROUP | 12 | 28 | 8,235 |
| FUND | 11 | 19 | 27,848,323 |
| COMMITTEE | 18 | 19 | 15,458 |
| ASSOC | 3 | 7 | 1,750 |
| INC | 3 | 3 | 6,000 |
| LIMITED | 1 | 1 | 750 |
| PARTNERS | 1 | 1 | 100,000 |

**Q5c V6: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| NEA ADVOCACY FUND, ASSOCIATION | 7 | 27,837,048 |
| NATIONAL ASSOCIATION OF REALTO, . | 29 | 20,054,012 |
| BRIGHTER FUTURE ALLIANCE, - ORGANIZATION | 16 | 514,090 |
| LEVY-CHURCH, JEANNE | 2 | 105,000 |
| PARTNERS LIMITED, RLM FAMILY | 1 | 100,000 |
| TRIBAL COUNCIL, PRAIRIE ISLAND | 2 | 53,300 |
| FAMILY TRUST, NERIN | 1 | 36,500 |
| STIEFEL TRUST, BARBARA A | 1 | 25,000 |
| HOLDINGS INC., OURREA | 1 | 22,000 |
| LEVY-CHURCH, KENNETH | 23 | 14,874 |
| ONCOLOGY PAC, FRIENDS OF COMMUNITY | 4 | 12,000 |
| SIMMONS (TMS FAMILY TRUST), TODD | 2 | 10,000 |
| STANDAFER TESTAMENTARY TRUST, W SCOTT | 1 | 10,000 |
| BORDER SECURITY ALLIANCE, BORDER SECURITY | 1 | 10,000 |
| PAC (HOEVEN), DAKOTA | 1 | 10,000 |
| US PAC, US VENTURE | 2 | 10,000 |
| LA, TUNICA-BILOXI TRIBE | 3 | 10,000 |
| INTERNATIONAL CORPORATION, PROBITY | 1 | 10,000 |
| OF FLORIDA, SEMINOLE TRIBE | 3 | 9,900 |
| TRIBAL NATION, MASHANTUCKET PEQUOT | 3 | 9,900 |
| STROTHER FAMILY TRUST, SCHOENWALD | 1 | 9,000 |
| KUMEYAAY NATION, SYCUAN BAND OF THE | 4 | 8,300 |
| INDIAN NATION, CATAWBA | 3 | 8,100 |
| ONEIDA NATION, . | 7 | 8,000 |
| MINGUS MT. REP. CLUB, MINGUS MT. REP. CLUB | 4 | 7,766 |
| TRIBE OF INDIANS, PUYALLUP | 4 | 7,600 |
| CHIPPEWA TRIBE OF ND, TURTLE MOUNTAIN BAND | 3 | 7,500 |
| OF LA, TUNICA-BILOXI TRIBE | 2 | 7,500 |
| OF OKLAHOMA, CHOCTAW NATION | 3 | 7,150 |
| OF INDIANS, PUYALLUP TRIBE | 2 | 6,600 |

**Q5c V6: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| STIEFEL TRUST, BARBARA A | 1 | 25,000 |
| FUTURE, COMMITTEE FOR A DEMO | 1 | 1,000 |
| INDIAN TRIBE, SAGINAW-CHIPPEWA | 1 | 1,000 |
| CONFEDERATED TRIBES & BANDS, OF THE YAKAMA NATION | 1 | 3,300 |
| CAMPAIGN-FUND, STEVEMEYERSON-JODIRE | 1 | 250 |
| VON BANK, HEATHER | 11 | 275 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| GOVERNMENT FUND, MARCHANT GOOD | 3 | 4,500 |
| INDIAN NATION, SAMISH TYEE | 1 | 1,000 |
| HPUL PROJECT OPERATIONS, .HABEMATOLEL TRIBE. | 1 | 3,300 |
| HATFIELD JR. (TRUST), JOE S. | 1 | 1,250 |
| WHITE, LORETTA CHURCH | 5 | 125 |
| CHURCH NEW, NANCY | 103 | 4,062 |
| DEMOCRATIC CLUB, GROSSE POINTE | 1 | 1,000 |
| KALISPEL, TRIBE OF INDIANS | 1 | 1,000 |
| COUNCIL-HURST, MARCIA | 10 | 223 |
| LEARY TRUST, DENNIS | 2 | 306 |
| MUSCOGEE, CREEK NATION | 2 | 2,000 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| ABDULLAHI CAMPAIGN COMMITTEE, MUNIRA | 1 | 3,300 |
| ALLIANCE OF REPUBLICANS, SOUTH TEXAS | 1 | 250 |
| HANSEN, CORNHUSKER BANK | 2 | 600 |
| NISQUALLY, INDIAN TRIBE | 1 | 1,000 |
| GUZZARDI, COMMITTEE TO ELECT W | 1 | 500 |
| ROBINSON, EDWARD N. MR. TRUST | 5 | 650 |
| OF LOUISIANA, TUNICA-BILOXI TRIBE | 1 | 2,700 |
| AMERICAN WOMEN PAC, NATIONAL COALITION O | 1 | 1,000 |
| TRIBAL COUNCIL, TULE RIVER | 1 | 3,300 |
| PHILLIPS HOLDINGS, ALAN | 3 | 625 |
| MICHIGAN, UNIVERSITY C. DR. | 1 | 1,000 |

**Q5c V6: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| FUTURE FORWARD USA ACTION | 22 | 266,470,349 |
| MAJORITY FORWARD | 58 | 127,230,000 |
| COINBASE | 9 | 71,519,995 |
| SECURING AMERICAN GREATNESS | 2 | 67,558,283 |
| HOUSE MAJORITY FORWARD | 21 | 47,088,047 |
| STAND TOGETHER CHAMBER OF COMMERCE | 4 | 44,800,000 |
| AMERICAN ACTION NETWORK | 17 | 43,040,000 |
| UNITED BROTHERHOOD OF CARPENTERS AND JOINERS | 22 | 32,773,042 |
| AMERICA VOTES | 49 | 32,142,000 |
| BUILDING AMERICA'S FUTURE | 11 | 28,470,000 |
| JUMP CRYPTO | 3 | 25,000,000 |
| COINBASE COMMERCE (EXCHANGE) | 1 | 25,000,000 |
| RAI SERVICES COMPANY | 32 | 22,445,000 |
| EVIDENCE FOR IMPACT | 6 | 16,810,000 |
| COMMUNICATIONS WORKERS OF AMERICA | 86 | 16,631,382 |
| RAPID RESIST ACTION | 33 | 12,860,000 |
| CLIMATE POWER | 11 | 10,415,419 |
| PIVOTAL VENTURES | 9 | 7,950,000 |
| BUILDING AMERIC'AS FUTURE | 3 | 6,350,000 |
| NEXTGEN CLIMATE ACTION | 4 | 5,200,000 |
| FAIR DEMOCRACY | 25 | 5,165,742 |
| UNITE HERE | 5 | 5,025,148 |
| DEFENDING DEMOCRACY TOGETHER (DDT) | 2 | 5,000,000 |
| CENTER FOR VOTER INFORMATION | 1 | 4,900,000 |
| GRATON RANCHERIA | 2 | 4,400,000 |
| CHAMBER OF COMMERCE OF THE USA | 4 | 4,394,000 |
| DEMOCRACY MATTERS | 4 | 4,250,000 |
| SAN PABLO LYTTON CASINO | 22 | 4,210,736 |
| OUR AMERICAN FUTURE ACTION | 10 | 4,150,000 |
| NO ON 2 | 2 | 4,000,000 |

**Q5d V6: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| CHURCH | 19 | 247 | 134,464 |
| ALLIANCE | 5 | 88 | 524,988 |
| NATION | 31 | 74 | 111,035 |
| TRIBE | 42 | 66 | 151,700 |
| TRUST | 36 | 59 | 126,780 |
| COUNCIL | 9 | 58 | 62,830 |
| PAC | 38 | 51 | 94,323 |
| ASSOCIATION | 2 | 36 | 47,891,060 |
| BANK | 8 | 35 | 5,873 |
| LLC | 18 | 30 | 7,926 |
| GROUP | 12 | 28 | 8,235 |
| FUND | 11 | 19 | 27,848,323 |
| COMMITTEE | 18 | 19 | 15,458 |
| CLUB | 7 | 18 | 10,320 |
| ASSOC | 3 | 7 | 1,750 |
| FOUNDATION | 4 | 5 | 12,100 |
| HOLDINGS | 2 | 4 | 22,625 |
| INC | 3 | 3 | 6,000 |
| COALITION | 2 | 2 | 2,000 |
| ENTERPRISES | 1 | 1 | 500 |
| INTERNATIONAL | 1 | 1 | 10,000 |
| LEAGUE | 1 | 1 | 100 |
| PARTNERS | 1 | 1 | 100,000 |
| LIMITED | 1 | 1 | 750 |
| UNIVERSITY | 1 | 1 | 1,000 |

**Q5c NC: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
|  UPDIKE | 9 | 867 |
| LOFTUS | 7 | 680 |
|  PATRICIA | 1 | 200 |
|  PHALEN BOB | 1 | 200 |

**Q5c NC: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
|  PHALEN BOB | 1 | 200 |
|  UPDIKE | 9 | 867 |
|  PATRICIA | 1 | 200 |
| LOFTUS | 7 | 680 |

**Q5c NC: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| LEAGUE OF CONSERVATION VOTERS, INC. | 35 | 48,976,704 |
| YOUNG AMERICANS FOR LIBERTY, INC. | 8 | 7,910,200 |
| AMERICAN FEDERATION OF STATE, COUNTY AND MUNICIPAL EMPLOYEES | 7 | 3,150,000 |
| BUILDING OUR FUTURE TODAY, LLC | 6 | 2,590,000 |
| AMERICAN FEDERATION OF STATE, COUNTY & MUNICIPAL EMPLOYEES | 5 | 2,052,547 |
| COINBASE, INC. | 3 | 2,000,000 |
| GREENPEACE, INC. | 181 | 1,497,440 |
| WISCO PROJECT, INC. | 11 | 1,391,946 |
| DEMOCRACY FIRST, LLC. | 2 | 1,250,000 |
| FAIR FIGHT ACTION, INC. | 12 | 1,189,595 |
| OUR VOICE OUR VOTE ARIZONA, INC. | 1 | 1,100,000 |
| OHIOANS FOR A HEALTHY ECONOMY, INC. | 4 | 1,100,000 |
| SAVE OUR HOME PLANET ACTION, INC. | 5 | 1,075,000 |
| PLANNED PARENTHOOD ACTION FUND, INC. | 2 | 1,014,454 |
| HAVERFORD-VALLEY, L.L.C | 3 | 1,000,000 |
| DAVIS, ANTHONY B. | 1 | 1,000,000 |
| PAYWARD, INC. | 2 | 1,000,000 |
| LRF JR, LLC | 1 | 1,000,000 |
| THE TYLER PERRY FOUNDATION, INC. | 2 | 1,000,000 |
| INSTITUTE FOR RESPONSIVE GOVERNMENT ACTION, INC. | 3 | 975,000 |
| INTERSECT POWER, LLC | 4 | 850,000 |
| AMERICAN EXCEPTIONALISM INSTITUTE, INC | 6 | 819,000 |
| AMERICAN ADVANCEMENT, INC | 2 | 800,000 |
| PIVOTAL VENTURES, LLC | 3 | 750,000 |
| PROJECT 72 WI, INC. | 7 | 653,320 |
| ENVIRONMENT CALIFORNIA, INC. | 1 | 650,000 |
| GOOD LEADERSHIP ACTION, INC. | 4 | 606,500 |
| PATTERN ENERGY GROUP, LP | 2 | 550,000 |
| THE WELCOME PARTY, INC. | 3 | 530,000 |
| GLOBAL IMPACT SOCIAL WELFARE FUND, INC. | 1 | 500,000 |

**Q5d NC: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| (no comma) | 4 | 18 | 1,947 |

**Q5c V7: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |
| FPHIS, INC | 1 | 2,500 |
| P.A.C., HANGER INC | 1 | 2,500 |
| N/A - CORPORATION, VICA CAPITAL LLC | 1 | 1,000 |
| PAC, NRDC ACTION FUND INC | 1 | 1,000 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
|  UPDIKE | 9 | 867 |
| BICKLER, JASON LIMITED | 1 | 750 |
| LOFTUS | 7 | 680 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| MEDEIROS, LORI LLC | 1 | 315 |
| PEARCE, IVA E LLC | 4 | 301 |
| HUDSON-PARKER, LLC | 2 | 300 |
| LARSON, BEV LLC | 1 | 300 |
|  PATRICIA | 1 | 200 |
|  PHALEN BOB | 1 | 200 |
| REINHOLDT, AMY S LLC | 2 | 170 |
| PAQUETTE, LYNDA (LAMP LLC) | 5 | 125 |
| MURACCO, CHRISTINA MARIE LLC | 1 | 122 |
| LEVINE, JEFFREY J. LLC | 1 | 121 |
| KLINGEMIER, AARON F LLC | 1 | 85 |
| OLIVA, CHRISTIAN LLC | 3 | 73 |
| LLC, VELAY LLC | 1 | 47 |
| WARREN, BC ARMORY, LLC | 1 | 20 |
| MCMAHAN, ELIZABETH LLC | 1 | 18 |
| SMITH, PATRICIA J LLC | 2 | 16 |

**Q5c V7: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
|  PHALEN BOB | 1 | 200 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| SMITH, PATRICIA J LLC | 2 | 16 |
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |
| BICKLER, JASON LIMITED | 1 | 750 |
| KLINGEMIER, AARON F LLC | 1 | 85 |
| FPHIS, INC | 1 | 2,500 |
| OLIVA, CHRISTIAN LLC | 3 | 73 |
| LEVINE, JEFFREY J. LLC | 1 | 121 |
| PAC, NRDC ACTION FUND INC | 1 | 1,000 |
| LARSON, BEV LLC | 1 | 300 |
| LLC, VELAY LLC | 1 | 47 |
| MCMAHAN, ELIZABETH LLC | 1 | 18 |
| PAQUETTE, LYNDA (LAMP LLC) | 5 | 125 |
| MEDEIROS, LORI LLC | 1 | 315 |
|  UPDIKE | 9 | 867 |
| WARREN, BC ARMORY, LLC | 1 | 20 |
| N/A - CORPORATION, VICA CAPITAL LLC | 1 | 1,000 |
|  PATRICIA | 1 | 200 |
| LOFTUS | 7 | 680 |
| MURACCO, CHRISTINA MARIE LLC | 1 | 122 |
| REINHOLDT, AMY S LLC | 2 | 170 |
| HUDSON-PARKER, LLC | 2 | 300 |
| PEARCE, IVA E LLC | 4 | 301 |
| P.A.C., HANGER INC | 1 | 2,500 |

**Q5c V7: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| AMERICAN FEDERATION OF STATE, COUNTY AND MUNICIPAL EMPLOYEES | 7 | 3,150,000 |
| AMERICAN FEDERATION OF STATE, COUNTY & MUNICIPAL EMPLOYEES | 5 | 2,052,547 |
| DAVIS, ANTHONY B. | 1 | 1,000,000 |
| PATTERN ENERGY GROUP, LP | 2 | 550,000 |
| LIBERTY VIEW ASSOCIATES, LP | 1 | 200,000 |
| HOLLY B. LEV FAMILY EMBT DTD, 5/1/1942 | 1 | 150,000 |
| AMERICAN FEDERATION OF STATE, COUNTY & MUNICIPAL EMPLOYEES, AFL-CIO | 1 | 100,000 |
| AMERICAN FEDERATION OF STATE, COUNTY, AND MUNICIPAL EMPLOYEES, AFL-CIO | 1 | 100,000 |
| WEITZ & LUXENBERG, P.C. | 1 | 100,000 |
| BARON & BUDD, P.C. | 3 | 77,300 |
| WORKING FAMILIES ERIN DARLING AND OPPOSING TRACI PARK FOR CITY COUNCIL 2022, SPONSORED BY UNITE HERE LOCAL 11 | 1 | 76,375 |
| PROJECT CANARY, PBC | 2 | 64,800 |
| LOS ANGELES TURF CLUB, INCORPORATED AND ITS AFFILIATED ENTITY, PACIFIC RACING ASSOCIATION | 4 | 64,800 |
| GOODLEAP, LLC DBA PARAMOUNT EQUITY MORTGAGE | 2 | 60,000 |
| COHEN, PLACITELLA & ROTH, PC | 1 | 50,000 |
| AMERICAN EXCEPTIONALISM INSTITUTE, | 1 | 50,000 |
| UNITED FOOD AND COMMERCIAL WORKERS INTERNATIONAL UNION, AFL-CIO, CLC | 1 | 50,000 |
| RESOLUTE SQURE, PBC | 2 | 49,230 |
| LOCAL 636 - PIPEFITTERS, STEAMFITTERS, REFRIGERATION AND AIR CONDITIONING SVC | 24 | 43,830 |
| LSN LAW, P.A. | 2 | 32,400 |
| LOCAL 174 - WEST MICHIGAN PLUMBERS, FITTERS & SERVICE TRADES | 24 | 30,003 |
| AT&T SERVICES, INC. AND ITS AFFILIATES | 2 | 30,000 |
| WATERS, MCPHERSON, MCNEILL, P.C. | 1 | 25,000 |
| INTERNATIONAL BROTHERHOOD OF ELECTRICAL WORKERS, LOCAL 5 PAC | 1 | 25,000 |
| D.R.I.V.E. - DEMOCRAT, REPUBLICAN, INDEPENDENT VOTER EDUCATION (THE PAC OF THE INTERNATIONAL BROTHERHOOD OF TEAMSTERS) | 1 | 25,000 |
| BARRON & BUDD, PC | 1 | 25,000 |
| DE CASTRO, P.C. | 1 | 20,000 |
| DEBARTOLO CORPORATION & AFFILIATED ENTITIES, INCLUDING THE FORTY NINERS FOOTBALL COMPANY, | 2 | 20,000 |
| STEBNER GERTLER GUADAGNI & KAWAMOTO, APLC | 2 | 20,000 |
| LAW OFFICES OF MARSHALL SILBERBERG, P.C. | 2 | 20,000 |

**Q5d V7: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| LLC | 18 | 30 | 7,926 |
| (no comma) | 4 | 18 | 1,947 |
| INC | 3 | 3 | 6,000 |
| LIMITED | 1 | 1 | 750 |

**Q5c V8: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| NEA ADVOCACY FUND, ASSOCIATION | 7 | 27,837,048 |
| PARTNERS LIMITED, RLM FAMILY | 1 | 100,000 |
| INTERNATIONAL CORPORATION, PROBITY | 1 | 10,000 |
| GOVERNMENT FUND, MARCHANT GOOD | 3 | 4,500 |
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |
| FPHIS, INC | 1 | 2,500 |
| P.A.C., HANGER INC | 1 | 2,500 |
| VICTORY FUND, AAPI | 1 | 1,250 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| THE US CAMPAIGN FUND, FEC ID C00575662 | 1 | 1,000 |
| N/A - CORPORATION, VICA CAPITAL LLC | 1 | 1,000 |
| AMERICAN WOMEN PAC, NATIONAL COALITION O | 1 | 1,000 |
| PAC, NRDC ACTION FUND INC | 1 | 1,000 |
| USA PAC, TURKISH COALITION | 1 | 1,000 |
| GARY CHEN, HH FUND | 1 | 1,000 |
| DEMOCRATIC ACTION FUND, ARAB AMERICAN | 1 | 1,000 |
|  UPDIKE | 9 | 867 |
| BICKLER, JASON LIMITED | 1 | 750 |
| LOFTUS | 7 | 680 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| CAMPAIGN FUND, TRAVIS MOORE | 1 | 600 |
| ENTERPRISES LLC, LAVERONE | 1 | 500 |
| VICTORY FUND, BIDEN | 1 | 500 |
| MEDEIROS, LORI LLC | 1 | 315 |
| PEARCE, IVA E LLC | 4 | 301 |
| LARSON, BEV LLC | 1 | 300 |
| HUDSON-PARKER, LLC | 2 | 300 |
| CAMPAIGN-FUND, STEVEMEYERSON-JODIRE | 1 | 250 |
|  PHALEN BOB | 1 | 200 |
|  PATRICIA | 1 | 200 |

**Q5c V8: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
|  PHALEN BOB | 1 | 200 |
| CAMPAIGN-FUND, STEVEMEYERSON-JODIRE | 1 | 250 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| GOVERNMENT FUND, MARCHANT GOOD | 3 | 4,500 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| AMERICAN WOMEN PAC, NATIONAL COALITION O | 1 | 1,000 |
| SMITH, PATRICIA J LLC | 2 | 16 |
| (OTOE MISSOURIA TRIBE), RS LLC | 1 | 3,300 |
| BICKLER, JASON LIMITED | 1 | 750 |
| KLINGEMIER, AARON F LLC | 1 | 85 |
| FPHIS, INC | 1 | 2,500 |
| PARTNERS LIMITED, RLM FAMILY | 1 | 100,000 |
| OLIVA, CHRISTIAN LLC | 3 | 73 |
| LEVINE, JEFFREY J. LLC | 1 | 121 |
| PAC, NRDC ACTION FUND INC | 1 | 1,000 |
| INTERNATIONAL CORPORATION, PROBITY | 1 | 10,000 |
| LARSON, BEV LLC | 1 | 300 |
| USA PAC, TURKISH COALITION | 1 | 1,000 |
| VICTORY FUND, BIDEN | 1 | 500 |
| NEA ADVOCACY FUND, ASSOCIATION | 7 | 27,837,048 |
| ENTERPRISES LLC, LAVERONE | 1 | 500 |
| THE US CAMPAIGN FUND, FEC ID C00575662 | 1 | 1,000 |
| LLC, VELAY LLC | 1 | 47 |
| MCMAHAN, ELIZABETH LLC | 1 | 18 |
| SURPLUS FUND, PATTY KUDERER | 1 | 175 |
| PAQUETTE, LYNDA (LAMP LLC) | 5 | 125 |
| CAMPAIGN FUND, TRAVIS MOORE | 1 | 600 |
| MEDEIROS, LORI LLC | 1 | 315 |
| DEMOCRATIC ACTION FUND, ARAB AMERICAN | 1 | 1,000 |
| LEAGUE-PASCUAL, JAMES | 1 | 100 |

**Q5c V8: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| DAVIS, ANTHONY B. | 1 | 1,000,000 |
| PATTERN ENERGY GROUP, LP | 2 | 550,000 |
| LIBERTY VIEW ASSOCIATES, LP | 1 | 200,000 |
| HOLLY B. LEV FAMILY EMBT DTD, 5/1/1942 | 1 | 150,000 |
| WEITZ & LUXENBERG, P.C. | 1 | 100,000 |
| BARON & BUDD, P.C. | 3 | 77,300 |
| WORKING FAMILIES ERIN DARLING AND OPPOSING TRACI PARK FOR CITY COUNCIL 2022, SPONSORED BY UNITE HERE LOCAL 11 | 1 | 76,375 |
| LOS ANGELES TURF CLUB, INCORPORATED AND ITS AFFILIATED ENTITY, PACIFIC RACING ASSOCIATION | 4 | 64,800 |
| PROJECT CANARY, PBC | 2 | 64,800 |
| GOODLEAP, LLC DBA PARAMOUNT EQUITY MORTGAGE | 2 | 60,000 |
| COHEN, PLACITELLA & ROTH, PC | 1 | 50,000 |
| RESOLUTE SQURE, PBC | 2 | 49,230 |
| LOCAL 636 - PIPEFITTERS, STEAMFITTERS, REFRIGERATION AND AIR CONDITIONING SVC | 24 | 43,830 |
| LSN LAW, P.A. | 2 | 32,400 |
| LOCAL 174 - WEST MICHIGAN PLUMBERS, FITTERS & SERVICE TRADES | 24 | 30,003 |
| AT&T SERVICES, INC. AND ITS AFFILIATES | 2 | 30,000 |
| BARRON & BUDD, PC | 1 | 25,000 |
| WATERS, MCPHERSON, MCNEILL, P.C. | 1 | 25,000 |
| TERRELL HOGAN YEGELWEL, P.A. | 1 | 20,000 |
| THE LAW OFFICES OF ARASH KHORSANDI, PC. | 2 | 20,000 |
| DE CASTRO, P.C. | 1 | 20,000 |
| LAW OFFICES OF MARSHALL SILBERBERG, P.C. | 2 | 20,000 |
| DEBARTOLO CORPORATION & AFFILIATED ENTITIES, INCLUDING THE FORTY NINERS FOOTBALL COMPANY, | 2 | 20,000 |
| STEBNER GERTLER GUADAGNI & KAWAMOTO, APLC | 2 | 20,000 |
| SANDLER, REIFF, LAMB, ROSENSTEIN & BIRKENSTOCK P.C. | 6 | 19,071 |
| RICHARDS, LAYTON & FINGER, PA | 1 | 15,000 |
| COLORADO RIVER INDIAN TRIBES OF THE COLORADO INDIAN RESERVATION, ARIZONA AND CALIFORNIA | 1 | 15,000 |
| CLARK BEVERAGE GROUP, INC. KY | 1 | 15,000 |
| DEMPSEY III, NEAL | 1 | 15,000 |
| RENAISSANCE VENTURES, LP | 1 | 15,000 |

**Q5d V8: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| LLC | 18 | 30 | 7,926 |
| FUND | 11 | 19 | 27,848,323 |
| (no comma) | 4 | 18 | 1,947 |
| INC | 3 | 3 | 6,000 |
| COALITION | 2 | 2 | 2,000 |
| INTERNATIONAL | 1 | 1 | 10,000 |
| ENTERPRISES | 1 | 1 | 500 |
| PARTNERS | 1 | 1 | 100,000 |
| LEAGUE | 1 | 1 | 100 |
| LIMITED | 1 | 1 | 750 |

**Q5c V9: false positives, the 30 IND/CAN names with the most dollars  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| NEA ADVOCACY FUND, ASSOCIATION | 7 | 27,837,048 |
| NATIONAL ASSOCIATION OF REALTO, . | 29 | 20,054,012 |
| PARTNERS LIMITED, RLM FAMILY | 1 | 100,000 |
| TRIBAL COUNCIL, PRAIRIE ISLAND | 2 | 53,300 |
| ONCOLOGY PAC, FRIENDS OF COMMUNITY | 4 | 12,000 |
| LA, TUNICA-BILOXI TRIBE | 3 | 10,000 |
| PAC (HOEVEN), DAKOTA | 1 | 10,000 |
| US PAC, US VENTURE | 2 | 10,000 |
| OF FLORIDA, SEMINOLE TRIBE | 3 | 9,900 |
| TRIBAL NATION, MASHANTUCKET PEQUOT | 3 | 9,900 |
| KUMEYAAY NATION, SYCUAN BAND OF THE | 4 | 8,300 |
| INDIAN NATION, CATAWBA | 3 | 8,100 |
| ONEIDA NATION, . | 7 | 8,000 |
| TRIBE OF INDIANS, PUYALLUP | 4 | 7,600 |
| CHIPPEWA TRIBE OF ND, TURTLE MOUNTAIN BAND | 3 | 7,500 |
| OF LA, TUNICA-BILOXI TRIBE | 2 | 7,500 |
| OF OKLAHOMA, CHOCTAW NATION | 3 | 7,150 |
| INDIANS OF WISCONSIN, ONEIDA TRIBE OF | 2 | 6,600 |
| TRIBE OF FLORIDA, SEMINOLE | 2 | 6,600 |
| OF INDIANS, PUYALLUP TRIBE | 2 | 6,600 |
| INDIAN NATION, ONEIDA | 2 | 6,600 |
| SAN PABLO LYTTON, CASINO TRIBE | 2 | 6,600 |
| TRIBAL SUPPORT, MIAMI TRIBE | 2 | 6,600 |
| THE CHICKASAW NATION, . | 2 | 6,600 |
| CHOCTAW NATION OF OKLAHOMA, . | 3 | 6,125 |
| INDIAN TRIBE, COWLITZ | 2 | 6,000 |
| WOMEN PAC, TRI-STATE MAXED-OUT | 2 | 6,000 |
| THAYER (SUSTAINABILITY GROUP /, MILLICENT S. | 1 | 5,000 |
| STREET PAC, REPUBLICAN MAIN | 5 | 5,000 |
| SPIRITS PAC, SOUTHERN WINE & | 1 | 5,000 |

**Q5c V9: false positives, 30 IND/CAN names drawn at random (by hash)  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| FUTURE, COMMITTEE FOR A DEMO | 1 | 1,000 |
| INDIAN TRIBE, SAGINAW-CHIPPEWA | 1 | 1,000 |
| CONFEDERATED TRIBES & BANDS, OF THE YAKAMA NATION | 1 | 3,300 |
|  PHALEN BOB | 1 | 200 |
| CAMPAIGN-FUND, STEVEMEYERSON-JODIRE | 1 | 250 |
| VON BANK, HEATHER | 11 | 275 |
| LARSON, BEV MS. LLC | 1 | 1,000 |
| GOVERNMENT FUND, MARCHANT GOOD | 3 | 4,500 |
| INDIAN NATION, SAMISH TYEE | 1 | 1,000 |
| HPUL PROJECT OPERATIONS, .HABEMATOLEL TRIBE. | 1 | 3,300 |
| KALISPEL, TRIBE OF INDIANS | 1 | 1,000 |
| COUNCIL-HURST, MARCIA | 10 | 223 |
| MUSCOGEE, CREEK NATION | 2 | 2,000 |
| MCINTYRE, LAVADA MS. LLC | 1 | 613 |
| ABDULLAHI CAMPAIGN COMMITTEE, MUNIRA | 1 | 3,300 |
| HANSEN, CORNHUSKER BANK | 2 | 600 |
| NISQUALLY, INDIAN TRIBE | 1 | 1,000 |
| GUZZARDI, COMMITTEE TO ELECT W | 1 | 500 |
| OF LOUISIANA, TUNICA-BILOXI TRIBE | 1 | 2,700 |
| AMERICAN WOMEN PAC, NATIONAL COALITION O | 1 | 1,000 |
| TRIBAL COUNCIL, TULE RIVER | 1 | 3,300 |
| MUSCOGEE CREEK NATION, . | 5 | 4,500 |
| POLYAK BROWN & ASSOC., BARBARA LANDAU | 5 | 1,250 |
| WOOTEN, COUNCIL JR | 39 | 1,942 |
| SMITH, PATRICIA J LLC | 2 | 16 |
| DEFEND THE DREAM PAC, CLAIRE M. DR. | 1 | 100 |
| TRIBAL COUNCIL, PRAIRIE ISLAND | 2 | 53,300 |
| INDIAN TRIBE, COWLITZ | 2 | 6,000 |
| NYDIA VELAZQUEZ, COMMITTEE TO RE-ELEC | 1 | 2,000 |
| MASHANTUCKET, PEQUOT TRIBE | 1 | 2,000 |

**Q5c V9: false negatives, the 30 ORG names with the most dollars it misses  (0 s)**

| NAME | rows | gross_dollars |
|---|---|---|
| DAVIS, ANTHONY B. | 1 | 1,000,000 |
| LIBERTY VIEW ASSOCIATES, LP | 1 | 200,000 |
| HOLLY B. LEV FAMILY EMBT DTD, 5/1/1942 | 1 | 150,000 |
| WEITZ & LUXENBERG, P.C. | 1 | 100,000 |
| BARON & BUDD, P.C. | 3 | 77,300 |
| PROJECT CANARY, PBC | 2 | 64,800 |
| GOODLEAP, LLC DBA PARAMOUNT EQUITY MORTGAGE | 2 | 60,000 |
| AMERICAN EXCEPTIONALISM INSTITUTE, | 1 | 50,000 |
| COHEN, PLACITELLA & ROTH, PC | 1 | 50,000 |
| RESOLUTE SQURE, PBC | 2 | 49,230 |
| LOCAL 636 - PIPEFITTERS, STEAMFITTERS, REFRIGERATION AND AIR CONDITIONING SVC | 24 | 43,830 |
| LSN LAW, P.A. | 2 | 32,400 |
| LOCAL 174 - WEST MICHIGAN PLUMBERS, FITTERS & SERVICE TRADES | 24 | 30,003 |
| AT&T SERVICES, INC. AND ITS AFFILIATES | 2 | 30,000 |
| WATERS, MCPHERSON, MCNEILL, P.C. | 1 | 25,000 |
| BARRON & BUDD, PC | 1 | 25,000 |
| DE CASTRO, P.C. | 1 | 20,000 |
| LAW OFFICES OF MARSHALL SILBERBERG, P.C. | 2 | 20,000 |
| THE LAW OFFICES OF ARASH KHORSANDI, PC. | 2 | 20,000 |
| STEBNER GERTLER GUADAGNI & KAWAMOTO, APLC | 2 | 20,000 |
| TERRELL HOGAN YEGELWEL, P.A. | 1 | 20,000 |
| DEBARTOLO CORPORATION & AFFILIATED ENTITIES, INCLUDING THE FORTY NINERS FOOTBALL COMPANY, | 2 | 20,000 |
| SANDLER, REIFF, LAMB, ROSENSTEIN & BIRKENSTOCK P.C. | 6 | 19,071 |
| RICHARDS, LAYTON & FINGER, PA | 1 | 15,000 |
| COLORADO RIVER INDIAN TRIBES OF THE COLORADO INDIAN RESERVATION, ARIZONA AND CALIFORNIA | 1 | 15,000 |
| DEMPSEY III, NEAL | 1 | 15,000 |
| RENAISSANCE VENTURES, LP | 1 | 15,000 |
| FAGUNDES, FAGUNDES, FAGUNDES | 1 | 10,000 |
| HURLEY, MCKENNA & MERTZ | 1 | 10,000 |
| ROMANO LAW, PL | 1 | 10,000 |

**Q5d V9: the suffixes and words behind its false positives  (0 s)**

| word | names | rows | gross_dollars |
|---|---|---|---|
| NATION | 31 | 74 | 111,035 |
| TRIBE | 42 | 66 | 151,700 |
| COUNCIL | 9 | 58 | 62,830 |
| PAC | 38 | 51 | 94,323 |
| ASSOCIATION | 2 | 36 | 47,891,060 |
| BANK | 8 | 35 | 5,873 |
| LLC | 18 | 30 | 7,926 |
| GROUP | 12 | 28 | 8,235 |
| FUND | 11 | 19 | 27,848,323 |
| COMMITTEE | 18 | 19 | 15,458 |
| (no comma) | 4 | 18 | 1,947 |
| ASSOC | 3 | 7 | 1,750 |
| INC | 3 | 3 | 6,000 |
| LIMITED | 1 | 1 | 750 |
| PARTNERS | 1 | 1 | 100,000 |


</details>

Each suffix and word alone. A suffix counts only as the last token. A word is counted anywhere,
and again under the segment rule:

<details>
<summary>Q5e: per-word true- and false-positive rows</summary>

**Q5e: each suffix and word alone, rows  (7 s)**

| word | how | tp_rows | fp_rows | precision_rows |
|---|---|---|---|---|
| INC | suffix (last token) | 2,232 | 3 | 99.87% |
| LLC | suffix (last token) | 2,096 | 30 | 98.59% |
| COMPANY | suffix (last token) | 168 | 18 | 90.32% |
| LLP | suffix (last token) | 159 |  | 100.00% |
| CORPORATION | suffix (last token) | 154 |  | 100.00% |
| CORP | suffix (last token) | 143 |  | 100.00% |
| LP | suffix (last token) | 82 | 52 | 61.19% |
| PC | suffix (last token) | 75 | 66 | 53.19% |
| CO | suffix (last token) | 45 | 52 | 46.39% |
| PLLC | suffix (last token) | 41 |  | 100.00% |
| LTD | suffix (last token) | 33 |  | 100.00% |
| INCORPORATED | suffix (last token) | 6 |  | 100.00% |
| LIMITED | suffix (last token) | 5 | 1 | 83.33% |
| PAC | word anywhere | 1,761 | 185 | 90.49% |
| FUND | word anywhere | 1,241 | 59 | 95.46% |
| TRIBE | word anywhere | 1,022 | 128 | 88.87% |
| NATION | word anywhere | 989 | 516 | 65.71% |
| COMMITTEE | word anywhere | 609 | 22 | 96.51% |
| ASSOCIATION | word anywhere | 542 | 38 | 93.45% |
| UNION | word anywhere | 476 | 125 | 79.20% |
| INTERNATIONAL | word anywhere | 421 | 1 | 99.76% |
| GROUP | word anywhere | 334 | 61 | 84.56% |
| BANK | word anywhere | 263 | 633 | 29.35% |
| TRUST | word anywhere | 196 | 393 | 33.28% |
| COUNCIL | word anywhere | 189 | 3,003 | 5.92% |
| COALITION | word anywhere | 149 | 14 | 91.41% |
| FOUNDATION | word anywhere | 149 | 12 | 92.55% |
| CLUB | word anywhere | 147 | 52 | 73.87% |
| ALLIANCE | word anywhere | 142 | 93 | 60.43% |
| HOLDINGS | word anywhere | 113 | 23 | 83.09% |
| LEAGUE | word anywhere | 102 | 137 | 42.68% |
| FEDERATION | word anywhere | 95 |  | 100.00% |
| PARTNERS | word anywhere | 93 | 3 | 96.88% |
| PARTNERSHIP | word anywhere | 69 | 5 | 93.24% |
| ENTERPRISES | word anywhere | 66 | 15 | 81.48% |
| INSTITUTE | word anywhere | 50 |  | 100.00% |
| INDUSTRIES | word anywhere | 41 | 1 | 97.62% |
| INTL | word anywhere | 40 |  | 100.00% |
| ASSOC | word anywhere | 25 | 8 | 75.76% |
| SOCIETY | word anywhere | 20 |  | 100.00% |
| HOSPITAL | word anywhere | 16 | 5 | 76.19% |
| SCHOOL | word anywhere | 10 | 22 | 31.25% |
| CHURCH | word anywhere | 7 | 8,044 | 0.09% |
| UNIVERSITY | word anywhere | 6 | 2 | 75.00% |
| ASSN | word anywhere | 6 |  | 100.00% |
| PAC | word, segment rule | 1,759 | 49 | 97.29% |
| FUND | word, segment rule | 1,241 | 19 | 98.49% |
| TRIBE | word, segment rule | 1,022 | 65 | 94.02% |
| NATION | word, segment rule | 989 | 74 | 93.04% |
| COMMITTEE | word, segment rule | 609 | 19 | 96.97% |
| ASSOCIATION | word, segment rule | 542 | 29 | 94.92% |
| UNION | word, segment rule | 476 |  | 100.00% |
| INTERNATIONAL | word, segment rule | 421 | 1 | 99.76% |
| GROUP | word, segment rule | 334 | 28 | 92.27% |
| BANK | word, segment rule | 263 | 35 | 88.26% |
| TRUST | word, segment rule | 196 | 59 | 76.86% |
| COUNCIL | word, segment rule | 189 | 58 | 76.52% |
| COALITION | word, segment rule | 149 | 2 | 98.68% |
| FOUNDATION | word, segment rule | 149 | 5 | 96.75% |
| CLUB | word, segment rule | 147 | 18 | 89.09% |
| ALLIANCE | word, segment rule | 142 | 88 | 61.74% |
| HOLDINGS | word, segment rule | 113 | 4 | 96.58% |
| LEAGUE | word, segment rule | 102 | 1 | 99.03% |
| FEDERATION | word, segment rule | 95 |  | 100.00% |
| PARTNERS | word, segment rule | 93 | 1 | 98.94% |
| PARTNERSHIP | word, segment rule | 69 |  | 100.00% |
| ENTERPRISES | word, segment rule | 66 | 1 | 98.51% |
| INSTITUTE | word, segment rule | 50 |  | 100.00% |
| INDUSTRIES | word, segment rule | 41 |  | 100.00% |
| INTL | word, segment rule | 40 |  | 100.00% |
| ASSOC | word, segment rule | 25 | 7 | 78.12% |
| SOCIETY | word, segment rule | 20 |  | 100.00% |
| HOSPITAL | word, segment rule | 16 |  | 100.00% |
| SCHOOL | word, segment rule | 10 |  | 100.00% |
| CHURCH | word, segment rule | 7 | 247 | 2.76% |
| UNIVERSITY | word, segment rule | 6 | 1 | 85.71% |
| ASSN | word, segment rule | 6 |  | 100.00% |

</details>

## Q6: blank rows under the picked rule

Counted `indiv` rows with a blank entity type in 2024, 1998 and 2000, and how many V8 and every
other variant call organizations. NEU-2132 can move no more than this in each cycle. 1998 and 2000
are the pre-2002 check: FEC filled `ENTITY_TP` only from April 2002.

```python
PICK = "V8"  # Q5b: the highest row recall at 99% row precision or more.
# Blank-entity-type counted indiv rows in 2024, 1998 and 2000, and the ones the picked rule calls
# organizations. 1998 and 2000 are registered in their own schemas, c1998.indiv and c2000.indiv.
for cycle in (1998, 2000):
    bulk("indiv", cycle)
    con.execute(f"""
    COPY (
        SELECT NAME, coalesce(nullif(trim(ENTITY_TP), ''), '<blank>') AS entity_type, CMTE_ID,
            count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars, sum(abs(TRANSACTION_AMT)) AS gross_dollars
        FROM c{cycle}.indiv
        WHERE MEMO_CD IS DISTINCT FROM 'X' AND TRANSACTION_TP IS DISTINCT FROM '24T'
        GROUP BY ALL
    ) TO '{work / f"names_{cycle}.parquet"}'
    """)
# 2024's by committee too, for the per-committee ceiling (names_2024.parquet has no CMTE_ID).
con.execute(f"""
COPY (
    SELECT NAME, entity_type, CMTE_ID, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars,
        sum(abs(TRANSACTION_AMT)) AS gross_dollars
    FROM counted WHERE entity_type = '<blank>' GROUP BY ALL
) TO '{work / "blank_2024.parquet"}'
""")
con.execute(f"""
CREATE TABLE blank AS
SELECT cycle, NAME, CMTE_ID, rows, net_dollars, gross_dollars, {flag(PICK)} AS is_org,
    {", ".join(f"{flag(v)} AS {v}" for v in VARIANTS)}
FROM (
    SELECT *, {TOKENS} AS tokens FROM (
        SELECT 2024 AS cycle, * FROM '{work / "blank_2024.parquet"}'
        UNION ALL BY NAME SELECT 1998 AS cycle, * FROM '{work / "names_1998.parquet"}' WHERE entity_type = '<blank>'
        UNION ALL BY NAME SELECT 2000 AS cycle, * FROM '{work / "names_2000.parquet"}' WHERE entity_type = '<blank>'
    )
)
""")
show("Q6a: counted indiv rows by entity type, 1998 and 2000", f"""
SELECT cycle, entity_type, sum(rows) AS rows, sum(net_dollars) AS net_dollars FROM (
    SELECT 1998 AS cycle, * FROM '{work / "names_1998.parquet"}'
    UNION ALL SELECT 2000 AS cycle, * FROM '{work / "names_2000.parquet"}'
) GROUP BY ALL ORDER BY cycle, rows DESC
""")
show(f"Q6b: blank-entity-type counted indiv rows, and those {PICK} calls organizations", """
SELECT cycle, sum(rows) AS blank_rows, sum(net_dollars) AS blank_net_dollars,
    sum(rows) FILTER (WHERE is_org) AS org_rows, sum(net_dollars) FILTER (WHERE is_org) AS org_net_dollars,
    sum(rows) FILTER (WHERE is_org)::DOUBLE / sum(rows) AS org_share_rows,
    sum(net_dollars) FILTER (WHERE is_org)::DOUBLE / sum(net_dollars) AS org_share_dollars
FROM blank GROUP BY cycle ORDER BY cycle
""")
show("Q6e: blank-entity-type counted rows each variant calls organizations, by cycle", " UNION ALL ".join(f"""
SELECT '{v}' AS variant, cycle, sum(rows) FILTER (WHERE {v}) AS org_rows,
    sum(rows) FILTER (WHERE {v})::DOUBLE / sum(rows) AS org_share_rows,
    sum(net_dollars) FILTER (WHERE {v}) AS org_net_dollars
FROM blank GROUP BY cycle""" for v in VARIANTS) + " ORDER BY cycle, variant")
for cycle in (2024, 1998, 2000):
    show(f"Q6c {cycle}: the 50 names {PICK} calls organizations with the most dollars", f"""
SELECT NAME, sum(rows) AS rows, sum(net_dollars) AS net_dollars
FROM blank WHERE cycle = {cycle} AND is_org
GROUP BY NAME ORDER BY net_dollars DESC LIMIT 50""")
    show(f"Q6d {cycle}: the ceiling by recipient, the 10 committees with the most dollars it moves", f"""
SELECT CMTE_ID, sum(rows) AS rows, sum(net_dollars) AS net_dollars
FROM blank WHERE cycle = {cycle} AND is_org
GROUP BY CMTE_ID ORDER BY net_dollars DESC LIMIT 10""")
```


**Q6a: counted indiv rows by entity type, 1998 and 2000  (0 s)**

| cycle | entity_type | rows | net_dollars |
|---|---|---|---|
| 1998 | `<blank>` | 1,008,123 | 844,536,353 |
| 2000 | `<blank>` | 1,691,171 | 1,811,352,432 |

**Q6b: blank-entity-type counted indiv rows, and those V8 calls organizations  (0 s)**

| cycle | blank_rows | blank_net_dollars | org_rows | org_net_dollars | org_share_rows | org_share_dollars |
|---|---|---|---|---|---|---|
| 1998 | 1,008,123 | 844,536,353 | 25,980 | 166,700,964 | 2.58% | 19.74% |
| 2000 | 1,691,171 | 1,811,352,432 | 44,598 | 388,993,512 | 2.64% | 21.48% |
| 2024 | 343 | 332,584 | 70 | 233,837 | 20.41% | 70.31% |

**Q6e: blank-entity-type counted rows each variant calls organizations, by cycle  (0 s)**

| variant | cycle | org_rows | org_share_rows | org_net_dollars |
|---|---|---|---|---|
| NC | 1998 | 25,866 | 2.57% | 166,333,348 |
| V1 | 1998 | 11,320 | 1.12% | 70,626,388 |
| V2 | 1998 | 14,435 | 1.43% | 96,938,906 |
| V3 | 1998 | 15,526 | 1.54% | 102,453,588 |
| V4 | 1998 | 8,915 | 0.88% | 55,493,629 |
| V5 | 1998 | 11,997 | 1.19% | 81,893,048 |
| V6 | 1998 | 12,982 | 1.29% | 87,518,366 |
| V7 | 1998 | 25,980 | 2.58% | 166,700,964 |
| V8 | 1998 | 25,980 | 2.58% | 166,700,964 |
| V9 | 1998 | 25,994 | 2.58% | 166,708,089 |
| NC | 2000 | 44,511 | 2.63% | 388,380,133 |
| V1 | 2000 | 18,896 | 1.12% | 126,646,641 |
| V2 | 2000 | 24,105 | 1.43% | 178,575,785 |
| V3 | 2000 | 25,743 | 1.52% | 190,200,092 |
| V4 | 2000 | 15,593 | 0.92% | 101,938,418 |
| V5 | 2000 | 20,708 | 1.22% | 154,116,771 |
| V6 | 2000 | 22,185 | 1.31% | 165,819,265 |
| V7 | 2000 | 44,595 | 2.64% | 388,772,031 |
| V8 | 2000 | 44,598 | 2.64% | 388,993,512 |
| V9 | 2000 | 44,639 | 2.64% | 389,074,194 |
| NC | 2024 | 69 | 20.12% | 223,837 |
| V1 | 2024 | 5 | 1.46% | 34,002 |
| V2 | 2024 | 19 | 5.54% | 95,041 |
| V3 | 2024 | 20 | 5.83% | 95,291 |
| V4 | 2024 | 5 | 1.46% | 34,002 |
| V5 | 2024 | 19 | 5.54% | 95,041 |
| V6 | 2024 | 20 | 5.83% | 95,291 |
| V7 | 2024 | 70 | 20.41% | 233,837 |
| V8 | 2024 | 70 | 20.41% | 233,837 |
| V9 | 2024 | 70 | 20.41% | 233,837 |


**Reading.** Every 1998 and 2000 row is blank, so the classifier decides each of them. V8 calls
2.58% (1998) and 2.64% (2000) of rows organizations, about 20% of dollars. That is close to the
dollar share of the organization types on 2024's filled rows (23.6%), though far above their row share
(0.04%), as expected while corporations and unions could still give soft money through `indiv`.
It does not call masses of people organizations: 97.4% of 1998's blank rows have a comma, so the `LAST, FIRST` convention
holds before 2002. The hits are real organizations: Philip Morris, Pfizer, Bell Atlantic, Bank of
America, AT&T, CWA-COPE. They also include **committees**: the RNC, DNC, NRCC, DSCC, and party
dinners and non-federal accounts (`DCCC NONFEDERAL RECEIPTS-C`, $15.4M in 2000). Their recipients
are `C6`-prefixed IDs (C60000015 takes $44.0M in 1998 and $79.7M in 2000), not checked here against
1998's or 2000's `cm`, which this run did not extract. In 2024 the rule moves 70 of 343 rows
($233,837). The largest single committee is C90020454 at $84,694.

<details>
<summary>Q6c/Q6d: the 50 names V8 calls organizations with the most dollars, and the 10 recipient
committees it moves the most from, per cycle</summary>

**Q6c 2024: the 50 names V8 calls organizations with the most dollars  (0 s)**

| NAME | rows | net_dollars |
|---|---|---|
| GROUNDSWELL ACTION FUND | 1 | 44,589 |
| TIDES ADVOCACY | 1 | 39,259 |
| RIC HOLDEN (ARCHIE RODERIC HOLDEN) | 2 | 27,069 |
| SCHAEFER JOHN MICHAEL MIKE | 1 | 15,128 |
| COMMERCIAL INSTALLATIONS INC | 1 | 15,000 |
| COBALT ADVOCATES | 3 | 12,305 |
| THE AMERICAN FOUNDATIONS COMMITTEE | 1 | 10,000 |
| PENNELO LAND COMPANY, LLC | 1 | 10,000 |
| CLATTERBUCK FOR CONGRESS | 2 | 8,600 |
| BEDENBAUGH RENTAL PROPERTIES LLC | 1 | 7,002 |
| AGGREGATE OF CONTRIBUTIONS BELOW THRESHOLD | 1 | 5,466 |
| DEMOCRATIC PARTY OF WISCONSIN | 1 | 5,000 |
| FAMILY VALUES AT WORK ACTION | 1 | 5,000 |
| SCOTT ALLEN HATFIELD JR | 1 | 3,849 |
| RAIFORD T CANTRELL | 4 | 3,200 |
| RAYONIER | 1 | 3,000 |
| NATURAL PRODUCTS ASSOCIATION | 1 | 2,000 |
| ARVIL LOVE FOR HOUSE 2 CAMPAIGN | 1 | 1,110 |
| GATOR PAC | 1 | 1,100 |
| BOULDIN AND PRATNER | 1 | 1,000 |
| HOTALEN | 1 | 1,000 |
| LEHIGH VALLEY FOR ALL PAC - STATE | 1 | 1,000 |
| GINSBERG JACOBS LLC | 1 | 1,000 |
| PENNECO LAND COMPANY LLC | 1 | 1,000 |
| MOVEMENT VOTER PROJECT | 1 | 846 |
| TANEY COUNTY DEMOCRATIC COMMITTEE | 1 | 750 |
| CHRISTIAN COUNTY DEMOCRATIC COMMITTEE | 1 | 750 |
| SOLOS | 4 | 720 |
| STONE COUNTY DEMOCRATIC COMMITTEE | 1 | 600 |
| MARTIN SUSTAINABLE RESOURCES | 1 | 500 |
| LAWRENCE COUNTY DEMOCRATS | 1 | 500 |
| FRIENDS OF SHERROD BROWN | 2 | 500 |
| PLUMBERS AND STEAMFITTERS LOCAL 538 | 1 | 500 |
| MEDICAL ASSOCIATES | 1 | 500 |
| ACTBLUE | 1 | 425 |
| VARIOUS | 1 | 389 |
| ABIGAIL STERNBACH | 1 | 360 |
| WIX.COM | 1 | 324 |
| MANNY MARINO | 1 | 250 |
| EVAN KORTH | 1 | 250 |
| STEVE GOLDSCHEIN | 1 | 250 |
| NEWTON COUNTY DEMOCRATIC COMMITTEE | 1 | 250 |
| VENICE ON THE LAKE | 1 | 250 |
| LAKE HAVASU REPUBLICAN MEN'S CLUB | 1 | 250 |
| ANONYMOUS | 2 | 245 |
| R&D FARMS | 1 | 200 |
| NATHAN CROWE | 1 | 100 |
| ROBIN WOHLSTETTER | 1 | 100 |
| FRED HARRISON | 1 | 100 |
| BRANDON GIMPELMAN | 1 | 100 |

**Q6d 2024: the ceiling by recipient, the 10 committees with the most dollars it moves  (0 s)**

| CMTE_ID | rows | net_dollars |
|---|---|---|
| C90020454 | 3 | 84,694 |
| C00852699 | 2 | 27,069 |
| C00877670 | 2 | 25,000 |
| C00868521 | 1 | 15,128 |
| C00625137 | 2 | 11,000 |
| C00803155 | 2 | 9,000 |
| C00847319 | 2 | 8,600 |
| C00864595 | 1 | 7,002 |
| C00548719 | 2 | 5,855 |
| C00649996 | 8 | 5,325 |

**Q6c 1998: the 50 names V8 calls organizations with the most dollars  (0 s)**

| NAME | rows | net_dollars |
|---|---|---|
| 1998 REPUBLICAN HOUSE-SENATE DINNE | 15 | 2,069,250 |
| PHILIP MORRIS COMPANIES INC | 47 | 1,988,013 |
| FIRST UNION NATIONAL BANK | 5 | 1,725,000 |
| REPUBLICAN NATIONAL COMMITTEE | 27 | 1,722,063 |
| DEMOCRATIC NATIONAL COMMITTEE | 11 | 1,563,387 |
| NATIONAL REPUBLICAN CONGRESSIONAL | 10 | 1,343,100 |
| SIGNET BANK | 3 | 1,050,000 |
| 1997 REPUBLICAN SENATE-HOUSE | 3 | 988,300 |
| NAT REP CONGL CMTE | 7 | 924,880 |
| DSCC-NON-FEDERAL MONEY MARKET | 4 | 909,610 |
| NATL REPUBLICAN SENATORIAL CMTE | 2 | 900,000 |
| FREDDIE MAC | 14 | 875,000 |
| CWA-COPE | 8 | 853,000 |
| 1997 REPUBLICAN HOUSE SENATE DINNE | 8 | 844,000 |
| DNC NON-FEDERAL UNINCORPORATED | 5 | 841,093 |
| DSCC NON-FEDERAL CORPORATE II | 2 | 803,275 |
| 1997 REP SEANTE-HOUSE DINNER CMTE | 6 | 788,000 |
| R J REYNOLDS TOBACCO COMPANY | 40 | 753,250 |
| PFIZER INC | 44 | 747,050 |
| DSCC NON-FEDERAL CORPORATE ACCOUNT | 1 | 700,000 |
| BELL ATLANTIC | 46 | 683,969 |
| NAT REPUBLICAN CONGRESSIONAL CMTE | 6 | 602,100 |
| NATIONSBANK | 6 | 578,091 |
| DNC SERVICES CORPORATION | 4 | 572,500 |
| NAT REP CONGRESSIONAL CMTE | 3 | 570,000 |
| WALT DISNEY COMPANY | 28 | 565,500 |
| AT&T | 29 | 564,571 |
| CSX CORPORATION | 12 | 530,250 |
| ALFA MUTUAL INSURANCE COMPANY | 5 | 530,000 |
| MICROSOFT | 15 | 524,566 |
| DSCC NON-FEDERAL CORPORATE | 4 | 508,375 |
| FEDERAL EXPRESS | 20 | 490,250 |
| DLO CORP | 8 | 462,500 |
| FANNIE MAE | 25 | 451,050 |
| CHEVRON CORPORATION | 30 | 446,050 |
| CONNELL COMPANY | 6 | 435,000 |
| MICHIGAN REPUBLICAN PARTY | 3 | 433,750 |
| NATL REPUBLICAN CONGRESSIONAL CMTE | 5 | 430,294 |
| DEMOCRATIC PARTY OF ILLINOIS | 3 | 429,147 |
| AMERICAN AIRLINES | 30 | 423,904 |
| E & J GALLO WINERY | 7 | 415,000 |
| REPUBLICAN NATIONAL STATE ELECTION | 3 | 400,000 |
| AMER FEDERATION OF TEACHERS PAC | 2 | 400,000 |
| ERNST & YOUNG LLP | 29 | 392,616 |
| TOBACCO INSTITUTE | 43 | 387,350 |
| BELLSOUTH CORPORATION | 36 | 384,598 |
| WASTE MANAGEMENT INC | 22 | 376,000 |
| TIME WARNER INC | 12 | 371,000 |
| SPRINT CORPORATION | 28 | 369,428 |
| AM FED OF STATE CNTY AND MUNICIPAL | 7 | 350,000 |

**Q6d 1998: the ceiling by recipient, the 10 committees with the most dollars it moves  (0 s)**

| CMTE_ID | rows | net_dollars |
|---|---|---|
| C60000015 | 3,437 | 43,993,281 |
| C60000148 | 2,910 | 21,348,528 |
| C60000262 | 2,079 | 19,972,403 |
| C60000205 | 9,298 | 17,803,167 |
| C60000619 | 861 | 9,477,169 |
| C60000080 | 1,337 | 7,802,600 |
| C60001161 | 426 | 7,141,927 |
| C60001120 | 463 | 5,867,281 |
| C60000676 | 377 | 3,285,402 |
| C60000247 | 163 | 3,125,450 |

**Q6c 2000: the 50 names V8 calls organizations with the most dollars  (0 s)**

| NAME | rows | net_dollars |
|---|---|---|
| DCCC NONFEDERAL RECEIPTS-C | 44 | 15,396,500 |
| DCCC UNINCORPORATED RECEIPTS ACCT | 10 | 5,790,000 |
| DCCC NONFEDERAL RECEIPTS-I | 13 | 4,793,000 |
| DNC NON-FEDERAL INDIVIDUAL | 18 | 4,506,000 |
| DCCC NONFEDERAL RECEIPTS-L | 11 | 4,470,000 |
| DCCC NONFEDERAL RECEIPTS | 9 | 3,900,000 |
| DNC NON-FEDERAL UNINCORPORATE | 3 | 3,600,000 |
| DCCC NONFEDERAL RECEIPTS-M | 20 | 2,890,000 |
| DSCC NON-FEDERAL LABOR | 10 | 2,583,272 |
| BANK OF AMERICA | 15 | 2,583,223 |
| DSCC NON-FEDERAL CORPORATE | 11 | 2,557,433 |
| AMERICAN FEDERATION OF STATE COUNT | 14 | 2,520,000 |
| DCCC NON-FEDERAL ACCOUNT #1 | 15 | 2,313,357 |
| NATIONAL REPUBLICAN CONGRESSIONAL | 9 | 2,255,460 |
| NEW YORK SENATE 2000-NF INDIVIDUAL | 12 | 2,209,500 |
| NAT REPUBLICAN CONGL COMMITTEE | 7 | 2,135,130 |
| FIRST UNION BANK | 3 | 2,125,600 |
| FREDDIE MAC | 30 | 1,968,000 |
| AT&T | 74 | 1,912,476 |
| PHILIP MORRIS COMPANIES INC | 51 | 1,893,100 |
| DCCC NON-FEDERAL ACCOUNT #5 | 4 | 1,849,189 |
| DSCC NF CORPORATE CD | 3 | 1,771,547 |
| 1999 REPUBLICAN SENATE | 11 | 1,707,500 |
| DSCC NON-FEDERAL UNINCORPORATED | 8 | 1,509,570 |
| DNC NON-FEDERAL GENERAL | 3 | 1,400,000 |
| FIRST UNION NATIONAL BANK | 5 | 1,360,000 |
| PFIZER INC | 39 | 1,352,448 |
| DSCC NF LABOR | 3 | 1,351,926 |
| REPUBLICAN NATIONAL COMMITTEE | 35 | 1,349,175 |
| CALIFORNIA REPUBLICAN PARTY | 2 | 1,325,000 |
| NEW YORK SENATE 2000 | 7 | 1,305,000 |
| DEMOCRATIC SENATORIAL CAMPGN CMTE | 2 | 1,200,000 |
| DCCC CORPORATE RECEIPTS ACCOUNT | 5 | 1,200,000 |
| CWA-COPE | 10 | 1,155,000 |
| A T & T | 14 | 1,081,605 |
| BELL ATLANTIC | 52 | 1,027,036 |
| FANNIE MAE | 30 | 1,021,500 |
| UNT'D BROTHERHD OF CARPENTERS AND | 2 | 1,013,500 |
| NEW YORK SENATE 2000-NF CORP | 3 | 990,000 |
| DCCC NONFEDERAL RECEIPTS-P | 10 | 966,000 |
| MAJORITY 2000 | 14 | 956,535 |
| NEW YORK SENATE 2000 - NF INDIV | 3 | 944,000 |
| HSBC | 15 | 939,267 |
| MICROSOFT CORPORATION | 43 | 936,300 |
| DSCC NF UNINCORPORATED CD | 3 | 907,158 |
| DNC GENERAL FUND | 61 | 899,675 |
| 1999 REPUBLICAN SENATE-HOUSE | 1 | 875,000 |
| DSCC NON-FEDERAL INCORPORATED | 6 | 862,000 |
| I B E W EDUCATIONAL COMMITTEE | 13 | 824,500 |
| CITIGROUP | 33 | 802,651 |

**Q6d 2000: the ceiling by recipient, the 10 committees with the most dollars it moves  (0 s)**

| CMTE_ID | rows | net_dollars |
|---|---|---|
| C60000015 | 6,267 | 79,699,218 |
| C60000262 | 3,054 | 42,703,931 |
| C60000205 | 18,635 | 36,663,793 |
| C60000148 | 3,061 | 30,616,571 |
| C60000080 | 569 | 22,175,381 |
| C60000619 | 1,023 | 21,075,008 |
| C60001450 | 1,897 | 17,223,593 |
| C60000247 | 231 | 14,098,700 |
| C60000288 | 49 | 9,651,743 |
| C60000668 | 79 | 7,079,449 |

</details>

## Q7: five super PACs against FEC's totals

The five super PACs (`cm.CMTE_TP` O or U) with the most ORG-typed counted `indiv` dollars, against
FEC's PAC summary file `webk24.zip`. FEC publishes no header file for `webk`, so its columns are
taken from FEC's [file description](https://www.fec.gov/campaign-finance-data/pac-and-party-summary-file-description/),
read 2026-11-05. fundlens's side is live gold, read by `psql`:

```python
import datetime as dt
import zipfile
from urllib.request import Request, urlopen

from fundlens.fec.extract import USER_AGENT

# FEC's 2024 PAC summary file, into `work` only: not catalogued, not in bronze. FEC publishes no
# header file for it; the columns are its file description's, in order
# (https://www.fec.gov/campaign-finance-data/pac-and-party-summary-file-description/, read 2026-11-05).
header = ["CMTE_ID", "CMTE_NM", "CMTE_TP", "CMTE_DSGN", "CMTE_FILING_FREQ", "TTL_RECEIPTS",
          "TRANS_FROM_AFF", "INDV_CONTRIB", "OTHER_POL_CMTE_CONTRIB", "CAND_CONTRIB", "CAND_LOANS",
          "TTL_LOANS_RECEIVED", "TTL_DISB", "TRANF_TO_AFF", "INDV_REFUNDS", "OTHER_POL_CMTE_REFUNDS",
          "CAND_LOAN_REPAY", "LOAN_REPAY", "COH_BOP", "COH_COP", "DEBTS_OWED_BY",
          "NONFED_TRANS_RECEIVED", "CONTRIB_TO_OTHER_CMTE", "IND_EXP", "PTY_COORD_EXP",
          "NONFED_SHARE_EXP", "CVG_END_DT"]
url = f"{settings.fec_bulk_url.rstrip('/')}/2024/webk24.zip"
with urlopen(Request(url, headers={"User-Agent": USER_AGENT})) as response:
    (work / "webk24.zip").write_bytes(response.read())
    print(url, "| Last-Modified:", response.headers.get("Last-Modified"),
          "| downloaded", dt.datetime.now(dt.UTC).isoformat(timespec="seconds"))
with zipfile.ZipFile(work / "webk24.zip") as archive:
    member = archive.namelist()[0]
    archive.extract(member, work)
columns = "{" + ", ".join(f"'{h}': 'VARCHAR'" for h in header) + "}"
con.execute(f"""
CREATE VIEW webk AS SELECT * FROM read_csv('{work / member}', delim = '|', quote = '', escape = '',
    header = false, auto_detect = false, columns = {columns})
""")
show("Q7: the five super PACs with the most ORG-typed indiv dollars, against FEC's summary", """
WITH top AS (
    SELECT CMTE_ID, sum(TRANSACTION_AMT) AS org_indiv_dollars
    FROM counted
    WHERE entity_type = 'ORG' AND recipient_group = 'super PAC'
    GROUP BY CMTE_ID ORDER BY org_indiv_dollars DESC LIMIT 5
),
org_oth AS (
    SELECT CMTE_ID, sum(TRANSACTION_AMT) AS org_oth_dollars
    FROM receipt
    WHERE giver_status IN ('unknown id', 'non-committee id', 'blank')
        AND entity_type IN ('ORG', 'PAC', 'COM', 'CCM', 'PTY')
        AND CMTE_ID IN (SELECT CMTE_ID FROM top)
    GROUP BY CMTE_ID
)
SELECT top.CMTE_ID, cm.CMTE_NM,
    CAST(webk.TTL_RECEIPTS AS DECIMAL(16, 2)) AS fec_ttl_receipts,
    CAST(webk.INDV_CONTRIB AS DECIMAL(16, 2)) AS fec_indv_contrib,
    CAST(webk.OTHER_POL_CMTE_CONTRIB AS DECIMAL(16, 2)) AS fec_other_pol_cmte_contrib,
    CAST(webk.TRANS_FROM_AFF AS DECIMAL(16, 2)) AS fec_trans_from_aff,
    CAST(webk.TTL_RECEIPTS AS DECIMAL(16, 2)) - CAST(webk.INDV_CONTRIB AS DECIMAL(16, 2))
        - CAST(webk.OTHER_POL_CMTE_CONTRIB AS DECIMAL(16, 2)) - CAST(webk.TRANS_FROM_AFF AS DECIMAL(16, 2)) AS fec_other_receipts,
    top.org_indiv_dollars, coalesce(org_oth.org_oth_dollars, 0) AS org_oth_dollars
FROM top
JOIN cm USING (CMTE_ID)
LEFT JOIN webk ON webk.CMTE_ID = top.CMTE_ID
LEFT JOIN org_oth USING (CMTE_ID)
ORDER BY top.org_indiv_dollars DESC
""")
```

https://www.fec.gov/files/bulk-downloads/2024/webk24.zip | Last-Modified: Wed, 04 Nov 2026 06:40:31 GMT | downloaded 2026-11-05T01:02:14+00:00

**Q7: the five super PACs with the most ORG-typed indiv dollars, against FEC's summary  (12 s)**

| CMTE_ID | CMTE_NM | fec_ttl_receipts | fec_indv_contrib | fec_other_pol_cmte_contrib | fec_trans_from_aff | fec_other_receipts | org_indiv_dollars | org_oth_dollars |
|---|---|---|---|---|---|---|---|---|
| C00835959 | FAIRSHAKE | 260,070,709 | 217,423,881 | 0 | 0 | 42,646,829 | 166,692,432 | 0 |
| C00484642 | SMP | 389,968,278 | 288,693,799 | 73,679,013 | 6,072 | 27,589,394 | 117,131,062 | 0 |
| C00834077 | NEVER BACK DOWN INC. | 145,723,169 | 144,591,259 | 116,873 | 0 | 1,015,037 | 95,595,613 | 0 |
| C00825851 | MAKE AMERICA GREAT AGAIN INC. | 410,509,931 | 383,797,396 | 14,759,411 | 0 | 11,953,124 | 83,345,136 | 0 |
| C00571703 | SENATE LEADERSHIP FUND | 298,859,707 | 220,738,384 | 8,934,548 | 0 | 69,186,775 | 79,260,000 | 0 |

```bash
# VM
pg -c "select committee_id, total_individual, total_from_committees,
  total_individual + total_from_committees as fundlens_total from gold.committee_cycle
  where cycle = 2024 and committee_id in ('C00835959', 'C00484642', 'C00834077', 'C00825851', 'C00571703')
  order by committee_id"
```

```text
 committee_id | total_individual | total_from_committees | fundlens_total
--------------+------------------+-----------------------+----------------
 C00484642    |     154500491.00 |           60739639.00 |   215240130.00
 C00571703    |     176050171.00 |                  0.00 |   176050171.00
 C00825851    |     305954164.00 |            2826533.00 |   308780697.00
 C00834077    |      45416704.00 |                  0.00 |    45416704.00
 C00835959    |       7326650.00 |                  0.00 |     7326650.00
```

And their counted `indiv` dollars by entity type (`q7b.py`):

```python
show("Q7b: the five super PACs' counted indiv dollars by entity type", """
SELECT CMTE_ID, entity_type, count(*) AS rows, sum(TRANSACTION_AMT) AS net_dollars
FROM counted
WHERE CMTE_ID IN ('C00835959', 'C00484642', 'C00834077', 'C00825851', 'C00571703')
GROUP BY ALL ORDER BY CMTE_ID, net_dollars DESC
""")
```


**Q7b: the five super PACs' counted indiv dollars by entity type  (8 s)**

| CMTE_ID | entity_type | rows | net_dollars |
|---|---|---|---|
| C00484642 | IND | 82,361 | 154,877,335 |
| C00484642 | ORG | 170 | 117,131,062 |
| C00484642 | PAC | 52 | 12,945,443 |
| C00571703 | IND | 356 | 176,050,171 |
| C00571703 | ORG | 89 | 79,260,000 |
| C00571703 | PAC | 19 | 8,934,545 |
| C00825851 | IND | 306 | 306,154,164 |
| C00825851 | ORG | 63 | 83,345,136 |
| C00825851 | PAC | 9 | 22,772,000 |
| C00825851 | COM | 3 | 6,300,000 |
| C00834077 | ORG | 76 | 95,595,613 |
| C00834077 | IND | 229 | 45,416,704 |
| C00834077 | PAC | 3 | 55,000 |
| C00834077 | CCM | 6 | 13,731 |
| C00835959 | ORG | 19 | 166,692,432 |
| C00835959 | IND | 37 | 7,326,650 |

Together:

| Committee | FEC total receipts | fundlens counts | Gap | ORG in `indiv` | PAC/COM/CCM in `indiv` | Gap left |
| --- | --- | --- | --- | --- | --- | --- |
| FAIRSHAKE (C00835959) | 260,070,709 | 7,326,650 | 252,744,059 | 166,692,432 | 0 | 86,051,627 |
| SMP (C00484642) | 389,968,278 | 215,240,130 | 174,728,148 | 117,131,062 | 12,945,443 | 44,651,643 |
| NEVER BACK DOWN INC. (C00834077) | 145,723,169 | 45,416,704 | 100,306,465 | 95,595,613 | 68,731 | 4,642,121 |
| MAKE AMERICA GREAT AGAIN INC. (C00825851) | 410,509,931 | 308,780,697 | 101,729,234 | 83,345,136 | 29,072,000 | -10,687,902 |
| SENATE LEADERSHIP FUND (C00571703) | 298,859,707 | 176,050,171 | 122,809,536 | 79,260,000 | 8,934,545 | 34,614,991 |

**Reading.** ORG money closes most of each gap, and none of these five has organization money in
`oth`. FEC's `INDV_CONTRIB` includes organizations: it is line 11(a), contributions from persons
other than committees. The PAC rows are the committee money Q3 drops. Senate Leadership Fund's
$8,934,545 of PAC-typed `indiv` rows is FEC's `OTHER_POL_CMTE_CONTRIB` ($8,934,548) to within $3.
SMP's $12.9M plus fundlens's $60.7M of transfers is FEC's $73.7M.

What remains does not split cleanly by committee. FEC's `fec_other_receipts` (total receipts less individuals, committees and
affiliates) is $42.6M for Fairshake and $69.2M for SLF, and Fairshake has $43.4M of
`INDV_CONTRIB` that its counted `indiv` rows do not reach. For SLF and MAGA Inc. the reverse
holds: their IND and ORG rows exceed FEC's `INDV_CONTRIB` (SLF $255.3M against $220.7M), so FEC's
summary puts some of those gifts on another line. This measurement does not say which one.
`TTL_RECEIPTS` also holds what never appears in `indiv`: unitemized contributions ($200 or less,
in `INDV_CONTRIB`), loans, offsets to operating expenditures and other receipts. The runbook
ticket (NEU-2128's eighth child) starts from this table.

## Decisions

**PAC/COM/CCM/PTY rows with no committee ID: drop.** $635,589,379 of their $788,411,601 (80.62%
net, 80.60% gross) names exactly one `cm` committee by name key, below the 95% bar. The other
$152,822,222 names several committees or none. Under the rule both sides are dropped: $788.4M stays
out of `committee_transfer` and out of `organization_receipt`, and nothing is counted twice.

*Note for NEU-2130.* The bar decides all-or-nothing, and the evidence argues against dropping.
Q7 shows these rows are committee gifts that FEC counts (SLF to within $3, SMP to within $6.1k).
Q3e shows `oth` holds a twin for 5 of the 2,546 `indiv` rows that name one committee ($70,000).
A split rule would recover $635.3M without counting anything twice: join the rows that name
exactly one committee and have no twin, and drop the rest. This ticket applies the
pinned rule. Changing it is NEU-2130's call.

**Classifier: V8.** Over the tokenized name, `trim(regexp_replace(regexp_replace(upper(NAME),
'[.'']', '', 'g'), '[^A-Z0-9]+', ' ', 'g'))`, a name is an organization when any of these holds:

- it has no comma: `NOT contains(NAME, ',')`;
- its last token is a strict suffix: `regexp_matches(tokens, '(^| )(INC|LLC|CORP|LTD|LLP|PLLC|INCORPORATED|CORPORATION|LIMITED)$')`;
- some comma-separated segment of `NAME`, tokenized the same way, holds two tokens or more and
  matches `(^| )(UNION|INTERNATIONAL|INTL|LEAGUE|FEDERATION|PARTNERSHIP|PARTNERS|INSTITUTE|INDUSTRIES|SOCIETY|HOSPITAL|SCHOOL|ASSN|FUND|COALITION|ENTERPRISES)( |$)`.

| Positives | Precision (rows) | Recall (rows) | Precision (dollars) | Recall (dollars) |
| --- | --- | --- | --- | --- |
| ORG/PAC/COM/CCM/PTY | 99.66% | 97.99% | 99.10% | 99.84% |
| ORG only | 99.58% | 97.82% | 98.78% | 99.86% |

Blank-entity-type counted rows it calls organizations: 2024 70 of 343 rows ($233,837 of
$332,584), 1998 25,980 of 1,008,123 ($166,700,964 of $844,536,353), 2000 44,598 of 1,691,171
($388,993,512 of $1,811,352,432).

Its false positives come from LLC (30 rows), FUND (19), no comma (18), INC (3), COALITION (2),
INTERNATIONAL, ENTERPRISES, PARTNERS and LEAGUE (1 each). NEU-2132's unit tests should cover these
names. Expected calls are given as the rule makes them, with what the name is:

| Name | V8 calls it | What it is |
| --- | --- | --- |
| `BANK, LISSY` | person | a person: a word alone in its segment |
| `WOOTEN, COUNCIL` | person | a person: a first name that is a word |
| `NATION, MARK` | person | a person |
| `COX, JOHN T. MR. III PC` | person | a person: PC is not a strict suffix |
| `PERRETT, LP` | person | a person: LP is not a strict suffix |
| `LEAGUE-PASCUAL, JAMES` | organization | a person: hyphenation splits LEAGUE into a two-token segment |
| `LARSON, BEV MS. LLC` | organization | a person, with an LLC leaked into the name |
| `SMITH, PATRICIA J LLC` | organization | a person, likewise |
| ` UPDIKE` | organization | a person filed with no comma |
| `LOFTUS` | organization | a person filed with no comma |
| `TRIBAL COUNCIL, PRAIRIE ISLAND` | person | an organization: COUNCIL is not in `SURE` |
| `NATION, CHEROKEE` | person | an organization typed IND, reversed |
| `NEA ADVOCACY FUND, ASSOCIATION` | organization | an organization typed IND |
| `ACME HOLDINGS, L.L.C.` (constructed) | organization | an organization: periods are deleted, so `LLC` is the last token |
| `FUTURE FORWARD USA ACTION` | organization | an organization with no comma |
| `LEAGUE OF CONSERVATION VOTERS, INC.` | organization | an organization: INC is the last token |
| `WEITZ & LUXENBERG, P.C.` | person | an organization: PC is not a strict suffix |

**Dedupe key for `organization_receipt`: the mirror, not `SUB_ID`.** No `oth` organization receipt
shares a `SUB_ID` with an `indiv` row. 2 rows ($133,900) mirror a counted `indiv` row: same
`CMTE_ID`, name key, `TRANSACTION_AMT` and `TRANSACTION_DT`. `organization_receipt` reads the
`indiv` row and drops the `oth` one that mirrors it.

## For NEU-2130, NEU-2131 and NEU-2132

- **NEU-2130 (glossary, spec, the organizations ADR).** Organization money in 2024: $2,257,182,796 in `indiv`
  (ORG), $23.1M in `oth` (ORG gifts with a blank or non-committee giver ID; 15J lines and loans
  excluded), against $9.82B from individuals. The PAC/COM rule above, and the note on
  it. Some C-prefixed givers that 05_committee_transfer.sql counts point at committee IDs `cm`
  does not hold (Q2 `unknown id`: 689 rows, $21.3M). They are counted today, and the ADR should
  say whether that stands.
- **NEU-2131 (silver `organization_receipt`).** The definition-of-done row count is within 1% of
  **18,336**. That is 18,233 counted ORG `indiv` rows ($2,257,182,796), plus 103 `oth` ORG receipts
  with a `blank` or `non-committee id` giver that are neither 15J nor a loan (16C, 16F, 16G):
  $23,073,903. Less up to 2 rows ($133,900) that mirror an `indiv` row, if both fall in that set
  (Q4 also looked at `unknown id`). It inherits contribution's earmark rules, and Q1 shows no ORG row
  goes to a committee missing from `cm`.
- **NEU-2132 (classifier).** V8 as written above, with the test names. The ceilings it checks
  against: 2024, 70 rows and $233,837, at most $84,694 to one committee (C90020454). 1998 moves
  $166.7M and 2000 $389.0M, at most $44.0M and $79.7M to one committee (C60000015). Party
  committees and their non-federal accounts are among the pre-2002 hits. They are committees, not
  organizations: route them by Q3's name match before classifying.
