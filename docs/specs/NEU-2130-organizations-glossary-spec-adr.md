# NEU-2130 — Glossary, spec amendment and ADR: organizations, `organization_receipt`, and why organizations are not resolved

**Ticket:** [NEU-2130](https://linear.app/neuroticsasquatch/issue/NEU-2130) · **Milestone:** M3.5 Organization money · **Parent story:** NEU-2128
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §2, §4, §6, §7.1, §9, §14 · **Glossary:** `CONTEXT.md` · **ADRs:** 0004 (earmarks count once), 0005 (overrides in git, crosswalk in Postgres), 0010 (re-clustering; the number the sibling tickets mistook for this one)
**Blocked by:** NEU-2129 (Done, PR #87: `docs/measurements/organization-money-2024.md`). **Blocks:** NEU-2131 (silver `organization_receipt`), NEU-2132 (blank-entity-type classifier), NEU-2133 (gold), and through them NEU-2134, NEU-2135 and NEU-2136.

Planned 2026-11-04. `/implementit NEU-2130` produces **one docs PR**: `CONTEXT.md`, the project spec, a new ADR 0011, and the decisions line in the root `CLAUDE.md`. Nothing under `sql/`, `src/` or `frontend/` changes. Every number below is from the measurement document and is quoted, not re-derived.

## 1. What and why

The domain model has no word for a giver that is neither an individual nor a committee. `CONTEXT.md` says "Only individuals need resolution; committees and candidates already carry regulator IDs", and a corporation, a union or a trade association is none of those. The project spec has no silver table, gold column or dataset entry for their money, and fundlens drops it: `04_contribution.sql` keeps only IND, CAN and blank entity types, `05_committee_transfer.sql` keeps an `oth` receipt only when its giver has a committee id. The measurement (NEU-2129) put the 2024 gap at $2.26 billion of ORG-typed `indiv` money, $1.42B of it to super PACs, plus $23.1M of ORG gifts in `oth` with no committee giver, against $9.82B from individuals.

Three implementation tickets build against this contract, and each reads a different part of it: NEU-2131 the silver table and the committee name-match rule, NEU-2132 the classifier's place in `contribution`, NEU-2133 the gold column and table. This ticket writes the contract once, into the documents the implementers read, so the three cannot drift from each other or from the milestone's shared contracts.

### 1.1 Decisions this spec pins (grilled 2026-11-04)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| The term for an organization's money | **Organization receipt**, its own Money term in `CONTEXT.md`: one itemized gift from an organization to a committee, held in `organization_receipt`. Organization money, **never a contribution**, as a JFC transfer is committee money and never a contribution. | The ticket's proposal, "a Contribution in the glossary sense held in another table": Contribution is defined by its contributor, so the term would name rows in two tables and Contributor (the raw name on a contribution) would have to cover organization names too. One term per table keeps every individual total a sum over `contribution`. |
| `organization_key` | **`resolve.normalize.normalize_employer`** over the reported name: cleaned, its legal form stripped (`LEGAL_FORMS`: INC, INCORPORATED, LLC, CORP, CORPORATION, LTD, LIMITED, CO, COMPANY), its employer alias resolved (`aliases.yaml`). Registered with DuckDB as the contributor normalizers are. The milestone's shorter suffix list is restated as this list. | A second normalizer that strips legal forms without the alias map: two normalizers that drift, and `SPACE EXPLORATION TECHNOLOGIES CORP` and `SPACEX` stay two organizations. The bare letters-and-digits key the committee name match uses: `KOCH INDUSTRIES INC` and `KOCH INDUSTRIES` stay two organizations, which undercuts the ranking the key exists for. |
| `oth` givers with a C-prefixed `OTHER_ID` the cycle's `cm` lacks (`unknown id`: 689 rows, $21.3M in 2024) | **Stand in `committee_transfer`, as today.** A C-prefixed id is a committee id by FEC's convention; the filer named one. It is committee money on the recipient's `total_from_committees` and is never an organization receipt. ADR 0011 says so; `05_committee_transfer.sql` and `silver_committee_transfer_recipient.sql` (which allows a giver `cm` lacks) do not change. | Treating an unknown id like a blank one and keying the row by name: relabels counted committee money as organization money and recovers nothing. Dropping them: loses $21.3M of counted money for no gain. |
| Where organization money shows | **Committee-level only.** `committee_cycle.total_from_organizations` and `committee_top_organization` are the only gold readers of `organization_receipt`. `cycle.total_amount`, every race total, candidate total (`total_individual`, `total_committee`, `total_jfc_transfers`) and donor total are untouched, and the spec says so in §7.1, so a cycle-wide figure needs a deliberate amendment. | Adding it to `cycle.total_amount`: the home page's headline would mix money credited to candidates with money that is not, and no ticket owns the change. A separate `cycle.total_organizations`: a new column, API field and page element, which is a new ticket, not a side effect of this one. |
| Which `oth` lines are an organization's receipts | **Receipt types `1x` and `3x`, except 15J (evidence, `jfc_attribution`) and every loan type: 16C, 16F, 16G.** A loan is not a gift: a bank's 16F is credit and its 16G is the repayment. This is the set the measurement's 18,336-row target counts; NEU-2131's text, which excludes only 15J and 16C, is corrected to say 16x. | Excluding 15J and 16C only: $786k of ORG-typed lender loans and repayments in 2024 would count as organization funding and then net back out. Also excluding the `3x` party-account lines: a union's gift to a party's building account (32J, 31K) is exactly the money S9 is about. |
| A blank-entity-type `oth` receipt with no committee giver | **Out of scope: stays dropped.** The classifier (NEU-2132) runs over `indiv` and the 15J `jfc_line` only. In 2024 the set is one row ($9,609, a 15J line). | Running the classifier over `oth` too: a rule for one row, in a table where the giver is usually a committee. |
| PAC/COM/CCM/PTY rows with a blank `OTHER_ID` | **Join `committee_transfer` when the name names exactly one `cm` committee; drop the rest**, as the ticket states and §2.2 below spells out. Amends the measurement's pinned 95% all-or-nothing bar, which got *drop*. | The all-or-nothing bar: it would drop $788.4M, including the $635.6M that matches cleanly and that FEC itself counts (Senate Leadership Fund's PAC-typed rows, $8,934,545, are FEC's `OTHER_POL_CMTE_CONTRIB` $8,934,548 to within $3; SMP's rows plus its existing transfers match FEC to within $6.1k). |
| Dedupe between `indiv` and `oth` | **By mirror, not `SUB_ID`.** No `oth` organization receipt shares a `SUB_ID` with an `indiv` row; 2 rows ($133,900) mirror a counted `indiv` row (same recipient, name key, amount and date). `organization_receipt` reads the `indiv` row and drops the `oth` mirror. | Dedupe by `SUB_ID` alone: misses both mirrors. |
| The ADR's number | **0011**, `docs/adr/0011-organizations-are-grouped-not-resolved.md`. 0010 is re-clustering. NEU-2132 and NEU-2133 cite "ADR 0010" for this decision; the implementer comments the correction on both (done at planning, see §5). | Renumbering nothing and letting the sibling tickets point at the wrong ADR. |
| Where the rules live in the spec | **§4, inline, in the style of the NEU-2126/2127 amendments**: a new table row, a new rules list for `08_organization_receipt.sql`, the amended `04_contribution.sql` entity-type line, and the name-match rule under `committee_transfer`'s row and rules. No separate appendix. | A standalone organizations section: the implementers read §4's table for columns and §4's rules for filters; splitting them is how one is updated without the other. |

## 2. The deliverables, file by file

### 2.1 `CONTEXT.md`

Under **Money**, after JFC transfer (before Self-funding):

> **Organization receipt**:
> One itemized gift from an organization to a committee, as reported to the regulator, held in `organization_receipt`. Organization money, never a contribution: in no individual total, no top-donor list and no race or candidate total; counted on the committee that received it. Loans (16C, 16F, 16G) and 15J memo lines are not receipts.
> _Avoid_: organization contribution, corporate donation, corporate money (unions and tribes give too)

Under **Parties**, after Committee (before Candidate):

> **Organization**:
> A giver that is neither an individual nor a committee: a corporation, union, trade association, tribe, 527 or other group, identified only by the name it is reported under. It carries no regulator ID and is never resolved; its receipts are grouped by organization key.
> _Avoid_: corporate donor, entity (that is FEC's word for every giver type), business, non-individual

Under **Resolution**, after Contributor key:

> **Organization key**:
> The normalized name that groups one organization's receipts: the reported name cleaned, its legal form stripped and its employer alias applied, by the same `normalize_employer` rule that normalizes a contributor's employer. Exact grouping, no linkage: two spellings share a key or they are two organizations.
> _Avoid_: organization id (there is none), resolved organization

Amend **Donor**'s second sentence: "Only individuals need resolution; committees and candidates already carry regulator IDs, and organizations are grouped by organization key, not resolved."

### 2.2 Project spec

**§2 Decisions table**, a new row after Self-funding:

> | Organizations | A giver that is neither an individual nor a committee is an organization: its gifts are `organization_receipt`, grouped by organization key (`normalize_employer`), never resolved, never a contribution, counted on the receiving committee only (ADR-0011). |

**§4 table**, a new row after `committee_transfer`:

> | `organization_receipt` | `(cycle, source, source_record_id)` | built by NEU-2131 (ADR-0011): from `indiv` rows with an organization entity type and from `oth` receipts whose giver has no committee id: `jurisdiction, organization_name, organization_key, city, state, zip, recipient_committee_id, amount, date, transaction_type, entity_type, report_type, amendment_indicator, memo_text, image_num, file_num, classified`. `organization_name` is the name as reported; `organization_key` is `normalize_employer` of it; `classified` is true when the entity type was blank and the classifier (NEU-2132) called the name an organization. No `candidate_id`, no `contributor_key`, no `donor_id`: organization money is the committee's only |

**§4 `committee_transfer` row**, append to the receipt sentence: "…or, when that is blank, the designation-J committee its `NAME` names (…NEU-2124), or, for a row with entity type PAC, COM, CCM or PTY, the one `cm` committee its `NAME` names (NEU-2131, the name-match rule below)".

**§4 rules for `04_contribution.sql`**, replace the first bullet's "Keep `ENTITY_TP IN ('IND','CAN')`" with:

> Keep `ENTITY_TP IN ('IND','CAN')`, and a blank `ENTITY_TP` (FEC fills it only on electronic filings since April 2002) unless the classifier (NEU-2132, `resolve.normalize.is_organization_name`, the measurement's rule V8) calls the name an organization, in which case the row is an organization receipt with `classified = true`. A filled entity type is never second-guessed. ORG rows are organization receipts (`08_organization_receipt.sql`); PAC, COM, CCM and PTY rows are committees' money, by the name-match rule below, or dropped. The same entity-type rule applies to the 15J `jfc_line` view (§6.11).

**§4, a new rules block after `04_contribution.sql`'s**, "Rules applied in `sql/silver/08_organization_receipt.sql` (NEU-2131, NEU-2132; ADR-0011)":

- From `indiv`: counted rows (`MEMO_CD` not `X`, `TRANSACTION_TP` not `24T`, as `contribution`) with `ENTITY_TP = 'ORG'`, or a blank `ENTITY_TP` the classifier calls an organization (`classified = true`), to a committee in `cm`. Earmark handling as `contribution`'s (ADR-0004): a conduit-side row is dropped. 2024: 18,233 ORG rows, $2,257,182,796; 70 blank rows the classifier calls organizations, $233,837.
- From `oth`: receipt types (`TRANSACTION_TP` `1x`, `3x`), not memo lines, with `ENTITY_TP = 'ORG'` and an `OTHER_ID` that is blank or not C-prefixed, and whose `NAME` names no JFC (the JFC rule, NEU-2124, is tried first: 4 rows, $183,545, in 2024 are a JFC's transfers); not 15J (evidence, `jfc_attribution`) and not a loan type (16C, 16F, 16G: a loan is not a gift). A C-prefixed `OTHER_ID` the cycle's `cm` lacks is still a committee's (689 rows, $21.3M in 2024, counted in `committee_transfer` as today). A blank entity type in `oth` is not classified: the row stays out. 2024: 103 rows, $23,073,903.
- An `oth` row that mirrors a counted `indiv` row (same recipient, name key, amount and date; 2 rows, $133,900 in 2024) is read once, from `indiv`. No `oth` organization receipt shares a `SUB_ID` with an `indiv` row.
- The refund sign rule and reversal pairing (NEU-2073) and the unknown-recipient rule (NEU-2070) as in `contribution`.
- `organization_key` = `normalize_employer(organization_name)`; a name that normalizes to nothing (`NO_VALUE`) keeps the row with the cleaned name as its key.
- `source_record_id` = FEC `SUB_ID`. The key is unique across `contribution`, `committee_transfer` and `organization_receipt`: a silver check fails the build if a `source_record_id` is in two of them.
- `organization_receipt` never feeds `contributor` (§6.1) or resolution, and no total outside `committee_cycle` and `committee_top_organization` reads it.
- Expected 2024 row count before the classifier (NEU-2131's target): 18,336, the 18,233 ORG `indiv` rows plus the 103 `oth` rows, less the mirrors; the classifier (NEU-2132) adds its 70 blank rows on top.

**§4, under `committee_transfer`'s rules (or a new short list, "Rules applied in `sql/silver/05_committee_transfer.sql` for rows naming a committee")**, the name-match rule:

> **PAC/COM/CCM/PTY rows without a committee id (NEU-2131; measurement Q3, Q7).** A counted `indiv` row with entity type PAC, COM, CCM or PTY and a blank `OTHER_ID`, whose name key (uppercased, letters and digits only, the key `04_contribution.sql` and `05_committee_transfer.sql` compare names by) names exactly one `cm` committee, is a `committee_transfer` receipt from that committee (`from_committee_id` = the named committee, `source_record_id` = its `SUB_ID`). The same applies to an `oth` receipt with a blank `OTHER_ID` that names no JFC (the JFC rule, NEU-2124, is tried first). Not when the named committee is the row's own recipient. Not when `oth` already holds the gift: same recipient, `OTHER_ID` = the named committee, same amount and date (5 `indiv` rows, $70,000 in 2024). Rows naming several committees or none are dropped: they are committees by entity type, so they are in `organization_receipt` neither. Nothing is counted twice. 2024: $788,411,601 in 4,052 rows, $778,467,682 of it in `indiv`; $635,589,379 (80.62%) names exactly one committee, in 2,546 `indiv` rows and 9 `oth` rows ($212,303); $152,822,222 names several or none and is dropped. The measurement's pinned 95% all-or-nothing bar got *drop*; it is amended here because the matched rows are FEC's own committee money (Senate Leadership Fund's PAC-typed rows, $8,934,545, against FEC's `OTHER_POL_CMTE_CONTRIB` $8,934,548; SMP within $6.1k).

**§4 FEC files table**: `indiv` → "contribution, organization_receipt"; `oth` → "committee_transfer, jfc_attribution (§6.11), organization_receipt".

**§6**, first line: "Only individuals are resolved; committees and candidates carry FEC IDs, and organizations are grouped by organization key (§4, ADR-0011), never linked." In §6.1, after "(and the JFC attributions, §6.11)": "and never `organization_receipt`".

**§7.1 table**: `committee_cycle` gains `total_from_organizations` ("NEU-2133: the net sum of `organization_receipt.amount` by recipient; 0 when none, never NULL"). A new row after `committee_top_donor`:

> | `committee_top_organization` | `committee_id, cycle, rank (≤100), organization_key, name, amount` (NEU-2133: the organizations that gave the committee the most, grouped by `organization_key`, ranked by net amount then key; `name` is the key's most-money reported spelling, as `donor.display_name` is chosen (§6.7); an organization netting to $0 or less is left out, as top-donor lists leave such donors out) |

**§7.1 prose**, after the donor-tables paragraph: "Organization money (ADR-0011) is committee-level only: `committee_cycle.total_from_organizations` and `committee_top_organization` are the only gold readers of `organization_receipt`. It is in no `cycle`, `race`, `race_candidate`, `candidate_cycle` or donor figure, and `committee_top_donor` lists resolved people only. A cycle-wide organization figure is a deliberate amendment, not a side effect."

**§9**: add `organization_receipt` to the table list after `committee_transfer`; add `organization_receipt.json` to the schema line's implied set (the list is "schema/<table>.json", so nothing to write, but the README's table list gains the row when NEU-2064 writes it).

**§14**: a new entry between M3 and M4: "**M3.5 Organization money** — `organization_receipt`, the blank-entity-type classifier, committee organization totals and top organizations, committee pages, 2024 run checked against FEC's committee summaries. Before M4's backfill, which would otherwise count pre-2002 organization gifts as individuals' money."

### 2.3 `docs/adr/0011-organizations-are-grouped-not-resolved.md`

Front matter `status: accepted`, in the form of 0010. Title: **Organizations are grouped by exact normalized name, not resolved, and have no pages in v1**. Body, three parts:

1. **Context.** A giver that is neither an individual nor a committee (ORG entity type; blank types the classifier calls organizations) gave $2.26B in 2024 that fundlens dropped. Organization identity is a different problem from person identity: subsidiaries, a corporation beside its PAC, name changes, DBAs; industry coding on top of it is OpenSecrets' core product and a project of its own. A committee's funders can be ranked without any of that.
2. **Decision.** (a) Organization money is its own silver table, `organization_receipt`, with its own glossary term, never a row in `contribution`: every individual total, top-donor list and the resolution input stay sums over `contribution`, and no filter has to remember to exclude organizations. (b) `organization_key` is `normalize_employer` over the reported name, grouped exactly; no Splink, no `donor_id`, no crosswalk, no override. (c) Committee-level only: `committee_cycle.total_from_organizations` and `committee_top_organization`; no organization page, no search entity, no cycle, race, candidate or donor figure in v1. (d) A row typed PAC/COM/CCM/PTY with no committee id is a committee's gift when its name names exactly one `cm` committee (minus self-matches and `oth` twins), else dropped; never an organization receipt. (e) A C-prefixed giver id `cm` lacks is a committee's, counted in `committee_transfer` as today. (f) A blank entity type is classified by name (the measurement's rule V8, 99.66% row precision on 2024 filled types); a filled type is never second-guessed.
3. **Rejected.** Splink over organizations (a second model, a second crosswalk, and the wrong problem); importing an industry or organization coding (OpenSecrets' licence and scope; not v1); `contribution` rows with an `is_organization` flag (one forgotten filter puts corporations among the donors); dropping PAC/COM rows with no id outright (loses $635.6M FEC itself counts); counting organization money in candidate or race totals (the committee that received it decides what it funds, and crediting it onward is the story's explicit non-scope).

**Consequences**: the dataset's `organization_receipt` is grouped, not resolved, and its README says so; `normalize_employer` now serves two tables, so an alias added for a donor's employer regroups an organization too (a feature, and one to expect when adding an alias; there is no add-an-alias runbook to note it in); the backfill (NEU-2060) waits for NEU-2132; a later organization-pages project starts from `organization_key`, not from a crosswalk.

### 2.4 Root `CLAUDE.md`

The decisions line lists 0001–0007 only. Extend it: "…0007 gold loads by DuckDB → CSV → `COPY`, 0008 Mantine is the SPA's component library, 0009 resolution quality is scored against DIME by FEC ids, 0010 clusters are re-clustered by constrained single-linkage, 0011 organizations are grouped by normalized name, not resolved". Adding 0008–0010 is in scope: the line is the index, and three entries were missing.

## 3. Acceptance criteria

- [ ] `CONTEXT.md` defines Organization receipt (Money), Organization (Parties) and Organization key (Resolution), each with an avoid-list, and Donor's sentence names organizations as grouped, not resolved.
- [ ] Spec §4 has the `organization_receipt` row with the column list in §2.2, the `08_organization_receipt.sql` rules (ORG and classified-blank `indiv` rows; `oth` ORG receipts minus 15J and 16C/16F/16G; mirror dedupe; refund and unknown-recipient rules; `normalize_employer` key; no feed into `contributor`), and the amended `04_contribution.sql` entity-type bullet.
- [ ] Spec §4 states the PAC/COM/CCM/PTY name-match rule with the measurement's dollars ($788,411,601 total; $635,589,379 joined in 2,546 `indiv` and 9 `oth` rows; 5 twins, $70,000; $152,822,222 dropped) and the reason the 95% bar was amended.
- [ ] Spec §4 says a C-prefixed giver id `cm` lacks stays in `committee_transfer` (689 rows, $21.3M).
- [ ] Spec §7.1 carries `committee_cycle.total_from_organizations` and `committee_top_organization` with columns, and the committee-level-only paragraph naming `cycle`, race, candidate and donor figures as untouched.
- [ ] Spec §9 lists `organization_receipt`; §2, §6, the FEC files table and §14 carry the amendments in §2.2.
- [ ] `docs/adr/0011-organizations-are-grouped-not-resolved.md` exists with `status: accepted` and the context, decision (a)–(f), rejected alternatives and consequences in §2.3; no file named 0010 is touched.
- [ ] Root `CLAUDE.md`'s decisions line lists 0008, 0009, 0010 and 0011.
- [ ] No change under `sql/`, `src/`, `frontend/` or `tests/` in the PR.
- [ ] `task format` passes (markdown is not linted by it, but the pre-commit hooks run).

## 4. Out of scope

- Any code or SQL: NEU-2131 (silver and the name match), NEU-2132 (classifier), NEU-2133 (gold), NEU-2134 (API), NEU-2135 (pages), NEU-2136 (runbook).
- Spec §7.2 (API) and §8 (frontend): NEU-2134 and NEU-2135 amend those when they fix the response shape.
- Organization pages, search entities, industry coding, crediting organization money to candidates or races, and a cycle-wide organization figure.
- Classifying blank-entity-type `oth` receipts (one row in 2024).
- The Linear project description's "Decisions: `docs/adr/0001`–`0006`" line (stale since 0007; a Linear edit, not a repo one).

## 5. Planning notes

- The sibling tickets NEU-2132 and NEU-2133 cite "ADR 0010" for the organizations ADR; it is 0011. NEU-2131 excludes 16C only; the spec excludes 16C, 16F and 16G. The corrections were commented on NEU-2131 and NEU-2133 at planning (2026-11-04); the NEU-2132 comment was not posted (the planning session was denied the write), so the implementer of NEU-2132 reads the ADR number from this spec. Where a ticket and this spec differ, the spec wins.
- Measurement sections to quote: Headline; Q2a/Q2b (giver status, loan types); Q3a/Q3b/Q3e (name match, twins); Q4 (mirrors); Decisions; "For NEU-2130, NEU-2131 and NEU-2132".
