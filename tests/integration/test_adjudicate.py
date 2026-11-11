"""`fundlens adjudicate` on the fixture cycle, with the fake model: the planted ambiguous pair is
asked about and merged by the next `resolve --full`, the unsure cluster is recorded and left alone,
and a second run asks nothing already decided (spec §6.8, NEU-2055)."""

from pathlib import Path
from typing import Any

import psycopg
import pytest
from typer.testing import CliRunner, Result

from fundlens import cli
from fundlens.resolve import adjudicate as adjudication
from fundlens.resolve.adjudicate import Reply
from fundlens.resolve.cluster import cluster_fingerprint
from fundlens.settings import Settings, get_settings
from tests.fake_adjudicator import FakeAdjudicator
from tests.integration.test_resolve import AGAIN, clusters, donor_keys, resolve

PROMPT_VERSION = "adjudicate_v1"


def adjudicate(*args: str) -> Result:
    return CliRunner().invoke(cli.app, ["adjudicate", *args])


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeAdjudicator:
    """The fake model, handed to every `adjudicate` the test runs in place of DeepInfra."""
    client = FakeAdjudicator()

    def client_for(settings: Settings) -> FakeAdjudicator:
        return client

    monkeypatch.setattr(adjudication, "client_for", client_for)
    return client


def verdicts(conninfo: str) -> dict[str, tuple[Any, ...]]:
    with psycopg.connect(conninfo) as conn:
        rows = conn.execute(
            "SELECT cluster_fingerprint, model, prompt_version, decision, confidence, reason,"
            " decided_at FROM app.adjudication"
        ).fetchall()
    return {row[0]: row[1:] for row in rows}


def pair_fingerprint(a: set[str], b: set[str]) -> str:
    return cluster_fingerprint([cluster_fingerprint(a), cluster_fingerprint(b)])


def test_the_planted_pair_is_merged_after_adjudicate_and_resolve_and_the_unsure_left_alone(
    resolved: Path, migrated_db: str, fake: FakeAdjudicator
) -> None:
    halvorsen = donor_keys(resolved, "adjudication_merge")
    thorsby = donor_keys(resolved, "adjudication_unsure")
    before = clusters(resolved)
    # What adjudication is for: linkage keeps the HALVORSENs apart, and joins THORSBY's employers.
    assert len({before[key] for key in halvorsen}) == 2
    assert len({before[key] for key in thorsby}) == 1

    result = adjudicate()

    assert result.exit_code == 0, result.output
    asked = {ask.keys: ask for _, ask in fake.asks}
    assert frozenset(halvorsen) in asked and frozenset(thorsby) in asked
    assert {model for model, _ in fake.asks} == {get_settings().adjudicate_model}
    # The prompt is the versioned file; the records name both sides.
    merge = asked[frozenset(halvorsen)]
    assert merge.system == get_settings().adjudicate_prompt_path.read_text()
    assert "Group A" in merge.user and "Group B" in merge.user
    assert "| HALVORSEN, KATHRYN | ARNOLD | MD | 21409 | HALVORSEN CONSULTING |" in merge.user
    found = verdicts(migrated_db)
    katherine, kathryn = sorted(halvorsen)
    pair = pair_fingerprint({katherine}, {kathryn})
    assert merge.fingerprint == pair
    model, prompt, decision, confidence, reason, decided_at = found[pair]
    assert (model, prompt, decision, float(confidence)) == (
        "deepseek-ai/DeepSeek-V4-Flash",
        PROMPT_VERSION,
        "merge",
        0.86,
    )
    assert reason.startswith("KATHRYN and KATHERINE") and decided_at is not None
    # THORSBY's side A is the employer with more of his dollars.
    [capital] = [key for key in thorsby if "THORSBY CAPITAL" in key]
    unsure = pair_fingerprint({capital}, thorsby - {capital})
    assert (found[unsure][2], float(found[unsure][3])) == ("unsure", 0.45)
    assert "recorded: " in result.output and "batch 1: " in result.output

    again = resolve("--full", "--build-id", AGAIN)

    assert again.exit_code == 0, again.output
    assert "adjudications: 1 verdicts: 1 merges joining 1 clusters into others, 0 splits" in (
        again.output
    )
    after = clusters(resolved)
    assert len({after[key] for key in halvorsen}) == 1
    assert {after[key] for key in thorsby} == {before[key] for key in thorsby}
    # Nothing else moved: the merge joined two clusters and only those.
    others = set(after) - halvorsen
    assert all(after[key] == before[key] for key in others)
    # `recluster` rewrites the clusters as `resolve --full` does, the merge included.
    rewritten = CliRunner().invoke(cli.app, ["recluster"])
    assert rewritten.exit_code == 0, rewritten.output
    assert "adjudications: 1 verdicts: 1 merges" in rewritten.output
    assert len({clusters(resolved)[key] for key in halvorsen}) == 1


def test_a_merge_under_the_confidence_threshold_is_recorded_and_not_applied(
    resolved: Path, migrated_db: str, fake: FakeAdjudicator
) -> None:
    halvorsen = frozenset(donor_keys(resolved, "adjudication_merge"))
    sure = fake.replies[halvorsen]
    fake.replies[halvorsen] = Reply(
        sure.content.replace('"confidence": 0.86', '"confidence": 0.7'),
        sure.prompt_tokens,
        sure.completion_tokens,
        sure.cost,
    )
    assert adjudicate().exit_code == 0
    [(decision, confidence)] = [
        (row[2], float(row[3])) for row in verdicts(migrated_db).values() if row[2] == "merge"
    ]
    assert (decision, confidence) == ("merge", 0.7)

    again = resolve("--full", "--build-id", AGAIN)

    assert again.exit_code == 0, again.output
    assert "adjudications: 0 verdicts: 0 merges" in again.output
    assert len({clusters(resolved)[key] for key in halvorsen}) == 2


def test_a_second_adjudicate_asks_nothing_already_decided(
    resolved: Path, migrated_db: str, fake: FakeAdjudicator
) -> None:
    first = adjudicate()
    assert first.exit_code == 0, first.output
    sent = len(fake.asks)
    assert sent >= 2
    recorded = verdicts(migrated_db)

    again = adjudicate()

    assert again.exit_code == 0, again.output
    assert len(fake.asks) == sent
    assert f"{sent} already decided" in again.output
    assert "chosen: 0" in again.output
    assert verdicts(migrated_db) == recorded


def test_another_model_is_asked_again(
    resolved: Path, migrated_db: str, fake: FakeAdjudicator, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert adjudicate().exit_code == 0
    sent = len(fake.asks)
    monkeypatch.setenv("ADJUDICATE_MODEL", "another/model")
    get_settings.cache_clear()

    again = adjudicate()

    assert again.exit_code == 0, again.output
    assert len(fake.asks) == 2 * sent
    assert {model for model, _ in fake.asks[sent:]} == {"another/model"}


def test_a_dry_run_lists_the_candidates_and_sends_and_writes_nothing(
    resolved: Path, migrated_db: str, fake: FakeAdjudicator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    get_settings.cache_clear()

    result = adjudicate("--dry-run")

    assert result.exit_code == 0, result.output
    assert fake.asks == []
    assert verdicts(migrated_db) == {}
    [pair] = [line for line in result.output.splitlines() if "HALVORSEN" in line]
    # The pair linkage kept apart scores inside the band.
    assert pair.startswith("pair ") and "$65000" in pair
    probability = float(pair.split(" p=")[1].split(":")[0])
    assert adjudication.BAND[0] <= probability < adjudication.BAND[1]
    [cluster] = [line for line in result.output.splitlines() if "THORSBY" in line]
    assert cluster.startswith("cluster ") and "$80000" in cluster
    assert "dry run: nothing sent, nothing written" in result.output


def test_a_limit_asks_about_the_most_dollars_first(resolved: Path, fake: FakeAdjudicator) -> None:
    result = adjudicate("--limit", "1")

    assert result.exit_code == 0, result.output
    assert "chosen: 1" in result.output
    [(_, ask)] = fake.asks
    # THORSBY's $80,000 before the HALVORSENs' $65,000.
    assert all(key.startswith("THORSBY") for key in ask.keys)


def test_above_every_cluster_s_dollars_there_is_nothing_to_ask(
    resolved: Path, fake: FakeAdjudicator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADJUDICATE_MIN_AMOUNT", "10000000")
    get_settings.cache_clear()

    result = adjudicate()

    assert result.exit_code == 0, result.output
    assert "candidates: 0 clusters, 0 pairs" in result.output
    assert fake.asks == []


def test_without_a_key_adjudicate_says_so_and_sends_nothing(
    resolved: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    get_settings.cache_clear()

    result = adjudicate()

    assert result.exit_code == 1
    assert "DEEPINFRA_API_KEY is not set" in result.output


def test_adjudicate_before_any_resolve_says_to_resolve(
    cli_env: Path, fake: FakeAdjudicator
) -> None:
    result = adjudicate()

    assert result.exit_code == 1
    assert "run `fundlens resolve --full`" in result.output
    assert fake.asks == []
