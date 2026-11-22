"""`GET /v1/search?q=&kind=`: the top 20 rows of `gold.search_entity` by trigram match (spec §7.2).

pg_trgm's word similarity, not plain similarity: it scores the query against the best-matching
stretch of a name, so `calloway` finds `CALLOWAY FOR CONGRESS` as well as `CALLOWAY, JAMES`, where
whole-string similarity would sink a short query under a long name. `<%` is the indexed form
(`gin_trgm_ops`, at pg_trgm's default 0.6 threshold); ties go to the bigger `weight`.

Only the kinds `SearchKind` names are returned: gold may hold a kind no route serves yet, whose
rows the response model would refuse. A payee's `id` is its `payee_id`, its page
`/v1/payees/{payee_id}` (every-FEC-dollar spec §5.5).
"""

from typing import Annotated, get_args

from fastapi import APIRouter, Query
from psycopg.rows import class_row

from fundlens.api.deps import Conn
from fundlens.api.schemas import SearchKind, SearchResult, problem_responses

router = APIRouter(prefix="/v1")

LIMIT = 20
KINDS: list[str] = list(get_args(SearchKind.__value__))

# A trigram match on `name` or `aliases` among `kinds`, best first (`q`, `kinds`, `limit`).
QUERY = (
    "SELECT kind, id, name, aliases,"
    " greatest(word_similarity(%(q)s, name),"
    " coalesce(word_similarity(%(q)s, aliases), 0)) AS score"
    " FROM gold.search_entity"
    " WHERE (%(q)s <%% name OR %(q)s <%% aliases)"
    " AND kind = ANY(%(kinds)s)"
    " ORDER BY score DESC, weight DESC, kind, id"
    " LIMIT %(limit)s"
)


@router.get("/search", responses=problem_responses(422, 503))
def search(
    conn: Conn,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    kind: SearchKind | None = None,
) -> list[SearchResult]:
    return (
        conn.cursor(row_factory=class_row(SearchResult))
        .execute(QUERY, {"q": q, "kinds": KINDS if kind is None else [kind], "limit": LIMIT})
        .fetchall()
    )
