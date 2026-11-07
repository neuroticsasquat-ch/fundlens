# NEU-2140 — Measure FEC's 2024 summary files against each other and against fundlens gold

**Ticket:** [NEU-2140](https://linear.app/neuroticsasquatch/issue/NEU-2140) · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Milestone:** M1 Reported totals · **Parent story:** NEU-2139
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §4 is not written yet (NEU-2137, Backlog); the milestone's **Shared contracts** stand in for it. v1 spec: §4 (the `ccl` credit rule, `04_contribution.sql`'s counted rows, `08_organization_receipt.sql`), §7.1 (`committee_cycle`, `candidate_cycle`) · **ADRs:** 0002 (R2 is the store of record), 0004 (earmarks count once), 0011 (organizations are grouped, not resolved)
**Blocks:** NEU-2141 (spec §4: `reported_total` columns, precedence, coverage), and through it NEU-2142 (catalogue and extract) and NEU-2143 (silver `reported_total`). **Related:** NEU-2136 (the 2024 organization-money run, whose step 9.3 handed this ticket three gaps), NEU-2129 (the measurement whose shape and setup this one reuses).

Planned 2026-11-05. `/implementit NEU-2140` produces **one PR**: `docs/measurements/summary-files-2024.md`, written from a manual run on `music-box-dancer` (§4), plus the Bug tickets §4.2 Q6 files in Linear. No change to `sql/`, `src/` or `frontend/`.

## 1. What and why

FEC publishes its own cycle-to-date figures for every candidate and committee: total receipts and disbursements, cash on hand, debts, loans, and individual money split into itemized and unitemized. fundlens shows none of them; it shows only what it sums from itemized rows. Milestone M1 adds the reported figures beside fundlens's, with `coverage = itemized / reported`. Its silver design (NEU-2141, NEU-2143) rests on four things nobody has measured:

1. **Grain and overlap.** Five files cover the same money at two grains: `weball` (candidates, 1980–), `webl` (House and Senate campaigns, 1996–), `webk` (PACs and parties, 1996–), `committee_summary_YYYY.csv` (every committee, 2008–) and `candidate_summary_YYYY.csv` (every candidate, 2008–; **added by this spec**, the ticket names four). Which rows each holds, how their keys relate, and which wins where, are unknown. The milestone contract's precedence (`committee_summary` over `webk`/`webl` over `weball`) is a guess this ticket confirms or amends.
2. **Candidate figures.** Whether a candidate's reported figures come from a candidate-grain file as filed or from summing the committees fundlens credits to the candidate (the v1 `ccl` rule, with handoffs and aliases).
3. **What `TTL_INDIV_CONTRIB` means.** FEC's description of `weball` does not say whether it includes unitemized money.
4. **Coverage today.** How far fundlens's itemized individual total sits from FEC's reported itemized figure for every 2024 committee, and why fundlens is *above* FEC for some. NEU-2136's run left three named gaps: Fairshake $43.4M under FEC with only 37 itemized gifts, MAGA Inc. $5.4M over, Senate Leadership Fund $34.6M over (net of refunds).

This ticket measures all four on 2024, repeats what it can on 2004 (where only `weball`, `webl` and `webk` exist), and writes the figures, the queries and the decisions into one document. It changes nothing in the pipeline.

### 1.1 Decisions this spec pins (grilled 2026-11-05)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| The files | **Five**: `weball24`, `webl24`, `webk24`, `committee_summary_2024.csv`, `candidate_summary_2024.csv`; and for 2004, `weball04`, `webl04`, `webk04`. All downloaded into the work dir with their `Last-Modified` recorded, **not** catalogued, **not** in bronze (NEU-2142 catalogues what this document recommends). | Four files as the ticket says: `candidate_summary` is FEC's own "candidate = sum of authorized committees" roll-up for 2008+ and carries the itemized/unitemized split `weball` lacks; the candidate-source decision cannot be made without it. |
| Where the queries run | **Prod's `pipeline` container** on `music-box-dancer`, as `docker exec -i … python - <<'PY'` scripts reusing `fundlens.transform.runner` (`connect`, `unzip_bulk`, `register_bulk`) and `fundlens.load.gold` (`_require_inputs`, `_register_silver`) so the live build's silver tables are DuckDB views exactly as gold reads them; live gold by `psycopg` on `settings.database_url`, read-only. | Re-deriving the credit rule, refund rule or counted-row filter in the measurement: it would drift from silver. The dev stack: no 2024 bronze or silver. |
| fundlens's side of coverage | **Both figures, reported side by side**: A = `committee_cycle.total_individual`; B = `total_individual + total_from_organizations`. Each against `INDV_ITEM_CONTB` (and, for context, `INDV_CONTB`). The document **decides which one NEU-2141's `coverage` uses**, with the numbers: Form 3/3X line 11(a)(i) counts every person who is not a committee, organizations included, so B is the like-for-like figure unless the measurement shows otherwise. | A alone, as the ticket says: at a super PAC it under-counts by every organization's gift and makes the coverage figure wrong by design. B alone: the decision is NEU-2141's to write down, and it needs A's numbers to show why. |
| The 2004 fundlens side | **A raw `indiv` sum, no silver written.** `fundlens extract --cycle 2004` puts 2004's catalogued files (`cm`, `cn`, `ccl`, `indiv`, `pas2`, `oth`) in R2 bronze, kept for the M4 backfill (NEU-2060) as NEU-2129 kept 1998 and 2000. DuckDB then sums counted `indiv` rows (§2) as the proxy for `total_individual`. No `silver/`, marker or gold is written for 2004. | Running the 2004 transform on prod: it writes silver partitions and a transformed marker for a cycle the backfill runbook owns. FEC files against each other only: the ticket's question is what pre-2008 pages can show, which needs a fundlens side. |
| Candidate comparison | **Whole population, 20 shown.** Every 2024 candidate in `weball` is compared (§4.2 Q3); the document reports the distribution of differences and a 20-row table picked by rule: the 2 largest by `TTL_RECEIPTS` in each of {H, S} × {I, C, O} (12), the 4 largest presidential, and the 4 largest House candidates with two or more P/A committees in `committee_summary`. | A hand-picked list of 20: the decision would rest on 20 rows and the pick would not be re-runnable. |
| Candidate-source decision rule | **2008 and later:** candidate reported figures are the **sum of the committees fundlens credits to the candidate** (`04_contribution.sql`'s `linked` rule over `candidate_committee_link` and `candidate.principal_committee_id`: P or A, principal first, lower `candidate_id`, aliases credited nothing) from `committee_summary`, **provided** that for ≥ 95% of candidates with at least one credited committee the summed `TTL_RECEIPTS` equals `candidate_summary.Total_Receipt` within 1%; **else** `candidate_summary` as filed. **Before 2008:** `weball` (`webl` for House and Senate only if Q3 and Q8 show it differs from `weball` for the same candidate), the only candidate-grain sources. The match rate and every mismatch are in the document. | `candidate_summary` always: Trump's 2024 campaign-turned-leadership-PAC (`C00828541`) and the Biden-to-Harris handoff (`C00703975`) would show FEC's attribution beside fundlens's itemized credit. Summing always: if FEC's roll-up disagrees with the sum for many candidates, the pages would show a candidate figure no FEC page shows, and nobody would know why. |
| Handed-off committees | **Measured, not decided.** A cycle-to-date summary row cannot be split at `handoff_date`. Q3 reports `C00703975`'s row under both Biden and Harris and the document states what each choice does to their figures; NEU-2141 decides. | Deciding here: it is a §4 contract, and `handoffs.csv` has one row. |
| The excess list | **Every 2024 committee whose fundlens itemized figure exceeds FEC's `INDV_ITEM_CONTB` by more than 1%, on measure A or B, no dollar floor.** Each gets §4.2 Q6's bulk diagnostics, a primary cause or `unexplained`, and the document lists them all. **One Bug ticket per distinct cause**, filed in the **v1 project (P-NEU-105)**, labelled `Bug` and `repo:fundlens`, related to NEU-2140, assigned to the user, in the three-heading format; the document names each ticket beside its cause. | A dollar floor: the user chose the DoD as written. Per-committee hand investigation: the diagnostics are SQL over all committees at once, so the count does not change the work. |
| `webk`/`webl` vs `committee_summary` precedence | **Confirmed numerically, not assumed.** `committee_summary` wins for 2008+ if it holds ≥ 99% of `webk`'s committees and agrees within $1 on `TTL_RECEIPTS`, `TTL_DISB` and `COH_COP` for ≥ 99% of the shared rows (Q2); every disagreement is listed with both `CVG_END_DT`s, so coverage lag is visible as the cause when it is. Below the bar the document says which file is right and why, and NEU-2141 amends the contract. | Taking the contract as given: the ticket's whole point is that the contract says "as the measurement ticket confirms". |
| Glossary and ADR | **None here.** NEU-2141 owns `CONTEXT.md`'s **Reported total**, **Itemized total**, **Coverage** and **Unitemized**, written from this document's numbers. This spec uses "reported" for FEC's summary figures and "itemized" for what fundlens sums from `contribution` and `organization_receipt`. | Adding the terms now: NEU-2141 would amend a definition this ticket guessed at before the numbers were in. |

## 2. Definitions used in the document

- **Reported figure:** a value from one of the five summary files, as filed, never netted or summed with itemized money (milestone contract).
- **Itemized figure:** live gold's `committee_cycle.total_individual` (measure A) or `total_individual + total_from_organizations` (measure B), build `20261105T205814Z` (the live build when this was planned; the document records the one it read). Both are net of refunds by silver's rule (`-abs(amount)` on `^[24][0-9]Y$`).
- **FEC's itemized individual figure:** `committee_summary.INDV_ITEM_CONTB`, Form 3/3X line 11(a)(i), gross of refunds (`INDV_REF` is line 20(a)); `INDV_CONTB` = `INDV_ITEM_CONTB + INDV_UNITEM_CONTB`. The document checks that identity holds.
- **Credited committee** of a candidate: `04_contribution.sql`'s `linked` rule, read from the build's silver `candidate_committee_link` and `candidate` (designation P or A, or the committee `candidate.principal_committee_id` names; principal first, then lower `candidate_id`; a candidate with `alias_of` set is credited nothing; a committee in `handoffs.csv` is reported under both candidates, see §1.1).
- **Counted `indiv` row (2004 proxy):** `MEMO_CD IS DISTINCT FROM 'X'`, `TRANSACTION_TP IS DISTINCT FROM '24T'`, `coalesce(nullif(trim(ENTITY_TP), ''), 'IND') IN ('IND', 'CAN')`, summed as `sum(TRANSACTION_AMT)` with refunds (`^[24][0-9]Y$`) as `-abs(TRANSACTION_AMT)`; 15C rows (candidate's own money) reported apart, as `self_funding` is. The 2004 proxy ignores the classifier, the earmark conduit rule and the name-match rule, and the document says so.
- **Key relations:** `weball`, `webl`, `candidate_summary` are keyed by `CAND_ID`; `webk`, `committee_summary` by `CMTE_ID`; `candidate_summary` and `committee_summary` carry `FEC_ELECTION_YR` / the cycle in the file name. Measures compared across files, by name in each:

| Measure | `weball` / `webl` (candidate) | `candidate_summary` (candidate) | `webk` (committee) | `committee_summary` (committee) |
|---|---|---|---|---|
| receipts | `TTL_RECEIPTS` | `Total_Receipt` | `TTL_RECEIPTS` | `TTL_RECEIPTS` |
| disbursements | `TTL_DISB` | `Total_Disbursement` | `TTL_DISB` | `TTL_DISB` |
| cash on hand, end | `COH_COP` | `Cash_On_Hand_COP` | `COH_COP` | `COH_COP` |
| cash on hand, start | `COH_BOP` | `Cash_On_Hand_BOP` | `COH_BOP` | `COH_BOP` |
| debts owed by | `DEBTS_OWED_BY` | `Debt_Owed_By_Committee` | `DEBTS_OWED_BY` | `DEBTS_OWED_BY_CMTE` |
| debts owed to | — | `Debt_Owe_To_Committee` | — | `DEBTS_OWED_TO_CMTE` |
| individual, total | `TTL_INDIV_CONTRIB` | `Individual_Contribution` | `INDV_CONTRIB` | `INDV_CONTB` |
| individual, itemized | — | `Individual_Itemized_Contribution` | — | `INDV_ITEM_CONTB` |
| individual, unitemized | — | `Individual_Unitemized_Contribution` | — | `INDV_UNITEM_CONTB` |
| other committees | `OTHER_POL_CMTE_CONTRIB` | `Other_Committee_Contribution` | `OTHER_POL_CMTE_CONTRIB` | `OTH_CMTE_CONTB` |
| party committees | `POL_PTY_CONTRIB` | `Party_Committee_Contribution` | — | `PTY_CMTE_CONTB` |
| candidate's own | `CAND_CONTRIB` | `Cand_Contribution` | `CAND_CONTRIB` | `CAND_CNTB` |
| candidate loans | `CAND_LOANS` | `Cand_Loan` | `CAND_LOANS` | `CAND_LOAN` |
| other loans | `OTHER_LOANS` | `Other_Loan` | `TTL_LOANS_RECEIVED` − `CAND_LOANS` | `OTH_LOANS` |
| transfers in | `TRANS_FROM_AUTH` | `Transfer_From_Other_Auth_Committee` | `TRANS_FROM_AFF` | `TRANF_FROM_OTHER_AUTH_CMTE` |
| transfers out | `TRANS_TO_AUTH` | `Transfer_To_Other_Auth_Committee` | `TRANF_TO_AFF` | `TRANF_TO_OTHER_AUTH_CMTE` |
| individual refunds | `INDIV_REFUNDS` | `Individual_Refund` | `INDV_REFUNDS` | `INDV_REF` |
| coverage end | `CVG_END_DT` | `Coverage_End_Date` | `CVG_END_DT` | `CVG_END_DT` |
| coverage start | — | `Coverage_Start_Date` | — | `CVG_START_DT` |

Column names are from FEC's file descriptions, read 2026-11-05 (all candidates; current campaigns House and Senate; PAC and party summary; committee summary; candidate summary). The document re-reads them on its run date and records any difference. The zips have no header row; the CSVs have one.

## 3. Preconditions

- Bronze 2024 `indiv`, `oth`, `cm`, `cn`, `ccl` in R2 (download date `2026-10-31`, the live build's) and the live build's silver partitions (`_require_inputs` downloads any the local cache lacks).
- Live gold is `20261105T205814Z` or later; the document records `gold.meta.build_id` and the cycle's source dates. The summary files are rebuilt nightly by FEC while the bulk itemized files are the 2026-10-31 download: Q6's D6 measures the lag rather than assuming it away.
- No pipeline step running (the Sunday 03:00 scheduled run, or a runbook in progress), and **no merge to `main` while the run is in progress**: a deploy restarts `pipeline` and kills the `docker exec` (project memory, 2026-11-02).
- Free disk under `/data/fundlens/scratch` for the unpacked 2024 `indiv` (about 5 GB) and 2004's files; the summary files are under 100 MB together.
- FEC's header files for `weball`, `webl` and `webk` are fetched with the project's `USER_AGENT` (`fundlens.fec.refresh_headers.fetch` does exactly this); if one is absent (NEU-2136's run found none for `webk`), the column list is the file description's, in order, as Q7 of the organization-money measurement did. The document says which it used for each.

## 4. The run

All on the VM, in `tmux`, using the `fl` helper from `docs/runbooks/first-run.md`. The document carries every block below verbatim, with its output, in the shape of `docs/measurements/organization-money-2024.md` (header table, a **Headline**, **How to re-run**, the setup, Q1–Q8, **Decisions**, **For NEU-2141, NEU-2142 and NEU-2143**).

### 4.1 Setup script

One Python heredoc, kept at the top of the document and pasted before each query block:

```python
import datetime as dt
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg

from fundlens import paths
from fundlens.fec.extract import USER_AGENT
from fundlens.fec.files import CATALOGUE
from fundlens.load.gold import _register_silver, _require_inputs
from fundlens.r2 import R2
from fundlens.settings import get_settings
from fundlens.transform.runner import Limits, connect, literal, register_bulk, unzip_bulk

settings = get_settings()
store = R2.from_settings(settings)
scratch = paths.scratch_dir(settings.data_dir)
work = scratch / "measure-summary-files-2024"
work.mkdir(parents=True, exist_ok=True)
con = connect(Limits.from_settings(settings), scratch)

# The live build's silver tables, as gold reads them (views silver.<table>).
with psycopg.connect(settings.database_url) as pg:
    BUILD = pg.execute("SELECT build_id FROM gold.meta").fetchone()[0]
_register_silver(con, _require_inputs(store, 2024, BUILD, data_dir=settings.data_dir))
# candidate_committee_link is not a gold input: register its partition by hand.
link = paths.local_path(settings.data_dir, paths.silver_partition("candidate_committee_link", 2024, BUILD))
for key in store.list_keys(paths.silver_partition("candidate_committee_link", 2024, BUILD)):
    local = paths.local_path(settings.data_dir, key)
    if not local.exists():
        store.download_to(key, local)
con.execute(f"CREATE VIEW silver.candidate_committee_link AS SELECT * FROM read_parquet({literal(link / '**' / '*.parquet')}, hive_partitioning = false)")

# 2024 bronze, as the transform sees it.
for name in ("indiv", "cm", "cn", "ccl"):
    register_bulk(con, CATALOGUE[name], unzip_bulk(store, 2024, CATALOGUE[name], data_dir=settings.data_dir, work=work))


def fetch(path: str) -> Path:
    """One FEC file into `work`, its Last-Modified printed; skipped when already there."""
    target = work / Path(path).name
    if not target.exists():
        url = f"{settings.fec_bulk_url.rstrip('/')}/{path}"
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT})) as response:
            target.write_bytes(response.read())
            print(url, "| Last-Modified:", response.headers.get("Last-Modified"),
                  "| downloaded", dt.datetime.now(dt.UTC).isoformat(timespec="seconds"))
    return target


def view_zip(name: str, path: Path, header: list[str]) -> None:
    """A pipe-delimited, headerless summary zip as a VARCHAR view named `name`."""
    with zipfile.ZipFile(path) as archive:
        member = archive.namelist()[0]
        archive.extract(member, work)
    columns = "{" + ", ".join(f"'{h}': 'VARCHAR'" for h in header) + "}"
    con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv({literal(work / member)}, delim = '|', "
                f"quote = '', escape = '', header = false, auto_detect = false, columns = {columns})")


def view_csv(name: str, path: Path) -> None:
    """A header-row CSV summary file as a view named `name`, every column VARCHAR."""
    con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv({literal(path)}, header = true, "
                "all_varchar = true)")


WEBALL = [...]  # 30 names: FEC's weball header file, else the file description in order (§3)
WEBK = [...]    # 27 names, as organization-money-2024.md Q7
view_zip("weball", fetch("2024/weball24.zip"), WEBALL)
view_zip("webl", fetch("2024/webl24.zip"), WEBALL)   # webl shares weball's layout
view_zip("webk", fetch("2024/webk24.zip"), WEBK)
view_csv("committee_summary", fetch("2024/committee_summary_2024.csv"))
view_csv("candidate_summary", fetch("2024/candidate_summary_2024.csv"))
```

Amount columns are cast `DECIMAL(16, 2)` and dates parsed (`MM/DD/YYYY`) inside each query, never in the views, so a malformed cell is visible rather than a read error. `show(title, sql)` prints a timed Markdown table, as in the organization-money measurement. The 2004 block (Q8) registers `weball04`, `webl04`, `webk04` the same way and 2004 `indiv`, `cm`, `cn`, `ccl` with `register_bulk` after `fundlens extract --cycle 2004` (run first, from the host's `docker exec`, as the runbooks run `extract`). The text files stay in `work` for the session; `work` is deleted at the end of the run and the document says so.

Query shape: `connect` disables DuckDB's build-side optimizer (NEU-2076), so joins put the small table on the right. Nothing materializes `indiv` or `silver.contribution`; per-committee aggregates are materialized once (`CREATE TABLE fl AS SELECT recipient_committee_id, … FROM silver.contribution GROUP BY 1`) and reused.

### 4.2 Queries and figures

Each is one SQL block in the document, dated, followed by its result table and one or two sentences of reading.

**Q1 — Grain, keys and overlap (2024).** For each of the five files: row count, distinct key count, duplicate keys with their rows (and the `FEC_ELECTION_YR` values in the two CSVs, since a 2024 file may carry 2023 special-election rows), the `CVG_END_DT` distribution (min, median, max, count at or before 2024-12-31). Then the overlaps, each as rows and the dollars of `TTL_RECEIPTS` on the side that has them: candidates in `weball` not in `candidate_summary` and the reverse; `webl` vs `weball` for H and S candidates (in one not the other; in both with any measure differing); candidates in `weball` with no credited committee in `committee_summary` (and no P/A committee at all in `cm`); committees in `committee_summary` credited to a candidate who is not in `weball`; committees in `webk` not in `committee_summary` and the reverse, by `CMTE_TP`; committees in `committee_summary` not in silver `committee` and the reverse, by `CMTE_TP`. The last is the committee count NEU-2143's definition of done is within 1% of: the document states it.

**Q2 — `webk` vs `committee_summary` (PACs and parties).** For every committee in both: `TTL_RECEIPTS`, `TTL_DISB`, `COH_BOP`, `COH_COP`, `DEBTS_OWED_BY`, `INDV_CONTRIB`/`INDV_CONTB`, `OTHER_POL_CMTE_CONTRIB`/`OTH_CMTE_CONTB`, `TRANS_FROM_AFF`/`TRANF_FROM_OTHER_AUTH_CMTE`, `INDV_REFUNDS`/`INDV_REF`, `CVG_END_DT` on each side: the count equal within $1, the distribution of differences, and the 20 largest differences with both coverage dates. The precedence rule of §1.1 is applied and its result stated. The same for `webl` vs the sum of credited committees in `committee_summary` for H and S candidates (the file's own note says a candidate with several authorized committees has inter-committee transfers counted twice; the document checks whether `TRANS_FROM_AUTH` explains the differences).

**Q3 — Candidate figures: `weball` vs `candidate_summary` vs the sum of credited committees.** For every 2024 candidate in `weball`, per measure (receipts, disbursements, cash on hand end, debts owed by, individual total, other committees, party committees, candidate's own, candidate loans, transfers in, transfers out): the three values and the pairwise differences; the share of candidates equal within $1, within 1%, beyond; by office and by number of credited committees (0, 1, 2+). The 20-row table of §1.1, every measure and all three sources, with each candidate's credited committees listed. `C00703975` under Biden and Harris both. Then the **decision line**: the ≥ 95% / 1% rule applied to receipts, the match rate, every mismatching candidate with the reason the queries show (transfers between authorized committees, a committee `ccl` links that FEC's roll-up excludes, a handoff, an alias, a committee in `cm` but not in `committee_summary`).

**Q4 — Does `TTL_INDIV_CONTRIB` include unitemized money?** For every candidate in both `weball` and `candidate_summary`: the count where `TTL_INDIV_CONTRIB` equals `Individual_Contribution` (itemized + unitemized), equals `Individual_Itemized_Contribution` alone, equals neither; the same against the sum of credited committees' `INDV_CONTB` and `INDV_ITEM_CONTB`; and whether `INDV_CONTB = INDV_ITEM_CONTB + INDV_UNITEM_CONTB` holds in every `committee_summary` row. One sentence states the answer and its count. The same check on `webk.INDV_CONTRIB` against `committee_summary` for PACs (Q2 already has the equality; this names which line it is).

**Q5 — Coverage today.** For every 2024 committee in silver `committee` with a `committee_summary` row: measure A, measure B, `INDV_ITEM_CONTB`, `INDV_UNITEM_CONTB`, `INDV_CONTB`, `INDV_REF`, and the ratios A/itemized, B/itemized, A/total, B/total. Reported: the distribution of B/itemized (and A/itemized) by decile and by `CMTE_TP`; the count and dollars at < 0.99, 0.99–1.01, > 1.01; the dollars FEC reports that fundlens does not reach, in total and by `CMTE_TP`; committees with a summary row but no gold row, and the reverse, with their dollars; and the **full list of committees over 1% on A or B**, with both measures, FEC's figure, the excess in dollars and percent, and the committee's type and name, sorted by excess dollars. The **decision line** for NEU-2141: whether `coverage` uses A or B, from how each behaves by committee type (B should match at super PACs and parties where A cannot; if B over-counts at candidate committees, the document says where and why).

**Q6 — Why fundlens exceeds FEC.** Over every committee on Q5's over-1% list at once, each diagnostic is one query producing per-committee rows and dollars, joined into one table:

- **D1 refund sign.** Counted refund rows (`^[24][0-9]Y$`) in `silver.contribution` and `silver.organization_receipt` whose `indiv` `TRANSACTION_AMT` was filed positive: rows and the dollars silver's `-abs` moved (twice the filed amount is the gap it opens against an as-filed sum).
- **D2 duplicates.** Rows sharing `(recipient_committee_id, contributor_key or organization_key, amount, date)` with different `source_record_id`s: rows and the dollars beyond the first of each group, split by whether the rows' `file_num`s differ (an amendment both of whose versions survived) or match.
- **D3 line mapping.** Counted rows by `transaction_type`, each mapped to the Form 3/3X line FEC puts it on (15, 15E, 15I, 15T, 11, 10 → 11(a)(i); 15C → 11(d), already `self_funding`; 15Z in-kind → 11(a)(i) unless memo; 16C, 16F, 16G, 16H, 16J, 16K, 16L, 16R loans → 13; 18G, 18J, 18K, 18L transfers → 12; 18H → 15; 19/19J → electioneering; 22Z, 20Y, 22Y → 20; anything else → `other`, listed): the dollars silver counts in `total_individual` that FEC does not put on line 11(a)(i). The mapping is written in the document as a CASE expression so NEU-2141 can lift it.
- **D4 committees typed as persons.** `organization_receipt` rows (measure B only) whose `organization_key` or name key names exactly one `cm` committee, and `contribution` rows whose `contributor_key` does: dollars FEC would put on 11(b)/11(c).
- **D5 earmarks.** Counted 15E/15I/15T rows plus any conduit-side row that survived (`conduit_committee_id` set on a row whose twin `24T` is absent): dollars; and `MEMO_CD = 'X'` rows that silver kept for any reason.
- **D6 coverage lag.** The summary row's `CVG_END_DT` against the bulk download date (2026-10-31) and the newest `date` in the committee's counted rows: dollars dated after `CVG_END_DT`, and whether the committee's `CVG_END_DT` is before 2024-12-31 (a report FEC has not yet rolled up).
- **D7 self-funding leak.** `contribution` rows with `is_self_funding = false` whose `contributor_key` is the recipient's candidate: dollars (a 15 filed for the candidate's own money).

Per committee: each diagnostic's dollars, the **primary cause** (the largest), and `explained` when the excess less the sum of the diagnostics' dollars is within 1% of `INDV_ITEM_CONTB`, else `unexplained`. The document lists every committee with its cause, then the **distinct causes** with their committee counts and dollars, and the Bug ticket filed for each (§1.1). An `unexplained` remainder gets one ticket of its own listing the committees. A cause that is not a fundlens bug (D6 lag; D3 rows FEC itself puts on 11(a)(i)) gets no ticket and is said to be none.

**Q7 — The three named gaps.** Fairshake (`C00835959`), MAGA Inc. (`C00825851`) and Senate Leadership Fund (`C00571703`), each with Q5's figures and Q6's diagnostics in full, and for Fairshake (fundlens *under* FEC by $43.4M with 37 itemized gifts) the reverse checks: `INDV_UNITEM_CONTB` (is it unitemized after all?), `indiv` rows for the committee that silver dropped, by reason (memo `X`, `24T`, PAC/COM/CCM/PTY rows naming several or no `cm` committee, ORG rows the conduit rule dropped), and rows in `indiv` dated after the bulk download's coverage. One paragraph per committee states what the gap is.

**Q8 — 2004 with `weball`, `webl` and `webk` only.** After `fundlens extract --cycle 2004`: Q1's grain and overlap for the three files; `webl` vs `weball` for H and S candidates; and coverage with the raw `indiv` proxy (§2): per committee in `webk`, proxy vs `INDV_CONTRIB` (distribution, the over-1% count); per candidate in `weball`, the proxy summed over the candidate's P/A committees (`ccl` 2004, plus `cn.CAND_PCC`) vs `TTL_INDIV_CONTRIB`. A closing table lists, per reported measure, which of the three files carries it in 2004, so the document can say what a pre-2008 candidate or committee page can show (no itemized/unitemized split, no debts owed to, no coverage start, no cash at the start of the cycle for candidates unless `COH_BOP` proves to be that).

### 4.3 The document

`docs/measurements/summary-files-2024.md`, in this order:

1. Header table: run date, `main` SHA (`service.version`), container, live build and its source dates, DuckDB limits, each FEC file's URL, `Last-Modified` and download time, which header source each zip used, the 2004 bronze keys written.
2. **Headline**: five or six bullets with the numbers that matter (the candidate-source decision, the precedence result, what `TTL_INDIV_CONTRIB` is, the coverage median and the over-1% count and dollars, the three named gaps in one line each).
3. **How to re-run** and the setup script.
4. Q1–Q8.
5. **Decisions**: (1) candidate figures' source, 2008+ and pre-2008, with the match rate; (2) precedence per cycle range (1980–1994, 1996–2006, 2008–), per grain, with the Q2 numbers; (3) what `TTL_INDIV_CONTRIB` and `INDV_CONTRIB` hold; (4) which fundlens figure `coverage` uses; (5) the over-1% causes and the tickets filed; (6) a recommendation on `candidate_summary` for NEU-2142 (catalogue it or not, and whether `webl` adds anything `weball` lacks).
6. **For NEU-2141, NEU-2142 and NEU-2143**: what each takes from here (the column availability per cycle range for `reported_total`'s NULL rules; the D3 line mapping; the committee count NEU-2143's definition of done checks; the handoff question NEU-2141 must answer).

No `capacity.md` row: this is a measurement, not a pipeline step. No change to `CONTEXT.md` or `docs/adr/`.

## 5. Acceptance criteria

- [ ] `docs/measurements/summary-files-2024.md` is merged; every figure is dated, every query is inline and runnable from the setup script, and each FEC file's URL and `Last-Modified` are given.
- [ ] Q1–Q8 are all present with results; nothing is marked "to do".
- [ ] The candidate-source decision is stated with the §1.1 rule applied, the match rate, and every mismatching candidate explained.
- [ ] The per-cycle precedence is stated for each of 1980–1994, 1996–2006 and 2008–, at both grains, with Q2's equality counts behind it; `candidate_summary`'s place is recommended for NEU-2142.
- [ ] Whether `TTL_INDIV_CONTRIB` and `INDV_CONTRIB` include unitemized money is stated with the counts.
- [ ] Every 2024 committee over 1% on measure A or B is listed with its diagnostics and a cause or `unexplained`; one Bug ticket per distinct cause exists in P-NEU-105, related to NEU-2140, and is named in the document.
- [ ] Which of measure A and B `coverage` uses is stated for NEU-2141, with the numbers by committee type.
- [ ] Fairshake, MAGA Inc. and Senate Leadership Fund each have a paragraph stating what their gap is.
- [ ] 2004's `cm`, `cn`, `ccl`, `indiv`, `pas2`, `oth` zips are in R2 bronze (`r2ls bronze/cycle=2004/`); no `silver/cycle=2004` object, no marker and no gold was written; `/data/fundlens/scratch/measure-summary-files-2024` is removed.
- [ ] No change under `sql/`, `src/` or `frontend/` in the PR.

## 6. Out of scope

- Any change to `sql/`, `src/`, `frontend/`, `CONTEXT.md` or `docs/adr/` (NEU-2141 onward).
- Fixing the causes Q6 finds (their Bug tickets).
- Cataloguing any summary file or reading one in the pipeline (NEU-2142).
- Cycles other than 2024 and 2004.
- Deciding what gold shows or how `reported_total` is shaped (NEU-2141), and the handoff rule for cycle-to-date rows (NEU-2141).
