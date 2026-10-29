---
status: accepted
---

# Manual overrides live in git; the crosswalk and model adjudications live in Postgres, mirrored to R2

The three kinds of resolution state have different authors and different reproducibility. Human merge/split assertions are tiny and should be reviewed, so they are a YAML file in the repo applied on every run; git is their history and their backup. LLM adjudications are generated from a cluster, a model and a prompt version, so they are reproducible by re-running and sit in a Postgres table keyed by cluster fingerprint and model version. The crosswalk (cluster fingerprint → `donor_id`, a sequential integer assigned on first sight, never reused) is generated but must survive every rebuild or donor URLs break, so it is a Postgres table snapshotted to R2 on every publish and covered by the nightly pg_dump. Putting the crosswalk in git would have the box pushing multi-megabyte commits weekly; putting overrides only in Postgres would hide them from code review.

## Consequences

- A donor merge keeps the lower `donor_id` and records a redirect so old URLs resolve.
- The crosswalk and the adjudications table are the only data the pipeline cannot regenerate from R2 bronze alone.
