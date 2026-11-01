import { Anchor, Badge, Group, Stack, Text, Title } from "@mantine/core";
import { useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { $api } from "../api/client";
import type { Office, Race, RaceCandidate, RaceTopCommittee, RaceTopDonor } from "../api/client";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import QueryStatus from "../components/QueryStatus";
import TopDonorsTable from "../components/TopDonorsTable";
import { count, DASH, money } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import { candidateName, candidateTotal } from "../domain/candidates";
import { officeLabel, raceLabel } from "../domain/states";
import { parseCycle } from "../shell/cycleTarget";
import { partyColour } from "../theme";
import CandidateTotalsChart from "./CandidateTotalsChart";
import NotFound from "./NotFound";

/** The URL's office segment, as the API takes it, and its FEC office code. */
const OFFICES = { president: "P", senate: "S", house: "H" } as const satisfies Record<
  string,
  Office
>;

type OfficeSegment = keyof typeof OFFICES;

const isOfficeSegment = (office: string | undefined): office is OfficeSegment =>
  office !== undefined && Object.hasOwn(OFFICES, office);

// The API's pattern for a race's place: `MD`, `MD-05`, `US`. Anything else is no race at all.
const PLACE = /^[A-Z]{2}(-[0-9]{2})?$/;

// FEC's incumbent/challenger/open code (`CAND_ICI`).
const SEAT_STATUS: Record<string, string> = { I: "Incumbent", C: "Challenger", O: "Open" };

const CANDIDATE_COLUMNS: Column<RaceCandidate>[] = [
  {
    key: "name",
    header: "Candidate",
    render: (candidate) => (
      <Anchor component={Link} to={`/candidate/${candidate.candidate_id}`}>
        {candidateName(candidate)}
      </Anchor>
    ),
    sortValue: candidateName,
  },
  {
    key: "party",
    header: "Party",
    render: (candidate) =>
      candidate.party ? (
        <Badge variant="light" color={partyColour(candidate.party)}>
          {candidate.party}
        </Badge>
      ) : (
        DASH
      ),
  },
  {
    key: "status",
    header: "Status",
    render: (candidate) =>
      SEAT_STATUS[candidate.incumbent_challenger_open ?? ""] ??
      candidate.incumbent_challenger_open ??
      DASH,
  },
  {
    key: "individual",
    header: "From individuals",
    align: "right",
    render: (candidate) => money(candidate.total_individual),
    sortValue: (candidate) => candidate.total_individual,
  },
  {
    key: "committee",
    header: "From committees",
    align: "right",
    render: (candidate) => money(candidate.total_committee),
    sortValue: (candidate) => candidate.total_committee,
  },
  {
    key: "self",
    header: "Self-funding",
    align: "right",
    render: (candidate) => money(candidate.self_funding),
    sortValue: (candidate) => candidate.self_funding,
  },
  {
    key: "total",
    header: "Total",
    align: "right",
    render: (candidate) => money(candidateTotal(candidate)),
    sortValue: candidateTotal,
  },
];

const COMMITTEE_KINDS: Record<RaceTopCommittee["kind"], string> = {
  contribution: "Contributions",
  ie: "Independent expenditures",
};

const COMMITTEE_COLUMNS: Column<RaceTopCommittee>[] = [
  {
    key: "rank",
    header: "Rank",
    align: "right",
    render: (committee) => count(committee.rank),
    sortValue: (committee) => committee.rank,
  },
  {
    key: "name",
    header: "Committee",
    render: (committee) => (
      <Anchor component={Link} to={`/committee/${committee.committee_id}`}>
        {committee.name ?? committee.committee_id}
      </Anchor>
    ),
  },
  {
    key: "kind",
    header: "Kind",
    render: (committee) => (
      <Badge variant="outline" color="gray">
        {COMMITTEE_KINDS[committee.kind]}
      </Badge>
    ),
  },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    render: (committee) => money(committee.amount),
    sortValue: (committee) => committee.amount,
  },
];

/**
 * The "Given to" column of a race's top donors: what each donor gave each candidate, most first,
 * the candidate linked to their page.
 */
function givenToColumn(candidates: RaceCandidate[]): Column<RaceTopDonor> {
  const names = new Map(candidates.map((candidate) => [candidate.candidate_id, candidate]));
  return {
    key: "given-to",
    header: "Given to",
    render: (donor) => (
      <Stack gap={0}>
        {[...donor.candidates]
          .sort((a, b) => b.amount - a.amount)
          .map(({ candidate_id, amount }) => {
            const candidate = names.get(candidate_id);
            return (
              <Text key={candidate_id} size="sm">
                <Anchor component={Link} to={`/candidate/${candidate_id}`} inherit>
                  {candidate ? candidateName(candidate) : candidate_id}
                </Anchor>{" "}
                {money(amount)}
              </Text>
            );
          })}
      </Stack>
    ),
  };
}

/** "2024 Senate · Maryland", "2024 House · Maryland 5th", "2024 President". */
function raceHeading(race: Pick<Race, "cycle" | "office" | "state" | "district">): string {
  const office = `${race.cycle} ${officeLabel(race.office)}`;
  // The special badge says "special"; the heading names the seat.
  return race.office === "P" ? office : `${office} · ${raceLabel({ ...race, is_special: false })}`;
}

/** `/race/:cycle/:office/:place` (`?special=1` for the special race): one race and its money. */
function RacePage() {
  const params = useParams();
  const [search] = useSearchParams();
  const cycle = parseCycle(params.cycle);
  const { office, place } = params;
  if (cycle === undefined || !isOfficeSegment(office) || !place || !PLACE.test(place)) {
    return <NotFound />;
  }
  const special = search.get("special") === "1";
  // Keyed, so a table's sort starts over in another race.
  return (
    <RaceView
      key={`${cycle}/${office}/${place}/${special}`}
      cycle={cycle}
      office={office}
      place={place}
      special={special}
    />
  );
}

function RaceView({
  cycle,
  office,
  place,
  special,
}: {
  cycle: number;
  office: OfficeSegment;
  place: string;
  special: boolean;
}) {
  const race = $api.useQuery("get", "/v1/races/{cycle}/{office}/{place}", {
    params: { path: { cycle, office, place }, query: special ? { special: true } : undefined },
  });
  const label = officeLabel(OFFICES[office]);
  usePageTitle(race.data ? raceHeading(race.data) : `${cycle} ${label} race`);

  return (
    <Stack gap="lg" py="md">
      <QueryStatus
        query={race}
        notFound={
          <Stack>
            <Title order={1}>
              No {label} {special ? "special " : ""}race for {place} in {cycle}
            </Title>
            <Anchor component={Link} to={`/cycles/${cycle}`}>
              All {cycle} races
            </Anchor>
          </Stack>
        }
      >
        {(data) => <RaceDetail race={data} />}
      </QueryStatus>
    </Stack>
  );
}

function RaceDetail({ race }: { race: Race }) {
  const donorColumns = useMemo(() => [givenToColumn(race.candidates)], [race.candidates]);
  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Group gap="sm">
          <Title order={1}>{raceHeading(race)}</Title>
          {race.is_special && <Badge size="lg">Special</Badge>}
        </Group>
        <Text c="dimmed">
          {count(race.candidate_count)}{" "}
          {race.candidate_count === 1 ? "candidate" : "candidates"} ·{" "}
          {money(race.total_individual)} from individuals · {money(race.total_committee)} from
          committees
        </Text>
      </Stack>
      {race.candidates.length === 0 ? (
        <Text>
          This race has no candidates.{" "}
          <Anchor component={Link} to={`/cycles/${race.cycle}`}>
            All {race.cycle} races
          </Anchor>
        </Text>
      ) : (
        <>
          <section aria-labelledby="candidates">
            <Title order={2} id="candidates" mb="sm">
              Candidates
            </Title>
            <Stack gap="md">
              <CandidateTotalsChart candidates={race.candidates} />
              <DataTable
                columns={CANDIDATE_COLUMNS}
                rows={race.candidates}
                rowKey={(candidate) => candidate.candidate_id}
                defaultSort={{ key: "total", direction: "desc" }}
              />
            </Stack>
          </section>
          <section aria-labelledby="top-committees">
            <Title order={2} id="top-committees" mb="sm">
              Top committees
            </Title>
            <DataTable
              columns={COMMITTEE_COLUMNS}
              rows={race.top_committees}
              rowKey={(committee) => `${committee.kind}-${committee.committee_id}`}
              emptyMessage="No committee has given to or spent on a candidate in this race."
            />
          </section>
          <section aria-labelledby="top-donors">
            <Title order={2} id="top-donors" mb="sm">
              Top donors
            </Title>
            <TopDonorsTable
              rows={race.top_donors}
              extraColumns={donorColumns}
              emptyMessage="No resolved individual donor has given to a candidate in this race."
            />
          </section>
        </>
      )}
    </Stack>
  );
}

export default RacePage;
