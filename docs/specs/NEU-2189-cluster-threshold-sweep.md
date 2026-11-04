# NEU-2189 — Re-run the threshold sweep on the fixed first-name model and set the cluster threshold

**Ticket:** [NEU-2189](https://linear.app/neuroticsasquatch/issue/NEU-2189) · **Milestone:** M3 Resolution · **Parent story:** NEU-2021
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §6.3 item 4 (amended by this ticket only if the default moves), §6.9 · **ADRs:** 0009 (quality scored against DIME), 0010 (re-clustering)
**Related:** NEU-2188 (Done: the first-name levels, `docs/specs/NEU-2188-first-name-levels.md`; **blocks** this), NEU-2182 (Done: `fundlens diagnose` and the first sweep), NEU-2122 (Done: re-clustering, the cluster cap and the quality bar, `docs/specs/NEU-2122-recluster-chains.md` §1.1).

Planned 2026-11-03. `/implementit NEU-2189` builds **PR 1** (§4) from this file. The sweep and the choice (§5) are manual steps on `music-box-dancer` that follow PR 1's deploy. PR 2, and PR 3 if the default moves (§6), carry the results.

## 1. What and why

Clustering joins two contributor keys over a scored pair at or above the **cluster threshold**, `resolve_cluster_threshold` (`src/fundlens/settings.py:53`, default 0.95), and that value has never been tuned. NEU-2182 swept it on 2024 against the old model. Most of what a higher threshold removed there was the first-initial defect that NEU-2188 has since fixed, so those figures no longer apply.

**Where NEU-2188 left 2024** (refreshing-dime Log, 2026-11-03; model `20261104T012451Z`, build `20261103T175128Z`), at 0.95:

| Scope | Precision | Recall |
| --- | --- | --- |
| Overall | 0.8229 | 0.9105 |
| Top 10,000 | 0.9739 | 0.7988 |

- That already meets NEU-2122's overall targets (≥ 0.8 / ≥ 0.88) and top-scope precision (≥ 0.92).
- Top-scope recall misses both NEU-2122's 0.81 and the 0.8023 that NEU-2188 carried over (by 0.0035, 1,495 correct pairs; accepted there pending this ticket).
- `diagnose` counted 438,256 wrong pairs. In the hand sample, 79 of 100 were DIME's own errors, which puts precision against the truth at about 0.95–0.97.

**What follows.** Raising the threshold can only lower recall. The ticket's grid (0.95 up to 0.9999) therefore cannot recover top-scope recall, and §8.5's rule would always end in a choice by hand. Raising it would mostly cut correct pairs to remove DIME's own mistakes. Lowering it is the only way to recover top-scope recall, and that needs no code: `edge` holds every scored pair at or above the match threshold (0.9), and `fundlens recluster --cluster-threshold` accepts any value at or above it (`cli.py:434`). So this ticket sweeps **both ways** and chooses by a rule written down before the run.

### 1.1 Decisions this spec pins (grilled 2026-11-03)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Grid | **0.90, 0.92, 0.93, 0.94, 0.95, 0.97, 0.99, 0.999, 0.9999**: four values below the default plus the ticket's five. | Only the ticket's grid: it cannot lift recall, so the choice is certain to fall to "by hand". Only the values below: it would lose the comparison with NEU-2182's table, and with it the measured cost of a higher threshold on the fixed model. |
| How to choose | Four tiers, in order. Inside a tier the winner is the threshold with the highest overall precision; on a tie, the one with the higher top-10,000 recall. **1.** It meets all of NEU-2122's targets: overall ≥ 0.8 / ≥ 0.88, top 10,000 ≥ 0.92 / ≥ 0.81. **2.** It meets §8.5's floor: overall recall ≥ 0.88, top 10,000 ≥ 0.92 / ≥ 0.81, with no bar on overall precision. **3.** The step down: overall ≥ 0.8 / ≥ 0.88, top 10,000 ≥ 0.92 / ≥ 0.8023. **4.** None of these: keep **0.95**, and the Log records top-scope recall's shortfall against 0.81 and 0.8023 as accepted. | Choosing by hand, as the ticket said: the step-down tier encodes the carried-over 0.8023 floor, so the run needs no judgement. Keeping 0.95 whenever the full targets are missed: that throws away a threshold that restores 0.8023 without costing the overall targets. |
| Where the change lands | **PR 1** (this `/implementit`): the runbook §9 amendment, plus this spec and the `CONTEXT.md` term. It is merged *before* the run, so the run follows the runbook. **PR 2**: the Log entry, the `capacity.md` Findings and, if the winner is not 0.95, the new default. **PR 3**, only if the default moved: a short Log entry with the figures after the redeploy. | One PR with the results, running from this spec's commands: the run would then follow two sources at once, and the runbook would be amended only after the run it describes. |
| How the default changes | The code default in `settings.py`, never a Coolify variable: the compose file passes `pipeline` no `RESOLVE_CLUSTER_THRESHOLD` (the same as the cap in §8.5). | — |
| The cluster cap | Out of scope. The cap **binds** at a threshold when that threshold's `recluster:` line ends `→ 200`, meaning re-clustering cut pieces at the cap rather than the veto cutting them below it. If the cap binds at the winner, the Log says so and a follow-up ticket is filed; `resolve_max_cluster_keys` is not changed here. | Re-tuning the cap inside this ticket would make the sweep two-dimensional. At 0.95 the cap does not bind (`largest 263 → 103`); it can only start to below 0.95. |

## 2. Definitions

The glossary term **cluster threshold** is new in `CONTEXT.md` (Resolution), added by this ticket. Use it, not "link threshold", and do not confuse it with the match threshold. The sweep's figures use the existing terms **validation**, **labelled key**, **reference label** and **cluster cap**.

## 3. Preconditions (checked, 2026-11-03)

- NEU-2188 is merged (PR #79, docs PR #80) and its `resolve --full` has run on 2024. The working file on `music-box-dancer` holds `edge` and `component` from model `20261104T012451Z`.
- `fundlens recluster --cluster-threshold <T>` rebuilds components from `edge` at or above T (NEU-2182) and refuses T below the match threshold.
- `fundlens validate --cycle C --clusters` scores the working file and writes nothing.

## 4. PR 1 — amend refreshing-dime §9 (what `/implementit` builds)

One file of real change: `docs/runbooks/refreshing-dime.md`. This spec and `CONTEXT.md` ride along. There is no code and no test. Branch from `main`; title `docs(runbook): sweep the cluster threshold both ways and choose by rule (NEU-2189)`.

1. **§9 intro.** Say that the sweep covers values below the default as well as above it, and that §9.6 chooses the threshold and changes the default. Keep the warning that a merge kills a running command.
2. **§9.1 Expected.** `service.version=<sha>` is the merge commit of NEU-2189's PR 1 or later. That commit includes NEU-2188.
3. **§9.4 The threshold sweep.** Add four command blocks *before* the 0.95 block, for `T=0.90`, `0.92`, `0.93` and `0.94`. Each has the existing two commands: `recluster --cluster-threshold "$T"`, teed to `recluster-t$T.txt`, then `validate --cycle "$C" --clusters`, teed to `validate-t$T.txt`. Keep every value as its own block with its own `export T=…` (one command per value; never "repeat for each"). Extend **Expected**:
   - Below 0.95, components grow, so a `recluster:` line may show more `oversized` components than 9.2's.
   - If a line ends `→ 200`, the cluster cap binds at that T. Note it beside that T's figures.
   - Copy each T's `recluster:` line (pieces, largest) and both scopes' precision and recall into the Log.
4. **New §9.6 Choose the threshold.** Write §1.1's four tiers as the rule, in the runbook's own words and modelled on §8.5. Then:
   - `export T_WINNER=<T>` as a command block. Not `WINNER`: 8.6 reads that as the cluster cap, and the not-0.95 path runs 8.6 after an explicit `export WINNER=200`.
   - **If the winner is 0.95:** nothing to change. 9.5 has already put the working file back.
   - **If the winner is not 0.95:**
     - Open a PR that sets `resolve_cluster_threshold`'s default in `src/fundlens/settings.py` to the winner. Update the comment above it so it names the tuning (refreshing-dime §9, NEU-2189). Put the sweep figures in the PR body. Give the reason a Coolify entry would not work: the compose file passes `pipeline` no `RESOLVE_CLUSTER_THRESHOLD`.
     - Merge it only with nothing running on `pipeline`.
     - After the deploy, run 8.1, 8.2, 8.3, 8.6 and step 5. **Expected:** 8.3's figures are within 0.002 of the winner's row in the sweep; a gap that large means the retrained model differs, so stop and record it. 8.6 returns `(0 rows)`. `gold.meta`'s quality line after `load` and `publish` matches 8.3.
     - Amend the project spec §6.3 item 4, where 0.95 is written into the clustering step, in the same PR as the default.
5. **§9.6 Record becomes §9.7.** Add to its Findings instruction that the entry states what the threshold gained and cost on the current model: the wrong pairs removed, and the correct pairs and top-scope recall lost, against 0.95. Fix every in-document reference to the renumbered step.
6. **§8.5**: leave as is. It governs the cap, not the threshold.

**PR 1's checks:** `task format`, and the rendered Markdown has no broken anchors. The repo has no link checker, so open the file in the PR's rich diff and click the §9 anchors. Merge PR 1 only with nothing running on `pipeline` (it redeploys `pipeline`).

## 5. The run (manual, after PR 1 deploys)

On `music-box-dancer`, in tmux, with step 0's helpers and `export C=2024`:

1. **§9.1** confirms PR 1's merge commit is deployed.
2. **§9.2**: a plain `recluster`. Its `recluster:` line must match NEU-2188's: `7,339 components (3 oversized, 7,339 inconsistent) into 18,975 pieces; largest 263 → 103`. A different line means the working file is not NEU-2188's resolve: stop.
3. **§9.4**, all nine values. 0.95's figures should reproduce NEU-2188's 0.8229 / 0.9105 and 0.9739 / 0.7988; if they don't, stop. §9.3 (`diagnose`) is **not** re-run: NEU-2188 already ran it on this working file. That run's 438,256 wrong pairs are the baseline the Findings compare against.
4. **§9.5** restores the working file to the default.
5. **§9.6** chooses by the rule.

The sweep takes about 9 × (18 s + 3.5 min) ≈ 35 minutes. Never merge to `main` while it runs.

## 6. PR 2 and PR 3 (after the run)

**PR 2:** `docs(resolve): record the cluster-threshold sweep on the fixed first-name model (NEU-2189)`. If the default moves, the type is `feat(resolve)` and the subject says "set the cluster threshold to <T>".

- A new refreshing-dime Log entry, `### 2026-11-<dd> — The cluster threshold, 2024 (NEU-2189)`, appended and never rewritten. It holds:
  - the deployed SHA, build and model;
  - 9.2's line;
  - the sweep table: T, pieces, largest, overall P / R, top-10,000 P / R and wrong pairs, for all nine values;
  - which tier the winner came from and why. If it comes from tier 4, the shortfall against 0.81 and 0.8023 is stated as accepted, closing NEU-2188's carry-over;
  - whether the cap bound at any T;
  - 9.5's line.
- A `docs/capacity.md` Validation row per T (Notes: `T = <T>, validate --clusters`). Add a Findings bullet on what moving the threshold gains and costs on the fixed model, set against NEU-2182's figures on the old one.
- If the winner is not 0.95: the `settings.py` default and its comment, and the project spec §6.3 item 4 amendment ("Amended by NEU-2189: the cluster threshold is <T>, tuned against DIME").

**PR 3**, only if the default moved: after PR 2's deploy and §9.6's post-deploy steps, a second Log entry with the figures from 8.2, 8.3 and 8.6, plus `load` and `publish` with the published build and `gold.meta`'s quality line.

## 7. Acceptance criteria

- [ ] PR 1 is merged. Refreshing-dime §9.4 has command blocks for all nine thresholds, and §9.6 states the four-tier rule and the change-the-default path.
- [ ] A refreshing-dime Log entry has, for every T in the grid, the `recluster:` line's pieces and largest, overall and top-10,000 precision and recall, and wrong pairs, all on NEU-2188's model. 0.95's row reproduces 0.8229 / 0.9105 and 0.9739 / 0.7988.
- [ ] The entry names the winner and the tier it came from. If that is tier 4, it records top-10,000 recall's shortfall against 0.81 and 0.8023 as accepted. It says whether the cluster cap bound at any T, and a follow-up ticket exists if it bound at the winner.
- [ ] If the winner is not 0.95: `resolve_cluster_threshold`'s default in `settings.py` is the winner, merged with the sweep figures in the PR body, and project spec §6.3 item 4 says so. After the redeploy and `resolve --full`, `fundlens validate --cycle 2024` reports the winner's sweep figures within 0.002. `gold.meta`'s quality line matches them after `load` and `publish`, and PR 3's Log entry records all of it.
- [ ] A `docs/capacity.md` Findings entry states what the threshold gained and cost on the fixed model: the wrong pairs removed, and the correct pairs and top-scope recall lost, against 0.95.
- [ ] The working file's `cluster` table matches the crosswalk at the end: 9.5's line equals 9.2's, or, if the default moved, 8.6 returns `(0 rows)` after the new resolve.

## 8. Out of scope

- **Model changes**, including the `jw ≥ 0.8` first-name patterns NEU-2188 found behind the most wrong pairs. If the sweep shows recall lost to first names neither the nickname table nor the prefix rule names (MARGARET / MEGGIE), that belongs to overrides or nickname-table additions, in a new ticket.
- **The cluster cap** (`resolve_max_cluster_keys`). It is recorded if it binds, never changed here.
- **The match threshold** (0.9). The sweep's floor is set by it; lowering it needs a re-predict, not a re-cluster.
- **Adjudication's candidate band** `[0.6, 0.95)` (project spec §6.3 item 8). Its upper bound mirrors today's cluster threshold. If the default moves, PR 2's body notes the band for NEU-2055 to revisit; the band is not built yet.
- **Other cycles.** 2024 only; the backfill (NEU-2060) inherits whatever default this sets.
