# fundlens frontend

The SPA behind [fundlens.org](https://fundlens.org): React, Vite and TypeScript, served by a
static-assets Cloudflare Worker (`wrangler.jsonc`) that Workers Builds deploys from this
directory (spec §8, ADR-0003). Like the backend, it runs only in a container: the `frontend`
compose service (`node:24`, this directory bind-mounted). Run everything from the repo root.

```sh
task fe:dev        # start the service: pnpm install, then Vite on http://localhost:5180
task fe:test       # vitest
task fe:lint       # oxlint, warnings fail
task fe:typecheck  # tsc -b
task fe:build      # production bundle into frontend/dist/
task fe:worker     # wrangler dev serving dist/ on http://localhost:8780, as the Worker will
```

`task fe:worker` is `npx wrangler dev` run inside the service (`pnpm exec wrangler dev --ip
0.0.0.0 --port 8787`, published on host port 8780). It serves whatever `task fe:build` last
wrote, so build first; any path that is not a built file gets `index.html`, as in production.

`task down` stops the frontend with the rest of the stack. Add a dependency with
`docker compose exec frontend pnpm add <pkg>` (`-D` for a dev one); the lockfile lands on the
host through the bind mount.

## Configuration

Read at build time and baked into the bundle (see `.env.example`):

| Variable | Meaning |
| --- | --- |
| `VITE_API_BASE_URL` | Origin of the API. Unset means same-origin `/v1`, which the dev server proxies to the `app` service. Workers Builds sets `https://api.fundlens.org`. |
| `WORKERS_CI_COMMIT_SHA` | Set by Workers Builds; the page shows its first 7 characters as the build. Anywhere else the build reads `dev`. |

## Deploy

Workers Builds (configured by [the Cloudflare runbook](../docs/runbooks/cloudflare-setup.md), not here): root directory `frontend`,
build command `pnpm install --frozen-lockfile && pnpm build`, deploy command
`npx wrangler deploy`, watch paths `frontend/**`, production branch `main`, preview
deployments on PRs.

As built: Worker \fundlens`, custom domain`fundlens.org`(docs/runbooks/cloudflare-setup.md).`
