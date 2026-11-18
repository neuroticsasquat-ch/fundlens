# NEU-2137 — Project spec for "every FEC dollar": file catalogue, shared contracts, section stubs per milestone

**Ticket:** [NEU-2137](https://linear.app/neuroticsasquatch/issue/NEU-2137) · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Milestone:** M1 Reported totals · no parent story
**v1 spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §1, §2, §3.4, §9, §14 · **Glossary:** `CONTEXT.md` · **ADRs:** 0002 (R2 is the store of record), 0011 (organizations are grouped, not resolved)
**Blocked by:** nothing. **Blocks:** NEU-2138, NEU-2141, NEU-2150, NEU-2151, NEU-2163, NEU-2164, NEU-2173, NEU-2352. **Related:** NEU-2064 (dataset snapshot publisher, Done), NEU-2140 (summary-files measurement, Done: `docs/measurements/summary-files-2024.md`).

Planned 2026-11-18. `/implementit NEU-2137` produces **one docs PR**: the new project spec, two lines in the root `CLAUDE.md`, and the `CONTEXT.md` term this planning session already wrote. Nothing under `sql/`, `src/` or `frontend/` changes.

## 1. What and why

P-NEU-107 has no spec. Its decisions, locked on 2026-11-02, and its milestones' shared contracts exist only in Linear, and seven tickets are waiting for a document to write their sections into. This ticket writes `docs/specs/fundlens-every-fec-dollar-project-spec.md`: purpose, decisions, the file catalogue, one stub per milestone, and the public-dataset rule.

The ticket text predates four things, which this spec reconciles:

1. NEU-2140's merged measurement dropped `webl` and `candidate_summary` from what fundlens reads and amended M1's source precedence.
2. The dataset shipped (NEU-2064, 2065, 2067), so "joins the public dataset" now takes code, not only a line in v1 §9.
3. `load` and the dataset snapshot both refuse a live build that lacks a silver table they read (`load/gold.py` `_require_inputs`, `publish/dataset.py` `_silver_copies`), which no P-NEU-107 ticket accounted for.
4. FEC's bulk-data page lists files the project description neither reads nor names as a non-goal.

### 1.1 Decisions pinned (grilled 2026-11-18)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| `webl` and `candidate_summary` | **Not read, and listed as such in §3 with the reason.** §3's read list for M1 is `weball`, `webk`, `committee_summary`. | The measurement's Decision 6: `webl` repeats `weball`'s rows; `candidate_summary` is the sum of `committee_summary`'s. Listing them silently absent was rejected: someone re-adds them. Keeping `webl` as the ticket says was rejected: it contradicts the merged measurement. |
| How much of FEC's page §3 covers | **The whole page.** Two tables: files read, and every other file on the page with why it is not read. §1's non-goals gain the entries the project description lacks. | "Every FEC dollar" should be checkable against FEC's own list. Covering only the two measured-out files leaves the Presidential map exports and paper filings unexplained. |
| Paper-filed `.fec` reports | **Not read; NEU-2181 (the M5 spike) decides.** The §9 stub adds them to the spike's question. | Senate campaigns filed on paper until 2018, so the spike should rule on them knowingly. Declaring them a non-goal now was rejected: nobody has measured what they hold that the bulk files lack. |
| M5's section | **§9 "Raw filings", a stub, after §8 Public dataset; §10 lists the milestones.** §4–§8 keep the numbers other tickets cite. | NEU-2141, 2150, 2163 and 2173 cite §4–§7, and this ticket cites §8. Renumbering was rejected for that reason; no section at all leaves M5 without a home. |
| What a stub carries | **Its milestone's Shared contracts, copied from Linear, plus the ticket that fills it.** M1's as the measurement amended it. No table design. | The ticket's own Problem is that decisions live only in Linear. Bare two-line stubs keep them there. Moving contracts to §2 mixes project-wide decisions with one milestone's rules. |
| Who puts a table in the dataset | **The spec ticket adds it to v1 §9's list; the silver ticket that builds it adds it to the dataset in code, in the same PR.** Additive under `v1/`, no `v2/`. | The table is public from its first build and the schema test covers it at once. The runbook tickets and one end-of-project ticket were rejected: both leave built tables unpublished for weeks. |
| A live build that predates a new table | **Tolerated until the backfill.** A named list of this project's tables may be absent from a live build; gold and the snapshot read such a cycle as having no rows of the table. A silver model always writes its partition, empty before its source's first cycle. NEU-2180 rebuilds every cycle and then empties the list. | Without it the first new gold input breaks the weekly run. Writing a table into a published build in place (`transform --table`) changes a published build, which nothing does today. Rebuilding every cycle per milestone is four backfills. |
| Where that mechanism is built | **NEU-2352**, a new M1 ticket created in this session: blocked by this one, blocking NEU-2143 and NEU-2144, and NEU-2180 gained a checkbox to empty the list. | Folding it into NEU-2143 makes one PR span silver SQL, load and publish. |
| Stale Linear text | **Corrected in this session** (§4.1). The electioneering first cycle is corrected by `/implementit`, once it has read FEC's page itself. | One correction, made from the repo and the merged measurement. |
| Glossary | **File catalogue** added to `CONTEXT.md` (written in this session, uncommitted). | Tickets and code already say "catalogue"; "manifest" already means a snapshot's. |

## 2. The document

`docs/specs/fundlens-every-fec-dollar-project-spec.md`, in the v1 spec's shape: a title, a header paragraph, numbered `##` sections, decisions as a table.

**Header.** Linear initiative fundlens (I-16), project P-NEU-107, team NEU. Glossary `CONTEXT.md`, decisions `docs/adr/`. One sentence on how it relates to the v1 spec: v1's §3 (architecture), §5 (pipeline), §10–§12 (infrastructure, local development, testing) govern this project unchanged; this document adds to v1's §4, §7 and §9 and says where. As in v1: a ticket needs its own `/planit` spec only where this document is silent.

### §1 Purpose

From the project description's first paragraph: v1 tracks itemized money into committees; this project adds the rest of what FEC publishes in bulk, so that fundlens accounts for every dollar FEC can show. It is the handover's Phase B.

**Non-goals**, each with its reason, from the project description's "Not in this project", plus two the page adds:

- FEC's Postgres dumps (duplicate the bulk files).
- Form 1 and Form 2 filer lists and the false and fictitious filings list (no money).
- The unofficial Senate e-filings, 2008–2018 (already in `indiv`).
- Pre-2002 party soft money (not in the bulk catalogue).
- Election results, Lobbying Disclosure Act data, state data.
- **Added:** the Presidential map exports (`Contributions_by_Size.csv`, `Contributions_by_3Zip.csv`, the overall summary): FEC's own aggregates of presidential committees' receipts, which fundlens computes from `contribution`. NEU-2141 may cite `Contributions_by_Size.csv` as a check on its gift-size buckets; it is never a source.
- **Added:** `webl` and `candidate_summary` (§3's not-read table; the measurement's Decision 6).

Paper-filed `.fec` reports are not a non-goal: §9.

### §2 Decisions

A table, `Area | Decision | Reason`. The four locked on 2026-11-02, then the two this session added:

| Area | Decision | Reason |
|---|---|---|
| Project boundary | Separate project from v1. M3.5 Organization money stayed in v1. | v1 ships on its own scope and Done line; M3.5 fixed a v1 bug ahead of v1's backfill. |
| Lobbyist files | FEC's lobbyist bundling and lobbyist/registrant PAC files are in scope. | v1's "lobbying" non-goal means Lobbying Disclosure Act data, not FEC disclosures. |
| Payees and organizations | Grouped by normalized name, never resolved with Splink, no industry coding. | ADR-0011: the hard cases are corporate structure, not spelling, and industry coding is a project of its own. The payee ADR (NEU-2150) will be 0012. |
| Public dataset | Every new silver table joins the dataset snapshot (§8). | The resolved dataset is the product (v1 §1). |
| Files read | The file catalogue (§3) is the only list of what fundlens reads; every file on FEC's bulk-data page is either in it or in §3's not-read table with a reason. | So "every FEC dollar" can be checked against FEC's page. |
| Older builds | A live build transformed before one of this project's tables existed may lack it: gold and the snapshot read that cycle as having no rows of the table. A silver model always writes its partition, empty for a cycle before its source's first cycle. NEU-2352 builds the list of tables allowed to be absent; NEU-2180's backfill rebuilds every cycle and empties it. | `load` rebuilds gold from every cycle's live build and the snapshot copies every one, and both refuse a build that lacks a table (v1 §3.4, §9). Rejected: adding a table to a published build in place; a full backfill per milestone. |

### §3 File catalogue

Opening rules, from M1's first shared contract and NEU-2138:

- Bulk files are catalogued only in `fundlens.fec.files`; a file outside the file catalogue is neither downloaded nor read.
- Two formats: `zip` (pipe-delimited, no header row, columns from a vendored header) and `csv` (comma-delimited, header row). Bronze keeps the source file as downloaded (ADR-0002).
- Three URL shapes below `FEC_BULK_URL` (`https://www.fec.gov/files/bulk-downloads`): per cycle in the cycle's directory (`<yyyy>/<name><yy>.zip`, `<yyyy>/<name>_<yyyy>.csv`); per year in an undated directory (`data.fec.gov/leadership<yyyy>.csv`); a single undated file (`data.fec.gov/lobbyist.csv`). NEU-2138's URL template per file must cover all three. Its ticket text names only two, so say so here.
- The page's access date, and a line that first cycles are the page's (FEC states two-year ranges; the first cycle is the even year).

**Read by this project.** Columns: `File | Format | URL pattern | First cycle | Milestone | Catalogued by`. The rows below are from a read of the page on 2026-11-18 **made through a summarizing fetch, so they are a starting point, not the record**: `/implementit` reads <https://www.fec.gov/data/browse-data/?tab=bulk-data> itself, writes what the page states, and records that day as the access date.

| File | Format | URL pattern | First cycle | Milestone | Catalogued by |
|---|---|---|---|---|---|
| `weball` | zip | `<yyyy>/weball<yy>.zip` | 1980 | M1 | NEU-2142 |
| `webk` | zip | `<yyyy>/webk<yy>.zip` | 1996 | M1 | NEU-2142 |
| `committee_summary` | csv | `<yyyy>/committee_summary_<yyyy>.csv` | 2008 | M1 | NEU-2142 |
| `oppexp` | zip | `<yyyy>/oppexp<yy>.zip` | 2004 | M2 | NEU-2151 |
| `independent_expenditure` | csv | `<yyyy>/independent_expenditure_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `ElectioneeringComm` | csv | `<yyyy>/ElectioneeringComm_<yyyy>.csv` | 2010 (Linear's M3 says 2008: verify) | M3 | NEU-2164 |
| `CommunicationCosts` | csv | `<yyyy>/CommunicationCosts_<yyyy>.csv` | 2010 | M3 | NEU-2164 |
| `leadership` | csv | `data.fec.gov/leadership<yyyy>.csv` | 2010 | M4 | NEU-2174 |
| `lobbyist` | csv | `data.fec.gov/lobbyist.csv` (one file, 2007–) | undated | M4 | NEU-2174 |
| `lobbyist_bundle` | csv | `data.fec.gov/lobbyist_bundle.csv` (one file, 2009–) | undated | M4 | NEU-2174 |

Notes the section carries:

- `weball` and `webk` have no header file on FEC's site (404 on 2026-11-05, the measurement's header table); their column lists are vendored from FEC's file descriptions.
- Whether `leadership<yyyy>.csv` exists for odd years, and what "first cycle" means for the two undated files, is NEU-2173's to measure; §3 states only what the page shows.
- v1's six files (`cm`, `cn`, `ccl`, `indiv`, `pas2`, `oth`) are listed in one line by reference to `fundlens.fec.files`, not re-described.

**On FEC's page and not read.** Columns: `File | Why not`.

| File | Why not |
|---|---|
| `webl` (1996–) | `weball`'s rows, identical on every measure in 2024 and 2004 (measurement Q1, Q3, Q8; Decision 6) |
| `candidate_summary` (2008–) | The sum of `committee_summary`'s own P/A rows (2,315 of 2,321); candidate figures are summed from credited committees instead (Decisions 1, 6) |
| Presidential map exports (2008–) | FEC's aggregates of money already in `indiv`; §1 |
| `Form1Filer`, `Form2Filer` | No money |
| `FalseFictitiousFilings.csv` | No money |
| Postgres dump files | Duplicate the bulk files |
| Senate unofficial e-filings, 2008–2018 | Already in `indiv` |
| Electronically filed reports (`.fec`) | §9: NEU-2181 decides |
| Paper-filed reports (`.fec`) | §9: NEU-2181 decides |

If the page lists a file that is in neither table, `/implementit` adds it to this one with a reason, or stops and asks if the file carries money no table here covers.

### §4–§7 Milestone stubs

Each stub is: one sentence of scope from its milestone description; **Shared contracts**, copied from the Linear milestone (fetch them at implementation, so a later edit is picked up); and "Filled by" naming the ticket. No columns, no gold fields.

| Section | Milestone | Filled by | Notes |
|---|---|---|---|
| §4 Reported totals | M1 | NEU-2141, from `docs/measurements/summary-files-2024.md` | The precedence contract is the amended one (corrected in Linear 2026-11-18): 2008–, `committee_summary` per committee with `webk` only for a measure it leaves blank, candidate figures the sum of credited committees; 1996–2006, `webk` and `weball`; 1980–1994, `weball` only. Link the measurement's Decisions; do not restate its numbers. M1's first contract (the catalogue and CSV rule) lives in §3, not here |
| §5 Spending | M2 | NEU-2150, from NEU-2149's measurement | Payees cite ADR-0011; the payee ADR will be 0012 |
| §6 Outside spending | M3 | NEU-2163, from NEU-2162's measurement | Builds on v1 §4's `independent_expenditure` (NEU-2057) |
| §7 Leadership PACs and lobbyist bundling | M4 | NEU-2173, with its own measurement | The milestone ends with NEU-2180's backfill, which also empties §2's older-builds list |

### §8 Public dataset

- Every silver table this project adds joins the dataset under `v1/`, as an additive change: a new table directory, a `CHANGELOG.md` entry, no `v2/`.
- The milestone's **spec ticket** adds the table to v1 spec §9's table list.
- The **silver ticket** that builds the table adds it to the dataset in the same PR: `DATASET_TABLES` in `publish/dataset.py`, its column descriptions in `docs/dataset/columns.yaml`, `schema/<table>.json` by `task dataset:schema`, a `docs/dataset/CHANGELOG.md` entry, the README where it lists tables, and NEU-2352's list of tables a live build may lack. `tests/integration/test_dataset.py` already fails on a missing description or a stale schema.
- Until NEU-2180's backfill, a snapshot's manifest lists a new table with only the cycles whose live build has it (§2, older builds).
- A table that is context and in no total (M4's bundled contributions) is still published; its README entry says what it must not be added to.

### §9 Raw filings

A stub for M5: NEU-2181's spike decides whether and how to ingest FEC's daily `.fec` filings for what no bulk file carries (Schedule C and D detail, Form 5 and Form 9 contributors, Form 3L's named bundlers), **and whether paper-filed reports are part of that**. NEU-2206 (recovering itemized receipts the bulk files omit) follows it. Filled by NEU-2181's outcome.

### §10 Milestones

The five milestones, one line each, as v1's §14: outline here, detail in Linear.

## 3. Other files in the PR

- **Root `CLAUDE.md`**, two lines:
  - Under `## Linear`, after the P-NEU-105 line: `Project: P-NEU-107 "fundlens: every FEC dollar" (initiative I-16)`.
  - Under `## Docs`, after the v1 project spec line: the new spec's path, as the shared reference for P-NEU-107's tickets, read with the v1 spec.
- **`CONTEXT.md`**: the **File catalogue** entry under Data tiers, already in the working tree from this session. Commit it with the PR; use the term (not "file list" or "registry") throughout the spec.
- No ADR. The older-builds rule is temporary and removed by NEU-2180, so it fails the hard-to-reverse test.

## 4. Linear

### 4.1 Already done in this session (2026-11-18)

- **M1 milestone**: the precedence contract rewritten per the measurement; `webl` and `candidate_summary` named as not read.
- **Project description**: `webl` dropped from M1's file list; "ADR 0010" corrected to 0011.
- **NEU-2142**: retitled without `webl`; three files, not four; headers vendored from FEC's file descriptions, since FEC publishes none; definition of done adjusted to match.
- **NEU-2150**: ADR numbers corrected (organizations 0011, payee ADR 0012).
- **NEU-2352** created; **NEU-2180** gained the checkbox that empties the list, and is blocked by NEU-2352.

### 4.2 For `/implementit`

- After reading FEC's page: where a first cycle in §3 differs from a Linear milestone or ticket text (expected: `ElectioneeringComm`, M3 says 2008), patch that text and say so in the PR description.
- Tick this ticket's definition-of-done boxes as each is verified.

## 5. Definition of done

- [ ] `docs/specs/fundlens-every-fec-dollar-project-spec.md` is merged with §1–§3 and §8 complete, §4–§7 and §9 as stubs naming the tickets that fill them, each of §4–§7 carrying its milestone's shared contracts, and §10 listing the five milestones.
- [ ] §3's read table gives each file's format, URL pattern and first cycle as FEC's bulk-data page states them, with the page's access date, and `webl` is not in it.
- [ ] Every file on FEC's bulk-data page on the access date is in §3's read table, in its not-read table with a reason, or among v1's six.
- [ ] §2 states the older-builds rule and names NEU-2352 and NEU-2180.
- [ ] Root `CLAUDE.md` names the spec and P-NEU-107; `CONTEXT.md` defines **File catalogue**.
- [ ] Any Linear text that §3's verified first cycles contradict is patched.

## 6. Out of scope

- Any milestone's table design, columns, gold fields or glossary terms (NEU-2141, 2150, 2163, 2173).
- Any change to `fundlens.fec.files`, the extractor or the dataset publisher (NEU-2138, NEU-2142, NEU-2352).
- Amending v1 spec §9: each milestone's spec ticket does that for its own tables.
- Measuring any file. §3 records what FEC's page says, not what the files hold.
