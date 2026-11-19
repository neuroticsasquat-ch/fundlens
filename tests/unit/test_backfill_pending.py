"""The backfill-pending tables (`paths.BACKFILL_PENDING`, CONTEXT.md, NEU-2352)."""

from fundlens import paths
from fundlens.load.gold import RESOLVED
from fundlens.publish.dataset import DATASET_TABLES


def test_every_backfill_pending_table_is_a_dataset_table_and_not_a_resolved_one() -> None:
    # A dataset table has a committed schema, which types its empty view when no build has it;
    # a resolved one would need a donor_id the empty view cannot give.
    assert paths.BACKFILL_PENDING <= set(DATASET_TABLES)
    assert not paths.BACKFILL_PENDING & RESOLVED
