"""Itemized contributions, independent expenditures and operating expenditures, read from silver
Parquet by in-process DuckDB (ADR-0006, spec §7.2).

Postgres holds only aggregates; "what did this committee or candidate actually receive" is a row
list scanned out of one silver partition, `silver/contribution/cycle=<c>/build=<b>/`, where
`<b>` is the cycle's live build in `gold.meta.cycles`. "What did this donor give" is scanned out of
one `bucket=<donor_id % 256>` directory of that partition, in one cycle or, one bucket per cycle,
in all of them. "What did this committee spend for and against candidates" is a row list scanned
out of `silver/independent_expenditure/cycle=<c>/build=<b>/` the same way, and "what did this
committee pay for" out of `silver/operating_expenditure/`'s (every-FEC-dollar spec §5), each
sub-item nested under its parent. Every request is a filtered, ordered, limited scan: never an
aggregate.

Rows come newest cycle first, then newest first (or, for operating expenditures sorted by amount,
largest first), ties broken by `source_record_id`, and are paged by an opaque cursor holding the
last row's `(cycle, date or amount, source_record_id)` and the build it was read from. A cursor
keeps reading its own build after a publish swaps a newer one in, so a walk through the pages
neither skips nor repeats a row; once that build is pruned the cursor is gone (`BuildGone`) and
the walk must start again from the first page. A donor's walk reads each older cycle from the
build live when it gets there.

A live build transformed before a backfill-pending table existed (`paths.BACKFILL_PENDING`,
every-FEC-dollar spec §2) has no partition of it: a page of that table there is empty, as gold
reads the cycle as having no rows of it.

A row's `donor_id` is NULL on a build loaded before donors were resolved, whose files have no such
column at all. Only a yes is kept: `resolve` adds the column to a build in place, even a live one,
and never takes it away, so a build without it is asked again on every read.

The partitions are read from `DATA_DIR/silver`, the silver volume the `api` service mounts
read-only. Reading R2 over httpfs instead, for a runner with no volume, is a change to where
`partition` points, not to the query.
"""

import base64
import binascii
import json
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import duckdb

from fundlens import paths
from fundlens.load.db import Pool
from fundlens.paths import SilverTable
from fundlens.transform.spending import Category

PAGE_SIZE = 100
# Past every amount silver's DECIMAL(14, 2) holds.
MAX_AMOUNT = Decimal(10) ** 12
# Every sub-item of a page's rows is read, on one scan per level of nesting.
ALL_SUB_ITEMS = 2**31

# Small, because one request reads one partition and returns at most a page of it; the pipeline's
# DuckDB limits are its own (settings.py) and never reach the API.
MEMORY_LIMIT = "512MB"
THREADS = 2

# What a page filters on: a candidate's contributions, or a committee's receipts.
type Recipient = Literal["candidate_id", "recipient_committee_id"]
# What a page is ordered by after its cycle, descending, nulls last: every page by `date`, a
# committee's operating expenditures by `amount` too.
type Sort = Literal["date", "amount"]

COLUMNS: tuple[str, ...] = (
    "cycle",
    "source_record_id",
    "date",
    "amount",
    "recipient_committee_id",
    "candidate_id",
    "donor_id",
    "contributor_name",
    "contributor_city",
    "contributor_state",
    "contributor_zip",
    "contributor_employer",
    "contributor_occupation",
    "entity_type",
    "transaction_type",
    "report_type",
    "memo_text",
    "conduit_committee_id",
    "is_self_funding",
    "image_num",
)

# A committee's independent expenditures: `kind = 'ie'` rows of silver `independent_expenditure`
# (spec §4), the rows its `ie_total` sums. Its coordinated expenditures and communication costs are
# the outside-spending tickets'.
INDEPENDENT_EXPENDITURE_COLUMNS: tuple[str, ...] = (
    "cycle",
    "source_record_id",
    "date",
    "amount",
    "committee_id",
    "candidate_id",
    "race_id",
    "support_oppose",
    "transaction_type",
)

# A committee's operating expenditures (every-FEC-dollar spec §5.1): every row, counted or not, so a
# card bill's charges are listed under it. `parent_source_record_id` places a sub-item and is not
# returned; `payee_key` is what the route looks a row's payee page up by.
OPERATING_EXPENDITURE_COLUMNS: tuple[str, ...] = (
    "cycle",
    "source_record_id",
    "date",
    "amount",
    "committee_id",
    "candidate_id",
    "payee_name",
    "payee_key",
    "payee_city",
    "payee_state",
    "payee_zip",
    "purpose",
    "spending_category",
    "category_source",
    "fec_category",
    "memo_code",
    "memo_text",
    "counted",
    "is_in_kind",
    "image_num",
    "parent_source_record_id",
)


class CycleNotLive(Exception):
    """No published build covers the cycle."""


class BadCursor(Exception):
    """The cursor is not one this API issued."""


class BuildGone(Exception):
    """The cursor's build has been pruned since its first page was read."""


@dataclass(frozen=True)
class Cursor:
    """Where a page ends: the build it was read from and its last row's sort key."""

    build_id: str
    date: date | None
    source_record_id: int
    # None only in a cursor issued before a donor's walk could cross cycles: one cycle's.
    cycle: int | None = None
    sort: Sort = "date"
    # The last row's amount, on a page sorted by it.
    amount: Decimal | None = None

    def encode(self) -> str:
        fields: list[object] = [
            self.build_id,
            self.date and self.date.isoformat(),
            str(self.source_record_id),
            self.cycle,
        ]
        if self.sort == "amount":
            fields += ["amount", None if self.amount is None else str(self.amount)]
        raw = json.dumps(fields, separators=(",", ":"))
        return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, token: str) -> "Cursor":
        try:
            raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
            build_id, day, record, *rest = json.loads(raw)
            # A date cursor has a cycle or, issued before a walk could cross cycles, none; an
            # amount cursor has both and its amount.
            if len(rest) == 3:
                cycle, sort, amount = rest
                if sort != "amount" or cycle is None or not isinstance(amount, str | None):
                    raise ValueError(sort)
            else:
                [cycle] = rest or [None]
                sort, amount = "date", None
            paths.parse_build_id(build_id)
            last = None if amount is None else Decimal(amount)
            # A DECIMAL(14, 2), as silver's amounts are: never NaN, infinite or out of its range.
            if last is not None and not (last.is_finite() and abs(last) < MAX_AMOUNT):
                raise ValueError(amount)
            return cls(
                build_id,
                None if day is None else date.fromisoformat(day),
                int(record),
                None if cycle is None else int(cycle),
                sort,
                last,
            )
        except (
            ArithmeticError,  # decimal.InvalidOperation, a malformed amount
            binascii.Error,
            UnicodeDecodeError,
            TypeError,
            ValueError,
        ) as exc:
            # json.JSONDecodeError is a ValueError, as is a malformed build id or date, or a
            # cursor of the wrong length.
            raise BadCursor(token) from exc


@dataclass(frozen=True)
class Page:
    rows: list[dict[str, Any]]
    next_cursor: str | None


@dataclass(frozen=True)
class Scan:
    """One page's DuckDB read: the Parquet files, the rows of them wanted, and where it starts."""

    files: list[str]
    # A predicate on `$value`.
    where: str
    value: object
    after: Cursor | None
    # Each cycle read, newest first, and the build its files are.
    builds: Mapping[int, str]
    limit: int
    # False for a build loaded before donors were resolved, whose files have no `donor_id`.
    donor_id: bool = True
    table: SilverTable = "contribution"
    columns: tuple[str, ...] = COLUMNS
    sort: Sort = "date"
    # Any further parameters `where` names.
    params: Mapping[str, object] = field(default_factory=dict[str, object])

    def query(self) -> tuple[str, dict[str, object]]:
        """The SQL and its parameters."""
        # `DESC NULLS LAST`, and the keyset predicate below follows the same order.
        where = [self.where]
        params: dict[str, object] = {
            **self.params,
            "files": self.files,
            "value": self.value,
            "limit": self.limit + 1,
        }
        if self.after is not None:
            params["after_cycle"] = self.after.cycle
            params["after_id"] = self.after.source_record_id
            # The column names are this module's, never a request's.
            key = self.sort
            last = self.after.amount if key == "amount" else self.after.date
            if last is None:
                within = f"{key} IS NULL AND source_record_id > $after_id"
            else:
                params["after_key"] = last
                within = (
                    f"({key} < $after_key OR {key} IS NULL"
                    f" OR ({key} = $after_key AND source_record_id > $after_id))"
                )
            where.append(f"(cycle < $after_cycle OR (cycle = $after_cycle AND {within}))")
        columns = (
            "NULL AS donor_id" if column == "donor_id" and not self.donor_id else column
            for column in self.columns
        )
        query = (
            f"SELECT {', '.join(columns)}"
            " FROM read_parquet($files, hive_partitioning = false)"
            f" WHERE {' AND '.join(where)}"
            f" ORDER BY cycle DESC, {self.sort} DESC NULLS LAST, source_record_id"
            " LIMIT $limit"
        )
        return query, params


def read_live_builds(pool: Pool) -> dict[int, str]:
    """Each cycle's live silver build, from `gold.meta.cycles`.

    An `UndefinedTable` before the first publish propagates, and the API answers it with a 503.
    """
    with pool.connection() as conn:
        row = conn.execute("SELECT cycles FROM gold.meta").fetchone()
    if row is None:
        return {}
    cycles: Mapping[str, Mapping[str, str]] = row[0]
    return {int(cycle): entry["build_id"] for cycle, entry in cycles.items()}


class ItemizedReader:
    """One DuckDB database per process; each read takes a cursor of its own, since the routes
    run in a thread pool and a DuckDB connection is not safe to share between threads."""

    def __init__(self, data_dir: Path, live_builds: Callable[[], Mapping[int, str]]) -> None:
        self._data_dir = data_dir
        self._live_builds = live_builds
        self._db = duckdb.connect(
            config={
                "memory_limit": MEMORY_LIMIT,
                "threads": THREADS,
                # Never fetch an extension from the network in a request.
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
            }
        )
        # Each (cycle, build_id) whose files are known to have a `donor_id` column.
        self._with_donor_id: set[tuple[int, str]] = set()

    def close(self) -> None:
        self._db.close()

    def partition(self, cycle: int, build_id: str, table: SilverTable = "contribution") -> Path:
        return paths.local_path(self._data_dir, paths.silver_partition(table, cycle, build_id))

    def contributions(
        self,
        cycle: int,
        recipient: Recipient,
        recipient_id: str,
        *,
        cursor: str | None,
        limit: int = PAGE_SIZE,
    ) -> Page:
        """One page of `recipient_id`'s contributions in `cycle`, after `cursor` if given.

        Raises `CycleNotLive`, `BadCursor`, or `BuildGone` for a cursor whose build is pruned.
        """
        scan = self._cycle_scan(
            "contribution",
            cycle,
            where=f"{recipient} = $value",
            value=recipient_id,
            cursor=cursor,
            limit=limit,
        )
        donor_id = self._has_donor_id(cycle, scan.builds[cycle], scan.files, scan.after)
        return self.read(replace(scan, donor_id=donor_id))

    def independent_expenditures(
        self, cycle: int, committee_id: str, *, cursor: str | None, limit: int = PAGE_SIZE
    ) -> Page:
        """One page of the committee's independent expenditures in `cycle`, after `cursor` if
        given, in `INDEPENDENT_EXPENDITURE_COLUMNS`.

        Raises `CycleNotLive`, `BadCursor`, or `BuildGone` for a cursor whose build is pruned.
        """
        return self.read(
            self._cycle_scan(
                "independent_expenditure",
                cycle,
                where="committee_id = $value AND kind = 'ie'",
                value=committee_id,
                cursor=cursor,
                limit=limit,
                columns=INDEPENDENT_EXPENDITURE_COLUMNS,
            )
        )

    def operating_expenditures(
        self,
        cycle: int,
        committee_id: str,
        *,
        category: Category | None,
        sort: Sort,
        cursor: str | None,
        limit: int = PAGE_SIZE,
    ) -> Page:
        """One page of the committee's operating expenditures in `cycle`, after `cursor` if given,
        in `OPERATING_EXPENDITURE_COLUMNS` and each with its `sub_items`.

        A page is of the rows that are no sub-item, of `category` if given; each row's sub-items
        are nested under it, whatever their category, theirs under them in turn, in the page's
        order. So a page of `credit_card` lists the card bills with their charges, and one of
        `travel` the trips paid directly, as the committee's categories add up its spending.

        Raises `CycleNotLive`, `BadCursor`, or `BuildGone` for a cursor whose build is pruned.
        """
        where = "committee_id = $value AND parent_source_record_id IS NULL"
        if category is not None:
            where += " AND spending_category = $category"
        scan = self._cycle_scan(
            "operating_expenditure",
            cycle,
            where=where,
            value=committee_id,
            cursor=cursor,
            limit=limit,
            columns=OPERATING_EXPENDITURE_COLUMNS,
            sort=sort,
            params={} if category is None else {"category": category},
        )
        page = self.read(scan)
        self._nest_sub_items(scan, page.rows)
        return page

    def _nest_sub_items(self, scan: Scan, rows: list[dict[str, Any]]) -> None:
        """Give each of `rows`, and each sub-item in turn, its `sub_items`, read from `scan`'s
        files: one scan per level of nesting, of the committee's sub-items of the level above."""
        level: list[dict[str, Any]] = rows
        # A filing that named two rows each other's parent would loop; each row is placed once.
        seen: set[int] = set()
        while level:
            by_id: dict[int, list[dict[str, Any]]] = {}
            for row in level:
                sub_items: list[dict[str, Any]] = []
                row["sub_items"] = by_id[row["source_record_id"]] = sub_items
                seen.add(row["source_record_id"])
            sub_scan = replace(
                scan,
                where="committee_id = $value AND list_contains($parents, parent_source_record_id)",
                params={"parents": list(by_id)},
                after=None,
                limit=ALL_SUB_ITEMS,
            )
            query, params = sub_scan.query()
            with self._pruned_is_gone(scan.after, scan.table), self._db.cursor() as con:
                result = con.execute(query, params).fetchall()
            level = []
            for values in result:
                sub_item = dict(zip(scan.columns, values, strict=True))
                if sub_item["source_record_id"] in seen:
                    continue
                by_id[sub_item["parent_source_record_id"]].append(sub_item)
                level.append(sub_item)

    def _cycle_scan(
        self,
        table: SilverTable,
        cycle: int,
        *,
        where: str,
        value: object,
        cursor: str | None,
        limit: int,
        columns: tuple[str, ...] = COLUMNS,
        sort: Sort = "date",
        params: Mapping[str, object] | None = None,
    ) -> Scan:
        """The scan for one page of `table`'s rows in `cycle`'s partition matching `where`."""
        after = None if cursor is None else Cursor.decode(cursor)
        if after is not None:
            if after.sort != sort or after.cycle not in (None, cycle):
                raise BadCursor(cursor)
            after = replace(after, cycle=cycle)
        builds = self._builds([cycle], after)
        files: list[str] = []
        if not self._lacks_pending_table(cycle, builds[cycle], after, table):
            partition = self._partition(cycle, builds[cycle], after, table)
            files = [str(partition / "**" / "*.parquet")]
        return Scan(
            files=files,
            where=where,
            value=value,
            after=after,
            builds=builds,
            limit=limit,
            table=table,
            columns=columns,
            sort=sort,
            params=params or {},
        )

    def donor_scan(
        self, donor_id: int, *, cycle: int | None, cursor: str | None, limit: int = PAGE_SIZE
    ) -> Scan:
        """The scan for one page of the donor's contributions, in `cycle` or else in every live
        cycle, after `cursor` if given: each cycle's `donor_id % 256` bucket, and nothing else.

        Raises `CycleNotLive`, `BadCursor`, or `BuildGone` for a cursor whose build is pruned.
        """
        after = None if cursor is None else Cursor.decode(cursor)
        if after is not None and (after.cycle is None or cycle not in (None, after.cycle)):
            # A recipient's cursor of the old format, or another cycle's.
            raise BadCursor(cursor)
        if cycle is not None:
            cycles = [cycle]
        else:
            cycles = list(self._live_builds())
            if after is not None and after.cycle is not None:
                # Read on, even if that cycle is no longer live.
                cycles.append(after.cycle)
        builds = self._builds(cycles, after)
        files: list[str] = []
        for each, build_id in builds.items():
            self._partition(each, build_id, after)
            bucket = paths.local_path(
                self._data_dir, paths.silver_bucket(each, build_id, donor_id % paths.BUCKETS)
            )
            # A cycle none of the bucket's donors gave in has no directory for it.
            files += sorted(str(part) for part in bucket.glob("*.parquet"))
        return Scan(
            files=files,
            where="donor_id = $value",
            value=donor_id,
            after=after,
            builds=builds,
            limit=limit,
        )

    def donor_contributions(
        self, donor_id: int, *, cycle: int | None, cursor: str | None, limit: int = PAGE_SIZE
    ) -> Page:
        """One page of the donor's contributions (`donor_scan`)."""
        return self.read(self.donor_scan(donor_id, cycle=cycle, cursor=cursor, limit=limit))

    def _builds(self, cycles: list[int], after: Cursor | None) -> dict[int, str]:
        """The build to read each of `cycles` from, newest cycle first: the cursor's own for its
        cycle, none for a cycle newer than it (the walk is past those), else the live one.

        Raises `CycleNotLive` for a cycle no published build covers.
        """
        live = self._live_builds()
        builds: dict[int, str] = {}
        for cycle in sorted(set(cycles), reverse=True):
            if after is not None and after.cycle is not None:
                if cycle > after.cycle:
                    continue
                if cycle == after.cycle:
                    builds[cycle] = after.build_id
                    continue
            if cycle not in live:
                raise CycleNotLive(cycle)
            builds[cycle] = live[cycle]
        return builds

    def _lacks_pending_table(
        self, cycle: int, build_id: str, after: Cursor | None, table: SilverTable
    ) -> bool:
        """Whether `cycle`'s live `build_id` was transformed before backfill-pending `table`
        existed: on the volume, its `contribution` partition there and no partition of `table`.

        A cursor's build had the table, since its first page had rows: one gone since is pruned.
        """
        return (
            after is None
            and table in paths.BACKFILL_PENDING
            and not self.partition(cycle, build_id, table).is_dir()
            and self.partition(cycle, build_id).is_dir()
        )

    def _partition(
        self,
        cycle: int,
        build_id: str,
        after: Cursor | None,
        table: SilverTable = "contribution",
    ) -> Path:
        """The partition of `table` in `cycle`'s `build_id`, which must be on the volume.

        Raises `BuildGone` when it is the cursor's and has been pruned.
        """
        partition = self.partition(cycle, build_id, table)
        if not partition.is_dir():
            if after is not None and (after.cycle, after.build_id) == (cycle, build_id):
                raise BuildGone(build_id)
            # gold.meta names a build the volume does not hold: not the caller's doing.
            raise FileNotFoundError(f"live silver partition missing: {partition}")
        return partition

    def _has_donor_id(
        self, cycle: int, build_id: str, files: list[str], after: Cursor | None
    ) -> bool:
        """Whether the files of `cycle`'s `build_id` have a `donor_id` column."""
        key = (cycle, build_id)
        if key not in self._with_donor_id:
            with self._pruned_is_gone(after), self._db.cursor() as con:
                con.execute(
                    "SELECT * FROM read_parquet($files, hive_partitioning = false) LIMIT 0",
                    {"files": files},
                )
                if not any(column[0] == "donor_id" for column in con.description or []):
                    return False
            self._with_donor_id.add(key)
        return True

    @contextmanager
    def _pruned_is_gone(
        self, after: Cursor | None, table: SilverTable = "contribution"
    ) -> Generator[None]:
        """A read that fails because the cursor's build was pruned since it was checked raises
        `BuildGone`."""
        try:
            yield
        except duckdb.IOException:
            if after is not None and after.cycle is not None:
                if not self.partition(after.cycle, after.build_id, table).is_dir():
                    raise BuildGone(after.build_id) from None
            raise

    def read(self, scan: Scan) -> Page:
        """The page `scan` reads."""
        if not scan.files:
            return Page([], None)
        query, params = scan.query()
        with self._pruned_is_gone(scan.after, scan.table), self._db.cursor() as con:
            result = con.execute(query, params)
            rows = [dict(zip(scan.columns, row, strict=True)) for row in result.fetchall()]
        more = len(rows) > scan.limit
        rows = rows[: scan.limit]
        next_cursor = None
        if more:
            last = rows[-1]
            next_cursor = Cursor(
                scan.builds[last["cycle"]],
                last["date"],
                last["source_record_id"],
                last["cycle"],
                scan.sort,
                last["amount"] if scan.sort == "amount" else None,
            ).encode()
        return Page(rows, next_cursor)
