# NEU-2150 — Spec §5 spending: `operating_expenditure`, counting rules, categories, payee tables; glossary; ADR on payees

**Ticket:** [NEU-2150](https://linear.app/neuroticsasquatch/issue/NEU-2150) · **Project:** P-NEU-107 "fundlens: every FEC dollar" · **Milestone:** M2 Spending · **Parent story:** NEU-2148
**Project spec:** `fundlens-every-fec-dollar-project-spec.md` §5 (a stub this ticket fills), §2 (older builds), §3 (file catalogue), §4.4 and §4.5 (reported operating expenditures, reconciliation), §8 (public dataset) · **v1 spec:** §4 (the credit rule, superseded filings, repeated rows), §6.7 (display values), §7.1, §9 · **Glossary:** `CONTEXT.md` · **ADRs:** 0006 (itemized detail from Parquet), 0011 (organizations are grouped, not resolved), 0012 (written in this session)
**Blocked by:** NEU-2137 (Done), NEU-2130 (Done), NEU-2149 (Done: `docs/measurements/oppexp-2024.md`, "the measurement" below). **Blocks:** NEU-2152, and through it NEU-2153 to NEU-2160. **Related:** NEU-2151 (catalogue and extract).

Planned 2026-11-20. `/implementit NEU-2150` produces **one docs PR**: project spec §5 written out, the six `CONTEXT.md` terms and ADR 0012 this planning session already wrote (uncommitted), the ADR's entry in root `CLAUDE.md`, one edit to the v1 spec (§9's table list), and the Linear text corrections of §6. Nothing under `sql/`, `src/`, `frontend/` or `tests/` changes. Every figure below is the measurement's, quoted with its question number, except where this spec says it derived one.

## 1. What and why

Nine tickets (NEU-2151 to NEU-2159) and the run (NEU-2160) build spending from one contract that is not written down: project spec §5 holds only the milestone's five shared contracts. This ticket writes it.

The ticket text predates the measurement, and differs from what this spec pins in these places:

1. The milestone says a sub-itemized payment counts at "the parent or its children … as the measurement ticket decides", and that `MEMO_CD = 'X'` rows are not counted. The measurement decided parent always, which needs one exception: a parent filed as a memo row counts.
2. The milestone's category list has 11 entries. The measurement's has 15.
3. The milestone and NEU-2153 read FEC's `CATEGORY` first. The measurement found its commonest code wrong on 96% of its dollars.
4. NEU-2152 keeps a superseded filing's rows with `counted = false`. `contribution` drops them.
5. The ticket's columns have no candidate, no link from a sub-item to its parent, and nothing that tells a person from a firm or marks an in-kind outlay.
6. The ticket gives every payee a page. The measurement handed over people, card issuers, in-kind outlays and names that name nobody as open questions.
7. NEU-2155 leaves `payee_id` to this spec.
8. NEU-2152's target is the measurement's $9,715,514,602, which includes $121,230,310 at filers `cm` does not hold, rows the same ticket drops (§2, §5.1 "2024 on this contract").

### 1.1 Decisions pinned (grilled 2026-11-20)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Sub-itemization, across cycles | **Parent always, in every cycle 2004–2026.** A parent counts, whatever its memo code. A sub-item never counts. | One rule: a payee's dollars mean the same in every cycle, and 2024 stays within $194,596 of FEC's own non-memo rule (Q3). Rejected: the 50% bar per cycle (ten cycles pass and 2016 and 2024 fail, Q2c, so a payee's 2022 and 2024 totals would be built by different rules, and the current cycle could flip as filings arrive); children wherever they add up, in every cycle (overrides the measurement's decision and the counted figures NEU-2152 and NEU-2160 are held to). |
| Category precedence | **The purpose rule first; a trusted FEC code where no pattern matches; else `other`.** Trusted: 002, 004, 005, 011, 102, 106. | The labels were made from purposes, and code 001 agrees with them on 3.57% of its $511.1M (Q8g). Purpose first also puts a code-004 row whose purpose says digital in `digital`. Rejected: the contract as written (about $493M of code-001 spending in the labelled set alone filed as `administrative`); trusted code first (15% of 004's labelled dollars, mostly digital, become `media`). |
| Category list | **The measurement's 15**, `credit_card` included. Every row gets a category, sub-items too. | The 2% bar was pinned by NEU-2149's spec and the test set is labelled in the 15. A sub-item is shown in the itemized list and needs a label there. |
| A superseded filing's rows | **Dropped in silver**, as `04_contribution.sql` drops them. | `counted = false` then means one thing: a memo row or a sub-item. The itemized list and the dataset never show a payment twice. Rejected: kept with `counted = false`, as NEU-2152 says (a reader could not tell a superseded copy from a sub-item without a second column). |
| Amendment rule | **The receipt side's `superseded_filing` set alone** (measurement Decision 2). The payment-side rule and its same-report variant are not adopted. | The variant would add 13 filings and $19,286, 0.0002% of counted spending, for a fourth rule (Q6e2). |
| People as payees | **No page and no search entry.** A person is a payee in silver, in the itemized list and in a committee's top payees, by name, unlinked. | 1,380 of 2024's 37,072 person keys already span two states or more (Q9g): a bare name cannot claim one recipient across committees, and a page would make anyone a campaign reimbursed searchable. Rejected: pages for everyone (`JOHNSON ROBERT` is one page for people in five states); a person's key with the state added (a consultant paid in two states is two payees, and the key stops being ADR-0011's). |
| Who is a person | **`ENTITY_TP` `IND` or `CAN`; when it is blank, a name `is_organization_name` (NEU-2132) does not call an organization.** Stored per row as `payee_is_person`. | `ENTITY_TP` is blank on 9.6–29.5% of dollars in 2006–2018, and the blank rows skew large, so they are mostly firms (Q2d). Rejected: blank is never a person (every blank-typed person of 2006–2018 gets a page); blank is always a person (the blank-typed media firms lose their pre-2020 history). **Asserted, not measured** on payee names: NEU-2180 checks it. |
| The grain of the person rule | **Per payee key, by majority of dollars.** A key is a person's when more than half of its payee dollars (§5.4), over every cycle in gold, are on person rows. | A firm one committee types `IND` and another `ORG` keeps one page with both; one mistyped `ORG` on `SMITH, JOHN` makes no page; a payee's total always equals its key's rows. Rejected: per row (the firm's page omits a committee); any person row hides the key (one mistyped row takes down a large firm's page). |
| Card issuers | **A page like any payee.** | The committee did pay American Express ($195.2M in 2024, Q9b), and FEC's totals count the bill. The rows carry `credit_card`, and the itemized list shows the charges under each bill. Rejected: a hand-kept issuer list, to hide or to flag (upkeep, and it hides or decorates a true fact). |
| In-kind outlays | **Counted in the committee's spending; credited to no payee.** `is_in_kind` is true for a sub-item whose parent is not in the file, or a row whose purpose matches `IN[- ]?KIND`. | The row names the giver as payee, who was paid nothing. The structural rule alone covers $19.6M; purposes naming in-kind on ordinary rows hold far more ('IN-KIND CONTRIBUTION' is $53.3M, $52.0M of it naming `UNITED STATES OF AMERICA`). Rejected: the structural rule alone; the purpose pattern alone (misses sub-items whose purpose is `ARTWORK`, $6.3M); proving each against the receipt files (a join to `indiv` inside a transform about 2.4 GiB under its limit). The pattern's precision is **asserted, not measured**: NEU-2160's payee review checks it. |
| Names that name nobody | **A vendored list, `fec/payee_no_page.csv`**, of payee keys treated as a person's key is: counted, listed on the committee, no page. Seeded from Q9e. | `PETTY CASH` would be one page "paid" by 19 unrelated committees. Rejected: nothing (searchable `UNITEMIZED` and `PETTY CASH` pages); a pattern (`CASH APP` and `PAYROLL DATA SERVICES` are real payees). |
| Candidate and race spending | **Silver gives each row a `candidate_id` by `04_contribution.sql`'s credit rule, handoff link included.** Biden's committee's spending dated before 2024-07-21 is Biden's, from then on Harris's. | The glossary's Handoff, and each candidate's raised and spent figures on one footing. Rejected: whole to the second candidate, as reported totals (Biden shows money raised and none spent); no candidate in silver (the same outcome). |
| Reconciliation | **A second `measure`, `operating_expenditures`**, built by NEU-2154. | The table and its publishing exist, and it is the only outside check on the counting rules (63 committees over by $1.09M in 2024, Q11). Rejected: the run's ten committees alone (a later excess goes unseen); a spending coverage ratio (parties sit at 83.83% because the file has no line 21(a), which a ratio would need page copy to explain). |
| `payee_id` | **The first 16 hexadecimal characters of the SHA-256 of `payee_key`**, lower case. | Deterministic, so links survive a rebuild with no crosswalk (NEU-2155's rejected sequence). 64 bits: a collision among a few million keys is negligible, and a gold check fails the build on one. |
| Split firms | **Joined by an alias in `resolve/aliases.yaml`, each filed as a Bug from NEU-2160's payee review**, the measurement's three first. Not inside M2's build tickets. | An alias regroups employers and organizations too (ADR-0011, ADR-0012), so each is its own reviewed change. |
| A committee as payee | **A payee by name, with no link to its committee page.** | Four of 2024's top 100 keys are committees (Q9b). Matching names to `cm` is NEU-2131's rule for givers, unmeasured for payees. |
| Missing spending | **`total_operating_expenditures` is NULL, never 0, where a committee, candidate or race has no counted row in the cycle.** | A cycle before 2004, or one whose live build lacks the table (project spec §2), must not read as "$0 spent". As §4.4's reported fields. Pinned by this spec without a question; say so in the PR. |
| Glossary | **Six terms**, written in this session: the ticket's four, plus **Sub-item** and **In-kind outlay**. | Tickets word a sub-item three ways ("memo children", "child rows", "sub-items") and an in-kind outlay two. |
| ADR | **0012, written in this session**, wider than the ticket's outline: it also records that people and no-payee names have no page, that a sub-item reaches no payee, and `payee_id`. | Each is hard to reverse once links and totals are public. |

## 2. The document: project spec §5

Replace §5's closing "**Filled by** NEU-2150 …" line with the subsections below. Keep the opening paragraph. Replace the five shared contracts with the amended five given first (the same text goes into the milestone, §6). Write each rule with its measurement citation, as given here ("Q" and "Decision" numbers are the measurement's). Where a rule rests on no measurement it says "asserted, not measured" and names the ticket that checks it.

**Shared contracts (amended):**

- A sub-itemized payment counts once, at its parent, in every cycle: the parent counts whatever its memo code, and a sub-item never does. Every other `MEMO_CD = 'X'` row is not counted.
- Refunds and offsets net out: amounts are summed as filed.
- Payees are grouped by `payee_key`, the rule that makes an organization key (`organization_key`, ADR-0011), never resolved with Splink. A payee page lists who paid it, by cycle. A person, or a name that names nobody, has no page (ADR-0012).
- `spending_category` is one of a fixed list of 15, from a measured purpose-text rule, else from FEC's `CATEGORY` where the code is one filers use reliably, else `other`.
- Spending is never a contribution and never in any receipt total.

### §5.1 Silver `operating_expenditure`

`sql/silver/12_operating_expenditure.sql` (NEU-2152), from `oppexp`. Key `(cycle, source, source_record_id)`. `source` is `fec` and `jurisdiction` `US`, as every silver table's (v1 §4).

Columns, in order:

| Column | From | Notes |
|---|---|---|
| `cycle`, `source`, `source_record_id`, `jurisdiction` | `SUB_ID` | Unique in the file (Q1a) |
| `committee_id` | `CMTE_ID` | The committee that paid |
| `candidate_id` | — | Nullable. `04_contribution.sql`'s credit rule applied to `committee_id` and `date` (v1 §4; project spec §4.3): linked P or A, or the committee `candidate.principal_committee_id` names; a handoff's committee by the row's date; a candidate alias is credited none |
| `payee_name` | `NAME` | As reported |
| `payee_key` | — | `organization_key(NAME)`, evaluated once per distinct name. NULL only for a row with no name (91 counted rows, $34,042, Q9c) |
| `payee_city`, `payee_state`, `payee_zip` | `CITY`, `STATE`, `ZIP_CODE` | As reported |
| `payee_is_person` | — | §5.4 |
| `amount` | `TRANSACTION_AMT` | `DECIMAL(14,2)`, as filed, negative amounts included (§5.2) |
| `date` | `TRANSACTION_DT` | `DATE` from `MM/DD/YYYY`. A filer's impossible year is kept as filed (years 1201 to 9201 appear in every cycle, Q2) |
| `purpose` | `PURPOSE` | As reported |
| `fec_category` | `CATEGORY` | FEC's code as a three-character string: one written without its leading zeros (`1`, `01`) is the code it pads to. Any other value is kept as filed |
| `spending_category`, `category_source` | — | §5.3. NULL until NEU-2153 |
| `election_code` | `TRANSACTION_PGI` | |
| `report_type`, `amendment_indicator` | `RPT_TP`, `AMNDT_IND` | |
| `memo_code`, `memo_text` | `MEMO_CD`, `MEMO_TEXT` | |
| `entity_type` | `ENTITY_TP` | As filed, blank as NULL |
| `tran_id`, `back_ref_tran_id` | `TRAN_ID`, `BACK_REF_TRAN_ID` | |
| `parent_source_record_id` | — | Nullable. The `source_record_id` of the row on the same committee and filing whose `TRAN_ID` is this row's `BACK_REF_TRAN_ID`, other than the row itself: a row naming its own `TRAN_ID` is no sub-item (4 rows in 2024, the measurement's setup). Set, the row is a sub-item (`CONTEXT.md`). Where a filing holds that `TRAN_ID` on two rows, the lower `SUB_ID` (none does in 2024 once repeated rows are read once, Q5d) |
| `image_num`, `file_num` | `IMAGE_NUM`, `FILE_NUM` | |
| `is_in_kind` | — | §5.4 |
| `counted` | — | §5.2 |

Not held: `RPT_YR`, `LINE_NUM`, `FORM_TP_CD`, `SCHED_TP_CD`, `CATEGORY_DESC`. The file holds three lines and nothing else, Form 3 line 17, Form 3P line 23 and Form 3X line 21(b), plus 47 rows on a line written `21` (Q1d). Adding a column later is an additive dataset change.

**Rows.** Every `oppexp` row whose committee is a committee of the cycle in silver `committee`, except:

- A **repeated row** (`CONTEXT.md`) is read once: `register_bulk` drops the copies, since `oppexp` has all four `TRANSACTION_KEY` columns. 2,943 rows, $3,238,816, on 11 filings in 2024; the raw filings hold each transaction once (Q5).
- A row on a **superseded filing** is dropped, as `contribution` drops it: `FILE_NUM` in `04_contribution.sql`'s `superseded_filing` set, the receipt side's, alone (Decision 2). 47 filings in 2024, 26 of them with `oppexp` rows, $15,117,610 of counted spending (Q6). The model must run where that set is in scope, or build it from the same three statements. A payment-side rule would add 23 filings and $124,469, of which 10 filings and $105,184 are a different report repeating payments, not an amendment; neither it nor its same-report variant (13 filings, $19,286) is adopted (Q6e, Q6e2).
- A row whose filer `cm` lacks is dropped, as `independent_expenditure`'s is: 3 filers, 18 rows, $121,715,789 in 2024, $121.2M of it one filer's four rows paid to itself (Q1h, Q9b).

No row is dropped as an overlap: no `oppexp` row shares a `SUB_ID`, or a filing, `TRAN_ID` and amount, with `pas2`, `oth` or `indiv`, and none is a silver `committee_transfer` or `independent_expenditure` row (Q7, Decision 3). There is no paper row to treat differently: no cycle has more than 4 rows without a `TRAN_ID` (Q4c).

Every sub-item and every memo row is kept, with `counted` false, so the itemized list can show a card bill's charges without counting them twice. Rejected: dropping them, and a second table for them.

**2024 on this contract.** The measurement counted 1,550,230 rows and $9,715,514,602 (R4, every filer). Of those, 5 rows and $121,230,310 are at filers `cm` lacks (Q8a, Q11e). So silver's 2024 partition should count **1,550,225 rows and $9,594,284,292**. This spec derived both by subtraction; NEU-2152's definition of done is within 1% of them.

**Checks** (NEU-2152): `silver_operating_expenditure_key.sql` (key unique); `..._committee.sql` (committee in `committee`); `..._counted_once.sql` (no row with `parent_source_record_id` set is counted); `..._no_contribution.sql` (no `source_record_id` is in `contribution`, `committee_transfer`, `organization_receipt` or `independent_expenditure`; the measurement found none, Q7).

**Memory.** The table holds about 0.87 GiB for 2024, which puts the transform's peak at about 27.35 GiB under the 29.80 GiB limit. NEU-2152 writes the table and drops it before `contribution`'s write, the transform's peak, if it can (Q1, Decision 7).

### §5.2 What counts

`counted` is the one flag every total reads:

1. A row with `parent_source_record_id` set, a **sub-item**, is not counted. This includes a row that is both a sub-item and a parent, the middle of a chain: chains are 8 rows, $10,804, in 2024, and none of a chain counts but its top parent (Q3f).
2. Otherwise, a row that some sub-item names as its parent is counted, **whatever its memo code**. 30 parents are memo rows in 2024, $164,432 (Q3m). This is the one exception to "memo rows are not counted".
3. Otherwise, a row is counted when `MEMO_CD` is not `X`. That covers an ordinary payment, and a row with `BACK_REF_TRAN_ID` filled whose parent is not in the file (7,284 in 2024, 5,552 of them naming a receipt on their filing: in-kind outlays, §5.4; Q3a, Q7c).

This is the measurement's R2, "parent always" (Decision 1), applied in every cycle FEC publishes the file for.

- **Why the parent.** 80,249 parents carry 670,054 sub-items in 2024. A parent is fully itemized when its sub-items add up to it within $1.00. Fully itemized parents hold $250,483,113 of the $524,208,828 parents carry, 47.78%: under the 50% bar NEU-2149's spec set for counting sub-items instead (Q3j). Card bills are what does not add up: 28.27% of card parents' dollars are fully itemized, against 71.25% of other parents' (Q3b).
- **One rule for every cycle.** The bar is met in ten of the twelve cycles, from 51.09% (2022) to 84.68% (2008), and fails in 2016 (47.73%) and 2024 (Q2c). It is not applied per cycle: a payee's totals would be built by different rules from one cycle to the next, and the current cycle could change rules as filings arrive.
- **What it costs.** No sub-item reaches a payee: $503.0M in 2024, $250.5M of it under fully itemized parents. Card issuers keep $192,903,671 of card bills that are not fully itemized (Q3j). A payee's total is what committees reported paying that name directly.
- **Against FEC's own rule** (non-memo rows), parent always differs by $194,596 in 2024 (Q3l, Q3m).
- **Sign: as filed** (Decision 4). A negative row subtracts, and nothing is negated or dropped for its purpose. Negative rows net −$191.5M of 2024's counted spending, $109.1M of it super PACs moving a payment to Schedule E, which then counts once, in `independent_expenditure`. Counting every amount positive would add $383.1M, and dropping the negatives $191.5M (Q10g). This is the contract's "refunds and offsets net out".
- **Against FEC's reported figure.** At the 9,909 committees with a reported figure above $0, counted spending is $9,594,311,329 against $9,916,558,902 reported: the median committee is at 98.76%, and 63 are more than 1% over, by $1.09M (Q11). Itemized spending sits below the reported figure by design: payments of $200 or less in a year are unitemized. Parties are at 83.83%: the file has no row on Form 3X line 21(a), their shared federal and nonfederal spending (Q1d, Q11b).

### §5.3 Spending category

Every row has one `spending_category` (`CONTEXT.md`), counted or not, from this list:

| Slug | Holds |
|---|---|
| `media` | Paid advertising in broadcast, cable, satellite, radio, print and out of home, its production and placement; an ad or "media" buy whose medium is unnamed |
| `digital` | Online advertising, text and email messaging, websites and hosting, digital organizing and consulting, campaign data and voter-file services |
| `mail` | Direct mail and printed material: design, printing, postage and lettershop, whether it persuades voters or asks them for money |
| `fundraising` | The cost of raising money: fundraising consultants and commissions, online fundraising, list rental and acquisition, telemarketing, merchandise, a fundraising event's costs where the purpose names fundraising |
| `payroll` | Pay to staff and its costs: salary, payroll taxes and withholding, benefits, payroll processors |
| `consulting` | General, political, strategic, management and communications consulting whose purpose names no other category |
| `field` | Voter contact in person and by phone: canvassing, field and relational organizing, voter registration, paid calls to voters |
| `polling_research` | Polling, surveys and focus groups, and opposition and policy research |
| `travel` | Air and ground travel, lodging, mileage, meals while travelling |
| `events` | Putting on an event: venue, production and staging, audio-visual, catering, advance |
| `administrative` | Running an office: rent, utilities, software, equipment, supplies, insurance other than staff's, taxes other than payroll's, security |
| `legal_compliance` | Legal services, compliance, accounting and FEC reporting |
| `transfers_fees` | Money passed on (transfers, contributions, donations, refunds, loan repayments) and fees charged per payment processed: merchant, card-processing, conduit and bank fees |
| `credit_card` | A card bill, counted as the bill: what it bought is itemized, if at all, only in sub-items |
| `other` | Anything else, and a purpose that names nothing bought (`SEE MEMO`, `OPERATING EXPENDITURE`) |

The milestone's 11 became 15 by the 2% bar NEU-2149's spec set: `mail` (7.39% of the labelled set's dollars), `field` (2.62%), `polling_research` (2.62%) and `credit_card` (2.38%) (Q8f). The definitions and the eleven tie-breaks (T1 to T11) are the measurement's Q8; the classifier follows them.

**Precedence**, first that applies:

1. **The purpose rule** (NEU-2153): an ordered list of patterns over the purpose, upper-cased, trimmed and with runs of whitespace made one space; the first match wins. `category_source = 'purpose_rule'`.
2. **A trusted FEC code**: 002 `travel`, 004 `media`, 005 `polling_research`, 011 `transfers_fees`, 102 `media`, 106 `polling_research`. `category_source = 'fec'`.
3. `other`, with `category_source = 'unclassified'`.

- **Why the purpose first.** `CATEGORY` is filled on 28.94% of counted rows and 16.20% of counted dollars (Q8a), and code 001 is a catch-all: filers write it on payroll ($121.1M), media ($65.8M), digital, mail, fundraising, consulting and legal work alike, so the labels agree with it on 3.57% of its $511,096,243 (Q8g, Q8h). The six trusted codes agree with the labels on 84.98% to 100% of their dollars. Even 004 cannot tell `digital` from `media`, which the purpose can.
- **Codes not trusted**, read by purpose alone: 001 (3.57%), 003 (64.58%), 006 (74.95%), 007 (51.75%), 101, 104 (6.82%), 107 (16.58%), and 008, 009, 010, 012, 103 and 105, which have too few labelled dollars to judge (Q8g). Trusting another code is a measured change.
- `fec_category` keeps FEC's code whatever the precedence did with it. FEC's 19 codes and what each means are the measurement's Decision 5 table.
- The test set is `tests/fixtures/spending/purpose_labels_2024.csv`: 200 purposes holding 76.75% of counted dollars, 35 of them judgement calls with reasons. **Asserted, not measured:** that the purpose rule and the six codes leave under 10% of counted dollars `unclassified`; NEU-2153's definition of done measures it.
- NEU-2153 adds its method note for the methodology page here.

### §5.4 Payees

- **Payee key** (`CONTEXT.md`, ADR-0012). `payee_key = organization_key(payee_name)`, the function organizations use: `normalize_employer`, falling back on the cleaned name. Exact grouping, no linkage, across committees and cycles. 105,313 raw names become 98,975 keys in 2024; the top 100 keys hold 52.37% of counted dollars and the top 1,000 hold 80.26% (Q9a). Read by eye, the top 100 hold no wrong merge and three split firms (`AX MEDIA` and `AXMEDIA`; `TEAM DIRECT` and `TEAMDIRECT`; `MISSIONWIRED`, `ANNE LEWIS STRATEGIES` and `ANNE LEWIS STRATEGIES LLC DBA MISSIONWIRED`), each joined by an alias in `resolve/aliases.yaml`, filed as a Bug from NEU-2160's payee review (Q9b).
- **Payee rows.** The rows payee figures read: `counted`, `payee_key` not NULL, `is_in_kind` false. "Payee dollars" below are their net amount.
- **A person** (`payee_is_person`, per row): `entity_type` is `IND` or `CAN`; or it is blank, the row has a name, and `is_organization_name` (v1 §4, NEU-2132) does not call the name an organization. 37,072 keys and $547.3M are `IND` in 2024 (Q9f). `ENTITY_TP` is filled on 99.98% of dollars from 2020 and blank on 9.6–29.5% in 2006–2018 (Q2d). **Asserted, not measured:** that the classifier, measured on `indiv`'s names, reads payee names as well; NEU-2180's backfill measures it on a 2006–2018 cycle before publishing one.
- **A key with no page.** A payee key has no `payee` row, no `payee_id` and no search entity when more than half of its payee dollars, over every cycle in gold, are on person rows, or when it is listed in `fec/payee_no_page.csv`. Its rows are counted and listed on the committee that paid them like any other. The list is vendored and hand-kept, one `payee_key` per row with a `reason`, seeded from Q9e's sixteen candidates (`UNITEMIZED …`, `PAYROLL`, `PETTY CASH`, `CASH`, `ATM`, `CASH WITHDRAWAL` and their variants: about $270,000 in 2024), each read before it is listed: `VARIOUS PRESSURES` may be a firm. NEU-2155 creates it; NEU-2160's review adds to it.
- **An in-kind outlay** (`CONTEXT.md`; `is_in_kind`): a row with `BACK_REF_TRAN_ID` filled and no parent in the file, or a row whose purpose, upper-cased, matches `IN[- ]?KIND`. It keeps its `counted` and its category, and is in no payee figure: its payee is the gift's giver. 5,552 of 2024's 7,284 parentless sub-items ($18,833,378) name a receipt on their own filing, mostly `indiv` 15 and 10 and `oth` 15Z and 18G (Q7c); the other 1,732 ($1,327,593) are flagged on the same structure. On ordinary rows, 'IN-KIND CONTRIBUTION' is 458 rows and $53.3M, and two single rows hold $23.0M in bitcoin and $15.5M in USDC (the labelled set). **Asserted, not measured:** the pattern's precision, and that a purpose avoiding the words ('24,999,995 USDC RECEIVED, NOT LIQUIDATED') is rare; NEU-2160's payee review checks both.
- **A card issuer is a payee like any other.** `AMERICAN EXPRESS` is 2024's third-largest key, $195.2M from 632 committees (Q9b). Its total is bills, not purchases, and the methodology page says so.
- **A conduit as payee.** ActBlue is paid $136.0M and WinRed $115.8M, nearly all fees per contribution processed, `transfers_fees` (Q10a, Q10b). They are payees by name, as any committee that appears as one is (four of the top 100 keys): no link to a committee page.
- **`payee_id`**: the first 16 hexadecimal characters, lower case, of the SHA-256 of `payee_key` (UTF-8). It is a page's address and nothing else. It changes when the key does (ADR-0012).

### §5.5 Gold

Adds to v1 §7.1. Every amount is net: counted rows' amounts added as filed.

| Table | Added or new | Built by |
|---|---|---|
| `committee_cycle` | `total_operating_expenditures`: the committee's counted rows, in-kind outlays included | NEU-2154 |
| `committee_spending_category` | `(committee_id, cycle, category, amount)`, key the first three: the committee's counted rows by `spending_category`. A category with no counted row has no row; one netting to $0 or less is kept, so the rows add up to `total_operating_expenditures` | NEU-2154 |
| `committee_top_payee` | `(committee_id, cycle, rank ≤ 100, payee_key, payee_id, name, amount)`: payee rows grouped by key, ranked by amount then key; a key netting to $0 or less is left out. `name` is the key's reported spelling with the most payee dollars in the cycle, chosen as `committee_top_organization.name` is. `payee_id` is NULL for a key with no page (§5.4) | NEU-2154 |
| `candidate_cycle` | `total_operating_expenditures`: counted rows by silver's `candidate_id` | NEU-2154 |
| `race_candidate` | `total_operating_expenditures`: the candidate's `candidate_cycle` value | NEU-2154 |
| `race` | `total_operating_expenditures`: the sum over its candidates | NEU-2154 |
| `payee` | `(payee_id, payee_key, display_name, city, state, total_all_cycles, first_cycle, last_cycle)`, key `payee_id`, `payee_key` unique: one row per key with a page and at least one payee row. Each display column is chosen on its own by most payee dollars over every cycle, as `donor`'s are (v1 §6.7) | NEU-2155 |
| `payee_cycle` | `(payee_id, cycle, total, committee_count)`, key the first two | NEU-2155 |
| `payee_top_payer` | `(payee_id, cycle, rank ≤ 100, committee_id, candidate_id, amount)`: the committees that paid the payee most in the cycle, ranked by amount then `committee_id`; one netting to $0 or less is left out. `candidate_id` is the rows' silver `candidate_id`, the one with more of the amount where a handoff gives two, NULL when none | NEU-2155 |
| `search_entity` | `kind = 'payee'`: `id` is `payee_id`, `name` is `display_name`, `aliases` the key's other reported spellings, most payee dollars first, `weight` is `total_all_cycles` | NEU-2155 |

- **NULL, never 0, where there is no counted row.** `total_operating_expenditures` is NULL for a committee or candidate with no counted row in the cycle, and for a race none of whose candidates has one. So a cycle before 2004, and one whose live build lacks the table (§2, older builds), reads as "not available", not as nothing spent (NEU-2158 shows it so). A committee whose counted rows net to $0 has 0.
- **The handoff.** `candidate_cycle` follows silver's dated credit: of `C00703975`'s 2024 spending, what is dated before 2024-07-21 is Biden's and the rest Harris's. `reported_operating_expenditures` is whole Harris's (§4.3), so the two are not comparable for either candidate, and no ratio of them is stored. **Asserted, not measured:** how `04_contribution.sql`'s rule credits an undated row; `oppexp` has none in 2024 (Q1a), and NEU-2152 follows the rule as written.
- **A campaign turned PAC** counts whole, as its itemized receipts do (§4.3).
- Spending is in no receipt total, no `cycle.total_amount`, no donor figure and no top-donor, top-organization or top-committee list.
- The three split firms and a firm paid under a person's name are known gaps, not bugs of the gold tickets.
- **Checks** (gold): a committee's `committee_spending_category` rows add up to its `total_operating_expenditures`; every `committee_top_payee` and `payee_top_payer` amount equals its silver sum; ranks are contiguous (`gold_rank_contiguous.sql`); `payee_id` is unique and `payee_key` is unique in `payee`; no `payee` row's key is in `fec/payee_no_page.csv`.

### §5.6 Reconciliation

Adds a second `measure` to §4.5's table: `operating_expenditures`. `fundlens` is `committee_cycle.total_operating_expenditures`, `reported` is `reported_operating_expenditures`, `ratio` is `fundlens ÷ reported`. A committee is listed by §4.5's rule: `reported` not NULL and `fundlens − reported > 0.01 × reported`; a reported 0 beside counted spending is listed with `ratio` NULL; no dollar floor; over only. Conduits are not left out: the exclusion is the receipt measure's. 2008 on, since no earlier file has the measure (§4.7). Never failing the build. Built by NEU-2154.

On the measurement's figures, 2024 would list 63 committees over by $1.09M, and 12 with a reported $0 beside counted money: Q11c's 16 less the 4 with no reported figure at all, which are not listed (Q11a, Q11c, Q11e). No shortfall is listed: itemized spending sits below the reported figure by design (§5.2).

### §5.7 What each cycle range has

| | 2020– | 2006–2018 | 2004 | 1980–2002 |
|---|---|---|---|---|
| `operating_expenditure` | yes | yes | yes | an empty partition (§2) |
| Counting rules (§5.2) | as written | as written | as written | — |
| A person by `ENTITY_TP` | filled on 99.98% of dollars | blank on 9.6–29.5% of dollars: the name classifier decides | blank on 2.6% | — |
| `reconciliation` measure | yes | from 2008 | no | — |

Every cycle has the same three lines, the same parent and sub-item links (92–99% of rows with `BACK_REF_TRAN_ID` have their parent in the file) and no paper rows (Q2, Q4c). Memo dollars are 21.22% of 2004's file against 5–8% later; its parents are fully itemized for 79.71% of their dollars, so its memo rows mostly restate their parents (Q2b, Q2c). Senate campaigns filed on paper until 2018 and their operating expenditures are not in the file at all (Q4): a gap in FEC's bulk data, §9's to recover.

### §5.8 Dataset and older builds

`operating_expenditure` joins the public dataset (§8): NEU-2152 adds it to `DATASET_TABLES`, `columns.yaml`, the schema, the changelog, the README and `paths.BACKFILL_PENDING` in the PR that builds it. Its README entry says: sum only rows where `counted` is true; a sub-item is shown under its parent and never added to it; `payee_key` is a normalized name, not an id (ADR-0012); and spending is never to be added to `contribution` amounts. `spending_category` and `category_source` are NULL in a build made before NEU-2153.

## 3. `CONTEXT.md`

Written in this session, uncommitted. Under **Money**, after Organization receipt: **Operating expenditure**, **Sub-item**, **In-kind outlay**, **Spending category**. Under **Parties**, after Organization: **Payee**. Under **Resolution**, after Organization key: **Payee key**. Each has its avoid list; the ticket's "vendor" and "spend" are in Payee's and Operating expenditure's. **Donor**'s second sentence now names payees beside organizations as grouped, not resolved.

`/implementit` commits them as they stand and checks that §5's text uses them: "payee", never "vendor"; "sub-item", never "child" or "memo child"; "operating expenditure" or "spending", never "spend" as a noun or "expense". The measurement's own words ("parent", "child", "orphan") stay in the measurement; §5 says "parent" for the row a sub-item itemizes, which the glossary does not define and need not.

## 4. ADR 0012

`docs/adr/0012-payees-are-grouped-like-organizations.md`, written in this session, uncommitted, `status: accepted`, in 0011's form. `/implementit` commits it as it stands, checks each figure in it against the measurement, and extends root `CLAUDE.md`'s decisions line: "…, 0011 organizations are grouped by normalized name, not resolved, 0012 payees are grouped like organizations and get pages; people and sub-items do not".

ADR-0011 is not edited: its "no pages" is about organizations that give.

## 5. The specs' other edits

- **v1 spec §9**, the layout block's table list: add `operating_expenditure` after `candidate_reported_total`.
- **Project spec §2**, the "Payees and organizations" row: "The payee ADR (NEU-2150) will be 0012." becomes "Payees: ADR-0012."
- **Project spec §5's** third contract already names the ADR; the amended contracts of §2 above replace it.
- v1 §2's file-table row for `oppexp` ("not loaded in v1") is NEU-2151's to amend, as its ticket says. v1 §7.1's table rows are the gold tickets' (NEU-2154, NEU-2155), as v1's gold tickets added theirs.

## 6. Linear text this spec supersedes

`/implementit` patches each, changing only the named text, and appends to each "Amended 2026-11-20 by project spec §5 (NEU-2150)."

| Where | Text | Becomes |
|---|---|---|
| Milestone M2 Spending, shared contracts | The five bullets | §2's amended five |
| NEU-2152 | "`counted` … false on superseded amendment rows and on rows spec §5 assigns to `pas2`/`oth`" | A superseded filing's rows are dropped, as `contribution`'s are; no row is an overlap (§5.1). `counted` is §5.2's three rules. |
| NEU-2152 | "with spec §5's columns" | Including `candidate_id`, `payee_is_person`, `parent_source_record_id` and `is_in_kind` (§5.1). |
| NEU-2152 | "`..._counted_once.sql` (no counted child whose parent is also counted)" | No row with `parent_source_record_id` set is counted. `..._no_contribution.sql` also reads `contribution` and `organization_receipt`. |
| NEU-2152 | "within 1% of NEU-2149's figures" | Within 1% of 1,550,225 counted rows and $9,594,284,292: the measurement's figures less the filers `cm` lacks (§5.1). |
| NEU-2153 | Title and "FEC CATEGORY maps by spec §5's table; otherwise an ordered list of normalized-purpose patterns" | The purpose patterns first; a trusted code (002, 004, 005, 011, 102, 106) where none matches; else `other`/`unclassified` (§5.3). Title: "Spending-category classifier: a measured purpose-text rule first, then FEC's trusted CATEGORY codes". |
| NEU-2154 | "`committee_spending_category` … every category present for the committee, 0 omitted" | A row per category with a counted row; one netting to $0 or less is kept (§5.5). |
| NEU-2154 | "`committee_top_payee` … (`payee_key`, display name, amount)" | Adds `payee_id`, NULL for a key with no page; in-kind outlays left out (§5.5). |
| NEU-2154 | "`race.total_operating_expenditures` and `race_candidate.total_operating_expenditures` over each candidate's committees through the v1 `ccl` rule" | By silver's `candidate_id`; also `candidate_cycle.total_operating_expenditures`; NULL, never 0, with no counted row (§5.5). Adds the `operating_expenditures` reconciliation measure (§5.6). |
| NEU-2155 | "`payee (payee_key, …)`", "`payee_cycle (payee_key, …)`" | `payee` is keyed by `payee_id` and holds only keys with a page: not a person's by the majority rule, not in `fec/payee_no_page.csv`, which this ticket creates (§5.4). `payee_cycle` and `payee_top_payer` are keyed by `payee_id`. In-kind outlays are in none. |
| NEU-2155 | "a stable `payee_id` (hash of `payee_key`, documented in spec §5)" | The first 16 hexadecimal characters of the SHA-256 of `payee_key` (§5.4). |
| NEU-2155, NEU-2157, NEU-2159 | "References: … ADR 0011" | Adds ADR 0012. |
| NEU-2156 | "memo children nested under or flagged against their parent per `counted`" | Sub-items nested under their parent by `parent_source_record_id`; each row carries `counted`, `is_in_kind` and `payee_id` (NULL with no page). |
| NEU-2158 | "linking each payee to `/payee/:payeeId`" | Only a payee with a `payee_id`; a person or a no-page name is shown unlinked. A missing spending total reads "not available". In-kind outlays are marked in the itemized list. |
| NEU-2160 | "the top 20 payees reviewed for wrong merges" | Also for split firms (the measurement's three, each a Bug adding an alias), for in-kind outlays the pattern missed, and for names to add to `fec/payee_no_page.csv`. Its ten comparisons are against Q11's figures. |

## 7. Acceptance criteria

- [ ] Project spec §5 holds §5.1–§5.8 as written in §2 above, under the opening paragraph and the amended shared contracts, with no "Filled by" line.
- [ ] Every rule in §5 that rests on the measurement cites its question or decision; each unmeasured one says "asserted, not measured" and names the ticket that checks it (the classifier on payee names, the in-kind pattern, the unclassified share, an undated row's credit).
- [ ] §5.1's table names a source column, or "—", for each of the 31 columns, and states the 2024 counted target as 1,550,225 rows and $9,594,284,292 with its derivation.
- [ ] §5.3 lists the 15 categories with a definition each, the three-step precedence, the six trusted codes and the codes not trusted.
- [ ] §5.5 gives every gold table's columns and key, the NULL rule and the gold checks.
- [ ] `CONTEXT.md` defines Operating expenditure, Sub-item, In-kind outlay, Spending category, Payee and Payee key, each with an avoid list, and `grep -n -i -w "vendor\|memo child\|child row" docs/specs/fundlens-every-fec-dollar-project-spec.md` (whole words: "vendored", of a file kept in the repo, is not the term) finds none outside a quoted FEC memo text.
- [ ] `docs/adr/0012-payees-are-grouped-like-organizations.md` is merged with `status: accepted`, every figure in it matching the measurement, and root `CLAUDE.md`'s decisions line lists 0012.
- [ ] v1 spec §9 lists `operating_expenditure`; project spec §2's payee row names ADR-0012.
- [ ] The milestone's contracts and the nine descriptions of §6 are patched in Linear.
- [ ] The PR changes nothing under `sql/`, `src/`, `frontend/` or `tests/`.

## 8. Out of scope

- Any code: the catalogue (NEU-2151), silver (NEU-2152), the classifier and its patterns (NEU-2153), gold (NEU-2154, NEU-2155), API (NEU-2156, NEU-2157), pages (NEU-2158, NEU-2159), the run (NEU-2160).
- `fec/payee_no_page.csv` itself (NEU-2155) and any alias in `resolve/aliases.yaml` (Bugs from NEU-2160).
- v1 §7.1's table rows, v1 §7.2's endpoints and v1 §2's `oppexp` row (their tickets).
- Linking a payee that is a committee to its committee page; resolving payees; industry coding of payees; a redirect for a `payee_id` whose key changed.
- An itemized route or list per payee (NEU-2157's rejected alternative).
- A spending coverage ratio, and any reconciliation of shortfalls.
- Party committees' line 21(a) spending and paper filers' operating expenditures, which the bulk file lacks (project spec §9).
- Measuring any cycle but 2024 in depth: the person rule on 2006–2018 names is NEU-2180's.
