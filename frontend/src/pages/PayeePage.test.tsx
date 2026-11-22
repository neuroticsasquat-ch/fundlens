import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Payee } from "../api/client";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { lastOption } from "../test/echarts";
import { PAYEE_BLUE_HARBOR, PAYEE_IDS } from "../test/fixtures";

const PATH = `/payee/${PAYEE_IDS.blueHarbor}`;

const section = (name: string) => screen.getByRole("region", { name });
const rows = (name: string) => within(section(name)).getAllByRole("row").slice(1);
const cells = (row: HTMLElement) =>
  within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent);

/**
 * BLUE HARBOR with a 2022 cycle too, paid by WHITLOCK FOR SENATE alone; the cycles each request
 * asked for, `null` for none.
 */
function twoCycles() {
  const asked: (string | null)[] = [];
  const payee: Payee = {
    ...PAYEE_BLUE_HARBOR,
    total_all_cycles: 12500,
    first_cycle: 2022,
    cycles: [...PAYEE_BLUE_HARBOR.cycles, { cycle: 2022, total: 2000, committee_count: 1 }],
  };
  const handler = http.get("/v1/payees/{payee_id}", ({ request, response }) => {
    const cycle = new URL(request.url).searchParams.get("cycle");
    asked.push(cycle);
    return response(200).json(
      cycle === "2022"
        ? {
            ...payee,
            cycle: 2022,
            top_payers: [{ ...PAYEE_BLUE_HARBOR.top_payers[1], rank: 1, amount: 2000 }],
          }
        : payee,
    );
  });
  return { handler, asked };
}

describe("PayeePage", () => {
  it("shows the payee's name, place, total and how it is grouped", async () => {
    renderApp(PATH);

    expect(
      await screen.findByRole("heading", { level: 1, name: "BLUE HARBOR STRATEGIES LLC" }),
    ).toBeInTheDocument();
    expect(screen.getByText("BALTIMORE, MD")).toBeInTheDocument();
    expect(screen.getByText("$10,500 paid by committees in 2024")).toBeInTheDocument();
    const note = screen.getByText(/^Grouped by reported payee name;/);
    expect(within(note).getByRole("link", { name: "Methodology" })).toHaveAttribute(
      "href",
      "/methodology",
    );
    expect(document.title).toBe("BLUE HARBOR STRATEGIES LLC · fundlens");
  });

  it("shows the totals by cycle as a table and a chart", async () => {
    renderApp(PATH);
    await screen.findByRole("region", { name: "Totals by cycle" });

    expect(rows("Totals by cycle").map(cells)).toEqual([["2024", "2", "$10,500"]]);
    expect(lastOption().series).toMatchObject([{ type: "bar", name: "Paid", data: [10500] }]);
  });

  it("lists both paying committees and their candidates, linked to their pages", async () => {
    renderApp(PATH);
    await screen.findByRole("region", { name: "Paid by" });

    expect(screen.getByRole("heading", { level: 2, name: "In 2024" })).toBeInTheDocument();
    expect(rows("Paid by").map(cells)).toEqual([
      ["1", "OKAFOR FOR MARYLAND", "OKAFOR, DIANA", "$7,500"],
      ["2", "WHITLOCK FOR SENATE", "WHITLOCK, GORDON", "$3,000"],
    ]);
    const paidBy = section("Paid by");
    expect(within(paidBy).getByRole("link", { name: "OKAFOR FOR MARYLAND" })).toHaveAttribute(
      "href",
      "/committee/C00800103",
    );
    expect(within(paidBy).getByRole("link", { name: "WHITLOCK FOR SENATE" })).toHaveAttribute(
      "href",
      "/committee/C00800104",
    );
    expect(within(paidBy).getByRole("link", { name: "WHITLOCK, GORDON" })).toHaveAttribute(
      "href",
      "/candidate/S4MD00104",
    );
  });

  it("shows a dash for a committee raising for no candidate", async () => {
    const payer = { ...PAYEE_BLUE_HARBOR.top_payers[0], candidate_id: null, candidate_name: null };
    renderApp(PATH, {
      handlers: [
        http.get("/v1/payees/{payee_id}", ({ response }) =>
          response(200).json({ ...PAYEE_BLUE_HARBOR, top_payers: [payer] }),
        ),
      ],
    });
    await screen.findByRole("region", { name: "Paid by" });

    expect(rows("Paid by").map(cells)).toEqual([["1", "OKAFOR FOR MARYLAND", "—", "$7,500"]]);
  });

  it("says so when no committee paid it in the cycle shown", async () => {
    renderApp(PATH, {
      handlers: [
        http.get("/v1/payees/{payee_id}", ({ response }) =>
          response(200).json({ ...PAYEE_BLUE_HARBOR, top_payers: [] }),
        ),
      ],
    });

    expect(await screen.findByText("No committee paid this payee in 2024.")).toBeInTheDocument();
  });

  it("asks for another cycle's payers when it is picked, and for none on load", async () => {
    const { handler, asked } = twoCycles();
    renderApp(PATH, { handlers: [handler] });
    await screen.findByRole("region", { name: "Paid by" });
    expect(asked).toEqual([null]);

    fireEvent.click(screen.getByRole("combobox", { name: "Cycle shown" }));
    fireEvent.click(await screen.findByRole("option", { name: "2022" }));

    expect(await screen.findByRole("heading", { level: 2, name: "In 2022" })).toBeInTheDocument();
    await within(section("Paid by")).findByText("$2,000");
    expect(rows("Paid by").map(cells)).toEqual([
      ["1", "WHITLOCK FOR SENATE", "WHITLOCK, GORDON", "$2,000"],
    ]);
    expect(asked).toEqual([null, "2022"]);
  });

  it("opens on the cycle the switcher sent it to", async () => {
    const { handler } = twoCycles();
    renderApp(`${PATH}#cycle-2022`, { handlers: [handler] });

    expect(await screen.findByRole("heading", { level: 2, name: "In 2022" })).toBeInTheDocument();
    await within(section("Paid by")).findByText("$2,000");
  });

  it("says a payee id it does not know has no page", async () => {
    renderApp("/payee/0000000000000000");

    expect(
      await screen.findByRole("heading", { level: 1, name: "No payee 0000000000000000" }),
    ).toBeInTheDocument();
  });

  it("renders NotFound for an id that is not a payee id", async () => {
    renderApp("/payee/BLUE-HARBOR");

    expect(await screen.findByText("There is no page at /payee/BLUE-HARBOR.")).toBeInTheDocument();
  });
});
