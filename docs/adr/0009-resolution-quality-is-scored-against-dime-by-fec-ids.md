---
status: accepted
---

# Resolution quality is scored against DIME, joined by FEC ids, over labelled contributor keys

fundlens publishes a precision and a recall for its donor resolution. The reference is Adam Bonica's DIME, Public version 4.0 (ODC-BY 1.0), whose contribution records carry a resolved contributor id, `bonica.cid`, and, on every electronically filed FEC row, the filer's FEC committee id and transaction id (`efec.comid.orig`, `efec.transaction.id.orig`). Planning NEU-2054 (2026-11-01) pinned three things the project spec (§6.9) had left open.

**The join is exact, by FEC ids, against bronze.** A DIME row meets an FEC contribution on `(CMTE_ID, TRAN_ID, amount, date)` read from the cycle's bronze `indiv` file (the amount by magnitude: a refund's sign is the filer's choice in FEC's bulk file, and DIME's may differ), and the `SUB_ID` then meets silver `contribution`. An FEC row matched to more than one `bonica.cid` is dropped. The spec's fuzzy join (date, amount, recipient committee, normalized name) was rejected: twelve of the fixture's 308 rows already collide on it, it would make the matched set depend on our own normalizer, and it needs DIME's recipients file to translate `bonica.rid`. Adding `TRAN_ID` to silver was rejected because bronze already holds it for every cycle and is never pruned.

**The record scored is the labelled contributor key**, one per distinct `(contributor_key, bonica.cid)` among the matched contributions, and the metrics are pairwise precision and recall from the `donor_id × cid` contingency table. A key DIME assigns to two people becomes two records fundlens necessarily puts together, so the figure does not flatter us. Scoring contribution rows was rejected because frequent givers would dominate the pairs; scoring keys by majority label because it hides DIME's splits.

**The DIME file is archived.** The raw `contribDB_<cycle>.csv.gz` (19.2 GB for 2024) and a slim Parquet of its FEC individual rows both live in R2 under `reference/dime/v<version>/`, written by `fundlens dime --import`; only the Parquet is read. Dropbox links rot and `bonica.cid` values change between DIME releases, so a published figure must be reproducible from what we hold.

## Consequences

- `app.resolution_quality` stores the figures and their pair counts per `(model_version, cycle, scope)`; `gold.meta` carries the live model's overall and top-10k figures, `matched_rows` and `dime_version`; the methodology page prints them with DIME's citation.
- The figures cover electronically filed contributions only. Early cycles will match few rows, and `matched_rows` says how many; whether that is enough to publish is the backfill's call.
- A new DIME release is a version bump, a re-import of every cycle and a re-validation; nothing under an old version's keys is touched.
- The top-10k scope is defined on DIME's side (the `cid`s with the most matched dollars), so it does not move when our clustering does.
