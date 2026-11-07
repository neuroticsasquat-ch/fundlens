import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { META } from "../test/fixtures";
import { matchMedia } from "../test/media";

const SECTIONS = [
  "Data sources and cycles",
  "Earmarks are counted once",
  "Self-funding",
  "The seat calendar",
  "How donors are resolved",
  "How well it scores",
  "Known limitations",
  "Using the data",
];

const unscored = http.get("/v1/meta", ({ response }) =>
  response(200).json({
    ...META,
    resolver_version: null,
    model_version: null,
    overrides_count: null,
    adjudications_applied: null,
    precision: null,
    recall: null,
    precision_top: null,
    recall_top: null,
    matched_rows: null,
    dime_version: null,
  }),
);

/** The table whose header row holds `header`. */
const tableWith = async (header: string) =>
  (await screen.findByRole("columnheader", { name: header })).closest("table")!;

describe("MethodologyPage", () => {
  it.each([false, true])("renders every section, dark scheme %s", async (dark) => {
    vi.stubGlobal("matchMedia", matchMedia({ dark }));

    renderApp("/methodology");

    expect(
      await screen.findByRole("heading", { level: 1, name: "Methodology" }),
    ).toBeInTheDocument();
    for (const name of SECTIONS) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
    expect(document.documentElement).toHaveAttribute(
      "data-mantine-color-scheme",
      dark ? "dark" : "light",
    );
    expect(document.title).toBe("Methodology · fundlens");
    // Every slot was filled: none is left in the text.
    expect(await tableWith("Precision")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("{{");
  });

  it("shows the live build's precision and recall, overall and for the top donors", async () => {
    renderApp("/methodology");

    const figures = await tableWith("Precision");
    const [, overall, top] = within(figures).getAllByRole("row");
    expect(overall).toHaveTextContent("Everyone matched to DIME62.9%91.2%");
    expect(top).toHaveTextContent("The 10,000 who gave the most matched dollars95.2%80.2%");
    expect(screen.getByText(/Scored on 41,230,118 contributions/)).toHaveTextContent(
      "matched to DIME version 4.0.",
    );
    expect(screen.getByText(/Bonica, Adam\. 2024\./)).toBeInTheDocument();
  });

  it("says which model and code resolved the build, and what it applied", async () => {
    renderApp("/methodology");

    const commit = await screen.findByRole("link", { name: "0123456" });
    expect(commit).toHaveAttribute(
      "href",
      "https://github.com/neuroticsasquat-ch/fundlens/commit/0123456789abcdef0123456789abcdef01234567",
    );
    expect(commit.closest("p")).toHaveTextContent(
      "Resolved with model 20241102T040000Z by fundlens 0123456, with 2 overrides and 31" +
        " adjudications applied.",
    );
  });

  it("lists each cycle with the date its files were downloaded", async () => {
    renderApp("/methodology");

    const [, row] = within(await tableWith("FEC files downloaded")).getAllByRole("row");
    expect(row).toHaveTextContent("20242024-11-0220241103T060000Z");
  });

  it("says a build not scored yet has no figures", async () => {
    renderApp("/methodology", { handlers: [unscored] });

    expect(
      await screen.findByText(/The live build has not been scored against DIME yet\./),
    ).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Precision" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Resolved with model/)).not.toBeInTheDocument();
  });

  it("links the dataset page inside the app and the repository outside it", async () => {
    const { router } = renderApp("/methodology");

    const dataset = await screen.findByRole("link", { name: "dataset page" });
    // The footer has a GitHub link of its own; this is the page's.
    const footer = screen.getByRole("contentinfo");
    const [github] = screen
      .getAllByRole("link", { name: "GitHub" })
      .filter((link) => !footer.contains(link));
    expect(github).toHaveAttribute("href", "https://github.com/neuroticsasquat-ch/fundlens");
    fireEvent.click(dataset);
    expect(router.state.location.pathname).toBe("/dataset");
  });
});
