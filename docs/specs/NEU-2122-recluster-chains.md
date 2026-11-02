# NEU-2122 — Re-cluster chains: constrained single-linkage over Splink's components

**Ticket:** [NEU-2122](https://linear.app/neuroticsasquatch/issue/NEU-2122) · **Milestone:** M3 Resolution · **Parent story:** NEU-2021
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §6.3, §6.4 (amended by this spec), §6.5, §6.6, §6.9, §6.10 · **ADRs:** 0005 (crosswalk in Postgres), 0009 (quality scored against DIME), 0010 (written with this spec: clusters are re-clustered by constrained single-linkage)
**Related:** NEU-2054 (merged: `fundlens validate`, `app.resolution_quality`), NEU-2049 (merged: crosswalk splits and merges), NEU-2055 (adjudication, keep for what is left), **blocks** NEU-2062 (incremental resolve reuses `recluster`) and NEU-2060 (backfill).

Planned 2026-11-02. `/implementit NEU-2122` implements straight from this file.

## 1. What and why

`resolve/cluster.py` keeps every predicted pair at or above `RESOLVE_CLUSTER_THRESHOLD` (0.95) as an edge and makes each connected component one donor. A connected component ignores every pair it did *not* link: if A links B and B links C, A and C are one donor even when the model would never pair them. Over 5.6M contributor keys those paths run far. The 2024 DIME validation (model `20261101T205049Z`, build `20261031T202003Z`, 2026-11-02) measured overall precision **0.3657** against recall **0.9149**; donor `1661978` holds 1,105 keys that DIME labels as 766 people (ELIZABETH JAMISON, CHRISTOPHER JENKINS, KIRSTEN JOHANSEN, BRYAN JOHANSON: one Soundex code, J525, across states); the ten largest clusters held about half of all wrong pairs, and DIME's own key splits account for 1.4% of them. The failure is the clustering, not the model.

The model already knows these are different people: its first-name comparison (`resolve/model.py`, `_first_name`) all but vetoes a pair whose first names disagree outright. The veto applies to one pair at a time; nothing applies it to a cluster. And no rule bounds how many keys a cluster may hold.

This ticket adds a **re-clustering pass** after Splink's connected components and before overrides. Every cluster that holds a vetoed pair, or more keys than the cluster cap, is rebuilt from its own edges, strongest first, under two constraints: a piece never holds a vetoed pair, and a piece never holds more than the cap. Every other cluster is untouched. It also keeps the predicted pairs in the working file and adds an offline tuning loop (`fundlens recluster`, `fundlens validate --clusters`) so the cap is chosen against DIME without rewriting the crosswalk per candidate.

### 1.1 Decisions this spec pins (the ticket asked `/planit` to pin them)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Which rules | **Both**: a first-name consistency rule (no cluster holds a vetoed pair) applied to every cluster whatever its size, and a size cap (no cluster holds more than N keys). | The size cap alone cannot split the ticket's three-key chain fixture without N < 4, which would break the four-key Musk case; it also leaves small chains merged. The first-name rule alone cannot touch a cluster of different JOHN JOHNSONs in one metro, whose first names agree. |
| How they are enforced | **One constrained single-linkage pass** per offending cluster: its edges in order of probability, strongest first; each edge unions the two pieces its ends are in unless the union would hold a vetoed pair or exceed N keys; a refused edge is skipped. | Two phases (name-pure pieces plus an attachment pass for null and initial-only names, then a per-component adaptive threshold) need seeding, attachment and stranded-key rules, and the threshold is a cliff: once the cap is hit every weaker edge in the component drops, so a 2N-key real donor shatters. The single pass keeps merging elsewhere in the component as long as the constraints allow, so it becomes a few large pieces (two or three for 2N keys), never a shower of singletons. A fixed ladder of thresholds tops out on probabilities that saturate near 1.0 and either leaves a piece oversized or shreds it. Raising `RESOLVE_CLUSTER_THRESHOLD` everywhere pays for a few hundred chains with recall on every donor. Community detection (Leiden/Louvain) needs a dependency, a seed and a paragraph on the methodology page. Adjudicating large clusters (NEU-2055) merges or splits named keys and cannot fit 1,105 keys in a prompt. |
| What a vetoed pair is | **Exactly the model's else level**: both first names present, not equal, Jaro-Winkler below `FIRST_NAME_VETO_JW` (0.8, a new constant in `resolve/model.py` that the comparison level reads too), and first initials different. An initial-only name takes part by its initial: `E` and `KIRSTEN` are vetoed, `E` and `EDWARD` are not. A null first name vetoes nothing. | A stricter notion (any two different full first names) splits ELIZABETH from ELISABETH and a household's EDWARD from ELIZABETH in clusters the model never contradicted. Reusing the model's own level means the rule cannot drift from the model. |
| Which clusters are rebuilt | **Offending clusters only**: those holding at least one vetoed pair or more than N keys. The rest keep their `cluster_id` and `match_probability`. | Rebuilding every cluster is 3.8M Python passes for nothing; the pass is a no-op on a consistent cluster under the cap. |
| The cap | A setting, `RESOLVE_MAX_CLUSTER_KEYS`, default **200 until the measurement (§7) says otherwise**; the PR sets the measured value. | A constant: the cap is retuned when the backfill adds 22 cycles of keys or the model is retrained. |
| How the cap is tuned | **Offline, in the working file**: the predicted pairs are kept as the `edge` table and Splink's components as `component`; `fundlens recluster --max-keys N` rewrites `cluster` from them; `fundlens validate --cycle C --clusters` scores the working file's clusters against DIME and writes nothing. About two minutes per candidate, no crosswalk churn. | A prod `resolve --full` per candidate is 13 minutes plus a validate, rewrites every cycle's silver and draws new donor_ids each time. A one-off script in the PR is lost by the backfill. |
| Quality bar | **Precision first, with a recall floor.** The DoD's figures (overall ≥ 0.8 / ≥ 0.88, top-10k ≥ 0.92 / ≥ 0.81) are targets. If no candidate reaches them, the default is the candidate with the highest overall precision whose overall recall stays ≥ 0.88 and whose top-10k stays ≥ 0.92 / 0.81; the PR records the measured figures and amends the DoD to them. **Measured 2026-11-02:** no candidate kept the top-10k recall floor (the veto alone gives 0.8023), so 200 was kept by hand at overall 0.6288 / 0.9121, top-10k 0.9516 / 0.8023; the refreshing-dime runbook Log has every candidate. | Best F1 can trade away precision, which is the public failure (strangers on one donor page); fragmentation is the quieter one. Treating the targets as hard blocks the backfill on a number nobody measured. |
| Where it runs | A new phase, `recluster`, in `resolve_full` between `cluster` and `overrides`, timed and logged like the others. Overrides and adjudications apply afterwards, unconstrained: a human merge may build a cluster over N or holding a vetoed pair. | Running after overrides would undo a reviewed merge. |

## 2. Definitions

These are glossary terms (`CONTEXT.md`, Resolution): **component** (what linkage's connected components give, before re-clustering), **chain** (a component holding keys linkage would never pair directly), **vetoed pair**, **re-clustering** and **cluster cap**. Use them in code and docs; avoid "raw cluster", "max cluster size", "over-merged".

- **Edge**: a predicted pair at or above the match threshold (0.9), with its `match_probability`. An edge *joins* two keys when its probability is at or above the cluster threshold (0.95). Edges are undirected: stored once with `contributor_key_l < contributor_key_r`.
- **Component**: Splink's connected component over the joining edges (today's cluster).
- **Vetoed pair**: two keys whose first names the model's else level rejects (§1.1).
- **Offending cluster**: a component holding a vetoed pair, or more than N keys.
- **Piece**: a cluster the pass makes from an offending component. Its `cluster_id` is its lowest `contributor_key`, as Splink names components.

## 3. The pass (`resolve/cluster.py`)

### 3.1 Tables

Three tables on the working file, all fundlens's own (so `delete_tables_created_by_splink_from_db` in the `save` phase leaves them). As built, `cluster()` writes `edge` and `component`, and `recluster()` writes `cluster`:

- `edge(contributor_key_l, contributor_key_r, match_probability)`: every predicted pair at or above the match threshold, `l < r`, one row per pair. Kept after the run: the tuning loop, `recluster`, and NEU-2062 read it. Size on 2024 is recorded in `docs/capacity.md` (the Resolution table gains a "Working file GB" note; expect low single-digit GB).
- `component(cluster_id, contributor_key)`: Splink's clustering at the cluster threshold, as `cluster_pairwise_predictions_at_threshold` returned it. Kept, so `recluster` starts from it without predicting again.
- `cluster(cluster_id, contributor_key, match_probability)`: unchanged schema, now the re-clustered result. `match_probability` is the strongest edge joining the key to another key *of its final cluster*, NULL for a key alone. Overrides, the crosswalk and the tests read it as before.

### 3.2 Finding offending clusters (SQL)

In DuckDB, over `component` joined to `contributor` (which carries `first_name`):

1. Oversized: `cluster_id` with `count(*) > N`.
2. Inconsistent: for each component with at least two distinct non-null first names, the pairs of its distinct first names (`a < b`) where `a <> b AND jaro_winkler_similarity(a, b) < FIRST_NAME_VETO_JW AND left(a, 1) <> left(b, 1)`. `jaro_winkler_similarity` is the DuckDB function Splink's `JaroWinklerLevel` compiles to, so the SQL and the model agree by construction. Any such pair makes the component inconsistent; the set of vetoed name pairs per component is passed to the pass.

The offending components, their members (with `first_name`) and their joining edges (both ends in the component) come out in one query each, ordered by `cluster_id`, and are grouped in Python per component. The largest component on 2024 is 1,105 keys; its internal edges are at most tens of thousands of rows. Memory is not a concern.

### 3.3 Re-clustering one component (pure Python, unit-tested)

```
recluster_component(members, edges, vetoed, max_keys) -> dict[contributor_key, cluster_id]
```

- `members`: each key and its first name (or None). `edges`: `(key_l, key_r, match_probability)` for the joining edges inside the component. `vetoed`: the set of frozenset name pairs the SQL found.
- Union-find over the members. Each piece tracks its key count and its set of distinct non-null first names.
- Edges are processed in order `(match_probability DESC, key_l, key_r)`. An edge whose ends are already one piece is skipped. Otherwise the union is **refused** when `count(A) + count(B) > max_keys`, or when any `(a in names(A), b in names(B))` is in `vetoed`; refused edges are never retried (a piece only grows and a name set only widens, so a refused union never later becomes allowed).
- The result maps each key to its piece's lowest key. Determinism: same inputs, same output; ties by key order, nothing random.
- Guarantees, asserted in tests: no piece exceeds `max_keys`; no piece holds a vetoed pair; a component with no vetoed pair and at most `max_keys` keys comes back as one piece (so running the pass on a non-offending component changes nothing, which is why they are skipped).

### 3.4 Writing the result

`cluster` is rebuilt as `component` with offending components replaced by their pieces, then `match_probability` recomputed per key from `edge` within the final cluster. A dataclass `Reclustered(oversized, inconsistent, components, pieces, largest_before, largest_after, keys_moved)` is returned, logged (`resolve recluster: 318 components (9 oversized, 311 inconsistent) into 4,102 pieces; largest 1,105 → 200`) and carried on `Resolved` for the CLI summary line.

`recluster(con, *, max_keys, cluster_threshold)` is a function of the working file alone: no Linker, no Postgres. It takes the cluster threshold because `edge` holds every pair at or above the match threshold, and only those at or above the cluster threshold join two keys. NEU-2062 (incremental) calls it on the new keys' components with the same `edge` conventions, which is the "reuse" the ticket asks for.

## 4. Settings and the run

- `Settings.resolve_max_cluster_keys: int = Field(default=200, alias="RESOLVE_MAX_CLUSTER_KEYS")`, `ge=2`. `resolve_full` takes it as `max_keys` (beside `thresholds`) and passes it to `recluster`.
- `resolve_full` phases become `load, train, cluster, recluster, overrides, save, crosswalk, silver`; the `resolved` marker, the summary line and `docs/capacity.md`'s Resolution table column list include `recluster`.
- `cluster_fingerprint` is unchanged (it hashes member keys); adjudication rows written against a chain's fingerprint simply no longer match anything, which is correct.
- The crosswalk needs no change: a split component keeps its donor_id on the piece holding most of its dollars and the other pieces draw new ids (spec §6.6); a redirect is written only for an id no key carries any more, so splits retire few ids. The PR body lists the run's `repointed` and `redirects` counts from `crosswalk:` output.

## 5. The tuning loop (CLI)

### 5.1 `fundlens recluster [--max-keys N]`

No family, hand-run, like `validate`. Opens the working file (`paths.resolution_database`), requires `component`, `edge` and `contributor` (else exit 1: `no components in the working file: run fundlens resolve --full`), reads the overrides file at `OVERRIDES_PATH` and checks it as `resolve_full` does (`overrides.check`, with the Postgres connection), then rewrites `cluster` = `recluster(con, max_keys=N or the setting)` followed by `overrides.rewrite`, so its `cluster` is exactly what `resolve --full` would write under that N. Prints the `Reclustered` summary and the cluster count. Touches nothing else: no crosswalk, no silver, no marker, no R2. A failure leaves the previous `cluster` in place (rebuild into a temp table, then swap).

### 5.2 `fundlens validate --cycle C --clusters`

Scores the working file's `cluster` table instead of silver's `donor_id`: the labelled records are built as today (bronze `indiv` by FEC ids, DIME by `(cmte_id, tran_id, amount, date)`, silver `contribution` by `SUB_ID` for `contributor_key` and amount), then `cluster_id` from the working file (attached read-only) stands in for `donor_id`. Under `--clusters`: silver's `donor_id` is not required (the `NotResolved` check is skipped), every labelled key must be in `cluster` (else exit 1 naming the count missing and `resolve --full`), the report prints with a last line `clusters from <working file path>; nothing written`, and **no row** goes to `app.resolution_quality`. The `Validated` result is returned for tests. Without `--clusters` nothing changes.

### 5.3 The loop, on `music-box-dancer` (also §8 of the runbook)

Each candidate is `recluster --max-keys N` then `validate --cycle 2024 --clusters`; the veto-only figure is `--max-keys` set to a number above the largest component (there is no "off"), so each rule's contribution is visible. Candidates: veto-only, 500, 200, 100, 50. The cycle's silver must be transformed (it is), and the working file must come from a `resolve --full` run by this PR's code (the one before it holds no `edge`).

## 6. Fixture and tests

### 6.1 The chain (fixture cycle 2024, `tests/fixtures/fec/2024/`)

Plant three counted `indiv` rows to one committee in `cm`, from one ZIP, forming three contributor keys that share `last_name` and `zip3` (so the first blocking rule compares all three):

| NAME | ZIP | EMPLOYER | OCCUPATION | Note |
|---|---|---|---|---|
| `QUINLAN, BEATRICE` | one ZIP5 | one employer | one occupation | end A |
| `QUINLAN, MRS` | same | same | same | the bridge: `normalize_name` drops the title, so `first_name` is NULL (verify with the normalizer; `QUINLAN,` with nothing after the comma also works) |
| `QUINLAN, DESMOND` | same | same | a different occupation | end B |

With the fixture's priors (no training, spec §6.3): bridge–BEATRICE agrees on everything but first name (null level), so it joins at far above 0.95; bridge–DESMOND agrees on all but first name and occupation, so it joins at above 0.95 but weaker; BEATRICE–DESMOND is a vetoed pair (B/D, JW well under 0.8) and never joins. Today's code makes one component of three; the pass makes `{BEATRICE, MRS}` and `{DESMOND}`, the bridge going with its strongest edge. Pick names and values that collide with no existing fixture donor (`grep` the CSVs), and add the three rows' DIME labels to `tests/fixtures/dime/contribDB_2024.csv`: BEATRICE and MRS one `bonica.cid`, DESMOND another, so `validate` stays 1.0 / 1.0.

`expected.yaml`: `rows.indiv` +3, `silver.contribution` +3, `silver.contributor` +3, `distinct_donors` +2, donors `chain_end_beatrice` (`resolved_by: linkage`, two sub_ids) and `chain_end_desmond` (`resolved_by: none`); `tests/unit/test_fec_fixture.py` keeps every number honest. The affected race/candidate/committee totals move by the planted amounts.

### 6.2 Unit (`tests/unit/test_cluster.py`, new)

`recluster_component` on hand-built components:

- A three-key chain with a null bridge splits as §6.1 says; the bridge follows the stronger edge; swapping the two edge strengths moves it.
- A vetoed pair reached only through two null keys (`ELIZABETH – ø – ø – KIRSTEN`) is split, and the two nulls end up on the side of their stronger edges.
- A cap of 3 on a five-key clique of equal probabilities gives pieces of 3 and 2, in key order (ties deterministic).
- A 2N-key component of one person (no vetoed pair, every key linked to every other at varied strengths) becomes two or three pieces, each ≤ N, no singleton. (As built: "exactly two" is not something greedy single-linkage can promise, since pieces of 4, 3 and 3 under a cap of 5 cannot merge; no two of the pieces left fit under the cap together, so 2N keys leave at most three.)
- A consistent component under the cap comes back unchanged.
- The vetoed-pair SQL agrees with the model's else level on a table of name pairs (exact, JW ≥ 0.92, JW ≥ 0.8, same initial, initial-only vs full, null, and vetoed), computed with the same `jaro_winkler_similarity`.

### 6.3 Integration (`tests/integration/test_resolve.py`, `test_validate.py`)

- `test_resolve_full_clusters_the_fixture_as_its_donors` passes as is with the new donors in `expected.yaml`: the chain's ends sit in different clusters, every other planted donor resolves as before, and after `fundlens dime --import` + `validate --cycle 2024 --top 3` both scopes are still 1.0 / 1.0.
- `edge` and `component` exist in the working file after `resolve --full`; `edge` has no row below the match threshold and `l < r` on every row.
- With `RESOLVE_MAX_CLUSTER_KEYS=3`, `resolve --full` leaves no cluster over three keys and the Musk case (four keys) is two clusters; `fundlens recluster --max-keys 3` on the working file of a default run gives the same `cluster` table, and `recluster --max-keys 200` restores it.
- `validate --cycle 2024 --clusters` after `recluster --max-keys 3` prints figures below 1.0 recall (Musk split), writes no row to `app.resolution_quality`, and says so in its last line; without `--clusters` the two rows are written as before.
- `recluster` with no working file, or one without `component`, exits 1 naming `resolve --full`.

### 6.4 Everything runs in the container

`task test:unit`, `task test:integration`, `task lint`, `task typecheck`, `task format` before committing; files staged by name. No migration: `app` is untouched.

## 7. Rollout on `music-box-dancer` (manual steps, after merge; the user walks these)

Never merge mid-runbook: a merge redeploys `pipeline` and kills a running step. The section goes into `docs/runbooks/refreshing-dime.md` as "8. Tuning the cluster cap", in the runbook's shape (every value its own command, expected output after each block, Log entry at the end). In outline:

1. Deploy; `printenv OTEL_RESOURCE_ATTRIBUTES` shows the merged SHA.
2. `fundlens resolve --full` (default N=200): writes `edge` and `component`, re-clusters, assigns the crosswalk. Record phases, the `recluster` summary, `repointed` and `redirects`, and the working file size in `docs/capacity.md`'s Resolution table.
3. `fundlens validate --cycle 2024`: the N=200 figures, into `app.resolution_quality`, the Log and the Validation table (N in Notes).
4. The loop (§5.3) for veto-only, 500, 100 and 50: each `recluster --max-keys N` then `validate --cycle 2024 --clusters`; every figure into the Log and the Validation table.
5. Choose by §1.1's quality bar. If the winner is not 200: open a follow-up PR that changes the default in `settings.py` (the compose file passes `pipeline` no `RESOLVE_MAX_CLUSTER_KEYS`, so a Coolify entry never reaches it), merge it with nothing running, then run `resolve --full` and `validate --cycle 2024` again. Either way, `recluster --max-keys <winner>` last, so the working file's `cluster` matches the crosswalk.
6. The next `load` + `publish` carry the figures into `gold.meta` (refreshing-dime step 5). The DoD's crosswalk query, given in the PR: `SELECT donor_id, count(*) FROM app.crosswalk GROUP BY donor_id HAVING count(*) > <N>` returns no row.

## 8. Docs

- `CONTEXT.md`: component, chain, vetoed pair, re-clustering, cluster cap (written with this spec).
- `docs/adr/0010-clusters-are-re-clustered-by-constrained-single-linkage.md` (written with this spec).
- Project spec §6.4: amended line pointing here (written with this spec). §6.10 (incremental): NEU-2062 reuses `recluster`; its spec says how.
- `docs/capacity.md`: the Resolution table's phase list gains `recluster`; new rows from §7; Validation rows per candidate.
- `docs/runbooks/refreshing-dime.md`: §8 "Tuning the cluster cap" (the loop, §7), and the "Not in this runbook" line loses "tuning the resolution thresholds".
- `docs/runbooks/adding-an-override.md` Facts: the working file now also holds `edge` and `component`; an override may build a cluster the cap or the veto would not.
- NEU-2056 (methodology page) gets one sentence to print: "Clusters are Splink's connected components, re-clustered so that no cluster holds two first names the model rejects or more than N keys."

## 9. Acceptance criteria

- [ ] On the fixture, after `resolve --full`, `QUINLAN, BEATRICE` and `QUINLAN, DESMOND` are in different clusters (and donor_ids), the bridge key is with BEATRICE, every planted donor in `expected.yaml` resolves as before, and `validate --cycle 2024 --top 3` reports 1.0 / 1.0 for both scopes (integration test).
- [ ] `recluster_component` passes §6.2's unit cases, including the guarantees (no piece over the cap, no vetoed pair in a piece, a non-offending component unchanged) and the SQL-versus-model agreement on vetoed pairs.
- [ ] `resolve --full` writes `edge` and `component` to the working file and keeps them past `save`; its summary and its log list the `recluster` phase (as built: a marker carries row counts only, so the `resolved` marker is unchanged).
- [ ] `RESOLVE_MAX_CLUSTER_KEYS=3` leaves no cluster over three keys on the fixture; `fundlens recluster --max-keys 3` reproduces that `cluster` table from a default run's working file (integration test).
- [ ] `validate --cycle 2024 --clusters` scores the working file, writes nothing, and names the working file in its last line (integration test).
- [ ] On `music-box-dancer`, the loop's figures for veto-only, 500, 200, 100 and 50 are in the runbook Log and `docs/capacity.md`; the chosen default meets the DoD's figures or §1.1's quality bar, and the PR (or its follow-up) carries the measured figures, the `repointed` and `redirects` counts, and the crosswalk query returning no row over N.
- [ ] `CONTEXT.md`, ADR-0010, spec §6.4, `capacity.md` and the two runbooks are updated as §8 says.

## 10. Out of scope and deferred

- Retraining the model or changing its comparisons (ticket). A cluster of different JOHN JOHNSONs across one metro whose keys each link at 0.99 is the model's problem; the cap bounds the damage, it does not fix the cause.
- The incremental resolve (NEU-2062): must call `recluster` on new keys' components; its spec says how `edge` is extended.
- Adjudication (NEU-2055) selects on probabilities in `[0.6, 0.95)`; `edge` holds pairs at or above 0.9 only, so NEU-2055 predicts at its own threshold or lowers the match threshold. Not this ticket's call.
- Community detection over components, if the single pass proves too blunt on the backfill: a later ticket with a measurement.
- A `--max-keys` per cycle or per model: one setting for the run.
