# NEU-2408 — The transform logs its memory after every step, and one 2024 run says whether the classifier holds any

**Ticket:** [NEU-2408](https://linear.app/neuroticsasquatch/issue/NEU-2408) · **Milestone:** M2 Spending (P-NEU-107) · **Parent:** NEU-2148
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §5.1, Memory (rewritten by this ticket's docs PR, §7.3)
**Related:** NEU-2153 (the classifier; its run peaked at 28.64 GiB), NEU-2152 (`operating_expenditure`; its run peaked at 26.91 GiB), NEU-2077 (the per-step log lines this builds on).

Planned 2026-11-21. `/implementit NEU-2408` implements §3 to §5 straight from this file as PR 1. §6 is a manual run on the VM after PR 1 is deployed. §7 is a docs PR written from that run's figures.

## 1. What and why

The first 2024 transform with NEU-2153's classifier (build `20261121T193655Z`, `2e86f5f`) peaked at 28.64 GiB of the `pipeline` container. NEU-2152's run the same day without it (build `20261121T183242Z`, `adbca96`) peaked at 26.91 GiB. The classifier was expected to add almost nothing, and nothing in the log says which step holds the extra 1.73 GiB. The only reading is `docker stats` every 10 s, which is the container's total.

Every silver table P-NEU-107 adds runs in this same transform, so each needs figures it can be measured against.

This ticket delivers three things:

1. **PR 1:** the transform logs four memory figures after every step (§3 to §5).
2. **One 2024 transform on the VM**, read by the rule in §6.3.
3. **A docs PR** recording the run, the verdict, and what spec §5.1 should say about memory (§7).

### 1.1 Decisions this spec pins (grilled 2026-11-21)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| What a memory line carries | Four figures: peak resident memory, resident memory now, DuckDB's bytes in memory, DuckDB's bytes spilled. | The ticket asked for peak resident memory alone. That figure only rises, so it reads the same whether the classifier holds memory or not (§2). |
| Where the figures are taken | At every step boundary: after the views, each model, each check, each write and each upload. | The ticket named models and writes only. A peak raised by a check would then be blamed on the first write after it; the backfill has seen `silver check silver_contribution_key.sql` named as a peak's step. An in-step sampler thread was rejected: what makes up `contribution`'s write is out of scope, and a second thread on the connection is new machinery to test. |
| What this ticket delivers | Logging, the run, and the record. A fix, if the run shows a step holding memory, is a **new ticket** with this run's figures as evidence. | The ticket said "fix it in this ticket". The fix's shape is unknown until the run is read, so a spec written now could only sketch it. |
| How the verdict is reached | By step deltas within one run, threshold 0.10 GiB (§6.3). The ticket's bar of "26.91 GiB plus that run's spread" is dropped. | 2024's total peak moves 2.49 GiB between rebuilds of the same code (`docs/capacity.md`), and follows DuckDB's limit. A bar on the total can pass or fail by chance. A second run for spread was rejected as unnecessary for a rule that reads deltas. |
| What the docs PR records | `capacity.md` rows for this run **and** both 2026-11-21 builds, a Findings bullet, and spec §5.1's Memory paragraph rewritten to what the run shows. | The ticket says to add the run "beside" those two builds, but neither is in `capacity.md`: their peaks are in Linear comments only. §5.1 budgets additively, which is wrong if the transform spills. |
| Whose log changes | The transform's only. `fundlens load`'s log is unchanged, though it shares `check()`. | Load would get figures after its checks and nowhere else, a partial picture nobody asked for. |
| Where the readers live | A new `src/fundlens/memory.py`; `resolve/cluster.py`'s existing peak line uses it. | Keeping a second inline `ru_maxrss` conversion in the runner duplicates the unit comment. |
| Glossary and ADRs | None. | This is logging, easy to reverse, and adds no domain term. |

## 2. What was found while planning

These are facts the design rests on. Each was read from the code or measured in the dev container on 2026-11-21.

- **A high-water mark cannot attribute.** `ru_maxrss` never falls. Whether the classifier holds 1.73 GiB or the rise is variance, the mark is set at the run's peak step and reads the same.
- **Resident memory does not fall after a drop.** Probe on DuckDB 2.0.0, `memory_limit = 400MB`: after two tables were dropped, DuckDB reported 0 bytes held and the process's resident memory stayed at 383 MB (peak 490 MB). The allocator keeps freed memory. So resident memory cannot show what a step holds either.
- **DuckDB reports what it holds.** `duckdb_memory()` returns `tag`, `memory_usage_bytes` and `temporary_storage_bytes`. In the probe a 4M-row table read 0.17 GiB under tag `IN_MEMORY_TABLE`, and both figures returned to 0 after the drops. `docs/measurements/oppexp-2024.md` Q1 used the same function for the 0.87 GiB figure.
- **In-memory tables spill.** In the probe, once a second table took the two past the limit, DuckDB held 0.37 GiB in memory and 0.67 GiB in temporary storage. So past its limit, a new table adds spill, not peak.
- **`capacity.md` already says the peak follows the limit**: "DuckDB holds more before it spills, so the peak follows the limit, not only the data" (Findings, backfill). 2024 peaked at 24.34 GiB under `28GB` and 28.97 GiB under `32GB`.
- **The classifier is an unlikely holder.** `operating_expenditure` is built by the last model, written first and dropped (`WRITTEN_FIRST`), all before `contribution`'s write. The `category` CTE is about 70,000 rows. This is reasoning, not measurement: the run decides.
- **`ru_maxrss` lags.** In the probe it read 476,128 KiB while `/proc/self/status` read `VmRSS` 476,928 kB at the same moment. `VmHWM` and `VmRSS` from one read of that file are consistent with each other, so both readers use it (§3).
- **Today's step lines are written before each step starts** (`silver <table> <cycle>: <file>`, `silver check <file>`, `write <table> <cycle>`, `upload <key>`). The backfill runbook's `where` helper names a peak's step as the last line at or before the peak's time. A line written after a step does not disturb that: during step N the last line is still N's start line.

## 3. `src/fundlens/memory.py` (new)

A module that depends on nothing else in the package. Two functions, both read from one parse of `/proc/self/status`:

- `resident_gib() -> float`: `VmRSS`, the process's resident memory now, in GiB.
- `peak_resident_gib() -> float`: `VmHWM`, the highest resident memory the process has had, in GiB.

The file's values are in kB (KiB); divide by 2²⁰. The pipeline runs only in its Linux container, so no other platform is handled: a missing file or field raises.

`resolve/cluster.py:484` drops its inline `resource.getrusage` lines and the `resource` import, and logs `peak_resident_gib()` in the same message. `tests/unit/test_cluster.py`'s assertion on that message is unchanged and must still pass.

## 4. `transform/runner.py`

### 4.1 The line

One helper writes it, on the module's own logger (`fundlens.transform.runner`):

```
memory after <step>: peak resident <p> GiB, resident <r> GiB, DuckDB <m> GiB in memory, <s> GiB spilled
```

- `<p>` and `<r>` are `peak_resident_gib()` and `resident_gib()`.
- `<m>` and `<s>` are `sum(memory_usage_bytes)` and `sum(temporary_storage_bytes)` over `duckdb_memory()`, each `coalesce`d to 0, in GiB (÷ 2³⁰).
- Every figure is formatted `%.2f`.

After the connection has closed there are no DuckDB figures, so an upload's line stops after the resident figure:

```
memory after <step>: peak resident <p> GiB, resident <r> GiB
```

### 4.2 Where it is written

`<step>` repeats the leading words of the step's own start line, so the two read as a pair.

| After | `<step>` |
|---|---|
| The last registration (`spending.register(con)`), before the first model | `views <cycle>` |
| Each silver model's `con.execute` | `silver <table> <cycle>` |
| Each silver check | `silver check <file name>` |
| Each write, after its `DROP TABLE` | `write <table> <cycle>` |
| Each upload, after its stale keys are deleted | `upload <key>` |

`views <cycle>` is the baseline. It comes after `_drop_fec_repeats` has scanned `indiv`, `oth`, `pas2` and `oppexp` for their `<file>_repeat` tables, which nothing logs today.

No existing line changes, moves or is removed. `_log_spending`'s line stays where it is, between the last check and the first write.

### 4.3 `check()`

`check()` is shared with `load/gold.py:501`. It gains one optional keyword argument, a callable taking the step's name (`f"{tier} check {path.name}"`), called after each check's rows have been fetched. `transform` passes one that writes the memory line; the gold loader passes nothing, and its log is unchanged.

### 4.4 Docstring

The module docstring's last paragraph gains one sentence saying that a `memory after <step>` line follows the views and each model, check, write and upload, and what its four figures are.

## 5. Tests

No new transform run: a run is the expensive part, and one test already makes one with `caplog`.

- **`tests/integration/test_transform.py::test_transform_logs_each_check_write_and_upload_after_the_last_model`** keeps its name (the ticket's definition of done cites it) and its existing assertion, which is unaffected: none of its prefixes matches `memory after `. It gains, over the whole log:
  - The `memory after ` lines name these steps, in this order: `views 2024`; `silver <table> 2024` for each model in run order; `silver check <file>` for each check in name order; `write <table> 2024` in `write_order`; `upload <key>` in `write_order`.
  - Each model's, check's, write's and upload's memory line comes after that step's start line and before the next step's start line.
  - Every line up to the last write matches the four-figure format, and every upload's line the two-figure format, by regular expression.
  - Peak resident never decreases from one line to the next, and on every line resident ≤ peak resident.
- **`tests/unit/test_memory.py`** (new): `0 < resident_gib() <= peak_resident_gib()`.
- **`tests/unit/test_cluster.py`**: unchanged, still passing.

Typecheck and the two touched test files while iterating; the pre-commit hook runs the full suite once at commit.

## 6. The 2024 run on the VM (manual, after PR 1 is deployed)

A transform-only build, never loaded or published, as NEU-2153's was. About 35 minutes.

**Do not start it while the weekly run is on.** The scheduled task starts Sunday 03:00 UTC (`docs/runbooks/weekly.md`), and both would share the container's 40 GiB.

### 6.1 Session

```bash
# VM
tmux new -s neu2408
```

```bash
# VM, in tmux
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
mk() { docker exec "$(fl pipeline)" python -c 'import sys; from fundlens import markers; from fundlens.r2 import R2; from fundlens.settings import get_settings; m = markers.read(sys.argv[1], R2.from_settings(get_settings()), cycle=int(sys.argv[2]), build_id=sys.argv[3]); print(m.model_dump_json(indent=2) if m else "MISSING")' "$1" "$2" "$3"; }
mkdir -p ~/fundlens-neu2408 && cd ~/fundlens-neu2408
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES DUCKDB_MEMORY_LIMIT
docker top "$(fl pipeline)"
```

**Expected:** `service.version=<PR 1's merge SHA>`, then `32GB`. `docker top` lists no `fundlens run`, `transform`, `resolve` or `load` process.

### 6.2 Sampler, seats, transform

Open a second window (`Ctrl-b c`) and start the sampler:

```bash
# VM, tmux window 1
cd ~/fundlens-neu2408
while true; do
  t=$(date -u +%FT%TZ); f=$(df -BGB --output=avail / | tail -1 | tr -dc '0-9')
  docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | grep -E '^(pipeline|fundlens-postgres)-lvch8zyndujjzkz16ksys8im' | sed "s/^/$t /; s/\$/ free=${f}G/"
  sleep 10
done | tee -a mem.txt
```

**Expected:** two lines every 10 s, `pipeline` under 1 GiB of 40 GiB. Switch back with `Ctrl-b 0`.

```bash
# VM, tmux window 0
export B=$(date -u +%Y%m%dT%H%M%SZ); echo "$B"
docker exec "$(fl pipeline)" fundlens seats --cycle 2024 --report --build-id "$B" 2>&1 | grep -v '^{'
time docker exec "$(fl pipeline)" fundlens transform --cycle 2024 --build-id "$B" 2>&1 | tee transform-raw.log | grep -v '^{'
```

**Expected:** seats prints 441 / 35 (2 special) / 1 races and 49 unmatched filings, as NEU-2153's run did. The transform takes about 32 minutes (`real`), with no `ChecksFailed`.

### 6.3 Read the figures

```bash
# VM, tmux window 0
docker exec -i "$(fl pipeline)" python -c '
import json, sys
for line in sys.stdin:
    if line.startswith("{"):
        entry = json.loads(line)
        if entry["message"].startswith("memory after "):
            print(entry["ts"][11:19], entry["message"][13:])' < transform-raw.log | tee memory.txt
wc -l < memory.txt
grep -o '"message": "operating_expenditure 2024[^"]*"' transform-raw.log
```

**Expected:** one line per step, `HH:MM:SS <step>: peak resident … spilled`. The count is 1 + 12 models + the checks + 12 writes + 12 uploads: 83 with the 46 checks at `2e86f5f`. The spending line reads `2,246,038 rows, 1,550,225 counted, $9,594,284,292.22 counted, $362,505,186.62 (3.78%) unclassified`, as NEU-2153's did.

```bash
# VM, tmux window 0
sort -k3 -h mem.txt | grep pipeline | tail -1
tail -1 memory.txt
peak=$(grep 'write ' memory.txt | tail -1 | grep -o 'peak resident [0-9.]* GiB'); grep -m1 "$peak" memory.txt
grep 'spilled' memory.txt | grep -v ' 0.00 GiB spilled' | head -1
grep -E '^[0-9:]+ (views|silver (independent_expenditure|reported_total|candidate_reported_total|operating_expenditure|contribution)|write (operating_expenditure|contribution)) 2024' memory.txt
mk transformed 2024 "$B" | grep duration_s
mk transformed 2024 20261121T193655Z | grep duration_s
mk transformed 2024 20261121T183242Z | grep duration_s
```

**Expected, in order:**

1. The sampler's peak for `pipeline` and its time.
2. The process's peak resident memory after the last upload. The sampler's peak minus this is what `docker stats` counts beyond the process (page cache, mostly).
3. The first step whose line carries the peak the writes ended on: **the step that set the peak**.
4. The first step that held spilled bytes, or nothing if DuckDB never spilled.
5. Eight lines: the baseline, models 04, 09, 10, 11 and 12, and the two writes the verdict reads.
6. Each build's transform seconds, for `capacity.md`'s rows.

Stop the sampler (`Ctrl-b 1`, `Ctrl-c`). Paste `memory.txt` and the outputs above into the session; they are the docs PR's evidence.

**The verdict.** For a step, call **held** its line's `in memory` plus `spilled`, and **outside** its `resident` minus `in memory`.

- **Arm 1:** held after `write operating_expenditure 2024` minus held after `silver candidate_reported_total 2024` is above 0.10 GiB. The table was dropped and something of it remains in DuckDB.
- **Arm 2:** outside after `silver operating_expenditure 2024` minus outside after `silver candidate_reported_total 2024` is above 0.10 GiB, **and** the same difference taken at `write operating_expenditure 2024` is also above 0.10 GiB. Something outside DuckDB grew across the classifier's model and stayed.

If either arm holds, **the classifier step holds memory into `contribution`'s write.** File a fix ticket with these figures and link it from NEU-2408.

If neither holds, it holds nothing, and the 1.73 GiB is explained by output 4:

- **DuckDB spilled** at or before `write contribution 2024`: the peak is bound by the 29.80 GiB limit plus whatever sits outside DuckDB, and a table's size does not add to it.
- **DuckDB never spilled:** the peak is the demand of the step output 3 names, and the difference between the two 2026-11-21 runs is that step's own spread.

**A caution on arm 2.** "Outside" also grows when DuckDB evicts blocks and the allocator keeps the memory, which has nothing to do with the classifier. So if arm 2 alone holds, compare it with the same difference across models 09 to 10 and 10 to 11 (output 5). If those move as much, record the verdict as "not held in DuckDB; outside-DuckDB growth is no larger than its neighbours'", and file no fix ticket.

## 7. The docs PR (after the run)

Branch from `main`; `docs(capacity): … (NEU-2408)`.

### 7.1 `docs/capacity.md`, Per cycle

Three 2024 rows dated 2026-11-21, transform only, every other step `—`:

| Build | SHA | Peak | Source |
|---|---|---|---|
| `20261121T183242Z` | `adbca96` | 26.91 GiB at 19:05:21Z | NEU-2152's manual-steps comment |
| `20261121T193655Z` | `2e86f5f` | 28.64 GiB at 20:08:18Z | NEU-2153's manual-steps comment |
| this run's | PR 1's merge SHA | the sampler's peak, and the step from output 3 | §6.3 |

Transform seconds are each marker's `duration_s` (§6.3, output 6). The Notes of the first two say what each added (`operating_expenditure`; the classifier) and that no step was named, since nothing logged one.

### 7.2 `docs/capacity.md`, Findings

One bullet: the per-step figures the verdict read (output 5), the step that set the peak, whether and where DuckDB spilled, the sampler's peak beside the process's, and the verdict in §6.3's words.

### 7.3 Spec §5.1, Memory

The paragraph is rewritten to what the run showed:

- **If DuckDB spilled:** the additive budget ("about 27.35 GiB under the 29.80 GiB limit") is replaced. The paragraph says the transform's peak is bound by DuckDB's limit, gives the measured figure outside DuckDB as the headroom the container needs above it, and says a new silver table is measured by its held delta across its model in the `memory after` lines.
- **If it never spilled:** the paragraph keeps an additive budget, restated from this run's figures, and says the same about how a new table is measured.

Either way `WRITTEN_FIRST`'s comment in `transform/runner.py` is checked against the run: it says the peak is `contribution`'s write, and is corrected if output 3 names another step.

### 7.4 Linear

A comment on NEU-2408 with the verdict and the figures behind it. If a step holds memory, the fix ticket, in the three-heading format, related to NEU-2408.

## 8. Out of scope

- Reducing `contribution`'s own peak (the ticket's own exclusion).
- Any fix to the classifier or to `12_operating_expenditure.sql`: a new ticket, only if §6.3 says so.
- Memory lines in `fundlens load` or `fundlens resolve`, beyond `cluster.py` reading the shared helper.
- Recording memory in the `transformed` marker. The log lines are enough for a run someone is watching; a durable per-run figure is a separate decision.
- Raising `DUCKDB_MEMORY_LIMIT` or `mem_limit` (the ticket's own rejection).
- Removing the transform-only builds this run and the two before it left in silver.

## 9. Acceptance

- [ ] A transform's log has a `memory after <step>` line after the views and after each silver model, check, write and upload, in §4.1's formats, and `test_transform_logs_each_check_write_and_upload_after_the_last_model` asserts their order, format and that peak resident never decreases.
- [ ] `fundlens load`'s log is unchanged, and `resolve recluster: peak resident memory` still logs, now from `fundlens.memory`.
- [ ] One 2024 transform on the VM, with the sampler running, is in `docs/capacity.md` with its peak and the step that set it, beside rows for builds `20261121T193655Z` and `20261121T183242Z`.
- [ ] NEU-2408 says, with that run's figures and §6.3's rule, whether the classifier step holds memory into `contribution`'s write. If it does, a fix ticket is filed and linked.
- [ ] Spec §5.1's Memory paragraph matches what the run showed.
