---
status: accepted
---

# Batch ELT on one machine, no queues, no workers, no managed database

The ~2025 attempt ran a claim-ticket microservice pipeline on Azure (Functions, storage queues, managed Postgres). Per-execution billing and queue chatter made a free public tool uneconomical, and the architecture spread one logical job across many small ones that were hard to make idempotent. FEC bulk data changes weekly for the current cycle and never for past cycles, so the whole pipeline is one scheduled job that rebuilds one cycle and republishes. DuckDB runs in-process (a library, not a service); Postgres is the only running datastore. Compute is the already-paid Hetzner Robot box.

## Consequences

- The CPU ceiling (2015 quad-core) is the real limit, not disk. Full-rebuild wall time is measured in v1 and is the trigger for moving the job to an ephemeral cloud runner (ADR-0002).
- Dagster/Prefect are not required; a single CLI with per-step completion markers is the orchestrator.
