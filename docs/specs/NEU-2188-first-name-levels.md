# NEU-2188 — Two first names are one person's only by initial, prefix or nickname

**Ticket:** [NEU-2188](https://linear.app/neuroticsasquatch/issue/NEU-2188) · **Milestone:** M3 Resolution · **Parent story:** NEU-2021
**Project spec:** `fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` §6.3 and §6.4 (both amended by this spec), §6.9 · **ADRs:** 0009 (quality scored against DIME), 0010 (re-clustering; amended by this spec)
**Related:** NEU-2182 (Done: `fundlens diagnose`, the diagnosis this fixes), NEU-2122 (Done: re-clustering and the veto, `docs/specs/NEU-2122-recluster-chains.md`), **blocks** NEU-2189 (re-run the threshold sweep on this model and set the cluster threshold).

Planned 2026-11-03. `/implementit NEU-2188` implements straight from this file. One PR; the manual steps (§8) follow its deploy.

## 1. What and why

The model's first-name comparison (`src/fundlens/resolve/model.py`, `_first_name`) has a level meant for an initial against its full name ("'A' for 'AUGUSTINE'"). It is written as `ExactMatchLevel("first_initial")`, so it fires for *any* two first names that start with the same letter. MARGO and MICHAEL, JANE and JOHN, KATHRYN and KHIA all land there at a weight of about 0.67 instead of the else level (the veto, m = 1e-10), and an exact surname and ZIP outvote it. Re-clustering's veto (`cluster.py`, `_vetoed_pairs`) copies the else level and so asks for *different* first initials; it never cuts these pairs either.

NEU-2182's diagnosis of 2024 (refreshing-dime Log, 2026-11-03): 54 of 100 hand-classified wrong pairs were joined through this level; `GREEN, MARGO|30316||` and `GREEN, MICHAEL|30316||CONSULTANT` scored 0.9998 and chained ten keys of about eight people; among direct wrong pairs the `initial only` patterns hold at least 441,466 wrong to 23,339 correct. Overall precision is 0.6288 against a target of 0.8.

This ticket replaces that one level with **one rule for "these two first names can be one person's"**, read by the model, the veto and `diagnose` from the same SQL fragments in `model.py`:

- an **initial** pair: one name is a single letter and both start with that letter (`C` / `CRAIG`);
- a **nickname** pair: one name is a prefix of the other and the shorter is at least three letters (`LOU` / `LOUIS`, `MATT` / `MATTHEW`), or the vendored nickname table links the two directly (`HAL` / `HAROLD`, `MIKE` / `MICHAEL`, `BILL` / `WILLIAM`);
- everything else that is neither equal nor Jaro-Winkler-close is the veto, **whatever the initials** (`MARGO` / `MICHAEL`, and also a household's `EDWARD` / `ELIZABETH`).

The project spec §6.3 said "a nickname is an override's or adjudication's to merge, not linkage's" (NEU-2048). This ticket reverses that for the nicknames a table and a prefix rule can name: 2024 shows the model has to tell a nickname from a different name to tell MARGO from MICHAEL at all, and the veto's old "different initials" clause existed only because the initial level would otherwise have fired on BILL/WILLIAM-style pairs' neighbours. The reversal is recorded in §6.3, ADR-0010 and `CONTEXT.md` (§9).

### 1.1 Decisions this spec pins (grilled 2026-11-03)

| Decision | Pinned | Why (rejected alternative) |
|---|---|---|
| Level order | `null, exact, nickname, jw ≥ 0.92, jw ≥ 0.8, initial, else`. The nickname level sits **right after exact match**. | The ticket said "above the initial level", i.e. after both JW levels; but LOU/LOUIS (JW ≈ 0.91) and HAL/HAROLD (JW ≈ 0.87) would then be caught by `jw ≥ 0.8` first, and the ticket's own test for them fails. A known nickname or prefix is a stronger claim than a similarity score, and the `diagnose` label then says what it means. |
| Initial rule | One name is exactly one letter and `left(a, 1) = left(b, 1)`. Two full names sharing a letter are *not* an initial. | Lowering the old level's m instead leaves it reachable for two full names, so surname and ZIP still win and the veto still misses them. |
| Nickname rule | Prefix: `starts_with(longer, shorter) AND len(shorter) >= 3`. Table: the pair is an upstream row **read both ways** (`HAROLD → HAL` gives HAL/HAROLD and HAROLD/HAL). Two nicknames of one canonical name (HAL/HARRY, BILL/WILLY, PEGGY/MAGGIE) are **not** a nickname pair. | Siblings would widen every name's list (MARGARET has 20+ nicknames) and admit pairs through hub names (AL and BERT are both ALBERT's). A person filed under two different nicknames and never the full name is rare; the prefix rule already covers BOB/BOBBY. |
| The table | `carltonnorthern/nicknames` `names.csv` (Apache-2.0; 2,827 `name1,has_nickname,name2` rows, ~1,100 canonical names), vendored **byte-identical** as `src/fundlens/resolve/nicknames.csv`, with its `License.txt` beside it and a README recording the source URL, upstream commit, date fetched and licence. A second file, `nicknames-excluded.csv`, lists the upstream pairs fundlens refuses, each with a reason, starting with `aaron,erin` (the upstream file's first data row, and two people). | Editing the vendored CSV loses the diff against upstream and makes a refresh redo the edits by hand. Shipping the table whole knowingly admits AARON/ERIN. The exclusions file keeps fundlens's judgments authored and reviewable, like `overrides.yaml` and `aliases.yaml`. |
| Plumbing | `load` adds a column `first_name_nicknames VARCHAR[]` to `contributor`: the names the table links to the key's first name, both directions, less exclusions, uppercased; `[]` when none. The rule is then a pure expression, `list_contains(a_nicknames, b_name) OR list_contains(b_nicknames, a_name)`, so Splink's `CASE WHEN`, the veto and `diagnose` share one fragment with no subquery and no UDF. | A `nickname` pair table needs a correlated `EXISTS` inside Splink's generated comparison SQL, untested with sqlglot. A Python UDF like `soundex` runs per scored pair: 1e8 u-sampling pairs plus every blocked pair. |
| m and u of the new levels | **Priors, trained like their neighbours**: a prior m and u on each, which EM and u-sampling then move. Only the else level stays fixed. | The ticket said "fixed, like the levels around it", but in `model.py` only the else level is fixed (it exists to stop EM learning a household as one person). Fixing two more levels would make them the only non-veto levels training cannot correct. |
| The veto | Both first names present, not equal, Jaro-Winkler under `FIRST_NAME_VETO_JW` (0.8), **and neither an initial pair nor a nickname pair**. Initials no longer matter. | The old "different initials" clause is what let MARGO/MICHAEL through re-clustering; it also cut BILL/WILLIAM (different initials, JW low), the likely cause of the top-scope recall NEU-2122 lost (asserted there, not measured; §8 measures it). |
| `diagnose` | Its first-name levels follow the model's order and labels: `exact, nickname, jw ≥ 0.92, jw ≥ 0.8, initial only, other`. | `initial only` keeps meaning what the model means; the new `nickname` label shows whether the table admits wrong pairs. |
| One source of truth | The initial and nickname rules are two functions in `model.py` returning SQL fragments over caller-named column expressions; `_first_name`, `_vetoed_pairs` and `diagnose._LEVELS` all call them. | Three hand-copied `CASE` branches is how the veto drifted from the level in the first place. |

## 2. Definitions

Glossary terms (`CONTEXT.md`, Resolution; amended by this ticket): **vetoed pair** (new definition), **initial pair** and **nickname pair** (new). Use them in code, tests and docs.

- **Initial pair**: two first names of which one is a single letter, both starting with that letter: `C` / `CRAIG`, `E` / `EDWARD`. `E` / `KIRSTEN` is not (different letter); `MARGO` / `MICHAEL` is not (neither is a letter); `JO` / `JOSEPH` is not (two letters, and under the prefix rule's three).
- **Nickname pair**: two different first names of which one is a prefix of the other and the shorter has at least three letters (`LOU` / `LOUIS`, `RON` / `RONALD`, `KAT` / `KATHRYN`, `MATT` / `MATTHEW`, and so `MARY` / `MARY ANN`), or which the nickname table links directly in either direction (`HAL` / `HAROLD`, `MIKE` / `MICHAEL`, `BILL` / `WILLIAM`, `BOB` / `ROBERT`, `JIM` / `JAMES`, `PEGGY` / `MARGARET`).
- **Vetoed pair**: two first names both present, not equal, with Jaro-Winkler under `FIRST_NAME_VETO_JW`, that are neither an initial pair nor a nickname pair. Whatever their initials. A missing first name vetoes nothing.
- The **nickname table**: the vendored upstream CSV less the exclusions file, read both ways (§4).

## 3. The rule and the model (`src/fundlens/resolve/model.py`)

### 3.1 Fragments

```python
# The shortest first name the prefix rule treats as a nickname of a longer one: LOU for LOUIS,
# not JO for JOSEPH.
NICKNAME_MIN_PREFIX = 3

def initial_pair_sql(name_a: str, name_b: str) -> str:
    """SQL over the two first-name expressions: one is a single letter and both start with it."""
    return (
        f"((len({name_a}) = 1 OR len({name_b}) = 1)"
        f" AND left({name_a}, 1) = left({name_b}, 1))"
    )

def nickname_pair_sql(name_a: str, nicknames_a: str, name_b: str, nicknames_b: str) -> str:
    """SQL over two first names and their `first_name_nicknames` lists: one is a prefix of the
    other at least NICKNAME_MIN_PREFIX letters long, or the table links them."""
    return (
        f"(((starts_with({name_a}, {name_b}) OR starts_with({name_b}, {name_a}))"
        f" AND least(len({name_a}), len({name_b})) >= {NICKNAME_MIN_PREFIX})"
        f" OR list_contains({nicknames_a}, {name_b}) OR list_contains({nicknames_b}, {name_a}))"
    )
```

Both fragments are parenthesised so a caller can `NOT` them or `AND` them. Neither tests equality or nulls: the callers' level order (§3.2), `WHERE` clauses (§5) and `CASE` order (§6) do. `starts_with(x, x)` is true, so the prefix clause is only ever reached for unequal names. Column names differ by caller (`first_name_l` in Splink, `a.first_name` in the veto's CTE), which is why the fragments take expressions.

### 3.2 The comparison

```python
cll.NullLevel("first_name"),
cll.ExactMatchLevel("first_name").configure(m_probability=0.86, u_probability=0.005),
cll.CustomLevel(
    nickname_pair_sql("first_name_l", "first_name_nicknames_l", "first_name_r", "first_name_nicknames_r"),
    label_for_charts="nickname",
).configure(m_probability=0.03, u_probability=0.002),
cll.JaroWinklerLevel("first_name", 0.92).configure(m_probability=0.06, u_probability=0.003),
cll.JaroWinklerLevel("first_name", FIRST_NAME_VETO_JW).configure(m_probability=0.03, u_probability=0.01),
cll.CustomLevel(initial_pair_sql("first_name_l", "first_name_r"), label_for_charts="initial")
    .configure(m_probability=0.02, u_probability=0.002),
cll.ElseLevel().configure(m_probability=1e-10, u_probability=0.978, fix_m_probability=True),
```

- The priors sum to 1 on each side (m: 0.86 + 0.03 + 0.06 + 0.03 + 0.02 ≈ 1; u: 0.005 + 0.002 + 0.003 + 0.01 + 0.002 + 0.978 = 1). The initial level's u falls from 0.03 to 0.002 because a real single-letter first name is rare in a random pair; its match weight goes from about −0.6 to about +3.3, which is what "'A' for 'AUGUSTINE'" always meant. Training re-estimates every level but the else level, as today.
- `first_initial` stays on `contributor`: blocking rule 2 (`last_name, first_initial, state`) reads it. Only the comparison level goes.
- Update the module docstring's "a nickname (PEGGY for MARGARET) is an override's or an adjudication's to merge" paragraph: a nickname the table or the prefix rule names is linkage's; one it does not name is still an override's.
- `retain_matching_columns=False` stays. Splink finds the comparison's input columns by parsing each level's SQL, so `first_name_nicknames` is carried into the pairwise table by `_l`/`_r` suffix like any column. **If it is not** (the predict SQL fails on an unknown column), set `additional_columns_to_retain=["first_name_nicknames"]` in `settings()`; say so in the PR.

## 4. The table (`src/fundlens/resolve/nicknames.py`, `_load_contributors`)

Files beside `aliases.yaml`:

- `nicknames.csv`: upstream `names.csv`, byte-identical. Header `name1,relationship,name2`, lowercase, one `has_nickname` row per canonical → nickname.
- `nicknames-LICENSE.txt`: upstream `License.txt` (Apache-2.0 requires the licence travel with the file).
- `nicknames.md`: the source (`https://github.com/carltonnorthern/nicknames`, file `names.csv`, the upstream commit SHA and the date fetched), the licence, the exclusions file's purpose, and how to refresh (re-download, re-run the exclusions test).
- `nicknames-excluded.csv`: header `name1,name2,reason`, lowercase as upstream, one row per refused upstream pair in upstream's direction. First row: `aaron,erin,different names that happen to sound alike; AARON is a man's name and ERIN a woman's`. Add any other pair that is plainly two people on a read of the file; the PR lists what it excluded and why.

`nicknames.py` mirrors `normalize`'s `aliases.yaml` handling:

```python
def pairs() -> set[tuple[str, str]]:
    """Every (name, other) the table links, both directions, uppercased, less the exclusions."""
```

It reads both files with `importlib.resources` (`package_files("fundlens.resolve")`), and raises `ValueError` naming the row when: an upstream row's relationship is not `has_nickname`; a row has an empty name; `name1 == name2`; an exclusion names a pair upstream does not have (a stale exclusion is a mistake, as an alias "under two employers" is). A unit test calls it on the vendored files (a stale exclusion fails the build) and asserts `("HAROLD", "HAL")` and `("HAL", "HAROLD")` are in, `("AARON", "ERIN")` is out, and `("HAL", "HARRY")` is out.

`_load_contributors` (`runner.py`) adds the column:

```sql
-- $names and $others are the two sides of `nicknames.pairs()`, passed as VARCHAR[] parameters.
nickname AS (
    SELECT name, list(DISTINCT other ORDER BY other) AS first_name_nicknames
    FROM (SELECT unnest($names::VARCHAR[]) AS name, unnest($others::VARCHAR[]) AS other)
    GROUP BY name
)
…
SELECT …,
    chosen.name_first AS first_name,
    coalesce(nickname.first_name_nicknames, []::VARCHAR[]) AS first_name_nicknames,
…
LEFT JOIN nickname ON nickname.name = chosen.name_first
```

Lists are small (MARGARET's is the longest, about 25) and only keys whose first name is in the table carry a non-empty one, so the working file grows by little; `docs/capacity.md`'s Resolution row for the run records the size as every row does.

## 5. The veto (`src/fundlens/resolve/cluster.py`, `_vetoed_pairs`)

The `name` CTE selects `DISTINCT c.cluster_id, k.first_name, k.first_name_nicknames`; the join and `WHERE` become:

```sql
WHERE jaro_winkler_similarity(a.first_name, b.first_name) < $jw
    AND NOT {initial_pair_sql("a.first_name", "b.first_name")}
    AND NOT {nickname_pair_sql("a.first_name", "a.first_name_nicknames", "b.first_name", "b.first_name_nicknames")}
```

(`b.first_name > a.first_name` already excludes equal names.) Its docstring changes from "different first initials" to "neither an initial pair nor a nickname pair". `recluster_component`, `components_at`, `recluster` and every table schema are unchanged: the veto is still a set of first-name pairs per component.

Consequence worth stating in the PR: a household's `EDWARD` and `ELIZABETH` are now a vetoed pair (NEU-2122 §1.1 said the old rule spared them; the model never did, and 11 of NEU-2182's 100 sampled wrong pairs were households). `E` / `EDWARD` is still not vetoed (initial pair), nor `E` / `ELIZABETH`; `E` / `KIRSTEN` still is.

## 6. `diagnose` (`src/fundlens/resolve/diagnose.py`, `_LEVELS["first_name"]`)

```sql
WHEN a.first_name = b.first_name THEN 'exact'
WHEN {nickname_pair_sql("a.first_name", "a.first_name_nicknames", "b.first_name", "b.first_name_nicknames")} THEN 'nickname'
WHEN jaro_winkler_similarity(a.first_name, b.first_name) >= 0.92 THEN 'jw ≥ 0.92'
WHEN jaro_winkler_similarity(a.first_name, b.first_name) >= $veto THEN 'jw ≥ 0.8'
WHEN {initial_pair_sql("a.first_name", "b.first_name")} THEN 'initial only'
ELSE 'other'
```

`SIDE_COLUMNS` and the `Side` dataclass do not change (the sample prints names, not lists). Nothing else in `diagnose` changes; the runbook's §9 text already describes the patterns without naming the labels.

## 7. Tests

All in `tests/unit`, on hand-built tables as the existing tests do. Every fixture `contributor` table gains `first_name_nicknames VARCHAR[]`; the `record()` and `working_file()` helpers fill it from `nicknames.pairs()` (or a literal list in the few tests that need one), so BILL's row carries `['WILLIAM', …]`.

- `test_resolve_model.py`: the first-name comparison's level for each pair, via `score_pair` and `gamma_first_name` as `test_cluster.model_vetoes` does, mapped to the level label: `MARGO/MICHAEL`, `JANE/JOHN`, `EDWARD/ELIZABETH`, `BEATRICE/DESMOND` → else; `C/CRAIG`, `E/EDWARD` → initial; `E/KIRSTEN` → else; `LOU/LOUIS`, `HAL/HAROLD`, `MIKE/MICHAEL`, `BILL/WILLIAM`, `MATT/MATTHEW` → nickname; `JO/JOSEPH` → whatever JW gives, not nickname (asserts the three-letter floor); `ELIZABETH/ELISABETH` → jw ≥ 0.92; `CARL/KARL` → jw ≥ 0.8; `JOHN/JOHN` → exact; `None/KIRSTEN` → null.
- `test_cluster.py`: `NAME_PAIRS` gains `("MARGO", "MICHAEL")`, `("BILL", "WILLIAM")`, `("C", "CRAIG")`, `("LOU", "LOUIS")`; the existing `test_the_vetoed_pairs_recluster_finds_are_the_models_else_level` keeps asserting the SQL agrees with the model on every pair, and its count of vetoes becomes the new truth (EDWARD/ELIZABETH and MARGO/MICHAEL join E/KIRSTEN and BEATRICE/DESMOND). A new test: a component of two keys MARGO and MICHAEL joined by one edge at 0.99 is re-clustered apart; one of BILL and WILLIAM is left whole.
- `test_diagnose.py`: the level parametrisation gains `("C", "CRAIG", "initial only")`, `("MARGO", "MICHAEL", "other")`, `("LOU", "LOUIS", "nickname")`, `("MIKE", "MICHAEL", "nickname")`; `("E", "EDWARD", "initial only")` stays.
- `test_nicknames.py` (new): §4's assertions; a stale or self-referential exclusion raises.
- The fixture-cycle tests (`resolve_full` on `tests/fixtures`) run unchanged; `_load_contributors` builds the column. If a fixture donor's keys now split (two full names sharing an initial that the fixture treated as one person), fix the fixture, not the rule, and say so in the PR.

`task format`, `task lint`, `task typecheck`, `task test` in the container, as always.

## 8. Manual steps, after the deploy (`docs/runbooks/refreshing-dime.md`)

Merge only with nothing running on `pipeline` (a merge redeploys it and kills in-flight `docker exec` steps). Then, on `music-box-dancer` for 2024, in this order:

1. §8.1 (the deployed SHA is this PR's merge), §8.2 `resolve --full` (a new model trains; copy the `recluster:` line, and add a Resolution-table row to `docs/capacity.md` with the working file size), §8.3 `validate`, §8.6 crosswalk check.
2. §9.2 plain `recluster` (must print §8.2's line), §9.3 `diagnose --cycle 2024 --sample 100`. No sweep here: that is NEU-2189.
3. §5 `load` and `publish` for 2024, so the live build's silver (rewritten in place by `resolve --full`) and gold agree. NEU-2189 repeats them after the threshold is set.
4. Append a Log entry (model, build, SHA, the `recluster:` line, both scopes' precision and recall, `diagnose`'s link table and top patterns, and the `initial only` and `nickname` pattern totals) and a Findings entry in `docs/capacity.md` stating what the levels gained and cost. Add a Validation-table row. Record the crosswalk churn (keys re-pointed, new donors, redirects): the first `resolve --full` after this splits many live donors.

### 8.1 Acceptance (the ticket's Definition of done)

- Overall precision ≥ 0.70 and recall ≥ 0.90 on 2024; top 10,000 not below 0.9516 / 0.8023 (the figures the veto left on 2026-11-02).
- `diagnose`: the `initial only` patterns hold fewer than 50,000 wrong pairs (441,466 before).
- Expected from NEU-2182's figures: removing the 441,466 direct wrong and 23,339 correct `initial only` pairs takes precision to about 0.73; if the veto also breaks the chained ones, about 0.77; recall may fall by up to 0.010, less whatever the nickname level keeps. Report what was measured, whichever way it went; if a floor is missed, say so in the Log and leave the ticket open for the user's call.

## 9. Documentation this spec amends (done with the spec, 2026-11-03)

- `CONTEXT.md` Resolution: **Vetoed pair** redefined; **Initial pair** and **Nickname pair** added.
- `docs/adr/0010-…`: an amendment paragraph (the veto no longer reads initials; nicknames are the table's and the prefix rule's).
- Project spec §6.3 and §6.4: NEU-2188 amendments.

The implementer updates `model.py`'s docstrings (§3.2), `_vetoed_pairs`'s docstring (§5) and writes `nicknames.md` (§4). The methodology page (NEU-2056, not yet built) will state the rule in one sentence when it is.

## 10. Not in scope

- The cluster threshold and its sweep: NEU-2189, blocked by this ticket.
- DIME's own splits (about 30% of the wrong pairs; reported, not fixable here); common names in one area; surname drift (GREEN/GREENE, FREEDMAN/FRIEDMAN).
- Siblings in the nickname table (HAL/HARRY), a larger or probabilistic nickname resource (LDC2012T11 is licensed, not open), and nickname handling for last names.
- The incremental resolve (NEU-2062) and the backfill (NEU-2060); both inherit the column and the rule through `_load_contributors` and `recluster`.
- Any change to blocking rules, the other comparisons, the cap, overrides or adjudication.
