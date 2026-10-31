"""Alembic environment for the `app` schema (spec §7.3, ADR-0005).

Only `app` is migrated, and the version table lives in it too. The `gold*` schemas belong to
the pipeline, which rebuilds them every run, so autogenerate and `alembic check` never look
outside `app`.
"""

from logging.config import fileConfig

import psycopg
from alembic import context
from sqlalchemy import Connection, NullPool, create_engine

from fundlens.app_schema import SCHEMA, metadata
from fundlens.settings import get_settings

config = context.config
# No file name when a test builds the Config in-process; `fileConfig` would then replace
# pytest's log handlers.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def include_name(name: str | None, type_: str, parent_names: object) -> bool:
    if type_ == "schema":
        return name == SCHEMA
    return True


def run_migrations_offline() -> None:
    context.configure(
        dialect_name="postgresql",
        target_metadata=metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
        version_table_schema=SCHEMA,
    )
    with context.begin_transaction():
        context.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema=SCHEMA,
    )
    with context.begin_transaction():
        # The version table lives in `app`, so the schema has to exist before Alembic creates
        # it; inside Alembic's transaction so a failed first upgrade leaves nothing behind.
        connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        context.run_migrations()


def run_migrations_online() -> None:
    # `attributes["conninfo"]` is set only by the migration tests, which run Alembic in-process
    # against a scratch database. Through psycopg's own `connect`, so DATABASE_URL may be a URL
    # or a libpq keyword string, and SQLAlchemy never has to translate it.
    conninfo: str = config.attributes.get("conninfo") or get_settings().database_url
    engine = create_engine(
        "postgresql+psycopg://", creator=lambda: psycopg.connect(conninfo), poolclass=NullPool
    )
    with engine.connect() as connection:
        do_run_migrations(connection)
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
