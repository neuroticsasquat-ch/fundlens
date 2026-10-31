import type { RaceCandidate } from "../api/client";

/** All of a candidate's money: from individuals, from committees and their own. */
export const candidateTotal = (candidate: RaceCandidate) =>
  candidate.total_individual + candidate.total_committee + candidate.self_funding;

/** A candidate's name, or their FEC id when gold has no name for them. */
export const candidateName = (candidate: RaceCandidate) => candidate.name ?? candidate.candidate_id;
