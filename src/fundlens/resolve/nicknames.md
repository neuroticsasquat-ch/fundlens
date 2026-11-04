# The nickname table

The first-name comparison's nickname level and re-clustering's veto read which first names are one
person's (NEU-2188, `docs/specs/NEU-2188-first-name-levels.md`). `nicknames.py` loads them.

## Source

- **Upstream:** <https://github.com/carltonnorthern/nicknames>, file `names.csv`
- **Commit:** `ed160b3af2d17e1af8ebd570f10a10e4dade4ff4` (committed 2026-08-02)
- **Fetched:** 2026-11-03
- **Licence:** Apache License 2.0, copied unchanged as `nicknames-LICENSE.txt`

`nicknames.csv` is upstream's `names.csv` **byte for byte**, CRLF line endings included: 2,827
`name1,has_nickname,name2` rows, lowercase, one per canonical name and a nickname of it. Do not
edit it. A pair fundlens refuses goes in `nicknames-excluded.csv`, so the vendored file always
diffs clean against upstream.

## Exclusions

`nicknames-excluded.csv` (`name1,name2,reason`) lists the upstream rows that are plainly two people,
written in upstream's direction, each with its reason: AARON and ERIN, ANDREA and ANDREW. An
exclusion removes the pair both ways. Every exclusion must name a pair upstream has; a stale one
fails `tests/unit/test_nicknames.py`.

## How the table is read

Both ways (HAROLD → HAL gives HAL/HAROLD and HAROLD/HAL), uppercased, less the exclusions. Two
nicknames of one name (HAL and HARRY, both HAROLD's) are not linked. `load` gives each contributor
key the names its first name is linked to as `first_name_nicknames`.

## Refreshing it

```bash
# laptop, from the repo root
SHA=<upstream commit>
curl -sfL -o src/fundlens/resolve/nicknames.csv \
  "https://raw.githubusercontent.com/carltonnorthern/nicknames/$SHA/names.csv"
curl -sfL -o src/fundlens/resolve/nicknames-LICENSE.txt \
  "https://raw.githubusercontent.com/carltonnorthern/nicknames/$SHA/License.txt"
task test -- tests/unit/test_nicknames.py
```

Then update the commit and date above, read the upstream diff for new pairs that are two people,
and add those to the exclusions. A changed table changes the model's levels, so the next
`resolve --full` is the one that takes it up.
