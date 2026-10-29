---
status: accepted
---

# Earmarked contributions count once, on the recipient side

FEC bulk data reports an earmarked contribution twice: the conduit (ActBlue, WinRed) reports receiving it and passing it on (transaction type `24T`), and the final recipient re-itemizes it with `MEMO_CD = 'X'` on the conduit's memo line. Counting both doubles every small-dollar donor and makes the conduits the top recipient of every race, which is what the ~2025 attempt got wrong. fundlens keeps the recipient-side itemization as the one counted contribution, drops `MEMO_CD = 'X'` memo rows and `24T` conduit rows from the contribution table, and records the conduit on the kept row as `conduit_committee_id`. This is the convention FEC.gov and OpenSecrets follow, so fundlens totals reconcile with theirs.

## Considered options

- **Keep both rows with a `counted` flag.** Full fidelity for the public dataset, but every consumer has to know the rule or they double count. Rejected: the dataset's point is to be the cleaned copy.
- **Count the conduit side.** Matches the conduit's own report but attributes money to ActBlue rather than the candidate.
