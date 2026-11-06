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

## Amended 2026-11-06: what a 24I is (NEU-2203)

FEC defines 24I as "earmarked intermediary out", a conduit-side code like 24T, and NEU-2193 kept it out of `total_individual` as one. Measured on FEC's 2024 files (`docs/measurements/summary-files-2024.md` Q10), it is mostly not. Of 138,156 counted 24Is ($4,664,149), 136,731 ($4,166,976) are recipients' own receipts of earmarks through ActBlue or WinRed: Retired Americans PAC, SMP and 21 other filers coded them 24I, not 15E, with the conduit in `OTHER_ID` or `MEMO_TEXT`. They are the recipient side and count, with the conduit as `conduit_committee_id`. Every counted 24I is filed on Form 3X line 11(a)(i), except two hybrid PACs' 151 ($22,920), on line 17 for their non-contribution account. So `fec_line` puts a 24I where it puts a 10, which misplaces the one other hybrid PAC's 24I, a V committee's $1,000 on 11(a)(i). One more 24I ($500) names an id `cm` lacks, and counts.

The rest, 1,424 ($496,673), are an intermediary's side: a committee that is no conduit (Senate Conservatives Fund, House Freedom Fund, Club for Growth PAC and three others) passing an individual's gift on to the candidate committee its `OTHER_ID` names. Where that committee itemized the gift too (a row of the same name and amount, no memo line, refund, 24T or 24I, within 30 days), the 24I is dropped as a 24T is: 262 rows, $235,403, in 2024. Where it did not (1,162 rows, $261,270), the 24I is the only record of the gift and counts, the intermediary's. The rule stands: an earmark counts once, on the recipient side when there is one. Dropping every 24I was rejected: it would erase the $4.17M of recipient-side money no other row holds.
