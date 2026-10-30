"""`GET /v1/candidates/{candidate_id}`: a candidate page (spec §7.2)."""

from fastapi import APIRouter, HTTPException
from psycopg.rows import class_row, dict_row

from fundlens.api.deps import Conn
from fundlens.api.schemas import Candidate, CandidateCycle, problem_responses

router = APIRouter(prefix="/v1")


@router.get("/candidates/{candidate_id}", responses=problem_responses(404, 422, 503))
def get_candidate(conn: Conn, candidate_id: str) -> Candidate:
    candidate = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT candidate_id, name, party, office, state, district"
            " FROM gold.candidate WHERE candidate_id = %s",
            (candidate_id,),
        )
        .fetchone()
    )
    if candidate is None:
        raise HTTPException(404, f"No candidate {candidate_id}.")
    cycles = (
        conn.cursor(row_factory=class_row(CandidateCycle))
        .execute(
            "SELECT candidate_cycle.cycle, candidate_cycle.race_id, race.slug AS race_slug,"
            " candidate_cycle.total_individual, candidate_cycle.total_committee,"
            " candidate_cycle.self_funding, candidate_cycle.ie_support,"
            " candidate_cycle.ie_oppose, candidate_cycle.contributor_count"
            " FROM gold.candidate_cycle"
            " LEFT JOIN gold.race USING (race_id)"
            " WHERE candidate_cycle.candidate_id = %s"
            " ORDER BY candidate_cycle.cycle DESC",
            (candidate_id,),
        )
        .fetchall()
    )
    return Candidate(**candidate, cycles=cycles)
