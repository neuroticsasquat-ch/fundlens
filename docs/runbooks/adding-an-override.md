# Runbook: adding an override

How to tell resolution that some contributor keys are one donor (a **merge**) or that one key is not
the donor linkage put it with (a **split**), in a reviewed commit that every rebuild applies (NEU-2050;
spec §6.5, §10.5; ADR-0005). The overrides live in [`resolution/overrides.yaml`](../../resolution/overrides.yaml);
`src/fundlens/resolve/overrides.py` reads, checks and applies them. Repeat it for each override; append
to the [Log](#log) at the bottom, never rewrite it.

**When to use one.** Linkage keeps apart what only a reviewer can join (a nickname: MARGARET and PEGGY)
and joins what only a reviewer can tell apart (father and son at one address, whose `JR` and `SR`
normalization strips). An override is for a donor you can name and justify in a sentence. It is not a
way to tune linkage across many donors: that is the thresholds (spec §6.4) and a `resolve --full`.

**Not in this runbook:** adjudication (spec §6.8), tuning the model, re-resolving after a change to the
model or normalization.

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Overrides file | `resolution/overrides.yaml` in the repo; `/app/resolution/overrides.yaml` in the image (`OVERRIDES_PATH`) |
| Where the keys come from | resolution's DuckDB working file, `/data/fundlens/resolution/resolve.duckdb` in `pipeline`: the `contributor` table (every cycle's silver `contributor` partition as one table, one row per key) and the `crosswalk` table (each key's `donor_id`), both as the last `fundlens resolve --full` left them |
| What applies the overrides | `fundlens resolve --full`, after clustering and before the crosswalk. Nothing else: there is no weekly run yet (`fundlens run` is NEU-2061, the schedule NEU-2063) and no incremental resolution (spec §6.10), so an override takes effect when this runbook's step 5 runs it by hand |
| What stops a run | a malformed file, a key in two entries, a key that is in no cycle's silver, a split `from` that is no donor_id the crosswalk gave. The run stops before the crosswalk changes and names every problem |

**What a merge does.** Every cluster holding one of the listed keys becomes one cluster, so list one key
from each donor to join; the crosswalk then keeps the id with the most dollars and redirects the others
to it (spec §6.6). **What a split does.** The key leaves its cluster for one of its own; the crosswalk
keeps the donor's id on the side with more dollars and gives the other side a new id. `from` is the
donor_id the key carried when you wrote the entry: the run checks it is an id the crosswalk gave, so an
entry cannot name a donor that never existed.

## 0. Session setup

```bash
# laptop
ssh hetzner-01
```

```bash
# VM
# Container names change on every deploy: look each one up when it is used (coolify-setup Log).
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
# A query from stdin against resolution's working file, read-only; `$surname` in it is the first argument.
rq() { docker exec -i "$(fl pipeline)" python -c 'import sys, duckdb; duckdb.connect("/data/fundlens/resolution/resolve.duckdb", read_only=True).sql(sys.stdin.read(), params={"surname": sys.argv[1]}).show(max_width=250, max_rows=200)' "$1"; }
# psql in the fundlens database.
pg() { docker exec "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
```

**Expected:** no output. `rq` fails with `Could not set lock on file` while a `resolve --full` is running:
the working file has one writer at a time. Wait for it to finish.

## 1. Find the keys

Look the donor up by surname: set `SURNAME` to the one you are after, uppercase as the FEC writes it
and without `JR`/`SR` (`ABERNATHY` below is the fixture's split donor):

```bash
# VM
export SURNAME=ABERNATHY
rq "$SURNAME" <<'SQL'
SELECT x.donor_id, k.contributor_key, k.city, k.state, k.contribution_count, k.amount_total,
    k.first_cycle, k.last_cycle
FROM contributor AS k
JOIN crosswalk AS x USING (contributor_key)
WHERE k.last_name = $surname
ORDER BY x.donor_id, k.amount_total DESC
SQL
```

**Expected:** one row per contributor key, grouped by `donor_id`. A contributor key is the donor's
normalized name, ZIP5, employer and occupation joined by `|`, an absent one empty, e.g.
`ABERNATHY, CHARLES|21044||STUDENT`. Copy keys exactly as printed, trailing `|`s included.

- **A merge:** one donor appears under two or more `donor_id`s. Pick one key from each.
- **A split:** a key sits under a `donor_id` it does not belong to. Note the key and that `donor_id`.
  If that key's `amount_total` is more than the rest of the donor's keys together, the split leaves
  **it** the `donor_id` and gives the rest a new one (spec §6.6): the donor's page moves to a new id.
  Say so in the PR.

No rows: the surname is spelled differently in the filings (change `=` to `LIKE` and set `SURNAME` to a prefix and `%`, e.g. `ABERN%`), or
the donor's cycle has not been resolved since it was transformed.

## 2. Write the entry

On the laptop, from an up-to-date `main`, branch, then append the entry to `resolution/overrides.yaml`.
Set `SURNAME` as in step 1 and `KIND` to `merge` or `split`:

```bash
# laptop
export SURNAME=ABERNATHY KIND=split
cd ~/projects/fundlens
git switch main
git pull --ff-only
git switch -c "fix/override-$KIND-$(echo "$SURNAME" | tr '[:upper:]' '[:lower:]')"
date +%F
```

**Expected:** a new branch, and today's date, which is the entry's `added`. Replace the file's final
`[]` with the first entry; later entries go after the last one. Quote every key (they hold `|` and
`,`).

A merge:

```yaml
- merge: ["KOWALCZYK, MARGARET|20910|MONTGOMERY COUNTY|LIBRARIAN", "KOWALCZYK, PEGGY|20910||"]
  reason: PEGGY is MARGARET's nickname; one address, one librarian since retired.
  added: 2026-10-31
```

A split:

```yaml
- split: {contributor_key: "ABERNATHY, CHARLES|21044||STUDENT", from: 1}
  reason: The student is CHARLES JR, not his retired father CHARLES SR at the same address.
  added: 2026-10-31
```

`reason` is the evidence, for the reviewer and for whoever reads the file in a year. A key goes in one
entry only: to join three donors, list one key of each in a single merge.

## 3. Run the validator

```bash
# laptop
task up
task test -- tests/unit/test_overrides.py
```

**Expected:** every test passes, `test_the_committed_file_is_valid` among them. A failure names the
entry and the problem, e.g. `overrides: entry 2 split.from: Field required` or
`overrides: 'KOWALCZYK, PEGGY|20910||' is in merge 1 and merge 2`. Fix the entry and run it again.

The validator checks the file by itself. Whether each key is in the data and each `from` is a donor_id
the crosswalk gave is checked by the run (step 5), against production; step 1 is where you got them, so
they are.

## 4. Open the PR

```bash
# laptop
task format
git add resolution/overrides.yaml
git commit -m "fix(resolve): $KIND override for $SURNAME"
git push -u origin HEAD
gh pr create --base main --fill
```

**Expected:** CI runs `tests/unit/test_overrides.py` with the rest of the suite and passes. Merge the PR
when it is reviewed. Coolify deploys `main`, which copies the file into the image.

## 5. Apply it

On the VM, once the deploy has finished:

```bash
# VM
git ls-remote https://github.com/neuroticsasquat-ch/fundlens main
docker exec "$(fl pipeline)" printenv OTEL_RESOURCE_ATTRIBUTES
docker exec "$(fl pipeline)" tail -n 5 /app/resolution/overrides.yaml
```

**Expected:** the `service.version=<sha>` in `OTEL_RESOURCE_ATTRIBUTES` is the SHA `ls-remote` prints,
and the file ends with your entry. If not: Coolify → the `fundlens` resource → *Deploy*, wait for it to
finish, and run this step again.

```bash
# VM, in tmux: a full resolution over every cycle takes as long as the last one did (docs/capacity.md)
time docker exec "$(fl pipeline)" fundlens resolve --full 2>&1 | tee resolve-override.log
```

**Expected:** exit 0, and an `overrides:` line counting your entry, e.g.
`overrides: 1 merges joining 1 clusters into others, 0 splits`. A line starting `overrides:` on stderr
and exit 1 means the run stopped before the crosswalk changed: it names the key or donor_id it does not
know. Correct the entry in a new PR and repeat from step 2.

Check the crosswalk took it. For a merge, every key you listed now has one `donor_id`, and the ids that
went away redirect to it; for a split, the key has a `donor_id` of its own:

```bash
# VM
pg -c "select contributor_key, donor_id from app.crosswalk where contributor_key in ('<key>', '<key>')"
pg -c "select old_donor_id, donor_id from app.donor_redirect where old_donor_id in (<old id>, <old id>)"
```

The itemized contributions read the new ids from silver at once. Gold carries them after its cycle is
loaded and published again: for each cycle `resolve` printed (`<cycle>: build <build>`), run
`docker exec "$(fl pipeline)" fundlens load --cycle <cycle> --build-id <build>` and then
`docker exec "$(fl pipeline)" fundlens publish --cycle <cycle>`.

`publish` ends with `kuma push (up) failed: HTTPError: HTTP Error 404: Not Found` while the Kuma monitors are paused
(coolify-setup step 12, until NEU-2063's schedule): Kuma refuses a push to a paused monitor. Leave them paused.

Append to the Log below: the date, the PR, the entry's donor, and the `overrides:` and `crosswalk:`
lines of the run.

## Log

<!-- Append entries below; never rewrite one. -->

### 2026-11-01 — Elon Musk's Hawthorne key (NEU-2121, PR #52)

A merge of `MUSK, ELON|90250|SPACE X TESLA MOTORS|CEO CHIEF TECHNOLOGY OFFICER` (donor `2441074`, alone, $825,000)
with `MUSK, ELON|78734|SPACEX|CEO` (donor `2441073`), applied from `bad9c28` by a `resolve --full` (model
`20261101T205049Z`, 9 m 55 s) and then 2024's load and publish of build `20261031T202003Z`:

- `overrides: 1 merges joining 1 clusters into others, 0 splits`
- `crosswalk: 0 new donors, 1 keys re-pointed, 1 redirects`

5,620,495 contributor keys in 3,816,140 clusters, one fewer than the first resolved run. Search for `musk elon` lists one
donor, `2441073`, with `contributor_key_count` 11 and `total_all_cycles` 213055236, and `/v1/donors/2441074` answers
`301` to `/v1/donors/2441073`. The publish's Kuma push answered `404`: `fundlens/publish` is paused until NEU-2063, as
step 5 says.
