"""The process's resident memory, now and at its highest, read from `/proc/self/status`.

Both are the kernel's own figures, `VmRSS` and `VmHWM`, from one read of the file, so they agree
with each other where `ru_maxrss` lags them (NEU-2408). The pipeline runs only in its Linux
container, so no other platform is handled, and a missing file or field raises.

`VmHWM` is not monotonic: the kernel reports the larger of a stored high-water mark, updated only
at some events such as an unmap, and current RSS, read from per-CPU counters that are only
approximate. So a later read can be lower than an earlier one. The peak given here is the highest
`VmHWM` or `VmRSS` this process has read, so it never falls (NEU-2455).
"""

import threading
from pathlib import Path

STATUS = Path("/proc/self/status")

# The highest `VmHWM` or `VmRSS` read so far in this process, in GiB. The lock keeps raising it one
# step, should two threads read at once.
_peak_gib = 0.0
_peak_lock = threading.Lock()


def resident_and_peak_gib() -> tuple[float, float]:
    """The process's resident memory now (`VmRSS`) and the highest it has been, in GiB, from one
    read of the file: the highest `VmHWM` or `VmRSS` read so far, never below the resident figure
    and never lower than an earlier call's."""
    fields: dict[str, float] = {}
    for line in STATUS.read_text().splitlines():
        name, _, value = line.partition(":")
        if name in ("VmRSS", "VmHWM"):
            # The file gives memory in kB, which are KiB.
            fields[name] = int(value.split()[0]) / 2**20
    try:
        resident, high_water = fields["VmRSS"], fields["VmHWM"]
    except KeyError as missing:
        raise LookupError(f"{STATUS} has no {missing.args[0]}") from None
    global _peak_gib
    with _peak_lock:
        _peak_gib = max(_peak_gib, high_water, resident)
        return resident, _peak_gib


def resident_gib() -> float:
    """The process's resident memory now (`VmRSS`), in GiB."""
    return resident_and_peak_gib()[0]


def peak_resident_gib() -> float:
    """The highest resident memory the process has had, in GiB: as `resident_and_peak_gib`'s."""
    return resident_and_peak_gib()[1]
