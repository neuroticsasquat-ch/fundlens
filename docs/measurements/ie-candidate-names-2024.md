# The candidate 2024's independent expenditures name: `pas2`'s `CAND_ID` against the filings

Measured for [NEU-2279](https://linear.app/neuroticsasquatch/issue/NEU-2279) (milestone M4
Backfill and independent expenditures). NEU-2277 credits spending that names Biden, dated on or
after the handoff, to Harris. Future Forward's three 24As of 2024-10-17 against **TRUMP, DONALD
J.** carry Biden's id in `pas2`, so they moved from Biden's `ie_oppose` to Harris's. This document
counts how often an independent expenditure's `CAND_ID` names a candidate other than the one its
filing names, and fixes the correction that NEU-2279 ships.

| What | Value |
| --- | --- |
| Run | 2026-11-12, 20:45–21:20 UTC, in the local `app` container |
| Code | `main` at `2ee9bcb118888dfb0e9778edfd5ed17b01128e3f` (NEU-2277 merged) |
| DuckDB | 2.0.0 |
| `pas224.zip` | `https://www.fec.gov/files/bulk-downloads/2024/pas224.zip`, `Last-Modified: Sun, 08 Nov 2026 21:37:55 GMT`, downloaded 2026-11-12T20:45Z |
| `cn24.zip` | `…/2024/cn24.zip`, `Last-Modified: Thu, 12 Nov 2026 06:40:08 GMT`, downloaded 2026-11-12T20:45Z |
| Filings | `https://docquery.fec.gov/dcdev/posted/<FILE_NUM>.fec` for each `FILE_NUM` of a counted 2024 IE row, 3,026 filings, fetched 20:46–20:47 UTC (1.08 GB). Only `HDR` and `SE` lines were kept, plus `F57` lines from the 251 Form 5 filings, fetched again at 20:51 UTC |
| `independent_expenditure_2024.csv` | `…/2024/independent_expenditure_2024.csv`, the 24/48-hour reports, downloaded 2026-11-12T20:44Z; a cross-check only |
| Live gold | build `20261112T193911Z`; Harris's 2024 `ie_oppose` there is $571,351,248, as this run's `pas2` gives it |

## Headline

- **The filings name the right candidate. The wrong id is FEC's coding in `pas2`.** Future
  Forward's amended F3X (filing 1894243) files all three lines as `O`, `P80001571`, TRUMP,
  DONALD J. FEC's `pas2` codes them `P80000722`, Biden's. Their `SUB_ID`s are
  `4060220251204384139` ($21,652), `4060220251204384159` ($229,244) and `4060220251204384180`
  ($15,743), $266,639 in all.
- **1,386 rows, $228,808,149, carry a `CAND_ID` that names a candidate other than the one their
  filing names** (Q2's "no" rows). 1,290 of them ($225,172,917) are Harris's spending coded Biden's
  after the handoff, which NEU-2277 already credits to her (Q3).
- **Of the $10,953,874 against Biden dated on or after the handoff, $268,489 is spending against
  Trump**: Future Forward's three lines and one of $1,850. $10,415,779 is filed against Harris,
  which NEU-2277 credits correctly, and $269,606 against Biden himself (Q4).
- **After the handoff, 96 rows ($3,635,232, 0.08% of 2024's IE dollars) are credited to a
  candidate their filing does not name.** 58 of them ($2.84M) are filed with an id and a name that
  agree, which `pas2` recodes to someone else (Q5).
- **That is a handful, so the fix is a vendored correction list** keyed by `SUB_ID`:
  `src/fundlens/fec/ie_candidate_corrections.csv`, one row for each of the 96 (Decisions).

## Method

The bulk files name no candidate on an IE row: `pas2`'s `NAME` is the payee. The filing does. A
`pas2` row's `FILE_NUM` is the electronic filing it was processed from, and its `TRAN_ID` is the
line's transaction id within that filing. So each counted 2024 IE row (`TRANSACTION_TP` 24A or 24E,
`MEMO_CD` not `X`; 73,825 rows, $4,422,471,620, as silver counts them) was matched to its own line:
an `SE` line of a Form 3X, or an `F57` line of a Form 5, with the same filing, filer and
transaction id. All 3,026 filings are format 8.4 or 8.5, field-separated by `0x1C`. On an `SE` line
the support/oppose code is field 26, the candidate id 27, and the last and first names 28 and 29;
on an `F57` line they are fields 23, 24, 25 and 26. 44 `SE` lines carry no `S` or `O` in field 26;
none of them is among the rows below.

A filed name **fits** a candidate when a token of three or more letters of the one (apostrophes
dropped, other punctuation a break, `JR`, `SR`, `III` and the like ignored) equals a token of the
other, or is one edit from it at five letters or more. That tolerates `D'Esposito`/`DESPOSITO`,
`Cleo Fields` filed first-name-last, `cn`'s own swapped `NICK, LALOTA`, and typos such as `TRIUMP`.
The **credited** candidate is the one silver attaches the row to: `CAND_ID`, then Biden's id
dated on or after 2024-07-21, or undated, as Harris's (NEU-2277).

The 24/48-hour file holds the same transactions under the same `TRAN_ID` (Future Forward's
`500191988` is in both). There, though, Future Forward's line names Trump with his own id, and the
amounts are the 24-hour report's estimates. It disagrees with `pas2`'s id on 2,713 rows,
$284,808,027, for the same reasons Q2 finds. It is not the source of record for a `pas2` row, so
everything below reads the filings.

## Q1. How many rows match their filed line?

| Rows | Count | Amount | Filings |
| --- | ---: | ---: | ---: |
| Matched to their `SE` or `F57` line | 73,688 | $4,422,163,602 | 3,007 |
| Filing unread: 18 return 404, 1 Form 5 holds no `F57` line | 132 | $305,703 | 19 |
| No line with its `TRAN_ID` in a filing that was read | 5 | $2,315 | 1 |

## Q2. How often does `pas2`'s id differ from the filed one?

Often, and mostly harmlessly: FEC codes a filer's id to the one it keeps for the person.

| `CAND_ID` against the filed id | Filed name fits the `CAND_ID` candidate | Rows | Amount |
| --- | --- | ---: | ---: |
| Same | yes | 59,709 | $3,269,244,082 |
| Same | no | 983 | $9,978,276 |
| Same | can't tell (no filed name, or the id not in `cn`) | 375 | $13,555,000 |
| Different | yes | 2,994 | $337,963,423 |
| Different | no | 354 | $215,126,161 |
| Different | can't tell | 610 | $27,747,888 |
| None filed | yes | 8,495 | $532,806,407 |
| None filed | no | 49 | $3,703,712 |
| None filed | can't tell | 119 | $12,038,653 |
| Unmatched (Q1) | | 137 | $308,018 |

"Same, no" is the filer's own mismatch, which `pas2` keeps, Harris's name with Biden's id among
it. Most of "Different, no" is the reverse of FEC's usual recoding: 295 lines ($212,225,510)
filed for **Harris with her own id** are coded **Biden's**. Meanwhile 1,303 lines
($272,098,439) filed for Harris with Biden's id are coded hers. Both land on Harris once
NEU-2277's handoff applies, when dated on or after it.

## Q3. After the handoff, which rows are credited to a candidate the filing does not name?

| `CAND_ID` fits the filed name | Credited candidate fits it | Rows | Amount |
| --- | --- | ---: | ---: |
| yes | yes | 71,063 | $4,138,848,089 |
| no | yes, the handoff fixed it | 1,290 | $225,172,917 |
| yes | no, the handoff moved it from Biden | 135 | $1,165,823 |
| no | no | 96 | $3,635,232 |
| can't tell | | 1,241 | $53,649,559 |

The 135 rows name Biden and are dated on or after the handoff, or undated. NEU-2277 credits them
to Harris deliberately, as the committee's own money is credited, so they are not corrected here.
The 1,241 rows that can't be told apart either have no filed name or carry a `CAND_ID` that `cn`
lacks. The first keep their `CAND_ID` unchecked; the second are attached to no candidate.

## Q4. The post-handoff Biden rows, by the name filed

`CAND_ID` `P80000722`, dated on or after 2024-07-21 or undated: all of it is Harris's in silver.

| Filed name | Side | Rows | Amount | Spenders |
| --- | --- | ---: | ---: | ---: |
| Harris | against (24A) | 33 | $10,415,779 | 5 |
| Biden | against (24A) | 48 | $269,606 | 2 |
| **Trump** | against (24A) | 4 | **$268,489** | 2 |
| Harris | for (24E) | 1,257 | $214,757,138 | 28 |
| Biden | for (24E) | 87 | $896,217 | 10 |

The four Trump rows are Future Forward's three, plus `4120420241074513605` ($1,850, C00869347),
filed against TRUMP, DONALD J. with his id and coded Biden's.

## Q5. The 96 rows credited to a candidate their filing does not name

| How | Rows | Amount | Spenders |
| --- | ---: | ---: | ---: |
| The filed id and name agree; `pas2` recodes the id to another candidate | 58 | $2,839,712 | 26 |
| No id filed; `pas2` codes the wrong candidate | 35 | $698,658 | 8 |
| The filed id is another person's that `cn` lacks (`H4NY04158` for GILLEN, LAURA) | 1 | $60,939 | 1 |
| The filed id is another candidate's and `pas2` keeps it | 2 | $35,923 | 2 |

The largest are one spender's six lines in Pennsylvania's Senate race ($1,938,809), filed against
CASEY and for MCCORMICK with each one's own id, which `pas2` swaps. The rest include Future
Forward's three. A Form 5 filer's nine lines for QUINTANA, EDUARDO are coded GALLEGO, RUBEN, and
twelve 2023 lines against TRUMP, DONALD, filed with no id, are coded HALEY, NIKKI.

Each row is resolved to the candidate its filing names. That is the filed id where the name fits
it and `cn` lists it, and otherwise the one 2024 `cn` candidate whose surname and given name both
fit. Three were settled by hand: `Suozzi, Tom` → `H6NY03247` (the 2024-02-13 NY-03 special);
`Gallego, Ruben` → `S4AZ00139`, his Senate race, not his House id `H4AZ07043`; and `GILLEN, LAURA`
→ `H2NY04244`, her id in `cn`.

## Q6. What the correction changes

All 96 apply, `pas2` still coding each as listed. Credited by the rules above, before and after:

| Candidate | Side | Before | After | Change |
| --- | --- | ---: | ---: | ---: |
| HARRIS `P00009423` | against | $571,351,248 | $571,037,126 | −$314,122 |
| HARRIS `P00009423` | for | $740,131,217 | $740,058,971 | −$72,246 |
| TRUMP `P80001571` | against | $156,945,097 | $157,429,716 | +$484,619 |
| TRUMP `P80001571` | for | $237,603,938 | $237,842,278 | +$238,340 |
| BIDEN `P80000722` | for | $7,626,671 | $7,637,925 | +$11,254 |

Harris's `ie_oppose` drops by $314,122, not by the ticket's $266,639: four other lines against
Trump ($142,737) coded hers or Biden's leave too, and two against Harris ($95,254) coded Trump's
arrive.

## Decisions

- **A vendored, hand-curated correction list, keyed by `SUB_ID`** (`fec/ie_candidate_corrections.csv`:
  `sub_id, committee_id, pas2_candidate_id, candidate_id, source`, the source citing the filing,
  line and filed name). Silver names the listed candidate in place of `CAND_ID` while `CAND_ID`
  is still `pas2_candidate_id`. If FEC recodes the row, or an amendment replaces it, the
  correction stops applying rather than overriding a newer coding. The alias and handoff rules then
  apply to the corrected id as to any. A silver check fails the build if a correction that applies
  names no candidate of the cycle.
- **Rejected: taking the candidate from the 24/48-hour file** (the ticket's "widespread" branch).
  The count is not widespread, and that file is a different report: it disagrees with `pas2` on
  2,713 rows, mostly over the same person's two ids, and its amounts are estimates.
- **Rejected: reading the filings in the pipeline.** It would fix every cycle at once, but it
  means a new 1 GB-a-cycle source and an `SE`/`F57` parser, for 0.08% of 2024's dollars.
- **Not measured:** cycles before 2024. The list holds 2024's rows only.
