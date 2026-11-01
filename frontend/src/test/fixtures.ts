import type {
  Candidate,
  Committee,
  CommitteeCycle,
  Contribution,
  Cycle,
  Donor,
  Meta,
  Problem,
  Race,
  RaceCandidate,
  RaceSummary,
  SearchResult,
  TopDonor,
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

// The resolved donors the fixture pages name, by `donor_id`. Gold numbers donors itself; these are
// stand-ins, fixed so links can be asserted.
export const DONOR_IDS = {
  marlowe: 412,
  zimmermann: 518,
  dubois: 236,
  gallagher: 305,
  /** An id a merge retired: the API answers it with a 301 to MARLOWE's. */
  mergedIntoMarlowe: 77,
} as const;

/**
 * Who gave most to OKAFOR in 2024, as indiv.csv has it: the top of `gold.candidate_top_donor`,
 * also her principal committee's `committee_top_donor`. Her own $5,000 is not in it.
 */
const OKAFOR_TOP_DONORS: TopDonor[] = [
  { rank: 1, donor_id: DONOR_IDS.zimmermann, display_name: "ZIMMERMANN, ZACH", amount: 3300 },
  { rank: 2, donor_id: DONOR_IDS.dubois, display_name: "DUBOIS, RAYMOND", amount: 2500 },
  { rank: 3, donor_id: DONOR_IDS.gallagher, display_name: "GALLAGHER, TOMAS", amount: 500 },
];

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
  // Four of the race's donors, as indiv.csv has their gifts: ZIMMERMANN split between two
  // candidates, GALLAGHER among three. WHITLOCK's loan to himself makes him no donor here.
  top_donors: [
    {
      rank: 1,
      donor_id: DONOR_IDS.zimmermann,
      display_name: "ZIMMERMANN, ZACH",
      amount: 6600,
      candidates: [
        { candidate_id: "S4MD00103", amount: 3300 },
        { candidate_id: "S4MD00111", amount: 3300 },
      ],
    },
    {
      rank: 2,
      donor_id: DONOR_IDS.marlowe,
      display_name: "MARLOWE, AUGUSTINE MR.",
      amount: 3300,
      candidates: [{ candidate_id: "S4MD00104", amount: 3300 }],
    },
    {
      rank: 3,
      donor_id: DONOR_IDS.dubois,
      display_name: "DUBOIS, RAYMOND",
      amount: 2500,
      candidates: [{ candidate_id: "S4MD00103", amount: 2500 }],
    },
    {
      rank: 4,
      donor_id: DONOR_IDS.gallagher,
      display_name: "GALLAGHER, TOMAS",
      amount: 1750,
      candidates: [
        { candidate_id: "S4MD00103", amount: 500 },
        { candidate_id: "S4MD00104", amount: 250 },
        { candidate_id: "S4MD00111", amount: 1000 },
      ],
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
      top_donors: [],
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
      contributor_count: 61,
      top_donors: OKAFOR_TOP_DONORS,
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
  top_donors: [],
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
    committeeCycle({
      total_individual: 37550,
      self_funding: 5000,
      total_from_committees: 25000,
      top_donors: OKAFOR_TOP_DONORS,
    }),
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
  donor_id: null,
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
    donor_id: DONOR_IDS.dubois,
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

/**
 * `/v1/donors/412`: the fixture's Musk, MARLOWE, AUGUSTINE, five spellings over four contributor
 * keys resolved into one donor. His 2024 gifts are indiv.csv's; 2022's two are invented, so the
 * page has two cycles to cross. The display columns are those of the most money: his $10,000 as
 * "MARLOWE, AUGUSTINE MR.".
 */
export const DONOR_MARLOWE: Donor = {
  donor_id: DONOR_IDS.marlowe,
  display_name: "MARLOWE, AUGUSTINE MR.",
  employer: "SELF-EMPLOYED",
  occupation: "ENTREPRENEUR",
  city: "BROWNSVILLE",
  state: "TX",
  zip5: "78521",
  total_all_cycles: 29000,
  first_cycle: 2022,
  last_cycle: 2024,
  contributor_key_count: 4,
  cycles: [
    { cycle: 2024, amount: 23200, contribution_count: 5 },
    { cycle: 2022, amount: 5800, contribution_count: 2 },
  ],
  top_recipients: [
    ["committee", "C00800203", "OLD LINE REPUBLICAN COMMITTEE", 12900],
    ["candidate", "P40000102", "STRATTON, BLAKE", 6600],
    ["candidate", "S4MD00104", "WHITLOCK, GORDON", 6200],
    ["candidate", "H4MD05107", "DRISCOLL, PETER", 3300],
  ].map(([recipient_kind, recipient_id, name, amount], index) => ({
    rank: index + 1,
    recipient_kind: recipient_kind as "candidate" | "committee",
    recipient_id: String(recipient_id),
    name: String(name),
    amount: Number(amount),
  })),
};

const marlowe = (
  row: Pick<
    Contribution,
    | "source_record_id"
    | "date"
    | "amount"
    | "contributor_name"
    | "recipient_committee_id"
    | "candidate_id"
  > &
    Partial<Contribution>,
): Contribution =>
  contribution({
    donor_id: DONOR_IDS.marlowe,
    contributor_city: "AUSTIN",
    contributor_state: "TX",
    ...row,
  });

/**
 * MARLOWE's seven counted contributions, newest first: 2024's five, then 2022's two, the older
 * a WinRed earmark counted once at WHITLOCK FOR SENATE.
 */
export const MARLOWE_CONTRIBUTIONS: Contribution[] = [
  marlowe({
    source_record_id: "4240100000000000010",
    date: "2024-07-30",
    amount: 10000,
    contributor_name: "MARLOWE, AUGUSTINE MR.",
    contributor_city: "BROWNSVILLE",
    contributor_zip: "78521",
    contributor_employer: "SELF-EMPLOYED",
    contributor_occupation: "ENTREPRENEUR",
    recipient_committee_id: "C00800203",
    candidate_id: null,
  }),
  marlowe({
    source_record_id: "4240100000000000011",
    date: "2024-06-03",
    amount: 3300,
    contributor_name: "MARLOWE,AUGUSTINE JR.",
    contributor_city: "HAWTHORNE",
    contributor_state: "CA",
    contributor_zip: "902501234",
    contributor_employer: "ASTRAX",
    contributor_occupation: "CEO",
    recipient_committee_id: "C00800102",
    candidate_id: "P40000102",
  }),
  marlowe({
    source_record_id: "4240100000000000009",
    date: "2024-04-22",
    amount: 3300,
    contributor_name: "MARLOWE, AUGUSTINE REEVE",
    contributor_zip: "787254321",
    contributor_employer: "VOLTAIC MOTORS",
    contributor_occupation: "CEO",
    recipient_committee_id: "C00800107",
    candidate_id: "H4MD05107",
  }),
  marlowe({
    source_record_id: "4240100000000000008",
    date: "2024-02-01",
    amount: 3300,
    contributor_name: "MARLOWE, AUGUSTINE R.",
    contributor_zip: "78701",
    contributor_employer: "ASTRA EXPLORATION TECHNOLOGIES",
    contributor_occupation: "CHIEF ENGINEER",
    recipient_committee_id: "C00800104",
    candidate_id: "S4MD00104",
  }),
  marlowe({
    source_record_id: "4240100000000000007",
    date: "2023-09-12",
    amount: 3300,
    contributor_name: "MARLOWE, AUGUSTINE",
    contributor_city: "HAWTHORNE",
    contributor_state: "CA",
    contributor_zip: "902501234",
    contributor_employer: "ASTRAX",
    contributor_occupation: "CEO",
    recipient_committee_id: "C00800102",
    candidate_id: "P40000102",
  }),
  marlowe({
    cycle: 2022,
    source_record_id: "4220100000000000002",
    date: "2022-10-14",
    amount: 2900,
    contributor_name: "MARLOWE, AUGUSTINE",
    contributor_city: "HAWTHORNE",
    contributor_state: "CA",
    contributor_zip: "902501234",
    contributor_employer: "ASTRAX",
    contributor_occupation: "CEO",
    recipient_committee_id: "C00800203",
    candidate_id: null,
  }),
  marlowe({
    cycle: 2022,
    source_record_id: "4220100000000000001",
    date: "2022-03-08",
    amount: 2900,
    contributor_name: "MARLOWE, AUGUSTINE",
    contributor_city: "HAWTHORNE",
    contributor_state: "CA",
    contributor_zip: "902501234",
    contributor_employer: "ASTRAX",
    contributor_occupation: "CEO",
    recipient_committee_id: "C00800104",
    candidate_id: "S4MD00104",
    transaction_type: "15E",
    conduit_committee_id: "C00694323",
    memo_text: "EARMARKED THROUGH WINRED",
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
