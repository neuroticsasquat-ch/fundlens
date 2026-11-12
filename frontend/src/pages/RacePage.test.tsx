import { DEFAULT_THEME } from "@mantine/core";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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
        "$0",
        "$80,000",
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
        "$150,000",
        "$45,000",
      ],
      ["BRANNIGAN, TESS", "DEM", "Open", "$7,175", "$0", "$0", "$0", "$7,175", "$0", "$0"],
      ["PELL, MARCUS", "LIB", "Open", "$3,250", "$0", "$0", "$0", "$3,250", "$0", "$0"],
    ]);
    expect(
      screen.getByText("Independent expenditures: $150,000 for candidates, $125,000 against"),
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
      "Independent expenditures for",
      "Independent expenditures against",
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

  it("says nothing of independent expenditures in a race that had none", async () => {
    const candidates = RACE_SENATE_MD.candidates.map((candidate) => ({
      ...candidate,
      ie_support: 0,
      ie_oppose: 0,
    }));
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({ ...RACE_SENATE_MD, ie_support: 0, ie_oppose: 0, candidates }),
        ),
      ],
    });
    await screen.findByRole("region", { name: "Candidates" });

    expect(screen.queryByText(/^Independent expenditures:/)).not.toBeInTheDocument();
    // A bar of what each raised, and no legend.
    expect(lastOption().series).toMatchObject([{ name: "Raised" }]);
    expect(lastOption().legend).toMatchObject({ show: false });
  });

  it("has a fixture whose candidates' independent expenditures add up to the race's", () => {
    const sum = (key: "ie_support" | "ie_oppose") =>
      RACE_SENATE_MD.candidates.reduce((total, candidate) => total + candidate[key], 0);
    expect(sum("ie_support")).toBe(RACE_SENATE_MD.ie_support);
    expect(sum("ie_oppose")).toBe(RACE_SENATE_MD.ie_oppose);
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

  it("lists the top committees with their kind, linked to their pages", async () => {
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Top committees" });

    expect(rows("Top committees").map(cells)).toEqual([
      ["1", "MARYLAND FORWARD PAC", "Independent expenditures", "$230,000"],
      ["2", "OLD LINE REPUBLICAN COMMITTEE", "Independent expenditures", "$45,000"],
      ["3", "BRICKLAYERS UNITED PAC", "Contributions", "$5,000"],
      ["4", "OLD LINE REPUBLICAN COMMITTEE", "Contributions", "$5,000"],
    ]);
    expect(
      within(section("Top committees")).getByRole("link", { name: "BRICKLAYERS UNITED PAC" }),
    ).toHaveAttribute("href", "/committee/C00800202");
    expect(
      within(section("Top committees")).getByRole("link", { name: "MARYLAND FORWARD PAC" }),
    ).toHaveAttribute("href", "/committee/C00800201");
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

  it("stacks each candidate's total, in their party's colour, and the independent expenditures for and against them", async () => {
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Candidates" });

    const option = lastOption();
    expect(option.yAxis).toMatchObject({
      data: ["WHITLOCK, GORDON", "OKAFOR, DIANA", "BRANNIGAN, TESS", "PELL, MARCUS"],
    });
    expect(option.series).toMatchObject([
      {
        type: "bar",
        name: "Raised",
        stack: "spending",
        data: [{ value: 1786850 }, { value: 79200 }, { value: 7175 }, { value: 3250 }],
      },
      {
        type: "bar",
        name: "Independent expenditures for",
        stack: "spending",
        data: [0, 150000, 0, 0],
      },
      {
        type: "bar",
        name: "Independent expenditures against",
        stack: "spending",
        data: [80000, 45000, 0, 0],
      },
    ]);
    expect(option.legend).toMatchObject({
      show: true,
      data: ["Independent expenditures for", "Independent expenditures against"],
    });
  });

  it("charts the candidates by their bars' length, whatever order the API gives them in", async () => {
    // BRANNIGAN, out-raised by OKAFOR in individual gifts and with no independent expenditures,
    // out-totals her bar via joint fundraising.
    const candidates = RACE_SENATE_MD.candidates.map((candidate) =>
      candidate.candidate_id === "S4MD00111"
        ? { ...candidate, total_jfc_transfers: 300000 }
        : candidate,
    );
    renderApp("/race/2024/senate/MD", {
      handlers: [
        http.get("/v1/races/{cycle}/{office}/{place}", ({ response }) =>
          response(200).json({ ...RACE_SENATE_MD, candidates }),
        ),
      ],
    });
    await screen.findByRole("region", { name: "Candidates" });

    expect(lastOption().yAxis).toMatchObject({
      data: ["WHITLOCK, GORDON", "BRANNIGAN, TESS", "OKAFOR, DIANA", "PELL, MARCUS"],
    });
  });

  it("charts only the 15 candidates with the most money, and says the table has the rest", async () => {
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
      screen.getByText("The 15 candidates with the most money, of 25. The table lists them all."),
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
