import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http } from "../test/api";
import { renderApp } from "../test/app";

describe("SearchPage", () => {
  it("asks for two characters and sends nothing for fewer", async () => {
    const queries: string[] = [];
    renderApp("/search?q=c", {
      handlers: [
        http.get("/v1/search", ({ request, response }) => {
          queries.push(new URL(request.url).search);
          return response(200).json([]);
        }),
      ],
    });

    expect(await screen.findByText("Type at least two characters to search.")).toBeInTheDocument();
    expect(queries).toEqual([]);
    expect(document.title).toBe("Search: c · fundlens");
  });

  it("lists the hits grouped by kind, linked, with their kind and aliases", async () => {
    renderApp("/search?q=calloway");

    const candidates = await screen.findByRole("region", { name: "Candidates" });
    const ruth = within(candidates).getByRole("link", { name: "CALLOWAY, RUTH" });
    expect(ruth).toHaveAttribute("href", "/candidate/H4MD05106");
    expect(within(candidates).getByText("candidate")).toBeInTheDocument();
    expect(within(candidates).getByText("CALLOWAY FOR CONGRESS")).toBeInTheDocument();

    const committees = screen.getByRole("region", { name: "Committees" });
    expect(
      within(committees)
        .getAllByRole("link")
        .map((l) => l.getAttribute("href")),
    ).toEqual(["/committee/C00800106", "/committee/C00800114"]);
    expect(screen.queryByRole("region", { name: "Races" })).not.toBeInTheDocument();
  });

  it("says when nothing matched", async () => {
    renderApp("/search?q=zzz");

    expect(await screen.findByText("No results for ‘zzz’.")).toBeInTheDocument();
  });
});
