import { Anchor, Badge } from "@mantine/core";
import { Link } from "react-router";
import type { CommitteeTopRecipient } from "../api/client";
import type { Column } from "../components/DataTable";
import { count, money } from "../components/format";

/** A committee's or a donor's top recipient: a candidate or a committee, and how much. */
export type TopRecipient = Pick<
  CommitteeTopRecipient,
  "rank" | "recipient_kind" | "recipient_id" | "name" | "amount"
>;

const RECIPIENT_KINDS: Record<TopRecipient["recipient_kind"], string> = {
  candidate: "Candidate",
  committee: "Committee",
};

/** A top-recipient list's columns, each recipient linked to their page. */
export const RECIPIENT_COLUMNS: Column<TopRecipient>[] = [
  {
    key: "rank",
    header: "Rank",
    align: "right",
    render: (row) => count(row.rank),
    sortValue: (row) => row.rank,
  },
  {
    key: "name",
    header: "Recipient",
    render: (row) => (
      <Anchor component={Link} to={`/${row.recipient_kind}/${row.recipient_id}`}>
        {row.name ?? row.recipient_id}
      </Anchor>
    ),
  },
  {
    key: "kind",
    header: "Kind",
    render: (row) => (
      <Badge variant="outline" color="gray">
        {RECIPIENT_KINDS[row.recipient_kind]}
      </Badge>
    ),
  },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    render: (row) => money(row.amount),
    sortValue: (row) => row.amount,
  },
];
