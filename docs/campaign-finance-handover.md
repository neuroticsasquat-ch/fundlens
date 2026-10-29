# Campaign Finance Data Platform — Planning Handover

**Status:** pre-planning. Nothing built. This document captures the architecture discussion and decisions to date so planning can start from here rather than from scratch.
**Owner:** Tom (neuroticsasquat.ch)
**Date:** 2026-10-29

---

## 1. Background

### Prior attempt (~2025)
An earlier version harvested FEC contribution data and presented it by race (top donors, top recipients). It failed on two fronts:

- **Cost.** Claim-ticket / microservice architecture on Azure (Functions + queues + managed Postgres). Per-execution billing, storage-queue chatter, and managed-DB pricing made it uneconomical for a free public tool.
- **Data quality.** Transformation was weak; the same donor appeared under many name/employer/address variants and was never rolled up (Elon Musk being the canonical example). Earmarked/conduit contributions (ActBlue/WinRed) were likely double-counted.

### Goal (restated)
Donor, candidate, and committee data for every race in the country, presented by race, with correctly resolved donor identities.

- **Phase A:** FEC bulk data (all cycles since 1980), federal offices.
- **Phase B:** Whatever else is needed for complete federal coverage (independent expenditures, party transfers, etc.).
- **Phase C:** State offices. Availability and format vary wildly by state; this is explicitly "later," but the schema must anticipate it from day one.

---

## 2. Product positioning (decided)

Research into the existing landscape (FEC.gov, OpenSecrets/FollowTheMoney, DIME, commercial tools like Ante/Quorum/Civly, single-state hobby sites in KY/IL/CA) produced these conclusions:

**Where the gaps actually are**
1. **Individual donor resolution.** FEC.gov does none. OpenSecrets' strength is org/industry coding, not individual clustering, and its power features moved behind a paid tier (OpenSecrets Pro, 2025).
2. **State data currency.** FollowTheMoney (now part of OpenSecrets) is current only through the 2024 cycle and is effectively in maintenance mode. People keep hand-building single-state replacements, one state each.
3. **Cross-jurisdiction donor view.** Same person's federal + state giving on one page. Nobody does this free.
4. **Open, cleaned bulk data.** FEC bulk is raw. OpenSecrets bulk is registration-gated and non-commercial. A downloadable, resolved Parquet dataset would be used by the single-state builders, journalists, and academics.
5. Race-centric unified view (contributions + IEs + party money). Real but incremental.

**Where not to compete:** federal industry/sector analysis (OpenSecrets' decades of manual coding), and the paid campaign-industry tooling market.

**Framing:** the dataset is the product; the web app is its demo. The federal-only first phase is table stakes, not the differentiator.

**Monetization (decided: not now)**
- 52 U.S.C. §30111(a)(4) / 11 CFR 104.15 prohibits using FEC contributor information for solicitation or commercial purposes (news-media exemption). The resolved-identity layer is exactly what donor-prospecting would want, which is the prohibited use. Several states have stricter commercial-use rules. **Not legal advice — verify 104.15 before any paid product touching individual donor records.**
- Segments that would pay (campaigns, consultants, corporate PACs) are already served by incumbents with sales teams and carry the legal exposure. Segments that make the project matter (journalists, academics, watchdogs) won't pay.
- Decision: free app, free dataset, open loaders, permissive license on derived data, GitHub Sponsors / Open Collective. Design the schema so a paid API layer (SLA, freshness, alerts, newsroom embeds) could sit on top later without restructuring. Don't build it first.
- Open loaders are also the answer to the solo-dev state-adapter treadmill: the existing single-state builders become contributors instead of parallel efforts.

---

## 3. Architecture (decided)

### Core shift
**Batch ELT on one machine. No queues, no workers, no managed DB tier.** FEC bulk files change weekly for the current cycle; historical cycles are frozen. The whole pipeline is a scheduled job that rebuilds one cycle and republishes.

### Layers

| Layer | Contents | Engine / format | Lives on |
|---|---|---|---|
| **Bronze** | Raw FEC bulk zips (`indiv`, `cm`, `cn`, `ccl`, `pas2`, `oth`, `oppexp`, independent expenditures), as downloaded | Original pipe-delimited zips | Current cycle on NVMe; all cycles in R2 (or Storage Box). Historical raw is **not** kept locally. |
| **Silver** | Normalized canonical tables | Parquet (zstd), partitioned by cycle; itemized rows additionally bucketed by `donor_id` hash | NVMe, mirrored to R2 |
| **Resolution state** | Splink model, cluster → `donor_id` crosswalk, manual/LLM overrides | DuckDB file + Parquet; crosswalk and overrides also in Postgres (authored data) | NVMe + Postgres |
| **Gold** | Pre-aggregated serving tables: race summaries, top-N donors per race/candidate/committee, top recipients per donor, per-cycle totals, trigram search index | Postgres 17/18 | Dedicated Coolify Postgres resource for this app |
| **Backups** | Postgres dumps, Parquet, raw | — | R2 / Storage Box |

DuckDB is a library, not a service; it runs in-process inside the pipeline job and inside the API container (read-only, mounted volume). Postgres is the only running datastore.

### Canonical schema (source-agnostic from day one)
```
contribution(source, source_record_id, jurisdiction, cycle, contributor_raw_id,
             recipient_committee_id, amount, date, txn_type, memo_flag, ...)
committee(...)
candidate(...)
race(cycle, jurisdiction, office, state, district)
candidate_committee_link(...)
independent_expenditure(..., support_oppose, candidate_id)
```
State loaders in Phase C become adapters writing into this schema, not new pipelines.

### Pipeline steps
1. **Extract** — download bulk zips per cycle; idempotent on `(source, cycle, file, download_date)`. Historical cycles download once. Convert → push zip to R2 → delete local. Idempotency check is "does the silver partition exist," not "is the zip on disk."
2. **Transform** — DuckDB reads pipe-delimited directly, writes Parquet. Plain SQL or dbt-duckdb. Must handle:
   - **Earmark/conduit dedup:** type `24T` and `MEMO_CD='X'` records double-count unless conduit-side and recipient-side entries are collapsed.
   - **Independent expenditures** (Schedule E) attach to races for/against a candidate so super PAC money appears in race views without being a contribution.
3. **Entity resolution** — see §4.
4. **Load** — build gold into a new Postgres schema, then `ALTER SCHEMA ... RENAME` swap. Readers never see a half-loaded state.
5. **Publish** — purge Cloudflare cache via API as the last step.

### Orchestration
Single Python CLI (`fec load --cycle 2026`, `fec resolve`, `fec publish`) driven by a Coolify scheduled task. Per-step completion markers. Dagster/Prefect optional, not required. SigNoz for traces/logs; healthchecks ping on completion.

### Web app
- FastAPI, server-rendered + HTMX (or SPA — open), on Coolify.
- Every endpoint is an indexed gold lookup or a single-partition DuckDB scan. **No on-request aggregation.**
- Cloudflare in front with long TTLs; data changes weekly so cache ratio should approach 100%. Purge on publish.
- Stable URLs around stable IDs: `/race/2026/senate/MD`, `/donor/{donor_id}`, `/committee/{cmte_id}`, `/candidate/{cand_id}`.
- Search: `pg_trgm` on canonical names + aliases. Skip Meilisearch unless latency becomes a complaint.
- Bulk dataset download: Parquet snapshots served from R2 (zero egress cost).

---

## 4. Entity resolution (the hard problem)

Committees and candidates have canonical FEC IDs. **Only individuals need resolution.**

**Tooling:** [Splink](https://github.com/moj-analytical-services/splink) — open-source Fellegi-Sunter probabilistic linkage, DuckDB backend, designed for 100M+ rows on one machine.

**Pipeline**
1. Deterministic pre-normalization: parse names (`nameparser`), strip suffixes/punctuation, ZIP5, normalize employer/occupation strings, optionally `usaddress`/libpostal on street.
2. Blocking rules: (last-name phonetic + ZIP3), (last name + first initial + state), (exact employer + last name).
3. Comparison vectors: first name (fuzzy), last name, ZIP, city/state, employer, occupation. Splink's EM training learns weights — no hand-tuned thresholds.
4. Cluster connected components → `donor_id`. Canonical display name = most frequent variant weighted by amount.
5. **Stable IDs:** a crosswalk table maps cluster fingerprints to persistent `donor_id`s so weekly rebuilds don't reshuffle URLs.
6. **Overrides table:** manual merge/split assertions applied after Splink; survive rebuilds.
7. **LLM adjudication:** cheap per-token model (DeepInfra) on ambiguous clusters above an amount threshold only. The top few thousand donors by dollars are where the public cares and where fragmentation is embarrassing.
8. **Validation labels:** Bonica's DIME dataset has resolved contributor IDs — use it to score precision/recall instead of eyeballing.
9. **Incremental weekly** (match new current-cycle records against existing clusters); full re-resolution only when the model changes. When state data arrives, resolve incrementally per state, not whole-country each week.

**Known hard cases to test against:** Musk; conduit duplicates; self-funding candidates (loans under their own name inflate "top donors" — break out separately); employer-variant rollups.

---

## 5. Infrastructure constraints (verified on the box)

**Host:** `music-box-dancer`, Hetzner Robot dedicated (auction), i7-6700 (4c/8t, 2015), 64 GB RAM, 2× 512 GB NVMe in md RAID 1. Coolify host, reserved for neuroticsasquat.ch tools.

```
/dev/md2   436G  122G  293G  30%  /
/dev/loop0  63G  8.0K   60G   1%  /mnt/listens-scratch   (sparse loop file on /; can consume up to 64G of the 293G)
```
Effective free: 229–293 GB depending on scratch usage.

**Disk budget (federal only → with states)**

| Tier | Federal | + States |
|---|---|---|
| Silver Parquet | 30–60 GB | 45–100 GB |
| Gold Postgres | 10–30 GB | 20–45 GB |
| Resolution state | < 5 GB | < 5 GB |
| Bronze (current cycle only) | ~10 GB | ~15 GB |
| Rebuild scratch (DuckDB spill, transient) | 20–50 GB | 20–50 GB |
| **Steady state** | **60–110 GB** | **90–160 GB** |

Fits. Growth after backfill is ~3–5 GB/yr federal, a few GB/yr all states combined. The local copy is a cache; everything is reproducible from R2, so disk is a dial (drop old cycles locally; DuckDB can read Parquet from R2 via httpfs) not a hard limit.

**Rules**
- Raw lives in the cloud, Parquet lives on the box. Never accumulate raw state scrapes locally "for debugging."
- Cap DuckDB memory at ~24–32 GB during rebuilds (`memory_limit`), set `temp_directory` to a known path and `max_temp_directory_size`.
- Watch ClickHouse (SigNoz) retention — it's the other unbounded-growth tenant on the same disk.

**The real ceiling is CPU, not disk.** Splink over 400M+ rows on a 2015 quad-core means multi-hour rebuilds during which the box is sluggish. Acceptable for a weekly Sunday-3am batch; not acceptable if a second batch-heavy app arrives.

**Postgres topology (decided):** per-app Postgres container (Coolify's model), own volume. Do not share with other apps — the weekly bulk load and schema swap are a textbook noisy neighbor, and this DB wants a real `shared_buffers`/`work_mem`. Pipeline job and API live in the same Coolify project so they reach the DB by internal service name.

**Backups:** existing custom script loops `docker exec <container> pg_dump` per resource to the Storage Box. Keep it (correct client version per container). Add a healthchecks ping per iteration. Alternative: Coolify native scheduled backups → `/data/coolify/backups/` → single rsync to Storage Box. Crosswalk + overrides are the only non-reproducible data and get the real backup discipline.

---

## 6. Cost picture

| Item | Cost |
|---|---|
| Compute | Hetzner box, already paid (~€33/mo total for everything on it) |
| Storage | ~100–160 GB NVMe (sunk); R2 backup/bulk hosting a few $/mo, $0 egress |
| Serving | Cloudflare absorbs nearly all traffic |
| LLM adjudication | Per-token, ambiguous high-value clusters only; small |
| Dev tooling | Claude Max flat rate |

Versus prior design: no per-execution billing, no managed Postgres, no queue chatter, no cross-service egress.

**Migration question (resolved: not now).** Netcup RS 4000 G12 (~€32/mo: 12 dedicated EPYC 9645 cores, 32 GB DDR5 ECC, 1 TB NVMe, Manassas VA available) is the same price with ~5× CPU, 2× usable disk, US latency, snapshots — but half the RAM, KVM not bare metal, and Coolify has no server-to-server migration (a weekend to rebuild). **Triggers to revisit:** steady-state disk > ~300 GB; weekly rebuild > 6–8 h; US latency matters for uncached API calls; a second batch-heavy app.

**Preferred alternative to migration:** decouple the rebuild from the serving box. Run the weekly pipeline on an hourly Hetzner Cloud instance (CCX dedicated-vCPU), reading raw from R2 and writing silver Parquet + gold dump back to R2; the Robot box pulls the result and swaps schemas. ~3 h/week → roughly €2–8/mo. Removes the CPU ceiling and the rebuild-time RAM pressure entirely. Not a second permanent VM. **Design the pipeline so it can run in either place from day one** (all inputs from R2, all outputs to R2, box-local disk is only a cache).

---

## 7. Sequencing

1. **One cycle (2024), end-to-end, no entity resolution.** Committee/candidate-level views only. Proves extract → Parquet → gold → atomic publish → Cloudflare purge. Includes earmark dedup.
2. **Splink on that cycle.** Validate against DIME. Build the crosswalk and overrides tooling. Test on the known hard cases.
3. **Backfill all cycles.** Add independent expenditures. Confirm disk budget against reality.
4. **Weekly incremental for 2026.** Scheduled task, incremental resolution, cache purge, healthchecks.
5. **Public bulk dataset.** Parquet snapshots + schema docs + license on R2.
6. **State adapters** into the canonical schema. Start with NIMSP/FollowTheMoney as the broadest single source; individual state portals fill gaps. Open the loader interface so outside contributors can add states.

---

## 8. Open questions for planning

- Frontend: HTMX server-rendered vs SPA. (Lean HTMX for cache-friendliness and solo maintenance.)
- dbt-duckdb vs plain SQL files for silver transforms. (dbt buys lineage/tests; plain SQL buys simplicity.)
- Itemized detail: DuckDB-over-Parquet from the API (two engines) vs Postgres-only with partitioned itemized table (~90 GB, halves disk headroom). Default: Parquet.
- Where the canonical `race` entity comes from for races without a candidate filing yet (early cycle).
- Redistricting: district boundaries change; `race` must be keyed by cycle, not just (state, district).
- License for derived data (CC-BY? ODbL?) and for code.
- Repo layout: single monorepo (pipeline + API + loaders) vs split. Lean monorepo.
- Whether to run step 1 on the Robot box or go straight to the ephemeral-cloud-runner pattern.

---

## 9. Non-goals (for now)

- Paid tier, API keys, SLAs.
- Industry/sector coding of donors.
- Lobbying data.
- Real-time / sub-weekly freshness.
- Local (municipal) races.
