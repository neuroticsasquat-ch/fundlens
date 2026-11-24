# fundlens

A free, public campaign-finance data platform: donor, candidate and committee money for every race in the country, presented by race, with individual donors correctly resolved across name, employer and address variants. The resolved dataset is the product; the web app is its demo.

## Language

### Money

**Contribution**:
One itemized transfer of money from a contributor to a committee, as reported to the regulator, in the canonical schema regardless of source (FEC bulk today, state portals later).
_Avoid_: donation, transaction, record

**Independent expenditure**:
Money a committee spends for or against a candidate without coordinating with them. It attaches to the candidate it names and their race when that candidate is one of the cycle, unless that candidate is a **Handoff**'s first and the spending is dated on or after the handoff, or undated: then it is the second candidate's. The candidate it names is the one its filing names: where `pas2`'s candidate id is another's, whether FEC coded it so or the filer did, a hand-curated list (`fec/ie_candidate_corrections.csv`) names the filed one. It is never a contribution. One naming no candidate of the cycle counts in its spender's total alone.
_Avoid_: IE spend, outside money, super PAC money

**Earmark**:
A contribution routed through a conduit (ActBlue, WinRed) to its final recipient. The regulator reports it twice, on the conduit side and the recipient side; fundlens counts it once. A committee passing on a gift it did not deposit (Senate Conservatives Fund's to a candidate, type 24I) is an earmark too: its side is dropped when the recipient itemized the gift, and kept, the committee's, when that side is the only record. Most 24Is are not this: they are recipients' own receipts of earmarks through a conduit.
_Avoid_: conduit contribution, pass-through

**JFC attribution**:
A joint fundraising committee participant's memo line (FEC type 15J) naming the individual behind part of a JFC transfer and the share attributed to that participant. Evidence that the individual's money reached the participant; never a contribution, and never counted in a total.
_Avoid_: JFC contribution, attributed contribution

**Orphaned attribution**:
A memo line that is the only record of a gift: a partnership's, LLC's or trust's gift itemized as its members' shares, whose parent row the regulator's bulk file leaves out. Counted as its giver's gift, a contribution or an organization receipt by its entity type. Every other memo line, an earmark's or a JFC attribution among them, is not counted.
_Avoid_: memo contribution, unparented memo

**JFC transfer**:
A joint fundraising committee's transfer of its participants' shares to a participant committee: a receipt from a designation-J committee, whatever type the filer gave it (mostly 18G, some 18J and 15J). Counted for a candidate when the participant raises for one, apart from the candidate's contributions and committee gifts. Committee money, never a contribution.
_Avoid_: JFC contribution

**Organization receipt**:
One itemized gift from an organization to a committee, as reported to the regulator, held in `organization_receipt`. Organization money, never a contribution: in no individual total, no top-donor list and no race or candidate total; counted on the committee that received it. Loans (16C, 16F, 16G) and 15J memo lines are not receipts.
_Avoid_: organization contribution, corporate donation, corporate money (unions and tribes give too)

**Operating expenditure**:
One itemized payment a committee made to run itself, for staff, advertising, rent, consultants or fees, as reported to the regulator. Spending, never a contribution: in no receipt total. One filed as a negative amount takes back or moves an earlier one, and nets against it.
_Avoid_: spend, expense, disbursement (that is every dollar a committee pays out, a reported total), outside spending (that is spending on a race by someone other than the campaign)

**Sub-item**:
A row itemizing part of an operating expenditure the committee already reported whole: a card bill's charges, a reimbursement's receipts. Shown under its operating expenditure and never counted, since the whole is; the merchant it names is credited nothing.
_Avoid_: memo child, child row, memo item, sub-itemization

**In-kind outlay**:
The spending-side record of a gift of goods, services or other property, cryptocurrency among them: the regulator has the committee report the gift as a receipt and its use as an operating expenditure naming the giver. Counted in the committee's spending, as the regulator counts it; credited to no payee, since the giver was paid nothing.
_Avoid_: in-kind payment, orphan child, in-kind contribution (that is the receipt)

**Spending category**:
What an operating expenditure bought, as one of a fixed list (media, digital, mail, payroll and the rest). fundlens's reading of the purpose the filer wrote and, where that says nothing, of the regulator's category code where filers use the code reliably; never the regulator's code as filed.
_Avoid_: FEC category (the regulator's code), purpose (the filer's free text), expense type

**Non-contribution account**:
A hybrid PAC's (FEC committee type V or W) second account, outside the contribution limits, whose receipts the regulator types 10 (24I for an earmark through a conduit, when its memo names the account; a 24I without that memo is the contribution account's) and whose refunds it types 20Y. Individuals' and organizations' money to it is kept, as contributions and organization receipts, with its refunds, and counted in the committee's own figure, never in its individual or organization totals, which hold the contribution account the regulator's itemized figure counts. Its givers are in the committee's top-donor and top-organization lists. A committee's gift to it is counted as any committee's gift. A type 10 to any other committee is an ordinary contribution, unless its memo begins with the account's name: then the filer has marked it the account's, whatever the regulator's committee type for the cycle.
_Avoid_: Carey account, soft money, super PAC account

**Party account**:
One of a national party committee's three accounts outside its main one, a convention, a headquarters and a recount account, whose receipts the regulator types 30, 31 and 32 (with variants such as 31T and 32E) and whose refunds 40Y, 41Y and 42Y. Individuals' gifts to one are kept as contributions, the donors', and organizations' as organization receipts; both are counted in the committee's other-lines figure, never in its individual total or its organizations' total, which hold what the regulator files on line 11(a)(i).
_Avoid_: building fund, soft money, special account

**Other-lines money**:
An individual's counted money, or an organization's, that the regulator files on a line other than 11(a)(i) and outside a non-contribution account: a party account's, a loan, a transfer or other receipt (18G, 18U, 18H) or a Form 9 donation, or a row whose filer's transaction id (`TRAN_ID`) names line 11(b), 11(c), 12 to 17 or Schedule L, as a super PAC's gift from another political organization on 11(c) often does whatever its type. Not one naming 17(a): that is a presidential committee's individuals' line. Kept, as contributions or organization receipts, in the donor's figures (an individual's), the committee's own figure and no individual or organizations' total; a candidate's own money is self-funding whatever its line. A returned cost is other-lines money too.
_Avoid_: off-book money, non-itemized money

**Returned cost**:
A receipt whose memo names a cost coming back to the committee, not a gift: a tax, vendor, media, expense or fee refund, rebate or reimbursement, as the tax authority refunding a party's payroll tax, filed as a gift from the treasury. Told by the memo's words, never the payer's name; a memo naming a refund alone is a gift the committee refunded later, and counts. Kept, on the regulator's line 15 as other-lines money where its type would put it on 11(a)(i), and on its own line otherwise (a non-contribution account's, a party account's); an organization's is on no top-organization list, whatever its line, since the organization gave nothing.
_Avoid_: offset, refund received

**Self-funding**:
A candidate's own money, including loans: a gift or loan to their own committee under their own name, or any contribution or loan the filer types as from the candidate (15C, 16C), whatever its name, route or recipient, less the loans repaid to them (20C). Reported separately from top-donor lists so a candidate does not appear as their own largest donor.

**Returned gift**:
A committee's gifts to one candidate that net below zero in a cycle: voids and refunds of gifts made in an earlier cycle, filed as negative gifts when they happen, with nothing in the cycle to net against. Kept as filed, and counted in the giver's own returned figure, never in its gifts to candidates, its top recipients, the candidate's committee total or a race's top committees. A void of a gift made in the same cycle nets against that gift instead.
_Avoid_: negative contribution, refund received, clawback

**Superseded filing**:
A report a committee filed again as an amendment that changed its form, report type or coverage, so the regulator's bulk data keeps both. Its gifts are counted from the amendment alone, never from it, even where the regulator's own itemized figure adds the two. Told by the amendment repeating at least half of its gifts. Repeats within one filing are separate gifts, and count, unless they are a repeated row.
_Avoid_: duplicate filing, stale report

**Repeated row**:
A transaction the regulator's bulk data holds on two or more rows, the same in every field but the regulator's own row id, under the one transaction id (`TRAN_ID`) its filer gave it on an electronic filing. The filing lists it once, so it is read once, from its first row, by every table. Rows sharing a transaction id that differ elsewhere are all read, and so are a paper filing's identical rows, which carry no transaction id.
_Avoid_: duplicate, double-count, FEC duplicate

**Reported total**:
A figure a committee reported to the regulator as its own total for a cycle, taken from the regulator's summary of its reports: what it raised, spent, holds and owes. Kept as filed: never corrected, netted or added to itemized money. A candidate's is the reported totals of the committees raising for them, added up (before 2008, the regulator's own figure for the candidate), and a handoff's committee's are the second candidate's alone.
_Avoid_: FEC total, official total, actual total, summary figure

**Itemized total**:
What fundlens itself counts, from itemized rows, toward the line the regulator's itemized individual figure reports: individuals' contributions and organization receipts on line 11(a)(i), before refunds are taken off. The figure coverage sets against a reported total; shown beside it, never added to it. Not a committee's individual total, which is net of refunds and leaves organizations out.
_Avoid_: fundlens total, computed total, our total, itemized individual total

**Coverage**:
The share of a committee's reported itemized individual money that fundlens itemizes: its itemized total over the regulator's itemized figure. A candidate's is taken over the committees raising for them. Undefined for a conduit, whose reported figure includes the earmarks it passes on; where the regulator gives no itemized figure; and before 2008, when its summaries did not split itemized money from unitemized. It can exceed 100%, and is shown as it is.
_Avoid_: match rate, completeness, itemization rate, coverage dates (that is the reporting period)

**Unitemized**:
Individuals' gifts a committee reports only as one lump, because each giver's aggregate stayed at or under the regulator's itemization threshold ($200). A reported total, and the committee's alone: no donor's, in no itemized total and no donor figure.
_Avoid_: small-dollar money (an itemized donor can be small, and twenty $50 gifts are not), small donors, under-$200 gifts

**Reporting period**:
The dates a committee's reported totals run from and to: the start of its first report of the cycle and the end of its latest. It says how current a reported total is.
_Avoid_: coverage dates, coverage period, as-of date

**Gift size**:
A donor's net gifts to one candidate's committees in a cycle, the amount that places the donor in a bucket: twenty $50 gifts are one $1,000 donor. Never the amount of a single contribution. Unitemized money has no donors and is a bucket of its own.
_Avoid_: contribution size, donation size, small-dollar donor

### Parties

**Donor**:
A resolved individual: the persistent identity behind many contributor-name, employer and address variants. Only individuals need resolution; committees and candidates already carry regulator IDs, and organizations and payees are grouped by organization key and payee key, not resolved.
_Avoid_: contributor (that is the raw, unresolved name on a record), person, entity

**Contributor**:
The raw name, employer, occupation and address as reported on a single contribution (or JFC attribution), before resolution.

**Committee**:
A regulator-registered fundraising entity (candidate committee, PAC, party committee, super PAC) identified by its regulator ID.

**Organization**:
A giver that is neither an individual nor a committee: a corporation, union, trade association, tribe, 527 or other group, identified only by the name it is reported under. It carries no regulator ID and is never resolved; its receipts are grouped by organization key.
_Avoid_: corporate donor, entity (that is FEC's word for every giver type), business, non-individual

**Payee**:
Whoever an operating expenditure names as paid: a firm, a person, a card issuer or another committee, identified only by the name it is reported under. It carries no regulator ID and is never resolved; its operating expenditures are grouped by payee key. A payee that is a person, or a name that names nobody (petty cash), is listed under the committee that paid it and has no page of its own.
_Avoid_: vendor (staff and card issuers are payees too), recipient (that is the committee a contribution goes to), contractor

**Candidate**:
A person seeking an office in a cycle, identified by their regulator ID.

### Structure

**Cycle**:
The two-year federal election period, named by its even year (2024). Historical cycles are frozen; the current cycle is rebuilt weekly.
_Avoid_: election year, period

**Current cycle**:
The newest cycle gold holds, which is what the home page summarises and the cycle switcher shows when the page's URL names no cycle. Usually the cycle being rebuilt weekly, but defined by what is published, not by the calendar.
_Avoid_: latest cycle, this cycle, active cycle

**Race**:
One contest for one seat in one cycle, keyed by cycle, jurisdiction, office, state and district. Keyed by cycle because district boundaries change.
_Avoid_: seat, contest, election

**Jurisdiction**:
The regulator whose rules and IDs a record follows: federal (FEC) in v1; a state later.

**Seat calendar**:
The generated list of every seat up in a cycle (all House districts under that cycle's apportionment, the Senate class plus specials, President every fourth year). It is the race universe; candidates attach to it, they do not create it.
_Avoid_: race list, ballot

**Conduit**:
A committee (ActBlue, WinRed) that forwards earmarked contributions to their final recipient. Flagged on the contribution. A recipient in fundlens only of gifts to itself (tips), net of the tips it refunds: its own side of an earmark, and its refund of one, are dropped (ADR-0004).

**Handoff**:
A candidate committee passed from one candidate to another mid-cycle (Biden's 2024 campaign, Harris's from 2024-07-21). Listed by hand in `fec/handoffs.csv`, never inferred; the committee's money, and spending that names the first candidate, is the first candidate's before the handoff date and the second's from it on.
_Avoid_: transfer (a committee's money moving), takeover

**Candidate alias**:
A second regulator ID one person holds for the same race (Hovde's 2024 `S4WI00256` beside `S2WI00268`), linked to a committee credited to the other ID, under the same last and first given name. Holds no money; listed nowhere, and its candidate page redirects to the ID that holds the money. Inferred by rule, never listed by hand.
_Avoid_: duplicate candidate, merged candidate

### Resolution

**Contributor key**:
The exact normalized tuple (name, ZIP5, employer, occupation) that identifies one unique contributor string across all its contributions. Resolution runs over contributor keys, not over contributions.

**Organization key**:
The normalized name that groups one organization's receipts: the reported name cleaned, its legal form stripped and its employer alias applied, by the same `normalize_employer` rule that normalizes a contributor's employer. Exact grouping, no linkage: two spellings share a key or they are two organizations.
_Avoid_: organization id (there is none), resolved organization

**Payee key**:
The normalized name that groups one payee's operating expenditures across committees and cycles, made by the rule that makes an organization key. Exact grouping, no linkage: two spellings share a key or they are two payees.
_Avoid_: payee id (that is a payee page's address, derived from the key), vendor id, resolved payee

**Cluster**:
The set of contributor keys that probabilistic linkage judges to be the same person in one resolution run.

**Component**:
The set of contributor keys joined by a path of matched pairs in one run: what linkage's connected components give, before re-clustering. A component is a cluster only once re-clustering has left it alone or cut it into pieces.
_Avoid_: raw cluster, Splink cluster

**Chain**:
A component holding keys linkage would never pair directly, joined only through intermediates: two first names that disagree, or hundreds of people under one surname sound. The failure re-clustering removes.
_Avoid_: over-merged cluster, mega-cluster

**Initial pair**:
Two first names of which one is a single letter and both start with that letter (`C` and `CRAIG`). Linkage's evidence of one person. Two full names sharing a first letter (`MARGO` and `MICHAEL`) are not an initial pair.
_Avoid_: same initial, initial match

**Nickname pair**:
Two different first names of which one is a prefix of the other at least three letters long (`LOU` and `LOUIS`), or which the vendored nickname table (`resolve/nicknames.csv` less `nicknames-excluded.csv`) links directly, read either way (`HAL` and `HAROLD`). Linkage's evidence of one person; a nickname the table does not name is still an override's to merge. Two nicknames of one name (`HAL` and `HARRY`) are not a nickname pair.
_Avoid_: alias (that is an employer's word), variant

**Vetoed pair**:
Two contributor keys whose first names the model rejects outright: both present, not the same, not close, and neither an initial pair nor a nickname pair, whatever their first letters. A missing first name vetoes nothing. Never in one cluster, except by an override or an adjudication.

**Re-clustering**:
Rebuilding a component that holds a vetoed pair or more keys than the cluster cap from its own matched pairs, strongest first, so that no piece holds either. Runs after linkage and before overrides; a component that offends neither is untouched.
_Avoid_: splitting (that is an override's word), pruning

**Cluster cap**:
The most contributor keys a cluster may hold after re-clustering. Tuned against the reference labels, not derived.
_Avoid_: max cluster size, size limit

**Cluster threshold**:
The match probability at or above which a scored pair joins its two contributor keys into one component (`RESOLVE_CLUSTER_THRESHOLD`). A pair between the match threshold and it is kept as an edge but joins nothing. Tuned against the reference labels, like the cluster cap.
_Avoid_: link threshold, match threshold (that is the lower bar, below which a pair is not kept at all)

**Crosswalk**:
The persistent mapping from contributor key to donor ID, so weekly rebuilds do not reshuffle donor URLs. A new cluster inherits the donor ID its members already carry; only never-seen keys get new IDs.

**Override**:
A manual merge or split assertion applied after linkage, authored data that survives every rebuild.

**Adjudication**:
A model's verdict on an ambiguous high-dollar candidate: two clusters linkage kept apart but scored in its ambiguous band, or one cluster whose keys report different employers. Recorded in `app.adjudication` with its model, prompt version and confidence, and applied like an override when the model is confident; never written to the overrides file, which stays the human record.
_Avoid_: LLM override, AI merge

**Reference label**:
The contributor id DIME (Bonica, Stanford) assigns to an FEC contribution, `bonica.cid`: the ground truth resolution is scored against. Never shown on the site and never a `donor_id`.
_Avoid_: DIME id, true donor, gold label

**Labelled key**:
One `(contributor key, reference label)` pair among the contributions DIME and fundlens both know: the record precision and recall count pairs of. A key DIME gives two labels is two labelled keys.

**Direct pair** / **Chained pair**:
Two labelled keys in one cluster that linkage scored as a pair (an edge between their contributor keys), or did not: a chained pair shares a cluster only through other keys. `fundlens diagnose` counts the wrong pairs of each.

**Validation**:
`fundlens validate`: scoring a resolved build's `donor_id`s against the reference labels, as pairwise precision and recall, overall and for the top contributors by dollars. A report, not a pipeline step: it writes `app.resolution_quality`, and `load` copies the live model's figures into `gold.meta`.
_Avoid_: evaluation, benchmark, accuracy (the figures are precision and recall, not accuracy)

**Live model**:
The model the current donor_ids were assigned with: the newest saved model whose resolution run finished. A model saved by a run that stopped part way is kept, and can be resolved with again, but is not live until a run with it finishes.
_Avoid_: latest model, newest model (a newer one may be saved and not live)

### Data tiers

**File catalogue**:
The regulator bulk files fundlens reads. A file outside it is neither downloaded nor read.
_Avoid_: file list, registry, manifest (the manifest is a snapshot's)

**Undated file**:
A regulator bulk file published once for every cycle, not once per cycle. Bronze keeps a copy under each cycle extracted, so a cycle rebuilds from its own bronze alone.
_Avoid_: global file, cycle-less file, shared file

**Bronze**:
Raw regulator bulk files exactly as downloaded.

**Silver**:
Normalized canonical tables in Parquet, partitioned by cycle.

**Gold**:
Pre-aggregated serving tables in Postgres that every page reads from. No page aggregates on request.

**Publish**:
The atomic swap that makes a freshly built gold schema live, followed by the cache purge.

**Build**:
One run of the pipeline for one cycle, named by its `build_id` (`YYYYMMDDTHHMMSSZ` of the run start). Every step of a run writes under the same build; `seats`, `transform`, `load` and `publish` must be given the same one.
_Avoid_: run id, version

**Live build**:
The build `gold.meta.cycles` names for a cycle: the one gold was built from and the one the API resolves silver partitions from. Every publish and rollback copies them to `markers/live.json` in R2, and a load of one cycle rebuilds gold from its new build and every other cycle's live build. The build it replaced sits in `gold_prev` and is the rollback target.
_Avoid_: current build, latest build (the newest build in R2 need not be live)

**Backfill-pending table**:
A silver table a live build may lack because the build was transformed before the table existed. A cycle whose build lacks one reads as having no rows of it, in gold and in a snapshot, whose manifest lists the table with only the cycles that have it. The tables are listed in `paths.BACKFILL_PENDING`: a silver ticket adds its table in the PR that creates it, and the backfill that rebuilds every cycle empties the list. Any other table missing from a live build fails the load and the snapshot.
_Avoid_: optional table, absent table (the state is temporary, and ends with the backfill)

**Rollback**:
`fundlens publish --rollback`: swapping `gold_prev` back in as `gold` and purging again. A second rollback swaps forward again.

**Snapshot**:
One dated release of the public dataset: the resolved silver tables, crosswalk and overrides as published to data.fundlens.org. `latest` always points at the newest snapshot.
