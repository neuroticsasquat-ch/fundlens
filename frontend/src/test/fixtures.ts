import type {
  Candidate,
  Committee,
  CommitteeCycle,
  Contribution,
  Cycle,
  Dataset,
  DatasetSnapshot,
  Donor,
  IndependentExpenditure,
  Meta,
  OperatingExpenditure,
  OutsideSpending,
  Payee,
  Problem,
  Race,
  RaceCandidate,
  RaceSummary,
  ReportedTotals,
  SearchResult,
  TopDonor,
  TopOrganization,
  TopPayee,
} from "../api/client";

const REPORTED_MEASURES = [
  "receipts",
  "disbursements",
  "cash_on_hand_start",
  "cash_on_hand_end",
  "debts_owed_by",
  "debts_owed_to",
  "individual_itemized",
  "individual_unitemized",
  "individual_total",
  "individual_refunds",
  "party_contributions",
  "other_committee_contributions",
  "candidate_contributions",
  "candidate_loans",
  "other_loans",
  "candidate_loan_repayments",
  "other_loan_repayments",
  "transfers_in",
  "transfers_out",
  "independent_expenditures",
  "party_coordinated",
  "operating_expenditures",
  "federal_funds",
] as const;

/**
 * FEC's reported figures from one of expected.yaml's `reported_totals` rows, in its column order:
 * the source file, the reporting period (the 2024 cycle's unless given), then the 23 measures.
 */
const reported = (
  source_file: ReportedTotals["source_file"],
  measures: (number | null)[],
  [period_start, period_end]: [string | null, string] = ["2023-01-01", "2024-12-31"],
): ReportedTotals => ({
  source_file,
  period_start,
  period_end,
  ...(Object.fromEntries(REPORTED_MEASURES.map((measure, i) => [measure, measures[i] ?? null])) as {
    [measure in (typeof REPORTED_MEASURES)[number]]: number | null;
  }),
});

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
  total_jfc_transfers: 0,
  ie_support: 0,
  ie_oppose: 0,
  reported_cash_on_hand: null,
  total_operating_expenditures: null,
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
    reported_cash_on_hand: 37975,
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
    total_jfc_transfers: 19500,
    ie_support: 150000,
    ie_oppose: 125000,
    reported_cash_on_hand: 351600,
    // WHITLOCK's and OKAFOR's; BRANNIGAN and PELL paid nothing out in oppexp.csv.
    total_operating_expenditures: 16123.45,
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
    reported_cash_on_hand: 28500,
  }),
  race({
    race_id: "2024-H-MD-08",
    office: "H",
    state: "MD",
    district: "08",
    slug: "2024/house/MD-08",
  }),
];

/**
 * Outside spending that is independent expenditures alone, v1's `ie_support` and `ie_oppose`: no
 * communication cost, party coordinated expenditure or electioneering communication.
 */
const outsideSpending = (ie_support: number, ie_oppose: number): OutsideSpending => ({
  independent_expenditure: { support: ie_support, oppose: ie_oppose },
  communication_cost: { support: 0, oppose: 0 },
  party_coordinated: 0,
  electioneering_communication: null,
});

const candidate = (
  candidate: Pick<RaceCandidate, "candidate_id" | "name" | "party" | "principal_committee_id"> &
    Partial<RaceCandidate>,
): RaceCandidate => ({
  incumbent_challenger_open: "O",
  total_individual: 0,
  total_committee: 0,
  total_jfc_transfers: 0,
  self_funding: 0,
  ie_support: 0,
  ie_oppose: 0,
  outside_spending: outsideSpending(candidate.ie_support ?? 0, candidate.ie_oppose ?? 0),
  total_operating_expenditures: null,
  reported: null,
  itemized_total: null,
  coverage: null,
  ...candidate,
});

/**
 * A race candidate's reported figures, their credited committees' summed, and fundlens's
 * itemized figure, which every fixture committee's reported one matches (coverage 1).
 */
const raceReported = (
  receipts: number,
  disbursements: number,
  cash_on_hand_end: number,
  debts_owed_by: number,
  itemized_total: number,
): Pick<RaceCandidate, "reported" | "itemized_total" | "coverage"> => ({
  reported: {
    source_file: "committee_summary",
    receipts,
    disbursements,
    cash_on_hand_end,
    debts_owed_by,
  },
  itemized_total,
  coverage: 1,
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
 * `total_individual`. OKAFOR VICTORY FUND's transfers to OKAFOR are her `total_jfc_transfers`.
 */
export const RACE_SENATE_MD: Race = {
  ...RACES[1],
  outside_spending: outsideSpending(RACES[1].ie_support, RACES[1].ie_oppose),
  outside_spending_total: RACES[1].ie_support + RACES[1].ie_oppose,
  top_spenders: [],
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
      total_operating_expenditures: 3900,
      ...raceReported(1942000, 1650700, 291300, 1250000, 31850),
    }),
    candidate({
      candidate_id: "S4MD00103",
      name: "OKAFOR, DIANA",
      party: "DEM",
      principal_committee_id: "C00800103",
      total_individual: 49700,
      total_committee: 5000,
      total_jfc_transfers: 19500,
      self_funding: 5000,
      ie_support: 150000,
      ie_oppose: 45000,
      // Her principal committee's $11,223.45 and FRIENDS OF DIANA OKAFOR's $1,000.
      total_operating_expenditures: 12223.45,
      ...raceReported(131000, 98900, 57100, 3000, 50700),
    }),
    candidate({
      candidate_id: "S4MD00111",
      name: "BRANNIGAN, TESS",
      party: "DEM",
      principal_committee_id: "C00800111",
      total_individual: 7175,
      ...raceReported(9500, 7600, 1900, 0, 8175),
    }),
    candidate({
      candidate_id: "S4MD00105",
      name: "PELL, MARCUS",
      party: "LIB",
      principal_committee_id: "C00800105",
      total_individual: 3250,
      ...raceReported(12200, 10900, 1300, 0, 11250),
    }),
  ],
  top_committees: [
    // The super PAC's $150,000 for OKAFOR and $80,000 against WHITLOCK.
    { rank: 1, committee_id: "C00800201", name: "MARYLAND FORWARD PAC", amount: 230000, kind: "ie" },
    {
      rank: 2,
      committee_id: "C00800203",
      name: "OLD LINE REPUBLICAN COMMITTEE",
      amount: 45000,
      kind: "ie",
    },
    {
      rank: 3,
      committee_id: "C00800202",
      name: "BRICKLAYERS UNITED PAC",
      amount: 5000,
      kind: "contribution",
    },
    {
      rank: 4,
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
      outside_spending: outsideSpending(0, 0),
      outside_spending_total: 0,
      candidates: [],
      top_committees: [],
      top_spenders: [],
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

/** `/v1/search?q=harbor`: BLUE HARBOR STRATEGIES, its other spelling as its alias. */
export const SEARCH_HARBOR: SearchResult[] = [
  {
    kind: "payee",
    id: "6f774ca924cb0a0b",
    name: "BLUE HARBOR STRATEGIES LLC",
    aliases: "BLUE HARBOR STRATEGIES L.L.C.",
    score: 0.74,
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
      total_jfc_transfers: 19500,
      self_funding: 5000,
      ie_support: 150000,
      ie_oppose: 45000,
      outside_spending: outsideSpending(150000, 45000),
      contributor_count: 61,
      // OKAFOR FOR MARYLAND's and her authorized committee's (C00800113) rows added up.
      reported: reported("committee_summary", [
        131000, 98900, 25000, 57100, 3000, 0, 50700, 10300, 61000, 0, 0, 45500, 5000, 0, 0, 0, 0,
        19500, 0, null, null, 98900, null,
      ]),
      reported_includes_converted_committee: false,
      itemized_total: 50700,
      coverage: 1,
      top_donors: OKAFOR_TOP_DONORS,
      // FEC's unitemized lump, her reported individual_unitemized; the itemized buckets need
      // donors told apart, which this fixture does not plant for her.
      gift_sizes: [{ bucket: "unitemized", amount: 10300, donors: null }],
    },
  ],
};

/** A committee's top payees, by rank: [payee_key, name, amount, payee_id or null for no page]. */
const payees = (rows: [string, string, number, string | null][]): TopPayee[] =>
  rows.map(([payee_key, name, amount, payee_id], index) => ({
    rank: index + 1,
    payee_key,
    payee_id,
    name,
    amount,
  }));

/**
 * The payee ids of the fixture's payee keys: SHA-256's first 16 hex digits (every-FEC-dollar spec
 * §5.4). PATAPSCO INN is only ever a card charge, never a payee row, so it has no page.
 */
export const PAYEE_IDS = {
  actblue: "64cd888f13722403",
  americanExpress: "f218949ae6b171c7",
  blueHarbor: "6f774ca924cb0a0b",
  capitolCompliance: "0306cea0052a3e1a",
  firstMariner: "944656893c7b84e9",
  skylineAir: "e8b3fcab41b3f954",
} as const;

/**
 * `/v1/payees/6f774ca924cb0a0b`: BLUE HARBOR STRATEGIES, as expected.yaml's `payees` has it, paid
 * by both Maryland Senate campaigns in 2024. Its display name is the LLC spelling, which has more
 * of its dollars than the L.L.C. one.
 */
export const PAYEE_BLUE_HARBOR: Payee = {
  payee_id: PAYEE_IDS.blueHarbor,
  payee_key: "BLUE HARBOR STRATEGIES",
  display_name: "BLUE HARBOR STRATEGIES LLC",
  city: "BALTIMORE",
  state: "MD",
  total_all_cycles: 10500,
  first_cycle: 2024,
  last_cycle: 2024,
  cycles: [{ cycle: 2024, total: 10500, committee_count: 2 }],
  cycle: 2024,
  top_payers: [
    {
      rank: 1,
      committee_id: "C00800103",
      committee_name: "OKAFOR FOR MARYLAND",
      candidate_id: "S4MD00103",
      candidate_name: "OKAFOR, DIANA",
      amount: 7500,
    },
    {
      rank: 2,
      committee_id: "C00800104",
      committee_name: "WHITLOCK FOR SENATE",
      candidate_id: "S4MD00104",
      candidate_name: "WHITLOCK, GORDON",
      amount: 3000,
    },
  ],
};

/**
 * OKAFOR FOR MARYLAND's 2024 spending, as expected.yaml's `operating_expenditures` has it: its
 * counted rows, two card bills counted once, as the bills, and an in-kind outlay in no payee's.
 */
const OKAFOR_SPENDING: Pick<
  CommitteeCycle,
  "total_operating_expenditures" | "spending_by_category" | "top_payees"
> = {
  total_operating_expenditures: 11223.45,
  spending_by_category: [
    { category: "consulting", amount: 7500 },
    { category: "credit_card", amount: 2500 },
    { category: "legal_compliance", amount: 750 },
    { category: "other", amount: 350 },
    { category: "transfers_fees", amount: 123.45 },
  ],
  top_payees: payees([
    ["BLUE HARBOR STRATEGIES", "BLUE HARBOR STRATEGIES LLC", 7500, PAYEE_IDS.blueHarbor],
    ["AMERICAN EXPRESS", "AMERICAN EXPRESS", 1250, PAYEE_IDS.americanExpress],
    ["FIRST MARINER CARD SERVICES", "FIRST MARINER CARD SERVICES", 1250, PAYEE_IDS.firstMariner],
    ["CAPITOL COMPLIANCE GROUP", "CAPITOL COMPLIANCE GROUP", 750, PAYEE_IDS.capitolCompliance],
    ["ACTBLUE", "ACTBLUE", 123.45, PAYEE_IDS.actblue],
  ]),
};

const committeeCycle = (cycle: Partial<CommitteeCycle>): CommitteeCycle => ({
  cycle: 2024,
  total_individual: 0,
  self_funding: 0,
  total_from_committees: 0,
  total_from_organizations: 0,
  total_to_candidates: 0,
  total_returned_by_candidates: 0,
  total_non_contribution_account: 0,
  total_refunds: 0,
  ie_total: 0,
  communication_cost_total: 0,
  party_coordinated_total: 0,
  electioneering_total: null,
  outside_spending_total: cycle.ie_total ?? 0,
  reported: null,
  itemized_total: 0,
  coverage: null,
  total_operating_expenditures: null,
  spending_by_category: [],
  top_payees: [],
  top_recipients: [],
  top_donors: [],
  top_organizations: [],
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
  // Its reported itemized figure holds the earmarks fundlens counts at their recipients, so no
  // coverage (every-FEC-dollar spec §4.4).
  cycles: [
    committeeCycle({
      reported: reported("committee_summary", [
        780, 700, 0, 80, 0, 0, 780, 0, 780, 55, 0, 0, null, null, 0, null, 0, 0, 0, 0, 0, 645, null,
      ]),
      itemized_total: 5,
    }),
  ],
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
      reported: reported("committee_summary", [
        117000, 87700, 25000, 54300, 3000, 0, 38550, 8450, 47000, 0, 0, 45500, 5000, 0, 0, 0, 0,
        19500, 0, null, null, 87700, null,
      ]),
      itemized_total: 38550,
      coverage: 1,
      top_donors: OKAFOR_TOP_DONORS,
      ...OKAFOR_SPENDING,
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
      reported: reported("committee_summary", [
        6000, 47000, 60000, 19000, 0, 0, 4550, 1450, 6000, 0, 0, 0, null, null, 0, null, 0, 0, 0,
        24000, 0, 0, null,
      ]),
      itemized_total: 4550,
      coverage: 1,
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

const organizations = (rows: [string, string, number][]): TopOrganization[] =>
  rows.map(([organization_key, name, amount], index) => ({
    rank: index + 1,
    organization_key,
    name,
    amount,
  }));

/**
 * The super PAC: one organization's gifts less a refund, under its most-money spelling, and its
 * individuals' net of theirs.
 */
export const COMMITTEE_MARYLAND_FORWARD: Committee = {
  committee_id: "C00800201",
  name: "MARYLAND FORWARD PAC",
  type: "O",
  designation: "U",
  party: null,
  connected_org: null,
  is_conduit: false,
  cycles: [
    committeeCycle({
      total_individual: 395875,
      total_from_committees: 65000,
      total_from_organizations: 72500,
      total_refunds: -3200,
      ie_total: 670000,
      reported: reported("committee_summary", [
        760000, 722000, 150000, 188000, 0, 0, 544925, 35075, 580000, 1600, 0, 155000, null, null,
        25000, null, 0, 0, 0, 670000, 0, 50400, null,
      ]),
      itemized_total: 544925,
      coverage: 1,
      top_organizations: organizations([["CHESAPEAKE STEEL", "CHESAPEAKE STEEL, INC.", 72500]]),
    }),
  ],
};

/** A candidate committee two companies gave to, most first. */
export const COMMITTEE_PELL: Committee = {
  committee_id: "C00800105",
  name: "PELL FOR LIBERTY",
  type: "S",
  designation: "P",
  party: "LIB",
  connected_org: null,
  is_conduit: false,
  cycles: [
    committeeCycle({
      total_individual: 3250,
      total_from_organizations: 8000,
      reported: reported("committee_summary", [
        12200, 10900, 0, 1300, 0, 0, 11250, 950, 12200, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, null, null,
        10900, null,
      ]),
      itemized_total: 11250,
      coverage: 1,
      top_organizations: organizations([
        ["ACME CONCRETE", "ACME CONCRETE LLC", 5000],
        ["ACME WIDGETS", "ACME WIDGETS INC", 3000],
      ]),
    }),
  ],
};

/**
 * A hybrid PAC: a few thousand in its contribution account, millions in its non-contribution
 * account, one of whose givers is its top organization.
 */
export const COMMITTEE_TIDEWATER_FUND: Committee = {
  committee_id: "C00800204",
  name: "TIDEWATER FUND",
  type: "V",
  designation: "U",
  party: null,
  connected_org: null,
  is_conduit: false,
  cycles: [
    committeeCycle({
      total_individual: 6250,
      total_from_organizations: 0,
      total_non_contribution_account: 4815000,
      reported: reported("committee_summary", [
        255000, 153000, 0, 102000, 0, 0, 4000, 251000, 255000, 5250, 0, 0, null, null, 0, null, 0,
        0, 0, 0, 0, 147750, null,
      ]),
      itemized_total: 4000,
      coverage: 1,
      top_organizations: organizations([["HARBOR HOLDINGS", "HARBOR HOLDINGS LLC", 1500000]]),
    }),
  ],
};

// Before 2008 (tests/fixtures/fec/1998, expected.yaml's 1998 `reported_totals`): FEC's files give
// no reporting period start, no itemized and unitemized split, and none of the measures only
// committee_summary has, so those are null and there is no coverage (every-FEC-dollar spec §4.7).
const PERIOD_1998: [null, string] = [null, "1998-12-31"];

/** `/v1/committees/C00298003`: the builders' PAC in 1998, its reported totals webk's row. */
export const COMMITTEE_BUILDERS_PAC_1998: Committee = {
  committee_id: "C00298003",
  name: "MARYLAND BUILDERS PAC",
  type: "Q",
  designation: "U",
  party: null,
  connected_org: "MARYLAND BUILDERS ASSOCIATION",
  is_conduit: false,
  cycles: [
    committeeCycle({
      cycle: 1998,
      total_to_candidates: 2000,
      reported: reported(
        "webk",
        [
          6000, 2500, 4000, 7500, 0, null, null, null, 6000, 0, null, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
          null, null,
        ],
        PERIOD_1998,
      ),
    }),
  ],
};

/** `/v1/candidates/H8MD05201`: CALDER in 1998, her reported totals weball's row as filed. */
export const CANDIDATE_CALDER_1998: Candidate = {
  candidate_id: "H8MD05201",
  name: "CALDER, RUTH",
  party: "DEM",
  office: "H",
  state: "MD",
  district: "05",
  cycles: [
    {
      cycle: 1998,
      race_id: "1998-H-MD-05",
      race_slug: "1998/house/MD-05",
      total_individual: 1000,
      total_committee: 2000,
      total_jfc_transfers: 0,
      self_funding: 0,
      ie_support: 0,
      ie_oppose: 0,
      outside_spending: outsideSpending(0, 0),
      contributor_count: 1,
      reported: reported(
        "weball",
        [
          9500, 8200, 0, 1300, 0, null, null, null, 7500, 0, 0, 2000, 0, 0, 0, 0, 0, 0, 0, null,
          null, null, null,
        ],
        PERIOD_1998,
      ),
      reported_includes_converted_committee: false,
      itemized_total: 1000,
      coverage: null,
      top_donors: [],
      // The five itemized buckets only: no file before 2008 has an unitemized figure.
      gift_sizes: [
        { bucket: "200_or_less", amount: 0, donors: 0 },
        { bucket: "under_500", amount: 0, donors: 0 },
        { bucket: "under_1000", amount: 0, donors: 0 },
        { bucket: "under_2000", amount: 1000, donors: 1 },
        { bucket: "2000_or_more", amount: 0, donors: 0 },
      ],
    },
  ],
};

export const COMMITTEES: Committee[] = [
  COMMITTEE_ACTBLUE,
  COMMITTEE_OKAFOR,
  COMMITTEE_BRICKLAYERS,
  COMMITTEE_MARYLAND_FORWARD,
  COMMITTEE_PELL,
  COMMITTEE_TIDEWATER_FUND,
];

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
  resolver_version: "0123456789abcdef0123456789abcdef01234567",
  model_version: "20241102T040000Z",
  overrides_count: 2,
  adjudications_applied: 31,
  precision: 0.6288,
  recall: 0.9121,
  precision_top: 0.9516,
  recall_top: 0.8023,
  matched_rows: 41_230_118,
  dime_version: "4.0",
  cycles: { "2024": { build_id: "20241103T060000Z", source_dates: { indiv: "2024-11-02" } } },
};

export const problem = (status: number, title: string, detail: string): Problem => ({
  type: "about:blank",
  title,
  status,
  detail,
});

const expenditure = (
  source_record_id: string,
  date: string,
  amount: number,
  candidate_id: string,
  candidate_name: string,
  race_id: string,
  support_oppose: "S" | "O",
  transaction_type: string,
  payee_name: string,
): IndependentExpenditure => ({
  cycle: 2024,
  source_record_id,
  date,
  amount,
  committee_id: "C00800201",
  candidate_id,
  candidate_name,
  race_id,
  support_oppose,
  transaction_type,
  source_file: "pas2",
  payee_name,
  purpose: null,
});

/**
 * MARYLAND FORWARD PAC's six independent expenditures in the fixture (pas2.csv, by SUB_ID), newest
 * first: they add up to its ie_total.
 */
export const EXPENDITURES: IndependentExpenditure[] = [
  expenditure("4240200000000000006", "2024-10-28", 400000, "P40000101", "HARGROVE, ELLEN", "2024-P-US-00", "S", "24E", "BLUE CRAB MEDIA LLC"),
  expenditure("4240200000000000002", "2024-10-22", 30000, "S4MD00103", "OKAFOR, DIANA", "2024-S-MD-00", "S", "24E", "BLUE CRAB MEDIA LLC"),
  expenditure("4240200000000000005", "2024-10-14", 15000, "H4MD05107", "DRISCOLL, PETER", "2024-H-MD-05", "O", "24A", "CHESAPEAKE MAIL CO"),
  expenditure("4240200000000000004", "2024-10-12", 25000, "H4MD05106", "CALLOWAY, RUTH", "2024-H-MD-05", "S", "24E", "CHESAPEAKE MAIL CO"),
  expenditure("4240200000000000003", "2024-10-05", 80000, "S4MD00104", "WHITLOCK, GORDON", "2024-S-MD-00", "O", "24A", "BLUE CRAB MEDIA LLC"),
  expenditure("4240200000000000001", "2024-09-20", 120000, "S4MD00103", "OKAFOR, DIANA", "2024-S-MD-00", "S", "24E", "BLUE CRAB MEDIA LLC"),
];

const DATA = "https://data.fundlens.org/v1/";

const snapshot = (date: string, build_id: string): DatasetSnapshot => ({
  snapshot_date: date,
  url: `${DATA}${date}/`,
  build_id,
  cycles: [2024, 2022],
  tables: [
    {
      name: "contribution",
      rows: 1_200,
      files: 3,
      bytes: 30_500,
      parts: [
        {
          cycle: 2022,
          path: "contribution/cycle=2022/bucket-00-part-0000.parquet",
          files: 1,
          bytes: 500,
        },
        { cycle: 2024, path: "contribution/cycle=2024/", files: 2, bytes: 30_000 },
      ],
    },
    {
      name: "race",
      rows: 12,
      files: 2,
      bytes: 3_000,
      parts: [
        { cycle: 2022, path: "race/cycle=2022/part-0000.parquet", files: 1, bytes: 1_000 },
        { cycle: 2024, path: "race/cycle=2024/part-0000.parquet", files: 1, bytes: 2_000 },
      ],
    },
    {
      name: "donor",
      rows: 40,
      files: 1,
      bytes: 9_876,
      parts: [{ cycle: null, path: "donor.parquet", files: 1, bytes: 9_876 }],
    },
  ],
  precision: 0.97,
  recall: 0.95,
  license: "CC BY 4.0",
  attribution: "fundlens (fundlens.org), CC BY 4.0",
});

/** Two snapshots, the newest the one `latest/` is a copy of. */
export const DATASET: Dataset = {
  base_url: DATA,
  latest: "2026-11-22",
  snapshots: [
    snapshot("2026-11-22", "20261122T030000Z"),
    { ...snapshot("2026-11-15", "20261115T030000Z"), precision: null, recall: null },
  ],
};

/** An operating expenditure by OKAFOR FOR MARYLAND in 2024, an ordinary counted payment. */
export const operatingExpenditure = (
  row: Pick<OperatingExpenditure, "source_record_id" | "date" | "amount" | "payee_name"> &
    Partial<OperatingExpenditure>,
): OperatingExpenditure => ({
  cycle: 2024,
  committee_id: "C00800103",
  candidate_id: "S4MD00103",
  payee_key: row.payee_name,
  payee_id: null,
  payee_city: null,
  payee_state: null,
  payee_zip: null,
  purpose: null,
  fec_category: null,
  spending_category: "other",
  category_source: "purpose_rule",
  memo_code: null,
  memo_text: null,
  image_num: null,
  is_in_kind: false,
  counted: true,
  sub_items: [],
  ...row,
});

/** A card charge itemizing a bill: a memo row, never counted. */
const charge = (row: Parameters<typeof operatingExpenditure>[0]) =>
  operatingExpenditure({ memo_code: "X", counted: false, spending_category: "travel", ...row });

/**
 * OKAFOR FOR MARYLAND's 2024 operating expenditures (oppexp.csv), newest first, as
 * `/v1/committees/C00800103/expenditures` serves them: three card bills with their charges under
 * them, VELASQUEZ's in-kind catering, and four ordinary payments.
 */
export const OPERATING_EXPENDITURES: OperatingExpenditure[] = [
  operatingExpenditure({
    source_record_id: "4240400000000000035",
    date: "2024-06-30",
    amount: 123.45,
    payee_name: "ACTBLUE",
    payee_id: PAYEE_IDS.actblue,
    purpose: "PROCESSING FEES",
    spending_category: "transfers_fees",
  }),
  operatingExpenditure({
    source_record_id: "4240400000000000020",
    date: "2024-06-27",
    amount: 750,
    payee_name: "FIRST MARINER CARD SERVICES",
    payee_id: PAYEE_IDS.firstMariner,
    purpose: "CREDIT CARD PAYMENT",
    spending_category: "credit_card",
    sub_items: [
      charge({
        source_record_id: "4240400000000000021",
        date: "2024-06-03",
        amount: 750,
        payee_name: "SKYLINE AIR",
        payee_id: PAYEE_IDS.skylineAir,
        purpose: "AIRFARE",
      }),
    ],
  }),
  operatingExpenditure({
    source_record_id: "4240400000000000016",
    date: "2024-05-11",
    amount: 350,
    payee_name: "VELASQUEZ, TERESA",
    payee_key: "VELASQUEZ TERESA",
    purpose: "IN-KIND CONTRIBUTION: CATERING",
    category_source: "unclassified",
    is_in_kind: true,
  }),
  operatingExpenditure({
    source_record_id: "4240400000000000032",
    date: "2024-04-30",
    amount: 7500,
    payee_name: "BLUE HARBOR STRATEGIES LLC",
    payee_key: "BLUE HARBOR STRATEGIES",
    payee_id: PAYEE_IDS.blueHarbor,
    purpose: "STRATEGY CONSULTING",
    fec_category: "001",
    spending_category: "consulting",
  }),
  operatingExpenditure({
    source_record_id: "4240400000000000052",
    date: "2024-03-29",
    amount: 750,
    payee_name: "CAPITOL COMPLIANCE GROUP",
    payee_id: PAYEE_IDS.capitolCompliance,
    purpose: "COMPLIANCE CONSULTING",
    spending_category: "legal_compliance",
  }),
  operatingExpenditure({
    source_record_id: "4240400000000000018",
    date: "2024-03-28",
    amount: 500,
    payee_name: "FIRST MARINER CARD SERVICES",
    payee_id: PAYEE_IDS.firstMariner,
    purpose: "CREDIT CARD PAYMENT",
    spending_category: "credit_card",
    sub_items: [
      charge({
        source_record_id: "4240400000000000019",
        date: "2024-03-02",
        amount: 500,
        payee_name: "PATAPSCO INN",
        purpose: "LODGING",
      }),
    ],
  }),
  operatingExpenditure({
    source_record_id: "4240400000000000003",
    date: "2024-03-05",
    amount: 1250,
    payee_name: "AMERICAN EXPRESS",
    payee_id: PAYEE_IDS.americanExpress,
    purpose: "CREDIT CARD PAYMENT",
    spending_category: "credit_card",
    sub_items: [
      charge({
        source_record_id: "4240400000000000004",
        date: "2024-02-12",
        amount: 412.5,
        payee_name: "SKYLINE AIR",
        payee_id: PAYEE_IDS.skylineAir,
        purpose: "AIRFARE",
        memo_text: "CHARGE ON CREDIT CARD",
      }),
      charge({
        source_record_id: "4240400000000000005",
        date: "2024-02-13",
        amount: 837.5,
        payee_name: "PATAPSCO INN",
        purpose: "LODGING",
        memo_text: "CHARGE ON CREDIT CARD",
      }),
    ],
  }),
];
