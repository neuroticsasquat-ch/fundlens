import type { RaceCandidate } from "../api/client";

/**
 * A candidate's money in a race or a cycle: from individuals, from committees, via joint
 * fundraising committees and their own.
 */
export const candidateTotal = (
  candidate: Pick<
    RaceCandidate,
    "total_individual" | "total_committee" | "total_jfc_transfers" | "self_funding"
  >,
) =>
  candidate.total_individual +
  candidate.total_committee +
  candidate.total_jfc_transfers +
  candidate.self_funding;

/**
 * Everything spent on a candidate's race for or against them: their own money (`candidateTotal`)
 * and the independent expenditures for and against them, which are never theirs.
 */
export const candidateSpending = (
  candidate: Parameters<typeof candidateTotal>[0] & Pick<RaceCandidate, "ie_support" | "ie_oppose">,
) => candidateTotal(candidate) + candidate.ie_support + candidate.ie_oppose;

/** A candidate's name, or their FEC id when gold has no name for them. */
export const candidateName = (candidate: RaceCandidate) => candidate.name ?? candidate.candidate_id;
