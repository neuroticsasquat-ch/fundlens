# Runbook: adjudicating the ambiguous high-dollar clusters

How to ask the adjudication model about the clusters where linkage is least sure and the money is
largest, and apply what it answers (NEU-2055; spec §6.8; ADR-0005).
`src/fundlens/resolve/adjudicate.py` chooses the candidates, sends them and applies the verdicts; the
prompt is [`resolution/prompts/adjudicate_v1.md`](../../resolution/prompts/adjudicate_v1.md). Append to
the [Log](#log) at the bottom after every run, never rewrite it.

**What is asked.** A *pair*: two clusters linkage keeps apart, sharing a last name and ZIP3, with
`ADJUDICATE_MIN_AMOUNT` (default $50,000) between them, whose best pair of keys the saved model scores
in `[0.6, 0.95)`. A *cluster*: one cluster of at least that much whose keys report two or more
employers, asked whether the keys of its other employers belong with those of its biggest one. A
candidate holding a key `resolution/overrides.yaml` names is never asked: the overrides are the human
record. **What is applied.** A `merge` or `split` with a confidence of at least 0.8, by every
`resolve --full` and `recluster` after it, between the overrides and the crosswalk. `unsure`, and
anything less sure, is recorded and never applied.

**Not in this runbook:** a review UI, adjudications in the public dataset (both out of scope), and
changing the default model, which needs its own timing run first (step 3).

## Facts

| What | Value |
| --- | --- |
| Host | `music-box-dancer` (tailnet `hetzner-01`) |
| Resource UUID | `lvch8zyndujjzkz16ksys8im` ([coolify-setup.md](coolify-setup.md) Log) |
| Model | `ADJUDICATE_MODEL`, default `deepseek-ai/DeepSeek-V4-Flash`, on DeepInfra with `DEEPINFRA_API_KEY` |
| Verdicts | `app.adjudication`, one row per (candidate fingerprint, model, prompt version); snapshotted to R2 at every publish |
| Candidates come from | the `unadjudicated` table of the working file `/data/fundlens/resolution/resolve.duckdb`: every key's cluster after overrides and before adjudications, as the last `resolve --full` or `recluster` left it. A working file from before NEU-2055 has no such table, and `adjudicate` says to resolve |
| Pair scores come from | the newest model in R2 `resolution/model/`, the one the last `resolve --full` trained |
| Cost | every request is billed. `--dry-run` sends nothing; a re-run sends nothing for a candidate this model and prompt already answered |

**Never merge to `main` while a step here is running:** every merge redeploys `pipeline` and kills a
running `docker exec`.

## 0. Session setup

```bash
# laptop
ssh hetzner-01
```

```bash
# VM
fl() { docker ps --format '{{.Names}}' | grep "^$1-lvch8zyndujjzkz16ksys8im" | head -1; }
pg() { docker exec "$(fl fundlens-postgres)" psql -U fundlens -d fundlens "$@"; }
PIPE=$(fl pipeline); echo "$PIPE"
```

**Expected:** one container name, `pipeline-lvch8zyndujjzkz16ksys8im-…`.

## 1. Give the working file its `unadjudicated` table

Only once, on a working file from before NEU-2055. `recluster` rewrites the clusters from the components
`resolve --full` left, as that run did, and keeps them as `unadjudicated`: a minute or two, no training,
and nothing outside the working file changes.

```bash
# VM
docker exec "$PIPE" fundlens recluster; echo "exit=$?"
```

**Expected:** `exit=0` and `adjudications: 0 verdicts: 0 merges joining 0 clusters into others, 0 splits`.

## 2. See the candidates

```bash
# VM
docker exec "$PIPE" fundlens adjudicate --dry-run > /tmp/adjudicate-dry-run.txt; echo "exit=$?"
head -3 /tmp/adjudicate-dry-run.txt; tail -1 /tmp/adjudicate-dry-run.txt
```

**Expected:** `exit=0`, a `candidates: <n> clusters, <m> pairs of at least $50000; 0 already decided …`
line, `chosen: <k>`, then one line per candidate (`pair <fingerprint> $<amount> p=<score>: …` or
`cluster <fingerprint> $<amount>: …`), the most dollars first, and `dry run: nothing sent, nothing
written`. Record `n`, `m` and `k` for the Log.

## 3. Time the model on 50 candidates

The model is confirmed, or replaced, by what this costs and how long it takes (the standing rule: time a
model before setting it). 50 candidates, the most dollars first:

```bash
# VM
docker exec "$PIPE" fundlens adjudicate --limit 50; echo "exit=$?"
```

**Expected:** `exit=0`, five `batch <n>: 10 requests, …` lines (`ADJUDICATE_BATCH_SIZE`, default 10),
each with its tokens in and out, its cost, its p50 and p95 latency and its wall time, and a
`recorded: …` line counting the decisions. `invalid` and `failed` should be 0; a few invalid replies
are asked again by the next run, but many mean the model does not keep to the prompt's JSON. Copy the
batch lines into the PR's or the ticket's timing record and the Log. Read a sample of the verdicts:

```bash
# VM
pg -c "SELECT decision, round(confidence, 2) AS confidence, reason FROM app.adjudication
  WHERE prompt_version = 'adjudicate_v1' ORDER BY decided_at DESC LIMIT 20;"
```

**Expected:** reasons that cite the records (names, places, employers), not boilerplate.

## 4. Ask about the rest

```bash
# VM
docker exec "$PIPE" fundlens adjudicate; echo "exit=$?"
```

**Expected:** `exit=0`, `50 already decided` in the first line, and batch lines for the rest. A run cut
short (a redeploy, a failed batch) keeps every batch it wrote: run it again.

## 5. Apply the verdicts

```bash
# VM
docker exec "$PIPE" fundlens resolve --full; echo "exit=$?"
```

It trains again on the same silver with the same seed, so its clusters before adjudication are the ones
`adjudicate` chose from, and each verdict finds its candidate by fingerprint. A verdict whose two sides
no longer exist as they were (a key more or fewer on either) is not applied; the next `adjudicate` asks
about the new sides. So when a merged donor gains a key, the crosswalk parts the two again (the smaller
half under a new `donor_id`, the old one redirected) until `adjudicate` and another `resolve --full` run:
adjudicate after every resolve that adds keys.

**Expected:** `exit=0` and an `adjudications: <v> verdicts: <a> merges joining <j> clusters into others,
<s> splits` line, `v` the confident verdicts this run's clusters still hold. Then load and publish each
cycle as [first-resolved-run.md](first-resolved-run.md) does, so gold carries the new donors.

## Log

<!-- Append entries below; never rewrite one. -->
