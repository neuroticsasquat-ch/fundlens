# NEU-2129 — Measure 2024 organization money in `indiv` and `oth`, and test a blank-entity-type organization classifier

**Ticket:** [NEU-2129](https://linear.app/neuroticsasquatch/issue/NEU-2129) · **Milestone:** M3.5 Organization money · **Parent story:** NEU-2128
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §4 (the `04_contribution.sql` rules, line 166), §6.11 (the 1,950 non-IND 15J lines) · **ADRs:** 0002 (R2 is the store of record), 0004 (earmarks count once)
**Blocks:** NEU-2130 (glossary, spec amendment, ADR), and through it NEU-2131 (silver `organization_receipt`) and NEU-2132 (the classifier). **Related:** NEU-2073 (refund sign rule), NEU-2070 (unknown recipients), NEU-2124 (JFC transfers with blank `OTHER_ID`).

Planned 2026-11-04. `/implementit NEU-2129` produces **one PR**: `docs/measurements/organization-money-2024.md`, written from a manual run on `music-box-dancer` (§4). No change to `sql/`, `src/` or the frontend.

## 1. What and why

fundlens drops every gift from an organization that is not a committee. `sql/silver/04_contribution.sql` keeps `indiv` rows whose entity type is IND, CAN or blank (blank is coalesced to IND); `05_committee_transfer.sql` keeps an `oth` receipt only when its giver is a `C`-prefixed `OTHER_ID` or, when that is blank, a uniquely named designation-J committee. A corporation's gift to a super PAC, a union's to a party account, and a trade association's to anything fall through both, so a super PAC funded by corporations looks nearly empty. The only measured figure is the spec's 1,950 non-IND 15J memo lines, measured once (NEU-2072) with queries that did not survive.

The M3.5 tickets cannot fix their rules until the money is counted: how much, under which entity and transaction types, to which committee types, how much of it is double-filed, and whether a blank entity type can be told from a person by name alone. This ticket measures all of that on 2024 and writes the figures, the queries and two decisions into one document. It changes nothing in the pipeline.

### 1.1 Decisions this spec pins (grilled 2026-11-04)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Where the queries run | **Prod's `pipeline` container** on `music-box-dancer`, as `docker exec -i … python - <<'PY'` scripts that import `fundlens.transform.runner` and reuse `unzip_bulk`, `register_bulk` and `connect`. The views `indiv`, `oth` and `cm` carry the vendored column names and catalogue types, exactly as the transform sees them. | Hand-written `read_csv` with its own column list: duplicates the catalogue and drifts from it. The dev stack: it has no 2024 bronze, and a 70M-row `indiv` on a laptop is a day of work for nothing the prod box cannot do in minutes. |
| The 1998 and 2000 files | **`fundlens extract --cycle <c> --file indiv`** for each, into R2 bronze. Writes no marker; the M4 backfill (NEU-2060) needs the same zips. `unzip_bulk` then reads them like 2024's, downloading to the work dir since only the current cycle's zip stays on local disk. | Downloading to scratch outside the pipeline: a second download path, and the backfill fetches them again. Skipping the check: the third definition-of-done item is the only pre-2002 evidence NEU-2132 will have. |
| Classifier scoring | **Positives are ORG, PAC, COM, CCM and PTY; negatives are IND and CAN**, on 2024 non-memo, non-24T `indiv` rows with a filled entity type. Precision and recall are reported **by rows and by dollars**, and ORG-only figures are reported beside them. A rule is **picked** when it is the highest-recall variant with **precision ≥ 99% by rows**. | ORG-only positives: PAC and COM names in `indiv` are what the classifier meets in old cycles, and the rule must not call them people. Choosing by eye: the pick must be defensible on the methodology page. Precision first because a false positive moves a person's money out of individuals' totals and out of resolution; a false negative leaves an organization where it is today. |
| PAC/COM/CCM/PTY rows with no committee ID | **Join `committee_transfer` only if ≥ 95% of their dollars name exactly one `cm` committee** by the normalized name key `04_contribution.sql` and `05_committee_transfer.sql` use (uppercase, letters and digits only). Below the bar they are dropped, and the document records the dollars lost. Either way the milestone contract holds: never counted twice. | Joining whenever the remainder is small in absolute dollars: the rule would depend on the cycle's size. Always dropping: throws away money that a name match recovers cleanly when the match rate is high. |
| The super PAC cross-check | **The five `cm.CMTE_TP` O or U committees with the most ORG-typed `indiv` dollars** in this measurement, compared against FEC's PAC summary bulk file **`webk24.zip`** (`TTL_RECEIPTS`, `INDV_CONTRIB`, `OTHER_POL_CMTE_CONTRIB`), downloaded into the work dir with its date recorded and **not** added to `fec.files`. fundlens's side is the live gold `committee_cycle.total_individual + total_from_committees`, by `psql`. | fec.gov committee pages by hand: not re-runnable, and the page's totals mix line types. Cataloguing `webk`: the catalogue is what `extract` downloads weekly, and nothing in the pipeline reads it. |
| Glossary and ADR | **None here.** NEU-2130 owns the `CONTEXT.md` terms (Organization, Organization key) and ADR 0010, written from this document's numbers. This spec uses "organization" in NEU-2128's sense: a giver that is neither an individual nor a committee, identified only by its reported name. | Adding the terms now: NEU-2130 would then amend a glossary entry this ticket guessed at before the numbers were in. |

## 2. Definitions used in the document

- **Counted `indiv` row:** `MEMO_CD IS DISTINCT FROM 'X'` and `TRANSACTION_TP IS DISTINCT FROM '24T'`, the same two filters `04_contribution.sql` applies before its entity-type rule. Earmark conduit rows and gifts to committees missing from `cm` are *not* filtered out: they are reported as their own rows so NEU-2131 can see what its inherited rules will drop.
- **Entity type:** `coalesce(nullif(trim(ENTITY_TP), ''), '<blank>')`, so blank is a visible bucket.
- **`oth` receipt:** `left(TRANSACTION_TP, 1) IN ('1', '3')` and `MEMO_CD IS DISTINCT FROM 'X'`, as `05_committee_transfer.sql` defines it. 15J and 16C rows are reported as their own lines, not excluded, because NEU-2131 excludes them and must know the size.
- **Giver status** of an `oth` receipt: `committee` (`OTHER_ID` trimmed starts with `C` and is in `cm`), `unknown id` (starts with `C`, not in `cm`), `non-committee id` (non-empty, not `C`-prefixed), `blank`.
- **Name key:** `regexp_replace(upper(NAME), '[^A-Z0-9]', '', 'g')`, the key both silver files compare names by.
- **Recipient group** from `cm.CMTE_TP`: `super PAC` (O, U), `party` (X, Y), `candidate` (H, S, P), `other` (everything else), `not in cm`.
- **Net dollars:** `sum(TRANSACTION_AMT)` as filed. The refund sign rule (NEU-2073) is silver's, not the measurement's; refund types (`^[24][0-9]Y$`) are reported as a separate row count and dollar figure so NEU-2131 can see what the rule will touch.

## 3. Preconditions

- Bronze 2024 `indiv`, `oth` and `cm` in R2 (they are; the live build is `20261103T175128Z`). The document records each zip's download date, which is its file name under `bronze/cycle=2024/<file>/`.
- No pipeline step running: the Sunday 03:00 scheduled run (spec §5.6), or any runbook in progress. The queries share the container's DuckDB memory limit (26 GiB) and must not race a transform. Do not merge anything to `main` while the run is in progress: a deploy restarts `pipeline` and kills the `docker exec` (see the project memory on mid-runbook merges).
- Free disk under `/data/fundlens/scratch` for the unpacked text files (2024 `indiv` is about 5 GB unpacked; `oth` and `cm` are small) plus 1998 and 2000 `indiv`.

## 4. The run

All on the VM, in `tmux`, using the `fl` helper from `docs/runbooks/first-run.md` to find the `pipeline` container. The document carries every block below verbatim, with its output.

### 4.1 Setup script

One Python heredoc, kept at the top of the document and pasted before each query block:

```python
from pathlib import Path
from fundlens import paths
from fundlens.fec.files import CATALOGUE
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import Limits, connect, register_bulk, unzip_bulk

settings = get_settings()
store = R2.from_settings(settings)
scratch = paths.scratch_dir(settings.data_dir)
work = scratch / "measure-organization-money-2024"
work.mkdir(parents=True, exist_ok=True)
con = connect(Limits.from_settings(settings), scratch)
for name in ("indiv", "oth", "cm"):
    register_bulk(con, CATALOGUE[name], unzip_bulk(store, 2024, CATALOGUE[name], data_dir=settings.data_dir, work=work))
```

The text files stay in `work` for the whole session, so later blocks skip the unzip and register the views from the existing paths. The 1998 and 2000 `indiv` files are unpacked into `work / "1998"` and `work / "2000"` and registered as `indiv_1998` and `indiv_2000` (rename the view after `register_bulk`, or register with a sub-connection). `work` is deleted at the end of the run.

Query shape: `connect` disables DuckDB's build-side optimizer (NEU-2076), so every join is written with the small table (`cm`, the name-key table, the classifier table) on the right. Nothing materializes `indiv`.

### 4.2 Queries and figures

Each is one SQL block in the document, dated, followed by its result table.

**Q1 — `indiv` by entity type and recipient group.** Counted rows grouped by entity type × recipient group: rows, net dollars, refund-type rows and dollars, distinct `CMTE_ID`s. One row per combination, with totals per entity type. A second cut, for ORG/PAC/COM/CCM/PTY only, by `TRANSACTION_TP`.

**Q2 — `oth` receipts whose giver is not a committee.** `oth` receipts grouped by giver status × entity type × `TRANSACTION_TP`: rows and net dollars. The `committee` status appears for scale; the other three are the organization candidates. 15J and 16C lines are visible by their `TRANSACTION_TP`. Also whether the receiving `CMTE_ID` is in `cm`.

**Q3 — PAC/COM/CCM/PTY rows without a committee ID.** From `indiv` counted rows and from Q2's `oth` set, the rows with those entity types and a blank `OTHER_ID`: rows and dollars split into *names exactly one `cm` committee* (name key matches one `CMTE_ID`), *names several*, *names none*. The decision line applies the 95% bar to the `indiv` and `oth` figures together, and states join or drop with the dollars on each side. A companion count: PAC/COM/CCM/PTY `indiv` rows whose `OTHER_ID` *is* a committee in `cm`: rows, dollars, and how many share a `SUB_ID` with an `oth` row (these are the committee gifts `committee_transfer` may already hold).

**Q4 — `indiv`/`oth` overlap.** For Q2's non-committee-giver receipts with an organization entity type: rows and dollars that (a) share a `SUB_ID` with an `indiv` row, (b) have a mirror in `indiv` (same `CMTE_ID`, name key, `TRANSACTION_AMT` and `TRANSACTION_DT`) under another `SUB_ID`, (c) neither. The document states which of (a) and (b) `organization_receipt` must dedupe on.

**Q5 — Classifier.** Built on distinct names, not rows: `CREATE TABLE name_class AS SELECT NAME, <variant flags> FROM (SELECT DISTINCT NAME FROM indiv WHERE …)`, each variant a DuckDB regular expression over the name key and over the uppercased, punctuation-stripped, space-tokenized name, so NEU-2132's Python `is_organization_name` is a transliteration. At least three variants:

- **V1** legal suffix as the last token: INC, LLC, CORP, CO, LTD, LLP, LP, PC, PLLC, INCORPORATED, CORPORATION, LIMITED, COMPANY.
- **V2** V1, or any whole-token organization word: UNION, ASSOCIATION, ASSN, ASSOC, COMMITTEE, FUND, PAC, TRIBE, NATION, COUNCIL, FEDERATION, PARTNERS, GROUP, BANK.
- **V3** V2 with the word list widened: TRUST, FOUNDATION, INSTITUTE, SOCIETY, LEAGUE, ALLIANCE, COALITION, ENTERPRISES, HOLDINGS, INDUSTRIES, INTERNATIONAL, INTL, PARTNERSHIP, CHURCH, SCHOOL, UNIVERSITY, HOSPITAL, CLUB.

The implementer may add variants (for instance, V2 minus a word that proves to be a surname) and must keep every variant tried. For each: a confusion matrix over counted 2024 rows with a filled entity type, by rows and by dollars, for positives = ORG/PAC/COM/CCM/PTY and again for positives = ORG only; precision and recall from both. Per variant, the false positives: the 30 IND/CAN names with the most dollars the rule calls organizations, and 30 drawn at random, each with its rows and dollars; and the false negatives: the 30 ORG names with the most dollars the rule misses. Also, for the picked rule, the words that produced false positives, each with its count (a person surnamed Bank; a person whose employer leaked into `NAME`). The pick follows §1.1: highest recall at ≥ 99% row precision. The document states the picked rule as the exact regular expressions and token lists, and lists the false-positive names NEU-2132's unit tests must cover.

**Q6 — Blank rows under the picked rule.** For 2024, 1998 and 2000: counted `indiv` rows with a blank entity type: rows and dollars in total, and rows and dollars the picked rule calls organizations, with the 50 hit names with the most dollars per cycle. The 2024 blank figure is the ceiling on what NEU-2132 can move in the live cycle; 1998 and 2000 are the sanity check for the backfill.

**Q7 — Five super PACs.** From Q1's ORG rows, the five O/U committees with the most ORG dollars. For each: `webk24` `TTL_RECEIPTS`, `INDV_CONTRIB`, `OTHER_POL_CMTE_CONTRIB` (file downloaded from `https://www.fec.gov/files/bulk-downloads/2024/webk24.zip` into `work`, column names from FEC's `data_dictionaries/webk_header_file.csv`, both dates recorded); live gold `total_individual` and `total_from_committees` (`pg -c "select … from gold.committee_cycle where cycle = 2024 and committee_id in (…)"`); this measurement's ORG `indiv` dollars and Q2 `oth` organization dollars for the committee; and the gap between FEC's total and fundlens's. A sentence explains what the gap still holds after organization money (unitemized receipts, loans, offsets), so the runbook ticket (NEU-2128 child 8) has a baseline.

### 4.3 The document

`docs/measurements/organization-money-2024.md` (new folder), in this order:

1. Header: run date, SHA of `main` the scripts ran against, container, the three 2024 zips' download dates and the 1998/2000 download dates, DuckDB limits in force.
2. §4.1's setup script.
3. Q1–Q7, each as: the question in one sentence, the SQL block, the result table, one or two sentences of reading.
4. **Decisions:** the PAC/COM/CCM/PTY join-or-drop line with the dollars on each side; the picked classifier rule with its precision and recall (rows and dollars, both positive sets), its false-positive word list and the test-case names; the dedupe key from Q4.
5. **For NEU-2130/2131/2132:** a short list of what each downstream ticket takes from here (the row count NEU-2131's definition of done is within 1% of; the classified-dollars-per-candidate ceiling NEU-2132 checks against, computed as part of Q6 for 2024 by `candidate` via the same `ccl` rule, or stated as the committee-level ceiling if that join is not worth doing here).

No `capacity.md` row: this is a measurement, not a pipeline step.

## 5. Acceptance criteria

- [ ] `docs/measurements/organization-money-2024.md` is merged; every figure is dated, every query is inline and runnable from the setup script, and each FEC file's download date is given.
- [ ] Q1–Q7 are all present with results; nothing is marked "to do".
- [ ] The join-or-drop decision for PAC/COM/CCM/PTY rows without a committee ID is stated with the ≥ 95% criterion applied and the dollars on each side.
- [ ] The picked classifier rule is stated as exact token lists and regular expressions, with precision and recall by rows and by dollars for both positive sets, at least three variants compared, the false-positive names listed, and 1998, 2000 and 2024 blank-row hit counts and dollars.
- [ ] The Q4 dedupe key `organization_receipt` must use is stated.
- [ ] 1998 and 2000 `indiv` zips are in R2 bronze (`r2ls bronze/cycle=1998/indiv/`); `/data/fundlens/scratch/measure-organization-money-2024` is removed; no silver, gold or marker was written.
- [ ] No change under `sql/`, `src/` or `frontend/` in the PR.

## 6. Out of scope

- Any change to `sql/`, `src/` or the glossary (NEU-2130 onward).
- Cycles other than 2024, beyond the 1998 and 2000 blank-row counts.
- Cataloguing `webk` or reading it in the pipeline.
- Deciding what gold shows (NEU-2130 fixes `total_from_organizations` and `committee_top_organization`).
- A learned classifier: the rule is a name pattern, by NEU-2132's design.
