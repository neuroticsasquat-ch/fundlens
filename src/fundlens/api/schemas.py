"""Pydantic response models: the OpenAPI contract the frontend's client is generated from.

Money is a JSON number of dollars (gold's `numeric(16, 2)`): a `Decimal` would serialize as a
string, and the SPA only formats and charts these figures. Every field is typed down to its
leaves, so the generated client has no `unknown` in it.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

PROBLEM_JSON = "application/problem+json"

type Office = Literal["H", "S", "P"]
type SearchKind = Literal["donor", "candidate", "committee", "race"]


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
    """The live gold build (`gold.meta`, spec §7.1)."""

    build_id: str
    published_at: datetime
    # None until M3 publishes a resolved build (NEU-2039 §3).
    resolver_version: str | None
    model_version: str | None
    precision: float | None
    recall: float | None
    # Keyed by cycle, as a string ("2024"): JSON object keys are strings.
    cycles: dict[str, MetaCycle]


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
    ie_support: float
    ie_oppose: float


class RaceCandidate(BaseModel):
    """`gold.race_candidate`: a candidate in the race and their money this cycle."""

    candidate_id: str
    name: str | None
    party: str | None
    incumbent_challenger_open: str | None
    principal_committee_id: str | None
    total_individual: float
    total_committee: float
    self_funding: float
    ie_support: float
    ie_oppose: float


class RaceTopCommittee(BaseModel):
    """`gold.race_top_committee`: a committee among the 100 that spent most on the race."""

    rank: int
    committee_id: str
    name: str | None
    amount: float
    kind: Literal["contribution", "ie"]


class Race(RaceSummary):
    """A race page: the race, its candidates (most money first) and its top committees."""

    candidates: list[RaceCandidate]
    top_committees: list[RaceTopCommittee]


class CandidateCycle(BaseModel):
    """`gold.candidate_cycle`: a candidate's money in one cycle."""

    cycle: int
    # None for a filing that matched no seat (spec §5.2).
    race_id: str | None
    race_slug: str | None
    total_individual: float
    total_committee: float
    self_funding: float
    ie_support: float
    ie_oppose: float
    # None until M3 resolves donors.
    contributor_count: int | None


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


class CommitteeCycle(BaseModel):
    """`gold.committee_cycle`: a committee's money in one cycle, and whom it gave most to."""

    cycle: int
    total_individual: float
    self_funding: float
    total_from_committees: float
    total_to_candidates: float
    ie_total: float
    top_recipients: list[CommitteeTopRecipient]


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


class ContributionPage(BaseModel):
    """A page of contributions, newest first; `next_cursor` fetches the next, None on the last."""

    contributions: list[Contribution]
    next_cursor: str | None


class SearchResult(BaseModel):
    """`gold.search_entity`: one match, best first."""

    kind: SearchKind
    # A candidate's or committee's FEC id, a race's race_id, a donor's donor_id.
    id: str
    name: str
    # The second string matched on: a race's slug, a candidate's principal committee, a
    # committee's connected organisation.
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
