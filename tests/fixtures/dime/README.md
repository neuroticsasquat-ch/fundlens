# DIME-shaped labels for the fixture cycle

`contribDB_2024.csv` gives each counted contribution in `tests/fixtures/fec/2024/indiv.csv` the
`bonica.cid` of the donor behind it, the way Bonica's DIME contribution records label real FEC
contributions. It is the ground truth `fundlens validate` scores the fixture's resolved donors
against (spec §6.9, ADR-0009): one row per counted contribution, one `bonica.cid` per invented
donor.

The columns are a subset of the real `contribDB_<cycle>.csv.gz` header of DIME Public version 4.0
(NEU-2054 §1.3), with its names, order and conventions: lower-case names and places, ISO dates,
amounts as the contribution counts (a refund negative). The validator joins on the two FEC ids
DIME carries for every electronically filed row:

- `efec.comid.orig`: the filer's FEC committee id, the `indiv` row's `CMTE_ID`;
- `efec.transaction.id.orig`: the filer's transaction id, its `TRAN_ID`;

with `amount` (by magnitude, since a refund's sign is the filer's choice) and `date`, and then the
`indiv` row's `SUB_ID` to silver `contribution`. `bonica.rid` holds DIME's own recipient id
(`comm<n>`), never an FEC id, so nothing joins on it by accident. `contributor.type` is `I`
throughout: the validator keeps only individuals' rows. `fundlens dime --import` reads this file as
it reads the real one.
