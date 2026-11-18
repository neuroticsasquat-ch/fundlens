# fundlens

[![Dataset: CC BY 4.0](https://img.shields.io/badge/dataset-CC%20BY%204.0-blue)](https://data.fundlens.org/v1/README.md)

Free public campaign-finance platform: donor, candidate and committee money for every federal
race since 1980, presented by race, with individual donors resolved across name, employer and
address variants. The resolved dataset is the product; the web app at
[fundlens.org](https://fundlens.org) is its demo.

## Dataset

The resolved data is published as an open dataset at
[data.fundlens.org](https://data.fundlens.org/v1/README.md): every federal cycle since 1980, as Parquet, a new
snapshot each week. It holds the contributions, contributors, committees, candidates, races, independent
expenditures, committee transfers and organization receipts, plus the resolved donors and the crosswalk from each
contributor key to its donor. The [dataset README](https://data.fundlens.org/v1/README.md) describes the layout,
the manifest and each table's schema. Every 2024 contribution, in DuckDB:

```sh
duckdb -c "
SET VARIABLE files = (
  SELECT list('https://data.fundlens.org/v1/latest/' || f.path)
  FROM (SELECT unnest(tables.contribution.files) AS f
        FROM read_json('https://data.fundlens.org/v1/latest/manifest.json'))
  WHERE f.path LIKE 'contribution/cycle=2024/%');
SELECT count(*) AS contributions, sum(amount) AS dollars
FROM read_parquet(getvariable('files'));
"
```

Licensed [CC BY 4.0](https://data.fundlens.org/v1/LICENSE); attribute it as `fundlens (fundlens.org), CC BY 4.0`.
Whatever this license allows, federal law forbids using the contributors' names and addresses to solicit
contributions or for commercial purposes (52 U.S.C. §30111(a)(4), 11 CFR 104.15).

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
task db:seed     # the synthetic 2024 cycle through every pipeline step, into MinIO + Postgres
```

`docker compose exec app fundlens --help` runs the CLI. After changing dependencies
(`task deps:add -- <pkg>`), run `task build`.

### FEC header files

FEC's bulk files have no header row; their column names come from FEC's data dictionaries,
vendored under `src/fundlens/fec/headers/` so neither the pipeline nor the tests fetch them.
`task fec:headers -- --check` compares the vendored copies with FEC's live ones (exit 1 if any
differs); `task fec:headers` overwrites them. When a file changes, update its columns in
`src/fundlens/fec/files.py` to match: `tests/unit/test_fec_files.py` fails until they agree.

### The fixture cycle

`tests/fixtures/fec/2024/` is a small invented 2024 cycle written by hand as CSVs, one per bulk
file, with comments naming the hard case each block plants (earmarks, the Musk-style donor,
self-funding, refunds, an unmatched district, IEs). `tests/fec_fixture.py` zips them into FEC's
exact layout, and the tests' fake FEC server serves them, so tests and `task db:seed` run the
real `extract` with no network. `expected.yaml` beside them holds the totals, counts and donor
groupings the pipeline must produce; `tests/unit/test_fec_fixture.py` fails when a CSV edit
leaves it behind. `tests/fixtures/dime/` labels every counted contribution with the donor
behind it, DIME-style, for the resolution validator.

The SPA in `frontend/` has its own container, started with `task fe:dev` (Vite on
http://localhost:5180), and `fe:test`, `fe:lint`, `fe:typecheck`, `fe:build` targets; see
[frontend/README.md](frontend/README.md).

`openapi.json` at the root is the API's contract, and `frontend/src/api/schema.d.ts` the
client types generated from it; both are committed. After changing a route or a model in
`src/fundlens/api/`, run `task fe:generate` (stack and frontend up) and commit what it changes:
it exports the document (`task api:openapi`, which is `fundlens api --export-openapi`) and
regenerates the types. The document carries the package version, so a version bump in
`pyproject.toml` needs the same.

`docs/dataset/` is the public dataset's README, license, changelog and per-table JSON Schemas,
which `fundlens dataset --snapshot` publishes beside the snapshots. After changing a column of a
dataset table, describe it in `docs/dataset/columns.yaml`, run `task dataset:schema` to
regenerate `docs/dataset/schema/`, add a `docs/dataset/CHANGELOG.md` entry, and commit all three:
`tests/integration/test_dataset.py` fails until they agree with the files.

Pre-commit hooks call the same `task` targets, so they need the stack up (and `task fe:dev`
for a commit touching `frontend/`):

```sh
pre-commit install
```

## Production

`docker-compose.prod.yml` is deployed by Coolify (`api`, an idle `pipeline` and Postgres 18); set it up
with [docs/runbooks/coolify-setup.md](docs/runbooks/coolify-setup.md), after Part A of
[docs/runbooks/cloudflare-setup.md](docs/runbooks/cloudflare-setup.md) (DNS, R2, tokens, the SPA's
Worker). `task prod:check` validates the file, as CI does. The first data run, 2024 end to end, is
[docs/runbooks/first-run.md](docs/runbooks/first-run.md); what each run costs is recorded in
[docs/capacity.md](docs/capacity.md).

## CI and dependency updates

`.github/workflows/ci.yml` calls the shared workflows in `neuroticsasquat-ch/workflows` (`@v1`) on
every PR and push to `main`. They run on the runner, not in the dev containers: `python` (ruff,
pyright, the Alembic head and drift checks and the whole pytest suite against Postgres 18 and the
MinIO that `.github/ci/setup.sh` starts), `js` (oxlint, `tsc -b`, vitest and the build, only when
`frontend/` or the workflow changes) and `image` (builds the prod image, checks it doesn't run as
root, then `.github/ci/smoke.sh`). Two jobs of this repo's own sit beside them: `prod-check`
validates `docker-compose.prod.yml`, and `openapi-drift` regenerates `openapi.json` and the
frontend's client types and fails if either changed. The `ci` job gathers them all, and it is the
only required check, set by the `neuroticsasquat-ch` org rulesets.
Dependabot opens its PRs against the long-lived `updates/dependencies` branch.
`.github/workflows/dependencies.yml` keeps that branch synced with `main` and auto-merges the PRs
into it once `ci` passes. It never promotes the branch to `main`, because every merge to `main`
redeploys `pipeline` and kills whatever runbook step is running in it. A person merges the
promotion PR when nothing is in flight.

## License

Code: [MIT](LICENSE). The published dataset carries its own license (CC BY 4.0), described with
the dataset.
