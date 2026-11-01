import { Anchor } from "@mantine/core";
import { Link } from "react-router";
import type { TopDonor } from "../api/client";
import { donorName } from "../domain/donors";
import DataTable from "./DataTable";
import type { Column } from "./DataTable";
import { count, money } from "./format";

const rankColumn: Column<TopDonor> = {
  key: "rank",
  header: "Rank",
  align: "right",
  render: (donor) => count(donor.rank),
  sortValue: (donor) => donor.rank,
};

const donorColumn: Column<TopDonor> = {
  key: "donor",
  header: "Donor",
  render: (donor) => (
    <Anchor component={Link} to={`/donor/${donor.donor_id}`}>
      {donorName(donor)}
    </Anchor>
  ),
};

const amountColumn: Column<TopDonor> = {
  key: "amount",
  header: "Amount",
  align: "right",
  render: (donor) => money(donor.amount),
  sortValue: (donor) => donor.amount,
};

/**
 * A top-donor list (spec §7.1), most first, each donor linked to their page. `extraColumns` go
 * between the donor and the amount: the race page's per-candidate breakdown.
 */
function TopDonorsTable<T extends TopDonor>({
  rows,
  emptyMessage,
  extraColumns = [],
}: {
  rows: T[];
  emptyMessage: string;
  extraColumns?: Column<T>[];
}) {
  return (
    <DataTable<T>
      columns={[rankColumn, donorColumn, ...extraColumns, amountColumn]}
      rows={rows}
      rowKey={(donor) => String(donor.donor_id)}
      emptyMessage={emptyMessage}
    />
  );
}

export default TopDonorsTable;
