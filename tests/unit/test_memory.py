"""The process's resident memory, from `/proc/self/status` (NEU-2408)."""

from pathlib import Path

import pytest

from fundlens import memory
from fundlens.memory import peak_resident_gib, resident_and_peak_gib, resident_gib


def test_resident_memory_is_above_nothing_and_never_above_its_peak() -> None:
    assert 0 < resident_gib() <= peak_resident_gib()


def test_one_read_gives_resident_memory_no_higher_than_its_peak() -> None:
    resident, peak = resident_and_peak_gib()
    assert 0 < resident <= peak


def status(rss_kib: int, hwm_kib: int) -> str:
    """A `/proc/self/status` with only the two fields read, in the kernel's kB."""
    return f"Name:\tpython\nVmHWM:\t{hwm_kib} kB\nVmRSS:\t{rss_kib} kB\n"


def test_the_peak_never_falls_when_the_kernels_high_water_mark_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The kernel's `VmHWM` can read lower than it did before: it is the larger of a stored mark,
    updated only at some events, and an approximate current RSS (NEU-2455). The peak returned is
    the highest seen, and never below the resident memory returned with it."""
    path = tmp_path / "status"
    monkeypatch.setattr(memory, "STATUS", path)
    monkeypatch.setattr(memory, "_peak_gib", 0.0)
    gib = 2**20

    path.write_text(status(rss_kib=3 * gib, hwm_kib=4 * gib))
    assert resident_and_peak_gib() == (3.0, 4.0)
    path.write_text(status(rss_kib=2 * gib, hwm_kib=3 * gib))
    assert resident_and_peak_gib() == (2.0, 4.0)
    assert peak_resident_gib() == 4.0
    # A resident figure above the kernel's mark raises the peak to it.
    path.write_text(status(rss_kib=5 * gib, hwm_kib=4 * gib))
    assert resident_and_peak_gib() == (5.0, 5.0)
