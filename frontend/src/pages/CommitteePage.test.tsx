import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Contribution } from "../api/client";
import type { ChartOption } from "../components/charts/echarts";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { allOptions } from "../test/echarts";
import {
  COMMITTEE_BUILDERS_PAC_1998,
  COMMITTEE_OKAFOR,
  contribution,
  EXPENDITURES,
  OPERATING_EXPENDITURES,
  PAYEE_IDS,
  problem,
} from "../test/fixtures";
import { figures } from "../test/reported";

const section = (name: string) => screen.getByRole("region", { name });
const rows = (name: string) => within(section(name)).getAllByRole("row").slice(1);
const cells = (row: HTMLElement) =>
  within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent);
const contributors = () => rows("Contributions received").map((row) => cells(row)[1]);

/** Five contributions to OKAFOR FOR MARYLAND, newest first, named A to E. */
const FIVE: Contribution[] = ["A", "B", "C", "D", "E"].map((name, index) =>
  contribution({
    source_record_id: String(index + 1),
    date: `2024-0${9 - index}-01`,
    amount: 100,
    contributor_name: name,
  }),
);

/**
 * The committee's contributions as three cursor pages, A–B, C–D and E; `failAt` answers that
 * cursor with `failStatus` instead, once (410 is a pruned build's). Records every cursor it is
 * asked for.
 */
function threePages({
  failAt,
  failStatus = 410,
}: { failAt?: string; failStatus?: 410 | 503 } = {}) {
  const PAGES: Record<string, { rows: Contribution[]; next: string | null }> = {
    "": { rows: FIVE.slice(0, 2), next: "p2" },
    p2: { rows: FIVE.slice(2, 4), next: "p3" },
    p3: { rows: FIVE.slice(4), next: null },
  };
  const cursors: string[] = [];
  let failed = false;
  const handler = http.get(
    "/v1/committees/{committee_id}/contributions",
    ({ request, response }) => {
      const cursor = new URL(request.url).searchParams.get("cursor") ?? "";
      cursors.push(cursor);
      if (cursor === failAt && !failed) {
        failed = true;
        return failStatus === 410
          ? response(410).json(
              problem(410, "Gone", "The data this cursor pages through has been replaced."),
            )
          : response(503).json(problem(503, "Service Unavailable", "Try again shortly."));
      }
      const page = PAGES[cursor];
      return response(200).json({ contributions: page.rows, next_cursor: page.next });
    },
  );
  return { handler, cursors };
}

describe("CommitteePage", () => {
  it("shows the conduit with no itemized receipts of its own", async () => {
    renderApp("/committee/C00401224");

    expect(await screen.findByRole("heading", { level: 1, name: "ACTBLUE" })).toBeInTheDocument();
    expect(screen.getByText("Conduit")).toBeInTheDocument();
    expect(
      screen.getByText("Hybrid PAC, nonqualified · Unauthorized · FEC C00401224"),
    ).toBeInTheDocument();
    expect(screen.getByText(/so a conduit receives nothing here\./)).toBeInTheDocument();
    expect(rows("Totals by cycle").map(cells)).toEqual([["2024", "$0", "$0", "$0", "$0"]]);
    expect(
      await within(section("Contributions received")).findByText(
        "No itemized contributions to this committee in 2024.",
      ),
    ).toBeInTheDocument();
    expect(document.title).toBe("ACTBLUE · fundlens");
  });

  it("shows the earmarked contribution at its recipient, badged with its conduit", async () => {
    renderApp("/committee/C00800103");

    expect(
      await screen.findByRole("heading", { level: 1, name: "OKAFOR FOR MARYLAND" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Conduit")).not.toBeInTheDocument();
    expect(rows("Totals by cycle").map(cells)).toEqual([
      ["2024", "$37,550", "$25,000", "$5,000", "$0"],
    ]);
    expect(rows("Totals by cycle")[0]).toHaveAttribute("id", "cycle-2024");

    const received = section("Contributions received");
    await within(received).findByText("REYES, CARMEN");
    // The authorized committee's gift is not this committee's.
    expect(contributors()).toEqual([
      "KOWALCZYK, PEGGY",
      "DUBOIS, RAYMOND",
      "YARBROUGH, ELENA",
      "REYES, CARMEN",
      "OKAFOR, DIANA",
    ]);
    const reyes = rows("Contributions received")[3];
    expect(cells(reyes)).toEqual([
      "2024-03-04",
      "REYES, CARMEN",
      "BALTIMORE CITY SCHOOLS",
      "$250",
      "via ActBlue",
    ]);
    expect(within(reyes).getByRole("link", { name: "via ActBlue" })).toHaveAttribute(
      "href",
      "/committee/C00401224",
    );
  });

  it("names the committee's kind and connected org, and lists its top recipients", async () => {
    renderApp("/committee/C00800202");

    expect(
      await screen.findByText("PAC, qualified · Lobbyist/registrant PAC · FEC C00800202"),
    ).toBeInTheDocument();
    expect(screen.getByText("Connected organization: BRICKLAYERS UNITED")).toBeInTheDocument();
    // Its $3,000 for CALLOWAY, spent and not given.
    expect(rows("Totals by cycle").map(cells)).toEqual([
      ["2024", "$4,050", "$0", "$0", "$17,500", "$3,000"],
    ]);
    expect(rows("Top recipients").map(cells)).toEqual([
      ["1", "CALLOWAY, RUTH", "Candidate", "$5,000"],
      ["2", "HARGROVE, ELLEN", "Candidate", "$5,000"],
      ["3", "OKAFOR, DIANA", "Candidate", "$5,000"],
      ["4", "DRISCOLL, PETER", "Candidate", "$2,500"],
    ]);
    expect(
      within(section("Top recipients")).getByRole("link", { name: "OKAFOR, DIANA" }),
    ).toHaveAttribute("href", "/candidate/S4MD00103");
    expect(
      within(section("Top donors")).getByText("No resolved individual donors in 2024."),
    ).toBeInTheDocument();
  });

  it("lists the cycle's top donors, linked to their donor pages", async () => {
    renderApp("/committee/C00800103");
    await screen.findByRole("region", { name: "Top donors" });

    expect(rows("Top donors").map(cells)).toEqual([
      ["1", "ZIMMERMANN, ZACH", "$3,300"],
      ["2", "DUBOIS, RAYMOND", "$2,500"],
      ["3", "GALLAGHER, TOMAS", "$500"],
    ]);
    expect(
      within(section("Top donors")).getByRole("link", { name: "DUBOIS, RAYMOND" }),
    ).toHaveAttribute("href", "/donor/236");
  });

  it("shows a super PAC's money from organizations beside its other receipts", async () => {
    renderApp("/committee/C00800201");

    expect(
      await screen.findByRole("heading", { level: 1, name: "MARYLAND FORWARD PAC" }),
    ).toBeInTheDocument();
    const totals = section("Totals by cycle");
    expect(
      within(totals)
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).toEqual([
      "Cycle",
      "From individuals",
      "From committees",
      "From organizations",
      "Refunds",
      "Self-funding",
      "To candidates",
      "Independent expenditures",
    ]);
    expect(rows("Totals by cycle").map(cells)).toEqual([
      ["2024", "$395,875", "$65,000", "$72,500", "−$3,200", "$0", "$0", "$670,000"],
    ]);
    expect(rows("Top organizations").map(cells)).toEqual([
      ["1", "CHESAPEAKE STEEL, INC.", "$72,500"],
    ]);
  });

  it("lists a super PAC's independent expenditures in a tab beside its contributions", async () => {
    renderApp("/committee/C00800201");
    const itemized = await screen.findByRole("region", { name: "Itemized" });

    // Contributions first; the expenditures are asked for only once their tab is opened.
    expect(within(itemized).getByRole("tab", { name: "Contributions received" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    fireEvent.click(within(itemized).getByRole("tab", { name: "Independent expenditures" }));
    const panel = await within(itemized).findByRole("tabpanel", {
      name: "Independent expenditures",
    });

    expect(
      await within(panel).findByText("6 independent expenditures, newest first"),
    ).toBeInTheDocument();
    expect(
      within(panel)
        .getAllByRole("row")
        .slice(1)
        .map(cells),
    ).toEqual([
      ["2024-10-28", "HARGROVE, ELLEN", "For", "$400,000"],
      ["2024-10-22", "OKAFOR, DIANA", "For", "$30,000"],
      ["2024-10-14", "DRISCOLL, PETER", "Against", "$15,000"],
      ["2024-10-12", "CALLOWAY, RUTH", "For", "$25,000"],
      ["2024-10-05", "WHITLOCK, GORDON", "Against", "$80,000"],
      ["2024-09-20", "OKAFOR, DIANA", "For", "$120,000"],
    ]);
    expect(within(panel).getAllByRole("link", { name: "WHITLOCK, GORDON" })[0]).toHaveAttribute(
      "href",
      "/candidate/S4MD00104",
    );
  });

  it("marks an independent expenditure from a 24- or 48-hour report an estimate", async () => {
    const [latest, ...rest] = EXPENDITURES.filter((row) => row.committee_id === "C00800201");
    renderApp("/committee/C00800201", {
      handlers: [
        http.get("/v1/committees/{committee_id}/independent-expenditures", ({ response }) =>
          response(200).json({
            expenditures: [{ ...latest, source_file: "ie_24_48" }, ...rest],
            next_cursor: null,
          }),
        ),
      ],
    });
    const itemized = await screen.findByRole("region", { name: "Itemized" });
    fireEvent.click(within(itemized).getByRole("tab", { name: "Independent expenditures" }));
    const panel = await within(itemized).findByRole("tabpanel", {
      name: "Independent expenditures",
    });
    await within(panel).findByText("6 independent expenditures, newest first");

    const [estimate, periodic] = within(panel).getAllByRole("row").slice(1);
    expect(cells(estimate)).toEqual([
      "2024-10-28",
      "HARGROVE, ELLEN",
      "For",
      "24/48-hour estimate$400,000",
    ]);
    expect(within(periodic).queryByText("24/48-hour estimate")).not.toBeInTheDocument();
  });

  it("lists a committee's contributions with no tabs when it made no independent expenditures", async () => {
    renderApp("/committee/C00800103");
    await screen.findByRole("region", { name: "Contributions received" });

    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    expect(
      within(section("Totals by cycle"))
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).not.toContain("Independent expenditures");
  });

  it("lists the top organizations in rank order, unlinked, after the top donors", async () => {
    renderApp("/committee/C00800105");
    const organizations = await screen.findByRole("region", { name: "Top organizations" });

    expect(rows("Top organizations").map(cells)).toEqual([
      ["1", "ACME CONCRETE LLC", "$5,000"],
      ["2", "ACME WIDGETS INC", "$3,000"],
    ]);
    // Organizations are grouped by name, not resolved: no page to link to (ADR-0011).
    expect(within(organizations).queryByRole("link", { name: /ACME/ })).not.toBeInTheDocument();
    expect(
      within(organizations).getByText(
        /Grouped by reported name; not resolved like individual donors\./,
      ),
    ).toBeInTheDocument();
    expect(within(organizations).getByRole("link", { name: "Methodology" })).toHaveAttribute(
      "href",
      "/methodology",
    );
    expect(
      section("Top donors").compareDocumentPosition(organizations) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("shows no organization money for a committee no organization gave to", async () => {
    renderApp("/committee/C00800103");
    await screen.findByRole("region", { name: "Top donors" });

    expect(screen.queryByRole("region", { name: "Top organizations" })).not.toBeInTheDocument();
    expect(
      within(section("Totals by cycle")).queryByRole("columnheader", {
        name: "From organizations",
      }),
    ).not.toBeInTheDocument();
  });

  it("shows a committee's refunds and its receipts before them, FEC's basis", async () => {
    renderApp("/committee/C00800201");
    await screen.findByRole("heading", { level: 1, name: "MARYLAND FORWARD PAC" });

    const totals = section("Totals by cycle");
    expect(within(totals).getByRole("columnheader", { name: "Refunds" })).toBeInTheDocument();
    // $395,875 from individuals and $72,500 from organizations, net of −$3,200 of refunds.
    expect(
      within(totals).getByText(
        "Refunds: what the committee refunded to givers, already taken out of “From individuals” and “From organizations”. FEC's itemized figure counts receipts before refunds: on that basis the committee received $471,575 from individuals and organizations in 2024.",
      ),
    ).toBeInTheDocument();
  });

  it("shows no refunds for a committee that made none", async () => {
    renderApp("/committee/C00800105");
    await screen.findByRole("heading", { level: 1, name: "PELL FOR LIBERTY" });

    const totals = section("Totals by cycle");
    expect(
      within(totals).queryByRole("columnheader", { name: "Refunds" }),
    ).not.toBeInTheDocument();
    expect(within(totals).queryByText(/Refunds:/)).not.toBeInTheDocument();
  });

  it("shows a hybrid PAC's non-contribution account beside its other receipts", async () => {
    renderApp("/committee/C00800204");

    expect(
      await screen.findByRole("heading", { level: 1, name: "TIDEWATER FUND" }),
    ).toBeInTheDocument();
    const totals = section("Totals by cycle");
    expect(
      within(totals)
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).toEqual([
      "Cycle",
      "From individuals",
      "From committees",
      "Non-contribution account",
      "Self-funding",
      "To candidates",
    ]);
    expect(rows("Totals by cycle").map(cells)).toEqual([
      ["2024", "$6,250", "$0", "$4,815,000", "$0", "$0"],
    ]);
    expect(
      within(totals).getByText(
        /Non-contribution account: what individuals and organizations give a hybrid PAC outside its contribution account/,
      ),
    ).toBeInTheDocument();
  });

  it("shows no non-contribution account for a committee without one", async () => {
    renderApp("/committee/C00800201");
    await screen.findByRole("heading", { level: 1, name: "MARYLAND FORWARD PAC" });

    const totals = section("Totals by cycle");
    expect(
      within(totals).queryByRole("columnheader", { name: "Non-contribution account" }),
    ).not.toBeInTheDocument();
    expect(within(totals).queryByText(/Non-contribution account/)).not.toBeInTheDocument();
  });

  it("says when the committee gave to no one in the cycle", async () => {
    renderApp("/committee/C00800103");

    expect(
      await within(await screen.findByRole("region", { name: "Top recipients" })).findByText(
        "No contributions to candidates or committees in 2024.",
      ),
    ).toBeInTheDocument();
  });

  it("walks three cursor pages with Load more, appending each without duplicates", async () => {
    const { handler, cursors } = threePages();
    renderApp("/committee/C00800103", { handlers: [handler] });

    await within(await screen.findByRole("region", { name: "Contributions received" })).findByText(
      "A",
    );
    expect(contributors()).toEqual(["A", "B"]);

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    await screen.findByText("D");
    expect(contributors()).toEqual(["A", "B", "C", "D"]);

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    await screen.findByText("E");
    expect(contributors()).toEqual(["A", "B", "C", "D", "E"]);
    expect(screen.getByText("5 contributions, newest first")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();

    expect(cursors).toEqual(["", "p2", "p3"]);
  });

  it("keeps the rows when a later page fails, and starts again from the first", async () => {
    const { handler, cursors } = threePages({ failAt: "p2" });
    renderApp("/committee/C00800103", { handlers: [handler] });
    await screen.findByText("B");

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Gone");
    expect(alert).toHaveTextContent("The data this cursor pages through has been replaced.");
    expect(contributors()).toEqual(["A", "B"]);

    fireEvent.click(within(alert).getByRole("button", { name: "Start again" }));
    await screen.findByRole("button", { name: "Load more" });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(contributors()).toEqual(["A", "B"]);
    expect(cursors).toEqual(["", "p2", ""]);
  });

  it("asks for a page that failed for another reason again, keeping its place", async () => {
    const { handler, cursors } = threePages({ failAt: "p2", failStatus: 503 });
    renderApp("/committee/C00800103", { handlers: [handler] });
    await screen.findByText("B");

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    const alert = await screen.findByRole("alert");
    fireEvent.click(within(alert).getByRole("button", { name: "Try again" }));

    await screen.findByText("D");
    expect(contributors()).toEqual(["A", "B", "C", "D"]);
    expect(cursors).toEqual(["", "p2", "p2"]);
  });

  it("shows the cycle's reported totals beside fundlens's itemized total, with its coverage", async () => {
    renderApp("/committee/C00800103");
    const reported = await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(
      within(reported).getByText(/Reporting period 2023-01-01 to 2024-12-31 · source/),
    ).toHaveTextContent("committee_summary");
    expect(figures(reported)).toEqual([
      ["Raised", "$117,000"],
      ["Spent", "$87,700"],
      ["Cash on hand", "$54,300"],
      ["Debts", "$3,000"],
      ["Loans from the candidate", "$0"],
      ["Other loans", "$0"],
      ["Unitemized from individuals", "$8,450"],
      ["Itemized from individuals", "$38,550"],
      ["Itemized by fundlens", "$38,550"],
    ]);
    expect(
      within(reported).getByText(
        /fundlens itemizes 100\.0% of the itemized individual money this committee reported\./,
      ),
    ).toBeInTheDocument();
    expect(within(reported).getByRole("link", { name: "Methodology" })).toHaveAttribute(
      "href",
      "/methodology",
    );
  });

  it("says why a conduit has no coverage", async () => {
    renderApp("/committee/C00401224");
    const reported = await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(within(reported).queryByText(/fundlens itemizes/)).toBeNull();
    expect(
      within(reported).getByText(/No coverage for a conduit: its reported itemized figure/),
    ).toBeInTheDocument();
  });

  it("says when FEC's files have no reported totals for the committee", async () => {
    renderApp("/committee/C00800103", {
      handlers: [
        http.get("/v1/committees/{committee_id}", ({ response }) =>
          response(200).json({
            ...COMMITTEE_OKAFOR,
            cycles: [{ ...COMMITTEE_OKAFOR.cycles[0], reported: null, coverage: null }],
          }),
        ),
      ],
    });
    const reported = await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(reported).toHaveTextContent(
      "FEC's files have no reported totals for this committee in 2024.",
    );
    expect(within(reported).queryByRole("term")).toBeNull();
  });

  it("shows a pre-2008 committee's reported totals with what FEC's files lack as not reported", async () => {
    renderApp("/committee/C00298003", {
      handlers: [
        http.get("/v1/committees/{committee_id}", ({ response }) =>
          response(200).json(COMMITTEE_BUILDERS_PAC_1998),
        ),
      ],
    });
    const reported = await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(within(reported).getByText(/Reporting period to 1998-12-31 · source/)).toHaveTextContent(
      "webk",
    );
    expect(figures(reported)).toEqual([
      ["Raised", "$6,000"],
      ["Spent", "$2,500"],
      ["Cash on hand", "$7,500"],
      ["Debts", "$0"],
      ["Loans from the candidate", "$0"],
      ["Other loans", "$0"],
      ["Unitemized from individuals", "not reported"],
      ["Itemized from individuals", "not reported"],
      ["Itemized by fundlens", "$0"],
    ]);
    expect(within(reported).queryByText(/fundlens itemizes/)).toBeNull();
    expect(
      within(reported).getByText(
        "No coverage: FEC's figures before 2008 do not split itemized money from unitemized.",
      ),
    ).toBeInTheDocument();
  });

  it("says when there is no such committee", async () => {
    renderApp("/committee/C00000000");

    expect(
      await screen.findByRole("heading", { level: 1, name: "No committee C00000000" }),
    ).toBeInTheDocument();
  });
});

/** The last option set on the spending-by-category chart: the page also draws its cycle totals. */
function spendingChart(): ChartOption {
  const option = allOptions()
    .filter((set) =>
      (set.series as { name?: string }[] | undefined)?.some((series) => series.name === "Spending"),
    )
    .at(-1);
  if (!option) throw new Error("No spending chart was drawn");
  return option;
}

/** `/expenditures` answering from the fixture, recording each request's query string. */
function recordedExpenditures() {
  const queries: URLSearchParams[] = [];
  const handler = http.get("/v1/committees/{committee_id}/expenditures", ({ request }) => {
    queries.push(new URL(request.url).searchParams);
    // Passed on to the fixture API's handler, which answers it.
    return undefined;
  });
  return { handler, queries };
}

describe("CommitteePage spending", () => {
  it("shows the cycle's spending total, its categories most first, and its top payees", async () => {
    renderApp("/committee/C00800103");
    const spending = await screen.findByRole("region", { name: "Spending" });

    expect(within(spending).getByText("$11,223")).toBeInTheDocument();
    expect(spendingChart().yAxis).toMatchObject({
      inverse: true,
      data: ["Consulting", "Credit card bills", "Legal and compliance", "Other", "Transfers and fees"],
    });
    expect(spendingChart().series).toMatchObject([
      { type: "bar", name: "Spending", data: [7500, 2500, 750, 350, 123.45] },
    ]);
    // The categories add up to the total, as gold's committee_spending_category rows do.
    const cycle = COMMITTEE_OKAFOR.cycles[0];
    expect(cycle.spending_by_category.reduce((sum, row) => sum + row.amount, 0)).toBeCloseTo(
      cycle.total_operating_expenditures!,
    );

    expect(rows("Top payees").map(cells)).toEqual([
      ["1", "BLUE HARBOR STRATEGIES LLC", "$7,500"],
      ["2", "AMERICAN EXPRESS", "$1,250"],
      ["3", "FIRST MARINER CARD SERVICES", "$1,250"],
      ["4", "CAPITOL COMPLIANCE GROUP", "$750"],
      ["5", "ACTBLUE", "$123"],
    ]);
    expect(
      within(section("Top payees")).getByRole("link", { name: "BLUE HARBOR STRATEGIES LLC" }),
    ).toHaveAttribute("href", `/payee/${PAYEE_IDS.blueHarbor}`);
  });

  it("shows a payee with no page unlinked", async () => {
    const shown = COMMITTEE_OKAFOR.cycles[0];
    renderApp("/committee/C00800103", {
      handlers: [
        http.get("/v1/committees/{committee_id}", ({ response }) =>
          response(200).json({
            ...COMMITTEE_OKAFOR,
            cycles: [
              {
                ...shown,
                top_payees: [
                  {
                    rank: 1,
                    payee_key: "PETTY CASH",
                    payee_id: null,
                    name: "PETTY CASH",
                    amount: 200,
                  },
                ],
              },
            ],
          }),
        ),
      ],
    });
    await screen.findByRole("region", { name: "Top payees" });

    expect(rows("Top payees").map(cells)).toEqual([["1", "PETTY CASH", "$200"]]);
    expect(
      within(within(section("Top payees")).getByRole("table")).queryByRole("link"),
    ).not.toBeInTheDocument();
  });

  it("lists every payment newest first, each card bill's charges under it and not counted", async () => {
    renderApp("/committee/C00800103");
    const itemized = await screen.findByRole("region", { name: "Itemized spending" });

    expect(await within(itemized).findByText("7 payments, newest first")).toBeInTheDocument();
    const CARD = ["CREDIT CARD PAYMENT", "Credit card bills"];
    const [IN_KIND, LEGAL] = ["In-kind", "Legal and compliance"];
    expect(rows("Itemized spending").map(cells)).toEqual([
      ["2024-06-30", "ACTBLUE", "PROCESSING FEES", "Transfers and fees", "$123", ""],
      ["2024-06-27", "FIRST MARINER CARD SERVICES", ...CARD, "$750", ""],
      ["2024-06-03", "↳ SKYLINE AIR", "AIRFARE", "Travel", "$750", "Not counted"],
      ["2024-05-11", "VELASQUEZ, TERESA", "IN-KIND CONTRIBUTION: CATERING", "Other", "$350", IN_KIND],
      ["2024-04-30", "BLUE HARBOR STRATEGIES LLC", "STRATEGY CONSULTING", "Consulting", "$7,500", ""],
      ["2024-03-29", "CAPITOL COMPLIANCE GROUP", "COMPLIANCE CONSULTING", LEGAL, "$750", ""],
      ["2024-03-28", "FIRST MARINER CARD SERVICES", ...CARD, "$500", ""],
      ["2024-03-02", "↳ PATAPSCO INN", "LODGING", "Travel", "$500", "Not counted"],
      ["2024-03-05", "AMERICAN EXPRESS", ...CARD, "$1,250", ""],
      ["2024-02-12", "↳ SKYLINE AIR", "AIRFARE", "Travel", "$413", "Not counted"],
      ["2024-02-13", "↳ PATAPSCO INN", "LODGING", "Travel", "$838", "Not counted"],
    ]);
    // A payee key with a page is linked, sub-items' too; a person and a charge-only name are not.
    expect(within(itemized).getAllByRole("link", { name: "SKYLINE AIR" })[0]).toHaveAttribute(
      "href",
      `/payee/${PAYEE_IDS.skylineAir}`,
    );
    expect(within(itemized).queryByRole("link", { name: "PATAPSCO INN" })).not.toBeInTheDocument();
    expect(
      within(itemized).queryByRole("link", { name: "VELASQUEZ, TERESA" }),
    ).not.toBeInTheDocument();
    // The counted payments add up to the committee's total; no charge is added to it.
    const counted = OPERATING_EXPENDITURES.filter((row) => row.counted);
    expect(counted.reduce((sum, row) => sum + row.amount!, 0)).toBeCloseTo(
      COMMITTEE_OKAFOR.cycles[0].total_operating_expenditures!,
    );
  });

  it("filters the itemized spending by a category the committee spent in", async () => {
    const { handler, queries } = recordedExpenditures();
    renderApp("/committee/C00800103", { handlers: [handler] });
    const itemized = await screen.findByRole("region", { name: "Itemized spending" });
    await within(itemized).findByText("7 payments, newest first");
    const category = within(itemized).getByRole("combobox", { name: "Category" });

    expect(
      within(category)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual([
      "All categories",
      "Consulting",
      "Legal and compliance",
      "Transfers and fees",
      "Credit card bills",
      "Other",
    ]);
    fireEvent.change(category, { target: { value: "credit_card" } });

    expect(await within(itemized).findByText("3 payments, newest first")).toBeInTheDocument();
    expect(rows("Itemized spending").map((row) => cells(row)[1])).toEqual([
      "FIRST MARINER CARD SERVICES",
      "↳ SKYLINE AIR",
      "FIRST MARINER CARD SERVICES",
      "↳ PATAPSCO INN",
      "AMERICAN EXPRESS",
      "↳ SKYLINE AIR",
      "↳ PATAPSCO INN",
    ]);
    expect(queries.at(-1)?.get("category")).toBe("credit_card");
    expect(queries[0].get("category")).toBeNull();
  });

  it("orders the itemized spending largest first", async () => {
    const { handler, queries } = recordedExpenditures();
    renderApp("/committee/C00800103", { handlers: [handler] });
    const itemized = await screen.findByRole("region", { name: "Itemized spending" });
    await within(itemized).findByText("7 payments, newest first");

    fireEvent.click(within(itemized).getByRole("radio", { name: "Largest first" }));

    expect(await within(itemized).findByText("7 payments, largest first")).toBeInTheDocument();
    expect(cells(rows("Itemized spending")[0])[1]).toBe("BLUE HARBOR STRATEGIES LLC");
    expect(queries.map((query) => query.get("sort"))).toEqual(["date", "amount"]);
  });

  it("says spending is not available for a cycle with no counted payment, and lists none", async () => {
    renderApp("/committee/C00401224");
    const spending = await screen.findByRole("region", { name: "Spending" });

    expect(within(spending).getByText("not available")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Itemized spending" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Top payees" })).not.toBeInTheDocument();
  });
});
