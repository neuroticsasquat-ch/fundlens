"""Adjudication: a model's second opinion on the ambiguous high-dollar clusters (spec §6.8,
ADR-0005).

The few thousand donors with the most money are where a fragmented or chained donor is most
visible and where linkage is least sure, so `fundlens adjudicate` asks a cheap model about them,
in batch and never from a request path, and every resolve run applies what it answered.

**Candidates.** Each candidate is a question about two sides, A and B, sets of contributor keys
from the working file's `unadjudicated` table (every key in its cluster after overrides, before
adjudications):

- a *pair*: two clusters that linkage keeps apart, holding keys of one last name and ZIP3 between
  them, with `amount_total` of at least `min_amount` together, and whose best-scoring pair of such
  keys lies in linkage's ambiguous band `BAND`. Linkage's `edge` table keeps no pair under the
  match threshold, so `adjudicate` scores the pairs again with the saved model, blocking on last
  name and ZIP3 only. The question: is A the same person as B?
- a *cluster*: one cluster of at least `min_amount` whose keys report two or more employers. Side
  A is the keys of its employer with the most dollars, with the keys that report none; side B is
  the rest. The question: does B belong with A?

Two clusters apart nearly always disagree on employer, so employer disagreement picks clusters
and the band picks pairs: a pair chosen by employer alone would make every same-surname neighbour
of a large donor a candidate. A candidate holding a key `resolution/overrides.yaml` names is
never one: the overrides file is the human record, and a model does not second-guess it.

**Fingerprint.** A candidate is known by the fingerprint of its two sides' fingerprints
(`cluster.cluster_fingerprint`, each side's keys; the pair of them in turn), so the same two sides
are the same question in any run, and one key more or fewer on either side is another.
`app.adjudication` keeps one verdict per fingerprint, model and prompt version.

**Apply.** A verdict of `merge` or `split` with a confidence of at least `APPLY_CONFIDENCE` is
applied after overrides and before the crosswalk, as an override is: `apply` keeps the clusters
it is handed as `unadjudicated`, finds the candidates in them again (without scoring: a verdict
already says the pair was worth asking about), and for each candidate with such a verdict joins
a pair's two clusters (`merge`) or moves a cluster's side B into a cluster of its own (`split`).
A `merge` of a cluster or a `split` of a pair leaves things as they are, and so does `unsure`.

**Client.** The model is reached through `Client`, one chat completion per candidate:
`DeepInfraClient` posts to DeepInfra's OpenAI-compatible endpoint, and the tests hand in a fake.
Requests go out `batch_size` at a time, concurrently; each batch's verdicts are written as soon as
it returns, and its tokens, cost and latency are logged.
"""

import json
import logging
import statistics
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import duckdb
from psycopg import Connection
from psycopg.rows import TupleRow
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from splink import DuckDBAPI

from fundlens import paths
from fundlens.r2 import R2
from fundlens.resolve import model
from fundlens.resolve.cluster import CLUSTER_TABLE
from fundlens.resolve.overrides import Overrides, join_clusters
from fundlens.settings import Settings
from fundlens.transform.runner import Limits

log = logging.getLogger(__name__)

# Every key in its cluster after overrides and before adjudications: what both `adjudicate` and
# the resolve run applying its verdicts find candidates in, so the two find the same ones.
UNADJUDICATED_TABLE = "unadjudicated"
_CONTRIBUTOR_TABLE = "contributor"

# Linkage's ambiguous band (spec §6.8): a pair of clusters whose best pair scores in it.
BAND = (0.6, 0.95)
# A verdict is applied when the model is at least this sure of it (spec §6.8).
APPLY_CONFIDENCE = 0.8
# The cluster a split's side B moves into, named by its lowest key: the prefix keeps it from any
# other cluster id, as an override's split prefix does (`overrides.SPLIT_CLUSTER_PREFIX`).
SPLIT_CLUSTER_PREFIX = "adjudication:"
# The most records of one side the prompt lists, those with the most dollars; the rest are
# summed in one line. The cluster cap allows a side of hundreds of keys.
MAX_RECORDS_PER_SIDE = 40

DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
ATTEMPTS = 3
RETRY_SECONDS = 5.0
TIMEOUT_SECONDS = 120.0

Kind = Literal["pair", "cluster"]
Decision = Literal["merge", "split", "unsure"]


class AdjudicationError(Exception):
    """Every request of a batch failed: the endpoint, the key or the model is wrong."""


@dataclass(frozen=True)
class Version:
    """Whose verdicts these are: the model, and the prompt by its file's stem (`adjudicate_v1`)."""

    model: str
    prompt_version: str


@dataclass(frozen=True)
class Prompt:
    """The versioned prompt (`resolution/prompts/adjudicate_<version>.md`): the system message."""

    version: str
    text: str

    @classmethod
    def load(cls, path: Path) -> "Prompt":
        return cls(path.stem, path.read_text())


# --- Candidates ----------------------------------------------------------------------------------


def _candidates(con: duckdb.DuckDBPyConnection, *, min_amount: int, excluded: set[str]) -> None:
    """Write the temp table `candidate(fingerprint, kind, cluster_a, cluster_b, employer, amount)`
    on `con` from its `unadjudicated` and `contributor` tables: every pair and every cluster that
    could be a candidate by dollars, last name, ZIP3 and employer (the module docstring), the band
    not yet tested. A cluster's `cluster_b` is its own id and `employer` the employer of its side
    A; a pair's `employer` is NULL. Clusters holding a key of `excluded` are left out."""
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE held AS
        SELECT u.cluster_id, k.contributor_key, k.last_name, k.zip3, k.employer_norm,
            k.amount_total
        FROM {UNADJUDICATED_TABLE} AS u
        JOIN {_CONTRIBUTOR_TABLE} AS k USING (contributor_key)
        WHERE u.cluster_id NOT IN (
            SELECT cluster_id FROM {UNADJUDICATED_TABLE}
            WHERE contributor_key IN (SELECT unnest($excluded::VARCHAR[]))
        )
        """,
        {"excluded": sorted(excluded)},
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE held_cluster AS
        SELECT cluster_id, sum(amount_total) AS amount,
            sha1(string_agg(contributor_key, chr(10) ORDER BY contributor_key)) AS fingerprint
        FROM held
        GROUP BY cluster_id
        """
    )
    # A pair reaching `min_amount` holds a cluster of at least half of it, so only such a
    # cluster's keys are joined to the rest: common surnames make the full self-join enormous.
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE candidate AS
        WITH
            big AS (
                SELECT h.* FROM held AS h
                JOIN held_cluster AS c USING (cluster_id)
                WHERE c.amount * 2 >= $min_amount
            ),
            pair AS (
                SELECT DISTINCT
                    least(b.cluster_id, o.cluster_id) AS cluster_a,
                    greatest(b.cluster_id, o.cluster_id) AS cluster_b
                FROM big AS b
                JOIN held AS o
                    ON o.last_name = b.last_name AND o.zip3 = b.zip3
                    AND o.cluster_id <> b.cluster_id
            ),
            by_employer AS (
                SELECT cluster_id, employer_norm, sum(amount_total) AS amount
                FROM held WHERE employer_norm IS NOT NULL
                GROUP BY ALL
            ),
            divided AS (
                SELECT c.cluster_id, c.amount,
                    first(e.employer_norm ORDER BY e.amount DESC, e.employer_norm) AS employer
                FROM held_cluster AS c
                JOIN by_employer AS e USING (cluster_id)
                WHERE c.amount >= $min_amount
                GROUP BY ALL
                HAVING count(*) >= 2
            ),
            side AS (
                SELECT d.cluster_id,
                    sha1(string_agg(h.contributor_key, chr(10) ORDER BY h.contributor_key))
                        AS fingerprint
                FROM divided AS d
                JOIN held AS h USING (cluster_id)
                GROUP BY d.cluster_id,
                    h.employer_norm IS NOT NULL AND h.employer_norm <> d.employer
            )
        SELECT
            sha1(least(a.fingerprint, b.fingerprint) || chr(10)
                || greatest(a.fingerprint, b.fingerprint)) AS fingerprint,
            'pair' AS kind, p.cluster_a, p.cluster_b, NULL::VARCHAR AS employer,
            a.amount + b.amount AS amount
        FROM pair AS p
        JOIN held_cluster AS a ON a.cluster_id = p.cluster_a
        JOIN held_cluster AS b ON b.cluster_id = p.cluster_b
        WHERE a.amount + b.amount >= $min_amount
        UNION ALL
        SELECT
            (SELECT sha1(min(s.fingerprint) || chr(10) || max(s.fingerprint))
                FROM side AS s WHERE s.cluster_id = d.cluster_id),
            'cluster', d.cluster_id, d.cluster_id, d.employer, d.amount
        FROM divided AS d
        """,
        {"min_amount": min_amount},
    )
    con.execute("DROP TABLE held_cluster")


def _side_keys_sql(side: Literal["A", "B"]) -> str:
    """SQL over `candidate AS c` and `held AS h`: whether key `h` is on `side` of candidate `c`."""
    if side == "A":
        return (
            "((c.kind = 'pair' AND h.cluster_id = c.cluster_a) OR (c.kind = 'cluster'"
            " AND h.cluster_id = c.cluster_a"
            " AND (h.employer_norm IS NULL OR h.employer_norm = c.employer)))"
        )
    return (
        "((c.kind = 'pair' AND h.cluster_id = c.cluster_b) OR (c.kind = 'cluster'"
        " AND h.cluster_id = c.cluster_a"
        " AND h.employer_norm IS NOT NULL AND h.employer_norm <> c.employer))"
    )


# --- Apply ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Applied:
    """What `apply` did."""

    # Verdicts at or above `APPLY_CONFIDENCE` whose candidate this run's clusters hold.
    verdicts: int
    merges: int
    splits: int
    # Clusters the merges joined into others, so no longer clusters of their own.
    clusters_joined: int

    def summary(self) -> str:
        return (
            f"{self.verdicts} verdicts: {self.merges} merges joining {self.clusters_joined}"
            f" clusters into others, {self.splits} splits"
        )


def confident(conn: Connection[TupleRow], version: Version) -> dict[str, Decision]:
    """Each fingerprint `version` decided `merge` or `split` with at least `APPLY_CONFIDENCE`."""
    rows = conn.execute(
        """
        SELECT cluster_fingerprint, decision FROM app.adjudication
        WHERE model = %s AND prompt_version = %s AND decision IN ('merge', 'split')
            AND confidence >= %s
        """,
        (version.model, version.prompt_version, APPLY_CONFIDENCE),
    ).fetchall()
    return {fingerprint: cast(Decision, decision) for fingerprint, decision in rows}


def apply(
    con: duckdb.DuckDBPyConnection,
    verdicts: Mapping[str, Decision],
    *,
    min_amount: int,
    overrides: Overrides,
) -> Applied:
    """Keep `con`'s `cluster` table as `unadjudicated`, then merge and split it in place as
    `verdicts` (`confident`) say, merges first (the module docstring). A split side's keys'
    `match_probability` becomes NULL, as an override's split key's does."""
    con.execute(f"CREATE OR REPLACE TABLE {UNADJUDICATED_TABLE} AS FROM {CLUSTER_TABLE}")
    if not verdicts:
        log.info("adjudications: no confident verdict to apply")
        return Applied(0, 0, 0, 0)
    _candidates(con, min_amount=min_amount, excluded=overrides.keys())
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE verdict AS
        SELECT unnest($fingerprints::VARCHAR[]) AS fingerprint,
            unnest($decisions::VARCHAR[]) AS decision
        """,
        {"fingerprints": list(verdicts), "decisions": list(verdicts.values())},
    )
    [(matched,)] = con.execute(
        "SELECT count(*) FROM candidate JOIN verdict USING (fingerprint)"
    ).fetchall()
    merges = con.execute(
        """
        SELECT cluster_a, cluster_b FROM candidate JOIN verdict USING (fingerprint)
        WHERE kind = 'pair' AND decision = 'merge'
        ORDER BY cluster_a, cluster_b
        """
    ).fetchall()
    joined = join_clusters(con, [{a, b} for a, b in merges])
    sides = con.execute(
        f"""
        SELECT c.fingerprint, list(h.contributor_key ORDER BY h.contributor_key)
        FROM candidate AS c
        JOIN verdict USING (fingerprint)
        JOIN held AS h ON {_side_keys_sql("B")}
        WHERE c.kind = 'cluster' AND verdict.decision = 'split'
        GROUP BY c.fingerprint
        """
    ).fetchall()
    for _, keys in sides:
        con.execute(
            f"""
            UPDATE {CLUSTER_TABLE}
            SET cluster_id = $cluster_id, match_probability = NULL
            WHERE contributor_key IN (SELECT unnest($keys::VARCHAR[]))
            """,
            {"cluster_id": SPLIT_CLUSTER_PREFIX + min(keys), "keys": keys},
        )
    for scratch in ("verdict", "candidate", "held"):
        con.execute(f"DROP TABLE {scratch}")
    applied = Applied(matched, len(merges), len(sides), joined)
    log.info("adjudications: %s", applied.summary())
    return applied


# --- The model -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Ask:
    """One candidate put to the model: its fingerprint and keys, and the chat to send."""

    fingerprint: str
    keys: frozenset[str]
    system: str
    user: str


@dataclass(frozen=True)
class Reply:
    """What the model answered, and what it cost."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    # US dollars, as the provider estimates them; None when it gives no estimate.
    cost: float | None


class Client(Protocol):
    """A chat model: one completion per `Ask`."""

    def complete(self, model: str, ask: Ask) -> Reply: ...


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes


# `(url, headers, body) -> response`; the tests hand in a recorder.
Post = Callable[[str, Mapping[str, str], bytes], Response]
Sleep = Callable[[float], None]


def http_post(url: str, headers: Mapping[str, str], body: bytes) -> Response:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return Response(response.status, response.read())
    except HTTPError as exc:
        # A 4xx or 5xx is an answer, with the provider's error in its body.
        return Response(exc.code, exc.read())


class DeepInfraClient:
    """DeepInfra's OpenAI-compatible chat completions, in JSON mode at temperature 0, retried on a
    429, a 5xx or no answer. The key reaches a request header and nothing else."""

    def __init__(
        self,
        api_key: str,
        *,
        url: str = DEEPINFRA_URL,
        post: Post = http_post,
        sleep: Sleep = time.sleep,
    ) -> None:
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._url = url
        self._post = post
        self._sleep = sleep

    def complete(self, model: str, ask: Ask) -> Reply:
        body = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": ask.system},
                    {"role": "user", "content": ask.user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            }
        ).encode()
        failure = ""
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = self._post(self._url, self._headers, body)
            # `URLError`, a timeout and a dropped connection (`RemoteDisconnected`) alike.
            except OSError as exc:
                failure = f"no answer: {exc}"
            else:
                if response.status == 200:
                    return _reply(response.body)
                failure = f"HTTP {response.status}: {response.body[:200]!r}"
                if response.status != 429 and response.status < 500:
                    break
            if attempt < ATTEMPTS:
                self._sleep(RETRY_SECONDS * attempt)
        raise RuntimeError(f"adjudication request failed: {failure}")


def _reply(body: bytes) -> Reply:
    payload = cast(dict[str, Any], json.loads(body))
    usage = cast(dict[str, Any], payload.get("usage") or {})
    cost = usage.get("estimated_cost")
    return Reply(
        content=str(payload["choices"][0]["message"]["content"] or ""),
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        cost=float(cost) if cost is not None else None,
    )


def client_for(settings: Settings) -> Client | None:
    """The configured model's client, or None when `DEEPINFRA_API_KEY` is unset."""
    key = settings.deepinfra_api_key
    return DeepInfraClient(key.get_secret_value()) if key is not None else None


Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Verdict(BaseModel):
    """The model's reply, as the prompt asks for it."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    decision: Decision
    confidence: float = Field(ge=0, le=1)
    reason: Reason


def parse_verdict(content: str) -> Verdict | None:
    """The verdict in a reply, or None when it is not the JSON object the prompt asks for. A
    Markdown code fence around it is allowed: some models add one even in JSON mode."""
    text = content.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return Verdict.model_validate(json.loads(text))
    except (ValueError, ValidationError):
        return None


# --- The run -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Record:
    """One contributor key as the prompt shows it."""

    contributor_key: str
    city: str | None
    state: str | None
    zip5: str | None
    employer: str | None
    occupation: str | None
    contributions: int
    amount: Decimal


@dataclass(frozen=True)
class Candidate:
    """One question worth asking (the module docstring)."""

    fingerprint: str
    kind: Kind
    amount: Decimal
    # The best score linkage gives a pair of keys between the sides; None for a cluster.
    probability: float | None
    a: tuple[Record, ...]
    b: tuple[Record, ...]

    def keys(self) -> frozenset[str]:
        return frozenset(record.contributor_key for record in (*self.a, *self.b))


def _table(records: Sequence[Record]) -> str:
    ranked = sorted(records, key=lambda r: (-r.amount, r.contributor_key))
    shown, rest = ranked[:MAX_RECORDS_PER_SIDE], ranked[MAX_RECORDS_PER_SIDE:]
    lines = [
        "| name | city | state | ZIP | employer | occupation | contributions | dollars |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in shown:
        name = r.contributor_key.split("|", 1)[0]
        cells = (name, r.city, r.state, r.zip5, r.employer, r.occupation)
        lines.append(
            "| "
            + " | ".join(cell or "" for cell in cells)
            + f" | {r.contributions} | {r.amount:.0f} |"
        )
    if rest:
        lines.append(
            f"| and {len(rest)} more records | | | | | |"
            f" {sum(r.contributions for r in rest)} | {sum(r.amount for r in rest):.0f} |"
        )
    return "\n".join(lines)


def ask_for(candidate: Candidate, prompt: Prompt) -> Ask:
    """The chat that puts `candidate` to the model: the prompt, then the two sides' records."""
    user = f"Group A\n\n{_table(candidate.a)}\n\nGroup B\n\n{_table(candidate.b)}\n"
    return Ask(candidate.fingerprint, candidate.keys(), prompt.text, user)


def _band_pairs(
    con: duckdb.DuckDBPyConnection, saved: dict[str, Any]
) -> dict[tuple[str, str], float]:
    """Each pair candidate of `con`'s `candidate` table whose best-scoring pair of keys sharing a
    last name and ZIP3 lies in `BAND`, scored by the saved model `saved`, and that score."""
    con.execute(
        f"""
        CREATE OR REPLACE TABLE pool AS
        SELECT * FROM {_CONTRIBUTOR_TABLE}
        WHERE contributor_key IN (
            SELECT h.contributor_key FROM held AS h
            JOIN candidate AS c ON c.kind = 'pair' AND h.cluster_id IN (c.cluster_a, c.cluster_b)
        )
        """
    )
    [(pooled,)] = con.execute("SELECT count(*) FROM pool").fetchall()
    if not pooled:
        return {}
    settings = {
        **saved,
        "blocking_rules_to_generate_predictions": [
            {"blocking_rule": 'l."last_name" = r."last_name" AND l."zip3" = r."zip3"'}
        ],
    }
    linker = model.linker(DuckDBAPI(con), "pool", settings)
    predictions = linker.inference.predict(
        threshold_match_probability=BAND[0], warning_mode="never"
    )
    rows = con.execute(
        f"""
        WITH scored AS (
            SELECT
                least(l.cluster_id, r.cluster_id) AS cluster_a,
                greatest(l.cluster_id, r.cluster_id) AS cluster_b,
                max(p.match_probability) AS probability
            FROM {predictions.physical_name} AS p
            JOIN held AS l ON l.contributor_key = p.contributor_key_l
            JOIN held AS r ON r.contributor_key = p.contributor_key_r
            WHERE l.cluster_id <> r.cluster_id
            GROUP BY ALL
        )
        SELECT s.cluster_a, s.cluster_b, s.probability
        FROM scored AS s
        JOIN candidate AS c USING (cluster_a, cluster_b)
        WHERE c.kind = 'pair' AND s.probability >= $low AND s.probability < $high
        """,
        {"low": BAND[0], "high": BAND[1]},
    ).fetchall()
    linker.table_management.delete_tables_created_by_splink_from_db()
    con.execute("DROP TABLE pool")
    log.info("adjudicate: scored %d keys of pair candidates, %d in the band", pooled, len(rows))
    return {(a, b): probability for a, b, probability in rows}


def _records(con: duckdb.DuckDBPyConnection, side: Literal["A", "B"]) -> dict[str, list[Record]]:
    """Each chosen candidate's records on `side`, by fingerprint."""
    found: dict[str, list[Record]] = {}
    for fingerprint, *fields in con.execute(
        f"""
        SELECT c.fingerprint, k.contributor_key, k.city, k.state, k.zip5, k.employer_norm,
            k.occupation_norm, k.contribution_count, k.amount_total
        FROM chosen AS c
        JOIN held AS h ON {_side_keys_sql(side)}
        JOIN {_CONTRIBUTOR_TABLE} AS k USING (contributor_key)
        ORDER BY c.fingerprint, k.contributor_key
        """
    ).fetchall():
        key, city, state, zip5, employer, occupation, contributions, amount = fields
        found.setdefault(fingerprint, []).append(
            Record(
                key, city, state, zip5, employer, occupation, int(contributions), Decimal(amount)
            )
        )
    return found


def decided(conn: Connection[TupleRow], version: Version) -> set[str]:
    """Every fingerprint `version` has a verdict on, whatever it was."""
    rows = conn.execute(
        "SELECT cluster_fingerprint FROM app.adjudication WHERE model = %s AND prompt_version = %s",
        (version.model, version.prompt_version),
    ).fetchall()
    return {fingerprint for (fingerprint,) in rows}


def _saved_model(store: R2, data_dir: Path) -> dict[str, Any]:
    """The newest saved model (`model.latest_version`), downloaded first if not cached."""
    version = model.latest_version(store)
    if version is None:
        raise FileNotFoundError("no saved model: run `fundlens resolve --full`")
    key = paths.resolution_model(version)
    local = paths.local_path(data_dir, key)
    if not local.exists():
        store.download_to(key, local)
    return cast(dict[str, Any], json.loads(local.read_text()))


@dataclass(frozen=True)
class Selected:
    """The candidates `select` found."""

    # By kind, before the already decided were set aside and the band tested.
    clusters: int
    pairs: int
    already_decided: int
    # The candidates to ask about, the most dollars first, at most the limit.
    chosen: tuple[Candidate, ...]


def select(
    store: R2,
    *,
    data_dir: Path,
    limits: Limits,
    conn: Connection[TupleRow],
    version: Version,
    min_amount: int,
    overrides: Overrides,
    limit: int | None = None,
) -> Selected:
    """The candidates in the working file that `version` has no verdict on yet, the most dollars
    first, at most `limit` of them (the module docstring).

    Raises `FileNotFoundError` when there is no working file, it holds no `unadjudicated` table,
    or no model is saved.
    """
    database = paths.resolution_database(data_dir)
    missing = FileNotFoundError(
        "no unadjudicated clusters in the working file: run `fundlens resolve --full`"
    )
    if not database.exists():
        raise missing
    scratch = paths.scratch_dir(data_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    # In memory, the working file attached read-only: Splink writes tables of its own.
    with duckdb.connect(config=limits.duckdb_config(scratch)) as con:
        con.execute(f"ATTACH '{database}' AS run (READ_ONLY)")
        tables = {
            name
            for (name,) in con.execute(
                "SELECT table_name FROM duckdb_tables() WHERE database_name = 'run'"
            ).fetchall()
        }
        if not {UNADJUDICATED_TABLE, _CONTRIBUTOR_TABLE} <= tables:
            raise missing
        for table in (UNADJUDICATED_TABLE, _CONTRIBUTOR_TABLE):
            con.execute(f"CREATE VIEW {table} AS FROM run.{table}")
        _candidates(con, min_amount=min_amount, excluded=overrides.keys())
        counts = dict(con.execute("SELECT kind, count(*) FROM candidate GROUP BY kind").fetchall())
        known = decided(conn, version)
        con.execute(
            "DELETE FROM candidate WHERE fingerprint IN (SELECT unnest($known::VARCHAR[]))",
            {"known": sorted(known)},
        )
        [(remaining,)] = con.execute("SELECT count(*) FROM candidate").fetchall()
        already = sum(counts.values()) - remaining
        has_pairs = con.execute("SELECT 1 FROM candidate WHERE kind = 'pair' LIMIT 1").fetchall()
        banded = _band_pairs(con, _saved_model(store, data_dir)) if has_pairs else {}
        con.execute(
            """
            CREATE TEMP TABLE chosen AS
            SELECT c.*, b.probability
            FROM candidate AS c
            LEFT JOIN (
                SELECT unnest($a::VARCHAR[]) AS cluster_a, unnest($b::VARCHAR[]) AS cluster_b,
                    unnest($p::DOUBLE[]) AS probability
            ) AS b USING (cluster_a, cluster_b)
            WHERE c.kind = 'cluster' OR b.probability IS NOT NULL
            ORDER BY c.amount DESC, c.fingerprint
            LIMIT $limit
            """,
            {
                "a": [a for a, _ in banded],
                "b": [b for _, b in banded],
                "p": list(banded.values()),
                "limit": limit if limit is not None else 2**62,
            },
        )
        side_a, side_b = _records(con, "A"), _records(con, "B")
        chosen = tuple(
            Candidate(
                fingerprint,
                cast(Kind, kind),
                Decimal(amount),
                probability,
                tuple(side_a.get(fingerprint, ())),
                tuple(side_b.get(fingerprint, ())),
            )
            for fingerprint, kind, amount, probability in con.execute(
                "SELECT fingerprint, kind, amount, probability FROM chosen"
                " ORDER BY amount DESC, fingerprint"
            ).fetchall()
        )
    return Selected(counts.get("cluster", 0), counts.get("pair", 0), already, chosen)


@dataclass(frozen=True)
class Batch:
    """One batch's requests, as logged."""

    number: int
    requests: int
    recorded: int
    # Replies that were not the JSON the prompt asks for, and requests that got no reply.
    invalid: int
    failed: int
    prompt_tokens: int
    completion_tokens: int
    cost: float | None
    p50_s: float
    p95_s: float
    wall_s: float

    def summary(self) -> str:
        cost = "n/a" if self.cost is None else f"${self.cost:.4f}"
        return (
            f"batch {self.number}: {self.requests} requests, {self.recorded} recorded,"
            f" {self.invalid} invalid, {self.failed} failed; tokens {self.prompt_tokens} in,"
            f" {self.completion_tokens} out; cost {cost}; latency p50 {self.p50_s:.2f} s,"
            f" p95 {self.p95_s:.2f} s; wall {self.wall_s:.2f} s"
        )


@dataclass(frozen=True)
class Adjudicated:
    """What `adjudicate` did."""

    batches: tuple[Batch, ...]
    decisions: dict[str, int] = field(default_factory=dict[str, int])


def p95(latencies: Sequence[float]) -> float:
    """The 95th percentile of `latencies`, by linear interpolation between the closest ranks."""
    if len(latencies) < 2:
        return latencies[0] if latencies else 0.0
    return statistics.quantiles(latencies, n=20, method="inclusive")[18]


def _timed(client: Client, model_name: str, ask: Ask) -> tuple[Reply | Exception, float]:
    started = time.perf_counter()
    try:
        reply: Reply | Exception = client.complete(model_name, ask)
    except Exception as exc:  # A failed request is counted, and retried by the next run.
        reply = exc
    return reply, time.perf_counter() - started


def _record(
    conn: Connection[TupleRow], version: Version, verdicts: list[tuple[str, Verdict]]
) -> None:
    if not verdicts:
        return
    decided_at = datetime.now(UTC)
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO app.adjudication
                (cluster_fingerprint, model, prompt_version, decision, confidence, reason,
                decided_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    fingerprint,
                    version.model,
                    version.prompt_version,
                    verdict.decision,
                    verdict.confidence,
                    verdict.reason,
                    decided_at,
                )
                for fingerprint, verdict in verdicts
            ],
        )


def adjudicate(
    candidates: Sequence[Candidate],
    *,
    client: Client,
    conn: Connection[TupleRow],
    version: Version,
    prompt: Prompt,
    batch_size: int,
) -> Adjudicated:
    """Ask `client` about each of `candidates`, `batch_size` at a time and concurrently, and
    write each batch's valid verdicts to `app.adjudication` as soon as it returns.

    Raises `AdjudicationError` when every request of a batch fails, after writing the batches
    before it; an invalid reply or a lone failed request is only counted, and asked again by the
    next run.
    """
    batches: list[Batch] = []
    decisions: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=batch_size) as pool:
        for start in range(0, len(candidates), batch_size):
            chunk = candidates[start : start + batch_size]
            asks = [ask_for(candidate, prompt) for candidate in chunk]
            started = time.perf_counter()
            answers = list(pool.map(partial(_timed, client, version.model), asks))
            wall = time.perf_counter() - started
            verdicts: list[tuple[str, Verdict]] = []
            replies = [reply for reply, _ in answers if isinstance(reply, Reply)]
            failures = [reply for reply, _ in answers if isinstance(reply, Exception)]
            for ask, (reply, _) in zip(asks, answers, strict=True):
                if isinstance(reply, Reply):
                    verdict = parse_verdict(reply.content)
                    if verdict is None:
                        log.warning("adjudicate: invalid reply for %s", ask.fingerprint)
                    else:
                        verdicts.append((ask.fingerprint, verdict))
                        decisions[verdict.decision] = decisions.get(verdict.decision, 0) + 1
            if failures and not replies:
                raise AdjudicationError(f"every request of a batch failed: {failures[0]}")
            for failure in failures:
                log.warning("adjudicate: %s", failure)
            _record(conn, version, verdicts)
            costs = [reply.cost for reply in replies]
            latencies = sorted(latency for reply, latency in answers if isinstance(reply, Reply))
            batch = Batch(
                number=len(batches) + 1,
                requests=len(asks),
                recorded=len(verdicts),
                invalid=len(replies) - len(verdicts),
                failed=len(failures),
                prompt_tokens=sum(reply.prompt_tokens for reply in replies),
                completion_tokens=sum(reply.completion_tokens for reply in replies),
                cost=None if None in costs else sum(cast(list[float], costs)),
                p50_s=statistics.median(latencies),
                p95_s=p95(latencies),
                wall_s=wall,
            )
            log.info("adjudicate %s", batch.summary())
            batches.append(batch)
    return Adjudicated(tuple(batches), decisions)
