"""`task db:seed`: the 2024 fixture cycle through every pipeline step that exists, into MinIO and
Postgres, for local dev to browse (spec §12).

Serves the fixture zips on the fake FEC server and runs the real CLI against it with one build:
`extract`, then `seats --report`. Each step that later tickets add goes on the end of `STEPS`.
Re-runnable: `extract` finds bronze unchanged and downloads nothing, and every other step writes
a fresh build. Run from the repo root inside the app container (`python -m tests.seed`), with
the `app` schema migrated.
"""

import os
from datetime import UTC, datetime

import typer

from fundlens import cli, paths
from fundlens.settings import get_settings
from tests import fec_fixture
from tests.fake_fec import FakeFec

STEPS = (
    ("extract", "--cycle", str(fec_fixture.CYCLE)),
    ("seats", "--cycle", str(fec_fixture.CYCLE), "--report"),
)


def seed() -> str:
    """Run every step on the fixture cycle under one new build; that build's id."""
    build_id = paths.format_build_id(datetime.now(UTC))
    with FakeFec().running() as fec:
        fec_fixture.serve(fec)
        # The CLI reads its settings from the environment; only the FEC address is the seed's.
        os.environ["FEC_BULK_URL"] = fec.url
        get_settings.cache_clear()
        try:
            for step in STEPS:
                typer.echo(f"$ fundlens {' '.join(step)}")
                # `standalone_mode=False`: a failed step raises here instead of exiting the process
                # from inside the fake server's context, and the rest are not run.
                code = cli.app([*step, "--build-id", build_id], standalone_mode=False)
                # A step that ends with `typer.Exit(n)` returns `n` rather than raising.
                if code:
                    raise SystemExit(f"fundlens {step[0]} exited {code}")
        finally:
            del os.environ["FEC_BULK_URL"]
            get_settings.cache_clear()
    typer.echo(f"seeded cycle {fec_fixture.CYCLE} as build {build_id}")
    return build_id


if __name__ == "__main__":
    seed()
