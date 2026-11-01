import { DEFAULT_THEME } from "@mantine/core";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { lastOption } from "../test/echarts";
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
      screen.getByText("4 candidates · $91,975 from individuals · $10,000 from committees"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Special")).not.toBeInTheDocument();
    expect(document.title).toBe("2024 Senate · Maryland · fundlens");

    expect(rows("Candidates").map(cells)).toEqual([
      ["WHITLOCK, GORDON", "REP", "Open", "$31,850", "$5,000", "$1,750,000", "$1,786,850"],
      ["OKAFOR, DIANA", "DEM", "Open", "$49,700", "$5,000", "$5,000", "$59,700"],
      ["BRANNIGAN, TESS", "DEM", "Open", "$7,175", "$0", "$0", "$7,175"],
      ["PELL, MARCUS", "LIB", "Open", "$3,250", "$0", "$0", "$3,250"],
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
    const sum = (key: "total_individual" | "total_committee") =>
      RACE_SENATE_MD.candidates.reduce((total, candidate) => total + candidate[key], 0);
    expect(sum("total_individual")).toBe(RACE_SENATE_MD.total_individual);
    expect(sum("total_committee")).toBe(RACE_SENATE_MD.total_committee);
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
      ["1", "BRICKLAYERS UNITED PAC", "Contributions", "$5,000"],
      ["2", "OLD LINE REPUBLICAN COMMITTEE", "Contributions", "$5,000"],
    ]);
    expect(
      within(section("Top committees")).getByRole("link", { name: "BRICKLAYERS UNITED PAC" }),
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

  it("draws each candidate's total as a bar in their party's colour", async () => {
    renderApp("/race/2024/senate/MD");
    await screen.findByRole("region", { name: "Candidates" });

    const option = lastOption();
    expect(option.yAxis).toMatchObject({
      data: ["WHITLOCK, GORDON", "OKAFOR, DIANA", "BRANNIGAN, TESS", "PELL, MARCUS"],
    });
    expect(option.series).toMatchObject([
      {
        type: "bar",
        data: [{ value: 1786850 }, { value: 59700 }, { value: 7175 }, { value: 3250 }],
      },
    ]);
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
