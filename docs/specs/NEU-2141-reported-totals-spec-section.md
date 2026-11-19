# NEU-2141 — Spec §4 reported totals: `reported_total` columns, source precedence, gold fields, coverage, gift-size buckets; glossary

**Ticket:** [NEU-2141](https://linear.app/neuroticsasquatch/issue/NEU-2141) · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Milestone:** M1 Reported totals · **Parent story:** NEU-2139
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §4 (a stub this ticket fills), §2 (older builds), §3 (file catalogue), §8 (public dataset) · **v1 spec:** §4 (the credit rule, `fec_line`, what `total_individual` counts), §7.1 (`committee_cycle`, `candidate_cycle`, `race_candidate`, `race`), §9 · **Glossary:** `CONTEXT.md` · **ADRs:** 0004 (earmarks count once), 0011 (organizations are grouped, not resolved)
**Blocked by:** NEU-2137 (Done), NEU-2140 (Done: `docs/measurements/summary-files-2024.md`, "the measurement" below). **Blocks:** NEU-2142, and through it NEU-2143 to NEU-2147. **Related:** NEU-2265 (`total_refunds`, Done), NEU-2276 (other-lines money by `TRAN_ID`, Done), NEU-2352 (backfill-pending tables, Done).

Planned 2026-11-18. `/implementit NEU-2141` produces **one docs PR**: project spec §4 written out, the six `CONTEXT.md` terms this planning session already wrote (uncommitted), two edits to the v1 spec (§9's table list, one sentence in §7.1), and the Linear text corrections of §5. Nothing under `sql/`, `src/` or `frontend/` changes.

## 1. What and why

Six tickets (NEU-2142 to NEU-2147) build reported totals from one contract that is not written down: project spec §4 holds only the milestone's three shared contracts. This ticket writes it.

The ticket text predates the measurement, and differs from what this spec pins in these places:

1. The ticket has one silver table, "one row per committee per cycle", with a second only "if NEU-2140 decided candidates come from `weball`". The measurement decided both: committees' sums from 2008, `weball` before.
2. The ticket's `coverage` is "itemized individual ÷ reported itemized individual". The measurement's Decision 4 makes the numerator individual plus organization money.
3. The ticket's columns have one `loan_repayments` and no refunds figure.
4. The ticket's `coverage_start` and `coverage_end` use "coverage" for dates, and its `coverage` for a ratio.
5. The ticket's buckets have no place for an itemized donor at $200 or less.
6. The measurement handed NEU-2141 two open questions: the handoff, and campaigns turned PACs.

### 1.1 Decisions pinned (grilled 2026-11-18)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Candidate grain before 2008 | **A second silver table, `candidate_reported_total`**, keyed `(cycle, candidate_id)`, with `reported_total`'s measure columns, written from `weball` for 1980–2006 and empty from 2008, where gold sums the credited committees. | One source per figure per cycle, and the dataset never holds a 2008+ candidate figure the site contradicts. Rejected: the same table for every cycle (two published answers for a 2024 candidate, and `weball` repeats 248 rows under second candidate ids in 2024, Q3h3); one table with two grains (breaks the `(cycle, committee_id)` key NEU-2143's checks assume). |
| A handoff's committee | **Its whole reported row is the second candidate's.** The first candidate's reported fields, `itemized_total` and `coverage` are NULL for that cycle. | A cycle-to-date row cannot be split at the handoff date (Q3k). Nothing is counted twice and no figure is invented. Rejected: both candidates, as FEC's files do (the race counts $1.175B twice); neither (the largest campaign of 2024 shows no cash on hand); apportioning by itemized share (fundlens's estimate, not FEC's figure). |
| A campaign turned PAC | **Its whole row counts toward the candidate, and the candidate-cycle is flagged** `reported_includes_converted_committee`. | Reported figures follow the credit rule itemized money follows, which has no date cut either, so coverage compares like with like. The flag lets the page say why the figure differs from fec.gov's. Rejected: FEC's P/A designation only (Trump's 2024 page loses his campaign committee's $495.9M of reported receipts while keeping its itemized money). |
| Columns | **The ticket's list, amended**: `loan_repayments` split into `candidate_loan_repayments` and `other_loan_repayments`; `individual_refunds` added; `coverage_start`/`coverage_end` renamed `period_start`/`period_end`. 23 measures. | Every file carries the two repayment figures and a refunds figure, and FEC's itemized figure is gross of refunds. Rejected: the list as written (the refund basis could not be shown); every one of `committee_summary`'s 77 figures (mostly blank, each needing a name that holds across three files; adding a column later is an additive dataset change). |
| The word "coverage" | **The ratio keeps it.** FEC's dates are the **reporting period**. | One word, one meaning. Rejected: renaming the ratio (the milestone contract, the story and five tickets say `coverage`); keeping both. |
| Coverage's numerator | **`itemized_total` = `total_individual + total_from_organizations − total_refunds`**: individual plus organization money (Decision 4), gross of refunds. | `INDV_ITEM_CONTB` is gross of refunds (NEU-2265: VIVEK 2024 reads −2.06% net, −0.17% gross). Rejected: net (every committee with refunds reads low for a reason that is not missing data); net against FEC's figure less `INDV_REF` (FEC's refund figure covers unitemized gifts' refunds too). |
| A candidate's coverage | **Summed over its credited committees, both sides**: the committees' `itemized_total`s over their reported itemized figures. | Candidate committees take ORG-typed gifts (812 within 1% of FEC with them, 728 without, Q5g), and the same committees are on both sides. Rejected: `candidate_cycle.total_individual` as numerator (reads low wherever there is ORG-typed or refunded money); no candidate-level figure (the story's definition of done asks for one). |
| Coverage over 100% | **Stored and shown as computed.** | The `reconciliation` table publishes every committee more than 1% over, so the figure and its explanation are both public. Rejected: capping at 100% (presents unmatched money as matched); NULL above 101% (a committee flips between a figure and nothing as filings are amended). |
| Where coverage is NULL | **At a conduit; where FEC's itemized figure is blank or 0; before 2008.** | Decision 4's caveats: a conduit's reported figure includes the earmarks fundlens credits to the recipient (ADR-0004, Q5m); Form 4 and Form 5 filers have no itemized figure; no pre-2008 file splits itemized from unitemized (Q8). |
| A donor's gift size | **Per resolved donor per candidate**: one `donor_id`, all the candidate's committees, net of refunds, over the rows `candidate_cycle.total_individual` counts. | The resolution is the product. Rejected: per committee, as FEC's threshold works (one person in two buckets for one candidate); per contributor key (two spellings are two small donors). |
| Itemized donors at $200 or less | **Their own bucket.** Six buckets: `unitemized` and five itemized. | The reported lump stays FEC's as filed, and the five itemized buckets add up to `total_individual`. Rejected: folding them into "$200 and under" with the lump (adds a reported figure to itemized money, against the milestone contract); leaving them out (the buckets stop adding up). |
| Donors netting $0 or less | **In the `200_or_less` bucket.** | The buckets must add up to `total_individual`, which nets them. |
| Reconciliation's measures | **One: `individual_itemized`**, over only, no dollar floor, 2008 on, conduits left out. | The only comparison the measurement diagnosed. The `measure` column stays for M2. Rejected: committee money and loans too (unmeasured across 2024's committees); both directions (thousands of rows repeating coverage below 100%). |
| Reconciliation with no reported figure | **A reported 0 beside fundlens money is listed, `ratio` NULL; a blank is not listed.** | A 0 is a figure FEC gives, a blank is not one. |
| Gold fields | **Every measure**, as `reported_<measure>`, on `committee_cycle` and `candidate_cycle`; a short set on `race_candidate`; summed cash on hand on `race`. | One mechanical rule, and M2 and M3 find reported operating and independent expenditures already there. Rejected: a page set of about twelve (this ticket's guess, widened one DDL change at a time); separate gold tables (a second lookup per page). |
| `source_file` | **`committee_summary`, `committee_summary+webk` or `webk`** on `reported_total`; `weball` on `candidate_reported_total`. From 2008 `webk` fills a blank measure and never adds a committee. | Decision 2 makes `webk` a per-measure fallback, so a row can draw on two files. The 2,248 committees only in `webk24` carry no money but one bad Form 5 record (Q1). |
| `operating_expenditures` | **`OP_EXP + TTL_OP_EXP`** (a blank as 0; NULL when both are blank). | Form 3 and 3P filers fill `OP_EXP`, Form 3X filers `TTL_OP_EXP`; a campaign that became a PAC fills both, for different reports (Appendix A, checked for this spec). Rejected: one column by committee type (drops NEVER SURRENDER's $463.0M of campaign spending, its type now being N). |
| Glossary | **Six terms**, written in this session: **Reported total**, **Itemized total**, **Coverage**, **Unitemized**, and two the ticket lacks, **Reporting period** and **Gift size**. | "Coverage dates" and "small-dollar" needed a canonical word each. |
| ADR | **None.** | Gold is rebuilt every run and silver keeps every figure as filed, so no choice here is hard to reverse. The payee ADR stays 0012. |

## 2. The document: project spec §4

Replace §4's closing "**Filled by** NEU-2141 …" line with the subsections below, keeping the opening paragraph and the three shared contracts as they are. Write each rule with its measurement citation, as given here. Where a rule rests on no measurement it says "asserted, not measured" and names the ticket that checks it.

### §4.1 Silver `reported_total`

Key `(cycle, committee_id)`. Columns, in order: `cycle, source, jurisdiction, source_file, committee_id, period_start, period_end`, then the 23 measures below. `source` is `fec` and `jurisdiction` `US`, as every silver table's (v1 §4).

Each measure is the file's figure as filed, `DECIMAL(14,2)`: a blank is NULL, a filed 0 is 0, and nothing is netted, corrected or derived from another measure except where the table says so. `INDV_CONTB = INDV_ITEM_CONTB + INDV_UNITEM_CONTB` fails for 166 committees in 2024, filers' arithmetic mostly (Q4c), so all three are stored as filed and no check enforces the identity. Dates are `DATE`: `committee_summary` writes `YYYYMMDD`, the zips `MM/DD/YYYY`.

| Column | `committee_summary` (2008–) | `webk` (1996–2006; a blank measure's fill from 2008) | `weball` (`candidate_reported_total`, §4.2) |
|---|---|---|---|
| `period_start` | `CVG_START_DT` | — | — |
| `period_end` | `CVG_END_DT` | `CVG_END_DT` | `CVG_END_DT` |
| `receipts` | `TTL_RECEIPTS` | `TTL_RECEIPTS` | `TTL_RECEIPTS` |
| `disbursements` | `TTL_DISB` | `TTL_DISB` | `TTL_DISB` |
| `cash_on_hand_start` | `COH_BOP` | `COH_BOP` | `COH_BOP` |
| `cash_on_hand_end` | `COH_COP` | `COH_COP` | `COH_COP` |
| `debts_owed_by` | `DEBTS_OWED_BY_CMTE` | `DEBTS_OWED_BY` | `DEBTS_OWED_BY` |
| `debts_owed_to` | `DEBTS_OWED_TO_CMTE` | — | — |
| `individual_itemized` | `INDV_ITEM_CONTB` | — | — |
| `individual_unitemized` | `INDV_UNITEM_CONTB` | — | — |
| `individual_total` | `INDV_CONTB` | `INDV_CONTRIB` | `TTL_INDIV_CONTRIB` |
| `individual_refunds` | `INDV_REF` | `INDV_REFUNDS` | `INDIV_REFUNDS` |
| `party_contributions` | `PTY_CMTE_CONTB` | — | `POL_PTY_CONTRIB` |
| `other_committee_contributions` | `OTH_CMTE_CONTB` | `OTHER_POL_CMTE_CONTRIB` | `OTHER_POL_CMTE_CONTRIB` |
| `candidate_contributions` | `CAND_CNTB` | `CAND_CONTRIB` | `CAND_CONTRIB` |
| `candidate_loans` | `CAND_LOAN` | `CAND_LOANS` | `CAND_LOANS` |
| `other_loans` | `OTH_LOANS`; where that is blank, `TTL_LOANS` less `CAND_LOAN` (a blank as 0) | `TTL_LOANS_RECEIVED` less `CAND_LOANS` | `OTHER_LOANS` |
| `candidate_loan_repayments` | `CAND_LOAN_REPYMNT` | `CAND_LOAN_REPAY` | `CAND_LOAN_REPAY` |
| `other_loan_repayments` | `OTH_LOAN_REPYMTS` | `LOAN_REPAY` | `OTHER_LOAN_REPAY` |
| `transfers_in` | `TRANF_FROM_OTHER_AUTH_CMTE` | `TRANS_FROM_AFF` | `TRANS_FROM_AUTH` |
| `transfers_out` | `TRANF_TO_OTHER_AUTH_CMTE` | `TRANF_TO_AFF` | `TRANS_TO_AUTH` |
| `independent_expenditures` | `INDT_EXP` | `IND_EXP` | — |
| `party_coordinated` | `COORD_EXP_BY_PTY_CMTE` | `PTY_COORD_EXP` | — |
| `operating_expenditures` | `OP_EXP + TTL_OP_EXP` (a blank as 0; NULL when both are blank) | — | — |
| `federal_funds` | `FED_FUNDS` | — | — |

Notes §4.1 carries under the table:

- **What the mapping rests on.** `individual_total` holds itemized plus unitemized money in all three files (Decision 3; Q4). `committee_summary` and `webk` agree within $1 on receipts for 9,843 of 9,845 shared committees, and on debts, other committees' contributions, transfers in and refunds for every one (Q2a). The column names are `committee_summary_2024.csv`'s own header row, read 2026-11-18, and the zips' are FEC's file descriptions (the measurement's header-sources row). The loan, repayment and operating-expenditure rows rest on Appendix A's check. **Asserted, not measured:** that `webk`'s `LOAN_REPAY` leaves out candidate loan repayments, and its `IND_EXP` and `PTY_COORD_EXP` against `committee_summary`'s; NEU-2143 compares each on 2024's shared committees and amends this table if one differs.
- **Rows, 2008 on.** One row per `CMTE_ID` of `committee_summary` that is a committee of the cycle in silver `committee`. The file repeats a committee once per linked candidate (65 committees, 136 rows in 2024, Q1): the transform keeps one and fails if a committee's rows differ in anything but `CAND_ID` and `Link_Image`. Each measure is `committee_summary`'s, or `webk`'s where `committee_summary`'s is blank and `webk` holds the committee: Form 5 filers (type I), whose `committee_summary` rows carry only `INDT_EXP`, and Form 7 filers (type C), whose rows carry only a communication-cost figure this table does not hold (204 and 68 committees in 2024, Q2f2; Appendix A). `source_file` is `committee_summary+webk` when any measure came from `webk`, else `committee_summary`. A committee only in `webk` gets no row. 2024: 13,995 committees, 13,994 of them silver committees (Q1i).
- **Rows, 1996–2006.** One row per `webk` committee in silver `committee`, `source_file` `webk`. House and Senate campaign committees have none: `webk04` holds 54 candidate committees (Q8).
- **Rows, 1980–1994.** None. The model still writes its partition, empty (§2, older builds).
- A row whose every measure is blank is kept: FEC lists the committee and reports nothing.
- **Not held:** FEC's `FED_CAND_CMTE_CONTB` (Form 3X line 23), which reconciles with neither the gross nor the net 24Ks (Decision 8), `OTHER_RECEIPTS`, and Form 7's `TTL_COMMUNICATION_COST`, which is M3's (§6).

### §4.2 Silver `candidate_reported_total`

Key `(cycle, candidate_id)`. Columns as `reported_total`'s with `candidate_id` in place of `committee_id`. Written from `weball`, the mapping's last column, for 1980–2006: one row per `CAND_ID` that is a candidate of the cycle in silver `candidate`, `source_file` `weball`. A measure `weball` lacks is NULL: `period_start`, `debts_owed_to`, the itemized and unitemized split, `independent_expenditures`, `party_coordinated`, `operating_expenditures`, `federal_funds`. From 2008 the partition is empty: candidate figures are summed from `reported_total` (§4.3).

`weball`'s rows are not additive across candidates: it lists a committee's money under each candidate id linked to it (248 rows in 2024, $789.4M, Q3h3). Before 2008 that stands as filed. A candidate alias has no gold row (v1 §7.1), so its repeat is in no race; a person's ids for two different races each keep their row.

`webl` and `candidate_summary` are not read (§3.2).

### §4.3 Candidate figures

- **2008 on: the sum of the candidate's credited committees' `reported_total` rows** (Decision 1). The credited committees are those `04_contribution.sql`'s `linked` rule gives the candidate (v1 §4): linked P or A, or the committee `candidate.principal_committee_id` names; a committee linked to two candidates is the principal link's, then the lower `candidate_id`'s; a candidate alias is credited none. Each committee has one candidate, so the figures add up across candidates as FEC's candidate files do not. Against `candidate_summary.Total_Receipt` the sum is within 1% for 2,235 of 2,255 candidates (99.11%; 99.95% of those with receipts), every mismatch explained (Q3g, Q3h).
- A measure is the sum over the credited committees that have it, NULL when none does. `reported_period_start` is the earliest, `reported_period_end` the latest.
- **Transfers between a candidate's own committees are not netted out**: each is in one committee's disbursements and another's receipts. FEC does not net them either: `weball` equals the committees' sum exactly for all 2,118 House and Senate candidates with a credited committee (Q2g, Q2h).
- **A handoff's committee is the second candidate's alone** (`fec/handoffs.csv`'s `to_candidate_id`), whole, in the cycle of the handoff: a cycle-to-date row cannot be split at `handoff_date`. In 2024 `C00703975`'s $1,175,189,365 of receipts is Harris's, and Biden has no credited committee, so his reported fields, `itemized_total` and `coverage` are NULL beside $73,961,689 of itemized individual money (Q3k, Q3n). FEC's files list the row under both. Rejected: both candidates, neither, and apportioning by itemized share.
- **A campaign turned PAC counts whole.** A committee credited through `principal_committee_id` alone, which `ccl` no longer designates P or A, adds its whole cycle-to-date row, what it raised after converting included: ten candidates in 2024, $523.3M, $495.9M of it Trump's NEVER SURRENDER (`C00828541`) and $23.2M Kunce's Heartland Patriots (Q3h). Itemized money follows the same rule with no date cut. `candidate_cycle.reported_includes_converted_committee` is true for such a candidate, so a page can say why its figure differs from FEC's, which credits these committees to no one.
- **Before 2008:** the candidate's `candidate_reported_total` row as filed. The flag is false.

### §4.4 Gold fields

The `reported_*` fields and `coverage` are NULL where there is no reported row, or the cycle's file lacks the measure, never 0. `itemized_total` is fundlens's own figure, and has its own rule below.

| Table | Added |
|---|---|
| `committee_cycle` | `reported_<measure>` for each of the 23 measures; `reported_period_start`, `reported_period_end`, `reported_source_file`; `itemized_total`; `coverage` |
| `candidate_cycle` | The same, by §4.3, and `reported_includes_converted_committee`. `reported_source_file` is `committee_summary` from 2008 and `weball` before |
| `race_candidate` | `reported_receipts`, `reported_disbursements`, `reported_cash_on_hand_end`, `reported_debts_owed_by`, `coverage`: the candidate's `candidate_cycle` values |
| `race` | `reported_cash_on_hand`: the sum of its candidates' `reported_cash_on_hand_end`, NULL when none has one |

- **`itemized_total`** (`CONTEXT.md`). A committee's is `total_individual + total_from_organizations − total_refunds` (v1 §7.1; NEU-2265), never NULL: individuals' and organizations' money on line 11(a)(i), gross of refunds, which is what `INDV_ITEM_CONTB` counts. A candidate's is the sum of its credited committees' (§4.3), NULL when it has none. It is a comparison figure: it is in no race total and no top list, and `total_individual` is unchanged. It is the one candidate figure that includes organization money; it reads `committee_cycle`, not `organization_receipt`, so ADR-0011's "only gold readers" stands.
- **`coverage`** = `itemized_total ÷ reported_individual_itemized`, a ratio (0.9412), not a percentage, stored as computed.
  - The numerator is individual plus organization money (Decision 4): within 1% of FEC's itemized figure at 5,114 committees against 4,440 for individual money alone, and at super PACs 802 against 386 (Q5g). Those counts were taken net of refunds. **Asserted, not measured:** the counts on the gross basis; NEU-2147's runbook records them.
  - NULL when `reported_individual_itemized` is NULL or 0; so NULL before 2008, whose files have no itemized figure (Q8), and for Form 4 and Form 5 filers.
  - NULL at a conduit (`committee.is_conduit`): ActBlue's and WinRed's `INDV_ITEM_CONTB` ($3.76B and $1.61B in 2024) include the earmarks fundlens counts at the recipient (ADR-0004; Q5m).
  - It can exceed 1. Where a filer put counted money on a line the bulk file does not show, fundlens is over (71 committees, $10,791,881, after NEU-2276; Q6 after NEU-2276); where FEC adds a superseded filing to its amendment, FEC is over (NEU-2196). Shown as it is. Rejected: capping at 1, and NULL above 1.01.
  - A candidate's is over the same committees on both sides, so Harris's spans the whole of `C00703975`.
- A hybrid PAC's `total_individual` and `total_from_organizations` hold its contribution account alone (v1 §7.1), which is what its `INDV_ITEM_CONTB` counts, so its coverage needs no special rule.

### §4.5 Reconciliation

Gold `reconciliation (committee_id, cycle, measure, fundlens, reported, ratio)`, key `(committee_id, cycle, measure)`: the committees where fundlens's figure exceeds FEC's reported one by more than 1%. Built by every load, published, and **never failing the build**: FEC's figures lag amendments, and a filer's line choice is not fundlens's to fix.

- M1 writes one measure, `individual_itemized`: `fundlens` is `itemized_total`, `reported` is `reported_individual_itemized`, `ratio` is `fundlens ÷ reported`.
- A committee is listed when `reported` is not NULL, it is not a conduit, and `fundlens − reported > 0.01 × reported`. A reported 0 beside fundlens money is listed with `ratio` NULL. A blank reported figure is not listed.
- No dollar floor, as the measurement's excess list had none. Over only: a shortfall is coverage below 1.
- 2008 on, since no earlier file has the measure.
- The measurement's list, on the net basis and before its bugs were fixed, was 725 committees and $1.94B (Q6); NEU-2192 to NEU-2199 and NEU-2276 took the diagnosed causes out, leaving 71 unexplained. **Asserted, not measured:** the table's row count on a current build; NEU-2147's runbook records it and dispositions its top ten.

### §4.6 Gift sizes

Gold `candidate_gift_size (candidate_id, cycle, bucket, amount, donors)`, key `(candidate_id, cycle, bucket)`.

| `bucket` | Holds | `donors` |
|---|---|---|
| `unitemized` | The candidate's `reported_individual_unitemized`, as filed | NULL |
| `200_or_less` | Donors whose gift size is $200 or less, those netting $0 or less among them | their count |
| `under_500` | over $200 and under $500 | their count |
| `under_1000` | $500 and under $1,000 | their count |
| `under_2000` | $1,000 and under $2,000 | their count |
| `2000_or_more` | $2,000 or more | their count |

- **Gift size** (`CONTEXT.md`) is a donor's net gifts to one candidate in the cycle: the sum, per `donor_id`, of the rows `candidate_cycle.total_individual` counts for that candidate (v1 §4: not self-funding, not other-lines money, refunds netting). A donor's aggregate decides the bucket: 20 gifts of $50 are one `under_2000` donor. `amount` is the bucket's donors' gift sizes added up.
- The five itemized buckets add up to `candidate_cycle.total_individual`, and a gold check fails the build if they do not. A candidate with a counted contribution has all five rows, a bucket with no donor at 0.
- The `unitemized` row exists only where the candidate has a reported unitemized figure: 2008 on. It is FEC's lump as filed, beside the itemized buckets, never added to one (the milestone's contract). A handoff's first candidate has none.
- A cycle loaded before `resolve` has no `donor_id`s and so no itemized bucket rows, as its `contributor_count` is NULL (v1 §7.1).
- Organization money is in no bucket: an organization is not a donor.
- Rejected: buckets by single gift (20 gifts of $50 are one $1,000 donor, not twenty $50 ones); the aggregate per committee, as FEC's itemization threshold is taken (one person in two buckets for one candidate); folding itemized donors at $200 or less into the unitemized bucket, as FEC's presidential `Contributions_by_Size.csv` does (**asserted, not measured**; §1 allows it as a check, never a source).

### §4.7 What each cycle range has

| | 2008– | 1996–2006 | 1980–1994 |
|---|---|---|---|
| Committee reported totals | every measure; Form 5 and Form 7 filers' from `webk` | `webk`'s measures; none for House and Senate campaign committees | none |
| Candidate reported totals | credited committees' sum | `weball`'s measures | `weball`'s measures |
| Missing measures | — | `period_start`, `debts_owed_to`, itemized and unitemized, `operating_expenditures`, `federal_funds`; and `party_contributions` (committees), `independent_expenditures` and `party_coordinated` (candidates) | as 1996–2006 |
| `coverage`, `reconciliation` | yes | NULL, no rows | NULL, no rows |
| Gift sizes | six buckets | five itemized | five itemized |

A page shows a missing figure as "not reported", never 0 (NEU-2146).

### §4.8 Dataset and older builds

`reported_total` and `candidate_reported_total` join the public dataset (§8): NEU-2143 adds both to `DATASET_TABLES`, `columns.yaml`, the schemas, the changelog, the README and `paths.BACKFILL_PENDING` in the PR that builds them. Their README entry says a reported total is never to be added to `contribution` amounts.

## 3. `CONTEXT.md`

Written in this session, under **Money**, uncommitted: **Reported total**, **Itemized total**, **Coverage**, **Unitemized**, **Reporting period**, **Gift size**, each with its avoid list. `/implementit` commits them as they stand and checks that §4's text uses them: "reporting period" for FEC's dates, never "coverage dates"; "unitemized", never "small-dollar".

## 4. The v1 spec

- **§9**, the layout block's table list: add `reported_total` and `candidate_reported_total` after `organization_receipt`.
- **§7.1**, the paragraph "Organization money (ADR-0011) is committee-level only …": add one sentence. "`itemized_total` (every FEC dollar spec §4.4) is the one candidate figure that includes it, summed from `committee_cycle` for comparison with FEC's itemized figure, and is in no total."
- §7.1's table rows are not edited here: NEU-2144 adds its columns to them when it builds them, as v1's gold tickets did.

ADR-0011 is not edited: its "no candidate figure" is scoped to v1, and `itemized_total` reads `committee_cycle`.

## 5. Linear text this spec supersedes

`/implementit` patches each description, changing only the named text, and appends to each "Amended 2026-11-18 by project spec §4 (NEU-2141)."

| Ticket | Text | Becomes |
|---|---|---|
| NEU-2143 | "candidate figures as spec §4 decided (summed … or `candidate_reported_total` from `weball`)" | Builds both tables: `reported_total` (§4.1) and `candidate_reported_total` from `weball`, 1980–2006, empty from 2008 (§4.2). Candidate sums are gold's (NEU-2144). |
| NEU-2143 | `silver_reported_total_coverage.sql (coverage_end ≥ coverage_start …)` | `silver_reported_total_period.sql` (`period_end ≥ period_start` when both set); add the duplicate-row check (§4.1) and `candidate_reported_total`'s key and candidate checks. |
| NEU-2143 | Fixture: "a pre-2008 cycle row from `webk`" | Also a pre-2008 `weball` row, and a `committee_summary+webk` row for a Form 5 filer. |
| NEU-2144 | "coverage is NULL exactly when the reported denominator is 0 or NULL" | "… or the committee is a conduit" (§4.4). Adds `itemized_total` and `reported_includes_converted_committee`. |
| NEU-2144 | `candidate_gift_size` "in spec §4's buckets … buckets sum to `total_individual + reported unitemized`" | Six buckets (§4.6); the five itemized ones sum to `total_individual`. Its definition-of-done donor, 20 × $50, is in `under_2000`. |
| NEU-2145 | `ReportedTotals` "… coverage dates" | `period_start`, `period_end`; every measure of §4.4; `itemized_total`; `reported_includes_converted_committee` on the candidate; `gift_sizes[].donors` nullable. |
| NEU-2146 | "labelled with the coverage dates" | Labelled with the reporting period. A coverage over 100% is shown as it is; a handoff's first candidate and a converted committee each get a one-line note. |

NEU-2141's own description gained its "Planned 2026-11-18 …" line in this session.

## 6. Acceptance criteria

- [ ] Project spec §4 holds §4.1–§4.8 as written in §2 above, the three shared contracts unchanged above them, and no "Filled by" line.
- [ ] Every rule in §4 that rests on a measurement cites the measurement's question or decision; each unmeasured one says "asserted, not measured" and names the ticket that checks it.
- [ ] §4.1's mapping table names a source column, or "—", for each of the 25 columns in each of the three files.
- [ ] `CONTEXT.md` defines the six terms, and `grep -n "coverage dates\|small-dollar" docs/specs/fundlens-every-fec-dollar-project-spec.md` finds neither outside an avoid note.
- [ ] v1 spec §9 lists `reported_total` and `candidate_reported_total`; §7.1's organization-money paragraph has the `itemized_total` sentence.
- [ ] The five descriptions of §5 are patched in Linear.
- [ ] The PR changes nothing under `sql/`, `src/` or `frontend/`.

## 7. Out of scope

- Any code: the catalogue (NEU-2142), silver (NEU-2143), gold (NEU-2144), API (NEU-2145), pages (NEU-2146), the run (NEU-2147).
- v1 §7.1's table rows and v1 §7.2's endpoints (their tickets).
- Reconciling committee money, loans or spending (a later `measure`).
- Gift sizes for committees that raise for no candidate.
- Recovering what FEC's bulk files omit (NEU-2181, NEU-2206).

## Appendix A. Checks made for this spec

`committee_summary_2024.csv`, `Last-Modified: Wed, 18 Nov 2026 10:12:49 GMT`, downloaded 2026-11-19T01:05:38Z into the dev stack's `app` container and deleted after; DuckDB, every column read as text, one row per `CMTE_ID` (14,066 rows, 13,995 committees, as Q1). `a(x)` casts a trimmed cell to `DECIMAL(16,2)`, a blank as 0.

```sql
CREATE VIEW cs AS SELECT * FROM read_csv('committee_summary_2024.csv', header = true, all_varchar = true)
QUALIFY row_number() OVER (PARTITION BY CMTE_ID ORDER BY CAND_ID) = 1;

-- A1: which operating-expenditure column each committee type fills.
SELECT CMTE_TP, count(*) AS n,
    count(*) FILTER (WHERE a(OP_EXP) <> 0) AS op_nonzero,
    count(*) FILTER (WHERE a(TTL_OP_EXP) <> 0) AS ttl_nonzero,
    count(*) FILTER (WHERE a(OP_EXP) <> 0 AND a(TTL_OP_EXP) <> 0 AND a(OP_EXP) <> a(TTL_OP_EXP)) AS both_differ
FROM cs GROUP BY ALL;

-- A2: where both are filled and differ, do they fit inside total disbursements together?
SELECT count(*) AS n, count(*) FILTER (WHERE a(OP_EXP) + a(TTL_OP_EXP) <= a(TTL_DISB) + 1) AS sum_fits
FROM cs WHERE a(OP_EXP) <> 0 AND a(TTL_OP_EXP) <> 0 AND a(OP_EXP) <> a(TTL_OP_EXP);

-- A3: loans. Is TTL_LOANS the candidate's loans plus the others', and where is OTH_LOANS blank?
SELECT CMTE_TP IN ('H', 'S', 'P') AS candidate_committee, count(*) AS n,
    count(*) FILTER (WHERE abs(a(TTL_LOANS) - a(CAND_LOAN) - a(OTH_LOANS)) <= 1) AS ttl_is_sum,
    count(*) FILTER (WHERE nullif(trim(OTH_LOANS), '') IS NULL) AS oth_blank
FROM cs WHERE a(TTL_LOANS) <> 0 GROUP BY ALL;

-- A4: repayments. Is TTL_LOAN_REPYMTS the two repayment figures added?
SELECT count(*) AS n, count(*) FILTER (WHERE abs(a(TTL_LOAN_REPYMTS) - a(CAND_LOAN_REPYMNT) - a(OTH_LOAN_REPYMTS)) <= 1) AS eq
FROM cs WHERE a(TTL_LOAN_REPYMTS) <> 0;
```

- **A1.** `OP_EXP` is nonzero at 3,163 of 3,837 House and Senate committees and 121 of 171 presidential ones; `TTL_OP_EXP` at 6,106 of 9,231 PACs and 400 of 480 party committees. Each is nonzero at few committees of the other kind (`TTL_OP_EXP` at 42 candidate committees, `OP_EXP` at 167 others).
- **A2.** 78 committees fill both with different figures, $559,487,959 of `OP_EXP` and $7,239,947 of `TTL_OP_EXP`, and at all 78 the two together fit inside `TTL_DISB`. The largest are campaigns turned PACs: NEVER SURRENDER (`C00828541`, type N) $463,004,903 and $300,265 of $471,501,652 disbursed; HEARTLAND PATRIOTS (`C00771972`) $22,579,887 and $244,781. Each column holds a different form's reports, so they add.
- **A3.** At candidate committees with loans, `TTL_LOANS = CAND_LOAN + OTH_LOANS` for 911 of 912. At others, `OTH_LOANS` is blank for 103 of 109 with a nonzero `TTL_LOANS`: Form 3X has one loans line.
- **A4.** `TTL_LOAN_REPYMTS = CAND_LOAN_REPYMNT + OTH_LOAN_REPYMTS` for 586 of 588. `OTH_LOAN_REPYMTS` is filled at every form's filers (9,202 of 9,231 PACs), `TTL_LOAN_REPYMTS` at 214 of them, so the two parts are stored and the total is not.
- **Form 5 and Form 7 rows.** The 208 type-I committees fill only `INDT_EXP` (200 nonzero) and the two dates; the 68 type-C committees only `TTL_COMMUNICATION_COST` (65 nonzero), `INDT_EXP` at 2, and the dates.
- **Dates.** `CVG_START_DT` and `CVG_END_DT` are filled on every row, `YYYYMMDD`.
