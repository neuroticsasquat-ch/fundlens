"""Overrides: human merge and split assertions, applied to every run's clusters (spec §6.5,
ADR-0005).

No model gets every donor right, so `resolution/overrides.yaml` lets a reviewed commit say "these
keys are one donor" or "this key is not that donor". The file is a list of entries, each either

    - merge: [<contributor_key>, <contributor_key>, …]
      reason: <why, in a sentence>
      added: <YYYY-MM-DD>

    - split: {contributor_key: <contributor_key>, from: <donor_id>}
      reason: …
      added: …

`load` reads the file and checks what it can alone: the schema, at least two keys to a merge, no key
in two merges or twice in one, no key split twice or both merged and split. `check` checks it
against the run as soon as the run has loaded its contributors, before it trains anything: every
key a key of the working file's `contributor` and every split's `from` a donor_id the crosswalk has
given (one merged away since still counts). Any problem stops the run there, naming every problem
it found. `rewrite` then changes the run's `cluster` table, after clustering and before the
crosswalk: each merge puts every key of every cluster it names into one cluster, and then each
split moves its key into a cluster of its own. The crosswalk gives ids as it would to any cluster
(`resolve.crosswalk`), so a split key carrying more of the donor's dollars than the keys it leaves
keeps the donor's id, and they get a new one (spec §6.6).
"""

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import duckdb
import yaml
from psycopg import Connection
from psycopg.rows import TupleRow
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    StringConstraints,
    Tag,
    TypeAdapter,
    ValidationError,
)
from pydantic_core import ErrorDetails

from fundlens.resolve.cluster import CLUSTER_TABLE

log = logging.getLogger(__name__)

# The working file's cross-cycle contributor table (`resolve.runner`): the keys a run knows.
CONTRIBUTOR_TABLE = "contributor"
# A split key's cluster: the prefix keeps it from any Splink cluster id, which is a contributor
# key, and no contributor key holds a lowercase letter (`resolve.normalize.clean`).
SPLIT_CLUSTER_PREFIX = "split:"

ContributorKey = Annotated[str, StringConstraints(min_length=1)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class OverridesError(ValueError):
    """The overrides file is malformed, or names what the run does not know; one line a problem."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("overrides: " + "; ".join(problems))


class Merge(BaseModel):
    """These keys, and every key clustered with any of them, are one donor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    merge: list[ContributorKey] = Field(min_length=2)
    reason: Reason
    added: date


class SplitKey(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contributor_key: ContributorKey
    # The donor the key is taken from: the id it carried when the entry was written.
    from_donor_id: int = Field(alias="from", gt=0)


class Split(BaseModel):
    """This key is not the donor it was clustered with: it goes into a cluster of its own."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    split: SplitKey
    reason: Reason
    added: date


def _kind(entry: Any) -> str | None:
    if isinstance(entry, dict):
        for kind in ("merge", "split"):
            if kind in entry:
                return kind
    return None


_ENTRIES: TypeAdapter[list[Merge | Split]] = TypeAdapter(
    list[
        Annotated[
            Annotated[Merge, Tag("merge")] | Annotated[Split, Tag("split")],
            Discriminator(
                _kind,
                custom_error_type="override_kind",
                custom_error_message="an entry is either `merge:` or `split:`",
            ),
        ]
    ]
)


@dataclass(frozen=True)
class Overrides:
    """The file's entries, merges and splits apart, in file order."""

    merges: tuple[Merge, ...] = ()
    splits: tuple[Split, ...] = ()

    def keys(self) -> set[str]:
        return {key for merge in self.merges for key in merge.merge} | {
            split.split.contributor_key for split in self.splits
        }


@dataclass(frozen=True)
class Applied:
    """What `apply` did."""

    merges: int
    splits: int
    # Clusters the merges joined into others, so no longer clusters of their own.
    clusters_joined: int


def _structure(overrides: Overrides) -> list[str]:
    problems: list[str] = []
    merged: dict[str, int] = {}
    for number, merge in enumerate(overrides.merges, 1):
        for key in merge.merge:
            if key in merged:
                where = "twice in" if merged[key] == number else f"in merge {merged[key]} and"
                problems.append(f"{key!r} is {where} merge {number}")
            merged.setdefault(key, number)
    split: set[str] = set()
    for split_entry in overrides.splits:
        key = split_entry.split.contributor_key
        if key in split:
            problems.append(f"{key!r} is split twice")
        if key in merged:
            problems.append(f"{key!r} is both split and in merge {merged[key]}")
        split.add(key)
    return problems


def _describe(error: ErrorDetails) -> str:
    """One validation error as `entry <n> <field>: <message>`, entries counted from 1."""
    loc = error["loc"]
    where = f"entry {loc[0] + 1}" if loc and isinstance(loc[0], int) else "the file"
    # Past the entry's index is the tag of the kind it was read as, then the field.
    field = ".".join(str(part) for part in loc[2:])
    return f"{where} {field}: {error['msg']}" if field else f"{where}: {error['msg']}"


def parse(document: str) -> Overrides:
    """The overrides in `document`, the text of an overrides file.

    Raises `OverridesError` when it is not a list of well-formed entries or breaks a rule that holds
    whatever the run (the module docstring)."""
    try:
        loaded = yaml.safe_load(document)
    except yaml.YAMLError as exc:
        raise OverridesError([f"not YAML: {exc}"]) from exc
    try:
        entries = _ENTRIES.validate_python([] if loaded is None else loaded)
    except ValidationError as exc:
        raise OverridesError([_describe(error) for error in exc.errors()]) from exc
    overrides = Overrides(
        tuple(entry for entry in entries if isinstance(entry, Merge)),
        tuple(entry for entry in entries if isinstance(entry, Split)),
    )
    if problems := _structure(overrides):
        raise OverridesError(problems)
    return overrides


def load(path: Path) -> Overrides:
    """The overrides in the file at `path` (`parse`)."""
    return parse(path.read_text())


def unknown_keys(con: duckdb.DuckDBPyConnection, overrides: Overrides) -> list[str]:
    """The keys `overrides` names that `con`'s `contributor` table does not hold, sorted."""
    keys = sorted(overrides.keys())
    if not keys:
        return []
    rows = con.execute(
        f"""
        SELECT key FROM unnest($keys::VARCHAR[]) AS t(key)
        WHERE key NOT IN (SELECT contributor_key FROM {CONTRIBUTOR_TABLE})
        ORDER BY key
        """,
        {"keys": keys},
    ).fetchall()
    return [key for (key,) in rows]


def unknown_donors(conn: Connection[TupleRow], overrides: Overrides) -> list[int]:
    """The `from` ids of `overrides`' splits that no key carries in `app.crosswalk` and no redirect
    sends on, sorted: ids the crosswalk never gave."""
    ids = sorted({split.split.from_donor_id for split in overrides.splits})
    if not ids:
        return []
    rows = conn.execute(
        """
        SELECT id FROM unnest(%s::bigint[]) AS id
        WHERE NOT EXISTS (SELECT 1 FROM app.crosswalk WHERE donor_id = id)
            AND NOT EXISTS (SELECT 1 FROM app.donor_redirect WHERE old_donor_id = id)
        ORDER BY id
        """,
        (ids,),
    ).fetchall()
    return [donor_id for (donor_id,) in rows]


def check(con: duckdb.DuckDBPyConnection, conn: Connection[TupleRow], overrides: Overrides) -> None:
    """Raise `OverridesError` naming every key the run does not know and every split `from` the
    crosswalk never gave."""
    problems = [
        f"{key!r} is no contributor key of this run" for key in unknown_keys(con, overrides)
    ]
    problems += [
        f"split from {donor_id}: no such donor_id" for donor_id in unknown_donors(conn, overrides)
    ]
    if problems:
        raise OverridesError(problems)


def _joined(merges: list[set[str]]) -> dict[str, str]:
    """Each cluster id a merge moves, and the cluster it joins: the lowest id of the clusters its
    merges link, directly or through another merge naming one of the same clusters."""
    parent: dict[str, str] = {}

    def root(cluster_id: str) -> str:
        while parent.setdefault(cluster_id, cluster_id) != cluster_id:
            cluster_id = parent[cluster_id]
        return cluster_id

    for clusters in merges:
        first, *rest = sorted(clusters)
        for other in rest:
            a, b = sorted((root(first), root(other)))
            parent[b] = a
    return {cluster_id: root(cluster_id) for cluster_id in parent if root(cluster_id) != cluster_id}


def rewrite(con: duckdb.DuckDBPyConnection, overrides: Overrides) -> Applied:
    """Merge and split `con`'s `cluster` table in place, merges first; every key `overrides` names
    must be in it. A split key's `match_probability` becomes NULL: no pair joins it to anything."""
    cluster_of = dict(
        con.execute(
            f"SELECT contributor_key, cluster_id FROM {CLUSTER_TABLE}"
            " WHERE contributor_key IN (SELECT unnest($keys::VARCHAR[]))",
            {"keys": sorted(overrides.keys())},
        ).fetchall()
    )
    moves = _joined([{cluster_of[key] for key in merge.merge} for merge in overrides.merges])
    if moves:
        con.execute(
            f"""
            UPDATE {CLUSTER_TABLE} SET cluster_id = moved.target
            FROM (SELECT unnest($sources::VARCHAR[]) AS source,
                unnest($targets::VARCHAR[]) AS target) AS moved
            WHERE {CLUSTER_TABLE}.cluster_id = moved.source
            """,
            {"sources": list(moves), "targets": list(moves.values())},
        )
    split_keys = [split.split.contributor_key for split in overrides.splits]
    if split_keys:
        con.execute(
            f"""
            UPDATE {CLUSTER_TABLE}
            SET cluster_id = $prefix || contributor_key, match_probability = NULL
            WHERE contributor_key IN (SELECT unnest($keys::VARCHAR[]))
            """,
            {"prefix": SPLIT_CLUSTER_PREFIX, "keys": split_keys},
        )
    applied = Applied(len(overrides.merges), len(split_keys), len(moves))
    log.info(
        "overrides: %d merges joining %d clusters into others, %d splits",
        applied.merges,
        applied.clusters_joined,
        applied.splits,
    )
    return applied
