import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { lastOption } from "../test/echarts";
import { CANDIDATE_OKAFOR } from "../test/fixtures";

const section = (name: string) => screen.getByRole("region", { name });
const rows = (name: string) => within(section(name)).getAllByRole("row").slice(1);
const cells = (row: HTMLElement) =>
  within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent);

/** OKAFOR in 2024 and 2022, answering each contributions request with one row naming its cycle. */
function twoCycles() {
  const requested: string[] = [];
  const handlers = [
    http.get("/v1/candidates/{candidate_id}", ({ response }) =>
      response(200).json({
        ...CANDIDATE_OKAFOR,
        cycles: [
          ...CANDIDATE_OKAFOR.cycles,
          { ...CANDIDATE_OKAFOR.cycles[0], cycle: 2022, race_id: null, race_slug: null },
        ],
      }),
    ),
    http.get("/v1/candidates/{candidate_id}/contributions", ({ request, response }) => {
      const cycle = new URL(request.url).searchParams.get("cycle") ?? "";
      requested.push(cycle);
      return response(200).json({
        contributions: [
          {
            cycle: Number(cycle),
            source_record_id: cycle,
            date: `${cycle}-06-01`,
            amount: 100,
            recipient_committee_id: "C00800103",
            candidate_id: "S4MD00103",
            contributor_name: `DONOR OF ${cycle}`,
            contributor_city: null,
            contributor_state: null,
            contributor_zip: null,
            contributor_employer: null,
            contributor_occupation: null,
            entity_type: "IND",
            transaction_type: "15",
            report_type: null,
            memo_text: null,
            conduit_committee_id: null,
            is_self_funding: false,
            image_num: null,
          },
        ],
        next_cursor: null,
      });
    }),
  ];
  return { handlers, requested };
}

describe("CandidatePage", () => {
  it("shows the candidate's header and per-cycle totals as expected.yaml has them", async () => {
    renderApp("/candidate/S4MD00103");

    expect(
      await screen.findByRole("heading", { level: 1, name: "OKAFOR, DIANA" }),
    ).toBeInTheDocument();
    expect(screen.getByText("DEM")).toBeInTheDocument();
    expect(screen.getByText("Senate · Maryland · FEC S4MD00103")).toBeInTheDocument();
    expect(document.title).toBe("OKAFOR, DIANA · fundlens");

    expect(rows("Totals by cycle").map(cells)).toEqual([
      ["2024", "Senate · Maryland", "$49,700", "$5,000", "$5,000", "$59,700"],
    ]);
    expect(rows("Totals by cycle")[0]).toHaveAttribute("id", "cycle-2024");
    expect(
      within(section("Totals by cycle")).getByRole("link", { name: "Senate · Maryland" }),
    ).toHaveAttribute("href", "/race/2024/senate/MD");
  });

  it("draws the totals by cycle as stacked bars", async () => {
    renderApp("/candidate/S4MD00103");
    await screen.findByRole("region", { name: "Totals by cycle" });

    const option = lastOption();
    expect(option.xAxis).toMatchObject({ data: ["2024"] });
    expect(option.series).toMatchObject([
      { type: "bar", name: "From individuals", stack: "total", data: [49700] },
      { type: "bar", name: "From committees", stack: "total", data: [5000] },
      { type: "bar", name: "Self-funding", stack: "total", data: [5000] },
    ]);
  });

  it("lists the cycle's itemized contributions, newest first, with their badges", async () => {
    renderApp("/candidate/S4MD00103");

    await within(await screen.findByRole("region", { name: "Contributions" })).findByText(
      "KOWALCZYK, PEGGY",
    );
    expect(rows("Contributions").map(cells)).toEqual([
      ["2024-09-30", "KOWALCZYK, PEGGY", "RETIRED", "$750", ""],
      ["2024-09-09", "DUBOIS, RAYMOND", "ASTRA EXPLORATION TECHNOLOGIES", "$1,500", ""],
      ["2024-06-02", "YARBROUGH, ELENA", "NORTHFIELD SOFTWARE", "$250", "via ActBlue"],
      ["2024-03-04", "REYES, CARMEN", "BALTIMORE CITY SCHOOLS", "$250", "via ActBlue"],
      ["2023-12-01", "OKAFOR, DIANA", "STATE OF MARYLAND", "$5,000", "Self-funding"],
      ["2023-01-24", "ZIMMERMANN, LUIS", "NOT EMPLOYED", "$3,300", ""],
    ]);
    const contributions = section("Contributions");
    expect(within(contributions).getByText("6 contributions, newest first")).toBeVisible();
    expect(within(contributions).queryByRole("button", { name: "Load more" })).toBeNull();
    expect(within(section("Top donors")).getByText("Top donors are coming.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "In 2024" })).toBeInTheDocument();
  });

  it("shows the newest cycle's contributions by default", async () => {
    const { handlers, requested } = twoCycles();
    renderApp("/candidate/S4MD00103", { handlers });

    expect(await screen.findByText("DONOR OF 2024")).toBeInTheDocument();
    expect(requested).toEqual(["2024"]);
  });

  it("follows the cycle switcher's hash to that cycle's row and contributions", async () => {
    const scrolled = vi.spyOn(HTMLElement.prototype, "scrollIntoView");
    const { handlers, requested } = twoCycles();
    renderApp("/candidate/S4MD00103#cycle-2022", { handlers });

    expect(await screen.findByText("DONOR OF 2022")).toBeInTheDocument();
    expect(requested).toEqual(["2022"]);
    expect(screen.getByRole("heading", { level: 2, name: "In 2022" })).toBeInTheDocument();
    expect(scrolled.mock.contexts.map((element) => (element as HTMLElement).id)).toContain(
      "cycle-2022",
    );
    expect(rows("Totals by cycle")[1]).toHaveAttribute("id", "cycle-2022");
  });

  it("picks another cycle into the URL", async () => {
    const { handlers, requested } = twoCycles();
    const { router } = renderApp("/candidate/S4MD00103", { handlers });
    await screen.findByText("DONOR OF 2024");

    fireEvent.click(screen.getByRole("combobox", { name: "Cycle shown" }));
    fireEvent.click(await screen.findByRole("option", { name: "2022" }));

    expect(await screen.findByText("DONOR OF 2022")).toBeInTheDocument();
    expect(router.state.location.search).toBe("?cycle=2022");
    expect(requested).toEqual(["2024", "2022"]);
    // A cycle the candidate does not have falls back to the newest.
    await act(() => router.navigate("/candidate/S4MD00103?cycle=1990"));
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 2, name: "In 2024" })).toBeInTheDocument(),
    );
  });

  it("says when there is no such candidate", async () => {
    renderApp("/candidate/H0XX00000");

    expect(
      await screen.findByRole("heading", { level: 1, name: "No candidate H0XX00000" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to fundlens" })).toHaveAttribute("href", "/");
  });
});
