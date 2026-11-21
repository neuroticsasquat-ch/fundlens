"""The process's resident memory, now and at its highest, read from `/proc/self/status`.

Both are the kernel's own figures, `VmRSS` and `VmHWM`, from one read of the file, so they agree
with each other where `ru_maxrss` lags them (NEU-2408). The pipeline runs only in its Linux
container, so no other platform is handled, and a missing file or field raises.
"""

from pathlib import Path

STATUS = Path("/proc/self/status")


def resident_and_peak_gib() -> tuple[float, float]:
    """The process's resident memory now (`VmRSS`) and the highest it has been (`VmHWM`), in GiB,
    from one read of the file."""
    fields: dict[str, float] = {}
    for line in STATUS.read_text().splitlines():
        name, _, value = line.partition(":")
        if name in ("VmRSS", "VmHWM"):
            # The file gives memory in kB, which are KiB.
            fields[name] = int(value.split()[0]) / 2**20
    try:
        return fields["VmRSS"], fields["VmHWM"]
    except KeyError as missing:
        raise LookupError(f"{STATUS} has no {missing.args[0]}") from None


def resident_gib() -> float:
    """The process's resident memory now (`VmRSS`), in GiB."""
    return resident_and_peak_gib()[0]


def peak_resident_gib() -> float:
    """The highest resident memory the process has had (`VmHWM`), in GiB."""
    return resident_and_peak_gib()[1]
