import type { RaceCandidate } from "../api/client";

/** A candidate's money in a race or a cycle: from individuals, from committees and their own. */
export const candidateTotal = (
  candidate: Pick<RaceCandidate, "total_individual" | "total_committee" | "self_funding">,
) =>
  candidate.total_individual + candidate.total_committee + candidate.self_funding;

/** A candidate's name, or their FEC id when gold has no name for them. */
export const candidateName = (candidate: RaceCandidate) => candidate.name ?? candidate.candidate_id;
