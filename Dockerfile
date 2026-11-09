FROM python:3.13-slim AS base

# UV_PROJECT_ENVIRONMENT: `uv sync` installs into the image's system Python rather than a
# .venv, so `fundlens`, `pytest` and `pyright` are on PATH with nothing to activate.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_PYTHON_DOWNLOADS=never

# opentelemetry-distro defaults the OTLP protocol to gRPC, but only the HTTP exporter is
# installed. Pin http/protobuf so the absent gRPC one is never looked up. The endpoint and the
# resource attributes come from the deploy env (spec §10.1).
ENV OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install from uv.lock, the set CI tests, not from pyproject.toml's ranges: those resolve to
# whatever is newest at build time, so CI, dev and prod could each run different versions.
# --locked fails the build when the lockfile is stale, as it fails CI. --inexact keeps what
# the lockfile doesn't list -- pip and uv itself -- in /usr/local.
COPY pyproject.toml uv.lock README.md ./


FROM base AS dev
# pyright downloads its own prebuilt node (via nodeenv), and that binary links against
# libatomic, which python:*-slim does not ship. Without it the pyright hook dies with
# "libatomic.so.1: cannot open shared object file".
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*
# The `dev` dependency group installs by default (`--no-dev` keeps it out of prod).
RUN uv sync --locked --inexact --no-cache --no-install-project
# Bake the node download into the image so the first pre-commit run does not pay for it
# (and does not need the network).
RUN pyright --version
COPY src/ src/
RUN uv sync --locked --inexact --no-cache
# Idle: every task runs through `docker compose exec app …`.
CMD ["sleep", "infinity"]


FROM base AS prod

RUN uv sync --locked --inexact --no-cache --no-dev --no-install-project

COPY src/ src/
# What `fundlens transform` runs (`SQL_DIR`, spec §3.1).
COPY sql/ sql/
# The overrides `fundlens resolve` applies (`OVERRIDES_PATH`, spec §6.5).
COPY resolution/ resolution/
# `alembic upgrade head` runs from /app in the pipeline container (spec §7.3).
COPY alembic.ini ./
COPY migrations/ migrations/

RUN uv sync --locked --inexact --no-cache --no-dev --no-editable

# Prod runs as a non-root user (the shared CI's image check, NEU-2239). Only this stage:
# the dev stage keeps root, because `task deps:*` runs `uv` against /usr/local and the
# bind-mounted repo. The UID/GID are fixed so the host can chown the volumes prod mounts under
# DATA_DIR to them (docs/runbooks/coolify-setup.md). DATA_DIR is created owned by it too: its
# `reference/` and `markers/` live outside the volumes, and a fresh volume mounted below it starts
# out with the ownership of the directory the image has there. The home directory is DuckDB's
# default extension directory.
RUN groupadd --system --gid 10001 fundlens \
    && useradd --system --uid 10001 --gid fundlens --create-home fundlens \
    && mkdir -p /data/fundlens/bronze /data/fundlens/silver /data/fundlens/scratch \
        /data/fundlens/resolution \
    && chown -R fundlens:fundlens /data/fundlens

USER fundlens

# No CMD: docker-compose.prod.yml gives each service its own (`api` runs uvicorn, `pipeline`
# idles for Coolify's scheduled tasks; spec §3.2).
