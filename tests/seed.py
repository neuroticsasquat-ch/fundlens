"""`task db:seed`: the 2024 fixture cycle through every pipeline step that exists, into MinIO and
Postgres, for local dev to browse (spec §12).

Serves the fixture zips on the fake FEC server and runs the real CLI against it with one build:
`extract`, `seats --report` (whose unmatched filings a transform check reads), `transform`,
`resolve --full` (whose model is saved under the build), `load`, then `publish` (whose Cloudflare
purge is skipped: dev has no zone). Each step that later tickets add goes on the end of `STEPS`.
Re-runnable: `extract` finds bronze unchanged and downloads nothing, and every other step writes
a fresh build, which `publish` swaps in over the last one. Run from the repo root inside the app
container (`python -m tests.seed`), with the `app` schema migrated.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import typer

from fundlens import cli, paths
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.fake_fec import FakeFec

STEPS = (
    ("extract", "--cycle", str(fec_fixture.CYCLE)),
    ("seats", "--cycle", str(fec_fixture.CYCLE), "--report"),
    ("transform", "--cycle", str(fec_fixture.CYCLE)),
    ("resolve", "--full"),
    ("load", "--cycle", str(fec_fixture.CYCLE)),
    ("publish", "--cycle", str(fec_fixture.CYCLE)),
)
# The repo's own overrides name production's keys, which the fixture cycle does not have.
NO_OVERRIDES = Path(__file__).parent / "fixtures" / "resolution" / "none.yaml"
# Every other step is told the build; `publish` reads it from `gold_build.meta`.
WITHOUT_BUILD_ID = frozenset({"publish"})


def seed() -> str:
    """Run every step on the fixture cycle under one new build; that build's id."""
    build_id = paths.format_build_id(datetime.now(UTC))
    with FakeFec().running() as fec:
        fec_fixture.serve(fec)
        # The CLI reads its settings from the environment; only the FEC address and the
        # overrides are the seed's.
        os.environ["FEC_BULK_URL"] = fec.url
        os.environ["OVERRIDES_PATH"] = str(NO_OVERRIDES)
        get_settings.cache_clear()
        try:
            for step in STEPS:
                typer.echo(f"$ fundlens {' '.join(step)}")
                # `standalone_mode=False`: a failed step raises here instead of exiting the process
                # from inside the fake server's context, and the rest are not run.
                args = [*step] if step[0] in WITHOUT_BUILD_ID else [*step, "--build-id", build_id]
                code = cli.app(args, standalone_mode=False)
                # A step that ends with `typer.Exit(n)` returns `n` rather than raising.
                if code:
                    raise SystemExit(f"fundlens {step[0]} exited {code}")
        finally:
            del os.environ["FEC_BULK_URL"], os.environ["OVERRIDES_PATH"]
            get_settings.cache_clear()
    typer.echo(f"seeded cycle {fec_fixture.CYCLE} as build {build_id}")
    return build_id


if __name__ == "__main__":
    seed()
