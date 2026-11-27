# Runbook: backfill every table this project adds, for every cycle

How to rebuild every cycle before 2024 with the seven silver tables the every-FEC-dollar project adds, so that each
one holds them for every cycle FEC publishes their source for (NEU-2180; every-FEC-dollar spec §2, §3, §10). Each
milestone runbook put its tables live for 2024 alone ([reported-totals-run.md](reported-totals-run.md),
[spending-run.md](spending-run.md), [outside-spending-run.md](outside-spending-run.md),
[leadership-bundling-run.md](leadership-bundling-run.md)). Every other cycle is still live from v1's backfill
([backfill.md](backfill.md), 2026-11-13 to 2026-11-17), transformed before any of the seven existed, so gold and the
dataset snapshot read it as having none of their rows. This run rebuilds 2022 back to 1980 with one `fundlens run`
per cycle, checks each one, then empties `paths.BACKFILL_PENDING`, so a build that lacks a table fails the load
and the snapshot again, as v1 intended. The figures go into [`docs/capacity.md`](../capacity.md) → *Every-FEC-dollar
backfill*. Run it one cycle at a time, with the checks between cycles. Append to the [Log](#log) at the bottom;
never rewrite it.

| Table | Source | First cycle with rows (spec) | Before it |
| --- | --- | --- | --- |
| `reported_total` | `webk` (1996–2006), `committee_summary` (2008–) | 1996 | an empty partition |
| `candidate_reported_total` | `weball` | 1980, to 2006 | — (empty from 2008: §4.2) |
| `operating_expenditure` | `oppexp` | 2004 | an empty partition |
| `electioneering_communication` | `ElectioneeringComm` | 2010 | an empty partition |
| `leadership_pac` | `leadership` | 2010 | an empty partition |
| `lobbyist_pac` | `lobbyist` | 2010 | an empty partition |
| `bundling_report` | `lobbyist_bundle` | 2010 | an empty partition |

The ticket asks for `reported_total` rows from 1980. Spec §4.1–§4.2 put a cycle's reported totals before 1996 in
`candidate_reported_total` (`weball`'s candidates), with `reported_total` (committees) empty until `webk` starts:
reported totals exist from 1980, in the table the spec gives them. Step 2.3 checks each by its range.

Two more of the project's files feed v1's `independent_expenditure`, which every build already holds: the 24/48-hour
file (`ie_24_48`) and `CommunicationCosts`, both from 2010. A cycle built before NEU-2165 lacks their rows and the
table's six new columns (spec §6.7), so this run rebuilds them too.

**Why `fundlens run` per cycle.** v1's backfill ran each step by hand, because `run` then resolved with `--full`
after every transform. Resolution is incremental since NEU-2062 (spec §6.10): a cycle's new contributor keys against
the live model, minutes, not hours. So `run` is the whole cycle: extract, seats, transform, resolve, load, publish,
under one build, each step writing its marker. A failed step resumes with the same command and build ID (step 2.5).

**Why each cycle is published before the next.** `load` rebuilds all of gold from every cycle's live build
(`markers/live.json`), so a cycle's new tables reach gold only by being published. Publishing each one lets it be
checked against the gold it replaced (`gold_prev`) before the next cycle changes gold again, and rolled back alone.
It costs a load per cycle: about 25 minutes each (2024's was 1,520 s, NEU-2179), a third of the run.

**Why newest first.** The ticket's order, 2022 back to 1980. The cycles from 2010 have every file, as 2024 does, so
the procedure meets every new table, and the two cycles larger than 2024 (2020 and 2022, `capacity.md` →
*Backfill*), first, while the memory is watched. Each earlier range has fewer files (the table above), and the run
gets cheaper as it goes.

**Why extract runs.** No cycle but 2024 and 2026 has the ten new files in bronze. `extract` downloads them and
checks v1's six against FEC's `Last-Modified` and size: a zip FEC has not changed is `unchanged`; one it has is
downloaded again, so the rebuild reads FEC's amendments since 2026-11-13. Step 2.3 separates those from this run's
code.

**Receipt totals will move in some cycles, by design.** Since v1's backfill, NEU-2400 (memo line naming the
non-contribution account), NEU-2401 (FEC's repeated rows) and NEU-2402 (refund memos on other receipts) changed
how silver counts receipts. 2024 and 2026 already carry them; every cycle rebuilt here gains them. Step 2.3 lists
what moved, and only a cycle that moves by more than 1% stops the run.

**2024 and 2026.** 2024 is live from NEU-2179's build `20261126T191724Z`, which holds every table: it is not
rebuilt. 2026 is rebuilt every Sunday by the scheduled `fundlens weekly` task; its build of 2026-11-23 predates
NEU-2175's three tables. Step 5 checks both, after a Sunday's run or a hand run of 2026.

**The payee person rule is measured first** (spec §5.4). Before 2020, `ENTITY_TP` is blank on 9.6–29.5% of spending
dollars, so the name classifier decides which payees are people and get no page. It was measured on `indiv`'s
names, never on payees'. Step 3 measures it on 2018's silver before 2018 is published, and a failed measurement
stops 2004–2018 from going live.

**Not in this runbook:** the `.fec` raw filings (M5, spec §9); 2024 (live with every table); `resolve --full`
(only if step 2.3 reports re-pointed keys, afterwards, as [weekly.md](weekly.md) → *Re-resolving with `--full`*
says); adjudicating new clusters; scoring other cycles against DIME.

## Before you start

- Every blocker of NEU-2180 is Done: NEU-2059, NEU-2060, NEU-2061, NEU-2352 and the four milestone runbooks. This
  runbook is merged. Step 1.1 checks that the deployed code includes it.
- **No merge to `main` while a cycle runs.** Every merge redeploys `pipeline` and kills a running `docker exec`
  (2026-11-02 a docs merge killed a `publish` part way). Step 1.1 turns off Dependabot's auto-merge until step 9.
  Between two cycles, merge only a fix this run needs, or docs; step 2.1 records the SHA each cycle is built from.
  A merge that changes silver is a reason to rebuild the cycles built before it: decide in the Log.
- **Not over Sunday's weekly run.** The scheduled task starts at Sunday 03:00 UTC and runs about 80 minutes with
  its snapshot ([weekly.md](weekly.md) Facts). Two pipeline runs at once do not fit the box. Start no cycle after
  Sunday 01:00 UTC until the weekly has published (step 2.1 checks the clock). A cycle may run through the nightly
  backup (02:00–02:30 UTC): the dump takes no lock on a gold table, but steps run slower while it does.
- The laptop is on the tailnet, `ssh hetzner-01` works, `~/projects/fundlens` is a clone of this repo, `gh` and
  `jq` are installed, and you can sign in to Coolify, Bugsink (`https://bugsink.neuroticsasquat.ch`) and Linear.
- Allow two or three days of sessions: 22 cycles of about 30 to 70 minutes each. A cycle can be left between any
  two cycles, and a failed one resumed (step 2.5).

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Cycles to build | 2022, 2020, …, 1982, 1980: 22 cycles, in that order, 2018 by step 3. Then 2026 if step 5 finds it short |
| Live before this run | 2024 at `20261126T191724Z` (NEU-2179), every table. 2026 at `20261123T224142Z` or a later Sunday's build. 1980–2022 at v1's backfill builds of 2026-11-13 to 2026-11-16 ([backfill.md](backfill.md) Log), none of the seven tables |
| The backfill-pending tables | `paths.BACKFILL_PENDING`: the seven above. Emptied in step 8 |
| Files per cycle | 1980–1994: v1's five and `weball` (6). 1996–1998: and `webk` (7). 2000–2002: and `ccl` (8). 2004–2006: and `oppexp` (9). 2008: and `committee_summary` (10). 2010–2022: and `ie_24_48`, `ElectioneeringComm`, `CommunicationCosts`, `leadership`, `lobbyist`, `lobbyist_bundle` (16) |
| `pipeline` memory | `mem_limit: 40g`. `DUCKDB_MEMORY_LIMIT` `32GB` (29.80 GiB), the compose fallback. 2024's transform peaked at 28.76 GiB with every table (NEU-2179), in `write contribution 2024` |
| Disk floor | **Stop if free disk on `/` drops under 60 GB**, at any time. Start a cycle only with at least 130 GB free: up to 60 GB of DuckDB scratch (`DUCKDB_MAX_TEMP_DIRECTORY_SIZE`), bronze being unzipped, and the floor. 202 GB were free after NEU-2179's publish |
| Monitors | `fundlens/publish` gets a push from every `publish`, so each cycle's resets its deadman, as a weekly run would. `run` without `--scheduled` pushes nothing to `fundlens/weekly` |
| Reconciliation | Gold `reconciliation`, 2008 on: committees whose figure is over FEC's reported one by more than 1% (spec §4.5, §5.6). 2024 lists 163 committees on `individual_itemized` (NEU-2147) |

## 0. Session setup

Every step runs on the VM, in this shell, unless it says `# laptop`.

```bash
# laptop
ssh hetzner-01
```

```bash
# VM. tmux keeps a long step running if the SSH session drops.
tmux new -s fundlens-efd-backfill
```

In the tmux session, define the helpers. Paste the whole block:

```bash
# VM, in tmux
mkdir -p ~/fundlens-efd-backfill && cd ~/fundlens-efd-backfill
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# psql in the fundlens database. `-i`, so a query can come from stdin (`pg < file.sql`).
pg() { docker exec -i "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
# A step's completion marker, or MISSING: `mk <step> <cycle> <build>`.
mk() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; m = markers.read(sys.argv[1], R2.from_settings(get_settings()), cycle=int(sys.argv[2]), build_id=sys.argv[3]); print(m.model_dump_json(indent=2) if m else "MISSING")' "$1" "$2" "$3"; }
# Each cycle's live build, from markers/live.json.
live() { docker exec "$(fl pipeline)" python -c 'from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; print(markers.read_live(R2.from_settings(get_settings())))'; }
# One cycle's live build ID: `live_of <cycle>`.
live_of() { live | grep -o "$1: '[0-9TZ]*'" | grep -o '[0-9]\{8\}T[0-9]\{6\}Z'; }
# The live gold build and the rollback target, from Postgres.
gmeta() { pg -Atc "select 'gold', build_id, published_at from gold.meta union all select 'gold_prev', build_id, published_at from gold_prev.meta"; }
# The deployed SHA.
sha() { docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES | sed 's/.*service.version=//; s/,.*//'; }
# Free disk on / in decimal GB, as capacity.md counts sizes.
free_gb() { df -BGB --output=avail / | tail -1 | tr -dc '0-9'; }
# A script on stdin, in `pipeline`, without its JSON log lines: `py <script> [args]`.
py() { local s=$1; shift; docker exec -i "$(fl pipeline)" python - "$@" < "$s" 2>&1 | grep -v '^{'; }

# One cycle's `fundlens run`, new or resumed: `cycle_run <cycle> [<build>]`. Its output is in
# <cycle>/run.log, and with the JSON log lines in <cycle>/run-raw.log, `time`'s figures at the end.
# The build the cycle was live from before is kept in <cycle>/old-build.txt.
cycle_run() {
  local c=$1 b=${2:-$(date -u +%Y%m%dT%H%M%SZ)} rc
  mkdir -p "$c" && echo "$b" > "$c/build-id.txt"
  [ -s "$c/old-build.txt" ] || live_of "$c" > "$c/old-build.txt"
  echo "$(date -u +%FT%TZ) start $c $b $(sha)" | tee -a "$c/window.txt"
  ( set -o pipefail; { time docker exec "$(fl pipeline)" fundlens run --cycle "$c" --build-id "$b"; } 2>&1 | tee -a "$c/run-raw.log" | grep -v '^{' | tee -a "$c/run.log" )
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "$(date -u +%FT%TZ) STOPPED $c $b, exit $rc" | tee -a "$c/window.txt"
    return 1
  fi
  echo "$(date -u +%FT%TZ) end $c $b" | tee -a "$c/window.txt"
}

# One step of a cycle's build by hand, logged as cycle_run logs: `cycle_step <cycle> <step>`.
cycle_step() {
  local c=$1 s=$2 b extra=
  b=$(cat "$c/build-id.txt"); [ "$s" = seats ] && extra=--report
  ( set -o pipefail; { time docker exec "$(fl pipeline)" fundlens "$s" --cycle "$c" $extra --build-id "$b"; } 2>&1 | tee -a "$c/run-raw.log" | grep -v '^{' | tee -a "$c/run.log" )
}

# The peak `pipeline` memory while a cycle ran, and the least free disk: `cycle_peak <cycle>`.
cycle_peak() {
  local from to
  from=$(awk '$2 == "start" { print $1; exit }' "$1/window.txt")
  to=$(awk '$2 == "end" || $2 == "STOPPED" { t = $1 } END { print t }' "$1/window.txt")
  awk -v from="$from" -v to="$to" '$1 >= from && $1 <= to {
      f = $NF; sub(/^free=/, "", f); f += 0
      if (low == "" || f < low) low = f
      if ($2 !~ /^pipeline-/) next
      n = $3 + 0; u = $3; sub(/^[0-9.]+/, "", u)
      g = (u == "GiB") ? n : (u == "MiB") ? n / 1024 : (u == "KiB") ? n / 1048576 : n / 1073741824
      if (g > max) { max = g; at = $1 }
    } END { printf "%.2f GiB at %s; least free disk %s GB\n", max, at, low }' ~/fundlens-efd-backfill/mem.txt
}

# The last log line of a cycle's run at or before a UTC time: which step held the peak.
# `where <cycle> <time>`, the time as cycle_peak prints it.
where() {
  docker exec -i "$(fl pipeline)" python -c '
import json, sys
at, last = sys.argv[1][:19], None
for line in sys.stdin:
    if line.startswith("{"):
        entry = json.loads(line)
        if entry["ts"][:19] <= at and (last is None or entry["ts"] >= last["ts"]):
            last = entry
print(*((last["ts"], last["message"]) if last else ("no log line before it",)))' "$2" < "$1/run-raw.log"
}
```

**Expected:** no output. If the tmux session is lost, run `tmux attach -t fundlens-efd-backfill`. If the session
itself is gone, `cd ~/fundlens-efd-backfill` and paste the block again: every build ID is in
`<cycle>/build-id.txt`.

**Scripts.** Each script below is saved to a file with `cat > <name> <<'EOF'` and run from it, never pasted as a
heredoc into `docker exec`: a long paste into tmux can arrive mangled (NEU-2160's run), and a file arrives whole or
not at all. Check each arrived whole with `tail -3 <name>`. Save all four now.

`tables.py` lists, for each cycle's live build, the rows of each of the seven tables (from its `transformed`
marker) and whether R2 holds a Parquet part for each. `load` and the snapshot need the part once step 8 empties the
list; a table with 0 rows still has one:

```bash
# VM, in tmux
cat > tables.py <<'EOF'
"""Each cycle's live build: the rows of each of this project's seven silver tables, and the
tables it lacks in R2. `tables.py [<cycle> ...]`, every live cycle by default."""

import sys

from fundlens import markers, paths
from fundlens.r2 import R2
from fundlens.settings import get_settings

# The seven, named here rather than read from paths.BACKFILL_PENDING, which step 8 empties.
TABLES = ("reported_total", "candidate_reported_total", "operating_expenditure",
          "electioneering_communication", "leadership_pac", "lobbyist_pac", "bundling_report")
store = R2.from_settings(get_settings())
live = markers.read_live(store)
for cycle in [int(arg) for arg in sys.argv[1:]] or sorted(live):
    build = live[cycle]
    marker = markers.read("transformed", store, cycle=cycle, build_id=build)
    counts = marker.row_counts if marker else {}
    lacks = [table for table in TABLES
             if not any(key.endswith(".parquet")
                        for key in store.list_keys(paths.silver_partition(table, cycle, build) + "/"))]
    state = "complete" if not lacks else "LACKS " + ",".join(lacks)
    print(cycle, build, state, " ".join(f"{table}={counts.get(table, '-')}" for table in TABLES))
EOF
tail -3 tables.py
```

`verify.sql` compares one cycle's gold with the gold it replaced, and prints the cycle's new figures. It runs
after the cycle's publish, while `gold_prev` is the gold from before it:

```bash
# VM, in tmux
cat > verify.sql <<'EOF'
\pset footer off
-- psql -v c=<cycle>: run after that cycle's publish, so gold_prev is the gold before it.

\echo 'v1 receipt figures, gold against gold_prev: rows missing from one side, rows moved'
select case when cycle = :c then 'this cycle' else 'other cycles' end as cycles, tbl,
    count(*) filter (where state = 'missing') as missing, count(*) filter (where state = 'moved') as moved
from (
    select cycle, 'committee_cycle' as tbl,
        case when o.committee_id is null or n.committee_id is null then 'missing'
            when row(o.total_individual, o.self_funding, o.total_from_committees, o.total_from_organizations,
                    o.total_non_contribution_account, o.total_other_lines, o.total_refunds,
                    o.total_to_candidates, o.total_returned_by_candidates)
                is distinct from row(n.total_individual, n.self_funding, n.total_from_committees,
                    n.total_from_organizations, n.total_non_contribution_account, n.total_other_lines,
                    n.total_refunds, n.total_to_candidates, n.total_returned_by_candidates) then 'moved'
        end as state
    from gold_prev.committee_cycle o full join gold.committee_cycle n using (committee_id, cycle)
    union all
    select cycle, 'candidate_cycle',
        case when o.candidate_id is null or n.candidate_id is null then 'missing'
            when row(o.race_id, o.total_individual, o.total_committee, o.total_jfc_transfers, o.self_funding)
                is distinct from row(n.race_id, n.total_individual, n.total_committee, n.total_jfc_transfers,
                    n.self_funding) then 'moved'
        end
    from gold_prev.candidate_cycle o full join gold.candidate_cycle n using (candidate_id, cycle)
    union all
    select coalesce(o.cycle, n.cycle), 'race',
        case when o.race_id is null or n.race_id is null then 'missing'
            when row(o.candidate_count, o.total_individual, o.total_committee, o.total_jfc_transfers)
                is distinct from row(n.candidate_count, n.total_individual, n.total_committee,
                    n.total_jfc_transfers) then 'moved'
        end
    from gold_prev.race o full join gold.race n using (race_id)
    union all
    select cycle, 'cycle',
        case when o.cycle is null or n.cycle is null then 'missing'
            when row(o.race_count, o.contribution_count, o.total_amount)
                is distinct from row(n.race_count, n.contribution_count, n.total_amount) then 'moved'
        end
    from gold_prev.cycle o full join gold.cycle n using (cycle)
) compared
where state is not null
group by 1, 2
order by 1 desc, 2;

\echo 'The cycle''s contributions, before and after'
select o.contribution_count as before_count, n.contribution_count as after_count,
    o.total_amount as before_total, n.total_amount as after_total,
    round(100 * (n.total_amount / nullif(o.total_amount, 0) - 1), 3) as pct_moved
from gold_prev.cycle o join gold.cycle n using (cycle) where cycle = :c;

\echo 'The ten committees whose individual receipts moved most'
select committee_id, o.total_individual as before, n.total_individual as after,
    n.total_individual - o.total_individual as moved
from gold_prev.committee_cycle o join gold.committee_cycle n using (committee_id, cycle)
where cycle = :c and o.total_individual is distinct from n.total_individual
order by abs(n.total_individual - o.total_individual) desc, committee_id limit 10;

\echo 'The cycle''s new figures, committees'
select count(*) as committees, count(reported_receipts) as reported, count(total_operating_expenditures)
        as with_spending, sum(total_operating_expenditures) as spending,
    sum(ie_total) as ie, sum(communication_cost_total) as communication_costs,
    sum(party_coordinated_total) as coordinated, count(electioneering_total) as with_electioneering,
    sum(electioneering_total) as electioneering,
    count(*) filter (where is_leadership_pac) as leadership_pacs, count(sponsor_candidate_id) as sponsored,
    count(*) filter (where is_lobbyist_pac) as lobbyist_pacs, count(bundled_total) as with_bundled,
    sum(bundled_total) as bundled
from gold.committee_cycle where cycle = :c;

\echo 'The cycle''s new figures, candidates'
select count(*) as candidates, count(reported_receipts) as reported,
    count(total_operating_expenditures) as with_spending, count(electioneering) as with_electioneering
from gold.candidate_cycle where cycle = :c;

\echo 'Reconciliation: committees listed, of those with the reported figure'
select m.measure, count(r.committee_id) as listed, m.eligible,
    round(100.0 * count(r.committee_id) / nullif(m.eligible, 0), 2) as pct,
    coalesce(sum(r.fundlens - r.reported), 0) as over_by
from (
    select 'individual_itemized' as measure, count(*) filter (where cc.reported_individual_itemized is not null
            and not c.is_conduit) as eligible
    from gold.committee_cycle cc join gold.committee c using (committee_id) where cc.cycle = :c
    union all
    select 'operating_expenditures', count(reported_operating_expenditures)
    from gold.committee_cycle where cycle = :c
) m
left join gold.reconciliation r on r.measure = m.measure and r.cycle = :c
group by m.measure, m.eligible
order by m.measure;
EOF
tail -3 verify.sql
```

`silver.py` reads one build's silver from R2, as [leadership-bundling-run.md](leadership-bundling-run.md) step 7.1's
`sponsors.py` does: outside spending by kind and source file, and with `--payees` the payee person rule (step 3):

```bash
# VM, in tmux
cat > silver.py <<'EOF'
"""One build's silver: outside spending by kind and source file; with --payees, the payee person
rule (is_payee_organization_name, NEU-2541) against ENTITY_TP (every-FEC-dollar spec §5.4).
`silver.py <cycle> <build> [--payees]`."""

import sys

from fundlens import paths
from fundlens.r2 import R2
from fundlens.resolve import normalize
from fundlens.settings import get_settings
from fundlens.transform import runner

cycle, build = int(sys.argv[1]), sys.argv[2]
settings = get_settings()
store = R2.from_settings(settings)


def parquet(table):
    """The build's partition of a silver table, downloaded first where the volume lacks it."""
    prefix = paths.silver_partition(table, cycle, build)
    for key in store.list_keys(prefix + "/"):
        local = paths.local_path(settings.data_dir, key)
        if key.endswith(".parquet") and not local.exists():
            store.download_to(key, local)
    files = paths.local_path(settings.data_dir, prefix) / "**" / "*.parquet"
    return f"read_parquet({runner.literal(files)}, hive_partitioning = false)"


con = runner.connect(runner.Limits.from_settings(settings), paths.scratch_dir(settings.data_dir))
print("independent_expenditure by kind and source file")
con.sql(f"SELECT kind, source_file, count(communication_type) AS with_type, count(*) AS rows,"
        f" sum(amount) AS amount FROM {parquet('independent_expenditure')} GROUP BY ALL ORDER BY ALL").show()
if "--payees" in sys.argv[3:]:
    normalize.register(con)
    # The payee rows (spec §5.4): counted, a key, not an in-kind outlay.
    con.execute(f"CREATE TEMP TABLE oe AS SELECT payee_key, payee_name, entity_type, payee_is_person,"
                f" amount FROM {parquet('operating_expenditure')}"
                f" WHERE counted AND payee_key IS NOT NULL AND NOT is_in_kind")
    con.execute("CREATE TEMP TABLE cls AS SELECT payee_name, is_payee_organization_name(payee_name) AS org"
                " FROM (SELECT DISTINCT payee_name FROM oe WHERE payee_name IS NOT NULL)")
    print("Payee dollars by ENTITY_TP: filed or blank")
    con.sql("SELECT entity_type IS NOT NULL AS filed, count(*) AS rows, sum(amount) AS amount,"
            " round(100 * sum(amount) / sum(sum(amount)) OVER (), 2) AS pct FROM oe GROUP BY ALL ORDER BY ALL").show()
    print("Filed rows: the classifier against ENTITY_TP, as a share of each side's dollars")
    con.sql("SELECT round(100 * sum(amount) FILTER (WHERE cls.org AND entity_type IN ('IND', 'CAN'))"
            " / sum(amount) FILTER (WHERE entity_type IN ('IND', 'CAN')), 2) AS persons_read_as_organizations,"
            " round(100 * sum(amount) FILTER (WHERE NOT cls.org AND entity_type NOT IN ('IND', 'CAN'))"
            " / sum(amount) FILTER (WHERE entity_type NOT IN ('IND', 'CAN')), 2) AS organizations_read_as_persons"
            " FROM oe JOIN cls USING (payee_name) WHERE entity_type IS NOT NULL").show()
    for person, title in ((False, "an organization's: each gets a page"), (True, "a person's: no page")):
        print(f"The 25 largest keys with blank-type rows the classifier reads as {title}")
        con.sql(f"SELECT payee_key, arg_max(payee_name, amount) AS name, count(*) AS rows, sum(amount) AS amount"
                f" FROM oe WHERE entity_type IS NULL AND payee_is_person = {person}"
                f" GROUP BY payee_key ORDER BY amount DESC, payee_key LIMIT 25").show(max_width=250)
EOF
tail -3 silver.py
```

`record.py` writes a cycle's row of `capacity.md` → *Every-FEC-dollar backfill* (step 2.4):

```bash
# VM, in tmux
cat > record.py <<'EOF'
"""One cycle's row of capacity.md's Every-FEC-dollar backfill table.
`record.py <cycle> <build> <old build> <peak> <free GB> <load halves>`."""

import os
import re
import sys
from typing import get_args

import psycopg

from fundlens import markers, paths
from fundlens.fec.files import files_for
from fundlens.r2 import R2
from fundlens.settings import get_settings

cycle, build, old, peak, free, halves = int(sys.argv[1]), *sys.argv[2:7]
settings = get_settings()
store = R2.from_settings(settings)
V1_FILES = {"cm", "cn", "ccl", "indiv", "pas2", "oth"}
NEW_SILVER = {"reported_total", "candidate_reported_total", "operating_expenditure",
              "electioneering_communication", "leadership_pac", "lobbyist_pac", "bundling_report"}
NEW_GOLD = {"reconciliation", "candidate_gift_size", "committee_spending_category", "committee_top_payee",
            "payee", "payee_cycle", "payee_top_payer", "race_top_spender"}


def seconds(step, of=build):
    marker = markers.read(step, store, cycle=cycle, build_id=of)
    return None if marker is None else marker.duration_s


def fmt(value, sign=""):
    return "—" if value is None else f"{value:{sign}.0f}"


def newest_size(name):
    objects = store.list_objects(paths.bronze_dir(cycle, name))
    return max(objects, key=lambda obj: obj.key).size if objects else 0


def gb(size):
    return f"{size / 1e9:.2f}"


new_bronze = sum(newest_size(file.name) for file in files_for(cycle) if file.name not in V1_FILES)
silver = {table: sum(obj.size for obj in store.list_objects(paths.silver_partition(table, cycle, build) + "/"))
          for table in get_args(paths.SilverTable)}
with psycopg.connect(settings.database_url) as conn:
    sizes = conn.execute(
        "SELECT c.relname, pg_total_relation_size(c.oid) FROM pg_class AS c"
        " JOIN pg_namespace AS n ON n.oid = c.relnamespace"
        " WHERE n.nspname = 'gold' AND c.relkind IN ('r', 'm')"
    ).fetchall()
transform, before = seconds("transformed"), seconds("transformed", old)
added = None if transform is None or before is None else transform - before
published = markers.read("published", store, cycle=cycle, build_id=build)
release = re.search(r"service\.version=([0-9a-f]{7})", os.environ.get("OTEL_RESOURCE_ATTRIBUTES", ""))
print(
    f"| {cycle} | {published.finished_at.date() if published else '—'} | `{build}` | `{release[1] if release else 'unknown'}`"
    f" | {fmt(seconds('extracted'))} | {fmt(transform)} | {fmt(before)} | {fmt(added, '+')}"
    f" | {fmt(seconds('resolved'))} | {fmt(seconds('loaded'))}{'' if halves == '—' else f' ({halves})'}"
    f" | {fmt(seconds('published'))} | {gb(new_bronze)} | {gb(sum(silver[t] for t in NEW_SILVER))}"
    f" | {gb(sum(silver.values()))} | {gb(sum(size for _, size in sizes))}"
    f" | {gb(sum(size for name, size in sizes if name in NEW_GOLD))} | {peak} | {free} | |"
)
EOF
tail -3 record.py
# A cycle's capacity row, in <cycle>/row.md: `cycle_record <cycle> "<peak>"`.
cycle_record() {
  local c=$1 halves
  halves=$(grep -o 'aggregates [0-9.]* s, copy [0-9.]* s' "$c/run.log" | tail -1 | awk '{ print $2 " + " $5 }')
  py record.py "$c" "$(cat "$c/build-id.txt")" "$(cat "$c/old-build.txt")" "$2" "$(free_gb)" "${halves:-—}" | tee "$c/row.md"
}
```

**Expected:** each `tail -3` prints the script's last three lines, and no other output.

Open a second tmux window (`Ctrl-b c`) and leave a sampler running there until step 9. Every 10 s it writes
`pipeline`'s and Postgres's memory, and the free disk, to `mem.txt`. `cycle_peak` reads it.

```bash
# VM, tmux window 1 (a new shell: the helpers are not defined here)
cd ~/fundlens-efd-backfill
while true; do
  t=$(date -u +%FT%TZ); f=$(df -BGB --output=avail / | tail -1 | tr -dc '0-9')
  docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | grep -E '^(pipeline|fundlens-postgres)-lvch8zyndujjzkz16ksys8im' | sed "s/^/$t /; s/\$/ free=${f}G/"
  sleep 10
done | tee -a mem.txt
```

**Expected:** two lines every 10 s, e.g. `2026-11-27T14:00:00Z pipeline-lvch8zyndujjzkz16ksys8im-… 1.2GiB / 40GiB
free=202G`. Switch back with `Ctrl-b 0`. Glance at this window during long steps:

- **`free=` under 60G: stop the cycle now.** `docker restart "$(fl pipeline)"` ends whatever runs in it. A
  transform or load killed this way uploads and swaps nothing. Then step 4.
- **`pipeline` above 38 GiB:** the step is about to be killed for memory. Let it run; step 2.5 says what to do if it
  is.

## 1. Preflight

### 1.1 The deployed code, and the merge freeze

```bash
# VM
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES DUCKDB_MEMORY_LIMIT
docker exec "$(fl pipeline)" sh -c 'ulimit -Sn'
docker exec "$(fl pipeline)" fundlens health; echo "exit=$?"
docker top "$(fl pipeline)" | grep -E 'fundlens (run|weekly|transform|resolve|load|publish)' || echo "nothing running"
sha | tee sha.txt
```

```bash
# laptop
cd ~/projects/fundlens
git fetch origin
SHA=$(ssh hetzner-01 'cat fundlens-efd-backfill/sha.txt')
git merge-base --is-ancestor ac0d459 "$SHA" && echo "NEU-2179 deployed"
git merge-base --is-ancestor "$(git log -1 --format=%H origin/main -- docs/runbooks/every-fec-dollar-backfill.md)" "$SHA" && echo "runbook deployed"
gh workflow disable dependencies --repo neuroticsasquat-ch/fundlens
gh workflow list --repo neuroticsasquat-ch/fundlens --all | grep dependencies
gh pr list --repo neuroticsasquat-ch/fundlens --state open
```

**Expected:** `service.version=<sha>` and `32GB`; `65536` (NEU-2399); `postgres: ok`, `r2: ok`, `exit=0`; `nothing
running`; the SHA. Then `NEU-2179 deployed` (`ac0d459` is NEU-2179's log merge), `runbook deployed`, and
`dependencies` listed as `disabled_manually`. If a `deployed` line is missing: Coolify → the `fundlens` resource
→ *Deploy*, wait for it to finish, and run this step again. Then the open PRs: none merges while a cycle runs.
Write the SHA in the Log: every cycle is built from it unless the Log says otherwise.

### 1.2 What is live, and what each live build lacks

```bash
# VM
gmeta | tee gmeta-before.txt
live | tee live-before.txt
py tables.py | tee tables-before.txt
```

**Expected:**

- `gold` and `gold_prev`, each with its `published_at`.
- Every cycle 1980 to 2026 with its build: 2024 at `20261126T191724Z`, 2026 at `20261123T224142Z` or a newer
  Sunday's, and 1980–2022 at the builds of [backfill.md](backfill.md)'s Log (2026-11-13 to 2026-11-16).
- A line per cycle. 2024 `complete`, its counts NEU-2179's: `reported_total` above 0,
  `candidate_reported_total=0`, `leadership_pac=833`, `lobbyist_pac=1461`, `bundling_report=317`. 1980–2022 `LACKS`
  all seven, each count `-`. 2026 `complete` if a Sunday since NEU-2175 built it, else `LACKS
  leadership_pac,lobbyist_pac,bundling_report`. Any other cycle `complete`, or a cycle missing, means someone
  rebuilt it since the Facts were written: stop and find out who, from [weekly.md](weekly.md)'s and the milestone
  runbooks' Logs.

### 1.3 Disk

```bash
# VM
df -h / | tee disk-before.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null' | tee -a disk-before.txt
pg -Atc "select pg_size_pretty(pg_database_size('fundlens'))" | tee -a disk-before.txt
free_gb
cat > r2size.py <<'EOF'
from fundlens.r2 import R2
from fundlens.settings import get_settings

store = R2.from_settings(get_settings())
for prefix in ("bronze/", "silver/", "resolution/"):
    objects = store.list_objects(prefix)
    print(f"{prefix} {len(objects)} objects, {sum(obj.size for obj in objects) / 1e9:.2f} GB")
EOF
tail -3 r2size.py
py r2size.py | tee r2-before.txt
```

**Expected:** at least 160 GB available on `/`: 130 GB is the gate for a cycle, and the rebuilt cycles' silver
grows on top of it. NEU-2060's backfill left silver at 17 GiB for every cycle; the new tables add a fraction of
that. Then the `/data/fundlens` directories and the database's size. Then R2's three prefixes. R2 sets no capacity
limit, so this is a record, not a gate: the run adds each cycle's new bronze and silver, and `publish` prunes the
silver builds older than the one before. Write the free disk and the R2 figures in the Log; step 9 measures R2 again.

## 2. One cycle

Repeat steps 2.1–2.4 for each cycle in order: 2022, 2020, then step 3 for 2018, then 2016, 2014, …, 1980. Set the
cycle first:

```bash
# VM, in tmux
C=2022
```

### 2.1 Before the cycle

```bash
# VM, in tmux
date -u +'%a %H:%M UTC'
free_gb
[ "$(sha)" = "$(cat sha.txt)" ] && echo "same code" || echo "DEPLOYED $(sha), was $(cat sha.txt)"
docker top "$(fl pipeline)" | grep -E 'fundlens (run|weekly|transform|resolve|load|publish)' || echo "nothing running"
```

**Expected:** not Sunday between 01:00 UTC and the end of the weekly run (Before you start); at least `130`;
`same code`; `nothing running`.

- Under 130: step 4, then come back.
- `DEPLOYED`: something merged since step 1.1. Find it with `git log --oneline <old>..<new>` on the laptop. Docs
  only, or a fix this run needed: write it in the Log, `sha > sha.txt`, and go on. Anything that changes
  `sql/silver`, `src/fundlens/transform` or `src/fundlens/fec`: stop, and decide in the Log whether the cycles built
  before it are rebuilt.

### 2.2 Run it

```bash
# VM, in tmux
cycle_run "$C"
```

**Expected,** in order, ending with `… end <C> <build>`:

- `build <B> of <C>`.
- **extract:** a `<file>: downloaded bronze/cycle=<C>/<file>/<today>.<zip|csv>` line for each of the cycle's new
  files (Facts, *Files per cycle*), and for each of v1's a `<file>: unchanged bronze/…` line, or a download where FEC
  has changed the zip since 2026-11-13. Write in the Log every v1 file downloaded: step 2.3 explains moved totals by them.
- **seats:** `house: <n> races`, `senate: <n> races`, a `president` line in years divisible by 4, `wrote
  silver/race/…`, and the unmatched filings recorded: the same counts as in [backfill.md](backfill.md)'s run.
- **transform:** a `<table>: <n> rows` line per silver table, then `wrote …` lines. Each of the seven is listed, at
  0 rows before its first cycle (the table at the top). From 2010, `run-raw.log` also holds the JSON lines
  `leadership_pac <C>: …`, `lobbyist_pac <C>: …` and `bundling_report <C>: …`, as NEU-2179's step 4 read them:
  `grep -oE '"message": "(leadership_pac|lobbyist_pac|bundling_report) [0-9]{4}:[^"]*"' "$C/run-raw.log"`. Write
  them in the cycle's Log line.
- **resolve:** `<C>: build <B>`, then `<n> new contributor keys of <k>`. `0 new` when `indiv` was `unchanged`;
  with a fresh `indiv`, a few, for the contributors FEC's amendments added. Then `crosswalk: <d> new donors, <r> keys
  re-pointed, …` and `model <M>: the live model, untrained`. A `warning: … keys that stood were re-pointed` line
  means an override or a verdict new since the last `--full`: the run goes on, but write it in the Log for the
  re-resolve afterwards (Not in this runbook).
- **load:** a `<table>: <n> rows` line per gold table, `quality: precision …`, a `resolution: release <sha>, …`
  line and `loaded build <B> into gold_build (aggregates <a> s, copy <c> s)`. That last line means every
  `sql/checks/gold_*.sql` passed.
- **publish:** `published build <B> of <C>`, `previous build: <C/old-build.txt>`, `cloudflare purge: done`, `wrote
  resolution/build=<B>/crosswalk.parquet`, `pruned <n> silver builds (<m> objects)`.
- `finished build <B> of <C>: ran extract, transform, resolve, load, publish`, then `time`'s lines.

**Estimated:** 2022 and 2020 about 70 minutes, the transform near 2024's 30; the 1980s under 40, mostly the load.

### 2.3 Check it

```bash
# VM, in tmux
B=$(cat "$C/build-id.txt")
for s in extracted transformed resolved loaded published; do printf '%s ' "$s"; mk "$s" "$C" "$B" | grep -c '"duration_s"'; done
gmeta
py tables.py "$C" | tee "$C/tables.txt"
pg -v c="$C" < verify.sql | tee "$C/verify.txt"
if [ "$C" -ge 2004 ] && [ "$C" -le 2016 ]; then py silver.py "$C" "$B" --payees; else py silver.py "$C" "$B"; fi | tee "$C/silver.txt"
```

**Expected:**

1. **Markers:** `1` after each of the five steps.
2. **`gmeta`:** `gold` naming `<B>`, `published_at` now; `gold_prev` the build before it.
3. **`tables.py`:** `<C> <B> complete`, and the counts the cycle's range has:

   | Range | `reported_total` | `candidate_reported_total` | `operating_expenditure` | the other four |
   | --- | --- | --- | --- | --- |
   | 2010–2022 | above 0 | 0 | above 0 | each above 0 |
   | 2008 | above 0 | 0 | above 0 | 0 |
   | 2004–2006 | above 0 | above 0 | above 0 | 0 |
   | 1996–2002 | above 0 | above 0 | 0 | 0 |
   | 1980–1994 | 0 | above 0 | 0 | 0 |

   `LACKS` after a publish, or a count of 0 where the range has rows, is a defect: file a Bug ticket with the line,
   link it from NEU-2180, and stop. The cycle stays live: it reads as before.
4. **`verify.sql`**, its first table: `other cycles` with no row, or every count 0. `load` rebuilt every other
   cycle from the same live builds, so another cycle's figure moving is a defect: roll back (step 2.5) and stop.
   `this cycle` with `missing` 0 in every table: the same committees, candidates and races as before. Any
   `missing` means the rebuild's committees, candidates or races differ from v1's. If step 2.2 downloaded `cm`,
   `cn` or `ccl` fresh, FEC's amendment can add or drop one: list the missing ids (`gold.committee_cycle` against
   `gold_prev`'s for the cycle) and check a few on FEC's site; write them in the Log and go on. With all three
   `unchanged`, a `missing` row is a defect: roll back and stop. `moved` may be above 0 (Receipt totals will move):
   read the next two tables.
5. **The cycle's contributions:** `pct_moved` within ±1%. The ten committees that moved most are NEU-2400–NEU-2402's
   cases (memo lines, FEC's repeated rows, refund memos) or a v1 file step 2.2 downloaded fresh. Over 1%, stop
   before the next cycle: find which rows moved for the largest committee (its silver `contribution` against the old
   build's), and file a Bug ticket unless it is one of those causes. The cycle may stay live meanwhile: it is the
   code's counting, which 2024 and 2026 already have.
6. **The cycle's new figures:** `reported` above 0 on committees from 1996 and on candidates in every cycle;
   `with_spending` and `spending` from 2004, NULL and 0 before; `ie`, `communication_costs` and `coordinated` above
   0 in every cycle (all three from `pas2`); `with_electioneering`, `sponsored`, `lobbyist_pacs` and `bundled` from
   2010, 0 or NULL before. `leadership_pacs` above 0 from 2010; before it, designation `D` alone, which may be 0 in
   the early cycles. `with_bundled` is every committee from 2010
   and 0 before: NULL, "no reports", never $0 (spec §7.7).
7. **Reconciliation:** two rows in every cycle, `listed` and `eligible` above 0 from 2008 and 0 before (no file
   before 2008 has the measures). A `pct`
   over 5 on either measure is investigated before the next cycle: list the cycle's ten largest rows
   (`select * from gold.reconciliation where cycle = <C> order by fundlens - reported desc limit 10`) and set them
   against 2024's causes in [reported-totals-run.md](reported-totals-run.md)'s and [spending-run.md](spending-run.md)'s
   Logs: a filer's line choice, an amendment FEC's summary has not caught up with. A cause of fundlens's own is a Bug
   ticket. Write each cycle's `listed`, `eligible` and `pct` in the Log either way.
8. **`silver.py`:** `ie`, `communication_cost` and `coordinated` rows from `pas2` in every cycle. From 2010 also
   `ie` rows from `ie_24_48`, and `communication_cost` rows with `with_type` above 0 (the `CommunicationCosts` CSV's
   types); before 2010 no `ie_24_48` row and `with_type` 0. A kind with no row where its range has one is a defect,
   as in item 3. For 2004–2016, the payee person rule's tables follow: step 3's gate applies to each cycle as it did
   to 2018. A cycle that fails it is rolled back (step 2.5) and the run goes on with 2002 and earlier, as step 3
   says: the blank share differs by cycle (9.6–29.5%, spec §5.7), so one cycle's pass does not stand for the rest.

### 2.4 Record it

```bash
# VM, in tmux
cycle_peak "$C"
```

It prints the peak and when it happened, e.g. `26.12 GiB at 2026-11-27T15:45:03Z; least free disk 171 GB`. Name the
step that held it, and the transform's own peak:

```bash
# VM, in tmux
where "$C" <the time cycle_peak printed>
grep -o 'memory after [^"]*' "$C/run-raw.log" | tail -1
cycle_record "$C" "<peak> GiB, <step>"
```

**Expected:** `where` prints the last log line before the peak, such as `write contribution 2020` or `gold donor`:
its step goes in the peak column. The `memory after` line is the transform's: its `peak resident` is the process's
own high-water mark up to the transform's end, which the sampler can miss between samples. Write it in the cycle's
Log line. Then `cycle_record` prints the cycle's row into `<C>/row.md`. Step 10 collects the rows. Next cycle:
step 2.1, or step 3 when the next cycle is 2018.

### 2.5 When a step fails

`cycle_run` stops and prints `STOPPED <C> <B>, exit <n>`; `run`'s output names the step and its error. Bugsink gets
an issue tagged `pipeline_mode=<step>`. Nothing after the failed step ran, and the live gold is the last cycle's.

| What failed | What to do |
| --- | --- |
| `extract` on FEC (a timeout, a `DownloadError`) | It retried five times already. Wait ten minutes, then resume the build: `cycle_run "$C" "$(cat $C/build-id.txt)"`. `run` skips every step with a marker |
| `extract` refuses a CSV (`<url>: the header row is not the catalogued <file> columns`) | FEC changed a file's columns for this cycle: spec §3 says every cycle's header equals 2024's. File a Bug ticket with the file and both headers, link it from NEU-2180, and stop |
| `transform` names a `sql/checks/silver_*.sql` | A check returned rows, so nothing was uploaded. A check of this project's tables (`silver_reported_total_*`, `silver_operating_expenditure_*`, `silver_electioneering_*`, `silver_leadership_pac_*`, `silver_lobbyist_pac_*`, `silver_bundling_report_*`, `silver_independent_expenditure_*`) on an old cycle is a rule 2024 did not meet. File a Bug ticket with the check's name and a few rows, link it from NEU-2180, and stop. After its fix merges, rebuild under a new build: `mv "$C" "$C-failed-$(cat $C/build-id.txt)"; cycle_run "$C"`. The cycles after it wait for the fix |
| `transform` stops with an `Out of Memory Error`, or a step with `exit 137` and the sampler near 40 GiB | DuckDB or the container ran out of memory; nothing was uploaded. File a ticket with the peak, the step `where` names and the DuckDB limit, link it from NEU-2180, and stop |
| `resolve` stops with exit 1 and a message | [weekly.md](weekly.md) → *A run missed* says what each one means. The cycle's transform stands: resume with `cycle_run "$C" "$(cat $C/build-id.txt)"` once it is dealt with |
| `load` names a `sql/checks/gold_*.sql`, or `publish` fails | No `gold_build` was kept, or the swap rolled back, and the live gold is unchanged. A gold check that fails on an old cycle is a Bug ticket, as above. After its fix merges, resume the build: `cycle_run "$C" "$(cat $C/build-id.txt)"` (the transform is not repeated) |
| The SSH session or tmux died | `docker exec` stopped with it, but the step may not have. Check `docker top "$(fl pipeline)"` for a `fundlens` process and wait until it is gone. Then resume: `cycle_run "$C" "$(cat $C/build-id.txt)"` |
| Step 2.3 says roll back | `docker exec "$(fl pipeline)" fundlens publish --rollback`. **Expected:** `rolled back: build <gold_prev's> is live`, then `build <B> is now gold_prev`, and `live_of "$C"` printing `$C/old-build.txt`'s build again. File a Bug ticket with step 2.3's output, link it from NEU-2180, and stop: the next cycle's load would read whatever is live |

A rebuild under a new build leaves the failed build's files behind, without a `transformed` marker. `load` reads
only live builds, and `publish` prunes the old silver builds.

## 3. 2018: the payee person rule before it publishes

2018 is the first cycle of 2006–2018, where `ENTITY_TP` is blank on 9.6–29.5% of spending dollars (spec §5.4, §5.7).
Run it to its transform by hand, measure the rule on its silver, then let `run` resume it:

```bash
# VM, in tmux
C=2018
```

Step 2.1 first. Then:

```bash
# VM, in tmux
mkdir -p "$C" && date -u +%Y%m%dT%H%M%SZ > "$C/build-id.txt" && live_of "$C" > "$C/old-build.txt"
echo "$(date -u +%FT%TZ) start $C $(cat $C/build-id.txt) $(sha)" | tee -a "$C/window.txt"
cycle_step "$C" extract && cycle_step "$C" seats && cycle_step "$C" transform
py silver.py "$C" "$(cat $C/build-id.txt)" --payees | tee "$C/payees.txt"
```

**Expected:** extract, seats and transform as in step 2.2, each ending with `time`'s lines. Then, from `silver.py`,
the outside-spending table of step 2.3 item 8, then:

1. **Payee dollars by `ENTITY_TP`:** `filed` false with a `pct` near the spec's range, 9.6–29.5%: the dollars the
   classifier decides.
2. **The classifier against `ENTITY_TP`**, on the rows where FEC's filer named the type:
   `persons_read_as_organizations`, the share of person dollars the classifier would give a page, and
   `organizations_read_as_persons`, the share of organization dollars it would take one from.
3. **The 25 largest blank-type keys read as an organization's**, and the 25 read as a person's.

**The gate.** Publish 2018 only if all three hold:

- `persons_read_as_organizations` is at most 5.00: a payee page under a private person's name is the costly error.
- `organizations_read_as_persons` is at most 5.00.
- Read by eye, none of the first 25 keys is a person's name, and no firm in the second list holds most of its
  key's dollars (a firm whose blank rows are read as a person's loses its page only if they are most of its dollars,
  spec §5.4).

All three hold: write the two figures and anything notable in the lists in the Log, then resume:

```bash
# VM, in tmux
cycle_run "$C" "$(cat $C/build-id.txt)"
```

**Expected:** `extract: skipped, done already`, `transform: skipped, done already`, then resolve, load and publish
as in step 2.2, and `finished build <B> of 2018: ran resolve, load, publish`. Then steps 2.3 and 2.4 for 2018, and
2016 next.

A figure over 5, or a person among the first 25: the rule is not good enough for these cycles. Do not resume 2018.
File a Bug ticket ("Payee person rule misreads 2006–2018 payees") with `payees.txt`, linked from NEU-2180, and write
the figures in the Log. Go on with 2002 and earlier, which have no `oppexp` (spec §5.7), and leave 2004–2018 live as
they are until the fix merges. Then rebuild 2018 from the start, `mv 2018 2018-failed-$(cat 2018/build-id.txt)`,
and run this step again.

Then the spec's assertion becomes a measurement: step 10 writes the figures into spec §5.4.

## 4. Pausing for disk

If free disk is under 130 GB before a cycle, find out what grew before going on:

```bash
# VM
df -h /
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null'
pg -Atc "select pg_size_pretty(pg_database_size('fundlens'))"
docker ps --format '{{.Names}}' | grep -i clickhouse | head -1 | xargs -I{} docker exec {} du -sh /var/lib/clickhouse
```

**Expected:** the free disk, the `/data/fundlens` directories, the database and SigNoz's ClickHouse. Compare each
with `disk-before.txt`:

- **`/data/fundlens/scratch` is above 1 GB:** a killed step left DuckDB spill behind. Remove it, with no step
  running: `docker exec "$(fl pipeline)" sh -c 'rm -rf /data/fundlens/scratch/*'`.
- **ClickHouse grew by more than 10 GB:** SigNoz → *Settings* → *General* → lower the logs and traces retention,
  e.g. to 7 days, *Save*. Write the old and new retention in the Log, and set it back in step 9.
- **Otherwise the growth is fundlens's own:** silver or gold beyond what the rows of `capacity.md` predict. Stop and
  file a ticket with the sizes, linked from NEU-2180: it is the steady-state disk trigger (`capacity.md` →
  *Triggers*).

## 5. 2024 and 2026

```bash
# VM, in tmux
py tables.py 2024 2026
```

**Expected:** 2024 `complete`, as in step 1.2. 2026 `complete` if a Sunday's run has built it since NEU-2175: write
its build in the Log, and go to step 6. If 2026 `LACKS` the three tables, rebuild it by hand, as a Sunday would, at a
time that is not Sunday's (step 2.1):

```bash
# VM, in tmux
C=2026
cycle_run "$C"
```

**Expected:** as in step 2.2: extract downloads whatever FEC changed this week, every one of 2026's 16 files in
bronze. Then step 2.3, items 1 to 3, 6 and 8, each as for 2010–2022: the receipt figures move with FEC's week, as on any Sunday, so items 4
and 5 do not apply. Then step 2.4.

## 6. Every live build holds every table

```bash
# VM, in tmux
live | tee live-after.txt
py tables.py | tee tables-after.txt
grep -vc ' complete ' tables-after.txt
```

**Expected:** every cycle 1980–2026, each with this run's build (2024's and 2026's as step 5 found them), each line
`complete`, and `0`: no line that is not. Any `LACKS` line: that cycle is rebuilt (step 2) before step 8, or step 8's
load fails on it.

## 7. Verify

### 7.1 The API, every cycle

```bash
# laptop
mkdir -p ~/fundlens-efd-backfill && cd ~/fundlens-efd-backfill
for c in $(seq 1980 2 2026); do
  curl -sS "https://api.fundlens.org/v1/cycles/$c/races?nocache=$(date +%s)" | jq -r --arg c "$c" '[length, ([.[] | .total_individual + .total_committee] | add), ([.[] | .total_operating_expenditures // empty] | length), ([.[] | select(.reported_cash_on_hand != null)] | length)] | "\($c) races=\(.[0]) money=\(.[1]) with_spending=\(.[2]) with_reported=\(.[3])"'
done | tee races.txt
```

**Expected:** a line per cycle. `races` and `money` above 0 in every cycle, as after v1's backfill. `with_spending`
0 before 2004 and above 0 from 2004 (`total_operating_expenditures`, NULL where no candidate has a counted row).
`with_reported` above 0 in every cycle: races whose candidates have a reported cash on hand, from `weball` to 2006
and `committee_summary` from 2008. Copy `races.txt` into the Log.

### 7.2 Three race pages

The ticket's three cycles. First pick a race in each, the House race with the most money:

```bash
# laptop
for c in 1996 2008 2016; do
  curl -sS "https://api.fundlens.org/v1/cycles/$c/races?nocache=$(date +%s)" | jq -r --arg c "$c" 'map(select(.office == "H" and (.is_special | not))) | max_by(.total_individual + .total_committee) | "\($c) \(.race_id) https://fundlens.org/race/\(.slug)"'
done | tee race-picks.txt
```

**Expected:** three lines, each a cycle, a race id and its page, e.g. `https://fundlens.org/race/2016/house/CA-12`.
Open each page, and one of its candidates.

**Expected:**

- **1996:** each candidate shows reported totals (receipts, disbursements, cash on hand from `weball`), with the
  figures 1996 lacks (itemized and unitemized, operating expenditures) as "not reported", never 0. No spending
  section's figure, or "not available": spending starts in 2004.
- **2008:** reported totals from `committee_summary`, spending (operating expenditures, and categories on the
  candidate's committee), and outside spending by kind: independent expenditures, communication costs and party
  coordinated expenditures. No electioneering communications: they start in 2010, so the figure is absent, not $0.
- **2016:** as 2008, and electioneering communications where the race has any.

Write what each page showed in the Log. A figure shown as $0 where the cycle has no source is a defect of the page
(NEU-2146's rule): a Bug ticket, linked from NEU-2180.

### 7.3 Signals

- **Bugsink** → `fundlens`: every `pipeline` issue since step 2 comes from a step that failed and was resumed
  (step 2.5). Write each in the Log, then resolve it. An `api` issue since the first publish means a route fails on
  an old cycle: file a ticket with it.

## 8. Empty the backfill-pending list

Only once step 6 printed `0`. With the list empty, a live build lacking any table fails the load and the snapshot,
as v1 has it for its own tables. Merging redeploys `pipeline`, so nothing may be running: `docker top` as in
step 2.1, and not between 02:00 and 02:30 UTC, nor Sunday from 03:00 UTC to the weekly's end.

```bash
# laptop
cd ~/projects/fundlens
git fetch origin && git switch -c chore/NEU-2180-empty-backfill-pending origin/main
```

In `src/fundlens/paths.py`, set the list empty, keeping its comment, which tells the next table's ticket what to do:

```python
BACKFILL_PENDING: frozenset[SilverTable] = frozenset()
```

and change the comment's `NEU-2180's backfill rebuilds every cycle and empties this again` to `a backfill that
rebuilds every cycle empties it again (NEU-2180 emptied it, 2026-<mm>-<dd>)`. Then commit and open the PR:

```bash
# laptop
task format
git add src/fundlens/paths.py
git commit -m "chore(paths): empty the backfill-pending list after the backfill (NEU-2180)"
git push -u origin chore/NEU-2180-empty-backfill-pending
gh pr create --repo neuroticsasquat-ch/fundlens --base main --title "chore(paths): empty the backfill-pending list after the backfill (NEU-2180)" --body "Every cycle's live build holds every table this project adds (docs/runbooks/every-fec-dollar-backfill.md step 6), so the list NEU-2352 introduced is emptied: a build lacking a table fails the load and the snapshot again.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

**Expected:** the pre-commit hook passes (its tests replace the list where they need one), the push, and the PR's
URL. Wait for CI, then merge with a merge commit, `gh pr merge <n> --merge --repo neuroticsasquat-ch/fundlens`,
and wait for Coolify's deploy to finish. Then, on the VM:

```bash
# VM, in tmux
sha
docker exec "$(fl pipeline)" python -c 'from fundlens import paths; print(sorted(paths.BACKFILL_PENDING))'
B26=$(live_of 2026)
{ time docker exec "$(fl pipeline)" fundlens load --cycle 2026 --build-id "$B26"; } 2>&1 | tee final-load-raw.log | grep -v '^{' | tee final-load.log
grep -c 'backfill-pending' final-load-raw.log
{ time docker exec "$(fl pipeline)" fundlens publish --cycle 2026 --build-id "$B26"; } 2>&1 | grep -v '^{' | tee final-publish.log
{ time docker exec "$(fl pipeline)" fundlens dataset --snapshot; } 2>&1 | grep -v '^{' | tee final-snapshot.log
```

**Expected:** the PR's merge SHA, then `[]`. Then the load: a `<table>: <n> rows` line per gold table and `loaded
build <B26> into gold_build (aggregates <a> s, copy <c> s)`. Then `0`: no `backfill-pending, read as no rows` log
line, since the list is empty (a build lacking a table would have failed the load instead). Then `published build <B26> of 2026` and `previous
build: <B26>`: the same build, only its gold rebuilt. Then the snapshot: `docs: …`, `took snapshot <today> of build
<B26>`, `latest/: copied` and the snapshots removed. If a Sunday already took today's, it prints `already took`:
then run the snapshot the next day instead. This is the ticket's "a load and a dataset snapshot then succeed with
every table required". About 25 + 3 + 16 minutes.

Then the manifest lists every cycle for each of the seven tables:

```bash
# laptop
curl -sS https://data.fundlens.org/v1/latest/manifest.json | jq -r '.snapshot_date, (.tables | to_entries[] | select(.key | IN("reported_total", "candidate_reported_total", "operating_expenditure", "electioneering_communication", "leadership_pac", "lobbyist_pac", "bundling_report")) | "\(.key) \([.value.files[].path | capture("cycle=(?<c>[0-9]+)/").c] | unique | length) cycles")'
```

**Expected:** today's date, then seven lines, each `24 cycles`: every cycle's file, a table with 0 rows in a cycle
included ([docs/dataset/README.md](../dataset/README.md) → *Snapshots*: the manifest lists exactly the files that
exist).

## 9. Restore

```bash
# laptop
gh workflow enable dependencies --repo neuroticsasquat-ch/fundlens
gh workflow list --repo neuroticsasquat-ch/fundlens --all | grep dependencies
```

**Expected:** `dependencies` listed as `active`. Then:

1. If step 4 lowered SigNoz's retention, set it back.
2. Stop the sampler (`Ctrl-b 1`, `Ctrl-c`), then `Ctrl-b 0`.

```bash
# VM
df -h / | tee disk-after.txt
docker exec "$(fl pipeline)" sh -c 'du -sh /data/fundlens/* 2>/dev/null; du -sc /data/fundlens | tail -1' | tee -a disk-after.txt
pg -Atc "select pg_size_pretty(pg_database_size('fundlens')), round(pg_database_size('fundlens') / 1e9, 2)" | tee -a disk-after.txt
py r2size.py | tee r2-after.txt
```

**Expected:** the disk after the backfill: each `/data/fundlens` directory and their total in KB, the database in
GB, and R2's three prefixes, beside `r2-before.txt`. From here, merging to `main` is safe again.

## 10. Record the run

Gather the rows and the run's figures:

```bash
# VM
cat $(ls -d [12][0-9][0-9][0-9] | sort -rn | sed 's|$|/row.md|') > backfill-rows.md 2>/dev/null
for c in $(ls -d [12][0-9][0-9][0-9] | sort -rn); do echo "== $c"; grep -E 'downloaded|new contributor keys|re-pointed|^real' "$c/run.log"; sed -n '/Reconciliation/,$p' "$c/verify.txt"; done > run-record.txt
grep -E '^(loaded build|published build|took snapshot|real)' final-*.log >> run-record.txt
```

```bash
# laptop
cd ~/fundlens-efd-backfill
for f in backfill-rows.md run-record.txt tables-before.txt tables-after.txt live-before.txt live-after.txt disk-before.txt disk-after.txt r2-before.txt r2-after.txt 2018/payees.txt; do scp "hetzner-01:fundlens-efd-backfill/$f" .; done
```

**Expected:** `backfill-rows.md` holds a row per cycle, newest first; `run-record.txt` each cycle's fresh downloads,
resolve's line, any re-pointing, its `real` and its reconciliation, then step 8's lines. One file per `scp`: since
OpenSSH 9, `scp` copies over SFTP, which does not expand braces in a remote path.

Then, in one PR, `docs(runbooks): log the every-FEC-dollar backfill (NEU-2180)`:

1. **`capacity.md` → Every-FEC-dollar backfill:** `backfill-rows.md`, one row per cycle, newest first, with each
   cycle's transform peak, any rerun and its reason in the Notes.
2. **`capacity.md` → Per cycle:** a row for step 8's load and publish of every cycle with every table, load as
   `<total> (<aggregates> + <copy>)`, against NEU-2179's 1,520 s. It is the weekly run's load from now on.
3. **`capacity.md` → Dataset snapshot:** a row for step 8's snapshot, its objects and its wall time.
4. **`capacity.md` → Triggers:** check the weekly run's estimate against the row above: 2026's extract to transform,
   its incremental resolve, and step 8's load and publish, against 6–8 h. And steady-state disk from
   `disk-after.txt` against ~300 GB. Update a figure only where it moved; file a ticket for a trigger that fired.
5. **`capacity.md` → Findings:** what the backfill showed that the rows do not say: which cycle was largest, what
   the new tables cost a transform per range, how much the load grew.
6. **The every-FEC-dollar spec:** §5.4's "**Asserted, not measured:** that the classifier … reads payee names as
   well" becomes "**Measured** by NEU-2180 on 2018 (`<B>`): <persons read as organizations>% of filed person
   dollars, <organizations read as persons>% of filed organization dollars", with the same two figures for each of
   2004–2016 from their `silver.txt`; and §2's *Older builds* row notes that
   NEU-2180 emptied the list on <date>.
7. **This runbook → Log:** an entry headed `### <date> — every cycle, 2022 to 1980 (NEU-2180)`: the SHA and any
   merge between cycles, step 1.2's and step 6's `tables.py`, per cycle the build, the v1 files downloaded fresh, the
   receipt move (`pct_moved`) and its cause, the reconciliation figures, every rerun and its reason, step 3's
   figures and each 2004–2016 cycle's, step 5, step 7's `races.txt` and the three pages, step 8's lines, step 9's disk, every deviation, and
   each ticket filed.

Merging it redeploys `pipeline`, which is safe now that nothing is running.

## Log

<!-- Append entries below; never rewrite one. -->
