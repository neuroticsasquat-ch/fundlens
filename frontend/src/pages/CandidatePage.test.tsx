import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { CandidateCycle, LeadershipPac } from "../api/client";
import type { ChartOption } from "../components/charts/echarts";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { allOptions } from "../test/echarts";
import { CANDIDATE_CALDER_1998, CANDIDATE_OKAFOR } from "../test/fixtures";
import { figures } from "../test/reported";

const section = (name: string) => screen.getByRole("region", { name });
const rows = (name: string) => within(section(name)).getAllByRole("row").slice(1);
const cells = (row: HTMLElement) =>
  within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent);

/** OKAFOR with her 2024 cycle changed by `cycle`. */
function okafor(cycle: Partial<CandidateCycle>) {
  return [
    http.get("/v1/candidates/{candidate_id}", ({ response }) =>
      response(200).json({
        ...CANDIDATE_OKAFOR,
        cycles: [{ ...CANDIDATE_OKAFOR.cycles[0], ...cycle }],
      }),
    ),
  ];
}

/** The last option set on the chart one of whose series is `name`: a page draws two. */
function chart(name: string): ChartOption {
  const option = allOptions()
    .filter((set) =>
      (set.series as { name?: string }[] | undefined)?.some((series) => series.name === name),
    )
    .at(-1);
  if (!option) throw new Error(`No chart with a ${name} series was drawn`);
  return option;
}

const giftSizes = () => chart("Gift sizes");

/** The tooltip the gift-size chart shows over its `index`th bar. */
const giftSizeTooltip = (index: number) =>
  (giftSizes().tooltip as { formatter: (params: object) => string }).formatter({
    dataIndex: index,
  });

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
            donor_id: null,
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
      [
        "2024",
        "Senate · Maryland",
        "$49,700",
        "$5,000",
        "$19,500",
        "$5,000",
        "$79,200",
        "$150,000",
        "$45,000",
      ],
    ]);
    expect(
      within(section("Totals by cycle"))
        .getAllByRole("columnheader")
        .map((header) => header.textContent)
        .slice(-2),
    ).toEqual(["Independent expenditures for", "Independent expenditures against"]);
    expect(rows("Totals by cycle")[0]).toHaveAttribute("id", "cycle-2024");
    expect(
      within(section("Totals by cycle")).getByRole("link", { name: "Senate · Maryland" }),
    ).toHaveAttribute("href", "/race/2024/senate/MD");
  });

  it("draws the totals by cycle as stacked bars", async () => {
    renderApp("/candidate/S4MD00103");
    await screen.findByRole("region", { name: "Totals by cycle" });

    const option = chart("From individuals");
    expect(option.xAxis).toMatchObject({ data: ["2024"] });
    expect(option.series).toMatchObject([
      { type: "bar", name: "From individuals", stack: "total", data: [49700] },
      { type: "bar", name: "From committees", stack: "total", data: [5000] },
      { type: "bar", name: "Via joint fundraising", stack: "total", data: [19500] },
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
    expect(
      within(contributions).getByRole("link", { name: "DUBOIS, RAYMOND" }),
    ).toHaveAttribute("href", "/donor/236");
    // A contribution no resolution has named a donor for is not a link.
    expect(within(contributions).queryByRole("link", { name: "KOWALCZYK, PEGGY" })).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "In 2024" })).toBeInTheDocument();
  });

  it("lists the cycle's top donors without the candidate's own money", async () => {
    renderApp("/candidate/S4MD00103");
    await screen.findByRole("region", { name: "Top donors" });

    expect(rows("Top donors").map(cells)).toEqual([
      ["1", "ZIMMERMANN, ZACH", "$3,300"],
      ["2", "DUBOIS, RAYMOND", "$2,500"],
      ["3", "GALLAGHER, TOMAS", "$500"],
    ]);
    expect(
      within(section("Top donors")).getByRole("link", { name: "ZIMMERMANN, ZACH" }),
    ).toHaveAttribute("href", "/donor/518");
    expect(within(section("Top donors")).queryByText("OKAFOR, DIANA")).toBeNull();
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

  it("shows the cycle's reported totals beside fundlens's itemized total, with its coverage", async () => {
    renderApp("/candidate/S4MD00103");
    const reported = await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(
      within(reported).getByText(/Reporting period 2023-01-01 to 2024-12-31 · source/),
    ).toHaveTextContent("committee_summary");
    expect(figures(reported)).toEqual([
      ["Raised", "$131,000"],
      ["Spent", "$98,900"],
      ["Cash on hand", "$57,100"],
      ["Debts", "$3,000"],
      ["Loans from the candidate", "$0"],
      ["Other loans", "$0"],
      ["Unitemized from individuals", "$10,300"],
      ["Itemized from individuals", "$50,700"],
      ["Itemized by fundlens", "$50,700"],
    ]);
    expect(
      within(reported).getByText(
        /fundlens itemizes 100\.0% of the itemized individual money this campaign reported\./,
      ),
    ).toBeInTheDocument();
    expect(within(reported).getByRole("link", { name: "Methodology" })).toHaveAttribute(
      "href",
      "/methodology",
    );
    // Reported totals are never added to the itemized ones.
    expect(cells(rows("Totals by cycle")[0])[6]).toBe("$79,200");
  });

  it("shows a coverage over 100% as it is", async () => {
    renderApp("/candidate/S4MD00103", { handlers: okafor({ coverage: 1.1234 }) });

    expect(
      await screen.findByText(/fundlens itemizes 112\.3% of the itemized individual money/),
    ).toBeInTheDocument();
  });

  it("says why a candidate with individuals' money but no credited committee has no reported totals", async () => {
    // A handoff's first candidate: no credited committee, so no reported totals, itemized total
    // or unitemized lump, beside the five itemized buckets of their own donors (spec §4.3, §4.6).
    renderApp("/candidate/S4MD00103", {
      handlers: okafor({
        reported: null,
        itemized_total: null,
        coverage: null,
        gift_sizes: CANDIDATE_CALDER_1998.cycles[0].gift_sizes,
      }),
    });
    const reported = await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(reported).toHaveTextContent(
      "No committee's reported totals are credited to this candidate in 2024. A campaign " +
        "committee handed to another candidate during the cycle counts whole as the second " +
        "candidate's, what it raised before the handoff included.",
    );
    expect(within(reported).queryByRole("term")).toBeNull();
    expect(giftSizes().xAxis).toMatchObject({
      data: ["$200 or less", "$200–$500", "$500–$1,000", "$1,000–$2,000", "$2,000 or more"],
    });
  });

  it("names no handoff for a candidate with no credited committee and no money of their own", async () => {
    renderApp("/candidate/S4MD00103", {
      handlers: okafor({
        reported: null,
        itemized_total: null,
        coverage: null,
        total_individual: 0,
        gift_sizes: [],
      }),
    });
    const reported = await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(reported).toHaveTextContent(
      "No committee's reported totals are credited to this candidate in 2024.",
    );
    expect(reported).not.toHaveTextContent(/handed/);
    expect(within(section("Gift sizes")).getByText("No gift sizes in 2024.")).toBeInTheDocument();
  });

  it("says why a 2008-on cycle with no reported itemized money has no coverage", async () => {
    const { reported } = CANDIDATE_OKAFOR.cycles[0];
    renderApp("/candidate/S4MD00103", {
      handlers: okafor({ reported: { ...reported!, individual_itemized: 0 }, coverage: null }),
    });

    expect(
      await screen.findByText(
        "No coverage: this campaign reported no itemized individual money to set it against.",
      ),
    ).toBeInTheDocument();
  });

  it("notes a converted committee counted in the candidate's reported totals", async () => {
    renderApp("/candidate/S4MD00103", {
      handlers: okafor({ reported_includes_converted_committee: true }),
    });

    expect(
      await screen.findByText(/Includes a campaign committee that became a PAC, counted whole/),
    ).toBeInTheDocument();
  });

  it("says nothing of a converted committee where none is counted", async () => {
    renderApp("/candidate/S4MD00103");
    await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(screen.queryByText(/became a PAC/)).toBeNull();
  });

  it("draws the unitemized lump as its own bar, and says why no donor's bucket is drawn", async () => {
    renderApp("/candidate/S4MD00103");
    const sizes = await screen.findByRole("region", { name: "Gift sizes" });

    expect(giftSizes().xAxis).toMatchObject({ data: ["Unitemized"] });
    expect(giftSizes().series).toMatchObject([{ type: "bar", data: [{ value: 10300 }] }]);
    expect(giftSizeTooltip(0)).toBe("Unitemized: $10,300, reported as one lump");
    expect(
      within(sizes).getByText(
        "No donors are resolved for 2024 yet, so only the unitemized lump is shown.",
      ),
    ).toBeInTheDocument();
  });

  it("charts every gift-size bucket in bucket order, unitemized in a colour of its own", async () => {
    const buckets: CandidateCycle["gift_sizes"] = [
      { bucket: "2000_or_more", amount: 6600, donors: 2 },
      { bucket: "unitemized", amount: 10300, donors: null },
      { bucket: "200_or_less", amount: 400, donors: 3 },
      { bucket: "under_500", amount: 750, donors: 2 },
      { bucket: "under_1000", amount: 500, donors: 1 },
      { bucket: "under_2000", amount: 1500, donors: 1 },
    ];
    renderApp("/candidate/S4MD00103", { handlers: okafor({ gift_sizes: buckets }) });
    const sizes = await screen.findByRole("region", { name: "Gift sizes" });

    expect(giftSizes().xAxis).toMatchObject({
      data: [
        "Unitemized",
        "$200 or less",
        "$200–$500",
        "$500–$1,000",
        "$1,000–$2,000",
        "$2,000 or more",
      ],
    });
    const [bar] = giftSizes().series as { data: { value: number; itemStyle: { color: string } }[] }[];
    expect(bar.data.map((point) => point.value)).toEqual([10300, 400, 750, 500, 1500, 6600]);
    const colours = new Set(bar.data.slice(1).map((point) => point.itemStyle.color));
    expect(colours.size).toBe(1);
    expect(colours.has(bar.data[0].itemStyle.color)).toBe(false);
    expect(giftSizeTooltip(1)).toBe("$200 or less: $400 from 3 donors");
    expect(giftSizeTooltip(4)).toBe("$1,000–$2,000: $1,500 from 1 donor");
    expect(within(sizes).queryByText(/No donors are resolved/)).toBeNull();
  });

  it("shows a pre-2008 cycle's reported totals with what FEC's files lack as not reported", async () => {
    renderApp("/candidate/H8MD05201", {
      handlers: [
        http.get("/v1/candidates/{candidate_id}", ({ response }) =>
          response(200).json(CANDIDATE_CALDER_1998),
        ),
      ],
    });
    const reported = await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(within(reported).getByText(/Reporting period to 1998-12-31 · source/)).toHaveTextContent(
      "weball",
    );
    expect(figures(reported)).toEqual([
      ["Raised", "$9,500"],
      ["Spent", "$8,200"],
      ["Cash on hand", "$1,300"],
      ["Debts", "$0"],
      ["Loans from the candidate", "$0"],
      ["Other loans", "$0"],
      ["Unitemized from individuals", "not reported"],
      ["Itemized from individuals", "not reported"],
      ["Itemized by fundlens", "$1,000"],
    ]);
    expect(within(reported).queryByText(/fundlens itemizes/)).toBeNull();
    expect(
      within(reported).getByText(
        "No coverage: FEC's figures before 2008 do not split itemized money from unitemized.",
      ),
    ).toBeInTheDocument();
    // The five itemized buckets, and no unitemized bar.
    expect(giftSizes().xAxis).toMatchObject({
      data: ["$200 or less", "$200–$500", "$500–$1,000", "$1,000–$2,000", "$2,000 or more"],
    });
  });

  it("says when there is no such candidate", async () => {
    renderApp("/candidate/H0XX00000");

    expect(
      await screen.findByRole("heading", { level: 1, name: "No candidate H0XX00000" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to fundlens" })).toHaveAttribute("href", "/");
  });

  it("shows the cycle's outside spending by kind and side, and says what each kind is", async () => {
    renderApp("/candidate/S4MD00103");
    const outside = await screen.findByRole("region", { name: "Outside spending in 2024" });

    expect(
      within(outside)
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).toEqual(["Kind", "For", "Against", "Neither side"]);
    // No kind is added to another, and an electioneering communication is on no side.
    expect(rows("Outside spending in 2024").map(cells)).toEqual([
      ["Independent expenditures", "$150,000", "$45,000", "—"],
      ["Communication costs", "$4,224", "$0", "—"],
      ["Electioneering communications", "—", "—", "$71,410"],
    ]);
    expect(
      within(outside).getByText(/^Electioneering communications: broadcast ads naming/),
    ).toBeInTheDocument();
    // Only the kinds she has are explained.
    expect(
      within(outside).queryByText(/^Party coordinated expenditures:/),
    ).not.toBeInTheDocument();
    expect(within(outside).getByRole("link", { name: "methodology" })).toHaveAttribute(
      "href",
      "/methodology",
    );
  });

  it("shows a party's coordinated expenditures as for the candidate, never against", async () => {
    renderApp("/candidate/S4MD00103", {
      handlers: okafor({
        outside_spending: {
          independent_expenditure: { support: 0, oppose: 0 },
          communication_cost: { support: 0, oppose: 0 },
          party_coordinated: 20000,
          electioneering_communication: null,
        },
      }),
    });
    await screen.findByRole("region", { name: "Outside spending in 2024" });

    expect(rows("Outside spending in 2024").map(cells)).toEqual([
      ["Party coordinated expenditures", "$20,000", "—", "—"],
    ]);
  });

  it("shows no outside spending for a candidate nobody spent anything on", async () => {
    renderApp("/candidate/S4MD00103", {
      handlers: okafor({
        ie_support: 0,
        ie_oppose: 0,
        outside_spending: {
          independent_expenditure: { support: 0, oppose: 0 },
          communication_cost: { support: 0, oppose: 0 },
          party_coordinated: 0,
          electioneering_communication: null,
        },
      }),
    });
    await screen.findByRole("region", { name: "Reported to the FEC" });

    expect(screen.queryByRole("region", { name: /^Outside spending/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/^Electioneering communications:/)).not.toBeInTheDocument();
  });
});

describe("CandidatePage leadership PACs", () => {
  /** OKAFOR, sponsoring `pacs`. */
  const sponsoring = (pacs: LeadershipPac[]) => [
    http.get("/v1/candidates/{candidate_id}", ({ response }) =>
      response(200).json({ ...CANDIDATE_OKAFOR, leadership_pacs: pacs }),
    ),
  ];

  it("links the PAC the candidate sponsors in the cycle shown, and says its money is not theirs", async () => {
    renderApp("/candidate/S4MD00103", {
      handlers: sponsoring([
        { committee_id: "C00800114", name: "CALLOWAY LEADERSHIP FUND", cycles: [2024] },
      ]),
    });
    await screen.findByRole("heading", { level: 1, name: "OKAFOR, DIANA" });

    expect(screen.getByText(/^Leadership PAC:/)).toHaveTextContent(
      "Leadership PAC: CALLOWAY LEADERSHIP FUND (2024)",
    );
    expect(screen.getByRole("link", { name: "CALLOWAY LEADERSHIP FUND" })).toHaveAttribute(
      "href",
      "/committee/C00800114?cycle=2024",
    );
    expect(
      screen.getByText("A PAC this member sponsors; its money is not counted as the campaign's."),
    ).toBeInTheDocument();
  });

  it("lists every PAC the candidate sponsors, each with its cycles and opened in its latest", async () => {
    renderApp("/candidate/S4MD00103", {
      handlers: sponsoring([
        { committee_id: "C00800114", name: "CALLOWAY LEADERSHIP FUND", cycles: [2024, 2022] },
        { committee_id: "C00800117", name: null, cycles: [2020, 2018, 2012] },
      ]),
    });
    await screen.findByRole("heading", { level: 1, name: "OKAFOR, DIANA" });

    expect(screen.getByText(/^Leadership PACs:/)).toHaveTextContent(
      "Leadership PACs: CALLOWAY LEADERSHIP FUND (2022–2024); C00800117 (2012, 2018–2020)",
    );
    // Not theirs in 2024, the cycle shown: opened in 2020, when it last was.
    expect(screen.getByRole("link", { name: "C00800117" })).toHaveAttribute(
      "href",
      "/committee/C00800117?cycle=2020",
    );
    expect(
      screen.getByText("PACs this member sponsors; their money is not counted as the campaign's."),
    ).toBeInTheDocument();
  });

  it("names no leadership PAC for a candidate who sponsors none", async () => {
    renderApp("/candidate/S4MD00103");
    await screen.findByRole("heading", { level: 1, name: "OKAFOR, DIANA" });

    expect(screen.queryByText(/^Leadership PAC/)).toBeNull();
  });

  it("goes to the PAC's page, which links back to the sponsor's", async () => {
    renderApp("/candidate/H4MD05106", {
      handlers: [
        http.get("/v1/candidates/{candidate_id}", ({ response }) =>
          response(200).json({
            ...CANDIDATE_OKAFOR,
            candidate_id: "H4MD05106",
            name: "CALLOWAY, RUTH",
            leadership_pacs: [
              { committee_id: "C00800114", name: "CALLOWAY LEADERSHIP FUND", cycles: [2024] },
            ],
          }),
        ),
      ],
    });
    fireEvent.click(await screen.findByRole("link", { name: "CALLOWAY LEADERSHIP FUND" }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "CALLOWAY LEADERSHIP FUND" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CALLOWAY, RUTH" })).toHaveAttribute(
      "href",
      "/candidate/H4MD05106?cycle=2024",
    );
  });
});
