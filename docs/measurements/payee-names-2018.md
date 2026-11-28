# Payee names in 2018 `oppexp`: the payee person rule

Measured for [NEU-2541](https://linear.app/neuroticsasquatch/issue/NEU-2541) (every-FEC-dollar spec
[§5.4](../specs/fundlens-every-fec-dollar-project-spec.md#54-payees)). From 2006 to 2018 FEC's
`ENTITY_TP` is blank on part of the spending dollars, and the name decides whether a payee row is a
person's. NEU-2180's backfill measured 2018's silver on 2026-11-27 with the contributor classifier
(`is_organization_name`, rule V8 of [organization-money-2024.md](organization-money-2024.md) Q5) and
failed runbook §3's by-eye gate: 345 keys lost their payee page, the largest all firms written with
a comma and a suffix V8's strict list leaves out (`CHAIN BRIDGE BANK, N.A.`, `VERDOLINO & LOWEY,
P.C.`, `DEMOCRACY ENGINE, INC. PAC`). This measures the payee classifier NEU-2541 adds,
`is_payee_organization_name`, on the same silver. Nothing is written: it reads one build's silver.

| What | Value |
| --- | --- |
| Run | 2026-11-27, between two backfill cycles, by hand over SSH on `music-box-dancer`; output in `~/fundlens-efd-backfill/2018-held-20261127T014447Z/payees2541.txt` (the first list) and `payees2541-final.txt` |
| Silver | 2018's held build `20261127T014447Z`, built with the contributor classifier and not published (section A: all 1,254,329 payee rows agree with it) |
| Code | The deployed `main`, before NEU-2541: the script used its own copy of the PR's rule, as its first line said |

## How to re-run

Run it only when no pipeline step is running: it shares `pipeline`'s DuckDB limits. Do not merge to
`main` while it runs. From the laptop, copy the script below to the VM as a file (a long paste
mangles in tmux), then run it in the backfill's tmux session, whose `py` helper is runbook §0's:

```bash
# laptop: the script below, saved as payees2541.py
scp payees2541.py hetzner-01:~/fundlens-efd-backfill/payees2541.py
```

```bash
# VM, in tmux, in ~/fundlens-efd-backfill
B=$(cat 2018-held-*/build-id.txt); echo "$B"
py payees2541.py 2018 "$B" | tee 2018-held-$B/payees2541.txt
```

It prints sections A to I:

- **A.** How many rows' `payee_is_person` agrees with each rule: which one the build used.
- **B.** Payee dollars with `ENTITY_TP` filed and blank.
- **C.** On filed rows, each rule against `ENTITY_TP`: `persons_read_as_organizations` (the share of
  IND/CAN dollars a rule would give a page) and `organizations_read_as_persons`. NEU-2541's bar: the
  payee rule's first figure is at most 1.00, and its second is no higher than the contributor rule's
  (it cannot be: the payee rule calls every name the contributor rule does an organization's).
- **D.** Each suffix on its own, over the names only it moves: filed person and organization rows
  and dollars, and blank dollars. A suffix with a low `org_pct` reads people as firms.
- **E.** The 25 largest filed IND/CAN names the payee rule reads as an organization's.
- **F.** Keys with blank-type person rows, and how many lose their page, under each rule.
- **G.** The 25 largest keys with blank-type rows the payee rule still reads as a person's.
  NEU-2541's bar, as amended on 2026-11-27: no firm whose name ends in a payee suffix among them with
  `loses_page` true. A suffix rule reaches no other.
- **H.** The 25 largest keys the payee rule moves to an organization's: read them for a person.
- **I.** Pages the payee rule gives back and takes away.

The page rule here weighs 2018's dollars alone, as `payshare.py` did; gold weighs every cycle, so
it is the upper bound.

```python
"""The payee person rule on one build's silver (every-FEC-dollar spec §5.4, NEU-2541): the
contributor classifier (`is_organization_name`, which builds before NEU-2541 used) against the payee
classifier (`is_payee_organization_name`), on the rows whose ENTITY_TP is filed and on the page rule
over this cycle's dollars. Reads silver only; writes nothing. `payees2541.py <cycle> <build>`."""

import sys

from duckdb.func import FunctionNullHandling

from fundlens import paths
from fundlens.load import gold
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.settings import get_settings
from fundlens.transform import runner

try:
    from fundlens.resolve.normalize import payee_suffix  # pyright: ignore

    RULE = "the deployed code's"
except ImportError:
    # The deployed code predates NEU-2541: its rule, as the PR writes it.
    RULE = "this script's copy of NEU-2541's"
    PAYEE_SUFFIXES = frozenset(
        {"PC", "PA", "NA", "PAC", "PLC", "CO", "COMPANY", "ASSOCIATES", "GROUP", "LNC", "LLN"}
    )
    FOLLOWERS = frozenset({"PAC", "DBA"})

    def payee_suffix(raw):
        if raw is None:
            return None
        tokens = normalize._name_tokens(raw)
        ends = [tokens[-1]] if tokens else []
        ends += [tokens[i - 1] for i in range(1, len(tokens)) if tokens[i] in FOLLOWERS]
        for end in ends:
            if end in normalize.STRICT_LEGAL_SUFFIXES or end in PAYEE_SUFFIXES:
                return end
        return None


cycle, build = int(sys.argv[1]), sys.argv[2]
settings = get_settings()
store = R2.from_settings(settings)


def parquet(table):
    """The build's partition of a silver table, downloaded first where the volume lacks it."""
    prefix = paths.silver_partition(table, cycle, build)
    keys = [key for key in store.list_keys(prefix + "/") if key.endswith(".parquet")]
    if not keys:
        sys.exit(f"no {table} parquet under {prefix}/")
    for key in keys:
        local = paths.local_path(settings.data_dir, key)
        if not local.exists():
            store.download_to(key, local)
    files = paths.local_path(settings.data_dir, prefix) / "**" / "*.parquet"
    return f"read_parquet({runner.literal(files)}, hive_partitioning = false)"


con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
normalize.register(con)
con.create_function(  # pyright: ignore
    "payee_suffix", payee_suffix, ["VARCHAR"], "VARCHAR", null_handling=FunctionNullHandling.SPECIAL
)
print(f"{cycle} build {build}; payee rule: {RULE}; suffixes and words before PAC/DBA as listed")

# The payee rows (spec §5.4): counted, a key, not an in-kind outlay. A key has a name.
con.execute(
    f"CREATE TEMP TABLE oe AS SELECT payee_key, payee_name, entity_type, payee_is_person, amount"
    f" FROM {parquet('operating_expenditure')} WHERE counted AND payee_key IS NOT NULL AND NOT is_in_kind"
)
con.execute(
    "CREATE TEMP TABLE cls AS SELECT payee_name, is_organization_name(payee_name) AS old_org,"
    " payee_suffix(payee_name) AS suffix FROM (SELECT DISTINCT payee_name FROM oe)"
)
con.execute(
    "CREATE TEMP TABLE r AS SELECT oe.*, cls.old_org, cls.suffix, cls.old_org OR cls.suffix IS NOT NULL AS new_org,"
    " coalesce(entity_type IN ('IND', 'CAN') OR (entity_type IS NULL AND NOT cls.old_org), false) AS old_person,"
    " coalesce(entity_type IN ('IND', 'CAN') OR (entity_type IS NULL AND NOT (cls.old_org OR cls.suffix IS NOT NULL)),"
    " false) AS new_person FROM oe JOIN cls USING (payee_name)"
)
no_page = gold.payee_no_page()
con.execute("CREATE TEMP TABLE no_page AS SELECT unnest($1::VARCHAR[]) AS payee_key", [no_page])

print("A. Which rule the build's payee_is_person is: rows agreeing with each")
con.sql(
    "SELECT count(*) AS rows, count(*) FILTER (WHERE payee_is_person = old_person) AS as_contributor_rule,"
    " count(*) FILTER (WHERE payee_is_person = new_person) AS as_payee_rule FROM r"
).show(max_rows=100)

print("B. Payee dollars by ENTITY_TP: filed or blank")
con.sql(
    "SELECT entity_type IS NOT NULL AS filed, count(*) AS rows, sum(amount) AS amount,"
    " round(100 * sum(amount) / sum(sum(amount)) OVER (), 2) AS pct FROM r GROUP BY ALL ORDER BY ALL"
).show(max_rows=100)

print("C. Filed rows: each rule against ENTITY_TP, as a share of each side's dollars (gate: <= 1.00, not rising)")
con.sql(
    "SELECT rule, round(100 * coalesce(sum(amount) FILTER (WHERE org AND person_tp), 0) / sum(amount) FILTER (WHERE person_tp), 2)"
    " AS persons_read_as_organizations, round(100 * coalesce(sum(amount) FILTER (WHERE NOT org AND NOT person_tp), 0)"
    " / sum(amount) FILTER (WHERE NOT person_tp), 2) AS organizations_read_as_persons"
    " FROM (SELECT amount, entity_type IN ('IND', 'CAN') AS person_tp, unnest(['contributor', 'payee']) AS rule,"
    " unnest([old_org, new_org]) AS org FROM r WHERE entity_type IS NOT NULL) GROUP BY rule ORDER BY rule"
).show(max_rows=100)

print("D. Each suffix, on the names the contributor rule reads as a person's and the payee rule does not")
con.sql(
    "SELECT suffix, count(*) FILTER (WHERE entity_type IN ('IND', 'CAN')) AS filed_person_rows,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IN ('IND', 'CAN')), 0) AS filed_person_dollars,"
    " count(*) FILTER (WHERE entity_type NOT IN ('IND', 'CAN')) AS filed_org_rows,"
    " coalesce(sum(amount) FILTER (WHERE entity_type NOT IN ('IND', 'CAN')), 0) AS filed_org_dollars,"
    " round(100 * filed_org_dollars / nullif(filed_org_dollars + filed_person_dollars, 0), 2) AS org_pct,"
    " count(*) FILTER (WHERE entity_type IS NULL) AS blank_rows,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IS NULL), 0) AS blank_dollars"
    " FROM r WHERE NOT old_org AND suffix IS NOT NULL GROUP BY suffix ORDER BY blank_dollars DESC, suffix"
).show(max_rows=100, max_width=300)

print("E. The 25 largest filed IND/CAN names the payee rule reads as an organization's (by eye: what it misreads)")
con.sql(
    "SELECT payee_name, entity_type, suffix, count(*) AS rows, sum(amount) AS amount FROM r"
    " WHERE NOT old_org AND new_org AND entity_type IN ('IND', 'CAN')"
    " GROUP BY ALL ORDER BY amount DESC, payee_name LIMIT 25"
).show(max_rows=100, max_width=300)

# The page rule (spec §5.4) over this cycle's dollars alone: gold weighs every cycle, so a firm with
# filed ORG rows in another cycle may keep a page this says it loses.
con.execute(
    "CREATE TEMP TABLE k AS SELECT payee_key, arg_max(payee_name, amount) AS name, sum(amount) AS total,"
    " coalesce(sum(amount) FILTER (WHERE old_person), 0) AS old_p, coalesce(sum(amount) FILTER (WHERE new_person), 0) AS new_p,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IS NULL AND old_person), 0) AS old_blank_p,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IS NULL AND new_person), 0) AS new_blank_p,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IS NULL AND NOT old_person AND NOT new_person), 0) AS blank_org,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IS NULL AND old_person AND NOT new_person), 0) AS flipped,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IN ('IND', 'CAN')), 0) AS filed_person,"
    " any_value(suffix) FILTER (WHERE entity_type IS NULL AND old_person AND NOT new_person) AS suffix,"
    " old_p > 0.5 * total AND old_p > 0 AS old_loses, new_p > 0.5 * total AND new_p > 0 AS new_loses"
    " FROM r ANTI JOIN no_page USING (payee_key) GROUP BY payee_key"
)

print("F. Keys with blank-type rows read as a person's, and how many lose their page, under each rule")
con.sql(
    "SELECT 'contributor' AS rule, count(*) FILTER (WHERE old_blank_p > 0) AS keys, sum(old_blank_p) AS blank_person_dollars,"
    " count(*) FILTER (WHERE old_blank_p > 0 AND old_loses) AS lose_page FROM k"
    " UNION ALL SELECT 'payee', count(*) FILTER (WHERE new_blank_p > 0), sum(new_blank_p),"
    " count(*) FILTER (WHERE new_blank_p > 0 AND new_loses) FROM k ORDER BY rule"
).show(max_rows=100)

print("G. Under the payee rule: the 25 largest keys with blank-type rows read as a person's (DoD: no firm with loses_page)")
con.sql(
    "SELECT payee_key, name, new_blank_p AS blank_person, total, new_loses AS loses_page, old_loses AS lost_before"
    " FROM k WHERE new_blank_p > 0 ORDER BY new_blank_p DESC, payee_key LIMIT 25"
).show(max_rows=100, max_width=300)

print("H. The 25 largest keys whose blank-type rows the payee rule moves to an organization's (by eye: no person)")
con.sql(
    "SELECT payee_key, name, suffix, flipped, total, filed_person, old_loses AS lost_before, new_loses AS loses_page"
    " FROM k WHERE flipped > 0 ORDER BY flipped DESC, payee_key LIMIT 25"
).show(max_rows=100, max_width=300)

print("I. Pages the payee rule gives back and takes away, on this cycle's dollars")
con.sql(
    "SELECT count(*) FILTER (WHERE old_loses AND NOT new_loses) AS pages_given_back,"
    " sum(total) FILTER (WHERE old_loses AND NOT new_loses) AS their_dollars,"
    " count(*) FILTER (WHERE new_loses AND NOT old_loses) AS pages_taken FROM k"
).show(max_rows=100)
```

## Results

Payee rows, 2018: 1,254,329 rows and $4,192,100,980.91. `ENTITY_TP` is blank on 96,542 of them,
$382,034,687.24 (9.11%), where the name decides.

**The first list** had `CPA` and `BANK` too. On the names only it moves, `CPA` was 67.18% organization dollars on
filed rows: `BLACKMAN, PERRY CPA` is $68,225 filed IND, and `HEINITZ, MARK CPA` and three more are people. `BANK`
was 0%: 25 filed IND rows ($10,618.70) and no organization's, though those 'persons' are banks a filer typed IND
(`FIRST, BANK`, `FRONTIER, BANK`). Both are out. With them the payee rule read 0.72% of person dollars as an
organization's.

**The final list** (`PC PA NA PAC PLC CO COMPANY ASSOCIATES GROUP LNC LLN`), on filed rows:

| Rule | Person dollars read as an organization's | Organization dollars read as a person's |
| --- | --- | --- |
| Contributor (`is_organization_name`, V8) | 0.70% | 0.68% |
| Payee (`is_payee_organization_name`) | 0.70% | 0.37% |

Each suffix over the names only it moves (section D):

| Suffix | Filed person $ | Filed organization $ | Organization share | Blank $ |
| --- | --- | --- | --- | --- |
| NA | 7,543 | 1,508,369 | 99.50% | 592,703 |
| PC | 0 | 2,263,154 | 100% | 488,879 |
| PAC | 0 | 91,560 | 100% | 478,202 |
| COMPANY | 0 | 834,274 | 100% | 342,270 |
| ASSOCIATES | 0 | 4,349,462 | 100% | 325,864 |
| LLN | 0 | 0 | — | 157,307 |
| GROUP | 0 | 35,235 | 100% | 64,741 |
| LNC | 0 | 0 | — | 40,271 |
| LLC, before DBA or PAC | 0 | 456,953 | 100% | 30,000 |
| PA | 0 | 584,594 | 100% | 20,300 |
| CO | 1,463 | 21,685 | 93.68% | 12,806 |
| INC, before DBA or PAC | 0 | 235,712 | 100% | 1,696 |
| PLC | 0 | 167,090 | 100% | 1,234 |

The filed IND/CAN names it reads as an organization's are six, $9,006, every one a firm or a placeholder a filer typed
as a person (`BARCLAYCARDUS, NA`, `APFEL, LEVY, ZLOTNICK & CO., -`, `SUMMARY, NA`, `FEDEX USA, NA`). Read by eye, none
of the 25 largest keys it moves to an organization's is a person's (section H): `CHAIN BRIDGE BANK N.A.`
($574,428), `DEMOCRACY ENGINE, INC. PAC`, `VERDOLINO & LOWEY, P.C.`, `FAIRBANK, MASLIN, MAULIN, METZ & ASSOCIATES`,
`IMAGE DIRECT,LLN` first.

**Pages, on 2018's dollars alone** (sections F, I):

| Rule | Keys with blank-type person rows | Their blank person $ | Of them, losing their page |
| --- | --- | --- | --- |
| Contributor | 431 | 3,681,870.65 | 345 |
| Payee | 362 | 1,125,597.42 | 309 |

The payee rule gives 36 keys their page back ($2,962,949.18) and takes none away.

**What it leaves** (section G). Of the 25 largest keys whose blank-type rows it still reads as a person's, 11 are
firms that lose their page, and no payee suffix ends any of them: a split initial (`CHAIN BRIDGE BANK, N,A`,
$55,440, beside `CHAIN BRIDGE BANK N.A.`'s own page), a name with no suffix (`LNEMARK, PRINTING` $46,078; `DEPT OF
TREASURY, IRS,` $39,171), a suffix run into the word before it (`FLANAGAN,FULKERSON&CO.LLC`), `LP`, which V8 left out
because people's names end in it (`1000 UNIVERSITY AVENUE PROPERTIES, LP`), and misspelt legal forms (`, ICN` twice,
`,LIC`, `, LLCQ`, `, LL`, `, LLX`; $9,200 to $15,371 each). Five are people (`LAFAVE, LORI,`, `ROSS, BRITTON`,
`JONES, JUSTIN C`, `THOMAS, STEVEN G`, `POSIN, JULIA JAYE`); the other nine keep their page. A suffix rule cannot
reach the rest without reading people's names as firms, so they are left: gold weighs every cycle, and a firm
with filed rows elsewhere keeps its page.

## NEU-2566: misspelt legal forms, LP and the split N,A

Measured for [NEU-2566](https://linear.app/neuroticsasquatch/issue/NEU-2566). The payee rule above leaves firms whose
suffix is misspelt or split, and section G lists them. This measures each candidate as section D measured the
suffixes: on the names only that candidate moves, with NEU-2541's rule as the baseline. A candidate is kept when filed
organization dollars are at least 98% of the filed dollars it moves, or it moves no filed person's dollar at all, as
`LNC` and `LLN` were kept. Nothing is written: it reads one build's silver.

| What | Value |
| --- | --- |
| Run | 2026-11-28, by hand over SSH on `music-box-dancer`; output in `~/fundlens-efd-backfill/payees2566.txt` |
| Silver | 2018's build `20261128T045110Z`, NEU-2180's rebuild with NEU-2541's rule (`c3536df`) |
| 2012 | Not measured: no 2012 build has `operating_expenditure` silver yet. NEU-2180's backfill builds it after 2018 |
| Code | `main` at `c3536df`. The script carries its own copy of NEU-2541's rule as the baseline, so it measures the same thing on later code |

The candidates:

- **Typos:** `ICN`, `LLCQ`, `LLX`, `LL`, `LIC`, at the last word or a word before `PAC` or `DBA`, as the payee suffixes are.
- **`LP`**, as a payee suffix only. V8 left it out because it ends people's names in `indiv`.
- **`CO` fused to a strict legal suffix** as the last word (`&CO.LLC` is `COLLC`, the period deleted before the split).
- **`N` and `A` as the last two words**, measured twice: split by a comma alone (`N,A`), and split by anything else
  (`N A`, which is mostly `N/A`).

### How to re-run

Run it only when no pipeline step is running, as above. Its arguments are `<cycle>=<build>` pairs; a build with no
`operating_expenditure` silver is reported and skipped.

```bash
# laptop: the script below, saved as payees2566.py
scp payees2566.py hetzner-01:~/fundlens-efd-backfill/payees2566.py
```

```bash
# VM, in tmux, in ~/fundlens-efd-backfill
A="2018=$(cat 2018/build-id.txt)"; [ -f 2012/build-id.txt ] && A="$A 2012=$(cat 2012/build-id.txt)"; echo "$A"
py payees2566.py $A > payees2566.txt; wc -l payees2566.txt
```

It prints sections A to J. **D** and **D'** are each candidate on the names only it moves, by cycle and over every
cycle given, with whether it is kept. **C** is NEU-2541's rule, with every candidate and with the kept ones, against
`ENTITY_TP` on filed rows. **E** and **E'** are the filed IND/CAN names and the blank-type names the candidates move,
to read by eye. **F** to **I** are the page rule as above, with the kept candidates. **J** is the ticket's named firms.

```python
"""NEU-2566's candidates for the payee classifier, each measured on the names only it moves (as
payee-names-2018.md section D measured NEU-2541's suffixes), on one or more builds' silver.
Reads silver only; writes nothing. `payees2566.py <cycle>=<build> [<cycle>=<build> ...]`.

The baseline is NEU-2541's payee rule, copied here so the script measures the same thing on any
deployed code. A candidate is kept when, over every cycle given, filed organization dollars are at
least 98% of the filed dollars it moves (or it moves no filed person dollar at all)."""

import re
import sys

from duckdb.func import FunctionNullHandling

from fundlens import paths
from fundlens.load import gold
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.settings import get_settings
from fundlens.transform import runner

STRICT = normalize.STRICT_LEGAL_SUFFIXES
# NEU-2541's payee suffixes and followers, as merged in c3536df.
BASE_SUFFIXES = frozenset(
    {"PC", "PA", "NA", "PAC", "PLC", "CO", "COMPANY", "ASSOCIATES", "GROUP", "LNC", "LLN"}
)
FOLLOWERS = frozenset({"PAC", "DBA"})
# NEU-2566's candidate suffixes: typos of INC (ICN), LLC (LLCQ, LLX, LL, LIC), and LP.
CANDIDATE_SUFFIXES = ("ICN", "LLCQ", "LLX", "LL", "LIC", "LP")


def ends(tokens):
    """The words a payee suffix is read at: the last, and each before a PAC or DBA."""
    out = [tokens[-1]] if tokens else []
    out += [tokens[i - 1] for i in range(1, len(tokens)) if tokens[i] in FOLLOWERS]
    return out


def base_suffix(raw):
    if raw is None:
        return None
    for end in ends(normalize._name_tokens(raw)):  # pyright: ignore
        if end in STRICT or end in BASE_SUFFIXES:
            return end
    return None


def candidate(raw):
    """The one candidate that makes `raw` a firm's where the baseline does not, or None. Checked
    in this order: N,A at the end, split by a comma alone ('N,A'); N and A as the last two words,
    split by anything ('N/A' too); a legal form fused to CO at the end ('&CO.LLC' is COLLC); then
    each candidate suffix at an end."""
    if raw is None:
        return None
    tokens = normalize._name_tokens(raw)  # pyright: ignore
    if len(tokens) >= 3 and re.search(r"[^A-Z0-9]N\s*,\s*A\W*$", raw.upper()):
        return "N,A"
    if len(tokens) >= 3 and tokens[-2:] == ["N", "A"]:
        return "N A"
    if tokens and tokens[-1].startswith("CO") and tokens[-1][2:] in STRICT:
        return "CO+" + tokens[-1][2:]
    for end in ends(tokens):
        if end in CANDIDATE_SUFFIXES:
            return end
    return None


pairs = [arg.split("=") for arg in sys.argv[1:]]
if not pairs:
    sys.exit("usage: payees2566.py <cycle>=<build> [...]")
settings = get_settings()
store = R2.from_settings(settings)


def parquet(cycle, build):
    prefix = paths.silver_partition("operating_expenditure", cycle, build)
    keys = [key for key in store.list_keys(prefix + "/") if key.endswith(".parquet")]
    if not keys:
        return None
    for key in keys:
        local = paths.local_path(settings.data_dir, key)
        if not local.exists():
            store.download_to(key, local)
    files = paths.local_path(settings.data_dir, prefix) / "**" / "*.parquet"
    return f"read_parquet({runner.literal(files)}, hive_partitioning = false)"


con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
normalize.register(con)
for name, fn in (("base_suffix", base_suffix), ("candidate", candidate)):
    con.create_function(  # pyright: ignore
        name, fn, ["VARCHAR"], "VARCHAR", null_handling=FunctionNullHandling.SPECIAL
    )

selects = []
for cycle_s, build in pairs:
    source = parquet(int(cycle_s), build)
    if source is None:
        print(f"{cycle_s} build {build}: no operating_expenditure silver; not measured")
        continue
    print(f"{cycle_s} build {build}: measured")
    selects.append(
        f"SELECT {int(cycle_s)} AS cycle, payee_key, payee_name, entity_type, amount FROM {source}"
        " WHERE counted AND payee_key IS NOT NULL AND NOT is_in_kind"
    )
if not selects:
    sys.exit("nothing to measure")
con.execute("CREATE TEMP TABLE oe AS " + " UNION ALL ".join(selects))
con.execute(
    "CREATE TEMP TABLE cls AS SELECT payee_name,"
    " is_organization_name(payee_name) OR base_suffix(payee_name) IS NOT NULL AS base_org,"
    " candidate(payee_name) AS cand FROM (SELECT DISTINCT payee_name FROM oe)"
)
# A candidate counts only on names the baseline reads as a person's.
con.execute("UPDATE cls SET cand = NULL WHERE base_org")
con.execute(
    "CREATE TEMP TABLE r AS SELECT oe.*, cls.base_org, cls.cand,"
    " entity_type IN ('IND', 'CAN') AS person_tp FROM oe JOIN cls USING (payee_name)"
)

print("\nA. Payee dollars by cycle, ENTITY_TP filed or blank")
con.sql(
    "SELECT cycle, entity_type IS NOT NULL AS filed, count(*) AS rows, sum(amount) AS amount,"
    " round(100 * sum(amount) / sum(sum(amount)) OVER (PARTITION BY cycle), 2) AS pct"
    " FROM r GROUP BY cycle, filed ORDER BY cycle, filed"
).show(max_rows=100)

D = (
    "count(*) FILTER (WHERE person_tp) AS filed_person_rows,"
    " coalesce(sum(amount) FILTER (WHERE person_tp), 0) AS filed_person_dollars,"
    " count(*) FILTER (WHERE NOT person_tp) AS filed_org_rows,"
    " coalesce(sum(amount) FILTER (WHERE NOT person_tp), 0) AS filed_org_dollars,"
    " round(100 * filed_org_dollars / nullif(filed_org_dollars + filed_person_dollars, 0), 2) AS org_pct,"
    " count(*) FILTER (WHERE entity_type IS NULL) AS blank_rows,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IS NULL), 0) AS blank_dollars"
)
print("\nD. Each candidate, on the names only it moves, by cycle")
con.sql(
    f"SELECT cand, cycle, {D} FROM r WHERE cand IS NOT NULL GROUP BY ALL ORDER BY cand, cycle"
).show(max_rows=100, max_width=300)
print("\nD'. Each candidate over every cycle given, and whether it is kept (org_pct >= 98, or no filed person $)")
con.execute(
    f"CREATE TEMP TABLE d AS SELECT cand, {D} FROM r WHERE cand IS NOT NULL GROUP BY cand"
)
con.execute(
    "CREATE TEMP TABLE kept AS SELECT cand FROM d WHERE filed_person_dollars = 0 OR org_pct >= 98"
)
con.sql(
    "SELECT d.*, cand IN (SELECT cand FROM kept) AS kept FROM d ORDER BY blank_dollars DESC, cand"
).show(max_rows=100, max_width=300)
for cand in ("N,A", "N A", "CO+LLC", *CANDIDATE_SUFFIXES):
    if not con.execute("SELECT count(*) FROM d WHERE cand = ?", [cand]).fetchone()[0]:  # pyright: ignore
        print(f"   {cand}: moves no name in these builds")

con.execute(
    "CREATE TEMP TABLE r2 AS SELECT *, base_org OR cand IS NOT NULL AS all_org,"
    " base_org OR coalesce(cand IN (SELECT cand FROM kept), false) AS kept_org FROM r"
)

print("\nC. Filed rows, by cycle: each rule against ENTITY_TP (gate on 2018: persons <= 1.00, organizations <= 0.37)")
con.sql(
    "SELECT cycle, rule, round(100 * coalesce(sum(amount) FILTER (WHERE org AND person_tp), 0) / sum(amount) FILTER (WHERE person_tp), 2)"
    " AS persons_read_as_organizations, round(100 * coalesce(sum(amount) FILTER (WHERE NOT org AND NOT person_tp), 0)"
    " / sum(amount) FILTER (WHERE NOT person_tp), 2) AS organizations_read_as_persons"
    " FROM (SELECT cycle, amount, person_tp, unnest(['1 NEU-2541', '2 + every candidate', '3 + kept']) AS rule,"
    " unnest([base_org, all_org, kept_org]) AS org FROM r2 WHERE entity_type IS NOT NULL) GROUP BY ALL ORDER BY ALL"
).show(max_rows=100)

print("\nE. Every filed IND/CAN name a candidate moves, the 40 largest (by eye: what it misreads)")
con.sql(
    "SELECT cand, cycle, payee_name, entity_type, count(*) AS rows, sum(amount) AS amount FROM r2"
    " WHERE cand IS NOT NULL AND person_tp GROUP BY ALL ORDER BY amount DESC, payee_name LIMIT 40"
).show(max_rows=100, max_width=300)

print("\nE'. The 40 largest blank-type names a candidate moves (by eye: no person)")
con.sql(
    "SELECT cand, cycle, payee_name, count(*) AS rows, sum(amount) AS amount FROM r2"
    " WHERE cand IS NOT NULL AND entity_type IS NULL GROUP BY ALL ORDER BY amount DESC, payee_name LIMIT 40"
).show(max_rows=100, max_width=300)

# The page rule (spec §5.4) per cycle, on that cycle's dollars alone, as payshare.py weighs it.
con.execute("CREATE TEMP TABLE no_page AS SELECT unnest($1::VARCHAR[]) AS payee_key", [gold.payee_no_page()])
con.execute(
    "CREATE TEMP TABLE k AS SELECT cycle, payee_key, arg_max(payee_name, amount) AS name, sum(amount) AS total,"
    " coalesce(sum(amount) FILTER (WHERE person_tp OR (entity_type IS NULL AND NOT base_org)), 0) AS base_p,"
    " coalesce(sum(amount) FILTER (WHERE person_tp OR (entity_type IS NULL AND NOT kept_org)), 0) AS kept_p,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IS NULL AND NOT base_org), 0) AS base_blank_p,"
    " coalesce(sum(amount) FILTER (WHERE entity_type IS NULL AND NOT kept_org), 0) AS kept_blank_p,"
    " any_value(cand) FILTER (WHERE entity_type IS NULL AND kept_org AND NOT base_org) AS cand,"
    " base_p > 0.5 * total AND base_p > 0 AS base_loses, kept_p > 0.5 * total AND kept_p > 0 AS kept_loses"
    " FROM r2 ANTI JOIN no_page USING (payee_key) GROUP BY cycle, payee_key"
)

print("\nF. Keys with blank-type rows read as a person's, and how many lose their page, by cycle")
con.sql(
    "SELECT cycle, 'NEU-2541' AS rule, count(*) FILTER (WHERE base_blank_p > 0) AS keys, sum(base_blank_p) AS blank_person_dollars,"
    " count(*) FILTER (WHERE base_blank_p > 0 AND base_loses) AS lose_page FROM k GROUP BY cycle"
    " UNION ALL SELECT cycle, '+ kept', count(*) FILTER (WHERE kept_blank_p > 0), sum(kept_blank_p),"
    " count(*) FILTER (WHERE kept_blank_p > 0 AND kept_loses) FROM k GROUP BY cycle ORDER BY ALL"
).show(max_rows=100)

print("\nG. With the kept candidates: the 25 largest keys per cycle with blank-type rows read as a person's")
con.sql(
    "SELECT cycle, payee_key, name, kept_blank_p AS blank_person, total, kept_loses AS loses_page, base_loses AS lost_before"
    " FROM (SELECT *, row_number() OVER (PARTITION BY cycle ORDER BY kept_blank_p DESC, payee_key) AS n FROM k WHERE kept_blank_p > 0)"
    " WHERE n <= 25 ORDER BY cycle, n"
).show(max_rows=100, max_width=300)

print("\nH. The 25 largest keys per cycle the kept candidates give a page back")
con.sql(
    "SELECT cycle, payee_key, name, cand, total FROM k WHERE base_loses AND NOT kept_loses"
    " ORDER BY cycle, total DESC, payee_key"
).show(max_rows=60, max_width=300)

print("\nI. Pages the kept candidates give back and take away, by cycle")
con.sql(
    "SELECT cycle, count(*) FILTER (WHERE base_loses AND NOT kept_loses) AS pages_given_back,"
    " sum(total) FILTER (WHERE base_loses AND NOT kept_loses) AS their_dollars,"
    " count(*) FILTER (WHERE kept_loses AND NOT base_loses) AS pages_taken FROM k GROUP BY cycle ORDER BY cycle"
).show(max_rows=100)

print("\nJ. NEU-2566's named firms, 2018: loses_page before and with the kept candidates")
con.sql(
    "SELECT payee_key, name, total, base_loses, kept_loses, cand FROM k WHERE cycle = 2018 AND ("
    " name LIKE 'CHAIN BRIDGE BANK%' OR name LIKE 'CIVIS ANALYTICS%' OR name LIKE 'GORDON, AND SCHWENKMEYER%'"
    " OR name LIKE 'TRILOGY INTERACTIVE%' OR name LIKE 'BURDICK CONSULTING%' OR name LIKE 'NEW BLUE INTERACTIVE%'"
    " OR name LIKE 'JOHNSON PRO SERVICES%' OR name LIKE 'FLANAGAN%FULKERSON%' OR name LIKE '1000 UNIVERSITY AVENUE%')"
    " ORDER BY total DESC"
).show(max_rows=100, max_width=300)
```

### Results

Each candidate over the names only it moves, 2018 (section D'):

| Candidate | Filed person $ | Filed organization $ | Organization share | Blank $ | Kept |
| --- | --- | --- | --- | --- | --- |
| `N,A` (comma) | 0 | 0 | — | 55,440 | yes |
| `ICN` | 0 | 0 | — | 38,235 | yes |
| `LP` | 250 | 2,517,249 | 99.99% | 25,441 | yes |
| `CO` + `LLC` | 0 | 0 | — | 19,375 | yes |
| `LIC` | 0 | 0 | — | 12,800 | yes |
| `LLCQ` | 0 | 0 | — | 12,232 | yes |
| `LL` | 0 | 10,000 | 100% | 10,000 | yes |
| `LLX` | 0 | 0 | — | 9,200 | yes |
| `N A` (other) | 29,655 | 5,121 | 14.73% | 0 | no |

`N A` fails on the `N/A` placeholder: the filed IND names it moves are `THE PRINTERS, INC, N/A`, `OTHER, N/A`, `US
POSTAL SERVICE, N/A` and six more. The one filed IND name `LP` moves is `SED QUAERE, L.P.` ($250), a firm. Read by eye,
no blank-type name a candidate moves is a person's (section E'): the ticket's firms, `PHILADELPHIA 76ERS, L.P.`,
`BLACKSTONE ADMINISTRATIVE SERVICES, LP`, and two more spellings of `FLANAGAN, FULKERSON & CO.LLC` and of `GORDON AND
SCHWENKMERYER, ICN`. No `CO` fused to a legal form but `LLC` appears.

On filed rows (section C), NEU-2541's gate holds:

| Rule | Person dollars read as an organization's | Organization dollars read as a person's |
| --- | --- | --- |
| NEU-2541 | 0.70% | 0.37% |
| With every candidate | 0.71% | 0.29% |
| With the kept ones | 0.70% | 0.29% |

**Pages, on 2018's dollars alone** (sections F, I): keys with blank-type person rows go from 362 to 349, their
blank person dollars from $1,125,597.42 to $942,874.57, and those losing their page from 309 to 296. The kept
candidates give 13 keys their page back ($200,386.40) and take none away. Every firm the ticket names keeps its page
(section J), `CHAIN BRIDGE BANK, N,A` ($56,022) the largest.

**What it leaves** (section G). Among the 25 largest keys whose blank-type rows are still read as a person's, those
losing their page are people (`LAFAVE, LORI,`, `ROSS, BRITTON`, `JONES, JUSTIN, C.,`, `THOMAS, STEVEN G`, `POSIN,
JULIA JAYE`, `PEREZ-CUBAS, OLIVIA`, `THOMAS, STEVEN`, `BEHNKE, KATIE`), placeholders (`PEOPLE, VARIOUS`), names
with no suffix (`LNEMARK, PRINTING` $46,078, `DEPT OF TREASURY, IRS,` $39,171, `PRINTINT, J&R,,,`), and one typo
not among the candidates (`MERKLE RESPONSE SERVICE, NIC.`, $8,222). None ends in a kept candidate.

