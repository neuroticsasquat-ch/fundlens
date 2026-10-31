import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderApp } from "./test/app";

describe("routes", () => {
  it.each([
    ["/race/2024/senate/MD", "Race"],
    ["/race/2024/senate/NE?special=1", "Race"],
    ["/candidate/H4MD05106", "Candidate"],
    ["/committee/C00800106", "Committee"],
    ["/donor/d-1", "Donor"],
    ["/dataset", "Dataset"],
    ["/methodology", "Methodology"],
  ])("%s renders the %s stub until its page is built", async (path, name) => {
    renderApp(path);

    expect(await screen.findByText(`${name} pages are coming.`)).toBeInTheDocument();
    expect(document.title).toBe(`${name} · fundlens`);
  });

  it.each([
    ["/", "Who funds federal races."],
    ["/cycles/2024", "2024 races"],
    ["/search?q=calloway", "Search: calloway"],
  ])("%s renders its page", async (path, heading) => {
    renderApp(path);

    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
  });

  it("renders NotFound for an unknown path", async () => {
    renderApp("/nowhere");

    expect(await screen.findByText("There is no page at /nowhere.")).toBeInTheDocument();
    expect(document.title).toBe("Not found · fundlens");
  });

  it("reaches the stubs from the footer links", async () => {
    const { router } = renderApp("/");
    const footer = screen.getByRole("contentinfo");

    fireEvent.click(within(footer).getByRole("link", { name: "Methodology" }));
    expect(router.state.location.pathname).toBe("/methodology");
    expect(await screen.findByText("Methodology pages are coming.")).toBeInTheDocument();

    fireEvent.click(within(footer).getByRole("link", { name: "Dataset" }));
    expect(await screen.findByText("Dataset pages are coming.")).toBeInTheDocument();
  });
});
