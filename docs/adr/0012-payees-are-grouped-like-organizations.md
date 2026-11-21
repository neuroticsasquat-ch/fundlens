---
status: accepted
---

# Payees are grouped by exact normalized name, as organizations are, and get pages; people and sub-items do not

An operating expenditure names whoever was paid by a reported name alone: FEC's `oppexp` carries no id for a payee. The 2024 measurement (NEU-2149, `docs/measurements/oppexp-2024.md`) counted $9,715,514,602 of spending under 98,975 payee keys from 105,313 raw names, the top 100 keys holding 52.37% of the dollars and the top 1,000 holding 80.26% (Q9a). Which campaigns pay a given consultant or media firm is the question spending data is read for, and the name is all there is to answer it with.

ADR-0011 met the same shape of problem for organizations that give, and decided to group them by exact normalized name, never to resolve them, and to give them no pages. This record takes the first two decisions for payees and reverses the third.

**`payee_key` is `organization_key` over the reported name, grouped exactly.** The same function, not a copy: `normalize_employer`, with its legal forms stripped and its employer aliases applied, falling back on the cleaned name. No Splink, no crosswalk, no override. Read by eye, the top 100 keys of 2024 hold no wrong merge and three firms split across keys (`AX MEDIA` and `AXMEDIA`; `TEAM DIRECT` and `TEAMDIRECT`; MissionWired under three), each of which one alias in `resolve/aliases.yaml` joins (Q9b).

**A payee gets a page where an organization does not.** An organization's page would have said who a corporation gave to, which is a claim about corporate identity (a parent beside its subsidiary, a company beside its PAC) that grouping by name cannot make. A payee's page says which committees paid a name, and a firm bills its clients under one trade name: the name is the identity the page needs, and it is the one place in fundlens where a name links many committees' money to one payee. The page is addressed by `payee_id`, the first 16 hexadecimal characters of the SHA-256 of the payee key, so a link survives every rebuild with no crosswalk to keep.

**A person has no page.** 37,072 of 2024's payee keys are people (`ENTITY_TP` `IND`), paid $547.3M: staff, reimbursements, solo consultants. 1,380 of those keys already span two states or more (`JOHNSON ROBERT` spans five, Q9g), which is the collision donors are resolved with Splink to avoid, and a page would make everyone a campaign reimbursed searchable. A person stays a payee in silver, in a committee's itemized spending and in its top payees, by name and with no link. A row is a person's when its entity type is `IND` or `CAN`, or is blank and the v1 name classifier (`is_organization_name`, NEU-2132) does not call the name an organization; a key is a person's when more than half of its payee dollars (counted rows that are not in-kind outlays), over every cycle in gold, are on such rows, so filers who type one firm differently do not split its page, and one mistyped row makes no page for a person.

**A name that names nobody has no page either.** `PETTY CASH`, `PAYROLL`, `CASH` and the `UNITEMIZED …` keys (about $270,000 in 2024, Q9e) are listed by hand in `fec/payee_no_page.csv` and treated as a person's key is.

**A sub-item reaches no payee, and a card issuer is one.** A sub-itemized payment counts at its parent in every cycle (project spec §5.2), so American Express is 2024's third-largest payee ($195.2M of card bills) and the merchants itemized under its bills are credited nothing: $503.0M of sub-items in 2024. A payee's total is therefore what committees reported paying that name directly, and every payee dollar is inside the total of the committee that paid it.

**An in-kind outlay is credited to no payee.** The spending-side record of a gift of goods names the giver as payee, who was paid nothing. It counts in the committee's spending, as FEC counts it, and is in no payee table.

Rejected: Splink over payees (a second model and a second crosswalk for a problem that is mostly trade names, which exact grouping already handles); payees only as a list on committee pages, as organizations are (the story's question, who else pays this firm, would have no page to answer it); pages for people, with or without the state in their key (name collisions presented as one payee, and a consultant paid in two states split in two); deciding a person row by row (a firm one filer types `IND` loses that committee from its page, and its total stops matching its key's rows); counting sub-items where they add up to their parent (the rule passes its bar in ten of twelve cycles and fails in 2016 and 2024, so a payee's totals would be built by different rules from one cycle to the next, Q2c); a sequence-assigned `payee_id` (payees are rebuilt from nothing every run); hiding card issuers behind a hand-kept list (the committee did pay the issuer, and FEC's own totals count the bill); a second normalizer for payees (two normalizers drift).

## Consequences

- `normalize_employer` and `resolve/aliases.yaml` now serve three things: a contributor's employer, an organization key and a payee key. An alias added for any one regroups the other two.
- A change to the normalizer or to an alias changes a payee's key and so its `payee_id`: the old page's link breaks. There is no redirect table.
- A payee's total understates what a merchant received through card bills and reimbursements, and the methodology page says so. Changing the sub-item rule later moves every payee's totals in every cycle.
- The person rule reads `ENTITY_TP`, which is blank on 9.6% to 29.5% of dollars in 2006–2018 (Q2d). There the name classifier decides, on names it was not measured on; NEU-2180's backfill checks it before those cycles are published.
- The public dataset's `operating_expenditure` is grouped, not resolved: `payee_key` is a normalized name, not an id, and its README entry says so.
- Spec: project spec ("every FEC dollar") §5; glossary `CONTEXT.md` (Operating expenditure, Sub-item, In-kind outlay, Spending category, Payee, Payee key); per-ticket spec `docs/specs/NEU-2150-spending-spec-section.md`.
