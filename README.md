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

Pre-commit hooks call the same `task` targets, so they need the stack up:

```sh
pre-commit install
```

## License

Code: [MIT](LICENSE). The published dataset carries its own license (CC BY 4.0), described with
the dataset.
