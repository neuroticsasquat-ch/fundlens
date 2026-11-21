# fundlens

Free public campaign-finance platform: donor, candidate and committee money for every federal race since 1980, presented by race, with individual donors resolved across name/employer/address variants. The resolved dataset is the product; the web app at fundlens.org is its demo. Runs as a weekly batch ELT on the Hetzner Coolify box with R2 as the store of record.

## Linear

linear_initiative: fundlens
linear_team: NEU
linear_repo: fundlens

Project: P-NEU-105 "fundlens v1: federal races, resolved donors, public dataset" (initiative I-16)
Project: P-NEU-107 "fundlens: every FEC dollar" (initiative I-16)

## Docs

specs_dir: docs

Project spec: `docs/specs/fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md` — the shared reference for every ticket; read it before implementing anything.
Every FEC dollar spec: `docs/specs/fundlens-every-fec-dollar-project-spec.md` — the shared reference for P-NEU-107's tickets, read with the v1 project spec: the file catalogue, the milestones' shared contracts, and how a new silver table joins the dataset.
Glossary: `CONTEXT.md` (terms are enforced in code and tickets; avoid the listed synonyms).
Decisions: `docs/adr/` (0001 batch ELT on one machine, 0002 R2 is the source of truth, 0003 monorepo + Worker frontend, 0004 earmarks count once, 0005 overrides in git / crosswalk in Postgres, 0006 itemized via DuckDB in the API, 0007 gold loads by DuckDB → CSV → `COPY`, 0008 Mantine is the SPA's component library, 0009 resolution quality is scored against DIME by FEC ids, 0010 clusters are re-clustered by constrained single-linkage, 0011 organizations are grouped by normalized name, not resolved, 0012 payees are grouped like organizations and get pages; people and sub-items do not).
Original brief: `docs/campaign-finance-handover.md`.

## Layout

One repo, one Python package (`src/fundlens`: pipeline + API, one image, per-service entrypoints) and `frontend/` (React + Vite + TypeScript SPA deployed by Cloudflare Workers Builds from this subdirectory).

## Toolchain

Backend: Python 3.13, uv, ruff, pyright strict, pytest, typer, FastAPI, psycopg 3 (plain SQL), Alembic (`app` schema only), DuckDB, Splink. Postgres 18. Frontend: pnpm, Vite, React, TypeScript, TanStack Query, ECharts, oxlint, vitest, Node 24.

Everything runs in the container: never run `pytest`, `ruff`, `pyright`, `alembic`, `python` or `pnpm` on the host — use `task` targets, which `docker compose exec` into the service. Pre-commit hooks run inside containers too. `task format` before committing; stage files by name.

## Branch flow

Greenfield: every ticket branches from and PRs into `main`. Conventional Commits with the Linear ID parenthetical; no `Co-Authored-By` trailer.
