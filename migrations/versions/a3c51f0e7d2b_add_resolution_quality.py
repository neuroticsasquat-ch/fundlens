"""Add `app.resolution_quality`, resolution scored against DIME (NEU-2054)

Revision ID: a3c51f0e7d2b
Revises: 5d8e919b342d
Create Date: 2026-11-01 00:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3c51f0e7d2b"
down_revision: str | None = "5d8e919b342d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resolution_quality",
        sa.Column("model_version", sa.Text()),
        sa.Column("cycle", sa.Integer()),
        sa.Column("scope", sa.Text()),
        sa.Column("dime_version", sa.Text(), nullable=False),
        sa.Column("top_limit", sa.Integer()),
        sa.Column("contribution_rows", sa.BigInteger(), nullable=False),
        sa.Column("matched_rows", sa.BigInteger(), nullable=False),
        sa.Column("labelled_keys", sa.BigInteger(), nullable=False),
        sa.Column("correct_pairs", sa.BigInteger(), nullable=False),
        sa.Column("predicted_pairs", sa.BigInteger(), nullable=False),
        sa.Column("true_pairs", sa.BigInteger(), nullable=False),
        sa.Column("precision", sa.Numeric()),
        sa.Column("recall", sa.Numeric()),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("model_version", "cycle", "scope"),
        sa.CheckConstraint("scope IN ('overall', 'top')", name="ck_resolution_quality_scope"),
        schema="app",
    )


def downgrade() -> None:
    op.drop_table("resolution_quality", schema="app")
