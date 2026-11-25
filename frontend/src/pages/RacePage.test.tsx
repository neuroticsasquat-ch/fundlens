import { DEFAULT_THEME } from "@mantine/core";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { OutsideSpending } from "../api/client";
import { http } from "../test/api";
import { allOptions, lastOption } from "../test/echarts";
import { renderApp } from "../test/app";
import { RACE_SENATE_MD } from "../test/fixtures";
import { matchMedia } from "../test/media";

const section = (name: string) => screen.getByRole("region", { name });
const rows = (name: string) => within(section(name)).getAllByRole("row").slice(1);
const cells = (row: HTMLElement) =>
  within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent);

/** No outside spending of any kind: a cycle with no electioneering row has `null`, never 0. */
const NO_OUTSIDE_SPENDING: OutsideSpending = {
  independent_expenditure: { support: 0, oppose: 0 },
  communication_cost: { support: 0, oppose: 0 },
  party_coordinated: 0,
  electioneering_communication: null,
};

/** Spending on a candidate that is independent expenditures alone. */
const independentOnly = (support: number, oppose: number): OutsideSpending => ({
  ...NO_OUTSIDE_SPENDING,
  independent_expenditure: { support, oppose },
});

describe("RacePage", () => {
  it("shows the race's header and every candidate's money, most first", async () => {
    renderApp("/race/2024/senate/MD");

    expect(
      await screen.findByRole("heading", { level: 1, name: "2024 Senate · Maryland" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "4 candidates · $91,975 from individuals · $10,000 from committees · $19,500 via joint fundraising",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Special")).not.toBeInTheDocument();
    expect(document.title).toBe("2024 Senate · Maryland · fundlens");

    expect(rows("Candidates").map(cells)).toEqual([
      [
        "WHITLOCK, GORDON",
        "REP",
        "Open",
        "$31,850",
        "$5,000",
        "$0",
        "$1,750,000",
        "$1,786,850",
        "$3,900",
        "$291,300",
      ],
      [
        "OKAFOR, DIANA",
        "DEM",
        "Open",
        "$49,700",
        "$5,000",
        "$19,500",
        "$5,000",
        "$79,200",
        "$12,223",
        "$57,100",
      ],
      [
        "BRANNIGAN, TESS",
        "DEM",
        "Open",
        "$7,175",
        "$0",
        "$0",
        "$0",
        "$7,175",
        "not available",
        "$1,900",
      ],
      [
        "PELL, MARCUS",
        "LIB",
        "Open",
        "$3,250",
        "$0",
        "$0",
        "$0",
        "$3,250",
        "not available",
        "$1,300",
      ],
    ]);
    // Each kind on its own, never one figure for them all.
    expect(
      screen.getByText(
        "Outside spending: independent expenditures $150,000 for candidates and $125,000 against · " +
          "communication costs $4,224 for candidates and $2,400 against · " +
          "party coordinated expenditures $20,000 · electioneering communications $101,319",
      ),
    ).toBeInTheDocument();
    expect(
      within(section("Candidates"))
        .getAllByRole("columnheader")
        .map((header) => header.textContent)
        .slice(3),
    ).toEqual([
      "From individuals",
      "From committees",
      "Via joint fundraising",
      "Self-funding",
      "Total ▼",
      "Spending",
      "Cash on hand",
    ]);
    const candidates = section("Candidates");
    expect(within(candidates).getByRole("columnheader", { name: /Total/ })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    expect(within(candidates).getByRole("link", { name: "PELL, MARCUS" })).toHaveAttribute(
      "href",
      "/candidate/S4MD00105",
    );
  });

  it("has a fixture whose candidates add up to the race's totals", () => {
    const sum = (key: "total_individual" | "total_committee" | "total_jfc_transfers") =>
      RACE_SENATE_MD.candidates.reduce((total, candidate) => total + candidate[key], 0);
    expect(sum("total_individual")).toBe(RACE_SENATE_MD.total_individual);
    expect(sum("total_committee")).toBe(RACE_SENATE_MD.total_committee);
    expect(sum("total_jfc_transfers")).toBe(RACE_SENATE_MD.total_jfc_transfers);
  });

  it("says nothing of joint fundraising in a race that had none", async () => {
    const candidates = RACE_SENATE_MD.candidates.map((candidate) => ({
      ...candidate,
      total_jfc_transfers: 0,
    }));
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({ ...RACE_SENATE_MD, total_jfc_transfers: 0, candidates }),
        ),
      ],
    });

    expect(
      await screen.findByText("4 candidates · $91,975 from individuals · $10,000 from committees"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/via joint fundraising/)).not.toBeInTheDocument();
  });

  it("says nothing of outside spending in a race that had none", async () => {
    const candidates = RACE_SENATE_MD.candidates.map((candidate) => ({
      ...candidate,
      ie_support: 0,
      ie_oppose: 0,
      outside_spending: NO_OUTSIDE_SPENDING,
    }));
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({
            ...RACE_SENATE_MD,
            ie_support: 0,
            ie_oppose: 0,
            outside_spending: NO_OUTSIDE_SPENDING,
            outside_spending_total: 0,
            top_spenders: [],
            candidates,
          }),
        ),
      ],
    });
    await screen.findByRole("region", { name: "Candidates" });

    expect(screen.queryByText(/^Outside spending:/)).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Outside spending" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Top outside spenders" })).not.toBeInTheDocument();
    // The "Raised" panel alone: a bar of what each raised, and no legend.
    const option = lastOption();
    expect(option.series).toMatchObject([{ name: "Raised" }]);
    expect(option.legend).toMatchObject({ show: false });
    expect(option.grid).not.toBeInstanceOf(Array);
    expect(option.title).toBeUndefined();
  });

  it("has a fixture whose candidates' outside spending adds up to the race's, kind by kind", () => {
    const sum = (value: (spending: OutsideSpending) => number) =>
      RACE_SENATE_MD.candidates.reduce(
        (total, candidate) => total + value(candidate.outside_spending),
        0,
      );
    const kinds: ((spending: OutsideSpending) => number)[] = [
      (spending) => spending.independent_expenditure.support,
      (spending) => spending.independent_expenditure.oppose,
      (spending) => spending.communication_cost.support,
      (spending) => spending.communication_cost.oppose,
      (spending) => spending.party_coordinated,
      (spending) => spending.electioneering_communication ?? 0,
    ];
    for (const kind of kinds) expect(sum(kind)).toBe(kind(RACE_SENATE_MD.outside_spending));
    expect(RACE_SENATE_MD.outside_spending.independent_expenditure).toEqual({
      support: RACE_SENATE_MD.ie_support,
      oppose: RACE_SENATE_MD.ie_oppose,
    });
    for (const candidate of RACE_SENATE_MD.candidates) {
      expect(candidate.outside_spending.independent_expenditure).toEqual({
        support: candidate.ie_support,
        oppose: candidate.ie_oppose,
      });
    }
    expect(kinds.reduce((total, kind) => total + kind(RACE_SENATE_MD.outside_spending), 0)).toBe(
      RACE_SENATE_MD.outside_spending_total,
    );
    // Every top spender's lines on a candidate add up to that candidate's, kind by kind.
    const lines = (candidateId: string, kind: string, side: "S" | "O" | null) =>
      RACE_SENATE_MD.top_spenders
        .filter(
          (line) =>
            line.candidate_id === candidateId && line.kind === kind && line.support_oppose === side,
        )
        .reduce((total, line) => total + line.amount, 0);
    for (const candidate of RACE_SENATE_MD.candidates) {
      const spending = candidate.outside_spending;
      const id = candidate.candidate_id;
      expect(lines(id, "independent_expenditure", "S")).toBe(
        spending.independent_expenditure.support,
      );
      expect(lines(id, "independent_expenditure", "O")).toBe(
        spending.independent_expenditure.oppose,
      );
      expect(lines(id, "communication_cost", "S")).toBe(spending.communication_cost.support);
      expect(lines(id, "communication_cost", "O")).toBe(spending.communication_cost.oppose);
      expect(lines(id, "party_coordinated", "S")).toBe(spending.party_coordinated);
      expect(lines(id, "electioneering_communication", null)).toBe(
        spending.electioneering_communication ?? 0,
      );
    }
  });

  it("shows each candidate's outside spending by kind and side, and says what each kind is", async () => {
    renderApp("/race/2024/senate/MD");
    const outside = await screen.findByRole("region", { name: "Outside spending" });

    expect(
      within(outside)
        .getAllByRole("columnheader")
        .map((header) => header.textContent)
        // The top spenders' table is the section's too.
        .slice(0, 7),
    ).toEqual([
      "Candidate",
      "Independent expenditures for",
      "Independent expenditures against",
      "Communication costs for",
      "Communication costs against",
      "Party coordinated expenditures",
      "Electioneering communications",
    ]);
    // BRANNIGAN, on whom nobody spent anything, is not listed.
    const [table] = within(outside).getAllByRole("table");
    expect(within(table).getAllByRole("row").slice(1).map(cells)).toEqual([
      ["WHITLOCK, GORDON", "$0", "$80,000", "$0", "$2,400", "$20,000", "$26,410"],
      ["OKAFOR, DIANA", "$150,000", "$45,000", "$4,224", "$0", "$0", "$71,410"],
      ["PELL, MARCUS", "$0", "$0", "$0", "$0", "$0", "$3,500"],
    ]);
    for (const line of [
      /^Independent expenditures: advertising and other spending/,
      /^Communication costs: what a corporation or union spent urging/,
      /^Party coordinated expenditures: what a party committee spent/,
      /^Electioneering communications: broadcast ads naming a candidate/,
    ]) {
      expect(within(outside).getByText(line)).toBeInTheDocument();
    }
    expect(within(outside).getByRole("link", { name: "methodology" })).toHaveAttribute(
      "href",
      "/methodology",
    );
  });

  it("shows only the kinds of outside spending a race had, and a dash for a cycle with no electioneering file", async () => {
    const candidates = RACE_SENATE_MD.candidates.map((candidate) => ({
      ...candidate,
      outside_spending: independentOnly(candidate.ie_support, candidate.ie_oppose),
    }));
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({
            ...RACE_SENATE_MD,
            outside_spending: independentOnly(RACE_SENATE_MD.ie_support, RACE_SENATE_MD.ie_oppose),
            outside_spending_total: RACE_SENATE_MD.ie_support + RACE_SENATE_MD.ie_oppose,
            top_spenders: RACE_SENATE_MD.top_spenders.filter(
              (line) => line.kind === "independent_expenditure",
            ),
            candidates,
          }),
        ),
      ],
    });
    const outside = await screen.findByRole("region", { name: "Outside spending" });

    expect(
      screen.getByText(
        "Outside spending: independent expenditures $150,000 for candidates and $125,000 against",
      ),
    ).toBeInTheDocument();
    const [table] = within(outside).getAllByRole("table");
    expect(within(table).getAllByRole("row").slice(1).map(cells)).toEqual([
      ["WHITLOCK, GORDON", "$0", "$80,000"],
      ["OKAFOR, DIANA", "$150,000", "$45,000"],
    ]);
    expect(within(outside).queryByText(/^Electioneering communications:/)).not.toBeInTheDocument();
    // The chart's two panels: no electioneering one.
    expect(lastOption().title).toMatchObject([{ text: "Raised" }, { text: "For and against" }]);
  });

  it("lists the top outside spenders, a spender that is not a committee badged and linked to its page", async () => {
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Top outside spenders" });

    expect(rows("Top outside spenders").map(cells)).toEqual([
      ["1", "MARYLAND FORWARD PAC", "OKAFOR, DIANA", "Independent expenditures", "For", "$150,000"],
      ["2", "MARYLAND FORWARD PAC", "WHITLOCK, GORDON", "Independent expenditures", "Against", "$80,000"],
      ["3", "RESTORATION PACNot a committee", "OKAFOR, DIANA", "Electioneering communications", "—", "$71,410"],
      ["4", "OLD LINE REPUBLICAN COMMITTEE", "OKAFOR, DIANA", "Independent expenditures", "Against", "$45,000"],
      ["5", "RESTORATION PACNot a committee", "WHITLOCK, GORDON", "Electioneering communications", "—", "$26,410"],
      ["6", "OLD LINE REPUBLICAN COMMITTEE", "WHITLOCK, GORDON", "Party coordinated expenditures", "For", "$20,000"],
      ["7", "STEAMFITTERS LOCAL 486Not a committee", "OKAFOR, DIANA", "Communication costs", "For", "$4,224"],
      ["8", "RESTORATION PACNot a committee", "PELL, MARCUS", "Electioneering communications", "—", "$3,500"],
      ["9", "STEAMFITTERS LOCAL 486Not a committee", "WHITLOCK, GORDON", "Communication costs", "Against", "$2,400"],
    ]);
    const [, , restoration] = rows("Top outside spenders");
    expect(within(restoration).getByRole("link", { name: "RESTORATION PAC" })).toHaveAttribute(
      "href",
      "/committee/C90800207",
    );
    expect(within(restoration).getByText("Not a committee")).toBeInTheDocument();
    expect(within(restoration).getByRole("link", { name: "OKAFOR, DIANA" })).toHaveAttribute(
      "href",
      "/candidate/S4MD00103",
    );
    const [forward] = rows("Top outside spenders");
    expect(within(forward).queryByText("Not a committee")).not.toBeInTheDocument();
    expect(
      within(section("Top outside spenders")).getByText(/^Not a committee: a non-committee spender/),
    ).toBeInTheDocument();
  });

  it("has a fixture whose candidates' cash on hand adds up to the race's", () => {
    const cash = RACE_SENATE_MD.candidates.reduce(
      (total, candidate) => total + (candidate.reported?.cash_on_hand_end ?? 0),
      0,
    );
    expect(cash).toBe(RACE_SENATE_MD.reported_cash_on_hand);
  });

  it("shows a candidate FEC's files have no cash on hand for as not reported, sorted last", async () => {
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({
            ...RACE_SENATE_MD,
            candidates: RACE_SENATE_MD.candidates.map((candidate) =>
              candidate.candidate_id === "S4MD00103"
                ? { ...candidate, reported: null, coverage: null }
                : candidate,
            ),
          }),
        ),
      ],
    });
    const candidates = await screen.findByRole("region", { name: "Candidates" });

    fireEvent.click(within(candidates).getByRole("button", { name: /Cash on hand/ }));

    expect(rows("Candidates").map((row) => [cells(row)[0], cells(row).at(-1)])).toEqual([
      ["WHITLOCK, GORDON", "$291,300"],
      ["BRANNIGAN, TESS", "$1,900"],
      ["PELL, MARCUS", "$1,300"],
      ["OKAFOR, DIANA", "not reported"],
    ]);
  });

  it("has a fixture whose candidates' spending adds up to the race's", () => {
    const spending = RACE_SENATE_MD.candidates.reduce(
      (total, candidate) => total + (candidate.total_operating_expenditures ?? 0),
      0,
    );
    expect(spending).toBeCloseTo(RACE_SENATE_MD.total_operating_expenditures!);
  });

  it("sorts the candidates by spending, most first, a candidate with none available last", async () => {
    renderApp("/race/2024/senate/MD");
    const candidates = await screen.findByRole("region", { name: "Candidates" });

    fireEvent.click(within(candidates).getByRole("button", { name: /Spending/ }));

    expect(rows("Candidates").map((row) => [cells(row)[0], cells(row)[8]])).toEqual([
      ["OKAFOR, DIANA", "$12,223"],
      ["WHITLOCK, GORDON", "$3,900"],
      ["BRANNIGAN, TESS", "not available"],
      ["PELL, MARCUS", "not available"],
    ]);
  });

  it("sorts the candidates from a column header", async () => {
    renderApp("/race/2024/senate/MD");
    const candidates = await screen.findByRole("region", { name: "Candidates" });

    fireEvent.click(within(candidates).getByRole("button", { name: /From individuals/ }));

    expect(rows("Candidates").map((row) => cells(row)[0])).toEqual([
      "OKAFOR, DIANA",
      "WHITLOCK, GORDON",
      "BRANNIGAN, TESS",
      "PELL, MARCUS",
    ]);
  });

  it("lists the committees that gave most, ranked among themselves, linked to their pages", async () => {
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Top contributing committees" });

    // Independent expenditures are the top outside spenders', by candidate and side.
    expect(rows("Top contributing committees").map(cells)).toEqual([
      ["1", "BRICKLAYERS UNITED PAC", "$5,000"],
      ["2", "OLD LINE REPUBLICAN COMMITTEE", "$5,000"],
    ]);
    expect(
      within(section("Top contributing committees")).getByRole("link", {
        name: "BRICKLAYERS UNITED PAC",
      }),
    ).toHaveAttribute("href", "/committee/C00800202");
  });

  it("lists the top donors with what each gave each candidate, and no self-funder", async () => {
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Top donors" });

    expect(rows("Top donors").map(cells)).toEqual([
      ["1", "ZIMMERMANN, ZACH", "OKAFOR, DIANA $3,300BRANNIGAN, TESS $3,300", "$6,600"],
      ["2", "MARLOWE, AUGUSTINE MR.", "WHITLOCK, GORDON $3,300", "$3,300"],
      ["3", "DUBOIS, RAYMOND", "OKAFOR, DIANA $2,500", "$2,500"],
      [
        "4",
        "GALLAGHER, TOMAS",
        "BRANNIGAN, TESS $1,000OKAFOR, DIANA $500WHITLOCK, GORDON $250",
        "$1,750",
      ],
    ]);
    const donors = section("Top donors");
    expect(within(donors).getByRole("link", { name: "MARLOWE, AUGUSTINE MR." })).toHaveAttribute(
      "href",
      "/donor/412",
    );
    const [zimmermann] = rows("Top donors");
    expect(within(zimmermann).getByRole("link", { name: "BRANNIGAN, TESS" })).toHaveAttribute(
      "href",
      "/candidate/S4MD00111",
    );
    // WHITLOCK's $1.75M of his own money makes him no donor to his race.
    expect(rows("Top donors").map((row) => cells(row)[1])).not.toContain("WHITLOCK, GORDON");
  });

  it("charts what each candidate raised, and beside it every kind of outside spending on them", async () => {
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Candidates" });

    const option = lastOption();
    const names = ["WHITLOCK, GORDON", "OKAFOR, DIANA", "BRANNIGAN, TESS", "PELL, MARCUS"];
    // Three panels side by side, the candidates down each one's category axis in one order.
    expect(option.title).toMatchObject([
      { text: "Raised" },
      { text: "For and against" },
      { text: "Electioneering" },
    ]);
    expect(option.grid).toHaveLength(3);
    expect(option.yAxis).toMatchObject([
      { gridIndex: 0, data: names },
      { gridIndex: 1, data: names, axisLabel: { show: false } },
      { gridIndex: 2, data: names, axisLabel: { show: false } },
    ]);
    const signed = { type: "bar", stack: "signed", xAxisIndex: 1, yAxisIndex: 1 };
    expect(option.series).toEqual([
      expect.objectContaining({
        type: "bar",
        name: "Raised",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: [
          expect.objectContaining({ value: 1786850 }),
          expect.objectContaining({ value: 79200 }),
          expect.objectContaining({ value: 7175 }),
          expect.objectContaining({ value: 3250 }),
        ],
      }),
      // Against a candidate left of zero, for them right of it, each kind stacked on its side.
      expect.objectContaining({
        ...signed,
        name: "Independent expenditures against",
        data: [-80000, -45000, 0, 0],
      }),
      expect.objectContaining({
        ...signed,
        name: "Communication costs against",
        data: [-2400, 0, 0, 0],
      }),
      expect.objectContaining({
        ...signed,
        name: "Independent expenditures for",
        data: [0, 150000, 0, 0],
      }),
      expect.objectContaining({ ...signed, name: "Communication costs for", data: [0, 4224, 0, 0] }),
      expect.objectContaining({
        ...signed,
        name: "Party coordinated expenditures",
        data: [20000, 0, 0, 0],
      }),
      // On no side, so a bar of its own, stacked on nothing.
      expect.objectContaining({
        type: "bar",
        name: "Electioneering communications",
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: [26409.5, 71409.5, 0, 3500],
      }),
    ]);
    // Nothing others spent is stacked onto what a candidate raised.
    const series = option.series as object[];
    expect(series[0]).not.toHaveProperty("stack");
    expect(series.at(-1)).not.toHaveProperty("stack");
    expect(option.legend).toMatchObject({
      show: true,
      data: [
        "Independent expenditures against",
        "Communication costs against",
        "Independent expenditures for",
        "Communication costs for",
        "Party coordinated expenditures",
        "Electioneering communications",
      ],
    });
  });

  it("shows the outside spending against a candidate as positive amounts", async () => {
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Candidates" });

    const option = lastOption();
    // Drawn below zero, "against" is told and labelled as the positive amount spent.
    const [, independent, communication] = option.series as {
      tooltip: { valueFormatter: (value: number) => string };
    }[];
    expect(independent.tooltip.valueFormatter(-80000)).toBe("$80,000");
    expect(communication.tooltip.valueFormatter(-2400)).toBe("$2,400");
    const [, signed, electioneering] = option.xAxis as {
      axisLabel: { formatter: (value: number) => string };
    }[];
    expect(signed.axisLabel.formatter(-50000)).toBe("$50K");
    expect(signed.axisLabel.formatter(150000)).toBe("$150K");
    expect(electioneering.axisLabel.formatter(70000)).toBe("$70K");
  });

  it("charts the candidates by what they raised, whatever order the API gives them in", async () => {
    // BRANNIGAN, out-raised by OKAFOR in individual gifts, out-raises her via joint fundraising.
    // PELL, attacked with more than anyone raised, stays last of those who raised money, and
    // SAYRE, who raised nothing, is charted below him for what was spent for her.
    const [model] = RACE_SENATE_MD.candidates;
    const candidates = [
      ...RACE_SENATE_MD.candidates.map((candidate) => {
        if (candidate.candidate_id === "S4MD00111")
          return { ...candidate, total_jfc_transfers: 300000 };
        if (candidate.candidate_id === "S4MD00105")
          return {
            ...candidate,
            ie_oppose: 5000000,
            outside_spending: independentOnly(0, 5000000),
          };
        return candidate;
      }),
      {
        ...model,
        candidate_id: "S4MD00199",
        name: "SAYRE, JUNE",
        total_individual: 0,
        total_committee: 0,
        total_jfc_transfers: 0,
        self_funding: 0,
        ie_support: 10000,
        ie_oppose: 0,
        outside_spending: independentOnly(10000, 0),
      },
    ].reverse();
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({ ...RACE_SENATE_MD, candidate_count: 5, candidates }),
        ),
      ],
    });
    await screen.findByRole("region", { name: "Candidates" });

    expect(lastOption().yAxis).toMatchObject([
      {
        data: [
          "WHITLOCK, GORDON",
          "BRANNIGAN, TESS",
          "OKAFOR, DIANA",
          "PELL, MARCUS",
          "SAYRE, JUNE",
        ],
      },
      {},
      {},
    ]);
  });

  it("charts only the 15 candidates who raised the most, and says the table has the rest", async () => {
    // A presidential race lists every filer: 1,602 in 2024, most with nothing. A bar each would
    // make a canvas taller than the browser will draw.
    const [model] = RACE_SENATE_MD.candidates;
    const candidates = Array.from({ length: 25 }, (_, i) => ({
      ...model,
      candidate_id: `P4000${String(i).padStart(4, "0")}`,
      name: `CANDIDATE ${i}`,
      total_individual: i < 20 ? (20 - i) * 1000 : 0,
      total_committee: 0,
      total_jfc_transfers: 0,
      self_funding: 0,
      ie_support: 0,
      ie_oppose: 0,
      outside_spending: NO_OUTSIDE_SPENDING,
    }));
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({ ...RACE_SENATE_MD, candidate_count: 25, candidates }),
        ),
      ],
    });
    await screen.findByRole("region", { name: "Candidates" });

    const option = lastOption();
    expect(option.yAxis).toMatchObject({
      data: candidates.slice(0, 15).map((candidate) => candidate.name),
    });
    expect(
      screen.getByText("The 15 candidates who raised the most, of 25. The table lists them all."),
    ).toBeInTheDocument();
    expect(rows("Candidates")).toHaveLength(25);
  });

  it("draws no chart when no candidate has any money", async () => {
    const candidates = RACE_SENATE_MD.candidates.map((candidate) => ({
      ...candidate,
      total_individual: 0,
      total_committee: 0,
      total_jfc_transfers: 0,
      self_funding: 0,
      ie_support: 0,
      ie_oppose: 0,
      outside_spending: NO_OUTSIDE_SPENDING,
    }));
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({ ...RACE_SENATE_MD, candidates }),
        ),
      ],
    });
    await screen.findByRole("region", { name: "Candidates" });

    expect(allOptions()).toEqual([]);
    expect(rows("Candidates")).toHaveLength(4);
  });

  it.each([
    ["light", false],
    ["dark", true],
  ])("renders the candidate-totals chart in the %s scheme", async (_scheme, dark) => {
    vi.stubGlobal("matchMedia", matchMedia({ dark }));
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Candidates" });

    // The scheme settles after the first render, so the snapshot is the last option set.
    const ink = dark ? DEFAULT_THEME.colors.dark[0] : DEFAULT_THEME.black;
    await waitFor(() => expect(lastOption().textStyle).toMatchObject({ color: ink }));
    expect(lastOption()).toMatchSnapshot();
  });

  it("badges a special race and renders the empty state when nobody is running", async () => {
    renderApp("/race/2024/senate/NE?special=1");

    expect(
      await screen.findByRole("heading", { level: 1, name: "2024 Senate · Nebraska" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Special")).toBeInTheDocument();
    expect(screen.getByText(/This race has no candidates\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All 2024 races" })).toHaveAttribute(
      "href",
      "/cycles/2024",
    );
    expect(screen.queryByRole("region", { name: "Candidates" })).not.toBeInTheDocument();
  });

  it("labels a House race by its district", async () => {
    renderApp("/race/2024/house/MD-08");

    expect(
      await screen.findByRole("heading", { level: 1, name: "2024 House · Maryland 8th" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("0 candidates · $0 from individuals · $0 from committees"),
    ).toBeInTheDocument();
  });

  it("says when there is no such race, and links to the cycle's index", async () => {
    renderApp("/race/2022/senate/MD");

    expect(
      await screen.findByRole("heading", { name: "No Senate race for MD in 2022" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All 2022 races" })).toHaveAttribute(
      "href",
      "/cycles/2022",
    );
    expect(document.title).toBe("2022 Senate race · fundlens");
  });

  it("names the special race it could not find", async () => {
    renderApp("/race/2024/senate/MD?special=1");

    expect(
      await screen.findByRole("heading", { name: "No Senate special race for MD in 2024" }),
    ).toBeInTheDocument();
  });

  it("shows the loading state until the race arrives", async () => {
    renderApp("/race/2024/senate/MD");

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Candidates" })).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading" })).not.toBeInTheDocument();
  });

  it.each([
    "/race/2024/governor/MD",
    "/race/latest/senate/MD",
    "/race/2024/senate/md",
    "/race/2024/house/MD-5",
  ])("renders NotFound for %s without asking the API", async (path) => {
    renderApp(path);

    expect(await screen.findByText(`There is no page at ${path}.`)).toBeInTheDocument();
  });
});
