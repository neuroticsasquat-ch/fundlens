"""The nickname table (NEU-2188): upstream's rows read both ways, less fundlens's exclusions."""

import pytest

from fundlens.resolve import nicknames

UPSTREAM = "name1,relationship,name2\nharold,has_nickname,hal\nharold,has_nickname,harry\n"


def test_the_vendored_table_links_a_nickname_both_ways_less_its_exclusions() -> None:
    pairs = nicknames.pairs()

    assert {("HAROLD", "HAL"), ("HAL", "HAROLD")} <= pairs
    assert {("AARON", "ERIN"), ("ERIN", "AARON")}.isdisjoint(pairs)
    # Two nicknames of one name are not linked by it.
    assert ("HAL", "HARRY") not in pairs


def test_an_exclusion_removes_its_pair_both_ways() -> None:
    excluded = "name1,name2,reason\nharold,harry,a test\n"

    found = nicknames._pairs(UPSTREAM, excluded)  # pyright: ignore[reportPrivateUsage]

    assert found == {("HAROLD", "HAL"), ("HAL", "HAROLD")}


@pytest.mark.parametrize(
    ("upstream", "excluded", "message"),
    [
        (UPSTREAM, "name1,name2,reason\nharold,henry,stale\n", "has no harold,henry"),
        (UPSTREAM, "name1,name2,reason\nhal,hal,itself\n", "paired with itself"),
        (UPSTREAM, "name1,name2,reason\nharold,,empty\n", "a name is empty"),
        (UPSTREAM + "hal,is_nickname_of,harold\n", "name1,name2,reason\n", "not has_nickname"),
        (UPSTREAM + "hal,has_nickname\n", "name1,name2,reason\n", "2 fields, not 3"),
        ("name,nickname\n", "name1,name2,reason\n", "the header must be"),
    ],
)
def test_a_malformed_row_is_refused_by_line(upstream: str, excluded: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        nicknames._pairs(upstream, excluded)  # pyright: ignore[reportPrivateUsage]
