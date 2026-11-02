---
status: accepted
---

# Earmarked contributions count once, on the recipient side

FEC bulk data reports an earmarked contribution twice: the conduit (ActBlue, WinRed) reports receiving it and passing it on (transaction type `24T`), and the final recipient re-itemizes it with `MEMO_CD = 'X'` on the conduit's memo line. Counting both doubles every small-dollar donor and makes the conduits the top recipient of every race, which is what the ~2025 attempt got wrong. fundlens keeps the recipient-side itemization as the one counted contribution, drops `MEMO_CD = 'X'` memo rows and `24T` conduit rows from the contribution table, and records the conduit on the kept row as `conduit_committee_id`. This is the convention FEC.gov and OpenSecrets follow, so fundlens totals reconcile with theirs.

## Considered options

- **Keep both rows with a `counted` flag.** Full fidelity for the public dataset, but every consumer has to know the rule or they double count. Rejected: the dataset's point is to be the cleaned copy.
- **Count the conduit side.** Matches the conduit's own report but attributes money to ActBlue rather than the candidate.

## Amended 2026-10-31: what the real 2024 files add (NEU-2070)

The first production run found two variants the fixture lacked. A conduit also files some earmarks' own side as a plain type `15` whose `MEMO_TEXT` names the recipient (`EARMARKED FOR BIDEN FOR PRESIDENT (C00703975)`, about $7M from ActBlue in 2024). That row is the conduit side, the same as a `24T`, and is dropped. And a conduit receives money of its own: ActBlue's 4.07M `CONTRIBUTION TO ACTBLUE` rows (mostly tips, $26.5M) are gifts to ActBlue, counted to it as recipient with no `conduit_committee_id`, since a committee is never the conduit of a gift to itself. The rule stands: an earmark counts once, on the recipient side.

## Amended 2026-11-01: a conduit's 24K in `pas2`

A conduit also files earmarks' own side in `pas2`, as committee contributions (type `24K`) to the recipient. Measured on FEC's public 2024 `pas2` file: WinRed filed 348,042 of them, netting −$10,171,281 (+$3,531,688 passed on, −$13,702,969 refunded), and ActBlue 28, all refunds, −$108,575. `committee_transfer` took them for committees' gifts, so the 2024 presidential race showed −$546,635 "from committees", with Haley at −$1,126,482. They are the conduit side, like a `24T`, and are dropped from `committee_transfer`: no candidate's `total_committee` and no conduit's `total_to_candidates` includes them. The rule stands: an earmark counts once, on the recipient side. Not measured: whether recipients also file `oth` receipts from a conduit that `total_from_committees` counts.
