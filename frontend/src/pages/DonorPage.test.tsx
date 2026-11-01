import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { lastOption } from "../test/echarts";
import { MARLOWE_CONTRIBUTIONS } from "../test/fixtures";

const section = (name: string) => screen.getByRole("region", { name });
const rows = (name: string) => within(section(name)).getAllByRole("row").slice(1);
const cells = (row: HTMLElement) =>
  within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent);

/** MARLOWE's contributions as two cursor pages, his first four then the rest; the queries asked. */
function twoPages() {
  const requests: string[] = [];
  const handler = http.get("/v1/donors/{donor_id}/contributions", ({ request, response }) => {
    const query = new URL(request.url).searchParams;
    requests.push(query.toString());
    const last = query.get("cursor") === "p2";
    return response(200).json({
      contributions: last ? MARLOWE_CONTRIBUTIONS.slice(4) : MARLOWE_CONTRIBUTIONS.slice(0, 4),
      next_cursor: last ? null : "p2",
    });
  });
  return { handler, requests };
}

describe("DonorPage", () => {
  it("shows the donor's header: display columns, combined total and name variants", async () => {
    renderApp("/donor/412");

    expect(
      await screen.findByRole("heading", { level: 1, name: "MARLOWE, AUGUSTINE MR." }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("SELF-EMPLOYED · ENTREPRENEUR · BROWNSVILLE, TX"),
    ).toBeInTheDocument();
    expect(screen.getByText("$29,000 given 2022–2024")).toBeInTheDocument();
    expect(screen.getByText("Appears under 4 name variants")).toBeInTheDocument();
    expect(document.title).toBe("MARLOWE, AUGUSTINE MR. · fundlens");
  });

  it("lists the variants as the contributions report them, on request", async () => {
    renderApp("/donor/412");
    const toggle = await screen.findByRole("button", { name: "Show as reported" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("list", { name: "Name variants as reported" })).toBeNull();

    fireEvent.click(toggle);

    const list = await screen.findByRole("list", { name: "Name variants as reported" });
    expect(within(list).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "MARLOWE, AUGUSTINE · ASTRAX · CEO · ZIP 90250 (3)",
      "MARLOWE, AUGUSTINE MR. · SELF-EMPLOYED · ENTREPRENEUR · ZIP 78521 (1)",
      "MARLOWE, AUGUSTINE R. · ASTRA EXPLORATION TECHNOLOGIES · CHIEF ENGINEER · ZIP 78701 (1)",
      "MARLOWE, AUGUSTINE REEVE · VOLTAIC MOTORS · CEO · ZIP 78725 (1)",
      "MARLOWE,AUGUSTINE JR. · ASTRAX · CEO · ZIP 90250 (1)",
    ]);
    expect(screen.getByText(/^As written on 7 contributions;/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hide" })).toHaveAttribute("aria-expanded", "true");
  });

  it("says the variants come from the newest page when there are more", async () => {
    const { handler } = twoPages();
    renderApp("/donor/412", { handlers: [handler] });

    fireEvent.click(await screen.findByRole("button", { name: "Show as reported" }));

    expect(await screen.findByText(/^As written on the newest 4 contributions;/)).toBeVisible();
  });

  it("shows the totals by cycle as a table and a chart", async () => {
    renderApp("/donor/412");
    await screen.findByRole("region", { name: "Totals by cycle" });

    expect(rows("Totals by cycle").map(cells)).toEqual([
      ["2024", "5", "$23,200"],
      ["2022", "2", "$5,800"],
    ]);
    const option = lastOption();
    expect(option.xAxis).toMatchObject({ data: ["2022", "2024"] });
    expect(option.series).toMatchObject([{ type: "bar", name: "Given", data: [5800, 23200] }]);
  });

  it("lists the top recipients over every cycle, linked to their pages", async () => {
    renderApp("/donor/412");
    await screen.findByRole("region", { name: "Top recipients" });

    expect(rows("Top recipients").map(cells)).toEqual([
      ["1", "OLD LINE REPUBLICAN COMMITTEE", "Committee", "$12,900"],
      ["2", "STRATTON, BLAKE", "Candidate", "$6,600"],
      ["3", "WHITLOCK, GORDON", "Candidate", "$6,200"],
      ["4", "DRISCOLL, PETER", "Candidate", "$3,300"],
    ]);
    const recipients = section("Top recipients");
    expect(
      within(recipients).getByRole("link", { name: "OLD LINE REPUBLICAN COMMITTEE" }),
    ).toHaveAttribute("href", "/committee/C00800203");
    expect(within(recipients).getByRole("link", { name: "STRATTON, BLAKE" })).toHaveAttribute(
      "href",
      "/candidate/P40000102",
    );
  });

  it("lists every itemized contribution across both cycles, newest first", async () => {
    renderApp("/donor/412");

    const contributions = await screen.findByRole("region", { name: "Contributions" });
    await within(contributions).findByText("MARLOWE,AUGUSTINE JR.");
    expect(rows("Contributions").map(cells)).toEqual([
      [
        "2024-07-30",
        "2024",
        "OLD LINE REPUBLICAN COMMITTEE",
        "MARLOWE, AUGUSTINE MR.",
        "SELF-EMPLOYED",
        "$10,000",
        "",
      ],
      ["2024-06-03", "2024", "STRATTON, BLAKE", "MARLOWE,AUGUSTINE JR.", "ASTRAX", "$3,300", ""],
      [
        "2024-04-22",
        "2024",
        "DRISCOLL, PETER",
        "MARLOWE, AUGUSTINE REEVE",
        "VOLTAIC MOTORS",
        "$3,300",
        "",
      ],
      [
        "2024-02-01",
        "2024",
        "WHITLOCK, GORDON",
        "MARLOWE, AUGUSTINE R.",
        "ASTRA EXPLORATION TECHNOLOGIES",
        "$3,300",
        "",
      ],
      ["2023-09-12", "2024", "STRATTON, BLAKE", "MARLOWE, AUGUSTINE", "ASTRAX", "$3,300", ""],
      [
        "2022-10-14",
        "2022",
        "OLD LINE REPUBLICAN COMMITTEE",
        "MARLOWE, AUGUSTINE",
        "ASTRAX",
        "$2,900",
        "",
      ],
      [
        "2022-03-08",
        "2022",
        "WHITLOCK, GORDON",
        "MARLOWE, AUGUSTINE",
        "ASTRAX",
        "$2,900",
        "via WinRed",
      ],
    ]);
    expect(within(contributions).getByText("7 contributions, newest first")).toBeVisible();
    const [, stratton] = rows("Contributions");
    expect(within(stratton).getByRole("link", { name: "STRATTON, BLAKE" })).toHaveAttribute(
      "href",
      "/candidate/P40000102",
    );
    expect(within(contributions).getByRole("link", { name: "via WinRed" })).toHaveAttribute(
      "href",
      "/committee/C00694323",
    );
  });

  it("asks for every cycle's contributions only once the variants are opened", async () => {
    const { handler, requests } = twoPages();
    renderApp("/donor/412?cycle=2022", { handlers: [handler] });
    await within(await screen.findByRole("region", { name: "Contributions" })).findByText(
      "MARLOWE, AUGUSTINE R.",
    );
    expect(requests).toEqual(["cycle=2022"]);

    fireEvent.click(screen.getByRole("button", { name: "Show as reported" }));

    await screen.findByRole("list", { name: "Name variants as reported" });
    expect(requests).toEqual(["cycle=2022", ""]);
  });

  it("filters the contributions to one cycle through the URL", async () => {
    const { router } = renderApp("/donor/412");
    await within(await screen.findByRole("region", { name: "Contributions" })).findByText(
      "7 contributions, newest first",
    );

    fireEvent.click(screen.getByRole("combobox", { name: "Contributions cycle" }));
    fireEvent.click(await screen.findByRole("option", { name: "2022" }));

    expect(
      await within(section("Contributions")).findByText("2 contributions, newest first"),
    ).toBeVisible();
    expect(rows("Contributions").map((row) => cells(row)[1])).toEqual(["2022", "2022"]);
    expect(router.state.location.search).toBe("?cycle=2022");

    fireEvent.click(screen.getByRole("combobox", { name: "Contributions cycle" }));
    fireEvent.click(await screen.findByRole("option", { name: "All cycles" }));
    expect(
      await within(section("Contributions")).findByText("7 contributions, newest first"),
    ).toBeVisible();
    expect(router.state.location.search).toBe("");
  });

  it("loads the next cursor's page on request", async () => {
    const { handler, requests } = twoPages();
    renderApp("/donor/412", { handlers: [handler] });
    const contributions = await screen.findByRole("region", { name: "Contributions" });
    await within(contributions).findByText("4 contributions, newest first");

    fireEvent.click(within(contributions).getByRole("button", { name: "Load more" }));

    expect(await within(contributions).findByText("7 contributions, newest first")).toBeVisible();
    expect(within(contributions).queryByRole("button", { name: "Load more" })).toBeNull();
    // The variant list and the table ask for every cycle the same way: one request a page.
    expect(requests).toEqual(["", "cursor=p2"]);
  });

  it("lands a merged donor's old id on the canonical page, keeping the query", async () => {
    const { router } = renderApp("/donor/77?cycle=2022");

    expect(
      await screen.findByRole("heading", { level: 1, name: "MARLOWE, AUGUSTINE MR." }),
    ).toBeInTheDocument();
    await waitFor(() => expect(router.state.location.pathname).toBe("/donor/412"));
    expect(router.state.location.search).toBe("?cycle=2022");
    expect(screen.getByRole("combobox", { name: "Contributions cycle" })).toHaveValue("2022");
  });

  it("says when there is no such donor", async () => {
    renderApp("/donor/999");

    expect(
      await screen.findByRole("heading", { level: 1, name: "No donor 999" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to fundlens" })).toHaveAttribute("href", "/");
  });

  it.each(["/donor/abc", "/donor/0", "/donor/12x"])(
    "renders NotFound for %s without asking the API",
    async (path) => {
      renderApp(path);

      expect(await screen.findByText(`There is no page at ${path}.`)).toBeInTheDocument();
    },
  );
});
