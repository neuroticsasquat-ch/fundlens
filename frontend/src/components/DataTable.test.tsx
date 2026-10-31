import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "../test/app";
import DataTable from "./DataTable";
import type { Column } from "./DataTable";

type Row = { name: string; amount: number | null };

const rows: Row[] = [
  { name: "Bravo", amount: 20 },
  { name: "Alpha", amount: null },
  { name: "Charlie", amount: 30 },
  { name: "Delta", amount: 10 },
];

const columns: Column<Row>[] = [
  { key: "name", header: "Name", render: (r) => r.name, sortValue: (r) => r.name },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    render: (r) => String(r.amount),
    sortValue: (r) => r.amount,
  },
  { key: "note", header: "Note", render: () => "" },
];

const names = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("cell")[0].textContent);

const header = (name: string) => screen.getByRole("columnheader", { name: new RegExp(name) });

describe("DataTable", () => {
  it("keeps the rows' own order until a header is clicked", () => {
    renderWithProviders(<DataTable columns={columns} rows={rows} rowKey={(r) => r.name} />);

    expect(names()).toEqual(["Bravo", "Alpha", "Charlie", "Delta"]);
    expect(header("Amount")).toHaveAttribute("aria-sort", "none");
    expect(header("Note")).not.toHaveAttribute("aria-sort");
  });

  it("sorts numbers biggest first, flips on a second click and puts nulls last both ways", () => {
    renderWithProviders(<DataTable columns={columns} rows={rows} rowKey={(r) => r.name} />);

    fireEvent.click(screen.getByRole("button", { name: /Amount/ }));
    expect(names()).toEqual(["Charlie", "Bravo", "Delta", "Alpha"]);
    expect(header("Amount")).toHaveAttribute("aria-sort", "descending");

    fireEvent.click(screen.getByRole("button", { name: /Amount/ }));
    expect(names()).toEqual(["Delta", "Bravo", "Charlie", "Alpha"]);
    expect(header("Amount")).toHaveAttribute("aria-sort", "ascending");
  });

  it("sorts strings from A first", () => {
    renderWithProviders(<DataTable columns={columns} rows={rows} rowKey={(r) => r.name} />);

    fireEvent.click(screen.getByRole("button", { name: /Name/ }));

    expect(names()).toEqual(["Alpha", "Bravo", "Charlie", "Delta"]);
    expect(header("Name")).toHaveAttribute("aria-sort", "ascending");
    expect(header("Amount")).toHaveAttribute("aria-sort", "none");
  });

  it("starts from a default sort", () => {
    renderWithProviders(
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => r.name}
        defaultSort={{ key: "amount", direction: "asc" }}
      />,
    );

    expect(names()).toEqual(["Delta", "Bravo", "Charlie", "Alpha"]);
  });

  it("passes row props through and says so when there are no rows", () => {
    const { unmount } = renderWithProviders(
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => r.name}
        rowProps={(r) => ({ id: `row-${r.name}` })}
      />,
    );
    expect(document.getElementById("row-Alpha")).toBeInTheDocument();
    unmount();

    renderWithProviders(
      <DataTable columns={columns} rows={[]} rowKey={(r) => r.name} emptyMessage="Nothing here." />,
    );
    expect(screen.getByText("Nothing here.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
