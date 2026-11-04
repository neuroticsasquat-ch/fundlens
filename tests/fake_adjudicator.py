"""A stand-in for the adjudication model: answers each candidate from the replies in
`fixtures/resolution/adjudication_replies.yaml`, matched by the candidate's contributor keys, and
records every request, so a test can count what was sent (spec §12: no network)."""

import threading
from pathlib import Path
from typing import TypedDict, cast

import yaml

from fundlens.resolve.adjudicate import Ask, Reply

REPLIES = Path(__file__).parent / "fixtures" / "resolution" / "adjudication_replies.yaml"
# What the fake answers a candidate with no recorded reply.
UNRECORDED = Reply(
    '{"decision": "unsure", "confidence": 0, "reason": "No reply was recorded."}', 500, 20, 0.00008
)


class _Recorded(TypedDict):
    keys: list[str]
    content: str
    prompt_tokens: int
    completion_tokens: int
    cost: float


def recorded(path: Path = REPLIES) -> dict[frozenset[str], Reply]:
    """Each recorded reply, by the contributor keys of the candidate it answers."""
    entries = cast(list[_Recorded], yaml.safe_load(path.read_text()))
    return {
        frozenset(entry["keys"]): Reply(
            entry["content"], entry["prompt_tokens"], entry["completion_tokens"], entry["cost"]
        )
        for entry in entries
    }


class FakeAdjudicator:
    """A `Client` answering from the recorded replies; `asks` is every request it was sent."""

    def __init__(self, replies: dict[frozenset[str], Reply] | None = None) -> None:
        self.replies = recorded() if replies is None else replies
        self.asks: list[tuple[str, Ask]] = []
        # `adjudicate` sends a batch's requests from several threads at once.
        self._lock = threading.Lock()

    def complete(self, model: str, ask: Ask) -> Reply:
        with self._lock:
            self.asks.append((model, ask))
        return self.replies.get(ask.keys, UNRECORDED)
