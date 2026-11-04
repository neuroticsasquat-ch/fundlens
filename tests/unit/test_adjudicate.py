"""Adjudication's parts that need no database or network: which clusters are candidates and how
they are fingerprinted, how confident verdicts rewrite a run's clusters, the prompt's records, the
reply's validation, the DeepInfra client and a batch's figures (spec §6.8). The fixture cycle end
to end, with the fake model, is in `tests/integration/test_adjudicate.py`."""

import json
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import duckdb
import pytest
from psycopg import Connection
from psycopg.rows import TupleRow

from fundlens.resolve import adjudicate as adjudication
from fundlens.resolve import overrides
from fundlens.resolve.adjudicate import (
    AdjudicationError,
    Applied,
    Ask,
    Candidate,
    Decision,
    DeepInfraClient,
    Prompt,
    Record,
    Reply,
    Response,
    Version,
)
from fundlens.resolve.cluster import cluster_fingerprint

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT = REPO_ROOT / "resolution" / "prompts" / "adjudicate_v1.md"
KEY = "d1Key"
MIN = 50_000

# Each key: its cluster, last name, ZIP3, employer and dollars.
Member = tuple[str, str, str, str | None, int]


def working_file(members: Mapping[str, Member]) -> duckdb.DuckDBPyConnection:
    """An in-memory working file: `cluster` and the `contributor` columns adjudication reads."""
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE contributor (contributor_key VARCHAR, last_name VARCHAR, zip3 VARCHAR,"
        " employer_norm VARCHAR, amount_total DECIMAL(14, 2))"
    )
    con.execute(
        "CREATE TABLE cluster (cluster_id VARCHAR, contributor_key VARCHAR,"
        " match_probability DOUBLE)"
    )
    for key, (cluster_id, last, zip3, employer, amount) in members.items():
        con.execute(
            "INSERT INTO contributor VALUES (?, ?, ?, ?, ?)", [key, last, zip3, employer, amount]
        )
        con.execute("INSERT INTO cluster VALUES (?, ?, 0.97)", [cluster_id, key])
    return con


def partition(con: duckdb.DuckDBPyConnection) -> set[frozenset[str]]:
    rows = con.execute(
        "SELECT list(contributor_key ORDER BY contributor_key) FROM cluster GROUP BY cluster_id"
    ).fetchall()
    return {frozenset(keys) for (keys,) in rows}


def sides(a: set[str], b: set[str]) -> str:
    return cluster_fingerprint([cluster_fingerprint(a), cluster_fingerprint(b)])


# Two clusters of one surname and ZIP3 worth $60,000 together; a cluster of two employers worth
# $80,000; a cluster of two employers worth $20,000; and a lone key of the same surname elsewhere.
FIXTURE: dict[str, Member] = {
    "SMITH, ANN|21401|NAVY|PROF": ("a", "SMITH", "214", "NAVY", 40_000),
    "SMITH, ANNE|21409||": ("b", "SMITH", "214", None, 20_000),
    "LEE, OLA|20814|ACME|CEO": ("c", "LEE", "208", "ACME", 50_000),
    "LEE, OLA|20814||": ("c", "LEE", "208", None, 5_000),
    "LEE, OLA|20814|BETA|CEO": ("c", "LEE", "208", "BETA", 25_000),
    "ROE, JO|10001|ACME|CEO": ("d", "ROE", "100", "ACME", 10_000),
    "ROE, JO|10001|BETA|CEO": ("d", "ROE", "100", "BETA", 10_000),
    "SMITH, ANN|90210|NAVY|PROF": ("e", "SMITH", "902", "NAVY", 40_000),
}
A, B = {"SMITH, ANN|21401|NAVY|PROF"}, {"SMITH, ANNE|21409||"}
LEE_A = {"LEE, OLA|20814|ACME|CEO", "LEE, OLA|20814||"}
LEE_B = {"LEE, OLA|20814|BETA|CEO"}


def candidates(
    con: duckdb.DuckDBPyConnection, excluded: set[str] | None = None
) -> set[tuple[Any, ...]]:
    con.execute(f"CREATE OR REPLACE TABLE {adjudication.UNADJUDICATED_TABLE} AS FROM cluster")
    adjudication._candidates(con, min_amount=MIN, excluded=excluded or set())  # pyright: ignore[reportPrivateUsage]
    return set(
        con.execute(
            "SELECT fingerprint, kind, cluster_a, cluster_b, employer FROM candidate"
        ).fetchall()
    )


def test_a_pair_of_one_surname_and_zip3_and_a_cluster_of_two_employers_are_candidates() -> None:
    found = candidates(working_file(FIXTURE))

    # Not ROE's two employers, worth less than the minimum; not SMITH of 902, in another ZIP3.
    assert found == {
        (sides(A, B), "pair", "a", "b", None),
        (sides(LEE_A, LEE_B), "cluster", "c", "c", "ACME"),
    }


def test_the_fingerprint_is_the_same_whichever_side_is_named_first() -> None:
    assert sides(A, B) == sides(B, A)
    assert sides(A, B) != sides(A | B, set())


def test_a_cluster_holding_a_key_the_overrides_name_is_no_candidate() -> None:
    found = candidates(working_file(FIXTURE), excluded={"SMITH, ANNE|21409||", "LEE, OLA|20814||"})

    assert found == set()


def test_a_pair_short_of_the_minimum_together_is_no_candidate() -> None:
    members = {key: member for key, member in FIXTURE.items() if member[0] in {"a", "b"}}
    members["SMITH, ANNE|21409||"] = ("b", "SMITH", "214", None, 9_999)

    assert candidates(working_file(members)) == set()


def applied(
    con: duckdb.DuckDBPyConnection, verdicts: Mapping[str, Decision], keys: set[str] | None = None
) -> Applied:
    asserted = overrides.parse(
        "" if not keys else f"- {{merge: {sorted(keys)!r}, reason: r, added: 2026-11-03}}"
    )
    return adjudication.apply(con, verdicts, min_amount=MIN, overrides=asserted)


def test_a_merge_joins_the_pair_and_a_split_moves_the_cluster_s_side_b() -> None:
    con = working_file(FIXTURE)

    result = applied(con, {sides(A, B): "merge", sides(LEE_A, LEE_B): "split"})

    assert result == Applied(verdicts=2, merges=1, splits=1, clusters_joined=1)
    assert partition(con) == {
        frozenset(A | B),
        frozenset(LEE_A),
        frozenset(LEE_B),
        frozenset({"ROE, JO|10001|ACME|CEO", "ROE, JO|10001|BETA|CEO"}),
        frozenset({"SMITH, ANN|90210|NAVY|PROF"}),
    }
    assert con.execute(
        "SELECT cluster_id, match_probability FROM cluster WHERE contributor_key = ?",
        ["LEE, OLA|20814|BETA|CEO"],
    ).fetchall() == [("adjudication:LEE, OLA|20814|BETA|CEO", None)]
    # The clusters as they were before, for the next `adjudicate` to choose from.
    assert con.execute("SELECT count(DISTINCT cluster_id) FROM unadjudicated").fetchall() == [(5,)]


def test_a_merge_of_a_cluster_and_a_split_of_a_pair_change_nothing() -> None:
    con = working_file(FIXTURE)
    before = partition(con)

    result = applied(con, {sides(A, B): "split", sides(LEE_A, LEE_B): "merge"})

    assert result == Applied(verdicts=2, merges=0, splits=0, clusters_joined=0)
    assert partition(con) == before


def test_a_verdict_on_sides_this_run_does_not_hold_changes_nothing() -> None:
    con = working_file(FIXTURE)
    before = partition(con)

    result = applied(con, {sides(A, B | {"SMITH, A|21401||"}): "merge"})

    assert result == Applied(verdicts=0, merges=0, splits=0, clusters_joined=0)
    assert partition(con) == before


def test_no_verdicts_keeps_the_clusters_and_still_writes_unadjudicated() -> None:
    con = working_file(FIXTURE)
    before = partition(con)

    assert applied(con, {}) == Applied(0, 0, 0, 0)
    assert partition(con) == before
    assert con.execute("SELECT count(*) FROM unadjudicated").fetchall() == [(len(FIXTURE),)]


class Verdicts:
    """A stand-in for the Postgres connection `confident` reads: the rows its query returns."""

    def __init__(self, rows: list[tuple[str, str]]) -> None:
        self.rows = rows
        self.query: tuple[str, tuple[Any, ...]] | None = None

    def execute(self, query: str, params: tuple[Any, ...]) -> "Verdicts":
        self.query = (query, params)
        return self

    def fetchall(self) -> list[tuple[str, str]]:
        return self.rows


def test_confident_asks_for_merges_and_splits_of_the_version_at_the_threshold() -> None:
    conn = Verdicts([("f1", "merge"), ("f2", "split")])

    found = adjudication.confident(cast(Connection[TupleRow], conn), Version("m", "adjudicate_v1"))

    assert found == {"f1": "merge", "f2": "split"}
    assert conn.query is not None
    query, params = conn.query
    assert "decision IN ('merge', 'split')" in query and "confidence >= %s" in query
    assert params == ("m", "adjudicate_v1", 0.8)


def record(key: str, amount: int, employer: str | None = "ACME") -> Record:
    return Record(key, "ANNAPOLIS", "MD", "21401", employer, "CEO", 1, Decimal(amount))


def test_the_prompt_is_the_file_and_its_stem_the_version() -> None:
    prompt = Prompt.load(PROMPT)

    assert prompt.version == "adjudicate_v1"
    assert '{"decision": "merge" | "split" | "unsure"' in prompt.text


def test_the_ask_lists_each_side_s_records_by_name_and_the_rest_on_one_line() -> None:
    many = tuple(record(f"DOE, J{n:02}|21401|ACME|CEO", 100 + n) for n in range(45))
    candidate = Candidate("f", "pair", Decimal(1), 0.8, (record("ROE, A|21401||", 5, None),), many)

    ask = adjudication.ask_for(candidate, Prompt("adjudicate_v1", "SYSTEM"))

    assert ask.system == "SYSTEM" and ask.fingerprint == "f"
    assert ask.keys == candidate.keys()
    group_a, group_b = ask.user.split("Group B")
    assert "| ROE, A | ANNAPOLIS | MD | 21401 |  | CEO | 1 | 5 |" in group_a
    # The forty with the most dollars, then the five least as one line.
    assert "| DOE, J44 |" in group_b and "| DOE, J05 |" in group_b
    assert "| DOE, J04 |" not in group_b
    assert "| and 5 more records | | | | | | 5 | 510 |" in group_b


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"decision": "merge", "confidence": 0.9, "reason": "same"}', ("merge", 0.9)),
        ('```json\n{"decision": "split", "confidence": 1, "reason": "two"}\n```', ("split", 1.0)),
        ('{"decision": "unsure", "confidence": 0, "reason": "?", "extra": 1}', ("unsure", 0.0)),
    ],
)
def test_a_reply_as_the_prompt_asks_is_a_verdict(content: str, expected: tuple[str, float]) -> None:
    verdict = adjudication.parse_verdict(content)

    assert verdict is not None
    assert (verdict.decision, verdict.confidence) == expected


@pytest.mark.parametrize(
    "content",
    [
        "They are the same person.",
        '{"decision": "maybe", "confidence": 0.5, "reason": "?"}',
        '{"decision": "merge", "confidence": 1.5, "reason": "sure"}',
        '{"decision": "merge", "confidence": 0.9, "reason": "  "}',
        '{"decision": "merge", "reason": "no confidence"}',
        "[]",
    ],
)
def test_any_other_reply_is_none(content: str) -> None:
    assert adjudication.parse_verdict(content) is None


class FakeDeepInfra:
    """Answers each POST with the next scripted response; the last one repeats."""

    def __init__(self, *responses: Response) -> None:
        self.responses = list(responses)
        self.posts: list[tuple[str, dict[str, str], bytes]] = []

    def __call__(self, url: str, headers: Mapping[str, str], body: bytes) -> Response:
        self.posts.append((url, dict(headers), body))
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


def completion(content: str, cost: float | None = 0.00012) -> Response:
    usage: dict[str, Any] = {"prompt_tokens": 600, "completion_tokens": 40}
    if cost is not None:
        usage["estimated_cost"] = cost
    body = {"choices": [{"message": {"role": "assistant", "content": content}}], "usage": usage}
    return Response(200, json.dumps(body).encode())


ASK = Ask("f", frozenset({"k"}), "SYSTEM", "USER")


def test_the_client_posts_one_json_mode_chat_and_reads_its_usage() -> None:
    post = FakeDeepInfra(completion('{"decision": "merge"}'))

    reply = DeepInfraClient(KEY, post=post, sleep=lambda _: None).complete("org/model", ASK)

    assert reply == Reply('{"decision": "merge"}', 600, 40, 0.00012)
    [(url, headers, body)] = post.posts
    assert url == "https://api.deepinfra.com/v1/openai/chat/completions"
    assert headers["Authorization"] == f"Bearer {KEY}"
    assert json.loads(body) == {
        "model": "org/model",
        "messages": [
            {"role": "system", "content": "SYSTEM"},
            {"role": "user", "content": "USER"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }


def test_a_reply_without_a_cost_estimate_has_none() -> None:
    post = FakeDeepInfra(completion("{}", cost=None))

    assert DeepInfraClient(KEY, post=post).complete("m", ASK).cost is None


def test_the_client_retries_a_5xx_and_a_429_and_then_answers() -> None:
    post = FakeDeepInfra(Response(503, b"busy"), Response(429, b"slow down"), completion("{}"))
    slept: list[float] = []

    reply = DeepInfraClient(KEY, post=post, sleep=slept.append).complete("m", ASK)

    assert reply.content == "{}"
    assert len(post.posts) == 3
    assert slept == [5.0, 10.0]


def test_the_client_retries_a_dropped_connection() -> None:
    answers = [ConnectionResetError("reset by peer")]

    def post(url: str, headers: Mapping[str, str], body: bytes) -> Response:
        if answers:
            raise answers.pop()
        return completion("{}")

    reply = DeepInfraClient(KEY, post=post, sleep=lambda _: None).complete("m", ASK)

    assert reply.content == "{}"


def test_the_client_gives_up_at_once_on_a_4xx_and_never_names_the_key() -> None:
    post = FakeDeepInfra(Response(401, b'{"error": "bad key"}'))

    with pytest.raises(RuntimeError, match="HTTP 401") as raised:
        DeepInfraClient(KEY, post=post, sleep=lambda _: None).complete("m", ASK)

    assert len(post.posts) == 1
    assert KEY not in str(raised.value)


def test_p95_interpolates_and_copes_with_one_or_none() -> None:
    assert adjudication.p95([float(n) for n in range(1, 21)]) == pytest.approx(19.05)
    assert adjudication.p95([2.5]) == 2.5
    assert adjudication.p95([]) == 0.0


class Failing:
    def complete(self, model: str, ask: Ask) -> Reply:
        raise RuntimeError("adjudication request failed: HTTP 401")


def test_a_batch_whose_every_request_fails_stops_the_run() -> None:
    candidate = Candidate(
        "f", "pair", Decimal(1), 0.8, (record("A|1||", 1),), (record("B|1||", 1),)
    )

    with pytest.raises(AdjudicationError, match="HTTP 401"):
        adjudication.adjudicate(
            [candidate, candidate],
            client=Failing(),
            # Never reached: a batch with no reply writes nothing.
            conn=cast(Connection[TupleRow], None),
            version=Version("m", "adjudicate_v1"),
            prompt=Prompt("adjudicate_v1", "SYSTEM"),
            batch_size=2,
        )
