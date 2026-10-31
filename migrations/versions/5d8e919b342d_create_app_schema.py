"""Create the `app` schema's tables and donor_id sequence (NEU-2031)

Revision ID: 5d8e919b342d
Revises:
Create Date: 2026-10-29 00:00:00.000000+00:00

The schema itself is created by env.py, before the version table it also holds, so the
downgrade drops what this revision made and leaves `app` and `alembic_version` in place.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5d8e919b342d"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crosswalk",
        sa.Column("contributor_key", sa.Text(), primary_key=True),
        sa.Column("donor_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        sa.Column("build_id", sa.Text()),
        schema="app",
    )
    op.create_index("ix_crosswalk_donor_id", "crosswalk", ["donor_id"], schema="app")
    op.create_table(
        "donor_redirect",
        sa.Column("old_donor_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("donor_id", sa.BigInteger(), nullable=False),
        schema="app",
    )
    op.create_table(
        "adjudication",
        sa.Column("cluster_fingerprint", sa.Text()),
        sa.Column("model", sa.Text()),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("decision", sa.Text()),
        sa.Column("confidence", sa.Numeric()),
        sa.Column("reason", sa.Text()),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("cluster_fingerprint", "model", "prompt_version"),
        sa.CheckConstraint(
            "decision IN ('merge', 'split', 'unsure')", name="ck_adjudication_decision"
        ),
        schema="app",
    )
    op.create_table(
        "unmatched_filing",
        sa.Column("cycle", sa.Integer()),
        sa.Column("candidate_id", sa.Text()),
        sa.Column("office", sa.Text()),
        sa.Column("state", sa.Text()),
        sa.Column("district", sa.Text()),
        sa.Column("seen_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("cycle", "candidate_id"),
        schema="app",
    )
    op.execute(sa.schema.CreateSequence(sa.Sequence("donor_id_seq", schema="app")))


def downgrade() -> None:
    op.execute(sa.schema.DropSequence(sa.Sequence("donor_id_seq", schema="app")))
    op.drop_table("unmatched_filing", schema="app")
    op.drop_table("adjudication", schema="app")
    op.drop_table("donor_redirect", schema="app")
    op.drop_index("ix_crosswalk_donor_id", table_name="crosswalk", schema="app")
    op.drop_table("crosswalk", schema="app")
