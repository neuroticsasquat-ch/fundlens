import { Anchor, Badge, Group, Stack, Text, Title } from "@mantine/core";
import { useMemo } from "react";
import { Link } from "react-router";
import type { OutsideSpendingKind, Race, RaceCandidate, RaceTopSpender } from "../api/client";
import DataTable from "../components/DataTable";
import type { Column } from "../components/DataTable";
import OutsideSpendingNotes from "../components/OutsideSpendingNotes";
import SideBadge from "../components/SideBadge";
import { count, money } from "../components/format";
import { candidateName } from "../domain/candidates";
import {
  byKind,
  hasOutsideSpending,
  kindsWithSpending,
  OUTSIDE_SPENDING_KINDS,
} from "../domain/outsideSpending";

/** The columns of a candidate's outside spending, for the kinds the race has. */
function candidateColumns(kinds: OutsideSpendingKind[]): Column<RaceCandidate>[] {
  const column = (
    key: string,
    header: string,
    value: (candidate: RaceCandidate) => number | null,
  ): Column<RaceCandidate> => ({
    key,
    header,
    align: "right",
    // An electioneering communication's null is no row, a dash, never $0 (spec §6.5).
    render: (candidate) => money(value(candidate)),
    sortValue: value,
  });
  const amounts = (candidate: RaceCandidate) => byKind(candidate.outside_spending);
  return [
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
    ...kinds.flatMap((kind) => {
      const { label } = OUTSIDE_SPENDING_KINDS[kind];
      if (kind === "electioneering_communication") {
        return [column(kind, label, (candidate) => amounts(candidate)[kind].none)];
      }
      if (kind === "party_coordinated") {
        return [column(kind, label, (candidate) => amounts(candidate)[kind].support)];
      }
      return [
        column(`${kind}-for`, `${label} for`, (candidate) => amounts(candidate)[kind].support),
        column(`${kind}-against`, `${label} against`, (candidate) => amounts(candidate)[kind].oppose),
      ];
    }),
  ];
}

/** The columns of the race's top spenders, each candidate named as the race names them. */
function spenderColumns(candidates: RaceCandidate[]): Column<RaceTopSpender>[] {
  const names = new Map(candidates.map((candidate) => [candidate.candidate_id, candidate]));
  return [
    {
      key: "rank",
      header: "Rank",
      align: "right",
      render: (spender) => count(spender.rank),
      sortValue: (spender) => spender.rank,
    },
    {
      key: "spender",
      header: "Spender",
      // Every spender has a committee page, a Form 5, 7 or 9 filer too (spec §6.5).
      render: (spender) => (
        <Group gap="xs" wrap="nowrap">
          <Anchor component={Link} to={`/committee/${spender.committee_id}`}>
            {spender.name ?? spender.committee_id}
          </Anchor>
          {!spender.is_committee && (
            <Badge variant="outline" color="gray">
              Not a committee
            </Badge>
          )}
        </Group>
      ),
    },
    {
      key: "candidate",
      header: "Candidate",
      render: (spender) => {
        const candidate = names.get(spender.candidate_id);
        return (
          <Anchor component={Link} to={`/candidate/${spender.candidate_id}`}>
            {candidate ? candidateName(candidate) : spender.candidate_id}
          </Anchor>
        );
      },
    },
    {
      key: "kind",
      header: "Kind",
      render: (spender) => OUTSIDE_SPENDING_KINDS[spender.kind].label,
    },
    {
      key: "side",
      header: "For or against",
      render: (spender) => <SideBadge side={spender.support_oppose} />,
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      render: (spender) => money(spender.amount),
      sortValue: (spender) => spender.amount,
    },
  ];
}

/**
 * A race's outside spending (every-FEC-dollar spec §6.5): each candidate's by kind and side, what
 * each kind is, and the race's biggest lines of it, one spender's spending of one kind on one
 * candidate on one side each. Nothing at all where nobody spent anything on the race.
 */
function RaceOutsideSpending({ race }: { race: Race }) {
  const kinds = useMemo(() => kindsWithSpending(race.outside_spending), [race.outside_spending]);
  const columns = useMemo(() => candidateColumns(kinds), [kinds]);
  const spenders = useMemo(() => spenderColumns(race.candidates), [race.candidates]);
  if (kinds.length === 0) return null;
  const spentOn = race.candidates.filter((candidate) =>
    hasOutsideSpending(candidate.outside_spending),
  );
  return (
    <section aria-labelledby="outside-spending">
      <Title order={2} id="outside-spending" mb="sm">
        Outside spending
      </Title>
      <Stack gap="md">
        <DataTable
          columns={columns}
          rows={spentOn}
          rowKey={(candidate) => candidate.candidate_id}
        />
        <OutsideSpendingNotes kinds={kinds} />
        <section aria-labelledby="top-spenders">
          <Title order={3} id="top-spenders" mb="sm">
            Top outside spenders
          </Title>
          <Stack gap="xs">
            <DataTable
              columns={spenders}
              rows={race.top_spenders}
              rowKey={(spender) => String(spender.rank)}
              emptyMessage="No spender's outside spending on a candidate in this race nets above $0."
            />
            {race.top_spenders.some((spender) => !spender.is_committee) && (
              <Text c="dimmed" size="sm">
                Not a committee: a non-committee spender, a person, group, corporation or union that
                reported only its outside spending to the FEC. Each still has a page.
              </Text>
            )}
          </Stack>
        </section>
      </Stack>
    </section>
  );
}

export default RaceOutsideSpending;
