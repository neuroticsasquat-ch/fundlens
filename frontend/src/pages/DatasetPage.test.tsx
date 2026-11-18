import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { DATASET } from "../test/fixtures";

const SNAPSHOT = "https://data.fundlens.org/v1/2026-11-22/";

/** The table whose caption is `caption`, and its body rows. */
const rowsOf = async (caption: string) => {
  const table = (await screen.findByText(caption)).closest("table")!;
  return within(table).getAllByRole("row").slice(1);
};

/** The row of the latest snapshot's table naming `name`. */
const tableRow = async (name: string) =>
  (await rowsOf("Tables of the snapshot of 2026-11-22")).find((row) =>
    within(row).queryByText(name, { selector: "code" }),
  )!;

describe("DatasetPage", () => {
  it("lists the latest snapshot's tables with their files for the newest cycle", async () => {
    renderApp("/dataset");

    expect(await screen.findByRole("heading", { level: 1, name: "Dataset" })).toBeInTheDocument();
    expect(document.title).toBe("Dataset · fundlens");
    expect(
      await screen.findByRole("heading", { level: 2, name: "Snapshot of 2026-11-22" }),
    ).toBeInTheDocument();
    expect(await rowsOf("Tables of the snapshot of 2026-11-22")).toHaveLength(3);
    expect(screen.getByText(/2 cycles · resolution precision 97\.0%, recall 95\.0%/)).toBeInTheDocument();

    // One file: a link to it, which a browser downloads.
    const race = await tableRow("race");
    expect(within(race).getByRole("link", { name: "race/cycle=2024/part-0000.parquet" })).toHaveAttribute(
      "href",
      `${SNAPSHOT}race/cycle=2024/part-0000.parquet`,
    );
    expect(within(race).getByRole("link", { name: "schema" })).toHaveAttribute(
      "href",
      "https://data.fundlens.org/v1/schema/race.json",
    );
    // Many files: the directory's address to copy, its files in the manifest.
    const contribution = await tableRow("contribution");
    expect(within(contribution).getByText(`${SNAPSHOT}contribution/cycle=2024/`)).toBeInTheDocument();
    expect(within(contribution).getByText(/2 files, 30 kB/)).toBeInTheDocument();
    expect(within(contribution).getByRole("link", { name: "manifest.json" })).toHaveAttribute(
      "href",
      `${SNAPSHOT}manifest.json`,
    );
    // A table with no cycle is its one file whatever the cycle.
    expect(within(await tableRow("donor")).getByRole("link", { name: "donor.parquet" })).toHaveAttribute(
      "href",
      `${SNAPSHOT}donor.parquet`,
    );
  });

  it("switches the files and the one-liners to the chosen cycle", async () => {
    renderApp("/dataset");

    const oneLiner = await screen.findByLabelText("DuckDB one-liner");
    expect(oneLiner).toHaveTextContent("contribution/cycle=2024/%");
    expect(oneLiner).toHaveTextContent(
      "read_json('https://data.fundlens.org/v1/latest/manifest.json')",
    );

    fireEvent.click(screen.getByRole("combobox", { name: "Show cycle" }));
    fireEvent.click(await screen.findByRole("option", { name: "2022" }));

    expect(await screen.findByLabelText("DuckDB one-liner")).toHaveTextContent(
      "contribution/cycle=2022/%",
    );
    expect(screen.getByLabelText("pandas one-liner")).toHaveTextContent("race/cycle=2022/");
    expect(
      within(await tableRow("contribution")).getByRole("link", {
        name: "contribution/cycle=2022/bucket-00-part-0000.parquet",
      }),
    ).toBeInTheDocument();
  });

  it("states the license, the FEC notice, and links the docs", async () => {
    renderApp("/dataset");

    expect(await screen.findByRole("link", { name: "CC BY 4.0" })).toHaveAttribute(
      "href",
      "https://data.fundlens.org/v1/LICENSE",
    );
    expect(screen.getByText("fundlens (fundlens.org), CC BY 4.0")).toBeInTheDocument();
    expect(within(screen.getByRole("alert")).getByText(/11 CFR 104\.15/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "README" })).toHaveAttribute(
      "href",
      "https://data.fundlens.org/v1/README.md",
    );
    expect(screen.getByRole("link", { name: "methodology page" })).toHaveAttribute(
      "href",
      "/methodology",
    );
  });

  it("lists the snapshots before the latest", async () => {
    renderApp("/dataset");

    const [previous, ...more] = await rowsOf("Earlier snapshots");
    expect(more).toHaveLength(0);
    expect(previous).toHaveTextContent("2026-11-15");
    expect(previous).toHaveTextContent("20261115T030000Z");
    expect(within(previous).getByRole("link", { name: "manifest.json" })).toHaveAttribute(
      "href",
      "https://data.fundlens.org/v1/2026-11-15/manifest.json",
    );
  });

  it("reads the newest snapshot from its own directory until latest/ holds it", async () => {
    // `latest/` still the previous week's: its copy of the newest is under way.
    renderApp("/dataset", {
      handlers: [
        http.get("/v1/dataset", ({ response }) =>
          response(200).json({ ...DATASET, latest: "2026-11-15" }),
        ),
      ],
    });

    expect(
      await screen.findByRole("heading", { level: 2, name: "Snapshot of 2026-11-22" }),
    ).toBeInTheDocument();
    expect(await screen.findByLabelText("DuckDB one-liner")).toHaveTextContent(
      `read_json('${SNAPSHOT}manifest.json')`,
    );
    expect(screen.queryByText("https://data.fundlens.org/v1/latest/")).not.toBeInTheDocument();
  });

  it("says so when no snapshot is published yet", async () => {
    renderApp("/dataset", {
      handlers: [
        http.get("/v1/dataset", ({ response }) =>
          response(200).json({ ...DATASET, latest: null, snapshots: [] }),
        ),
      ],
    });

    expect(await screen.findByText(/No snapshot is published yet/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2 })).not.toBeInTheDocument();
  });
});
