"""The process's resident memory, from `/proc/self/status` (NEU-2408)."""

from fundlens.memory import peak_resident_gib, resident_and_peak_gib, resident_gib


def test_resident_memory_is_above_nothing_and_never_above_its_peak() -> None:
    assert 0 < resident_gib() <= peak_resident_gib()


def test_one_read_gives_resident_memory_no_higher_than_its_peak() -> None:
    resident, peak = resident_and_peak_gib()
    assert 0 < resident <= peak
