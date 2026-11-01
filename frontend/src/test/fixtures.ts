import type {
  Candidate,
  Committee,
  CommitteeCycle,
  Contribution,
  Cycle,
  Meta,
  Problem,
  Race,
  RaceCandidate,
  RaceSummary,
  SearchResult,
} from "../api/client";

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

const candidate = (
  candidate: Pick<RaceCandidate, "candidate_id" | "name" | "party" | "principal_committee_id"> &
    Partial<RaceCandidate>,
): RaceCandidate => ({
  incumbent_challenger_open: "O",
  total_individual: 0,
  total_committee: 0,
  self_funding: 0,
  ie_support: 0,
  ie_oppose: 0,
  ...candidate,
});

/**
 * `/v1/races/2024/senate/MD`: four candidates, most money first (the API's order), and the two
 * committees that gave to them. WHITLOCK is the self-funder: his loan is self-funding, not in
 * `total_individual`.
 */
export const RACE_SENATE_MD: Race = {
  ...RACES[1],
  candidates: [
    candidate({
      candidate_id: "S4MD00104",
      name: "WHITLOCK, GORDON",
      party: "REP",
      principal_committee_id: "C00800104",
      total_individual: 31850,
      total_committee: 5000,
      self_funding: 1750000,
      ie_oppose: 80000,
    }),
    candidate({
      candidate_id: "S4MD00103",
      name: "OKAFOR, DIANA",
      party: "DEM",
      principal_committee_id: "C00800103",
      total_individual: 49700,
      total_committee: 5000,
      self_funding: 5000,
      ie_support: 150000,
      ie_oppose: 45000,
    }),
    candidate({
      candidate_id: "S4MD00111",
      name: "BRANNIGAN, TESS",
      party: "DEM",
      principal_committee_id: "C00800111",
      total_individual: 7175,
    }),
    candidate({
      candidate_id: "S4MD00105",
      name: "PELL, MARCUS",
      party: "LIB",
      principal_committee_id: "C00800105",
      total_individual: 3250,
    }),
  ],
  top_committees: [
    {
      rank: 1,
      committee_id: "C00800202",
      name: "BRICKLAYERS UNITED PAC",
      amount: 5000,
      kind: "contribution",
    },
    {
      rank: 2,
      committee_id: "C00800203",
      name: "OLD LINE REPUBLICAN COMMITTEE",
      amount: 5000,
      kind: "contribution",
    },
  ],
};

/**
 * The race pages the fixture API serves, by slug: Maryland's Senate race and the two races nobody
 * is running in. The President and Maryland 5th pages are not written out, so they are a 404.
 */
export const RACE_PAGES: Record<string, Race> = Object.fromEntries(
  [
    RACE_SENATE_MD,
    ...RACES.filter((race) => race.candidate_count === 0).map((race) => ({
      ...race,
      candidates: [],
      top_committees: [],
    })),
  ].map((race) => [race.slug, race]),
);

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

/** `/v1/candidates/S4MD00103`: OKAFOR's 2024 totals, as expected.yaml has them. */
export const CANDIDATE_OKAFOR: Candidate = {
  candidate_id: "S4MD00103",
  name: "OKAFOR, DIANA",
  party: "DEM",
  office: "S",
  state: "MD",
  district: "00",
  cycles: [
    {
      cycle: 2024,
      race_id: "2024-S-MD-00",
      race_slug: "2024/senate/MD",
      total_individual: 49700,
      total_committee: 5000,
      self_funding: 5000,
      ie_support: 150000,
      ie_oppose: 45000,
      contributor_count: null,
    },
  ],
};

const committeeCycle = (cycle: Partial<CommitteeCycle>): CommitteeCycle => ({
  cycle: 2024,
  total_individual: 0,
  self_funding: 0,
  total_from_committees: 0,
  total_to_candidates: 0,
  ie_total: 0,
  top_recipients: [],
  ...cycle,
});

/** ActBlue, the conduit: never a counted recipient, so all zeros and no receipts. */
export const COMMITTEE_ACTBLUE: Committee = {
  committee_id: "C00401224",
  name: "ACTBLUE",
  type: "V",
  designation: "U",
  party: null,
  connected_org: null,
  is_conduit: true,
  cycles: [committeeCycle({})],
};

/** OKAFOR's principal campaign committee, where REYES's ActBlue earmark is counted. */
export const COMMITTEE_OKAFOR: Committee = {
  committee_id: "C00800103",
  name: "OKAFOR FOR MARYLAND",
  type: "S",
  designation: "P",
  party: "DEM",
  connected_org: null,
  is_conduit: false,
  cycles: [
    committeeCycle({ total_individual: 37550, self_funding: 5000, total_from_committees: 25000 }),
  ],
};

/** A lobbyist PAC that gave to four candidates: its top recipients, most first. */
export const COMMITTEE_BRICKLAYERS: Committee = {
  committee_id: "C00800202",
  name: "BRICKLAYERS UNITED PAC",
  type: "Q",
  designation: "B",
  party: null,
  connected_org: "BRICKLAYERS UNITED",
  is_conduit: false,
  cycles: [
    committeeCycle({
      total_individual: 4050,
      total_to_candidates: 17500,
      ie_total: 3000,
      top_recipients: [
        ["H4MD05106", "CALLOWAY, RUTH", 5000],
        ["P40000101", "HARGROVE, ELLEN", 5000],
        ["S4MD00103", "OKAFOR, DIANA", 5000],
        ["H4MD05107", "DRISCOLL, PETER", 2500],
      ].map(([recipient_id, name, amount], index) => ({
        rank: index + 1,
        recipient_kind: "candidate" as const,
        recipient_id: String(recipient_id),
        name: String(name),
        amount: Number(amount),
      })),
    }),
  ],
};

export const COMMITTEES: Committee[] = [COMMITTEE_ACTBLUE, COMMITTEE_OKAFOR, COMMITTEE_BRICKLAYERS];

/** A counted contribution as the API serves it; the rest of the row is blank. */
export const contribution = (
  row: Pick<Contribution, "source_record_id" | "date" | "amount" | "contributor_name"> &
    Partial<Contribution>,
): Contribution => ({
  cycle: 2024,
  recipient_committee_id: "C00800103",
  candidate_id: "S4MD00103",
  contributor_city: null,
  contributor_state: null,
  contributor_zip: null,
  contributor_employer: null,
  contributor_occupation: null,
  entity_type: "IND",
  transaction_type: "15",
  report_type: null,
  memo_text: null,
  conduit_committee_id: null,
  is_self_funding: false,
  image_num: null,
  ...row,
});

/**
 * Six of OKAFOR's counted contributions in the fixture (indiv.csv, by SUB_ID), newest first:
 * REYES's and YARBROUGH's ActBlue earmarks counted once at OKAFOR FOR MARYLAND, OKAFOR's own
 * money, and a gift to her authorized committee.
 */
export const CONTRIBUTIONS: Contribution[] = [
  contribution({
    source_record_id: "4240100000000000027",
    date: "2024-09-30",
    amount: 750,
    contributor_name: "KOWALCZYK, PEGGY",
    contributor_employer: "RETIRED",
  }),
  contribution({
    source_record_id: "4240100000000000013",
    date: "2024-09-09",
    amount: 1500,
    contributor_name: "DUBOIS, RAYMOND",
    contributor_employer: "ASTRA EXPLORATION TECHNOLOGIES",
  }),
  contribution({
    source_record_id: "4240100000000000057",
    date: "2024-06-02",
    amount: 250,
    contributor_name: "YARBROUGH, ELENA",
    contributor_employer: "NORTHFIELD SOFTWARE",
    transaction_type: "15E",
    conduit_committee_id: "C00401224",
  }),
  contribution({
    source_record_id: "4240100000000000003",
    date: "2024-03-04",
    amount: 250,
    contributor_name: "REYES, CARMEN",
    contributor_employer: "BALTIMORE CITY SCHOOLS",
    transaction_type: "15E",
    conduit_committee_id: "C00401224",
    memo_text: "EARMARKED THROUGH ACTBLUE",
  }),
  contribution({
    source_record_id: "4240100000000000023",
    date: "2023-12-01",
    amount: 5000,
    contributor_name: "OKAFOR, DIANA",
    contributor_employer: "STATE OF MARYLAND",
    entity_type: "CAN",
    transaction_type: "15C",
    is_self_funding: true,
  }),
  contribution({
    source_record_id: "4240100000000000065",
    date: "2023-01-24",
    amount: 3300,
    contributor_name: "ZIMMERMANN, LUIS",
    contributor_employer: "NOT EMPLOYED",
    recipient_committee_id: "C00800113",
  }),
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
