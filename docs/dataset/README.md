# fundlens dataset

Federal campaign-finance money for every cycle since 1980, from the FEC's bulk files, as open
Parquet files: contributions, committees, candidates, races, committee transfers, organizations'
gifts, independent expenditures, electioneering communications, committees' spending and the
totals committees report, with **individual donors resolved** across the name, employer and address
variants they are reported under. It is the data behind [fundlens.org](https://fundlens.org).

Served from `https://data.fundlens.org/v1/`. License: [CC BY 4.0](LICENSE). Read the
[notice on contributor information](#notice-contributor-information-and-the-fec) before you use
it.

## What is in it

| Table | One row per | Files |
|---|---|---|
| `contribution` | itemized contribution from an individual to a committee, with its `donor_id` | `contribution/cycle=<c>/*.parquet` |
| `contributor` | contributor key (a unique normalized name, ZIP5, employer and occupation) seen in a cycle | `contributor/cycle=<c>/*.parquet` |
| `donor` | resolved donor, across every cycle | `donor.parquet` |
| `crosswalk` | contributor key, with the donor it is resolved to | `crosswalk.parquet` |
| `committee` | committee registered with the FEC in a cycle | `committee/cycle=<c>/*.parquet` |
| `candidate` | candidate registered with the FEC in a cycle | `candidate/cycle=<c>/*.parquet` |
| `candidate_committee_link` | link between a candidate and a committee in a cycle | `candidate_committee_link/cycle=<c>/*.parquet` |
| `race` | contest for one seat in one cycle | `race/cycle=<c>/*.parquet` |
| `committee_transfer` | committee's money to another committee or a candidate | `committee_transfer/cycle=<c>/*.parquet` |
| `organization_receipt` | itemized gift to a committee from an organization | `organization_receipt/cycle=<c>/*.parquet` |
| `independent_expenditure` | expenditure for or against a candidate | `independent_expenditure/cycle=<c>/*.parquet` |
| `reported_total` | committee's own reported totals for a cycle (from 1996) | `reported_total/cycle=<c>/*.parquet` |
| `candidate_reported_total` | candidate's own reported totals for a cycle, before 2008 | `candidate_reported_total/cycle=<c>/*.parquet` |
| `operating_expenditure` | payment a committee itemized as spending (from 2004), counted or not | `operating_expenditure/cycle=<c>/*.parquet` |
| `electioneering_communication` | electioneering communication's share for one candidate (from 2010) | `electioneering_communication/cycle=<c>/*.parquet` |

Every column of every table is described in its JSON Schema, `schema/<table>.json` (for
example [`schema/contribution.json`](schema/contribution.json)), and every change to them is in
the [changelog](CHANGELOG.md). Beside the tables, a snapshot holds
`overrides.yaml`, the hand-reviewed merges and splits of donors applied after resolution, and
`manifest.json`.

A few things to know before you add anything up:

- **An earmark counts once.** A contribution through a conduit (ActBlue, WinRed) is its final
  recipient's row, with the conduit in `conduit_committee_id`; the conduit's own side is left
  out.
- **Refunds are negative.** A refund of a contribution or an organization's gift is negative
  whatever sign it was filed with; corrections are kept, and both net out in a sum.
- **Some rows are outside a committee's individual total**: a candidate's own money
  (`is_self_funding`), a hybrid PAC's non-contribution account (`is_non_contribution_account`)
  and money filed on another line of the FEC form (`is_other_line`). They are kept, and the
  donors' own. An organization receipt whose memo names a cost coming back to the committee, a
  tax or vendor refund, is no gift at all (`is_returned_cost`), on another line too.
- **`committee_transfer` holds both sides of many gifts.** Sum one `side` only.
- **A reported total is never added to `contribution` amounts.** `reported_total` and
  `candidate_reported_total` hold the FEC's own cycle-to-date figures, as filed: they already
  include the itemized money the other tables itemize. Compare the two; don't sum them.
- **Tell `independent_expenditure`'s kinds apart by `kind`.** Only `kind = 'ie'` is independent
  expenditure. A row with `source_file = 'ie_24_48'` is a 24- or 48-hour report's estimate, and
  leaves the table when a periodic report restates it, so its `source_record_id` is not stable
  from one snapshot to the next. Outside spending is never to be added to `contribution` amounts.
- **Sum `electioneering_communication`'s `amount`, never `disbursement_amount`.** A disbursement
  naming several candidates is one row per candidate, each with the FEC's equal share in
  `amount`; `disbursement_amount` is the whole disbursement, on each of its rows. A row has no
  side: the filing does not say whether the ad is for or against the candidate. The FEC's file
  shows no amendment, so a report a later one restates may be counted twice (0.36% of 2024's
  dollars). Outside spending is never to be added to `contribution` amounts.
- **Organizations are not resolved.** Their gifts are grouped by `organization_key`, the
  normalized name.
- **Sum `operating_expenditure` only where `counted` is true.** A sub-item, a card bill's charge
  or a reimbursement's receipt, is shown under the payment it itemizes
  (`parent_source_record_id`) and never added to it. `payee_key` is a normalized name, not an id:
  payees are grouped by it, never resolved. Spending is never to be added to `contribution`
  amounts, nor to any other receipt. `spending_category` is fundlens's reading of the purpose,
  not the FEC's code (`fec_category` holds that, as filed); `category_source` says which rule
  gave it. Both are null in a build made before fundlens classified spending.
- A `cycle=<c>` directory is a Hive partition. `contributor`'s files hold no cycle column of
  their own: read it from the path, as DuckDB does, adding a `cycle` column.

## How it is built

A weekly batch run downloads the FEC's bulk files for the current cycle, transforms them into
these tables, resolves contributors into donors and publishes the result to fundlens.org.
Historical cycles are built once and frozen. Resolution links contributor keys into donors by
probabilistic record linkage (Splink), then applies the reviewed overrides; the crosswalk keeps a
donor's `donor_id` stable from week to week, so an id changes only when a donor is merged or
split. Resolution is scored against DIME (Bonica, Stanford): `manifest.json` gives the pairwise
`precision` and `recall`. The code is at
[github.com/neuroticsasquat-ch/fundlens](https://github.com/neuroticsasquat-ch/fundlens), MIT.

## Snapshots

A snapshot is taken weekly, after the Sunday run, at `v1/<YYYY-MM-DD>/`. The newest 8 are kept.
`v1/latest/` is a copy of the newest.

Each snapshot's `manifest.json` lists its live build per cycle, every file with its row count,
size and SHA-256, and the resolution scores (null until the live model is scored). Paths in it
are relative to the snapshot, so they hold for `latest/` too. A table added to the dataset
recently may have no files for a cycle not yet rebuilt since: the manifest lists exactly the files
that exist, so read a table's cycles from its files, not from `cycles`. Abridged, with made-up
values:

```json
{
  "snapshot_date": "2026-11-22",
  "build_id": "20261122T030000Z",
  "cycles": {"2024": "20261122T030000Z"},
  "tables": {"race": {"rows": 470, "files": [{"path": "race/cycle=2024/part-0000.parquet", "sha256": "…", "bytes": 9876}]}},
  "overrides": {"path": "overrides.yaml", "sha256": "…", "bytes": 1234},
  "precision": 0.97,
  "recall": 0.95,
  "license": "CC BY 4.0",
  "attribution": "fundlens (fundlens.org), CC BY 4.0"
}
```

`latest/` is refreshed in place, so while it is being copied a reader can see parts of two
snapshots. For an exact read, read a dated snapshot, or the files `latest/manifest.json` lists.

## Reading it

The files are served over plain HTTPS. HTTPS has no directory listing, so a `*.parquet` glob
does not work: list the files from `manifest.json`. In DuckDB, every 2024 contribution:

```sh
duckdb -c "
SET VARIABLE files = (
  SELECT list('https://data.fundlens.org/v1/latest/' || f.path)
  FROM (SELECT unnest(tables.contribution.files) AS f
        FROM read_json('https://data.fundlens.org/v1/latest/manifest.json'))
  WHERE f.path LIKE 'contribution/cycle=2024/%');
SELECT count(*) AS contributions, sum(amount) AS dollars
FROM read_parquet(getvariable('files'));
"
```

In pandas (with pyarrow) or polars:

```python
import json, urllib.request
import pandas as pd
import polars as pl

base = "https://data.fundlens.org/v1/latest/"
manifest = json.load(urllib.request.urlopen(base + "manifest.json"))
races = [base + f["path"] for f in manifest["tables"]["race"]["files"]]

donors = pd.read_parquet(base + "donor.parquet")  # one file
races_pd = pd.concat(pd.read_parquet(url) for url in races)  # pandas
races_pl = pl.read_parquet(races)  # polars
```

A per-IP rate limit applies to `data.fundlens.org`. A query that reads many files at once, a
whole cycle of contributions for one, can reach it. For work across a whole table or the whole
dataset, download the files once and read them locally. With `curl` and `jq`, checking every
file against the manifest:

```sh
base=https://data.fundlens.org/v1/latest
curl -fsS -o manifest.json "$base/manifest.json"
jq -r '.tables[].files[].path, .overrides.path' manifest.json | while read -r path; do
  curl -fsS --retry 5 --create-dirs -o "$path" "$base/$path"
done
jq -r '(.tables[].files[], .overrides) | "\(.sha256)  \(.path)"' manifest.json | sha256sum -c --quiet
```

## License and attribution

The dataset is licensed under the [Creative Commons Attribution 4.0 International
license](LICENSE) (CC BY 4.0). Credit it as:

> fundlens (fundlens.org), CC BY 4.0

The code that builds it is MIT-licensed. The FEC's own filings are public records.

## Notice: contributor information and the FEC

Federal law restricts how the contributor information in FEC reports may be used, and this
dataset is drawn from those reports. 52 U.S.C. §30111(a)(4) and the FEC's rule at 11 CFR 104.15
say that information copied from them may not be sold or used by anyone to solicit contributions
or for any commercial purpose, other than using a political committee's name and address to
solicit contributions from that committee. Committees may include a few fictitious contributor
names in their reports to detect such use.

**These restrictions apply to the contributor information in this dataset (names, addresses,
employers and occupations, resolved into donors or not) independently of this license.** CC BY
4.0 grants what rights fundlens holds in the dataset; it cannot waive the law's limits on what
the information may be used for. Some states restrict the use of their own campaign-finance data
further.

This notice is not legal advice. If your use is commercial or involves contacting donors, read
11 CFR 104.15 and the FEC's guidance on it, and ask a lawyer.
