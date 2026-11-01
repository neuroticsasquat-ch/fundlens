import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { META, TWO_CYCLES } from "../test/fixtures";

const twoCycles = http.get("/v1/cycles", ({ response }) => response(200).json(TWO_CYCLES));

const header = () => screen.getByRole("banner");
const switcher = (scope: HTMLElement = header()) =>
  within(scope).getByRole("combobox", { name: "Cycle" });

/** Picks `cycle` in the switcher, once the cycles have loaded. */
async function pick(cycle: string, scope?: HTMLElement) {
  await waitFor(() => expect(switcher(scope)).toBeEnabled());
  fireEvent.click(switcher(scope));
  fireEvent.click(await screen.findByRole("option", { name: cycle }));
}

describe("the shell", () => {
  it("links the brand home and Races to the current cycle", async () => {
    renderApp("/methodology");

    expect(within(header()).getByRole("link", { name: "fundlens" })).toHaveAttribute("href", "/");
    expect(await within(header()).findByRole("link", { name: "Races" })).toHaveAttribute(
      "href",
      "/cycles/2024",
    );
  });

  it.each([
    ["/", "2024"],
    ["/cycles/2022", "2022"],
    ["/race/2022/senate/MD", "2022"],
    ["/candidate/H4MD05106", "2024"],
  ])("shows %s's cycle in the switcher: %s", async (path, cycle) => {
    renderApp(path, { handlers: [twoCycles] });

    await waitFor(() => expect(switcher()).toHaveValue(cycle));
  });

  it.each([
    ["/", "/cycles/2022", ""],
    ["/cycles/2024", "/cycles/2022", ""],
    ["/race/2024/senate/MD", "/race/2022/senate/MD", ""],
    ["/race/2024/house/MD-05", "/race/2022/house/MD-05", ""],
    ["/race/2024/senate/NE?special=1", "/race/2022/senate/NE", ""],
    ["/candidate/H4MD05106", "/candidate/H4MD05106", "#cycle-2022"],
    ["/committee/C00800106", "/committee/C00800106", "#cycle-2022"],
    ["/donor/412", "/cycles/2022", ""],
    ["/search?q=calloway", "/cycles/2022", ""],
    ["/dataset", "/cycles/2022", ""],
    ["/methodology", "/cycles/2022", ""],
    ["/nowhere", "/cycles/2022", ""],
  ])("picking 2022 on %s goes to %s%s", async (path, pathname, hash) => {
    const { router } = renderApp(path, { handlers: [twoCycles] });

    await pick("2022");

    expect(router.state.location.pathname).toBe(pathname);
    expect(router.state.location.search).toBe("");
    expect(router.state.location.hash).toBe(hash);
  });

  it("opens a drawer holding the switcher and the Races link from the Burger", async () => {
    const { router } = renderApp("/", { handlers: [twoCycles] });

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    const drawer = await screen.findByRole("dialog");
    expect(await within(drawer).findByRole("link", { name: "Races" })).toBeInTheDocument();

    await pick("2022", drawer);
    expect(router.state.location.pathname).toBe("/cycles/2022");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("shows the footer links, notices and build, and the provenance once meta loads", async () => {
    renderApp("/");
    const footer = screen.getByRole("contentinfo");

    for (const name of ["Dataset", "Methodology", "GitHub", "API"]) {
      expect(within(footer).getByRole("link", { name })).toBeInTheDocument();
    }
    expect(within(footer).getByRole("link", { name: "API" })).toHaveAttribute(
      "href",
      "https://api.fundlens.org/docs",
    );
    expect(footer).toHaveTextContent("11 CFR 104.15");
    expect(footer).toHaveTextContent("CC BY 4.0");
    expect(footer).toHaveTextContent("fundlens · build dev");
    expect(footer).not.toHaveTextContent("Source: FEC bulk data");

    expect(
      await within(footer).findByText(
        `Source: FEC bulk data · build ${META.build_id} published 2024-11-03`,
      ),
    ).toBeInTheDocument();
  });
});
