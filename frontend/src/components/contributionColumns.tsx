import { Badge, Group } from "@mantine/core";
import { Link } from "react-router";
import type { Contribution } from "../api/client";
import { conduitName } from "../domain/committees";
import type { Column } from "./DataTable";
import { DASH, isoDate, money } from "./format";

// The columns every itemized-contributions table shares (`ContributionsTable`).

export const dateColumn: Column<Contribution> = {
  key: "date",
  header: "Date",
  render: (row) => isoDate(row.date),
};

export const employerColumn: Column<Contribution> = {
  key: "employer",
  header: "Employer",
  render: (row) => row.contributor_employer ?? DASH,
};

export const amountColumn: Column<Contribution> = {
  key: "amount",
  header: "Amount",
  align: "right",
  render: (row) => money(row.amount),
};

/** The conduit an earmark came through, linked, and whether it is the candidate's own money. */
export const notesColumn: Column<Contribution> = {
  key: "notes",
  header: "Notes",
  render: (row) => (
    <Group gap={4} wrap="nowrap">
      {row.conduit_committee_id && (
        <Badge
          variant="light"
          component={Link}
          to={`/committee/${row.conduit_committee_id}`}
          style={{ cursor: "pointer" }}
        >
          via {conduitName(row.conduit_committee_id)}
        </Badge>
      )}
      {row.is_self_funding && (
        <Badge variant="outline" color="gray">
          Self-funding
        </Badge>
      )}
    </Group>
  ),
};
