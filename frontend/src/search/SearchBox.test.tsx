import { act, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SearchResult } from "../api/client";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { SEARCH_CALLOWAY } from "../test/fixtures";

// A committee scores above a race: the API's top hit is not the first option shown.
const MARYLAND: SearchResult[] = [
  { kind: "committee", id: "C00800103", name: "OKAFOR FOR MARYLAND", aliases: null, score: 0.9 },
  {
    kind: "race",
    id: "2024-S-MD-00",
    name: "2024 Senate MD",
    aliases: "2024/senate/MD",
    score: 0.6,
  },
];

let queries: string[];

const recording = (results: (q: string) => SearchResult[]) =>
  http.get("/v1/search", ({ request, response }) => {
    const q = new URL(request.url).searchParams.get("q") ?? "";
    queries.push(q);
    return response(200).json(results(q));
  });

const box = () => within(screen.getByRole("banner")).getByRole("textbox", { name: "Search" });

async function type(value: string) {
  fireEvent.change(box(), { target: { value } });
  await act(() => vi.advanceTimersByTimeAsync(300));
}

const key = (code: string) => fireEvent.keyDown(box(), { key: code, code });

const dropdown = () => screen.queryByRole("listbox", { name: "Search results" });

beforeEach(() => {
  queries = [];
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("SearchBox", () => {
  it("sends nothing under two characters and one request once typing settles", async () => {
    renderApp("/methodology", { handlers: [recording(() => SEARCH_CALLOWAY)] });

    await type("c");
    expect(queries).toEqual([]);
    expect(within(dropdown()!).queryAllByRole("option")).toEqual([]);
    expect(screen.queryByText("Searching…")).not.toBeInTheDocument();

    fireEvent.change(box(), { target: { value: "ca" } });
    fireEvent.change(box(), { target: { value: "cal" } });
    await type("calloway");
    await screen.findByRole("option", { name: /CALLOWAY, RUTH/ });

    expect(queries).toEqual(["calloway"]);
  });

  it("groups hits by kind, races first, with the aliases and an all-results option", async () => {
    renderApp("/methodology", {
      handlers: [recording((q) => (q === "maryland" ? MARYLAND : SEARCH_CALLOWAY))],
    });

    await type("calloway");
    await screen.findByRole("option", { name: /CALLOWAY, RUTH/ });
    const listbox = dropdown()!;
    expect(within(listbox).getByText("Candidates")).toBeInTheDocument();
    expect(within(listbox).getByText("Committees")).toBeInTheDocument();
    expect(within(listbox).queryByText("Races")).not.toBeInTheDocument();
    expect(
      within(listbox)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual([
      "CALLOWAY, RUTHCALLOWAY FOR CONGRESS",
      "CALLOWAY FOR CONGRESS",
      "CALLOWAY LEADERSHIP FUND",
      "All results for ‘calloway’",
    ]);

    await type("maryland");
    await screen.findByRole("option", { name: "2024 Senate MD" });
    // A race's alias is its slug, which is not shown.
    expect(
      within(dropdown()!)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["2024 Senate MD", "OKAFOR FOR MARYLAND", "All results for ‘maryland’"]);
  });

  it("opens the API's top hit on Enter with nothing highlighted, and clears the box", async () => {
    const { router } = renderApp("/methodology", { handlers: [recording(() => MARYLAND)] });

    await type("maryland");
    await screen.findByRole("option", { name: "2024 Senate MD" });
    key("Enter");

    expect(router.state.location.pathname).toBe("/committee/C00800103");
    expect(box()).toHaveValue("");
  });

  it("opens the highlighted option on Down then Enter", async () => {
    const { router } = renderApp("/methodology", { handlers: [recording(() => MARYLAND)] });

    await type("maryland");
    await screen.findByRole("option", { name: "2024 Senate MD" });
    key("ArrowDown");
    key("Enter");

    expect(router.state.location.pathname).toBe("/race/2024/senate/MD");
  });

  it("opens the results page from all-results and from Enter under two characters", async () => {
    const { router } = renderApp("/methodology", { handlers: [recording(() => SEARCH_CALLOWAY)] });

    await type("calloway");
    fireEvent.click(await screen.findByRole("option", { name: "All results for ‘calloway’" }));
    expect(router.state.location.pathname).toBe("/search");
    expect(router.state.location.search).toBe("?q=calloway");

    await type("c");
    key("Enter");
    expect(router.state.location.search).toBe("?q=c");
  });

  it("closes on Escape and keeps the text", async () => {
    renderApp("/methodology", { handlers: [recording(() => SEARCH_CALLOWAY)] });

    await type("calloway");
    await screen.findByRole("option", { name: /CALLOWAY, RUTH/ });
    key("Escape");

    expect(dropdown()).not.toBeInTheDocument();
    expect(box()).toHaveValue("calloway");
  });

  it("says when nothing matched", async () => {
    renderApp("/methodology", { handlers: [recording(() => [])] });

    await type("zzz");

    expect(await screen.findByText("No results for ‘zzz’")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "All results for ‘zzz’" })).toBeInTheDocument();
  });
});
