# fundlens

A free, public campaign-finance data platform: donor, candidate and committee money for every race in the country, presented by race, with individual donors correctly resolved across name, employer and address variants. The resolved dataset is the product; the web app is its demo.

## Language

### Money

**Contribution**:
One itemized transfer of money from a contributor to a committee, as reported to the regulator, in the canonical schema regardless of source (FEC bulk today, state portals later).
_Avoid_: donation, transaction, record

**Independent expenditure**:
Money a committee spends for or against a candidate without coordinating with them. It attaches to a race and a candidate but is never a contribution.
_Avoid_: IE spend, outside money, super PAC money

**Earmark**:
A contribution routed through a conduit (ActBlue, WinRed) to its final recipient. The regulator reports it twice, on the conduit side and the recipient side; fundlens counts it once. A committee passing on a gift it did not deposit (Senate Conservatives Fund's to a candidate, type 24I) is an earmark too: its side is dropped when the recipient itemized the gift, and kept, the committee's, when that side is the only record. Most 24Is are not this: they are recipients' own receipts of earmarks through a conduit.
_Avoid_: conduit contribution, pass-through

**JFC attribution**:
A joint fundraising committee participant's memo line (FEC type 15J) naming the individual behind part of a JFC transfer and the share attributed to that participant. Evidence that the individual's money reached the participant; never a contribution, and never counted in a total.
_Avoid_: JFC contribution, attributed contribution

**JFC transfer**:
A joint fundraising committee's transfer of its participants' shares to a participant committee: a receipt from a designation-J committee, whatever type the filer gave it (mostly 18G, some 18J and 15J). Counted for a candidate when the participant raises for one, apart from the candidate's contributions and committee gifts. Committee money, never a contribution.
_Avoid_: JFC contribution

**Organization receipt**:
One itemized gift from an organization to a committee, as reported to the regulator, held in `organization_receipt`. Organization money, never a contribution: in no individual total, no top-donor list and no race or candidate total; counted on the committee that received it. Loans (16C, 16F, 16G) and 15J memo lines are not receipts.
_Avoid_: organization contribution, corporate donation, corporate money (unions and tribes give too)

**Non-contribution account**:
A hybrid PAC's (FEC committee type V or W) second account, outside the contribution limits, whose receipts the regulator types 10 (24I for an earmark through a conduit, when its memo names the account; a 24I without that memo is the contribution account's) and whose refunds it types 20Y. Individuals' and organizations' money to it is kept, as contributions and organization receipts, with its refunds, and counted in the committee's own figure, never in its individual or organization totals, which hold the contribution account the regulator's itemized figure counts. Its givers are in the committee's top-donor and top-organization lists. A committee's gift to it is counted as any committee's gift. A type 10 to any other committee is an ordinary contribution.
_Avoid_: Carey account, soft money, super PAC account

**Party account**:
One of a national party committee's three accounts outside its main one, a convention, a headquarters and a recount account, whose receipts the regulator types 30, 31 and 32 (with variants such as 31T and 32E) and whose refunds 40Y, 41Y and 42Y. Individuals' gifts to one are kept as contributions, the donors', and counted in the committee's other-lines figure, never in its individual total, which holds what the regulator files on line 11(a)(i).
_Avoid_: building fund, soft money, special account

**Other-lines money**:
An individual's counted money the regulator files on a line other than 11(a)(i) and outside a non-contribution account: a party account's, a loan, a transfer or other receipt (18G, 18U, 18H) or a Form 9 donation. Kept, as contributions, in the donor's figures, the committee's own figure and no individual total; a candidate's own money is self-funding whatever its line.
_Avoid_: off-book money, non-itemized money

**Self-funding**:
A candidate's own money, including loans, given to their own committee. Reported separately from top-donor lists so a candidate does not appear as their own largest donor.

### Parties

**Donor**:
A resolved individual: the persistent identity behind many contributor-name, employer and address variants. Only individuals need resolution; committees and candidates already carry regulator IDs, and organizations are grouped by organization key, not resolved.
_Avoid_: contributor (that is the raw, unresolved name on a record), person, entity

**Contributor**:
The raw name, employer, occupation and address as reported on a single contribution (or JFC attribution), before resolution.

**Committee**:
A regulator-registered fundraising entity (candidate committee, PAC, party committee, super PAC) identified by its regulator ID.

**Organization**:
A giver that is neither an individual nor a committee: a corporation, union, trade association, tribe, 527 or other group, identified only by the name it is reported under. It carries no regulator ID and is never resolved; its receipts are grouped by organization key.
_Avoid_: corporate donor, entity (that is FEC's word for every giver type), business, non-individual

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
A committee (ActBlue, WinRed) that forwards earmarked contributions to their final recipient. Flagged on the contribution; never a recipient in fundlens.

**Handoff**:
A candidate committee passed from one candidate to another mid-cycle (Biden's 2024 campaign, Harris's from 2024-07-21). Listed by hand in `fec/handoffs.csv`, never inferred; the committee's money is the first candidate's before the handoff date and the second's from it on.
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

### Data tiers

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
The build `gold.meta.cycles` names for a cycle: the one gold was built from and the one the API resolves silver partitions from. The build it replaced sits in `gold_prev` and is the rollback target.
_Avoid_: current build, latest build (the newest build in R2 need not be live)

**Rollback**:
`fundlens publish --rollback`: swapping `gold_prev` back in as `gold` and purging again. A second rollback swaps forward again.

**Snapshot**:
One dated release of the public dataset: the resolved silver tables, crosswalk and overrides as published to data.fundlens.org. `latest` always points at the newest snapshot.
