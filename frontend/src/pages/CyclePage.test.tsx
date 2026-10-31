import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderApp } from "../test/app";

const section = (name: string) => screen.getByRole("region", { name });
const raceLinks = (name: string) =>
  within(section(name))
    .getAllByRole("row")
    .slice(1)
    .map((row) => {
      const link = within(row).getByRole("link");
      return [link.textContent, link.getAttribute("href")];
    });

describe("CyclePage", () => {
  it("lists every fixture race in its office's section, linked to its race page", async () => {
    renderApp("/cycles/2024");

    await screen.findByRole("region", { name: "President" });
    expect(raceLinks("President")).toEqual([["President", "/race/2024/president/US"]]);
    expect(raceLinks("Senate")).toEqual([
      ["Maryland", "/race/2024/senate/MD"],
      ["Nebraska special", "/race/2024/senate/NE?special=1"],
    ]);
    expect(raceLinks("House")).toEqual([
      ["Maryland 5th", "/race/2024/house/MD-05"],
      ["Maryland 8th", "/race/2024/house/MD-08"],
    ]);
    expect(document.title).toBe("2024 races · fundlens");
    expect(await screen.findByText("5 races · $2.2M raised")).toBeInTheDocument();
  });

  it("shows a race's money and dims the races nobody is running in", async () => {
    renderApp("/cycles/2024");

    const maryland = (await screen.findByRole("link", { name: "Maryland" })).closest("tr")!;
    expect(maryland).toHaveTextContent("$91,975");
    expect(maryland).toHaveTextContent("$10,000");
    expect(maryland).toHaveTextContent("$101,975");
    expect(maryland.style.color).toBe("");

    const nebraska = screen.getByRole("link", { name: "Nebraska special" });
    expect(nebraska.closest("tr")!.style.color).toContain("dimmed");
    expect(nebraska.style.color).toContain("dimmed");
    expect(screen.getByRole("link", { name: "Maryland" }).style.color).not.toContain("dimmed");
  });

  it("filters every section by state but never filters out President", async () => {
    renderApp("/cycles/2024");

    fireEvent.click(await screen.findByRole("combobox", { name: "State" }));
    const states = await screen.findByRole("listbox", { name: "State" });
    expect(
      within(states)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["All states", "Maryland", "Nebraska"]);
    fireEvent.click(within(states).getByRole("option", { name: "Nebraska" }));

    expect(raceLinks("President")).toEqual([["President", "/race/2024/president/US"]]);
    expect(raceLinks("Senate")).toEqual([["Nebraska special", "/race/2024/senate/NE?special=1"]]);
    expect(within(section("House")).getByText("No House races in Nebraska.")).toBeInTheDocument();
  });

  it("sorts a section by Total from its header", async () => {
    renderApp("/cycles/2024");

    const senate = await screen.findByRole("region", { name: "Senate" });
    fireEvent.click(within(senate).getByRole("button", { name: /Total/ }));
    expect(within(senate).getByRole("columnheader", { name: /Total/ })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    fireEvent.click(within(senate).getByRole("button", { name: /Total/ }));

    expect(raceLinks("Senate").map(([label]) => label)).toEqual(["Nebraska special", "Maryland"]);
    expect(within(senate).getByRole("columnheader", { name: /Total/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
  });

  it("scrolls to the office the URL's hash names once the races arrive", async () => {
    const scrolled = vi.spyOn(window.HTMLElement.prototype, "scrollIntoView");
    renderApp("/cycles/2024#senate");

    await screen.findByRole("region", { name: "Senate" });

    await waitFor(() => expect(scrolled).toHaveBeenCalled());
    expect(scrolled.mock.contexts.at(-1)).toBe(screen.getByRole("heading", { name: "Senate" }));
  });

  it("says when gold has no such cycle", async () => {
    renderApp("/cycles/1990");

    expect(await screen.findByText("No 1990 cycle.")).toBeInTheDocument();
    expect(
      within(screen.getByRole("main")).getByRole("link", { name: "Back to fundlens" }),
    ).toHaveAttribute("href", "/");
  });

  it("renders NotFound for a cycle that is not a number", async () => {
    renderApp("/cycles/latest");

    expect(await screen.findByText("There is no page at /cycles/latest.")).toBeInTheDocument();
  });
});
