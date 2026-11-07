# NEU-2132 — Classify blank-entity-type organization gifts into `organization_receipt`, out of `contribution` and resolution

**Ticket:** [NEU-2132](https://linear.app/neuroticsasquatch/issue/NEU-2132) · **Milestone:** M3.5 Organization money · **Parent story:** NEU-2128
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §4 (the `04_contribution.sql` entity-type bullet, the `08_organization_receipt.sql` rules, the PAC/COM/CCM/PTY name-match rule), §6.1, §6.5–§6.6, §6.11 · **Glossary:** `CONTEXT.md` (Organization, Organization receipt, Organization key) · **ADRs:** 0004 (earmarks count once), 0005 (overrides in git, crosswalk in Postgres), 0011 (organizations are grouped, not resolved)
**Measurement:** `docs/measurements/organization-money-2024.md` (Q5 the classifier, Q6 blank rows, Decisions, "For NEU-2132")
**Blocked by:** NEU-2131 (Done, PR #89). **Blocks:** NEU-2136 (2024 production run), NEU-2060 (the M4 backfill).

Planned 2026-11-05. `/implementit NEU-2132` produces **one PR**: the classifier in `resolve.normalize`, four silver files, one new check, the fixture and its expectations, the override runbook, and the spec and ADR amendments in §2.6. Where the Linear ticket and this spec differ, this spec wins (the ticket's `fundlens overrides check` and "dev stack" items are corrected here, §1.1).

## 1. What and why

FEC fills `ENTITY_TP` only on electronic filings since April 2002. `sql/silver/04_contribution.sql` coalesces a blank one to `IND`, in both the `individual` CTE and the 15J `jfc_line` view, so on paper filings and in every cycle before 2002 an organization's gift is counted as individuals' money, its name becomes a contributor key, and resolution can make it a donor or merge it into a person. In 2024 that is 70 of 343 blank rows ($233,837 of $332,584; `GROUNDSWELL ACTION FUND` and `TIDES ADVOCACY` are live donor pages today). In 1998 and 2000 every row is blank: the measurement's rule calls 25,980 rows ($166.7M) and 44,598 rows ($389.0M) organizations, Philip Morris, Pfizer, Bell Atlantic and CWA-COPE among them, and the M4 backfill (NEU-2060) would write them into individuals' totals for every cycle since 1980.

This ticket puts the measurement's picked rule, **V8**, where the spec already says it goes: a pure Python `is_organization_name` in `resolve.normalize`, registered with DuckDB like the other normalizers and evaluated once per distinct name. A blank-type `indiv` row it calls an organization leaves `contribution`, `jfc_line` and `contributor`, and lands in `organization_receipt` with `classified = true`, or, when its name names exactly one `cm` committee, in `committee_transfer` as that committee's gift (§1.1). A filled entity type is never second-guessed.

### 1.1 Decisions this spec pins (grilled 2026-11-05)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| A classified blank row whose name names exactly one `cm` committee | **A `committee_transfer` receipt from that committee**, by NEU-2131's name-match rule extended to classified blank rows: same name key, same exclusions (not its own recipient; not when `oth` already holds the gift under that committee's id with the same recipient, amount and date). The name match is gated on the classifier: a blank row the classifier calls a person is never routed by name. A classified row naming **none** is an organization receipt; one naming **several** is an organization receipt too (the money is a non-individual's and is counted once, on its recipient; unlike a PAC-typed row, nothing says it is a committee's). Spec §4 and ADR 0011 (f) are amended in this PR (§2.6). | The spec as written (every classified row an organization receipt): the measurement's Q6c shows the RNC, DNC, NRCC, DSCC non-federal accounts and party dinner committees among the largest 1998/2000 hits; counting them as organizations breaks the milestone contract that a committee's money is committee money. Deferring the routing to NEU-2060: the backfill is exactly where the misroute would land first. |
| An override naming a key the classifier has moved out of `contribution` | **No code change.** `overrides.check` keeps stopping `resolve --full` (and `recluster`) before training on an unknown key, as today. `docs/runbooks/adding-an-override.md` gains the cause and the fix: remove the entry in a PR. There is no `fundlens overrides check` command, and none is added. | A warning instead of a stop: weakens the guard that catches a mistyped key. A new `fundlens overrides check` command: a CLI surface for one rare case the run already reports in minutes. |
| Verifying the classifier on real 2024 data | **A read-only query on prod's `pipeline` container**, as NEU-2129 ran its measurement: the Python `is_organization_name` beside the measurement's SQL V8 over 2024 `indiv`'s distinct names, asserting they agree on every name with at least one token; then the blank counted rows the Python rule classifies (expected 70 rows, $233,837, at most $84,694 to one committee, C90020454) and how many of those name exactly one `cm` committee. Nothing is transformed, resolved or written. The per-candidate `total_individual` check moves to NEU-2136's runbook (commented there at planning). | The ticket's "2024 transform and resolve on the dev stack": the dev stack has no 2024 bronze (NEU-2129's spec). A full 2024 transform on prod inside this ticket: hours of pipeline time writing a build NEU-2136 then rewrites. |
| Donor ids whose every key is classified away | **Their `app.crosswalk` rows stay** (ids are never reused; `resolve.crosswalk` already keeps a row for a key a run did not cluster and writes no redirect for it). With no `contribution` or `jfc_attribution` line, gold has **no donor row** for the id after the next load, and `GET /v1/donors/<id>` answers **404**. No API, gold or redirect change. | A 410 Gone by consulting `app.crosswalk` for ids gold lacks: an API change for ids that were never a person. A $0 donor row as a 15J-only donor has: shows organizations as donors, which ADR 0011 forbids. |

Not a user decision, pinned here so the diff is predictable: the classifier is evaluated **once per distinct name**, in a temp table `04_contribution.sql` builds beside `contributor_name` and that `05_committee_transfer.sql` and `08_organization_receipt.sql` read later in the run (§2.2).

## 2. The deliverables, file by file

### 2.1 `src/fundlens/resolve/normalize.py` — `is_organization_name`

`is_organization_name(raw: str | None) -> bool`, a pure function, the measurement's V8 transliterated:

- **Tokenize** a string by uppercasing it, deleting periods and apostrophes (`L.L.C.` is `LLC`, `O'BRIEN` is `OBRIEN`), replacing every other run of non-alphanumerics with one space and trimming.
- `None`, or a name that tokenizes to nothing, is **not** an organization: the row stays what it is today. (The measurement's SQL would call an empty string an organization by the no-comma rule; no counted 2024 row is known to have one, and the prod query in §4 reports any disagreement on such names separately.)
- A name is an organization when **any** of these holds:
  1. **No comma** in `raw`: `FUTURE FORWARD USA ACTION`, ` UPDIKE`, `LOFTUS`.
  2. The **last token** of the whole tokenized name is a strict legal suffix, `STRICT_LEGAL_SUFFIXES = {INC, LLC, CORP, LTD, LLP, PLLC, INCORPORATED, CORPORATION, LIMITED}`: `LEAGUE OF CONSERVATION VOTERS, INC.`, `ACME HOLDINGS, L.L.C.`, `LARSON, BEV MS. LLC`. Not `CO`, `COMPANY`, `PC`, `LP`: they end people's names.
  3. Some **comma-separated segment** of `raw`, tokenized the same way, holds **two tokens or more** and one of them is an organization word, `ORGANIZATION_WORDS = {UNION, INTERNATIONAL, INTL, LEAGUE, FEDERATION, PARTNERSHIP, PARTNERS, INSTITUTE, INDUSTRIES, SOCIETY, HOSPITAL, SCHOOL, ASSN, FUND, COALITION, ENTERPRISES}`: `NEA ADVOCACY FUND, ASSOCIATION`, `LEAGUE-PASCUAL, JAMES` (the hyphen splits the segment into two tokens). A word standing alone in its segment does not count: `BANK, LISSY`, `WOOTEN, COUNCIL`, `NATION, CHEROKEE` are people by this rule (`COUNCIL`, `NATION`, `BANK` are not in the list at all).
- Otherwise not an organization: `COX, JOHN T. MR. III PC`, `PERRETT, LP`, `WEITZ & LUXENBERG, P.C.` (an organization the rule misses; a false negative leaves the row where it is today).

Both frozensets are module constants with a comment naming the measurement (Q5, V8: 99.66% row precision, 97.99% row recall on 2024's filled types) so a later change is measured, not guessed. The docstring says what the rule is for and that a filled entity type never reaches it.

`register` adds `("is_organization_name", is_organization_name, "BOOLEAN")` with the same `null_handling=SPECIAL`, so a NULL name is `false`. The module docstring's `organization_key` paragraph gains a sentence on the classifier.

`tests/unit/test_normalize.py`: a parametrized `test_is_organization_name` over every name in the measurement's Decisions table, with the call the rule makes (not what the name really is): `BANK, LISSY` F, `WOOTEN, COUNCIL` F, `NATION, MARK` F, `COX, JOHN T. MR. III PC` F, `PERRETT, LP` F, `LEAGUE-PASCUAL, JAMES` T, `LARSON, BEV MS. LLC` T, `SMITH, PATRICIA J LLC` T, ` UPDIKE` T, `LOFTUS` T, `TRIBAL COUNCIL, PRAIRIE ISLAND` F, `NATION, CHEROKEE` F, `NEA ADVOCACY FUND, ASSOCIATION` T, `ACME HOLDINGS, L.L.C.` T, `FUTURE FORWARD USA ACTION` T, `LEAGUE OF CONSERVATION VOTERS, INC.` T, `WEITZ & LUXENBERG, P.C.` F; plus the fixture's `ACME WIDGETS INC` T, `BANKS, JOHN` F, `OLD LINE REPUBLICAN COMMITTEE` T, and `None`, `""`, `" . "` F. `test_the_normalizers_are_duckdb_functions_once_registered` gains `is_organization_name('ACME WIDGETS INC')` and `is_organization_name(NULL)`.

### 2.2 `sql/silver/04_contribution.sql`

- **The classification table.** After `contributor_name` is built: `CREATE TEMP TABLE organization_name_class AS SELECT raw, is_organization_name(raw) AS is_organization FROM contributor_name;` — one Python call per distinct name, over names `normalize_name` has already parsed, so the cost is a fraction of what the run already pays. It **outlives this file**, as the `contributor_*` tables do: `05_committee_transfer.sql` and `08_organization_receipt.sql` read it. The header comment says so.
- **`jfc_line`.** Today's view (15J, memo, IND or blank, filer in `cm`) becomes `jfc_line_reported`, which `contributor_value` reads so the names of every 15J line are in `contributor_name`. `jfc_line` is then defined, after `organization_name_class`, as `jfc_line_reported` minus the rows whose entity type is blank and whose `NAME` is in `organization_name_class` with `is_organization` true. `06_jfc_attribution.sql` keeps reading `jfc_line` and does not change. A classified 15J line is in no table: it was evidence about a person, and it is not about one.
- **`individual`.** The entity-type predicate becomes: `ENTITY_TP` trimmed is `IND` or `CAN`, **or** it is blank and `NAME` is **not** a name `organization_name_class` calls an organization (a semi-join whose right side is the small class table; `indiv` is still scanned once). A filled type other than IND/CAN is unchanged: ORG, PAC, COM, CCM, PTY never enter.
- The header comment's "a blank one is an individual" paragraph is rewritten: a blank one is an individual unless the classifier (`resolve.normalize.is_organization_name`, the measurement's V8) calls the name an organization; a filled type is never second-guessed.

Nothing else in the file changes: contributor keys, conduits, refunds, handoffs and self-funding are untouched.

### 2.3 `sql/silver/05_committee_transfer.sql`

The `indiv`-side name-match CTE (today `WHERE trim(indiv.ENTITY_TP) IN ('PAC', 'COM', 'CCM', 'PTY')`) also takes a counted row whose entity type is blank and whose `NAME` is in `organization_name_class` with `is_organization` true, with a blank `OTHER_ID`, whose name key names exactly one `cm` committee that is not its recipient, and that `oth` does not already hold as that committee's gift (same recipient, `OTHER_ID` = the named committee, same amount and date). The `oth` side does not change: a blank entity type in `oth` is not classified (spec §4). The header comment gains a sentence; `silver_committee_transfer_name_match_twin.sql` already covers the twin rule for whatever the CTE emits.

### 2.4 `sql/silver/08_organization_receipt.sql`

The `individual` CTE's `trim(ENTITY_TP) = 'ORG'` becomes: `ORG`, **or** a blank entity type whose `NAME` `organization_name_class` calls an organization **and** whose name key does not name exactly one `cm` committee other than its recipient (with a blank `OTHER_ID`), by §2.3's rule. (Amended at implementation: excluding only the `SUB_ID`s already in `committee_transfer` would let a row §2.3 drops for its `oth` twin fall into `organization_receipt` and count the gift twice; excluding by the rule puts a twin-dropped row in neither table.) Every other filter (memo, 24T, conduit side, recipient in `cm`) applies as today. The `classified` output column becomes `nullif(trim(kept.ENTITY_TP), '') IS NULL` (true exactly on the classified rows; the `oth` rows are all ORG, so false). `entity_type` stays as filed (NULL or blank). `organization_key` applies unchanged (`organization_key('LOFTUS')` is `LOFTUS`). The header's "every row here is false" sentence goes.

**New check** `sql/checks/silver_organization_receipt_classified.sql`: returns the rows where `classified` disagrees with the entity type (`classified` true with a filled `entity_type`, or false with a blank one), so the flag can never drift from the rule. A unit test in `tests/integration/test_transform.py` beside the three NEU-2131 check tests fails it on a hand-broken row. `silver_organization_receipt_disjoint.sql` needs no change and must still pass: a classified row is in `committee_transfer` or `organization_receipt`, never both, and never in `contribution`.

### 2.5 Fixture (`tests/fixtures/fec/2024/`), `expected.yaml`, `tests/unit/test_fec_fixture.py`

New `indiv` rows, each with a **blank `ENTITY_TP`**, in a commented block "Blank entity types (NEU-2132): pre-2002-style rows FEC filed without a type":

| Row | Name | To | Expected |
|---|---|---|---|
| a | `ACME WIDGETS INC` | C00800105, 15, a few thousand dollars | `organization_receipt`, `classified = true`, key `ACME WIDGETS`; in no `contribution`, `contributor` or donor row |
| b | `BANKS, JOHN`, with ZIP, employer, occupation | any candidate committee, 15 | a counted `contribution` and a new contributor key and donor: the classifier must leave him an individual |
| c | `OLD LINE REPUBLICAN COMMITTEE` | a committee in `cm` other than C00800104, with an amount and date that match **no** `oth` 18K from C00800203 (the fixture has one to C00800104, $5,000 on 08052024) | a `committee_transfer` receipt from C00800203 by the extended name match; in `name_matched`; in neither `contribution` nor `organization_receipt` |

And one `oth` row: a blank-type **15J memo line** with an organization name (`CHESAPEAKE STEEL INC`, filed by a participant in `cm`, `OTHER_ID` blank), expected in no table: `jfc_attribution` stays at its count.

Row b is a counted, dated contribution, so `tests/fixtures/dime/contribDB_2024.csv` gets a DIME row for it and `expected.yaml`'s `validation` and `donors` sections carry him (`test_every_counted_contribution_has_exactly_one_dime_label`, `test_each_donor_grouping_is_its_contributions_and_one_dime_donor`).

`expected.yaml`: `rows` (indiv +3, oth +1), `silver` (contribution +1, committee_transfer +1, organization_receipt +1, contributor +1, jfc_attribution unchanged), `contributions.dropped_not_individual` (redefined in the comment and the tally as "rows that are no individual's by type or by the classifier"), `contributions.total_amount`, `organization_receipts.keys`/`by_key`/`by_committee`/`total_amount` (row a), a new `organization_receipts.classified: [<row a's SUB_ID>]`, `name_matched` (row c → C00800203), the recipient's `total_from_committees`, and the rule comments at the top (the blank-type sentence of the first bullet, the organization-receipt bullet, the name-match sentence). The header comment's "Every number here is checked against the fixture CSVs" stays true: `test_fec_fixture.py`'s `counts()`, `organization_receipts()`, `name_matched_gifts()` and `attributions()` learn the classifier by importing `normalize.is_organization_name`, and a new assertion checks `organization_receipts.classified` is exactly the blank-type receipts.

`tests/integration/test_transform.py`: the organization-receipt assertions check `classified` is true on row a and false elsewhere, that row a's `SUB_ID` is in no `contribution`/`contributor` partition and row c's is in `committee_transfer`; the resolve/load tests need no new case beyond `distinct_donors` moving with row b.

### 2.6 Docs

- **Project spec §4.** The `04_contribution.sql` entity-type bullet: after "in which case the row is an organization receipt with `classified = true`", add "or, when its name key names exactly one `cm` committee (not its recipient, no `oth` twin), a `committee_transfer` receipt from that committee by the name-match rule below (NEU-2132)". The `08_organization_receipt.sql` first bullet: "a blank `ENTITY_TP` the classifier calls an organization (`classified = true`) and the name match did not route to `committee_transfer`". The name-match rule: "A counted `indiv` row with entity type PAC, COM, CCM or PTY, **or a blank entity type the classifier calls an organization (NEU-2132)**, and a blank `OTHER_ID`…"; and after "Rows naming several committees or none are dropped": "a classified blank row naming several or none is an organization receipt instead: nothing says it is a committee's".
- **ADR 0011**, decision (f): append "A classified name that names exactly one `cm` committee is that committee's gift by (d); one naming several or none is an organization receipt (NEU-2132)."
- **`docs/runbooks/adding-an-override.md`**: the Facts table's "What stops a run" row gains "a key that is in no cycle's silver — including one the blank-entity-type classifier (NEU-2132) now calls an organization, so its rows are organization receipts and the key no longer exists; the fix is a PR removing the entry". Step 1's "No rows" paragraph gains the same cause.
- **`CONTEXT.md`**: no change. Organization, Organization receipt and Organization key already say what a blank-type organization row is; the classifier is implementation.

### 2.7 Out of this PR, done at planning

- A comment on NEU-2136: its runbook verifies that no candidate's `total_individual` moved by more than the classified dollars of their committees (2024 ceiling: $233,837 in all, $84,694 to one committee), and that `organization_receipt`'s 2024 count is 18,336 plus the classified blank rows not routed to `committee_transfer` (70 before routing).
- A comment on NEU-2132 pointing here, correcting the `fundlens overrides check` and dev-stack items.

## 3. Acceptance criteria

- [ ] `test_normalize.py` covers `is_organization_name` on every name in the measurement's Decisions table with the call V8 makes, plus the fixture's three names and the empty cases; the DuckDB registration test covers it.
- [ ] On the fixture: `ACME WIDGETS INC` is in `organization_receipt` with `classified = true` and in no `contribution`, `contributor` or donor row; `BANKS, JOHN` is a contribution with a contributor key and a donor; `OLD LINE REPUBLICAN COMMITTEE` (blank type) is a `committee_transfer` receipt from C00800203 and in neither other table; the blank-type organization 15J line is in no table.
- [ ] Every row of `organization_receipt` with a filled entity type has `classified = false` and every blank-type row `classified = true`: `silver_organization_receipt_classified.sql` passes on the fixture and fails on a hand-broken row in its unit test.
- [ ] `silver_organization_receipt_disjoint.sql` and `silver_committee_transfer_name_match_twin.sql` still pass; no row is in two of `contribution`, `committee_transfer`, `organization_receipt`.
- [ ] Every existing fixture row's table and amount is unchanged: the `expected.yaml` diff touches only the new rows' counts, keys, totals, the recipient's `total_from_committees`, the new donor and his DIME label, and the rule comments.
- [ ] The read-only prod query (§4) is run and its output pasted into the PR: Python and SQL V8 agree on every 2024 distinct `indiv` name with at least one token; the blank counted rows classified number 70, $233,837, at most $84,694 to one committee; and the count of those naming exactly one `cm` committee is recorded.
- [ ] The runbook, spec §4 and ADR 0011 carry the amendments in §2.6; `CONTEXT.md` is untouched.
- [ ] `task format`, `task lint` (ruff, pyright strict) and the full `task test` pass in the container.

## 4. The prod verification query

On `music-box-dancer`, in `tmux`, with no transform or resolve running and nothing merged to `main` mid-run (a deploy restarts `pipeline`). The image must carry this branch's `normalize.py`: either deploy the PR's branch to the `fundlens` resource temporarily, or `docker cp` the one file into the container's `site-packages` for the session and restore it after (say which in the PR). Reuse NEU-2129's setup script (register 2024 `indiv` and `cm` through `transform.runner`'s `unzip_bulk` and `register_bulk`, work dir under scratch, deleted after), then `normalize.register(con)` and:

1. `names`: `SELECT DISTINCT NAME FROM indiv WHERE MEMO_CD IS DISTINCT FROM 'X' AND TRANSACTION_TP IS DISTINCT FROM '24T'`, with `is_organization_name(NAME) AS py` and the measurement's V8 SQL (`flag("V8")` from Q5, verbatim) `AS sql`. Report `count(*) FILTER (WHERE py <> sql)`, split by whether the tokenized name is empty; the non-empty count must be 0.
2. Blank counted rows: rows, net dollars, and the same by `CMTE_ID` (top 10) where `py`; expected 70, $233,837, C90020454 at $84,694.
3. Of those, rows whose name key (`regexp_replace(upper(NAME), '[^A-Z0-9]', '', 'g')`) matches exactly one `cm` name key other than their recipient: rows and dollars. Recorded for NEU-2136.

Nothing is written to silver, gold, markers or Postgres.

## 5. Out of scope

- Reclassifying rows whose entity type is filled; classifying blank-type `oth` receipts (one row, $9,609 in 2024; spec §4).
- A learned classifier, or any change to V8's lists: the rule is measured, and a change goes back through a measurement.
- Gold (`total_from_organizations`, `committee_top_organization`: NEU-2133), API, pages, the 2024 production run and FEC cross-check (NEU-2136), the backfill (NEU-2060).
- A methodology page: the frontend has none yet; the rule's explainability is the measurement document and spec §4.
- Any change to `resolve.crosswalk`, `resolve.overrides`, the donor API or redirects (§1.1).
