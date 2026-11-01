"""The `app` schema: the authored tables the pipeline cannot regenerate (ADR-0005, spec §7.3).

Declared here only as Alembic's `target_metadata`, so `alembic check` fails when a migration
and this declaration disagree on a table, column or index. Autogenerate compares neither
sequences nor CHECK constraints: `tests/integration/test_migrations.py` pins those against the
migrated database instead. Nothing queries through it: reads and writes are plain SQL over
psycopg, like everything else. The `gold*` schemas are not declared: the pipeline rebuilds them
from `sql/gold` every run and they are never migrated.
"""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    Sequence,
    Table,
    Text,
)

SCHEMA = "app"

metadata = MetaData(schema=SCHEMA)

# contributor_key → donor_id. Rows are irreplaceable: donor URLs are built from these ids.
crosswalk = Table(
    "crosswalk",
    metadata,
    Column("contributor_key", Text, primary_key=True),
    Column("donor_id", BigInteger, nullable=False),
    Column("assigned_at", DateTime(timezone=True)),
    Column("build_id", Text),
    Index("ix_crosswalk_donor_id", "donor_id"),
)

# A merged-away donor_id → the one it merged into, so old donor URLs still resolve (301).
donor_redirect = Table(
    "donor_redirect",
    metadata,
    # Not autoincrement: a lone integer primary key would otherwise become a BIGSERIAL with a
    # sequence of its own. Ids come from the crosswalk, never from this table.
    Column("old_donor_id", BigInteger, primary_key=True, autoincrement=False),
    Column("donor_id", BigInteger, nullable=False),
)

# One model's verdict on one ambiguous cluster under one prompt version (spec §6.8).
adjudication = Table(
    "adjudication",
    metadata,
    Column("cluster_fingerprint", Text),
    Column("model", Text),
    Column("prompt_version", Text),
    Column("decision", Text),
    Column("confidence", Numeric()),
    Column("reason", Text),
    Column("decided_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("cluster_fingerprint", "model", "prompt_version"),
    CheckConstraint("decision IN ('merge', 'split', 'unsure')", name="ck_adjudication_decision"),
)

# A filing whose candidate matches no seat in the cycle's seat calendar (spec §5.2).
unmatched_filing = Table(
    "unmatched_filing",
    metadata,
    Column("cycle", Integer),
    Column("candidate_id", Text),
    Column("office", Text),
    Column("state", Text),
    Column("district", Text),
    Column("seen_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("cycle", "candidate_id"),
)

# One model's resolution scored against DIME for one cycle, overall or over the top donors by
# matched dollars (NEU-2054, ADR-0009). The pair counts are kept so cycles can be pooled later.
resolution_quality = Table(
    "resolution_quality",
    metadata,
    Column("model_version", Text),
    Column("cycle", Integer),
    Column("scope", Text),
    Column("dime_version", Text, nullable=False),
    Column("top_limit", Integer),
    Column("contribution_rows", BigInteger, nullable=False),
    Column("matched_rows", BigInteger, nullable=False),
    Column("labelled_keys", BigInteger, nullable=False),
    Column("correct_pairs", BigInteger, nullable=False),
    Column("predicted_pairs", BigInteger, nullable=False),
    Column("true_pairs", BigInteger, nullable=False),
    Column("precision", Numeric()),
    Column("recall", Numeric()),
    Column("validated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("model_version", "cycle", "scope"),
    CheckConstraint("scope IN ('overall', 'top')", name="ck_resolution_quality_scope"),
)

# A never-seen contributor key's new donor_id (spec §6.6). Never reset: ids are never reused.
donor_id_seq = Sequence("donor_id_seq", metadata=metadata)
