---
status: accepted
---

# One repo: pipeline + API as one Python package and image; SPA in frontend/ deployed as a Cloudflare Worker

Pipeline and API share the canonical schema, the gold DDL and the DuckDB-over-Parquet readers, so they live in one Python package built into one image with per-service entrypoints (argelander pattern) and deployed as two services in one Coolify project. The web UI is a React + Vite + TypeScript SPA because the race, donor and committee views want client-side sorting, filtering and charts; it is deployed by Cloudflare Workers Builds from the `frontend/` subdirectory (root directory + build watch paths) rather than from a separate repo. Keeping it in the monorepo means the FastAPI OpenAPI schema and the generated TypeScript client change in the same PR, one CI pipeline, and one `repo:fundlens` label.

## Considered options

- **Split `fundlens-frontend` repo** (tvbf, boone-gifts pattern). Rejected: those splits predate the monorepo convention and exist for a separately-owned deploy cadence, which a solo project does not have. The API contract would need a published client package to stay in sync.
- **FastAPI + Jinja2 + HTMX, server-rendered.** Rejected: cache-friendlier and no second toolchain, but the interactive views were judged worth the SPA.
