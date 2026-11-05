---
status: accepted
---

# Organizations are grouped by exact normalized name, not resolved, and have no pages in v1

A giver that is neither an individual nor a committee, a corporation, union, trade association, tribe, 527 or other group, has entity type ORG in FEC's `indiv` and `oth` files, or a blank entity type the classifier (NEU-2132) calls an organization. `04_contribution.sql` kept only IND, CAN and blank types and `05_committee_transfer.sql` kept an `oth` receipt only when its giver had a committee id or, with a blank id, named a JFC (NEU-2124), so fundlens dropped this money unmeasured. The 2024 measurement (NEU-2129, `docs/measurements/organization-money-2024.md`) put it at $2,257,182,796 in 18,233 `indiv` rows, $1.42B of it to super PACs, plus $23.1M of ORG gifts in `oth` with no committee giver, against $9.82B from individuals. Fairshake's FEC total is $260.1M and fundlens counted $7.3M of it.

Organization identity is a different problem from an individual's. A subsidiary beside its parent, a corporation beside its PAC, a name change, a DBA: none of these is a spelling variant, and deciding which of them are one organization is a coding exercise, not linkage. Industry coding on top of it is OpenSecrets' core product and a project of its own. A committee's funders can be ranked without any of that.

**Organization money is its own silver table, `organization_receipt`, with its own glossary term, and is never a row in `contribution`.** Every individual total, top-donor list and the resolution input stay sums over `contribution`, and no filter has to remember to exclude organizations: one forgotten filter is how a corporation ends up among the donors. The table has no `candidate_id`, no `contributor_key` and no `donor_id`.

**`organization_key` is `normalize_employer` over the reported name, grouped exactly.** The name is cleaned, its legal form stripped (INC, LLC, CORP and the rest of `LEGAL_FORMS`) and its employer alias applied, by the same rule that normalizes a contributor's employer, so `KOCH INDUSTRIES INC` and `KOCH INDUSTRIES` are one organization and `SPACE EXPLORATION TECHNOLOGIES CORP` and `SPACEX` are one by alias. No Splink, no `donor_id`, no crosswalk, no override: two spellings share a key or they are two organizations.

**Committee-level only.** `committee_cycle.total_from_organizations` and `committee_top_organization` are the only gold readers of `organization_receipt`. There is no organization page, no search entity, and no cycle, race, candidate or donor figure in v1. The committee that received the money decides what it funds, and crediting it onward to a candidate or race is the milestone's explicit non-scope.

**A row typed PAC, COM, CCM or PTY with no committee id is a committee's gift when its name names exactly one `cm` committee, else dropped; never an organization receipt.** It joins `committee_transfer` as a receipt from the named committee, except when that committee is the row's own recipient or `oth` already holds the gift (same recipient, giver id, amount and date). In 2024 that is $635,589,379 of $788,411,601; the $152,822,222 naming several committees or none is dropped. The measurement's pinned all-or-nothing 95% bar got *drop* for the whole $788.4M; it is amended because the matched rows are FEC's own committee money (Senate Leadership Fund's PAC-typed rows, $8,934,545, are FEC's `OTHER_POL_CMTE_CONTRIB` $8,934,548 to within $3).

**A C-prefixed giver id the cycle's `cm` lacks is a committee's.** A C-prefixed id is a committee id by FEC's convention; the filer named one. The row stays in `committee_transfer` as today (689 rows, $21.3M in 2024) and is never keyed by name as an organization.

**A blank entity type is classified by name; a filled type is never second-guessed.** The classifier is the measurement's rule V8 (99.66% row precision and 97.99% row recall on 2024's filled types); it runs over `indiv` and the 15J memo lines (`jfc_line`), not over the rest of `oth`, where the one blank-typed 2024 row it would touch ($9,609) stays out. Loans (16C, 16F, 16G) and 15J memo lines are never receipts.

Rejected: Splink over organizations (a second model, a second crosswalk, and the wrong problem: the hard cases are corporate structure, not spelling); importing an industry or organization coding (OpenSecrets' licence and scope; not v1); `contribution` rows with an `is_organization` flag (every individual total, top-donor list and the resolution input would have to filter it, and one forgotten filter puts corporations among the donors); dropping PAC/COM/CCM/PTY rows with no id outright (loses $635.6M that FEC itself counts); counting organization money in candidate or race totals (the committee that received it decides what it funds; crediting it onward is the story's explicit non-scope); a cycle-wide organization total (the home page's headline would mix money credited to candidates with money that is not, and no ticket owns the change).

## Consequences

- The public dataset's `organization_receipt` is grouped, not resolved, and its README says so; `organization_key` is a normalized name, not an id, and may regroup when the normalizer or the alias map changes.
- `normalize_employer` now serves two tables: an alias added to `resolve/aliases.yaml` for a donor's employer regroups an organization too. A feature, and one to expect when adding an alias.
- `source_record_id` is unique across `contribution`, `committee_transfer` and `organization_receipt`; a silver check fails the build when a row is in two of them, so nothing is counted twice.
- The backfill (NEU-2060) waits for the classifier (NEU-2132): before April 2002 FEC left the entity type blank, and without the classifier pre-2002 organization gifts would count as individuals' money.
- A later organization-pages project starts from `organization_key`, not from a crosswalk; whatever identity work it does is additive to the grouping, which stays the dataset's contract.
- Spec: project spec §2, §4, §6, §7.1, §9, §14; glossary `CONTEXT.md` (Organization, Organization receipt, Organization key); per-ticket spec `docs/specs/NEU-2130-organizations-glossary-spec-adr.md`.
