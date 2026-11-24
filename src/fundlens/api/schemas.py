"""Pydantic response models: the OpenAPI contract the frontend's client is generated from.

Money is a JSON number of dollars (gold's `numeric(16, 2)`): a `Decimal` would serialize as a
string, and the SPA only formats and charts these figures. Every field is typed down to its
leaves, so the generated client has no `unknown` in it.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from fundlens.transform import spending

PROBLEM_JSON = "application/problem+json"

type Office = Literal["H", "S", "P"]
type SearchKind = Literal["donor", "candidate", "committee", "race", "payee"]
# Where a row's reported figures came from (every-FEC-dollar spec §4.1, §4.2): a committee's from
# `committee_summary` (2008 on, `+webk` where a Form 5 or 7 filer's blanks were filled), `webk`
# (1996-2006); a candidate's summed from their committees' (`committee_summary`) or `weball`.
type ReportedSourceFile = Literal["committee_summary", "committee_summary+webk", "webk", "weball"]
# One of the fifteen spending categories, and what decided it (every-FEC-dollar spec §5.3).
type SpendingCategory = spending.Category
type SpendingCategorySource = spending.CategorySource
# A candidate's gift-size buckets (spec §4.6), in this order: FEC's unitemized lump, then each
# donor's net gifts to the candidate in the cycle.
type GiftSizeBucket = Literal[
    "unitemized", "200_or_less", "under_500", "under_1000", "under_2000", "2000_or_more"
]
# The four kinds of outside spending, as gold names them (every-FEC-dollar spec §6.1).
type OutsideSpendingKind = Literal[
    "independent_expenditure",
    "communication_cost",
    "party_coordinated",
    "electioneering_communication",
]


class Problem(BaseModel):
    """An RFC 9457 problem details document (`application/problem+json`)."""

    type: str
    title: str
    status: int
    detail: str


class ValidationErrorDetail(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationProblem(Problem):
    """A 422: the problem details document, with what was wrong with each parameter."""

    errors: list[ValidationErrorDetail]


class Health(BaseModel):
    postgres: str
    silver: str


class MetaCycle(BaseModel):
    """One cycle's live build and the date of each bulk file it was built from."""

    build_id: str
    # FEC bulk file name (`cm`, `indiv`, …) → its download date.
    source_dates: dict[str, date]


class Meta(BaseModel):
    """The live gold build (`gold.meta`, spec §7.1): how its donors were resolved and how well
    that scored against DIME, which the methodology page prints (NEU-2056)."""

    build_id: str
    published_at: datetime
    # The release (commit) that resolved, and the Splink model's version: None before a
    # resolved build, the release also where none was known.
    resolver_version: str | None
    model_version: str | None
    # Override entries and adjudication verdicts the resolution applied: None when the model's
    # run kept no record of them.
    overrides_count: int | None
    adjudications_applied: int | None
    # Pairwise precision and recall against DIME, over every matched contributor and over the
    # top 10,000 by matched dollars; the contributions they rest on; the DIME release. None until
    # the cycle is validated under the live model (NEU-2054).
    precision: float | None
    recall: float | None
    precision_top: float | None
    recall_top: float | None
    matched_rows: int | None
    dime_version: str | None
    # Keyed by cycle, as a string ("2024"): JSON object keys are strings.
    cycles: dict[str, MetaCycle]


class DatasetPart(BaseModel):
    """One table's files in one cycle of a dataset snapshot, or a table's one file when it has
    no cycle (`donor`, `crosswalk`)."""

    # None for a table with no cycle.
    cycle: int | None
    # Relative to the snapshot's `url`: the file itself when the part is one file, which a
    # browser can download; else the directory holding its files (`contribution/cycle=2024/`),
    # which HTTPS cannot list: the snapshot's `manifest.json` names each file.
    path: str
    files: int
    bytes: int


class DatasetTable(BaseModel):
    """One table of a dataset snapshot, from its `manifest.json` (spec §9)."""

    name: str
    rows: int
    files: int
    bytes: int
    # In the manifest's order: by cycle, oldest first.
    parts: list[DatasetPart]


class DatasetSnapshot(BaseModel):
    """One finished dataset snapshot, `v1/<snapshot_date>/` in the public bucket."""

    snapshot_date: date
    # Where its files are served: `https://data.fundlens.org/v1/<snapshot_date>/`.
    url: str
    # The build `gold` was published from when it was taken.
    build_id: str
    # Newest first.
    cycles: list[int]
    # In the manifest's order.
    tables: list[DatasetTable]
    # Resolution quality against DIME (spec §6.9): None when the live model was unscored.
    precision: float | None
    recall: float | None
    license: str
    attribution: str


class Dataset(BaseModel):
    """The public dataset's snapshots (`GET /v1/dataset`, spec §9)."""

    # Where the dataset is served: its README, LICENSE, CHANGELOG and `schema/` are here too.
    base_url: str
    # The snapshot `latest/` is a copy of: None before the first, or while its first copy is
    # unfinished.
    latest: date | None
    # Every finished snapshot, newest first.
    snapshots: list[DatasetSnapshot]


class Cycle(BaseModel):
    """`gold.cycle`: one cycle's totals."""

    cycle: int
    race_count: int
    contribution_count: int
    total_amount: float


class RaceSummary(BaseModel):
    """`gold.race`: one race and its totals, summed over its candidates."""

    race_id: str
    cycle: int
    office: Office
    state: str
    district: str
    is_special: bool
    # The race's URL under `/v1/races/` and the SPA's: `2024/senate/MD`, `2024/house/MD-05`.
    slug: str
    candidate_count: int
    total_individual: float
    total_committee: float
    # A joint fundraising committee's transfers to the candidate's committees: committee money,
    # in neither total_individual nor total_committee (NEU-2124).
    total_jfc_transfers: float
    ie_support: float
    ie_oppose: float
    # FEC's reported cash on hand at the end of the cycle, its candidates' added up; None when none
    # has a reported figure (every-FEC-dollar spec §4.4).
    reported_cash_on_hand: float | None
    # Its candidates' operating expenditures added up (every-FEC-dollar spec §5.5): None, never 0,
    # when none has a counted one in the cycle, as before 2004.
    total_operating_expenditures: float | None


class ReportedTotals(BaseModel):
    """A committee's or candidate's reported totals for a cycle, as filed (CONTEXT.md;
    every-FEC-dollar spec §4.1 to §4.4): never summed with itemized money, shown beside the
    itemized total.

    A measure the cycle's file lacks is None, never 0, while the rest stand: before 2008 there is
    no `period_start`, `debts_owed_to`, itemized and unitemized split, `operating_expenditures` or
    `federal_funds` (spec §4.7). A candidate's from 2008 are their credited committees' added up.
    """

    source_file: ReportedSourceFile
    # The reporting period the figures cover (CONTEXT.md), as filed, so possibly reversed.
    period_start: date | None
    period_end: date | None
    receipts: float | None
    disbursements: float | None
    cash_on_hand_start: float | None
    cash_on_hand_end: float | None
    debts_owed_by: float | None
    debts_owed_to: float | None
    individual_itemized: float | None
    # A committee-level lump of gifts under $200, never attributed to a donor.
    individual_unitemized: float | None
    individual_total: float | None
    individual_refunds: float | None
    party_contributions: float | None
    other_committee_contributions: float | None
    candidate_contributions: float | None
    candidate_loans: float | None
    other_loans: float | None
    candidate_loan_repayments: float | None
    other_loan_repayments: float | None
    transfers_in: float | None
    transfers_out: float | None
    independent_expenditures: float | None
    party_coordinated: float | None
    operating_expenditures: float | None
    federal_funds: float | None


class SupportOppose(BaseModel):
    """One kind of outside spending naming a candidate, for them and against them, net as filed."""

    support: float
    oppose: float


class OutsideSpending(BaseModel):
    """Spending on a candidate or race by anyone but its candidates' own committees, by kind
    (every-FEC-dollar spec §6.5): never a contribution and in no receipt total. A row filed with no
    side is in none of these.

    `independent_expenditure` is v1's `ie_support` and `ie_oppose`, the 24/48-hour file's rows
    included. Party coordinated expenditures are always in support. An electioneering communication
    says neither: its figure is None, never 0, where there is no row, as before 2010 or on a build
    loaded before the table existed."""

    independent_expenditure: SupportOppose
    communication_cost: SupportOppose
    party_coordinated: float
    electioneering_communication: float | None


class RaceCandidateReported(BaseModel):
    """A race candidate's headline reported figures, their `candidate_cycle` values (spec §4.4)."""

    source_file: ReportedSourceFile
    receipts: float | None
    disbursements: float | None
    cash_on_hand_end: float | None
    debts_owed_by: float | None


class GiftSize(BaseModel):
    """`gold.candidate_gift_size`: one bucket of a candidate's money in a cycle (spec §4.6)."""

    bucket: GiftSizeBucket
    amount: float
    # The bucket's donors; None for `unitemized`, FEC's lump, which names no donor.
    donors: int | None


class RaceCandidate(BaseModel):
    """`gold.race_candidate`: a candidate in the race and their money this cycle."""

    candidate_id: str
    name: str | None
    party: str | None
    incumbent_challenger_open: str | None
    principal_committee_id: str | None
    total_individual: float
    total_committee: float
    # A joint fundraising committee's transfers to the candidate's committees: committee money,
    # in neither total_individual nor total_committee (NEU-2124).
    total_jfc_transfers: float
    self_funding: float
    ie_support: float
    ie_oppose: float
    # Every kind of outside spending naming them, for and against: no one total, since the two
    # point opposite ways (every-FEC-dollar spec §6.5).
    outside_spending: OutsideSpending
    # The operating expenditures of the committees credited to them (every-FEC-dollar spec §5.5),
    # None, never 0, with no counted one in the cycle.
    total_operating_expenditures: float | None
    # The candidate's reported totals, None where FEC's files have no row for any committee
    # credited to them; their itemized total, None when no committee is credited to them; and
    # coverage, the one over the other (spec §4.4), None where that cannot be taken.
    reported: RaceCandidateReported | None
    itemized_total: float | None
    coverage: float | None


class RaceTopCommittee(BaseModel):
    """`gold.race_top_committee`: a committee among the 100 that spent most on the race."""

    rank: int
    committee_id: str
    name: str | None
    amount: float
    kind: Literal["contribution", "ie"]


class RaceTopSpender(BaseModel):
    """`gold.race_top_spender`: one of the race's 100 biggest lines of outside spending, a line
    being one spender's spending of one kind on one of its candidates, on one side (every-FEC-dollar
    spec §6.5)."""

    rank: int
    # The spender, a committee or not: every spender has a page.
    committee_id: str
    name: str | None
    candidate_id: str
    # False for a non-committee spender: a person or group filing Form 5, 7 or 9 (`committee.type`
    # I, C or E), not a political committee.
    is_committee: bool
    kind: OutsideSpendingKind
    # Always S for `party_coordinated`; None for `electioneering_communication`, whose filing says
    # neither.
    support_oppose: Literal["S", "O"] | None
    amount: float


class RaceTopDonorCandidate(BaseModel):
    """What a race's top donor gave one of its candidates, net of refunds."""

    candidate_id: str
    amount: float


class RaceTopDonor(BaseModel):
    """`gold.race_top_donor`: a donor among the 100 who gave most to the race's candidates, their
    own money left out (spec §7.1)."""

    rank: int
    donor_id: int
    display_name: str | None
    amount: float
    # Most first; always adds up to `amount`.
    candidates: list[RaceTopDonorCandidate]


class Race(RaceSummary):
    """A race page: the race, its candidates (most money first), its outside spending, its top
    committees, top spenders and top donors."""

    # Its candidates' outside spending added up, by kind; an electioneering figure None where none
    # has a row.
    outside_spending: OutsideSpending
    # How much was spent on the race by anyone but its candidates' committees: every kind, both
    # sides, a None electioneering figure as 0 (every-FEC-dollar spec §6.5).
    outside_spending_total: float
    candidates: list[RaceCandidate]
    top_committees: list[RaceTopCommittee]
    # Most first; every kind, a non-committee spender's too.
    top_spenders: list[RaceTopSpender]
    # Empty on a build loaded before donors were resolved.
    top_donors: list[RaceTopDonor]


class TopDonor(BaseModel):
    """`gold.candidate_top_donor` or `gold.committee_top_donor`: a donor among the 100 who gave
    most in a cycle, the candidate's own money left out (spec §7.1)."""

    rank: int
    donor_id: int
    display_name: str | None
    amount: float


class CandidateCycle(BaseModel):
    """`gold.candidate_cycle`: a candidate's money in one cycle."""

    cycle: int
    # None for a filing that matched no seat (spec §5.2).
    race_id: str | None
    race_slug: str | None
    total_individual: float
    total_committee: float
    # A joint fundraising committee's transfers to the candidate's committees: committee money,
    # in neither total_individual nor total_committee (NEU-2124).
    total_jfc_transfers: float
    self_funding: float
    ie_support: float
    ie_oppose: float
    # Every kind of outside spending naming them, for and against (every-FEC-dollar spec §6.5).
    outside_spending: OutsideSpending
    # None until M3 resolves donors.
    contributor_count: int | None
    # Reported totals (spec §4.3): from 2008 the credited committees' added up, before it the
    # candidate's `weball` row; None where there is none.
    reported: ReportedTotals | None
    # True when a credited committee is a campaign turned PAC, counted whole, so the reported
    # figures include what it raised after converting, which FEC credits to no one (spec §4.3).
    reported_includes_converted_committee: bool
    # The credited committees' itemized totals added up, None when no committee is credited to
    # the candidate; over their reported itemized figure, `coverage`: a ratio (0.9412), which can
    # exceed 1, None before 2008 or where the reported figure is 0 or missing (spec §4.4).
    itemized_total: float | None
    coverage: float | None
    # Empty on a build loaded before donors were resolved.
    top_donors: list[TopDonor]
    # In bucket order (`GiftSizeBucket`): the five itemized buckets add up to `total_individual`;
    # `unitemized` only from 2008, and alone on a build loaded before donors were resolved.
    gift_sizes: list[GiftSize]


class Candidate(BaseModel):
    """A candidate page: `gold.candidate` and a row per cycle, newest first."""

    candidate_id: str
    name: str | None
    party: str | None
    office: Office | None
    state: str | None
    district: str | None
    cycles: list[CandidateCycle]


class CommitteeTopRecipient(BaseModel):
    """`gold.committee_top_recipient`: one of the 100 a committee gave most to in a cycle."""

    rank: int
    recipient_kind: Literal["candidate", "committee"]
    recipient_id: str
    name: str | None
    amount: float


class TopOrganization(BaseModel):
    """`gold.committee_top_organization`: an organization among the 100 that gave a committee
    most in a cycle, its gifts grouped by organization key, never resolved (ADR-0011)."""

    rank: int
    # The key's reported spelling with the most money; a receipt filed with no name has no key
    # and is on no list.
    name: str
    organization_key: str
    amount: float


class SpendingByCategory(BaseModel):
    """`gold.committee_spending_category`: a committee's counted operating expenditures in one
    spending category in a cycle, net as filed, so possibly 0 or less (every-FEC-dollar spec
    §5.3, §5.5)."""

    category: SpendingCategory
    amount: float


class TopPayee(BaseModel):
    """`gold.committee_top_payee`: a payee among the 100 a committee paid most in a cycle, its
    payments grouped by payee key, never resolved (ADR-0012; every-FEC-dollar spec §5.4)."""

    rank: int
    # The key's reported spelling with the most payee dollars in the cycle.
    name: str
    payee_key: str
    # The payee's page, `/v1/payees/{payee_id}`; None for a person or a name that names nobody,
    # which have none.
    payee_id: str | None
    amount: float


class CommitteeCycle(BaseModel):
    """`gold.committee_cycle`: a committee's money in one cycle, whom it gave most to, and who
    gave most to it."""

    cycle: int
    total_individual: float
    self_funding: float
    total_from_committees: float
    # Gifts from givers neither people nor committees, net of refunds: counted on the receiving
    # committee only, in no race, candidate or cycle-wide figure (ADR-0011). A hybrid PAC's
    # non-contribution account and gifts FEC files off line 11(a)(i), a party account's above all,
    # are left out (NEU-2192, NEU-2205).
    total_from_organizations: float
    total_to_candidates: float
    # Its 24Ks to each candidate they net below 0 for, summed, so 0 or less: voids and refunds of
    # earlier cycles' gifts, in no total_to_candidates or top recipient (NEU-2204).
    total_returned_by_candidates: float
    # A hybrid PAC's non-contribution account: its individuals' and organizations' gifts there, net
    # of refunds, in neither total_individual nor total_from_organizations (NEU-2192). 0 at every
    # committee with no such account.
    total_non_contribution_account: float
    # The refunds already netted into total_individual and total_from_organizations, so 0 or
    # less (NEU-2265). FEC's itemized figure is gross of them: total_individual +
    # total_from_organizations - total_refunds.
    total_refunds: float
    # The committee's own outside spending (every-FEC-dollar spec §6.5), every row of each kind,
    # both sides, those naming no candidate of the cycle and those with no side included: its
    # independent expenditures, communication costs (a corporation's or union's, Form 7) and party
    # coordinated expenditures, 0 where it has none; its electioneering communications (Form 9),
    # None where there is no row, as before 2010; and the four added up, a None as 0. Spending,
    # never in a receipt total.
    ie_total: float
    communication_cost_total: float
    party_coordinated_total: float
    electioneering_total: float | None
    outside_spending_total: float
    # The committee's reported totals as filed (spec §4.1), None where FEC's files have no row
    # for it: every committee before 1996, and House and Senate campaigns before 2008.
    reported: ReportedTotals | None
    # The itemized total, toward the line FEC's itemized individual figure reports:
    # total_individual + total_from_organizations - total_refunds. `coverage` is it over that
    # figure: a ratio, which can exceed 1, None before 2008, at a conduit, or where the reported
    # figure is 0 or missing (spec §4.4).
    itemized_total: float
    coverage: float | None
    # Its counted operating expenditures, net as filed (every-FEC-dollar spec §5.2, §5.5): None,
    # never 0, with no counted one in the cycle, as before 2004 or on a build that lacks them.
    total_operating_expenditures: float | None
    # By category, most first; adding up to total_operating_expenditures, and empty where it is
    # None.
    spending_by_category: list[SpendingByCategory]
    top_payees: list[TopPayee]
    top_recipients: list[CommitteeTopRecipient]
    # Empty on a build loaded before donors were resolved.
    top_donors: list[TopDonor]
    top_organizations: list[TopOrganization]


class Committee(BaseModel):
    """A committee page: `gold.committee` and a row per cycle, newest first."""

    committee_id: str
    name: str | None
    type: str | None
    designation: str | None
    party: str | None
    connected_org: str | None
    is_conduit: bool
    cycles: list[CommitteeCycle]


class Contribution(BaseModel):
    """One counted contribution from silver `contribution` (spec §4), the contributor as
    reported."""

    cycle: int
    # FEC's SUB_ID, as a string: its 19 digits are past what a JSON number holds exactly.
    source_record_id: str
    # None for a filing whose date FEC could not parse.
    date: date | None
    amount: float
    recipient_committee_id: str
    # The candidate the recipient raises for as principal or authorized committee, if any.
    candidate_id: str | None
    # The resolved donor (spec §6), `/v1/donors/{donor_id}`; None on a build loaded before donors
    # were resolved.
    donor_id: int | None
    contributor_name: str | None
    contributor_city: str | None
    contributor_state: str | None
    contributor_zip: str | None
    contributor_employer: str | None
    contributor_occupation: str | None
    entity_type: str | None
    transaction_type: str | None
    report_type: str | None
    memo_text: str | None
    # The conduit (ActBlue, WinRed) an earmark came through.
    conduit_committee_id: str | None
    is_self_funding: bool
    # The filing image FEC shows this contribution on.
    image_num: str | None


class IndependentExpenditure(BaseModel):
    """One independent expenditure from silver `independent_expenditure` (spec §4): a committee's
    spending for or against a candidate, never a gift to one."""

    cycle: int
    # FEC's SUB_ID, as a string: its 19 digits are past what a JSON number holds exactly. A row
    # of the 24/48-hour file, a 24- or 48-hour report's estimate no periodic report holds yet, has
    # none: its key is `<file_num>:<tran_id>` (every-FEC-dollar spec §6.2, NEU-2165).
    source_record_id: str
    # None for a filing whose date FEC could not parse.
    date: date | None
    # As filed: a negative one is a correction, and nets out of the spender's ie_total.
    amount: float
    committee_id: str
    # The candidate it was spent for or against, None when FEC's CAND_ID names no candidate of
    # the cycle; their name from `gold.candidate`.
    candidate_id: str | None
    candidate_name: str | None
    # The candidate's race, None when their seat is not up this cycle.
    race_id: str | None
    # S for the candidate (FEC's 24E), O against (24A); None for a 24/48-hour row filed with
    # neither, which is in its spender's ie_total and no candidate's figure.
    support_oppose: Literal["S", "O"] | None
    # FEC's transaction type, 24E or 24A; None for a 24/48-hour row: that file has none.
    transaction_type: str | None
    # `pas2`, the periodic report's line, or `ie_24_48`, a 24- or 48-hour report's estimate no
    # periodic report holds yet, which leaves the list once one restates it (every-FEC-dollar spec
    # §6.2, §6.3).
    source_file: Literal["pas2", "ie_24_48"]
    # Whom the spender paid, as reported; None on a build transformed before it was kept.
    payee_name: str | None
    # What for, as reported: a 24/48-hour row's alone, since `pas2` has none.
    purpose: str | None


class IndependentExpenditurePage(BaseModel):
    """A page of independent expenditures, newest first; `next_cursor` fetches the next, None on
    the last."""

    expenditures: list[IndependentExpenditure]
    next_cursor: str | None


class OperatingExpenditure(BaseModel):
    """One operating expenditure from silver `operating_expenditure` (every-FEC-dollar spec §5.1): a
    payment a committee itemized, the payee as reported, with the sub-items that itemize it.

    Only `counted` rows add up to the committee's total_operating_expenditures: a sub-item (a card
    bill's charge) is listed under its parent and never counted, nor is a memo row nothing names.
    Spending, never a contribution."""

    cycle: int
    # FEC's SUB_ID, as a string: its 19 digits are past what a JSON number holds exactly.
    source_record_id: str
    # None for a filing whose date FEC could not parse.
    date: date | None
    # As filed: a negative one is a refund or an offset, and nets out.
    amount: float | None
    committee_id: str
    # The candidate the paying committee is credited to on the row's date, if any.
    candidate_id: str | None
    payee_name: str | None
    # The payee's normalized name (ADR-0012), None for a row with no name; and its page,
    # `/v1/payees/{payee_id}`, None where the key has none: a person's, or a name naming nobody.
    payee_key: str | None
    payee_id: str | None
    payee_city: str | None
    payee_state: str | None
    payee_zip: str | None
    purpose: str | None
    # None on a build transformed before payments were classified.
    spending_category: SpendingCategory | None
    category_source: SpendingCategorySource | None
    # FEC's own category code, as filed, three digits.
    fec_category: str | None
    memo_code: str | None
    memo_text: str | None
    counted: bool
    # An in-kind outlay: counted, but in no payee's figures, since its payee is the gift's giver.
    is_in_kind: bool
    # The filing image FEC shows this payment on.
    image_num: str | None
    # The rows that itemize this one, never counted, in the page's order; a sub-item can have its
    # own.
    sub_items: list["OperatingExpenditure"]


class OperatingExpenditurePage(BaseModel):
    """A page of a committee's operating expenditures, each with its sub-items; `next_cursor`
    fetches the next, None on the last."""

    expenditures: list[OperatingExpenditure]
    next_cursor: str | None


class DonorCycle(BaseModel):
    """`gold.donor_cycle`: a donor's counted money in one cycle."""

    cycle: int
    amount: float
    contribution_count: int


class DonorTopRecipient(BaseModel):
    """`gold.donor_top_recipient`: one of the 100 a donor gave most to, over every cycle: a
    candidate, for a gift to a committee raising for one, else the committee."""

    rank: int
    recipient_kind: Literal["candidate", "committee"]
    recipient_id: str
    name: str | None
    amount: float


class Donor(BaseModel):
    """A donor page: `gold.donor`, every name, employer and address variant resolved into one
    (spec §6), a row per cycle, newest first, and whom they gave most to."""

    donor_id: int
    # Each the variant with the most counted money (spec §6.7).
    display_name: str | None
    employer: str | None
    occupation: str | None
    city: str | None
    state: str | None
    zip5: str | None
    # Their own money as a candidate included; a donor known only from JFC attributions has $0.
    total_all_cycles: float
    first_cycle: int
    last_cycle: int
    # How many name/address/employer variants were resolved into this donor.
    contributor_key_count: int
    cycles: list[DonorCycle]
    top_recipients: list[DonorTopRecipient]


class PayeeCycle(BaseModel):
    """`gold.payee_cycle`: what committees paid a payee in one cycle, net as filed
    (every-FEC-dollar spec §5.4, §5.5)."""

    cycle: int
    total: float
    # How many committees paid it in the cycle.
    committee_count: int


class PayeeTopPayer(BaseModel):
    """`gold.payee_top_payer`: one of the 100 committees that paid a payee most in a cycle."""

    rank: int
    committee_id: str
    committee_name: str | None
    # The candidate the committee's payments to it are credited to: the one with more of the
    # amount where a handoff gives two, None for a committee raising for no candidate.
    candidate_id: str | None
    candidate_name: str | None
    amount: float


class Payee(BaseModel):
    """A payee page: `gold.payee`, the payments committees reported to one payee key, grouped by
    normalized name and never resolved (ADR-0012), a row per cycle, newest first, and who paid it
    most in `cycle`. A sub-item and an in-kind outlay reach no payee (every-FEC-dollar spec
    §5.4)."""

    payee_id: str
    # The normalized name the payments are grouped by.
    payee_key: str
    # Each the value with the most payee dollars over every cycle.
    display_name: str
    city: str | None
    state: str | None
    total_all_cycles: float
    first_cycle: int
    last_cycle: int
    cycles: list[PayeeCycle]
    # The cycle top_payers is for: the one asked for, else last_cycle.
    cycle: int
    # Most first; empty in a cycle it was not paid in.
    top_payers: list[PayeeTopPayer]


class ContributionPage(BaseModel):
    """A page of contributions, newest first; `next_cursor` fetches the next, None on the last."""

    contributions: list[Contribution]
    next_cursor: str | None


class Reconciliation(BaseModel):
    """`gold.reconciliation`: a committee whose fundlens figure exceeds its reported one by more
    than 1% on a measure (every-FEC-dollar spec §4.5, §5.6). Never a build failure: reported totals
    lag amendments, and a filer's line choice is not fundlens's to fix."""

    committee_id: str
    name: str | None
    cycle: int
    # The measure compared: `individual_itemized`, the itemized total against the reported
    # itemized individual figure; `operating_expenditures`, counted spending against the reported
    # operating expenditures.
    measure: str
    # fundlens's figure and the reported one, as gold's columns name them.
    fundlens: float
    reported: float
    # fundlens over reported; None where FEC reported 0.
    ratio: float | None


class ReconciliationPage(BaseModel):
    """A page of a cycle's reconciliation rows, the largest excess (fundlens - reported) first;
    `next_cursor` fetches the next, None on the last."""

    rows: list[Reconciliation]
    next_cursor: str | None


class SearchResult(BaseModel):
    """`gold.search_entity`: one match, best first."""

    kind: SearchKind
    # A candidate's or committee's FEC id, a race's race_id, a donor's donor_id, a payee's
    # payee_id.
    id: str
    name: str
    # The second string matched on: a race's slug, a candidate's principal committee, a
    # committee's connected organisation, a payee's other reported spellings.
    aliases: str | None
    # pg_trgm word similarity of the query to the better of name and aliases, 0 to 1.
    score: float


def problem_responses(*statuses: int) -> dict[int | str, dict[str, object]]:
    """A route's `responses=` entry documenting `statuses` as problem details.

    `model` registers the schema as a component, which FastAPI also files under the route's own
    `application/json`; the `application/problem+json` entry is what the API actually sends.
    Naming 422 also replaces FastAPI's own validation-error schema, which `problems.py` does
    not send.
    """
    responses: dict[int | str, dict[str, object]] = {}
    for status in statuses:
        model = ValidationProblem if status == 422 else Problem
        responses[status] = {
            "model": model,
            "content": {
                PROBLEM_JSON: {"schema": {"$ref": f"#/components/schemas/{model.__name__}"}}
            },
        }
    return responses
