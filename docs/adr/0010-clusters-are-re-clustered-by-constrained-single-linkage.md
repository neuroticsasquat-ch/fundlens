---
status: accepted
---

# Clusters are Splink's components re-clustered by constrained single-linkage: no vetoed first-name pair, at most N keys

Splink's `cluster_pairwise_predictions_at_threshold` makes each connected component of the pairs at or above the cluster threshold one cluster, and fundlens made each cluster one donor. A connected component ignores every pair it did not link, so a path of individually plausible pairs joins people the model would never pair directly. The 2024 DIME validation (NEU-2054, 2026-11-02) measured overall precision 0.3657 against recall 0.9149; one donor held 1,105 keys DIME labels as 766 people, the ten largest clusters held half of all wrong pairs, and DIME's own key splits explained 1.4% of them. Planning NEU-2122 pinned the fix.

**Every component that holds a vetoed pair, or more keys than the cluster cap, is rebuilt from its own edges, strongest first, under two constraints.** A vetoed pair is exactly the pair the model's first-name comparison rejects at its else level (both names present, not equal, Jaro-Winkler under 0.8, different initials), computed with the same DuckDB function the model compiles to, so the rule cannot drift from the model. The cap, `RESOLVE_MAX_CLUSTER_KEYS`, is a setting tuned against DIME. An edge unions the two pieces its ends are in unless the union would hold a vetoed pair or exceed the cap; a refused edge is skipped. Components that offend neither constraint are untouched. The pass runs after linkage and before overrides, which may still build any cluster a reviewer asserts.

Rejected: raising the cluster threshold everywhere (a chain forms at any threshold; recall on every donor pays for a few hundred chains); re-clustering oversized components at a per-component adaptive threshold or a fixed ladder (a threshold is a cliff: once the cap is hit every weaker edge in the component drops, so a real donor of 2N keys shatters, and probabilities saturate near 1.0 so a ladder tops out); a first-name rule alone (cannot touch a cluster of same-named people across one metro); community detection (a dependency, a seed, and a paragraph on the methodology page, for no measured gain yet); sending large clusters to adjudication (NEU-2055's apply rule merges or splits named keys, and 1,105 keys fit in no prompt).

**The predicted pairs stay in the working file.** `edge` (pairs at or above the match threshold) and `component` (Splink's clustering) are kept beside `cluster`, so the cap is tuned offline (`fundlens recluster --max-keys N`, `fundlens validate --clusters`) without a `resolve --full` and a crosswalk rewrite per candidate, and so the incremental resolve (NEU-2062) re-clusters new keys the same way.

## Consequences

- The first `resolve --full` after this splits many live donors: each keeps its id on the piece holding most of its dollars, the other pieces draw new ids, and redirects are written only for ids no key carries any more (ADR-0005). The PR records the counts.
- The methodology page states the rule in one sentence; precision and recall published with it are the re-clustered figures.
- `RESOLVE_MAX_CLUSTER_KEYS` is retuned when the model is retrained or the backfill adds cycles; the loop in `docs/runbooks/refreshing-dime.md` is how.
- A cluster of different people who share a first name and link pairwise at 0.99 is still one donor up to the cap: the cap bounds the model's error, it does not fix it.
- The working file grows by the `edge` and `component` tables (low single-digit GB on 2024; `docs/capacity.md` records it).

## Amendment 2026-11-03 (NEU-2188): the veto reads no initials

The first-name comparison's "initial" level was an exact match on `first_initial`, so any two names sharing a first letter (MARGO and MICHAEL) scored as an initial and its full name instead of reaching the else level; NEU-2182's diagnosis of 2024 put 54 of 100 sampled wrong pairs on it. The veto above copied that level, so it required *different* initials and never cut those pairs either, while it did cut BILL from WILLIAM.

A vetoed pair is now: both first names present, not equal, Jaro-Winkler under 0.8, and **neither an initial pair** (one name a single letter, both starting with it) **nor a nickname pair** (one a prefix of the other at least three letters long, or the two linked directly by the vendored nickname table `resolve/nicknames.csv` less `nicknames-excluded.csv`), whatever their initials. The model gains a nickname level and its initial level fires only for a real single letter; the model, the veto and `fundlens diagnose` read the initial and nickname rules from the same two SQL fragments in `resolve/model.py`, so the three cannot drift. A household's EDWARD and ELIZABETH are now a vetoed pair. Spec: `docs/specs/NEU-2188-first-name-levels.md`.
