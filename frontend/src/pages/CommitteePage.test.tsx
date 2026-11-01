import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Contribution } from "../api/client";
import { http } from "../test/api";
import { renderApp } from "../test/app";
import { contribution, problem } from "../test/fixtures";

const section = (name: string) => screen.getByRole("region", { name });
const rows = (name: string) => within(section(name)).getAllByRole("row").slice(1);
const cells = (row: HTMLElement) =>
  within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent);
const contributors = () => rows("Contributions received").map((row) => cells(row)[1]);

/** Five contributions to OKAFOR FOR MARYLAND, newest first, named A to E. */
const FIVE: Contribution[] = ["A", "B", "C", "D", "E"].map((name, index) =>
  contribution({
    source_record_id: String(index + 1),
    date: `2024-0${9 - index}-01`,
    amount: 100,
    contributor_name: name,
  }),
);

/**
 * The committee's contributions as three cursor pages, A–B, C–D and E; `failAt` answers that
 * cursor with `failStatus` instead, once (410 is a pruned build's). Records every cursor it is
 * asked for.
 */
function threePages({
  failAt,
  failStatus = 410,
}: { failAt?: string; failStatus?: 410 | 503 } = {}) {
  const PAGES: Record<string, { rows: Contribution[]; next: string | null }> = {
    "": { rows: FIVE.slice(0, 2), next: "p2" },
    p2: { rows: FIVE.slice(2, 4), next: "p3" },
    p3: { rows: FIVE.slice(4), next: null },
  };
  const cursors: string[] = [];
  let failed = false;
  const handler = http.get(
    "/v1/committees/{committee_id}/contributions",
    ({ request, response }) => {
      const cursor = new URL(request.url).searchParams.get("cursor") ?? "";
      cursors.push(cursor);
      if (cursor === failAt && !failed) {
        failed = true;
        return failStatus === 410
          ? response(410).json(
              problem(410, "Gone", "The data this cursor pages through has been replaced."),
            )
          : response(503).json(problem(503, "Service Unavailable", "Try again shortly."));
      }
      const page = PAGES[cursor];
      return response(200).json({ contributions: page.rows, next_cursor: page.next });
    },
  );
  return { handler, cursors };
}

describe("CommitteePage", () => {
  it("shows the conduit with no itemized receipts of its own", async () => {
    renderApp("/committee/C00401224");

    expect(await screen.findByRole("heading", { level: 1, name: "ACTBLUE" })).toBeInTheDocument();
    expect(screen.getByText("Conduit")).toBeInTheDocument();
    expect(
      screen.getByText("Hybrid PAC, nonqualified · Unauthorized · FEC C00401224"),
    ).toBeInTheDocument();
    expect(screen.getByText(/so a conduit receives nothing here\./)).toBeInTheDocument();
    expect(rows("Totals by cycle").map(cells)).toEqual([["2024", "$0", "$0", "$0", "$0"]]);
    expect(
      await within(section("Contributions received")).findByText(
        "No itemized contributions to this committee in 2024.",
      ),
    ).toBeInTheDocument();
    expect(document.title).toBe("ACTBLUE · fundlens");
  });

  it("shows the earmarked contribution at its recipient, badged with its conduit", async () => {
    renderApp("/committee/C00800103");

    expect(
      await screen.findByRole("heading", { level: 1, name: "OKAFOR FOR MARYLAND" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Conduit")).not.toBeInTheDocument();
    expect(rows("Totals by cycle").map(cells)).toEqual([
      ["2024", "$37,550", "$25,000", "$5,000", "$0"],
    ]);
    expect(rows("Totals by cycle")[0]).toHaveAttribute("id", "cycle-2024");

    const received = section("Contributions received");
    await within(received).findByText("REYES, CARMEN");
    // The authorized committee's gift is not this committee's.
    expect(contributors()).toEqual([
      "KOWALCZYK, PEGGY",
      "DUBOIS, RAYMOND",
      "YARBROUGH, ELENA",
      "REYES, CARMEN",
      "OKAFOR, DIANA",
    ]);
    const reyes = rows("Contributions received")[3];
    expect(cells(reyes)).toEqual([
      "2024-03-04",
      "REYES, CARMEN",
      "BALTIMORE CITY SCHOOLS",
      "$250",
      "via ActBlue",
    ]);
    expect(within(reyes).getByRole("link", { name: "via ActBlue" })).toHaveAttribute(
      "href",
      "/committee/C00401224",
    );
  });

  it("names the committee's kind and connected org, and lists its top recipients", async () => {
    renderApp("/committee/C00800202");

    expect(
      await screen.findByText("PAC, qualified · Lobbyist/registrant PAC · FEC C00800202"),
    ).toBeInTheDocument();
    expect(screen.getByText("Connected organization: BRICKLAYERS UNITED")).toBeInTheDocument();
    expect(rows("Totals by cycle").map(cells)).toEqual([
      ["2024", "$4,050", "$0", "$0", "$17,500"],
    ]);
    expect(rows("Top recipients").map(cells)).toEqual([
      ["1", "CALLOWAY, RUTH", "Candidate", "$5,000"],
      ["2", "HARGROVE, ELLEN", "Candidate", "$5,000"],
      ["3", "OKAFOR, DIANA", "Candidate", "$5,000"],
      ["4", "DRISCOLL, PETER", "Candidate", "$2,500"],
    ]);
    expect(
      within(section("Top recipients")).getByRole("link", { name: "OKAFOR, DIANA" }),
    ).toHaveAttribute("href", "/candidate/S4MD00103");
    expect(
      within(section("Top donors")).getByText("No resolved individual donors in 2024."),
    ).toBeInTheDocument();
  });

  it("lists the cycle's top donors, linked to their donor pages", async () => {
    renderApp("/committee/C00800103");
    await screen.findByRole("region", { name: "Top donors" });

    expect(rows("Top donors").map(cells)).toEqual([
      ["1", "ZIMMERMANN, ZACH", "$3,300"],
      ["2", "DUBOIS, RAYMOND", "$2,500"],
      ["3", "GALLAGHER, TOMAS", "$500"],
    ]);
    expect(
      within(section("Top donors")).getByRole("link", { name: "DUBOIS, RAYMOND" }),
    ).toHaveAttribute("href", "/donor/236");
  });

  it("says when the committee gave to no one in the cycle", async () => {
    renderApp("/committee/C00800103");

    expect(
      await within(await screen.findByRole("region", { name: "Top recipients" })).findByText(
        "No contributions to candidates or committees in 2024.",
      ),
    ).toBeInTheDocument();
  });

  it("walks three cursor pages with Load more, appending each without duplicates", async () => {
    const { handler, cursors } = threePages();
    renderApp("/committee/C00800103", { handlers: [handler] });

    await within(await screen.findByRole("region", { name: "Contributions received" })).findByText(
      "A",
    );
    expect(contributors()).toEqual(["A", "B"]);

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    await screen.findByText("D");
    expect(contributors()).toEqual(["A", "B", "C", "D"]);

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    await screen.findByText("E");
    expect(contributors()).toEqual(["A", "B", "C", "D", "E"]);
    expect(screen.getByText("5 contributions, newest first")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();

    expect(cursors).toEqual(["", "p2", "p3"]);
  });

  it("keeps the rows when a later page fails, and starts again from the first", async () => {
    const { handler, cursors } = threePages({ failAt: "p2" });
    renderApp("/committee/C00800103", { handlers: [handler] });
    await screen.findByText("B");

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Gone");
    expect(alert).toHaveTextContent("The data this cursor pages through has been replaced.");
    expect(contributors()).toEqual(["A", "B"]);

    fireEvent.click(within(alert).getByRole("button", { name: "Start again" }));
    await screen.findByRole("button", { name: "Load more" });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(contributors()).toEqual(["A", "B"]);
    expect(cursors).toEqual(["", "p2", ""]);
  });

  it("asks for a page that failed for another reason again, keeping its place", async () => {
    const { handler, cursors } = threePages({ failAt: "p2", failStatus: 503 });
    renderApp("/committee/C00800103", { handlers: [handler] });
    await screen.findByText("B");

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    const alert = await screen.findByRole("alert");
    fireEvent.click(within(alert).getByRole("button", { name: "Try again" }));

    await screen.findByText("D");
    expect(contributors()).toEqual(["A", "B", "C", "D"]);
    expect(cursors).toEqual(["", "p2", "p2"]);
  });

  it("says when there is no such committee", async () => {
    renderApp("/committee/C00000000");

    expect(
      await screen.findByRole("heading", { level: 1, name: "No committee C00000000" }),
    ).toBeInTheDocument();
  });
});
