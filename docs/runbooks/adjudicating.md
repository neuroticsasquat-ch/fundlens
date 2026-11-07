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

### 2026-11-04 — First adjudication run, 2024 (NEU-2055)

Model `deepseek-ai/DeepSeek-V4-Flash`, prompt `adjudicate_v1`, minimum $50,000.

```text
candidates: 7149 clusters, 112865 pairs of at least $50000; 0 already decided by deepseek-ai/DeepSeek-V4-Flash adjudicate_v1
chosen: 8176
limit50.txt:batch 1: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 17899 in, 809 out; cost $0.0017; latency p50 3.15 s, p95 3.82 s; wall 3.86 s
limit50.txt:batch 2: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13952 in, 703 out; cost $0.0012; latency p50 3.04 s, p95 3.74 s; wall 3.75 s
limit50.txt:batch 3: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13035 in, 706 out; cost $0.0011; latency p50 2.86 s, p95 4.05 s; wall 4.11 s
limit50.txt:batch 4: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11841 in, 709 out; cost $0.0010; latency p50 3.31 s, p95 4.78 s; wall 5.08 s
limit50.txt:batch 5: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 18111 in, 711 out; cost $0.0013; latency p50 2.88 s, p95 4.94 s; wall 5.46 s
limit50.txt:recorded: 38 merge, 12 split
rest.txt:batch 1: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13415 in, 815 out; cost $0.0013; latency p50 3.85 s, p95 4.80 s; wall 4.98 s
rest.txt:batch 2: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 15350 in, 728 out; cost $0.0013; latency p50 3.33 s, p95 12.17 s; wall 12.29 s
rest.txt:batch 3: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13009 in, 762 out; cost $0.0011; latency p50 3.25 s, p95 4.06 s; wall 4.15 s
rest.txt:batch 4: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13925 in, 724 out; cost $0.0012; latency p50 5.93 s, p95 6.12 s; wall 6.13 s
rest.txt:batch 5: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 14163 in, 806 out; cost $0.0012; latency p50 3.67 s, p95 5.87 s; wall 6.49 s
rest.txt:batch 6: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9985 in, 728 out; cost $0.0008; latency p50 3.21 s, p95 5.15 s; wall 5.49 s
rest.txt:batch 7: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10715 in, 711 out; cost $0.0009; latency p50 3.12 s, p95 8.36 s; wall 8.36 s
rest.txt:batch 8: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 12488 in, 711 out; cost $0.0011; latency p50 2.84 s, p95 3.68 s; wall 4.19 s
rest.txt:batch 9: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11582 in, 771 out; cost $0.0009; latency p50 3.95 s, p95 4.49 s; wall 4.64 s
rest.txt:batch 10: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13761 in, 833 out; cost $0.0012; latency p50 2.81 s, p95 5.44 s; wall 5.73 s
rest.txt:batch 11: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11778 in, 710 out; cost $0.0010; latency p50 3.22 s, p95 5.98 s; wall 6.07 s
rest.txt:batch 12: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13160 in, 724 out; cost $0.0011; latency p50 2.56 s, p95 3.43 s; wall 3.56 s
rest.txt:batch 13: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13852 in, 797 out; cost $0.0012; latency p50 3.23 s, p95 4.14 s; wall 4.47 s
rest.txt:batch 14: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10692 in, 678 out; cost $0.0009; latency p50 4.95 s, p95 7.84 s; wall 8.11 s
rest.txt:batch 15: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 12674 in, 715 out; cost $0.0011; latency p50 3.74 s, p95 4.92 s; wall 5.01 s
rest.txt:batch 16: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 12308 in, 711 out; cost $0.0011; latency p50 2.70 s, p95 4.11 s; wall 4.57 s
rest.txt:batch 17: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10323 in, 730 out; cost $0.0009; latency p50 2.78 s, p95 3.52 s; wall 3.56 s
rest.txt:batch 18: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13877 in, 722 out; cost $0.0012; latency p50 3.56 s, p95 4.33 s; wall 4.52 s
rest.txt:batch 19: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 12568 in, 696 out; cost $0.0011; latency p50 3.62 s, p95 4.86 s; wall 5.43 s
rest.txt:batch 20: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11950 in, 640 out; cost $0.0009; latency p50 2.89 s, p95 3.73 s; wall 3.79 s
rest.txt:batch 21: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 12869 in, 790 out; cost $0.0011; latency p50 2.99 s, p95 3.90 s; wall 4.22 s
rest.txt:batch 22: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10100 in, 652 out; cost $0.0008; latency p50 3.87 s, p95 4.16 s; wall 4.17 s
rest.txt:batch 23: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11887 in, 747 out; cost $0.0010; latency p50 4.25 s, p95 6.01 s; wall 6.50 s
rest.txt:batch 24: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13594 in, 800 out; cost $0.0012; latency p50 4.75 s, p95 6.61 s; wall 6.72 s
rest.txt:batch 25: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 12626 in, 798 out; cost $0.0011; latency p50 3.19 s, p95 4.49 s; wall 4.73 s
rest.txt:batch 26: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13859 in, 753 out; cost $0.0012; latency p50 3.42 s, p95 4.37 s; wall 4.38 s
rest.txt:batch 27: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10936 in, 699 out; cost $0.0009; latency p50 2.94 s, p95 3.34 s; wall 3.35 s
rest.txt:batch 28: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9655 in, 732 out; cost $0.0008; latency p50 3.20 s, p95 4.16 s; wall 4.35 s
rest.txt:batch 29: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10074 in, 736 out; cost $0.0009; latency p50 3.97 s, p95 4.34 s; wall 4.36 s
rest.txt:batch 30: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10593 in, 727 out; cost $0.0009; latency p50 2.65 s, p95 5.14 s; wall 6.44 s
rest.txt:batch 31: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10153 in, 738 out; cost $0.0009; latency p50 4.12 s, p95 5.07 s; wall 5.40 s
rest.txt:batch 32: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11116 in, 697 out; cost $0.0009; latency p50 3.04 s, p95 3.97 s; wall 4.62 s
rest.txt:batch 33: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8970 in, 744 out; cost $0.0007; latency p50 3.45 s, p95 4.86 s; wall 5.39 s
rest.txt:batch 34: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9520 in, 716 out; cost $0.0008; latency p50 4.10 s, p95 4.22 s; wall 4.29 s
rest.txt:batch 35: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9400 in, 668 out; cost $0.0008; latency p50 2.85 s, p95 5.30 s; wall 5.69 s
rest.txt:batch 36: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9500 in, 683 out; cost $0.0008; latency p50 2.94 s, p95 3.37 s; wall 3.47 s
rest.txt:batch 37: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11420 in, 715 out; cost $0.0010; latency p50 4.49 s, p95 5.33 s; wall 5.33 s
rest.txt:batch 38: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9802 in, 923 out; cost $0.0009; latency p50 3.06 s, p95 9.91 s; wall 10.59 s
rest.txt:batch 39: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 11122 in, 998 out; cost $0.0010; latency p50 3.45 s, p95 8.06 s; wall 9.48 s
rest.txt:batch 40: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9547 in, 774 out; cost $0.0008; latency p50 2.90 s, p95 3.77 s; wall 4.02 s
rest.txt:batch 41: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 13366 in, 1254 out; cost $0.0012; latency p50 5.57 s, p95 9.91 s; wall 10.26 s
rest.txt:batch 42: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9877 in, 726 out; cost $0.0008; latency p50 3.69 s, p95 5.88 s; wall 6.18 s
rest.txt:batch 43: 10 requests, 3 recorded, 7 invalid, 0 failed; tokens 9881 in, 1212 out; cost $0.0009; latency p50 4.18 s, p95 10.10 s; wall 13.14 s
rest.txt:batch 44: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9232 in, 696 out; cost $0.0008; latency p50 2.96 s, p95 7.27 s; wall 8.88 s
rest.txt:batch 45: 10 requests, 3 recorded, 7 invalid, 0 failed; tokens 7002 in, 620 out; cost $0.0006; latency p50 2.63 s, p95 7.92 s; wall 8.62 s
rest.txt:batch 46: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 11284 in, 1136 out; cost $0.0009; latency p50 3.53 s, p95 9.93 s; wall 9.98 s
rest.txt:batch 47: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9864 in, 753 out; cost $0.0008; latency p50 3.70 s, p95 5.78 s; wall 6.08 s
rest.txt:batch 48: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 11286 in, 1088 out; cost $0.0010; latency p50 5.10 s, p95 9.78 s; wall 10.59 s
rest.txt:batch 49: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10877 in, 740 out; cost $0.0009; latency p50 3.91 s, p95 27.01 s; wall 28.83 s
rest.txt:batch 50: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 7465 in, 679 out; cost $0.0006; latency p50 19.20 s, p95 83.43 s; wall 126.91 s
rest.txt:batch 51: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7774 in, 637 out; cost $0.0006; latency p50 2.32 s, p95 3.54 s; wall 3.61 s
rest.txt:batch 52: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8544 in, 626 out; cost $0.0007; latency p50 2.60 s, p95 3.32 s; wall 3.41 s
rest.txt:batch 53: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9933 in, 814 out; cost $0.0009; latency p50 4.15 s, p95 7.16 s; wall 8.55 s
rest.txt:batch 54: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 11065 in, 688 out; cost $0.0009; latency p50 3.07 s, p95 5.14 s; wall 5.66 s
rest.txt:batch 55: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 10923 in, 687 out; cost $0.0009; latency p50 3.27 s, p95 6.33 s; wall 7.83 s
rest.txt:batch 56: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8173 in, 776 out; cost $0.0007; latency p50 5.13 s, p95 6.89 s; wall 7.16 s
rest.txt:batch 57: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 10080 in, 739 out; cost $0.0009; latency p50 3.26 s, p95 4.94 s; wall 5.32 s
rest.txt:batch 58: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10960 in, 707 out; cost $0.0009; latency p50 2.74 s, p95 3.40 s; wall 3.41 s
rest.txt:batch 59: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9203 in, 684 out; cost $0.0008; latency p50 2.77 s, p95 4.55 s; wall 4.80 s
rest.txt:batch 60: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 9122 in, 758 out; cost $0.0008; latency p50 2.81 s, p95 5.30 s; wall 5.76 s
rest.txt:batch 61: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9622 in, 850 out; cost $0.0008; latency p50 3.36 s, p95 5.68 s; wall 7.07 s
rest.txt:batch 62: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 10055 in, 595 out; cost $0.0008; latency p50 2.91 s, p95 3.91 s; wall 4.51 s
rest.txt:batch 63: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8116 in, 690 out; cost $0.0007; latency p50 5.50 s, p95 5.86 s; wall 6.08 s
rest.txt:batch 64: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 10100 in, 838 out; cost $0.0009; latency p50 3.51 s, p95 6.40 s; wall 6.96 s
rest.txt:batch 65: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10150 in, 678 out; cost $0.0009; latency p50 3.10 s, p95 4.76 s; wall 4.79 s
rest.txt:batch 66: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11710 in, 748 out; cost $0.0010; latency p50 2.41 s, p95 3.19 s; wall 3.58 s
rest.txt:batch 67: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 10415 in, 869 out; cost $0.0009; latency p50 3.88 s, p95 6.15 s; wall 7.21 s
rest.txt:batch 68: 10 requests, 2 recorded, 8 invalid, 0 failed; tokens 9171 in, 925 out; cost $0.0008; latency p50 4.44 s, p95 8.60 s; wall 8.61 s
rest.txt:batch 69: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 9559 in, 891 out; cost $0.0008; latency p50 3.02 s, p95 8.30 s; wall 9.50 s
rest.txt:batch 70: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8411 in, 793 out; cost $0.0007; latency p50 4.19 s, p95 6.13 s; wall 6.20 s
rest.txt:batch 71: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 10158 in, 1182 out; cost $0.0009; latency p50 6.04 s, p95 8.09 s; wall 8.50 s
rest.txt:batch 72: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 11011 in, 1038 out; cost $0.0010; latency p50 5.65 s, p95 8.48 s; wall 8.76 s
rest.txt:batch 73: 10 requests, 1 recorded, 9 invalid, 0 failed; tokens 8602 in, 1146 out; cost $0.0008; latency p50 4.48 s, p95 7.78 s; wall 8.39 s
rest.txt:batch 74: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8736 in, 683 out; cost $0.0007; latency p50 11.58 s, p95 14.24 s; wall 14.30 s
rest.txt:batch 75: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9852 in, 682 out; cost $0.0008; latency p50 2.55 s, p95 4.63 s; wall 4.88 s
rest.txt:batch 76: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7260 in, 678 out; cost $0.0006; latency p50 2.39 s, p95 6.73 s; wall 8.37 s
rest.txt:batch 77: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10955 in, 793 out; cost $0.0009; latency p50 2.80 s, p95 4.01 s; wall 4.34 s
rest.txt:batch 78: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9184 in, 696 out; cost $0.0008; latency p50 2.52 s, p95 2.76 s; wall 2.78 s
rest.txt:batch 79: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 6973 in, 887 out; cost $0.0006; latency p50 2.58 s, p95 9.56 s; wall 9.89 s
rest.txt:batch 80: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7937 in, 709 out; cost $0.0007; latency p50 3.27 s, p95 4.55 s; wall 4.59 s
rest.txt:batch 81: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 9086 in, 1073 out; cost $0.0008; latency p50 3.83 s, p95 8.56 s; wall 8.63 s
rest.txt:batch 82: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 9787 in, 594 out; cost $0.0008; latency p50 2.90 s, p95 8.62 s; wall 9.69 s
rest.txt:batch 83: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8536 in, 695 out; cost $0.0007; latency p50 3.54 s, p95 4.93 s; wall 5.27 s
rest.txt:batch 84: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8437 in, 611 out; cost $0.0007; latency p50 3.56 s, p95 4.54 s; wall 4.69 s
rest.txt:batch 85: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 9220 in, 1286 out; cost $0.0009; latency p50 7.97 s, p95 10.76 s; wall 11.65 s
rest.txt:batch 86: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 9871 in, 921 out; cost $0.0009; latency p50 3.61 s, p95 8.95 s; wall 10.32 s
rest.txt:batch 87: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 9203 in, 999 out; cost $0.0008; latency p50 6.17 s, p95 9.41 s; wall 10.16 s
rest.txt:batch 88: 10 requests, 2 recorded, 8 invalid, 0 failed; tokens 12158 in, 911 out; cost $0.0011; latency p50 3.18 s, p95 6.13 s; wall 7.06 s
rest.txt:batch 89: 10 requests, 2 recorded, 8 invalid, 0 failed; tokens 8632 in, 1675 out; cost $0.0009; latency p50 6.52 s, p95 7.96 s; wall 8.49 s
rest.txt:batch 90: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8886 in, 1246 out; cost $0.0008; latency p50 3.92 s, p95 8.31 s; wall 9.31 s
rest.txt:batch 91: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9074 in, 844 out; cost $0.0008; latency p50 3.63 s, p95 6.21 s; wall 7.76 s
rest.txt:batch 92: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9204 in, 730 out; cost $0.0008; latency p50 3.40 s, p95 5.67 s; wall 6.37 s
rest.txt:batch 93: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 9716 in, 936 out; cost $0.0008; latency p50 3.12 s, p95 6.53 s; wall 7.45 s
rest.txt:batch 94: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11836 in, 645 out; cost $0.0007; latency p50 2.71 s, p95 3.96 s; wall 3.96 s
rest.txt:batch 95: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 12108 in, 602 out; cost $0.0006; latency p50 1.44 s, p95 3.36 s; wall 3.44 s
rest.txt:batch 96: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11947 in, 582 out; cost $0.0004; latency p50 2.24 s, p95 3.62 s; wall 3.93 s
rest.txt:batch 97: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11925 in, 649 out; cost $0.0006; latency p50 3.26 s, p95 3.62 s; wall 3.68 s
rest.txt:batch 98: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 9733 in, 1052 out; cost $0.0008; latency p50 4.20 s, p95 7.41 s; wall 7.52 s
rest.txt:batch 99: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9550 in, 644 out; cost $0.0007; latency p50 4.25 s, p95 7.59 s; wall 7.59 s
rest.txt:batch 100: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9586 in, 636 out; cost $0.0008; latency p50 3.32 s, p95 4.27 s; wall 4.40 s
rest.txt:batch 101: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8824 in, 687 out; cost $0.0007; latency p50 2.33 s, p95 6.33 s; wall 8.72 s
rest.txt:batch 102: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7841 in, 670 out; cost $0.0006; latency p50 2.80 s, p95 3.59 s; wall 3.64 s
rest.txt:batch 103: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 9050 in, 1077 out; cost $0.0008; latency p50 4.67 s, p95 12.10 s; wall 12.91 s
rest.txt:batch 104: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 11141 in, 590 out; cost $0.0009; latency p50 3.61 s, p95 7.49 s; wall 8.17 s
rest.txt:batch 105: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10728 in, 705 out; cost $0.0009; latency p50 3.23 s, p95 4.73 s; wall 5.05 s
rest.txt:batch 106: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 10125 in, 1012 out; cost $0.0009; latency p50 4.64 s, p95 7.75 s; wall 9.18 s
rest.txt:batch 107: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7990 in, 694 out; cost $0.0007; latency p50 2.89 s, p95 4.49 s; wall 5.57 s
rest.txt:batch 108: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8526 in, 723 out; cost $0.0007; latency p50 3.06 s, p95 75.63 s; wall 132.72 s
rest.txt:batch 109: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9769 in, 718 out; cost $0.0008; latency p50 2.53 s, p95 4.17 s; wall 4.25 s
rest.txt:batch 110: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 9215 in, 771 out; cost $0.0008; latency p50 3.97 s, p95 8.68 s; wall 10.51 s
rest.txt:batch 111: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8392 in, 971 out; cost $0.0007; latency p50 3.61 s, p95 7.46 s; wall 8.47 s
rest.txt:batch 112: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8367 in, 752 out; cost $0.0007; latency p50 4.49 s, p95 5.16 s; wall 5.23 s
rest.txt:batch 113: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9195 in, 725 out; cost $0.0008; latency p50 3.54 s, p95 5.15 s; wall 5.41 s
rest.txt:batch 114: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7410 in, 648 out; cost $0.0006; latency p50 3.85 s, p95 4.70 s; wall 4.88 s
rest.txt:batch 115: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 10464 in, 822 out; cost $0.0009; latency p50 4.17 s, p95 7.65 s; wall 7.87 s
rest.txt:batch 116: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8169 in, 483 out; cost $0.0006; latency p50 4.70 s, p95 5.86 s; wall 6.48 s
rest.txt:batch 117: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8339 in, 732 out; cost $0.0007; latency p50 4.45 s, p95 6.36 s; wall 6.51 s
rest.txt:batch 118: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8997 in, 715 out; cost $0.0008; latency p50 5.04 s, p95 74.48 s; wall 127.47 s
rest.txt:batch 119: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8168 in, 725 out; cost $0.0007; latency p50 3.97 s, p95 6.01 s; wall 6.34 s
rest.txt:batch 120: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7720 in, 697 out; cost $0.0006; latency p50 3.82 s, p95 5.02 s; wall 5.23 s
rest.txt:batch 121: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 12114 in, 779 out; cost $0.0010; latency p50 3.77 s, p95 7.26 s; wall 9.02 s
rest.txt:batch 122: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10437 in, 737 out; cost $0.0009; latency p50 3.26 s, p95 3.93 s; wall 4.04 s
rest.txt:batch 123: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9087 in, 846 out; cost $0.0008; latency p50 5.19 s, p95 8.78 s; wall 10.53 s
rest.txt:batch 124: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8158 in, 618 out; cost $0.0007; latency p50 3.09 s, p95 5.46 s; wall 5.80 s
rest.txt:batch 125: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 11143 in, 736 out; cost $0.0010; latency p50 4.01 s, p95 5.65 s; wall 5.73 s
rest.txt:batch 126: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9098 in, 654 out; cost $0.0008; latency p50 3.72 s, p95 4.39 s; wall 4.41 s
rest.txt:batch 127: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8476 in, 1084 out; cost $0.0008; latency p50 4.98 s, p95 9.99 s; wall 10.59 s
rest.txt:batch 128: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8228 in, 838 out; cost $0.0007; latency p50 3.72 s, p95 5.81 s; wall 6.52 s
rest.txt:batch 129: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9229 in, 723 out; cost $0.0008; latency p50 3.83 s, p95 5.61 s; wall 5.78 s
rest.txt:batch 130: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10425 in, 725 out; cost $0.0009; latency p50 3.47 s, p95 6.18 s; wall 6.70 s
rest.txt:batch 131: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9140 in, 749 out; cost $0.0008; latency p50 4.43 s, p95 6.34 s; wall 6.60 s
rest.txt:batch 132: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7682 in, 730 out; cost $0.0006; latency p50 4.00 s, p95 4.35 s; wall 4.43 s
rest.txt:batch 133: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9041 in, 707 out; cost $0.0008; latency p50 2.87 s, p95 5.40 s; wall 5.65 s
rest.txt:batch 134: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 11139 in, 546 out; cost $0.0009; latency p50 3.06 s, p95 4.27 s; wall 4.44 s
rest.txt:batch 135: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8671 in, 626 out; cost $0.0007; latency p50 3.70 s, p95 4.27 s; wall 4.36 s
rest.txt:batch 136: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9033 in, 702 out; cost $0.0008; latency p50 3.84 s, p95 4.73 s; wall 4.92 s
rest.txt:batch 137: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8024 in, 723 out; cost $0.0007; latency p50 3.30 s, p95 5.19 s; wall 5.63 s
rest.txt:batch 138: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8412 in, 899 out; cost $0.0007; latency p50 4.74 s, p95 9.89 s; wall 10.71 s
rest.txt:batch 139: 10 requests, 3 recorded, 7 invalid, 0 failed; tokens 9581 in, 1000 out; cost $0.0009; latency p50 4.50 s, p95 6.93 s; wall 7.70 s
rest.txt:batch 140: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9492 in, 989 out; cost $0.0008; latency p50 3.70 s, p95 9.94 s; wall 10.61 s
rest.txt:batch 141: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8160 in, 669 out; cost $0.0007; latency p50 4.45 s, p95 5.30 s; wall 5.46 s
rest.txt:batch 142: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 9293 in, 1235 out; cost $0.0008; latency p50 5.65 s, p95 10.24 s; wall 12.72 s
rest.txt:batch 143: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 9156 in, 664 out; cost $0.0008; latency p50 4.62 s, p95 11.18 s; wall 12.16 s
rest.txt:batch 144: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8713 in, 601 out; cost $0.0007; latency p50 3.44 s, p95 4.40 s; wall 4.45 s
rest.txt:batch 145: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8721 in, 703 out; cost $0.0007; latency p50 3.61 s, p95 4.56 s; wall 4.65 s
rest.txt:batch 146: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8547 in, 780 out; cost $0.0007; latency p50 3.61 s, p95 7.64 s; wall 10.12 s
rest.txt:batch 147: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7523 in, 841 out; cost $0.0006; latency p50 4.52 s, p95 7.61 s; wall 8.85 s
rest.txt:batch 148: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8522 in, 977 out; cost $0.0008; latency p50 3.93 s, p95 9.33 s; wall 9.94 s
rest.txt:batch 149: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8120 in, 736 out; cost $0.0007; latency p50 3.57 s, p95 8.20 s; wall 10.05 s
rest.txt:batch 150: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9810 in, 985 out; cost $0.0009; latency p50 3.84 s, p95 7.67 s; wall 9.22 s
rest.txt:batch 151: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8848 in, 751 out; cost $0.0007; latency p50 4.36 s, p95 4.91 s; wall 4.94 s
rest.txt:batch 152: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7449 in, 685 out; cost $0.0006; latency p50 4.10 s, p95 5.48 s; wall 6.00 s
rest.txt:batch 153: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8045 in, 724 out; cost $0.0007; latency p50 3.31 s, p95 4.64 s; wall 5.13 s
rest.txt:batch 154: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10039 in, 630 out; cost $0.0008; latency p50 3.47 s, p95 4.81 s; wall 5.01 s
rest.txt:batch 155: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 13979 in, 743 out; cost $0.0008; latency p50 4.03 s, p95 5.18 s; wall 5.38 s
rest.txt:batch 156: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9186 in, 669 out; cost $0.0008; latency p50 3.00 s, p95 4.60 s; wall 4.71 s
rest.txt:batch 157: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9091 in, 707 out; cost $0.0008; latency p50 4.23 s, p95 5.53 s; wall 6.19 s
rest.txt:batch 158: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8448 in, 684 out; cost $0.0007; latency p50 3.45 s, p95 3.87 s; wall 3.95 s
rest.txt:batch 159: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7790 in, 698 out; cost $0.0006; latency p50 5.12 s, p95 8.36 s; wall 9.67 s
rest.txt:batch 160: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9011 in, 643 out; cost $0.0007; latency p50 4.57 s, p95 5.73 s; wall 6.05 s
rest.txt:batch 161: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7655 in, 759 out; cost $0.0006; latency p50 5.02 s, p95 9.49 s; wall 9.97 s
rest.txt:batch 162: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8360 in, 677 out; cost $0.0007; latency p50 3.81 s, p95 4.60 s; wall 4.79 s
rest.txt:batch 163: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7022 in, 718 out; cost $0.0006; latency p50 3.23 s, p95 6.05 s; wall 6.43 s
rest.txt:batch 164: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8583 in, 779 out; cost $0.0007; latency p50 4.16 s, p95 8.37 s; wall 10.96 s
rest.txt:batch 165: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 11320 in, 729 out; cost $0.0010; latency p50 3.82 s, p95 6.36 s; wall 6.65 s
rest.txt:batch 166: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8739 in, 680 out; cost $0.0007; latency p50 4.42 s, p95 6.13 s; wall 6.66 s
rest.txt:batch 167: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7911 in, 653 out; cost $0.0006; latency p50 4.49 s, p95 5.51 s; wall 5.76 s
rest.txt:batch 168: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9277 in, 797 out; cost $0.0008; latency p50 4.07 s, p95 6.05 s; wall 6.80 s
rest.txt:batch 169: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 9091 in, 714 out; cost $0.0008; latency p50 2.80 s, p95 6.45 s; wall 8.21 s
rest.txt:batch 170: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8386 in, 882 out; cost $0.0007; latency p50 4.01 s, p95 8.34 s; wall 10.01 s
rest.txt:batch 171: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9545 in, 611 out; cost $0.0008; latency p50 3.91 s, p95 4.76 s; wall 5.10 s
rest.txt:batch 172: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10004 in, 664 out; cost $0.0008; latency p50 3.56 s, p95 4.34 s; wall 4.63 s
rest.txt:batch 173: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8558 in, 736 out; cost $0.0007; latency p50 5.34 s, p95 7.19 s; wall 7.21 s
rest.txt:batch 174: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10234 in, 728 out; cost $0.0009; latency p50 3.62 s, p95 4.35 s; wall 4.68 s
rest.txt:batch 175: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8346 in, 718 out; cost $0.0007; latency p50 3.99 s, p95 5.72 s; wall 6.23 s
rest.txt:batch 176: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9188 in, 707 out; cost $0.0008; latency p50 4.01 s, p95 5.74 s; wall 6.20 s
rest.txt:batch 177: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 11367 in, 698 out; cost $0.0009; latency p50 4.21 s, p95 5.54 s; wall 5.70 s
rest.txt:batch 178: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7889 in, 719 out; cost $0.0006; latency p50 4.06 s, p95 5.99 s; wall 6.85 s
rest.txt:batch 179: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8883 in, 819 out; cost $0.0008; latency p50 4.16 s, p95 9.19 s; wall 9.96 s
rest.txt:batch 180: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7973 in, 774 out; cost $0.0007; latency p50 3.37 s, p95 4.76 s; wall 5.20 s
rest.txt:batch 181: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6965 in, 627 out; cost $0.0006; latency p50 3.49 s, p95 5.34 s; wall 5.72 s
rest.txt:batch 182: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9363 in, 632 out; cost $0.0008; latency p50 3.52 s, p95 5.64 s; wall 5.94 s
rest.txt:batch 183: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8365 in, 926 out; cost $0.0007; latency p50 3.16 s, p95 9.36 s; wall 10.08 s
rest.txt:batch 184: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9069 in, 765 out; cost $0.0008; latency p50 4.24 s, p95 5.45 s; wall 5.55 s
rest.txt:batch 185: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 10066 in, 1073 out; cost $0.0009; latency p50 7.02 s, p95 9.44 s; wall 9.93 s
rest.txt:batch 186: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 9468 in, 1069 out; cost $0.0009; latency p50 4.51 s, p95 11.11 s; wall 11.17 s
rest.txt:batch 187: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9446 in, 673 out; cost $0.0008; latency p50 3.12 s, p95 4.08 s; wall 4.57 s
rest.txt:batch 188: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7313 in, 648 out; cost $0.0006; latency p50 3.34 s, p95 4.83 s; wall 5.28 s
rest.txt:batch 189: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8944 in, 679 out; cost $0.0007; latency p50 4.06 s, p95 5.41 s; wall 6.01 s
rest.txt:batch 190: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 7969 in, 483 out; cost $0.0006; latency p50 3.38 s, p95 5.25 s; wall 5.55 s
rest.txt:batch 191: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 9172 in, 391 out; cost $0.0007; latency p50 2.16 s, p95 4.14 s; wall 4.21 s
rest.txt:batch 192: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8859 in, 694 out; cost $0.0007; latency p50 3.79 s, p95 5.71 s; wall 5.84 s
rest.txt:batch 193: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7527 in, 689 out; cost $0.0006; latency p50 3.80 s, p95 4.59 s; wall 4.92 s
rest.txt:batch 194: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8280 in, 700 out; cost $0.0007; latency p50 3.75 s, p95 4.96 s; wall 5.19 s
rest.txt:batch 195: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7002 in, 660 out; cost $0.0006; latency p50 2.95 s, p95 4.43 s; wall 4.96 s
rest.txt:batch 196: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 7946 in, 1080 out; cost $0.0007; latency p50 4.63 s, p95 9.42 s; wall 11.52 s
rest.txt:batch 197: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8348 in, 812 out; cost $0.0007; latency p50 4.27 s, p95 22.94 s; wall 37.11 s
rest.txt:batch 198: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 6088 in, 838 out; cost $0.0005; latency p50 3.13 s, p95 8.00 s; wall 8.97 s
rest.txt:batch 199: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9045 in, 904 out; cost $0.0008; latency p50 4.44 s, p95 9.48 s; wall 9.67 s
rest.txt:batch 200: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8077 in, 689 out; cost $0.0007; latency p50 3.94 s, p95 6.43 s; wall 8.10 s
rest.txt:batch 201: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8738 in, 708 out; cost $0.0007; latency p50 3.72 s, p95 5.16 s; wall 5.21 s
rest.txt:batch 202: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9024 in, 712 out; cost $0.0008; latency p50 4.34 s, p95 6.43 s; wall 6.72 s
rest.txt:batch 203: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8424 in, 990 out; cost $0.0008; latency p50 3.83 s, p95 9.08 s; wall 9.52 s
rest.txt:batch 204: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9029 in, 729 out; cost $0.0008; latency p50 2.86 s, p95 4.74 s; wall 5.74 s
rest.txt:batch 205: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9654 in, 695 out; cost $0.0008; latency p50 3.41 s, p95 5.71 s; wall 6.30 s
rest.txt:batch 206: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 9112 in, 686 out; cost $0.0008; latency p50 3.01 s, p95 5.03 s; wall 5.55 s
rest.txt:batch 207: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8628 in, 634 out; cost $0.0007; latency p50 3.08 s, p95 3.51 s; wall 3.53 s
rest.txt:batch 208: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7100 in, 688 out; cost $0.0006; latency p50 3.10 s, p95 3.91 s; wall 4.05 s
rest.txt:batch 209: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8466 in, 863 out; cost $0.0007; latency p50 3.40 s, p95 6.68 s; wall 7.63 s
rest.txt:batch 210: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8708 in, 762 out; cost $0.0007; latency p50 3.70 s, p95 7.02 s; wall 9.28 s
rest.txt:batch 211: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 9074 in, 1236 out; cost $0.0008; latency p50 4.38 s, p95 7.74 s; wall 8.43 s
rest.txt:batch 212: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8506 in, 794 out; cost $0.0007; latency p50 2.84 s, p95 5.52 s; wall 5.98 s
rest.txt:batch 213: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7349 in, 707 out; cost $0.0006; latency p50 3.50 s, p95 5.76 s; wall 5.89 s
rest.txt:batch 214: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8921 in, 695 out; cost $0.0007; latency p50 4.00 s, p95 6.28 s; wall 7.38 s
rest.txt:batch 215: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7106 in, 626 out; cost $0.0006; latency p50 2.98 s, p95 4.02 s; wall 4.13 s
rest.txt:batch 216: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7762 in, 687 out; cost $0.0006; latency p50 3.01 s, p95 4.07 s; wall 4.20 s
rest.txt:batch 217: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 10009 in, 764 out; cost $0.0009; latency p50 3.78 s, p95 4.42 s; wall 4.60 s
rest.txt:batch 218: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8528 in, 806 out; cost $0.0007; latency p50 3.52 s, p95 6.14 s; wall 7.34 s
rest.txt:batch 219: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8985 in, 626 out; cost $0.0007; latency p50 4.76 s, p95 6.28 s; wall 6.76 s
rest.txt:batch 220: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8612 in, 935 out; cost $0.0008; latency p50 4.59 s, p95 9.06 s; wall 11.28 s
rest.txt:batch 221: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10481 in, 654 out; cost $0.0007; latency p50 4.05 s, p95 5.13 s; wall 5.36 s
rest.txt:batch 222: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 9707 in, 922 out; cost $0.0007; latency p50 4.16 s, p95 7.18 s; wall 7.37 s
rest.txt:batch 223: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10034 in, 639 out; cost $0.0006; latency p50 3.91 s, p95 5.76 s; wall 5.88 s
rest.txt:batch 224: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 10314 in, 913 out; cost $0.0009; latency p50 3.35 s, p95 7.30 s; wall 7.63 s
rest.txt:batch 225: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8277 in, 758 out; cost $0.0006; latency p50 3.84 s, p95 6.81 s; wall 7.42 s
rest.txt:batch 226: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8028 in, 685 out; cost $0.0006; latency p50 3.47 s, p95 4.46 s; wall 4.76 s
rest.txt:batch 227: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8147 in, 726 out; cost $0.0007; latency p50 3.16 s, p95 4.13 s; wall 4.29 s
rest.txt:batch 228: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6760 in, 689 out; cost $0.0005; latency p50 3.01 s, p95 4.70 s; wall 5.42 s
rest.txt:batch 229: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8186 in, 707 out; cost $0.0007; latency p50 3.40 s, p95 4.70 s; wall 4.71 s
rest.txt:batch 230: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7073 in, 747 out; cost $0.0006; latency p50 3.48 s, p95 5.30 s; wall 6.28 s
rest.txt:batch 231: 10 requests, 2 recorded, 8 invalid, 0 failed; tokens 7553 in, 1075 out; cost $0.0007; latency p50 5.53 s, p95 9.18 s; wall 10.64 s
rest.txt:batch 232: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7712 in, 789 out; cost $0.0007; latency p50 3.67 s, p95 6.13 s; wall 7.68 s
rest.txt:batch 233: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8274 in, 634 out; cost $0.0007; latency p50 2.79 s, p95 4.29 s; wall 4.44 s
rest.txt:batch 234: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8269 in, 909 out; cost $0.0007; latency p50 2.83 s, p95 8.02 s; wall 8.45 s
rest.txt:batch 235: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8765 in, 748 out; cost $0.0007; latency p50 3.94 s, p95 5.04 s; wall 5.34 s
rest.txt:batch 236: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8072 in, 1058 out; cost $0.0007; latency p50 4.34 s, p95 8.52 s; wall 8.71 s
rest.txt:batch 237: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 9685 in, 600 out; cost $0.0008; latency p50 3.66 s, p95 4.17 s; wall 4.19 s
rest.txt:batch 238: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8260 in, 934 out; cost $0.0007; latency p50 3.26 s, p95 7.88 s; wall 10.47 s
rest.txt:batch 239: 10 requests, 3 recorded, 7 invalid, 0 failed; tokens 8721 in, 1370 out; cost $0.0008; latency p50 4.27 s, p95 7.69 s; wall 8.30 s
rest.txt:batch 240: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 8874 in, 1143 out; cost $0.0008; latency p50 4.15 s, p95 8.44 s; wall 8.78 s
rest.txt:batch 241: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 7364 in, 1008 out; cost $0.0007; latency p50 3.76 s, p95 6.11 s; wall 6.28 s
rest.txt:batch 242: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 6433 in, 1030 out; cost $0.0006; latency p50 4.32 s, p95 6.31 s; wall 6.66 s
rest.txt:batch 243: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7565 in, 779 out; cost $0.0006; latency p50 3.70 s, p95 6.67 s; wall 7.87 s
rest.txt:batch 244: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8936 in, 709 out; cost $0.0007; latency p50 3.07 s, p95 3.72 s; wall 4.04 s
rest.txt:batch 245: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8875 in, 809 out; cost $0.0008; latency p50 3.43 s, p95 5.81 s; wall 7.04 s
rest.txt:batch 246: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 9821 in, 978 out; cost $0.0009; latency p50 3.84 s, p95 6.80 s; wall 6.82 s
rest.txt:batch 247: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7450 in, 647 out; cost $0.0006; latency p50 3.84 s, p95 4.84 s; wall 5.19 s
rest.txt:batch 248: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8436 in, 756 out; cost $0.0007; latency p50 4.33 s, p95 5.04 s; wall 5.35 s
rest.txt:batch 249: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8714 in, 929 out; cost $0.0008; latency p50 3.99 s, p95 7.88 s; wall 9.81 s
rest.txt:batch 250: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8730 in, 726 out; cost $0.0007; latency p50 3.93 s, p95 4.94 s; wall 5.03 s
rest.txt:batch 251: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9113 in, 780 out; cost $0.0008; latency p50 4.01 s, p95 5.30 s; wall 5.51 s
rest.txt:batch 252: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9897 in, 823 out; cost $0.0009; latency p50 5.73 s, p95 8.23 s; wall 9.18 s
rest.txt:batch 253: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7941 in, 831 out; cost $0.0007; latency p50 3.73 s, p95 7.05 s; wall 9.06 s
rest.txt:batch 254: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8900 in, 751 out; cost $0.0008; latency p50 3.31 s, p95 5.87 s; wall 6.64 s
rest.txt:batch 255: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8646 in, 764 out; cost $0.0007; latency p50 3.69 s, p95 6.75 s; wall 8.14 s
rest.txt:batch 256: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8373 in, 735 out; cost $0.0007; latency p50 3.69 s, p95 5.83 s; wall 5.87 s
rest.txt:batch 257: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8272 in, 624 out; cost $0.0007; latency p50 2.78 s, p95 73.82 s; wall 130.39 s
rest.txt:batch 258: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9285 in, 686 out; cost $0.0008; latency p50 4.34 s, p95 6.39 s; wall 7.36 s
rest.txt:batch 259: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8543 in, 795 out; cost $0.0007; latency p50 4.17 s, p95 6.46 s; wall 6.71 s
rest.txt:batch 260: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10640 in, 706 out; cost $0.0009; latency p50 3.82 s, p95 5.02 s; wall 5.44 s
rest.txt:batch 261: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8950 in, 656 out; cost $0.0007; latency p50 3.10 s, p95 3.53 s; wall 3.56 s
rest.txt:batch 262: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8854 in, 720 out; cost $0.0007; latency p50 4.41 s, p95 5.49 s; wall 5.82 s
rest.txt:batch 263: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 10582 in, 913 out; cost $0.0008; latency p50 4.65 s, p95 6.63 s; wall 7.74 s
rest.txt:batch 264: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10850 in, 744 out; cost $0.0008; latency p50 4.96 s, p95 6.03 s; wall 6.83 s
rest.txt:batch 265: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9307 in, 662 out; cost $0.0007; latency p50 3.01 s, p95 3.75 s; wall 3.77 s
rest.txt:batch 266: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8640 in, 675 out; cost $0.0006; latency p50 3.64 s, p95 4.63 s; wall 4.64 s
rest.txt:batch 267: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7560 in, 621 out; cost $0.0006; latency p50 3.47 s, p95 4.94 s; wall 5.28 s
rest.txt:batch 268: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7582 in, 675 out; cost $0.0006; latency p50 3.25 s, p95 4.02 s; wall 4.06 s
rest.txt:batch 269: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10174 in, 692 out; cost $0.0008; latency p50 3.72 s, p95 4.05 s; wall 4.17 s
rest.txt:batch 270: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8675 in, 747 out; cost $0.0007; latency p50 3.43 s, p95 4.62 s; wall 4.92 s
rest.txt:batch 271: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9567 in, 750 out; cost $0.0008; latency p50 3.37 s, p95 5.75 s; wall 6.39 s
rest.txt:batch 272: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8847 in, 693 out; cost $0.0007; latency p50 3.70 s, p95 4.31 s; wall 4.37 s
rest.txt:batch 273: 10 requests, 3 recorded, 7 invalid, 0 failed; tokens 7220 in, 850 out; cost $0.0006; latency p50 4.39 s, p95 6.22 s; wall 6.34 s
rest.txt:batch 274: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8541 in, 818 out; cost $0.0007; latency p50 4.23 s, p95 5.78 s; wall 6.49 s
rest.txt:batch 275: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7833 in, 623 out; cost $0.0006; latency p50 3.12 s, p95 4.66 s; wall 4.80 s
rest.txt:batch 276: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 6933 in, 593 out; cost $0.0005; latency p50 3.69 s, p95 5.00 s; wall 5.13 s
rest.txt:batch 277: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7510 in, 649 out; cost $0.0006; latency p50 3.73 s, p95 4.03 s; wall 4.09 s
rest.txt:batch 278: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7330 in, 698 out; cost $0.0006; latency p50 13.70 s, p95 14.64 s; wall 14.87 s
rest.txt:batch 279: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7718 in, 630 out; cost $0.0006; latency p50 4.21 s, p95 5.30 s; wall 5.48 s
rest.txt:batch 280: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9436 in, 714 out; cost $0.0008; latency p50 3.01 s, p95 5.38 s; wall 6.14 s
rest.txt:batch 281: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 7973 in, 981 out; cost $0.0007; latency p50 3.75 s, p95 7.13 s; wall 7.83 s
rest.txt:batch 282: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7128 in, 676 out; cost $0.0006; latency p50 4.31 s, p95 5.05 s; wall 5.40 s
rest.txt:batch 283: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9904 in, 656 out; cost $0.0006; latency p50 3.18 s, p95 3.64 s; wall 3.68 s
rest.txt:batch 284: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 9547 in, 601 out; cost $0.0007; latency p50 3.27 s, p95 5.92 s; wall 6.63 s
rest.txt:batch 285: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7860 in, 742 out; cost $0.0007; latency p50 3.81 s, p95 5.30 s; wall 5.34 s
rest.txt:batch 286: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8646 in, 764 out; cost $0.0007; latency p50 4.40 s, p95 7.56 s; wall 9.15 s
rest.txt:batch 287: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8556 in, 698 out; cost $0.0007; latency p50 4.67 s, p95 6.92 s; wall 8.06 s
rest.txt:batch 288: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8065 in, 903 out; cost $0.0007; latency p50 4.77 s, p95 6.58 s; wall 6.88 s
rest.txt:batch 289: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8450 in, 722 out; cost $0.0007; latency p50 4.38 s, p95 5.26 s; wall 5.65 s
rest.txt:batch 290: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8953 in, 729 out; cost $0.0008; latency p50 3.31 s, p95 4.46 s; wall 4.52 s
rest.txt:batch 291: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7833 in, 694 out; cost $0.0006; latency p50 2.72 s, p95 4.22 s; wall 4.89 s
rest.txt:batch 292: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7282 in, 735 out; cost $0.0006; latency p50 3.16 s, p95 4.45 s; wall 4.71 s
rest.txt:batch 293: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7787 in, 634 out; cost $0.0006; latency p50 3.49 s, p95 4.18 s; wall 4.43 s
rest.txt:batch 294: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10672 in, 689 out; cost $0.0009; latency p50 3.81 s, p95 5.19 s; wall 5.42 s
rest.txt:batch 295: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8291 in, 721 out; cost $0.0007; latency p50 3.36 s, p95 5.30 s; wall 5.80 s
rest.txt:batch 296: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7929 in, 769 out; cost $0.0007; latency p50 3.72 s, p95 5.38 s; wall 5.50 s
rest.txt:batch 297: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 7826 in, 851 out; cost $0.0007; latency p50 4.19 s, p95 6.58 s; wall 7.60 s
rest.txt:batch 298: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 7337 in, 653 out; cost $0.0006; latency p50 2.71 s, p95 7.33 s; wall 7.80 s
rest.txt:batch 299: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9786 in, 724 out; cost $0.0008; latency p50 4.54 s, p95 9.40 s; wall 9.45 s
rest.txt:batch 300: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8678 in, 718 out; cost $0.0007; latency p50 4.07 s, p95 5.37 s; wall 5.61 s
rest.txt:batch 301: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8408 in, 700 out; cost $0.0007; latency p50 3.77 s, p95 4.26 s; wall 4.42 s
rest.txt:batch 302: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 6643 in, 749 out; cost $0.0005; latency p50 3.66 s, p95 6.09 s; wall 7.90 s
rest.txt:batch 303: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9542 in, 686 out; cost $0.0008; latency p50 3.64 s, p95 3.85 s; wall 3.96 s
rest.txt:batch 304: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8013 in, 719 out; cost $0.0007; latency p50 4.15 s, p95 5.25 s; wall 5.89 s
rest.txt:batch 305: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10467 in, 680 out; cost $0.0009; latency p50 6.24 s, p95 7.05 s; wall 7.53 s
rest.txt:batch 306: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7365 in, 550 out; cost $0.0006; latency p50 4.06 s, p95 5.45 s; wall 5.46 s
rest.txt:batch 307: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7271 in, 739 out; cost $0.0006; latency p50 3.98 s, p95 7.29 s; wall 9.23 s
rest.txt:batch 308: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8529 in, 702 out; cost $0.0007; latency p50 2.84 s, p95 4.19 s; wall 4.47 s
rest.txt:batch 309: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8088 in, 694 out; cost $0.0007; latency p50 2.95 s, p95 4.64 s; wall 5.09 s
rest.txt:batch 310: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8449 in, 702 out; cost $0.0007; latency p50 3.08 s, p95 5.86 s; wall 6.63 s
rest.txt:batch 311: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7380 in, 628 out; cost $0.0006; latency p50 2.79 s, p95 5.23 s; wall 6.65 s
rest.txt:batch 312: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10231 in, 736 out; cost $0.0009; latency p50 3.77 s, p95 4.89 s; wall 5.24 s
rest.txt:batch 313: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7318 in, 554 out; cost $0.0006; latency p50 2.58 s, p95 3.85 s; wall 4.33 s
rest.txt:batch 314: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7248 in, 788 out; cost $0.0006; latency p50 3.39 s, p95 6.32 s; wall 8.45 s
rest.txt:batch 315: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 6959 in, 520 out; cost $0.0005; latency p50 2.64 s, p95 2.77 s; wall 2.79 s
rest.txt:batch 316: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7303 in, 631 out; cost $0.0006; latency p50 2.59 s, p95 3.66 s; wall 3.91 s
rest.txt:batch 317: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7759 in, 819 out; cost $0.0007; latency p50 4.71 s, p95 7.67 s; wall 8.89 s
rest.txt:batch 318: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7328 in, 692 out; cost $0.0006; latency p50 2.60 s, p95 4.09 s; wall 4.38 s
rest.txt:batch 319: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6885 in, 700 out; cost $0.0006; latency p50 3.63 s, p95 4.88 s; wall 4.91 s
rest.txt:batch 320: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 7420 in, 991 out; cost $0.0007; latency p50 5.29 s, p95 8.86 s; wall 9.08 s
rest.txt:batch 321: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8573 in, 721 out; cost $0.0007; latency p50 3.99 s, p95 5.61 s; wall 6.33 s
rest.txt:batch 322: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8607 in, 671 out; cost $0.0007; latency p50 3.07 s, p95 3.94 s; wall 3.97 s
rest.txt:batch 323: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8690 in, 694 out; cost $0.0007; latency p50 3.08 s, p95 3.78 s; wall 3.91 s
rest.txt:batch 324: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9106 in, 724 out; cost $0.0008; latency p50 2.73 s, p95 4.02 s; wall 4.07 s
rest.txt:batch 325: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8249 in, 697 out; cost $0.0007; latency p50 2.95 s, p95 7.41 s; wall 10.15 s
rest.txt:batch 326: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 8103 in, 722 out; cost $0.0007; latency p50 3.17 s, p95 5.45 s; wall 5.59 s
rest.txt:batch 327: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7427 in, 638 out; cost $0.0006; latency p50 3.09 s, p95 3.53 s; wall 3.78 s
rest.txt:batch 328: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 7812 in, 571 out; cost $0.0006; latency p50 2.39 s, p95 6.66 s; wall 8.20 s
rest.txt:batch 329: 10 requests, 3 recorded, 7 invalid, 0 failed; tokens 8505 in, 830 out; cost $0.0007; latency p50 3.64 s, p95 8.35 s; wall 8.62 s
rest.txt:batch 330: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8614 in, 686 out; cost $0.0007; latency p50 3.04 s, p95 3.94 s; wall 4.35 s
rest.txt:batch 331: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7074 in, 646 out; cost $0.0006; latency p50 2.37 s, p95 3.48 s; wall 3.67 s
rest.txt:batch 332: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6949 in, 705 out; cost $0.0005; latency p50 3.63 s, p95 4.93 s; wall 5.73 s
rest.txt:batch 333: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7838 in, 735 out; cost $0.0007; latency p50 3.67 s, p95 6.03 s; wall 6.35 s
rest.txt:batch 334: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 8681 in, 1197 out; cost $0.0008; latency p50 4.68 s, p95 7.25 s; wall 7.76 s
rest.txt:batch 335: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 7006 in, 743 out; cost $0.0006; latency p50 3.55 s, p95 5.88 s; wall 6.00 s
rest.txt:batch 336: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 9579 in, 672 out; cost $0.0008; latency p50 3.19 s, p95 5.96 s; wall 6.37 s
rest.txt:batch 337: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8057 in, 754 out; cost $0.0007; latency p50 3.52 s, p95 5.32 s; wall 5.56 s
rest.txt:batch 338: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7446 in, 758 out; cost $0.0006; latency p50 2.63 s, p95 8.78 s; wall 9.31 s
rest.txt:batch 339: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7080 in, 952 out; cost $0.0006; latency p50 2.94 s, p95 9.04 s; wall 13.61 s
rest.txt:batch 340: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7821 in, 725 out; cost $0.0007; latency p50 3.95 s, p95 4.64 s; wall 4.72 s
rest.txt:batch 341: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7482 in, 671 out; cost $0.0006; latency p50 3.23 s, p95 4.13 s; wall 4.68 s
rest.txt:batch 342: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 8254 in, 1154 out; cost $0.0008; latency p50 3.50 s, p95 11.95 s; wall 13.92 s
rest.txt:batch 343: 10 requests, 2 recorded, 8 invalid, 0 failed; tokens 8184 in, 1384 out; cost $0.0008; latency p50 8.97 s, p95 11.42 s; wall 11.58 s
rest.txt:batch 344: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8572 in, 725 out; cost $0.0007; latency p50 3.78 s, p95 6.16 s; wall 7.13 s
rest.txt:batch 345: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8976 in, 705 out; cost $0.0008; latency p50 3.75 s, p95 7.08 s; wall 8.36 s
rest.txt:batch 346: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 7987 in, 972 out; cost $0.0007; latency p50 4.60 s, p95 8.07 s; wall 8.38 s
rest.txt:batch 347: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8560 in, 653 out; cost $0.0007; latency p50 3.97 s, p95 4.40 s; wall 4.48 s
rest.txt:batch 348: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 6908 in, 473 out; cost $0.0005; latency p50 2.99 s, p95 3.72 s; wall 3.88 s
rest.txt:batch 349: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8479 in, 706 out; cost $0.0007; latency p50 2.44 s, p95 3.10 s; wall 3.17 s
rest.txt:batch 350: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 7597 in, 1021 out; cost $0.0007; latency p50 3.27 s, p95 7.66 s; wall 8.25 s
rest.txt:batch 351: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 8002 in, 507 out; cost $0.0006; latency p50 3.92 s, p95 5.39 s; wall 6.09 s
rest.txt:batch 352: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7057 in, 672 out; cost $0.0006; latency p50 4.98 s, p95 6.09 s; wall 6.23 s
rest.txt:batch 353: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7553 in, 652 out; cost $0.0006; latency p50 5.11 s, p95 6.45 s; wall 6.80 s
rest.txt:batch 354: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 8092 in, 763 out; cost $0.0007; latency p50 3.58 s, p95 5.29 s; wall 5.72 s
rest.txt:batch 355: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 10728 in, 939 out; cost $0.0010; latency p50 4.38 s, p95 6.79 s; wall 6.96 s
rest.txt:batch 356: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 7817 in, 1175 out; cost $0.0007; latency p50 5.21 s, p95 7.53 s; wall 7.81 s
rest.txt:batch 357: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7956 in, 794 out; cost $0.0007; latency p50 4.93 s, p95 6.44 s; wall 6.63 s
rest.txt:batch 358: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7180 in, 755 out; cost $0.0006; latency p50 4.56 s, p95 5.72 s; wall 5.84 s
rest.txt:batch 359: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7602 in, 645 out; cost $0.0006; latency p50 3.16 s, p95 4.50 s; wall 5.13 s
rest.txt:batch 360: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7424 in, 708 out; cost $0.0006; latency p50 3.69 s, p95 4.53 s; wall 4.56 s
rest.txt:batch 361: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7613 in, 699 out; cost $0.0006; latency p50 3.55 s, p95 5.23 s; wall 5.43 s
rest.txt:batch 362: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7092 in, 661 out; cost $0.0006; latency p50 3.74 s, p95 4.87 s; wall 4.88 s
rest.txt:batch 363: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6659 in, 666 out; cost $0.0005; latency p50 4.15 s, p95 5.87 s; wall 5.87 s
rest.txt:batch 364: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7428 in, 788 out; cost $0.0006; latency p50 3.76 s, p95 6.04 s; wall 7.19 s
rest.txt:batch 365: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 8109 in, 801 out; cost $0.0007; latency p50 4.22 s, p95 74.61 s; wall 129.40 s
rest.txt:batch 366: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7917 in, 769 out; cost $0.0007; latency p50 3.09 s, p95 4.65 s; wall 4.90 s
rest.txt:batch 367: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 8262 in, 812 out; cost $0.0007; latency p50 3.12 s, p95 6.02 s; wall 7.62 s
rest.txt:batch 368: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7809 in, 575 out; cost $0.0006; latency p50 2.58 s, p95 3.53 s; wall 3.67 s
rest.txt:batch 369: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7915 in, 682 out; cost $0.0007; latency p50 3.81 s, p95 4.90 s; wall 4.93 s
rest.txt:batch 370: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7162 in, 702 out; cost $0.0006; latency p50 3.54 s, p95 4.43 s; wall 4.74 s
rest.txt:batch 371: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7011 in, 648 out; cost $0.0006; latency p50 3.42 s, p95 4.75 s; wall 5.17 s
rest.txt:batch 372: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7137 in, 562 out; cost $0.0006; latency p50 4.31 s, p95 4.89 s; wall 4.93 s
rest.txt:batch 373: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 8422 in, 591 out; cost $0.0007; latency p50 4.39 s, p95 6.47 s; wall 6.80 s
rest.txt:batch 374: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8536 in, 669 out; cost $0.0007; latency p50 3.46 s, p95 5.16 s; wall 5.36 s
rest.txt:batch 375: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8302 in, 683 out; cost $0.0007; latency p50 3.07 s, p95 4.42 s; wall 4.87 s
rest.txt:batch 376: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8003 in, 722 out; cost $0.0007; latency p50 3.32 s, p95 3.94 s; wall 3.95 s
rest.txt:batch 377: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 7617 in, 897 out; cost $0.0007; latency p50 3.40 s, p95 8.22 s; wall 8.60 s
rest.txt:batch 378: 10 requests, 6 recorded, 4 invalid, 0 failed; tokens 7747 in, 703 out; cost $0.0006; latency p50 2.87 s, p95 6.02 s; wall 7.46 s
rest.txt:batch 379: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8100 in, 712 out; cost $0.0007; latency p50 3.19 s, p95 4.27 s; wall 4.47 s
rest.txt:batch 380: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7836 in, 717 out; cost $0.0006; latency p50 3.89 s, p95 10.56 s; wall 12.36 s
rest.txt:batch 381: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7567 in, 630 out; cost $0.0006; latency p50 4.18 s, p95 5.57 s; wall 5.66 s
rest.txt:batch 382: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7459 in, 768 out; cost $0.0006; latency p50 4.25 s, p95 8.85 s; wall 9.09 s
rest.txt:batch 383: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 6058 in, 471 out; cost $0.0004; latency p50 2.81 s, p95 3.78 s; wall 4.20 s
rest.txt:batch 384: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7123 in, 1041 out; cost $0.0006; latency p50 6.53 s, p95 10.51 s; wall 11.60 s
rest.txt:batch 385: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 7724 in, 903 out; cost $0.0007; latency p50 4.11 s, p95 10.61 s; wall 13.18 s
rest.txt:batch 386: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 6714 in, 1027 out; cost $0.0006; latency p50 4.41 s, p95 8.99 s; wall 9.17 s
rest.txt:batch 387: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9925 in, 735 out; cost $0.0008; latency p50 3.93 s, p95 4.65 s; wall 4.77 s
rest.txt:batch 388: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8351 in, 687 out; cost $0.0007; latency p50 4.70 s, p95 6.28 s; wall 6.59 s
rest.txt:batch 389: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6799 in, 653 out; cost $0.0005; latency p50 5.44 s, p95 7.14 s; wall 7.31 s
rest.txt:batch 390: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7466 in, 620 out; cost $0.0006; latency p50 3.83 s, p95 5.69 s; wall 5.77 s
rest.txt:batch 391: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 7417 in, 807 out; cost $0.0006; latency p50 3.65 s, p95 5.61 s; wall 6.80 s
rest.txt:batch 392: 10 requests, 5 recorded, 5 invalid, 0 failed; tokens 8091 in, 647 out; cost $0.0007; latency p50 3.90 s, p95 6.32 s; wall 6.74 s
rest.txt:batch 393: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7372 in, 588 out; cost $0.0006; latency p50 3.29 s, p95 22.54 s; wall 36.86 s
rest.txt:batch 394: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6565 in, 654 out; cost $0.0005; latency p50 4.81 s, p95 6.59 s; wall 6.67 s
rest.txt:batch 395: 10 requests, 9 recorded, 1 invalid, 0 failed; tokens 6682 in, 804 out; cost $0.0006; latency p50 3.69 s, p95 7.33 s; wall 9.38 s
rest.txt:batch 396: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 9209 in, 1030 out; cost $0.0008; latency p50 2.84 s, p95 7.20 s; wall 8.14 s
rest.txt:batch 397: 10 requests, 8 recorded, 2 invalid, 0 failed; tokens 7826 in, 1038 out; cost $0.0007; latency p50 2.84 s, p95 8.49 s; wall 10.65 s
rest.txt:batch 398: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8472 in, 755 out; cost $0.0007; latency p50 4.94 s, p95 6.39 s; wall 6.47 s
rest.txt:batch 399: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7642 in, 669 out; cost $0.0006; latency p50 3.83 s, p95 4.38 s; wall 4.64 s
rest.txt:batch 400: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8324 in, 700 out; cost $0.0007; latency p50 3.87 s, p95 4.59 s; wall 4.73 s
rest.txt:batch 401: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7785 in, 731 out; cost $0.0006; latency p50 5.99 s, p95 13.44 s; wall 13.52 s
rest.txt:batch 402: 10 requests, 4 recorded, 6 invalid, 0 failed; tokens 9290 in, 1114 out; cost $0.0009; latency p50 4.58 s, p95 7.13 s; wall 7.87 s
rest.txt:batch 403: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8090 in, 667 out; cost $0.0007; latency p50 5.48 s, p95 6.57 s; wall 6.58 s
rest.txt:batch 404: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8107 in, 707 out; cost $0.0007; latency p50 2.48 s, p95 3.95 s; wall 4.55 s
rest.txt:batch 405: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7560 in, 669 out; cost $0.0006; latency p50 2.69 s, p95 3.70 s; wall 3.97 s
rest.txt:batch 406: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7487 in, 658 out; cost $0.0006; latency p50 3.23 s, p95 4.02 s; wall 4.04 s
rest.txt:batch 407: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8525 in, 680 out; cost $0.0007; latency p50 3.91 s, p95 4.78 s; wall 4.93 s
rest.txt:batch 408: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9044 in, 711 out; cost $0.0008; latency p50 5.47 s, p95 6.45 s; wall 6.91 s
rest.txt:batch 409: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7678 in, 668 out; cost $0.0006; latency p50 3.35 s, p95 4.53 s; wall 4.78 s
rest.txt:batch 410: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6797 in, 634 out; cost $0.0005; latency p50 3.08 s, p95 4.10 s; wall 4.21 s
rest.txt:batch 411: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7110 in, 655 out; cost $0.0006; latency p50 3.90 s, p95 18.32 s; wall 18.52 s
rest.txt:batch 412: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6572 in, 669 out; cost $0.0005; latency p50 2.83 s, p95 3.83 s; wall 4.10 s
rest.txt:batch 413: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7560 in, 703 out; cost $0.0006; latency p50 3.08 s, p95 4.99 s; wall 5.06 s
rest.txt:batch 414: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7623 in, 652 out; cost $0.0006; latency p50 3.09 s, p95 8.08 s; wall 11.24 s
rest.txt:batch 415: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7770 in, 683 out; cost $0.0006; latency p50 3.31 s, p95 3.88 s; wall 3.94 s
rest.txt:batch 416: 10 requests, 7 recorded, 3 invalid, 0 failed; tokens 7699 in, 3799 out; cost $0.0012; latency p50 2.85 s, p95 14.28 s; wall 22.23 s
rest.txt:batch 417: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7105 in, 640 out; cost $0.0006; latency p50 2.79 s, p95 3.56 s; wall 3.77 s
rest.txt:batch 418: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8533 in, 739 out; cost $0.0007; latency p50 3.09 s, p95 6.39 s; wall 6.95 s
rest.txt:batch 419: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7688 in, 698 out; cost $0.0006; latency p50 3.90 s, p95 5.90 s; wall 7.11 s
rest.txt:batch 420: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7462 in, 734 out; cost $0.0006; latency p50 3.08 s, p95 4.30 s; wall 4.47 s
rest.txt:batch 421: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7772 in, 663 out; cost $0.0006; latency p50 3.64 s, p95 5.84 s; wall 6.30 s
rest.txt:batch 422: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6628 in, 633 out; cost $0.0005; latency p50 2.63 s, p95 4.05 s; wall 4.14 s
rest.txt:batch 423: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9450 in, 663 out; cost $0.0008; latency p50 2.37 s, p95 4.09 s; wall 4.15 s
rest.txt:batch 424: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8154 in, 672 out; cost $0.0007; latency p50 2.16 s, p95 3.05 s; wall 3.23 s
rest.txt:batch 425: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7746 in, 651 out; cost $0.0006; latency p50 2.33 s, p95 3.73 s; wall 3.83 s
rest.txt:batch 426: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7870 in, 654 out; cost $0.0006; latency p50 5.03 s, p95 5.14 s; wall 5.17 s
rest.txt:batch 427: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7138 in, 760 out; cost $0.0006; latency p50 3.18 s, p95 4.57 s; wall 4.89 s
rest.txt:batch 428: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6612 in, 629 out; cost $0.0005; latency p50 3.06 s, p95 4.86 s; wall 4.87 s
rest.txt:batch 429: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7614 in, 705 out; cost $0.0006; latency p50 5.32 s, p95 6.91 s; wall 7.04 s
rest.txt:batch 430: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7206 in, 647 out; cost $0.0005; latency p50 2.91 s, p95 3.29 s; wall 3.52 s
rest.txt:batch 431: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7949 in, 695 out; cost $0.0006; latency p50 2.75 s, p95 3.49 s; wall 3.58 s
rest.txt:batch 432: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7383 in, 620 out; cost $0.0006; latency p50 2.62 s, p95 3.99 s; wall 4.32 s
rest.txt:batch 433: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8871 in, 718 out; cost $0.0007; latency p50 2.68 s, p95 4.40 s; wall 4.49 s
rest.txt:batch 434: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7846 in, 633 out; cost $0.0006; latency p50 2.61 s, p95 3.69 s; wall 4.10 s
rest.txt:batch 435: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7558 in, 663 out; cost $0.0006; latency p50 2.25 s, p95 3.64 s; wall 3.68 s
rest.txt:batch 436: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6383 in, 647 out; cost $0.0005; latency p50 2.66 s, p95 4.08 s; wall 4.45 s
rest.txt:batch 437: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8808 in, 671 out; cost $0.0007; latency p50 2.88 s, p95 3.73 s; wall 3.79 s
rest.txt:batch 438: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8001 in, 693 out; cost $0.0007; latency p50 4.07 s, p95 7.04 s; wall 7.44 s
rest.txt:batch 439: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7027 in, 679 out; cost $0.0006; latency p50 3.39 s, p95 4.29 s; wall 4.50 s
rest.txt:batch 440: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6587 in, 652 out; cost $0.0005; latency p50 3.25 s, p95 4.54 s; wall 4.61 s
rest.txt:batch 441: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7543 in, 644 out; cost $0.0006; latency p50 3.82 s, p95 5.19 s; wall 5.21 s
rest.txt:batch 442: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8408 in, 730 out; cost $0.0007; latency p50 3.81 s, p95 5.50 s; wall 5.56 s
rest.txt:batch 443: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7385 in, 757 out; cost $0.0006; latency p50 3.18 s, p95 4.67 s; wall 4.81 s
rest.txt:batch 444: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7294 in, 635 out; cost $0.0006; latency p50 4.82 s, p95 8.88 s; wall 9.12 s
rest.txt:batch 445: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7053 in, 676 out; cost $0.0006; latency p50 3.54 s, p95 4.34 s; wall 4.69 s
rest.txt:batch 446: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6706 in, 656 out; cost $0.0005; latency p50 3.17 s, p95 16.66 s; wall 20.22 s
rest.txt:batch 447: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8149 in, 720 out; cost $0.0007; latency p50 3.45 s, p95 47.39 s; wall 47.68 s
rest.txt:batch 448: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7284 in, 631 out; cost $0.0006; latency p50 3.45 s, p95 4.33 s; wall 4.40 s
rest.txt:batch 449: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6795 in, 611 out; cost $0.0005; latency p50 3.05 s, p95 3.45 s; wall 3.55 s
rest.txt:batch 450: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7775 in, 691 out; cost $0.0006; latency p50 3.90 s, p95 5.58 s; wall 5.69 s
rest.txt:batch 451: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6706 in, 625 out; cost $0.0005; latency p50 2.92 s, p95 3.86 s; wall 4.15 s
rest.txt:batch 452: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7677 in, 712 out; cost $0.0006; latency p50 3.64 s, p95 4.88 s; wall 5.08 s
rest.txt:batch 453: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7773 in, 732 out; cost $0.0006; latency p50 3.15 s, p95 4.10 s; wall 4.15 s
rest.txt:batch 454: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8293 in, 725 out; cost $0.0007; latency p50 3.35 s, p95 4.76 s; wall 4.94 s
rest.txt:batch 455: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8161 in, 714 out; cost $0.0007; latency p50 3.82 s, p95 4.67 s; wall 5.00 s
rest.txt:batch 456: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7724 in, 649 out; cost $0.0006; latency p50 2.73 s, p95 3.91 s; wall 3.95 s
rest.txt:batch 457: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7921 in, 676 out; cost $0.0007; latency p50 3.45 s, p95 4.51 s; wall 4.66 s
rest.txt:batch 458: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6248 in, 604 out; cost $0.0005; latency p50 4.90 s, p95 7.02 s; wall 7.10 s
rest.txt:batch 459: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6126 in, 692 out; cost $0.0005; latency p50 3.00 s, p95 3.72 s; wall 3.73 s
rest.txt:batch 460: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5412 in, 555 out; cost $0.0004; latency p50 3.48 s, p95 4.60 s; wall 4.61 s
rest.txt:batch 461: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5421 in, 580 out; cost $0.0004; latency p50 1.94 s, p95 2.75 s; wall 3.20 s
rest.txt:batch 462: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6569 in, 628 out; cost $0.0005; latency p50 2.76 s, p95 3.68 s; wall 3.91 s
rest.txt:batch 463: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9795 in, 700 out; cost $0.0008; latency p50 4.10 s, p95 5.67 s; wall 5.94 s
rest.txt:batch 464: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9513 in, 692 out; cost $0.0008; latency p50 3.81 s, p95 4.69 s; wall 4.89 s
rest.txt:batch 465: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9306 in, 718 out; cost $0.0008; latency p50 3.41 s, p95 4.57 s; wall 5.04 s
rest.txt:batch 466: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7295 in, 684 out; cost $0.0006; latency p50 3.10 s, p95 4.02 s; wall 4.29 s
rest.txt:batch 467: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6270 in, 606 out; cost $0.0005; latency p50 3.15 s, p95 3.51 s; wall 3.57 s
rest.txt:batch 468: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7158 in, 688 out; cost $0.0006; latency p50 2.82 s, p95 3.40 s; wall 3.60 s
rest.txt:batch 469: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9141 in, 707 out; cost $0.0008; latency p50 2.66 s, p95 3.56 s; wall 3.74 s
rest.txt:batch 470: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8092 in, 679 out; cost $0.0007; latency p50 2.77 s, p95 3.70 s; wall 3.87 s
rest.txt:batch 471: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9167 in, 689 out; cost $0.0008; latency p50 2.26 s, p95 3.14 s; wall 3.39 s
rest.txt:batch 472: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8162 in, 644 out; cost $0.0006; latency p50 2.93 s, p95 4.67 s; wall 4.79 s
rest.txt:batch 473: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7779 in, 670 out; cost $0.0006; latency p50 3.10 s, p95 4.63 s; wall 5.02 s
rest.txt:batch 474: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8262 in, 720 out; cost $0.0007; latency p50 4.02 s, p95 5.13 s; wall 5.87 s
rest.txt:batch 475: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7594 in, 670 out; cost $0.0006; latency p50 3.00 s, p95 4.41 s; wall 4.66 s
rest.txt:batch 476: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9485 in, 660 out; cost $0.0008; latency p50 3.41 s, p95 4.32 s; wall 4.60 s
rest.txt:batch 477: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7425 in, 737 out; cost $0.0006; latency p50 3.12 s, p95 3.89 s; wall 4.01 s
rest.txt:batch 478: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8191 in, 651 out; cost $0.0007; latency p50 3.93 s, p95 6.02 s; wall 6.19 s
rest.txt:batch 479: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7058 in, 635 out; cost $0.0006; latency p50 3.20 s, p95 4.96 s; wall 5.39 s
rest.txt:batch 480: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7681 in, 744 out; cost $0.0006; latency p50 2.92 s, p95 4.52 s; wall 4.87 s
rest.txt:batch 481: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6868 in, 654 out; cost $0.0006; latency p50 2.68 s, p95 3.94 s; wall 4.61 s
rest.txt:batch 482: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7861 in, 735 out; cost $0.0007; latency p50 3.55 s, p95 4.84 s; wall 4.88 s
rest.txt:batch 483: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7406 in, 658 out; cost $0.0006; latency p50 2.50 s, p95 3.45 s; wall 3.58 s
rest.txt:batch 484: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9726 in, 726 out; cost $0.0008; latency p50 3.25 s, p95 7.68 s; wall 7.80 s
rest.txt:batch 485: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7830 in, 641 out; cost $0.0006; latency p50 2.99 s, p95 3.89 s; wall 4.04 s
rest.txt:batch 486: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7385 in, 684 out; cost $0.0006; latency p50 2.70 s, p95 3.76 s; wall 4.37 s
rest.txt:batch 487: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8773 in, 674 out; cost $0.0007; latency p50 3.11 s, p95 6.65 s; wall 8.86 s
rest.txt:batch 488: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8145 in, 711 out; cost $0.0007; latency p50 2.77 s, p95 3.64 s; wall 3.80 s
rest.txt:batch 489: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9121 in, 797 out; cost $0.0008; latency p50 3.85 s, p95 6.93 s; wall 8.48 s
rest.txt:batch 490: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7410 in, 705 out; cost $0.0006; latency p50 2.97 s, p95 4.33 s; wall 4.66 s
rest.txt:batch 491: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7889 in, 695 out; cost $0.0006; latency p50 3.33 s, p95 4.58 s; wall 4.90 s
rest.txt:batch 492: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7157 in, 697 out; cost $0.0006; latency p50 2.97 s, p95 8.41 s; wall 11.45 s
rest.txt:batch 493: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7586 in, 688 out; cost $0.0006; latency p50 3.57 s, p95 4.73 s; wall 4.96 s
rest.txt:batch 494: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6885 in, 653 out; cost $0.0006; latency p50 3.66 s, p95 4.43 s; wall 4.54 s
rest.txt:batch 495: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7027 in, 641 out; cost $0.0006; latency p50 3.29 s, p95 3.65 s; wall 3.67 s
rest.txt:batch 496: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7445 in, 690 out; cost $0.0006; latency p50 3.02 s, p95 4.01 s; wall 4.05 s
rest.txt:batch 497: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7598 in, 713 out; cost $0.0006; latency p50 3.65 s, p95 4.34 s; wall 4.54 s
rest.txt:batch 498: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8001 in, 709 out; cost $0.0007; latency p50 2.81 s, p95 4.04 s; wall 4.38 s
rest.txt:batch 499: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6800 in, 708 out; cost $0.0006; latency p50 2.85 s, p95 5.20 s; wall 5.32 s
rest.txt:batch 500: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7368 in, 697 out; cost $0.0006; latency p50 3.69 s, p95 5.11 s; wall 5.68 s
rest.txt:batch 501: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7838 in, 685 out; cost $0.0006; latency p50 4.64 s, p95 6.01 s; wall 6.12 s
rest.txt:batch 502: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7380 in, 717 out; cost $0.0006; latency p50 5.00 s, p95 5.97 s; wall 6.12 s
rest.txt:batch 503: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8300 in, 702 out; cost $0.0007; latency p50 3.40 s, p95 4.15 s; wall 4.31 s
rest.txt:batch 504: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8248 in, 709 out; cost $0.0007; latency p50 3.07 s, p95 3.97 s; wall 4.29 s
rest.txt:batch 505: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7536 in, 689 out; cost $0.0006; latency p50 3.59 s, p95 4.79 s; wall 5.20 s
rest.txt:batch 506: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7464 in, 683 out; cost $0.0006; latency p50 3.35 s, p95 3.63 s; wall 3.66 s
rest.txt:batch 507: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7986 in, 674 out; cost $0.0006; latency p50 3.08 s, p95 4.07 s; wall 4.32 s
rest.txt:batch 508: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7785 in, 688 out; cost $0.0006; latency p50 4.02 s, p95 14.10 s; wall 19.47 s
rest.txt:batch 509: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7359 in, 608 out; cost $0.0006; latency p50 3.52 s, p95 4.15 s; wall 4.26 s
rest.txt:batch 510: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7764 in, 681 out; cost $0.0006; latency p50 2.77 s, p95 4.73 s; wall 4.92 s
rest.txt:batch 511: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7663 in, 620 out; cost $0.0006; latency p50 2.09 s, p95 4.06 s; wall 4.44 s
rest.txt:batch 512: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7800 in, 730 out; cost $0.0006; latency p50 2.67 s, p95 3.16 s; wall 3.26 s
rest.txt:batch 513: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7620 in, 670 out; cost $0.0006; latency p50 3.58 s, p95 4.79 s; wall 5.03 s
rest.txt:batch 514: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6965 in, 650 out; cost $0.0006; latency p50 2.76 s, p95 4.51 s; wall 5.40 s
rest.txt:batch 515: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8846 in, 756 out; cost $0.0007; latency p50 2.98 s, p95 3.84 s; wall 4.04 s
rest.txt:batch 516: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7168 in, 649 out; cost $0.0006; latency p50 2.71 s, p95 4.02 s; wall 4.27 s
rest.txt:batch 517: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7530 in, 742 out; cost $0.0006; latency p50 5.31 s, p95 6.65 s; wall 6.86 s
rest.txt:batch 518: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7666 in, 630 out; cost $0.0006; latency p50 3.81 s, p95 5.15 s; wall 5.18 s
rest.txt:batch 519: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7615 in, 725 out; cost $0.0006; latency p50 3.77 s, p95 5.12 s; wall 5.53 s
rest.txt:batch 520: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7719 in, 708 out; cost $0.0006; latency p50 3.16 s, p95 5.44 s; wall 6.94 s
rest.txt:batch 521: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6540 in, 654 out; cost $0.0005; latency p50 3.52 s, p95 4.37 s; wall 4.52 s
rest.txt:batch 522: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6775 in, 691 out; cost $0.0005; latency p50 3.75 s, p95 7.29 s; wall 7.48 s
rest.txt:batch 523: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8295 in, 647 out; cost $0.0007; latency p50 3.90 s, p95 4.24 s; wall 4.29 s
rest.txt:batch 524: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7445 in, 642 out; cost $0.0006; latency p50 2.96 s, p95 3.42 s; wall 3.62 s
rest.txt:batch 525: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8134 in, 658 out; cost $0.0007; latency p50 3.09 s, p95 13.92 s; wall 16.94 s
rest.txt:batch 526: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7179 in, 645 out; cost $0.0006; latency p50 3.59 s, p95 4.44 s; wall 4.95 s
rest.txt:batch 527: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6976 in, 697 out; cost $0.0006; latency p50 4.06 s, p95 6.31 s; wall 6.52 s
rest.txt:batch 528: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7273 in, 716 out; cost $0.0006; latency p50 3.59 s, p95 4.11 s; wall 4.33 s
rest.txt:batch 529: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7448 in, 686 out; cost $0.0006; latency p50 3.71 s, p95 4.38 s; wall 4.40 s
rest.txt:batch 530: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7219 in, 709 out; cost $0.0006; latency p50 3.53 s, p95 5.61 s; wall 5.84 s
rest.txt:batch 531: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6649 in, 686 out; cost $0.0005; latency p50 3.26 s, p95 4.68 s; wall 5.45 s
rest.txt:batch 532: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7925 in, 710 out; cost $0.0007; latency p50 3.39 s, p95 9.15 s; wall 10.48 s
rest.txt:batch 533: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8853 in, 732 out; cost $0.0007; latency p50 2.75 s, p95 3.51 s; wall 3.76 s
rest.txt:batch 534: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7546 in, 674 out; cost $0.0006; latency p50 3.42 s, p95 4.31 s; wall 4.45 s
rest.txt:batch 535: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6539 in, 617 out; cost $0.0005; latency p50 2.87 s, p95 5.24 s; wall 5.38 s
rest.txt:batch 536: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7436 in, 710 out; cost $0.0006; latency p50 3.58 s, p95 5.48 s; wall 5.52 s
rest.txt:batch 537: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7367 in, 651 out; cost $0.0006; latency p50 3.81 s, p95 6.73 s; wall 7.52 s
rest.txt:batch 538: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6515 in, 661 out; cost $0.0005; latency p50 3.85 s, p95 4.71 s; wall 5.05 s
rest.txt:batch 539: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8026 in, 759 out; cost $0.0007; latency p50 3.97 s, p95 4.91 s; wall 5.28 s
rest.txt:batch 540: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6570 in, 667 out; cost $0.0005; latency p50 2.54 s, p95 3.95 s; wall 4.01 s
rest.txt:batch 541: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7614 in, 661 out; cost $0.0006; latency p50 1.99 s, p95 3.51 s; wall 3.72 s
rest.txt:batch 542: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9256 in, 704 out; cost $0.0008; latency p50 2.72 s, p95 7.63 s; wall 11.32 s
rest.txt:batch 543: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9179 in, 727 out; cost $0.0008; latency p50 3.04 s, p95 4.45 s; wall 4.46 s
rest.txt:batch 544: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7858 in, 698 out; cost $0.0006; latency p50 3.71 s, p95 4.93 s; wall 5.44 s
rest.txt:batch 545: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7176 in, 700 out; cost $0.0006; latency p50 2.55 s, p95 4.47 s; wall 4.88 s
rest.txt:batch 546: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7143 in, 652 out; cost $0.0006; latency p50 3.53 s, p95 4.28 s; wall 4.41 s
rest.txt:batch 547: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8638 in, 696 out; cost $0.0007; latency p50 3.31 s, p95 5.71 s; wall 6.83 s
rest.txt:batch 548: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6812 in, 711 out; cost $0.0006; latency p50 3.97 s, p95 5.58 s; wall 5.72 s
rest.txt:batch 549: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 10051 in, 729 out; cost $0.0009; latency p50 3.39 s, p95 4.02 s; wall 4.06 s
rest.txt:batch 550: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7577 in, 730 out; cost $0.0006; latency p50 2.64 s, p95 5.69 s; wall 5.92 s
rest.txt:batch 551: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8865 in, 688 out; cost $0.0007; latency p50 2.70 s, p95 4.08 s; wall 4.19 s
rest.txt:batch 552: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7098 in, 639 out; cost $0.0006; latency p50 5.21 s, p95 5.84 s; wall 5.98 s
rest.txt:batch 553: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7612 in, 658 out; cost $0.0006; latency p50 2.81 s, p95 6.18 s; wall 7.79 s
rest.txt:batch 554: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8690 in, 695 out; cost $0.0007; latency p50 3.39 s, p95 4.49 s; wall 4.74 s
rest.txt:batch 555: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7200 in, 630 out; cost $0.0006; latency p50 3.65 s, p95 5.62 s; wall 5.95 s
rest.txt:batch 556: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8936 in, 697 out; cost $0.0007; latency p50 3.08 s, p95 5.96 s; wall 6.46 s
rest.txt:batch 557: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8338 in, 759 out; cost $0.0007; latency p50 2.89 s, p95 3.55 s; wall 3.61 s
rest.txt:batch 558: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8173 in, 702 out; cost $0.0007; latency p50 4.69 s, p95 5.61 s; wall 5.85 s
rest.txt:batch 559: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7160 in, 653 out; cost $0.0006; latency p50 2.70 s, p95 3.85 s; wall 4.32 s
rest.txt:batch 560: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7646 in, 793 out; cost $0.0006; latency p50 3.54 s, p95 7.87 s; wall 9.65 s
rest.txt:batch 561: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8945 in, 740 out; cost $0.0008; latency p50 2.85 s, p95 3.35 s; wall 3.38 s
rest.txt:batch 562: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7677 in, 682 out; cost $0.0006; latency p50 2.93 s, p95 3.44 s; wall 3.74 s
rest.txt:batch 563: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7446 in, 675 out; cost $0.0006; latency p50 2.45 s, p95 3.12 s; wall 3.23 s
rest.txt:batch 564: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6925 in, 713 out; cost $0.0006; latency p50 2.93 s, p95 3.31 s; wall 3.44 s
rest.txt:batch 565: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8115 in, 716 out; cost $0.0007; latency p50 2.53 s, p95 3.75 s; wall 4.30 s
rest.txt:batch 566: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7926 in, 699 out; cost $0.0007; latency p50 3.38 s, p95 4.71 s; wall 5.13 s
rest.txt:batch 567: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9775 in, 789 out; cost $0.0008; latency p50 3.89 s, p95 4.96 s; wall 5.67 s
rest.txt:batch 568: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7705 in, 655 out; cost $0.0006; latency p50 3.38 s, p95 3.81 s; wall 3.90 s
rest.txt:batch 569: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6763 in, 668 out; cost $0.0005; latency p50 3.55 s, p95 4.42 s; wall 4.48 s
rest.txt:batch 570: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6967 in, 706 out; cost $0.0006; latency p50 5.17 s, p95 5.94 s; wall 6.00 s
rest.txt:batch 571: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7633 in, 691 out; cost $0.0006; latency p50 2.31 s, p95 2.40 s; wall 2.42 s
rest.txt:batch 572: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6640 in, 637 out; cost $0.0005; latency p50 2.95 s, p95 3.99 s; wall 4.08 s
rest.txt:batch 573: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7185 in, 650 out; cost $0.0006; latency p50 3.75 s, p95 4.34 s; wall 4.41 s
rest.txt:batch 574: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6494 in, 590 out; cost $0.0005; latency p50 3.12 s, p95 4.73 s; wall 5.20 s
rest.txt:batch 575: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7480 in, 661 out; cost $0.0006; latency p50 3.29 s, p95 3.61 s; wall 3.64 s
rest.txt:batch 576: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7548 in, 714 out; cost $0.0006; latency p50 6.53 s, p95 7.30 s; wall 7.72 s
rest.txt:batch 577: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8888 in, 720 out; cost $0.0007; latency p50 3.71 s, p95 4.18 s; wall 4.20 s
rest.txt:batch 578: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7216 in, 695 out; cost $0.0006; latency p50 4.24 s, p95 5.39 s; wall 5.55 s
rest.txt:batch 579: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6953 in, 646 out; cost $0.0006; latency p50 4.97 s, p95 21.39 s; wall 21.52 s
rest.txt:batch 580: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7533 in, 721 out; cost $0.0006; latency p50 2.52 s, p95 3.51 s; wall 3.68 s
rest.txt:batch 581: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7048 in, 675 out; cost $0.0006; latency p50 3.03 s, p95 4.57 s; wall 4.60 s
rest.txt:batch 582: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7431 in, 677 out; cost $0.0006; latency p50 3.45 s, p95 4.14 s; wall 4.20 s
rest.txt:batch 583: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7303 in, 673 out; cost $0.0006; latency p50 3.52 s, p95 5.73 s; wall 6.66 s
rest.txt:batch 584: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7870 in, 645 out; cost $0.0006; latency p50 2.14 s, p95 3.30 s; wall 3.57 s
rest.txt:batch 585: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7320 in, 645 out; cost $0.0006; latency p50 2.56 s, p95 3.30 s; wall 3.41 s
rest.txt:batch 586: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7749 in, 730 out; cost $0.0006; latency p50 3.47 s, p95 4.08 s; wall 4.08 s
rest.txt:batch 587: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8816 in, 713 out; cost $0.0007; latency p50 4.92 s, p95 6.32 s; wall 6.55 s
rest.txt:batch 588: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7014 in, 628 out; cost $0.0006; latency p50 2.54 s, p95 3.62 s; wall 3.70 s
rest.txt:batch 589: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7515 in, 707 out; cost $0.0006; latency p50 2.67 s, p95 4.73 s; wall 5.96 s
rest.txt:batch 590: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6738 in, 679 out; cost $0.0005; latency p50 3.68 s, p95 4.67 s; wall 4.68 s
rest.txt:batch 591: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7235 in, 658 out; cost $0.0006; latency p50 3.70 s, p95 4.68 s; wall 4.83 s
rest.txt:batch 592: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8556 in, 755 out; cost $0.0007; latency p50 3.42 s, p95 7.34 s; wall 8.61 s
rest.txt:batch 593: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7504 in, 681 out; cost $0.0006; latency p50 2.52 s, p95 3.36 s; wall 3.45 s
rest.txt:batch 594: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9114 in, 703 out; cost $0.0008; latency p50 3.40 s, p95 5.46 s; wall 5.70 s
rest.txt:batch 595: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7195 in, 674 out; cost $0.0006; latency p50 3.57 s, p95 4.80 s; wall 5.06 s
rest.txt:batch 596: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7662 in, 682 out; cost $0.0006; latency p50 3.33 s, p95 3.94 s; wall 3.97 s
rest.txt:batch 597: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7154 in, 635 out; cost $0.0005; latency p50 3.27 s, p95 4.46 s; wall 4.84 s
rest.txt:batch 598: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7249 in, 663 out; cost $0.0005; latency p50 3.91 s, p95 5.94 s; wall 6.22 s
rest.txt:batch 599: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8229 in, 630 out; cost $0.0006; latency p50 2.43 s, p95 3.71 s; wall 3.94 s
rest.txt:batch 600: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7032 in, 688 out; cost $0.0006; latency p50 5.00 s, p95 6.40 s; wall 6.50 s
rest.txt:batch 601: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7888 in, 618 out; cost $0.0006; latency p50 2.63 s, p95 4.02 s; wall 4.95 s
rest.txt:batch 602: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6874 in, 651 out; cost $0.0006; latency p50 3.22 s, p95 4.05 s; wall 4.56 s
rest.txt:batch 603: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6542 in, 670 out; cost $0.0005; latency p50 3.67 s, p95 4.03 s; wall 4.08 s
rest.txt:batch 604: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6950 in, 646 out; cost $0.0006; latency p50 2.50 s, p95 3.45 s; wall 3.49 s
rest.txt:batch 605: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8538 in, 728 out; cost $0.0007; latency p50 3.07 s, p95 4.52 s; wall 4.62 s
rest.txt:batch 606: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7408 in, 649 out; cost $0.0006; latency p50 2.59 s, p95 4.62 s; wall 5.25 s
rest.txt:batch 607: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5931 in, 648 out; cost $0.0005; latency p50 3.80 s, p95 4.54 s; wall 4.55 s
rest.txt:batch 608: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7342 in, 657 out; cost $0.0006; latency p50 3.39 s, p95 4.68 s; wall 5.40 s
rest.txt:batch 609: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7705 in, 680 out; cost $0.0006; latency p50 4.13 s, p95 4.94 s; wall 5.20 s
rest.txt:batch 610: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7659 in, 743 out; cost $0.0006; latency p50 4.10 s, p95 5.68 s; wall 5.77 s
rest.txt:batch 611: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8078 in, 714 out; cost $0.0007; latency p50 3.71 s, p95 4.63 s; wall 4.98 s
rest.txt:batch 612: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7665 in, 671 out; cost $0.0006; latency p50 3.74 s, p95 15.62 s; wall 24.38 s
rest.txt:batch 613: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7407 in, 669 out; cost $0.0006; latency p50 3.14 s, p95 4.66 s; wall 5.19 s
rest.txt:batch 614: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8706 in, 639 out; cost $0.0007; latency p50 3.57 s, p95 4.36 s; wall 4.52 s
rest.txt:batch 615: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7799 in, 702 out; cost $0.0006; latency p50 3.81 s, p95 4.57 s; wall 4.66 s
rest.txt:batch 616: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7489 in, 685 out; cost $0.0006; latency p50 3.08 s, p95 4.28 s; wall 4.43 s
rest.txt:batch 617: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7331 in, 695 out; cost $0.0006; latency p50 3.11 s, p95 4.15 s; wall 4.18 s
rest.txt:batch 618: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7085 in, 734 out; cost $0.0006; latency p50 3.35 s, p95 4.37 s; wall 4.52 s
rest.txt:batch 619: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6930 in, 656 out; cost $0.0006; latency p50 3.22 s, p95 4.73 s; wall 4.85 s
rest.txt:batch 620: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7262 in, 651 out; cost $0.0006; latency p50 3.69 s, p95 11.43 s; wall 16.70 s
rest.txt:batch 621: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7374 in, 644 out; cost $0.0006; latency p50 2.42 s, p95 3.50 s; wall 3.90 s
rest.txt:batch 622: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6439 in, 614 out; cost $0.0005; latency p50 3.61 s, p95 6.20 s; wall 6.62 s
rest.txt:batch 623: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7754 in, 664 out; cost $0.0006; latency p50 3.50 s, p95 5.83 s; wall 6.23 s
rest.txt:batch 624: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6768 in, 679 out; cost $0.0005; latency p50 3.53 s, p95 4.72 s; wall 5.21 s
rest.txt:batch 625: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7135 in, 678 out; cost $0.0006; latency p50 3.79 s, p95 4.92 s; wall 5.05 s
rest.txt:batch 626: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6686 in, 665 out; cost $0.0005; latency p50 3.41 s, p95 3.66 s; wall 3.79 s
rest.txt:batch 627: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7059 in, 647 out; cost $0.0006; latency p50 4.07 s, p95 4.75 s; wall 4.94 s
rest.txt:batch 628: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6785 in, 614 out; cost $0.0005; latency p50 4.68 s, p95 5.46 s; wall 5.75 s
rest.txt:batch 629: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7325 in, 678 out; cost $0.0006; latency p50 5.93 s, p95 7.37 s; wall 8.04 s
rest.txt:batch 630: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8907 in, 697 out; cost $0.0007; latency p50 4.42 s, p95 5.11 s; wall 5.14 s
rest.txt:batch 631: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7951 in, 738 out; cost $0.0007; latency p50 4.47 s, p95 7.95 s; wall 8.90 s
rest.txt:batch 632: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6360 in, 593 out; cost $0.0005; latency p50 4.24 s, p95 4.92 s; wall 4.99 s
rest.txt:batch 633: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6997 in, 689 out; cost $0.0006; latency p50 3.53 s, p95 4.20 s; wall 4.34 s
rest.txt:batch 634: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7224 in, 630 out; cost $0.0006; latency p50 2.57 s, p95 3.37 s; wall 3.74 s
rest.txt:batch 635: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7902 in, 692 out; cost $0.0007; latency p50 3.85 s, p95 4.40 s; wall 4.53 s
rest.txt:batch 636: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6900 in, 642 out; cost $0.0006; latency p50 3.99 s, p95 4.71 s; wall 5.15 s
rest.txt:batch 637: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6780 in, 658 out; cost $0.0005; latency p50 3.14 s, p95 3.97 s; wall 4.38 s
rest.txt:batch 638: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8231 in, 706 out; cost $0.0007; latency p50 3.27 s, p95 4.20 s; wall 4.27 s
rest.txt:batch 639: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6900 in, 686 out; cost $0.0006; latency p50 3.13 s, p95 3.98 s; wall 4.26 s
rest.txt:batch 640: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7972 in, 664 out; cost $0.0007; latency p50 2.54 s, p95 4.53 s; wall 4.88 s
rest.txt:batch 641: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6728 in, 734 out; cost $0.0006; latency p50 4.15 s, p95 5.21 s; wall 5.71 s
rest.txt:batch 642: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7827 in, 726 out; cost $0.0007; latency p50 2.72 s, p95 3.54 s; wall 3.69 s
rest.txt:batch 643: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8214 in, 714 out; cost $0.0007; latency p50 2.73 s, p95 3.62 s; wall 3.76 s
rest.txt:batch 644: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7848 in, 744 out; cost $0.0007; latency p50 6.07 s, p95 6.60 s; wall 6.68 s
rest.txt:batch 645: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6671 in, 617 out; cost $0.0005; latency p50 2.25 s, p95 3.27 s; wall 3.59 s
rest.txt:batch 646: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7719 in, 659 out; cost $0.0006; latency p50 4.01 s, p95 4.16 s; wall 4.18 s
rest.txt:batch 647: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6617 in, 709 out; cost $0.0005; latency p50 2.65 s, p95 4.10 s; wall 4.20 s
rest.txt:batch 648: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6829 in, 675 out; cost $0.0006; latency p50 3.60 s, p95 4.70 s; wall 4.96 s
rest.txt:batch 649: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6996 in, 731 out; cost $0.0006; latency p50 3.34 s, p95 3.70 s; wall 3.74 s
rest.txt:batch 650: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8236 in, 749 out; cost $0.0007; latency p50 3.23 s, p95 4.64 s; wall 4.69 s
rest.txt:batch 651: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7508 in, 703 out; cost $0.0006; latency p50 2.50 s, p95 4.19 s; wall 4.35 s
rest.txt:batch 652: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7525 in, 653 out; cost $0.0006; latency p50 3.03 s, p95 3.60 s; wall 3.67 s
rest.txt:batch 653: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7557 in, 707 out; cost $0.0006; latency p50 4.71 s, p95 5.70 s; wall 6.03 s
rest.txt:batch 654: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6769 in, 636 out; cost $0.0005; latency p50 3.49 s, p95 5.10 s; wall 5.71 s
rest.txt:batch 655: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6683 in, 613 out; cost $0.0005; latency p50 2.69 s, p95 4.48 s; wall 4.88 s
rest.txt:batch 656: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7276 in, 712 out; cost $0.0006; latency p50 4.65 s, p95 6.00 s; wall 6.01 s
rest.txt:batch 657: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8710 in, 716 out; cost $0.0007; latency p50 3.79 s, p95 4.97 s; wall 5.05 s
rest.txt:batch 658: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8363 in, 689 out; cost $0.0007; latency p50 2.54 s, p95 5.51 s; wall 5.65 s
rest.txt:batch 659: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7486 in, 671 out; cost $0.0006; latency p50 2.53 s, p95 3.33 s; wall 3.72 s
rest.txt:batch 660: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6340 in, 608 out; cost $0.0005; latency p50 2.23 s, p95 3.90 s; wall 4.04 s
rest.txt:batch 661: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8477 in, 659 out; cost $0.0007; latency p50 3.72 s, p95 4.51 s; wall 4.52 s
rest.txt:batch 662: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6557 in, 650 out; cost $0.0005; latency p50 3.47 s, p95 4.24 s; wall 4.55 s
rest.txt:batch 663: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7850 in, 689 out; cost $0.0006; latency p50 2.92 s, p95 3.46 s; wall 3.52 s
rest.txt:batch 664: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7085 in, 642 out; cost $0.0006; latency p50 2.44 s, p95 7.21 s; wall 7.28 s
rest.txt:batch 665: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7420 in, 711 out; cost $0.0006; latency p50 3.34 s, p95 11.74 s; wall 15.99 s
rest.txt:batch 666: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6836 in, 685 out; cost $0.0006; latency p50 2.13 s, p95 7.66 s; wall 7.92 s
rest.txt:batch 667: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6365 in, 730 out; cost $0.0005; latency p50 3.00 s, p95 4.84 s; wall 5.58 s
rest.txt:batch 668: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6869 in, 741 out; cost $0.0006; latency p50 3.24 s, p95 4.72 s; wall 5.66 s
rest.txt:batch 669: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6810 in, 661 out; cost $0.0005; latency p50 2.46 s, p95 4.78 s; wall 5.08 s
rest.txt:batch 670: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7896 in, 698 out; cost $0.0007; latency p50 4.52 s, p95 5.35 s; wall 5.36 s
rest.txt:batch 671: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7156 in, 650 out; cost $0.0006; latency p50 3.65 s, p95 4.64 s; wall 4.65 s
rest.txt:batch 672: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7540 in, 738 out; cost $0.0006; latency p50 4.26 s, p95 7.89 s; wall 8.31 s
rest.txt:batch 673: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8021 in, 671 out; cost $0.0007; latency p50 4.40 s, p95 4.96 s; wall 5.02 s
rest.txt:batch 674: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7727 in, 639 out; cost $0.0006; latency p50 3.45 s, p95 4.79 s; wall 5.09 s
rest.txt:batch 675: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7890 in, 648 out; cost $0.0006; latency p50 2.61 s, p95 3.36 s; wall 3.37 s
rest.txt:batch 676: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7021 in, 696 out; cost $0.0006; latency p50 4.46 s, p95 5.06 s; wall 5.17 s
rest.txt:batch 677: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7754 in, 700 out; cost $0.0006; latency p50 4.16 s, p95 4.67 s; wall 4.68 s
rest.txt:batch 678: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7279 in, 711 out; cost $0.0006; latency p50 2.27 s, p95 3.44 s; wall 3.65 s
rest.txt:batch 679: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7148 in, 674 out; cost $0.0006; latency p50 2.83 s, p95 4.26 s; wall 4.36 s
rest.txt:batch 680: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9062 in, 665 out; cost $0.0008; latency p50 2.81 s, p95 3.46 s; wall 3.67 s
rest.txt:batch 681: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7000 in, 663 out; cost $0.0006; latency p50 3.62 s, p95 6.11 s; wall 6.35 s
rest.txt:batch 682: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7378 in, 677 out; cost $0.0006; latency p50 3.51 s, p95 5.29 s; wall 5.30 s
rest.txt:batch 683: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8771 in, 678 out; cost $0.0007; latency p50 2.83 s, p95 3.16 s; wall 3.30 s
rest.txt:batch 684: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6209 in, 646 out; cost $0.0005; latency p50 2.98 s, p95 3.87 s; wall 4.03 s
rest.txt:batch 685: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7615 in, 706 out; cost $0.0006; latency p50 3.21 s, p95 4.89 s; wall 5.90 s
rest.txt:batch 686: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7807 in, 685 out; cost $0.0006; latency p50 6.13 s, p95 6.98 s; wall 7.10 s
rest.txt:batch 687: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5827 in, 569 out; cost $0.0004; latency p50 2.93 s, p95 3.53 s; wall 3.59 s
rest.txt:batch 688: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5836 in, 605 out; cost $0.0004; latency p50 2.16 s, p95 3.65 s; wall 4.26 s
rest.txt:batch 689: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7498 in, 732 out; cost $0.0006; latency p50 2.88 s, p95 3.78 s; wall 3.96 s
rest.txt:batch 690: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9011 in, 684 out; cost $0.0007; latency p50 3.20 s, p95 5.20 s; wall 6.20 s
rest.txt:batch 691: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7544 in, 708 out; cost $0.0006; latency p50 2.30 s, p95 3.51 s; wall 3.64 s
rest.txt:batch 692: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7845 in, 662 out; cost $0.0006; latency p50 2.69 s, p95 5.92 s; wall 6.80 s
rest.txt:batch 693: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8058 in, 678 out; cost $0.0007; latency p50 3.08 s, p95 5.40 s; wall 5.94 s
rest.txt:batch 694: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6668 in, 650 out; cost $0.0005; latency p50 3.33 s, p95 3.50 s; wall 3.52 s
rest.txt:batch 695: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8227 in, 696 out; cost $0.0007; latency p50 2.88 s, p95 3.94 s; wall 4.01 s
rest.txt:batch 696: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7306 in, 703 out; cost $0.0006; latency p50 4.85 s, p95 5.05 s; wall 5.12 s
rest.txt:batch 697: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6962 in, 740 out; cost $0.0006; latency p50 2.40 s, p95 3.64 s; wall 4.14 s
rest.txt:batch 698: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7342 in, 650 out; cost $0.0006; latency p50 3.52 s, p95 4.32 s; wall 4.83 s
rest.txt:batch 699: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7822 in, 709 out; cost $0.0006; latency p50 3.74 s, p95 4.49 s; wall 4.50 s
rest.txt:batch 700: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7581 in, 688 out; cost $0.0006; latency p50 3.22 s, p95 6.30 s; wall 6.73 s
rest.txt:batch 701: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6945 in, 668 out; cost $0.0006; latency p50 2.70 s, p95 3.71 s; wall 4.05 s
rest.txt:batch 702: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7073 in, 630 out; cost $0.0005; latency p50 3.20 s, p95 3.87 s; wall 4.01 s
rest.txt:batch 703: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8551 in, 645 out; cost $0.0007; latency p50 3.52 s, p95 6.75 s; wall 8.76 s
rest.txt:batch 704: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6311 in, 615 out; cost $0.0005; latency p50 2.58 s, p95 4.26 s; wall 4.67 s
rest.txt:batch 705: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6636 in, 710 out; cost $0.0005; latency p50 3.56 s, p95 4.30 s; wall 4.57 s
rest.txt:batch 706: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7222 in, 734 out; cost $0.0006; latency p50 2.81 s, p95 4.50 s; wall 4.92 s
rest.txt:batch 707: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7127 in, 684 out; cost $0.0006; latency p50 3.55 s, p95 4.59 s; wall 4.71 s
rest.txt:batch 708: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7426 in, 691 out; cost $0.0006; latency p50 3.48 s, p95 4.90 s; wall 4.98 s
rest.txt:batch 709: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6739 in, 688 out; cost $0.0005; latency p50 2.62 s, p95 3.99 s; wall 4.17 s
rest.txt:batch 710: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7441 in, 649 out; cost $0.0006; latency p50 3.35 s, p95 4.36 s; wall 4.67 s
rest.txt:batch 711: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7456 in, 668 out; cost $0.0006; latency p50 3.73 s, p95 4.41 s; wall 4.89 s
rest.txt:batch 712: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7636 in, 649 out; cost $0.0006; latency p50 2.97 s, p95 4.14 s; wall 4.24 s
rest.txt:batch 713: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6713 in, 646 out; cost $0.0005; latency p50 2.59 s, p95 3.70 s; wall 4.10 s
rest.txt:batch 714: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7080 in, 694 out; cost $0.0006; latency p50 2.82 s, p95 3.26 s; wall 3.36 s
rest.txt:batch 715: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7300 in, 680 out; cost $0.0006; latency p50 2.30 s, p95 4.64 s; wall 5.81 s
rest.txt:batch 716: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7202 in, 644 out; cost $0.0006; latency p50 2.83 s, p95 4.21 s; wall 4.61 s
rest.txt:batch 717: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6747 in, 642 out; cost $0.0005; latency p50 2.75 s, p95 5.33 s; wall 5.70 s
rest.txt:batch 718: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6557 in, 624 out; cost $0.0005; latency p50 2.50 s, p95 3.52 s; wall 3.59 s
rest.txt:batch 719: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7464 in, 657 out; cost $0.0006; latency p50 2.56 s, p95 3.45 s; wall 3.60 s
rest.txt:batch 720: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6037 in, 652 out; cost $0.0005; latency p50 2.16 s, p95 4.94 s; wall 5.89 s
rest.txt:batch 721: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5614 in, 617 out; cost $0.0004; latency p50 3.74 s, p95 4.44 s; wall 4.62 s
rest.txt:batch 722: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7651 in, 654 out; cost $0.0006; latency p50 2.97 s, p95 3.70 s; wall 3.77 s
rest.txt:batch 723: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6970 in, 670 out; cost $0.0006; latency p50 3.37 s, p95 3.68 s; wall 3.85 s
rest.txt:batch 724: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7573 in, 646 out; cost $0.0006; latency p50 3.44 s, p95 4.59 s; wall 4.87 s
rest.txt:batch 725: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7958 in, 641 out; cost $0.0006; latency p50 3.58 s, p95 3.86 s; wall 3.87 s
rest.txt:batch 726: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8208 in, 643 out; cost $0.0007; latency p50 2.11 s, p95 2.98 s; wall 3.10 s
rest.txt:batch 727: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6988 in, 644 out; cost $0.0006; latency p50 6.43 s, p95 7.65 s; wall 7.65 s
rest.txt:batch 728: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6478 in, 700 out; cost $0.0005; latency p50 2.63 s, p95 3.81 s; wall 3.89 s
rest.txt:batch 729: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 9015 in, 714 out; cost $0.0008; latency p50 2.93 s, p95 3.59 s; wall 3.74 s
rest.txt:batch 730: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7718 in, 691 out; cost $0.0006; latency p50 3.23 s, p95 4.03 s; wall 4.14 s
rest.txt:batch 731: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7015 in, 627 out; cost $0.0006; latency p50 2.64 s, p95 3.34 s; wall 3.54 s
rest.txt:batch 732: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7418 in, 651 out; cost $0.0006; latency p50 2.60 s, p95 3.92 s; wall 4.59 s
rest.txt:batch 733: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8121 in, 702 out; cost $0.0007; latency p50 3.00 s, p95 4.07 s; wall 4.42 s
rest.txt:batch 734: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7204 in, 648 out; cost $0.0006; latency p50 2.10 s, p95 3.37 s; wall 3.64 s
rest.txt:batch 735: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7038 in, 703 out; cost $0.0006; latency p50 3.32 s, p95 4.56 s; wall 5.14 s
rest.txt:batch 736: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6218 in, 600 out; cost $0.0005; latency p50 3.43 s, p95 4.06 s; wall 4.15 s
rest.txt:batch 737: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7598 in, 612 out; cost $0.0006; latency p50 2.35 s, p95 4.83 s; wall 4.95 s
rest.txt:batch 738: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6729 in, 682 out; cost $0.0005; latency p50 3.28 s, p95 4.52 s; wall 4.87 s
rest.txt:batch 739: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6259 in, 701 out; cost $0.0005; latency p50 2.79 s, p95 5.81 s; wall 6.20 s
rest.txt:batch 740: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6409 in, 595 out; cost $0.0005; latency p50 3.59 s, p95 4.40 s; wall 4.65 s
rest.txt:batch 741: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6016 in, 674 out; cost $0.0005; latency p50 5.45 s, p95 6.18 s; wall 6.28 s
rest.txt:batch 742: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7041 in, 659 out; cost $0.0006; latency p50 2.50 s, p95 3.89 s; wall 4.15 s
rest.txt:batch 743: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7767 in, 658 out; cost $0.0006; latency p50 2.84 s, p95 4.06 s; wall 4.35 s
rest.txt:batch 744: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7254 in, 673 out; cost $0.0006; latency p50 3.12 s, p95 5.25 s; wall 5.59 s
rest.txt:batch 745: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6977 in, 641 out; cost $0.0006; latency p50 3.10 s, p95 4.00 s; wall 4.38 s
rest.txt:batch 746: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7501 in, 736 out; cost $0.0006; latency p50 5.01 s, p95 6.06 s; wall 6.12 s
rest.txt:batch 747: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8716 in, 719 out; cost $0.0007; latency p50 3.12 s, p95 3.91 s; wall 4.06 s
rest.txt:batch 748: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6306 in, 619 out; cost $0.0005; latency p50 3.14 s, p95 11.46 s; wall 11.69 s
rest.txt:batch 749: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7265 in, 784 out; cost $0.0006; latency p50 4.06 s, p95 5.68 s; wall 6.17 s
rest.txt:batch 750: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7417 in, 742 out; cost $0.0006; latency p50 2.87 s, p95 3.58 s; wall 3.75 s
rest.txt:batch 751: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7409 in, 641 out; cost $0.0006; latency p50 3.56 s, p95 4.38 s; wall 4.39 s
rest.txt:batch 752: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7539 in, 667 out; cost $0.0006; latency p50 3.08 s, p95 3.91 s; wall 3.94 s
rest.txt:batch 753: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7003 in, 629 out; cost $0.0006; latency p50 2.65 s, p95 3.69 s; wall 3.70 s
rest.txt:batch 754: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6940 in, 684 out; cost $0.0006; latency p50 2.04 s, p95 2.59 s; wall 2.86 s
rest.txt:batch 755: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6436 in, 648 out; cost $0.0005; latency p50 2.44 s, p95 4.01 s; wall 4.79 s
rest.txt:batch 756: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6452 in, 655 out; cost $0.0005; latency p50 2.90 s, p95 5.77 s; wall 7.67 s
rest.txt:batch 757: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6638 in, 656 out; cost $0.0005; latency p50 2.91 s, p95 3.62 s; wall 3.90 s
rest.txt:batch 758: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6986 in, 656 out; cost $0.0006; latency p50 3.13 s, p95 4.02 s; wall 4.15 s
rest.txt:batch 759: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7028 in, 635 out; cost $0.0006; latency p50 2.67 s, p95 3.37 s; wall 3.78 s
rest.txt:batch 760: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6443 in, 616 out; cost $0.0005; latency p50 2.76 s, p95 3.56 s; wall 3.77 s
rest.txt:batch 761: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5778 in, 636 out; cost $0.0005; latency p50 2.26 s, p95 2.87 s; wall 2.87 s
rest.txt:batch 762: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6038 in, 602 out; cost $0.0005; latency p50 2.37 s, p95 5.06 s; wall 5.10 s
rest.txt:batch 763: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6887 in, 692 out; cost $0.0006; latency p50 2.34 s, p95 5.39 s; wall 6.15 s
rest.txt:batch 764: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7247 in, 700 out; cost $0.0006; latency p50 2.62 s, p95 3.97 s; wall 4.10 s
rest.txt:batch 765: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6276 in, 593 out; cost $0.0005; latency p50 2.76 s, p95 3.79 s; wall 3.83 s
rest.txt:batch 766: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7192 in, 696 out; cost $0.0006; latency p50 2.43 s, p95 3.85 s; wall 4.16 s
rest.txt:batch 767: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7193 in, 695 out; cost $0.0006; latency p50 2.16 s, p95 3.27 s; wall 3.53 s
rest.txt:batch 768: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7120 in, 680 out; cost $0.0006; latency p50 2.32 s, p95 2.74 s; wall 2.75 s
rest.txt:batch 769: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6720 in, 680 out; cost $0.0005; latency p50 2.62 s, p95 4.01 s; wall 4.07 s
rest.txt:batch 770: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8613 in, 670 out; cost $0.0007; latency p50 2.56 s, p95 4.26 s; wall 4.38 s
rest.txt:batch 771: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6180 in, 605 out; cost $0.0005; latency p50 2.86 s, p95 4.23 s; wall 4.39 s
rest.txt:batch 772: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6827 in, 638 out; cost $0.0005; latency p50 2.55 s, p95 3.38 s; wall 3.59 s
rest.txt:batch 773: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6754 in, 637 out; cost $0.0005; latency p50 2.32 s, p95 3.93 s; wall 4.33 s
rest.txt:batch 774: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8789 in, 645 out; cost $0.0007; latency p50 3.06 s, p95 3.50 s; wall 3.56 s
rest.txt:batch 775: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6839 in, 706 out; cost $0.0006; latency p50 3.25 s, p95 4.27 s; wall 4.38 s
rest.txt:batch 776: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6694 in, 573 out; cost $0.0005; latency p50 2.38 s, p95 3.23 s; wall 3.73 s
rest.txt:batch 777: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7553 in, 724 out; cost $0.0006; latency p50 2.15 s, p95 3.90 s; wall 3.92 s
rest.txt:batch 778: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5776 in, 641 out; cost $0.0005; latency p50 2.68 s, p95 3.71 s; wall 3.71 s
rest.txt:batch 779: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6885 in, 590 out; cost $0.0005; latency p50 2.56 s, p95 3.36 s; wall 3.51 s
rest.txt:batch 780: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6537 in, 649 out; cost $0.0005; latency p50 3.21 s, p95 4.91 s; wall 5.53 s
rest.txt:batch 781: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8156 in, 676 out; cost $0.0007; latency p50 2.76 s, p95 4.18 s; wall 4.98 s
rest.txt:batch 782: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7119 in, 670 out; cost $0.0006; latency p50 2.18 s, p95 5.74 s; wall 6.03 s
rest.txt:batch 783: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6816 in, 620 out; cost $0.0005; latency p50 3.83 s, p95 6.17 s; wall 6.49 s
rest.txt:batch 784: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6999 in, 700 out; cost $0.0006; latency p50 2.33 s, p95 4.05 s; wall 4.16 s
rest.txt:batch 785: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6795 in, 673 out; cost $0.0005; latency p50 3.65 s, p95 4.56 s; wall 4.86 s
rest.txt:batch 786: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6764 in, 658 out; cost $0.0005; latency p50 3.03 s, p95 5.45 s; wall 5.90 s
rest.txt:batch 787: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8455 in, 674 out; cost $0.0007; latency p50 2.46 s, p95 3.67 s; wall 3.98 s
rest.txt:batch 788: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6233 in, 648 out; cost $0.0005; latency p50 2.48 s, p95 3.70 s; wall 3.93 s
rest.txt:batch 789: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7019 in, 604 out; cost $0.0006; latency p50 2.71 s, p95 4.48 s; wall 4.75 s
rest.txt:batch 790: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7550 in, 686 out; cost $0.0006; latency p50 3.39 s, p95 4.08 s; wall 4.22 s
rest.txt:batch 791: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7668 in, 739 out; cost $0.0006; latency p50 3.36 s, p95 4.61 s; wall 4.86 s
rest.txt:batch 792: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7571 in, 700 out; cost $0.0006; latency p50 2.81 s, p95 4.48 s; wall 4.78 s
rest.txt:batch 793: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6605 in, 663 out; cost $0.0005; latency p50 2.20 s, p95 2.70 s; wall 2.77 s
rest.txt:batch 794: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6130 in, 594 out; cost $0.0005; latency p50 2.03 s, p95 3.92 s; wall 4.12 s
rest.txt:batch 795: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6463 in, 583 out; cost $0.0005; latency p50 2.48 s, p95 5.24 s; wall 5.38 s
rest.txt:batch 796: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6782 in, 680 out; cost $0.0005; latency p50 2.91 s, p95 3.82 s; wall 3.99 s
rest.txt:batch 797: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7157 in, 615 out; cost $0.0006; latency p50 3.09 s, p95 3.79 s; wall 3.91 s
rest.txt:batch 798: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7456 in, 685 out; cost $0.0006; latency p50 3.19 s, p95 4.21 s; wall 4.59 s
rest.txt:batch 799: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7391 in, 688 out; cost $0.0006; latency p50 3.16 s, p95 3.56 s; wall 3.59 s
rest.txt:batch 800: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7035 in, 681 out; cost $0.0006; latency p50 1.80 s, p95 2.26 s; wall 2.35 s
rest.txt:batch 801: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6575 in, 608 out; cost $0.0005; latency p50 2.05 s, p95 3.48 s; wall 3.60 s
rest.txt:batch 802: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 7454 in, 653 out; cost $0.0005; latency p50 3.29 s, p95 3.64 s; wall 3.70 s
rest.txt:batch 803: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 8075 in, 696 out; cost $0.0006; latency p50 5.21 s, p95 6.81 s; wall 7.06 s
rest.txt:batch 804: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6896 in, 712 out; cost $0.0006; latency p50 3.57 s, p95 5.04 s; wall 5.42 s
rest.txt:batch 805: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6075 in, 614 out; cost $0.0005; latency p50 3.40 s, p95 3.91 s; wall 3.93 s
rest.txt:batch 806: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6404 in, 685 out; cost $0.0005; latency p50 2.76 s, p95 5.10 s; wall 6.02 s
rest.txt:batch 807: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6722 in, 701 out; cost $0.0005; latency p50 2.20 s, p95 4.17 s; wall 4.23 s
rest.txt:batch 808: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 6970 in, 675 out; cost $0.0006; latency p50 2.43 s, p95 2.96 s; wall 2.99 s
rest.txt:batch 809: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5338 in, 530 out; cost $0.0004; latency p50 1.78 s, p95 17.67 s; wall 29.74 s
rest.txt:batch 810: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5422 in, 575 out; cost $0.0004; latency p50 2.84 s, p95 3.82 s; wall 3.95 s
rest.txt:batch 811: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5593 in, 574 out; cost $0.0004; latency p50 2.40 s, p95 3.58 s; wall 3.69 s
rest.txt:batch 812: 10 requests, 10 recorded, 0 invalid, 0 failed; tokens 5544 in, 585 out; cost $0.0004; latency p50 3.87 s, p95 5.42 s; wall 5.63 s
rest.txt:batch 813: 6 requests, 6 recorded, 0 invalid, 0 failed; tokens 3158 in, 317 out; cost $0.0002; latency p50 1.44 s, p95 1.70 s; wall 1.70 s
rest.txt:recorded: 6501 merge, 1023 split, 8 unsure
adjudications: 7568 verdicts: 357 merges joining 357 clusters into others, 458 splits
crosswalk: 458 new donors, 2610 keys re-pointed, 357 redirects
loaded build 20261103T175128Z into gold_build (aggregates 72.86 s, copy 96.19 s)
published build 20261103T175128Z of 2024
```
