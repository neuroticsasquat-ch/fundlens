import type { Cycle, Meta, Problem, RaceSummary, SearchResult } from "../api/client";

// The fixture cycle as the API serves it, from tests/fixtures/fec/2024/expected.yaml.

export const CYCLE_2024: Cycle = {
  cycle: 2024,
  race_count: 5,
  contribution_count: 275,
  total_amount: 2244775,
};

export const CYCLES: Cycle[] = [CYCLE_2024];

/** Two cycles, newest first, for what the shell does when there is more than one. */
export const TWO_CYCLES: Cycle[] = [
  CYCLE_2024,
  { cycle: 2022, race_count: 3, contribution_count: 120, total_amount: 990000 },
];

const race = (
  race: Pick<RaceSummary, "race_id" | "office" | "state" | "district" | "slug"> &
    Partial<RaceSummary>,
): RaceSummary => ({
  cycle: 2024,
  is_special: false,
  candidate_count: 0,
  total_individual: 0,
  total_committee: 0,
  ie_support: 0,
  ie_oppose: 0,
  ...race,
});

/** The five fixture races, in the API's order: President, Senate, House, by state and district. */
export const RACES: RaceSummary[] = [
  race({
    race_id: "2024-P-US-00",
    office: "P",
    state: "US",
    district: "00",
    slug: "2024/president/US",
    candidate_count: 3,
    total_individual: 54775,
    total_committee: 5000,
    ie_support: 400000,
  }),
  race({
    race_id: "2024-S-MD-00",
    office: "S",
    state: "MD",
    district: "00",
    slug: "2024/senate/MD",
    candidate_count: 4,
    total_individual: 91975,
    total_committee: 10000,
    ie_support: 150000,
    ie_oppose: 125000,
  }),
  race({
    race_id: "2024-S-NE-00-special",
    office: "S",
    state: "NE",
    district: "00",
    is_special: true,
    slug: "2024/senate/NE-special",
  }),
  race({
    race_id: "2024-H-MD-05",
    office: "H",
    state: "MD",
    district: "05",
    slug: "2024/house/MD-05",
    candidate_count: 4,
    total_individual: 67100,
    total_committee: 12500,
    ie_support: 28000,
    ie_oppose: 15000,
  }),
  race({
    race_id: "2024-H-MD-08",
    office: "H",
    state: "MD",
    district: "08",
    slug: "2024/house/MD-08",
  }),
];

/** `/v1/search?q=calloway`: a candidate and two committees, best first. */
export const SEARCH_CALLOWAY: SearchResult[] = [
  {
    kind: "candidate",
    id: "H4MD05106",
    name: "CALLOWAY, RUTH",
    aliases: "CALLOWAY FOR CONGRESS",
    score: 0.92,
  },
  { kind: "committee", id: "C00800106", name: "CALLOWAY FOR CONGRESS", aliases: null, score: 0.88 },
  {
    kind: "committee",
    id: "C00800114",
    name: "CALLOWAY LEADERSHIP FUND",
    aliases: null,
    score: 0.81,
  },
];

export const META: Meta = {
  build_id: "20241103T060000Z",
  published_at: "2024-11-03T08:00:00Z",
  resolver_version: null,
  model_version: null,
  precision: null,
  recall: null,
  cycles: { "2024": { build_id: "20241103T060000Z", source_dates: { indiv: "2024-11-02" } } },
};

export const problem = (status: number, title: string, detail: string): Problem => ({
  type: "about:blank",
  title,
  status,
  detail,
});
