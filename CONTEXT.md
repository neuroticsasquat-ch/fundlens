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
A contribution routed through a conduit (ActBlue, WinRed) to its final recipient. The regulator reports it twice, on the conduit side and the recipient side; fundlens counts it once.
_Avoid_: conduit contribution, pass-through

**Self-funding**:
A candidate's own money, including loans, given to their own committee. Reported separately from top-donor lists so a candidate does not appear as their own largest donor.

### Parties

**Donor**:
A resolved individual: the persistent identity behind many contributor-name, employer and address variants. Only individuals need resolution; committees and candidates already carry regulator IDs.
_Avoid_: contributor (that is the raw, unresolved name on a record), person, entity

**Contributor**:
The raw name, employer, occupation and address as reported on a single contribution, before resolution.

**Committee**:
A regulator-registered fundraising entity (candidate committee, PAC, party committee, super PAC) identified by its regulator ID.

**Candidate**:
A person seeking an office in a cycle, identified by their regulator ID.

### Structure

**Cycle**:
The two-year federal election period, named by its even year (2024). Historical cycles are frozen; the current cycle is rebuilt weekly.
_Avoid_: election year, period

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

### Resolution

**Contributor key**:
The exact normalized tuple (name, ZIP5, employer, occupation) that identifies one unique contributor string across all its contributions. Resolution runs over contributor keys, not over contributions.

**Cluster**:
The set of contributor keys that probabilistic linkage judges to be the same person in one resolution run.

**Crosswalk**:
The persistent mapping from contributor key to donor ID, so weekly rebuilds do not reshuffle donor URLs. A new cluster inherits the donor ID its members already carry; only never-seen keys get new IDs.

**Override**:
A manual merge or split assertion applied after linkage, authored data that survives every rebuild.

**Adjudication**:
A model's judgment on an ambiguous high-value cluster, recorded as an override with its provenance.

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
