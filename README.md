# fundlens

Free public campaign-finance platform: donor, candidate and committee money for every federal
race since 1980, presented by race, with individual donors resolved across name, employer and
address variants. The resolved dataset is the product; the web app at
[fundlens.org](https://fundlens.org) is its demo.

## Where to start

- [Project spec](docs/specs/fundlens-v1-federal-races-resolved-donors-public-dataset-project-spec.md):
  the shared reference for every piece of v1.
- [Glossary](CONTEXT.md): the domain terms, as used in code and tickets.
- [Architecture decisions](docs/adr/): what was decided and why.
- [Original brief](docs/campaign-finance-handover.md).

## Local development

Everything runs in containers; the host needs only Docker and
[go-task](https://taskfile.dev).

```sh
task up          # app, Postgres 18 and MinIO (the R2 stand-in), waits until healthy
task test        # pytest (task test:unit / task test:integration for one suite)
task lint        # ruff check
task format      # ruff format
task typecheck   # pyright, strict
task shell       # bash inside the app container
```

`docker compose exec app fundlens --help` runs the CLI. After changing dependencies
(`task deps:add -- <pkg>`), run `task build`.

The SPA in `frontend/` has its own container, started with `task fe:dev` (Vite on
http://localhost:5180), and `fe:test`, `fe:lint`, `fe:typecheck`, `fe:build` targets; see
[frontend/README.md](frontend/README.md).

Pre-commit hooks call the same `task` targets, so they need the stack up (and `task fe:dev`
for a commit touching `frontend/`):

```sh
pre-commit install
```

## Production

`docker-compose.prod.yml` is deployed by Coolify (`api`, an idle `pipeline` and Postgres 18); set it up
with [docs/runbooks/coolify-setup.md](docs/runbooks/coolify-setup.md). `task prod:check` validates the
file, as CI does.

## CI and dependency updates

`.github/workflows/ci.yml` builds the dev image and runs lint, format check, typecheck and the
whole pytest suite against the compose stack on every PR and push to `main`; its `test` job is a
required check on `main`. So is its `frontend` job (typecheck, oxlint, vitest, build in the
frontend container), which runs only when `frontend/`, the compose file, the Taskfile or the
workflow changes and otherwise reports as skipped.
Dependabot opens its PRs against the long-lived `updates/dependencies` branch, and
`merge-main-into-dependencies.yml` merges `main` into it every Saturday before Dependabot runs.
The branch and the repository rulesets are created, and kept as declared, by
`scripts/github-rulesets.sh` (run on the host with `gh` and `jq`; safe to re-run).

## License

Code: [MIT](LICENSE). The published dataset carries its own license (CC BY 4.0), described with
the dataset.
