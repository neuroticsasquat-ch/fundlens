# Methodology

fundlens is built from the Federal Election Commission's public bulk data. This page says what goes
in, how money is counted, how individual donors are resolved, and how well that resolution scores
against an independent reference.

## Data sources and cycles

Every figure comes from the FEC's bulk data files for each two-year cycle: committees, candidates,
the links between candidates and their committees, contributions from individuals, contributions
from committees to candidates, and other committee transactions. The current cycle is rebuilt every
week from fresh downloads; earlier cycles are built once.

Only itemized contributions appear. A committee has to itemize a contributor once their gifts pass
$200, so most smaller gifts are in a committee's reported totals but not in this data.

{{cycles}}

## Earmarks are counted once

A gift made through a conduit such as ActBlue or WinRed is reported twice: once by the conduit,
which passes it on, and once by the campaign that receives it. fundlens counts it once, as the
recipient reported it, and records the conduit alongside it. This is the convention FEC.gov and
OpenSecrets follow, so a conduit is never a race's top recipient and totals reconcile with theirs.
Money given to a conduit itself, such as a tip to ActBlue, counts to the conduit.

The same rule keeps joint fundraising from counting twice. A joint fundraising committee's transfers
to its participants are committee money, shown apart from individual contributions. The memo lines
in which a participant names the people behind a transfer help resolve donors, but are never added
to any total. Where the joint committee itemized a gift itself, the money is counted there;
where it did not, the money appears only as the joint committee's transfer.

## Self-funding

A candidate's own money, including loans to their campaign, is shown as self-funding on the
candidate. It is not counted as an individual contribution, and a candidate is never listed as
their own top donor.

## The seat calendar

Races come from a calendar of every seat up in a cycle, not from whatever candidates filed for:
every House district under the apportionment in force, the delegate seats (the District of
Columbia, Puerto Rico, American Samoa, Guam, the Northern Mariana Islands and the U.S. Virgin
Islands), the Senate class up that cycle and any special elections, and the presidency every fourth
year. A candidate attaches to a seat by the office, state and district they filed for. A filing that
matches no seat is set aside for review; it never creates a race.

## How donors are resolved

The FEC gives committees and candidates IDs, but not the people who give to them. One person can
appear as `SMITH, JOHN`, `SMITH, JOHN A MR.` and `SMITH, JON`, under different employers and
addresses. fundlens resolves them into donors in five steps.

1. **Contributor keys.** Each contribution's name, ZIP code, employer and occupation are
   normalized: names parsed and stripped of titles and suffixes, ZIP codes cut to five digits,
   common employer spellings merged, and placeholders such as "self-employed" and "retired"
   cleared. Each distinct combination is a contributor key. Resolution works on these keys rather
   than on every contribution.
2. **Probabilistic linkage.** [Splink](https://github.com/moj-analytical-services/splink) scores
   pairs of keys that share a similar-sounding surname and area, a surname, first initial and
   state, or a surname and employer, on
   how well their first names, last names, ZIP codes, cities, employers and occupations agree. Two
   first names that plainly disagree all but rule a pair out; an initial or a common nickname does
   not.
3. **Clustering.** Pairs scored as near-certain matches are joined into clusters. Clusters are
   Splink's connected components, re-clustered so that no cluster holds two first names the model
   rejects or more than 200 keys.
4. **Overrides and adjudication.** A short list of merges and splits, each checked by a person and
   kept in the public repository, is applied next. Then a language model's verdicts on ambiguous
   cases involving at least $50,000 are applied where the model was confident: two clusters with one
   surname and area that linkage scored as possible matches, or one cluster whose keys report
   different employers. The model is consulted in batches while the data is built, never when you
   load a page.
5. **The crosswalk.** Each cluster gets a permanent donor ID. A cluster keeps the ID its keys
   already carry, so donor links stay the same from week to week. When two donors turn out to be
   one, the retired ID redirects to the one that remains. IDs are never reused.

## How well it scores

{{quality}}

Resolution is scored against the Database on Ideology, Money in Politics, and Elections (DIME),
which assigns its own contributor ID to each FEC contribution: Bonica, Adam. 2024. *Database on
Ideology, Money in Politics, and Elections: Public version 4.0* [Computer file]. Stanford, CA:
Stanford University Libraries. <https://data.stanford.edu/dime>. Used under the Open Data Commons
Attribution License (ODC-BY 1.0).

fundlens matches its contributions to DIME's by the filer's own transaction IDs, so only
electronically filed contributions are scored, and the figures count pairs of contributor keys
that DIME labels. Precision is the share of the pairs fundlens puts in one donor that DIME also
puts together: when it is low, different people have been merged. Recall is the share of the pairs
DIME puts together that fundlens also does: when it is low, one person is split across several
donors.

## Known limitations

- **Resolution errs in both directions.** Several people sharing a common name in one area can be
  merged into one donor, and someone who moves or changes jobs can be split into several. Check a
  donor's contributions before relying on their total.
- **Only itemized contributions.** Gifts below the itemization threshold are not in the data, so a
  campaign's itemized total is less than what it raised.
- **Scored on electronic filings only.** Contributions filed on paper cannot be matched to DIME, so
  the score rests on fewer contributions for older cycles, and on none for a cycle DIME does not
  yet cover.
- **As reported.** Names, employers and occupations are what the filer wrote. fundlens does not
  code industries or correct a filer's mistakes.
- **Federal races only.** No state or local races.
- **Weekly.** Filings and amendments the FEC processes after a weekly build appear in the next one.

## Using the data

The resolved data is published as an open dataset under CC BY 4.0: see the
[dataset page](/dataset). The code that builds it is MIT-licensed and public on
[GitHub](https://github.com/neuroticsasquat-ch/fundlens).

Federal law limits how contributor information may be used (52 U.S.C. 30111(a)(4), 11 CFR 104.15):
information copied from reports filed with the FEC may not be sold or used by any person for the
purpose of soliciting contributions or for commercial purposes, other than using the name and
address of a political committee to solicit contributions from that committee.
