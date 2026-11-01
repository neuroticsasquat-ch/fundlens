import { Anchor, Badge, Group, Stack, Text, Title } from "@mantine/core";
import { Link, useParams } from "react-router";
import { $api } from "../api/client";
import type { Candidate, CandidateCycle } from "../api/client";
import { CONTRIBUTION_PAGES } from "../api/contributions";
import ContributionsTable from "../components/ContributionsTable";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import QueryStatus from "../components/QueryStatus";
import TopDonorsTable from "../components/TopDonorsTable";
import { DASH, money } from "../components/format";
import { usePageTitle } from "../components/usePageTitle";
import { candidateTotal } from "../domain/candidates";
import { officeLabel, raceLabel, raceSlugLabel } from "../domain/states";
import { raceRoute } from "../search/target";
import { partyColour } from "../theme";
import CycleHeading from "./CycleHeading";
import CycleTotalsChart from "./CycleTotalsChart";
import type { CycleSeries } from "./cycleTotalsOption";
import { useScrollToHash, useShownCycle } from "./entityCycle";

const CYCLE_COLUMNS: Column<CandidateCycle>[] = [
  {
    key: "cycle",
    header: "Cycle",
    render: (row) => row.cycle,
    sortValue: (row) => row.cycle,
  },
  {
    key: "race",
    header: "Race",
    render: (row) =>
      row.race_slug ? (
        <Anchor component={Link} to={raceRoute(row.race_slug)}>
          {raceSlugLabel(row.race_slug)}
        </Anchor>
      ) : (
        DASH
      ),
  },
  {
    key: "individual",
    header: "From individuals",
    align: "right",
    render: (row) => money(row.total_individual),
    sortValue: (row) => row.total_individual,
  },
  {
    key: "committee",
    header: "From committees",
    align: "right",
    render: (row) => money(row.total_committee),
    sortValue: (row) => row.total_committee,
  },
  {
    key: "self",
    header: "Self-funding",
    align: "right",
    render: (row) => money(row.self_funding),
    sortValue: (row) => row.self_funding,
  },
  {
    key: "total",
    header: "Total",
    align: "right",
    render: (row) => money(candidateTotal(row)),
    sortValue: candidateTotal,
  },
];

const CYCLE_SERIES: CycleSeries<CandidateCycle>[] = [
  { name: "From individuals", value: (row) => row.total_individual },
  { name: "From committees", value: (row) => row.total_committee },
  { name: "Self-funding", value: (row) => row.self_funding },
];

/** "Senate · Maryland", "House · Maryland 5th", "President"; null when gold has no office. */
function seatLabel({ office, state, district }: Candidate): string | null {
  if (office === null) return null;
  // Without a state there is no seat to name, only the office.
  if (office === "P" || state === null) return officeLabel(office);
  const seat = raceLabel({ office, state, district: district ?? "00", is_special: false });
  return `${officeLabel(office)} · ${seat}`;
}

/** `/candidate/:id`: a candidate's money in every cycle, and what they received in one. */
function CandidatePage() {
  const id = useParams().id ?? "";
  // Keyed, so a table's sort starts over on another candidate.
  return <CandidateView key={id} id={id} />;
}

function CandidateView({ id }: { id: string }) {
  const candidate = $api.useQuery("get", "/v1/candidates/{candidate_id}", {
    params: { path: { candidate_id: id } },
  });
  usePageTitle(candidate.data ? (candidate.data.name ?? id) : "Candidate");

  return (
    <Stack gap="lg" py="md">
      <QueryStatus
        query={candidate}
        notFound={
          <Stack>
            <Title order={1}>No candidate {id}</Title>
            <Anchor component={Link} to="/">
              Back to fundlens
            </Anchor>
          </Stack>
        }
      >
        {(data) => <CandidateDetail candidate={data} />}
      </QueryStatus>
    </Stack>
  );
}

function CandidateDetail({ candidate }: { candidate: Candidate }) {
  useScrollToHash();
  const cycles = candidate.cycles.map((row) => row.cycle);
  const [cycle, showCycle] = useShownCycle(cycles);
  const shown = candidate.cycles.find((row) => row.cycle === cycle);
  const seat = seatLabel(candidate);

  return (
    <Stack gap="xl">
      <Stack gap={4}>
        <Group gap="sm">
          <Title order={1}>{candidate.name ?? candidate.candidate_id}</Title>
          {candidate.party && (
            <Badge size="lg" variant="light" color={partyColour(candidate.party)}>
              {candidate.party}
            </Badge>
          )}
        </Group>
        <Text c="dimmed">
          {seat ? `${seat} · ` : ""}FEC {candidate.candidate_id}
        </Text>
      </Stack>
      <section aria-labelledby="by-cycle">
        <Title order={2} id="by-cycle" mb="sm">
          Totals by cycle
        </Title>
        {candidate.cycles.length === 0 ? (
          <Text c="dimmed">No money is recorded for this candidate in any cycle.</Text>
        ) : (
          <Stack gap="md">
            <CycleTotalsChart rows={candidate.cycles} series={CYCLE_SERIES} />
            <DataTable
              columns={CYCLE_COLUMNS}
              rows={candidate.cycles}
              rowKey={(row) => String(row.cycle)}
              rowProps={(row) => ({ id: `cycle-${row.cycle}` })}
            />
          </Stack>
        )}
      </section>
      {shown && (
        <section aria-labelledby="in-cycle">
          <Stack gap="lg">
            <CycleHeading cycles={cycles} cycle={shown.cycle} onChange={showCycle} />
            <section aria-labelledby="top-donors">
              <Title order={3} id="top-donors" mb="sm">
                Top donors
              </Title>
              <TopDonorsTable
                // Keyed, so the sort starts over in another cycle.
                key={shown.cycle}
                rows={shown.top_donors}
                emptyMessage={`No resolved individual donors in ${shown.cycle}.`}
              />
            </section>
            <section aria-labelledby="contributions">
              <Title order={3} id="contributions" mb="sm">
                Contributions
              </Title>
              <CandidateContributions id={candidate.candidate_id} cycle={shown.cycle} />
            </section>
          </Stack>
        </section>
      )}
    </Stack>
  );
}

function CandidateContributions({ id, cycle }: { id: string; cycle: number }) {
  const contributions = $api.useInfiniteQuery(
    "get",
    "/v1/candidates/{candidate_id}/contributions",
    { params: { path: { candidate_id: id }, query: { cycle } } },
    CONTRIBUTION_PAGES,
  );
  return (
    <ContributionsTable
      query={contributions}
      emptyMessage={`No itemized contributions to this candidate in ${cycle}.`}
    />
  );
}

export default CandidatePage;
