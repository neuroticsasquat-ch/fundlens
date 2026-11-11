"""A time bound that a neighbouring xdist worker's burst cannot fail (NEU-2268)."""

from collections.abc import Callable


def assert_within(bound: float, measure: Callable[[], float], *, attempts: int = 3) -> None:
    """Pass if any of up to `attempts` runs of `measure` (seconds taken) is under `bound`
    seconds: a regression fails every attempt, a passing burst of load on the box does not."""
    taken: list[float] = []
    for _ in range(attempts):
        taken.append(measure())
        if taken[-1] < bound:
            return
    tried = ", ".join(f"{seconds * 1000:.1f} ms" for seconds in taken)
    raise AssertionError(f"{tried}: none under {bound * 1000:.0f} ms")
