# House filings `cn` files under the old map's district: 2002, 2012 and 2022 against FEC's election results

Measured for [NEU-2293](https://linear.app/neuroticsasquatch/issue/NEU-2293) (milestone M4
Backfill and independent expenditures). NEU-2060's backfill found 2012's NY-11 holding only a
$0 Green, because `cn` files Michael Grimm (`H0NY13074`, the incumbent re-elected there) and
Mark Murphy (`H2NY13088`) under NY-13, the old Staten Island number, and CA-38 missing Linda
Sánchez (`H2CA39078`), who won it, because `cn` files her under CA-39. This document finds a
source for the district each House candidate ran in, counts the filings where `cn` disagrees
in the first cycle on each of the last three maps, and fixes the correction NEU-2293 ships:
`src/fundlens/fec/seats/house_districts.csv`. [NEU-2294](https://linear.app/neuroticsasquatch/issue/NEU-2294)
extends it to 1982 and 1992, the first cycles on the two maps before, whose results are PDF only:
see [1982 and 1992](#1982-and-1992).

| What | Value |
| --- | --- |
| Run | 2026-11-14, 03:10–03:30 UTC, in the local `app` container (`uv run --no-project --with xlrd --with openpyxl`, xlrd 2.0.2, openpyxl 3.1.5) |
| Code | `main` at `c8bec5f865b96da29008a15fd84b9f214df16ba7` |
| `2002fedresults.xls` | `https://www.fec.gov/documents/1620/2002fedresults.xls`, sheet `2002 House & Senate Results`, SHA-256 `517ce032aaed3f38…` |
| `2012congresults.xls` | `https://www.fec.gov/documents/1682/2012congresults.xls`, sheet `2012 US House & Senate Results`, SHA-256 `fe5e089dfd9c456f…` |
| `federalelections2022.xlsx` | `https://www.fec.gov/documents/5676/federalelections2022.xlsx`, sheet `8. US House Results by State`, SHA-256 `cdb258ea23803e50…` |
| `cn` | `https://www.fec.gov/files/bulk-downloads/<cycle>/cn<yy>.zip` for 2002, 2012, 2022, downloaded 2026-11-14T03:13Z (SHA-256 `0a7a253b…`, `53a07683…`, `0de15007…`) |
| `weball` | `…/<cycle>/weball<yy>.zip`, FEC's candidate summary, for each filing's total receipts (`TTL_RECEIPTS`), downloaded 2026-11-14T03:15Z (`4a6f581b…`, `d6668d32…`, `5aa60dd4…`) |

## Headline

- **FEC's per-cycle candidate history, FEC's elections endpoint and DIME all carry `cn`'s stale
  district.** `/v1/candidate/H0NY13074/history/2012/` gives Grimm district `13`, and Murphy `13`
  and Sánchez `39` the same way; `/v1/elections/?cycle=2012&office=house&state=NY&district=11`
  returns no candidate. DIME 4.0's `dime_recipients_1979_2024.csv` has `2012_NY_13` for Grimm and
  `2012_CA_39` for Sánchez. Each takes the district from the candidate's statement of candidacy,
  which they never amended, so the source the ticket proposed would have changed nothing.
- **FEC's election results list each candidate under the district they ran in, with their FEC
  id.** Grimm and Murphy are NY-11 (rows 2911 and 2914 of `2012congresults.xls`), Sánchez CA-38
  (row 485). They are spreadsheets for 2002, 2012 and 2022. 1982's and 1992's
  (`federalelections82.pdf`, `federalelections92.pdf`) are PDF only, and are measured under
  [1982 and 1992](#1982-and-1992): 3 filings change district in 1992, none in 1982.
- **68 filings change district: 10 in 2002, 11 in 2012, 47 in 2022.** By FEC's total receipts
  they hold $476,509, $5,969,717 and $24,917,356, which moves from the race `cn` names to the one
  they ran in (Q2).
- **The results' ids are not all right, so a row corrects a filing only after name checks.** The
  2022 file swaps the two Maloneys' ids (Carolyn B., NY-12, under Sean Patrick's `H2NY22139`, and
  him, NY-17, under hers), gives retiring Mike Doyle's id to the Republican Mike Doyle of PA-12
  (`H2PA12070` in `cn`), and Melissa Melendez's (`H2CA41140`, CA-41) to Rudy Melendez of CA-29.
  `cn` has all four right. A row is used only when its surname is in the filing's `cn` name, a
  given name's initial matches, and no other standing filing with that surname is already in the
  district the results name (Q1). 29 rows are turned down: 17 the results list under two
  districts, and 12 ($11,334,623) on the name checks, $11,117,801 of that the Maloneys' and
  Doyle's.
- **The most money moved is the ticket's own cases and a few like them.** In 2012, Grimm
  ($2.26M), Bauer (SC-00 to SC-07, $1.19M), Sánchez ($1.05M), Murphy ($0.93M); in 2022, Marcus
  Flowers (GA-13 to GA-14, $16.97M), Schweikert (AZ-06 to AZ-01, $2.02M), Walberg (MI-07 to MI-05,
  $1.52M) and McClain (MI-10 to MI-09, $1.27M).

## Method

For each of 2002, 2012 and 2022:

1. Read the results sheet: every row whose FEC id starts `H` and whose district is one or two
   digits, or `NN - FULL TERM` (a regular election held beside a special for the same seat).
   `NN - UNEXPIRED TERM` rows are specials, held on the old map, and are skipped. State and id
   are stripped, including the non-breaking spaces of 2002's state column and 2022's ids.
2. Read the cycle's `cn` and keep the House filings that stand in the cycle under
   `transform.seats.stands`: the cycle's year or the odd year before it, or a House incumbent's
   filing for the next election (NEU-2283, NEU-2287).
3. For each standing filing the results name, compare the results' (state, district) with
   `cn`'s, padded to two digits. Where they differ, decide by Q1's checks. The script is under
   [Reproducing](#reproducing).

## Q1. Which results rows correct a filing

A row whose district differs from `cn`'s corrects the filing when all of these hold:

- **The results list the id under one district only.** 17 ids appear under two (15 in 2022, 2 in
  2002; why was not checked). For 16 of them `cn`'s district is one of the two (Wasserman Schultz:
  `cn` FL-25, results FL-25 and FL-26), and for Thomas Bookwalter (`H2IN04168`, `cn` IN-04,
  results IN-06 and IN-07) neither is. All 17 keep `cn`'s district.
- **The state is the same.** No row failed this.
- **The results' surname, accents folded, is in the `cn` name.** This turns down Gregg Mele
  (`H2NJ06210`), whose id the 2022 file gives to Malinowski in NJ-07. Without folding, it turned
  down Sánchez, Gómez and Sánchez Hernandez, so the script folds them.
- **A given name's initial matches one of the `cn` filing's**, honorifics aside, since a candidate
  may go by a middle name ("Lacy" for EUGENE LACY WATSON, "Rene" for JESUS RENE LOPEZ). This catches
  a results row that carries a namesake's id: the Maloneys, Melissa Melendez (results CA-29, where
  Rudy Melendez ran), Kina Collins (IL-01, Jacqueline Collins), Bradley Martin (IL-13, Terry
  Martin), Lindsey Williams (NY-22, Brandon Williams), Tyler Smith (TX-26, Isaac Smith), Jessica
  Anderson (VA-07, Derrick Anderson) and Jorge Sánchez Hernandez (CA-38, Linda Sánchez). Comparing
  the first initial alone also turned down Watson and Lopez, so any initial counts. Melendez got
  through the surname check alone and was found in review; the initial check now runs on every
  cycle, and turns down no row of 2002 or 2012.
- **No other standing filing with that surname is already in the results' district.** This
  catches the namesakes who share an initial: Mike Doyle (results PA-12, the Republican Michael
  Doyle `H2PA12070`), and Robert Benjamin Clark III (`H2NC04150`, `cn` NC-04, results NC-09), Ben
  Clark's first registration, his NC-09 run being `H2NC09225` in `cn`.

Every row Q1 turns down keeps `cn`'s district: the table below lists them.

## Q2. The filings that change district

Receipts are FEC's `TTL_RECEIPTS` for the filing in `weball`, the money that moves with it. Filings
with none still move: a candidate on the ballot belongs to the race they ran in.

| Cycle | Filings corrected | With receipts | Receipts | Turned down |
| --- | ---: | ---: | ---: | ---: |
| 2002 | 10 | 5 | $476,509 | 2 |
| 2012 | 11 | 5 | $5,969,717 | 0 |
| 2022 | 47 | 36 | $24,917,356 | 27 |
| All | 68 | 46 | $31,363,582 | 29 |

### 2002

| Candidate | Id | `cn` | Results | Row | Receipts |
| --- | --- | --- | --- | ---: | ---: |
| MASS, MICHAEL | `H2OK03065` | OK-03 | OK-02 | 2766 | $251,690 |
| FINLEY, JOSEPH P | `H2NY05068` | NY-05 | NY-02 | 2298 | $162,305 |
| STAMPLEY,NATHANIEL J | `H0WI05089` | WI-00 | WI-04 | 3764 | $28,105 |
| LEFEMINE, STEVE C | `H2SC02117` | SC-02 | SC-05 | 3085 | $25,083 |
| MCPEEK, CHARLES CURTIS SR | `H2MD06096` | MD-06 | MD-07 | 1515 | $9,326 |
| KOPROWSKI, GENE | `H2IL00051` | IL-00 | IL-05 | 1080 | $0 |
| MELTON, JEFF | `H2IN00018` | IN-00 | IN-09 | 1240 | $0 |
| DEPRIMA, JANEEN | `H2NY03113` | NY-02 | NY-03 | 2312 | $0 |
| BIGELOW, CHRIS | `H2OR04053` | OR-05 | OR-04 | 2844 | $0 |
| CYRUS, MIKE | `H4CA32087` | CA-32 | CA-35 | 514 | $0 |

### 2012

| Candidate | Id | `cn` | Results | Row | Receipts |
| --- | --- | --- | --- | ---: | ---: |
| GRIMM, MICHAEL | `H0NY13074` | NY-13 | NY-11 | 2911 | $2,263,994 |
| BAUER, ANDRE | `H2SC00020` | SC-00 | SC-07 | 3865 | $1,188,138 |
| SANCHEZ, LINDA | `H2CA39078` | CA-39 | CA-38 | 485 | $1,048,195 |
| MURPHY, MARK | `H2NY13088` | NY-13 | NY-11 | 2914 | $928,666 |
| WIELAND, RICHARD E | `H2CT00033` | CT-00 | CT-04 | 721 | $540,725 |
| BATCHER, SCOTT | `H0IA03170` | IA-02 | IA-03 | 1511 | $0 |
| PROWELL, ANTHONY GENE | `H2AZ08045` | AZ-01 | AZ-02 | 103 | $0 |
| MANOLAKIS, CHARLIE | `H2AZ08128` | AZ-08 | AZ-02 | 98 | $0 |
| GRADY, ZACH | `H2TX13109` | TX-13 | TX-14 | 4156 | $0 |
| ARENTZ, ERIC G. JR. | `H2WA06152` | WA-07 | WA-06 | 4688 | $0 |
| DEWITT, REBECCA | `H8AZ04116` | AZ-04 | AZ-07 | 151 | $0 |

### 2022

| Candidate | Id | `cn` | Results | Row | Receipts |
| --- | --- | --- | --- | ---: | ---: |
| FLOWERS, MARCUS | `H2GA14044` | GA-13 | GA-14 | 1138 | $16,972,738 |
| SCHWEIKERT, DAVID S. | `H4AZ06045` | AZ-06 | AZ-01 | 89 | $2,018,409 |
| WALBERG, TIMOTHY L REP | `H4MI07103` | MI-07 | MI-05 | 1887 | $1,520,615 |
| MCCLAIN, LISA | `H0MI10287` | MI-10 | MI-09 | 1925 | $1,269,568 |
| MATHYS, CHRIS | `H2CA21183` | CA-21 | CA-22 | 369 | $384,662 |
| POZZOLO, LUIS B | `H2AZ03152` | AZ-03 | AZ-07 | 157 | $268,102 |
| FAULKNER, WILLIAM | `H2NY16099` | NY-16 | NY-17 | 2726 | $237,886 |
| GARCIA, ERIC | `H0CA22110` | CA-22 | CA-21 | 364 | $219,071 |
| MEDEIROS, ADAM THOMAS MR | `H2CA21225` | CA-21 | CA-22 | 370 | $204,214 |
| HOLDEN, STEVEN WESLEY SR. | `H2NY24127` | NY-21 | NY-24 | 2826 | $184,512 |
| MOORE FOR AZ, JOHN W | `H2AZ01347` | AZ-01 | AZ-02 | 103 | $181,612 |
| DISANTO, DELINA | `H8AZ04165` | AZ-06 | AZ-01 | 95 | $177,851 |
| LOPEZ, JESUS RENE JR. | `H2AZ09167` | AZ-09 | AZ-04 | 123 | $177,180 |
| SMITH, AJA | `H8CA41170` | CA-41 | CA-39 | 490 | $163,142 |
| BROOKS, LINDA SUSAN MS. | `H2FL02140` | FL-02 | FL-03 | 760 | $131,434 |
| JEFFERSON, JRMAR | `H2TX01146` | TX-30 | TX-01 | 3652 | $128,131 |
| YATES, ANDY | `H2AZ01370` | AZ-01 | AZ-02 | 102 | $114,706 |
| GILES, DAVID VICTOR | `H6AZ09010` | AZ-09 | AZ-04 | 122 | $83,800 |
| BISH, CHRISTINE | `H0CA06170` | CA-00 | CA-06 | 250 | $83,696 |
| SCHULZ, JONAH | `H2OH16069` | OH-13 | OH-07 | 3070 | $74,823 |
| BURTON, DANIEL LEROY JR | `H2PA00034` | PA-00 | PA-04 | 3322 | $55,995 |
| LUEVANOS, RUTH | `H2CA25200` | CA-25 | CA-27 | 403 | $55,620 |
| MAJOK, CHOL-AWAN A | `H2NY24168` | NY-24 | NY-22 | 2803 | $45,718 |
| GADDIS, CHARLIE | `H2OH13249` | OH-13 | OH-07 | 3071 | $28,759 |
| AQUINO, DARREN DIONE MR. | `H0FL19163` | FL-25 | FL-26 | 980 | $26,369 |
| SOUTHWORTH-BECKWITH, MAXIMILLIAN | `H2NC07153` | NC-03 | NC-07 | 2919 | $18,237 |
| GRIFFIN, LANCE ALAN | `H2MD03200` | MD-03 | MD-02 | 1679 | $17,220 |
| FREE, LUCRETIA | `H2AZ02394` | AZ-02 | AZ-06 | 144 | $16,697 |
| GUTIERREZ, REX DALE ALEXANDER | `H2CA31158` | CA-31 | CA-33 | 449 | $15,840 |
| SABATUCCI, DANTE | `H2OH07209` | OH-07 | OH-13 | 3128 | $15,551 |
| WATTERS, ANDREW G. | `H2CA14154` | CA-14 | CA-15 | 321 | $10,000 |
| SHELBY, DOC MR | `H2TX04116` | TX-04 | TX-03 | 3675 | $8,481 |
| HOWARD, EUGENE | `H2TX22159` | TX-22 | TX-14 | 3769 | $3,532 |
| GOMEZ, BLANCA | `H0CA08226` | CA-08 | CA-23 | 375 | $1,389 |
| WOODARD, JEFF | `H2PA18234` | PA-18 | PA-12 | 3400 | $1,010 |
| MARTIN, BRANDON RAY | `H8AZ02201` | AZ-02 | AZ-06 | 141 | $785 |
| GIBLIN, SCOTT | `H0CA05107` | CA-05 | CA-04 | 232 | $0 |
| JONES, PAUL IRVING REVEREND | `H0CA38140` | CA-38 | CA-44 | 528 | $0 |
| MILTON, CHRISTOPHER | `H0CO03173` | CO-06 | CO-07 | 652 | $0 |
| NADELL, BRIAN | `H0NV03207` | NV-04 | NV-02 | 2296 | $0 |
| WATSON, EUGENE LACY | `H0WV03144` | WV-03 | WV-01 | 4315 | $0 |
| DEL CASTELLO, EVE | `H2CA12224` | CA-12 | CA-11 | 288 | $0 |
| GIBSON, JAMES FRANCIS | `H2CA36454` | CA-36 | CA-25 | 387 | $0 |
| KELLEY, JOE | `H2MD02301` | MD-02 | MD-03 | 1689 | $0 |
| WALKING CHILD, CHARLES A | `H2MT01102` | MT-01 | MT-02 | 2229 | $0 |
| JONES, ERIC SCOTT | `H2OH13215` | OH-13 | OH-06 | 3064 | $0 |
| DECK, BETH A. MRS. | `H2OH19204` | OH-19 | OH-09 | 3093 | $0 |

### Turned down

| Cycle | Candidate | Id | `cn` | Results row | Receipts | Why |
| --- | --- | --- | --- | ---: | ---: | --- |
| 2002 | PANKAU, MARTIN | `H2IL04137` | IL-04 | 1065 | $0 | results list it under two districts IL-04 IL-07 |
| 2002 | HOWARD, HARVEY | `H2TN04217` | TN-04 | 3180 | $0 | results list it under two districts TN-04 TN-06 |
| 2022 | SPALDING, CARLA A | `H0FL23090` | FL-25 | 974 | $2,002,922 | results list it under two districts FL-25 FL-27 |
| 2022 | COLLINS, KINA ISIS | `H0IL07167` | IL-07 | 1206 | $3,548 | results name 'Jacqueline "Jacqui"' 'Collins' is not this filing's |
| 2022 | SANCHEZ HERNANDEZ, JORGE | `H2CA22157` | CA-22 | 484 | $0 | results name 'Linda T.' 'Sánchez' is not this filing's |
| 2022 | CALVERT, KEN | `H2CA37023` | CA-41 | 504 | $3,728,273 | results list it under two districts CA-41 CA-42 |
| 2022 | MELENDEZ, MELISSA | `H2CA41140` | CA-41 | 418 | $0 | results name 'Rudy' 'Melendez' is not this filing's |
| 2022 | STURGILL, SCOTT | `H2FL07214` | FL-07 | 791 | $321,786 | results list it under two districts FL-07 FL-08 |
| 2022 | BROWN, GAVIN | `H2FL15225` | FL-15 | 819 | $26,646 | results list it under two districts FL-10 FL-15 |
| 2022 | PALMER, ROBERT A | `H2IL01430` | IL-01 | 1214 | $0 | results list it under two districts IL-01 IL-13 |
| 2022 | CONFORTI, NIKI | `H2IL06090` | IL-06 | 1270 | $75,519 | results list it under two districts IL-06 IL-07 |
| 2022 | KOPPIE, CHAD | `H2IL08203` | IL-08 | 1282 | $11,417 | results list it under two districts IL-07 IL-08 |
| 2022 | MARTIN, BRADLEY | `H2IL09136` | IL-09 | 1335 | $0 | results name 'Terry' 'Martin' is not this filing's |
| 2022 | FOSTER, NANCY | `H2IL13211` | IL-13 | 1326 | $0 | results list it under two districts IL-12 IL-13 |
| 2022 | BOOKWALTER, THOMAS CHARLES | `H2IN04168` | IN-04 | 1434 | $8,480 | results list it under two districts IN-06 IN-07 |
| 2022 | NEHME, HASSAN H | `H2MI13196` | MI-12 | 1963 | $25,000 | results list it under two districts MI-12 MI-13 |
| 2022 | SMITH, WESLEY GILMAN | `H2MO02177` | MO-02 | 2120 | $0 | results list it under two districts MO-02 MO-08 |
| 2022 | CLARK, ROBERT BENJAMIN III | `H2NC04150` | NC-04 | 2937 | $171,780 | NC-09 already has H2NC09225 of the same surname in cn |
| 2022 | MELE, GREGG | `H2NJ06210` | NJ-06 | 2459 | $0 | results name 'Malinowski' is not this filing's |
| 2022 | WILLIAMS, LINDSEY DEMART | `H2NY13120` | NY-13 | 2794 | $41,494 | results name 'Brandon M.' 'Williams' is not this filing's |
| 2022 | MALONEY, CAROLYN B. | `H2NY14037` | NY-12 | 2736 | $4,835,087 | results name 'Sean Patrick' 'Maloney' is not this filing's |
| 2022 | MALONEY, SEAN PATRICK | `H2NY22139` | NY-17 | 2673 | $6,079,999 | results name 'Carolyn B.' 'Maloney' is not this filing's |
| 2022 | MAGAZINER, SETH | `H2RI02184` | RI-02 | 3468 | $3,904,869 | results list it under two districts RI-01 RI-02 |
| 2022 | SMITH, TYLER RAY | `H2TX25301` | TX-25 | 3878 | $0 | results name 'Isaac' 'Smith' is not this filing's |
| 2022 | HILL, VONCIEL JONES | `H2TX30152` | TX-30 | 3854 | $36,438 | results list it under two districts TX-23 TX-30 |
| 2022 | CISNEROS, LAURA E. DR. | `H2TX34188` | TX-34 | 3897 | $204,861 | results list it under two districts TX-28 TX-34 |
| 2022 | ANDERSON, JESSICA LYNNE | `H2VA01108` | VA-01 | 4150 | $0 | results name 'Derrick M.' 'Anderson' is not this filing's |
| 2022 | WASSERMAN SCHULTZ, DEBBIE | `H4FL20023` | FL-25 | 971 | $2,087,129 | results list it under two districts FL-25 FL-26 |
| 2022 | DOYLE, MICHAEL | `H4PA18131` | PA-18 | 3404 | $202,715 | PA-12 already has H2PA12070 of the same surname in cn |

## 1982 and 1992

Measured for [NEU-2294](https://linear.app/neuroticsasquatch/issue/NEU-2294).

| What | Value |
| --- | --- |
| Run | 2026-11-14, 19:40–20:30 UTC, in the local `app` container (`uv run --no-project --with pdfplumber`, pdfplumber 0.11.10, pdfminer.six 20260107) |
| Code | `main` at `a22a808e2c51d75a666fb8bc03a2bf093f0ec592` |
| `federalelections82.pdf` | `https://www.fec.gov/documents/1547/federalelections82.pdf`, 111 pages, House on pages 13–111, SHA-256 `8ec63985f7d05ef1…` |
| `federalelections92.pdf` | `https://www.fec.gov/documents/1552/federalelections92.pdf`, 126 pages, House on pages 54–102, SHA-256 `4fb5f46d47043dbf…` |
| `cn` | `…/1982/cn82.zip`, `…/1992/cn92.zip`, downloaded 2026-11-14T19:43Z (SHA-256 `c29c0270…`, `95624748…`) |
| `weball` | `…/1982/weball82.zip`, `…/1992/weball92.zip`, downloaded 2026-11-14T19:43Z (`e7b0dd6e…`, `9cc20240…`) |

### Headline

- **Both PDFs are scans with an OCR text layer, and neither prints FEC ids.** 1982's columns
  are last name, first name and initial, party, votes and percent; 1992's are `Last, First`,
  party, votes and percent. A row can be matched to a filing only by name, through OCR that
  reads 1982's F as P and C as E (`Perraro Geraldine`, `Demoeratie`) and 1992's W as V or `~`
  (`VASHINGTON`, `~rite-In`).
- **1982's `cn` agrees with its results throughout: no filing changes district.** Of 1,976 standing
  House filings, 922 ($137.00M of receipts) are found in the results, every one in the district
  `cn` gives.
- **3 of 1992's change district, none with receipts:** Kenneth Hemmerle (`H2FL00110`, `cn`
  FL-00, a write-in in FL-19), Robert Stockhausen (`H2MO03084`, MO-02 to MO-03, Libertarian) and
  Nana LaLuz (`H2NY17089`, NY-08 to NY-17, Natural Law). The other 1,231 found ($300.25M) are in
  `cn`'s district.
- **The ticket's races with two incumbent filings or more are member-against-member races and
  members who did not run, not stale districts.** There are 17 in 1982 by this script's standing
  rule, `seats.stands` (the ticket counted 18; the difference was not traced), and 18 in 1992.
  In each, the results place at least one of the incumbents in the race. Each of the others is
  placed there too, as a pairing the new map forced (1982: Frank and
  Heckler, MA-04; Bailey and Skelton, MO-04. 1992: Nussle and Nagle, IA-02; Huckaby and McCrery,
  LA-05; Holloway and Baker, LA-06; McMillen and Gilchrest, MD-01), or is in no district of the
  results at all: retired, beaten in the primary, or a row the OCR garbled (Rousselot, CA-30,
  reads `Rousse1ot`). None of the latter is a close name in another district of the results.

### Method

For each cycle:

1. Read the House pages' text with pdfplumber. A line is a state header when it is capitals
   without digits and close to a state's name (difflib ratio 0.6; two headers past that are
   listed by hand: 1982's `MEW BAMPSBillB` and 1992's `!OVA`). A district header is one whose
   text before its first colon or digit is capitals and close to `DISTRICT` (ratio 0.6:
   `DIR'f'IU CT: 7`, `D1STRICT: 2`, `DIST1UCT 4`). The lines up to the next header are its
   block. `- Unexpired Term` blocks are specials, held on the old map, and skipped, as for 2002.
2. Number each block from its header where the number follows the block before, and as the
   block before plus one where the OCR misreads it (1982's CA-07 reads `DISTRICT: 1`). Every
   state with two seats or more then has one block per seat, except 1982's LA-03 and LA-04:
   Louisiana prints no general-election row for a district its primary decided unopposed. A
   state with one seat, or a territory, has only district `00`, so its 38 (1982) and 65 (1992)
   filings are not compared. `cn` files every one of them under `00`, among them South Dakota's
   in 1982 and Montana's in 1992, the two states cut to one seat.
3. Read the cycle's `cn` and keep the House filings that stand, as for 2002 (step 2 above).
4. Look for each filing in every block of its state. It is in a block when the block has a line
   holding its surname, folded for the OCR's confusions on both sides, as a word or a run of up
   to three words (`La Rocco`, `Won Pat`), and one of its given names, honorifics aside, on that
   line. A line without a vote count, which the OCR split from the row beside it, counts with
   that row. A given name matches when it is the same word, a nickname of it (Bill, William; the
   list is in the script) or one the prefix of the other, three letters at least (Dan, Daniel).
   This is stricter than Q1's initial, on evidence. A spreadsheet row has a given-name column;
   a PDF line does not, so an initial check matches whatever word stands beside the surname.
   Run with Q1's initial (of the word just after the surname, or any given name as above), the
   script corrects five more filings, and all five are wrong. 1982's Robert Curtis (`H2CA43070`,
   CA-43) matched `Cross Curtis R. "Sam"` in CA-37, Curtis being Cross's given name; 1992's John
   Charles Williams (`H2CA42080`) matched James E. Williams; Harley Ross (`H2CA43302`) matched
   `Crain, Ross`; Roosevelt Thomas (`H2IL01034`) matched `Ewing, Thomas Republican`, on the R of
   the party; and L.D. Knox (`H8LA05057`) matched `Irvin, Wilma Knox`. It also finds 41 more of
   1982's filings, and 18 more of 1992's, in their own district: the stricter rule costs recall,
   which the next section checks.
5. A filing found only in a district other than `cn`'s is corrected under Q1's remaining checks:
   it is found in one district only, and no other standing filing with its surname is in that
   district. 1992's one row turned down is Terrance James Brown (`H2CA01086`, `cn` CA-01), whose
   given name matched a write-in, James P. Brown, Sr., in CA-38, where Dennis Brown
   (`H2CA38054`) stands.

### Recall

A filing the script does not find keeps `cn`'s district. That is right for a candidate who
was not on the general-election ballot, and wrong only for one who ran elsewhere under a name
the OCR garbled. Two checks look for those:

- **Unmatched results rows near a filing elsewhere.** Of the lines with a vote count, 569 of
  1,491 in 1982 and 288 of 1,521 in 1992 match no filing: candidates who never registered with
  the FEC, the extra party lines of New York's fusion ballots, and OCR misses. For each, the
  script lists the state's unfound filings whose surname is close to the row's first word
  (ratio 0.75) and whose `cn` district is another. That gives 5 pairs in 1982 and 15 in 1992,
  and all 20 are different people: Richardson and Richards (CA-03, CA-36), Dave and John Charles
  Williams (CA-10, CA-42), Traylor and Taylor (TX-01, TX-09), and so on.
- **District blocks no filing is found in.** Nine in 1982, each because the OCR garbled the
  winner (AL-07 `Sbelby Riebard`, KS-01 `lloberts Pat`, MA-11 `Doonelly`, MI-05 `Sawyer
  881'0ld`, NY-07 `Jlosentbal`, NY-10 `Scluner Cbarles`, NC-10 `Broyhill .lamesT.`, TX-01 `aa n
  Sam B.`, TX-19 `Ranee Kent`). Checked by hand, `cn` has each incumbent in that district:
  Shelby `H8AL07014`, Roberts `H0KS01016`, Donnelly `H8MA11018`, Sawyer `H6MI05102`, Rosenthal
  `H6NY08022`, Schumer `H0NY16010`, Broyhill `H6NC10018`, Hall `H6TX01022`, Hance `H8TX19020`.
  One in 1992, FL-21, where the only line with digits is a footnote: Lincoln Diaz-Balart ran
  unopposed, his row prints no votes, and he is found there.

The filings not found hold $56.60M of 1982's receipts (1,016 filings) and $103.35M of 1992's
(1,353), most of it primary losers' money. The general-election results cannot say where a
primary loser ran. That is a limit 2002's spreadsheets do not share, since they carry primary
votes by id.

### The filings that change district

| Cycle | Candidate | Id | `cn` | Results | PDF page | Results line | Receipts |
| --- | --- | --- | --- | --- | ---: | --- | ---: |
| 1992 | HEMMERLE, KENNETH V SR | `H2FL00110` | FL-00 | FL-19 | 65 | `Hemmerle, Kenneth v,, Sr. Write-In 4 .00` | $0 |
| 1992 | STOCKHAUSEN, ROBERT | `H2MO03084` | MO-02 | MO-03 | 78 | `Stockhausen, Robert Libertarian 7,828 2.88` | $0 |
| 1992 | LALUZ, NANA | `H2NY17089` | NY-08 | NY-17 | 85 | `LaLuz, Nana Natural Law 1,592 1.30` | $0 |

`house_districts.csv` cites them as `federalelections92.pdf page <n>`, the PDF's page (printed
pages −60−, −73− and −80−).

## Not fixed here

- **Results candidates whose `cn` filing stands in no race at all.** 57 House ids in 2002's results
  ($104,788) and 8 in 2022's ($156,022) are in `cn` with an election year that does not stand in
  the cycle: Victor Good (`H0CO03058`, $57,554) is `cn` 2000 in 2002's file, Max Rose
  (`H8NY11113`) 2020 in 2022's. This is a stale election year, not a stale district, and they are in
  no race before or after this ticket. 12 ids in 2002's results, 19 in 2012's and 44 in 2022's are
  in no `cn` row at all, mostly mistyped (`H8HY02031`).
- **Ben Clark's duplicate registration** (`H2NC04150`, NC-04, beside `H2NC09225`, NC-09) stays in
  NC-04 (Q1).

## Reproducing

Download the files of the table at the top into `/tmp/d/` in the `app` container (the 2022 results
as `fe2022.xlsx`), then `uv run --no-project --with xlrd --with openpyxl python gen.py > rows.csv`.
Each row is a filing whose district the results give differently, with its verdict;
`house_districts.csv` is the `corrected` rows, `source` being the results file and row.

<details><summary><code>gen.py</code></summary>

```python
"""NEU-2293: House filings whose district in FEC's election results differs from cn's."""
import csv, io, re, sys, unicodedata, zipfile, collections
import xlrd, openpyxl

SRC = {
    2002: ("2002fedresults.xls", "2002 House & Senate Results", "FEC ID", "STATE", "DISTRICT", "LAST NAME", "FIRST NAME"),
    2012: ("2012congresults.xls", "2012 US House & Senate Results", "FEC ID#", "STATE ABBREVIATION", "D", "CANDIDATE NAME (Last)", "CANDIDATE NAME (First)"),
    2022: ("federalelections2022.xlsx", "8. US House Results by State", "FEC ID", "STATE ABBREVIATION", "DISTRICT", "CANDIDATE NAME (Last)", "CANDIDATE NAME (First)"),
}
LOCAL = {"2002fedresults.xls": "2002fedresults.xls", "2012congresults.xls": "2012congresults.xls", "federalelections2022.xlsx": "fe2022.xlsx"}

def sheet_rows(fname, sheet):
    path = "/tmp/d/" + LOCAL[fname]
    if path.endswith(".xls"):
        s = xlrd.open_workbook(path).sheet_by_name(sheet)
        for r in range(s.nrows):
            yield r + 1, s.row_values(r)
    else:
        for n, row in enumerate(openpyxl.load_workbook(path, read_only=True)[sheet].iter_rows(values_only=True), start=1):
            yield n, list(row)

def text(v):
    if v is None: return ""
    if isinstance(v, float): v = int(v)
    return str(v).replace("\xa0", " ").strip()

def letters(s): return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFKD", s).upper())

# A given name's initials, honorifics aside: a candidate may go by a middle name ("Lacy" for
# EUGENE LACY WATSON).
def initials(s): return {w[0] for w in (letters(t) for t in s.split()) if w and w not in {"MR", "MRS", "MS", "DR", "REV", "JR", "SR"}}

def results(cycle):
    fname, sheet, idc, stc, dc, lnc, fnc = SRC[cycle]
    it = sheet_rows(fname, sheet)
    _, header = next(it)
    at = {text(h): i for i, h in enumerate(header)}
    for n, row in it:
        fid, st, d, last, given = (text(row[at[c]]) for c in (idc, stc, dc, lnc, fnc))
        full = re.fullmatch(r"(\d{1,2}) ?- ?full term", d, re.I)
        if full: d = full.group(1)
        if fid.startswith("H") and re.fullmatch(r"\d{1,2}", d):
            yield n, fid, st, d.zfill(2), last, given

def bulk(name, cycle):
    z = zipfile.ZipFile(f"/tmp/d/{name}{str(cycle)[2:]}.zip")
    return [r for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("latin-1")), delimiter="|", quoting=csv.QUOTE_NONE) if r]

def stands(cycle, year, office, ici):
    year = year.strip()
    return year in {str(cycle - 1), str(cycle)} or (office == "H" and year in {str(cycle + 1), str(cycle + 2)} and ici == "I")

out = csv.writer(sys.stdout, lineterminator="\n")
out.writerow(["cycle", "candidate_id", "name", "cn_district", "district", "results_row", "receipts", "verdict"])
for cycle in SRC:
    cn = {}
    for r in bulk("cn", cycle):
        cn[r[0]] = dict(name=r[1], year=r[3], state=r[4], office=r[5], district=r[6].strip().zfill(2), ici=r[7])
    receipts = {r[0]: float(r[5] or 0) for r in bulk("weball", cycle)}
    standing = {cid: f for cid, f in cn.items() if f["office"] == "H" and stands(cycle, f["year"], f["office"], f["ici"])}
    seats, first = collections.defaultdict(set), {}
    for n, fid, st, d, last, given in results(cycle):
        seats[fid].add((st, d)); first.setdefault(fid, (n, last, given))
    for fid in sorted(seats):
        f = standing.get(fid)
        if f is None: continue
        n, last, given = first[fid]
        if len(seats[fid]) > 1:
            verdict = "rejected: results list it under two districts " + " ".join(sorted(f"{s}-{d}" for s, d in seats[fid]))
            out.writerow([cycle, fid, f["name"], f"{f['state']}-{f['district']}", "", n, receipts.get(fid, 0), verdict]); continue
        [(st, d)] = seats[fid]
        if (st, d) == (f["state"], f["district"]): continue
        if st != f["state"]:
            verdict = "rejected: results state differs"
        elif letters(last) not in letters(f["name"]):
            verdict = f"rejected: results name {last!r} is not this filing's"
        elif given and not initials(given) & initials(f["name"].partition(",")[2]):
            verdict = f"rejected: results name {given!r} {last!r} is not this filing's"
        elif any(o["state"] == st and o["district"] == d and letters(last) in letters(o["name"]) for c, o in standing.items() if c != fid):
            twin = [c for c, o in standing.items() if c != fid and o["state"] == st and o["district"] == d and letters(last) in letters(o["name"])]
            verdict = f"rejected: {st}-{d} already has {','.join(twin)} of the same surname in cn"
        else:
            verdict = "corrected"
        out.writerow([cycle, fid, f["name"], f"{f['state']}-{f['district']}", f"{st}-{d}", n, receipts.get(fid, 0), verdict])
```

</details>

For 1982 and 1992, download the files of [their table](#1982-and-1992) into the same `/tmp/d/`
(the PDFs as `fe82.pdf` and `fe92.pdf`), then
`uv run --no-project --with pdfplumber python pdfgen.py > rows.csv 2> log.txt`. `rows.csv` has
the same columns, with the matched results line in place of the row number; `log.txt` has the
header repairs, the blocks missing, the recall checks' lists, the races with two incumbent filings
or more, and each cycle's counts.

<details><summary><code>pdfgen.py</code></summary>

```python
"""NEU-2294: 1982 and 1992 House filings whose district in FEC's PDF election results differs from cn's."""
import collections, csv, difflib, io, re, sys, unicodedata, zipfile

import pdfplumber

D = "/tmp/d/"
SEATS_DIR = "/app/src/fundlens/fec/seats/"
# The House pages of each PDF (1-based), and the letters its OCR confuses, folded alike on both
# sides of a name comparison.
SRC = {
    1982: ("federalelections82.pdf", "fe82.pdf", range(13, 112), str.maketrans("FCL", "PEI")),
    1992: ("federalelections92.pdf", "fe92.pdf", range(54, 103), str.maketrans("W", "V")),
}
STATES = {
    "AL": "ALABAMA", "AK": "ALASKA", "AS": "AMERICAN SAMOA", "AZ": "ARIZONA", "AR": "ARKANSAS",
    "CA": "CALIFORNIA", "CO": "COLORADO", "CT": "CONNECTICUT", "DE": "DELAWARE",
    "DC": "DISTRICT OF COLUMBIA", "FL": "FLORIDA", "GA": "GEORGIA", "GU": "GUAM", "HI": "HAWAII",
    "ID": "IDAHO", "IL": "ILLINOIS", "IN": "INDIANA", "IA": "IOWA", "KS": "KANSAS",
    "KY": "KENTUCKY", "LA": "LOUISIANA", "ME": "MAINE", "MD": "MARYLAND", "MA": "MASSACHUSETTS",
    "MI": "MICHIGAN", "MN": "MINNESOTA", "MS": "MISSISSIPPI", "MO": "MISSOURI", "MT": "MONTANA",
    "NE": "NEBRASKA", "NV": "NEVADA", "NH": "NEW HAMPSHIRE", "NJ": "NEW JERSEY",
    "NM": "NEW MEXICO", "NY": "NEW YORK", "NC": "NORTH CAROLINA", "ND": "NORTH DAKOTA",
    "OH": "OHIO", "OK": "OKLAHOMA", "OR": "OREGON", "PA": "PENNSYLVANIA", "PR": "PUERTO RICO",
    "RI": "RHODE ISLAND", "SC": "SOUTH CAROLINA", "SD": "SOUTH DAKOTA", "TN": "TENNESSEE",
    "TX": "TEXAS", "UT": "UTAH", "VT": "VERMONT", "VI": "VIRGIN ISLANDS", "VA": "VIRGINIA",
    "WA": "WASHINGTON", "WV": "WEST VIRGINIA", "WI": "WISCONSIN", "WY": "WYOMING",
}
# State headers the OCR mangles past a close match.
HEADER_OCR = {"MEW BAMPSBillB": "NH", "!OVA": "IA"}
HONORIFICS = {"MR", "MRS", "MS", "DR", "REV", "JR", "SR", "II", "III", "IV", "HON", "REP"}
# Names a candidate goes by that are not a prefix of the given name `cn` has.
NICKNAMES = {
    "BILL": {"WILLIAM"}, "BILLY": {"WILLIAM"}, "BOB": {"ROBERT"}, "BOBBY": {"ROBERT"},
    "JIM": {"JAMES"}, "JIMMY": {"JAMES"}, "JAY": {"JAMES"}, "DICK": {"RICHARD"},
    "RICK": {"RICHARD"}, "RICHIE": {"RICHARD"}, "JACK": {"JOHN"}, "CHUCK": {"CHARLES"},
    "MIKE": {"MICHAEL"}, "MAC": {"MICHAEL"}, "TOM": {"THOMAS"}, "TOMMY": {"THOMAS"},
    "TED": {"EDWARD", "THEODORE"}, "ED": {"EDWARD", "EDWIN"}, "TONY": {"ANTHONY"},
    "HANK": {"HENRY"}, "LARRY": {"LAWRENCE"}, "JERRY": {"GERALD", "JEROME"},
    "ANDY": {"ANDREW"}, "STEVE": {"STEPHEN", "STEVEN"}, "AL": {"ALFRED", "ALAN", "ALLAN", "ALLEN", "ALBERT", "ALMON"},
    "PEGGY": {"MARGARET"}, "BETTY": {"ELIZABETH"}, "BETH": {"ELIZABETH"}, "LIZ": {"ELIZABETH"},
    "NED": {"EDWARD"}, "SANDY": {"SANDRA"}, "MARCY": {"MARCIA"}, "NEIL": {"CORNELIUS"},
    "GENE": {"EUGENE"}, "CHET": {"CHESTER"}, "JAKE": {"JACOB", "JAMES"}, "DENNY": {"DENNIS"},
}


def letters(s: str) -> str:
    return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFKD", s).upper())


def words(s: str) -> list[str]:
    return [w for w in (letters(t) for t in re.split(r"[\s,.\-'\"()]+", s.replace("~", "W"))) if w]


def capitals(s: str) -> bool:
    caps = [c for c in s if c.isalpha()]
    return len(caps) >= 4 and sum(c.isupper() for c in caps) >= 0.6 * len(caps)


def state_of(line: str) -> str | None:
    """The state a header line names, or None: a header is capitals, no digits, close to a name."""
    text = re.sub(r"\(.*", "", line).strip(" .·•-")
    if text in HEADER_OCR:
        return HEADER_OCR[text]
    if not capitals(text) or any(c.isdigit() for c in text):
        return None
    key = letters(text).replace("V", "W")
    names = {letters(n).replace("V", "W"): st for st, n in STATES.items()}
    match = difflib.get_close_matches(key, list(names), n=1, cutoff=0.6)
    return names[match[0]] if match else None


def district_of(line: str) -> tuple[str, bool] | None:
    """(the number a district header prints, whether it is an unexpired term), or None. The OCR
    mangles the word (DIR'f'IU CT, D1STRICT, DISTRfcT), so it is matched loosely: the text before
    the first colon or digit, in capitals, close to DISTRICT."""
    # A 1 inside the word is an I (D1STRICT, DIST1UCT).
    line = re.sub(r"(?<=[A-Za-z'])1(?=[A-Za-z'])", "I", line)
    # And an l or I standing alone after it is a 1 (DISTRICT: l).
    line = re.sub(r"(?<=[:\s])[lI](?=\W*$)", "1", line)
    m = re.match(r"^\W*([^:\d]+?)\W*(\d.*|)$", line)
    if not m or not capitals(m.group(1)) or len(letters(m.group(1))) > 10:
        return None
    if difflib.SequenceMatcher(None, letters(m.group(1)), "DISTRICT").ratio() < 0.6:
        return None
    num = re.match(r"\d+", m.group(2))
    return (num.group() if num else ""), "UNEXPIRED" in line.upper()


def pages(cycle: int) -> list[str]:
    _, local, wanted, _ = SRC[cycle]
    with pdfplumber.open(D + local) as pdf:
        return [pdf.pages[n - 1].extract_text() or "" for n in wanted]


def blocks(cycle: int, seats: dict[str, int]) -> list[dict]:
    """Each district block of a state with two seats or more, in the PDF's order. It takes the
    number it prints where that follows the one before (Louisiana skips the districts its primary
    decided unopposed), and the one before plus one where the OCR misreads it."""
    state, out = None, []
    for text in pages(cycle):
        for raw in text.splitlines():
            line = raw.strip()
            header = district_of(line)
            if header and state:
                out.append(dict(state=state, header=line, printed=header[0], unexpired=header[1], lines=[]))
                continue
            st = state_of(line)
            if st:
                if st != state:
                    print(f"# {cycle} state {st} from {line!r}", file=sys.stderr)
                state = st
            elif out and line:
                out[-1]["lines"].append(line)
    previous: dict[str, int] = collections.Counter()
    kept = []
    for b in out:
        st = b["state"]
        if b["unexpired"] or seats.get(st, 0) < 2:
            continue
        printed = int(b["printed"]) if b["printed"] else 0
        number = printed if previous[st] < printed <= seats[st] else previous[st] + 1
        if number != printed:
            print(f"# {cycle} {st} header {b['header']!r} read as district {number}", file=sys.stderr)
        previous[st] = number
        b["district"] = f"{number:02d}"
        kept.append(b)
    for st, n in sorted(seats.items()):
        got = {b["district"] for b in kept if b["state"] == st}
        want = {f"{d:02d}" for d in range(1, n + 1)}
        if n >= 2 and got != want:
            print(f"# {cycle} {st}: missing {sorted(want - got)}, extra {sorted(got - want)}", file=sys.stderr)
    return kept


def house_seats(cycle: int) -> dict[str, int]:
    """Voting seats per state under the apportionment in force; one for each delegate up."""
    in_force: dict[str, tuple[int, int]] = {}
    for row in csv.DictReader(open(SEATS_DIR + "apportionment.csv")):
        st, n, first = row["state"], int(row["seats"]), int(row["first_cycle"])
        if first <= cycle and (st not in in_force or first > in_force[st][1]):
            in_force[st] = (n, first)
    seats = {st: n for st, (n, _) in in_force.items()}
    for row in csv.DictReader(open(SEATS_DIR + "delegates.csv")):
        if int(row["first_cycle"]) <= cycle and cycle % int(row["term_years"]) == 0:
            seats[row["state"]] = 1
    return seats


def bulk(name: str, cycle: int) -> list[list[str]]:
    z = zipfile.ZipFile(f"{D}{name}{str(cycle)[2:]}.zip")
    return [r for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("latin-1")), delimiter="|", quoting=csv.QUOTE_NONE) if r]


def stands(cycle: int, year: str, office: str, ici: str) -> bool:
    year = year.strip()
    return year in {str(cycle - 1), str(cycle)} or (office == "H" and year in {str(cycle + 1), str(cycle + 2)} and ici == "I")


def given_matches(fold, given: list[str], seen: list[str]) -> bool:
    """A given name of the filing's is a word near the results' surname: the same, a nickname
    of it, or one the prefix of the other (Dan, Daniel), three letters at least."""
    nick = {k.translate(fold): {v.translate(fold) for v in vs} for k, vs in NICKNAMES.items()}
    for g in given:
        for w in seen:
            if len(w) < 2 or len(g) < 2:
                continue
            if w == g or g in nick.get(w, ()) or w in nick.get(g, ()):
                return True
            if min(len(w), len(g)) >= 3 and (w.startswith(g) or g.startswith(w)):
                return True
    return False


def find(fold, surname: str, given: list[str], lines: list[str]) -> str | None:
    """The results line naming a filing in a district block: its surname a word, or a run of up
    to three, and a given name on that line or the line either side (the OCR splits rows)."""
    folded = [[w.translate(fold) for w in words(line)] for line in lines]
    # Only a fragment, a line without a vote count, is part of the row beside it.
    fragment = [not re.search(r"\d", line) for line in lines]
    for i, ws in enumerate(folded):
        for a in range(len(ws)):
            for b in range(a + 1, min(a + 3, len(ws)) + 1):
                if "".join(ws[a:b]) == surname:
                    near = ws[:a] + ws[b:]
                    for j in (i - 1, i + 1):
                        if 0 <= j < len(lines) and (fragment[j] or fragment[i]):
                            near += folded[j]
                    if given_matches(fold, given, near):
                        return lines[i]
    return None


def main() -> None:
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["cycle", "candidate_id", "name", "cn_district", "district", "results_line", "receipts", "verdict"])
    for cycle, (_, _, _, fold) in SRC.items():
        seats = house_seats(cycle)
        by_state = collections.defaultdict(list)
        for b in blocks(cycle, seats):
            by_state[b["state"]].append(b)
        cn = {r[0]: dict(name=r[1], year=r[3], state=r[4], office=r[5], district=r[6].strip().zfill(2), ici=r[7]) for r in bulk("cn", cycle)}
        receipts = {r[0]: float(r[5] or 0) for r in bulk("weball", cycle)}
        standing = {cid: f for cid, f in cn.items() if f["office"] == "H" and stands(cycle, f["year"], f["office"], f["ici"])}
        surname = {cid: "".join(words(f["name"].partition(",")[0])).translate(fold) for cid, f in standing.items()}
        tally = collections.Counter()
        matched: set = set()
        found: set = set()
        same: set = set()
        money = collections.Counter()
        for cid in sorted(standing):
            f = standing[cid]
            if seats.get(f["state"], 0) < 2:
                tally["one seat, cn not 00" if f["district"] != "00" else "one seat"] += 1
                continue
            given = [w.translate(fold) for w in words(f["name"].partition(",")[2]) if w not in HONORIFICS]
            hits: dict[str, str] = {}
            for b in by_state.get(f["state"], []):
                line = find(fold, surname[cid], given, b["lines"])
                if line:
                    hits.setdefault(b["district"], line)
                    matched.add((id(b), line))
                    found.add(cid)
            if not hits:
                tally["not in results"] += 1
                money["not in results"] += receipts.get(cid, 0)
                continue
            if f["district"] in hits:
                tally["same district"] += 1
                money["same district"] += receipts.get(cid, 0)
                same.add(cid)
                continue
            row = [cycle, cid, f["name"], f"{f['state']}-{f['district']}"]
            if len(hits) > 1:
                tally["two districts"] += 1
                out.writerow(row + ["", " | ".join(hits.values()), receipts.get(cid, 0), "rejected: results name it in two districts " + " ".join(f"{f['state']}-{d}" for d in sorted(hits))])
                continue
            [(d, line)] = hits.items()
            twin = [c for c, o in standing.items() if c != cid and o["state"] == f["state"] and o["district"] == d and surname[c] == surname[cid]]
            verdict = f"rejected: {f['state']}-{d} already has {','.join(twin)} of the same surname in cn" if twin else "corrected"
            tally[verdict.partition(":")[0]] += 1
            out.writerow(row + [f"{f['state']}-{d}", line, receipts.get(cid, 0), verdict])
        # Recall. A results row with a vote count that no filing matched may be a filing the OCR
        # garbled: compare its first word with the surname of every filing of the state matched
        # nowhere, and list those close to it (difflib ratio 0.75 or more) that `cn` files in
        # another district. A district block no filing matched at all is listed too.
        unfound = {cid for cid in standing if seats.get(standing[cid]["state"], 0) >= 2 and cid not in found}
        for st, bs in by_state.items():
            for b in bs:
                rows = [line for line in b["lines"] if re.search(r"\d", line) and not re.match(r"\W*(T\S*l\s+V|Write|Combined|Total)", line, re.I)]
                if rows and not any((id(b), line) in matched for line in rows):
                    print(f"# {cycle} no filing in {st}-{b['district']}: {rows[0]!r}", file=sys.stderr)
                for line in rows:
                    if (id(b), line) in matched:
                        continue
                    tally["results rows unmatched"] += 1
                    head = words(line.split(",")[0] if "," in line else line.split()[0])
                    key = "".join(head).translate(fold)
                    for c in unfound:
                        o = standing[c]
                        if o["state"] == st and o["district"] != b["district"] and difflib.SequenceMatcher(None, surname[c], key).ratio() >= 0.75:
                            tally["review"] += 1
                            print(f"# {cycle} review {st}-{b['district']} {line!r}: {c} {o['name']!r} cn {st}-{o['district']} receipts {receipts.get(c, 0):.0f}", file=sys.stderr)
                tally["results rows"] += len(rows)
        # The races `cn` gives two incumbent filings or more, and where the results put each.
        incumbents = collections.defaultdict(list)
        for cid, f in standing.items():
            if f["ici"] == "I" and seats.get(f["state"], 0) >= 2:
                incumbents[(f["state"], f["district"])].append(cid)
        for (st, d), cids in sorted(incumbents.items()):
            if len(cids) > 1:
                where = ", ".join(f"{standing[c]['name']} {c} {'results ' + st + '-' + d if c in same else 'results elsewhere' if c in found else 'not in results'}" for c in sorted(cids))
                print(f"# {cycle} incumbents {st}-{d}: {where}", file=sys.stderr)
        print(f"# {cycle}: {len(standing)} standing House filings: {dict(tally)}; receipts {dict((k, round(v)) for k, v in money.items())}", file=sys.stderr)


main()
```

</details>
