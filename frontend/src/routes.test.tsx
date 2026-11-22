import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderApp } from "./test/app";

describe("routes", () => {
  it.each([
    ["/", "Who funds federal races."],
    ["/cycles/2024", "2024 races"],
    ["/race/2024/senate/MD", "2024 Senate · Maryland"],
    ["/race/2024/senate/NE?special=1", "2024 Senate · Nebraska"],
    ["/candidate/S4MD00103", "OKAFOR, DIANA"],
    ["/committee/C00401224", "ACTBLUE"],
    ["/donor/412", "MARLOWE, AUGUSTINE MR."],
    ["/payee/6f774ca924cb0a0b", "BLUE HARBOR STRATEGIES LLC"],
    ["/search?q=calloway", "Search: calloway"],
    ["/dataset", "Dataset"],
    ["/methodology", "Methodology"],
  ])("%s renders its page", async (path, heading) => {
    renderApp(path);

    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
  });

  it("renders NotFound for an unknown path", async () => {
    renderApp("/nowhere");

    expect(await screen.findByText("There is no page at /nowhere.")).toBeInTheDocument();
    expect(document.title).toBe("Not found · fundlens");
  });

  it("reaches the methodology and dataset pages from the footer links", async () => {
    const { router } = renderApp("/");
    const footer = screen.getByRole("contentinfo");

    fireEvent.click(within(footer).getByRole("link", { name: "Methodology" }));
    expect(router.state.location.pathname).toBe("/methodology");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Methodology" }),
    ).toBeInTheDocument();

    fireEvent.click(within(footer).getByRole("link", { name: "Dataset" }));
    expect(router.state.location.pathname).toBe("/dataset");
    expect(await screen.findByRole("heading", { level: 1, name: "Dataset" })).toBeInTheDocument();
  });
});
