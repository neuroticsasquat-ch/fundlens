import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { TWO_CYCLES } from "../test/fixtures";

const main = () => screen.getByRole("main");

describe("HomePage", () => {
  it("says what fundlens is and offers a search box", async () => {
    renderApp("/");

    expect(
      screen.getByRole("heading", { level: 1, name: "Who funds federal races." }),
    ).toBeInTheDocument();
    expect(within(main()).getByRole("textbox", { name: "Search" })).toBeInTheDocument();
    expect(document.title).toBe("fundlens");
  });

  it("shows the current cycle's figures, each linking to its race index", async () => {
    renderApp("/");

    const raised = await within(main()).findByRole("link", { name: /Raised/ });
    expect(raised).toHaveTextContent("$2.2M");
    expect(within(raised).getByTitle("$2,244,775")).toBeInTheDocument();
    expect(within(main()).getByRole("link", { name: /^Races/ })).toHaveTextContent("5");
    expect(within(main()).getByRole("link", { name: /Contributions counted/ })).toHaveTextContent(
      "275",
    );
    for (const tile of ["Races", "Contributions counted", "Raised"]) {
      expect(within(main()).getByRole("link", { name: new RegExp(`^${tile}`) })).toHaveAttribute(
        "href",
        "/cycles/2024",
      );
    }
    expect(
      await within(main()).findByText("2024 cycle · data as of 2024-11-03"),
    ).toBeInTheDocument();
  });

  it("links each office card to its section of the index", async () => {
    renderApp("/");

    for (const [office, anchor] of [
      ["President", "president"],
      ["Senate", "senate"],
      ["House", "house"],
    ]) {
      expect(
        await within(main()).findByRole("link", { name: new RegExp(`^${office}`) }),
      ).toHaveAttribute("href", `/cycles/2024#${anchor}`);
    }
  });

  it("lists the earlier cycles only when there are any", async () => {
    const { unmount } = renderApp("/");
    await within(main()).findByRole("link", { name: /Raised/ });
    expect(screen.queryByText("Earlier cycles:")).not.toBeInTheDocument();
    unmount();

    renderApp("/", {
      handlers: [http.get("/v1/cycles", ({ response }) => response(200).json(TWO_CYCLES))],
    });
    expect(await screen.findByText("Earlier cycles:")).toBeInTheDocument();
    expect(within(main()).getByRole("link", { name: "2022" })).toHaveAttribute(
      "href",
      "/cycles/2022",
    );
  });
});
