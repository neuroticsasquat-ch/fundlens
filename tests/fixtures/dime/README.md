# DIME-shaped labels for the fixture cycle

`contribDB_2024.csv` gives each counted contribution in `tests/fixtures/fec/2024/indiv.csv` the
`bonica.cid` of the donor behind it, the way Bonica's DIME contribution records label real FEC
contributions. It is the ground truth the resolution validator scores clusters against
(spec §6.9): one row per counted contribution, one `bonica.cid` per invented donor.

The columns are a subset of DIME's `contribDB` with its names and conventions (lower-case
names and places, ISO dates). `bonica.rid` here holds the recipient's FEC committee id, the key
the validator joins on with date, amount and name; the DIME validation ticket (NEU-2054) pins
the real file's columns and join, and this file follows whatever that settles.
